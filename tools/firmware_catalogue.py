#!/usr/bin/env python3
"""Stream a regular disk image and inspect explicitly selected bounded components.

No mounts, block devices, firmware execution, recursive archive extraction, or
inference of physical memory addresses. Optional FAT reads use pyfatfs read-only.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import struct
import research as r

LIMIT = 32 * 1024 * 1024


class Window(io.RawIOBase):
    def __init__(self, base, start, length):
        self.base, self.start, self.length, self.pos = base, start, length, 0
    def readable(self): return True
    def writable(self): return False
    def write(self, data): raise io.UnsupportedOperation('read-only partition window')
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        new = off if whence == 0 else self.pos+off if whence == 1 else self.length+off if whence == 2 else -1
        if not 0 <= new <= self.length: raise ValueError('FAT seek outside partition')
        self.pos = new
        return new
    def read(self, n=-1):
        if n < 0: n = self.length-self.pos
        n = min(n, self.length-self.pos)
        self.base.seek(self.start+self.pos)
        data = self.base.read(n); self.pos += len(data)
        return data



def regular(path):
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('input must be an ordinary file')


def region(f, offset, size, total):
    if not isinstance(offset, int) or not isinstance(size, int) or offset < 0 or not 0 < size <= LIMIT:
        raise ValueError('invalid or oversized region')
    if offset + size > total:
        raise ValueError('region exceeds image')
    f.seek(offset)
    data = f.read(size)
    if len(data) != size:
        raise ValueError('short region read')
    return data


def mbr(data, total):
    if len(data) != 512 or data[510:] != b'\x55\xaa':
        raise ValueError('missing MBR signature')
    result = []
    for i in range(4):
        e = data[446+i*16:462+i*16]
        start, count = struct.unpack_from('<II', e, 8)
        if not e[4]:
            if start or count:
                raise ValueError('nonempty unused MBR entry')
            continue
        if e[4] in (0x05, 0x0f, 0x85, 0xee):
            raise ValueError('extended partitions/GPT require a separate parser')
        if e[0] not in (0, 0x80) or not start or not count or (start+count)*512 > total:
            raise ValueError('invalid MBR bounds or boot flag')
        item = dict(index=i+1, type=hex(e[4]), bootable=e[0] == 0x80,
                    start_lba=start, sectors=count, offset=start*512, size=count*512)
        if any(item['offset'] < x['offset']+x['size'] and x['offset'] < item['offset']+item['size'] for x in result):
            raise ValueError('overlapping MBR partitions')
        result.append(item)
    return result


def safe_name(name):
    if not isinstance(name, str) or not name or name in ('.', '..') or '/' in name or '\\' in name:
        raise ValueError('component ID must be a filename without directories')
    return name


def catalogue(image, plan, output_dir=None):
    regular(image)
    total = image.stat().st_size
    with image.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
        if plan.get('image_sha256') != digest:
            raise ValueError('image SHA-256 does not match acquisition plan')
        f.seek(0)
        parts = mbr(f.read(512), total)
        result = dict(format_version=1, source=plan['source'], release=plan['release'],
                      size=total, sha256=digest, sector_size=512, partitions=parts, components=[])
        selected = plan.get('raw_regions', []) + plan.get('fat_files', [])
        names = [safe_name(x['id']) for x in selected]
        if len(set(names)) != len(names):
            raise ValueError('duplicate component ID')
        def add(spec, data, location):
            entry = dict(id=spec['id'], location=location, **r.firmware(data))
            result['components'].append(entry)
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                dest = output_dir / spec['id']
                # Refuse symlinks and accidental replacement of previous research inputs.
                with dest.open('xb') as out:
                    out.write(data)
        for spec in plan.get('raw_regions', []):
            size = spec.get('size')
            if spec.get('format') == 'uImage':
                h = region(f, spec['offset'], 64, total)
                if h[:4] != b'\x27\x05\x19\x56':
                    raise ValueError('missing expected uImage header')
                size = 64 + struct.unpack_from('>I', h, 12)[0]
            data = region(f, spec['offset'], size, total)
            add(spec, data, dict(kind='disk-region', offset=spec['offset'], size=size,
                                boundary=spec.get('boundary', 'format-declared')))
        if plan.get('fat_files'):
            index = plan['fat_partition']
            part = next((x for x in parts if x['index'] == index), None)
            if part is None or int(part['type'], 16) not in (0x01, 0x04, 0x06, 0x0b, 0x0c, 0x0e):
                raise ValueError('selected partition is not declared FAT')
            # Bound pyfatfs to the partition, preventing malformed FAT pointers
            # from reaching other image regions. Copying a partition is unnecessary.
            from pyfatfs.PyFatFS import PyFatBytesIOFS
            with PyFatBytesIOFS(Window(f, part['offset'], part['size'])) as fs:
                for spec in plan['fat_files']:
                    path = PurePosixPath(spec['path'])
                    if not path.is_absolute() or '..' in path.parts:
                        raise ValueError('unsafe FAT path')
                    info = fs.getinfo(str(path), namespaces=['details'])
                    if not info.is_file or not 0 < info.size <= LIMIT:
                        raise ValueError('invalid or oversized FAT file')
                    with fs.openbin(str(path)) as inp:
                        data = inp.read(LIMIT+1)
                    if len(data) != info.size:
                        raise ValueError('FAT file length mismatch')
                    add(spec, data, dict(kind='fat-file', partition=index, path=str(path)))
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path); p.add_argument('plan', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--extract', type=Path, help='new component files only, never execute')
    a = p.parse_args()
    data = catalogue(a.image, json.loads(a.plan.read_text()), a.extract)
    a.output.write_text(json.dumps(data, indent=2)+'\n')


if __name__ == '__main__':
    main()
