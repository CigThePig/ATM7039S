#!/usr/bin/env python3
"""List and extract selected members of firmware distribution archives safely.

ZIP is read with Python's zipfile. RAR/7z use an external, read-only listing
and single-member stream (``7z`` preferred, ``lsar``/``unar`` fallback). Nothing
inside an archive is executed and nothing is extracted implicitly: every output
is a single named member streamed to a new file under the output directory,
with a byte ceiling and streaming SHA-256.

Rejected outright: absolute names, ``..`` components, backslashes or drive
prefixes, NUL bytes, duplicate names, symlinks/devices and declared sizes above
the ceiling.  A member whose streamed length differs from its declared length,
or that exceeds the ceiling, is deleted and reported as an error.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile

DEFAULT_LIMIT = 16 * 1024**3
CHUNK = 1024 * 1024


def check_name(name):
    if not isinstance(name, str) or not name or '\0' in name or '\\' in name:
        raise ValueError(f'unsafe archive member name: {name!r}')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or (len(name) > 1 and name[1] == ':'):
        raise ValueError(f'unsafe archive member name: {name!r}')
    return str(p)


def detect(path):
    with path.open('rb') as f:
        head = f.read(8)
    if head.startswith(b'PK\x03\x04') or head.startswith(b'PK\x05\x06'):
        return 'zip'
    if head.startswith(b'Rar!\x1a\x07\x01\x00'):
        return 'rar5'
    if head.startswith(b'Rar!\x1a\x07\x00'):
        return 'rar4'
    if head.startswith(b"7z\xbc\xaf'\x1c"):
        return '7z'
    raise ValueError('unsupported or unrecognised archive container')


def _7z():
    for exe in ('7z', '7zz', '7za'):
        if shutil.which(exe):
            return exe
    return None


def list_members(path):
    kind = detect(path)
    members = []
    if kind == 'zip':
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                mode = (i.external_attr >> 16) & 0o170000
                members.append(dict(name=i.filename.rstrip('/'), size=i.file_size, packed=i.compress_size,
                                    directory=i.is_dir(), special=mode not in (0, 0o100000, 0o040000),
                                    crc32=f'{i.CRC:08x}', method=i.compress_type))
    else:
        exe = _7z()
        if exe:
            out = subprocess.run([exe, 'l', '-slt', '-ba', '--', str(path)], capture_output=True, text=True,
                                 timeout=600, check=True).stdout
            rec = {}
            for line in out.splitlines() + ['']:
                if not line.strip():
                    if 'Path' in rec:
                        attrs = rec.get('Attributes', '')
                        members.append(dict(name=rec['Path'], size=int(rec.get('Size') or 0),
                                            packed=int(rec.get('Packed Size') or 0),
                                            directory=rec.get('Folder') == '+' or attrs.startswith('D'),
                                            special=' l' in attrs.lower() or 'lnk' in attrs.lower(),
                                            crc32=(rec.get('CRC') or '').lower() or None,
                                            method=rec.get('Method'), modified=rec.get('Modified')))
                    rec = {}
                elif ' = ' in line:
                    k, v = line.split(' = ', 1)
                    rec[k.strip()] = v.strip()
        elif shutil.which('lsar'):
            data = json.loads(subprocess.run(['lsar', '-j', str(path)], capture_output=True, text=True,
                                             timeout=600, check=True).stdout)
            for e in data['lsarContents']:
                members.append(dict(name=e['XADFileName'], size=int(e.get('XADFileSize', 0)),
                                    packed=int(e.get('XADCompressedSize', 0)),
                                    directory=bool(e.get('XADIsDirectory')), special=bool(e.get('XADIsLink')),
                                    crc32=None, method=e.get('XADCompressionName')))
        else:
            raise RuntimeError('no RAR/7z lister available (install 7zip or unar)')
    seen = set()
    for m in members:
        m['name'] = check_name(m['name'])
        if m['name'] in seen:
            raise ValueError('duplicate archive member ' + m['name'])
        seen.add(m['name'])
    return dict(container=kind, members=sorted(members, key=lambda m: m['name']))


def _stream_commands(kind, path, name):
    """Candidate single-member stdout extractors, in preference order. Distribution
    7-Zip builds often omit the non-free RAR codec, and libarchive's RAR4 decoder
    rejects some valid archives, so RAR tries bsdtar, then unar, then 7z."""
    order = ['bsdtar', 'unar', '7z'] if kind.startswith('rar') else ['7z', 'bsdtar']
    cmds = []
    for tool in order:
        if tool == '7z' and _7z():
            cmds.append([_7z(), 'x', '-so', '--', str(path), name])
        elif tool == 'bsdtar' and shutil.which('bsdtar'):
            cmds.append(['bsdtar', '-x', '-O', '-f', str(path), '--', name])
        elif tool == 'unar' and shutil.which('unar'):
            cmds.append(['unar', '-q', '-o', '-', str(path), name])
    if not cmds:
        raise RuntimeError('no extractor for ' + kind)
    return cmds


def _copy(stream, dest, limit, declared):
    h = hashlib.sha256()
    total = 0
    try:
        with dest.open('xb') as out:
            while True:
                block = stream.read(CHUNK)
                if not block:
                    break
                total += len(block)
                if total > limit:
                    raise ValueError('member exceeds extraction ceiling')
                h.update(block)
                out.write(block)
        if declared is not None and total != declared:
            raise ValueError(f'member length {total} differs from declared {declared}')
    except FileExistsError:
        raise
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return dict(size=total, sha256=h.hexdigest())


def extract(path, member, outdir, limit=DEFAULT_LIMIT, out_name=None):
    listing = list_members(path)
    entry = next((m for m in listing['members'] if m['name'] == check_name(member)), None)
    if entry is None:
        raise KeyError('member not in archive: ' + member)
    if entry['directory'] or entry['special']:
        raise ValueError('only regular file members can be extracted')
    if entry['size'] > limit:
        raise ValueError('declared member size exceeds ceiling')
    name = out_name or PurePosixPath(entry['name']).name
    if '/' in name or name in ('', '.', '..'):
        raise ValueError('output name must be a plain filename')
    outdir.mkdir(parents=True, exist_ok=True)
    dest = outdir / name
    if listing['container'] == 'zip':
        with zipfile.ZipFile(path) as z, z.open(entry['name']) as s:
            result = _copy(s, dest, limit, entry['size'])
    else:
        errors = []
        for cmd in _stream_commands(listing['container'], path, entry['name']):
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                result = _copy(proc.stdout, dest, limit, entry['size'])
                failed = None
            except (ValueError, OSError) as e:
                failed = str(e)
            finally:
                proc.stdout.close()
                err = proc.stderr.read().decode(errors='replace')
                code = proc.wait(timeout=600)
            if failed is None and code == 0:
                result['extractor'] = cmd[0]
                break
            dest.unlink(missing_ok=True)
            errors.append(f'{cmd[0]}: {failed or err[-300:]}')
        else:
            raise RuntimeError('all extractors failed: ' + ' | '.join(errors))
        if entry.get('crc32') and listing['container'] != 'zip':
            result['declared_crc32'] = entry['crc32']
    return dict(member=entry['name'], output=name, **result)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    l = sub.add_parser('list'); l.add_argument('archive', type=Path); l.add_argument('output', type=Path)
    x = sub.add_parser('extract'); x.add_argument('archive', type=Path); x.add_argument('member')
    x.add_argument('outdir', type=Path); x.add_argument('--limit', type=int, default=DEFAULT_LIMIT)
    x.add_argument('--name')
    a = p.parse_args()
    if not a.archive.is_file():
        raise ValueError('archive must be a regular file')
    if a.cmd == 'list':
        result = list_members(a.archive)
        with a.archive.open('rb') as f:
            result = dict(archive_size=a.archive.stat().st_size,
                          archive_sha256=hashlib.file_digest(f, 'sha256').hexdigest(), **result)
        a.output.write_text(json.dumps(result, indent=1) + '\n')
    else:
        print(json.dumps(extract(a.archive, a.member, a.outdir, a.limit, a.name), indent=1))


if __name__ == '__main__':
    main()
