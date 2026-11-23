#!/usr/bin/env python3
"""Check firmware evidence links, hashes and ranges without requiring binary inputs."""
import json
from pathlib import Path
import re


def validate(root):
    errors=[];index={}
    folder=root/'evidence/firmware'
    if not folder.exists():return errors
    for name in ['koriki-v1.0.json','koriki-v1.0-rootfs.json','v6c-bootfix.json','koriki-1031-boot.json']:
        p=folder/name
        try:
            m=json.loads(p.read_text());seen=set()
            for c in m['components']:
                key=str(p.relative_to(root))+'#'+c['id']
                if c['id'] in seen:errors.append('duplicate firmware component '+key)
                seen.add(c['id'])
                if not re.fullmatch('[0-9a-f]{64}',c['sha256']) or c['size']<=0:
                    errors.append('invalid component hash/size '+key)
                loc=c.get('location',{})
                if loc.get('kind')=='disk-region' and not 0 <= loc['offset'] < loc['offset']+c['size'] <= m['size']:
                    errors.append('invalid disk component bounds '+key)
                index[key]=c
        except (KeyError,ValueError,OSError) as e:errors.append('invalid firmware manifest '+name+': '+str(e))
    for f in json.loads((root/'evidence/findings.json').read_text()):
        for e in f['evidence']:
            if 'artifact' not in e:continue
            c=index.get(e['artifact'])
            if c is None:errors.append('unknown binary artifact '+f['id']);continue
            if e.get('sha256')!=c['sha256']:errors.append('binary evidence hash mismatch '+f['id'])
            if 'offset_start' in e and not 0 <= e['offset_start'] < e.get('offset_end',e['offset_start']+1) <= c['size']:
                errors.append('binary evidence range outside artifact '+f['id'])
    for name in ['early-afi-refs.json','uboot-afi-refs.json']:
        p=folder/name
        try:
            m=json.loads(p.read_text())
            if not 0<=m['range_start']<m['range_end']<=m['size']:errors.append('bad ARM inventory range '+name)
            if any(not m['range_start']<=x['offset']<m['range_end'] for x in m['references']):errors.append('ARM reference outside range '+name)
        except (KeyError,ValueError,OSError) as e:errors.append('invalid ARM inventory '+name+': '+str(e))
    return errors


if __name__=='__main__':
    result=validate(Path(__file__).resolve().parents[1]);print(json.dumps({'errors':result},indent=2));raise SystemExit(bool(result))
