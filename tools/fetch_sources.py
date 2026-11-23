#!/usr/bin/env python3
"""Retrieve hash-pinned public inputs as files; never execute or redistribute them."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from build_dataset import REPOS
import research as r

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
 manifest=json.loads((r.ROOT/'evidence/files.json').read_text())
 for item in manifest:
  sid=item['source'];rel=Path(item['path'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe manifest path')
  dest=a.output/(REPOS[sid][0] if sid in REPOS else '')/rel
  if dest.exists() and r.sha(dest.read_bytes())==item['sha256']:continue
  req=urllib.request.Request(item['raw_url'],headers={'User-Agent':'ATM7039S-public-research/0.1'})
  with urllib.request.urlopen(req,timeout=90) as response:
   data=response.read(32*1024*1024+1)
  if len(data)>32*1024*1024:raise ValueError('source exceeds download limit')
  if len(data)!=item['size'] or r.sha(data)!=item['sha256']:raise ValueError('source hash/length mismatch: '+str(dest))
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  print(sid+': '+item['path'])
