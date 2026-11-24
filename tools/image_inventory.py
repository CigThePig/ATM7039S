#!/usr/bin/env python3
"""Read-only whole-disk-image inventory: partitions, raw regions and filesystem trees.

Handles a primary MBR or a GPT behind a protective MBR (header and entry-array
CRCs, backup header, bounds and overlap are checked). Bytes outside partitions
are reported as hashed non-zero *raw regions* with recognised signatures. FAT
and ext2/3/4 partitions are walked with bounded user-space parsers (pyfatfs via
a partition window; dissect.extfs) and every regular file is hashed by
streaming. Nothing is mounted, executed or written except explicitly selected
extraction outputs.

``--summary-only NAME`` records only filesystem identity and aggregate counts
for a partition (used for the bundled game-ROM partition, which is out of
scope). ``--extract PATHLIST DIR`` copies the listed ``PARTITION:/path`` files
(one per line) into DIR, refusing existing names.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import uuid
import zlib

from firmware_catalogue import Window, regular

SECTOR = 512
EXTRACT_LIMIT = 256 * 1024 * 1024
FAT_TYPES = {0x01, 0x04, 0x06, 0x0b, 0x0c, 0x0e}
BASIC_DATA = 'ebd0a0a2-b9e5-4433-87c0-68b6b72699c7'
LINUX_DATA = '0fc63daf-8483-4772-8e79-3d69d8477de4'
SIGNATURES = [(b'\x27\x05\x19\x56', 'uImage'), (b'\xd0\x0d\xfe\xed', 'fdt'), (b'\x7fELF', 'elf'),
              (b'ActBrm', 'actions-brom-tag'), (b'\x1f\x8b\x08', 'gzip'), (b'ANDROID!', 'android-boot')]


def _overlap(items):
    s = sorted(items, key=lambda x: x['offset'])
    for a, b in zip(s, s[1:]):
        if a['offset'] + a['size'] > b['offset']:
            raise ValueError('overlapping partitions')


def parse_mbr(sector, total):
    if len(sector) != SECTOR or sector[510:] != b'\x55\xaa':
        raise ValueError('missing MBR signature')
    parts = []
    for i in range(4):
        e = sector[446 + 16 * i:462 + 16 * i]
        start, count = struct.unpack_from('<II', e, 8)
        if not e[4]:
            continue
        parts.append(dict(index=i + 1, type=e[4], boot=e[0], start=start, count=count))
    return parts


def parse_gpt(f, total, allow_truncated=False):
    f.seek(SECTOR)
    h = f.read(SECTOR)
    if h[:8] != b'EFI PART':
        raise ValueError('protective MBR without GPT header')
    rev, hsize, hcrc, _, cur, backup, first, last = struct.unpack_from('<IIIIQQQQ', h, 8)
    if not 92 <= hsize <= SECTOR:
        raise ValueError('invalid GPT header size')
    hh = bytearray(h[:hsize]); hh[16:20] = b'\0' * 4
    if zlib.crc32(hh) != hcrc:
        raise ValueError('GPT header CRC mismatch')
    disk_guid = str(uuid.UUID(bytes_le=h[56:72]))
    ent_lba, count, esize, ecrc = struct.unpack_from('<QIII', h, 72)
    sectors = total // SECTOR
    truncated = backup >= sectors or last >= sectors
    if truncated and not allow_truncated:
        raise ValueError('invalid GPT geometry (image shorter than declared disk; see --allow-truncated)')
    if cur != 1 or not first <= last or (not truncated and last >= sectors) or esize < 128 or esize % 8 or count > 4096:
        raise ValueError('invalid GPT geometry')
    if (ent_lba + (count * esize + SECTOR - 1) // SECTOR) * SECTOR > total:
        raise ValueError('GPT entry array exceeds image')
    f.seek(ent_lba * SECTOR)
    entries = f.read(count * esize)
    if zlib.crc32(entries) != ecrc:
        raise ValueError('GPT entry array CRC mismatch')
    backup_ok = None
    if backup < sectors:
        f.seek(backup * SECTOR)
        b = f.read(SECTOR)
        if b[:8] == b'EFI PART':
            bb = bytearray(b[:hsize]); bcrc = struct.unpack_from('<I', b, 16)[0]; bb[16:20] = b'\0' * 4
            backup_ok = zlib.crc32(bb) == bcrc and struct.unpack_from('<Q', b, 24)[0] == backup
        else:
            backup_ok = False
    parts, beyond = [], []
    for i in range(count):
        e = entries[i * esize:(i + 1) * esize]
        if not any(e[:16]):
            continue
        s, l, attr = struct.unpack_from('<QQQ', e, 32)
        if not first <= s <= l <= last:
            raise ValueError(f'GPT entry {i + 1} outside usable LBAs')
        name = e[56:128].decode('utf-16le', errors='replace').split('\0')[0]
        if (l + 1) * SECTOR > total:
            item = dict(index=i + 1, name=name, start_lba=s, sectors=l - s + 1)
            if s * SECTOR < total:
                # Its in-image bytes still belong to the partition, not to unpartitioned space.
                item['in_image_bytes'] = total - s * SECTOR
            beyond.append(item)
            continue
        parts.append(dict(index=i + 1, name=name, type_guid=str(uuid.UUID(bytes_le=e[:16])),
                          unique_guid=str(uuid.UUID(bytes_le=e[16:32])), start_lba=s, sectors=l - s + 1,
                          offset=s * SECTOR, size=(l - s + 1) * SECTOR, attributes=attr))
    _overlap(parts)
    return dict(scheme='gpt', revision=hex(rev), disk_guid=disk_guid, first_usable_lba=first,
                last_usable_lba=last, entry_array_lba=ent_lba, backup_lba=backup,
                backup_header_valid=backup_ok, truncated_image=truncated,
                partitions_beyond_image=beyond, partitions=parts)


def partition_table(f, total, allow_truncated=False):
    f.seek(0)
    mbr = parse_mbr(f.read(SECTOR), total)
    if any(p['type'] == 0xee for p in mbr):
        if len(mbr) != 1 or mbr[0]['start'] != 1:
            raise ValueError('hybrid or malformed protective MBR')
        return parse_gpt(f, total, allow_truncated)
    parts = []
    for p in mbr:
        if p['type'] in (0x05, 0x0f, 0x85):
            raise ValueError('extended MBR partitions are not supported')
        if p['boot'] not in (0, 0x80) or not p['start'] or not p['count'] or (p['start'] + p['count']) * SECTOR > total:
            raise ValueError('invalid MBR entry')
        parts.append(dict(index=p['index'], mbr_type=hex(p['type']), bootable=p['boot'] == 0x80,
                          start_lba=p['start'], sectors=p['count'], offset=p['start'] * SECTOR,
                          size=p['count'] * SECTOR))
    _overlap(parts)
    return dict(scheme='mbr', partitions=parts)


def signatures(data, base):
    found = []
    for magic, kind in SIGNATURES:
        pos = data.find(magic)
        while pos >= 0 and len(found) < 512:
            found.append(dict(offset=base + pos, kind=kind))
            pos = data.find(magic, pos + 1)
    return sorted(found, key=lambda x: (x['offset'], x['kind']))


def raw_regions(f, total, parts, gap=64 * 1024, limit=64 * 1024 * 1024):
    """Non-zero sector runs outside partitions (and outside the partition table itself)."""
    reserved = [(0, SECTOR)] + [(p['offset'], p['offset'] + p['size']) for p in parts]
    reserved.sort()
    holes, pos = [], 0
    for a, b in reserved:
        if a > pos:
            holes.append((pos, a))
        pos = max(pos, b)
    if pos < total:
        holes.append((pos, total))
    regions = []
    for a, b in holes:
        if b - a > limit:
            # Large unpartitioned tails are only checked for being all-zero, block by block.
            nz = 0
            f.seek(a)
            left = b - a
            while left:
                blk = f.read(min(left, 1 << 20)); left -= len(blk)
                nz += len(blk) - blk.count(0)
            regions.append(dict(offset=a, size=b - a, kind='large-gap', nonzero_bytes=nz))
            continue
        f.seek(a)
        data = f.read(b - a)
        runs, cur, last = [], None, None
        for o in range(0, len(data), SECTOR):
            if any(data[o:o + SECTOR]):
                if cur is None or o - last > gap:
                    if cur is not None:
                        runs.append((cur, last))
                    cur = o
                last = o + SECTOR
        if cur is not None:
            runs.append((cur, last))
        for s, e in runs:
            chunk = data[s:e]
            regions.append(dict(offset=a + s, size=e - s, sha256=hashlib.sha256(chunk).hexdigest(),
                                signatures=signatures(chunk, a + s)))
    return regions


def classify(head):
    if head.startswith(b'\x7fELF') and len(head) >= 20:
        endian = '<' if head[5] == 1 else '>'
        return dict(format='elf', elf_class=head[4], machine=struct.unpack_from(endian + 'H', head, 18)[0],
                    elf_type=struct.unpack_from(endian + 'H', head, 16)[0])
    for magic, kind in [(b'\x27\x05\x19\x56', 'uImage'), (b'\xd0\x0d\xfe\xed', 'fdt'), (b'\x1f\x8b', 'gzip'),
                        (b'#!', 'script'), (b'PK\x03\x04', 'zip'), (b'\x89PNG', 'png'), (b'ANDROID!', 'android-boot'),
                        (b'070701', 'cpio-newc'), (b'hsqs', 'squashfs')]:
        if head.startswith(magic):
            return dict(format=kind)
    return {}


def _hash_stream(stream, want_head=64):
    h = hashlib.sha256(); size = 0; head = b''
    while True:
        b = stream.read(1 << 20)
        if not b:
            break
        if len(head) < want_head:
            head += b[:want_head - len(head)]
        h.update(b); size += len(b)
    return size, h.hexdigest(), head


def walk_fat(f, part, keep):
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    files = []
    agg = dict(file_count=0, directories=0, bytes=0)
    with PyFatBytesIOFS(Window(f, part['offset'], part['size'])) as fs:
        label = None
        try:
            label = fs.fs.get_volume_label() if hasattr(fs.fs, 'get_volume_label') else None
        except Exception:
            label = None
        for path, info in sorted(_fat_iter(fs, '/'), key=lambda x: x[0]):
            if info.is_dir:
                agg['directories'] += 1
                if keep(path):
                    files.append(dict(path=path, type='directory'))
                continue
            agg['file_count'] += 1; agg['bytes'] += info.size
            if not keep(path):
                continue
            with fs.openbin(path) as s:
                size, digest, head = _hash_stream(s)
            if size != info.size:
                raise ValueError('FAT length mismatch for ' + path)
            files.append(dict(path=path, type='file', size=size, sha256=digest, **classify(head)))
    return dict(filesystem='fat', label=label, **agg), files


def _fat_iter(fs, root):
    for info in fs.scandir(root, namespaces=['details']):
        p = str(PurePosixPath(root) / info.name)
        yield p, info
        if info.is_dir:
            yield from _fat_iter(fs, p)


def walk_ext(f, part, keep):
    from dissect.extfs import ExtFS
    win = Window(f, part['offset'], part['size'])
    ext = ExtFS(win)
    files = []
    agg = dict(file_count=0, directories=0, symlinks=0, other=0, bytes=0)
    stack = [('/', ext.root)]
    seen = set()
    while stack:
        path, node = stack.pop()
        if node.inum in seen and node.filetype == stat.S_IFDIR:
            continue
        seen.add(node.inum)
        for name, child in sorted(node.listdir().items()):
            if name in ('.', '..'):
                continue
            if '/' in name or '\0' in name:
                raise ValueError('unsafe ext directory entry')
            p = str(PurePosixPath(path) / name)
            ft = child.filetype
            mode = child.inode.i_mode & 0o7777
            rec = dict(path=p, inode=child.inum, mode=f'{mode:04o}', uid=child.inode.i_uid, gid=child.inode.i_gid)
            if ft == stat.S_IFDIR:
                agg['directories'] += 1
                stack.append((p, child))
                rec['type'] = 'directory'
            elif ft == stat.S_IFREG:
                agg['file_count'] += 1; agg['bytes'] += child.size
                if keep(p):
                    with child.open() as s:
                        size, digest, head = _hash_stream(s)
                    if size != child.size:
                        raise ValueError('ext length mismatch for ' + p)
                    rec.update(type='file', size=size, sha256=digest, **classify(head))
            elif ft == stat.S_IFLNK:
                agg['symlinks'] += 1
                rec.update(type='symlink', target=child.link)
            else:
                agg['other'] += 1
                rec.update(type='special', filetype=oct(ft))
            if keep(p):
                files.append(rec)
    files.sort(key=lambda x: x['path'])
    sb = ext.sb
    info = dict(filesystem='ext' + str(ext.type), volume_name=ext.volume_name, block_size=ext.block_size,
                uuid=str(ext.uuid) if getattr(ext, 'uuid', None) else None,
                last_mounted=getattr(ext, 'last_mount', None), **agg)
    try:
        info['created'] = int(sb.s_mkfs_time); info['last_write'] = int(sb.s_wtime)
    except Exception:
        pass
    return {k: v for k, v in info.items() if v is not None}, files


def detect_fs(f, part):
    f.seek(part['offset'])
    b = f.read(4096)
    if b[510:512] == b'\x55\xaa' and (b[0x36:0x39] == b'FAT' or b[0x52:0x57] == b'FAT32'):
        return 'fat', b[3:11].decode('ascii', 'replace')
    if len(b) > 0x43a and struct.unpack_from('<H', b, 0x438)[0] == 0xef53:
        return 'ext', None
    if b[:4] == b'hsqs':
        return 'squashfs', None
    return None, None


def _keeper(label, index, summary_only, include):
    """Return a path predicate: everything, nothing, or only listed prefixes."""
    prefixes = [x.split(':', 1)[1] for x in include if x.split(':', 1)[0] in (label, str(index))]
    if prefixes:
        return lambda p: any(p == x or p.startswith(x.rstrip('/') + '/') for x in prefixes), 'selected prefixes hashed: ' + ', '.join(prefixes)
    if label in summary_only or str(index) in summary_only:
        return lambda p: False, 'summary-only (out of scope)'
    return lambda p: True, 'files hashed'


def inventory(image, summary_only=(), expected_sha256=None, include=(), allow_truncated=False):
    regular(image)
    total = image.stat().st_size
    if total % SECTOR:
        raise ValueError('image length is not a multiple of 512')
    with image.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
        if expected_sha256 and digest != expected_sha256:
            raise ValueError('image SHA-256 does not match expected value')
        table = partition_table(f, total, allow_truncated)
        parts = table['partitions']
        result = dict(format_version=1, tool='image_inventory.py', size=total, sha256=digest, sector_size=SECTOR,
                      partition_table=table, partitions=[])
        reserved = parts + [dict(offset=b['start_lba'] * SECTOR, size=b['in_image_bytes'])
                            for b in table.get('partitions_beyond_image', []) if b.get('in_image_bytes')]
        result['raw_regions'] = raw_regions(f, total, reserved)
        for p in parts:
            label = p.get('name') or str(p['index'])
            kind, oem = detect_fs(f, p)
            entry = dict(index=p['index'], name=p.get('name'), offset=p['offset'], size=p['size'])
            keep, note = _keeper(label, p['index'], summary_only, include)
            if kind == 'fat':
                info, files = walk_fat(f, p, keep)
                info['oem_name'] = oem.strip()
            elif kind == 'ext':
                info, files = walk_ext(f, p, keep)
            else:
                f.seek(p['offset'])
                info, files = dict(filesystem=kind or 'unknown', first_sector_sha256=hashlib.sha256(f.read(SECTOR)).hexdigest()), []
            entry.update(info)
            entry['contents'] = note
            entry['files'] = files
            result['partitions'].append(entry)
    return result


def extract(image, inv, pathlist, outdir):
    """Copy selected PARTITION:/path regular files (bounded) into outdir."""
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    from dissect.extfs import ExtFS
    outdir.mkdir(parents=True, exist_ok=True)
    wanted = [l.strip() for l in pathlist.read_text().splitlines() if l.strip() and not l.startswith('#')]
    done = []
    with image.open('rb') as f:
        for item in wanted:
            label, _, path = item.partition(':')
            pp = PurePosixPath(path)
            if not pp.is_absolute() or '..' in pp.parts:
                raise ValueError('unsafe extraction path ' + item)
            part = next(p for p in inv['partitions'] if p['name'] == label or str(p['index']) == label)
            rec = next((x for x in part['files'] if x['path'] == path and x.get('type') == 'file'), None)
            if rec is None or rec['size'] > EXTRACT_LIMIT:
                raise ValueError('not an inventoried bounded regular file: ' + item)
            name = re.sub(r'[^A-Za-z0-9._-]', '_', f"{part['name'] or part['index']}{path}".replace('/', '__'))
            dest = outdir / name
            if part['filesystem'] == 'fat':
                with PyFatBytesIOFS(Window(f, part['offset'], part['size'])) as fs, fs.openbin(path) as s:
                    data = s.read(EXTRACT_LIMIT + 1)
            else:
                ext = ExtFS(Window(f, part['offset'], part['size']))
                with ext.get(path).open() as s:
                    data = s.read(EXTRACT_LIMIT + 1)
            if hashlib.sha256(data).hexdigest() != rec['sha256']:
                raise ValueError('extracted bytes do not match inventory hash: ' + item)
            with dest.open('xb') as out:
                out.write(data)
            done.append(dict(item=item, output=name, sha256=rec['sha256']))
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('image', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--summary-only', action='append', default=[], help='partition name/index to summarise only')
    p.add_argument('--include', action='append', default=[], help='PARTITION:/prefix to hash within a partition (others counted only)')
    p.add_argument('--sha256', help='expected image SHA-256')
    p.add_argument('--allow-truncated', action='store_true',
                   help='accept a GPT whose declared disk is longer than the image; partitions past the end are listed, not read')
    p.add_argument('--extract', nargs=2, metavar=('PATHLIST', 'DIR'), type=Path)
    a = p.parse_args()
    inv = inventory(a.image, a.summary_only, a.sha256, a.include, a.allow_truncated)
    a.output.write_text(json.dumps(inv, indent=1, sort_keys=False) + '\n')
    if a.extract:
        print(json.dumps(extract(a.image, inv, *a.extract), indent=1))


if __name__ == '__main__':
    main()
