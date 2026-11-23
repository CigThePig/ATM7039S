#!/usr/bin/env python3
"""Validate local source hashes and evidence line ranges; no network or hardware."""
import argparse
import json
from pathlib import Path
import research as r
from build_dataset import REPOS

def audit(inputs,root=None):
 root=root or r.ROOT
 manifest=json.loads((root/'evidence/files.json').read_text());errors=[];lookup={}
 for record in manifest:
  sid=record['source'];p=inputs/(REPOS[sid][0] if sid in REPOS else '')/record['path']
  if not p.exists():errors.append('missing '+str(p));continue
  data=p.read_bytes()
  if r.sha(data)!=record['sha256'] or len(data)!=record['size']:errors.append('hash/size mismatch '+str(p))
  lookup[sid,record['path']]=data
 refs=[]
 for f in json.loads((root/'evidence/findings.json').read_text()):refs+=f['evidence']
 for b in json.loads((root/'registers/canonical/hardware.json').read_text())['blocks']:
  refs+=b['evidence']
  for reg in b['registers']:
   refs+=reg['evidence']
   for field in reg['fields']:refs+=field['evidence']
 for e in refs:
  if 'path' not in e:continue
  key=e['source'],e['path']
  if key not in lookup:errors.append('uncatalogued evidence file '+str(key));continue
  if 'line_start' in e:
   count=len(lookup[key].splitlines());start=e['line_start'];end=e.get('line_end',start)
   if not 1<=start<=end<=count:errors.append('invalid evidence lines '+str(e))
 return dict(files=len(manifest),references=len(refs),errors=sorted(set(errors)))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('inputs',type=Path);a=p.parse_args();result=audit(a.inputs);print(json.dumps(result,indent=2));raise SystemExit(bool(result['errors']))
