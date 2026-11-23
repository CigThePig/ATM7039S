#!/usr/bin/env python3
"""Rebuild source-derived datasets from pinned checkouts (no downloading)."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import research as r

ROOT=r.ROOT
REPOS={
 'vendor-kernel':('s500_kernel','rg35xx-cfw/s500_kernel','81cc77b59250341b9abe90ed4188cde7b7aa1eeb'),
 'uboot':('u-boot_s500','rg35xx-cfw/u-boot_s500','0a557e37a5274d40bcd357585d4bcd3b73619371'),
 'batocera':('batocera.linux','rg35xx-cfw/batocera.linux','961d8abcea18017e6c6275c914f81f3b3d72c760'),
 'linux':('linux','torvalds/linux','adc218676eef25575469234709c2d87185ca223a'),
 'knulli-wiki':('knulli.org','knulli-cfw/knulli.org','314b26f1822c8531bed8a9cea72028b229b4436e'),
 'stock-demo':('rg35xx-stock-sdl-demo','yohanes/rg35xx-stock-sdl-demo','8dbe95d60558740893a57593d792e388c0932ba9'),
 'cfw-wiki':('rg35xx-cfw.github.io','rg35xx-cfw/rg35xx-cfw.github.io','1dc0a87ee27a9d6216678929bcc54eee87f281f9'),
 'buildroot':('buildroot','rg35xx-cfw/buildroot','798ba21c01ceb8ab1a5a4ae6986e0b77d5d8f7aa'),
 'remesa':('reMESA','reMESA-devgroup/reMESA','845f385cd61aa17042f9426ec8306b4386005c24'),
 'sgx544-history':('SGX544-reMESA','reMESA-devgroup/SGX544-reMESA','4c1e3095e73a506bfc48bd77041d35da0d1231e6'),
 'koriki':('Koriki','rg35xx-cfw/Koriki','26f47799202530c89edadd2dc9faa4ffcab0960e')}
HEADER='arch/arm/mach-owl/include/mach/regs_map-atm7039.h'
BOARD='board/batocera/actions/rg35xx/'
DTB=BOARD+'2100mAh-gpu.dtb'
MODULE=BOARD+'old_overlay/fsoverlay/userdata/system/modules/gpio_keys_polled.ko'
FILES={
 'vendor-kernel':[HEADER,'Makefile','COPYING','arch/arm/boot/dts/rg35xx_atm7039.dts','arch/arm/boot/dts/actduino.dtsi','arch/arm/configs/rg35xx_atm7039_defconfig','arch/arm/mach-owl/common-owl.c','arch/arm/mach-owl/platsmp-owl.c','arch/arm/mach-owl/clocktree-atm7059.c','arch/arm/mach-owl/pinctrl_data-atm7059.c','drivers/gpu/pvr/eurasia_km_linux/config_kernel.h','drivers/gpu/pvr/eurasia_km/include4/pvrversion.h','drivers/gpu/pvr/eurasia_km_linux/include4/pvrversion.h','drivers/gpu/pvr/eurasia_km_linux/config_kernel.mk','drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/syslocal.h','drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/sysconfig.c','drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/sysconfig.h','drivers/video/owl/dss/de_atm7059.c','drivers/video/owl/displays/lcdc/lcdchw.c'],
 'uboot':['Makefile','Licenses/README','board/actions/owl/owl.c','board/actions/owl/owl_afi.c','arch/arm/include/asm/arch-owl/owl_mmc.h','arch/arm/cpu/armv7/owl/owl_clk.c','include/configs/s500.h'],
 'batocera':[DTB,MODULE,BOARD+'genimage.cfg',BOARD+'create-boot-script.sh',BOARD+'uEnv.txt','configs/batocera-rg35xx.board','package/batocera/boot/uboot-rg35xx/uboot-rg35xx.mk','package/batocera/gpu/powervr-sgx544-driver/powervr-sgx544-driver.mk'],
 'linux':['arch/arm/boot/dts/actions/owl-s500.dtsi','arch/arm64/boot/dts/actions/s700.dtsi','arch/arm64/boot/dts/actions/s900.dtsi','drivers/clk/actions/owl-s500.c','drivers/pinctrl/actions/pinctrl-s500.c','drivers/dma/owl-dma.c','drivers/mmc/host/owl-mmc.c','drivers/tty/serial/owl-uart.c','drivers/i2c/busses/i2c-owl.c','drivers/spi/spi-owl.c','drivers/clocksource/timer-owl.c','drivers/gpu/drm/imagination/Kconfig','drivers/pmdomain/actions/owl-sps.c'],
 'knulli-wiki':['docs/devices/anbernic/rg35xx.md'],
 'stock-demo':['README.md','Makefile','menu.c','ADB_ON.sh'],
 'cfw-wiki':['1_Introduction.md','_docs/00_general/2_status.md'],
 'remesa':['README.md','LICENSE','projects/sgx544/README.md','projects/sgx544/docs/FINDINGS.md','projects/sgx544/docs/ROADMAP.md'],
 'sgx544-history':['README.md','LICENSE'],
 'koriki':['README.md','generate_release.sh'], 'buildroot':['README']}

def apply_cmu_fields(blocks):
 rows=json.loads((ROOT/'comparisons/cmu-fields.json').read_text())
 block=next(b for b in blocks if b['id']=='candidate:CMU_BASE')
 for row in rows:
  reg=next(x for x in block['registers'] if x['name']==row['register'])
  if not any(f['name']==row['field']['name'] for f in reg['fields']):
   reg['fields'].append(row['field'])

def preserve_extra(generated, previous, key):
 keys={key(x) for x in generated}
 return generated+[x for x in previous if key(x) not in keys]

def ref(source,path,line=1,end=None):return dict(source=source,path=path,line_start=line,line_end=end or line)

def build(inputs):
 old_sources=json.loads((ROOT/'evidence/sources.json').read_text())
 old_files=json.loads((ROOT/'evidence/files.json').read_text())
 sources=[];file_records=[]
 for sid,(folder,repo,commit) in REPOS.items():
  p=inputs/folder
  if (p/'.git').exists():
   head=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()
   if head!=commit:raise ValueError('unexpected revision: '+folder)
  else:
   manifest=json.loads((ROOT/'evidence/files.json').read_text())
   for record in manifest:
    if record['source']==sid:
     f=p/record['path']
     if not f.exists() or r.sha(f.read_bytes())!=record['sha256']:raise ValueError('source hash mismatch: '+str(f))
  sources.append(dict(id=sid,url='https://github.com/'+repo,revision=commit,type='source-repository',examined='2026-11-22',license_status='file-specific; see reports/licensing.md',scope='related-chip source' if sid in ['linux','vendor-kernel','uboot'] else 'project history and configuration'))
  for name in FILES[sid]:
   f=p/name
   if not f.is_file():continue
   data=f.read_bytes()
   file_records.append(dict(source=sid,path=name,sha256=r.sha(data),size=len(data),raw_url='https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+name,view_url='https://github.com/'+repo+'/blob/'+commit+'/'+name))
 sources += [dict(id='gist',url='https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0',revision='7783b472fce9256d91e3d8d331f6dd8cd8aeb8d6',type='flattened-device-tree',examined='2026-11-22',license_status='No license established; original source not redistributed',scope='public RG35XX-labelled software artifact; extraction provenance not established'),
 dict(id='sec2015',url='https://www.sec.gov/Archives/edgar/data/1342068/000114420416096913/v436680_20f.htm',revision='2015 Form 20-F, filed 2016',type='manufacturer-filing',examined='2026-11-22',license_status='Referenced, not copied',scope='manufacturer product table; not electrical characterization'),
 dict(id='sec2013',url='https://www.sec.gov/Archives/edgar/data/1342068/000114420414024402/v374190_20f.htm',revision='2013 Form 20-F, filed 2014',type='manufacturer-filing',examined='2026-11-22',license_status='Referenced, not copied',scope='ATM7039, not S variant'),
 dict(id='tinyhack',url='https://tinyhack.com/2023/12/31/reverse-engineering-rg35xx-stock-firmware/',revision='article dated 2023-12-31; accessed 2026-11-22',type='researcher-report',examined='2026-11-22',license_status='Referenced; independently paraphrased',scope='reported stock firmware observations, not independently reproduced boot'),
 dict(id='actions-launch',url='https://www.prnewswire.com/news-releases/actions-semiconductor-launches-high-performance-owl-series-chipset-225168632.html',revision='2013-09-25',type='manufacturer-announcement',examined='2026-11-22',license_status='Referenced only',scope='ATM7039 announcement, not ATM7039S')]
 r.save(ROOT/'evidence/sources.json',sources);r.save(ROOT/'evidence/files.json',file_records)
 data=(inputs/'rg35xx.dts').read_bytes();gist=r.tree(data);gist.update(ranges=r.ranges(gist['nodes']),input_sha256=r.sha(data))
 r.save(ROOT/'evidence/gist-tree.json',gist)
 blob=(inputs/'batocera.linux'/DTB).read_bytes();dtb=r.tree(blob);dtb.update(ranges=r.ranges(dtb['nodes']),input_sha256=r.sha(blob))
 r.save(ROOT/'evidence/batocera-2100-tree.json',dtb);r.save(ROOT/'evidence/batocera-2100-artifact.json',r.firmware(blob))
 diff=r.compare(gist['nodes'],dtb['nodes']);r.save(ROOT/'comparisons/gist-vs-batocera-2100.json',diff)
 lines=['# Gist versus published 2100mAh GPU DTB','','Properties compared as serialized bytes, ignoring line numbers, property order, and DTB offsets. This comparison does not establish independent provenance.','','| Node | Changed properties |','|---|---|']
 for row in diff:
  a,b=row['left'] or {},row['right'] or {};keys=[k for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)]
  lines.append('| `'+row['path']+'` | '+', '.join('`'+k+'`' for k in keys)+' |')
 (ROOT/'comparisons/gist-vs-batocera-2100.md').write_text('\n'.join(lines)+'\n')
 blocks=[]
 for x in gist['ranges']:
  if x['size'] is None or x['size']==0:continue
  node=next(n for n in gist['nodes'] if n['path']==x['path'])
  props=node['properties'];deps={k:v for k,v in props.items() if 'clock' in k or 'reset' in k or 'supply' in k or 'pinctrl' in k}
  blocks.append(dict(id='dt:'+x['path']+':'+str(x['index']),base=x['address'],size=x['size'],scope='RG35XX-gist-software',status=x['status'],interrupts_raw=x['interrupts_raw'],dependencies=json.dumps(deps),evidence=[ref('gist','rg35xx.dts',x['line'])],registers=[],notes='Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.'))
 h=r.constants((inputs/'s500_kernel'/HEADER).read_text(),HEADER)
 # Resolve only explicit BASE+offset relationships; no guessing from nearby numbers.
 defs={x['name']:x for x in h['definitions']};group={}
 for x in h['definitions']:
  m=re.fullmatch(r'\(\s*(\w+_BASE)\s*\+\s*(0[xX][0-9a-fA-F]+)\s*\)',x['expression'])
  if not m or m[1] not in defs:continue
  group.setdefault(m[1],[]).append(dict(id='reg:'+x['name'],name=x['name'],offset=int(m[2],16),width=None,access='unknown',reset=None,fields=[],confidence='inferred',scope='related-ATM7039-header',hardware_validated=False,evidence=[ref('vendor-kernel',HEADER,x['line'])]))
 for base,regs in group.items():
  d=defs[base];blocks.append(dict(id='candidate:'+base,base=d['value'],size=None,scope='related-ATM7039-header',status='candidate-only',interrupts_raw=[],dependencies='Unknown on ATM7039S; consult vendor clock/reset/power code before use.',evidence=[ref('vendor-kernel',HEADER,d['line'])],registers=regs,notes='Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.'))
 # Add explicitly scoped S500 source bit masks only when register offsets agree.
 for block in blocks:
  match=re.fullmatch(r'candidate:(UART[0-6]|SD[0-2])_BASE',block['id'])
  if not match:continue
  family='uart' if match[1].startswith('UART') else 'mmc'
  path='drivers/tty/serial/owl-uart.c' if family=='uart' else 'drivers/mmc/host/owl-mmc.c'
  defs2=r.constants((inputs/'linux'/path).read_text(),path)['definitions']
  index2={d['name']:d for d in defs2}
  for reg in block['registers']:
   suffix=reg['name'].split('_',1)[1]
   upstream_name=('OWL_UART_' if family=='uart' else 'OWL_REG_SD_')+suffix
   if upstream_name not in index2 or index2[upstream_name]['value']!=reg['offset']:continue
   prefix=('OWL_UART_' if family=='uart' else 'OWL_SD_')+suffix+'_'
   for field in defs2:
    if field['name'].startswith(prefix) and field['expression'].startswith(('BIT(', 'GENMASK(')):
     reg['fields'].append(dict(name=field['name'],mask=field['value'],meaning='S500 source symbol; ATM7039S semantics unverified',scope='S500-source',confidence='inferred',evidence=[ref('linux',path,field['line'])]))
 apply_cmu_fields(blocks)
 r.save(ROOT/'registers/canonical/hardware.json',dict(schema_version=1,target='ATM7039S',hardware_validated=False,blocks=blocks))
 # Preserve upstream register/bitmask observations separately from target claims.
 upstream=[]
 for path in FILES['linux']:
  if path.endswith('.c') and (inputs/'linux'/path).exists():
   v=r.constants((inputs/'linux'/path).read_text(),path)
   upstream.append(dict(source='linux',path=path,**v))
 r.save(ROOT/'evidence/upstream-constants.json',upstream)
 # Component-only acquisition record: no whole stock/Garlic image has been analysed.
 artifacts=[]
 for path in [DTB,MODULE]:
  b=(inputs/'batocera.linux'/path).read_bytes();a=r.firmware(b)
  a.update(source='batocera',source_revision=REPOS['batocera'][2],original_filename=Path(path).name,path=path,acquired='2026-11-22',device='RG35XX original-labelled repository path; no hardware execution',version='repository snapshot, not a firmware release version',redistribution='not included; rights not independently cleared',identified_components='FDT' if path==DTB else 'ARM relocatable kernel module',partition_layout='not applicable: standalone component')
  if path==MODULE:
   proc=subprocess.run(['readelf','-p','.modinfo',str(inputs/'batocera.linux'/path)],capture_output=True,text=True,check=True)
   # Metadata only; no proprietary machine-code excerpt.
   a['module_metadata']=[line.split('] ',1)[1] for line in proc.stdout.splitlines() if '] ' in line]
  artifacts.append(a)
 r.save(ROOT/'evidence/artifacts.json',artifacts)
 # Pin raw gist file as retrieved; do not redistribute unlicensed original source.
 raw='https://gist.githubusercontent.com/macromorgan/0491c853fcd28dc093945220348192c0/raw/d5c388f54dd687637a6331b8a611e84e25deff9a/rg35xx.dts'
 file_records.append(dict(source='gist',path='rg35xx.dts',sha256=r.sha(data),size=len(data),raw_url=raw,view_url='https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0'))
 pdf=inputs/'s500-datasheet.pdf'
 if pdf.exists():
  b=pdf.read_bytes();url='https://gzhls.at/blob/ldb/9/a/e/c/e8dd47a7e48102d05772a88a11c09fc5d86e.pdf'
  sources.append(dict(id='s500-pdf',url=url,revision='S500 datasheet v1.4 dated 2015-07-17; mirrored manufacturer-branded document',type='related-chip-manual',examined='2026-11-22',license_status='All rights reserved; referenced, not redistributed',scope='S500 only; not authenticated as an ATM7039S manual'))
  file_records.append(dict(source='s500-pdf',path='s500-datasheet.pdf',sha256=r.sha(b),size=len(b),raw_url=url,view_url=url,pages=329))
 # Preserve curated acquisition sources and extra audited files not regenerated here.
 sources=preserve_extra(sources,old_sources,lambda x:x['id'])
 file_records=preserve_extra(file_records,old_files,lambda x:(x['source'],x['path']))
 r.save(ROOT/'evidence/sources.json',sources)
 r.save(ROOT/'evidence/files.json',file_records)
 r.generate(ROOT)
 print(json.dumps(dict(blocks=len(blocks),registers=sum(len(x['registers']) for x in blocks),different_nodes=len(diff),files=len(file_records))))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('inputs',type=Path);build(p.parse_args().inputs)
