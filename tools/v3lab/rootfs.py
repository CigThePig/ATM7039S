"""Phase-aware verification of the Koriki root filesystem container (boot/BATOCERA).

Why this exists (OBS-001): Koriki's ramdisk /init loop-mounts boot/BATOCERA read-write as
the root filesystem, so the container's bytes change on the first boot. A byte hash can
therefore only verify the downloaded image and a freshly flashed card. After a boot the
card is verified semantically: every reachable path is described without inode numbers
or timestamps, compared with a trusted baseline, and each difference must be explained
by a rule derived from the pinned firmware (evidence/firmware/koriki-v1.0-first-boot.json).
Anything unexplained fails closed.

Phases
    pristine      the container inside the downloaded image     -> byte hash == catalogue
    fresh-flash   the card before its first boot                 -> byte hash == catalogue
    prepared      the card after the first boot, before capture  -> semantic vs pristine,
                                                                    first-boot rules
    post-capture  the card after the capture boot                -> semantic vs prepared
                                                                    baseline, rerun rules

What is NOT covered (stated in every report): journal contents, free/unallocated blocks,
unreachable or orphaned inodes, deleted data, block allocation, timestamps. The health
gate reports the superblock state, error count, orphan list and journal-recovery flag,
and refuses filesystems with features this reader does not understand.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import struct

SCHEMA = 2
MAX_PATHS = 2_000_000
READ = 1024 * 1024

# ext4 feature bits (linux/fs/ext4/ext4.h)
INCOMPAT = {0x2: 'filetype', 0x4: 'recover', 0x40: 'extents', 0x80: '64bit', 0x200: 'flex_bg'}
COMPAT = {0x4: 'has_journal', 0x8: 'ext_attr', 0x10: 'resize_inode', 0x20: 'dir_index'}
RO_COMPAT = {0x1: 'sparse_super', 0x2: 'large_file', 0x8: 'huge_file', 0x20: 'dir_nlink', 0x40: 'extra_isize'}
# Inode flags that describe on-disk layout, not file semantics: EXTENTS, INDEX (htree), HUGE_FILE.
STORAGE_FLAGS = 0x80000 | 0x1000 | 0x40000
TYPES = {stat.S_IFDIR: 'dir', stat.S_IFREG: 'file', stat.S_IFLNK: 'symlink', stat.S_IFCHR: 'chardev',
         stat.S_IFBLK: 'blockdev', stat.S_IFIFO: 'fifo', stat.S_IFSOCK: 'socket'}
SENSITIVE = ('/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/lib', '/usr/lib', '/root', '/boot', '/init',
             '/linuxrc', '/usr/share/batocera', '/usr/libexec')
COVERAGE = ('Reachable directory tree: type, permissions, owner, group, semantic inode flags, extended attributes '
            '(name and value hash), link counts, hard-link topology, symbolic-link targets, device numbers, regular '
            'file size and SHA-256. Not covered: timestamps, journal contents, free or unallocated blocks, '
            'unreachable or orphaned inodes, deleted data and block allocation.')


class RootfsError(RuntimeError):
    pass


# --------------------------------------------------------------------------- reading

def health(ext):
    """Superblock facts that decide whether the tree can be trusted at all."""
    sb = ext.sb
    fails, review, facts = [], [], {}
    for name, value, known in (('incompat', int(sb.s_feature_incompat), INCOMPAT),
                               ('compat', int(sb.s_feature_compat), COMPAT),
                               ('ro_compat', int(sb.s_feature_ro_compat), RO_COMPAT)):
        unknown = value & ~sum(known)
        facts[name] = sorted(v for k, v in known.items() if value & k)
        if unknown:
            fails.append(f'unsupported ext4 {name} features 0x{unknown:x}: this reader cannot verify such a filesystem')
    if int(sb.s_feature_incompat) & 0x4:
        review.append('the journal needs recovery (the filesystem was not cleanly unmounted): Linux will replay it '
                      'on the next mount, so the tree read here may not be what the handheld sees')
    state = int(sb.s_state)
    facts['state'] = state
    if not state & 1:
        review.append('superblock is not marked clean')
    if state & 2:
        fails.append('superblock records filesystem errors')
    if int(getattr(sb, 's_error_count', 0) or 0):
        fails.append(f'superblock error count {int(sb.s_error_count)}')
    if int(sb.s_last_orphan):
        review.append('orphan inode list is not empty (files deleted while open); their data is outside this check')
    facts.update(block_size=ext.block_size, inodes=int(sb.s_inodes_count),
                 blocks=int(sb.s_blocks_count_lo) | (int(sb.s_blocks_count_hi) << 32), volume_name=ext.volume_name)
    return dict(fails=fails, review=review, facts=facts)


def _device(node):
    # i_block is the raw 60-byte block map; device numbers live in its first two words.
    b0, b1 = struct.unpack('<II', bytes(node.inode.i_block)[:8])
    # ext4 old (16-bit) encoding in i_block[0], new encoding in i_block[1].
    if b0:
        return [(b0 >> 8) & 0xff, b0 & 0xff]
    return [(b1 & 0xfff00) >> 8, (b1 & 0xff) | ((b1 >> 12) & 0xfff00)]


def describe(node, path, cached_hash=None):
    """One path's semantic record; the inode number is returned separately."""
    ino = node.inode
    mode = int(ino.i_mode)
    kind = TYPES.get(stat.S_IFMT(mode), f'unknown-{stat.S_IFMT(mode):o}')
    uid = int(ino.i_uid) | (int(getattr(ino, 'i_uid_high', 0) or 0) << 16)
    gid = int(ino.i_gid) | (int(getattr(ino, 'i_gid_high', 0) or 0) << 16)
    flags = int(ino.i_flags)
    rec = dict(type=kind, perm=f'{stat.S_IMODE(mode):04o}', uid=uid, gid=gid, flags=f'0x{flags & ~STORAGE_FLAGS:x}',
               storage_flags=f'0x{flags & STORAGE_FLAGS:x}', links=int(ino.i_links_count))
    xa = []
    for x in node.xattr:
        value = bytes(x.value)
        name = str(x.name) if str(x.name).startswith(str(x.prefix)) else f'{x.prefix}{x.name}'
        xa.append([name, len(value), hashlib.sha256(value).hexdigest()])
    rec['xattrs'] = sorted(xa)
    if kind == 'file':
        digest = cached_hash(int(node.inum)) if cached_hash else None
        if digest is None:
            h, n = hashlib.sha256(), 0
            with node.open() as f:
                while chunk := f.read(READ):
                    h.update(chunk)
                    n += len(chunk)
            if n != node.size:
                raise RootfsError(f'short read at {path}: {n} of {node.size} bytes')
            digest = h.hexdigest()
        rec.update(size=int(node.size), sha256=digest)
    elif kind == 'symlink':
        rec['target'] = node.link
    elif kind in ('chardev', 'blockdev'):
        rec['device'] = _device(node)
    return rec


def canonical(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


class Manifest:
    """paths -> semantic record, plus hard-link groups. Comparable across inode renumbering."""

    def __init__(self, entries, inodes, health_report, source_sha256):
        self.entries, self.inodes, self.health, self.source_sha256 = entries, inodes, health_report, source_sha256

    def hardlink_groups(self):
        groups = {}
        for p, ino in self.inodes.items():
            if self.entries[p]['type'] != 'dir':
                groups.setdefault(ino, []).append(p)
        return sorted(sorted(g) for g in groups.values() if len(g) > 1)

    def digest(self):
        h = hashlib.sha256()
        for p in sorted(self.entries):
            h.update(canonical([p, self.entries[p]]).encode() + b'\n')
        h.update(canonical(self.hardlink_groups()).encode())
        return h.hexdigest()

    def to_json(self):
        return dict(schema=SCHEMA, source_sha256=self.source_sha256, health=self.health, digest=self.digest(),
                    entries=self.entries, hardlink_groups=self.hardlink_groups(),
                    inodes=self.inodes)

    @classmethod
    def from_json(cls, d):
        if d.get('schema') != SCHEMA:
            raise RootfsError('stored manifest uses an older format; it will be rebuilt')
        m = cls(d['entries'], d['inodes'], d['health'], d['source_sha256'])
        if m.digest() != d['digest']:
            raise RootfsError('stored manifest is damaged (digest mismatch)')
        return m


def scan(ext, source_sha256, checkpoint_db, job=None, estimate=None, interrupt_after=None):
    """Walk the whole tree; record every path in a SQLite checkpoint keyed by the source hash.

    Interrupting (cancel, crash, power loss) keeps every committed path; the next run
    replays the directory walk and only hashes what is missing, so a resumed scan
    produces exactly the records a fresh scan would.
    """
    rep = health(ext)
    if rep['fails']:
        # Do not walk a filesystem we cannot interpret; report why.
        return Manifest({}, {}, rep, source_sha256)
    con = sqlite3.connect(checkpoint_db, timeout=5)
    try:
        con.execute('PRAGMA synchronous=FULL')
        con.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS entries (path TEXT PRIMARY KEY, inode INTEGER NOT NULL, rec TEXT NOT NULL)')
        meta = dict(con.execute('SELECT key, value FROM meta'))
        ident = {'schema': str(SCHEMA), 'source_sha256': source_sha256, 'checkpoint_format': '2'}
        if meta and any(meta.get(k) != v for k, v in ident.items()):
            raise RootfsError('checkpoint belongs to a different filesystem or tool version; it is ignored')
        if not meta:
            if con.execute('SELECT COUNT(*) FROM entries').fetchone()[0]:
                raise RootfsError('checkpoint has entries but no identity; refusing to reuse it')
            con.executemany('INSERT INTO meta VALUES (?, ?)', ident.items())
            con.commit()
        saved = {p: (i, json.loads(r)) for p, i, r in con.execute('SELECT path, inode, rec FROM entries')}
        hashes = {i: r['sha256'] for i, r in saved.values() if r.get('type') == 'file'}
        if meta.get('complete') == 'yes' and meta.get('count') == str(len(saved)):
            entries = {p: r for p, (i, r) in saved.items()}
            cached = Manifest(entries, {p: i for p, (i, r) in saved.items()}, rep, source_sha256)
            if cached.digest() != meta.get('digest'):
                raise RootfsError('checkpoint belongs to a different filesystem or tool version (damaged digest)')
            return cached
        if job:
            job.start_phase('reading the file list', estimate, 'paths')
            job.message = f'{len(saved):,} paths recovered from an earlier run' if saved else ''
        entries, inodes, visited_dirs = {}, {}, set()
        stack = [('/', ext.get('/'))]
        pending, new = 0, 0
        try:
            while stack:
                path, node = stack.pop()
                if path in entries:
                    raise RootfsError(f'duplicate path {path}: directory structure is inconsistent')
                if len(entries) >= MAX_PATHS:
                    raise RootfsError('more paths than any Koriki image contains; refusing to continue')
                ino = int(node.inum)
                if path in saved and saved[path][0] == ino:
                    rec = saved[path][1]
                else:
                    try:
                        rec = json.loads(canonical(describe(node, path, hashes.get)))
                    except RootfsError:
                        raise
                    except Exception as e:  # unreadable content is a finding, not a crash
                        rec = dict(type='unreadable', error=f'{type(e).__name__}: {e}'[:300])
                    con.execute('INSERT OR REPLACE INTO entries VALUES (?, ?, ?)', (path, ino, canonical(rec)))
                    if rec.get('type') == 'file':
                        hashes.setdefault(ino, rec['sha256'])
                    pending += 1
                    new += 1
                entries[path], inodes[path] = rec, ino
                if rec['type'] == 'dir':
                    if ino in visited_dirs:
                        raise RootfsError(f'directory inode {ino} is reachable twice (at {path}): filesystem damage')
                    visited_dirs.add(ino)
                    for name, child in sorted(node.listdir().items()):
                        if name in ('.', '..'):
                            continue
                        if '/' in name or '\0' in name or not name:
                            raise RootfsError(f'invalid name in {path}')
                        stack.append((path.rstrip('/') + '/' + name, child))
                if pending >= 200:
                    con.commit()
                    pending = 0
                if job:
                    job.advance(1)
                if interrupt_after is not None and new >= interrupt_after:
                    raise KeyboardInterrupt('test interruption')
            stale = set(saved) - set(entries)
            if stale:
                con.executemany('DELETE FROM entries WHERE path = ?', [(p,) for p in stale])
            con.execute("INSERT OR REPLACE INTO meta VALUES ('complete', 'yes')")
            con.execute("INSERT OR REPLACE INTO meta VALUES ('count', ?)", (str(len(entries)),))
            con.execute("INSERT OR REPLACE INTO meta VALUES ('digest', ?)",
                        (Manifest(entries, inodes, rep, source_sha256).digest(),))
            con.commit()
        except BaseException:
            con.commit()
            raise
        return Manifest(entries, inodes, rep, source_sha256)
    finally:
        con.close()


def open_container_in_image(image, catalogue, rootcat):
    """Context manager yielding a file object for boot/BATOCERA inside the pinned image."""
    import contextlib
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from firmware_catalogue import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS

    @contextlib.contextmanager
    def opener():
        part = next(x for x in catalogue['partitions'] if x['index'] == 1)
        with open(image, 'rb') as raw, PyFatBytesIOFS(Window(raw, part['offset'], part['size'])) as fs:
            with fs.openbin(rootcat['container_path']) as f:
                yield f
    return opener


# --------------------------------------------------------------------------- policy and comparison

def load_policy(root):
    return json.loads((Path(root) / 'evidence/firmware/koriki-v1.0-first-boot.json').read_text(encoding='utf-8'))


def _matches(rec, expect):
    """Does a record satisfy a policy expectation? Returns a list of mismatches."""
    bad = []
    if rec is None:
        return ['path is absent']
    for k, v in expect.items():
        if k == 'size_multiple_of':
            if rec.get('size') is None or rec['size'] % v:
                bad.append(f'size {rec.get("size")} is not a multiple of {v}')
        elif k == 'max_size':
            if rec.get('size') is None or rec['size'] > v:
                bad.append(f'size {rec.get("size")} exceeds {v}')
        elif k == 'no_children':
            continue
        elif rec.get(k) != v:
            bad.append(f'{k} is {rec.get(k)!r}, expected {v!r}')
    return bad


def _sensitive(path):
    return any(path == s or path.startswith(s + '/') for s in SENSITIVE)


def compare(baseline, current, policy, phase):
    """Classify every difference between two manifests for one phase.

    Returns a report with verdict PASS, REVIEW or FAIL and one item per difference.
    """
    if phase not in ('prepared', 'post-capture'):
        raise ValueError('semantic comparison applies to the prepared and post-capture phases only')
    items, notes = [], []
    rules = [r for r in policy['rules'] if phase in r['phases']]
    a, b = baseline.entries, current.entries
    explained = set()
    for r in rules:
        p = r['path']
        before, after = a.get(p), b.get(p)
        if r['change'] == 'added':
            if before is None and after is not None:
                bad = _matches(after, r['after'])
                items.append(dict(path=p, change='added', rule=r['id'], status='fail' if bad else 'expected',
                                  detail='; '.join(bad) or r['explanation']))
                explained.add(p)
            elif before is not None and after is not None and r.get('may_already_exist'):
                bad = _matches(after, r['after'])
                if before != after:
                    items.append(dict(path=p, change='changed', rule=r['id'], status='fail' if bad else 'expected',
                                      detail='; '.join(bad) or r['explanation']))
                explained.add(p)
        elif r['change'] == 'changed':
            if before is not None and after is not None and before != after:
                bad = _matches(before, r.get('before', {})) + _matches(after, r['after'])
                items.append(dict(path=p, change='changed', rule=r['id'], status='fail' if bad else 'expected',
                                  detail='; '.join(bad) or r['explanation']))
                explained.add(p)
                if r['after'].get('no_children'):
                    kids = [q for q in b if q.startswith(p.rstrip('/') + '/')]
                    for q in kids:
                        items.append(dict(path=q, change='added', rule=None, status='fail', sensitive=True,
                                          detail=f'{p} was expected to stay empty ({r["explanation"]})'))
                        explained.add(q)
    # Directory link counts follow their subdirectories (ext4 dir_nlink semantics).
    subdirs_a = _subdir_counts(a)
    subdirs_b = _subdir_counts(b)
    for p in sorted(set(a) | set(b)):
        if p in explained:
            continue
        ra, rb = a.get(p), b.get(p)
        if ra == rb:
            continue
        if ra is None or rb is None:
            rec = rb or ra
            status = 'fail'
            why = ('unexpected new ' if ra is None else 'unexpected removal of ') + rec['type']
            if rec['type'] == 'file' and int(rec.get('perm', '0'), 8) & 0o111:
                why += ' (executable)'
            if rec['type'] == 'unreadable':
                why = 'content could not be read: ' + rec.get('error', '')
            items.append(dict(path=p, change='added' if ra is None else 'removed', rule=None, status=status,
                              sensitive=_sensitive(p) or rec['type'] in ('chardev', 'blockdev'), detail=why))
            continue
        fields = sorted(k for k in set(ra) | set(rb) if ra.get(k) != rb.get(k))
        metadata_only = set(fields) <= {'links', 'storage_flags'} and ra['type'] == rb['type'] == 'dir'
        if metadata_only and 'links' in fields:
            delta = rb['links'] - ra['links']
            if delta != subdirs_b.get(p, 0) - subdirs_a.get(p, 0):
                metadata_only = False
        if metadata_only:
            items.append(dict(path=p, change='changed', rule='dir-link-count', status='metadata',
                              detail=f"directory link count {ra.get('links')} -> {rb.get('links')} follows its "
                                     'subdirectory count (ext4 bookkeeping, not a content change)'))
            continue
        if set(fields) == {'storage_flags'}:
            items.append(dict(path=p, change='changed', rule='storage-layout', status='metadata',
                              detail='on-disk layout flag changed (extents/index), content unchanged'))
            continue
        items.append(dict(path=p, change='changed', rule=None, status='fail', fields=fields,
                          sensitive=_sensitive(p) or bool({'perm', 'uid', 'gid', 'xattrs', 'target', 'sha256'} & set(fields)),
                          detail='unexpected change of ' + ', '.join(fields),
                          before={k: ra.get(k) for k in fields}, after={k: rb.get(k) for k in fields}))
    # Hard-link topology among unchanged paths.
    ga = {tuple(g) for g in baseline.hardlink_groups()}
    gb = {tuple(g) for g in current.hardlink_groups()}
    for g in sorted(ga ^ gb):
        # No policy rule authorizes hard-link group changes, even at runtime paths.
        items.append(dict(path=g[0], change='hardlinks', rule=None, status='fail', sensitive=True,
                          detail=('hard-link group appeared: ' if g in gb else 'hard-link group disappeared: ') + ', '.join(g)))
    # Rules whose change did not happen are not failures (a step may not have run), but are reported.
    seen = {i.get('rule') for i in items}
    for r in rules:
        if r['id'] not in seen and r.get('required_in_phase') == phase:
            if r['change'] == 'added' and r['path'] in a and r['path'] in b and a[r['path']] == b[r['path']]:
                continue
            notes.append(f"{r['id']}: expected change did not occur ({r['path']}); the step that makes it may not have run")
    h_fail = current.health['fails']
    h_review = current.health['review']
    fails = [i for i in items if i['status'] == 'fail']
    verdict = 'FAIL' if (fails or h_fail) else ('REVIEW' if (h_review or notes) else 'PASS')
    for k in ('volume_name', 'inodes', 'blocks', 'incompat', 'compat', 'ro_compat'):
        if baseline.health['facts'].get(k) != current.health['facts'].get(k):
            fails.append(dict(path='(superblock)', status='fail', detail=f'filesystem {k} changed'))
            items.append(fails[-1])
            verdict = 'FAIL'
    return dict(phase=phase, verdict=verdict, baseline_digest=baseline.digest(), current_digest=current.digest(),
                baseline_source_sha256=baseline.source_sha256, current_source_sha256=current.source_sha256,
                baseline_paths=len(a), current_paths=len(b), items=items, notes=notes,
                health=current.health, coverage=COVERAGE, policy=policy['id'],
                counts={s: sum(1 for i in items if i['status'] == s) for s in ('expected', 'metadata', 'fail')})


def _subdir_counts(entries):
    out = {}
    for p, r in entries.items():
        if r['type'] == 'dir' and p != '/':
            parent = str(PurePosixPath(p).parent)
            out[parent] = out.get(parent, 0) + 1
    return out


def summarize(report):
    """Plain-language lines for the operator."""
    v = report['verdict']
    lines = []
    if v == 'PASS':
        lines.append('The card\'s system files are in the expected state.')
    elif v == 'REVIEW':
        lines.append('The card looks consistent, but something needs a second opinion before continuing.')
    else:
        lines.append('The card\'s system files contain changes that are not explained. Stop here and keep the card as it is.')
    c = report['counts']
    lines.append(f"{c['expected']} expected change(s), {c['metadata']} bookkeeping change(s), {c['fail']} unexplained.")
    for i in report['items']:
        if i['status'] == 'fail':
            lines.append(f"  UNEXPLAINED  {i['path']}: {i['detail']}")
    for n in report['notes'] + report['health']['review'] + report['health']['fails']:
        lines.append('  NOTE  ' + n)
    return lines
