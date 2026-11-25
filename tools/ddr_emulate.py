#!/usr/bin/env python3
"""Bounded Unicorn emulation of the stock loader's DRAM routine (0xb40673f4).

Nothing here runs on, or talks to, hardware. The loader's own instructions are
executed inside a Unicorn CPU with *no* peripheral model beyond an explicit,
logged "oracle" for each MMIO read. Every value the firmware reads from a
peripheral or from DRAM is recorded together with the oracle rule that supplied
it, so a reader can see exactly which outputs depend on assumptions.

Execution plan (all addresses are firmware instructions; see
reports/ddr-timing-reconstruction.md):

1. ``0xb4065ff8``: copy bootloader.ini (load ``0xb4062400``) into the
   parameter blocks ``0xb4070820`` (ini+0x1c) and ``0xb407084c`` (ini+0x4c).
2. ``0xb40666ac..0xb40666e4``: the cold-boot caller's record selection: if the
   ini word at +0x2c is non-zero, 12 bytes are copied from ``0xb407084c`` over
   ``0xb4070820`` (byte memcpy ``0xb406af64``).
3. ``0xb40690b8``: the cold-boot wrapper (clears the mode bytes at
   ``0xb4070804``) which calls the DRAM routine ``0xb40673f4``.
4. On success, ``0xb4066280``: the caller's write-back of the parameter block
   over the in-SRAM ini primary record.

Stubs (functions not executed, by design):

* ``0xb40693f8`` busy-wait delay (its only effect is elapsed time; the timer
  base is set up by code outside this window).
* ``0xb4066854`` console printf: arguments are captured and formatted, nothing
  else happens.

Oracle rules for reads (``--scenario`` selects the hardware hypothesis):

* uPCTL STAT follows the last SCTL command (0->0, 1->1, 2->3, 3->5, 4->3),
  the documented DesignWare state encoding; reset state Init_mem (0).
* MCMD reads return the last write with bit 31 (start/busy) cleared.
* POWSTAT, CMDTSTAT, DFISTSTAT0 bit 0 read as 1 (done).
* PUBL PGSR: 0x7 after reset/PIR=0x10000000, 0xf after a DRAM-init PIR,
  and after the training PIR (bit 7) 0x1f (pass) or 0x3f (DTERR) according to
  the scenario's rank/width hypothesis.
* PUBL ZQ0SR0 reads 0x80000000 (done; impedance code unknown, reported as 0).
* DXGSR0 lane status reads 0 (unknown).
* Any other MMIO read returns the last value written there, or the reset seed
  (``--reset-seed``) if never written. Running with two seeds exposes
  reset-dependent bits.
* DRAM reads follow a wrap-around (aliasing) model of a hypothetical device
  geometry: during the column probe addresses wrap at the real column span,
  afterwards at one rank's size. It is only consulted by the capacity probe and
  is a hypothesis about the DMM address map, not a recovered fact.

The result lists every MMIO write in order, every read with its oracle, the
printf lines, the final parameter block and the return value.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

BASE = 0xB4060000
SRAM_SIZE = 0x40000           # analysis window 0xb4060000..0xb40a0000
LOAD_SPAN = 0x19000           # code/data loaded (PACK, ini, bootloader code); app.bin area left zero
INI_LOAD = 0xB4062400
PARAM = 0xB4070820
PARAM2 = 0xB407084C
MODE = 0xB4070804
STACK_TOP = 0xB407F000
SENTINEL = 0xB407FF00         # return address; never executed
MMIO_BASE, MMIO_SIZE = 0xB0000000, 0x00400000
F_INI_COPY = 0xB4065FF8
SEL_START, SEL_END = 0xB40666AC, 0xB40666E4
F_WRAPPER_MODE0 = 0xB40690B8
F_DRAM = 0xB40673F4
F_DELAY = 0xB40693F8
F_PRINTF = 0xB4066854
F_STORE = 0xB40670E8
F_LOAD = 0xB40670F0
F_WRITEBACK = 0xB4066280
BL_SIZE = 0x33C00             # PACK member bootloader.bin
CODE_SPAN = (0x5400, BL_SIZE)  # identical in all four stock releases
INSN_LIMIT = 2_000_000

UPCTL, PUBL = 0xB01C0000, 0xB01C8000
SCTL, STAT, MCMD, POWSTAT, CMDTSTAT = UPCTL + 0x4, UPCTL + 0x8, UPCTL + 0x40, UPCTL + 0x48, UPCTL + 0x4C
DFISTSTAT0 = UPCTL + 0x2C0
PIR, PGSR, ZQ0SR0 = PUBL + 0x4, PUBL + 0xC, PUBL + 0x188
DXGSR0 = tuple(PUBL + 0x1C4 + 0x40 * i for i in range(4))
DCU_CFG = 0xB0290028

SCENARIOS = {
    # name: (ranks present, data width present, column bits, row bits, banks log2)
    'x16-1rank-2Gb': dict(ranks=1, width=16, col_bits=10, row_bits=14, bank_log2=3,
                          note='one x16 DDR3 2Gb die (256 MiB): the geometry the primary record rcc=0x48 encodes'),
    'x16-2rank-2Gb': dict(ranks=2, width=16, col_bits=10, row_bits=14, bank_log2=3,
                          note='hypothetical second rank; not claimed for any board'),
    'x16-1rank-4Gb': dict(ranks=1, width=16, col_bits=10, row_bits=15, bank_log2=3,
                          note='hypothetical 512 MiB die; shows how detection changes outputs'),
    'x16-1rank-1Gb': dict(ranks=1, width=16, col_bits=10, row_bits=13, bank_log2=3,
                          note='hypothetical 128 MiB die'),
}


def _sprintf(fmt, args):
    """Minimal C printf for the loader's format strings (%d %x %%)."""
    out, i, ai = [], 0, 0
    while i < len(fmt):
        c = fmt[i]
        if c != '%':
            out.append(c); i += 1; continue
        j = i + 1
        while j < len(fmt) and fmt[j] in '0123456789-l':
            j += 1
        conv = fmt[j] if j < len(fmt) else ''
        if conv == '%':
            out.append('%')
        elif conv in 'duxi':
            v = args[ai] if ai < len(args) else 0
            ai += 1
            if conv in 'di':
                v = v - (1 << 32) if v & 0x80000000 else v
                out.append(str(v))
            elif conv == 'u':
                out.append(str(v))
            else:
                out.append(format(v, 'x'))
        elif conv == 's':
            out.append('<str>'); ai += 1
        else:
            out.append(fmt[i:j + 1])
        i = j + 1
    return ''.join(out)


def check_code(data):
    if len(data) < BL_SIZE:
        raise ValueError('loader region shorter than bootloader.bin (0x33c00 bytes)')
    return hashlib.sha256(data[CODE_SPAN[0]:CODE_SPAN[1]]).hexdigest()


class Emulation:
    def __init__(self, loader, scenario='x16-1rank-2Gb', reset_seed=0, record='firmware', train_override=None):
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, \
            UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED
        from unicorn import arm_const as A
        self.A = A
        if scenario not in SCENARIOS:
            raise ValueError('unknown scenario')
        if record not in ('firmware', 'primary', 'second'):
            raise ValueError('record must be firmware, primary or second')
        self.hw = SCENARIOS[scenario]
        self.scenario = scenario
        self.seed = reset_seed & 0xFFFFFFFF
        self.record = record
        self.train_override = train_override
        self.loader = bytes(loader[:BL_SIZE])
        self.uc = uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(BASE, SRAM_SIZE)
        uc.mem_write(BASE, self.loader[:LOAD_SPAN])
        uc.mem_map(MMIO_BASE, MMIO_SIZE)
        self.regs = {}                 # MMIO register file (last written)
        self.writes, self.reads, self.prints = [], [], []
        self.dram = {}                 # aliasing DRAM model: physical offset -> byte
        self.dram_pages = set()
        self.dcu_writes = 0
        self.events = []
        self.sctl_state = 0
        self.pgsr = 0x7
        self.insns = 0
        uc.hook_add(UC_HOOK_MEM_READ, self._mmio_read, begin=MMIO_BASE, end=MMIO_BASE + MMIO_SIZE - 1)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._mmio_write, begin=MMIO_BASE, end=MMIO_BASE + MMIO_SIZE - 1)
        uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        uc.hook_add(UC_HOOK_MEM_READ, self._dram_read, begin=0, end=0x7FFFFFFF)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._dram_write, begin=0, end=0x7FFFFFFF)
        uc.hook_add(UC_HOOK_CODE, self._code)

    # ---- helpers -------------------------------------------------------
    def reg(self, name):
        return self.uc.reg_read(getattr(self.A, 'UC_ARM_REG_' + name.upper()))

    def setreg(self, name, v):
        self.uc.reg_write(getattr(self.A, 'UC_ARM_REG_' + name.upper()), v & 0xFFFFFFFF)

    def u32(self, addr):
        return struct.unpack('<I', self.uc.mem_read(addr, 4))[0]

    def cstr(self, addr):
        out = bytearray()
        while len(out) < 512:
            b = self.uc.mem_read(addr + len(out), 1)[0]
            if not b:
                break
            out.append(b)
        return out.decode('latin-1')

    def param(self, addr=PARAM):
        b = bytes(self.uc.mem_read(addr, 12))
        clk, cap = struct.unpack_from('<HH', b)
        return dict(clock_mhz=clk, capacity_mib=cap, bus_sel=b[4], cs=b[5], type=b[6], rcc=b[7],
                    rdodt=b[8], wrodt=b[9], drv=b[10], byte_b=b[11], raw=b.hex())

    def _site(self, accessor):
        """Accessor loads/stores (0xb40670f0/0xb40670e8, reached directly or by tail call from the RMW helpers)
        are attributed to the firmware call site that requested them (lr - 4); other accesses to their own pc."""
        pc = self.reg('pc')
        return self.reg('lr') - 4 if pc == accessor else pc

    # ---- hooks ---------------------------------------------------------
    def _code(self, uc, address, size, user):
        self.insns += 1
        if self.insns > INSN_LIMIT:
            uc.emu_stop()
            self.events.append('instruction limit reached')
            return
        if address == F_DELAY:
            self.setreg('pc', self.reg('lr'))
        elif address == F_PRINTF:
            sp = self.reg('sp')
            args = [self.reg('r1'), self.reg('r2'), self.reg('r3')] + [self.u32(sp + 4 * i) for i in range(10)]
            fmt = self.cstr(self.reg('r0'))
            self.prints.append(dict(pc=hex(self.reg('lr') - 4), format_address=hex(self.reg('r0')),
                                    text=_sprintf(fmt, args).strip('\n')))
            self.setreg('r0', 0)
            self.setreg('pc', self.reg('lr'))

    def _unmapped(self, uc, access, address, size, value, user):
        if address < 0x80000000:       # lazily map DRAM-window pages for the probe model
            page = address & ~0xFFF
            if page not in self.dram_pages:
                uc.mem_map(page, 0x1000)
                self.dram_pages.add(page)
            return True
        return False

    def _training_passes(self):
        if self.train_override is not None:
            return self.train_override
        p = self.param()
        cfg_width = 16 if p['bus_sel'] else 32
        return p['cs'] <= self.hw['ranks'] and cfg_width <= self.hw['width']

    def _oracle(self, addr):
        if addr == STAT:
            return self.sctl_state, 'STAT follows last SCTL command'
        if addr == MCMD:
            return self.regs.get(addr, 0) & 0x7FFFFFFF, 'MCMD start bit cleared (command done)'
        if addr in (POWSTAT, CMDTSTAT, DFISTSTAT0):
            return 1, 'done bit set'
        if addr == PGSR:
            return self.pgsr, 'PGSR follows last PIR and scenario training result'
        if addr == ZQ0SR0:
            return 0x80000000, 'ZQ done; impedance code unknown'
        if addr in DXGSR0:
            return 0, 'lane status unknown'
        if addr in self.regs:
            return self.regs[addr], 'last written value'
        return self.seed, 'reset seed (unknown reset value)'

    def _mmio_read(self, uc, access, address, size, value, user):
        a = address & ~3
        v, rule = self._oracle(a)
        uc.mem_write(a, struct.pack('<I', v & 0xFFFFFFFF))
        self.reads.append(dict(site=hex(self._site(F_LOAD)), address=hex(a), value=hex(v), rule=rule))

    def _mmio_write(self, uc, access, address, size, value, user):
        a = address & ~3
        v = value & ((1 << (8 * size)) - 1)
        if size != 4:
            old = self.regs.get(a, self.seed)
            sh = 8 * (address - a)
            v = (old & ~(((1 << (8 * size)) - 1) << sh)) | (v << sh)
        self.regs[a] = v
        self.writes.append(dict(site=hex(self._site(F_STORE)), address=hex(a), value=hex(v)))
        if a == SCTL:
            self.sctl_state = {0: 0, 1: 1, 2: 3, 3: 5, 4: 3}.get(v & 7, self.sctl_state)
        elif a == PIR:
            if v & 0x80:
                self.pgsr = 0x1F if self._training_passes() else 0x3F
                self.events.append(f"training PIR=0x{v:x} with cs={self.param()['cs']} bus_sel={self.param()['bus_sel']}: "
                                   + ('pass' if self.pgsr == 0x1F else 'DTERR'))
            elif v & 0x1:
                self.pgsr = 0xF
            else:
                self.pgsr = 0x7
        elif a == DCU_CFG:
            self.dcu_writes += 1

    # Aliasing DRAM model. Only the capacity probe reads DRAM in this window.
    def _phys(self, address):
        hw = self.hw
        wlog = 1 if hw['width'] == 16 else 2
        if self.dcu_writes == 2:        # column probe phase: wrap at the real column span
            mod = 1 << (wlog + hw['col_bits'])
        else:                           # row probe / later: wrap at total capacity
            mod = 1 << (wlog + hw['col_bits'] + hw['row_bits'] + hw['bank_log2'])   # per-rank wrap (hypothesis)
        return address % mod

    def _dram_write(self, uc, access, address, size, value, user):
        p = self._phys(address)
        for i in range(size):
            self.dram[p + i] = (value >> (8 * i)) & 0xFF
        self.events.append(f'DRAM write 0x{address:x} (phys 0x{p:x}) = 0x{value & ((1 << 8 * size) - 1):x}')

    def _dram_read(self, uc, access, address, size, value, user):
        p = self._phys(address)
        v = sum(self.dram.get(p + i, 0) << (8 * i) for i in range(size))
        uc.mem_write(address, v.to_bytes(size, 'little'))
        self.reads.append(dict(site=hex(self._site(F_LOAD)), address=hex(address), value=hex(v),
                               rule=f'DRAM aliasing model ({self.scenario}), phys 0x{p:x}'))

    # ---- drivers -------------------------------------------------------
    def call(self, entry, r0=0, r1=0, until=SENTINEL):
        self.setreg('sp', STACK_TOP)
        self.setreg('lr', SENTINEL)
        self.setreg('r0', r0)
        self.setreg('r1', r1)
        self.uc.emu_start(entry, until, count=INSN_LIMIT)
        return self.reg('r0')

    def run(self):
        self.call(F_INI_COPY, r0=INI_LOAD)
        ini_param = dict(primary=self.param(PARAM), second=self.param(PARAM2))
        if self.record == 'firmware':
            self.setreg('sp', STACK_TOP)
            self.uc.emu_start(SEL_START, SEL_END, count=10_000)
            selected = 'second' if bytes(self.uc.mem_read(PARAM, 12)) == bytes(self.uc.mem_read(PARAM2, 12)) \
                and self.u32(INI_LOAD + 0x2C) else 'primary'
        else:
            selected = self.record
            if selected == 'second':
                self.uc.mem_write(PARAM, bytes(self.uc.mem_read(PARAM2, 12)))
        before = self.param()
        self.writes.clear(); self.reads.clear()
        ret = self.call(F_WRAPPER_MODE0, r0=PARAM)
        writeback = None
        if ret == 0:
            # Cold-boot caller, success branch: 0xb4066280 copies the parameter block back over the
            # in-SRAM bootloader.ini primary record (ini+0x1c..+0x2b, with +0x1e/+0x1f/+0x22/+0x23 zeroed).
            self.call(F_WRITEBACK)
            writeback = bytes(self.uc.mem_read(INI_LOAD + 0x1C, 16)).hex()
        return dict(ini_primary_after_writeback=writeback,
                    ini_primary_as_shipped=self.loader[INI_LOAD - BASE + 0x1C:INI_LOAD - BASE + 0x2C].hex(),scenario=self.scenario, scenario_hypothesis=self.hw, reset_seed=hex(self.seed),
                    record_selection=self.record, selected_record=selected,
                    ini_word_0x2c=self.u32(INI_LOAD + 0x2C), ini_records=ini_param,
                    param_before=before, param_after=self.param(), return_value=hex(ret),
                    instructions=self.insns, prints=self.prints, events=self.events,
                    mmio_writes=self.writes, reads=self.reads)


def emulate(loader, **kw):
    r = Emulation(loader, **kw).run()
    r['code_sha256'] = check_code(loader)
    return r


def load_region(path, image_offset=None):
    """Loader region from a 448-sector region file or from a disk image at an offset."""
    with open(path, 'rb') as f:
        if image_offset is not None:
            f.seek(image_offset)
            return f.read(448 * 512)
        data = f.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError('region larger than 4 MiB; pass --image-offset for disk images')
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', type=Path, help='loader region (448 sectors) or disk image with --image-offset')
    p.add_argument('output', type=Path)
    p.add_argument('--image-offset', type=lambda x: int(x, 0), help='e.g. 0x200200 for a stock image')
    p.add_argument('--scenario', default='x16-1rank-2Gb', choices=sorted(SCENARIOS))
    p.add_argument('--reset-seed', type=lambda x: int(x, 0), default=0)
    p.add_argument('--record', default='firmware', choices=('firmware', 'primary', 'second'))
    a = p.parse_args()
    data = load_region(a.input, a.image_offset)
    a.output.write_text(json.dumps(emulate(data, scenario=a.scenario, reset_seed=a.reset_seed, record=a.record),
                                   indent=1) + '\n')


if __name__ == '__main__':
    main()
