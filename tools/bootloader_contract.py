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
# Boundary restrictions live in an explicit check-level ``window``; selectors match event fields only.
VALID_EVENT_MATCH = set(FIELDS)
TRACE_ORDERS = (None, 'last-before-first', 'first-before-first', 'per-attempt')
STATE_ROLES = {'execution', 'value', 'absence'}
OCCURRENCES = {'only', 'first', 'last'}
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


class Observation:
    """Outcome of one successful check.

    ``execution_positions`` holds trace positions on a doubled scale: event ``i``
    is ``2*i + 1`` and a boundary or supplemental anchor at event count ``b`` is
    ``2*b``, so an anchor recorded before event ``b`` orders strictly before it.
    A passing absence or value assertion never contributes execution evidence."""
    __slots__ = ('assertion_passed', 'execution_positions', 'state_execution', 'absence_confirmed', 'role', 'check')

    def __init__(self, role, positions=(), state_execution=False, absence_confirmed=False):
        self.assertion_passed = True
        self.role = role
        self.execution_positions = list(positions)
        self.state_execution = state_execution
        self.absence_confirmed = absence_confirmed
        self.check = None

    @property
    def execution_observed(self):
        return bool(self.execution_positions) or self.state_execution


def event_position(index):
    return 2 * index + 1


def anchor_position(index):
    return 2 * index


def resolve_boundary(rule, boundaries, who):
    """Index of the boundary a window names. Missing or ambiguous boundaries fail closed."""
    hits = [index for phase, pc, index in boundaries
            if phase == rule['phase'] and ('pc' not in rule or pc == rule['pc'])]
    occurrence = rule['occurrence']
    if not hits:
        if 'else' in rule:
            return resolve_boundary(rule['else'], boundaries, who)
        raise ValueError(f"{who}: required boundary {rule['phase']} is absent")
    if occurrence == 'only':
        if len(hits) != 1:
            raise ValueError(f"{who}: boundary {rule['phase']} occurs {len(hits)} times; window is ambiguous")
        return hits[0]
    if occurrence == 'first':
        return hits[0]
    if occurrence == 'last':
        return hits[-1]
    if not 1 <= occurrence <= len(hits):
        raise ValueError(f"{who}: boundary {rule['phase']} occurrence {occurrence} is absent")
    return hits[occurrence - 1]


def window_of(check, boundaries, who):
    window = check.get('window') or {}
    lower = resolve_boundary(window['after'], boundaries, who) if 'after' in window else 0
    upper = resolve_boundary(window['before'], boundaries, who) if 'before' in window else None
    if upper is not None and lower > upper:
        raise ValueError(f'{who}: window boundaries are reversed ({lower} > {upper})')
    return lower, upper


def select_events(rows, selector, window=(0, None)):
    """Matching events clipped to ``[lower, upper)``. RLE runs that straddle a
    boundary contribute only the repetitions inside the window."""
    lower, upper = window
    access = {k: v for k, v in selector.items() if k in FIELDS}
    out = []
    for start, count, event in rows:
        first = max(start, lower)
        last = start + count if upper is None else min(start + count, upper)
        if first < last and event_matches(event, access):
            out.append((first, last - first, event))
    return out


def find_events(rows, checks, boundaries, window=None):
    """Compatibility wrapper: explicit window or the whole stream."""
    return select_events(rows, checks, window or (0, None))


def check_access(operation, check, rows, boundaries, supplemental, result):
    selector = check['match'] if check['kind'] != 'state' else None
    count, positions = 0, []
    if check['kind'] == 'boundary':
        positions = [anchor_position(index) for phase, pc, index in boundaries
                     if event_matches({'phase': phase, 'pc': pc}, selector)]
        count = len(positions)
    elif check['kind'] == 'supplemental':
        positions = [anchor_position(e['event_index']) for e in supplemental if event_matches(e, selector)]
        count = len(positions)
    elif check['kind'] == 'state':
        actual = result
        for key in check['path']:
            actual = actual[key]
        if actual != check['equals']:
            raise ValueError(f"{operation}: {check['path']} was {actual!r}, expected {check['equals']!r}")
        role = check['role']
        if role == 'execution':
            status = result['stages'][check['stage']]['status']
            if status not in check['stage_status']:
                raise ValueError(f"{operation}: execution state claimed from stage {check['stage']} with status {status}")
            return Observation(role, state_execution=True)
        if role == 'absence':
            return Observation(role, absence_confirmed=True)
        return Observation(role)
    else:
        window = window_of(check, boundaries, operation)
        selected = select_events(rows, selector, window)
        positions = [event_position(i) for start, n, _ in selected for i in range(start, start + n)]
        count = sum(n for _, n, _ in selected)
        if 'rmw' in check:
            rmw = check['rmw']
            preceding = select_events(rows, rmw['read'], window)
            for start, n, event in selected:
                before = [row for row in preceding if row[0] < start]
                prior = before[-1] if before else None
                if (n != 1 or prior is None or prior[2]['address'] != event['address'] or
                        prior[2]['width'] != event['width'] or prior[2]['domain'] != event['domain'] or
                        (prior[2]['value'] & ~rmw['clear'] | rmw['set']) != event['value']):
                    raise ValueError(f'{operation}: RMW mismatch at event {start}')
    lo, hi = check['count']
    if count < lo or (hi is not None and count > hi):
        raise ValueError(f'{operation}: {check["kind"]} match {selector}: count {count}, expected {lo}..{hi}')
    if hi == 0:
        # Excludes one access pattern. Only an explicit absence role confirms the
        # operation itself did not run.
        role = check.get('role', 'exclusion')
        return Observation(role, absence_confirmed=role == 'absence')
    return Observation('execution', positions)


def anchors(op, rows, boundaries, supplemental, result):
    """Presence of an operation regardless of scenario conditions: positive trace
    selectors anywhere in the stream, or a completed stage named by an execution-
    role state check. Used to reject forbidden operations."""
    found = []
    for check in op['checks']:
        if check['kind'] == 'state':
            if check['role'] == 'execution' and result['stages'][check['stage']]['status'] in check['stage_status']:
                found.append(None)
            continue
        if check['count'][0] < 1:
            continue
        sel = check['match']
        if check['kind'] == 'boundary':
            found += [anchor_position(i) for phase, pc, i in boundaries if event_matches({'phase': phase, 'pc': pc}, sel)]
        elif check['kind'] == 'supplemental':
            found += [anchor_position(e['event_index']) for e in supplemental if event_matches(e, sel)]
        else:
            found += [event_position(i) for start, n, _ in select_events(rows, sel) for i in range(start, start + n)]
    return found


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
    result_stages = set(next(iter(next(iter(history['scenarios'].values())).values()))['stages'])
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
        require(field['record'] in ('ini', 'working-dram-record') and field['meaning'], f'{key}: invalid record')
        require(isinstance(field['reference'], list) and field['reference'] and
                all(row['releases'] and set(row['releases']) <= spec['firmware'].keys() for row in field['reference']),
                f'{key}: reference values must name releases')
        if field['record'] == 'working-dram-record':
            require(field['endianness'] == 'little' and field['ini_slot_width'] in (1, 4) and
                    set(field['ini_offsets']) == {'primary', 'secondary'} and
                    field['ini_offsets']['secondary'] - field['ini_offsets']['primary'] == 0x30,
                    f'{key}: working field needs little-endian primary/secondary INI placement')
            require(all({'primary', 'secondary'} <= row.keys() for row in field['reference']),
                    f'{key}: working reference needs primary and secondary values')
        else:
            require(all('value' in row for row in field['reference']), f'{key}: INI reference needs a value')
    sem = spec['semantics']
    require({'dram-bus', 'dram-rank', 'dram-retry', 'dram-capacity', 'dram-timing'} <= sem.keys(),
            'missing structured DRAM semantics')
    for key, block in sem.items():
        cites(block['evidence'], f'semantics.{key}')
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
            if check['kind'] == 'state':
                require(check['role'] in STATE_ROLES, f'{key}: state check needs a role')
                if check['role'] == 'execution':
                    require(check['stage'] in result_stages and check['stage_status'] and
                            set(check['stage_status']) <= {'completed', 'terminal'} and check['equals'] is not None,
                            f'{key}: execution state needs a positive predicate from a named stage')
                if check['role'] == 'absence':
                    require(check['path'] == ['stages', check['stage'], 'status'] and
                            check['equals'] not in ('completed', 'terminal'),
                            f'{key}: absence must assert a stage that did not run')
            require('window' not in check or check['kind'] == 'event', f'{key}: only event checks take a window')
            for side, rule in (check.get('window') or {}).items():
                require(side in ('after', 'before'), f'{key}: invalid window side')
                while rule is not None:
                    require(rule['phase'] and (rule['occurrence'] in OCCURRENCES or
                            isinstance(rule['occurrence'], int) and rule['occurrence'] >= 1),
                            f'{key}: window boundary needs a phase and explicit occurrence')
                    rule = rule.get('else')
            if check['kind'] != 'state':
                lo, hi = check['count']
                require(lo >= 0 and (hi is None or lo <= hi), f'{key}: invalid count')
                require(check['match'] and all(isinstance(v, list) and v for v in check['match'].values()),
                        f'{key}: invalid trace selector')
            if check['kind'] == 'event':
                sel = check['match']
                require(set(sel) <= VALID_EVENT_MATCH and {'pc', 'site', 'width', 'address', 'domain', 'op'} <= sel.keys(),
                        f'{key}: instruction address, bus address and width required for trace checks')
                if sel['domain'] == ['storage']:
                    transfers = {(r['start'], r['end'] - r['start']) for r in spec['interfaces']['sram-layout']['ranges']
                                 if r['basis'] == 'observed-transfer'}
                    require(all((a, w) in transfers for a in sel['address'] for w in sel['width']),
                            f'{key}: storage access must match a declared observed-transfer range')
                    continue
                for addr in sel['address']:
                    for width in sel['width']:
                        require(any(regs[reg]['space'] in sel['domain'] and (regs[reg]['address'], regs[reg]['width'])
                                    == (addr, width) for reg in op['registers']), f'{key}: access lacks register reference')

    # Ordering-only and unresolved relationships do not establish prerequisites.
    for key, edge in spec['dependencies'].items():
        require(edge['from'] in ops and edge['to'] in ops and edge['relation'] in RELATIONS and edge['why'],
                f'{key}: invalid dependency')
        require(edge['trace_order'] in TRACE_ORDERS, f'{key}: bad order rule')
        require((edge['trace_order'] == 'first-before-first') == bool(edge.get('occurrence_justification')) and
                (edge['trace_order'] != 'first-before-first' or
                 not {ops[edge['from']]['stage'], ops[edge['to']]['stage']} & {'dram', 'resume'}),
                f'{key}: first-occurrence ordering needs a justification and cannot span DRAM attempts')
        require(edge['trace_order'] != 'per-attempt' or {ops[edge['from']]['stage'], ops[edge['to']]['stage']} <=
                {'dram', 'resume'}, f'{key}: per-attempt ordering applies to DRAM attempt operations only')
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
        require(set(branch['confirm_absent']) <= set(branch['forbids']), f'{key}: confirmed absence must be forbidden')
        require(('linux-entry' in branch['requires']) != ('linux-entry' in branch['confirm_absent']),
                f'{key}: every terminal branch must require Linux entry or confirm its absence')
        cites(branch['evidence'], key)
    attempts = spec['attempts']
    cites(attempts['evidence'], 'attempts')
    require(set(attempts['required']) == {'all'} | attempts['outcomes'].keys() and
            set(attempts['forbidden']) == attempts['outcomes'].keys(), 'attempt outcome rules incomplete')
    for outcome, names in list(attempts['required'].items()) + list(attempts['forbidden'].items()):
        require(set(names) <= ops.keys() and all(ops[n]['stage'] in ('dram', 'resume') for n in names),
                f'attempts.{outcome}: unknown or non-DRAM operation')
    for outcome in attempts['outcomes']:
        require(not set(attempts['required'][outcome]) & set(attempts['forbidden'][outcome]),
                f'attempts.{outcome}: operation both required and forbidden')
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
        require(retry['mode'] == sem['dram-retry']['mode'] == 'cold' and retry['from_operation'] == 'train' and
                retry['to_operation'] in ops and retry['when'] and retry['bound'],
                'retry transitions must start from the training error the firmware retries')
        cites(retry['evidence'], 'retry transition')
    afi = spec['interfaces']['afi']
    require(afi['required_by_linux'] is False, 'AFI must not be described as a Linux requirement')
    cites(afi['consumer']['evidence'], 'interfaces.afi.consumer')
    for row in spec['interfaces']['sram-layout']['ranges']:
        cites(row['evidence'], f"sram {row['id']}")
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


def check_handoff(key, case, events, spec=None):
    result = case['result']
    dram = result['dram']
    address = spec['interfaces']['afi']['address'] if spec else 0xB4060300
    if dram is not None:
        afi = dram['afi']
        afi_bytes, count = reconstruct_sram(events, address, afi['before'])
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
    import contract_semantics as semantics
    stats = Counter()
    semantic = semantics.check_dram_semantics(spec)
    semantic.update(configuration_checks=semantics.check_configuration(spec, history, trace),
                    afi_checks=semantics.check_afi(spec, trace, history),
                    sram_checks=semantics.check_sram(spec, trace),
                    timing_checks=semantics.check_timing(spec, trace),
                    linux_handoff_checks=semantics.check_linux_handoff(spec, trace))
    static_verified = semantics.check_static_operations(spec, trace)
    checked = Counter()
    observed, state_only, absent = set(), set(), set()
    covered_edges, attempt_edges = set(), set()
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
        check_handoff(key, case, events, spec)
        semantics.check_afi_stores(spec['interfaces']['afi'], key, events)
        found, positions, executed, confirmed_absent = case_observations(spec, facts, case, events, checked)
        observed |= {op for op in executed if positions[op]}
        state_only |= {op for op in executed if not positions[op]}
        absent |= confirmed_absent
        for op_id in executed & confirmed_absent:
            raise ValueError(f'{key}: {op_id} is both observed and confirmed absent')
        for edge_id, edge in spec['dependencies'].items():
            if edge['trace_order'] not in ('last-before-first', 'first-before-first') or not matches(facts, edge['when']):
                continue
            left, right = positions.get(edge['from'], []), positions.get(edge['to'], [])
            if not left or not right:
                raise ValueError(f'{key}: missing operation for ordered dependency {edge_id}')
            if (max(left) if edge['trace_order'] == 'last-before-first' else min(left)) > min(right):
                raise ValueError(f'{key}: swapped ordering for {edge_id}')
            covered_edges.add(edge_id)
        attempt_edges |= check_attempts(spec, key, facts, case, events, positions, found)
        stats['attempts'] += sum(1 for b in case['boundaries'] if b[0] == spec['attempts']['start_boundary']['phase'])
        stats['absence_confirmations'] += check_branch(spec, key, facts, case, events, executed, confirmed_absent)
    for op_id, op in spec['operations'].items():
        if op['checks'] and not checked[op_id]:
            raise ValueError(f'{op_id}: operation covered by no trace')
    edges = spec['dependencies'].values()
    return dict(
        cases=len(fixtures), operations=len(checked), checks=sum(checked.values()),
        checked_ordered_dependencies=len(covered_edges), per_attempt_dependencies=len(attempt_edges),
        dram_attempts=stats['attempts'], absence_confirmations=stats['absence_confirmations'],
        operation_definitions=len(spec['operations']),
        operations_observed_in_trace=len(observed), operations_state_only=len(state_only - observed),
        operations_checked_without_execution=sorted(set(checked) - observed - state_only),
        operations_confirmed_absent=len(absent),
        operations_without_checks=sorted(k for k, op in spec['operations'].items() if not op['checks']),
        operations_static_verified=static_verified,
        operations_unverified=sorted(k for k, op in spec['operations'].items()
                                     if not op['checks'] and k not in static_verified),
        dependencies=len(spec['dependencies']),
        dependencies_without_trace_order=sum(1 for e in edges if e['trace_order'] is None),
        dependencies_unresolved=sum(1 for e in edges if e['relation'] == 'unresolved'),
        semantics=semantic)


def case_observations(spec, facts, case, events, checked=None):
    """Run every applicable check: observations, execution positions, executed and confirmed-absent sets."""
    found = defaultdict(list)
    for op_id, op in spec['operations'].items():
        for check in op['checks']:
            if matches(facts, check['when']):
                obs = check_access(op_id, check, events, case['boundaries'], case['supplemental'], case['result'])
                obs.check = check
                found[op_id].append(obs)
                if checked is not None:
                    checked[op_id] += 1
    positions = {op: sorted(p for o in obs for p in o.execution_positions) for op, obs in found.items()}
    executed = {op for op, obs in found.items() if any(o.execution_observed for o in obs)}
    confirmed_absent = {op for op, obs in found.items() if any(o.absence_confirmed for o in obs)}
    return found, positions, executed, confirmed_absent


def check_branch(spec, key, facts, case, events, executed, confirmed_absent):
    active = [branch for branch in spec['branches'].values() if matches(facts, branch['when'])]
    if len(active) != 1:
        raise ValueError(f'{key}: expected exactly one terminal branch, got {len(active)}')
    branch = active[0]
    dram = case['result']['dram']
    if (dram['terminal']['pc'] if dram else None) != branch['dram_terminal_pc']:
        raise ValueError(f'{key}: terminal branch expects DRAM terminal {branch["dram_terminal_pc"]}')
    for op_id in branch['requires']:
        if op_id not in executed:
            raise ValueError(f'{key}: terminal branch missing {op_id}')
    for op_id in branch['forbids']:
        if op_id in executed or anchors(spec['operations'][op_id], events, case['boundaries'],
                                        case['supplemental'], case['result']):
            raise ValueError(f'{key}: terminal branch reached forbidden {op_id}')
    for op_id in branch['confirm_absent']:
        if op_id not in confirmed_absent:
            raise ValueError(f'{key}: terminal branch lacks a positive absence check for {op_id}')
    return len(branch['confirm_absent'])


def attempt_intervals(spec, case):
    """Attempt identities and event intervals from the executed boundary stream."""
    cfg = spec['attempts']
    start = cfg['start_boundary']
    bounds = case['boundaries']
    out = []
    for pos, (phase, pc, index) in enumerate(bounds):
        if phase != start['phase'] or pc != start['pc']:
            continue
        end, inner = None, []
        for later_phase, _, later in bounds[pos + 1:]:
            if later_phase in cfg['end_phases']:
                end = later
                break
            inner.append(later_phase)
        out.append(dict(number=len(out) + 1, start=index, end=end, phases=inner))
    return out


def check_attempts(spec, key, facts, case, events, positions, found=None):
    """Per-attempt operation order, required/forbidden operations and retry transitions."""
    import contract_semantics as semantics
    cfg = spec['attempts']
    sem = spec['semantics']
    dram = case['result']['dram']
    intervals = attempt_intervals(spec, case)
    if not intervals:
        return set()
    total = sum(n for _, n, _ in events)
    covered = set()
    observed = []
    for attempt in intervals:
        lo, hi = 2 * attempt['start'], 2 * (attempt['end'] if attempt['end'] is not None else total)
        inside = {op: [p for p in ps if lo <= p < hi] for op, ps in positions.items()}
        anchor_inside = {op: [p for p in anchors(spec['operations'][op], events, case['boundaries'], case['supplemental'],
                                                 case['result']) if p is not None and lo <= p < hi]
                         for op in {n for names in cfg['forbidden'].values() for n in names}}
        phases = attempt['phases']
        if 'training-dterr' in phases:
            outcome = 'training-error'
        elif 'training-passed' in phases:
            outcome = 'trained'
        elif 'controller-phy-programmed' not in phases:
            outcome = 'programming-failure'
        elif dram['terminal'].get('known_poll'):
            outcome = 'unbounded-poll'
        else:
            raise ValueError(f'{key}: attempt {attempt["number"]} has no classifiable outcome')
        who = f'{key} attempt {attempt["number"]} ({outcome})'
        for op in cfg['required']['all'] + cfg['required'][outcome]:
            if not inside.get(op):
                raise ValueError(f'{who}: required operation {op} absent')
            # Unbounded access checks describe accesses repeated by every attempt.
            for obs in (found or {}).get(op, []):
                check = obs.check
                if (check['kind'] == 'event' and check['count'][0] >= 1 and check['count'][1] is None and
                        not any(lo <= p < hi for p in obs.execution_positions)):
                    raise ValueError(f"{who}: required operation {op} lacks access at site "
                                     f"{check['match']['site'][0]:#x} in this attempt")
        for op in cfg['forbidden'][outcome]:
            if inside.get(op) or anchor_inside[op]:
                raise ValueError(f'{who}: forbidden operation {op} present')
        for edge_id, edge in spec['dependencies'].items():
            if edge['trace_order'] != 'per-attempt' or not matches(facts, edge['when']):
                continue
            left, right = inside.get(edge['from'], []), inside.get(edge['to'], [])
            if right and not left:
                raise ValueError(f'{who}: {edge["to"]} without prerequisite {edge["from"]} ({edge_id})')
            if left and right:
                if max(left) > min(right):
                    raise ValueError(f'{who}: swapped ordering for {edge_id}')
                covered.add(edge_id)
        config = {}
        for name, rule in cfg['configuration'].items():
            words = [e['value'] for start, n, e in events if lo <= 2 * start + 1 < hi and e['op'] == 'w' and
                     e['address'] == rule['address'] and e.get('site') == rule['site']]
            if len(words) > 1:
                raise ValueError(f'{who}: {name} programmed {len(words)} times')
            if words:
                config[name] = (rule['values'][f'{words[0]:#x}'] if 'values' in rule else
                                rule['set'] if words[0] >> rule['bit'] & 1 else rule['clear'])
        observed.append(dict(outcome=outcome, config=config))
    training = [a for a in observed if a['outcome'] in ('training-error', 'trained')]
    if [(a['config'].get('ranks'), a['config'].get('width_bits'), a['outcome']) for a in training] != [
            (t['ranks'], t['width_bits'], 'trained' if t['pgsr_response'] == '0x1f' else 'training-error')
            for t in dram['training']]:
        raise ValueError(f'{key}: attempt configuration or outcome differs from the recorded training results')
    for attempt in observed[:-1]:
        if attempt['outcome'] != 'training-error':
            raise ValueError(f'{key}: retry after a non-retryable {attempt["outcome"]} attempt')
    if facts['mode'] != 'cold':
        if len(observed) != 1:
            raise ValueError(f'{key}: resume attempts must not retry')
        return covered
    # Predict the cold sequence from the input record and the structured retry rules.
    selection = dram['record_selection']
    raw = bytes.fromhex(dram['ini_initial'][selection])
    base = semantics.INI_RECORD_BASES[selection]
    fields = spec['configuration_fields']
    bus_in = raw[fields['dram-bus']['ini_offsets'][selection] - base]
    cs_in = raw[fields['dram-cs']['ini_offsets'][selection] - base]
    outcomes = iter(a['outcome'] == 'trained' for a in observed)
    calls = []

    def trains(ranks, width):
        calls.append((ranks, width))
        result = next(outcomes, None)
        if result is None:
            raise ValueError(f'{key}: structured retry rules predict attempt {len(calls)} which did not execute')
        return result

    if observed[-1]['outcome'] in ('training-error', 'trained'):
        predicted = semantics.attempts(sem, bus_in, cs_in, trains)
        if len(predicted['attempts']) != len(observed):
            raise ValueError(f'{key}: {len(observed)} attempts executed, retry rules predict {len(predicted["attempts"])}')
        final = dram['record_final']
        if (final['bus_sel'], final['cs']) != (predicted['working_bus'], predicted['working_cs']):
            raise ValueError(f'{key}: final working selectors differ from the retry rules')
    else:
        # The last attempt ended before training. Earlier attempts all failed training (checked above),
        # so the rules must offer exactly one further candidate after each of them.
        def stop_after_observed(ranks, width):
            calls.append((ranks, width))
            return len(calls) == len(observed)

        semantics.attempts(sem, bus_in, cs_in, stop_after_observed)
        if len(calls) != len(observed):
            raise ValueError(f'{key}: {len(observed)} attempts executed, retry rules permit {len(calls)}')
    for number, (attempt, (ranks, width)) in enumerate(zip(observed, calls), 1):
        for name, value in (('ranks', ranks), ('width_bits', width)):
            if name in attempt['config'] and attempt['config'][name] != value:
                raise ValueError(f'{key}: attempt {number} {name} {attempt["config"][name]} differs from retry rules {value}')
    return covered


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


CONTRACT_DOC = 'docs/bootloader-initialization-contract.md'
BLOCK = re.compile(r'(<!-- generated:([a-z-]+) start -->\n)(.*?)(<!-- generated:\2 end -->)', re.S)


def _hex(value):
    return '—' if value is None else f'`{value:#x}`'


def _refs(rows, keys):
    out = []
    for row in rows:
        values = ' / '.join(str(row[k]) for k in keys)
        group = 'all releases' if len(rows) == 1 else ', '.join(row['releases'])
        out.append(f'{values} ({group})')
    return '; '.join(out)


def render_blocks(contract):
    """Tables generated from the verified structured definitions."""
    import contract_semantics as semantics
    sem, fields = contract['semantics'], contract['configuration_fields']
    blocks = {}
    rows = ['| Field | Working offset | Width | Primary INI | Secondary INI | INI slot | Reference primary / secondary | Meaning |',
            '|---|---:|---:|---:|---:|---:|---|---|']
    for key, f in sorted(fields.items(), key=lambda kv: kv[1]['offset']):
        if f['record'] != 'working-dram-record':
            continue
        rows.append(f"| `{key}` | +{f['offset']:#x} | {f['width']} | +{f['ini_offsets']['primary']:#x} | "
                    f"+{f['ini_offsets']['secondary']:#x} | {f['ini_slot_width']} | "
                    f"{_refs(f['reference'], ('primary', 'secondary'))} | {f['meaning']} |")
    rows += ['', '| INI field | Offset | Width | Reference | Meaning |', '|---|---:|---:|---|---|']
    for key, f in sorted(fields.items(), key=lambda kv: kv[1]['offset']):
        if f['record'] == 'ini':
            rows.append(f"| `{key}` | +{f['offset']:#x} | {f['width']} | {_refs(f['reference'], ('value',))} | {f['meaning']} |")
    blocks['dram-record'] = rows
    bus, rank, retry = sem['dram-bus'], sem['dram-rank'], sem['dram-retry']
    rows = ['| Input bus selector | Initial width | Automatic x16 fallback | Working byte per attempt | Byte after persistent training failure |',
            '|---|---|---|---|---|']
    for r in bus['rules']:
        span = f"{r['input_min']}" if r['input_min'] == r['input_max'] else f"{r['input_min']}..{r['input_max']}"
        working = f"{r['working_bus_selector']} (x{r['initial_width_bits']})"
        if r['automatic_width_fallback']:
            working += ', then 1 (x16) after fallback'
        rows.append(f"| {span} | x{r['initial_width_bits']} | {'yes' if r['automatic_width_fallback'] else 'no'} | "
                    f"{working} | {r['retained_selector']} |")
    rows += ['', '| Input chip-select selector | Initial ranks | Automatic rank retry | Byte after persistent training failure |',
             '|---|---:|---|---|']
    for r in rank['rules']:
        span = f"{r['input_min']}" if r['input_min'] == r['input_max'] else f"{r['input_min']}..{r['input_max']}"
        rows.append(f"| {span} | {r['initial_ranks']} | {'yes, 2 then 1' if r['automatic'] else 'no'} | {r['retained_selector']} |")
    order = []
    for b_in, c_in in ((2, 0), (2, 1), (2, 2), (1, 0), (0, 0)):
        seq = semantics.attempts(sem, b_in, c_in, lambda *_: False)['attempts']
        order.append(f"bus {b_in}, cs {c_in}: " + ' → '.join(f'({r},x{w})' for r, w in seq))
    rows += ['', f"Retry is eligible only for internal {', '.join(retry['eligible_internal_codes'])} "
             f"({retry['eligibility']}). Other internal codes return {retry['collapsed_return']} without retry. "
             f"Attempt order with every attempt failing training: " + '; '.join(order) + '.']
    blocks['dram-selectors'] = rows
    cap = sem['dram-capacity']
    rows = [f"Exponent e = {' + '.join(cap['exponent_terms'])} + {cap['exponent_bias']}; accepted when e ≤ {cap['max_exponent']}, "
            f"else internal {cap['exponent_overflow']['internal_code']} returned as {cap['exponent_overflow']['returned_code']}. "
            f"capacity_width_operand is {bus['capacity_width_operand']['16']} for x16 and {bus['capacity_width_operand']['32']} for x32; "
            'it is not the working bus selector (0 for x32).', '']
    rows += [f"* Bank code{'s' if len(b['bank_codes']) > 1 else ''} {', '.join(map(str, b['bank_codes']))}: `{b['formula']}`"
             for b in cap['bank_branches']]
    rows += ['', '| rcc | Row code | Column code | Bank code | Width | Ranks | Capacity |', '|---|---:|---:|---:|---|---:|---|']
    for rcc, width, ranks in ((0x48, 16, 1), (0x48, 32, 1), (0x48, 16, 2), (0x48, 32, 2), (0x00, 16, 1), (0xCC, 16, 1),
                              (0xCC, 16, 2), (0x49, 16, 1)):
        mib, err = semantics.capacity(sem, rcc, width, ranks)
        rows.append(f"| `{rcc:#04x}` | {rcc >> 6} | {(rcc >> 2) & 3} | {rcc & 3} | x{width} | {ranks} | "
                    f"{f'{mib} MiB' if err is None else f'rejected ({err})'} |")
    rows += ['', 'Limitations: ' + ' '.join(f'{x}.' for x in cap['limitations'])]
    blocks['dram-capacity'] = rows
    afi = contract['interfaces']['afi']
    fb = afi['consumer']['fallback']
    getter = {v: k for k, v in afi['consumer']['getters'].items()}
    rows = ['| Offset | Width | Field | Encoding | Producer source | Getter fallback without magic |', '|---:|---:|---|---|---|---|']
    for r in afi['format']:
        source = r.get('source_field') and f"INI `{r['source_field']}`" or {
            'magic': '`41 46 49`', 'reserved_byte_3': f"zero; not compared", 'boot_mode': f"{afi['cold_boot_mode']} on cold boot",
            'boot_dev': ', '.join(f'{m} `{v:#x}`' for m, v in afi['boot_device_by_medium'].items()),
            'capacity_bytes': afi['capacity_conversion']}[r['field']]
        fallback = fb.get(getter.get(r['field'])) if r['field'] in getter else '—'
        rows.append(f"| {r['offset']} | {r['width']} | `{r['field']}` | {r['encoding']} | {source} | {fallback} |")
    rows += ['', f"Base `{afi['address']:#x}`, {afi['size']} bytes. Getters compare {afi['consumer']['magic_checked_bytes']} magic bytes. "
             f"`dram_init` uses the size when it is at least {afi['consumer']['minimum_size_bytes'] >> 20} MiB, otherwise "
             f"`{afi['consumer']['fallback_ram_bytes']:#x}`. {afi['generation']['note']} {afi['admission']['note']} {afi['linux_note']}"]
    blocks['afi-layout'] = rows
    layout = contract['interfaces']['sram-layout']
    rows = ['| Range | Identifier | Basis | Live stages | Owner and derivation |', '|---|---|---|---|---|']
    for r in layout['ranges']:
        span = (f"`[{r['start']:#x},{r['end']:#x})`" if r['end'] is not None else f"top `{r['top']:#x}`, grows down, extent unknown")
        d = r.get('derivation') or {}
        how = {'sectors': f"; end = start + {d.get('sectors')} × {d.get('sector_bytes')}" +
               (f" (storage read {d['storage_read']})" if 'storage_read' in d else ''),
               'length': f"; end = start + {d.get('bytes', 0):#x}"}.get(d.get('kind'), '')
        rows.append(f"| {span} | `{r['id']}` | {r['basis']} | {', '.join(r['stages'])} | {r['owner']}{how} |")
    rows += ['', '| Overlap | Relation | Justification |', '|---|---|---|']
    rows += [f"| `{o['a']}` / `{o['b']}` | {o['relation']} | {o['why']} |" for o in layout['overlaps']]
    lo, hi = layout['emulator_mapping']
    rows += ['', f"The emulator maps `[{lo:#x},{hi:#x})` ({layout['emulator_mapping_basis']}). Physical SRAM extent: unresolved."]
    blocks['sram-layout'] = rows
    return {name: '\n'.join(text) + '\n' for name, text in blocks.items()}


def render_contract_doc(contract, text):
    blocks = render_blocks(contract)
    seen = set()

    def fill(match):
        name = match.group(2)
        if name not in blocks:
            raise ValueError(f'{CONTRACT_DOC}: unknown generated block {name}')
        seen.add(name)
        return match.group(1) + blocks[name] + match.group(4)

    out = BLOCK.sub(fill, text)
    if seen != blocks.keys():
        raise ValueError(f'{CONTRACT_DOC}: missing generated blocks {sorted(blocks.keys() - seen)}')
    return out


def check_generated(root):
    spec = read(root / INPUT)
    contract = build_contract(root, spec)
    if formatted(contract) != (root / CONTRACT).read_bytes():
        raise ValueError(f'{CONTRACT} is stale')
    if render_reference(contract) != (root / REFERENCE).read_bytes():
        raise ValueError(f'{REFERENCE} is stale')
    doc = (root / CONTRACT_DOC).read_text(encoding='utf-8')
    if render_contract_doc(contract, doc) != doc:
        raise ValueError(f'{CONTRACT_DOC} generated tables are stale')
    trace = read(root / TRACE)
    if trace_bytes(trace) != (root / TRACE).read_bytes():
        raise ValueError(f'{TRACE} is not canonical')
    return validate_trace(contract, trace, read(root / HISTORY))


def verify_sources(root, sources_dir):
    """Check each pinned source reference against a local file: git blob SHA-1 and line bounds.

    Distinguishes a digest that merely looks valid from one checked against the file."""
    from build_dataset import REPOS
    report = {}
    for row in read(root / 'specifications/bootloader-source-references.json'):
        folder, _, revision = REPOS[row['source']]
        if revision != row['revision']:
            raise ValueError(f"{row['id']}: revision differs from the source ledger")
        path = Path(sources_dir) / folder / row['path']
        if not path.is_file():
            report[row['id']] = 'unavailable'
            continue
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
        lines = data.decode('utf-8', 'replace').splitlines()
        if blob != row['git_blob_sha1']:
            raise ValueError(f"{row['id']}: local file blob {blob} differs from the pinned reference")
        if not all(0 < a <= b <= len(lines) for a, b in row['line_ranges']):
            raise ValueError(f"{row['id']}: line ranges exceed the {len(lines)}-line file")
        report[row['id']] = 'verified'
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', choices=('generate', 'validate', 'replay', 'compare', 'sources'))
    cli.add_argument('--sources-dir', type=Path, default=os.environ.get('ATM_SOURCES_DIR'))
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
            doc = ROOT / CONTRACT_DOC
            doc.write_text(render_contract_doc(contract, doc.read_text(encoding='utf-8')), encoding='utf-8')
        elif args.mode == 'validate':
            print(json.dumps(check_generated(ROOT), sort_keys=True))
        elif args.mode == 'sources':
            if not args.sources_dir:
                cli.error('sources requires --sources-dir or ATM_SOURCES_DIR')
            print(json.dumps(verify_sources(ROOT, args.sources_dir), sort_keys=True))
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
