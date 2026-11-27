#!/usr/bin/env python3
"""Offline reconstruction of the remaining stock-loader DRAM behaviour (PR #6).

This extends the PR #4 harness (``ddr_emulate.Emulation``) rather than replacing
it. Everything runs the firmware's own instructions in Unicorn, or an
independent Python model of them. Nothing touches hardware.

What is covered (addresses are bootloader.bin VAs, identical in all four stock
releases; see reports/dram-complete-reconstruction.md):

* the DRAM caller ``0xb40665d0`` end to end: ini copy, PMIC init and the
  suspend/resume decision, ADFU checks, record selection, mode-0 init, the
  memory test ``0xb406631c``, the write-back ``0xb4066280`` and the AFI write;
* the resume path ``0xb40664e4`` -> ``0xb4067094`` -> mode 1 ``0xb40690d0``,
  including the resume-vector jump, the RTC-alarm re-arm and the PMIC
  power-off that follow a failure;
* the memory test on a sparse, fault-injectable RAM model, plus an
  independent Python implementation of the same algorithm;
* explicit PUBL/uPCTL response scenarios for training, ZQ, PHY and controller
  failures, with every synthetic response logged;
* the LPDDR branch (``type & 0xf != 0``), recorded by emulation only;
* a DMM address-decode hypothesis model for the capacity probe and memory
  test, used to ask which DRAM geometries the firmware can tell apart.

Modelled behaviour (never observed on a handheld):

* PMIC registers are a register file (``Pmic``) behind the loader's own I2C
  accessors ``0xb4069610``/``0xb40696c0``; detection ``0xb4069890`` and the
  UART init ``0xb4066784`` are stubbed. Defaults are listed in ``PMIC_DEFAULTS``.
* PUBL/uPCTL status reads follow ``Scenario`` (rules are recorded per read).
* DRAM follows ``Ram``: wrap-around at a size (PR #4 hypothesis), or the
  ``dmm`` field decode (``DmmDevice``), with optional injected faults.

Usage::

    python tools/dram_complete.py evidence OUT.json --loader stock-221203=loader-221203.bin ...
    python tools/dram_complete.py memtest LOADER --capacity 256 --ram wrap:128
    python tools/dram_complete.py resume LOADER --scenario resume-valid
"""
import argparse
from dataclasses import dataclass, field, asdict
import hashlib
import json
from pathlib import Path
import struct

import ddr_emulate as de
import ddr_model as dm

TOOL_VERSION = 1

# ---------------------------------------------------------------- firmware coordinates
FN = dict(
    main=0xB4065400, caller=0xB40665D0, ini_copy=0xB4065FF8, ini_version=0xB4066194, ini_print=0xB40661B0,
    timer_init=0xB4069440, uart_init=0xB4066784, boot_code=0xB40664F0, board_init=0xB406A608,
    pmu_init=0xB40699E8, pmu_detect=0xB4069890, pmic_read=0xB4069610, pmic_write=0xB40696C0,
    adfu_check=0xB4069254, rom_reentry=0xB40691A4, publish_globals=0xB406622C, spinand_restore=0xB40663F8,
    mode0=0xB40690B8, mode1=0xB40690D0, mode1_selfrefresh=0xB4069128, dram=0xB40673F4,
    pctl_state=0xB4067170, selfrefresh_entry=0xB4067248, dmm_setup=0xB406735C,
    memtest=0xB406631C, writeback=0xB4066280, afi_code=0xB4066588, afi_write=0xB4066500, ddr_size=0xB4069180,
    resume_entry=0xB40664E4, resume_dispatch=0xB4067094, prewake=0xB4066B64, alarm_rearm=0xB4066EAC,
    rtc_add=0xB4066D90, power_off=0xB4066BF0, resume_jump=0xB4066FD4,
)
POWER_OFF_PMIC = 0xB4066C30          # inside power_off, after the optional self-refresh entry; never returns
GLOBALS, GLOBALS_LEN = 0xB4070800, 0x7C   # cleared by main (0xb4065400) before the caller runs
RESUME_FLAG, RESUME_VECTOR, ALARM_FLAG = 0xB4070874, 0xB4070878, 0xB4070870
MODE_BYTE = 0xB4070804               # +0 mode (0 cold, 1 resume), +1 sub-flag (always 0 in this loader)
BOOT_CODE = 0xB4064C00
AFI = 0xB4060300
DCU_CFG = de.DCU_CFG
MCFG1 = de.UPCTL + 0x7C
INTERNAL_CODES = {0x2A00FA11: 'ZQ0SR0 done bit not set in 101 reads', 0x9A00FA11: 'PGSR & 7 != 7 in 101 reads',
                  0xDF00FA11: 'DFISTSTAT0 bit 0 not set in 101 reads', 0xF000FA11: 'row-probe exponent 32 (unreachable: exponent 31 ends the search first)',
                  0xC000FA11: 'capacity exponent > 31', 0x1017FA11: 'PUBL data training error (PGSR 0x3f)'}
DRAM_WINDOW = 0x80000000              # the harness maps DRAM lazily below this; above it is SRAM/MMIO/unknown
SUBFLAG_SWEEP = 0xB4069088
COLLAPSED = 0x1747FA11                # 0xb4068f34: every code whose low 24 bits are 0x00fa11 is replaced by this

# PMIC register numbers used by the type-2 branch (table 0xb406b9a0.., third column)
PMIC_REG = dict(ctl3=0x03, wake_flag=0x01, vec_lo=0x08, vec_hi=0x5D, s4_check=0x14, ic_version=0xDC,
                pmu_status=0x35, rtc_ms=0x56, rtc_h=0x57, rtc_date=0x59, alarm_ms=0x53, alarm_h=0x54, alarm_date=0x55)
# RTC packing as the loader uses it (0xb4066d90, and the pmu_init printf): ms = minute << 6 | second,
# h = hour (5 bits), date = year << 9 | month << 5 | day.
PMIC_DEFAULTS = {0xDC: 1, 0x14: 0x8000}   # ic version non-zero (0 hangs: "pmu ver=0 not support"); 0x14 bit 15 set


def decode_afi(b):
    magic, mode, dev, uart, pad, baud, size = struct.unpack('<4sBBBBII', bytes(b))
    return dict(magic_ok=magic[:3] == b'AFI', magic=magic.hex(), boot_mode=mode, boot_dev=dev, uart_index=uart,
                uart_pad=pad, uart_baudrate=baud, ddr_size=size)


def uboot_ram_size(afi):
    """U-Boot side (BOOT-013/017, evidence/firmware/stock-boot-chain.json): the getters return ddr_size only when
    the magic is present (otherwise 0), and dram_init keeps it only if >= 8 MiB, else CONFIG_SYS_SDRAM_SIZE."""
    size = afi['ddr_size'] if afi['magic_ok'] else 0
    ram = size if size >= 8 << 20 else 0x1F000000
    return dict(ddr_size=size, gd_ram_size=ram, memory_reg=[0, ram], fallback=ram != size,
                boot_mode=afi['boot_mode'] if afi['magic_ok'] else 1)


def afi_ddr_size(capacity_mib):
    """0xb4069180: ((byte3 << 8) | byte2) << 20, 32-bit."""
    return (capacity_mib & 0xFFFF) << 20 & 0xFFFFFFFF


def returned_code(internal):
    """0xb4068f34..0xb4068f50: what the DRAM routine returns for an internal failure code."""
    if internal == 0:
        return 0
    return COLLAPSED if internal & 0xFFFFFF == 0xFA11 else internal


# ---------------------------------------------------------------- models of what the firmware observes
@dataclass
class Scenario:
    """Synthetic PUBL/uPCTL responses. Nothing here was observed on an RG35XX."""
    name: str = 'reference'
    note: str = 'one x16 2 Gb rank; training passes iff configured ranks/width are present (PR #4 reference)'
    ranks: int = 1
    width: int = 16
    col_bits: int = 10
    row_bits: int = 14
    bank_log2: int = 3
    training: object = 'geometry'      # 'geometry' or a list of booleans consumed per training PIR
    training_pgsr: int = None          # explicit PGSR after a failed training PIR (default 0x3f)
    zq_done: bool = True
    phy_init_done: bool = True         # PGSR & 7 == 7 after reset
    dram_init_done: bool = True        # PGSR == 0xf after the DRAM-init PIR
    dfi_ready: bool = True
    stat_stuck: int = None             # uPCTL STAT never reaches this state (unbounded poll)
    idle_self_refresh: bool = False    # STAT reports 0x15 (Low_power via idle) after GO when MCFG1 idle is set
    lanes: tuple = (0, 0, 0, 0)        # DXGSR0..3 words
    reset_seed: int = 0


@dataclass
class DmmDevice:
    """A DRAM device behind a hypothetical DMM address decode (field order low to high above the bus bytes).

    The DMM is assumed to split a CPU byte address into bus bytes, then the fields named in ``order`` with the
    widths configured in DCU_CFG (columns 8+code, 8 banks, rows 13+code, one rank bit when cs = 2) and to ignore
    higher bits. The device keeps only the field bits it has; an absent rank reads ``float_value``."""
    col_bits: int = 10
    row_bits: int = 14
    bank_log2: int = 3
    ranks: int = 1
    order: tuple = ('col', 'bank', 'row', 'rank')


@dataclass
class Ram:
    kind: str = 'wrap'                 # 'wrap' (mod size), 'open' (beyond size: writes lost, reads float), 'dmm'
    size: int = 256 << 20
    device: DmmDevice = None
    float_value: int = 0xFFFFFFFF
    read_xor: dict = field(default_factory=dict)    # byte address -> xor mask on the 32-bit word read there
    write_drop: tuple = ()                          # byte addresses whose writes are lost
    stuck_high: int = 0                             # data bits stuck at 1 / 0 on every access
    stuck_low: int = 0


class Pmic:
    """Register file standing in for the ATC260x-family PMIC (I2C slave 0x65 in the loader's accessors)."""

    def __init__(self, regs=None):
        self.regs = dict(PMIC_DEFAULTS)
        self.regs.update(regs or {})
        self.initial = dict(self.regs)
        self.log = []

    def read(self, reg):
        v = self.regs.get(reg, 0) & 0xFFFF
        self.log.append(('r', reg, v))
        return v

    def write(self, reg, v):
        self.regs[reg] = v & 0xFFFF
        self.log.append(('w', reg, v & 0xFFFF))


# ---------------------------------------------------------------- the harness
class Harness(de.Emulation):
    def __init__(self, loader, scenario=None, pmic=None, ram=None, limit=3_000_000, boot_code=0, clear_globals=True):
        self.s = scenario or Scenario()
        super().__init__(loader, scenario='x16-1rank-2Gb', reset_seed=self.s.reset_seed)
        self.hw = dict(ranks=self.s.ranks, width=self.s.width, col_bits=self.s.col_bits, row_bits=self.s.row_bits,
                       bank_log2=self.s.bank_log2)
        self.pmic = pmic or Pmic()
        self.ram = ram
        self.limit = limit
        self.stops = {}
        self.stopped = None
        self.trace = []
        self.cells = {}
        self.dram_log = []
        self.in_memtest = False
        self._memtest_lr = None
        self.training_calls = 0
        self.uc.mem_write(BOOT_CODE, struct.pack('<I', boot_code))
        if clear_globals:                                   # main: memset(0xb4070800, 0, 0x7c)
            self.uc.mem_write(GLOBALS, b'\0' * GLOBALS_LEN)
        self.stubs = {FN['uart_init']: ('UART init (stub)', lambda: 0),
                      FN['pmu_detect']: ('PMIC detection (stub)', lambda: 0),
                      FN['pmic_read']: ('PMIC read (register file)', lambda: self.pmic.read(self.reg('r0') & 0xFF)),
                      FN['pmic_write']: ('PMIC write (register file)',
                                         lambda: self.pmic.write(self.reg('r0') & 0xFF, self.reg('r1')) or 0)}
        self.watch = {v: k for k, v in FN.items()}

    # ---- execution --------------------------------------------------
    def call(self, entry, r0=0, r1=0, until=de.SENTINEL):
        self.setreg('sp', de.STACK_TOP)
        self.setreg('lr', de.SENTINEL)
        self.setreg('r0', r0)
        self.setreg('r1', r1)
        self.stopped = None
        try:
            self.uc.emu_start(entry, until, count=self.limit + 16)
        except Exception as e:                       # unmapped access outside the modelled windows
            self.stopped = dict(kind='fault', error=str(e), pc=hex(self.reg('pc')))
        return self.reg('r0')

    def _code(self, uc, address, size, user):
        self.insns += 1
        if self.insns > self.limit:
            last = self.reads[-1] if self.reads else None
            self.stopped = dict(kind='unbounded poll (instruction limit)', pc=hex(address), last_read=last)
            uc.emu_stop()
            return
        if address in self.watch:
            self.trace.append(dict(fn=self.watch[address], at=hex(address), r0=hex(self.reg('r0')), r1=hex(self.reg('r1'))))
        if address in self.stops:
            self.stopped = dict(kind='stop', name=self.stops[address], pc=hex(address), r0=hex(self.reg('r0')),
                                r1=hex(self.reg('r1')))
            uc.emu_stop()
            return
        if address == FN['memtest']:
            self._memtest_lr = self.reg('lr')
            self.in_memtest = True
        elif self.in_memtest and address == self._memtest_lr:
            self.in_memtest = False
        if address == de.F_DELAY:
            self.setreg('pc', self.reg('lr'))
        elif address == de.F_PRINTF:
            sp = self.reg('sp')
            args = [self.reg('r1'), self.reg('r2'), self.reg('r3')] + [self.u32(sp + 4 * i) for i in range(10)]
            self.prints.append(dict(pc=hex(self.reg('lr') - 4), text=de._sprintf(self.cstr(self.reg('r0')), args).strip('\n')))
            self.setreg('r0', 0)
            self.setreg('pc', self.reg('lr'))
        elif address in self.stubs:
            v = self.stubs[address][1]()
            self.setreg('r0', v if v is not None else 0)
            self.setreg('pc', self.reg('lr'))

    # ---- PUBL / uPCTL responses ------------------------------------
    def _training_passes(self):
        if self.s.training == 'geometry':
            return super()._training_passes()
        seq = list(self.s.training)
        ok = seq[self.training_calls] if self.training_calls < len(seq) else seq[-1]
        self.training_calls += 1
        return ok

    def _oracle(self, addr):
        s, tag = self.s, f'scenario {self.s.name}: '
        if addr == de.ZQ0SR0:
            return (0x80000000 if s.zq_done else 0), tag + ('ZQ done (code unknown)' if s.zq_done else 'ZQ never done')
        if addr == de.PGSR:
            v = self.pgsr
            if v == 0x7 and not s.phy_init_done:
                return 0x3, tag + 'PGSR after reset lacks ZCDONE'
            if v == 0xF and not s.dram_init_done:
                return 0x7, tag + 'PGSR never reports DIDONE'
            return v, tag + 'PGSR follows last PIR'
        if addr in de.DXGSR0:
            return s.lanes[de.DXGSR0.index(addr)], tag + 'synthetic DXGSR0 lane word'
        if addr == de.DFISTSTAT0:
            return (1 if s.dfi_ready else 0), tag + ('DFI init complete' if s.dfi_ready else 'DFI never ready')
        if addr == de.STAT:
            want = self.sctl_state
            if s.stat_stuck is not None and want == s.stat_stuck:
                return self._stat_prev, tag + f'STAT stuck before state {want}'
            self._stat_prev = want
            if want == 5:
                return 0x45, tag + 'Low_power, lp_trig 4 (software request; DesignWare encoding)'
            if want == 3 and s.idle_self_refresh and self.regs.get(MCFG1, 0) & 0xFF:
                self._idle_reads += 1                 # Access first (0xb4067170 waits for it), then idle Low_power
                if self._idle_reads > 1:
                    return 0x15, tag + 'Low_power via idle self-refresh (lp_trig 1)'
            return want, tag + 'STAT follows last SCTL command'
        return super()._oracle(addr)

    _stat_prev = 0
    _idle_reads = 0

    def _mmio_write(self, uc, access, address, size, value, user):
        super()._mmio_write(uc, access, address, size, value, user)
        a = address & ~3
        if a == de.PIR and value & 0x80 and self.pgsr == 0x3F and self.s.training_pgsr is not None:
            self.pgsr = self.s.training_pgsr

    # ---- DRAM ------------------------------------------------------
    def _active_ram(self):
        """A ``dmm`` model answers every DRAM access; wrap/open models answer only inside the memory test (the
        capacity probe then keeps the PR #4 aliasing model, so probe and test hypotheses stay separate)."""
        r = self.ram
        if r is None or (r.kind != 'dmm' and not self.in_memtest and not self.ram_everywhere):
            return None
        return r

    ram_everywhere = False

    def _key(self, addr):
        r = self._active_ram()
        if r is None:
            return 'flat', self._phys(addr)
        if r.kind == 'wrap':
            return 'flat', addr % r.size
        if r.kind == 'open':
            return ('flat', addr) if addr < r.size else (None, None)
        dev, dcu = r.device, self.regs.get(DCU_CFG, 0)
        a = addr >> (2 if dcu & 1 else 1)
        widths = dict(col=8 + (dcu >> 1 & 3), bank=3, row=13 + (dcu >> 5 & 3), rank=(dcu >> 4) & 1)
        have = dict(col=dev.col_bits, bank=dev.bank_log2, row=dev.row_bits)
        out = {}
        for f in dev.order:
            out[f] = a & ((1 << widths[f]) - 1)
            a >>= widths[f]
        if out['rank'] >= dev.ranks:
            return None, None
        return (out['rank'], out['bank'] & ((1 << have['bank']) - 1), out['row'] & ((1 << have['row']) - 1),
                out['col'] & ((1 << have['col']) - 1)), addr & (3 if dcu & 1 else 1)

    fault_address = None

    def _unmapped(self, uc, access, address, size, value, user):
        if address >= DRAM_WINDOW:
            self.fault_address = address
        return super()._unmapped(uc, access, address, size, value, user)

    def _dram_write(self, uc, access, address, size, value, user):
        r = self._active_ram()
        if r is not None and (address & ~3) in r.write_drop:
            self.dram_log.append(('w', address, value, 'dropped (injected)'))
            return
        for i in range(size):
            base, off = self._key(address + i)
            if base is None:
                continue
            self.cells[(base, off)] = (value >> (8 * i)) & 0xFF
        self.dram_log.append(('w', address, value & ((1 << 8 * size) - 1), None))

    def _dram_read(self, uc, access, address, size, value, user):
        r = self._active_ram()
        v = 0
        for i in range(size):
            base, off = self._key(address + i)
            if base is None:
                b = ((r.float_value if r else 0) >> (8 * ((address + i) & 3))) & 0xFF
            else:
                b = self.cells.get((base, off), 0)
            v |= b << (8 * i)
        if r is not None:
            m = (1 << 8 * size) - 1
            v = (v | r.stuck_high) & ~r.stuck_low & m
            v ^= r.read_xor.get(address & ~3, 0) & m
        uc.mem_write(address, v.to_bytes(size, 'little'))
        self.dram_log.append(('r', address, v, None))
        self.reads.append(dict(site=hex(self._site(de.F_LOAD)), address=hex(address), value=hex(v),
                               rule=f'DRAM model {r.kind if r else "PR #4 wrap"}'))

    # ---- views -----------------------------------------------------
    def word(self, a):
        return self.u32(a)

    def flags(self):
        return dict(resume_flag=self.word(RESUME_FLAG), resume_vector=hex(self.word(RESUME_VECTOR)),
                    alarm_flag=self.word(ALARM_FLAG), mode=self.uc.mem_read(MODE_BYTE, 2).hex())

    def pmic_writes(self):
        return [dict(reg=hex(r), value=hex(v)) for k, r, v in self.pmic.log if k == 'w']


# ---------------------------------------------------------------- memory test
def memtest_model(capacity_mib, ram):
    """Independent re-statement of 0xb406631c(capacity_mib). Returns (prints, accesses, verdict).

    N = capacity << 18 (32-bit) words. Phase A (address lines): for i = 4, 8, 16 ... < N, store i at byte 4*i;
    then load each back; the first mismatch prints "addr:ddr_test fail <i>, <read>" and ends the test.
    Phase B (data/stride): v = 0x10 + k*0x41114 < N, store v at byte 4*v; then load back; a mismatch prints
    "tmp:ddr_test fail <v>, <read>". All passes print "== ok==". The caller ignores the result."""
    n = (capacity_mib << 18) & 0xFFFFFFFF
    mem, acc = {}, []

    def key(a):
        if ram.kind == 'wrap':
            return a % ram.size
        if ram.kind == 'open':
            return a if a < ram.size else None
        raise ValueError('memtest_model supports wrap/open RAM only')

    class Outside(Exception):
        pass

    def wr(a, v):
        if a >= DRAM_WINDOW:
            raise Outside(a)
        acc.append(('w', a, v))
        if a in ram.write_drop:
            return
        k = key(a)
        if k is not None:
            mem[k] = v

    def rd(a):
        if a >= DRAM_WINDOW:
            raise Outside(a)
        k = key(a)
        v = mem.get(k, 0) if k is not None else ram.float_value
        v = ((v | ram.stuck_high) & ~ram.stuck_low & 0xFFFFFFFF) ^ ram.read_xor.get(a, 0)
        acc.append(('r', a, v))
        return v

    prints = [f'==ddr_test {capacity_mib} MB ==']
    try:
        return _memtest_body(n, wr, rd, prints, acc)
    except Outside as e:
        return prints, acc, f'outside-dram-window 0x{e.args[0]:x}'


def _memtest_body(n, wr, rd, prints, acc):
    i = 4
    while i < n:
        wr((i << 2) & 0xFFFFFFFF, i)
        i = (i << 1) & 0xFFFFFFFF
    i = 4
    while i < n:
        v = rd((i << 2) & 0xFFFFFFFF)
        if v != i:
            prints.append(f'addr:ddr_test fail {i}, 0x{v:x} ')
            return prints, acc, 'addr-fail'
        i = (i << 1) & 0xFFFFFFFF
    a, v = 0, 0x10
    while v < n:
        wr(a + 0x40, v)
        v += 0x41114
        a += 0x104450
    a, v = 0, 0x10
    while v < n:
        r = rd(a + 0x40)
        if r != v:
            prints.append(f'tmp:ddr_test fail {v}, 0x{r:x} ')
            return prints, acc, 'data-fail'
        v += 0x41114
        a += 0x104450
    prints.append('== ok==')
    return prints, acc, 'ok'


def memtest_emulated(loader, capacity_mib, ram, limit=2_000_000):
    h = Harness(loader, ram=ram, limit=limit)
    h.ram_everywhere = True
    h.call(FN['memtest'], r0=capacity_mib & 0xFFFF)
    acc = [(k, a, v) for k, a, v, _ in h.dram_log]
    prints = [p['text'] for p in h.prints]
    verdict = 'ok' if prints and prints[-1] == '== ok==' else (
        'addr-fail' if any(p.startswith('addr:') for p in prints) else
        'data-fail' if any(p.startswith('tmp:') for p in prints) else 'incomplete')
    if h.stopped and h.stopped['kind'] == 'fault':
        verdict = f'outside-dram-window 0x{h.fault_address:x}' if h.fault_address is not None else 'fault'
    return dict(prints=prints, accesses=acc, verdict=verdict, stopped=h.stopped, instructions=h.insns)


def memtest_summary(acc):
    w = [a for k, a, _ in acc if k == 'w']
    r = [a for k, a, _ in acc if k == 'r']
    return dict(writes=len(w), reads=len(r), lowest=hex(min(w)) if w else None, highest=hex(max(w)) if w else None,
                sha256=hashlib.sha256(json.dumps(acc).encode()).hexdigest())


MEMTEST_CASES = [
    # name, capacity argument (MiB), RAM model, what the case demonstrates
    ('valid-256', 256, Ram('wrap', 256 << 20), 'contiguous 256 MiB, test argument 256'),
    ('valid-128', 128, Ram('wrap', 128 << 20), 'smaller part, consistent argument'),
    ('alias-2x', 256, Ram('wrap', 128 << 20), '128 MiB wraps, argument 256: one-bit overestimate'),
    ('alias-4x', 256, Ram('wrap', 64 << 20), '64 MiB wraps, argument 256'),
    ('open-2x', 256, Ram('open', 128 << 20), 'nothing decoded above 128 MiB (reads float high)'),
    ('read-fault', 256, Ram('wrap', 256 << 20, read_xor={0x40 + 3 * 0x104450: 0x100}),
     'one bit flips on read at a phase-B address'),
    ('read-fault-phaseA', 256, Ram('wrap', 256 << 20, read_xor={0x100: 0x1}), 'bit flip on read at byte 0x100'),
    ('write-drop', 256, Ram('wrap', 256 << 20, write_drop=(0x40 + 7 * 0x104450,)), 'one phase-B write lost'),
    ('write-drop-unvisited', 256, Ram('wrap', 256 << 20, write_drop=(0x1004,)), 'a lost write at an address the test never visits'),
    ('stuck-data-bit', 256, Ram('wrap', 256 << 20, stuck_low=1 << 20), 'data bit 20 stuck at 0'),
    ('zero-size', 0, Ram('wrap', 256 << 20), 'argument 0: N = 0, nothing tested'),
    ('wrapped-size-16384', 16384, Ram('wrap', 256 << 20), 'argument 16384: N = 2^32 wraps to 0'),
    ('size-4096', 4096, Ram('wrap', 256 << 20), 'argument 4096: phase A reaches byte 0x80000000 (outside DRAM window)'),
    ('size-2048', 2048, Ram('wrap', 256 << 20), 'argument 2048 (the forced mode-0 value) on 256 MiB'),
]


def memtest_cases(loader):
    out = {}
    for name, cap, ram, note in MEMTEST_CASES:
        m_prints, m_acc, m_verdict = memtest_model(cap, ram)
        e = memtest_emulated(loader, cap, ram) if loader is not None else None
        row = dict(capacity_argument=cap, ram=_ram_desc(ram), note=note, model_verdict=m_verdict,
                   model_prints=m_prints, model_accesses=memtest_summary(m_acc))
        if e is not None:
            row.update(emulated_verdict=e['verdict'], emulated_prints=e['prints'],
                       emulated_accesses=memtest_summary(e['accesses']),
                       emulation_stopped=e['stopped']['kind'] if e['stopped'] else None,
                       model_equals_emulation=(e['prints'] == m_prints and e['accesses'] == m_acc))
        out[name] = row
    return out


def _ram_desc(ram):
    d = dict(kind=ram.kind, size=hex(ram.size))
    for k in ('read_xor', 'write_drop', 'stuck_high', 'stuck_low'):
        v = getattr(ram, k)
        if v:
            d[k] = {hex(a): hex(m) for a, m in v.items()} if isinstance(v, dict) else (
                [hex(a) for a in v] if isinstance(v, tuple) else hex(v))
    if ram.device:
        d['device'] = asdict(ram.device)
    return d


# ---------------------------------------------------------------- training / failure scenarios (mode 0)
TRAINING_SCENARIOS = [
    Scenario('reference', ranks=1),
    Scenario('two-ranks-first-attempt', note='hypothetical second rank: cs=2 trains first time', ranks=2),
    Scenario('persistent-training-failure', note='training reports DTERR for cs=2 and cs=1', training=[False, False],
             lanes=(0x1, 0x0, 0x10, 0x0)),
    Scenario('zq-timeout', note='ZQ0SR0 never reports done', zq_done=False),
    Scenario('phy-init-timeout', note='PGSR never shows IDONE|DLDONE|ZCDONE', phy_init_done=False),
    Scenario('dram-init-hang', note='PGSR never reaches 0xf after PIR 0x7f', dram_init_done=False),
    Scenario('training-other-status', note='PGSR 0x5f (DTIERR) after training PIR', training=[False],
             training_pgsr=0x5F),
    Scenario('dfi-timeout', note='DFISTSTAT0 never ready', dfi_ready=False),
    Scenario('controller-stuck-config', note='uPCTL STAT never reaches Config', stat_stuck=1),
    Scenario('unsupported-geometry-rows', note='17 row bits: row probe finds no alias', row_bits=17),
    Scenario('unsupported-geometry-cols', note='12 column bits: column probe finds no alias', col_bits=12),
    Scenario('lane-words-nonzero', note='cs=2 fails with non-zero DXGSR0 words, cs=1 passes', ranks=1,
             lanes=(0x00010203, 0x0, 0x80000000, 0xFFFFFFFF)),
]


def _second_record(h):
    h.call(de.F_INI_COPY, r0=de.INI_LOAD)
    if h.u32(de.INI_LOAD + 0x2C):
        h.uc.mem_write(de.PARAM, bytes(h.uc.mem_read(de.PARAM2, 12)))


def summarise_run(h, ret):
    pirs = [w['value'] for w in h.writes if int(w['address'], 16) == de.PIR]
    synthetic = sorted({r['rule'] for r in h.reads if r['rule'].startswith('scenario')})
    return dict(return_value=hex(ret) if h.stopped is None else None, stopped=h.stopped, prints=[p['text'] for p in h.prints],
                pir_sequence=pirs, training_attempts=sum(1 for v in pirs if int(v, 16) & 0x80),
                param_after=h.param(), mmio_writes=len(h.writes), synthetic_rules=synthetic, instructions=h.insns)


def training_scenarios(loader):
    out = {}
    for s in TRAINING_SCENARIOS:
        h = Harness(loader, scenario=s, limit=400_000)
        _second_record(h)
        h.writes.clear()
        h.reads.clear()
        ret = h.call(FN['mode0'], r0=de.PARAM)
        row = summarise_run(h, ret)
        row['scenario'] = asdict(s)
        out[s.name] = row
    # bus-width auto retry, reachable only with a patched record (bus_sel >= 2)
    h = Harness(loader, scenario=Scenario('bus-auto', note='record bus_sel patched to 2; x16 hardware'), limit=400_000)
    _second_record(h)
    h.uc.mem_write(de.PARAM + 4, bytes([2]))
    h.writes.clear()
    ret = h.call(FN['mode0'], r0=de.PARAM)
    out['bus-auto-patched-record'] = summarise_run(h, ret)
    return out


# ---------------------------------------------------------------- caller / resume
RESUME_VECTOR_SYNTH = 0x00108000


def resume_pmic(vector=RESUME_VECTOR_SYNTH, s2=True, from_s4=False, wake=0, extra=None):
    regs = {PMIC_REG['ctl3']: 0x10 if s2 else 0, PMIC_REG['s4_check']: 0 if from_s4 else 0x8000,
            PMIC_REG['vec_lo']: vector & 0xFFFF, PMIC_REG['vec_hi']: vector >> 16 & 0xFFFF, PMIC_REG['wake_flag']: wake,
            PMIC_REG['rtc_h']: 12, PMIC_REG['rtc_ms']: 59 << 6 | 58, PMIC_REG['rtc_date']: 23 << 9 | 10 << 5 | 14}
    regs.update(extra or {})
    return Pmic(regs)


RESUME_CASES = [
    # name, PMIC registers, DRAM scenario, ini patches (offset -> bytes), note
    ('cold-no-s2-flag', dict(s2=False), Scenario(), {}, 'PMU_CTL3 bit 4 clear: ordinary cold boot'),
    ('resume-valid', dict(), Scenario(), {}, 'S2 flag, not from S4, vector 0x00108000: resume'),
    ('s2-but-from-s4', dict(from_s4=True), Scenario(), {}, 'PMIC reg 0x14 bit 15 clear: "from s4", flag cleared'),
    ('s2-vector-zero', dict(vector=0), Scenario(), {}, 'S2 flag but no resume vector'),
    ('resume-training-failure', dict(), Scenario('resume-fail', training=[False]), {},
     'mode-1 training error: RTC alarm +3 s, S2 flag re-set, power off'),
    ('resume-zq-timeout', dict(), Scenario('resume-zq', zq_done=False), {}, 'mode-1 ZQ timeout'),
    ('resume-alarm-check', dict(vector=0x80108000, wake=0x100), Scenario(), {},
     'vector bit 31 and alarm wake flag: DRAM restored, back to self-refresh, power off'),
    ('resume-vector-bit31-no-alarm', dict(vector=0x80108000, wake=0), Scenario(), {},
     'vector bit 31 without alarm wake: bit cleared, jump'),
    ('resume-stale-capacity', dict(), Scenario(), {0x20: (512).to_bytes(2, 'little')},
     'primary record says 512 MiB on 256 MiB hardware: programmed as stored, no check'),
    ('resume-cs-zero', dict(), Scenario(), {0x25: b'\x00'}, 'primary record cs = 0 (inconsistent): density divides by 0'),
    ('adfu-request', dict(s2=False, extra={PMIC_REG['pmu_status']: 0x2}), Scenario(), {},
     'pmu_status bit 1: ADFU entry before DRAM init'),
    ('pmic-version-zero', dict(s2=False, extra={PMIC_REG['ic_version']: 0}), Scenario(), {},
     'PMIC version register 0: "pmu ver=0 not support" loop'),
]


def run_caller(loader, pmic, scenario, ini_patch=None, ram=None, follow_resume=True, limit=3_000_000, boot_code=0):
    """Execute 0xb40665d0(ini, 0) as main does, then, on return 2, 0xb40664e4 (main's resume branch).

    boot_code is the word block 0 leaves at 0xb4064c00. The committed PR #6 evidence uses the default 0 (SD0 path);
    predram_analysis.py compares 0 and 2 through here (PR #9)."""
    h = Harness(loader, scenario=scenario, pmic=pmic, ram=ram, limit=limit, boot_code=boot_code)
    for off, b in (ini_patch or {}).items():
        h.uc.mem_write(de.INI_LOAD + off, bytes(b))
    afi_before = bytes(h.uc.mem_read(AFI, 16))
    h.stops = {FN['rom_reentry']: 'ROM re-entry 0xb40691a4 (ADFU)', POWER_OFF_PMIC: 'PMIC power-off (never returns)'}
    ret = h.call(FN['caller'], r0=de.INI_LOAD, r1=0)
    first = dict(stopped=h.stopped, return_value=None if h.stopped else hex(ret), flags=h.flags(),
                 record_used=h.param(), afi=decode_afi(h.uc.mem_read(AFI, 16)),
                 afi_written=bytes(h.uc.mem_read(AFI, 16)) != afi_before,
                 memtest_called=any(t['fn'] == 'memtest' for t in h.trace),
                 ini_primary_after=bytes(h.uc.mem_read(de.INI_LOAD + 0x1C, 16)).hex())
    out = dict(caller=first)
    if follow_resume and h.stopped is None and ret == 2:
        vec = h.word(RESUME_VECTOR)
        h.stops[vec & 0x7FFFFFFF] = 'resume vector (jump target)'
        h.stops[vec] = 'resume vector (jump target)'
        h.insns = 0
        r2 = h.call(FN['resume_entry'])
        out['resume'] = dict(stopped=h.stopped, return_value=None if h.stopped else hex(r2), flags=h.flags(),
                             afi=decode_afi(h.uc.mem_read(AFI, 16)), afi_written_since_boot=bytes(h.uc.mem_read(AFI, 16)) != afi_before,
                             memtest_called=any(t['fn'] == 'memtest' for t in h.trace))
    out['functions'] = _order([t['fn'] for t in h.trace])
    out['prints'] = _collapse([p['text'] for p in h.prints])
    out['pmic_writes'] = h.pmic_writes()[-64:]
    out['pir_sequence'] = [w['value'] for w in h.writes if int(w['address'], 16) == de.PIR]
    out['mode_bytes_final'] = h.uc.mem_read(MODE_BYTE, 2).hex()
    out['afi_bytes_before'] = afi_before.hex()
    h_afi = decode_afi(h.uc.mem_read(AFI, 16))
    out['uboot_view'] = uboot_ram_size(h_afi)
    return out, h


def _collapse(lines):
    """Consecutive identical console lines as one entry with a repeat count (a looping printf otherwise
    produces millions of lines before the instruction limit)."""
    out = []
    for x in lines:
        if out and out[-1][0] == x:
            out[-1][1] += 1
        else:
            out.append([x, 1])
    return [x if n == 1 else f'{x} [repeated {n} times]' for x, n in out]


ODT_FIELDS = ('rdodt', 'wrodt', 'drv', 'raw', 'ini_primary_after', 'MR1', 'ZQ0CR1',
              'instructions', 'pc')   # instruction counts and the pc inside a poll loop vary with the ODT branches


def normalise_ini_odt(o):
    """Remove what only the ini ODT/drive bytes change (20231014 vs older), for cross-release comparison."""
    import re
    if isinstance(o, dict):
        return {k: normalise_ini_odt(v) for k, v in o.items() if k not in ODT_FIELDS}
    if isinstance(o, list):
        return [normalise_ini_odt(x) for x in o]
    if isinstance(o, str):
        return re.sub(r'wrodt\d+,rdodt\d+,drv[0-9a-f]+', 'wrodt*,rdodt*,drv*', o)
    return o


def _order(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def resume_cases(loader):
    out = {}
    for name, pm, scen, patch, note in RESUME_CASES:
        r, _ = run_caller(loader, resume_pmic(**pm), scen, patch, limit=1_500_000)
        r['note'] = note
        r['pmic_inputs'] = {hex(k): hex(v) for k, v in sorted(resume_pmic(**pm).initial.items())}
        out[name] = r
    return out


# ---------------------------------------------------------------- mode 0 vs mode 1
def mode_comparison(loader):
    """Final successful pass of mode 0 (second record, reference scenario) against mode 1 (primary record)."""
    h0 = Harness(loader)
    _second_record(h0)
    h0.writes.clear()
    r0 = h0.call(FN['mode0'], r0=de.PARAM)
    w0 = h0.writes
    idx = max(i for i, w in enumerate(w0) if w['address'] == hex(de.PUBL + 0x14) and w['value'] == '0x0')
    w0 = w0[idx - 6:]
    h1 = Harness(loader)
    h1.call(de.F_INI_COPY, r0=de.INI_LOAD)
    h1.writes.clear()
    r1 = h1.call(FN['mode1'], r0=de.PARAM, r1=0)
    seq = lambda ws: [(dm.REG.get(int(w['address'], 16), w['address']), w['value']) for w in ws]
    a, b = seq(w0), seq(h1.writes)
    va, vb = {}, {}
    for k, v in a:
        va.setdefault(k, []).append(v)
    for k, v in b:
        vb.setdefault(k, []).append(v)
    diffs = [dict(register=k, mode0=va.get(k), mode1=vb.get(k)) for k in sorted(set(va) | set(vb)) if va.get(k) != vb.get(k)]
    return dict(mode0=dict(return_value=hex(r0), writes=len(a), prints=[p['text'] for p in h0.prints][-2:]),
                mode1=dict(return_value=hex(r1), writes=len(b), prints=[p['text'] for p in h1.prints],
                           record=h1.param()),
                differing_registers=diffs)


def mode1_model_sweep(loader, clocks=range(100, 1201)):
    """Unicorn mode 1 against ddr_model.run(mode=1) at every clock (primary record, reference hardware)."""
    bad = []
    for clk in clocks:
        h = Harness(loader)
        h.call(de.F_INI_COPY, r0=de.INI_LOAD)
        h.uc.mem_write(de.PARAM, clk.to_bytes(2, 'little'))
        rec = dm.Record.from_bytes(bytes(h.uc.mem_read(de.PARAM, 12)))
        h.writes.clear()
        ret = h.call(FN['mode1'], r0=de.PARAM, r1=0)
        m = dm.run(rec, dm.Hardware(reset=dm.ResetAll(0)), mode=1)
        if [(int(w['address'], 16), int(w['value'], 16)) for w in h.writes] != [(w.address, w.value) for w in m['writes']] \
                or [p['text'] for p in h.prints] != m['prints'] or (ret == 0) != (m['result'] == '0x0'):
            bad.append(clk)
    return dict(clocks=[min(clocks), max(clocks)], count=len(clocks), mismatches=bad)


def unreachable_subflag(loader):
    """The sub-flag (0xb4070805) is only ever 0 (both callers pass r1 = 0). Exercise it anyway, to document it."""
    h = Harness(loader)
    h.call(de.F_INI_COPY, r0=de.INI_LOAD)
    h.writes.clear()
    h.stops = {SUBFLAG_SWEEP: 'start of the 0..0x1400000 word-read sweep (0xb4069088)'}
    ret = h.call(FN['mode1'], r0=de.PARAM, r1=1)
    pll = [w['value'] for w in h.writes if int(w['address'], 16) == dm.CMU + 0x08]
    sweep = sum(1 for k, a, v, _ in h.dram_log if k == 'r')
    return dict(stopped=h.stopped, prints=[p['text'] for p in h.prints], cmu_ddrpll_writes=pll,
                dram_reads_before_sweep=sweep, record_after=h.param(),
                note='0xb406908c..0xb40690a0 then reads every word below 0x1400000 (20 MiB) and returns 0; the '
                     'wrapper then re-runs the routine at the stored clock. Unreachable: both callers pass r1 = 0.')


# ---------------------------------------------------------------- LPDDR branch
def lpddr_branch(loader, types=(0x10, 0x11, 0x12, 0x01, 0x02), clocks=(200, 400, 468, 533)):
    out = {}
    for t in types:
        for clk in clocks:
            for mode in (0, 1):
                h = Harness(loader, scenario=Scenario('lpddr', idle_self_refresh=True), limit=400_000)
                if mode:
                    h.call(de.F_INI_COPY, r0=de.INI_LOAD)
                else:
                    _second_record(h)
                h.uc.mem_write(de.PARAM, clk.to_bytes(2, 'little'))
                h.uc.mem_write(de.PARAM + 6, bytes([t]))
                h.writes.clear()
                ret = h.call(FN['mode1'] if mode else FN['mode0'], r0=de.PARAM, r1=0)
                regs = {}
                for w in h.writes:
                    regs.setdefault(dm.REG.get(int(w['address'], 16), w['address']), []).append(w['value'])
                last = {k: v[-1] for k, v in regs.items()}
                out[f'type0x{t:02x}-{clk}MHz-mode{mode}'] = dict(
                    return_value=None if h.stopped else hex(ret), stopped=h.stopped['kind'] if h.stopped else None,
                    prints=[p['text'] for p in h.prints][-1:],
                    pir=[w['value'] for w in h.writes if int(w['address'], 16) == de.PIR],
                    final=last)
    # registers whose final value differs from DDR3 (type 0x10) at 468 MHz, mode 0
    ref = out['type0x10-468MHz-mode0']['final']
    diff = {}
    for t in types:
        if t == 0x10:
            continue
        f = out[f'type0x{t:02x}-468MHz-mode0']['final']
        diff[f'type0x{t:02x}'] = {k: [ref.get(k), f.get(k)] for k in sorted(set(ref) | set(f)) if ref.get(k) != f.get(k)}
    return dict(runs=out, differs_from_ddr3_at_468MHz_mode0=diff)


# ---------------------------------------------------------------- geometry distinguishability
ORDERS = {'col-bank-row': ('col', 'bank', 'row', 'rank'), 'col-row-bank': ('col', 'row', 'bank', 'rank'),
          'bank-col-row': ('bank', 'col', 'row', 'rank')}


def geometry_study(loader):
    """Run the firmware's cold-boot probe and memory test against DRAM devices behind each DMM decode
    hypothesis, and group the outcomes the firmware can see (console, write-back, memory test)."""
    shipped = bytes(loader[de.INI_LOAD - de.BASE + 0x1C:de.INI_LOAD - de.BASE + 0x2C]).hex()
    rows = []
    for oname, order in ORDERS.items():
        for ranks in (1, 2):
            for banks in (2, 3):
                for col in (9, 10, 11):
                    for row in (12, 13, 14, 15, 16):
                        dev = DmmDevice(col, row, banks, ranks, order)
                        s = Scenario(f'{oname}', ranks=ranks, col_bits=col, row_bits=row, bank_log2=banks)
                        h = Harness(loader, scenario=s, ram=Ram('dmm', device=dev, float_value=0), limit=600_000)
                        _second_record(h)
                        ret = h.call(FN['mode0'], r0=de.PARAM)
                        wb = None
                        mt = None
                        if h.stopped is None and ret == 0:
                            h.call(de.F_WRITEBACK)
                            wb = bytes(h.uc.mem_read(de.INI_LOAD + 0x1C, 16)).hex()
                            h.prints.clear()
                            h.call(FN['memtest'], r0=h.param()['capacity_mib'])
                            mt = [p['text'] for p in h.prints][-1] if h.prints else None
                        true_mib = (1 << (1 + col + row + banks)) * ranks >> 20
                        rows.append(dict(order=oname, ranks=ranks, banks=1 << banks, col_bits=col, row_bits=row,
                                         true_capacity_mib=true_mib, return_value=hex(ret) if h.stopped is None else None,
                                         reported_capacity_mib=h.param()['capacity_mib'] if ret == 0 else None,
                                         rcc=hex(h.param()['rcc']), cs=h.param()['cs'], writeback=wb,
                                         equals_shipped_primary=wb == shipped, memtest_last_line=mt))
    groups = {}
    for r in rows:
        k = (r['return_value'], r['reported_capacity_mib'], r['rcc'], r['cs'], r['memtest_last_line'])
        groups.setdefault(json.dumps(k), []).append(r)
    matching = [r for r in rows if r['equals_shipped_primary']]
    wrong = [r for r in rows if r['return_value'] == '0x0' and r['reported_capacity_mib'] != r['true_capacity_mib']]
    return dict(hypotheses=list(ORDERS), devices=len(rows), shipped_primary=shipped,
                produce_shipped_record=matching,
                capacity_misreported_but_memtest_ok=[r for r in wrong if r['memtest_last_line'] == '== ok=='],
                capacity_misreported=len(wrong),
                outcome_classes=len(groups), runs=rows)


# ---------------------------------------------------------------- integrated handoff
def handoff(loader, scenario=None, ram=None):
    """Cold boot through the caller (reference PMIC, no S2 flag): DRAM result -> AFI -> U-Boot -> /memory."""
    r, h = run_caller(loader, resume_pmic(s2=False), scenario or Scenario(), ram=ram)
    c = r['caller']
    afi = c['afi']
    reached = c['stopped'] is None and c['return_value'] == '0x0'
    return dict(dram_return=c['return_value'], record=c['record_used'], afi=afi, uboot_reached=reached,
                after_caller='app.bin/U-Boot load' if reached else ('ADFU via 0xb4065494 (no U-Boot)' if c['stopped'] is None
                                                                    else c['stopped']['kind']),
                afi_ddr_size_from_record=hex(afi_ddr_size(c['record_used']['capacity_mib'])),
                uboot=r['uboot_view'] if reached else None, memtest_called=c['memtest_called'], prints=r['prints'],
                ini_primary_after=c['ini_primary_after'])


def derived_capacity(loader, scenario_name='reference'):
    """Capacity (MiB) the stock loader reports to U-Boot under a named training scenario (used by boot_chain.py)."""
    s = next(x for x in TRAINING_SCENARIOS if x.name == scenario_name)
    h = handoff(loader, s)
    if not h['uboot_reached']:
        return None, h
    return h['uboot']['gd_ram_size'] >> 20, h


HANDOFF_CASES = [
    ('reference', Scenario(), None, 'one x16 2 Gb rank'),
    ('two-ranks', Scenario('two-ranks', ranks=2), Ram('wrap', 512 << 20), 'hypothetical 2 ranks'),
    ('1Gb-die', Scenario('1Gb', row_bits=13), Ram('wrap', 128 << 20), 'hypothetical 1 Gb die'),
    ('training-failure', Scenario('fail', training=[False, False]), None, 'both training attempts fail'),
    ('zq-timeout', Scenario('zq', zq_done=False), None, 'ZQ never done'),
    ('memtest-fails', Scenario(), Ram('wrap', 256 << 20, stuck_low=1 << 20), 'memory test reports a data error'),
]


def handoff_cases(loader):
    out = {}
    for name, s, ram, note in HANDOFF_CASES:
        h = handoff(loader, s, ram)
        h['note'] = note
        out[name] = h
    return out


# ---------------------------------------------------------------- evidence
def code_hashes(loader):
    spans = dict(caller=(0xB40665D0, 0xB4066784), memtest=(0xB406631C, 0xB40663F8), resume=(0xB4066B64, 0xB40670E8),
                 dram=(0xB40670E8, 0xB40691A4), pmu=(0xB4069524, 0xB406A1D0), adfu_check=(0xB4069254, 0xB40693F8))
    return {k: hashlib.sha256(loader[a - de.BASE:b - de.BASE]).hexdigest() for k, (a, b) in spans.items()}


def analyse(loader, release, quick=False):
    doc = dict(release=release, loader_sha256=hashlib.sha256(loader).hexdigest(), code_sha256=de.check_code(loader),
               function_hashes=code_hashes(loader))
    doc['memtest'] = memtest_cases(loader)
    doc['training'] = training_scenarios(loader)
    doc['resume'] = resume_cases(loader)
    doc['mode_comparison'] = mode_comparison(loader)
    doc['unreachable_subflag'] = unreachable_subflag(loader)
    doc['handoff'] = handoff_cases(loader)
    if not quick:
        doc['mode1_model_sweep'] = mode1_model_sweep(loader)
        doc['lpddr'] = lpddr_branch(loader)
        doc['geometry'] = geometry_study(loader)
    return doc


def _compact(o):
    """Drop bulky per-run detail from the committed evidence while keeping hashes of it."""
    if isinstance(o, dict):
        return {k: _compact(v) for k, v in o.items() if k not in ('scenario',)}
    if isinstance(o, list):
        return [_compact(x) for x in o]
    return o


def evidence(docs):
    rel = list(docs)
    ref = docs[rel[-1]]
    same = {k: len({json.dumps(normalise_ini_odt(d[k]), sort_keys=True) for d in docs.values()}) == 1
            for k in ('function_hashes', 'memtest', 'resume', 'training', 'unreachable_subflag', 'handoff')}
    out = dict(format_version=1, tool=f'dram_complete.py v{TOOL_VERSION}', reference_release=rel[-1],
               releases={r: dict(loader_sha256=d['loader_sha256'], code_sha256=d['code_sha256'],
                                 function_hashes=d['function_hashes']) for r, d in docs.items()},
               identical_across_releases=same,
               identical_across_releases_note='after removing only the ini ODT/drive bytes and what they change '
                                              '(console wrodt/rdodt/drv, record bytes, MR1, ZQ0CR1) and instruction counts / the pc within a '
                                              'poll loop at the instruction limit (the poll site itself is compared)',
               raw_identical_across_releases={k: len({json.dumps(d[k], sort_keys=True) for d in docs.values()}) == 1
                                              for k in ('memtest', 'resume', 'training')},
               per_release_differences={r: dict(mode_comparison=d['mode_comparison'], handoff_reference=d['handoff']['reference'])
                                        for r, d in docs.items()},
               models=dict(pmic_defaults={hex(k): hex(v) for k, v in PMIC_DEFAULTS.items()},
                           resume_vector_synthetic=hex(RESUME_VECTOR_SYNTH),
                           note='Every PMIC, PUBL, uPCTL and DRAM response is synthetic (see Scenario/Pmic/Ram). '
                                'Nothing was observed on hardware.'),
               internal_codes={hex(k): dict(meaning=v, returned=hex(returned_code(k))) for k, v in INTERNAL_CODES.items()})
    for k in ('memtest', 'training', 'resume', 'mode_comparison', 'unreachable_subflag', 'handoff', 'mode1_model_sweep',
              'lpddr', 'geometry'):
        if k in ref:
            out[k] = _compact(ref[k])
    if 'lpddr' in out:
        for k, v in out['lpddr']['runs'].items():
            if '-468MHz-' not in k:
                v.pop('final', None)
    if 'geometry' in out:
        out['geometry']['runs'] = [r for r in out['geometry']['runs'] if r['equals_shipped_primary']
                                   or r['order'] == 'col-bank-row']
    out['mode1_model_sweep_all'] = {r: d.get('mode1_model_sweep') for r, d in docs.items()}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('evidence')
    e.add_argument('output', type=Path)
    e.add_argument('--loader', action='append', required=True, help='release=loader-region.bin')
    e.add_argument('--quick', action='store_true', help='skip the clock sweep, LPDDR and geometry studies')
    m = sub.add_parser('memtest')
    m.add_argument('loader', type=Path)
    m.add_argument('--capacity', type=int, default=256)
    m.add_argument('--ram', default='wrap:256', help='wrap:MiB or open:MiB')
    r = sub.add_parser('resume')
    r.add_argument('loader', type=Path)
    r.add_argument('--case', default='resume-valid', choices=[c[0] for c in RESUME_CASES])
    a = p.parse_args()
    if a.cmd == 'evidence':
        docs = {}
        for spec in a.loader:
            name, path = spec.split('=', 1)
            docs[name] = analyse(de.load_region(Path(path)), name, a.quick)
        a.output.write_text(json.dumps(evidence(docs), indent=1, sort_keys=False) + '\n')
    elif a.cmd == 'memtest':
        kind, mib = a.ram.split(':')
        res = memtest_emulated(de.load_region(a.loader), a.capacity, Ram(kind, int(mib) << 20))
        res['accesses'] = memtest_summary(res['accesses'])
        print(json.dumps(res, indent=1))
    else:
        case = next(c for c in RESUME_CASES if c[0] == a.case)
        out, _ = run_caller(de.load_region(a.loader), resume_pmic(**case[1]), case[2], case[3])
        print(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
    main()
