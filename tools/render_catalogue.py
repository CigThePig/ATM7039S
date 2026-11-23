#!/usr/bin/env python3
"""Render searchable source and finding indexes from the evidence database."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sources=json.loads((ROOT/'evidence/sources.json').read_text());byid={s['id']:s for s in sources}
files=json.loads((ROOT/'evidence/files.json').read_text())
lines=['# Source and provenance catalogue','','Machine-readable records: `sources.json`, `files.json`, `artifacts.json`. Hashes identify exact examined bytes; repository URLs below are accompanied by immutable revisions. Acquisition date: 2026-11-22.','','| ID | Source | Revision | Scope | License treatment |','|---|---|---|---|---|']
for s in sources:lines.append('| '+s['id']+' | ['+s['id']+']('+s['url']+') | `'+s['revision']+'` | '+s['scope']+' | '+s['license_status']+' |')
lines+=['','## Examined files','','| Source | File | SHA-256 | Bytes |','|---|---|---|---|']
for f in files:lines.append('| '+f['source']+' | ['+f['path']+']('+f['view_url']+') | `'+f['sha256']+'` | '+str(f['size'])+' |')
(ROOT/'evidence/catalogue.md').write_text('\n'.join(lines)+'\n')
lines=['# Findings ledger','','Confidence applies to the exact claim and scope. A verified source observation is not hardware validation. All findings in this edition are unvalidated on the physical target. See `findings.json` for structured records and `contradictions.json` for unresolved conflicts.']
for f in json.loads((ROOT/'evidence/findings.json').read_text()):
 lines+=['', '## '+f['id'],'',f['claim'],'', '**Confidence:** '+f['confidence']+' · **Scope:** '+f['scope']+' · **Validation:** '+f['validation'],'','Evidence:']
 for e in f['evidence']:
  source=byid[e['source']];url=source['url'];label=e['source']
  if e.get('path'):
   label+=' / '+e['path'];record=next((x for x in files if x['source']==e['source'] and x['path']==e['path']),None)
   if record:url=record['view_url']
   if e.get('line_start'):url+='#L'+str(e['line_start'])+'-L'+str(e.get('line_end',e['line_start']))
  if e.get('section'):label+=' / '+e['section']
  if e.get('node'):label+=' / '+e['node']
  lines+=['','- ['+label+']('+url+')']
 lines+=['','Limits: '+f['limitations']]
(ROOT/'evidence/findings.md').write_text('\n'.join(lines)+'\n')
print('Rendered source and finding catalogues')
