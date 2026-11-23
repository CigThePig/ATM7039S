#!/usr/bin/env python3
"""Inspect selected files in a hash-identified ext4 image nested in FAT; no mounts."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from firmware_catalogue import catalogue, Window, LIMIT, safe_name
import research as r


def elf_metadata(data):
    from elftools.elf.elffile import ELFFile
    elf = ELFFile(io.BytesIO(data))
    result = dict(machine=elf['e_machine'], elf_class=elf.elfclass, little_endian=elf.little_endian,
                  type=elf['e_type'])
    mod = elf.get_section_by_name('.modinfo')
    if mod:
        result['modinfo'] = [x.decode('utf-8', errors='replace') for x in mod.data().split(b'\0') if x]
    dynamic = elf.get_section_by_name('.dynamic')
    if dynamic:
        result['needed'] = [t.needed for t in dynamic.iter_tags('DT_NEEDED')]
    return result


def inspect(image, plan, output_dir=None):
    # The common reader verifies SHA-256, MBR and image bounds first.
    disk = catalogue(image, dict(plan, raw_regions=[], fat_files=[]))
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    from dissect.extfs import ExtFS
    part = next(x for x in disk['partitions'] if x['index'] == plan['fat_partition'])
    if int(part['type'],16) not in (1,4,6,11,12,14):
        raise ValueError('not a FAT partition')
    result = dict(format_version=1, source=plan['source'], image_sha256=disk['sha256'],
                  container_path=plan['rootfs_path'], components=[])
    with image.open('rb') as raw, PyFatBytesIOFS(Window(raw,part['offset'],part['size'])) as fs:
        with fs.openbin(plan['rootfs_path']) as root:
            result['container_size'] = fs.getsize(plan['rootfs_path'])
            result['container_sha256'] = hashlib.file_digest(root, 'sha256').hexdigest()
            root.seek(0)
            ext = ExtFS(root)
            result.update(filesystem='ext'+str(ext.type), block_size=ext.block_size,
                          volume_name=ext.volume_name)
            names = [safe_name(s['id']) for s in plan['rootfs_files']]
            if len(names) != len(set(names)): raise ValueError('duplicate output name')
            for spec in plan['rootfs_files']:
                path = PurePosixPath(spec['path'])
                if not path.is_absolute() or '..' in path.parts: raise ValueError('unsafe path')
                node = ext.get(str(path))
                if node.filetype != 0x8000 or not 0 < node.size <= LIMIT:
                    raise ValueError('selected inode must be bounded regular file')
                with node.open() as f:
                    data = f.read(LIMIT+1)
                if len(data) != node.size: raise ValueError('inode length mismatch')
                entry = dict(id=spec['id'], path=str(path), inode=node.inum, size=len(data), sha256=r.sha(data))
                if data.startswith(b'\x7fELF'): entry['elf'] = elf_metadata(data)
                result['components'].append(entry)
                if output_dir:
                    output_dir.mkdir(parents=True,exist_ok=True)
                    with (output_dir/spec['id']).open('xb') as out: out.write(data)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--extract',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(inspect(a.image,json.loads(a.plan.read_text()),a.extract),indent=2)+'\n')
