#!/usr/bin/env python3
"""Readable model of the stock RG35XX loader's DDR3 timing calculations.

This is a clean re-statement, in Python, of what the loader routine at
``0xb40673f4`` computes for a DDR3 record (``type & 0xf == 0``) on the cold-boot
path (mode 0). It was written from the instructions (Capstone listing, with
Ghidra used locally as a reading aid) and is *checked*, not trusted:

* tests compare its complete MMIO write sequence with bounded Unicorn
  emulation of the firmware for every clock 100..1200 MHz and every recorded
  hardware hypothesis (tools/ddr_emulate.py);
* each clock-dependent value is proven equal to the z3 expression that the
  independent symbolic interpreter derives from the instructions
  (tools/ddr_symbolic.py), over the whole analysed clock domain.

Inputs are split by provenance, and every output carries one of these classes:

``constant``     immediate or literal-pool value in the firmware
``ini``          a deterministic function of bootloader.ini fields (incl. clock)
``detected``     depends on a hardware-dependent outcome: the rank count that
                 survived PUBL data training, or the capacity probe result
``reset``        bits preserved from an unknown hardware reset value (RMW)

The LPDDR branch (``type & 0xf != 0``) and the resume path (mode 1) are not
modelled; ``ddr_symbolic.py`` can still analyse them.

Register names follow the public DesignWare uPCTL/PUBL layout in U-Boot's
``ddr_rk3288.h`` (pinned in evidence); that the ATM7039S uses this IP is a
strongly supported inference (DDR-001), not a vendor statement. Names in
``TIMING_NOTES`` that go beyond the register name are interpretations.
"""
from dataclasses import dataclass, field

UPCTL, PUBL, DMM, CMU = 0xB01C0000, 0xB01C8000, 0xB0290000, 0xB0160000

REG = {  # address -> name (uPCTL/PUBL from ddr_rk3288.h; CMU/DMM from the vendor clock tree / report)
    CMU + 0x08: 'CMU_DDRPLL', CMU + 0xA0: 'CMU_DEVCLKEN0', CMU + 0xA8: 'CMU_DEVRST0',
    UPCTL + 0x000: 'uPCTL.SCFG', UPCTL + 0x004: 'uPCTL.SCTL', UPCTL + 0x040: 'uPCTL.MCMD',
    UPCTL + 0x044: 'uPCTL.POWCTL', UPCTL + 0x050: 'uPCTL.TSTATEN', UPCTL + 0x07C: 'uPCTL.MCFG1',
    UPCTL + 0x080: 'uPCTL.MCFG', UPCTL + 0x084: 'uPCTL.PPCFG', UPCTL + 0x0C0: 'uPCTL.TOGCNT1U',
    UPCTL + 0x0C4: 'uPCTL.TINIT', UPCTL + 0x0C8: 'uPCTL.TRSTH', UPCTL + 0x0CC: 'uPCTL.TOGCNT100N',
    UPCTL + 0x0D0: 'uPCTL.TREFI', UPCTL + 0x0D4: 'uPCTL.TMRD', UPCTL + 0x0D8: 'uPCTL.TRFC',
    UPCTL + 0x0DC: 'uPCTL.TRP', UPCTL + 0x0E0: 'uPCTL.TRTW', UPCTL + 0x0E4: 'uPCTL.TAL',
    UPCTL + 0x0E8: 'uPCTL.TCL', UPCTL + 0x0EC: 'uPCTL.TCWL', UPCTL + 0x0F0: 'uPCTL.TRAS',
    UPCTL + 0x0F4: 'uPCTL.TRC', UPCTL + 0x0F8: 'uPCTL.TRCD', UPCTL + 0x0FC: 'uPCTL.TRRD',
    UPCTL + 0x100: 'uPCTL.TRTP', UPCTL + 0x104: 'uPCTL.TWR', UPCTL + 0x108: 'uPCTL.TWTR',
    UPCTL + 0x10C: 'uPCTL.TEXSR', UPCTL + 0x110: 'uPCTL.TXP', UPCTL + 0x114: 'uPCTL.TXPDLL',
    UPCTL + 0x118: 'uPCTL.TZQCS', UPCTL + 0x11C: 'uPCTL.TZQCSI', UPCTL + 0x120: 'uPCTL.TDQS',
    UPCTL + 0x124: 'uPCTL.TCKSRE', UPCTL + 0x128: 'uPCTL.TCKSRX', UPCTL + 0x12C: 'uPCTL.TCKE',
    UPCTL + 0x130: 'uPCTL.TMOD', UPCTL + 0x134: 'uPCTL.TRSTL', UPCTL + 0x138: 'uPCTL.TZQCL',
    UPCTL + 0x13C: 'uPCTL.TMRR', UPCTL + 0x140: 'uPCTL.TCKESR', UPCTL + 0x144: 'uPCTL.TDPD',
    UPCTL + 0x148: 'uPCTL+0x148 (reserved5[0] in ddr_rk3288.h)', UPCTL + 0x180: 'uPCTL.ECCCFG',
    UPCTL + 0x240: 'uPCTL.DFITCTRLDELAY', UPCTL + 0x244: 'uPCTL.DFIODTCFG', UPCTL + 0x24C: 'uPCTL.DFIODTRANKMAP',
    UPCTL + 0x250: 'uPCTL.DFITPHYWRDATA', UPCTL + 0x254: 'uPCTL.DFITPHYWRLAT', UPCTL + 0x260: 'uPCTL.DFITRDDATAEN',
    UPCTL + 0x264: 'uPCTL.DFITPHYRDLAT', UPCTL + 0x270: 'uPCTL.DFITPHYUPDTYPE0', UPCTL + 0x280: 'uPCTL.DFITCTRLUPDMIN',
    UPCTL + 0x284: 'uPCTL.DFITCTRLUPDMAX', UPCTL + 0x288: 'uPCTL.DFITCTRLUPDDLY', UPCTL + 0x2C4: 'uPCTL.DFISTCFG0',
    UPCTL + 0x2C8: 'uPCTL.DFISTCFG1', UPCTL + 0x2D0: 'uPCTL.DFITDRAMCLKEN', UPCTL + 0x2D4: 'uPCTL.DFITDRAMCLKDIS',
    UPCTL + 0x2D8: 'uPCTL.DFISTCFG2', UPCTL + 0x2F0: 'uPCTL.DFILPCFG0',
    PUBL + 0x04: 'PUBL.PIR', PUBL + 0x08: 'PUBL.PGCR', PUBL + 0x14: 'PUBL.ACDLLCR', PUBL + 0x18: 'PUBL.PTR0',
    PUBL + 0x1C: 'PUBL.PTR1', PUBL + 0x20: 'PUBL.PTR2', PUBL + 0x24: 'PUBL.ACIOCR', PUBL + 0x28: 'PUBL.DXCCR',
    PUBL + 0x2C: 'PUBL.DSGCR', PUBL + 0x30: 'PUBL.DCR', PUBL + 0x34: 'PUBL.DTPR0', PUBL + 0x38: 'PUBL.DTPR1',
    PUBL + 0x3C: 'PUBL.DTPR2', PUBL + 0x40: 'PUBL.MR0', PUBL + 0x44: 'PUBL.MR1', PUBL + 0x48: 'PUBL.MR2',
    PUBL + 0x4C: 'PUBL.MR3', PUBL + 0x50: 'PUBL.ODTCR', PUBL + 0x54: 'PUBL.DTAR', PUBL + 0x184: 'PUBL.ZQ0CR1',
    PUBL + 0x1C0: 'PUBL.DX0GCR', PUBL + 0x200: 'PUBL.DX1GCR', PUBL + 0x240: 'PUBL.DX2GCR', PUBL + 0x280: 'PUBL.DX3GCR',
    PUBL + 0x3FC: 'PUBL+0x3fc (outside ddr_rk3288.h)',
    DMM + 0x00: 'DMM+0x00', DMM + 0x04: 'DMM+0x04', DMM + 0x0C: 'DMM+0x0c', DMM + 0x10: 'DMM+0x10',
    DMM + 0x24: 'DMM+0x24', DMM + 0x28: 'DMM DCU_CFG (+0x28; name from the loader string)', DMM + 0x64: 'DMM+0x64',
    DMM + 0x68: 'DMM+0x68', DMM + 0x80: 'DMM+0x80', DMM + 0x88: 'DMM+0x88', 0xB01B00B4: '0xb01b00b4',
}

# tRFC (ns) by per-rank density (MiB) as the loader selects it (literals 110/160/260/350 in 0xb40673f4)
TRFC_NS = ((256, 110), (512, 160), (1024, 260))
TRFC_NS_MAX = 350


@dataclass
class Record:
    """The 12-byte DRAM record at 0xb4070820 (copied from bootloader.ini)."""
    clock_mhz: int
    capacity_mib: int
    bus_sel: int
    cs: int
    type: int
    rcc: int
    rdodt: int
    wrodt: int
    drv: int

    @classmethod
    def from_bytes(cls, b):
        return cls(int.from_bytes(b[0:2], 'little'), int.from_bytes(b[2:4], 'little'), *b[4:11])


class ResetAll(dict):
    """Reset-value map that answers ``seed`` for every register not listed (mirrors ddr_emulate --reset-seed)."""

    def __init__(self, seed, **known):
        super().__init__(**known)
        self.seed = seed & 0xFFFFFFFF

    def get(self, key, default=None):
        return super().get(key, self.seed)


@dataclass
class Hardware:
    """Hardware-dependent outcomes the firmware observes (inputs to the model, never inferred by it)."""
    ranks: int = 1                 # rank count for which PUBL data training passes
    width: int = 16                # data width for which training passes
    col_code: int = 2              # capacity probe result, columns (rcc bits 3:2)
    row_code: int = 1              # capacity probe result, rows (rcc bits 7:6)
    reset: dict = field(default_factory=dict)   # address -> reset value for RMW'd registers (unknown; default 0)

    def trains(self, cs, bus_sel):
        return cs <= self.ranks and (16 if bus_sel else 32) <= self.width


@dataclass
class Write:
    address: int
    value: int
    cls: str
    formula: str
    site: int = None

    @property
    def register(self):
        return REG.get(self.address, hex(self.address))


def udiv(a, b):
    return a // b


def timings(F, cs, bus_sel, capacity_mib=0x800):
    """All DDR3 timing quantities computed by 0xb40673f4 for rounded clock F (MHz).

    Returns a dict of named integers (clock cycles unless noted). Names follow
    the uPCTL register each value is written to. ``capacity_mib`` is the value
    the routine holds at this point: in mode 0 it is forced to 0x800 (2048).
    """
    density = udiv(udiv(capacity_mib, 1 if bus_sel else 2), cs)
    trfc_ns = next((ns for lim, ns in TRFC_NS if density < lim), TRFC_NS_MAX)
    t = dict(F=F, density_mib=density, tRFC_ns=trfc_ns, tRFC=udiv(F * trfc_ns, 1000) + 1)
    if F <= 400:
        t.update(tRP=udiv(F * 15, 1000) + 1, tRAS=udiv(F * 375, 10000) + 1, tFAW=udiv(F, 20) + 1,
                 tRRD=4, CWL=5, CL=6, tXP=3, tCKE=3)
    elif F <= 533:
        t.update(tRP=udiv(F * 15, 1000) + 1, tRAS=udiv(F * 375, 10000) + 1, tFAW=udiv(F, 20) + 1,
                 tRRD=udiv(F, 100) + 1, CWL=6, CL=8, tXP=4, tCKE=3)
    elif F < 668:
        t.update(tRP=udiv(F * 15, 1000) + 1, tRAS=udiv(F * 36, 1000) + 1, tFAW=udiv(F * 45, 1000) + 1,
                 tRRD=udiv(F * 75, 10000) + 1, CWL=7, CL=10, tXP=udiv(F * 6, 1000) + 1, tCKE=4)
    elif F < 801:
        t.update(tRP=udiv(F * 1375, 100000) + 1, tRAS=udiv(F * 35, 1000) + 1, tFAW=udiv(F, 25) + 1,
                 tRRD=udiv(F * 75, 10000) + 1, CWL=8, CL=11, tXP=5, tCKE=udiv(F, 200) + 1)
    else:
        x = udiv(F * 6, 1000) + 1
        t.update(tRP=udiv(F * 1391, 100000) + 1, tRAS=udiv(F * 34, 1000) + 1, tFAW=udiv(F * 35, 1000) + 1,
                 tRRD=x, CWL=9, CL=13, tXP=x, tCKE=udiv(F, 200) + 1)
    t['tRCD'] = t['tRP']
    t['tRC'] = t['tRP'] + t['tRAS']
    t['tREFI_cycles'] = udiv(F * 78, 10)            # 7.8 us in cycles
    t['TRTW'] = t['CL'] + 6 - t['CWL']
    if F > 533:
        t['tRTP'] = t['tWTR'] = udiv(F * 75, 10000) + 1
    else:
        t['tRTP'] = t['tWTR'] = 4
    if F >= 400 or F > 533:
        t['tWR'] = udiv(F * 15, 1000) + 1
        t['tXPDLL'] = 10 if F <= 416 else udiv(F * 24, 1000) + 1
    else:
        t['tWR'], t['tXPDLL'] = 6, 10
    t['tCKSRE'] = t['tCKSRX'] = 5 if F < 500 else udiv(F, 100) + 1
    t['tRSTL'] = udiv(F * 150, 1000)
    t['tCKESR'] = t['tCKE'] + 1
    t['tZQCSI'] = t['tREFI_cycles'] << 3
    t['dfi_wrlat'] = ((t['CWL'] - 2) if t['CWL'] % 2 == 0 else (t['CWL'] - 1)) >> 1
    t['dfi_rddata_en'] = ((t['CL'] - 2) if t['CL'] % 2 == 0 else (t['CL'] - 3)) >> 1
    return t


RTT_NOM = {0: 0, 1: 0x4, 2: 0x40, 3: 0x44, 4: 0x200, 5: 0x204}   # MR1 bits from the wrodt byte (0xb40673f4)
ZQ_ODT = {1: 0x40, 2: 0x20, 3: 0x60, 4: 0xC0}                    # ZQ0CR1 bits 7:4 from rdodt; default 0x80


def packed(t, rec):
    """Register values packed from the timing quantities (DDR3 branch)."""
    F = t['F']
    tdllsrst = udiv(F * 80, 1000) + 1 if F * 80 <= 62999 else 0x3F
    p = {
        'MCFG': ((udiv(t['tFAW'], t['tRRD']) - 3) << 18 | 0x28029) & 0xFFFFFFFF,
        'MCFG1': ((t['tRRD'] * (udiv(t['tFAW'], t['tRRD']) + 1) - t['tFAW']) << 8) & 0xFFFFFFFF,
        'MR0': (t['CL'] - 4) << 4 | 0x1100 | t['tWR'] << 9,
        'MR1': RTT_NOM.get(rec.wrodt, 0) | 2,
        'MR2': (t['CWL'] - 5) << 3 | 0x240,
        'PTR0': tdllsrst | (udiv(F * 0x1400, 1000) + 1) << 6 | 0x280000,
        'PTR1': F * 500 | (t['tRFC'] + udiv(F, 100)) << 19,
        'PTR2': F * 200 | F << 17,
        'DTPR0': (t['tRP'] << 8 | t['tRCD'] << 12 | t['tRAS'] << 16 | t['tRRD'] << 21 | t['tRC'] << 25
                  | t['tRTP'] << 2 | t['tWTR'] << 5) & 0xFFFFFFFF,
        'DTPR1': t['tRFC'] << 16 | t['tFAW'] << 3,
        'DTPR2': t['tCKESR'] << 15 | 0x10000200 | t['tXPDLL'] << 10,
        'TREFI': 78 | 0x70000,
        'DMM80': ((t['tRC'] + 3) >> 2) + 1 | (((t['tRTP'] + t['tRCD'] - 1 + (t['tRP'] & 0x1F)) >> 2) + 1) << 8
                 | (((t['tWR'] + t['tRCD'] + 3 + t['CWL'] + (t['tRP'] & 0x1F)) >> 2) + 1) << 4,
    }
    return p


class Sequencer:
    """Builds the MMIO write sequence, tracking RMW state like the hardware register file would."""

    RANK = ('constant', 'ini', 'detected', 'reset')

    def __init__(self, hw):
        self.hw, self.regs, self.taint, self.out = hw, {}, {}, []
        self.context = 'constant'       # taint of the branch condition currently being modelled

    def cur(self, a):
        return self.regs.get(a, self.hw.reset.get(a, 0))

    def join(self, *classes):
        return max(classes, key=self.RANK.index)

    def w(self, a, v, cls, formula):
        v &= 0xFFFFFFFF
        cls = self.join(cls, self.context)
        self.regs[a] = v
        self.taint[a] = cls
        self.out.append(Write(a, v, cls, formula))

    def rmw(self, a, v, formula):
        # read-modify-write keeps the bits (and the provenance) of the previous value
        self.w(a, v, self.taint.get(a, 'reset'), formula)

    def clear(self, a, m, formula=None):
        self.rmw(a, self.cur(a) & ~m, formula or f'prev & ~{m:#x}')

    def set(self, a, m, formula=None):
        self.rmw(a, self.cur(a) | m, formula or f'prev | {m:#x}')


def attempt(seq, rec, cs, F):
    """One pass of the init loop (0xb40674dc..): returns True if training passes."""
    w = seq.w
    t = timings(F, cs, rec.bus_sel)
    p = packed(t, rec)
    seq.clear(CMU + 0x08, 0x100)
    seq.clear(CMU + 0xA0, 0xA)
    seq.clear(CMU + 0xA8, 0x5)
    seq.set(CMU + 0xA8, 0x5)
    w(CMU + 0x08, (udiv(F, 12) & 0xFF) | 0x300, 'ini', '(F/12) | 0x300  (F/12 = PLL multiple of 12 MHz)')
    seq.set(CMU + 0xA0, 0xA)
    w(PUBL + 0x14, 0, 'constant', '0'); w(PUBL + 0x14, 0x40000000, 'constant', 'DLLSRST')
    w(PUBL + 0x04, 0x10000000, 'constant', 'PIR_CLRSR')
    w(UPCTL + 0x280, 4, 'constant', '4'); w(UPCTL + 0x284, 10, 'constant', '10'); w(UPCTL + 0x288, 8, 'constant', '8')
    w(UPCTL + 0x0C0, F >> 1, 'ini', 'F >> 1   (1 us in controller clocks, F/2)')
    w(UPCTL + 0x0CC, udiv(F, 20), 'ini', 'F / 20  (100 ns in controller clocks)')
    w(UPCTL + 0x0C4, 200, 'constant', '200'); w(UPCTL + 0x0C8, 500, 'constant', '500 (DDR3 branch)')
    w(DMM + 0x64, 1, 'constant', '1'); w(DMM + 0x64, 0, 'constant', '0')
    w(UPCTL + 0x044, 1, 'constant', 'POWER_UP_START')
    w(UPCTL + 0x080, p['MCFG'], 'ini', '((tFAW/tRRD) - 3) << 18 | 0x28029')
    w(UPCTL + 0x07C, p['MCFG1'], 'ini', '(tRRD*(tFAW/tRRD + 1) - tFAW) << 8')
    w(PUBL + 0x30, 0xB, 'constant', '0xb (DDR3 branch)')
    w(PUBL + 0x40, p['MR0'], 'ini', '(CL-4)<<4 | 0x1100 | tWR<<9')
    w(PUBL + 0x44, p['MR1'], 'ini', 'RTT_NOM[wrodt] | 2')
    w(PUBL + 0x48, p['MR2'], 'ini', '(CWL-5)<<3 | 0x240')
    w(PUBL + 0x18, p['PTR0'], 'ini', 'min63(F*80/1000+1) | (F*5120/1000+1)<<6 | 0xa<<18')
    w(PUBL + 0x1C, p['PTR1'], 'ini', 'F*500 | (tRFC + F/100)<<19')
    w(PUBL + 0x20, p['PTR2'], 'ini', 'F*200 | F<<17')
    w(PUBL + 0x34, p['DTPR0'], 'ini', 'tRTP<<2|tWTR<<5|tRP<<8|tRCD<<12|tRAS<<16|tRRD<<21|tRC<<25')
    w(PUBL + 0x38, p['DTPR1'], 'ini', 'tFAW<<3 | tRFC<<16')
    w(PUBL + 0x3C, p['DTPR2'], 'ini', '0x200 | tXPDLL<<10 | tCKESR<<15 | 0x200<<19')
    w(PUBL + 0x54, 0x20000000, 'constant', '0x20000000')
    seq.context = 'ini'                 # constants below are selected by rdodt/wrodt/bus_sel/type branches
    if rec.rdodt == 0:
        w(PUBL + 0x28, 0x800, 'constant', '0x800'); w(PUBL + 0x50, 0, 'constant', '0')
        w(PUBL + 0x184, rec.drv, 'ini', 'drv')
        w(PUBL + 0x24, 0xBC3F8F6, 'constant', '0xbc3f8f6')
        for lane in range(4):
            seq.clear(PUBL + 0x1C0 + 0x40 * lane, 0x786)
    else:
        w(PUBL + 0x28, 0x911, 'constant', '0x911'); w(PUBL + 0x50, 0x21, 'constant', '0x21')
        w(PUBL + 0x184, ZQ_ODT.get(rec.rdodt, 0x80) | rec.drv, 'ini', 'ZQ_ODT[rdodt] | drv')
        w(PUBL + 0x24, 0xBC03812, 'constant', '0xbc03812')
    if rec.wrodt:
        seq.set(PUBL + 0x50, 0x210000)
    if rec.bus_sel == 0:
        seq.set(PUBL + 0x240, 1); seq.set(PUBL + 0x280, 1)
    else:
        seq.clear(PUBL + 0x240, 1); seq.clear(PUBL + 0x280, 1)
    if rec.type == 2:
        w(PUBL + 0x3FC, 1, 'constant', '1')
    w(PUBL + 0x2C, 0xF2001807, 'constant', '0xf2001807 (DDR3 branch)')
    seq.context = 'constant'
    w(PUBL + 0x08, 0x1842E02 if cs == 1 else 0x18C2E02, 'detected', 'cs==1 ? 0x1842e02 : 0x18c2e02 (rank enables)')
    w(PUBL + 0x04, 0x7F, 'constant', 'PIR 0x7f (DDR3, mode 0)')
    w(PUBL + 0x04, 0x81, 'constant', 'PIR_INIT|PIR_QSTRN (data training)')
    return t, p


def after_training(seq, rec, cs, t, p):
    w = seq.w
    F = t['F']
    for reg, key in ((0xD4, None), (0xD8, 'tRFC'), (0xDC, 'tRP'), (0xE4, None), (0xE8, 'CL'), (0xEC, 'CWL'),
                     (0xF0, 'tRAS'), (0xF4, 'tRC'), (0xF8, 'tRCD'), (0xFC, 'tRRD'), (0x100, 'tRTP'), (0x104, 'tWR'),
                     (0x108, 'tWTR')):
        if key is None:
            w(UPCTL + reg, 4 if reg == 0xD4 else 0, 'constant', '4' if reg == 0xD4 else '0')
        else:
            w(UPCTL + reg, t[key], 'ini', key)
    w(UPCTL + 0x10C, 512, 'constant', '512')
    w(UPCTL + 0x0D0, p['TREFI'], 'constant', '78 | 0x70000')
    w(UPCTL + 0x148, t['tREFI_cycles'], 'ini', 'F*78/10')
    w(UPCTL + 0x110, t['tXP'], 'ini', 'tXP')
    w(UPCTL + 0x120, 1, 'constant', '1')
    w(UPCTL + 0x0E0, t['TRTW'], 'ini', 'CL + 6 - CWL')
    w(UPCTL + 0x124, t['tCKSRE'], 'ini', 'F<500 ? 5 : F/100+1')
    w(UPCTL + 0x128, t['tCKSRX'], 'ini', 'F<500 ? 5 : F/100+1')
    w(UPCTL + 0x130, 12, 'constant', '12')
    w(UPCTL + 0x12C, t['tCKE'], 'ini', 'tCKE')
    w(UPCTL + 0x13C, 2, 'constant', '2')
    w(UPCTL + 0x134, t['tRSTL'], 'ini', 'F*150/1000')
    w(UPCTL + 0x118, 0x40, 'constant', '64')
    w(UPCTL + 0x138, 0x200, 'constant', '512')
    w(UPCTL + 0x114, t['tXPDLL'], 'ini', 'tXPDLL')
    w(UPCTL + 0x11C, t['tZQCSI'], 'ini', '(F*78/10) << 3')
    w(UPCTL + 0x140, t['tCKESR'], 'ini', 'tCKE + 1')
    w(UPCTL + 0x144, 0, 'constant', '0')
    rank = 0x100000 if cs == 1 else 0x300000
    w(UPCTL + 0x040, 0x80000000 | rank, 'detected', 'START | rank mask(cs) | NOP')
    w(UPCTL + 0x040, 0x80000001 | rank, 'detected', 'START | rank mask(cs) | 1')
    w(UPCTL + 0x004, 1, 'constant', 'CFG_STATE (via 0xb4067170)')
    w(UPCTL + 0x000, 0x700, 'constant', '0x700')
    w(UPCTL + 0x264, 10, 'constant', '10'); w(UPCTL + 0x250, 0, 'constant', '0')
    w(UPCTL + 0x084, 1 if rec.bus_sel else 0, 'ini', 'bus_sel ? 1 : 0')
    w(UPCTL + 0x24C, 0x21 if cs == 2 else 1, 'detected', 'cs==2 ? 0x21 : 1')
    for reg, v in ((0x2C4, 7), (0x2C8, 3), (0x2D8, 3), (0x2F0, 0x70101), (0x180, 0)):
        w(UPCTL + reg, v, 'constant', hex(v))
    w(UPCTL + 0x254, t['dfi_wrlat'], 'ini', '(CWL even ? CWL-2 : CWL-1) >> 1')
    w(UPCTL + 0x260, t['dfi_rddata_en'], 'ini', '(CL even ? CL-2 : CL-3) >> 1')
    for reg, v in ((0x2D4, 2), (0x2D0, 2), (0x240, 2), (0x270, 1)):
        w(UPCTL + reg, v, 'constant', hex(v))
    seq.context = 'ini'
    if rec.wrodt:
        w(UPCTL + 0x244, 0x808, 'constant', '0x808')
    if rec.rdodt:
        seq.set(UPCTL + 0x244, 0x202)
    seq.context = 'constant'
    w(UPCTL + 0x050, 1, 'constant', '1')
    w(UPCTL + 0x004, 2, 'constant', 'GO_STATE (via 0xb4067170)')
    w(DMM + 0x88, 1, 'constant', '1')
    bw = 1 - rec.bus_sel if rec.bus_sel <= 1 else 0
    w(DMM + 0x28, bw | 8 | bw << 12 | (cs - 1) << 4, 'detected', 'x32 | 8 | x32<<12 | (cs-1)<<4')
    seq.set(DMM + 0x00, 0x40000000)
    w(DMM + 0x24, 2, 'constant', '2')
    w(DMM + 0x80, p['DMM80'], 'ini', '((tRC+3)>>2)+1 | (((tWR+tRCD+3+CWL+tRP)>>2)+1)<<4 | (((tRTP+tRCD-1+tRP)>>2)+1)<<8')
    seq.set(DMM + 0x00, 0x8000000)


def capacity_probe(seq, rec, cs, hw):
    """rcc/capacity resolution (0xb4068c5c..0xb4068f30) for mode 0. Returns (rcc, capacity_mib, error)."""
    rcc = rec.rcc & 0xCF
    w = seq.w
    if rec.rcc & 0xCC == 0:
        c = min(hw.col_code, 3)
        w(DMM + 0x28, (seq.cur(DMM + 0x28) & 0xFFFE1F99) | 0x2006, 'detected', 'prev & 0xfffe1f99 | 0x2006 (column probe)')
        rcc |= c << 2
        w(DMM + 0x28, (seq.cur(DMM + 0x28) & 0xFFFFFF99) | c << 1 | 0x60, 'detected', 'prev & 0xffffff99 | col<<1 | 0x60 (row probe)')
        base = 0x19 if rec.bus_sel else 0x1A
        r = hw.row_code
        if r > 3 or base + c + r >= 0x20:
            return None, None, 'row probe exhausted (0xf000fa11) or limit'
        rcc |= r << 6
    bw = 1 if rec.bus_sel else 2
    n = (rcc >> 6) + ((rcc & 0xC) >> 2) + bw + cs + 0x17
    if n > 0x1F:
        return rcc, None, 'capacity exponent > 31 (0xc000fa11)'
    n -= 0x14
    cap = ((0x10000 << n) >> 16) & 0xFFFF if rcc & 3 == 0 else (((3 << n) + (3 if (3 << n) < 0 else 0)) << 14 >> 16) & 0xFFFF
    return rcc, cap, None


def final_dcu(seq, rcc, cap):
    prev = seq.cur(DMM + 0x28)
    if rcc & 3 == 0:
        x = cap * 0x10000
        hi = (((x >> 24) - 1) << 8) if x > 0xFF0000 else 0
        v = prev & 0xFFFC1899 | rcc >> 1 | 0x2000 | hi
    else:
        raise NotImplementedError('rcc bank code != 0 not modelled')
    seq.w(DMM + 0x28, v, 'detected', 'prev & 0xfffc1899 | rcc>>1 | 0x2000 | ((cap>>8)-1)<<8')


def dmm_setup(seq):
    w = seq.w
    def rmw(a, clr, st):
        if clr & 0xFFFFFFFF == 0xFFFFFFFF:       # full-mask RMW: value no longer depends on the old contents
            w(a, st, 'constant', f'prev & ~{clr:#x} | {st:#x}')
        else:
            seq.rmw(a, seq.cur(a) & ~clr | st, f'prev & ~{clr:#x} | {st:#x}')
    rmw(DMM + 0x0C, 0xFFFF, 0xF801); rmw(DMM + 0x04, 0xFFFFFFFF, 0x818F808); rmw(0xB01B00B4, 0xFFFF, 0x3FF)
    w(DMM + 0x68, 0x3180, 'constant', '0x3180'); w(DMM + 0x10, 0xF8010000, 'constant', '0xf8010000')
    seq.clear(DMM + 0x00, 4); seq.set(DMM + 0x00, 4)


def run(rec, hw):
    """Full cold-boot (mode 0) DDR3 sequence. Returns dict(writes, prints, param_after, result)."""
    if rec.type & 0xF:
        raise NotImplementedError('only the DDR3 branch (type & 0xf == 0) is modelled')
    F = udiv(rec.clock_mhz, 12) * 12          # 0xb40674c0: clock rounded down to a 12 MHz multiple
    auto_cs = rec.cs == 0 or rec.cs >= 3       # cs byte not 1 or 2 -> try 2 then 1
    cs = 1 if rec.cs == 1 else 2
    bus_auto = rec.bus_sel > 1
    bus_sel = 1 if rec.bus_sel == 1 else 0
    rec = Record(F, 0x800, bus_sel, cs, rec.type, rec.rcc, rec.rdodt, rec.wrodt, rec.drv)
    seq = Sequencer(hw)
    prints = []
    while True:
        rec.cs, rec.bus_sel = cs, bus_sel
        prints.append(f'DRAM init mode0,type{rec.type},{cs}cs,x{16 if bus_sel else 32}bus,rcc0x{rec.rcc:x},'
                      f'wrodt{rec.wrodt},rdodt{rec.rdodt},drv{rec.drv:x},{F}MHz.@180525_R...')
        t, p = attempt(seq, rec, cs, F)
        if hw.trains(cs, bus_sel):
            break
        prints.append('Fail:0x0,0x0,0x0,0x0;')   # DXGSR0 lane reads: hardware values, 0 in this model
        # A retry exists only because training failed, so anything a later pass reads back from this pass
        # (the CMU read-modify-writes) inherits a hardware dependency.
        seq.taint = {a: seq.join(c, 'detected') for a, c in seq.taint.items()}
        if auto_cs and cs == 2:
            cs = 1
            continue
        if bus_auto and bus_sel == 0:
            bus_sel = 1
            if auto_cs and cs == 1:
                cs = 2
            continue
        return dict(writes=seq.out, prints=prints, result='0x1017fa11 (training failed)')
    after_training(seq, rec, cs, t, p)
    rcc, cap, err = capacity_probe(seq, rec, cs, hw)
    if err:
        return dict(writes=seq.out, prints=prints, result=err)
    final_dcu(seq, rcc, cap)
    prints.append(f'Ok:DCU_CFG:0x{seq.cur(DMM + 0x28):x},{cap}MByte Cap.')
    dmm_setup(seq)
    rec.rcc, rec.capacity_mib = rcc, cap
    return dict(writes=seq.out, prints=prints, result='0x0', timings=t, packed=p,
                param_after=dict(clock_mhz=F, capacity_mib=cap, bus_sel=bus_sel, cs=cs, type=rec.type, rcc=rcc,
                                 rdodt=rec.rdodt, wrodt=rec.wrodt, drv=rec.drv))


# Interpretations of the computed quantities (JEDEC DDR3 nominal values the constants correspond to).
TIMING_NOTES = {
    'tRFC': 'tRFC_ns * F/1000 + 1; tRFC_ns 110/160/260/350 by per-rank density <256/<512/<1024/>=1024 MiB',
    'tRP': '15 ns (F<=667), 13.75 ns (668..800), 13.91 ns (>800)', 'tRCD': 'equal to tRP',
    'tRAS': '37.5 ns (F<=533), 36/35/34 ns in higher bands', 'tRC': 'tRP + tRAS',
    'tFAW': '50 ns (F<=533), 45 ns, 40 ns (F/25), 35 ns', 'tRRD': '4 nCK (F<=400), 10 ns, 7.5 ns, 6 ns',
    'tWR': '15 ns (F>=400), else 6 nCK', 'tRTP/tWTR': '4 nCK (F<=533), else 7.5 ns',
    'CL/CWL': 'speed-bin table: 6/5 (<=400), 8/6 (<=533), 10/7 (<668), 11/8 (<801), 13/9',
    'tREFI': '7.8 us', 'tXPDLL': '24 ns, minimum 10 nCK up to 416 MHz', 'tRSTL': '150 ns',
    'PTR0': 'tDLLSRST 80 ns (max 63), tDLLLOCK 5.12 us, tITMSRST 10',
    'PTR1': 'tDINIT0 500 us, tDINIT1 = tRFC + 10 ns (JEDEC tXPR)', 'PTR2': 'tDINIT2 200 us, tDINIT3 1 us',
}
