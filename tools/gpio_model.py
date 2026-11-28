#!/usr/bin/env python3
"""Deterministic synthetic model of the ATM7039S GPIO/pad window, for offline firmware execution only.

Nothing here describes measured hardware. Every behaviour the model needs and the silicon has not been
shown to have is an explicit, named assumption recorded in ``GpioModel.assumptions()``:

* Register layout (vendor header regs_map-atm7039.h, pinned): bank b in A..E has OUTEN at 0xb01b0000+12b,
  INEN at +4, DAT at +8; PAD_PULLCTL0..2 at 0xb01b0060/64/68. Only the registers listed in ``window`` are
  modelled; any other access inside 0xb01b0000..0xb01b0100 is recorded as *unexpected* and answers 0.
* OUTEN/INEN/PULLCTL reads return the last value written (or the declared initial value).
* DAT read semantics, selectable, all hypotheses:
    ``mixed`` (default): per bit, OUTEN=1 -> output latch; else INEN=1 -> the pad's input level;
                         else -> ``undriven`` (0 by default).
    ``latch``:           every bit returns the latch (inputs are invisible).
* Pad input levels come from ``inputs``: {pin: rule}. Unlisted input pins read ``idle_level``.
  Rules are functions of the model clock and of the waveform written on other pins:
    ('const', v)            constant level
    ('follow', pin)         level of pin's output latch now (ideal loopback)
    ('invert', pin)         complement of pin's latch now
    ('delay', pin, us, idle) latch of pin as it was ``us`` microseconds earlier (idle before history)
    ('script', [levels], idle) level = levels[k] in sample window k (see below), idle outside
    ('follow_except', pin, {k: v}) follow pin, except window k forced to v
    ('prbs', seed)          bit k of a 32-bit Galois LFSR (taps 0xA3000000) in window k
* Sample windows: the model clock (``now``, microseconds) is advanced only by the harness (``advance``).
  A DAT access that happens at least ``window_gap_us`` after the previous DAT access opens a new window;
  window k (0-based) is the k-th such gap. In the firmware's loop each 1 ms delay therefore separates
  windows, so window k covers sample k and the read-modify-writes of iteration k+1. This is a modelling
  convention, not a statement about pad timing.
"""
from dataclasses import dataclass, field

GPIO_BASE = 0xB01B0000
BANKS = 'ABCDE'


def bank_regs(bank):
    b = BANKS.index(bank)
    return dict(outen=GPIO_BASE + 12 * b, inen=GPIO_BASE + 12 * b + 4, dat=GPIO_BASE + 12 * b + 8)


C = bank_regs('C')
PULLCTL = (0xB01B0060, 0xB01B0064, 0xB01B0068)
DEFAULT_WINDOW = {C['outen']: 'GPIO_COUTEN', C['inen']: 'GPIO_CINEN', C['dat']: 'GPIO_CDAT',
                  PULLCTL[0]: 'PAD_PULLCTL0', PULLCTL[1]: 'PAD_PULLCTL1', PULLCTL[2]: 'PAD_PULLCTL2'}


def pin(bank, bit):
    return 32 * BANKS.index(bank) + bit


C10, C11 = pin('C', 10), pin('C', 11)


def lfsr_bits(seed, n=32):
    s, out = seed & 0xFFFFFFFF or 1, []
    for _ in range(n):
        out.append(s & 1)
        s = (s >> 1) ^ (0xA3000000 if s & 1 else 0)
    return out


@dataclass
class GpioModel:
    initial: dict = field(default_factory=dict)          # address -> value (unlisted modelled regs start at 0)
    inputs: dict = field(default_factory=dict)           # pin -> rule tuple
    read_semantics: str = 'mixed'
    undriven: int = 0
    idle_level: int = 0
    window_gap_us: int = 500
    window: dict = field(default_factory=lambda: dict(DEFAULT_WINDOW))
    label: str = ''
    strict: bool = True                                  # False: other window addresses are plain storage


    def __post_init__(self):
        if self.read_semantics not in ('mixed', 'latch'):
            raise ValueError('read_semantics must be mixed or latch')
        self.regs = {a: self.initial.get(a, 0) & 0xFFFFFFFF for a in self.window}
        self.now = 0
        self.history = {}                 # pin -> [(time, level)] of the output latch
        self.log, self.unexpected, self.passthrough, self.other = [], [], [], {}
        self.samples = []                 # (window, pin, level, time) for every DAT read of a listed input pin
        self._last_dat = None
        self.win = -1                     # -1 before the first gap
        for p in self.inputs:
            self._latch_history(p)
        for p in {r[1] for r in self.inputs.values() if r[0] in ('follow', 'invert', 'delay', 'follow_except')}:
            self._latch_history(p)

    # ---- harness interface
    def covers(self, address):
        return GPIO_BASE <= address < GPIO_BASE + 0x100

    def advance(self, us):
        self.now += int(us)

    def read(self, address, pc=None):
        a = address & ~3
        if a not in self.regs:
            rec = dict(op='read', address=f'0x{a:08x}', pc=None if pc is None else f'0x{pc:08x}')
            if self.strict:
                self.unexpected.append(rec)
                return 0
            self.passthrough.append(rec)
            return self.other.get(a, 0)
        if self._is_dat(a):
            self._tick_window()
            v = self._dat_read(a)
        else:
            v = self.regs[a]
        self.log.append(dict(t=self.now, op='read', reg=self.window[a], value=f'0x{v:08x}', window=self.win))
        return v

    def write(self, address, value, pc=None):
        a = address & ~3
        value &= 0xFFFFFFFF
        if a not in self.regs:
            rec = dict(op='write', address=f'0x{a:08x}', value=f'0x{value:08x}', pc=None if pc is None else f'0x{pc:08x}')
            (self.unexpected if self.strict else self.passthrough).append(rec)
            if not self.strict:
                self.other[a] = value
            return
        if self._is_dat(a):
            self._tick_window()
        old = self.regs[a]
        self.regs[a] = value
        self.log.append(dict(t=self.now, op='write', reg=self.window[a], old=f'0x{old:08x}', new=f'0x{value:08x}',
                             changed=f'0x{old ^ value:08x}', window=self.win))
        if self._is_dat(a):
            bank = (a - GPIO_BASE) // 12
            for p, h in self.history.items():
                if p // 32 == bank and (old ^ value) >> (p % 32) & 1:
                    h.append((self.now, value >> (p % 32) & 1))

    # ---- internals
    def _is_dat(self, a):
        return a < GPIO_BASE + 60 and (a - GPIO_BASE) % 12 == 8

    def _tick_window(self):
        if self._last_dat is not None and self.now - self._last_dat >= self.window_gap_us:
            self.win += 1
        self._last_dat = self.now

    def _latch_history(self, p):
        if p not in self.history:
            dat = GPIO_BASE + 12 * (p // 32) + 8
            self.history[p] = [(-10 ** 9, self.regs.get(dat, 0) >> (p % 32) & 1)]

    def latch(self, p, at=None):
        h = self.history.get(p)
        if h is None:
            return self.regs.get(GPIO_BASE + 12 * (p // 32) + 8, 0) >> (p % 32) & 1
        at = self.now if at is None else at
        lvl = h[0][1]
        for t, v in h:
            if t <= at:
                lvl = v
        return lvl

    def level(self, p):
        rule = self.inputs.get(p)
        if rule is None:
            return self.idle_level
        kind, k = rule[0], self.win
        if kind == 'const':
            return rule[1] & 1
        if kind == 'follow':
            return self.latch(rule[1])
        if kind == 'invert':
            return 1 - self.latch(rule[1])
        if kind == 'delay':
            h = self.history[rule[1]]
            first = h[1][0] if len(h) > 1 else None
            if first is None or self.now - rule[2] < first:
                return rule[3]
            return self.latch(rule[1], self.now - rule[2])
        if kind == 'script':
            return rule[1][k] & 1 if 0 <= k < len(rule[1]) else rule[2]
        if kind == 'follow_except':
            return rule[2][k] & 1 if k in rule[2] else self.latch(rule[1])
        if kind == 'prbs':
            bits = lfsr_bits(rule[1])
            return bits[k] if 0 <= k < 32 else self.idle_level
        raise ValueError(f'unknown input rule {kind}')

    def _dat_read(self, a):
        bank = (a - GPIO_BASE) // 12
        latch = self.regs[a]
        if self.read_semantics == 'latch':
            return latch
        out_en, in_en = self.regs.get(a - 8, 0), self.regs.get(a - 4, 0)
        v = 0
        for bit in range(32):
            m = 1 << bit
            if out_en & m:
                v |= latch & m
            elif in_en & m:
                p = 32 * bank + bit
                lv = self.level(p)
                if p in self.inputs:
                    self.samples.append((self.win, p, lv, self.now))
                v |= lv << bit
            else:
                v |= (self.undriven & 1) << bit
        return v

    # ---- reporting
    def state(self):
        return {self.window[a]: f'0x{v:08x}' for a, v in sorted(self.regs.items())}

    def describe(self):
        return dict(label=self.label, strict=self.strict, read_semantics=self.read_semantics, undriven=self.undriven,
                    idle_level=self.idle_level, window_gap_us=self.window_gap_us,
                    initial={self.window[a]: f'0x{self.initial.get(a, 0) & 0xFFFFFFFF:08x}' for a in sorted(self.regs)},
                    inputs={f'GPIO{BANKS[p // 32]}{p % 32}': list(r) if r[0] != 'follow_except'
                            else [r[0], r[1], {str(k): v for k, v in r[2].items()}] for p, r in self.inputs.items()})

    @staticmethod
    def assumptions():
        return [
            'strict mode: any access in 0xb01b0000..0xb01b0100 outside the modelled registers is reported as '
            'unexpected (answers 0); pass-through mode (strict=False) stores such writes and returns them, '
            'logging each access, for whole-path runs where other routines legitimately use the block.',
            'Register addresses and names from the vendor header regs_map-atm7039.h (pinned); semantics not verified.',
            'OUTEN/INEN/PULLCTL reads return the last value written.',
            'DAT read semantics are a selectable hypothesis (mixed: OUTEN -> latch, else INEN -> pad input, else '
            'undriven constant; latch: always the latch).',
            'Pad input levels are synthetic rules of the model clock and of other pins\' latches; pull, mux, '
            'electrical drive and propagation delay are not modelled.',
            'Pin mux is not modelled: GPIO enables are assumed to control the pad whatever MFP_CTL selects.',
            'Sample windows are delimited by gaps of window_gap_us between DAT accesses on the model clock, '
            'which the harness advances (synthetic timer reads or requested delays).',
        ]
