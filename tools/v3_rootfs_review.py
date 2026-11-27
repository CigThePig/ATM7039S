"""V3 root filesystem diagnostic, recovery edition (V2.1).
Run from the project: python tools/v3_rootfs_review.py [--card E:/boot/BATOCERA]
Reads the source image and card, writes only local diagnostic files. No preflight override.
"""
import argparse
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import time

VERSION = '2.2'
SCHEMA = 1
CHUNK = 4 * 1024 * 1024
MIB = 1024 * 1024
SCOPE = ('Reachable directory tree, regular file contents, symlinks, inode IDs, modes, '
         'ownership fields, flags, link counts, xattrs and device IDs; excludes timestamps, '
         'journal, allocation state, free space and unreferenced inodes.')


def say(*args):
    print(*args, flush=True)


def low_priority():
    try:
        if sys.platform == 'win32':
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.GetCurrentProcess.restype = ctypes.c_void_p
            k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            k.SetPriorityClass.restype = ctypes.c_int
            if not k.SetPriorityClass(k.GetCurrentProcess(), 0x40):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.nice(10)
        say('Background CPU priority enabled.')
    except Exception as e:
        say('WARNING: Could not lower CPU priority:', e)


@contextlib.contextmanager
def session_lock(path):
    with path.open('a+b') as f:
        if not path.stat().st_size:
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as e:
                raise RuntimeError('Another diagnostic is running. Close it first.') from e
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                raise RuntimeError('Another diagnostic is running. Close it first.') from e
        try:
            yield
        finally:
            # OS releases the lock even after a crash; the lock file itself is harmless.
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def atomic_json(path, data):
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=True)
        f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)


def sha_file(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def source_stamp(path):
    s = path.stat()
    return (s.st_size, s.st_mtime_ns, s.st_dev, s.st_ino)


def windows_roots():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetLogicalDrives.restype = ctypes.c_uint32
    k.GetVolumeInformationW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32,
                                       ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_wchar_p, ctypes.c_uint32]
    k.GetVolumeInformationW.restype = ctypes.c_int
    k.GetDriveTypeW.argtypes = [ctypes.c_wchar_p]
    k.GetDriveTypeW.restype = ctypes.c_uint32
    mask = k.GetLogicalDrives()
    for i in range(26):
        if not mask & (1 << i):
            continue
        root = chr(65+i) + ':\\'
        # Avoid network, optical, and unrecognized volumes.
        if k.GetDriveTypeW(root) not in (2, 3):
            continue
        label = ctypes.create_unicode_buffer(261)
        if k.GetVolumeInformationW(root, label, len(label), None, None, None, None, 0):
            if label.value.upper() == 'BATOCERA':
                yield Path(root)


def check_container(f, size):
    if f.seek(0, 2) != size:
        raise ValueError('Root filesystem size differs from catalogue.')
    f.seek(1024 + 56)
    if f.read(2) != b'\x53\xef':
        raise ValueError('Expected ext filesystem magic not found.')
    f.seek(0)


def detect_card(explicit, size):
    candidates = [Path(explicit)] if explicit else [p / 'boot' / 'BATOCERA' for p in windows_roots()] if os.name == 'nt' else []
    valid = []
    for p in candidates:
        try:
            with p.open('rb') as f:
                check_container(f, size)
            if not all((p.parent.parent / name).is_file() for name in ('uImage', 'KERNEL.DTB', 'RAMDISK.IMG', 'batocera-boot.conf')):
                raise ValueError('Expected boot files not found on same volume.')
            valid.append(p.resolve())
        except (OSError, ValueError) as e:
            say('Skipped card candidate', p, ':', e)
    if len(valid) != 1:
        raise RuntimeError(f'Expected one readable BATOCERA card, found {len(valid)}. '
                           'Insert only the test card; or supply --card E:/boot/BATOCERA (correct letter).')
    return valid[0]


def copy_stream(src, dest, size, label, expected=None):
    """Atomic local snapshot. Interrupted copies never become usable inputs."""
    check_container(src, size)
    if shutil.disk_usage(dest.parent).free < size + 128*MIB:
        raise RuntimeError(f'Not enough local free space for {label} snapshot. Need about 2.6 GB more.')
    tmp = dest.with_name(dest.name + '.partial')
    h = hashlib.sha256(); done = 0; last = -1
    with tmp.open('wb') as f:
        while done < size:
            data = src.read(min(CHUNK, size-done))
            if not data:
                raise IOError(f'Short read in {label}: {done} of {size} bytes.')
            f.write(data); h.update(data); done += len(data)
            pct = done * 100 // size
            if pct // 10 != last or done == size:
                last = pct // 10; say(f'{label} copy: {pct}% ({done//MIB:,}/{size//MIB:,} MiB)')
        if src.read(1):
            raise IOError('Source grew during copy.')
        f.flush(); os.fsync(f.fileno())
    digest = h.hexdigest()
    if expected and digest != expected:
        raise ValueError(f'{label} SHA-256 mismatch: {digest}; expected {expected}.')
    # Verify bytes actually written before publishing the snapshot.
    if sha_file(tmp) != digest:
        raise IOError(f'{label} local copy failed verification.')
    os.replace(tmp, dest)
    return digest


def stage_original(image, part, rootcat, cache, Window, PyFatBytesIOFS):
    dest = cache / 'original.ext4'
    expected = rootcat['container_sha256']; size = rootcat['container_size']
    if dest.is_file() and dest.stat().st_size == size and sha_file(dest) == expected:
        say('Verified original local copy reused.'); return dest, expected
    stamp = source_stamp(image)
    with image.open('rb') as raw, PyFatBytesIOFS(Window(raw, part['offset'], part['size'])) as fat:
        with fat.openbin(rootcat['container_path']) as src:
            digest = copy_stream(src, dest, size, 'Original', expected)
    if source_stamp(image) != stamp:
        raise RuntimeError('Original image changed during copy. Stop and verify the source.')
    return dest, digest


def stage_card(explicit, rootcat, cache, root):
    size = rootcat['container_size']; dest = cache / 'card.ext4'
    # Re-resolve immediately before access, since Windows can change drive letters.
    card = detect_card(explicit, size)
    if card.anchor == root.anchor and os.name == 'nt':
        raise RuntimeError('Project and card must be on different drives. No card writes allowed.')
    say('Card located:', card)
    stamp = source_stamp(card)
    if dest.is_file() and dest.stat().st_size == size:
        say('Checking current card against saved local copy (sequential read)...')
        current = sha_file(card)
        if source_stamp(card) != stamp:
            raise RuntimeError('Card changed during hash; reconnect it and rerun.')
        if current == sha_file(dest):
            say('Verified card local copy reused.'); return dest, current, str(card)
    with card.open('rb') as src:
        digest = copy_stream(src, dest, size, 'Card')
    if source_stamp(card) != stamp:
        raise RuntimeError('Card changed or moved during copy. Reconnect and rerun.')
    say('Card snapshot saved. The scan now reads the local copy, not the SD card.')
    return dest, digest, str(card)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def record(node, path, cached_hash):
    ino = node.inode; mode = int(ino.i_mode)
    rec = {'inode': int(node.inum), 'mode': mode, 'uid_low': int(ino.i_uid),
           'gid_low': int(ino.i_gid), 'links': int(ino.i_links_count), 'flags': int(ino.i_flags)}
    for field in ('i_uid_high', 'i_gid_high'):
        if hasattr(ino, field):
            rec[field] = int(getattr(ino, field))
    rec['xattrs'] = sorted([str(x.name), str(x.prefix), bytes(x.value).hex()] for x in node.xattr)
    if stat.S_ISREG(mode):
        digest = cached_hash(rec['inode'])
        if digest is None:
            h = hashlib.sha256(); n = 0
            with node.open() as f:
                while chunk := f.read(MIB):
                    h.update(chunk); n += len(chunk)
            if n != node.size:
                raise IOError(f'Short read at {path}: {n} != {node.size}')
            digest = h.hexdigest()
        rec.update(size=int(node.size), sha256=digest)
    elif stat.S_ISLNK(mode):
        rec['target'] = node.link
    elif stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
        rec['device_raw'] = [int(x) for x in ino.i_block[:2]]
    return rec


def snapshot(fs, label, dbpath, digest, estimate=None, interrupt_after=None):
    """Persist records in SQLite. Replay directory traversal on resume, skip completed hashes.
    No symlink resolution on replay: children are read using the original directory API.
    """
    con = sqlite3.connect(dbpath, timeout=2)
    try:
        con.execute('PRAGMA synchronous=FULL')
        con.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS entries (path TEXT PRIMARY KEY, rec TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS hashes (inode INTEGER PRIMARY KEY, sha TEXT NOT NULL)')
        meta = dict(con.execute('SELECT key,value FROM meta'))
        identity = {'schema': str(SCHEMA), 'source_sha256': digest}
        if meta and any(meta.get(k) != v for k,v in identity.items()):
            raise RuntimeError(f'Checkpoint identity mismatch: {dbpath}. Rename this local checkpoint and rerun.')
        if not meta:
            if con.execute('SELECT COUNT(*) FROM entries').fetchone()[0]:
                raise RuntimeError('Checkpoint has entries but no identity; refusing to reuse.')
            con.executemany('INSERT INTO meta VALUES (?,?)', identity.items()); con.commit()
        saved = {p: json.loads(r) for p,r in con.execute('SELECT path,rec FROM entries')}
        if meta.get('complete') == 'yes':
            if meta.get('count') != str(len(saved)):
                raise RuntimeError('Completed checkpoint count mismatch.')
            say(f'{label}: reusing {len(saved):,} completed paths.'); return saved
        say(f'{label}: {len(saved):,} paths recovered from checkpoint.' if saved else f'{label}: starting scan.')
        hashes = dict(con.execute('SELECT inode,sha FROM hashes'))
        stack = [('/', fs.get('/'))]; dirs = set(); visited = set()
        pending = 0; new = 0; last = time.monotonic(); last_print = last
        try:
            while stack:
                path, node = stack.pop()
                if path in visited:
                    raise ValueError(f'Duplicate path: {path}')
                visited.add(path)
                mode = int(node.inode.i_mode); ino = int(node.inum)
                if path in saved:
                    rec = saved[path]
                    if rec['inode'] != ino or rec['mode'] != mode:
                        raise ValueError(f'Checkpoint entry no longer matches at {path}')
                else:
                    rec = record(node, path, hashes.get)
                    # Normalize JSON representation (e.g. tuples) across fresh and resumed scans.
                    rec = json.loads(canonical(rec))
                    con.execute('INSERT INTO entries VALUES (?,?)', (path, canonical(rec)))
                    if 'sha256' in rec and ino not in hashes:
                        hashes[ino] = rec['sha256']
                        con.execute('INSERT INTO hashes VALUES (?,?)', (ino, rec['sha256']))
                    saved[path] = rec; pending += 1; new += 1
                if stat.S_ISDIR(mode):
                    if ino in dirs:
                        raise ValueError(f'Repeated directory inode at {path}')
                    dirs.add(ino)
                    for name, child in node.listdir().items():
                        if name not in ('.', '..'):
                            stack.append((path.rstrip('/') + '/' + name, child))
                now = time.monotonic()
                if pending and (pending >= 50 or now-last >= 5):
                    con.commit(); pending = 0; last = now
                if len(visited) % 1000 == 0 or now-last_print >= 20:
                    total = f' / ~{estimate:,}' if estimate else ''
                    say(f'{label}: {len(visited):,}{total} paths visited; {len(saved):,} hashed/recorded.')
                    last_print = now
                if interrupt_after is not None and new >= interrupt_after:
                    raise KeyboardInterrupt
            if visited != saved.keys():
                raise RuntimeError('Checkpoint contains paths not found in this snapshot.')
            con.execute("INSERT OR REPLACE INTO meta VALUES ('complete','yes'), ('count',?)", (str(len(saved)),)); con.commit()
        except BaseException:
            # A normal interruption or read error retains all fully recorded entries.
            # An abrupt power loss can lose only the last uncommitted batch.
            con.commit(); raise
        say(f'{label}: {len(saved):,} paths checked (complete).')
        return saved
    finally:
        con.close()


def compare(a,b):
    return {'removed': sorted(a.keys()-b.keys()), 'added': sorted(b.keys()-a.keys()),
            'changed': [{'path': k, 'fields': {f: [a[k].get(f), b[k].get(f)]
                         for f in sorted(a[k].keys() | b[k].keys()) if a[k].get(f) != b[k].get(f)}}
                        for k in sorted(a.keys() & b.keys()) if a[k] != b[k]]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('legacy_card', nargs='?', help=argparse.SUPPRESS)
    p.add_argument('--card', help='Explicit root filesystem file if auto-detection fails')
    p.add_argument('--normal-priority', action='store_true', help='Do not lower CPU priority')
    args = p.parse_args(); explicit = args.card or args.legacy_card
    root = Path(__file__).resolve().parents[1]
    image = root / 'inputs/koriki-v1.0.img'
    catfile = root / 'evidence/firmware/koriki-v1.0.json'
    rootfile = root / 'evidence/firmware/koriki-v1.0-rootfs.json'
    for path in (image, catfile, rootfile, root/'tools/firmware_catalogue.py'):
        if not path.is_file():
            raise RuntimeError(f'Missing {path}. Open PowerShell in ATM7039S-main first.')
    cat = json.loads(catfile.read_text(encoding='utf-8'))
    rootcat = json.loads(rootfile.read_text(encoding='utf-8'))
    part = next(x for x in cat['partitions'] if x['index'] == 1)
    if image.stat().st_size != cat['size'] or rootcat['image_sha256'] != cat['sha256']:
        raise RuntimeError('Original image size or catalogue identity mismatch.')
    card = detect_card(explicit, rootcat['container_size'])
    if os.name == 'nt' and root.anchor == card.anchor:
        raise RuntimeError('Project must be on a different drive from the card.')
    sys.path.insert(0, str(root/'tools'))
    from firmware_catalogue import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    from dissect.extfs import ExtFS
    if not args.normal_priority:
        low_priority()
    cache = root / '.v3-rootfs-review'
    cache.mkdir(exist_ok=True)
    if cache.is_symlink() or cache.resolve().parent != root:
        raise RuntimeError('Diagnostic cache is redirected outside the project.')
    say(f'Root filesystem diagnostic V{VERSION}. Read-only inputs. Local checkpoints: {cache}')
    if any(p.is_symlink() for p in cache.iterdir()):
        raise RuntimeError('Unexpected symbolic link in local diagnostic cache; refusing to write.')
    with session_lock(cache/'session.lock'):
        # Remove only our own incomplete copies; never delete source or completed checkpoint.
        for name in ('original.ext4.partial', 'card.ext4.partial'):
            (cache/name).unlink(missing_ok=True)
        orig, origsha = stage_original(image, part, rootcat, cache, Window, PyFatBytesIOFS)
        cardfile, cardsha, cardpath = stage_card(explicit, rootcat, cache, root)
        # Both inputs exist and have been copied/verified BEFORE scanning any trees.
        with orig.open('rb') as f:
            a = snapshot(ExtFS(f), 'Original', cache/f'original-{origsha}.sqlite', origsha, 27112)
        with cardfile.open('rb') as f:
            b = snapshot(ExtFS(f), 'Card', cache/f'card-{cardsha}.sqlite', cardsha, len(a))
        report = compare(a,b)
        report.update(added_records={k: b[k] for k in report['added']},
                      removed_records={k: a[k] for k in report['removed']},
                      original_paths=len(a), card_paths=len(b), scope=SCOPE,
                      diagnostic_version=VERSION, original_container_sha256=origsha,
                      card_container_sha256=cardsha,
                      note='Comparison is of local snapshots; not a V3 preflight override or authorization.')
        out = cache/'report.json'
        atomic_json(out, report)
        for k in ('added','removed','changed'):
            say(f'{k}: {len(report[k])}')
            for e in report[k][:20]:
                say(' ', e if isinstance(e,str) else (e['path'], list(e['fields'])))
        say('Private report saved:', out)
        say('Review report for sensitive paths, xattrs and identifiers before sharing.')
        say('Diagnostic complete. Do not proceed until the failed V3 preflight is resolved.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        say('\nStopped. Run the same command to resume from saved checkpoints.'); sys.exit(130)
    except Exception as e:
        say(f'\nERROR ({type(e).__name__}): {e}')
        say('No source changes requested. Completed local checkpoints are retained. Fix the issue and rerun.')
        sys.exit(1)
