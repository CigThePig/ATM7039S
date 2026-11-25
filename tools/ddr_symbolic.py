#!/usr/bin/env python3
"""Symbolic evaluation of the stock DRAM routine (0xb40673f4) with z3.

An independent second method next to ddr_emulate.py: instead of Unicorn's CPU,
a small ARM (A32) interpreter written here decodes the loader's instructions
with Capstone and evaluates them over z3 bit-vectors. The DDR clock field of
the parameter block is a free symbol ``clk`` (16 bits); the other record bytes
are concrete values from bootloader.ini (``--symbolic`` can free more of them).
Every conditional branch whose outcome depends on a symbol forks the path
(checked for feasibility with z3), so the result is a partition of the input
domain, each part with the exact expression of every MMIO write as a function
of the inputs. Conditional (non-branch) instructions become ``If`` terms.

Only these functions are *modelled* instead of interpreted, and each model is
validated separately against the firmware (tests/test_ddr_timing.py):

* ``0xb406ae80``  unsigned 32-bit division: r0 = UDiv(r0, r1)
* ``0xb406ad40``  signed 32-bit division:   r0 = SDiv(r0, r1)
  (r1-r3, ip are given fresh "clobbered" symbols; any output that depended
  on them would expose a free ``clobber_*`` symbol)
* ``0xb40670e8`` / ``0xb40670f0``  the MMIO/DRAM store and load accessors
  (records the store; the load is answered by the same oracle rules as
  ddr_emulate.py, re-implemented here)
* ``0xb40693f8`` delay (no effect) and ``0xb4066854`` printf (captured).

The interpreter executes only the instruction classes that occur in the
analysed functions and raises on anything else rather than guessing.
"""
import argparse
import json
from pathlib import Path
import struct

import z3

import ddr_emulate as de

M32 = 0xFFFFFFFF
F_UDIV, F_SDIV = 0xB406AE80, 0xB406AD40
F_STORE, F_LOAD = 0xB40670E8, 0xB40670F0
F_STRH_PATTERN = 0xB4067160
STEP_LIMIT = 400_000
COND = ('eq', 'ne', 'hs', 'lo', 'mi', 'pl', 'vs', 'vc', 'hi', 'ls', 'ge', 'lt', 'gt', 'le', 'al')
FIELDS = dict(clock=(0, 2), capacity=(2, 2), bus_sel=(4, 1), cs=(5, 1), type=(6, 1), rcc=(7, 1),
              rdodt=(8, 1), wrodt=(9, 1), drv=(10, 1))


def bv(v):
    return z3.BitVecVal(v & M32, 32)


def concrete(e):
    e = z3.simplify(e)
    return e.as_long() if z3.is_bv_value(e) else None


def coalesce(bs):
    """Rebuild a little-endian load from stored byte slices: if byte i is Extract(8i+7+k, 8i+k, X) of one
    term X, return the matching slice of X instead of a concatenation (purely cosmetic; equivalent)."""
    x0 = bs[0]
    if z3.is_app_of(x0, z3.Z3_OP_EXTRACT):
        src = x0.arg(0)
        k = x0.params()[1]
        if all(z3.is_app_of(b, z3.Z3_OP_EXTRACT) and b.arg(0).eq(src) and b.params() == [8 * i + 7 + k, 8 * i + k]
               for i, b in enumerate(bs)):
            return z3.simplify(z3.Extract(8 * len(bs) - 1 + k, k, src))
    return z3.Concat(*reversed(bs))


class Unsupported(Exception):
    pass


class State:
    """One symbolic path. Copy-on-fork; z3 terms are immutable so shallow copies suffice."""

    def __init__(self):
        self.r = {}
        self.f = dict(N=z3.BoolVal(False), Z=z3.BoolVal(False), C=z3.BoolVal(False), V=z3.BoolVal(False))
        self.mem = {}            # byte address -> 8-bit z3 term (overlay on the image)
        self.mmio = {}           # MMIO register file
        self.path = []           # z3 Bool constraints
        self.decisions = []
        self.writes, self.reads, self.prints = [], [], []
        self.sctl_state, self.pgsr, self.dcu_writes = 0, 0x7, 0
        self.dram = {}
        self.pc = 0
        self.steps = 0
        self.clobber = 0

    def fork(self):
        s = State.__new__(State)
        s.__dict__ = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in self.__dict__.items()}
        return s


class Machine:
    def __init__(self, loader, scenario='x16-1rank-2Gb', reset_seed=0, symbolic=('clock',), domain=None,
                 record='firmware', prepared=None):
        import capstone
        from capstone import arm
        self.arm = arm
        self.cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        self.cs.detail = True
        self.image = bytes(loader[:de.LOAD_SPAN]).ljust(de.LOAD_SPAN, b'\0')
        self.hw = de.SCENARIOS[scenario]
        self.scenario = scenario
        self.seed = reset_seed & M32
        self.decoded = {}
        if prepared is not None:            # synthetic images (tests): parameter block and globals supplied
            self.param_bytes, self.globals = prepared
        else:
            # Concrete parameter block from the firmware's own ini copy and record selection (steps 1-2 of
            # ddr_emulate.py), so the symbolic run starts from exactly the state the firmware builds.
            em = de.Emulation(loader, scenario=scenario, reset_seed=reset_seed, record=record)
            em.call(de.F_INI_COPY, r0=de.INI_LOAD)
            if record == 'firmware':
                em.setreg('sp', de.STACK_TOP)
                em.uc.emu_start(de.SEL_START, de.SEL_END, count=10_000)
            elif record == 'second':
                em.uc.mem_write(de.PARAM, bytes(em.uc.mem_read(de.PARAM2, 12)))
            self.param_bytes = bytes(em.uc.mem_read(de.PARAM, 12))
            self.globals = bytes(em.uc.mem_read(0xB4070800, 0x80))
        self.symbols = {}
        self.base_state = State()
        for name in symbolic:
            if name not in FIELDS:
                raise ValueError('unknown field ' + name)
            off, size = FIELDS[name]
            sym = z3.BitVec(name, 8 * size)
            self.symbols[name] = sym
            for i in range(size):
                self.base_state.mem[de.PARAM + off + i] = z3.Extract(8 * i + 7, 8 * i, sym)
        for name, sym in self.symbols.items():
            lo, hi = (domain or {}).get(name, (0, (1 << sym.size()) - 1))
            self.base_state.path += [z3.UGE(sym, lo), z3.ULE(sym, hi)]
        self.domain = {n: (domain or {}).get(n, (0, (1 << s.size()) - 1)) for n, s in self.symbols.items()}

    # ---- memory ---------------------------------------------------------
    def byte(self, s, a):
        if a in s.mem:
            return s.mem[a]
        if de.BASE <= a < de.BASE + de.LOAD_SPAN:
            if 0xB4070800 <= a < 0xB4070880:
                return z3.BitVecVal(self.globals[a - 0xB4070800], 8)
            if de.PARAM <= a < de.PARAM + 12:
                return z3.BitVecVal(self.param_bytes[a - de.PARAM], 8)
            return z3.BitVecVal(self.image[a - de.BASE], 8)
        if de.BASE <= a < de.BASE + de.SRAM_SIZE:
            return z3.BitVecVal(0, 8)
        raise Unsupported(f'read of unmodelled address 0x{a:x}')

    def load(self, s, a, n):
        if de.MMIO_BASE <= a < de.MMIO_BASE + de.MMIO_SIZE or a < 0x80000000:
            return self.io_read(s, a, n)
        bs = [self.byte(s, a + i) for i in range(n)]
        e = coalesce(bs) if n > 1 else bs[0]
        return z3.ZeroExt(32 - 8 * n, e) if n < 4 else e

    def store(self, s, a, v, n):
        if de.MMIO_BASE <= a < de.MMIO_BASE + de.MMIO_SIZE or a < 0x80000000:
            return self.io_write(s, a, v, n)
        if not de.BASE <= a < de.BASE + de.SRAM_SIZE:
            raise Unsupported(f'store to unmodelled address 0x{a:x}')
        for i in range(n):
            s.mem[a + i] = z3.Extract(8 * i + 7, 8 * i, z3.simplify(v))   # not simplified: keeps slices coalescable

    # ---- oracle (same rules as ddr_emulate.py, independent code) -------
    def param(self, s, off):
        v = concrete(z3.ZeroExt(24, self.byte(s, de.PARAM + off)))
        if v is None:
            raise Unsupported('oracle needs a concrete parameter byte')
        return v

    def io_read(self, s, a, n):
        if a < 0x80000000:
            hw = self.hw
            wlog = 1 if hw['width'] == 16 else 2
            mod = 1 << (wlog + hw['col_bits']) if s.dcu_writes == 2 else \
                1 << (wlog + hw['col_bits'] + hw['row_bits'] + hw['bank_log2'])
            p = a % mod
            val = sum(s.dram.get(p + i, 0) << (8 * i) for i in range(n))
            s.reads.append((a, val, 'dram'))
            return bv(val)
        a &= ~3
        if a == de.STAT:
            v = s.sctl_state
        elif a == de.MCMD:
            v = s.mmio.get(a, bv(0))
            v = v & bv(0x7FFFFFFF)
        elif a in (de.POWSTAT, de.CMDTSTAT, de.DFISTSTAT0):
            v = 1
        elif a == de.PGSR:
            v = s.pgsr
        elif a == de.ZQ0SR0:
            v = 0x80000000
        elif a in de.DXGSR0:
            v = 0
        else:
            v = s.mmio.get(a, bv(self.seed))
        v = v if isinstance(v, z3.ExprRef) else bv(v)
        s.reads.append((a, v, 'mmio'))
        return v

    def io_write(self, s, a, v, n):
        if a < 0x80000000:
            cv = concrete(v)
            if cv is None:
                raise Unsupported('symbolic DRAM store')
            hw = self.hw
            wlog = 1 if hw['width'] == 16 else 2
            mod = 1 << (wlog + hw['col_bits']) if s.dcu_writes == 2 else \
                1 << (wlog + hw['col_bits'] + hw['row_bits'] + hw['bank_log2'])
            for i in range(n):
                s.dram[(a % mod) + i] = (cv >> (8 * i)) & 0xFF
            return
        if n != 4:
            raise Unsupported('narrow MMIO store')
        v = z3.simplify(v)
        s.mmio[a] = v
        s.writes.append((a, v))
        cv = concrete(v)
        if a == de.SCTL:
            if cv is None:
                raise Unsupported('symbolic SCTL')
            s.sctl_state = {0: 0, 1: 1, 2: 3, 3: 5, 4: 3}.get(cv & 7, s.sctl_state)
        elif a == de.PIR:
            if cv is None:
                raise Unsupported('symbolic PIR')
            if cv & 0x80:
                width = 16 if self.param(s, 4) else 32
                s.pgsr = 0x1F if (self.param(s, 5) <= self.hw['ranks'] and width <= self.hw['width']) else 0x3F
            elif cv & 1:
                s.pgsr = 0xF
            else:
                s.pgsr = 0x7
        elif a == de.DCU_CFG:
            s.dcu_writes += 1

    # ---- operands -------------------------------------------------------
    def rget(self, s, reg, insn):
        name = insn.reg_name(reg)
        if name == 'pc':
            return bv(insn.address + 8)
        return s.r.get(name, bv(0))

    def shift(self, s, val, sh, insn, carry_in):
        a = self.arm
        t, amt = sh.type, sh.value
        if t == a.ARM_SFT_INVALID or (t in (a.ARM_SFT_LSL,) and amt == 0):
            return val, carry_in
        if t in (a.ARM_SFT_LSL_REG, a.ARM_SFT_LSR_REG, a.ARM_SFT_ASR_REG, a.ARM_SFT_ROR_REG):
            amt = self.rget(s, amt, insn) & bv(0xFF)
            t = {a.ARM_SFT_LSL_REG: a.ARM_SFT_LSL, a.ARM_SFT_LSR_REG: a.ARM_SFT_LSR,
                 a.ARM_SFT_ASR_REG: a.ARM_SFT_ASR, a.ARM_SFT_ROR_REG: a.ARM_SFT_ROR}[t]
            if t == a.ARM_SFT_LSL:
                return z3.If(z3.UGE(amt, 32), bv(0), val << amt), None
            if t == a.ARM_SFT_LSR:
                return z3.If(z3.UGE(amt, 32), bv(0), z3.LShR(val, amt)), None
            if t == a.ARM_SFT_ASR:
                return z3.If(z3.UGE(amt, 32), val >> 31, val >> amt), None
            return z3.RotateRight(val, amt), None
        amt = int(amt)
        if t == a.ARM_SFT_LSL:
            return val << amt, z3.Extract(32 - amt, 32 - amt, val) == 1
        if t == a.ARM_SFT_LSR:
            amt = amt or 32
            return (z3.LShR(val, amt) if amt < 32 else bv(0)), z3.Extract(amt - 1, amt - 1, val) == 1
        if t == a.ARM_SFT_ASR:
            amt = amt or 32
            return val >> min(amt, 31), z3.Extract(min(amt, 32) - 1, min(amt, 32) - 1, val) == 1
        if t == a.ARM_SFT_ROR:
            return z3.RotateRight(val, amt), z3.Extract(amt - 1, amt - 1, val) == 1
        raise Unsupported('shift type')

    def operand(self, s, op, insn):
        a = self.arm
        if op.type == a.ARM_OP_IMM:
            return bv(op.imm), None
        if op.type == a.ARM_OP_REG:
            return self.shift(s, self.rget(s, op.reg, insn), op.shift, insn, s.f['C'])
        raise Unsupported('operand type')

    def address(self, s, op, insn):
        m = op.mem
        base = self.rget(s, m.base, insn)
        if m.index:
            idx = self.rget(s, m.index, insn)
            if op.shift.type:
                idx, _ = self.shift(s, idx, op.shift, insn, None)
            off = idx
        else:
            off = bv(abs(m.disp))
        neg = op.subtracted or m.disp < 0
        return base, (base - off if neg else base + off)

    # ---- conditions -----------------------------------------------------
    def cond(self, s, cc):
        N, Z, C, V = (s.f[k] for k in 'NZCV')
        return {'eq': Z, 'ne': z3.Not(Z), 'hs': C, 'lo': z3.Not(C), 'mi': N, 'pl': z3.Not(N),
                'vs': V, 'vc': z3.Not(V), 'hi': z3.And(C, z3.Not(Z)), 'ls': z3.Or(z3.Not(C), Z),
                'ge': N == V, 'lt': N != V, 'gt': z3.And(z3.Not(Z), N == V), 'le': z3.Or(Z, N != V),
                'al': z3.BoolVal(True)}[cc]

    def split(self, mnemonic):
        for base in sorted(('add', 'adc', 'sub', 'rsb', 'and', 'orr', 'eor', 'bic', 'mov', 'mvn', 'lsl',
                            'lsr', 'asr', 'mul', 'mla', 'cmp', 'cmn', 'tst', 'ldrb', 'ldrh', 'ldr', 'strb',
                            'strh', 'str', 'push', 'pop', 'bl', 'bx', 'b'), key=len, reverse=True):
            if mnemonic.startswith(base):
                rest = mnemonic[len(base):]
                setf = rest.startswith('s') and base not in ('cmp', 'cmn', 'tst', 'b', 'bl', 'bx') and \
                    (len(rest) in (1, 3))
                if setf:
                    rest = rest[1:]
                if rest in COND or rest == '':
                    return base, setf, rest or 'al'
        raise Unsupported('mnemonic ' + mnemonic)

    def decode(self, pc):
        if pc not in self.decoded:
            off = pc - de.BASE
            insn = next(self.cs.disasm(self.image[off:off + 4], pc), None)
            if insn is None:
                raise Unsupported(f'undecodable instruction at 0x{pc:x}')
            self.decoded[pc] = insn
        return self.decoded[pc]

    # ---- execution ------------------------------------------------------
    def feasible(self, s, c):
        sol = z3.Solver()
        sol.add(*s.path, c)
        return sol.check() == z3.sat

    def call_model(self, s, target):
        """Return True if target was handled as a model (and set pc to lr)."""
        r = s.r
        if target in (F_UDIV, F_SDIV):
            n, d = r.get('r0', bv(0)), r.get('r1', bv(0))
            if concrete(d) == 0:
                raise Unsupported('division by zero')
            r['r0'] = z3.simplify(z3.UDiv(n, d) if target == F_UDIV else n / d)
        elif target == F_STORE:
            a = concrete(r.get('r1', bv(0)))
            if a is None:
                raise Unsupported('symbolic store address')
            self.store(s, a, r.get('r0', bv(0)), 4)
        elif target == F_LOAD:
            a = concrete(r.get('r0', bv(0)))
            if a is None:
                raise Unsupported('symbolic load address')
            r['r0'] = self.load(s, a, 4)
        elif target == de.F_DELAY:
            pass
        elif target == de.F_PRINTF:
            sp = concrete(r['sp'])
            args = [r.get('r1'), r.get('r2'), r.get('r3')] + [self.load(s, sp + 4 * i, 4) for i in range(10)]
            fa = concrete(r['r0'])
            fmt = bytearray()
            while self.image[fa - de.BASE + len(fmt)]:
                fmt.append(self.image[fa - de.BASE + len(fmt)])
            s.prints.append((fmt.decode('latin-1'), [z3.simplify(x) if x is not None else bv(0) for x in args]))
            r['r0'] = bv(0)
        else:
            return False
        # The accessors only touch r0 (verified from their two instructions). Every other model clobbers
        # all registers the AAPCS lets a callee change; a fresh symbol makes any reliance visible.
        if target not in (F_STORE, F_LOAD):
            for k in ('r1', 'r2', 'r3', 'ip'):
                s.clobber += 1
                r[k] = z3.BitVec(f'clobber_{k}_{s.clobber}', 32)
        s.pc = concrete(r['lr'])
        return True

    def step(self, s):
        """Execute one instruction; returns a list of successor states."""
        a = self.arm
        insn = self.decode(s.pc)
        base, setf, cc = self.split(insn.mnemonic)
        ops = insn.operands
        nxt = insn.address + 4
        c = self.cond(s, cc)
        cval = z3.simplify(c)
        if base in ('b', 'bl', 'bx'):
            if base == 'bx':
                tgt = self.rget(s, ops[0].reg, insn)
                tgt_c = concrete(tgt)
                if tgt_c is None or tgt_c & 1:
                    raise Unsupported('indirect/Thumb bx')
            else:
                tgt_c = ops[0].imm & M32
            outs = []
            for taken, cnd in ((True, c), (False, z3.Not(c))):
                if z3.is_false(z3.simplify(cnd)):
                    continue
                t = s if z3.is_true(z3.simplify(cnd)) else None
                if t is None:
                    if not self.feasible(s, cnd):
                        continue
                    t = s.fork()
                    t.path.append(cnd)
                    t.decisions.append((hex(insn.address), taken))
                if taken:
                    if base == 'bl':
                        t.r['lr'] = bv(nxt)
                        t.pc = tgt_c
                        if not self.call_model(t, tgt_c):
                            pass
                    else:
                        t.pc = tgt_c
                else:
                    t.pc = nxt
                outs.append(t)
                if t is s:
                    break
            return outs
        s.pc = nxt

        def assign(reg, val):
            name = insn.reg_name(reg)
            val = z3.simplify(val)
            if name == 'pc':
                pcv = concrete(z3.If(c, val, bv(nxt)))
                if pcv is None:
                    raise Unsupported('symbolic pc')
                s.pc = pcv
            else:
                s.r[name] = val if z3.is_true(cval) else z3.simplify(z3.If(c, val, s.r.get(name, bv(0))))

        if base in ('push', 'pop'):
            regs = [o.reg for o in ops]
            sp = s.r['sp']
            if base == 'push':
                sp = sp - 4 * len(regs)
                for i, rg in enumerate(regs):
                    self.store_cond(s, concrete(sp) + 4 * i, self.rget(s, rg, insn), 4, c)
                s.r['sp'] = z3.simplify(z3.If(c, sp, s.r['sp']))
            else:
                vals = [self.load(s, concrete(sp) + 4 * i, 4) for i in range(len(regs))]
                s.r['sp'] = z3.simplify(z3.If(c, sp + 4 * len(regs), sp))
                for rg, v in zip(regs, vals):
                    assign(rg, v)
            return [s]
        if base in ('ldr', 'ldrb', 'ldrh', 'str', 'strb', 'strh'):
            n = {'b': 1, 'h': 2}.get(base[3:], 4)
            mem = ops[1]
            b0, ea = self.address(s, mem, insn)
            post = len(ops) > 2
            if post:
                off, _ = self.operand(s, ops[2], insn)
                ea_access = b0
                new_base = b0 - off if ops[2].subtracted else b0 + off
            else:
                ea_access = ea
                new_base = ea
            addr = concrete(ea_access)
            if addr is None:
                raise Unsupported(f'symbolic address at 0x{insn.address:x}')
            if base.startswith('ldr'):
                if z3.is_false(cval):
                    return [s]
                if not z3.is_true(cval) and (de.MMIO_BASE <= addr < de.MMIO_BASE + de.MMIO_SIZE or addr < 0x80000000):
                    raise Unsupported('conditional MMIO load')
                assign(ops[0].reg, self.load(s, addr, n))
            else:
                v = self.rget(s, ops[0].reg, insn)
                self.store_cond(s, addr, v, n, c)
            if insn.writeback or post:
                s.r[insn.reg_name(mem.mem.base)] = z3.simplify(z3.If(c, new_base, b0))
            return [s]
        if base in ('cmp', 'cmn', 'tst'):
            x = self.rget(s, ops[0].reg, insn)
            y, carry = self.operand(s, ops[1], insn)
            if base == 'cmp':
                self.setflags_sub(s, x, y, c)
            elif base == 'cmn':
                self.setflags_add(s, x, y, c)
            else:
                res = x & y
                self.setnz(s, res, c, carry)
            return [s]
        # data processing
        if base in ('mov', 'mvn'):
            y, carry = self.operand(s, ops[1], insn)
            res = y if base == 'mov' else ~y
            assign(ops[0].reg, res)
            if setf:
                self.setnz(s, res, c, carry)
            return [s]
        if base in ('lsl', 'lsr', 'asr'):
            if len(ops) == 2:            # Capstone folds 'lsl rd, rm, #n' into a shifted operand
                res, _ = self.operand(s, ops[1], insn)
                if setf:
                    raise Unsupported('flag-setting shift')
                assign(ops[0].reg, res)
                return [s]
            x = self.rget(s, ops[1].reg, insn)
            amt = ops[2]
            if amt.type == a.ARM_OP_IMM:
                k = amt.imm
                res = {'lsl': lambda: x << k, 'lsr': lambda: z3.LShR(x, k) if k < 32 else bv(0),
                       'asr': lambda: x >> min(k, 31)}[base]()
            else:
                k = self.rget(s, amt.reg, insn) & bv(0xFF)
                res = {'lsl': z3.If(z3.UGE(k, 32), bv(0), x << k),
                       'lsr': z3.If(z3.UGE(k, 32), bv(0), z3.LShR(x, k)),
                       'asr': z3.If(z3.UGE(k, 32), x >> 31, x >> k)}[base]
            if setf:
                raise Unsupported('flag-setting shift')
            assign(ops[0].reg, res)
            return [s]
        if base in ('mul', 'mla'):
            x = self.rget(s, ops[1].reg, insn)
            y = self.rget(s, ops[2].reg, insn)
            res = x * y + (self.rget(s, ops[3].reg, insn) if base == 'mla' else 0)
            if setf:
                raise Unsupported('muls')
            assign(ops[0].reg, res)
            return [s]
        if base in ('add', 'adc', 'sub', 'rsb', 'and', 'orr', 'eor', 'bic'):
            if len(ops) == 2:
                x, (y, carry) = self.rget(s, ops[0].reg, insn), self.operand(s, ops[1], insn)
            else:
                x, (y, carry) = self.rget(s, ops[1].reg, insn), self.operand(s, ops[2], insn)
            cin = z3.If(s.f['C'], bv(1), bv(0))
            res = {'add': lambda: x + y, 'adc': lambda: x + y + cin, 'sub': lambda: x - y,
                   'rsb': lambda: y - x, 'and': lambda: x & y, 'orr': lambda: x | y,
                   'eor': lambda: x ^ y, 'bic': lambda: x & ~y}[base]()
            if setf:
                if base == 'add':
                    self.setflags_add(s, x, y, c)
                elif base == 'sub':
                    self.setflags_sub(s, x, y, c)
                elif base == 'rsb':
                    self.setflags_sub(s, y, x, c)
                elif base in ('and', 'orr', 'eor', 'bic'):
                    self.setnz(s, res, c, carry)
                else:
                    raise Unsupported('adcs')
            assign(ops[0].reg, res)
            return [s]
        raise Unsupported(insn.mnemonic)

    def store_cond(self, s, addr, v, n, c):
        if z3.is_false(z3.simplify(c)):
            return
        if not z3.is_true(z3.simplify(c)):
            if de.MMIO_BASE <= addr < de.MMIO_BASE + de.MMIO_SIZE or addr < 0x80000000:
                raise Unsupported('conditional MMIO store')
            old = self.load(s, addr, n)
            v = z3.If(c, v, old)
        self.store(s, addr, v, n)

    def setnz(self, s, res, c, carry):
        upd = dict(N=z3.Extract(31, 31, res) == 1, Z=res == 0)
        if carry is not None:
            upd['C'] = carry
        for k, v in upd.items():
            s.f[k] = z3.simplify(z3.If(c, v, s.f[k]))

    def setflags_sub(self, s, x, y, c):
        res = x - y
        upd = dict(N=z3.Extract(31, 31, res) == 1, Z=x == y, C=z3.UGE(x, y),
                   V=z3.And(z3.Extract(31, 31, x) != z3.Extract(31, 31, y),
                            z3.Extract(31, 31, res) != z3.Extract(31, 31, x)))
        for k, v in upd.items():
            s.f[k] = z3.simplify(z3.If(c, v, s.f[k]))

    def setflags_add(self, s, x, y, c):
        res = x + y
        upd = dict(N=z3.Extract(31, 31, res) == 1, Z=res == 0,
                   C=z3.ULT(res, x),
                   V=z3.And(z3.Extract(31, 31, x) == z3.Extract(31, 31, y),
                            z3.Extract(31, 31, res) != z3.Extract(31, 31, x)))
        for k, v in upd.items():
            s.f[k] = z3.simplify(z3.If(c, v, s.f[k]))

    def explore(self, entry=de.F_WRAPPER_MODE0, max_paths=256, regs=None):
        s0 = self.base_state.fork()
        s0.r.update(sp=bv(de.STACK_TOP), lr=bv(de.SENTINEL), r0=bv(de.PARAM))
        s0.r.update({k: bv(v) for k, v in (regs or {}).items()})
        s0.pc = entry
        work, done = [s0], []
        while work:
            s = work.pop()
            while s.pc != de.SENTINEL:
                s.steps += 1
                if s.steps > STEP_LIMIT:
                    raise Unsupported('step limit')
                try:
                    succ = self.step(s)
                except Unsupported as e:
                    raise Unsupported(f'{e} at 0x{s.pc:x}: {self.decode(s.pc).mnemonic} {self.decode(s.pc).op_str}')
                if len(succ) > 1:
                    work.extend(succ[1:])
                    if len(done) + len(work) > max_paths:
                        raise Unsupported('path limit')
                s = succ[0]
            done.append(s)
        return done


# ---- reporting ------------------------------------------------------------

def infix(e):
    """Readable infix for the z3 terms this analysis produces."""
    e = z3.simplify(e)
    if z3.is_bv_value(e):
        v = e.as_long()
        return str(v) if v < 4096 else hex(v)
    if z3.is_const(e):
        return str(e)
    k = e.decl().kind()
    ch = [infix(x) for x in e.children()]
    ops = {z3.Z3_OP_BADD: '+', z3.Z3_OP_BMUL: '*', z3.Z3_OP_BOR: '|', z3.Z3_OP_BAND: '&',
           z3.Z3_OP_BXOR: '^', z3.Z3_OP_BSHL: '<<', z3.Z3_OP_BLSHR: '>>', z3.Z3_OP_BUDIV: '/u',
           z3.Z3_OP_BUDIV_I: '/u', z3.Z3_OP_BSDIV: '/s', z3.Z3_OP_BSDIV_I: '/s', z3.Z3_OP_BSUB: '-'}
    if k in ops:
        return '(' + f' {ops[k]} '.join(ch) + ')'
    if k == z3.Z3_OP_CONCAT:
        kids = list(e.children())
        merged = []                      # merge adjacent slices X[a:b], X[b-1:c] -> X[a:c]
        for x in kids:
            if merged and z3.is_app_of(x, z3.Z3_OP_EXTRACT) and z3.is_app_of(merged[-1], z3.Z3_OP_EXTRACT) \
                    and x.arg(0).eq(merged[-1].arg(0)) and x.params()[0] + 1 == merged[-1].params()[1]:
                merged[-1] = z3.Extract(merged[-1].params()[0], x.params()[1], x.arg(0))
            else:
                merged.append(x)
        lead_zero = z3.is_bv_value(merged[0]) and merged[0].as_long() == 0 and len(merged) == 2
        if lead_zero:
            merged = merged[1:]
        if len(merged) == 1:
            m = merged[0]
            if z3.is_app_of(m, z3.Z3_OP_EXTRACT) and m.params()[1] == 0:
                hi = m.params()[0]
                return infix(m.arg(0)) if hi + 1 >= m.arg(0).size() else f'{infix(m.arg(0))}[{hi}:0]'
            return infix(m)
        return 'concat(' + ', '.join(infix(x) for x in merged) + ')'
    if k == z3.Z3_OP_EXTRACT:
        hi, lo = e.params()
        return f'{ch[0]}[{hi}:{lo}]'
    if k == z3.Z3_OP_ZERO_EXT:
        return ch[0]
    if k == z3.Z3_OP_ITE:
        return f'ite({ch[0]}, {ch[1]}, {ch[2]})'
    if k == z3.Z3_OP_ULEQ:
        return f'({ch[0]} <=u {ch[1]})'
    if k == z3.Z3_OP_SLEQ:
        return f'({ch[0]} <=s {ch[1]})'
    if k == z3.Z3_OP_EQ:
        return f'({ch[0]} == {ch[1]})'
    if k == z3.Z3_OP_NOT:
        return f'!{ch[0]}'
    if k in (z3.Z3_OP_AND, z3.Z3_OP_OR):
        return '(' + (' && ' if k == z3.Z3_OP_AND else ' || ').join(ch) + ')'
    if k == z3.Z3_OP_BNOT:
        return '~' + ch[0]
    return e.sexpr()


def intervals(sym, constraints, lo, hi):
    """Maximal integer intervals of `sym` in [lo, hi] satisfying `constraints` (exact, by z3 bisection)."""
    sol = z3.Solver()
    sol.add(*constraints)

    def all_sat(a, b):
        sol.push(); sol.add(z3.UGE(sym, a), z3.ULE(sym, b), z3.Not(z3.And(*constraints) if constraints else True))
        r = sol.check() == z3.unsat
        sol.pop()
        return r

    def any_sat(a, b):
        sol.push(); sol.add(z3.UGE(sym, a), z3.ULE(sym, b))
        r = sol.check() == z3.sat
        sol.pop()
        return r

    out = []

    def rec(a, b):
        if a > b or not any_sat(a, b):
            return
        s2 = z3.Solver(); s2.add(z3.UGE(sym, a), z3.ULE(sym, b), z3.Not(z3.And(*constraints)))
        if s2.check() == z3.unsat:
            if out and out[-1][1] == a - 1:
                out[-1][1] = b
            else:
                out.append([a, b])
            return
        m = (a + b) // 2
        rec(a, m); rec(m + 1, b)

    rec(lo, hi)
    return out


def summarise(machine, paths, evaluate=None):
    out = []
    for s in paths:
        entry = dict(decisions=s.decisions, steps=s.steps)
        if len(machine.symbols) == 1:
            (name, sym), = machine.symbols.items()
            lo, hi = machine.domain[name]
            entry['domain'] = {name: intervals(sym, s.path, lo, hi)}
        else:
            entry['path_condition'] = infix(z3.And(*s.path))
        free = set()
        writes = []
        for a, v in s.writes:
            text = infix(v)
            if 'clobber_' in text:
                free.add(text)
            writes.append(dict(address=hex(a), expression=text))
        entry['mmio_writes'] = writes
        entry['prints'] = [dict(format=f.strip('\n'), args=[infix(x) for x in args[:f.count('%') - 2 * f.count('%%')]])
                           for f, args in s.prints]
        p = [z3.simplify(machine.byte(s, de.PARAM + i)) for i in range(12)]
        entry['param_after'] = [infix(x) for x in p]
        entry['clobber_dependent_writes'] = sorted(free)
        if evaluate:
            m = z3.Solver(); m.add(*s.path, *[machine.symbols[k] == v for k, v in evaluate.items()])
            if m.check() == z3.sat:
                mod = m.model()
                entry['evaluated'] = dict(inputs=evaluate, mmio_writes=[
                    dict(address=hex(a), value=hex(mod.eval(v, model_completion=True).as_long())) for a, v in s.writes])
        out.append(entry)
    return out


def analyse(loader, scenario='x16-1rank-2Gb', symbolic=('clock',), domain=None, evaluate=None, reset_seed=0,
            record='firmware'):
    m = Machine(loader, scenario=scenario, reset_seed=reset_seed, symbolic=symbolic, domain=domain, record=record)
    paths = m.explore()
    return dict(format_version=1, tool='ddr_symbolic.py', code_sha256=de.check_code(loader), scenario=scenario,
                reset_seed=hex(reset_seed), record_selection=record, concrete_param_block=m.param_bytes.hex(),
                symbols={k: list(v) for k, v in m.domain.items()}, paths=summarise(m, paths, evaluate))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('input', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--image-offset', type=lambda x: int(x, 0))
    p.add_argument('--scenario', default='x16-1rank-2Gb', choices=sorted(de.SCENARIOS))
    p.add_argument('--record', default='firmware', choices=('firmware', 'primary', 'second'))
    p.add_argument('--clock-range', default='100:1200', help='domain of the symbolic clock (MHz), lo:hi')
    p.add_argument('--evaluate-clock', type=int, help='also evaluate every path containing this clock')
    a = p.parse_args()
    lo, hi = (int(x) for x in a.clock_range.split(':'))
    data = de.load_region(a.input, a.image_offset)
    r = analyse(data, scenario=a.scenario, domain={'clock': (lo, hi)}, record=a.record,
                evaluate={'clock': a.evaluate_clock} if a.evaluate_clock else None)
    a.output.write_text(json.dumps(r, indent=1) + '\n')


if __name__ == '__main__':
    main()
