#!/usr/bin/env python3
"""Pre-DRAM reconstruction of the ATM7039S stock early loader (PR #9).

Everything here is offline. Inputs are hash-pinned disk images; nothing is
written to a device, card or register. Results keep four kinds of statement
apart and every record says which one it is:

``decoded``
    read directly from an instruction (Capstone A32) or from a firmware data
    table, with the instruction address;
``static-path``
    a control-flow fact (reachability, call edge, branch condition) from a
    recursive-descent walk of the instructions. Static reachability is not
    proof that an instruction executes on a given boot;
``executed``
    an access performed by the firmware's own instructions inside a bounded
    Unicorn run. Every value the run *reads* from a peripheral comes from an
    explicit synthetic rule that is logged with the read (``SYNTHETIC_RULES``);
``annotated``
    a helper whose address formula is written down by hand (``HELPERS``) and
    checked against executed traces by the tests.

Register names come from the related-SoC ``candidate:`` blocks of
registers/canonical/hardware.json and are labels, not ATM7039S semantics.

Usage::

    python tools/predram_analysis.py evidence OUT.json --image koriki-v1.0=IMG [--image stock-230309=IMG ...]
    python tools/predram_analysis.py graph IMG           # call graph (text)
    python tools/predram_analysis.py trace IMG --boot-code 2 [--scenario loopback]
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

TOOL_VERSION = 1
BASE = 0xB4060000
SRAM_SIZE = 0x40000
LOADER_DISK = 0x200200
LOADER_SIZE = 448 * 512
BLOCK0 = (0xB4060000, 0xB4060200)          # executed by the Boot ROM after its own read
BL_CODE = (0xB4065400, 0xB4093C00)         # PACK member bootloader.bin (loader 0x5400..0x33c00)
ROM_HOLE = (0xB4060400, 0xB4061E00)        # zero in the image; Boot ROM code/services live here at run time
MMIO = (0xB0000000, 0xB0400000)
ROM_SERVICE = 0xB4060400
BOOT_CODE_VA = 0xB4064C00
BOOT_CODE_GETTER = 0xB40664F0
MAIN = 0xB4065400
CALLER = 0xB40665D0
DRAM_COLD = 0xB40690B8
DRAM_CORE = 0xB40673F4
ROM_REENTRY = 0xB40691A4
RESUME_ENTRY = 0xB40664E4
ADFU_EXIT = 0xB4065494
DELAY_US = 0xB40693F8
INI_VA = 0xB4062400
GLOBALS = (0xB4070800, 0xB407087C)
STACK_TOP = 0xB409F000                     # emulator choice; the real value is set by the Boot ROM (unknown)

# Names for functions whose role is established in this or earlier work. Roles are
# interpretations; the function inventory records the evidence for each.
NAMES = {
    0xB4060000: 'block0_entry', 0xB4065400: 'main', 0xB4065D04: 'load_ini', 0xB4065BAC: 'storage_read_dispatch',
    0xB4065B24: 'rom_read_chunked', 0xB40654A4: 'rom_service_read', 0xB4065FF8: 'ini_to_globals',
    0xB40665D0: 'dram_caller', 0xB4069440: 'timer_init', 0xB4069484: 'timer_reset', 0xB40694C4: 'timer_start',
    0xB4069470: 'timer_base', 0xB4069504: 'timer_count', 0xB40693F8: 'delay_us', 0xB4069434: 'delay_ms',
    0xB4066784: 'uart_init', 0xB4066A14: 'uart_setup', 0xB40669D4: 'uart_set_baud', 0xB40667A8: 'putc',
    0xB4066ADC: 'uart_tx', 0xB4066854: 'printf', 0xB40664F0: 'get_boot_code', 0xB40663F8: 'spinand_restore',
    0xB40661B0: 'ini_print', 0xB4066194: 'ini_version_check', 0xB406A608: 'board_mfp_init',
    0xB40699E8: 'pmu_init', 0xB4069890: 'pmu_detect', 0xB4069710: 'pmu_clkout_select', 0xB4069610: 'pmic_read',
    0xB40696C0: 'pmic_write', 0xB40697F4: 'pmic_read_t2', 0xB40697F8: 'pmic_write_t2', 0xB40695AC: 'i2c_select_t1',
    0xB406A788: 'i2c_select', 0xB406A758: 'i2c_base', 0xB406AB7C: 'i2c_probe', 0xB406AC10: 'i2c_read',
    0xB406AC60: 'i2c_write', 0xB406A994: 'i2c_xfer', 0xB4069254: 'adfu_check', 0xB40691A4: 'rom_reentry_adfu',
    0xB40693E0: 'adfu_fail_print', 0xB406622C: 'publish_globals', 0xB40690B8: 'dram_init_cold',
    0xB40690D0: 'dram_init_resume', 0xB40673F4: 'dram_core', 0xB406631C: 'memtest', 0xB4066280: 'record_writeback',
    0xB4066588: 'afi_from_boot_code', 0xB4066500: 'afi_write', 0xB40664E4: 'resume_entry', 0xB4065FC0: 'icache_on',
    0xB4065FDC: 'icache_off', 0xB4065F80: 'sctlr_read', 0xB4065F88: 'sctlr_write', 0xB406A6AC: 'clk_gate_on',
    0xB406A65C: 'clk_gate', 0xB406A6C8: 'reset_ctl', 0xB406A718: 'reset_assert', 0xB406A720: 'reset_deassert',
    0xB406A728: 'reset_pulse', 0xB406ACE0: 'gpio_out', 0xB406AF4C: 'memset', 0xB406AF64: 'memcpy',
    0xB406AF84: 'strcmp', 0xB4065D8C: 'load_app', 0xB4065BF0: 'load_uboot', 0xB4065F70: 'pre_app_clocks',
    0xB4069180: 'ddr_size_bytes', 0xB4069524: 'pmic_spi_read', 0xB406956C: 'pmic_spi_write',
    0xB4069850: 'pmic_t1_version', 0xB40695B0: 'pmic_t1_read', 0xB4069670: 'pmic_t1_write',
}

# Hand-written formulas for helpers whose target address is computed from arguments.
# Each is checked against executed traces (tests/test_predram.py).
HELPERS = {
    0xB4069468: dict(kind='write32', addr='r1', value='r0'),
    0xB406951C: dict(kind='read32', addr='r0'),
    0xB4069514: dict(kind='write32', addr='r1', value='r0'),
    0xB4069194: dict(kind='write32', addr='r1', value='r0'),
    0xB406919C: dict(kind='read32', addr='r0'),
    0xB40669C4: dict(kind='write32', addr='r1', value='r0'),
    0xB40669CC: dict(kind='read32', addr='r0'),
    0xB406A748: dict(kind='write32', addr='r1', value='r0'),
    0xB406A750: dict(kind='read32', addr='r0'),
    0xB406A774: dict(kind='write32', addr='r0', value='r1'),
    0xB406A784: dict(kind='read32', addr='r0'),
    0xB406A648: dict(kind='rmw32', addr='r0', clear='r1', set='r2'),
    0xB4069470: dict(kind='address', formula='0xb0168008 + 12*r0 (timer r0 control word)'),
    0xB406A65C: dict(kind='bit-rmw', formula='CMU 0xb01600a0 + 4*(r0>>5), bit r0&31: set if r1 != 0 else clear'),
    0xB406A6AC: dict(kind='bit-rmw', formula='CMU 0xb01600a0 + 4*(r0>>5), set bit r0&31 (clock gate on)'),
    0xB406A6C8: dict(kind='bit-rmw', formula='CMU 0xb01600a8 + 4*(r0>>5), bit r0&31: clear if r1 != 0 else set'),
    0xB406A718: dict(kind='bit-rmw', formula='CMU 0xb01600a8 + 4*(r0>>5), clear bit r0&31'),
    0xB406A720: dict(kind='bit-rmw', formula='CMU 0xb01600a8 + 4*(r0>>5), set bit r0&31'),
    0xB406A728: dict(kind='bit-rmw', formula='clear bit then delay_us(1) then set bit in CMU 0xb01600a8 + 4*(r0>>5)'),
    0xB406ACE0: dict(kind='bit-rmw', formula='GPIO bank b=r0>>5, bit r0&31: 0xb01b0004+12b clear, 0xb01b0000+12b set, '
                                             '0xb01b0008+12b := r1'),
    0xB406A758: dict(kind='address', formula='((word 0xb406ba10) + 0x2c05c) << 14 = 0xb0170000 + 0x4000*bus'),
}


def helper_address(va, r0, r1=None):
    """Resolve a bit-indexed helper call to (address, clear_mask, set_mask) or a list of them."""
    if r0 is None:
        return None
    bit, word = r0 & 31, r0 >> 5
    if va in (0xB406A6AC,) or (va == 0xB406A65C and r1):
        return [(0xB01600A0 + 4 * word, 1 << bit, 1 << bit)]
    if va == 0xB406A65C:
        return [(0xB01600A0 + 4 * word, 1 << bit, 0)]
    if va == 0xB406A718 or (va == 0xB406A6C8 and r1):
        return [(0xB01600A8 + 4 * word, 1 << bit, 0)]
    if va in (0xB406A720, 0xB406A6C8):
        return [(0xB01600A8 + 4 * word, 1 << bit, 1 << bit)]
    if va == 0xB406A728:
        a = 0xB01600A8 + 4 * word
        return [(a, 1 << bit, 0), (a, 1 << bit, 1 << bit)]
    if va == 0xB406ACE0:
        b = 12 * word
        rows = [(0xB01B0004 + b, 1 << bit, 0), (0xB01B0000 + b, 1 << bit, 1 << bit)]
        rows.append((0xB01B0008 + b, 1 << bit, None if r1 is None else (r1 << bit) & 0xFFFFFFFF))
        return rows
    return None


def sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()


def h32(v):
    return None if v is None else f'0x{v & 0xffffffff:08x}'


# --------------------------------------------------------------------------- inputs

def manifest():
    return json.loads((ROOT / 'evidence/firmware/acquisitions.json').read_text(encoding='utf-8'))


def expected_for(path):
    name = Path(path).name
    for e in manifest():
        if e.get('expanded_filename') == name:
            return e
    return None


def file_sha256(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load_image(path, verify=True):
    """Return (loader_bytes, identity). With verify, the whole image must match the manifest."""
    ident = dict(file=Path(path).name)
    e = expected_for(path)
    if e:
        ident.update(source=e['source'], archive=e['filename'], expected_sha256=e['expanded_sha256'],
                     expected_size=e['expanded_size'])
    if verify:
        if not e:
            raise ValueError(f'{path}: not a manifest-listed expanded image')
        actual = file_sha256(path)
        if actual != e['expanded_sha256']:
            raise ValueError(f'{path}: SHA-256 {actual} differs from manifest')
        ident['actual_sha256'] = actual
        ident['verified'] = True
    with open(path, 'rb') as f:
        f.seek(LOADER_DISK)
        loader = f.read(LOADER_SIZE)
    ident.update(loader_disk_offset=f'0x{LOADER_DISK:x}', loader_size=LOADER_SIZE, loader_sha256=sha(loader),
                 block0_sha256=sha(loader[:0x200]), bootloader_code_sha256=sha(loader[0x5400:0x33C00]))
    return loader, ident


class Code:
    def __init__(self, loader):
        self.data = bytes(loader)
        from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
        self.md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        self.md.detail = True
        self._cache = {}

    def inside(self, va):
        return BLOCK0[0] <= va < BLOCK0[1] or BL_CODE[0] <= va < BL_CODE[1]

    def word(self, va):
        return struct.unpack_from('<I', self.data, va - BASE)[0]

    def bytes(self, a, b):
        return self.data[a - BASE:b - BASE]

    def insn(self, va):
        if va not in self._cache:
            o = va - BASE
            got = list(self.md.disasm(self.data[o:o + 4], va, 1))
            self._cache[va] = got[0] if got else None
        return self._cache[va]

    def cstr(self, va, limit=200):
        if not (BASE <= va < BASE + len(self.data)):
            return None
        o = va - BASE
        e = self.data.find(b'\0', o, o + limit)
        if e <= o:
            return None
        s = self.data[o:e]
        return s.decode() if all(32 <= c < 127 or c in (9, 10) for c in s) else None


# --------------------------------------------------------------------------- static analysis

REGN = {f'r{i}': i for i in range(13)}
REGN.update(sb=9, sl=10, fp=11, ip=12, sp=13, lr=14, pc=15)
CONDS = ('eq', 'ne', 'cs', 'hs', 'cc', 'lo', 'mi', 'pl', 'vs', 'vc', 'hi', 'ls', 'ge', 'lt', 'gt', 'le')


def split_cond(mnemonic):
    for c in CONDS:
        if mnemonic.endswith(c) and len(mnemonic) > len(c) and mnemonic[:-len(c)] in (
                'b', 'bl', 'bx', 'blx', 'mov', 'mvn', 'ldr', 'str', 'pop', 'add', 'sub', 'orr', 'bic', 'and',
                'cmp', 'cmn', 'tst', 'ldrb', 'ldrh', 'strb', 'strh', 'ldm', 'eor', 'rsb', 'lsl', 'lsr', 'asr',
                'mul', 'mla', 'orrs', 'ands', 'subs', 'adds', 'mvns', 'movs', 'ldrsb', 'ldrsh', 'teq', 'push'):
            return mnemonic[:-len(c)], c
    return mnemonic, None


def imm_target(insn):
    op = insn.op_str
    return int(op[1:], 16) if op.startswith('#') else None


def is_return(insn):
    base, _ = split_cond(insn.mnemonic)
    if base == 'bx' and insn.op_str == 'lr':
        return True
    if base in ('pop', 'ldm') and 'pc' in insn.op_str:
        return True
    return base == 'mov' and insn.op_str.startswith('pc,')


class Tracker:
    """Straight-line constant propagation for one basic block (reset at block starts and after calls)."""

    def __init__(self, code):
        self.code, self.r = code, {}

    def get(self, name):
        return self.r.get(REGN.get(name))

    def clobber_call(self):
        for k in (0, 1, 2, 3, 12, 14):
            self.r.pop(k, None)

    def step(self, i):
        """Update register constants after instruction i; returns nothing."""
        from capstone.arm import ARM_OP_REG, ARM_OP_IMM, ARM_OP_MEM
        base, cond = split_cond(i.mnemonic)
        ops = i.operands
        written = [REGN.get(i.reg_name(r)) for r in i.regs_access()[1]]
        if base in ('bl', 'blx'):
            self.clobber_call()
            return
        val = None
        if cond is None and ops and ops[0].type == ARM_OP_REG:
            dst = REGN.get(i.reg_name(ops[0].reg))
            src = ops[1:]
            try:
                if base in ('mov', 'movw') and len(src) == 1:
                    s = src[0]
                    val = s.imm & 0xFFFFFFFF if s.type == ARM_OP_IMM else self.r.get(REGN.get(i.reg_name(s.reg))) \
                        if s.type == ARM_OP_REG and not s.shift.type else None
                elif base == 'mvn' and len(src) == 1 and src[0].type == ARM_OP_IMM:
                    val = ~src[0].imm & 0xFFFFFFFF
                elif base == 'movt' and dst in self.r:
                    val = (self.r[dst] & 0xFFFF) | ((src[0].imm & 0xFFFF) << 16)
                elif base == 'ldr' and len(src) == 1 and src[0].type == ARM_OP_MEM and \
                        i.reg_name(src[0].mem.base) == 'pc' and not src[0].mem.index:
                    val = self.code.word(i.address + 8 + src[0].mem.disp)
                elif base in ('add', 'sub', 'orr', 'bic', 'and', 'eor', 'lsl', 'lsr') and len(src) == 2 and \
                        src[0].type == ARM_OP_REG and src[1].type == ARM_OP_IMM:
                    a = self.r.get(REGN.get(i.reg_name(src[0].reg)))
                    b = src[1].imm & 0xFFFFFFFF
                    if a is not None:
                        val = {'add': a + b, 'sub': a - b, 'orr': a | b, 'bic': a & ~b, 'and': a & b, 'eor': a ^ b,
                               'lsl': a << b, 'lsr': a >> b}[base] & 0xFFFFFFFF
                elif base in ('add', 'sub', 'orr') and len(src) == 2 and src[0].type == ARM_OP_REG and \
                        src[1].type == ARM_OP_REG and not src[1].shift.type:
                    a = self.r.get(REGN.get(i.reg_name(src[0].reg)))
                    b = self.r.get(REGN.get(i.reg_name(src[1].reg)))
                    if a is not None and b is not None:
                        val = {'add': a + b, 'sub': a - b, 'orr': a | b}[base] & 0xFFFFFFFF
            except (AttributeError, IndexError):
                val = None
            for w in written:
                if w is not None and w != dst:
                    self.r.pop(w, None)
            if dst is not None:
                if val is None:
                    self.r.pop(dst, None)
                else:
                    self.r[dst] = val
            return
        for w in written:
            if w is not None:
                self.r.pop(w, None)

    def mem_address(self, i):
        """Effective address of a load/store when its base is a known constant (pc-relative excluded)."""
        from capstone.arm import ARM_OP_MEM
        for o in i.operands:
            if o.type == ARM_OP_MEM:
                bn = i.reg_name(o.mem.base)
                if bn == 'pc' or o.mem.index:
                    return None, bn
                b = self.r.get(REGN.get(bn))
                post = len(i.operands) > 2 or '], #' in i.op_str   # post-indexed: address is the base
                if b is None:
                    return None, bn
                return ((b if post else b + o.mem.disp) & 0xFFFFFFFF), bn
        return None, None


def access_width(base):
    if base.endswith('b') or base in ('ldrsb', 'ldrb', 'strb'):
        return 1
    if base.endswith('h') or base in ('ldrsh',):
        return 2
    if base.endswith('d'):
        return 8
    return 4


def region_of(a):
    if a is None:
        return 'unresolved'
    if MMIO[0] <= a < MMIO[1]:
        return 'mmio'
    if ROM_HOLE[0] <= a < ROM_HOLE[1]:
        return 'sram-rom-hole'
    if BASE <= a < BASE + SRAM_SIZE:
        return 'sram'
    if a >= 0xFFFF0000:
        return 'rom'
    if a < 0x80000000:
        return 'dram'
    return 'other'


def explore(code, root, known_entries):
    """Recursive descent over one function. Returns its record (blocks, calls, accesses, branches)."""
    from capstone.arm import ARM_OP_MEM
    todo, seen, starts = [root], set(), {root}
    calls, branches, accesses, literals, sysops, notes = [], [], [], set(), [], []
    jt_targets = set()
    while todo:
        va = todo.pop()
        if va in seen:
            continue
        tr = Tracker(code)
        while True:
            if va in seen and va != todo and va in starts and tr.r:
                break
            if va in seen:
                break
            if not code.inside(va):
                notes.append(f'flow leaves analysed code at 0x{va:x}')
                break
            i = code.insn(va)
            if i is None:
                notes.append(f'undecodable word at 0x{va:x}')
                break
            seen.add(va)
            base, cond = split_cond(i.mnemonic)
            # literal pool use
            for o in i.operands:
                if o.type == ARM_OP_MEM and i.reg_name(o.mem.base) == 'pc' and not o.mem.index:
                    literals.add(i.address + 8 + o.mem.disp)
            if base in ('mcr', 'mrc', 'msr', 'mrs', 'cps', 'cpsid', 'cpsie', 'svc', 'wfi', 'wfe', 'dsb', 'isb', 'dmb'):
                sysops.append(dict(at=h32(va), insn=f'{i.mnemonic} {i.op_str}', meaning=sysop_meaning(i),
                                   register_value=h32(tr.get(i.op_str.split(', ')[2])) if base == 'mcr' else None))
            # memory accesses with a constant base
            if base in ('ldr', 'str', 'ldrb', 'strb', 'ldrh', 'strh', 'ldrsb', 'ldrsh', 'ldrd', 'strd') and \
                    not ('[pc' in i.op_str):
                addr, bn = tr.mem_address(i)
                kind = 'read' if base.startswith('ldr') else 'write'
                rec = dict(at=h32(va), insn=f'{i.mnemonic} {i.op_str}', access=kind, width=access_width(base),
                           address=h32(addr), region=region_of(addr), conditional=cond is not None)
                if kind == 'write':
                    vreg = i.reg_name(i.operands[0].reg)
                    rec['value'] = h32(tr.get(vreg))
                if addr is None:
                    rec['expression'] = i.op_str.split(', ', 1)[1] if ', ' in i.op_str else i.op_str
                    rec['base_register'] = bn
                if bn not in ('sp',) or addr is not None:
                    accesses.append(rec)
            if base in ('b', 'bl', 'blx', 'bx'):
                t = imm_target(i)
                if base in ('bl', 'blx'):
                    if t is None:
                        tv = tr.get(i.op_str)
                        calls.append(dict(site=h32(va), target=h32(tv), indirect=True, resolved=tv is not None,
                                          register=i.op_str, conditional=cond is not None,
                                          args=[h32(tr.r.get(k)) for k in range(4)]))
                    else:
                        calls.append(dict(site=h32(va), target=h32(t), indirect=False, conditional=cond is not None,
                                          args=[h32(tr.r.get(k)) for k in range(4)], r9=h32(tr.r.get(9))))
                    tr.step(i)
                    va += 4
                    continue
                if base == 'bx':
                    if i.op_str == 'lr':
                        if cond is None:
                            break
                        va += 4
                        continue
                    tv = tr.get(i.op_str)
                    calls.append(dict(site=h32(va), target=h32(tv), indirect=True, resolved=tv is not None,
                                      register=i.op_str, tail=True, conditional=cond is not None, args=[]))
                    if cond is None:
                        break
                    va += 4
                    continue
                # b / bcond
                if t == va:
                    branches.append(dict(at=h32(va), kind='self-loop (hang)', condition=cond))
                    break
                tail = t in known_entries and t != root
                if cond is not None:
                    branches.append(dict(at=h32(va), condition=cond, taken=h32(t), fallthrough=h32(va + 4),
                                     compare=prev_compare(code, va)))
                if tail:
                    calls.append(dict(site=h32(va), target=h32(t), indirect=False, tail=True,
                                      conditional=cond is not None, args=[h32(tr.r.get(k)) for k in range(4)]))
                else:
                    if t not in starts:
                        starts.add(t)
                        todo.append(t)
                if cond is None:
                    break
                tr.step(i)
                va += 4
                continue
            # jump table: ldr<cond> pc, [pc, rN, lsl #2]
            if base == 'ldr' and i.op_str.startswith('pc, [pc, '):
                n = jump_table_bound(code, va)
                if n is None:
                    notes.append(f'unresolved computed jump at 0x{va:x}')
                    break
                for k in range(n):
                    t = code.word(va + 8 + 4 * k)
                    jt_targets.add(t)
                    literals.add(va + 8 + 4 * k)
                    if t not in starts:
                        starts.add(t)
                        todo.append(t)
                branches.append(dict(at=h32(va), kind='jump table', condition=cond, entries=n,
                                     targets=[h32(code.word(va + 8 + 4 * k)) for k in range(n)]))
                va += 4
                continue
            if is_return(i):
                if cond is None:
                    break
                tr.step(i)
                va += 4
                continue
            if base in ('ldr',) and i.op_str.startswith('pc,'):
                notes.append(f'unresolved computed jump at 0x{va:x}')
                break
            tr.step(i)
            va += 4
    insns = sorted(seen)
    end = (max(insns) + 4) if insns else root
    pool = sorted(a for a in literals if a >= end)
    extent_end = max([end] + [a + 4 for a in pool if a < end + 0x400])
    return dict(entry=root, instructions=len(insns), code_end=end, extent_end=extent_end, calls=calls,
                branches=branches, accesses=accesses, literal_words=len(pool), sysops=sysops, notes=notes,
                code_sha256=sha(b''.join(code.bytes(a, a + 4) for a in insns)),
                extent_sha256=sha(code.bytes(root, extent_end)), noncontiguous=len(insns) != (end - root) // 4)


def prev_compare(code, va, back=6):
    """The flag-setting instruction a conditional branch depends on (nearest before it, same block)."""
    for k in range(1, back + 1):
        i = code.insn(va - 4 * k)
        if i is None:
            return None
        b, _ = split_cond(i.mnemonic)
        if b in ('cmp', 'cmn', 'tst', 'teq') or b.endswith('s') and b in ('subs', 'ands', 'orrs', 'adds', 'movs'):
            return f'0x{i.address:x}: {i.mnemonic} {i.op_str}'
        if b in ('b', 'bl', 'bx', 'blx', 'pop'):
            return None
    return None


def jump_table_bound(code, va):
    for k in range(1, 6):
        i = code.insn(va - 4 * k)
        if i and i.mnemonic == 'cmp' and '#' in i.op_str:
            return int(i.op_str.split('#')[1], 0) + 1
    return None


def sysop_meaning(i):
    s = i.op_str
    if 'p15' in s and 'c1, c0, #0' in s:
        return 'SCTLR ' + ('read' if i.mnemonic.startswith('mrc') else 'write')
    if 'p15' in s and 'c12, c0, #0' in s:
        return 'VBAR write' if i.mnemonic.startswith('mcr') else 'VBAR read'
    return 'other system instruction'


def call_graph(code, roots=(MAIN,), stop_at=(DRAM_CORE,)):
    """Fixed-point recursive descent from roots. Functions in stop_at are recorded but not entered."""
    known = set(NAMES) | set(roots)
    funcs = {}
    changed = True
    while changed:
        changed = False
        todo = list(roots)
        visited = set()
        while todo:
            f = todo.pop()
            if f in visited:
                continue
            visited.add(f)
            if f in stop_at or not code.inside(f) or (BLOCK0[0] <= f < BLOCK0[1] and f not in roots):
                funcs.setdefault(f, None)
                continue
            rec = explore(code, f, known)
            if funcs.get(f) is None or funcs[f]['instructions'] != rec['instructions']:
                funcs[f] = rec
            for c in rec['calls']:
                t = int(c['target'], 16) if c['target'] else None
                if t is None:
                    continue
                if t not in known:
                    known.add(t)
                    changed = True
                todo.append(t)
    return funcs


# Literal-pool inline data that the walker should never treat as code is excluded by
# construction: only control flow is followed. Below: the targets that are not code
# in the image (provided by the Boot ROM at run time) are external.
EXTERNAL = {ROM_SERVICE: 'Boot ROM service (selector in r9; SRAM 0xb4060400, absent from the image)',
            0xFFFF0140: 'Boot ROM ADFU entry (literal)', 0x1000: 'app.bin entry (DRAM)',
            0xB4060000: 'SRAM 0xb4060000 after the ROM copy (rom_reentry_adfu jumps there)',
            0xB4060758: 'Boot ROM code in the SRAM hole (absent from the image)'}


PRE_DRAM_SITES = {MAIN: (MAIN, 0xB4065428), CALLER: (CALLER, 0xB4066718)}


def predram_subgraph(funcs):
    """Functions reachable before the DRAM boundary: main's calls up to the dram_caller call (0xb4065424) and
    dram_caller's calls before 0xb4066718 (the call of dram_init_cold), closed transitively. Static: it says what
    can run, not what runs on a given boot."""
    edges, reach, todo = [], set(), [MAIN]
    while todo:
        f = todo.pop()
        if f in reach:
            continue
        reach.add(f)
        r = funcs.get(f)
        if not r:
            continue
        lo, hi = PRE_DRAM_SITES.get(f, (0, 0xFFFFFFFF))
        for c in r['calls']:
            if not c['target']:
                continue
            site, t = int(c['site'], 16), int(c['target'], 16)
            if not lo <= site < hi and f in PRE_DRAM_SITES:
                if f == CALLER and site == 0xB4066718:
                    edges.append(dict(caller=h32(f), site=c['site'], callee=h32(t), kind='boundary (DRAM init)'))
                continue
            kind = 'tail' if c.get('tail') else ('indirect' if c.get('indirect') else 'call')
            edges.append(dict(caller=h32(f), caller_name=NAMES.get(f), site=c['site'], callee=h32(t),
                              callee_name=NAMES.get(t) or EXTERNAL.get(t), kind=kind,
                              conditional=c.get('conditional', False)))
            if t in (ROM_REENTRY,) or (BLOCK0[0] <= t < BLOCK0[1]) or not (BL_CODE[0] <= t < BL_CODE[1]):
                if t == ROM_REENTRY:
                    todo.append(t)
                continue
            todo.append(t)
    return dict(functions=sorted(h32(f) for f in reach), edges=edges,
                exits=[dict(to='0xb40690b8 dram_init_cold', how='normal path (dram_caller 0xb4066718)'),
                       dict(to='0xb40664e4 resume_entry', how='dram_caller returns 2 (resume flag and vector set)'),
                       dict(to='0xb4065494 -> 0xb40693e0 -> 0xb40691a4', how='dram_caller returns -1 (ini version '
                            'is not "1.1")'),
                       dict(to='0xb40691a4 rom_reentry_adfu', how='adfu_check: PMIC status bit 1, or the code != 0 '
                            'GPIO loopback reads 0x55aa55aa'),
                       dict(to='self-loop hangs', how='pmu_detect type-2 identity check fails (0xb40699c4); pmu_init '
                            'version 0 (0xb4069f2c) or < 0 (0xb406a194)')])


def dram_stage_comparison(loader):
    """Re-run the PR #6 DRAM caller (dram_complete.run_caller, reference scenario only) with boot codes 0 and 2 and
    diff the complete MMIO write and read sequences. All PUBL/uPCTL/PMIC responses there are synthetic."""
    import dram_complete as D
    runs = {}
    for bc in (0, 2):
        out, h = D.run_caller(loader, D.Pmic(), D.TRAINING_SCENARIOS[0], boot_code=bc)
        runs[bc] = dict(out=out, writes=[(w['address'], w['value']) for w in h.writes],
                        reads=[(r['address'], r['value']) for r in h.reads])
    res = {}
    for kind in ('writes', 'reads'):
        a, b = runs[0][kind], runs[2][kind]
        ops = [op for op in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes() if op[0] != 'equal']
        res[kind] = dict(code0=len(a), code2=len(b), differences=[dict(
            change=t, code0_range=[i1, i2], code2_range=[j1, j2],
            code2_addresses=sorted({x[0] for x in b[j1:j2]}), code0_addresses=sorted({x[0] for x in a[i1:i2]}))
            for t, i1, i2, j1, j2 in ops])
    only_gpio = all(int(x, 16) >> 12 == 0xB01B0 for k in res for d in res[k]['differences']
                    for x in d['code2_addresses'] + d['code0_addresses'])
    return dict(method='executed (dram_complete.run_caller, scenario "reference", synthetic PUBL/uPCTL/PMIC)',
                **res, differences_confined_to_gpio_block=only_gpio,
                functions_identical=runs[0]['out']['functions'] == runs[2]['out']['functions'],
                return_values=[runs[0]['out']['caller']['return_value'], runs[2]['out']['caller']['return_value']],
                afi_boot_dev=[runs[0]['out']['caller']['afi']['boot_dev'], runs[2]['out']['caller']['afi']['boot_dev']],
                note='The other PR #6 training/failure scenarios were not re-run for code 2 (out of scope). The harness '
                     'answers GPIO reads with the last value written, i.e. it models "no loopback".')


def find(code, start, end, mnemonic, operand_substring=None, nth=0):
    """nth instruction in [start, end) whose mnemonic matches and whose operands contain the substring."""
    k = 0
    for va in range(start, end, 4):
        i = code.insn(va)
        if i and i.mnemonic == mnemonic and (operand_substring is None or operand_substring in i.op_str):
            if k == nth:
                return i
            k += 1
    return None


def fact(i, meaning, value=None, code=None):
    if i is None:
        return dict(found=False, meaning=meaning)
    out = dict(found=True, at=h32(i.address), insn=f'{i.mnemonic} {i.op_str}', meaning=meaning)
    if value is not None:
        out['value'] = value
    if code is not None and '[pc' in i.op_str:
        out['literal'] = h32(code.word(i.address + 8 + i.operands[-1].mem.disp))
    return out


def structure_facts(code):
    """Decoded control-flow and constant facts for the routines whose behaviour differs or matters before DRAM.
    Each fact names the instruction it was read from; 'found': False means the pattern is absent."""
    A = 0xB4069254
    adfu = dict(
        function=h32(A), end=h32(0xB40693C0),
        pmic_status_register=fact(find(code, A, A + 0x10, 'ldrh', '[r3, #4]'),
                                  'register number = halfword at 0xb406b9d4 (table 0xb406b9d0 + 4)',
                                  value=h32(struct.unpack_from('<H', code.bytes(0xB406B9D4, 0xB406B9D6))[0])),
        status_bit_test=fact(find(code, A, A + 0x40, 'ands', '#2'), 'bit 1 set -> write back with bits 0-1 cleared, '
                                                                    'then ADFU'),
        status_clear=fact(find(code, A, A + 0x50, 'bic', '#3'), 'value written back to the status register'),
        enable_argument=fact(find(code, A, A + 0x50, 'cmp', 'r7, #0'), 'r0 at entry = ini word +0x14; 0 -> return'),
        boot_code_test=fact(find(code, A, A + 0x60, 'bl', '#0xb40664f0'), 'get_boot_code(); 0 -> return (SD0 path '
                                                                          'skips the GPIO test)'),
        pattern=fact(find(code, A, A + 0x80, 'ldr', 'r6, [pc'), 'drive pattern (shifted out LSB first)', code=code),
        drive_bit=fact(find(code, A, A + 0x140, 'orr', 'lsl #11'), 'GPIO C data bit 11 := next pattern bit'),
        sample_bit=fact(find(code, A, A + 0x140, 'tst', '#0x400'), 'GPIO C data bit 10 sampled after the delay'),
        per_bit_delay=fact(find(code, A, A + 0x140, 'bl', '#0xb4069434'), 'delay_ms(1) per bit'),
        loop_bound=fact(find(code, A, A + 0x140, 'cmp', 'r4, #0x20'), '32 iterations'),
        restore=[fact(find(code, A, A + 0x170, 'bl', '#0xb4069194', nth=k), m) for k, m in
                 ((7, 'GPIO C input-enable restored'), (8, 'GPIO C output-enable restored'))],
        success_compare=fact(find(code, A + 0x140, A + 0x160, 'cmp', 'r5, ip'),
                             'sampled word == pattern -> print "Prepare to entry ADFU mode", tail-call 0xb40691a4'),
        not_restored=['0xb01b0064 bit 17 (cleared at 0xb40692c0)', '0xb01b0020 bit 11 (last pattern bit, 0)'],
        gpio_setup=[fact(find(code, A, A + 0xE0, 'bic', '#0x20000'), '0xb01b0064 &= ~bit 17'),
                    fact(find(code, A, A + 0xE0, 'bic', '#0x400'), '0xb01b0018 &= ~bit 10 (C10 output off)'),
                    fact(find(code, A, A + 0xE0, 'orr', '#0x400'), '0xb01b001c |= bit 10 (C10 input on)'),
                    fact(find(code, A, A + 0xE0, 'bic', '#0x800'), '0xb01b001c &= ~bit 11 (C11 input off)'),
                    fact(find(code, A, A + 0xE0, 'orr', '#0x800'), '0xb01b0018 |= bit 11 (C11 output on)')],
        names='C10/C11 follow the related-SoC GPIO bank layout (A at 0x00, B 0x0c, C 0x18: OUTEN, INEN, DAT); '
              'the physical pins are not established.')
    T = 0xB40693F8
    timer = dict(
        base=fact(find(code, 0xB4069470, 0xB4069484, 'add', '#0xb0000008'), 'timer n control word = 0xb0168008 + 12n'),
        gate=fact(find(code, 0xB4069484, 0xB40694C4, 'mov', 'r0, #0x3b'), 'clk_gate_on(59): 0xb01600a4 bit 27'),
        enable_value=fact(find(code, 0xB40694C4, 0xB4069504, 'mov', 'r0, #4'), 'control word := 4 after zeroing'),
        count_offset=fact(find(code, 0xB4069504, 0xB4069514, 'ldr', '[r0, #8]'), 'count word = control + 8'),
        ticks_per_us=fact(find(code, T, T + 0x40, 'mov', 'r3, #0x18'), 'target = start + 24 * us'),
        wrap_safe_compare=fact(find(code, T, T + 0x40, 'blt'), 'loop while (int32)(now - target) < 0: wrap-safe, '
                                                                 'unbounded if the count never advances'),
        ms=fact(find(code, 0xB4069434, 0xB4069440, 'mov', '#0x3e8'), 'delay_ms(n) = delay_us(1000 n)'))
    uart = dict(
        tx_full_poll=fact(find(code, 0xB4066ADC, 0xB4066B28, 'tst', '#0x40'), 'wait while status bit 6 set (unbounded)'),
        tx_data=fact(find(code, 0xB4066ADC, 0xB4066B28, 'add', '#8'), 'character written to base + 8'),
        tx_empty_poll=fact(find(code, 0xB4066ADC, 0xB4066B28, 'tst', '#0x400'), 'then wait until status bit 10 set '
                                                                               '(unbounded)'),
        crlf=fact(find(code, 0xB40667A8, 0xB40667D8, 'mov', 'r1, #0xd'), 'putc sends CR before LF'),
        divisor_clock=fact(find(code, 0xB40669D4, 0xB4066A10, 'ldr', '[pc'), 'divider = 24000000 / (8 * baud) - 1',
                           code=code),
        control=fact(find(code, 0xB4066A14, 0xB4066AD4, 'ldr', 'r0, [pc'), 'UART control word written', code=code),
        handle=fact(find(code, 0xB4066784, 0xB40667A4, 'str', 'r0, [r3]'), 'table entry pointer -> 0xb4070800 '
                                                                          '(0 when no entry matches)'))
    i2c = dict(
        bus_cache=fact(find(code, 0xB406A788, 0xB406A7B0, 'ldr', 'r3, [pc'), 'current bus word (0xffffffff in image)',
                       code=code),
        clkdiv=fact(find(code, 0xB406A950, 0xB406A968, 'mov', 'r0, #0x10'), 'I2C base + 4 := 0x10'),
        probe_poll=fact(find(code, 0xB406AB7C, 0xB406AC0C, 'tst', 'r0, #1'), 'probe waits for base+0x20 bit 0 '
                                                                             '(unbounded)'),
        xfer_timeout=fact(find(code, 0xB406A994, 0xB406AB78, 'ldr', 'r6, [pc'), 'transfer poll bound: 501 x '
                                                                               'delay_ms(1)', code=code),
        slave=fact(find(code, 0xB4069610, 0xB406966C, 'mov', 'r0, #0x65'), 'PMIC I2C slave address 0x65'))
    return dict(adfu_check=adfu, timer=timer, uart=uart, i2c=i2c)


def graph_document(code, funcs):
    out = {}
    for f, r in sorted(funcs.items()):
        name = NAMES.get(f)
        if r is None:
            out[h32(f)] = dict(name=name, analysed=False,
                               reason='boundary (not entered)' if code.inside(f) else EXTERNAL.get(f, 'outside the image'))
            continue
        out[h32(f)] = dict(name=name, analysed=True, instructions=r['instructions'], code_end=h32(r['code_end']),
                           extent_end=h32(r['extent_end']), noncontiguous=r['noncontiguous'],
                           code_sha256=r['code_sha256'], extent_sha256=r['extent_sha256'],
                           callees=sorted({c['target'] for c in r['calls'] if c['target']}),
                           unresolved_indirect=[c['site'] for c in r['calls'] if c.get('indirect') and not c.get('resolved')],
                           conditional_branches=sum(1 for b in r['branches'] if b.get('condition')),
                           sysops=r['sysops'], notes=r['notes'], helper=HELPERS.get(f))
    callers = {}
    for f, r in funcs.items():
        for c in (r or {}).get('calls', []):
            if c['target']:
                callers.setdefault(c['target'], set()).add(h32(f))
    for k, v in out.items():
        v['callers'] = sorted(callers.get(k, ()))
    return out


def static_accesses(code, funcs):
    """Register accesses resolvable from instructions: direct constant-base loads/stores, accessor
    helpers called with constant arguments, and annotated bit-indexed helpers."""
    rows = []
    for f, r in sorted(funcs.items()):
        if r is None or f in HELPERS:
            continue
        for a in r['accesses']:
            if a['region'] in ('mmio', 'unresolved', 'rom') or (a['address'] and int(a['address'], 16) in
                                                                (BOOT_CODE_VA,)):
                rows.append(dict(function=h32(f), function_name=NAMES.get(f), instruction=a['at'], via=None,
                                 access=a['access'], width=a['width'], address=a['address'], region=a['region'],
                                 value=a.get('value'), expression=a.get('expression'), conditional=a['conditional'],
                                 evidence='decoded' if a['address'] else 'unresolved'))
        for c in r['calls']:
            t = int(c['target'], 16) if c['target'] else None
            hp = HELPERS.get(t)
            if not hp:
                continue
            args = [int(x, 16) if x else None for x in c['args']] + [None] * 4
            if hp['kind'] in ('read32', 'write32', 'rmw32'):
                addr = args[int(hp['addr'][1])]
                row = dict(function=h32(f), function_name=NAMES.get(f), instruction=c['site'], via=h32(t),
                           access={'read32': 'read', 'write32': 'write', 'rmw32': 'rmw'}[hp['kind']], width=4,
                           address=h32(addr), region=region_of(addr), conditional=c['conditional'],
                           evidence='decoded (accessor call with constant argument)' if addr is not None else 'unresolved')
                if hp['kind'] == 'write32':
                    row['value'] = h32(args[int(hp['value'][1])])
                if hp['kind'] == 'rmw32':
                    row['clear'], row['set'] = h32(args[1]), h32(args[2])
                if addr is None:
                    row['expression'] = f"{hp['addr']} at call (not a constant)"
                rows.append(row)
            elif hp['kind'] == 'bit-rmw':
                res = helper_address(t, args[0], args[1])
                if not res:
                    rows.append(dict(function=h32(f), function_name=NAMES.get(f), instruction=c['site'], via=h32(t),
                                     access='rmw', width=4, address=None, region='unresolved',
                                     expression=hp['formula'] + ' with non-constant r0', conditional=c['conditional'],
                                     evidence='unresolved'))
                for addr, clr, st in res or ():
                    rows.append(dict(function=h32(f), function_name=NAMES.get(f), instruction=c['site'], via=h32(t),
                                     access='rmw', width=4, address=h32(addr), region=region_of(addr),
                                     clear=h32(clr), set=h32(st), conditional=c['conditional'],
                                     evidence='annotated (helper formula, constant argument)'))
    return rows


def boot_code_references(code, funcs):
    """Every decoded use of the boot-code word: direct loads/stores of 0xb4064c00 (also as 0xb4064000+0xc00),
    calls to the getter, and calls that receive the value in an argument register."""
    rows = []
    # 1. any load/store whose constant effective address is the boot-code word, across all analysed code
    for f, r in sorted(funcs.items()):
        if not r:
            continue
        for a in r['accesses']:
            if a['address'] and int(a['address'], 16) == BOOT_CODE_VA:
                rows.append(dict(kind='direct ' + a['access'], function=h32(f), function_name=NAMES.get(f),
                                 at=a['at'], insn=a['insn'], value=a.get('value')))
        for c in r['calls']:
            if c['target'] == h32(BOOT_CODE_GETTER):
                rows.append(dict(kind='getter call', function=h32(f), function_name=NAMES.get(f), at=c['site']))
    # 2. call sites where r0 was just loaded from the boot-code word (main's load_* calls)
    for f, r in sorted(funcs.items()):
        if not r:
            continue
        for c in r['calls']:
            site = int(c['site'], 16)
            prev = code.insn(site - 4)
            if prev and prev.mnemonic == 'ldr' and prev.op_str.startswith('r0, [r1]'):
                p2 = code.insn(site - 8)
                if p2 and p2.mnemonic == 'ldr' and '[pc' in p2.op_str:
                    lit = code.word(p2.address + 8 + p2.operands[1].mem.disp)
                    if lit == BOOT_CODE_VA:
                        rows.append(dict(kind='passed as r0', function=h32(f), function_name=NAMES.get(f),
                                         at=c['site'], callee=c['target'], callee_name=NAMES.get(int(c['target'], 16))))
    # 3. literal-pool words equal to the address, inside or outside analysed functions (data, not proof of use)
    lits = []
    for va in range(BASE, BL_CODE[1], 4):
        if va - BASE + 4 <= len(code.data) and code.word(va) in (BOOT_CODE_VA, 0xB4064000):
            lits.append(dict(at=h32(va), word=h32(code.word(va))))
    return dict(references=rows, literal_words=lits,
                note='0xb4064000 is also the base other code uses for 0xb4064c60..c74 (publish_globals); a literal '
                     'is a data word, not evidence of a use. Uses are the decoded loads/stores and calls above.')


# --------------------------------------------------------------------------- emulation

SYNTHETIC_RULES = {
    'timer': 'T0 count word (timer base+8, 0xb0168010): +24 per read (1 synthetic us per read)',
    'uart_stat': 'UART status (base+0xc): 0x400 (bit 10 set, bit 6 clear) - TX never full, always drains',
    'i2c_fifostat': 'I2C base+0x20: 0x1 (bit 0 set, bit 1 clear) - every probe/transfer completes without error',
    'gpio_cdat': 'GPIO C data (0xb01b0020): last written value; bit 10 := 0 (no-loopback) or := bit 11 (loopback)',
    'seeded': 'any other MMIO read: last value written there, else the run seed (0 or 0xffffffff)',
    'pmic': 'PMIC I2C transactions (0xb406ac10 read / 0xb406ac60 write) served by a register file (Pmic)',
    'rom_service': 'Boot ROM service r9=4 (sector read) served from the disk image',
}

PMIC_DEFAULTS = {0xFF: 0x00CA, 0x32: 0x1BC0, 0xDC: 0x0001, 0x14: 0x8000, 0x35: 0x0000, 0x03: 0x0000}


class Pmic:
    def __init__(self, regs=None):
        self.regs = dict(PMIC_DEFAULTS)
        self.regs.update(regs or {})
        self.log = []


class Machine:
    """Minimal bounded Unicorn A32 CPU: SRAM + MMIO window + ROM page, explicit stubs and stops."""

    def __init__(self, sram, mmio_read, mmio_write, sram_write, limit):
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, \
            UC_HOOK_MEM_UNMAPPED
        from unicorn import arm_const as A
        self.R = [A.UC_ARM_REG_R0, A.UC_ARM_REG_R1, A.UC_ARM_REG_R2, A.UC_ARM_REG_R3, A.UC_ARM_REG_R4,
                  A.UC_ARM_REG_R5, A.UC_ARM_REG_R6, A.UC_ARM_REG_R7, A.UC_ARM_REG_R8, A.UC_ARM_REG_R9,
                  A.UC_ARM_REG_R10, A.UC_ARM_REG_R11, A.UC_ARM_REG_R12, A.UC_ARM_REG_SP, A.UC_ARM_REG_LR,
                  A.UC_ARM_REG_PC, A.UC_ARM_REG_CPSR]
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(BASE, SRAM_SIZE)
        self.uc.mem_write(BASE, bytes(sram))
        self.uc.mem_map(MMIO[0], MMIO[1] - MMIO[0])
        self.uc.mem_map(0xFFFF0000, 0x10000)        # stop page only: stops fire before anything executes there
        self.stubs, self.stops, self.limit, self.count = {}, {}, limit, 0
        self.stopped, self.error, self.on_code = None, None, None
        self._mr, self._mw = mmio_read, mmio_write
        self.uc.hook_add(UC_HOOK_CODE, self._code)
        self.uc.hook_add(UC_HOOK_MEM_READ, self._mread, begin=MMIO[0], end=MMIO[1] - 1)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self._mwrite, begin=MMIO[0], end=MMIO[1] - 1)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, sram_write, begin=BASE, end=BASE + SRAM_SIZE - 1)
        self.uc.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)

    def reg(self, n, value=None):
        if value is None:
            return self.uc.reg_read(self.R[n])
        self.uc.reg_write(self.R[n], value & 0xFFFFFFFF)

    def read(self, va, n):
        return bytes(self.uc.mem_read(va, n))

    def u32(self, va):
        return struct.unpack('<I', self.read(va, 4))[0]

    def cstr(self, va, limit=512):
        out = bytearray()
        while len(out) < limit:
            c = self.read(va + len(out), 1)[0]
            if not c:
                break
            out.append(c)
        return out.decode('latin1')

    def stop(self, name, at):
        self.stopped = dict(at=at, name=name, regs=[self.reg(k) for k in range(16)])
        self.uc.emu_stop()

    def _code(self, uc, address, size, _):
        self.count += 1
        if self.count > self.limit:
            self.error = f'instruction limit {self.limit} reached at 0x{address:x}'
            uc.emu_stop()
            return
        if self.on_code:
            self.on_code(address)
        if address in self.stops:
            self.stop(self.stops[address], address)
            return
        if address in self.stubs:
            try:
                ret = self.stubs[address][1](self)
            except Exception as e:          # an unmodelled request inside a stub ends the run
                self.error = f'{type(e).__name__}: {e}'
                uc.emu_stop()
                return
            if ret is not None:
                self.reg(0, ret)
            self.reg(15, self.reg(14) & ~1)

    def _mread(self, uc, access, address, size, value, _):
        v = self._mr(address, size)
        uc.mem_write(address, struct.pack('<I', v & 0xFFFFFFFF)[:size])

    def _mwrite(self, uc, access, address, size, value, _):
        self._mw(address, size, value)

    def _unmapped(self, uc, access, address, size, value, _):
        self.error = f'unmapped access 0x{address:08x} at pc 0x{self.reg(15):x} (no memory is modelled there)'
        return False

    def call(self, entry, sp):
        self.reg(13, sp)
        self.reg(14, 0xFFFFFFF0)
        self.stops.setdefault(0xFFFFFFF0, 'return')
        self.reg(16, 0x1D3)                 # SVC, IRQ/FIQ masked, ARM: an emulator choice, not the ROM's state
        try:
            self.uc.emu_start(entry, 0xFFFFFFFF)
        except Exception as e:
            if not self.error:
                self.error = f'{type(e).__name__}: {e}'
        return self.stopped


class Trace:
    def __init__(self, loader, disk, code, funcs, boot_code, scenario='no-loopback', seed=0, pmic=None,
                 ini_patch=None, limit=3_000_000):
        self.boot_code, self.scenario, self.seed = boot_code, scenario, seed
        self.pmic = Pmic(pmic)
        self.disk, self.code = disk, code
        self.entries = {f for f in funcs if funcs[f] is not None} | set(NAMES)
        sram = bytearray(SRAM_SIZE)
        sram[0:0x33C00] = loader[0:0x33C00]
        self.ini_patch = ini_patch or {}
        self.events, self.calls, self.printed, self.delays, self.services = [], [], [], [], []
        self.mem, self.stack, self.min_sp, self.sram_writes = {}, [], STACK_TOP, set()
        self.emu = Machine(sram, self._mmio_read, self._mwrite, self._sram_write, limit)
        self.emu.uc.mem_write(BOOT_CODE_VA, struct.pack('<I', boot_code))
        self.emu.stubs = {0xB4066854: ('printf', self._printf), ROM_SERVICE: ('Boot ROM service', self._service),
                          0xB406AC10: ('i2c_read (PMIC register file)', self._i2c_read),
                          0xB406AC60: ('i2c_write (PMIC register file)', self._i2c_write)}
        self.emu.stops = {DRAM_COLD: 'DRAM init entry 0xb40690b8 (boundary)', DRAM_CORE: 'DRAM core 0xb40673f4',
                          ROM_REENTRY: 'ROM re-entry 0xb40691a4 (ADFU)', ADFU_EXIT: "main's ADFU exit 0xb4065494",
                          RESUME_ENTRY: 'resume entry 0xb40664e4'}
        self.emu.on_code = self._on_code

    def _on_code(self, pc):
        self._track(pc)
        if pc == DELAY_US:
            self.delays.append(dict(us=self.emu.reg(0), caller=self._caller_name()))
        i = self.code.insn(pc) if self.code.inside(pc) else None
        if i is not None and i.mnemonic == 'b' and imm_target(i) == pc:
            self.emu.stop(f'self-loop (hang) at 0x{pc:x}', pc)

    # ---- frame tracking
    def _track(self, pc):
        while self.stack and pc == self.stack[-1][1]:
            self.stack.pop()
        if pc in self.entries:
            lr = self.emu.reg(14)
            if self.stack and self.stack[-1][1] == lr:
                self.stack[-1] = (pc, lr)
            else:
                self.stack.append((pc, lr))
            self.calls.append(pc)
        sp = self.emu.reg(13)
        if sp < self.min_sp:
            self.min_sp = sp

    def _frame(self):
        """Innermost function that is not an accessor helper, plus the innermost frame."""
        inner = self.stack[-1][0] if self.stack else None
        for f, _ in reversed(self.stack):
            if f not in HELPERS:
                return f, inner
        return inner, inner

    def _site(self):
        """Address of the instruction in the innermost non-helper function that led to the current access: the
        access itself, or the call of the first helper frame above that function."""
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k][0] not in HELPERS:
                if k == len(self.stack) - 1:
                    return self.emu.reg(15)
                return (self.stack[k + 1][1] - 4) & 0xFFFFFFFF
        return self.emu.reg(15)

    def _caller_name(self):
        for f, _ in reversed(self.stack[:-1]):
            if f not in HELPERS and f not in (DELAY_US, 0xB4069434):
                return NAMES.get(f, h32(f))
        return None

    # ---- MMIO
    def _mmio_read(self, a, size):
        rule = 'seeded'
        if a == 0xB0168010:
            self.mem[a] = (self.mem.get(a, 0) + 24) & 0xFFFFFFFF
            v, rule = self.mem[a], 'timer'
        elif 0xB0120000 <= a < 0xB012E000 and a & 0x1FFF == 0xC:
            v, rule = 0x400, 'uart_stat'
        elif 0xB0170000 <= a < 0xB0180000 and a & 0x3FFF == 0x20:
            v, rule = 0x1, 'i2c_fifostat'
        elif a == 0xB01B0020:
            last = self.mem.get(a, self.seed)
            bit = ((last >> 11) & 1) if self.scenario == 'loopback' else 0
            v, rule = (last & ~0x400) | (bit << 10), 'gpio_cdat'
        else:
            v = self.mem.get(a, self.seed)
        f, inner = self._frame()
        self.events.append(dict(op='read', address=a, value=v & 0xFFFFFFFF, width=size, pc=self._site(),
                                insn=self.emu.reg(15), function=f, inner=inner, rule=rule))
        return v

    def _mwrite(self, address, size, value):
        self.mem[address] = value & 0xFFFFFFFF
        f, inner = self._frame()
        self.events.append(dict(op='write', address=address, value=value & 0xFFFFFFFF, width=size,
                                pc=self._site(), insn=self.emu.reg(15), function=f, inner=inner))

    def _sram_write(self, uc, access, address, size, value, _):
        if address < self.emu.reg(13) - 0x40 or address >= STACK_TOP:
            self.sram_writes.add(address & ~3)

    # ---- stubs
    def _printf(self, emu):
        from ddr_emulate import _sprintf
        fmt = emu.cstr(emu.reg(0))
        sp = emu.reg(13)
        args = [emu.reg(1), emu.reg(2), emu.reg(3)] + [emu.u32(sp + 4 * k) for k in range(6)]
        text = _sprintf(fmt, args).rstrip('\n')
        f, _ = self._frame()
        self.events.append(dict(op='print', text=text, function=self._caller_name() and f, pc=emu.reg(14) - 4))
        self.printed.append(text)
        return 0

    def _service(self, emu):
        sel = emu.reg(9)
        if sel != 4:
            raise RuntimeError(f'ROM service selector r9={sel} not modelled')
        lba, count, dest = emu.reg(0), emu.reg(1), emu.reg(2)
        data = bytearray(self.disk.sectors(lba, count))
        if dest == INI_VA:
            for off, b in self.ini_patch.items():
                data[off:off + len(b)] = bytes(b)
        emu.uc.mem_write(dest, bytes(data))
        rec = dict(selector=4, disk_offset=h32(lba * 512), sectors=count, dest=h32(dest), sha256=sha(data))
        self.services.append(rec)
        self.events.append(dict(op='rom-read', **rec, function=self._frame()[0]))
        return 0

    def _i2c_read(self, emu):
        slave, reg, buf, n = emu.reg(0), emu.reg(1) & 0xFF, emu.reg(3), emu.u32(emu.reg(13))
        v = self.pmic.regs.get(reg, 0) & 0xFFFF
        emu.uc.mem_write(buf, bytes([v >> 8, v & 0xFF])[:n])
        self.pmic.log.append(('r', reg, v))
        self.events.append(dict(op='pmic-read', slave=slave, reg=reg, value=v, function=self._caller_name()))
        return 0

    def _i2c_write(self, emu):
        slave, reg, buf = emu.reg(0), emu.reg(1) & 0xFF, emu.reg(3)
        b = emu.read(buf, 2)
        v = (b[0] << 8) | b[1]
        self.pmic.regs[reg] = v
        self.pmic.log.append(('w', reg, v))
        self.events.append(dict(op='pmic-write', slave=slave, reg=reg, value=v, function=self._caller_name()))
        return 0

    def run(self):
        self.emu.call(MAIN, STACK_TOP)
        st = self.emu.stopped
        return dict(stopped=st['name'] if st else None, error=self.emu.error, instructions=self.emu.count,
                    regs_at_stop=None if not st or 'regs' not in st else [h32(x) for x in st['regs'][:4]])


class Disk:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.f.seek(0, 2)
        self.size = self.f.tell()

    def sectors(self, lba, count):
        if (lba + count) * 512 > self.size:
            raise RuntimeError('read beyond image')
        self.f.seek(lba * 512)
        return self.f.read(count * 512)


def event_key(e):
    """Comparable signature of an event (no pc-in-poll noise, no instruction counts)."""
    if e['op'] == 'read' and e.get('rule') == 'timer':
        return f"read {e['address']:08x} (timer count) [{NAMES.get(e['function'], h32(e['function']))}]"
    if e['op'] in ('read', 'write'):
        return f"{e['op']} {e['address']:08x} = {e['value']:08x} [{NAMES.get(e['function'], h32(e['function']))}]"
    if e['op'] in ('pmic-read', 'pmic-write'):
        return f"{e['op']} reg 0x{e['reg']:02x} = 0x{e['value']:04x} [{e['function']}]"
    if e['op'] == 'print':
        return f"print {e['text']!r}"
    if e['op'] == 'rom-read':
        return f"rom-read {e['disk_offset']} x{e['sectors']} -> {e['dest']}"
    return e['op']


def collapse(keys):
    out = []
    for k in keys:
        if out and out[-1][0] == k:
            out[-1][1] += 1
        else:
            out.append([k, 1])
    return out


def run_trace(loader, disk, code, funcs, boot_code, **kw):
    t = Trace(loader, disk, code, funcs, boot_code, **kw)
    res = t.run()
    st = t.emu.stopped
    if st and st['name'].startswith('DRAM init entry'):
        rec_va = t.emu.reg(0)
        res['dram_argument'] = dict(r0=h32(rec_va), record_bytes=t.emu.read(rec_va, 12).hex()
                                    if BASE <= rec_va < BASE + SRAM_SIZE - 12 else None,
                                    mode_bytes=t.emu.read(0xB4070804, 2).hex())
    res['globals'] = t.emu.read(GLOBALS[0], GLOBALS[1] - GLOBALS[0]).hex()
    res['afi'] = t.emu.read(0xB4060300, 16).hex()
    res['pointer_table'] = t.emu.read(0xB4064C60, 0x18).hex()
    res['i2c_bus_cache'] = h32(t.emu.u32(0xB406BA10))
    res['stack_depth_bytes'] = STACK_TOP - t.min_sp
    return t, res


def summarise_trace(t, res):
    keys = [event_key(e) for e in t.events]
    mmio = [e for e in t.events if e['op'] in ('read', 'write')]
    seeded = sorted({e['address'] for e in mmio if e['op'] == 'read' and e['rule'] == 'seeded'})
    return dict(result=res, printed=t.printed, rom_reads=t.services,
                delays_requested_us=sum(d['us'] for d in t.delays),
                delay_calls=collapse([f"{d['us']} us from {d['caller']}" for d in t.delays]),
                pmic=[dict(op=o, reg=f'0x{r:02x}', value=f'0x{v:04x}') for o, r, v in t.pmic.log],
                mmio_accesses=len(mmio), mmio_writes=sum(1 for e in mmio if e['op'] == 'write'),
                seeded_read_addresses=[h32(a) for a in seeded],
                functions_entered=ordered_unique([NAMES.get(f, h32(f)) for f in t.calls]),
                call_sequence=collapse([NAMES.get(f, h32(f)) for f in t.calls if f not in HELPERS and
                                        f not in (0xB4069504, 0xB4069470)]),
                sram_written_ranges=ranges(sorted(t.sram_writes)),
                events=collapse(keys))


def ordered_unique(xs):
    seen, out = set(), []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def ranges(addrs):
    out = []
    for a in addrs:
        if out and a == out[-1][1]:
            out[-1][1] = a + 4
        else:
            out.append([a, a + 4])
    return [f'0x{a:08x}..0x{b:08x}' for a, b in out]


def diff_events(a, b, label_a, label_b):
    ka = [k for k, n in a['events'] for _ in range(min(n, 3))]
    kb = [k for k, n in b['events'] for _ in range(min(n, 3))]
    sm = difflib.SequenceMatcher(a=ka, b=kb, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        out.append(dict(change=tag, position=i1, **{label_a: collapse(ka[i1:i2]), label_b: collapse(kb[j1:j2])}))
    return out


def executed_accesses(t, boot_code, scenario):
    """Unique (pc, address, op, value) MMIO accesses of one run, attributed to functions."""
    seen = {}
    for e in t.events:
        if e['op'] not in ('read', 'write'):
            continue
        k = (e['pc'], e['address'], e['op'])
        r = seen.setdefault(k, dict(instruction=h32(e['pc']), access_instruction=h32(e['insn']),
                                    function=h32(e['function']),
                                    function_name=NAMES.get(e['function']), helper=h32(e['inner'])
                                    if e['inner'] != e['function'] else None, access=e['op'], width=e['width'],
                                    address=h32(e['address']), values=[], count=0, rule=e.get('rule'),
                                    boot_code=boot_code, scenario=scenario))
        r['count'] += 1
        v = h32(e['value'])
        if v not in r['values'] and len(r['values']) < 4:
            r['values'].append(v)
    return list(seen.values())


# --------------------------------------------------------------------------- data tables decoded from the image

def ini_inputs(code):
    ini = code.bytes(INI_VA, INI_VA + 0x60)
    u32 = lambda o: struct.unpack_from('<I', ini, o)[0]
    return {
        'ini+0x00 version': ini[0:4].split(b'\0')[0].decode('latin1'),
        'ini+0x0c bootdev (printed only)': f'0x{ini[0x0c]:02x}',
        'ini+0x0d board MFP index -> 0xb4070810': ini[0x0d],
        'ini+0x0e UART index -> 0xb407082c': ini[0x0e],
        'ini+0x0f UART pad -> 0xb4070830': ini[0x0f],
        'ini+0x10 baud -> 0xb4070834': u32(0x10),
        'ini+0x14 ADFU handshake enable (word)': u32(0x14),
        'ini+0x18 PMIC I2C bus -> 0xb4070858[0]': ini[0x18],
        'ini+0x19 -> 0xb4070858[1]': ini[0x19],
        'ini+0x1a -> 0xb407085c': ini[0x1a],
        'ini+0x1b PMIC reg 0x14 adjust -> 0xb4070860': ini[0x1b],
        'ini+0x2c second-record select (word)': u32(0x2c),
        'primary record -> 0xb4070820 (ini 0x1c,1d,20,21,24..2b)': bytes(ini[o] for o in PRIMARY_MAP).hex(),
        'second record -> 0xb407084c (ini 0x4c,4d,50,51,54..5b)': bytes(ini[o] for o in SECOND_MAP).hex(),
    }


# Byte map of ini_to_globals (0xb4065ff8): record byte k <- ini offset MAP[k] (decoded from its ldrb/strb pairs).
PRIMARY_MAP = (0x1C, 0x1D, 0x20, 0x21, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B)
SECOND_MAP = (0x4C, 0x4D, 0x50, 0x51, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B)


def uart_table(code, index, pad):
    """Decode the 24-entry UART table at 0xb406b520 (0x30 bytes each) for one (index, pad)."""
    for k in range(24):
        e = 0xB406B520 + 0x30 * k
        b = code.bytes(e, e + 4)
        if b[0] == index and b[1] == pad:
            mux = []
            for j in range(3):
                a, m, v = (code.word(e + 0xC + 12 * j + 4 * n) for n in range(3))
                if m:
                    mux.append(dict(address=h32(a), clear=h32(m), set=h32(v)))
            gate, rst = b[2], b[3]
            return dict(table_entry=k, table_va=h32(e), uart_base=h32(code.word(e + 4)),
                        clock_divider_register=h32(code.word(e + 8)),
                        clock_gate=dict(bit_index=gate, register=h32(0xB01600A0 + 4 * (gate >> 5)), bit=gate & 31),
                        reset=dict(bit_index=rst, register=h32(0xB01600A8 + 4 * (rst >> 5)), bit=rst & 31),
                        pin_mux_writes=mux, control_value='0x00008003')
    return None


def board_table(code):
    return [dict(index=k, register=h32(code.word(0xB406B4C8 + 12 * k)), clear=h32(code.word(0xB406B4CC + 12 * k)),
                 set=h32(code.word(0xB406B4D0 + 12 * k))) for k in range(2)]


def baud_divisor(baud):
    """0xb40669d4: CMU divider := 24000000 // (baud * 8) - 1 (when the quotient is non-zero)."""
    q = 24_000_000 // (baud << 3) if baud else None
    if q is None:
        return None
    return dict(written=q - 1 if q else 0, quotient=q, implied_baud_if_24MHz=round(24_000_000 / (8 * q), 1) if q else None)


# --------------------------------------------------------------------------- canonical names

def canonical_names():
    model = json.loads((ROOT / 'registers/canonical/hardware.json').read_text(encoding='utf-8'))
    names = {}
    for b in model['blocks']:
        for r in b['registers']:
            a = b['base'] + r['offset']
            names.setdefault(a, (r['name'], b['id'], b.get('scope')))
    return names


# --------------------------------------------------------------------------- top level

SCENARIOS = [
    # (label, boot_code, kwargs)
    ('code0', 0, {}),
    ('code2', 2, {}),
    ('code0-seedFF', 0, dict(seed=0xFFFFFFFF)),
    ('code2-seedFF', 2, dict(seed=0xFFFFFFFF)),
    ('code2-loopback', 2, dict(scenario='loopback')),
    ('code0-loopback', 0, dict(scenario='loopback')),
    ('code2-handshake-disabled', 2, dict(ini_patch={0x14: b'\0\0\0\0'})),
    ('code2-pmu-status-bit1', 2, dict(pmic={0x35: 0x0002})),
]


def analyse_release(path, release, verify=True, scenarios=SCENARIOS):
    loader, ident = load_image(path, verify=verify)
    code = Code(loader)
    funcs = call_graph(code)
    disk = Disk(path)
    runs, traces = {}, {}
    for label, bc, kw in scenarios:
        t, res = run_trace(loader, disk, code, funcs, bc, **kw)
        runs[label] = summarise_trace(t, res)
        traces[label] = t
    return dict(release=release, identity=ident, code=code, funcs=funcs, runs=runs, traces=traces, loader=loader)


def access_inventory(doc, canon):
    """Merge executed (code 0 / code 2) and static accesses into one inventory with explicit evidence types."""
    code, funcs, traces = doc['code'], doc['funcs'], doc['traces']
    rows = {}
    ex = {lab: executed_accesses(traces[lab], traces[lab].boot_code, traces[lab].scenario)
          for lab in ('code0', 'code2', 'code2-loopback', 'code2-pmu-status-bit1')}
    for lab, lst in ex.items():
        for r in lst:
            key = (r['instruction'], r['address'], r['access'])
            row = rows.setdefault(key, dict(
                release=doc['release'], function_address=r['function'], function_name=r['function_name'],
                instruction_address=r['instruction'], access_instruction=r['access_instruction'], helper=r['helper'],
                register_address=r['address'],
                access_width=r['width'], access_type=r['access'], values_observed_in_emulation={},
                read_value_source=r['rule'] if r['access'] == 'read' else None, executed_in=[],
                evidence_type='executed (synthetic conditions)'))
            row['executed_in'].append(lab)
            row['values_observed_in_emulation'][lab] = r['values']
    for r in rows.values():
        a = int(r['register_address'], 16)
        n = canon.get(a)
        r['register_identity'] = (f'{n[0]} ({n[1]}, {n[2]}; related-SoC label, not verified on ATM7039S)'
                                  if n else 'unknown (no catalogue entry)')
        on0, on2 = 'code0' in r['executed_in'], 'code2' in r['executed_in']
        r['boot_code_condition'] = ('both' if on0 and on2 else 'code 2 only' if on2 else 'code 0 only' if on0
                                    else 'scenario-only (' + ', '.join(r['executed_in']) + ')')
        r['execution_phase'] = PHASE.get(r['function_name'], 'pre-DRAM') if r['function_name'] else 'pre-DRAM'
        r['confidence'] = 'verified-instruction; values depend on synthetic reads' if r['access_type'] == 'read' or \
            r['read_value_source'] else 'verified-instruction'
    static = static_accesses(code, funcs)
    out = sorted(rows.values(), key=lambda r: (int(r['instruction_address'], 16), r['register_address']))
    executed_sites = {r['instruction_address'] for r in out}
    executed_callers = {(r['function_address']) for r in out}
    not_executed = []
    for s in static:
        if s['region'] not in ('mmio', 'unresolved'):
            continue
        if s['instruction'] in executed_sites:
            continue
        not_executed.append(dict(release=doc['release'], function_address=s['function'],
                                 function_name=s['function_name'], instruction_address=s['instruction'],
                                 via=s['via'], register_address=s['address'], access_type=s['access'],
                                 value_or_mask=s.get('value') or (dict(clear=s.get('clear'), set=s.get('set'))
                                                                  if s.get('clear') else None),
                                 expression=s.get('expression'), evidence_type='static-path (' + s['evidence'] + ')',
                                 note='decoded in a function reachable from main; not executed in the code-0/code-2 '
                                      'runs' if s['function'] not in executed_callers else
                                 'decoded; this site was not executed in the code-0/code-2 runs'))
    return out, not_executed


PHASE = {
    'main': 'main', 'load_ini': 'storage (ini reload)', 'storage_read_dispatch': 'storage (ini reload)',
    'ini_to_globals': 'config', 'timer_init': 'timer', 'timer_reset': 'timer', 'timer_start': 'timer',
    'delay_us': 'timer', 'uart_init': 'uart', 'uart_setup': 'uart', 'uart_set_baud': 'uart', 'board_mfp_init': 'board',
    'pmu_init': 'pmic', 'pmu_detect': 'pmic', 'pmu_clkout_select': 'pmic', 'i2c_select': 'pmic (I2C bus)',
    'i2c_probe': 'pmic (I2C bus)', 'adfu_check': 'adfu', 'rom_reentry_adfu': 'adfu exit', 'dram_caller': 'config',
}


def release_comparison(docs):
    """Per-function hashes across releases, plus the ini inputs the pre-DRAM code consumes."""
    rels = list(docs)
    allf = sorted({f for d in docs.values() for f, r in d['funcs'].items() if r})
    rows = []
    for f in allf:
        hs = {r: (docs[r]['funcs'].get(f) or {}).get('code_sha256') for r in rels}
        xs = {r: (docs[r]['funcs'].get(f) or {}).get('extent_sha256') for r in rels}
        rows.append(dict(function=h32(f), name=NAMES.get(f), code_identical=len(set(hs.values())) == 1,
                         extent_identical=len(set(xs.values())) == 1, code_sha256=next(iter(hs.values())),
                         **({} if len(set(hs.values())) == 1 else dict(per_release=hs))))
    ini = {r: ini_inputs(docs[r]['code']) for r in rels}
    keys = list(next(iter(ini.values())))
    ini_rows = {k: ({r: ini[r][k] for r in rels} if len({json.dumps(ini[r][k]) for r in rels}) > 1
                    else dict(all=ini[rels[0]][k])) for k in keys}
    tables = {r: dict(uart=sha(docs[r]['code'].bytes(0xB406B520, 0xB406B520 + 24 * 0x30)),
                      board=sha(docs[r]['code'].bytes(0xB406B4C8, 0xB406B4E0)),
                      pmic_reg_table=sha(docs[r]['code'].bytes(0xB406B9D0, 0xB406BA14))) for r in rels}
    boundary = {r: docs[r]['runs']['code2']['result'].get('dram_argument') for r in rels}
    traces = {}
    for lab in ('code0', 'code2'):
        sigs = {r: sha(json.dumps(docs[r]['runs'][lab]['events']).encode()) for r in rels}
        traces[lab] = dict(identical=len(set(sigs.values())) == 1, **({} if len(set(sigs.values())) == 1
                                                                       else dict(per_release=sigs)))
    return dict(functions=rows, all_function_code_identical=all(r['code_identical'] for r in rows),
                all_function_extents_identical=all(r['extent_identical'] for r in rows),
                ini_inputs=ini_rows, data_tables=tables,
                data_tables_identical={k: len({tables[r][k] for r in rels}) == 1 for k in ('uart', 'board',
                                                                                             'pmic_reg_table')},
                executed_event_sequences=traces,
                dram_boundary_argument_code2=boundary,
                normalisation='None. Hashes are of the raw instruction words each function decodes (code_sha256) '
                              'and of the raw bytes from entry to the end of its literal pool (extent_sha256). '
                              'Event sequences compare (op, address, value, function) after collapsing consecutive '
                              'identical events into one entry with a count; instruction counts are not compared.')


def evidence(docs, reference):
    canon = canonical_names()
    ref = docs[reference]
    code, funcs = ref['code'], ref['funcs']
    pre = predram_subgraph(funcs)
    pre_set = {int(x, 16) for x in pre['functions']}
    graph = graph_document(code, {f: r for f, r in funcs.items() if f in pre_set | {DRAM_COLD, DRAM_CORE}})
    inv, static_only = access_inventory(ref, canon)
    static_only = [r for r in static_only if int(r['function_address'], 16) in pre_set]
    unresolved = {}
    for r in static_only:
        if r['register_address'] is None:
            unresolved[r['function_name'] or r['function_address']] = unresolved.get(
                r['function_name'] or r['function_address'], 0) + 1
    static_only = [r for r in static_only if r['register_address'] is not None]
    r0, r2 = ref['runs']['code0'], ref['runs']['code2']
    uidx, upad, baud = code.bytes(INI_VA + 0xE, INI_VA + 0xF)[0], code.bytes(INI_VA + 0xF, INI_VA + 0x10)[0], \
        struct.unpack_from('<I', code.bytes(INI_VA + 0x10, INI_VA + 0x14))[0]
    sys_all = [dict(function=k, **s) for k, v in graph.items() for s in v.get('sysops', [])] if graph else []
    doc = dict(
        format_version=1, tool=f'predram_analysis.py v{TOOL_VERSION}', reference_release=reference,
        findings=FINDINGS,
        tool_versions=tool_versions(),
        releases={r: d['identity'] for r, d in docs.items()},
        boundary=dict(start=h32(MAIN), stop=h32(DRAM_COLD), core=h32(DRAM_CORE),
                      note='The pre-DRAM path ends at the call of 0xb40690b8 (cold DRAM init wrapper) from 0xb4066718. '
                           'The DRAM routine itself is out of scope (PR #4/#6).'),
        execution_environment=environment(code, funcs, r0, r2, sys_all),
        call_graph=graph,
        predram_graph=pre,
        other_reachable_from_main=sorted(f'{h32(f)} {NAMES.get(f) or ""}'.strip() for f in funcs if f not in pre_set),
        call_order=dict(code0=r0['functions_entered'], code2=r2['functions_entered']),
        block0=block0_static(code),
        boot_code=dict(writers=block0_writers(code), references=boot_code_references(code, funcs),
                       consumers=BOOT_CODE_CONSUMERS),
        config_inputs=ini_inputs(code),
        structure=structure_facts(code),
        uart=dict(ini=dict(index=uidx, pad=upad, baud=baud), table=uart_table(code, uidx, upad),
                  divisor=baud_divisor(baud)),
        board=dict(ini_index=code.bytes(INI_VA + 0xD, INI_VA + 0xE)[0], table=board_table(code)),
        runs={k: compact_run(v) for k, v in ref['runs'].items()},
        code0_vs_code2=diff_events(r0, r2, 'code0', 'code2'),
        dram_stage_code0_vs_code2=dram_stage_comparison(ref['loader']),
        seed_dependence={b: dict(control_flow_identical=ref['runs'][f'code{b}']['call_sequence'] ==
                                 ref['runs'][f'code{b}-seedFF']['call_sequence'],
                                 delays_us=[ref['runs'][f'code{b}']['delays_requested_us'],
                                            ref['runs'][f'code{b}-seedFF']['delays_requested_us']],
                                 call_differences=[dict(change=t, seed0=ref['runs'][f'code{b}']['call_sequence'][i1:i2],
                                                        seedFF=ref['runs'][f'code{b}-seedFF']['call_sequence'][j1:j2])
                                                   for t, i1, i2, j1, j2 in difflib.SequenceMatcher(
                                                       a=[json.dumps(x) for x in ref['runs'][f'code{b}']['call_sequence']],
                                                       b=[json.dumps(x) for x in ref['runs'][f'code{b}-seedFF']['call_sequence']],
                                                       autojunk=False).get_opcodes() if t != 'equal'],
                                 differences=diff_events(ref['runs'][f'code{b}'], ref['runs'][f'code{b}-seedFF'],
                                                         'seed0', 'seedFF'))
                         for b in (0, 2)},
        register_inventory=inv, static_only_accesses=static_only,
        unresolved_static_accesses=dict(per_function=dict(sorted(unresolved.items())),
                                        note='Loads/stores whose base register is not a block-local constant (pointer '
                                             'arguments, globals reached through registers). Those on the executed '
                                             'path are attributed in register_inventory from the trace; the rest are '
                                             'not resolved.'),
        release_comparison=release_comparison(docs) if len(docs) > 1 else None,
        synthetic_rules=SYNTHETIC_RULES, pmic_defaults={f'0x{k:02x}': f'0x{v:04x}' for k, v in PMIC_DEFAULTS.items()},
        emulation_audit=EMULATION_AUDIT, unknowns=UNKNOWNS)
    return doc


def compact_run(r):
    out = {k: v for k, v in r.items() if k != 'events'}
    out['event_count'] = sum(n for _, n in r['events'])
    out['events_sha256'] = sha(json.dumps(r['events']).encode())
    return out


def block0_writers(code):
    rows = []
    for va in range(BLOCK0[0], BLOCK0[1], 4):
        i = code.insn(va)
        if i and i.mnemonic == 'str' and i.op_str == 'r1, [r0]':
            p = code.insn(va - 4)
            if p and p.mnemonic == 'ldr' and '[pc' in p.op_str and \
                    code.word(p.address + 8 + p.operands[1].mem.disp) == BOOT_CODE_VA:
                rows.append(dict(store=h32(va)))
    # values written: the immediates loaded into r1 on each path (decoded, see report for the branch tree)
    return dict(stores=rows, decision=[
        dict(condition='[0xb01600a0] & 0x80 != 0 (tested first)', code=2, path='0xb40600cc'),
        dict(condition='bit 7 clear, [0xb01600a0] & 0x10 != 0', code=0, path='0xb40600d4'),
        dict(condition='bits 7 and 4 clear, [0xb4060408] == 0xeb0001d0', code=4, path='0xb406004c'),
        dict(condition='bits 7 and 4 clear, [0xb4060408] != 0xeb0001d0', code=5, path='0xb4060088')],
        note='Codes 0 and 2 then share one instruction path: ROM service r9=4, sector 0x102b, 0x50 sectors to '
             '0xb4065400, blx 0xb4065400. 0xb01600a0 is CMU_DEVCLKEN0 in the related S500 clock tree; which '
             'Boot ROM search sets bit 7 is inferred (BOOT-012), not observed.')


FINDINGS = ['BOOT-021', 'BOOT-024', 'BOOT-025', 'CLK-007', 'UART-004', 'PMIC-002', 'GPIO-002']


def block0_static(code):
    """Block 0 (executed by the Boot ROM, before bootloader.bin): system instructions, MMIO and the ROM calls."""
    r = explore(code, BLOCK0[0], set(NAMES))
    return dict(instructions=r['instructions'], sysops=r['sysops'],
                mmio=[a for a in r['accesses'] if a['region'] == 'mmio'],
                boot_code_stores=[a for a in r['accesses'] if a['address'] == h32(BOOT_CODE_VA)],
                calls=[dict(site=c['site'], target=c['target'], r9=c.get('r9'), args=c['args']) for c in r['calls']],
                sets_sp_or_cpsr=any(('sp,' in s_['insn'] or 'cpsr' in s_['insn']) for s_ in r['sysops']),
                note='No instruction in block 0 writes SP, CPSR or CP15; calls to 0xb4060400 (r9 selector) and to '
                     'addresses in the zero hole are Boot ROM code that the image does not contain.')


BOOT_CODE_CONSUMERS = [
    dict(where='0xb4065410 main -> 0xb4065d04 load_ini(r0=code)', pre_dram=True,
         effect='codes 0 and 2: sector (0x200200+0x2400)>>9 = 0x1022, 8 sectors to 0xb4062400 via ROM service; '
                'code 4: sector 0x2800>>9 = 0x14 via 0xb40654b8; code 5: SPI-NAND reads 0xb4065a28/0xb4065a7c; '
                'other codes: sector 0x12', codes_0_2_differ=False),
    dict(where='0xb4065d7c -> 0xb4065bac storage_read_dispatch(r3=code)', pre_dram=True,
         effect='codes 0 and 2 -> 0xb4065b24 (ROM service r9=4 in 256-sector chunks); 4 -> 0xb40654b8; others -> '
                '0xb4065568', codes_0_2_differ=False),
    dict(where='0xb4066604 dram_caller -> get_boot_code() == 5 and r1 == 0', pre_dram=True,
         effect='SPI-NAND record restore 0xb40663f8; not taken for 0 or 2', codes_0_2_differ=False),
    dict(where='0xb40692a0 adfu_check -> get_boot_code() != 0 (after PMIC status, with ini+0x14 != 0)', pre_dram=True,
         effect='code 0 returns; code 2 runs the GPIO C10/C11 32-bit loopback test (32 x delay_ms(1))',
         codes_0_2_differ=True),
    dict(where='0xb4066748 dram_caller -> 0xb4066588 afi_from_boot_code', pre_dram=False,
         effect='AFI boot_dev 0x20 (code 0) / 0x22 (code 2); after DRAM init', codes_0_2_differ=True),
    dict(where='0xb4065448/0xb406545c main -> load_app / load_uboot(r0=code)', pre_dram=False,
         effect='same storage dispatch as load_ini; after DRAM init', codes_0_2_differ=False),
]


def environment(code, funcs, r0, r2, sysops):
    return dict(
        established_by_firmware=[
            'Block 0 and main execute in A32 (ARM) state: every analysed instruction decodes as A32 and no BX/BLX '
            'to an odd address occurs on the path (decoded).',
            'main clears the loader globals 0xb4070800..0xb407087b (memset, 0xb406540c) before anything else (decoded).',
            'main reloads bootloader.ini (8 sectors) to 0xb4062400 through the Boot ROM service (decoded, executed).',
            'No CP15 instruction runs before DRAM init: SCTLR is read and written (bit 12, I-cache) only by '
            '0xb4065fc0/0xb4065fdc, which main calls after dram_caller returns or on its ADFU exit; '
            'VBAR is written (0xffff0000) only in rom_reentry_adfu 0xb406921c (decoded).',
            'No instruction on the pre-DRAM path writes SP, CPSR or SPSR; no MMU, D-cache or cache maintenance '
            'operation exists in the reachable code (decoded).',
        ],
        inherited_from_boot_rom=[
            'Stack pointer: neither block 0 nor main sets SP; the value is the Boot ROM\'s (unknown). The emulator '
            f'uses 0x{STACK_TOP:08x}; the deepest pre-DRAM stack use measured there is '
            f"{max(r0['result']['stack_depth_bytes'], r2['result']['stack_depth_bytes'])} bytes.",
            'CPU mode, interrupt masks, exception vector base and SCTLR (MMU/caches) at entry: not set before DRAM init, '
            'so inherited (unknown). The emulator starts in SVC mode with IRQ/FIQ masked (0x1d3) - an emulator choice.',
            'SRAM mapping 0xb4060000.. with block 0 at 0xb4060000; the Boot ROM service entry 0xb4060400 and the '
            'code at 0xb4060758 live in the zero hole 0x400..0x1e00 of the image, so they are placed there by the ROM.',
            'Clock tree: HOSC (24 MHz by the delay constant 24 ticks/us and the UART formula 24000000/(8*baud)) and '
            'bus clocks are not programmed before DRAM init except the gates/resets listed in the inventory.',
            'CMU_DEVCLKEN0 bit 7 (SD2 gate in the related S500 tree) - read by block 0, set by the ROM (inferred).',
        ],
        supplied_by_emulator=list(SYNTHETIC_RULES.values()) + [
            f'SRAM 0xb4060000..0xb4093c00 := loader bytes from the image (the ROM-filled hole stays zero)',
            f'boot code word 0xb4064c00 := 0 or 2 (as block 0 would write)', f'SP := 0x{STACK_TOP:08x}'],
        inferred=['The loader expects SRAM to persist between block 0 and main (shared 0xb4064c00 word, AFI at '
                  '0xb4060300) and to be at least 0xb4070880 long (globals).'],
        unknown=['Boot ROM register state at the jump to 0xb4060000 (r0-r12, lr)', 'exception vectors and VBAR',
                 'interrupt controller state', 'whether L2 / caches were left enabled by the ROM',
                 'reset values of every MMIO register read before DRAM init (see seeded reads)'],
        sram_map=[
            dict(range='0xb4060000..0xb4060200', what='loader block 0 (Boot ROM copy); overwritten by rom_reentry_adfu'),
            dict(range='0xb4060300..0xb4060310', what='AFI record (written after DRAM init)'),
            dict(range='0xb4060400..0xb4061e00', what='zero in the image; Boot ROM service code at run time (inferred)'),
            dict(range='0xb4062400..0xb4063400', what='bootloader.ini (reloaded by load_ini; ini+0x1c primary record)'),
            dict(range='0xb4064c00..0xb4064c04', what='boot code word (block 0 -> bootloader.bin)'),
            dict(range='0xb4064c60..0xb4064c78', what='pointer table written by publish_globals 0xb406622c'),
            dict(range='0xb4065400..0xb4093c00', what='bootloader.bin (code, rodata, tables)'),
            dict(range='0xb406ba10..0xb406ba14', what='I2C bus cache (0xffffffff in the image; written by i2c_select)'),
            dict(range='0xb4070800..0xb407087c', what='loader globals (cleared by main): +0 UART handle, +0xc timer '
                                                       'index, +0x10 board index, +0x14/+0x18 ini pointer, +0x1c '
                                                       'bootdev byte, +0x20 DRAM record, +0x2c/+0x30/+0x34 UART '
                                                       'index/pad/baud, +0x4c second record, +0x58 PMIC config, '
                                                       '+0x64 PMIC config copy, +0x70/+0x74/+0x78 alarm/resume flag/'
                                                       'resume vector'),
            dict(range='stack', what='location set by the Boot ROM (unknown)'),
        ],
        executed_sram_writes=dict(code0=r0['sram_written_ranges'], code2=r2['sram_written_ranges']),
        system_instructions=sysops)


EMULATION_AUDIT = [
    dict(item='boot_chain.loader_main(boot_code=...)', status='Supplied state + Stubbed',
         detail='boot code is a parameter (0 and 2 used by boot-path); stubs timer_init, uart_init, board_mfp_init, '
                'pmu_init, adfu_check and the DRAM init with return 0, so none of the code-dependent pre-DRAM '
                'behaviour executes there.'),
    dict(item='dram_complete.Harness(boot_code=0)', status='Supplied state',
         detail='boot_code defaults to 0; run_caller() never passes it, so every committed DRAM-stage run used code 0 '
                'and skipped the GPIO handshake.'),
    dict(item='dram_complete stubs', status='Stubbed',
         detail='uart_init 0xb4066784 and pmu_detect 0xb4069890 are stubbed; delay 0xb40693f8 and printf are stubbed '
                'by ddr_emulate; PMIC accessors 0xb4069610/0xb40696c0 are a register file.'),
    dict(item='dram_complete MMIO oracle', status='Partially modelled',
         detail='non-DDR MMIO reads return the last written value or a reset seed, so GPIO C data reads in the handshake '
                'would return what was written (bit 10 never mirrors bit 11) - that silently models "no loopback".'),
    dict(item='ddr_emulate.Emulation', status='Executed (DRAM routine) / Stubbed (delay)',
         detail='starts at 0xb4065ff8 or the DRAM routine; nothing before the ini copy is executed.'),
    dict(item='predram_analysis.Trace (this tool)', status='Executed + Partially modelled',
         detail='executes main from 0xb4065400 through every pre-DRAM function including timer, UART, board, PMIC '
                'detection/bus selection and the ADFU check; stubs only printf, the Boot ROM read service and the I2C '
                'transaction layer (0xb406ac10/0xb406ac60). Reads follow SYNTHETIC_RULES; stops at 0xb40690b8.'),
]

UNKNOWNS = [
    'Electrical meaning of every PMIC write (no PMIC datasheet for the type-2 device; the vendor kernel driver names '
    'are not established for this board).',
    'Real reset values of the MFP/CMU/GPIO registers the pre-DRAM code read-modify-writes (seeded reads).',
    'Whether GPIO C10/C11 are connected to anything on the RG35XX board, so whether the code-2 loopback test '
    'can ever succeed on a production unit.',
    'Pin assignment of UART3 pad 0: its table entry performs no pin-mux write, so the console pins rely on '
    'register state set elsewhere (ROM or reset default) - not established.',
    'Real elapsed time of the delays (depends on the timer clock actually being 24 MHz).',
    'Whether the Boot ROM leaves the I2C/UART/timer blocks clocked; the loader enables the gates itself.',
]


def tool_versions():
    import capstone
    import unicorn
    return dict(predram_analysis=TOOL_VERSION, capstone=capstone.__version__, unicorn=unicorn.__version__)


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items()}
    if isinstance(o, list):
        return [strip(x) for x in o]
    return o


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('evidence')
    e.add_argument('output', type=Path)
    e.add_argument('--image', action='append', required=True, help='release=path to the expanded image')
    e.add_argument('--reference', default=None)
    e.add_argument('--no-verify', action='store_true', help='skip the whole-image SHA-256 check (not for evidence)')
    g = sub.add_parser('graph')
    g.add_argument('image')
    t = sub.add_parser('trace')
    t.add_argument('image')
    t.add_argument('--boot-code', type=int, default=2)
    t.add_argument('--scenario', default='no-loopback', choices=('no-loopback', 'loopback'))
    a = p.parse_args()
    if a.cmd == 'evidence':
        docs = {}
        for spec in a.image:
            rel, path = spec.split('=', 1)
            docs[rel] = analyse_release(path, rel, verify=not a.no_verify)
        ref = a.reference or list(docs)[0]
        out = evidence(docs, ref)
        a.output.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
        print(f'wrote {a.output}')
    elif a.cmd == 'graph':
        loader, _ = load_image(a.image, verify=False)
        code = Code(loader)
        for k, v in graph_document(code, call_graph(code)).items():
            print(k, v['name'], '<-', ','.join(v['callers']), '->', ','.join(v.get('callees', [])))
    else:
        loader, _ = load_image(a.image, verify=False)
        code = Code(loader)
        funcs = call_graph(code)
        tr, res = run_trace(loader, Disk(a.image), code, funcs, a.boot_code, scenario=a.scenario)
        s = summarise_trace(tr, res)
        print(json.dumps({k: v for k, v in s.items() if k != 'events'}, indent=1))
        for k, n in s['events']:
            print(f'{n:6d}  {k}')


if __name__ == '__main__':
    main()
