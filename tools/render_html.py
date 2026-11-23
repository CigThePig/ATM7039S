#!/usr/bin/env python3
"""Build local, searchable HTML; does not deploy or publish a website."""
from pathlib import Path
import html
import re
import markdown
ROOT=Path(__file__).resolve().parents[1]
site=ROOT/'site';site.mkdir(exist_ok=True)
files=[ROOT/'README.md',ROOT/'CONTRIBUTING.md',ROOT/'tools/README.md']+sorted((ROOT/'docs').glob('*.md'))+sorted((ROOT/'reports').glob('*.md'))+sorted((ROOT/'comparisons').glob('*.md'))+[ROOT/'registers/generated/reference.md',ROOT/'evidence/catalogue.md',ROOT/'evidence/findings.md']
style='body{font:17px/1.6 system-ui;max-width:1100px;margin:2em auto;padding:0 1em;color:#18232b}table{border-collapse:collapse;display:block;overflow:auto}td,th{border:1px solid #adb9c3;padding:.35em .65em;text-align:left}code{background:#edf1f4}pre{overflow:auto;padding:1em;background:#edf1f4}a{color:#075ca8}nav{border-bottom:1px solid #ccd;padding:1em 0}h1,h2,h3{scroll-margin-top:1em}.scope{background:#fff3cd;padding:1em}'
for p in files:
 text=p.read_text();body=markdown.markdown(text,extensions=['tables','fenced_code','toc'])
 body=re.sub(r'href="([^"#]+)\.md(#[^"]*)?"',lambda m:'href="'+m[1]+'.html'+(m[2] or '')+'"',body)
 rel=p.relative_to(ROOT).with_suffix('.html');dest=site/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 prefix='../'*len(rel.parent.parts)
 dest.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(p.stem)+' — ATM7039S research</title><style>'+style+'</style><nav><a href="'+prefix+'README.html">Project index</a> · Source-derived research, no target hardware validation</nav><main>'+body+'</main></html>')
(site/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=README.html"><title>ATM7039S reference</title><a href="README.html">Open reference</a></html>')
print('Rendered',len(files),'documents to site/')

# Copy only original textual research artifacts needed by relative links.
import shutil
for folder in ['evidence','registers','comparisons','reports','tools']:
 for p in (ROOT/folder).rglob('*'):
  if p.is_file() and p.suffix in ['.json','.csv','.h','.py','.log']:
   dest=site/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
shutil.copyfile(ROOT/'LICENSE',site/'LICENSE')
