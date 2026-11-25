#!/usr/bin/env python3
"""Reconstruct and cross-validate the stock loader's DRAM timing calculations.

Runs three independent methods on each supplied loader region and records
where they agree:

1. bounded Unicorn emulation of the firmware instructions (ddr_emulate.py),
2. z3 symbolic evaluation with our own ARM interpreter (ddr_symbolic.py),
3. the hand-written readable model (ddr_model.py).

It then classifies every MMIO write of the successful init pass by
*differential* runs (reset seed, hardware hypothesis, clock, ODT/drive
fields) and compares that classification with the model's static labels.

Output is a JSON evidence file with values, formulas, firmware call-site
addresses and provenance classes. It contains no firmware bytes, disassembly
or decompiler output.

    python tools/ddr_timing.py OUT.json --loader stock-221203=loader-221203.bin ...
    python tools/ddr_timing.py OUT.json --image stock-20231014=stock-20231014.img   # reads 0x200200
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random

import ddr_emulate as de
import ddr_model as dm

REFERENCE = 'x16-1rank-2Gb'
SWEEP = (100, 1200)
LOADER_OFFSET = 0x200200


def ini_record(data, off):
    """A DRAM record as laid out in bootloader.ini (padded; the copy at 0xb4065ff8 packs it): u16 clock at +0,
    u16 capacity at +4, then bus_sel, cs, type, rcc, rdodt, wrodt, drv at +8..+0xe."""
    return dm.Record(int.from_bytes(data[off:off + 2], 'little'), int.from_bytes(data[off + 4:off + 6], 'little'),
                     *data[off + 8:off + 15])


def hw_for(scenario, seed=0):
    h = de.SCENARIOS[scenario]
    return dm.Hardware(ranks=h['ranks'], width=h['width'], col_code=h['col_bits'] - 8, row_code=h['row_bits'] - 13,
                       reset=dm.ResetAll(seed))


def firmware_record(loader, record='firmware'):
    em = de.Emulation(loader, record=record)
    em.call(de.F_INI_COPY, r0=de.INI_LOAD)
    if record == 'firmware':
        em.setreg('sp', de.STACK_TOP)
        em.uc.emu_start(de.SEL_START, de.SEL_END, count=10_000)
    elif record == 'second':
        em.uc.mem_write(de.PARAM, bytes(em.uc.mem_read(de.PARAM2, 12)))
    return em


def unicorn_run(loader, clock=None, scenario=REFERENCE, seed=0, record='firmware', patch=None):
    """Emulate with the firmware-selected record, optionally overriding clock or record bytes (ini inputs)."""
    em = de.Emulation(loader, scenario=scenario, reset_seed=seed, record=record)
    em.call(de.F_INI_COPY, r0=de.INI_LOAD)
    if record == 'firmware':
        em.setreg('sp', de.STACK_TOP)
        em.uc.emu_start(de.SEL_START, de.SEL_END, count=10_000)
    elif record == 'second':
        em.uc.mem_write(de.PARAM, bytes(em.uc.mem_read(de.PARAM2, 12)))
    if clock is not None:
        em.uc.mem_write(de.PARAM, clock.to_bytes(2, 'little'))
    for off, val in (patch or {}).items():
        em.uc.mem_write(de.PARAM + off, bytes([val]))
    rec = dm.Record.from_bytes(bytes(em.uc.mem_read(de.PARAM, 12)))
    em.writes.clear(); em.reads.clear()
    ret = em.call(de.F_WRAPPER_MODE0, r0=de.PARAM)
    return em, rec, ret


def final_pass(writes):
    """Writes of the last (successful) init pass: everything from the last DDRPLL enable-clear onwards."""
    starts = [i for i, w in enumerate(writes) if w['site'] == '0xb406800c']
    return writes[starts[-1]:] if starts else writes


def keyed(writes):
    seen, out = {}, {}
    for w in writes:
        k = (w['site'], w['address'])
        seen[k] = seen.get(k, 0) + 1
        out[k + (seen[k],)] = int(w['value'], 16)
    return out


def model_vs_unicorn(loader, clocks, scenario=REFERENCE, seed=0, record='firmware'):
    bad = []
    for clk in clocks:
        em, rec, ret = unicorn_run(loader, clk, scenario, seed, record)
        m = dm.run(rec, hw_for(scenario, seed))
        u = [(int(w['address'], 16), int(w['value'], 16)) for w in em.writes]
        if u != [(w.address, w.value) for w in m['writes']] or [p['text'] for p in em.prints] != m['prints']:
            bad.append(clk)
    return bad


def division_helpers(loader, n=2000, rng_seed=7039):
    """Validate the division models used by ddr_symbolic.py against the firmware helpers (Unicorn)."""
    rng = random.Random(rng_seed)
    em = de.Emulation(loader)
    bad = 0
    cases = [(rng.randrange(0, 1 << 31), rng.randrange(1, 1 << 16)) for _ in range(n)]
    cases += [(x * 1000 + y, 1000) for x in range(0, 70) for y in (0, 1, 999)] + [(0, 1), (12, 12), (11, 12)]
    for a, b in cases:
        if em.call(0xB406AE80, a, b) != a // b or em.call(0xB406AD40, a, b) != a // b:
            bad += 1
    return dict(cases=len(cases), mismatches=bad, helpers=['0xb406ae80 unsigned', '0xb406ad40 signed (non-negative operands)'])


def classify(loader, base_em):
    """Differential classification of the final-pass writes."""
    base = keyed(final_pass(base_em.writes))
    variants = {
        'reset': [unicorn_run(loader, seed=s)[0] for s in (0xFFFFFFFF, 0xA5A5A5A5)],
        'hardware': [unicorn_run(loader, scenario=s)[0] for s in sorted(de.SCENARIOS) if s != REFERENCE],
        'clock': [unicorn_run(loader, clock=c)[0] for c in (264, 480, 600, 720, 900)],
        'ini_odt_drv': [unicorn_run(loader, patch={8: r, 9: w, 10: d})[0] for r, w, d in ((0, 0, 9), (1, 1, 12), (3, 5, 7))],
    }
    out = {}
    for k, v in base.items():
        tags = []
        for name, ems in variants.items():
            if any(keyed(final_pass(e.writes)).get(k) != v for e in ems):
                tags.append(name)
        out[k] = tags
    return out


def register_table(loader, em, rec):
    m = dm.run(rec, hw_for(REFERENCE))
    fp = final_pass(em.writes)
    start = len(em.writes) - len(fp)
    mw = m['writes'][start:]
    diff = classify(loader, em)
    rows = []
    seen = {}
    for w, mwr in zip(fp, mw):
        k = (w['site'], w['address'])
        seen[k] = seen.get(k, 0) + 1
        tags = diff[k + (seen[k],)]
        observed = ('reset' if 'reset' in tags else 'detected' if 'hardware' in tags else
                    'ini' if ('clock' in tags or 'ini_odt_drv' in tags) else 'constant')
        rows.append(dict(site=w['site'], address=w['address'], register=dm.REG.get(int(w['address'], 16), w['address']),
                         value=w['value'], model_value=hex(mwr.value), model_class=mwr.cls, formula=mwr.formula,
                         varies_with=tags, observed_class=observed))
    return rows, m


def class_consistency(rows):
    """Model labels vs differential observation. A model 'ini'/'detected' label may legitimately observe as
    constant if the varied inputs did not reach it; contradictions are labelled constant but observed varying."""
    rank = {'constant': 0, 'ini': 1, 'detected': 2, 'reset': 3}
    contradictions = [r for r in rows if rank[r['observed_class']] > rank[r['model_class']]]
    unexercised = [r['register'] for r in rows if rank[r['observed_class']] < rank[r['model_class']]]
    return dict(contradictions=[(r['site'], r['register']) for r in contradictions], model_more_general=unexercised)


def named_timings(t):
    F = t['F']
    keys = ('tRFC', 'tRP', 'tRCD', 'tRAS', 'tRC', 'tRRD', 'tFAW', 'tWR', 'tRTP', 'tWTR', 'CL', 'CWL', 'tXP', 'tXPDLL',
            'tCKE', 'tCKESR', 'tCKSRE', 'tRSTL', 'tREFI_cycles', 'tZQCSI', 'TRTW', 'dfi_wrlat', 'dfi_rddata_en')
    return {k: dict(cycles=t[k], ns=round(t[k] * 1000 / F, 3)) for k in keys} | dict(
        F_mhz=F, tCK_ns=round(1000 / F, 4), density_mib=t['density_mib'], tRFC_ns_selected=t['tRFC_ns'])


def symbolic_summary(loader, clock_eval):
    import ddr_symbolic as ds
    r = ds.analyse(loader, domain={'clock': SWEEP}, evaluate={'clock': clock_eval})
    em, _, _ = unicorn_run(loader)
    u = [(w['address'], w['value']) for w in em.writes]
    ev = next(p['evaluated'] for p in r['paths'] if 'evaluated' in p)
    return dict(paths=len(r['paths']), domains=[p['domain']['clock'] for p in r['paths']],
                writes_per_path=sorted({len(p['mmio_writes']) for p in r['paths']}),
                clobber_dependent=sorted({x for p in r['paths'] for x in p['clobber_dependent_writes']}),
                evaluated_at_clock=clock_eval,
                equals_unicorn=[(w['address'], w['value']) for w in ev['mmio_writes']] == u,
                clock_dependent_writes=sorted({w['address'] for p in r['paths'] for w in p['mmio_writes']
                                               if 'clock' in w['expression']}))


def analyse(loaders, sweep_step=1, symbolic=True):
    result = dict(format_version=1, tool='ddr_timing.py', function='0xb40673f4', reference_scenario=REFERENCE,
                  scenarios=de.SCENARIOS, sweep=dict(clocks=list(SWEEP), step=sweep_step), releases={})
    codes = set()
    first = None
    for name, data in loaders.items():
        code = de.check_code(data)
        codes.add(code)
        ini_off = de.INI_LOAD - de.BASE
        ini = dict(primary=asdict(ini_record(data, ini_off + 0x1C)), second=asdict(ini_record(data, ini_off + 0x4C)),
                   word_0x2c=int.from_bytes(data[ini_off + 0x2C:ini_off + 0x30], 'little'))
        em, rec, ret = unicorn_run(data)
        rows, m = register_table(data, em, rec)
        clocks = range(SWEEP[0], SWEEP[1] + 1, sweep_step)
        rel = dict(loader_sha256=hashlib.sha256(data).hexdigest(), code_sha256=code,
                   bootloader_ini=dict(primary_record=ini['primary'], second_record=ini['second'],
                                       word_0x2c=ini['word_0x2c'],
                                       selected='second' if ini['word_0x2c'] else 'primary',
                                       decode_matches_firmware_copy=all(
                                           {k: v for k, v in firmware_record(data, rec_name).param().items()
                                            if k in ini[key]} == ini[key]
                                           for rec_name, key in (('primary', 'primary'), ('second', 'second')))),
                   console=[p['text'] for p in em.prints], return_value=hex(ret),
                   ini_writeback={sc: (lambda r: dict(after=r['ini_primary_after_writeback'],
                                                      equals_shipped=r['ini_primary_after_writeback'] == r['ini_primary_as_shipped']))
                                  (de.emulate(data, scenario=sc)) for sc in sorted(de.SCENARIOS)},
                   ini_primary_as_shipped=data[ini_off + 0x1C:ini_off + 0x2C].hex(),
                   param_after=em.param(), instructions=em.insns,
                   timings=named_timings(m['timings']), final_pass=rows,
                   class_consistency=class_consistency(rows),
                   hardware_reads=[dict(site=r['site'], address=r['address'], value=r['value'], rule=r['rule'])
                                   for r in em.reads],
                   model_vs_unicorn=dict(
                       firmware_record_reference=model_vs_unicorn(data, clocks),
                       primary_record_reference=model_vs_unicorn(data, clocks[::7], record='primary'),
                       scenarios={s: model_vs_unicorn(data, clocks[::7], scenario=s) for s in sorted(de.SCENARIOS)},
                       reset_seeds={hex(s): model_vs_unicorn(data, clocks[::11], seed=s) for s in (0xFFFFFFFF, 0xA5A5A5A5)},
                       note='lists of clocks (MHz) where the model and Unicorn write sequences or console lines differ'))
        if symbolic:
            rel['symbolic'] = symbolic_summary(data, rec.clock_mhz)
        if first is None:
            first = data
        result['releases'][name] = rel
    result['identical_code_across_releases'] = len(codes) == 1
    result['division_helpers'] = division_helpers(first)
    # Cross-release: which final-pass values differ between releases
    names = list(result['releases'])
    diffs = []
    for i, row in enumerate(result['releases'][names[0]]['final_pass']):
        vals = {n: result['releases'][n]['final_pass'][i]['value'] for n in names}
        if len(set(vals.values())) > 1:
            diffs.append(dict(register=row['register'], site=row['site'], values=vals))
    result['cross_release_differences'] = diffs
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('output', type=Path)
    p.add_argument('--loader', action='append', default=[], help='NAME=PATH of a 448-sector loader region')
    p.add_argument('--image', action='append', default=[], help='NAME=PATH of a stock disk image (loader at 0x200200)')
    p.add_argument('--sweep-step', type=int, default=1)
    p.add_argument('--no-symbolic', action='store_true')
    a = p.parse_args()
    loaders = {}
    for spec in a.loader:
        n, path = spec.split('=', 1)
        loaders[n] = de.load_region(path)
    for spec in a.image:
        n, path = spec.split('=', 1)
        loaders[n] = de.load_region(path, LOADER_OFFSET)
    if not loaders:
        raise SystemExit('supply at least one --loader or --image')
    a.output.write_text(json.dumps(analyse(loaders, a.sweep_step, not a.no_symbolic), indent=1) + '\n')


if __name__ == '__main__':
    main()
