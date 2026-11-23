#!/usr/bin/env python3
"""Bounded gzip stream identification inside boot components; no extraction/execution."""
import argparse
import json
from pathlib import Path
import re
import zlib
import research as r


def inspect(data, max_expanded=64*1024*1024):
    if len(data)>32*1024*1024:raise ValueError('component exceeds 32 MiB')
    streams=[]
    matches=list(re.finditer(b'\x1f\x8b\x08',data))
    if len(matches)>256:raise ValueError('too many compression candidates')
    for m in matches:
        try:
            obj=zlib.decompressobj(31)
            payload=obj.decompress(data[m.start():],max_expanded+1)
            if len(payload)>max_expanded:raise ValueError('decompression exceeds 64 MiB')
            if not obj.eof:continue
            stream=dict(offset=m.start(),compressed_size=len(data)-m.start()-len(obj.unused_data),
                        size=len(payload),sha256=r.sha(payload),gzip_crc_valid=True)
            stream['linux_version_strings']=[dict(offset=x.start(),text=x[0].decode('ascii',errors='replace'))
                for x in re.finditer(rb'Linux version [^\x00\n]{1,250}',payload)]
            stream['cpio_newc_magic']=payload[:6] in (b'070701',b'070702')
            streams.append(stream)
        except zlib.error:
            continue
    return dict(size=len(data),sha256=r.sha(data),gzip_streams=streams)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    if not a.input.is_file() or a.input.stat().st_size>32*1024*1024:raise ValueError('expected bounded regular file')
    a.output.write_text(json.dumps(inspect(a.input.read_bytes()),indent=2)+'\n')
