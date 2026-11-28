#!/usr/bin/env python3
"""Check firmware evidence links, hashes and ranges without requiring binary inputs."""
import hashlib
import json
from pathlib import Path
import re


HEX64=re.compile('[0-9a-f]{64}')


def stock_index(root,index):
    """Index and sanity-check the stock-firmware manifests (inventories, loaders, kernels, platform)."""
    errors=[];folder=root/'evidence/firmware'
    for p in sorted(folder.glob('stock-*-inventory.json')):
        key=str(p.relative_to(root))
        try:
            m=json.loads(p.read_text());total=m['size']
            if not HEX64.fullmatch(m['sha256']) or total%512:errors.append('invalid inventory identity '+key)
            index[key]=dict(sha256=m['sha256'],size=total)
            parts=m['partition_table']['partitions']
            for x in parts:
                if not 0<x['offset']<x['offset']+x['size']<=total:errors.append(f'partition outside image {key}#{x["index"]}')
            for a,b in zip(sorted(parts,key=lambda x:x['offset']),sorted(parts,key=lambda x:x['offset'])[1:]):
                if a['offset']+a['size']>b['offset']:errors.append('overlapping partitions '+key)
            for r in m['raw_regions']:
                if not 0<=r['offset']<r['offset']+r['size']<=total:errors.append(f'raw region outside image {key}')
                if 'sha256' in r:index[f'{key}#raw:0x{r["offset"]:x}']=dict(sha256=r['sha256'],size=r['size'])
            for part in m['partitions']:
                label=part['name'] or str(part['index'])
                for f in part['files']:
                    if f.get('type')!='file':continue
                    if not HEX64.fullmatch(f['sha256']) or f['size']<0 or f['size']>part['size']:errors.append(f'invalid file record {key}#{label}:{f["path"]}')
                    index[f'{key}#{label}:{f["path"]}']=dict(sha256=f['sha256'],size=f['size'])
        except (KeyError,ValueError,OSError) as e:errors.append('invalid stock inventory '+key+': '+str(e))
    p=folder/'stock-loaders.json'
    if p.exists():
        key=str(p.relative_to(root))
        try:
            for name,l in json.loads(p.read_text())['loaders'].items():
                index[f'{key}#{name}']=dict(sha256=l['sha256'],size=l['size'])
                if not all(t['valid'] for t in l['trailers']):errors.append(f'invalid ActBrm trailer recorded in {key}#{name}')
                for mem in (l.get('pack') or {}).get('members',[]):
                    lo,hi=mem['byte_range']
                    if not 0<=lo<hi<=l['size']:errors.append(f'PACK member outside loader {key}#{name}:{mem["name"]}');continue
                    index[f'{key}#{name}:{mem["name"]}']=dict(sha256=mem['sha256'],size=hi-lo)
        except (KeyError,ValueError,OSError) as e:errors.append('invalid loader manifest: '+str(e))
    for name,sections in (('stock-platform.json',('uboot',)),('stock-kernels.json',('kernels',))):
        p=folder/name
        if not p.exists():continue
        key=str(p.relative_to(root))
        try:
            m=json.loads(p.read_text())
            for rel,v in m['uboot' if 'uboot' in sections else 'kernels'].items():
                if 'uboot' in sections:index[f'{key}#uboot:{rel}']=dict(sha256=v['sha256'],size=v['size'])
                else:
                    index[f'{key}#uimage:{rel}']=dict(sha256=v['uimage_sha256'],size=v['uimage_size'])
                    index[f'{key}#image:{rel}']=dict(sha256=v['image_sha256'],size=v['image_size'])
        except (KeyError,ValueError,OSError) as e:errors.append('invalid manifest '+key+': '+str(e))
    p=folder/'stock-ddr-timing.json'
    if p.exists():
        try:
            m=json.loads(p.read_text());loaders=json.loads((folder/'stock-loaders.json').read_text())['loaders']
            if len({r['code_sha256'] for r in m['releases'].values()})!=1:errors.append('DDR timing: code differs between releases')
            for name,r in m['releases'].items():
                if loaders.get(name,{}).get('sha256')!=r['loader_sha256']:errors.append('DDR timing loader hash mismatch '+name)
                mv=r['model_vs_unicorn']
                if mv['firmware_record_reference'] or mv['primary_record_reference'] or any(mv['scenarios'].values()) \
                        or any(mv['reset_seeds'].values()):errors.append('DDR timing: model/emulation disagreement '+name)
                if 'symbolic' in r and not r['symbolic']['equals_unicorn']:errors.append('DDR timing: symbolic/emulation disagreement '+name)
                if r['class_consistency']['contradictions']:errors.append('DDR timing: provenance class contradiction '+name)
            if m['division_helpers']['mismatches']:errors.append('DDR timing: division helper model mismatch')
        except (KeyError,ValueError,OSError) as e:errors.append('invalid DDR timing evidence: '+str(e))
    errors.extend(boot_chain_checks(folder))
    p=folder/'stock-ddr-sequence.json'
    if p.exists():
        m=json.loads(p.read_text())
        if m['named']+m['unnamed']!=m['accesses'] or len(m['sequence'])!=m['accesses']:errors.append('inconsistent DDR sequence counts')
    return errors


def boot_chain_checks(folder):
    """Consistency of stock-boot-chain.json with the other manifests and between its methods."""
    p=folder/'stock-boot-chain.json'
    if not p.exists():return []
    errors=[]
    try:
        m=json.loads(p.read_text())
        loaders=json.loads((folder/'stock-loaders.json').read_text())['loaders']
        uboot=json.loads((folder/'stock-platform.json').read_text())['uboot']
        stages=m['stages']
        if [s['id'] for s in stages]!=[f'S{i}' for i in range(len(stages))]:errors.append('boot chain: stage ids not sequential')
        for a,b in zip(stages,stages[1:]):
            if b['caller']!=a['id']:errors.append('boot chain: broken caller link at '+b['id'])
        for rel,r in m['releases'].items():
            c=r['components']
            if rel.startswith('stock-'):
                if loaders.get(rel,{}).get('sha256')!=c['loader']['sha256']:errors.append('boot chain: loader hash mismatch '+rel)
                if uboot.get(rel,{}).get('sha256')!=c['uboot']['uimage_sha256']:errors.append('boot chain: U-Boot hash mismatch '+rel)
            main=r['loader']['main']
            if main['error'] or main['stopped']!='app.bin entry 0x1000':errors.append('boot chain: loader emulation incomplete '+rel)
            model=[r['bootargs']['gpio_low']]+([r['bootargs']['gpio_high']] if r['bootargs']['gpio_high'] else [])
            if [h['dt_chosen'].get('bootargs') for h in r.get('handoff',[])]!=model:
                errors.append('boot chain: emulated handoff bootargs differ from the model '+rel)
            if any(h['error'] for h in r.get('handoff',[])+r.get('handoff_bootargs',[])):errors.append('boot chain: handoff emulation error '+rel)
    except (KeyError,ValueError,OSError,StopIteration) as e:errors.append('invalid boot chain evidence: '+str(e))
    return errors


def dram_complete_checks(folder):
    """Consistency of stock-dram-complete.json (PR #6) with the loader manifest and between its methods."""
    p=folder/'stock-dram-complete.json'
    if not p.exists():return []
    errors=[]
    try:
        m=json.loads(p.read_text());loaders=json.loads((folder/'stock-loaders.json').read_text())['loaders']
        if len({r['code_sha256'] for r in m['releases'].values()})!=1:errors.append('DRAM complete: code differs between releases')
        for name,r in m['releases'].items():
            if loaders.get(name,{}).get('sha256')!=r['loader_sha256']:errors.append('DRAM complete loader hash mismatch '+name)
        for name,s in m['mode1_model_sweep_all'].items():
            if s is None or s['mismatches']:errors.append('DRAM complete: mode-1 model/emulation disagreement '+name)
        for name,row in m['memtest'].items():
            if row['model_verdict']!=row.get('emulated_verdict'):errors.append('DRAM complete: memtest model/emulation disagreement '+name)
        if not all(m['identical_across_releases'].values()):errors.append('DRAM complete: release-dependent behaviour not explained')
        if 'synthetic' not in m['models']['note'].lower():errors.append('DRAM complete: modelling note missing')
    except (KeyError,ValueError,OSError,TypeError) as e:errors.append('invalid DRAM complete evidence: '+str(e))
    return errors


def predram_checks(folder):
    """Consistency of sd2-predram.json (PR #9) with the loader manifest, the findings ledger and its own rules."""
    p=folder/'sd2-predram.json'
    if not p.exists():return []
    errors=[]
    try:
        m=json.loads(p.read_text());loaders=json.loads((folder/'stock-loaders.json').read_text())['loaders']
        fids={f['id'] for f in json.loads((folder.parent/'findings.json').read_text())}
        for name,r in m['releases'].items():
            if loaders.get(name,{}).get('sha256')!=r['loader_sha256']:errors.append('pre-DRAM loader hash mismatch '+name)
            if not r.get('verified') or r.get('actual_sha256')!=r.get('expected_sha256'):errors.append('pre-DRAM image not verified '+name)
        if len({r['bootloader_code_sha256'] for r in m['releases'].values()})!=1:errors.append('pre-DRAM: code differs between releases')
        if m['release_comparison'] and not m['release_comparison']['all_function_code_identical']:
            errors.append('pre-DRAM: function difference not explained')
        for f in m['findings']:
            if f not in fids:errors.append('pre-DRAM evidence cites unknown finding '+f)
        for r in m['register_inventory']:
            if r['boot_code_condition'] not in ('both','code 0 only','code 2 only') and not r['boot_code_condition'].startswith('scenario-only'):
                errors.append('pre-DRAM: bad boot_code_condition at '+r['instruction_address'])
            if r['access_type']=='read' and r.get('read_value_source') not in m['synthetic_rules']:
                errors.append('pre-DRAM: read without a named synthetic rule at '+r['instruction_address'])
        for lab,run in m['runs'].items():
            if run['result']['error']:errors.append('pre-DRAM run error '+lab)
    except (KeyError,ValueError,OSError,TypeError) as e:errors.append('invalid pre-DRAM evidence: '+str(e))
    return errors
def adfu_checks(folder):
    """Consistency of adfu-loopback.json (PR #9): provenance, anchors, model agreement, no hardware claims."""
    p=folder/'adfu-loopback.json'
    if not p.exists():return []
    errors=[]
    try:
        m=json.loads(p.read_text());loaders=json.loads((folder/'stock-loaders.json').read_text())['loaders']
        fids={f['id'] for f in json.loads((folder.parent/'findings.json').read_text())}
        for name,r in m['releases'].items():
            if loaders.get(name,{}).get('sha256')!=r['loader_sha256']:errors.append('ADFU loader hash mismatch '+name)
            if not r.get('verified'):errors.append('ADFU image not verified '+name)
        if not all(m['regions']['identical_across_releases'].values()):errors.append('ADFU regions differ between releases')
        if not m['anchors']['all_match_in_every_release']:errors.append('ADFU instruction anchor mismatch')
        for s in m['scenarios']:
            if not s['comparison']['agree']:errors.append('ADFU reference/firmware disagreement '+s['name'])
            if s['firmware']['outcome'].startswith('emulator'):errors.append('ADFU emulator failure '+s['name'])
        for f in m['findings']:
            if f not in fids:errors.append('ADFU evidence cites unknown finding '+f)
        if not m['model']['assumptions']:errors.append('ADFU model assumptions missing')
        if m['reentry']['reached_dram_init'] or any(x['reached_dram_init'] for x in m['full_path'] if 'loopback' in x['name'] and 'code2' in x['name']):
            errors.append('ADFU decision reached DRAM init')
    except (KeyError,ValueError,OSError,TypeError) as e:errors.append('invalid ADFU evidence: '+str(e))
    return errors
def sd2_dram_checks(folder):
    """Verify committed comparison coverage and trace provenance without firmware inputs."""
    path = folder / 'sd2-dram-comparison.json'
    errors = []
    try:
        doc = json.loads(path.read_bytes())
        releases, objects = doc['releases'], doc['distinct_pairs']
        pinned = {m['expanded_filename']: m for m in json.loads((folder / 'acquisitions.json').read_bytes())
                  if 'expanded_filename' in m}
        loaders = json.loads((folder / 'stock-loaders.json').read_bytes())['loaders']
        if set(releases) != {'koriki-v1.0', 'stock-221203', 'stock-221223', 'stock-230309', 'stock-20231014'}:
            errors.append('SD2 DRAM: missing pinned release')
        for name, release in releases.items():
            meta = pinned[release['file']]
            if (not release['verified'] or release['actual_sha256'] != meta['expanded_sha256']
                    or release['expected_sha256'] != meta['expanded_sha256']
                    or release['verified_size'] != meta['expanded_size']
                    or release['loader_sha256'] != loaders[name]['sha256']):
                errors.append('SD2 DRAM: provenance mismatch ' + name)
            if release['pairs'].keys() != doc['scenarios'].keys():
                errors.append('SD2 DRAM: incomplete scenarios for ' + name)
            for scenario, obj in release['pairs'].items():
                result = objects[obj]
                cmp = result['comparison']
                if not cmp['boot_code_provenance_ok'] or not cmp['gpio_reference_agreement']:
                    errors.append(f'SD2 DRAM: boot-code or GPIO evidence mismatch {name} {scenario}')
                if cmp['same_after_expected_differences'] != (scenario != 'gpio-exact-echo'):
                    errors.append(f'SD2 DRAM: unexplained paired difference {name} {scenario}')
                for boot_code, run in result['runs'].items():
                    if run['boot_code_observed'] != int(boot_code) or not HEX64.fullmatch(run['trace']['sha256']):
                        errors.append(f'SD2 DRAM: missing raw evidence {name} {scenario} code {boot_code}')
        for key, obj in objects.items():
            data = json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii')
            if hashlib.sha256(data).hexdigest() != key:
                errors.append('SD2 DRAM: content-addressed pair digest mismatch ' + key)
        if not doc['obs_001']['memory_property_matches'] or not doc['obs_001']['previous_command_line_agrees']:
            errors.append('SD2 DRAM: observation reconciliation mismatch')
        if doc['geometry']['devices'] != len(doc['geometry']['runs']):
            errors.append('SD2 DRAM: geometry baseline incomplete')
    except (KeyError, ValueError, OSError, TypeError) as e:
        errors.append('Invalid SD2 DRAM evidence: ' + str(e))
    return errors


def unified_checks(folder):
    """Check integrity of the compact boot-chain evidence with no firmware payloads."""
    errors = []
    try:
        doc = json.loads((folder / 'unified-boot-chain.json').read_bytes())
        acquisitions = json.loads((folder / 'acquisitions.json').read_bytes())
        pinned = {m['expanded_filename']: m for m in acquisitions if 'expanded_filename' in m}
        graph = doc['stage_graph']
        releases = {'koriki-v1.0', 'stock-221203', 'stock-221223', 'stock-230309', 'stock-20231014'}
        if set(doc['firmware']) != releases or set(doc['scenarios']) != releases:
            errors.append('Unified boot: missing pinned firmware coverage')
        if list(graph.values()) != [None, *list(graph)[:-1]] or set(graph) != set(doc['stage_coverage']):
            errors.append('Unified boot: invalid stage dependency graph')
        for release, scenarios in doc['scenarios'].items():
            firmware = doc['firmware'][release]
            pin = pinned[firmware['file']]
            if (firmware['actual_sha256'] != pin['expanded_sha256'] or
                    firmware['expected_sha256'] != pin['expanded_sha256'] or
                    firmware['verified_size'] != pin['expanded_size'] or not firmware['verified']):
                errors.append('Unified boot: firmware provenance mismatch ' + release)
            for name, run in scenarios.items():
                label = f'{release} {name}'
                rows = run['stages']
                if set(rows) != set(graph):
                    errors.append('Unified boot: incomplete graph ' + label)
                    continue
                terminal = run['terminal']
                outcome = terminal['outcome']
                parent = blocker = None
                for stage in graph:
                    row = rows[stage]
                    if blocker:
                        if row['status'] != 'blocked' or row['blocked_by'] != blocker:
                            errors.append(f'Unified boot: stage after terminal executed {label} {stage}')
                    elif row['status'] == 'terminal' and terminal['stage'] == stage and row['input_sha256'] == parent:
                        blocker = stage
                    elif (row['status'] == 'completed' and row['input_sha256'] == parent and
                          HEX64.fullmatch(row['state_sha256'])):
                        parent = row['state_sha256']
                    else:
                        errors.append(f'Unified boot: invalid state chain {label} {stage}')
                if (blocker is None) != (outcome == 'linux-entry-boundary'):
                    errors.append('Unified boot: outcome/graph mismatch ' + label)
                if blocker is None:
                    raw = rows['uboot-entry']['state']['afi_exact_hex']
                    consume = rows['uboot-afi-and-ram']['state']['afi']
                    handoff = rows['device-tree']['state']
                    jump = rows['linux-entry']['state']
                    if (len(bytes.fromhex(raw)) != 16 or raw != consume['exact_hex'] or raw != handoff['afi_in_memory'] or
                            raw != run['dram_result']['afi']['bytes'] or
                            handoff['dt_memory_reg'] != ['0x0', hex(consume['gd_ram_size'])] or
                            jump['r2'] != handoff['ft_addr']):
                        errors.append('Unified boot: AFI, memory or Linux transfer mismatch ' + label)
            for medium in ('sd0', 'sd2'):
                if scenarios[f'{medium}-reference']['terminal']['outcome'] != 'linux-entry-boundary':
                    errors.append(f'Unified boot: failed {medium} reference {release}')
        if not doc['obs_001']['sd2-reference']['all_match'] or doc['obs_001']['sd2-strap-low']['all_match']:
            errors.append('Unified boot: inconsistent observation reconciliation')
    except (KeyError, ValueError, OSError, TypeError) as error:
        errors.append('Invalid unified boot-chain evidence: ' + str(error))
    return errors


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
    # Decompressed kernel streams recorded by payload manifests are citable by stream index.
    for p in sorted(folder.glob('*kernel-payload.json')):
        try:
            for i,s in enumerate(json.loads(p.read_text()).get('gzip_streams',[])):
                if not re.fullmatch('[0-9a-f]{64}',s['sha256']) or s['size']<=0:errors.append('invalid gzip stream record '+p.name)
                index[f'{p.relative_to(root)}#gzip_streams/{i}']=dict(sha256=s['sha256'],size=s['size'])
        except (KeyError,ValueError,OSError) as e:errors.append('invalid payload manifest '+p.name+': '+str(e))
    errors.extend(stock_index(root,index))
    errors.extend(dram_complete_checks(folder))
    errors.extend(predram_checks(folder))
    errors.extend(adfu_checks(folder))
    errors.extend(sd2_dram_checks(folder))
    errors.extend(unified_checks(folder))
    cited=[(f['id'],e) for f in json.loads((root/'evidence/findings.json').read_text()) for e in f['evidence']]
    hw=root/'registers/canonical/hardware.json'
    if hw.exists():
        for b in json.loads(hw.read_text())['blocks']:
            cited+=[(b['id'],e) for e in b['evidence']]
            cited+=[(r['id'],e) for r in b['registers'] for e in r['evidence']]
    for owner,e in cited:
            if 'artifact' not in e:continue
            c=index.get(e['artifact'])
            if c is None:errors.append('unknown binary artifact '+owner+' '+e['artifact']);continue
            if e.get('sha256')!=c['sha256']:errors.append('binary evidence hash mismatch '+owner)
            if 'offset_start' in e and not 0 <= e['offset_start'] < e.get('offset_end',e['offset_start']+1) <= c['size']:
                errors.append('binary evidence range outside artifact '+owner)
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
