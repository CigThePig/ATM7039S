#!/usr/bin/env python3
"""Fetch pinned public firmware; optionally expand it with exact byte limits.

gzip is expanded with Python's gzip module. ZIP/RAR/7z archives are expanded
only when the manifest names exactly one ``expanded_member``; that single member
is streamed by archive_members.py and must match ``expanded_size`` and
``expanded_sha256``. The size ceiling is ``max_bytes`` from the manifest entry
(default 8 GiB), so large manufacturer images can be admitted explicitly.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
from firmware_catalogue import safe_name, regular


DEFAULT_CEILING = 8*1024**3


def copy_checked(inp, output, size, digest, ceiling=DEFAULT_CEILING, progress=False):
    if not 0 < size <= ceiling: raise ValueError('acquisition exceeds size ceiling')
    h=hashlib.sha256();total=0;last=-1
    try:
        with output.open('xb') as out:
            while True:
                block=inp.read(min(1024*1024,size-total+1))
                if not block:break
                total+=len(block)
                if total>size:raise ValueError('expanded/downloaded size exceeds manifest')
                h.update(block);out.write(block)
                pct=total*100//size
                if progress and pct//5 != last:
                    last=pct//5; print(f'{output.name}: {pct}% ({total//1048576}/{size//1048576} MiB)', flush=True)
        if total!=size or h.hexdigest()!=digest:raise ValueError('acquisition hash/size mismatch')
    except FileExistsError:
        raise
    except BaseException:
        output.unlink(missing_ok=True)
        raise


def check(path,size,digest):
    regular(path)
    with path.open('rb') as f:
        if path.stat().st_size!=size or hashlib.file_digest(f,'sha256').hexdigest()!=digest:
            raise ValueError('existing acquisition hash/size mismatch')


def expand(item,dest,outdir):
    """Expand a verified acquisition according to its manifest entry; returns the output path."""
    expanded=outdir/safe_name(item['expanded_filename'])
    ceiling=item.get('max_bytes',DEFAULT_CEILING)
    if expanded.exists():check(expanded,item['expanded_size'],item['expanded_sha256'])
    elif item['compression']=='gzip':
        with gzip.open(dest,'rb') as f:
            copy_checked(f,expanded,item['expanded_size'],item['expanded_sha256'],ceiling,progress=True)
    elif item['compression'] in ('zip','rar4','rar5','7z') and item.get('expanded_member'):
        import archive_members
        r=archive_members.extract(dest,item['expanded_member'],outdir,ceiling,expanded.name)
        if r['size']!=item['expanded_size'] or r['sha256']!=item['expanded_sha256']:
            expanded.unlink(missing_ok=True)
            raise ValueError('expanded member hash/size mismatch')
    else:
        raise ValueError('no safe automatic expansion for this entry')
    return expanded


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('output',type=Path);p.add_argument('--expand',action='store_true')
    p.add_argument('--filename',help='select one entry when a source has several (manifest filename)')
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    items=[x for x in json.loads((root/'evidence/firmware/acquisitions.json').read_text(encoding='utf-8')) if x['source']==a.source and (a.filename is None or x['filename']==a.filename)]
    if not items:raise SystemExit('no manifest entry for that source/filename')
    if len(items)>1:raise SystemExit('source has several entries; pass --filename: '+', '.join(x['filename'] for x in items))
    item=items[0]
    a.output.mkdir(parents=True,exist_ok=True);dest=a.output/safe_name(item['filename'].replace('/','_'))
    if dest.exists():check(dest,item['size'],item['sha256'])
    else:
        with urllib.request.urlopen(item['url'],timeout=60) as response:
            copy_checked(response,dest,item['size'],item['sha256'],progress=True)
    if a.expand:
        expand(item,dest,a.output)
    print('Verified '+item['source'])
