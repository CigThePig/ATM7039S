#!/usr/bin/env python3
"""Build, replay and validate the offline ATM7039S initialization specification."""
import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INPUT = 'specifications/bootloader-initialization.json'
CONTRACT = 'evidence/firmware/bootloader-initialization-contract.json'
TRACE = 'evidence/firmware/boot-initialization-trace.json'
REFERENCE = 'docs/bootloader-operation-reference.md'
HISTORY = 'evidence/firmware/unified-boot-chain.json'
CANONICAL = 'registers/canonical/hardware.json'
FIELDS = ['phase', 'domain', 'op', 'address', 'width', 'value', 'pc', 'site', 'function', 'rule']
IMPLEMENTATION = {
    'architectural', 'demonstrated-consumer', 'documented-hardware', 'conservative',
    'board-specific', 'configuration-dependent', 'recovery-only', 'resume-only',
    'diagnostic', 'proprietary-compatibility', 'replaceable', 'omission-candidate', 'unknown',
}
EVIDENCE = {'physical-observation', 'executed', 'static', 'executed-synthetic', 'pinned-source',
            'independent-model', 'related-soc', 'hypothesis', 'unknown'}
RELATIONS = {'firmware-data', 'firmware-control', 'documented-hardware', 'ordering-only',
             'model', 'conservative', 'unresolved'}
CONDITIONS = {'medium', 'mode', 'release', 'scenario', 'outcome', 'completed', 'boot_code'}
VALID_EVENT_MATCH = set(FIELDS) | {'after_boundary', 'before_boundary'}
PRIVATE_PATH = re.compile(r'(/(?:workspace|home|Users|mnt/data)/|[A-Za-z]:\\(?:Users|Documents)\\)')


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique_keys)


def digest_bytes(blob):
    return hashlib.sha256(blob).hexdigest()


def digest(obj):
    return digest_bytes(json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii'))


def formatted(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=True, sort_keys=True) + '\n').encode('ascii')


def read_evidence(root, spec):
    refs = {}
    sources = {row['id']: row for row in read(root / 'evidence/sources.json')}
    for key, ref in spec['evidence'].items():
        path = Path(ref['path'])
        if path.is_absolute() or '..' in path.parts or path.suffix != '.json':
            raise ValueError(f'{key}: evidence must be a repository-relative JSON path')
        data = read(root / path)
        item = data
        for part in ref.get('pointer', []):
            item = item[part]
        if 'id' in ref:
            item, = (row for row in item if row['id'] == ref['id'])
        if isinstance(item, dict) and 'git_blob_sha1' in item:
            source = sources[item['source']]
            if (item['revision'] != source['revision'] or not re.fullmatch(r'[0-9a-f]{40}', item['git_blob_sha1'])
                    or not all(0 < start <= end for start, end in item['line_ranges'])):
                raise ValueError(f'{key}: invalid pinned source reference')
        refs[key] = {**ref, 'selection_sha256': digest(item)}
    return refs


def registers(root, spec):
    catalogue = read(root / CANONICAL)
    by_address = defaultdict(list)
    for block in catalogue['blocks']:
        for row in block['registers']:
            by_address[block['base'] + row['offset']].append(row['id'])
    return {
        key: {**row, 'catalogue_ids': sorted(set(by_address[row['address']]))
              if row['space'] == 'mmio' else []}
        for key, row in spec['registers'].items()
    }


def build_contract(root, spec):
    evidence = read_evidence(root, spec)
    firmware = read(root / HISTORY)
    identities = {}
    for release, data in firmware['firmware'].items():
        uboot = firmware['scenarios'][release]['sd2-reference']['stages']['uboot-entry']['state']['uboot']
        identities[release] = {key: data[key] for key in (
            'file', 'actual_sha256', 'loader_sha256', 'bootloader_code_sha256', 'block0_sha256', 'config')}
        identities[release]['app_span_sha256'] = (
            firmware['scenarios'][release]['sd2-reference']['stages']['load-app-and-uboot']['state']['app_sha256'])
        identities[release]['uboot_payload_sha256'] = uboot['payload_sha256']
    return {**spec, 'evidence': evidence, 'registers': registers(root, spec), 'firmware': identities,
            'register_catalogue': CANONICAL, 'trace': TRACE}


def trace_bytes(doc):
    # Each scenario's RLE stream occupies one row per actual event run. Keep the
    # rest ordinary pretty JSON and the index independent of line numbering.
    header = formatted({key: value for key, value in doc.items() if key != 'events'}).rstrip()
    streams = []
    for name, rows in sorted(doc['events'].items()):
        lines = [json.dumps(row, ensure_ascii=True, separators=(',', ':')) for row in rows]
        streams.append(f'    {json.dumps(name)}: [\n      ' + ',\n      '.join(lines) + '\n    ]')
    return header[:-2] + (',\n  "events": {\n' + ',\n'.join(streams) + '\n  }\n}\n').encode('ascii')


def fixture_id(release, name):
    return f'{release}/{name}'


def state_of(row, stage):
    return row['stages'][stage].get('state', {})


def facts_for(release, run):
    decision = state_of(run, 'recovery-resume-decision').get('decision')
    return dict(release=release, scenario=run['scenario']['name'], medium=run['scenario']['medium'],
                mode=decision, outcome=run['terminal']['outcome'],
                completed=[key for key, row in run['stages'].items() if row['status'] == 'completed'],
                boot_code=state_of(run, 'block-0').get('boot_code'))


def matches(facts, conditions):
    for key, allowed in conditions.items():
        if key == 'completed':
            if not set(allowed) <= set(facts[key]):
                return False
        elif facts[key] not in allowed:
            return False
    return True


def event_matches(event, selector):
    return all(key in event and event[key] in allowed for key, allowed in selector.items())


def indexed_events(rows):
    index = 0
    for count, values in rows:
        yield index, count, dict(zip(FIELDS, values))
        index += count


def find_events(rows, checks, boundaries):
    access = {k: v for k, v in checks.items() if k in FIELDS}
    lower = max((index for phase, _, index in boundaries if phase in checks.get('after_boundary', [])), default=0)
    upper = min((index for phase, _, index in boundaries if phase in checks.get('before_boundary', [])),
                default=float('inf'))
    return [(i, n, e) for i, n, e in rows if lower <= i < upper and event_matches(e, access)]


def check_access(operation, check, rows, boundaries, supplemental, result):
    selector = check['match']
    pos = []
    count = 0
    if check['kind'] == 'boundary':
        pos = [index for phase, pc, index in boundaries
               if event_matches({'phase': phase, 'pc': pc}, selector)]
        count = len(pos)
    elif check['kind'] == 'supplemental':
        pos = [e['event_index'] for e in supplemental if event_matches(e, selector)]
        count = len(pos)
    elif check['kind'] == 'state':
        actual = result
        for key in check['path']:
            actual = actual[key]
        if actual != check['equals']:
            raise ValueError(f"{operation}: {check['path']} was {actual!r}, expected {check['equals']!r}")
        return [None]
    else:
        selected = find_events(rows, selector, boundaries)
        pos = [i for i, _, _ in selected]
        count = sum(n for _, n, _ in selected)
        if 'rmw' in check:
            rmw = check['rmw']
            preceding = find_events(rows, rmw['read'], boundaries)
            read_index = 0
            for index, _, event in selected:
                while read_index < len(preceding) and preceding[read_index][0] < index:
                    read_index += 1
                before = preceding[read_index - 1] if read_index else None
                if (before is None or before[2]['address'] != event['address'] or
                        before[2]['width'] != event['width'] or before[2]['domain'] != event['domain'] or
                        (before[2]['value'] & ~rmw['clear'] | rmw['set']) != event['value']):
                    raise ValueError(f'{operation}: RMW mismatch at event {index}')
    lo, hi = check['count']
    if count < lo or (hi is not None and count > hi):
        raise ValueError(f'{operation}: {check["kind"]} match {selector}: count {count}, expected {lo}..{hi}')
    return pos


def check_structure(spec, history):
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def cites(ids, who):
        require(ids and set(ids) <= refs.keys(), f'{who}: missing or unknown evidence')

    def when(conditions, who):
        require(set(conditions) <= CONDITIONS and all(isinstance(v, list) and v for v in conditions.values()),
                f'{who}: invalid conditions')
        require(any(matches(facts, conditions) for facts in fixtures.values()), f'{who}: conditions cover no known fixture')

    require(spec['format_version'] == 1, 'unsupported contract format')
    require(not PRIVATE_PATH.search(json.dumps(spec)), 'private local path in specification')
    refs = spec['evidence']
    fixtures = {fixture_id(release, name): facts_for(release, history['scenarios'][release][name])
                for release, names in spec['trace_cases'].items() for name in names}
    ops, stages, regs, unknowns = (spec[key] for key in ('operations', 'stages', 'registers', 'uncertainties'))
    for items in (ops, stages, regs, refs, unknowns, spec['dependencies'], spec['branches'], spec['configuration_fields']):
        require(all(re.fullmatch(r'[a-z][a-z0-9.-]*', key) for key in items), 'invalid identifier')
    for key, stage in stages.items():
        require(all(stage[field] for field in ('input_state', 'observed_output', 'independent_constraint')),
                f'{key}: incomplete stage interface')
        cites(stage['evidence'], key)
    for key, ref in refs.items():
        require(ref['classification'] in EVIDENCE, f'{key}: invalid evidence classification')
        require(ref['classification'] != 'physical-observation' or
                ref['path'] == 'evidence/observations/OBS-001.json' and ref.get('pointer'),
                f'{key}: physical evidence requires an OBS-001 selection')
    require(spec['target'] == 'original RG35XX ATM7039S' and re.fullmatch(r'[0-9a-f]{40}', spec['source_research_revision']),
            'invalid target or research revision')
    rom = spec['interfaces']['rom']
    require(all(rom[key] is None for key in ('physical_pc', 'physical_sram_extent', 'physical_cpsr',
            'physical_sctlr', 'physical_vbar', 'physical_service_clobbers')), 'unsupported resolution of physical ROM input')
    for key, data in spec['firmware'].items():
        require(data['actual_sha256'] == history['firmware'][key]['actual_sha256'],
                f'{key}: incorrect firmware identity')
    require(spec['firmware'].keys() == history['firmware'].keys(), 'incomplete firmware identity set')
    for key, field in spec['configuration_fields'].items():
        cites(field['evidence'], key)
        require(field['width'] in (1, 2, 4) and field['offset'] >= 0, f'{key}: invalid field')
    for key, reg in regs.items():
        require(reg['space'] in ('mmio', 'pmic', 'sram') and reg['width'] in (1, 2, 4),
                f'{key}: register address space or access width invalid')
        cites(reg['evidence'], key)
    for key, op in ops.items():
        require(op['stage'] in stages, f'{key}: unknown stage')
        require(op['evidence_classification'] in EVIDENCE and op['confidence'] in ('anchored', 'supported', 'open'),
                f'{key}: invalid evidence class or confidence')
        require(op['implementation'] and set(op['implementation']) <= IMPLEMENTATION,
                f'{key}: invalid implementation classification')
        require(op['behavior'] and op['justification'] and op['model_assumptions'] is not None,
                f'{key}: incomplete operation definition')
        cites(op['evidence'], key)
        require(op['evidence_classification'] in {refs[e]['classification'] for e in op['evidence']},
                f'{key}: evidence does not support its classification')
        require(set(op['registers']) <= regs.keys() and
                set(op['configuration_fields']) <= spec['configuration_fields'].keys(), f'{key}: invalid operand reference')
        for check in op['checks']:
            when(check['when'], key)
            require(check['kind'] in ('event', 'boundary', 'state', 'supplemental'), f'{key}: invalid check kind')
            if check['kind'] != 'state':
                lo, hi = check['count']
                require(lo >= 0 and (hi is None or lo <= hi), f'{key}: invalid count')
                require(check['match'] and all(isinstance(v, list) and v for v in check['match'].values()),
                        f'{key}: invalid trace selector')
            if check['kind'] == 'event':
                sel = check['match']
                require(set(sel) <= VALID_EVENT_MATCH and {'pc', 'site', 'width', 'address', 'domain', 'op'} <= sel.keys(),
                        f'{key}: instruction address, bus address and width required for trace checks')
                for addr in sel['address']:
                    for width in sel['width']:
                        require(any(regs[reg]['space'] in sel['domain'] and (regs[reg]['address'], regs[reg]['width'])
                                    == (addr, width) for reg in op['registers']), f'{key}: access lacks register reference')

    # Ordering-only and unresolved relationships do not establish prerequisites.
    for key, edge in spec['dependencies'].items():
        require(edge['from'] in ops and edge['to'] in ops and edge['relation'] in RELATIONS and edge['why'],
                f'{key}: invalid dependency')
        require(edge['trace_order'] in (None, 'first-before-first', 'last-before-first'), f'{key}: bad order rule')
        when(edge['when'], key)
        cites(edge['evidence'], key)
    for fixture in fixtures.values():
        visiting, visited = set(), set()
        edges = defaultdict(list)
        for edge in spec['dependencies'].values():
            if edge['relation'] not in ('unresolved', 'ordering-only') and matches(fixture, edge['when']):
                edges[edge['from']].append(edge['to'])

        def walk(node):
            require(node not in visiting, f'dependency cycle at {node} for {fixture["scenario"]}')
            if node not in visited:
                visiting.add(node)
                for child in edges[node]:
                    walk(child)
                visiting.remove(node)
                visited.add(node)

        for node in ops:
            walk(node)
    for key, branch in spec['branches'].items():
        when(branch['when'], key)
        require(branch['requires'] and branch['forbids'], f'{key}: branch must define positive and negative states')
        require((set(branch['requires']) | set(branch['forbids'])) <= ops.keys() and
                not set(branch['requires']) & set(branch['forbids']), f'{key}: invalid branch operations')
        cites(branch['evidence'], key)
    for key, row in unknowns.items():
        require(row['status'] == 'open' and row['resolution'] is None, f'{key}: unsupported resolution')
        require(set(row['stages']) <= stages.keys() and row['stages'], f'{key}: invalid affected stages')
        require(set(row['blocks']) <= spec['profiles'].keys() and row['priority'] in (1, 2, 3, 4),
                f'{key}: invalid priority or blocked profile')
        require(row['earliest_profile_blocker'] == ('a' in row['blocks']), f'{key}: SRAM blocker inconsistent')
        require(all(row[k] for k in ('consequence', 'offline', 'future_observation', 'discriminates')),
                f'{key}: incomplete uncertainty')
        cites(row['evidence'], key)
    for key, profile in spec['profiles'].items():
        require(profile['blockers'] and set(profile['blockers']) ==
                {u for u, row in unknowns.items() if key in row['blocks']}, f'{key}: profile blockers inconsistent')
        require(set(profile['dependencies']) <= (spec['profiles'].keys() - {key}),
                f'{key}: invalid profile dependencies')
        require(all(profile[k] for k in ('maturity', 'prerequisites', 'validation', 'excluded', 'promotion')),
                f'{key}: incomplete profile')
    for retry in spec['retry_transitions']:
        require(retry['mode'] == 'cold' and retry['from_operation'] in ops and retry['to_operation'] in ops
                and retry['when'] and retry['bound'], 'invalid retry transition')
        cites(retry['evidence'], 'retry transition')
    return fixtures


def reconstruct_sram(events, base, before):
    data = bytearray.fromhex(before)
    stores = 0
    for _, count, event in events:
        addr, width = event['address'], event['width']
        if event['domain'] != 'sram' or event['op'] != 'w' or not base <= addr < base + len(data):
            continue
        start = addr - base
        if start + width > len(data):
            raise ValueError(f'SRAM store crosses record boundary at {addr:#x}')
        data[start:start + width] = event['value'].to_bytes(width, 'little')
        stores += count
    return data.hex(), stores


def check_handoff(key, case, events):
    result = case['result']
    dram = result['dram']
    if dram is not None:
        afi = dram['afi']
        afi_bytes, count = reconstruct_sram(events, 0xB4060300, afi['before'])
        if (afi_bytes, count) != (afi['bytes'], afi['stores']):
            raise ValueError(f'{key}: ordered AFI stores disagree with the final bytes or store count')
        final, _ = reconstruct_sram(events, 0xB406241C, dram['ini_initial']['primary'])
        if final != dram['ini_final']['primary']:
            raise ValueError(f'{key}: ordered INI stores disagree with the final record')
        for field in ('selector', 'secondary'):
            if dram['ini_initial'][field] != dram['ini_final'][field]:
                raise ValueError(f'{key}: unexpected cold or resume configuration side effect on {field}')
    if result['terminal']['outcome'] != 'linux-entry-boundary':
        return
    installed = state_of(result, 'uboot-entry')
    consumer = state_of(result, 'uboot-afi-and-ram')['afi']
    files = state_of(result, 'boot-files')
    dt = state_of(result, 'device-tree')
    jump = state_of(result, 'linux-entry')
    if (dram is None or dram['dram_return'] != '0x0' or not dram['afi']['generated'] or
            dram['terminal']['pc'] != '0xb4065440' or consumer['fallback_used'] or
            afi_bytes != installed['afi_exact_hex'] or afi_bytes != consumer['exact_hex'] or
            afi_bytes != dt['afi_in_memory']):
        raise ValueError(f'{key}: Linux handoff lacks a valid cold AFI transfer')
    if (consumer['gd_ram_size'] != dram['capacity_mib'] << 20 or
            dt['dt_memory_reg'] != ['0x0', hex(consumer['gd_ram_size'])] or
            int(jump['r2'], 16) != int(dt['ft_addr'], 16) or jump['pc'] != files['kernel']['entry'] or
            jump['r0'] != 0 or jump['mode'] != '0x13' or not jump['irq_fiq_masked'] or
            any(jump[field] for field in ('mmu', 'dcache', 'icache', 'thumb'))):
        raise ValueError(f'{key}: consumer memory bank, kernel entry or CPU state differs')
    if (dt['dt_chosen']['linux,initrd-start'] != [dt['initrd_start']] or
            dt['dt_chosen']['linux,initrd-end'] != [dt['initrd_end']]):
        raise ValueError(f'{key}: FDT initrd range differs from the prepared boot files')


def validate_trace(spec, trace, history):
    fixtures = check_structure(spec, history)
    if (trace['format_version'] != 1 or trace['fields'] != FIELDS
            or trace['source_evidence'] != HISTORY):
        raise ValueError('unsupported trace format')
    if set(fixtures) != trace['events'].keys() or set(fixtures) != trace['cases'].keys():
        raise ValueError('trace fixture coverage differs from the contract')
    if PRIVATE_PATH.search(json.dumps(trace)):
        raise ValueError('private local path in trace')
    startup = trace['startup_audit']
    if (startup['classification'] != 'static' or startup['runtime_relocation'] is not None or
            startup['runtime_reservations'] is not None or startup['payload_sha256'] !=
            spec['firmware'][startup['release']]['uboot_payload_sha256']):
        raise ValueError('incorrect U-Boot startup scope or provenance')
    checked = Counter()
    covered_edges = set()
    for key, facts in fixtures.items():
        release, name = key.split('/')
        expected = history['scenarios'][release][name]
        case = trace['cases'][key]
        rows = trace['events'][key]
        if (case['firmware_sha256'] != history['firmware'][release]['actual_sha256'] or
                case['historical_result_sha256'] != digest(expected) or case['result'] != select_result(expected)):
            raise ValueError(f'{key}: historical outcome or delivered state differs')
        if not rows or any(not isinstance(n, int) or n < 1 or len(row) != len(FIELDS) for n, row in rows):
            raise ValueError(f'{key}: bad RLE stream')
        for _, values in rows:
            _, domain, operation, address, width, value, pc, site, _, _ = values
            if (not all(isinstance(word, int) and 0 <= word <= 0xFFFFFFFF for word in (address, pc, site))
                    or domain not in ('mmio', 'pmic', 'sram', 'ram', 'storage')):
                raise ValueError(f'{key}: invalid event address or domain')
            if domain == 'storage':
                if operation != 'read' or width < 512 or width % 512 or not re.fullmatch('[a-f0-9]{64}', value):
                    raise ValueError(f'{key}: storage event must describe a hashed sector span')
            elif (operation not in ('r', 'w') or width not in (1, 2, 4, 8) or
                  (value is not None and (not isinstance(value, int) or not 0 <= value < 1 << (8 * width)))):
                raise ValueError(f'{key}: invalid observed access width or value')
        event_count = sum(n for n, _ in rows)
        if case['raw_trace'] != dict(events=event_count, sha256=digest(rows)):
            raise ValueError(f'{key}: raw trace integrity failure')
        # Later live or terminal snapshots independently bind the event prefix.
        prefix = max(historical_prefixes(expected), key=lambda p: p['events'], default=None)
        if prefix is not None:
            taken, remaining = [], prefix['events']
            for count, event in rows:
                if not remaining:
                    break
                kept = min(remaining, count)
                taken.append([kept, event])
                remaining -= kept
            if remaining or digest(taken) != prefix['sha256']:
                raise ValueError(f'{key}: ordered trace differs from historical execution prefix')
        indexes = [row[2] for row in case['boundaries']]
        supplements = [row['event_index'] for row in case['supplemental']]
        if any(seq != sorted(seq) or any(not 0 <= i <= event_count for i in seq) for seq in (indexes, supplements)):
            raise ValueError(f'{key}: invalid event index')
        events = list(indexed_events(rows))
        check_handoff(key, case, events)
        positions = {}
        for op_id, op in spec['operations'].items():
            for check in op['checks']:
                if matches(facts, check['when']):
                    pos = check_access(op_id, check, events, case['boundaries'], case['supplemental'], case['result'])
                    positions.setdefault(op_id, []).extend(pos)
                    checked[op_id] += 1
        for edge_id, edge in spec['dependencies'].items():
            if not edge['trace_order'] or not matches(facts, edge['when']):
                continue
            left = [value for value in positions.get(edge["from"], []) if value is not None]
            right = [value for value in positions.get(edge["to"], []) if value is not None]
            if not left or not right:
                raise ValueError(f'{key}: missing operation for ordered dependency {edge_id}')
            antecedent = max(left) if edge['trace_order'] == 'last-before-first' else min(left)
            if antecedent > min(right):
                raise ValueError(f'{key}: swapped ordering for {edge_id}')
            covered_edges.add(edge_id)
        active = [branch for branch in spec['branches'].values() if matches(facts, branch['when'])]
        if len(active) != 1:
            raise ValueError(f'{key}: expected exactly one terminal branch, got {len(active)}')
        for op_id in active[0]['requires']:
            if not positions.get(op_id):
                raise ValueError(f'{key}: terminal branch missing {op_id}')
        for op_id in active[0]['forbids']:
            if positions.get(op_id):
                raise ValueError(f'{key}: terminal branch reached forbidden {op_id}')
    for op_id, op in spec['operations'].items():
        if op['checks'] and not checked[op_id]:
            raise ValueError(f'{op_id}: operation covered by no trace')
    return dict(cases=len(fixtures), operations=len(checked), checks=sum(checked.values()),
                checked_ordered_dependencies=len(covered_edges))


def select_result(run):
    stages = {}
    for name, row in run['stages'].items():
        if name in ('mmc-registration', 'boot-device', 'boot-files', 'device-tree',
                    'linux-entry', 'uboot-entry', 'uboot-afi-and-ram', 'boot-rom-boundary',
                    'recovery-resume-decision'):
            stages[name] = row
        else:
            stages[name] = {k: v for k, v in row.items() if k != 'state'}
    return dict(terminal=run['terminal'], stages=stages, storage_reads=run['storage_reads'],
                warning=run['diagnostic_warning'], dram=run.get('dram_result'), reentry=run.get('rom_reentry'),
                SFVD_write_requests=run['app_write_requests'], persistent_environment=run.get('persistent_environment'))


def historical_prefixes(run):
    for row in run['stages'].values():
        machine = row.get('state', {}).get('machine', {})
        if 'trace' in machine:
            yield machine['trace']
    if run.get('dram_result'):
        yield run['dram_result']['trace']
    if run.get('rom_reentry'):
        yield run['rom_reentry']['machine']['trace']


def replay(root, spec, directory):
    # Keep ordinary schema checks runnable with stdlib, including on systems
    # without the optional ARM/FAT execution dependencies.
    from unicorn import UC_HOOK_MEM_WRITE
    import ddr_emulate as ddr
    import unified_boot_chain as fw

    class TraceLoader(fw.Loader):
        def __init__(self, *args):
            self.supplemental = []
            super().__init__(*args)
            for address in (0xB4064C00, 0xB4060018):
                self.uc.hook_add(UC_HOOK_MEM_WRITE, self._record_store, begin=address, end=address + 3)

        def _note(self, kind, pc, **fields):
            self.supplemental.append(dict(kind=kind, event_index=self.ordered.count, pc=pc, **fields))

        def _record_store(self, uc, access, address, width, value, user):
            self._note('sram-write', self.reg('pc'), address=address, width=width, value=value)

        def _code(self, uc, address, size, user):
            if self.insns - self.budget_start < self.budget:
                if address == ddr.F_DELAY:
                    method = 'executed timer poll' if self.window in ('early', 'app') else 'delay stub'
                    self._note('delay-us', address, site=self.reg('lr') - 4, value=self.reg('r0'), method=method)
                elif address == 0xB4065F88:
                    self._note('cpu-control-write', address, register='sctlr', value=self.reg('r0'))
                elif address == 0xB406921C:
                    self._note('cpu-control-write', address, register='vbar', value=self.reg('r1'))
                elif address == 0x1014 and self.window == 'app':
                    self._note('cpu-control-write', address, register='cpsr', value=self.reg('r0'))
            super()._code(uc, address, size, user)

    class Execution(fw.Execution):
        loader_type = TraceLoader

    history = read(root / HISTORY)
    doc = dict(format_version=1, fields=FIELDS, tool='tools/bootloader_contract.py', cases={}, events={},
               source_evidence=HISTORY,
               boundary_note='Only the loader through U-Boot entry has one live ordered hook stream. '
               'Downstream stages carry distinct historical state envelopes and their own execution methods. '
               'Supplemental instruction anchors are indexed into the loader stream. Scope ends before Linux executes.')
    for release, names in spec['trace_cases'].items():
        with fw.Release(directory, release) as source:
            if release == fw.REFERENCE:
                meta = history['scenarios'][release]['sd2-reference']['stages']['uboot-entry']['state']['uboot']
                doc['startup_audit'] = audit_startup(source.disk, meta)
            for name in names:
                key = fixture_id(release, name)
                run = Execution(source.disk, source.loader, source.identity, fw.SCENARIO_BY_NAME[name], True)
                result = run.run()
                historical = history['scenarios'][release][name]
                # Round-trip JSON types before comparing. Numeric PMIC map keys
                # and tuple members have JSON string and list representations.
                compact = json.loads(json.dumps(fw.compact_run(result)))
                if compact != historical:
                    different = sorted(k for k in compact.keys() | historical.keys()
                                       if digest(compact.get(k)) != digest(historical.get(k)))
                    raise ValueError(f'{key}: fresh execution differs from the historical summary in {different}')
                detail = result['trace_detail']
                if list(detail['fields']) != FIELDS:
                    raise ValueError(f'{key}: upstream trace fields changed')
                rows = detail['events']
                doc['events'][key] = rows
                doc['cases'][key] = dict(
                    firmware_sha256=source.identity['actual_sha256'],
                    historical_result_sha256=digest(historical), result=select_result(historical),
                    raw_trace=run.loader.ordered.summary(),
                    boundaries=[[b['phase'], int(b['pc'], 16), b['event_index']] for b in detail['boundaries']],
                    supplemental=run.loader.supplemental)
                del run, result, detail
                gc.collect()
    return doc


def audit_startup(disk, meta):
    """Verify narrow startup landmarks against the pinned Koriki binary."""
    import boot_chain as boot
    size = meta['size'] + 64
    data = disk.sectors(boot.UBOOT_DISK // 512, (size + 511) // 512)[64:size]
    if digest_bytes(data) != meta['payload_sha256']:
        raise ValueError('startup audit needs the verified U-Boot payload')
    ub = boot.Blob(data, meta['entry'], 'U-Boot')
    anchors = {
        0x05000040: ('b', '#0x5000300', 'entry branches to reset stub'),
        0x05000350: ('b', '#0x5000304', 'reset stub reaches CPU setup'),
        0x0500031C: ('msr', 'cpsr_fc, r0', 'mode and IRQ/FIQ mask update'),
        0x05000330: ('mcr', 'p15, #0, r0, c12, c0, #0', 'initial VBAR write'),
        0x050003B0: ('ldr', 'sp, [pc, #0x18]', 'first local stack load'),
        0x050036B4: ('ldr', 'sp, [pc, #0x88]', 'reloads initial stack for startup frame'),
        0x050036C0: ('sub', 'sp, sp, #0xa8', 'subtracts 168 bytes before zero fill'),
        0x050036C8: ('mov', 'sb, sp', 'r9 receives startup data pointer'),
        0x050036E8: ('ldr', 'sp, [sb, #0x40]', 'later stack pointer comes from computed runtime state'),
        0x05003704: ('ldr', 'r0, [sb, #0x30]', 'relocation destination comes from runtime state'),
        0x05003758: ('mcr', 'p15, #0, r0, c12, c0, #0', 'VBAR written from computed address'),
        0x05003774: ('stm', 'r0!, {sl, fp}', 'relocation copy writes two words per iteration'),
        0x05003790: ('cmp', 'r1, #0x17', 'filters relocation records for type 23 (R_ARM_RELATIVE)'),
    }
    for pc, (mnemonic, operands, _) in anchors.items():
        ins, = boot.disasm(ub, pc, 1)
        if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError(f'changed static U-Boot startup instruction at {pc:#x}')
    literals = {0x050003AC: 0x05000040, 0x050003D0: 0x050FFFF0, 0x05003744: 0x050FFFF0,
                0x050037B4: 0x05000040, 0x050037B8: 0x050A0790,
                0x050037BC: 0x050A0790, 0x050037C0: 0x050AD5E0}
    if any(ub.word(address) != word for address, word in literals.items()):
        raise ValueError('changed static U-Boot startup literal')
    return dict(classification='static', release='koriki-v1.0', payload_sha256=meta['payload_sha256'],
                anchors={hex(pc): row[2] for pc, row in anchors.items()},
                literals={hex(address): hex(word) for address, word in literals.items()},
                runtime_relocation=None, runtime_reservations=None)


def render_reference(contract):
    rows = ['# Bootloader operation and dependency reference', '',
            'Generated by `tools/bootloader_contract.py` from the curated specification. '
            'Widths are bytes. Names denote evidence-backed labels and may have related-chip scope.',
            '', '[Engineering specification](bootloader-initialization-contract.md) · '
            '[Ordered events](../evidence/firmware/boot-initialization-trace.json)', '']
    rows += ['## Operation anchors', '',
             '| Operation | Stage | Function entry | Instruction or call site | Implementation |',
             '|---|---|---|---|---|']
    for key, row in sorted(contract['operations'].items()):
        sites = sorted({site for check in row['checks'] if check['kind'] in ('event', 'supplemental')
                        for site in check['match'].get('site', check['match'].get('pc', []))})
        if 'stock_call_site' in row:
            sites = sorted({*sites, row['stock_call_site']})
        anchors = ', '.join(f'`{site:#010x}`' for site in sites) or '—'
        fn = f'`{row["function_address"]:#010x}`' if row['function_address'] is not None else '—'
        rows.append(f'| `{key}` | {row["stage"]} | {fn} | {anchors} | {", ".join(row["implementation"])} |')
    rows += ['', '## Register references', '',
             '| Identifier | Address or index | Space | Width | Catalogue IDs |', '|---|---|---|---:|---|']
    for key, reg in sorted(contract['registers'].items(), key=lambda item: (item[1]['space'], item[1]['address'])):
        catalogue = ', '.join(f'`{item}`' for item in reg['catalogue_ids'])
        if reg.get('related_source_name'):
            catalogue = f'ATC2603C source: `{reg["related_source_name"]}`'
        catalogue = catalogue or 'Firmware evidence'
        rows.append(f'| `{key}` | `{reg["address"]:#x}` | {reg["space"]} | {reg["width"]} | {catalogue} |')
    rows += ['', '## Dependencies', '',
             '| From | To | Relationship | When | Justification |', '|---|---|---|---|---|']
    for row in contract['dependencies'].values():
        cond = ', '.join(f'{key}={json.dumps(values, separators=(",", ":"))}' for key, values in row['when'].items())
        rows.append(f'| `{row["from"]}` | `{row["to"]}` | {row["relation"]} | {cond or "all paths"} | {row["why"]} |')
    return ('\n'.join(rows) + '\n').encode('utf-8')


def check_generated(root):
    spec = read(root / INPUT)
    contract = build_contract(root, spec)
    if formatted(contract) != (root / CONTRACT).read_bytes():
        raise ValueError(f'{CONTRACT} is stale')
    if render_reference(contract) != (root / REFERENCE).read_bytes():
        raise ValueError(f'{REFERENCE} is stale')
    trace = read(root / TRACE)
    if trace_bytes(trace) != (root / TRACE).read_bytes():
        raise ValueError(f'{TRACE} is not canonical')
    return validate_trace(contract, trace, read(root / HISTORY))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', choices=('generate', 'validate', 'replay', 'compare'))
    cli.add_argument('--firmware-dir', type=Path, default=os.environ.get('ATM_FIRMWARE_DIR'))
    cli.add_argument('--check', action='store_true', help='for replay, compare the new timeline byte for byte')
    args = cli.parse_args()
    try:
        spec = read(ROOT / INPUT)
        contract = build_contract(ROOT, spec)
        history = read(ROOT / HISTORY)
        if args.mode == 'generate':
            check_structure(contract, history)
            (ROOT / CONTRACT).write_bytes(formatted(contract))
            (ROOT / REFERENCE).write_bytes(render_reference(contract))
        elif args.mode == 'validate':
            print(json.dumps(check_generated(ROOT), sort_keys=True))
        elif args.mode == 'compare':
            print(json.dumps({name: {'config': row['config'], 'reference_dram': {
                key: history['scenarios'][name]['sd2-reference']['dram_result'][key]
                for key in ('record_selection', 'record_final', 'capacity_mib')}}
                for name, row in contract['firmware'].items()}, indent=2))
        else:
            if not args.firmware_dir:
                cli.error('replay requires --firmware-dir or ATM_FIRMWARE_DIR')
            timeline = replay(ROOT, contract, args.firmware_dir)
            stats = validate_trace(contract, timeline, history)
            content = trace_bytes(timeline)
            if args.check:
                if (ROOT / TRACE).read_bytes() != content:
                    raise ValueError(f'{TRACE} differs from verified replay')
            else:
                from unified_boot_chain import write_json_output
                write_json_output(ROOT / TRACE, args.firmware_dir, content)
            print(json.dumps(stats, sort_keys=True))
    except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
        cli.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
