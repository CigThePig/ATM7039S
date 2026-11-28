#!/usr/bin/env python3
"""Semantic checks for the bootloader initialization contract.

The curated specification states DRAM selection, retry, capacity, record layout,
AFI and SRAM semantics as structured data. This module interprets that data and
compares the interpretation with references that do not derive from it:

* actual loader execution under Unicorn, recorded in
  ``evidence/firmware/dram-selector-semantics.json`` (``generate`` mode needs the
  hash-pinned images);
* the independently written DRAM model ``tools/ddr_model.py``;
* historical firmware-backed evidence (SD2 DRAM comparison, unified boot chain);
* bytes delivered by firmware in the committed ordered trace, and the executed
  U-Boot AFI getters.

A structured value is never compared with a rendering of itself.
"""
import argparse
from functools import lru_cache
import gc
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SEMANTICS_EVIDENCE = 'evidence/firmware/dram-selector-semantics.json'
SEMANTIC_RELEASES = ('koriki-v1.0', 'stock-20231014')
BYTE = range(256)
MASK32 = 0xFFFFFFFF
SECONDARY_INI = 0x4C        # the shipped cold path selects the secondary record (selector word +0x2c != 0)
INI_RECORD_BASES = {'primary': 0x1C, 'secondary': 0x4C}
RECORD_BYTES = 12           # packed working record at 0xb4070820
INI_RECORD_BYTES = 16       # INI representation +0x1c..+0x2b (and +0x4c..+0x5b)

# Matrix executed on the actual loader. Inputs patch the secondary INI record that
# the shipped cold path selects. Synthetic hardware decides training and aliasing.
SELECTOR_BUS = (0, 1, 2, 3, 0x80, 0xFF)
SELECTOR_CS = (0, 1, 2, 3)
SELECTOR_HW = ((16, 1), (16, 2), (32, 1), (32, 2))
# (bus, cs, rcc, width_bits, ranks, col_bits, row_bits). rcc & 0xcc != 0 skips the
# alias probe and uses the record's row/column codes. rcc = 0 probes the synthetic
# device: column code = col_bits - 8, row code = row_bits - 13.
CAPACITY_CASES = (
    (1, 1, 0x00, 16, 1, 8, 13), (1, 1, 0x04, 16, 1, 10, 14), (1, 1, 0x40, 32, 2, 10, 14),
    (1, 1, 0x48, 32, 2, 10, 14), (0, 1, 0x48, 32, 2, 10, 14), (1, 2, 0x48, 32, 2, 10, 14),
    (0, 2, 0x48, 32, 2, 10, 14), (1, 1, 0xCC, 32, 2, 10, 14), (1, 2, 0xCC, 32, 2, 10, 14),
    (0, 1, 0xCC, 32, 2, 10, 14), (0, 2, 0xCC, 32, 2, 10, 14), (1, 2, 0x8C, 32, 2, 10, 14),
    (0, 1, 0x8C, 32, 2, 10, 14), (1, 1, 0x49, 32, 2, 10, 14), (1, 1, 0x4A, 32, 2, 10, 14),
    (1, 1, 0x4B, 32, 2, 10, 14), (0, 2, 0x49, 32, 2, 10, 14), (1, 1, 0xCD, 32, 2, 10, 14),
    (0, 2, 0x8D, 32, 2, 10, 14), (1, 1, 0xC9, 32, 2, 10, 14), (2, 0, 0x00, 32, 2, 10, 14),
    (2, 0, 0x00, 16, 2, 10, 14), (3, 1, 0x00, 16, 1, 10, 14), (0, 0, 0x00, 32, 1, 10, 14),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


# ---------------------------------------------------------------------------
# Interpretation of the structured DRAM semantics

def rule_for(rules, value, name):
    hits = [rule for rule in rules if rule['input_min'] <= value <= rule['input_max']]
    require(len(hits) == 1, f'{name}: input {value} matches {len(hits)} rules')
    return hits[0]


def check_partition(rules, name):
    require(rules and [r['input_min'] for r in rules] == sorted(r['input_min'] for r in rules), f'{name}: rules unsorted')
    edge = 0
    for rule in rules:
        require(rule['input_min'] == edge and rule['input_max'] >= rule['input_min'], f'{name}: rules do not partition 0..255')
        edge = rule['input_max'] + 1
    require(edge == 256, f'{name}: rules do not partition 0..255')


def working_selector(sem, width_bits):
    encoding = {int(k): v for k, v in sem['dram-bus']['working_selector_width_bits'].items()}
    hits = [k for k, v in encoding.items() if v == width_bits]
    require(len(hits) == 1, f'no working selector encodes x{width_bits}')
    return hits[0]


def attempts(sem, bus_in, cs_in, trains):
    """Cold attempt sequence implied by the structured selection and retry rules.

    ``trains(ranks, width_bits)`` supplies the synthetic training outcome. Returns
    the attempt list, whether an attempt trained, and the working-record bus and
    chip-select bytes left after the final attempt."""
    bus = rule_for(sem['dram-bus']['rules'], bus_in, 'dram-bus')
    rank = rule_for(sem['dram-rank']['rules'], cs_in, 'dram-rank')
    retry = sem['dram-retry']
    width, ranks = bus['initial_width_bits'], rank['initial_ranks']
    seen = []
    while True:
        seen.append((ranks, width))
        require(len(seen) <= retry['max_attempts'], 'structured retry rules exceed the attempt bound')
        if trains(ranks, width):
            return dict(attempts=seen, trained=True, working_bus=working_selector(sem, width), working_cs=ranks)
        stepped = False
        for step in retry['order']:
            if step == 'rank':
                rule = retry['rank_step']
                if rank['automatic'] and ranks == rule['from_ranks']:
                    ranks, stepped = rule['to_ranks'], True
            elif step == 'width':
                rule = retry['width_step']
                if bus['automatic_width_fallback'] and width == rule['from_width_bits']:
                    width, stepped = rule['to_width_bits'], True
                    if rank['automatic']:
                        ranks = rule['automatic_rank_restart']
            else:
                raise ValueError(f'unknown retry step {step}')
            if stepped:
                break
        if not stepped:
            terminal = retry['persistent_training_failure_writeback']
            return dict(attempts=seen, trained=False,
                        working_bus=bus[terminal['bus_byte']], working_cs=rank[terminal['cs_byte']])


def capacity(sem, rcc, width_bits, ranks):
    """Firmware capacity arithmetic from the structured definition: (MiB or None, internal error)."""
    cap = sem['dram-capacity']
    fields = {name: (rcc >> lo) & ((1 << (hi - lo + 1)) - 1) for name, (hi, lo) in cap['rcc_fields'].items()}
    operand = sem['dram-bus']['capacity_width_operand'][str(width_bits)]
    terms = dict(fields, capacity_width_operand=operand, chip_select_count=ranks)
    exponent = sum(terms[name] for name in cap['exponent_terms']) + cap['exponent_bias']
    if exponent > cap['max_exponent']:
        return None, cap['exponent_overflow']['internal_code']
    shift = exponent - cap['mib_shift']
    rows = [row for row in cap['bank_branches'] if fields['bank_code'] in row['bank_codes']]
    require(len(rows) == 1, f'bank code {fields["bank_code"]} matches {len(rows)} capacity branches')
    value = ((rows[0]['scale'] << shift) >> rows[0]['divide_shift']) & MASK32
    return value & cap['result_mask'], None


def returned_code(sem, internal):
    retry = sem['dram-retry']
    if internal == '0x0':
        return '0x0'
    if internal in retry['eligible_internal_codes']:
        return internal
    require(internal in retry['collapsed_internal_codes'], f'unclassified internal code {internal}')
    return retry['collapsed_return']


# ---------------------------------------------------------------------------
# Independent model reference

@lru_cache(maxsize=None)
def model_attempts(bus_in, cs_in, width_bits, ranks):
    sys.path.insert(0, str(ROOT / 'tools'))
    import ddr_model as m
    out = m.run(m.Record(468, 0, bus_in, cs_in, 0x10, 0x48, 1, 1, 12),
                m.Hardware(ranks=ranks, width=width_bits, col_code=2, row_code=1))
    seen = []
    for line in out['prints']:
        if line.startswith('DRAM init mode0'):
            fields = line.split(',')
            seen.append((int(fields[2][:-2]), int(fields[3][1:-3])))
    return tuple(seen), out['result'] == '0x0'


@lru_cache(maxsize=None)
def model_capacity(rcc, width_bits, ranks):
    sys.path.insert(0, str(ROOT / 'tools'))
    import ddr_model as m

    class Seq:
        def __init__(self):
            self.values = {}

        def w(self, address, value, *_):
            self.values[address] = value

        def cur(self, address):
            return self.values.get(address, 0)

    record = m.Record(468, 0, 1 if width_bits == 16 else 0, ranks, 0x10, rcc, 1, 1, 12)
    _, mib, error = m.capacity_probe(Seq(), record, ranks, m.Hardware(ranks=ranks, width=width_bits))
    return mib, error


def trains_with(width_bits, ranks):
    return lambda r, w: r <= ranks and w <= width_bits


def model_domain():
    for bus in BYTE:
        for cs in (0, 1, 2, 3, 0x80, 0xFF):
            yield bus, cs
    for cs in BYTE:
        for bus in (0, 1, 2, 3, 0xFF):
            yield bus, cs


def check_dram_semantics(contract, root=ROOT):
    """Return comparison statistics; raise on any disagreement."""
    sem = contract['semantics']
    bus, rank, retry, cap = (sem[k] for k in ('dram-bus', 'dram-rank', 'dram-retry', 'dram-capacity'))
    check_partition(bus['rules'], 'dram-bus')
    check_partition(rank['rules'], 'dram-rank')
    require(bus['input_field'] == 'dram-bus' and rank['input_field'] == 'dram-cs', 'semantics name wrong input fields')
    require(set(bus['working_selector_width_bits'].values()) == {16, 32}, 'working selector must encode x16 and x32')
    require({int(k) for k in bus['capacity_width_operand']} == {16, 32}, 'width operand must cover x16 and x32')
    # Normalization keeps the original selector distinct from the working byte.
    for value in BYTE:
        rule = rule_for(bus['rules'], value, 'dram-bus')
        require(rule['working_bus_selector'] == working_selector(sem, rule['initial_width_bits']),
                f'dram-bus {value}: working selector disagrees with its initial width')
    stats = dict(model_comparisons=0, firmware_rows=0, historical_checks=0)

    # 1. Independent model: attempt order and training success over the input domain.
    for bus_in, cs_in in model_domain():
        for width, ranks in SELECTOR_HW:
            interp = attempts(sem, bus_in, cs_in, trains_with(width, ranks))
            seen, ok = model_attempts(bus_in, cs_in, width, ranks)
            require((tuple(interp['attempts']), interp['trained']) == (seen, ok),
                    f'semantics disagree with ddr_model for bus {bus_in} cs {cs_in} on x{width}/{ranks} ranks: '
                    f'{interp["attempts"]} vs {list(seen)}')
            stats['model_comparisons'] += 1
    for rcc in BYTE:
        if rcc & 0xCC == 0:
            continue     # probe path: the model's result depends on its synthetic alias rule
        for width in (16, 32):
            for ranks in (1, 2):
                require(capacity(sem, rcc, width, ranks)[0] == model_capacity(rcc, width, ranks)[0],
                        f'capacity semantics disagree with ddr_model for rcc {rcc:#x} x{width} cs {ranks}')
                stats['model_comparisons'] += 1

    # 2. Actual loader execution.
    doc = json.loads((root / SEMANTICS_EVIDENCE).read_bytes())
    require(doc['format_version'] == 1 and set(doc['firmware']) == set(SEMANTIC_RELEASES), 'selector evidence scope changed')
    history = json.loads((root / 'evidence/firmware/unified-boot-chain.json').read_bytes())
    for release, row in doc['firmware'].items():
        require(row['actual_sha256'] == history['firmware'][release]['actual_sha256'] and
                row['loader_sha256'] == history['firmware'][release]['loader_sha256'],
                f'{release}: selector evidence firmware identity differs')
    for block in ('dram-bus', 'dram-rank', 'dram-retry', 'dram-capacity'):
        for pc, text in sem[block]['instructions']:
            for release in SEMANTIC_RELEASES:
                require(doc['instruction_audit'][release].get(f'{pc:#x}') == text,
                        f'{block}: cited instruction {pc:#x} {text!r} differs from the audited {release} loader')
                stats.setdefault('audited_instructions', 0)
                stats['audited_instructions'] += 1
    for row in doc['runs']:
        i, o = row['input'], row['observed']
        interp = attempts(sem, i['bus'], i['cs'], trains_with(i['width_bits'], i['ranks']))
        where = f"{row['release']} {row['id']}"
        require([tuple(a) for a in o['attempts']] == interp['attempts'],
                f'{where}: firmware attempts {o["attempts"]} differ from semantics {interp["attempts"]}')
        require(o['record_final']['bus_sel'] == interp['working_bus'] and o['record_final']['cs'] == interp['working_cs'],
                f'{where}: final working selectors differ from semantics')
        if interp['trained']:
            rcc_final = o['record_final']['rcc']
            require(rcc_final & 3 == i['rcc'] & 3, f'{where}: bank code was not taken from the record')
            if i['rcc'] & cap['probe_skip_mask']:
                require(rcc_final == i['rcc'], f'{where}: stored geometry changed without a probe')
            mib, err = capacity(sem, rcc_final, interp['attempts'][-1][1], interp['working_cs'])
            internal = err or '0x0'
            require(o['capacity_mib'] == mib and o['internal_codes'][-1] == internal,
                    f'{where}: firmware capacity {o["capacity_mib"]} differs from semantics {mib} ({internal})')
        else:
            internal = retry['eligible_internal_codes'][0]
            require(o['internal_codes'][-1] == internal and o['capacity_mib'] is None,
                    f'{where}: persistent training failure differs')
        require(o['dram_return'] == returned_code(sem, internal), f'{where}: returned code differs from semantics')
        stats['firmware_rows'] += 1
    require(stats['firmware_rows'] == len(SEMANTIC_RELEASES) * (len(SELECTOR_BUS) * len(SELECTOR_CS) * len(SELECTOR_HW)
                                                                 + len(CAPACITY_CASES)), 'selector evidence incomplete')

    # 3. Historical firmware-backed results recorded before this correction.
    comparison = json.loads((root / 'evidence/firmware/sd2-dram-comparison.json').read_bytes())
    for name, bus_in, cs_in, width, ranks in (
            ('bus-auto-patched-record', 2, 0, 16, 1), ('mixed-gpio-bus-retry', 2, 0, 16, 1),
            ('persistent-training-failure', 1, 0, 0, 0), ('reference', 1, 0, 16, 1),
            ('two-ranks-first-attempt', 1, 0, 16, 2)):
        for release, pairs in comparison['releases'].items():
            run = comparison['distinct_pairs'][pairs['pairs'][name]]['runs']['2']
            interp = attempts(sem, bus_in, cs_in, trains_with(width, ranks))
            require([(t['ranks'], t['width_bits']) for t in run['training']] == interp['attempts'] and
                    run['record_final']['bus_sel'] == interp['working_bus'] and
                    run['record_final']['cs'] == interp['working_cs'],
                    f'{release} {name}: historical attempts or working selectors differ from semantics')
            stats['historical_checks'] += 1
    for release, pairs in comparison['releases'].items():
        dfi = comparison['distinct_pairs'][pairs['pairs']['dfi-timeout']]['runs']['2']
        require(dfi['internal_codes'][-1] == '0xdf00fa11' and dfi['dram_return'] == returned_code(sem, '0xdf00fa11') and
                [t['pgsr_response'] for t in dfi['training']] == ['0x3f', '0x1f'] and
                len(dfi['training']) == len(attempts(sem, 1, 0, trains_with(16, 1))['attempts']),
                f'{release}: DFI timeout must follow a training retry and must not retry itself')
        over = comparison['distinct_pairs'][pairs['pairs']['capacity-exponent-overflow']]['runs']['2']
        require(over['internal_codes'][-1] == capacity(sem, 0xCC, 32, 2)[1] and
                over['dram_return'] == cap['exponent_overflow']['returned_code'],
                f'{release}: historical capacity overflow differs from semantics')
        stats['historical_checks'] += 2
    failed = history['scenarios']['koriki-v1.0']['training-failure']['dram_result']['record_final']
    interp = attempts(sem, 1, 0, lambda *_: False)
    require((failed['bus_sel'], failed['cs']) == (interp['working_bus'], interp['working_cs']),
            'unified training-failure write-back differs from semantics')
    stats['historical_checks'] += 1
    return stats


def check_static_operations(contract, trace, root=ROOT):
    """Operations whose behavior is bound to audited static instructions rather than replayed events."""
    doc = json.loads((root / SEMANTICS_EVIDENCE).read_bytes())
    verified = []
    for key, op in contract['operations'].items():
        rows = op.get('static_instructions', [])
        for pc, text in rows:
            for release in SEMANTIC_RELEASES:
                require(doc['instruction_audit'][release].get(f'{pc:#x}') == text,
                        f'{key}: static instruction {pc:#x} {text!r} differs from the audited {release} loader')
        for pc, word in op.get('static_literals', []):
            for release in SEMANTIC_RELEASES:
                require(doc['literal_audit'][release].get(f'{pc:#x}') == f'{word:#x}',
                        f'{key}: literal {pc:#x} differs from the audited {release} loader')
        anchors = op.get('static_anchors', [])
        for pc in anchors:
            require(pc in trace['startup_audit']['anchors'], f'{key}: anchor {pc} absent from the U-Boot startup audit')
        for pc in op.get('static_literals_from_audit', []):
            require(pc in trace['startup_audit']['literals'], f'{key}: literal {pc} absent from the U-Boot startup audit')
        if rows or anchors:
            require(op['evidence_classification'] in ('static', 'executed-synthetic'), f'{key}: static binding class')
            verified.append(key)
    return sorted(verified)


# ---------------------------------------------------------------------------
# Configuration records

def field_value(blob, offset, width):
    require(offset + width <= len(blob), f'field at {offset:#x} exceeds the record')
    return int.from_bytes(blob[offset:offset + width], 'little')


def check_configuration(contract, history, trace):
    fields = contract['configuration_fields']
    releases = set(history['firmware'])
    working = {k: f for k, f in fields.items() if f['record'] == 'working-dram-record'}
    # Packed working record: twelve bytes, no gaps or overlaps.
    covered = sorted((f['offset'], f['offset'] + f['width'], k) for k, f in working.items())
    require(covered[0][0] == 0 and covered[-1][1] == RECORD_BYTES and
            all(a[1] == b[0] for a, b in zip(covered, covered[1:])), 'working DRAM record fields overlap or leave gaps')
    for key, field in working.items():
        require(set(field['ini_offsets']) == set(INI_RECORD_BASES), f'{key}: needs primary and secondary INI offsets')
        for record, base in INI_RECORD_BASES.items():
            rel = field['ini_offsets'][record] - base
            require(0 <= rel and rel + field['ini_slot_width'] <= INI_RECORD_BYTES and
                    field['width'] <= field['ini_slot_width'], f'{key}: INI placement outside the record')
    ini_covered = sorted((f['ini_offsets']['primary'] - 0x1C, f['ini_offsets']['primary'] - 0x1C + f['ini_slot_width'])
                         for f in working.values())
    require(ini_covered[0][0] == 0 and ini_covered[-1][1] == INI_RECORD_BYTES and
            all(a[1] == b[0] for a, b in zip(ini_covered, ini_covered[1:])), 'INI DRAM record slots overlap or leave gaps')
    for key, field in fields.items():
        groups = field['reference']
        listed = [r for row in groups for r in row['releases']]
        require(sorted(listed) == sorted(releases), f'{key}: reference must name every release exactly once')
    checked = 0
    # Packed record bytes recorded from the executed copy in every release.
    for release, data in history['firmware'].items():
        config = data['config']
        packed = {
            'primary': bytes.fromhex(next(v for k, v in config.items() if k.startswith('primary record'))),
            'secondary': bytes.fromhex(next(v for k, v in config.items() if k.startswith('second record'))),
        }
        for key, field in working.items():
            row = next(r for r in field['reference'] if release in r['releases'])
            for record in INI_RECORD_BASES:
                require(field_value(packed[record], field['offset'], field['width']) == row[record],
                        f'{release} {key}: {record} reference differs from the executed working copy')
                checked += 1
        # INI fields outside the records, by the offsets the pre-DRAM decoder printed.
        labelled = {}
        for label, value in config.items():
            if label.startswith('ini+0x'):
                labelled[int(label[4:].split()[0].split('-')[0], 16)] = value
        for key, field in fields.items():
            if field['record'] != 'ini' or field['offset'] not in labelled:
                continue
            row = next(r for r in field['reference'] if release in r['releases'])
            expected = labelled[field['offset']]
            require(row['value'] == expected, f'{release} {key}: reference {row["value"]!r} differs from decoded INI {expected!r}')
            checked += 1
    # Raw INI bytes observed in SRAM by the traced executions.
    for case_id, case in trace['cases'].items():
        dram = case['result']['dram']
        if not dram:
            continue
        release = case_id.split('/')[0]
        require(dram['ini_initial']['selector'] == next(
            r['value'] for r in fields['dram-select']['reference'] if release in r['releases']),
            f'{case_id}: record-selection word differs')
        for record in INI_RECORD_BASES:
            raw = bytes.fromhex(dram['ini_initial'][record])
            require(len(raw) == INI_RECORD_BYTES, f'{case_id}: INI record length')
            for key, field in working.items():
                rel = field['ini_offsets'][record] - INI_RECORD_BASES[record]
                row = next(r for r in field['reference'] if release in r['releases'])
                require(field_value(raw, rel, field['width']) == row[record],
                        f'{case_id} {key}: INI byte placement differs from the observed {record} record')
                checked += 1
        # Write-back stores the final working record in the INI primary layout.
        if trace_facts(history, case_id)['mode'] == 'cold' and dram['dram_return'] is not None:
            final = bytes.fromhex(dram['record_final']['raw'])
            image = bytearray(INI_RECORD_BYTES)
            for key, field in working.items():
                rel = field['ini_offsets']['primary'] - 0x1C
                image[rel:rel + field['width']] = final[field['offset']:field['offset'] + field['width']]
            require(image.hex() == dram['ini_final']['primary'],
                    f'{case_id}: write-back layout differs from the observed INI primary record')
            checked += 1
    return checked


# ---------------------------------------------------------------------------
# AFI

def afi_fields(afi, blob):
    out = {}
    for row in afi['format']:
        raw = blob[row['offset']:row['offset'] + row['width']]
        out[row['field']] = raw.hex() if row['encoding'] == 'bytes' else int.from_bytes(raw, row['encoding'][-2:] == 'le'
                                                                                        and 'little' or 'big')
    return out


def afi_consumer(afi, blob):
    """Pinned getter behavior from the structured consumer definition."""
    consumer = afi['consumer']
    fields = afi_fields(afi, blob)
    magic = blob[:consumer['magic_checked_bytes']].hex() == consumer['magic'][:2 * consumer['magic_checked_bytes']]
    getters = {name: (fields[field] if magic else consumer['fallback'][name])
               for name, field in consumer['getters'].items()}
    size = getters['size']
    fallback = not (magic and size >= consumer['minimum_size_bytes'])
    return getters, consumer['fallback_ram_bytes'] if fallback else size, fallback


def check_afi(contract, trace, history):
    afi = contract['interfaces']['afi']
    rows = sorted(afi['format'], key=lambda r: r['offset'])
    require(rows[0]['offset'] == 0 and all(a['offset'] + a['width'] == b['offset'] for a, b in zip(rows, rows[1:])) and
            rows[-1]['offset'] + rows[-1]['width'] == afi['size'] == 16, 'AFI fields overlap, leave gaps or change size')
    require(afi['address'] % 4 == 0 and all(r['offset'] % r['width'] == 0 for r in rows if r['width'] in (2, 4)),
            'AFI words must be naturally aligned')
    require(all(r['encoding'] in ('bytes', 'u8', 'u32le') for r in rows) and
            all((r['encoding'] == 'u32le') == (r['width'] == 4) for r in rows), 'AFI encodings inconsistent with widths')
    require(afi['required_by_linux'] is False, 'AFI is a stock U-Boot interface, not a Linux boot requirement')
    by_field = {r['field']: r for r in rows}
    consumer = afi['consumer']
    require(1 <= consumer['magic_checked_bytes'] <= 4, 'AFI magic comparison length outside the four-byte slot')
    sram = {r['id']: r for r in contract['interfaces']['sram-layout']['ranges']}
    require((sram['afi']['start'], sram['afi']['end']) == (afi['address'], afi['address'] + afi['size']),
            'AFI SRAM range differs from the interface')
    checked = 0
    fields = contract['configuration_fields']
    medium = afi['boot_device_by_medium']
    for case_id, case in trace['cases'].items():
        result, dram = case['result'], case['result']['dram']
        release = case_id.split('/')[0]
        facts = trace_facts(history, case_id)
        generated = bool(dram and dram['afi']['generated'])
        rule = afi['generation']
        expect_generated = (facts['mode'] == rule['mode'] and dram is not None and
                            (dram['dram_return'] is not None) == rule['requires_dram_return'])
        require(generated == expect_generated, f'{case_id}: AFI generation contradicts the structured generation rule')
        consumed = result['stages']['uboot-afi-and-ram']['status'] == 'completed'
        admit = afi['admission']
        admitted = (generated and dram['dram_return'] == admit['dram_return'] and
                    dram['terminal']['pc'] == admit['dram_terminal_pc'] and
                    result['stages']['dram-and-main-dispatch']['status'] == 'completed')
        require(consumed <= admitted, f'{case_id}: AFI consumed although the structured admission rule rejects it')
        if consumed:
            require(admitted, f'{case_id}: consumer reached without admission')
        if not generated:
            continue
        blob = bytes.fromhex(dram['afi']['bytes'])
        # Every observed store lies wholly inside one declared field.
        decoded = afi_fields(afi, blob)
        require(decoded['magic'] == consumer['magic'], f'{case_id}: AFI magic differs')
        require(decoded['boot_dev'] == medium[facts['medium']], f'{case_id}: AFI boot device differs for {facts["medium"]}')
        require(decoded['boot_mode'] == afi['cold_boot_mode'], f'{case_id}: AFI boot mode differs')
        for name in ('uart_index', 'uart_pad', 'uart_baud'):
            source = by_field[name]['source_field']
            value = next(r['value'] for r in fields[source]['reference'] if release in r['releases'])
            require(decoded[name] == value, f'{case_id}: AFI {name} differs from INI {source}')
        require(decoded['capacity_bytes'] == (dram['record_final']['capacity_mib'] << afi['capacity_shift']) & MASK32,
                f'{case_id}: AFI capacity conversion differs from the working record')
        require(decoded['reserved_byte_3'] == afi['producer_reserved_value'], f'{case_id}: reserved byte differs')
        if consumed:
            state = result['stages']['uboot-afi-and-ram']['state']['afi']
            getters, ram, fallback = afi_consumer(afi, blob)
            require(getters == state['getters'] and ram == state['gd_ram_size'] and fallback == state['fallback_used'],
                    f'{case_id}: structured AFI consumer disagrees with executed U-Boot getters')
        checked += 1
    for name, control in history['isolated_afi_controls'].items():
        getters, ram, fallback = afi_consumer(afi, bytes.fromhex(control['exact_hex']))
        require(getters == control['getters'] and ram == control['gd_ram_size'] and fallback == control['fallback_used'],
                f'AFI control {name}: structured consumer disagrees with executed getters')
        checked += 1
    return checked


def check_afi_stores(afi, case_id, events):
    rows = afi['format']
    base = afi['address']
    for _, count, event in events:
        if event['domain'] != 'sram' or event['op'] != 'w':
            continue
        start, end = event['address'], event['address'] + event['width']
        if end <= base or start >= base + afi['size']:
            continue
        inside = [r for r in rows if base + r['offset'] <= start and end <= base + r['offset'] + r['width']]
        require(len(inside) == 1, f'{case_id}: AFI store at {start:#x} width {event["width"]} crosses declared fields')


def trace_facts(history, case_id):
    release, name = case_id.split('/')
    run = history['scenarios'][release][name]
    return dict(medium=run['scenario']['medium'],
                mode=run['stages']['recovery-resume-decision'].get('state', {}).get('decision'))


# ---------------------------------------------------------------------------
# SRAM layout

OVERLAP_RELATIONS = {'containment', 'stage-reuse', 'recovery-overwrite', 'unresolved'}
BASES = {'observed-transfer', 'observed-access', 'static-span', 'static-inference', 'interface', 'emulator-assumption'}


def check_sram(contract, trace):
    layout = contract['interfaces']['sram-layout']
    require(layout['physical_extent'] is None, 'physical SRAM extent is unresolved')
    lo, hi = layout['emulator_mapping']
    require(layout['emulator_mapping_basis'] == 'emulator-assumption', 'emulator mapping is not physical evidence')
    ranges = {r['id']: r for r in layout['ranges']}
    require(len(ranges) == len(layout['ranges']), 'duplicate SRAM range')
    for key, r in ranges.items():
        require(r['basis'] in BASES and r['basis'] != 'physical', f'{key}: invalid range basis')
        if r['end'] is None:
            require(r['start'] is None and r.get('grows') == 'down' and r['space'] == 'sram' and
                    lo < r['top'] <= hi, f'{key}: a stack needs a down-growing top inside the modeled mapping')
            continue
        require(r['start'] < r['end'], f'{key}: reversed or empty range')
        if r['space'] == 'sram':
            require(lo <= r['start'] and r['end'] <= hi, f'{key}: outside the modeled SRAM mapping')
        derivation = r.get('derivation')
        if derivation and derivation['kind'] == 'length':
            require(r['end'] - r['start'] == derivation['bytes'], f'{key}: length differs from its derivation')
        if derivation and derivation['kind'] == 'sectors':
            require(r['end'] - r['start'] == derivation['sectors'] * derivation['sector_bytes'],
                    f'{key}: sector-derived end differs')
    checked = 0
    # Observed transfers: destination + sectors * 512 for every case reaching the read.
    for key, r in ranges.items():
        derivation = r.get('derivation') or {}
        if derivation.get('kind') != 'sectors' or 'storage_read' not in derivation:
            continue
        index = derivation['storage_read']
        for case_id, case in trace['cases'].items():
            reads = case['result']['storage_reads']
            if len(reads) <= index or reads[index]['status'] != 'ok':
                continue
            read = reads[index]
            require(int(read['destination'], 16) == r['start'] and read['sectors'] == derivation['sectors'] and
                    read['bytes'] == read['sectors'] * derivation['sector_bytes'] and
                    int(read['destination'], 16) + read['bytes'] == r['end'],
                    f'{case_id}: observed transfer {index} differs from SRAM range {key}')
            checked += 1
    # Observed SRAM stores fall within declared ranges with an owner.
    sram_stores = set()
    for case_id, rows in trace['events'].items():
        for _, values in rows:
            if values[1] == 'sram' and values[2] == 'w':
                sram_stores.add((values[3], values[4]))
    for address, width in sram_stores:
        owners = [k for k, r in ranges.items() if r['space'] == 'sram' and r['end'] is not None
                  and r['start'] <= address and address + width <= r['end']]
        require(owners, f'SRAM store at {address:#x} has no declared range')
    # Overlaps must carry an explicit relation that matches their geometry and lifetime.
    relations = {}
    for row in layout['overlaps']:
        pair = tuple(sorted((row['a'], row['b'])))
        require(pair not in relations and row['relation'] in OVERLAP_RELATIONS and row['why'], f'{pair}: invalid overlap')
        relations[pair] = row
    bounded = [r for r in ranges.values() if r['end'] is not None and r['space'] == 'sram']
    found = set()
    for i, a in enumerate(bounded):
        for b in bounded[i + 1:]:
            if a['start'] < b['end'] and b['start'] < a['end']:
                pair = tuple(sorted((a['id'], b['id'])))
                found.add(pair)
                require(pair in relations, f'unexplained SRAM overlap {pair}')
                row = relations[pair]
                outer, inner = ranges[row['a']], ranges[row['b']]
                if row['relation'] == 'containment':
                    require(outer['start'] <= inner['start'] and inner['end'] <= outer['end'],
                            f'{pair}: containment relation is not geometric containment')
                elif row['relation'] == 'stage-reuse':
                    require(not set(outer['stages']) & set(inner['stages']), f'{pair}: reuse ranges share a live stage')
                elif row['relation'] == 'recovery-overwrite':
                    require('recovery' in set(outer['stages']) ^ set(inner['stages']),
                            f'{pair}: recovery overwrite needs one recovery-only owner')
                else:
                    require(row['open'], f'{pair}: unresolved ownership must stay open')
                checked += 1
    require(found == set(relations), f'stale overlap declarations {sorted(set(relations) - found)}')
    return checked


# ---------------------------------------------------------------------------
# DRAM timing inputs

def check_timing(contract, trace):
    timing = contract['semantics']['dram-timing']
    sys.path.insert(0, str(ROOT / 'tools'))
    import ddr_model as m
    classes = timing['trfc_classes']
    require([c['below_density_mib'] for c in classes[:-1]] == [lim for lim, _ in m.TRFC_NS] and
            [c['ns'] for c in classes] == [ns for _, ns in m.TRFC_NS] + [m.TRFC_NS_MAX] and
            classes[-1]['below_density_mib'] is None, 'tRFC classes differ from the independent model')
    operand = contract['semantics']['dram-bus']['capacity_width_operand']
    checked = 0
    for mhz in range(240, 1000, 12):
        f = (mhz // timing['clock_step_mhz']) * timing['clock_step_mhz']
        for width in (16, 32):
            for ranks in (1, 2):
                for cap in (timing['cold_timing_capacity_mib'], 256, 512, 128):
                    density = cap // operand[str(width)] // ranks
                    ns = next((c['ns'] for c in classes if c['below_density_mib'] is None or density < c['below_density_mib']))
                    t = m.timings(f, ranks, 1 if width == 16 else 0, cap)
                    require((t['density_mib'], t['tRFC']) == (density, f * ns // 1000 + 1),
                            f'density or tRFC semantics disagree with the model at {f} MHz x{width} cs {ranks} {cap} MiB')
                    checked += 1
    # PLL word observed in every traced DRAM attempt.
    for case_id, rows in trace['events'].items():
        dram = trace['cases'][case_id]['result']['dram']
        if not dram or not dram.get('record_final'):
            continue
        f = (dram['record_final']['clock_mhz'] // timing['clock_step_mhz']) * timing['clock_step_mhz']
        words = [v[5] for _, v in rows if v[1] == 'mmio' and v[2] == 'w' and v[7] == timing['pll_write_site']]
        attempts_seen = sum(b[0] == 'controller-phy-programming' for b in trace['cases'][case_id]['boundaries'])
        require(len(words) == attempts_seen and all(w == (f // 12) | timing['pll_word_or'] for w in words),
                f'{case_id}: PLL word differs from (F/12)|{timing["pll_word_or"]:#x}')
        checked += len(words)
    return checked


# ---------------------------------------------------------------------------
# Firmware execution of the selector/capacity matrix

def matrix():
    for bus in SELECTOR_BUS:
        for cs in SELECTOR_CS:
            for width, ranks in SELECTOR_HW:
                yield dict(id=f'selector-b{bus}-cs{cs}-x{width}-r{ranks}', bus=bus, cs=cs, rcc=0,
                           width_bits=width, ranks=ranks, col_bits=10, row_bits=14)
    for bus, cs, rcc, width, ranks, col, row in CAPACITY_CASES:
        yield dict(id=f'capacity-b{bus}-cs{cs}-rcc{rcc:02x}-x{width}-r{ranks}-c{col}-r{row}', bus=bus, cs=cs, rcc=rcc,
                   width_bits=width, ranks=ranks, col_bits=col, row_bits=row)


def execute(directory):
    sys.path.insert(0, str(ROOT / 'tools'))
    import dram_complete as dram
    import sd2_dram_analysis as sd2
    doc = dict(format_version=1, tool='tools/contract_semantics.py', runs=[], firmware={},
               method='Actual loader instructions under Unicorn through sd2_dram_analysis.execute with boot code 2. '
               'Inputs patch the secondary INI record (+0x54 bus, +0x55 cs, +0x57 rcc) selected by the shipped cold path. '
               'Training passes iff the synthetic ranks and width cover the attempt; the alias decode follows the '
               'synthetic geometry. Nothing here was observed on hardware.',
               patch_offsets=dict(bus=SECONDARY_INI + 8, cs=SECONDARY_INI + 9, rcc=SECONDARY_INI + 11))
    import capstone
    spec = json.loads((ROOT / 'specifications/bootloader-initialization.json').read_bytes())
    sites = sorted({pc for block in ('dram-bus', 'dram-rank', 'dram-retry', 'dram-capacity')
                    for pc, _ in spec['semantics'][block]['instructions']} |
                   {pc for op in spec['operations'].values() for pc, _ in op.get('static_instructions', [])})
    words = sorted({pc for op in spec['operations'].values() for pc, _ in op.get('static_literals', [])})
    doc['literal_audit'] = {}
    md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    doc['instruction_audit'] = {}
    for release in SEMANTIC_RELEASES:
        loader, _, identity = sd2.load_release(Path(directory), release)
        audit = doc['instruction_audit'][release] = {}
        for pc in sites:
            offset = pc - 0xB4060000
            ins, = md.disasm(loader[offset:offset + 4], pc)
            audit[f'{pc:#x}'] = f'{ins.mnemonic} {ins.op_str}'
        doc['literal_audit'][release] = {
            f'{pc:#x}': f"{int.from_bytes(loader[pc - 0xB4060000:pc - 0xB4060000 + 4], 'little'):#x}" for pc in words}
        doc['firmware'][release] = {k: identity[k] for k in ('actual_sha256', 'loader_sha256', 'bootloader_code_sha256')}
        doc['firmware'][release]['dram_function_sha256'] = identity['function_hashes']['dram']
        for spec in matrix():
            case = sd2.Case(spec['id'], 'cold', dram.Scenario(spec['id'], width=spec['width_bits'], ranks=spec['ranks'],
                                                             col_bits=spec['col_bits'], row_bits=spec['row_bits']),
                            ini_patch={SECONDARY_INI + 8: bytes([spec['bus']]), SECONDARY_INI + 9: bytes([spec['cs']]),
                                       SECONDARY_INI + 11: bytes([spec['rcc']])})
            result, harness = sd2.execute(loader, case, 2)
            final = result['record_final']
            doc['runs'].append(dict(
                release=release, id=spec['id'], input={k: v for k, v in spec.items() if k != 'id'},
                observed=dict(attempts=[[t['ranks'], t['width_bits']] for t in result['training']],
                              training_sites=sorted({t['site'] for t in result['training']}),
                              dram_return=result['dram_return'], internal_codes=result['internal_codes'],
                              capacity_mib=result['capacity_mib'],
                              record_final={k: final[k] for k in ('bus_sel', 'cs', 'rcc', 'capacity_mib', 'raw')},
                              dcu_print=next((p for p in result['prints'] if p.startswith(('Ok:DCU_CFG', 'Fail: 0x'))), None),
                              trace=result['trace'])))
            del result, harness
        del loader
        gc.collect()
    return doc


def formatted(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=True, sort_keys=True) + '\n').encode('ascii')


def main():
    cli = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cli.add_argument('mode', choices=('generate', 'check'))
    cli.add_argument('--firmware-dir', type=Path, default=os.environ.get('ATM_FIRMWARE_DIR'))
    args = cli.parse_args()
    if not args.firmware_dir:
        cli.error('requires --firmware-dir or ATM_FIRMWARE_DIR')
    content = formatted(execute(args.firmware_dir))
    if args.mode == 'check':
        if (ROOT / SEMANTICS_EVIDENCE).read_bytes() != content:
            cli.exit(1, f'{SEMANTICS_EVIDENCE} differs from a fresh firmware execution\n')
    else:
        (ROOT / SEMANTICS_EVIDENCE).write_bytes(content)
    print(json.dumps(dict(runs=len(json.loads(content)['runs'])), sort_keys=True))


if __name__ == '__main__':
    main()
