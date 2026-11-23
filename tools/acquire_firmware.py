#!/usr/bin/env python3
"""Fetch pinned public firmware, optionally expand gzip with exact byte limits."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request
from firmware_catalogue import safe_name, regular


def copy_checked(inp, output, size, digest):
    if not 0 < size <= 8*1024**3: raise ValueError('acquisition exceeds 8 GiB ceiling')
    h=hashlib.sha256();total=0
    try:
        with output.open('xb') as out:
            while True:
                block=inp.read(min(1024*1024,size-total+1))
                if not block:break
                total+=len(block)
                if total>size:raise ValueError('expanded/downloaded size exceeds manifest')
                h.update(block);out.write(block)
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


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source');p.add_argument('output',type=Path);p.add_argument('--expand',action='store_true')
    a=p.parse_args();root=Path(__file__).resolve().parents[1]
    item=next(x for x in json.loads((root/'evidence/firmware/acquisitions.json').read_text()) if x['source']==a.source)
    a.output.mkdir(parents=True,exist_ok=True);dest=a.output/safe_name(item['filename'])
    if dest.exists():check(dest,item['size'],item['sha256'])
    else:
        with urllib.request.urlopen(item['url'],timeout=60) as response:
            copy_checked(response,dest,item['size'],item['sha256'])
    if a.expand:
        if item['compression']!='gzip':raise ValueError('automatic expansion supports gzip only')
        expanded=a.output/safe_name(item['expanded_filename'])
        if expanded.exists():check(expanded,item['expanded_size'],item['expanded_sha256'])
        else:
            with gzip.open(dest,'rb') as f:
                copy_checked(f,expanded,item['expanded_size'],item['expanded_sha256'])
    print('Verified '+item['source'])
