#!/usr/bin/env python3
"""Compare verified SD0/SD2 loader instructions in synthetic hardware, offline.

Reuses the PR #6 caller harness. The starting point supplies the state at
main's call site after the earlier storage/Boot ROM stages. Execute main's
caller dispatch and stop at its next-stage or recovery boundary.
"""
import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import gc
import json
from pathlib import Path

import adfu_analysis as adfu
import ddr_emulate as emu
import ddr_model as model
import dram_complete as dram
from gpio_model import C, C10, C11, DEFAULT_WINDOW, GpioModel
import predram_analysis as pre

FORMAT_VERSION = 1
TOOL_VERSION = 1
REFERENCE = 'koriki-v1.0'
RELEASES = (REFERENCE, 'stock-221203', 'stock-221223', 'stock-230309', 'stock-20231014')
MAIN_CALL = 0xB4065420
CALLER_RETURN = 0xB4065428
MAIN_LOAD = 0xB4065440
MAIN_RECOVERY = 0xB4065494
ADFU_RETURN = 0xB4066684
BOOT_CODE_LOAD = 0xB40664F4
BOOT_CODE_CALL_SITES = (0xB4066604, 0xB40692A0, 0xB406658C)
INI_SECOND_COPY = 0xB40666E0
AFI_DEVICE_STORE = 0xB4066538
RESUME_CALL_VECTOR = 0xB406706C
DEFAULT_LIMIT = 100_000
GPIO_LOOP_IO = {
    0xB40692B0: ('r', adfu.PULL1), 0xB40692C4: ('w', adfu.PULL1),
    0xB40692CC: ('r', C['inen']), 0xB40692D8: ('r', C['outen']),
    0xB40692E4: ('r', C['outen']), 0xB40692F0: ('w', C['outen']),
    0xB40692F8: ('r', C['inen']), 0xB4069304: ('w', C['inen']),
    0xB406930C: ('r', C['inen']), 0xB4069318: ('w', C['inen']),
    0xB4069320: ('r', C['outen']), 0xB406932C: ('w', C['outen']),
    0xB4069334: ('r', C['dat']), 0xB4069340: ('w', C['dat']),
    0xB4069348: ('r', C['dat']), 0xB406935C: ('w', C['dat']),
    0xB406936C: ('r', C['dat']),
    0xB4069394: ('w', C['inen']), 0xB40693A0: ('w', C['outen']),
}
PERSISTENT_GPIO = (adfu.PULL1, C['dat'], C['outen'], C['inen'])
POLL_LOOPS = {
    'dram-init-pgsr': (0xB4068704, 0xB4068714),
    'training-pgsr': (0xB40687A0, 0xB40687B8),
    'controller-config': (0xB406721C, 0xB4067230),
    'unsupported-pmic-version': (0xB4069F24, 0xB4069F30),
}
PHASES = {
    dram.FN['adfu_check']: 'before-adfu',
    ADFU_RETURN: 'after-adfu',
    dram.FN['mode0']: 'cold-entry',
    dram.FN['resume_entry']: 'resume-dispatch',
    dram.FN['mode1']: 'resume-entry',
    0xB4067FEC: 'controller-phy-programming',
    0xB40686DC: 'controller-phy-programmed',
    0xB4068794: 'training-request',
    0xB40687B8: 'training-passed',
    0xB40687D8: 'dfi-ready',
    0xB4068F20: 'training-dterr',
    0xB4068C44: 'capacity-probe',
    0xB4068E74: 'final-dcu-programming',
    0xB4068F08: 'final-dcu-programmed',
    dram.FN['memtest']: 'memory-test',
    dram.FN['writeback']: 'writeback',
    dram.FN['afi_code']: 'afi',
    dram.FN['selfrefresh_entry']: 'resume-self-refresh',
    dram.FN['alarm_rearm']: 'resume-alarm-rearm',
}
RETURN_PHASES = {
    0xB406671C: 'cold-return',
    0xB4066748: 'after-writeback',
    0xB406674C: 'caller-finishing',  # also the early resume return; AFI may be absent
}
FUNCTION_RANGES = (
    (MAIN_CALL, MAIN_RECOVERY + 4, 'main'),
    (0xB406631C, 0xB40663F8, 'memtest'),
    (0xB4066280, 0xB406631C, 'writeback'),
    (0xB40664F0, 0xB4066500, 'boot_code'),
    (0xB4066500, 0xB4066588, 'afi_write'),
    (0xB4066588, 0xB40665D0, 'afi_code'),
    (0xB40665D0, 0xB4066784, 'caller'),
    (0xB4066B64, 0xB4066BF0, 'prewake'),
    (0xB4066BF0, 0xB4066D90, 'power_off'),
    (0xB4066D90, 0xB4066EAC, 'rtc_add'),
    (0xB4066EAC, 0xB4066FD4, 'alarm_rearm'),
    (0xB4066FD4, 0xB4067094, 'resume_jump'),
    (0xB4067094, 0xB40670E8, 'resume_dispatch'),
    (0xB40670E8, 0xB4067170, 'dram_accessors'),
    (0xB4067170, 0xB4067248, 'pctl_state'),
    (0xB4067248, 0xB406735C, 'selfrefresh_entry'),
    (0xB406735C, 0xB40673F4, 'dmm_setup'),
    (0xB40673F4, 0xB40690B8, 'dram'),
    (0xB4069254, 0xB40693C0, 'adfu_check'),
    (0xB4069440, 0xB4069524, 'timer_helpers'),
    (0xB40699E8, 0xB406A1D0, 'pmu_init'),
    (0xB406A608, 0xB406A648, 'board_init'),
    (0xB406A648, 0xB406A758, 'board_mmio_helpers'),
)
CPU_REGISTERS = tuple(f'r{i}' for i in range(13)) + ('sp', 'lr', 'cpsr')
ADFU_CALL_CLOBBERS = ('r0', 'r1', 'r2', 'r3', 'r12', 'lr')
TRACE_FIELDS = ('phase', 'domain', 'op', 'address', 'width', 'value', 'pc', 'site', 'function', 'rule')
NORMALIZATION = {
    'gpio': 'Only the identified 32-bit MMIO accesses at the exact ADFU loopback accessor sites are omitted.',
    'boot_word': 'Only the verified getter load of the 32-bit boot-code word at 0xb4064c00 is canonicalized.',
    'afi': 'Only the AFI device byte store to 0xb4060305 at 0xb4066538 is canonicalized for 0x20/0x22.',
    'boundary_cpu': 'At normal ADFU return, report r0-r3, r12, lr and CPSR.NZCV as transient. '
                    'Require full sampled CPU equality at later shared boundaries.',
    'everything_else': 'Order, instruction and call sites, widths, read rules and run lengths are compared exactly.',
}


def serial(value, *, indent=None):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, indent=indent,
                      separators=(',', ':') if indent is None else None)


def digest(value):
    return hashlib.sha256(serial(value).encode('ascii')).hexdigest()


def word_map(values):
    return {hex(k): hex(v) for k, v in sorted(values.items())}


def differences(left, right):
    return {k: [left.get(k), right.get(k)] for k in sorted(left.keys() | right.keys())
            if left.get(k) != right.get(k)}


class Trace:
    """One hook-ordered stream, losslessly run-length encoded for repeated polls."""

    def __init__(self):
        self.runs = []
        self.count = 0

    def add(self, event, count=1):
        if self.runs and self.runs[-1][1] == event:
            n, _ = self.runs[-1]
            self.runs[-1] = (n + count, event)
        else:
            self.runs.append((count, event))
        self.count += count

    def summary(self):
        return {'events': self.count, 'sha256': digest(self.runs)}

    def normalized(self, code):
        out = Trace()
        excluded = Counter()
        for count, event in self.runs:
            phase, domain, op, address, width, value, pc, site, _, _ = event
            if (phase == 'before-adfu' and domain == 'mmio' and width == 4
                    and pc == (0xB406919C if op == 'r' else 0xB4069194)
                    and GPIO_LOOP_IO.get(site) == (op, address)):
                excluded['gpio'] += count
                continue
            if ((domain, op, address, width, pc, value) == ('sram', 'r', dram.BOOT_CODE, 4, BOOT_CODE_LOAD, code)
                    and site in BOOT_CODE_CALL_SITES):
                event = event[:5] + ('boot code',) + event[6:]
                excluded['boot_word'] += count
            if ((domain, op, address, width, pc, value)
                    == ('sram', 'w', dram.AFI + 5, 1, AFI_DEVICE_STORE, 0x20 + code)):
                event = event[:5] + ('AFI boot device',) + event[6:]
                excluded['afi'] += count
            out.add(event, count)
        return out, dict(excluded)


def first_difference(a, b):
    """Locate first unequal expanded event, including a missing event."""
    i = j = position = 0
    used_a = used_b = 0
    while i < len(a.runs) and j < len(b.runs):
        na, ea = a.runs[i]
        nb, eb = b.runs[j]
        if ea != eb:
            break
        count = min(na - used_a, nb - used_b)
        position += count
        used_a += count
        used_b += count
        if used_a == na:
            i += 1
            used_a = 0
        if used_b == nb:
            j += 1
            used_b = 0
    if i == len(a.runs) and j == len(b.runs):
        return None
    return dict(index=position,
                left=dict(zip(TRACE_FIELDS, a.runs[i][1])) if i < len(a.runs) else None,
                right=dict(zip(TRACE_FIELDS, b.runs[j][1])) if j < len(b.runs) else None)


class ComparisonHarness(dram.Harness):
    boot_word_rule = 'seeded boot word, loaded by firmware'

    def __init__(self, loader, case, boot_code, initial_mmio=None, budget=DEFAULT_LIMIT):
        from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE

        self.boot_code = boot_code
        self.budget = budget
        self.budget_start = 0
        self.ordered = Trace()
        self.phase = 'start'
        self.boundaries = []
        self.caller_return = self.core_return = self.memtest_return = None
        self.core_entry_event = self.core_end_event = self.core_lr = None
        self.written_mmio = set()
        self.internal_codes = []
        self.training = []
        self.afi_stores = []
        self.afi_writer_entered = self.afi_writer_returned = False
        self.ini_stores = []
        self.last_mmio_read = None
        self.loopback_word = None
        self.unsupported = Counter()
        self.adfu_arg = None
        self.record_selection = None
        self.initial_mmio = dict(case.initial_mmio)
        self.initial_mmio.update(initial_mmio or {})
        gpio_seed = dict(case.gpio_initial)
        gpio_seed.update({a: v for a, v in self.initial_mmio.items() if a in DEFAULT_WINDOW})
        gpio = GpioModel(initial=gpio_seed, inputs={C10: deepcopy(case.c10_rule)},
                         read_semantics=case.gpio_semantics, strict=False)
        super().__init__(loader, scenario=deepcopy(case.scenario), pmic=dram.Pmic(case.pmic),
                         ram=deepcopy(case.ram), gpio=gpio, boot_code=boot_code, limit=3 * budget + 48)
        for addr, value in self.initial_mmio.items():
            if addr & 3 or not emu.MMIO_BASE <= addr < emu.MMIO_BASE + emu.MMIO_SIZE or not 0 <= value <= 0xffffffff:
                raise ValueError(f'invalid MMIO seed {addr:#x}={value:#x}')
            if gpio.covers(addr) and addr not in gpio.regs:
                gpio.other[addr] = value
            self.regs[addr] = value
        for offset, data in case.ini_patch.items():
            if not 0 <= offset < offset + len(data) <= 0x60:
                raise ValueError(f'INI patch out of bounds at {offset:#x}')
            self.uc.mem_write(emu.INI_LOAD + offset, data)
        self.afi_before = case.afi_seed if case.afi_seed is not None else bytes(16)
        if len(self.afi_before) != 16:
            raise ValueError('AFI seed must be 16 bytes')
        self.uc.mem_write(dram.AFI, self.afi_before)
        self.ini_before = self.ini_records()
        self.stubs[dram.FN['pmic_read']] = ('PMIC read', lambda: self._pmic('r', case.pmic_errors))
        self.stubs[dram.FN['pmic_write']] = ('PMIC write', lambda: self._pmic('w', case.pmic_errors))
        self.stops = {MAIN_LOAD: 'main normal continuation', MAIN_RECOVERY: 'main recovery dispatch',
                      dram.FN['rom_reentry']: 'ADFU ROM routine entry', dram.POWER_OFF_PMIC: 'PMIC power-off boundary'}
        self.uc.hook_add(UC_HOOK_MEM_READ, self._boot_word, begin=dram.BOOT_CODE, end=dram.BOOT_CODE + 3)
        for base, size in ((dram.AFI, 16), (emu.INI_LOAD + 0x1C, 16)):
            self.uc.hook_add(UC_HOOK_MEM_WRITE, self._sram_write, begin=base, end=base + size - 1)

    def ini_records(self):
        ini = bytes(self.uc.mem_read(emu.INI_LOAD, 0x60))
        return {'primary': ini[0x1C:0x2C].hex(), 'secondary': ini[0x4C:0x5C].hex(),
                'selector': int.from_bytes(ini[0x2C:0x30], 'little')}

    def _snapshot(self, phase, pc):
        self.phase = phase
        regs = {**self.regs, **self.gpio.other, **self.gpio.regs}
        self.boundaries.append(dict(phase=phase, pc=hex(pc), event_index=self.ordered.count,
                                    boot_word=self.word(dram.BOOT_CODE),
                                    cpu={r: hex(self.reg(r)) for r in CPU_REGISTERS}, pmic=word_map(self.pmic.regs),
                                    gpio=word_map(self.gpio.regs), mmio=word_map(regs),
                                    flags=self.flags(), records=self.ini_records(),
                                    param=self.param(), param2=self.param(emu.PARAM2),
                                    afi=bytes(self.uc.mem_read(dram.AFI, 16)).hex(),
                                    pgsr=hex(self.pgsr), sctl_state=self.sctl_state))

    def _function(self, site):
        return next((name for start, end, name in FUNCTION_RANGES if start <= site < end), None)

    def _event(self, domain, op, address, width, value, rule=None, site=None):
        pc = self.reg('pc')
        site = pc if site is None else site
        self.ordered.add((self.phase, domain, op, address, width, value, pc, site, self._function(site), rule))

    def _boot_word(self, uc, access, address, size, value, user):
        value = int.from_bytes(uc.mem_read(address, size), 'little')
        self._event('sram', 'r', address, size, value, self.boot_word_rule,
                    self.reg('lr') - 4 if self.reg('pc') == BOOT_CODE_LOAD else None)

    def _sram_write(self, uc, access, address, size, value, user):
        dest = self.afi_stores if dram.AFI <= address < dram.AFI + 16 else self.ini_stores
        dest.append(self.ordered.count)
        pc = self.reg('pc')
        site = self.reg('lr') - 4 if 0xB406AF4C <= pc < 0xB406AF84 else pc
        self._event('sram', 'w', address, size, value & ((1 << (8 * size)) - 1), site=site)

    def _pmic(self, op, errors):
        reg = self.reg('r0') & 0xFF
        site = self.reg('lr') - 4
        if op == 'r':
            failed = reg in errors
            value = 0xFFFFFFFF if failed else self.pmic.read(reg)
            self._event('pmic', op, reg, 2, None if failed else value,
                        'injected I2C read error: accessor returns -1' if failed else 'synthetic PMIC register file',
                        site=site)
            return value
        value = self.reg('r1') & 0xffff
        self.pmic.write(reg, value)
        self._event('pmic', op, reg, 2, value, 'synthetic PMIC write, accessor succeeds', site=site)
        return 0

    def _oracle(self, addr):
        if self.gpio.covers(addr):
            value = self.gpio.read(addr, self.reg('pc'))
            if addr not in self.gpio.regs:
                return value, 'unsupported GPIO/pad semantics: per-address storage or zero'
            return value, f'synthetic GPIO ({self.gpio.read_semantics})'
        value, rule = super()._oracle(addr)
        if rule == 'last written value' and addr in self.initial_mmio and addr not in self.written_mmio:
            rule = 'explicit initial MMIO word (hypothesis)'
        return value, rule

    def _mmio_read(self, uc, access, address, size, value, user):
        super()._mmio_read(uc, access, address, size, value, user)
        read = self.reads[-1]
        v = (int(read['value'], 16) >> (8 * (address & 3))) & ((1 << (8 * size)) - 1)
        pc = self.reg('pc')
        site = self.reg('lr') - 4 if pc == 0xB406919C else int(read['site'], 16)
        self._event('mmio', 'r', address, size, v, read['rule'], site)
        self.last_mmio_read = self.ordered.runs[-1][1]
        if (read['rule'].startswith(('unsupported', 'reset seed', 'explicit initial')) or read['rule'] == 'done bit set'):
            self.unsupported[(address, read['rule'])] += 1

    def _mmio_write(self, uc, access, address, size, value, user):
        self.written_mmio.add(address & ~3)
        before = self.param() if address == emu.PIR and value & 0x80 else None
        super()._mmio_write(uc, access, address, size, value, user)
        pc = self.reg('pc')
        site = self.reg('lr') - 4 if pc == 0xB4069194 else int(self.writes[-1]['site'], 16)
        self._event('mmio', 'w', address, size, value & ((1 << (8 * size)) - 1), site=site)
        if before is not None:
            self.training.append(dict(pir=hex(value), pgsr_response=hex(self.pgsr),
                                      ranks=before['cs'], bus_sel=before['bus_sel'],
                                      width_bits=16 if before['bus_sel'] else 32, site=hex(site),
                                      source='synthetic PUBL response rule'))
        if self.gpio.covers(address) and (address & ~3) not in self.gpio.regs:
            self.unsupported[(address, 'unsupported GPIO/pad semantics: write to storage')] += 1

    def _phys(self, address):
        # The inherited PR #4 counter identifies column-probe accesses only in the
        # probing path. A preconfigured primary record can finish with two DCU
        # writes and no column probe. The diagnostic always spans per-rank RAM.
        if self.in_memtest:
            hw = self.hw
            bits = (1 if hw['width'] == 16 else 2) + hw['col_bits'] + hw['row_bits'] + hw['bank_log2']
            return address % (1 << bits)
        return super()._phys(address)

    def _dram_write(self, uc, access, address, size, value, user):
        super()._dram_write(uc, access, address, size, value, user)
        self._event('ram', 'w', address, size, value & ((1 << (8 * size)) - 1), self.dram_log[-1][3],
                    self._site(emu.F_STORE))

    def _dram_read(self, uc, access, address, size, value, user):
        super()._dram_read(uc, access, address, size, value, user)
        self._event('ram', 'r', address, size, self.dram_log[-1][2], self.reads[-1]['rule'], self._site(emu.F_LOAD))

    def _code(self, uc, address, size, user):
        if self.insns - self.budget_start >= self.budget:
            last = self.last_mmio_read
            poll = next((name for name, (lo, hi) in POLL_LOOPS.items() if lo <= address < hi), None)
            if poll is None and last and address in (emu.F_LOAD, emu.F_LOAD + 4):
                poll = next((name for name, (lo, hi) in POLL_LOOPS.items() if lo <= last[7] < hi), None)
            if poll is None and address == emu.F_PRINTF and self.reg('lr') == 0xB4069F2C:
                poll = 'unsupported-pmic-version'
            self.stopped = dict(kind='instruction limit', pc=hex(address), known_poll=poll)
            self.stopped['last_mmio_read'] = dict(zip(TRACE_FIELDS, last)) if last else None
            uc.emu_stop()
            return
        if address in (ADFU_RETURN, dram.FN['resume_entry']):
            self.budget_start = self.insns
        if address == dram.FN['adfu_check']:
            self.adfu_arg = self.reg('r0')
        if address == INI_SECOND_COPY:
            self.record_selection = 'secondary'
        if address in (dram.FN['mode0'], dram.FN['mode1']) and self.record_selection is None:
            self.record_selection = 'primary'
        if address == 0xB40693A8:
            self.loopback_word = self.reg('r5')
        if address == dram.FN['afi_write']:
            self.afi_writer_entered = True
        if address == 0xB406674C and self.afi_writer_entered:
            self.afi_writer_returned = True
        if address == CALLER_RETURN:
            self.caller_return = self.reg('r0')
        if address == dram.FN['dram']:
            self.core_entry_event = self.ordered.count
            self.core_lr = self.reg('lr')
        elif address == self.core_lr:
            self.core_end_event = self.ordered.count
            self.core_return = self.reg('r0')
            self.core_lr = None
        if address == 0xB4068F34:
            self.internal_codes.append(hex(self.reg('r1')))
        if address == 0xB4066744 and self.in_memtest:
            self.memtest_return = self.reg('r0')
            self._snapshot('after-memory-test', address)
        if address == RESUME_CALL_VECTOR:
            vector = self.reg('r3')
            if vector != dram.RESUME_VECTOR_SYNTH:
                self.stopped = dict(kind='unmodelled resume target', pc=hex(address), target=hex(vector))
                uc.emu_stop()
                return
            self.stops[vector] = 'synthetic resume vector (before target instruction)'
        phase = PHASES.get(address) or RETURN_PHASES.get(address)
        if phase:
            self._snapshot(phase, address)
        super()._code(uc, address, size, user)

    def core_writes(self):
        if self.core_entry_event is None:
            return []
        index = 0
        out = []
        for n, e in self.ordered.runs:
            end = self.core_end_event if self.core_end_event is not None else self.ordered.count
            count = min(index + n, end) - max(index, self.core_entry_event)
            if count > 0 and e[1:3] == ('mmio', 'w'):
                out.extend([(e[3], e[5])] * count)
            index += n
        return out

    def run_whole_caller(self):
        self._snapshot('start', MAIN_CALL)
        self.call(MAIN_CALL, r0=emu.INI_LOAD)
        self._snapshot('terminal', self.reg('pc'))
        return self

    def verdict(self):
        stop = self.stopped or {}
        name, kind = stop.get('name'), stop.get('kind')
        if kind == 'instruction limit':
            return 'bounded-unbounded-poll' if stop.get('known_poll') else 'instruction-limit'
        if kind == 'fault':
            return 'emulator-fault'
        if name == self.stops[MAIN_LOAD] and self.caller_return == 0 and self.core_return == 0:
            if self.memtest_return is None:
                return 'unmodelled-outcome'
            if self.memory_test()[0] == 'failed':
                return 'cold-success-diagnostic-failure'
            return 'cold-success' if self.memory_test()[0] == 'passed' else 'unmodelled-outcome'
        if name == self.stops[MAIN_RECOVERY] and self.caller_return is not None:
            return 'returned-dram-failure' if self.core_return not in (None, 0) else 'caller-rejected-ini'
        if name == self.stops[dram.FN['rom_reentry']]:
            return 'adfu-before-dram'
        if name == self.stops[dram.POWER_OFF_PMIC]:
            return 'resume-power-off'
        if name == self.stops.get(dram.RESUME_VECTOR_SYNTH) and name is not None:
            return 'resume-vector-transfer'
        return 'unmodelled-outcome'

    def memory_test(self):
        events = [(n, e) for n, e in self.ordered.runs if e[0] == 'memory-test' and e[1] == 'ram']
        lines = [p['text'] for p in self.prints if 'ddr_test' in p['text'] or p['text'] == '== ok==']
        status = 'passed' if '== ok==' in lines else ('failed' if any('ddr_test fail' in s for s in lines)
                                                     else ('incomplete' if self._memtest_lr else 'not-run'))
        return status, events, lines

    def result(self):
        afibytes = bytes(self.uc.mem_read(dram.AFI, 16))
        outcome = self.verdict()
        status, acc, prints = self.memory_test()
        entry = next((b for b in self.boundaries if b['phase'] in ('cold-entry', 'resume-entry')), None)
        observed = dict(
            boot_code=self.boot_code, boot_code_observed=self.word(dram.BOOT_CODE), outcome=outcome,
            caller_return=None if self.caller_return is None else hex(self.caller_return),
            dram_return=None if self.core_return is None else hex(self.core_return),
            terminal=self.stopped, main_continuation_boundary_reached=bool(
                self.stopped and self.stopped.get('name') == self.stops[MAIN_LOAD]),
            functions=dram._order([v['fn'] for v in self.trace]), flags=self.flags(),
            adfu=dict(argument=self.adfu_arg, loopback_word=None if self.loopback_word is None else hex(self.loopback_word),
                      completed=self.loopback_word is not None,
                      c10_samples=sum(n for n, e in self.ordered.runs if (e[0], e[1], e[7])
                                      == ('before-adfu', 'mmio', adfu.SITE_SAMPLE))),
            dram_entry=entry, record_selection=self.record_selection, record_final=self.param(),
            capacity_mib=self.param()['capacity_mib'] if self.core_return == 0 else None,
            ini_initial=self.ini_before,
            ini_final=self.ini_records(), ini_primary_stores=len(self.ini_stores),
            internal_codes=self.internal_codes, training=self.training,
            pir_requests=[w['value'] for w in self.writes if int(w['address'], 16) == emu.PIR],
            controller_commands=self.mmio_sequence((emu.SCTL, emu.MCMD)),
            dmm_cfg_writes=self.mmio_sequence((emu.DCU_CFG,)),
            status_reads={hex(a): self._status_summary(a) for a in (emu.PGSR, emu.ZQ0SR0, emu.DFISTSTAT0, emu.STAT,
                                                                    *emu.DXGSR0)},
            memory_test=dict(status=status, capacity_mib=self.param()['capacity_mib'] if self._memtest_lr else None,
                             return_register=None if self.memtest_return is None else hex(self.memtest_return),
                             reads=sum(n for n, e in acc if e[2] == 'r'),
                             writes=sum(n for n, e in acc if e[2] == 'w'), trace_sha256=digest(acc), prints=prints),
            afi=dict(before=self.afi_before.hex(), bytes=afibytes.hex(), decoded=dram.decode_afi(afibytes),
                     stores=len(self.afi_stores), changed=afibytes != self.afi_before,
                     generated=self.afi_writer_returned and bool(self.afi_stores)),
            gpio_final=word_map(self.gpio.regs), pmic_final=word_map(self.pmic.regs),
            selected_mmio_final=word_map({a: self.regs[a] for a in (emu.DCU_CFG, emu.PIR, emu.SCTL, 0xB01B00B4)
                                          if a in self.regs}),
            downstream_gpio_accesses=[dict(count=n, **dict(zip(TRACE_FIELDS, e))) for n, e in self.ordered.runs
                                      if e[0] not in ('start', 'before-adfu') and e[1] == 'mmio'
                                      and e[3] & ~3 in PERSISTENT_GPIO],
            synthetic_or_unmodelled=[dict(address=hex(a), rule=r, count=n)
                                      for (a, r), n in sorted(self.unsupported.items())],
            prints=dram._collapse([p['text'] for p in self.prints]),
            trace=self.ordered.summary(), instructions=self.insns,
        )
        return observed

    def mmio_sequence(self, addresses):
        return [[n, hex(e[3]), hex(e[5]), hex(e[7])] for n, e in self.ordered.runs
                if e[1:3] == ('mmio', 'w') and e[3] in addresses]

    def _status_summary(self, address):
        values = Counter()
        for n, e in self.ordered.runs:
            if e[1:4] == ('mmio', 'r', address):
                values[hex(e[5])] += n
        return dict(values)


@dataclass
class Case:
    name: str
    group: str
    scenario: dram.Scenario = field(default_factory=dram.Scenario)
    pmic: dict = field(default_factory=dict)
    pmic_errors: tuple = ()
    ini_patch: dict = field(default_factory=dict)
    ram: dram.Ram | None = None
    gpio_initial: dict = field(default_factory=dict)
    gpio_semantics: str = 'mixed'
    c10_rule: tuple = ('const', 0)
    initial_mmio: dict = field(default_factory=dict)
    afi_seed: bytes | None = None
    note: str = ''

    def inputs(self):
        out = asdict(self)
        out['ini_patch'] = {hex(k): v.hex() for k, v in self.ini_patch.items()}
        out['afi_seed'] = self.afi_seed.hex() if self.afi_seed is not None else None
        return out


def cases():
    """Return fresh scenario definitions on every invocation."""
    cold = [Case(s.name, 'cold', deepcopy(s)) for s in dram.TRAINING_SCENARIOS]
    cold.extend([
        Case('bus-auto-patched-record', 'cold', ini_patch={0x54: b'\x02'},
             note='Hypothetical secondary record advertises automatic bus width.'),
        Case('primary-record-selected', 'cold', ini_patch={0x2C: bytes(4)},
             note='Hypothetical selector 0 supplies primary geometry to the cold routine.'),
        Case('hypothetical-lpddr-record', 'cold', ini_patch={0x56: b'\x11'},
             note='Hypothetical secondary type changes the firmware programming branch.'),
        Case('config-guard-clear', 'cold', ini_patch={0x14: bytes(4)},
             note='Hypothetical INI GPIO guard is zero on both paths.'),
        Case('capacity-exponent-overflow', 'cold',
             dram.Scenario('capacity-exponent-overflow', width=32, ranks=2),
             ini_patch={0x54: b'\x00', 0x57: b'\xcc'},
             note='Hypothetical x32, dual-rank record forces geometry and takes the exponent >31 error.'),
    ])
    resume = [Case(name, 'resume', deepcopy(s), pmic=dram.resume_pmic(**pm).initial,
                   ini_patch=deepcopy(patch), note=note)
              for name, pm, s, patch, note in dram.RESUME_CASES]
    control = [
        Case('pmic-read-error', 'control', pmic_errors=(0x35,),
             note='At the accessor boundary supply -1 as the result of a synthetic I2C error.'),
        Case('gpio-exact-echo', 'control', c10_rule=('follow', C11),
             note='Exact synthetic pad echo requests ADFU for code 2. Code 0 skips GPIO.'),
        Case('invalid-ini-version', 'control', ini_patch={0: b'0.0\0'},
             note='Caller returns -1 and main dispatches toward recovery before DRAM.'),
    ]
    faults = [
        Case('memory-test-small-alias', 'memory', ram=dram.Ram('wrap', 128 << 20)),
        Case('memory-test-open-tail', 'memory', ram=dram.Ram('open', 128 << 20)),
        Case('memory-test-dropped-write', 'memory', ram=dram.Ram(write_drop=(0x10,))),
        Case('memory-test-stuck-bit', 'memory', ram=dram.Ram(stuck_low=1 << 20)),
        Case('memory-test-read-error', 'memory', ram=dram.Ram(read_xor={0x10: 1})),
    ]
    all_ones = {a: 0xffffffff for a in DEFAULT_WINDOW}
    mixed = {adfu.PULL1: 0xA5020040, C['dat']: 0x34120C55, C['outen']: 0x43210055, C['inen']: 0x842108AA}
    gpio = [
        Case('all-ones-gpio-mixed', 'gpio', gpio_initial=all_ones),
        Case('mixed-gpio-latch', 'gpio', gpio_initial=mixed, gpio_semantics='latch', c10_rule=('follow', C11)),
        Case('mixed-gpio-bus-retry', 'gpio', gpio_initial=mixed, c10_rule=('invert', C11),
             ini_patch={0x54: b'\x02'}, initial_mmio={0xB01B00B4: 0xA5001234}),
        Case('mixed-gpio-resume', 'gpio', gpio_initial=mixed, pmic=dram.resume_pmic().initial),
        Case('mixed-gpio-training-failure', 'gpio', gpio_initial=mixed,
             scenario=dram.Scenario('mixed-gpio-training-failure', training=[False, False])),
        Case('mixed-gpio-near-echo', 'gpio', gpio_initial=mixed, c10_rule=('follow_except', C11, {31: 1})),
    ]
    # Representative classes chosen before running the paired experiment. The baseline
    # separately enumerates all 180 classes on the isolated routine.
    geometry = []
    for order, col, row, banks, ranks in [
        ('col-bank-row', 10, 14, 3, 1), ('col-bank-row', 10, 14, 2, 1),
        ('col-bank-row', 10, 12, 3, 1), ('col-bank-row', 10, 13, 3, 1),
        ('col-bank-row', 10, 14, 3, 2), ('col-row-bank', 10, 14, 3, 1),
        ('bank-col-row', 10, 14, 3, 1), ('col-row-bank', 11, 16, 3, 2),
        ('col-bank-row', 12, 17, 3, 1),
    ]:
        name = f'{order}-c{col}-r{row}-b{1 << banks}-cs{ranks}'
        dev = dram.DmmDevice(col, row, banks, ranks, dram.ORDERS[order])
        s = dram.Scenario(name, col_bits=col, row_bits=row, bank_log2=banks, ranks=ranks)
        geometry.append(Case(name, 'geometry', s, ram=dram.Ram('dmm', device=dev, float_value=0)))
    return cold + resume + control + faults + gpio + geometry


def execute(loader, case, boot_code, initial_mmio=None, budget=DEFAULT_LIMIT):
    if boot_code not in (0, 2):
        raise ValueError('boot code must be 0 or 2')
    if len(loader) < emu.BL_SIZE:
        raise ValueError('loader region is truncated')
    if budget <= 0:
        raise ValueError('instruction budget must be positive')
    harness = ComparisonHarness(loader, case, boot_code, initial_mmio, budget).run_whole_caller()
    return harness.result(), harness


def compare_boundaries(left, right, *, compact=False, cross_release=False):
    out = []
    for i in range(max(len(left), len(right))):
        a = left[i] if i < len(left) else {}
        b = right[i] if i < len(right) else {}
        phase = a.get('phase') or b['phase']
        row = dict(phase=phase, raw_sha256=[digest(a), digest(b)])
        expected = {}
        da, db = dict(a), dict(b)
        if a and b and a['phase'] == b['phase']:
            for key in ('boot_word', 'event_index'):
                if a[key] != b[key]:
                    expected[key] = [a[key], b[key]]
                    da.pop(key)
                    db.pop(key)
            if not cross_release:
                if phase == 'after-adfu':
                    ca, cb = dict(a['cpu']), dict(b['cpu'])
                    transient = differences(ca, cb)
                    for reg, (x, y) in transient.items():
                        changes_nzcv_only = reg == 'cpsr' and (int(x, 16) ^ int(y, 16)) & 0x0FFFFFFF == 0
                        if reg in ADFU_CALL_CLOBBERS or changes_nzcv_only:
                            expected.setdefault('transient_cpu', {})[reg] = [x, y]
                            del ca[reg], cb[reg]
                    da['cpu'], db['cpu'] = ca, cb
                for key in ('gpio', 'mmio'):
                    ma, mb = dict(a[key]), dict(b[key])
                    for addr in PERSISTENT_GPIO:
                        addr = hex(addr)
                        if addr in ma and addr in mb and ma[addr] != mb[addr]:
                            expected.setdefault(key, {})[addr] = [ma[addr], mb[addr]]
                            # COUTEN and CINEN must be restored on normal continuation.
                            if int(addr, 16) in (adfu.PULL1, C['dat']):
                                del ma[addr], mb[addr]
                    da[key], db[key] = ma, mb
                raw_a, raw_b = bytes.fromhex(a['afi']), bytes.fromhex(b['afi'])
                if raw_a[:5] + raw_a[6:] == raw_b[:5] + raw_b[6:] and raw_a[5] == 0x20 and raw_b[5] == 0x22:
                    expected['afi_boot_device'] = ['0x20', '0x22']
                    da.pop('afi')
                    db.pop('afi')
        if not a or not b or a['phase'] != b['phase']:
            changed = {'phase_alignment': [a.get('phase'), b.get('phase')]}
        else:
            changed = differences(da, db)
            for key in ('cpu', 'mmio', 'gpio', 'pmic'):
                if key in changed:
                    changed[key] = differences(da[key], db[key])
        row.update(expected=expected, remaining=changed)
        if not compact:
            row['state'] = [a, b]
        out.append(row)
    return out


def compare_runs(a, h0, b, h2, *, compact=False):
    n0, x0 = h0.ordered.normalized(0)
    n2, x2 = h2.ordered.normalized(2)
    first = first_difference(n0, n2)
    raw_first = first_difference(h0.ordered, h2.ordered)
    selected = ('outcome', 'caller_return', 'dram_return', 'terminal', 'main_continuation_boundary_reached',
                'flags', 'record_selection', 'record_final', 'capacity_mib', 'ini_initial', 'ini_final', 'ini_primary_stores', 'functions',
                'internal_codes', 'training', 'pir_requests', 'memory_test', 'pmic_final', 'selected_mmio_final',
                'downstream_gpio_accesses', 'synthetic_or_unmodelled', 'status_reads', 'controller_commands',
                'dmm_cfg_writes', 'prints')
    changes = differences({key: a[key] for key in selected}, {key: b[key] for key in selected})
    states = compare_boundaries(h0.boundaries, h2.boundaries, compact=compact)
    afi_a, afi_b = a['afi'], b['afi']
    afi_changes = [i for i, (x, y) in enumerate(zip(bytes.fromhex(afi_a['bytes']), bytes.fromhex(afi_b['bytes'])))
                   if x != y]
    expected_afi = afi_a['generated'] and afi_b['generated'] and afi_changes == [5] and (
        afi_a['decoded']['boot_dev'], afi_b['decoded']['boot_dev']) == (0x20, 0x22)
    if (afi_changes and not expected_afi) or afi_a['stores'] != afi_b['stores'] or afi_a['generated'] != afi_b['generated']:
        changes['afi'] = [afi_a, afi_b]
    gpio0, gpio2 = a['adfu'], b['adfu']
    boot_reads = [[dict(site=hex(e[7]), value=e[5]) for n, e in h.ordered.runs for _ in range(n)
                   if (e[1], e[2], e[3], e[6]) == ('sram', 'r', dram.BOOT_CODE, BOOT_CODE_LOAD)]
                  for h in (h0, h2)]
    proven = True
    for run, reads, code in zip((a, b), boot_reads, (0, 2)):
        want = [hex(BOOT_CODE_CALL_SITES[0])]
        if run['adfu']['argument'] and (run['outcome'] != 'adfu-before-dram' or run['adfu']['completed']):
            want.append(hex(BOOT_CODE_CALL_SITES[1]))
        if run['afi']['generated']:
            want.append(hex(BOOT_CODE_CALL_SITES[2]))
        proven &= run['boot_code'] == run['boot_code_observed'] == code and reads == [
            dict(site=site, value=code) for site in want]
    return dict(raw_first=raw_first, normalized_first=first, normalized_trace=[n0.summary(), n2.summary()],
                normalization_counts=[x0, x2], boot_code_reads=boot_reads, boot_code_provenance_ok=proven,
                boundaries=states, result_differences=changes, afi_byte_offsets_changed=afi_changes,
                expected_afi_boot_device_difference=expected_afi,
                gpio_state_differences=differences(a['gpio_final'], b['gpio_final']),
                same_after_expected_differences=(
                    proven and first is None and not changes and not any(s['remaining'] for s in states)
                    and not gpio0['completed'] and (not gpio2['completed'] or gpio2['c10_samples'] == 32)
                ))


def memory_model_comparison(result, h, case):
    if result['memory_test']['status'] not in ('passed', 'failed') or (case.ram and case.ram.kind == 'dmm'):
        return None
    ram = case.ram or dram.Ram(size=(1 << (1 if case.scenario.width == 16 else 2)
                                    + case.scenario.col_bits + case.scenario.row_bits + case.scenario.bank_log2))
    lines, expected, verdict = dram.memtest_model(result['memory_test']['capacity_mib'], ram)
    _, events, actual_lines = h.memory_test()
    actual = [(e[2], e[3], e[5]) for n, e in events for _ in range(n)]
    change = next((dict(index=i, firmware=actual[i] if i < len(actual) else None,
                        model=expected[i] if i < len(expected) else None)
                   for i in range(max(len(actual), len(expected)))
                   if i >= len(actual) or i >= len(expected) or actual[i] != expected[i]), None)
    return dict(matches=change is None and lines == actual_lines, first_access_difference=change,
                model_verdict=verdict, model_prints=lines, model_access_count=len(expected),
                formula='word_count=(MiB<<18) modulo 2^32; powers-of-two word indices from 4, '
                        'then 0x10 + k*0x41114; byte address is 4*word index')


def core_model_comparison(result, h, case):
    entry = result['dram_entry']
    if not entry or case.scenario.training != 'geometry' or case.ram or entry['phase'] not in ('cold-entry', 'resume-entry'):
        return None
    s = case.scenario
    if not (s.zq_done and s.phy_init_done and s.dram_init_done and s.dfi_ready) or s.stat_stuck is not None:
        return None
    if (case.group not in ('cold', 'resume') or (s.col_bits, s.row_bits) != (10, 14)
            or entry['param']['type'] & 0xf or case.name == 'resume-cs-zero'):
        return None
    mode = int(entry['phase'] == 'resume-entry')
    # Slice by execution boundaries so subsequent resume self-refresh cannot enter the core comparison.
    core = h.core_writes()
    rec = model.Record.from_bytes(bytes.fromhex(entry['param']['raw']))
    hw = model.Hardware(ranks=s.ranks, width=s.width, reset=model.ResetAll(s.reset_seed))
    hw.reset.update({int(a, 16): int(v, 16) for a, v in entry['mmio'].items()})
    expected = model.run(rec, hw, mode=mode)
    writes = [(w.address, w.value) for w in expected['writes']]
    change = next((dict(index=i, firmware=core[i] if i < len(core) else None,
                        model=writes[i] if i < len(writes) else None)
                   for i in range(max(len(core), len(writes)))
                   if i >= len(core) or i >= len(writes) or core[i] != writes[i]), None)
    param = expected.get('param_after')
    final = result['record_final']
    state_matches = None if param is None else all(final.get(k) == v for k, v in param.items())
    return dict(mode=mode, writes_match=change is None, first_write_difference=change, firmware_writes=len(core),
                final_record_matches=state_matches,
                model_writes=len(writes), model_return=expected['result'],
                model_final_record=expected.get('param_after'), model_timing=expected.get('packed'),
                shared_inputs='record and observed-at-entry register seeds, synthetic training geometry, '
                              'known reference column and row probe codes')


def gpio_model_comparison(result, h, case, constants):
    before = next((b for b in h.boundaries if b['phase'] == 'before-adfu'), None)
    if before is None:
        return None
    relevant = Trace()
    expected = []
    reg = constants['status_register']
    hypothesis = adfu.reference_model(
        constants, result['boot_code'], result['adfu']['argument'], int(before['pmic'].get(hex(reg), '0'), 16),
        {int(k, 16): int(v, 16) for k, v in before['gpio'].items()}, case.c10_rule, case.gpio_semantics,
        pmic_fail=reg in case.pmic_errors, observe=lambda op, a, v: expected.append((op, a, v)))
    actual = []
    pmic = []
    for n, e in h.ordered.runs:
        if e[0] != 'before-adfu':
            continue
        if e[1] == 'pmic' and e[2] == 'w':
            pmic.extend([dict(reg=e[3], value=e[5])] * n)
        if e[1] == 'mmio' and (e[3] & ~3) in PERSISTENT_GPIO:
            relevant.add(e, n)
            actual.extend([(e[2], e[3], e[5])] * n)
    checks = dict(
        ordered_gpio=actual == expected,
        received_word=result['adfu']['loopback_word'] == (
            hex(hypothesis['received']) if hypothesis['received'] is not None else None),
        pmic_writes=pmic == hypothesis['pmic_writes'],
        decision=(result['outcome'] == 'adfu-before-dram') == hypothesis['decision'].startswith('adfu'),
        directions_and_latches=all(result['gpio_final'][hex(int(a, 16))] == hex(int(v, 16))
                                   for a, v in hypothesis['final'].items()),
    )
    first = next((dict(index=i, firmware=actual[i] if i < len(actual) else None,
                       model=expected[i] if i < len(expected) else None)
                  for i in range(max(len(actual), len(expected)))
                  if i >= len(actual) or i >= len(expected) or actual[i] != expected[i]), None)
    return dict(agree=all(checks.values()), decision=hypothesis['decision'], checks=checks,
                gpio_trace=relevant.summary(), first_gpio_difference=first)


def validate_return(result):
    if result['dram_return'] is None or not result['internal_codes']:
        return None
    code = int(result['internal_codes'][-1], 16)
    expected = hex(dram.returned_code(code))
    return dict(internal=hex(code), expected=expected, matches=result['dram_return'] == expected)


HASH_REGIONS = {
    'main-dispatch-and-literals': (0xB4065400, 0xB40654A4),
    'ini-decode-writeback-memtest': (0xB4065FF8, 0xB40663F8),
    'resume-entry-boot-code-afi-caller': (0xB40664E4, 0xB4066784),
    'resume-dispatch-and-power-path': (0xB4066B64, 0xB40670E8),
    'dram-core-wrappers-and-afi-size': (0xB40670E8, 0xB4069194),
    'adfu-and-timer': (0xB4069194, 0xB4069524),
    'pmic-board-and-accessors': (0xB4069524, 0xB406AF4C),
    'shared-memset-memcpy-and-loader-tables': (0xB406AF4C, 0xB406BC00),
}
INSTRUCTION_ANCHORS = {
    MAIN_CALL: ('mov', 'r1, #0'),
    MAIN_CALL + 4: ('bl', '#0xb40665d0'),
    CALLER_RETURN: ('cmp', 'r0, #0'),
    MAIN_LOAD: ('bl', '#0xb4065fc0'),
    MAIN_RECOVERY: ('bl', '#0xb4065fdc'),
    0xB4066680: ('bl', '#0xb4069254'),
    0xB4066684: ('bl', '#0xb406622c'),
    INI_SECOND_COPY: ('bl', '#0xb406af64'),
    0xB4066718: ('bl', '#0xb40690b8'),
    0xB4066740: ('bl', '#0xb406631c'),
    0xB4066744: ('bl', '#0xb4066280'),
    0xB4066748: ('bl', '#0xb4066588'),
    0xB40665CC: ('b', '#0xb4066500'),
    BOOT_CODE_LOAD: ('ldr', 'r0, [r3, #0xc00]'),
    AFI_DEVICE_STORE: ('strb', 'r5, [r6, #0x305]'),
    RESUME_CALL_VECTOR: ('blx', 'r3'),
    0xB4068708: ('bl', '#0xb40670f0'),
    0xB40687A4: ('bl', '#0xb40670f0'),
    0xB4068F34: ('ldr', 'r3, [pc, #-0x9e4]'),
}
SOURCES = {
    'rk3288_uboot_pin': '9d67454e920b3908529c9fc642a8c911db040896',
    'rk3288_register_file': 'arch/arm/include/asm/arch-rockchip/ddr_rk3288.h',
    'rk3288_ddr_source': 'drivers/ram/rockchip/sdram_rk3288.c',
    'rk3288_ddr_source_sha256': '104f12d537fbf56df331483316b1a9f616d21a338f805d414b1131ded8070780',
    'microchip_analog': 'https://onlinedocs.microchip.com/oxy/GUID-82119957-1E11-4B69-84AC-EF0EA08F5595-en-US-5/'
                         'GUID-17C1D14E-6C75-4D58-95E6-CE141F571720.html',
    'assessment': 'RK3288 shares PIR/PGSR offsets and requests DRAMRST with DRAMINIT during DDR3 cold boot. '
                  'The Microchip SAMA7D6 register manual documents independent DDR3 reset for its PHY with the same bit '
                  'numbers. Neither establishes the ATM7039S PHY revision or its reset-output behaviour.',
}
ASSUMPTIONS = {
    'start': 'main 0xb4065420 after storage load and global clearing; r0=INI SRAM, r1 set by actual instructions',
    'boot_code': 'Seeded at SRAM 0xb4064c00 before execution. The Boot ROM and block 0 are outside this run.',
    'clock': 'Timer initialization executes. Busy-wait and UART/printf are stubbed; GPIO time advances by requested delay.',
    'pmic': 'PMIC detection and transport are stubbed. The register file, successful writes and injected -1 reads '
            'represent assumptions at the accessor boundary, not I2C electrical behaviour.',
    'dram': 'Each run has fresh synthetic PUBL/uPCTL state and sparse RAM. A wrap model answers the probe and '
            'defaults to per-rank wrap in the diagnostic; explicit DMM models apply to both. Other RAM variants '
            'apply to the diagnostic only. Training/DFI/PGSR/STAT/ZQ responses are synthetic.',
    'gpio': GpioModel.assumptions(),
    'passthrough': 'Unimplemented GPIO/pad addresses return per-address seeded/last-written storage or zero; '
                   'other fallback MMIO reads return register-file values, an explicit word or a synthetic reset seed. '
                   'Undefined effects are visible in the trace and summaries.',
    'bounds': 'Separate instruction budgets from entry, after normal ADFU return and after resume dispatch. '
              'Expiry is named a firmware poll only at verified loop sites, including accessor/printf calls from them.',
    'exits': 'Stop before app/U-Boot load, main recovery body, ADFU ROM routine, PMIC power-off or first instruction '
             'at 0x00108000. Any other resume target stops at the call instruction.',
    'initial_afi': 'AFI scratch is zero-seeded by default because the real ROM-provided state is unknown. '
                   'AFI stores and before/after bytes are captured independently of each other.',
    'comparison': 'Ordered stream contains MMIO, emulator-side PMIC accessor responses, RAM accesses and watched '
                  'SRAM evidence. It does not reconstruct bus timing or a full CPU instruction trace.',
}
UNRESOLVED = [
    'Boot ROM-provided register, pad, clock/reset, SRAM and stack state for each boot medium.',
    'Actual TF2 wiring, pad input/latch behaviour and pin-multiplexer priority; possible electrical coupling.',
    'Actual PMIC version, status, regulator voltages and wake behavior; synthetic I2C responses.',
    'Actual electrical training outcomes, impedance, memory part/rank, DMM order/alias responses and data retention.',
    'C-RESUME-DRAMRST: actual revision and independent reset-pin behavior when PIR writes 0x3f.',
    'App-side persistence, U-Boot consumption and a second live AFI capture are outside caller execution.',
]


def load_release(directory, release, *, stream=None):
    if release not in RELEASES:
        raise ValueError(f'unknown release {release}')
    path = Path(directory) / f'{release}.img'
    loader, identity = pre.load_image(path, stream=stream)
    if stream is None:
        image_size = path.stat().st_size
    else:
        stream.seek(0, 2)
        image_size = stream.tell()
    if image_size != identity['expected_size'] or len(loader) != pre.LOADER_SIZE:
        raise ValueError(f'{release}: verified image or extracted loader length is unexpected')
    code = pre.Code(loader)
    for pc, expected in INSTRUCTION_ANCHORS.items():
        insn = code.insn(pc)
        if insn is None or (insn.mnemonic, insn.op_str) != expected:
            raise ValueError(f'{release}: instruction anchor differs at {pc:#x}')
    if code.word(BOOT_CODE_LOAD + 8) + 0xC00 != dram.BOOT_CODE:
        raise ValueError(f'{release}: boot-code getter literal does not point to 0xb4064c00')
    for pc, (op, _) in GPIO_LOOP_IO.items():
        if pre.imm_target(code.insn(pc)) != (0xB406919C if op == 'r' else 0xB4069194):
            raise ValueError(f'{release}: GPIO accessor anchor differs at {pc:#x}')
    identity.update(release=release, verified_size=image_size,
                    regions={k: dict(start=hex(a), end_exclusive=hex(b), sha256=pre.sha(code.bytes(a, b)))
                             for k, (a, b) in HASH_REGIONS.items()},
                    function_hashes=dram.code_hashes(loader), config=pre.ini_inputs(code))
    return loader, code, identity


def pair(loader, code, case, *, initial_mmio=None, budget=DEFAULT_LIMIT, detail=False):
    runs, harnesses, models = {}, {}, {}
    constants = adfu.decoded_constants(code)
    for bc in (0, 2):
        result, h = execute(loader, case, bc, initial_mmio, budget)
        runs[str(bc)], harnesses[str(bc)] = result, h
        models[str(bc)] = dict(gpio=gpio_model_comparison(result, h, case, constants),
                               memory_test=memory_model_comparison(result, h, case),
                               dram_core=core_model_comparison(result, h, case),
                               failure_mapping=validate_return(result))
    a, b = runs['0'], runs['2']
    h0, h2 = harnesses['0'], harnesses['2']
    comparison = compare_runs(a, h0, b, h2, compact=not detail)
    comparison['gpio_reference_agreement'] = all(m['gpio'] is None or m['gpio']['agree'] for m in models.values())
    comparison['same_after_expected_differences'] &= comparison['gpio_reference_agreement']
    out = dict(runs=runs, comparison=comparison, independent_models=models)
    if detail:
        out['raw_ordered_trace_rle'] = {bc: h.ordered.runs for bc, h in harnesses.items()}
        out['trace_fields'] = TRACE_FIELDS
    return out, harnesses


def count_trace_by_site(trace):
    output = {}
    for n, e in trace.runs:
        phase, domain, op, address, width, value, pc, site, _, rule = e
        key = (phase, domain, op, address, width, pc, site, rule)
        output.setdefault(key, Counter())[value] += n
    return output


def release_trace_difference(a, b):
    """Cross-release raw deltas, including a first ordered difference and all value/count changes."""
    first = first_difference(a, b)
    if first is None:
        return None
    left, right = count_trace_by_site(a), count_trace_by_site(b)
    changes = []
    for key in sorted(left.keys() | right.keys(), key=serial):
        x, y = left.get(key, {}), right.get(key, {})
        if x != y:
            changes.append(dict(site_key=key, reference=dict(x), release=dict(y)))
    return dict(first=first, changed_site_values=changes)


def cross_release_change(reference, candidate, reference_traces, candidate_traces):
    groups = {}
    for bc in ('0', '2'):
        a, b = reference['runs'][bc], candidate['runs'][bc]
        change = release_trace_difference(reference_traces[bc], candidate_traces[bc])
        if change:
            groups[bc] = change
        state = differences(
            {k: a[k] for k in ('record_final', 'ini_final', 'afi', 'outcome', 'caller_return', 'dram_return', 'terminal',
                               'record_selection', 'memory_test', 'training', 'prints', 'instructions')},
            {k: b[k] for k in ('record_final', 'ini_final', 'afi', 'outcome', 'caller_return', 'dram_return', 'terminal',
                               'record_selection', 'memory_test', 'training', 'prints', 'instructions')},
        )
        if state:
            groups.setdefault(bc, {})['result_fields'] = state
    return groups


def geometry_comparison(loader, executed):
    baseline = dram.geometry_study(loader)
    outcome_key = lambda r: (r['return_value'], r['reported_capacity_mib'], r['rcc'], r['cs'], r['memtest_last_line'])
    counts = Counter(map(outcome_key, baseline['runs']))
    baseline['observable_outcome_classes'] = [
        dict(return_value=k[0], reported_mib=k[1], rcc=k[2], cs=k[3], diagnostic=k[4], hypotheses=n)
        for k, n in sorted(counts.items(), key=lambda v: serial(v[0]))]
    baseline['method'] = 'Isolated mode 0: run ini copy, supply selected record, invoke DRAM core wrapper, ' \
                         'then explicitly call write-back and the diagnostic when mode 0 succeeds.'
    baseline['paired_checks'] = {}
    for case, rows in executed:
        d = case.ram.device
        isolated = next((r for r in baseline['runs'] if tuple(d.order) == dram.ORDERS[r['order']]
                         and (r['col_bits'], r['row_bits'], r['banks'], r['ranks'])
                         == (d.col_bits, d.row_bits, 1 << d.bank_log2, d.ranks)), None)
        baseline['paired_checks'][case.name] = dict(
            model_mib=((1 << (1 + d.col_bits + d.row_bits + d.bank_log2)) * d.ranks) >> 20,
            isolated=None if isolated is None else list(outcome_key(isolated)),
            caller={bc: [r['dram_return'], r['capacity_mib'], hex(r['record_final']['rcc']), r['record_final']['cs'],
                         r['memory_test']['prints'][-1] if r['memory_test']['prints'] else None]
                    for bc, r in rows.items()})
    return baseline


def obs_reconciliation(reference):
    obs = json.loads((pre.ROOT / 'evidence/observations/OBS-001.json').read_text(encoding='utf-8'))
    previous = json.loads((pre.ROOT / 'evidence/firmware/koriki-v1.0-boot-path.json').read_text(encoding='utf-8'))
    facts = next(p['values'] for p in obs['predictions'] if p['id'] == 'P-BOOTDEV')
    quant = obs['summary']['memory_model']['quantities']
    q = reference['runs']['2']
    projected = dram.uboot_ram_size(q['afi']['decoded']) if q['main_continuation_boundary_reached'] else None
    return dict(observation='OBS-001', controller=f"0x{facts['boot_controller']}", boot_dev=facts['boot_dev'],
                boot_disk=facts['boot_disk'], kernel_command_line=obs['summary']['cmdline']['raw'],
                device_tree_banks=quant['device_tree_banks'], kernel_system_ram_bytes=quant['kernel_system_ram_bytes'],
                kernel_memory_line=quant['kernel_memory_line'], memtotal_kib=quant['memtotal_kB'],
                vendor_reserved_mib=quant['vendor_reserved_MB'],
                reconstructed_afi_boot_device=q['afi']['decoded']['boot_dev'],
                projected_memory_property=projected['memory_reg'] if projected else None,
                memory_property_matches=projected is not None and quant['device_tree_banks'] == [
                    {'base': projected['memory_reg'][0], 'size': projected['memory_reg'][1]}],
                previous_command_line_agrees=obs['summary']['cmdline']['raw'] == previous['observed_cmdline'],
                code_2_basis='Earlier pinned-image reconstruction reproduces the complete captured command line. '
                             'OBS-001 exposes the Linux boot layer, and does not directly measure the boot-code word.',
                unavailable=['live AFI', 'physical DRAM rank count and geometry', 'training status',
                             'PMIC voltage', 'Boot ROM state', 'early serial output'])


def build_evidence(directory):
    all_cases = cases()
    doc = dict(format_version=FORMAT_VERSION, tool='sd2_dram_analysis.py', tool_version=TOOL_VERSION,
               tool_versions=pre.tool_versions(), reference_release=REFERENCE, releases={}, distinct_pairs={},
               cross_release={}, scenarios={c.name: c.inputs() for c in all_cases}, model_assumptions=ASSUMPTIONS,
               normalization=NORMALIZATION, trace_fields=TRACE_FIELDS, default_instruction_budget=DEFAULT_LIMIT,
               instruction_anchors={hex(k): v for k, v in INSTRUCTION_ANCHORS.items()}, sources=SOURCES,
               unresolved=UNRESOLVED,
               reproduction='python tools/sd2_dram_analysis.py evidence --firmware-dir FW OUT.json')
    reference = {}
    geometry = []
    for release in RELEASES:
        loader, code, identity = load_release(directory, release)
        identity['pairs'] = {}
        doc['releases'][release] = identity
        variant_differences = {}
        for case in all_cases:
            result, harnesses = pair(loader, code, case)
            traces = {bc: h.ordered for bc, h in harnesses.items()}
            del harnesses
            gc.collect()  # release Unicorn hook cycles and their mapped pages between cases
            key = digest(result)
            doc['distinct_pairs'].setdefault(key, result)
            identity['pairs'][case.name] = key
            if release == REFERENCE:
                reference[case.name] = (result, traces)
                if case.group == 'geometry':
                    geometry.append((case, result['runs']))
            elif key != doc['releases'][REFERENCE]['pairs'][case.name]:
                base, base_harnesses = reference[case.name]
                variant_differences[case.name] = cross_release_change(base, result, base_harnesses, traces)
        if release == REFERENCE:
            doc['static_gpio_address_scan'] = adfu.downstream_static({'code': code})
            doc['geometry'] = geometry_comparison(loader, geometry)
            doc['obs_001'] = obs_reconciliation(reference['reference'][0])
        else:
            base = doc['releases'][REFERENCE]
            doc['cross_release'][release] = dict(
                same_bootloader_region=identity['bootloader_code_sha256'] == base['bootloader_code_sha256'],
                same_function_and_literal_regions=identity['regions'] == base['regions'],
                same_block0=identity['block0_sha256'] == base['block0_sha256'],
                config_changes=differences(base['config'], identity['config']),
                changed_pairs=variant_differences,
                exact_pair_matches=len(all_cases) - len(variant_differences),
                execution='Both boot codes were independently executed for every listed scenario.',
            )
    return doc


def evidence_bytes(doc):
    """Keep one independently addressable pair per line in the generated evidence."""
    lines = []
    for key in sorted(doc):
        if key in ('distinct_pairs', 'cross_release', 'scenarios'):
            rows = ',\n'.join(f'  {serial(k)}: {serial(v)}' for k, v in sorted(doc[key].items()))
            val = '{\n' + rows + '\n }'
        else:
            val = serial(doc[key])
        lines.append(f' {serial(key)}: {val}')
    return ('{\n' + ',\n'.join(lines) + '\n}\n').encode('ascii')


def parse_seed(raw):
    try:
        k, v = raw.split('=', 1)
        return int(k, 0), int(v, 0)
    except ValueError as e:
        raise argparse.ArgumentTypeError('expected ADDRESS=WORD as decimal or 0x-prefixed hexadecimal') from e


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    available = {c.name: c for c in cases()}
    run = sub.add_parser('run', help='run one boot code, or compare both for one scenario')
    suite = sub.add_parser('suite', help='run paired scenarios in a selected group')
    for p in (run, suite):
        p.add_argument('--firmware-dir', type=Path, required=True, help='directory containing pinned expanded images')
        p.add_argument('--release', choices=RELEASES, default=REFERENCE)
        p.add_argument('--mmio', action='append', type=parse_seed, default=[], metavar='ADDRESS=WORD')
        p.add_argument('--limit', type=int, default=DEFAULT_LIMIT, help='instruction budget per stage')
    run.add_argument('--scenario', choices=available, default='reference')
    run.add_argument('--boot-code', type=int, choices=(0, 2), help='if omitted, execute a pair')
    run.add_argument('--detail', action='store_true', help='include full boundary state and ordered trace')
    suite.add_argument('--group', choices=('all', 'cold', 'resume', 'memory', 'geometry', 'gpio', 'control'), default='all')
    generate = sub.add_parser('evidence', help='independently execute all five releases and write deterministic evidence')
    generate.add_argument('--firmware-dir', type=Path, required=True)
    generate.add_argument('output', type=Path)
    sub.add_parser('list', help='list scenario inputs without loading firmware')
    args = parser.parse_args()
    try:
        if args.command == 'list':
            print(serial({k: c.inputs() for k, c in available.items()}, indent=2))
            return
        if args.command == 'evidence':
            args.output.write_bytes(evidence_bytes(build_evidence(args.firmware_dir)))
            return
        loader, code, identity = load_release(args.firmware_dir, args.release)
        seeded = dict(args.mmio)
        if args.command == 'run':
            case = available[args.scenario]
            if args.boot_code is None:
                data, _ = pair(loader, code, case, initial_mmio=seeded, budget=args.limit, detail=args.detail)
            else:
                data, h = execute(loader, case, args.boot_code, seeded, args.limit)
                data['independent_models'] = dict(
                    gpio=gpio_model_comparison(data, h, case, adfu.decoded_constants(code)),
                    memory_test=memory_model_comparison(data, h, case), dram_core=core_model_comparison(data, h, case),
                    failure_mapping=validate_return(data))
                data['phase_boundaries'] = h.boundaries if args.detail else [
                    dict(phase=v['phase'], pc=v['pc'], sha256=digest(v)) for v in h.boundaries]
                if args.detail:
                    data['raw_ordered_trace_rle'] = h.ordered.runs
            out = dict(result=data, inputs=case.inputs())
        else:
            out = dict(results={})
            for case in available.values():
                if args.group in ('all', case.group):
                    result, harnesses = pair(loader, code, case, initial_mmio=seeded, budget=args.limit)
                    out['results'][case.name] = dict(inputs=case.inputs(), result=result)
                    del harnesses
                    gc.collect()
        print(serial(dict(format_version=FORMAT_VERSION, firmware=identity, explicit_mmio=word_map(seeded),
                          instruction_budget=args.limit, assumptions=ASSUMPTIONS, trace_fields=TRACE_FIELDS, **out),
                     indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{parser.prog}: {exc}\n')


if __name__ == '__main__':
    main()
