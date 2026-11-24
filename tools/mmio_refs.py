#!/usr/bin/env python3
"""Static MMIO access discovery for 32-bit ARM components (Capstone; nothing executed).

A linear sweep with intentionally simple constant propagation: register values
are tracked only through MOV/MVN/MOVW/MOVT, PC-relative literal loads and
ADD/SUB/ORR/BIC/EOR/LSL with immediates. Knowledge is discarded at every
branch target, after unconditional control transfer, and for caller-saved
registers after calls. A load/store whose base register is a known constant
is reported when its effective address translates into the MMIO window.

Coordinates are explicit and never mixed:
  offset   component-relative file offset of the instruction
  address  load-address view (``--load`` + offset); an assumption the caller supplies
  target   CPU-visible effective address computed by the instruction
  physical ``target`` after optional ``--io-map VIRT:PHYS:SIZE`` translation

Results are *candidate* register references.  A constant-propagation result is
static dataflow evidence, not proof that a path executes, and code/data
separation is only as good as the supplied ranges or function list.
"""
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import struct

LIMIT = 64 * 1024 * 1024
DEFAULT_WINDOW = (0xB0000000, 0xB8000000)
CALL_CLOBBER = ('r0', 'r1', 'r2', 'r3', 'r12', 'ip', 'lr')  # Capstone names r12 'ip'


def parse_int(text):
    return int(text, 0)


def parse_range(text):
    lo, hi = (parse_int(x) for x in text.split(':'))
    if not 0 <= lo < hi:
        raise argparse.ArgumentTypeError('range must be start:end with start<end')
    return lo, hi


def parse_iomap(text):
    virt, phys, size = (parse_int(x) for x in text.split(':'))
    if size <= 0 or virt < 0 or phys < 0 or virt + size > 1 << 32 or phys + size > 1 << 32:
        raise argparse.ArgumentTypeError('io-map must be VIRT:PHYS:SIZE within 32 bits')
    return virt, phys, size


class RegisterMap:
    """Exact-address lookups against registers/canonical/hardware.json."""

    def __init__(self, model=None):
        self.exact = {}
        self.blocks = []
        if not model:
            return
        for block in model['blocks']:
            for reg in block['registers']:
                self.exact.setdefault(block['base'] + reg['offset'], []).append(reg['name'])
            if block.get('size'):
                self.blocks.append((block['base'], block['base'] + block['size'], block['id']))
        self.blocks.sort()

    def describe(self, address):
        names = sorted(set(self.exact.get(address, [])))
        blocks = sorted({b for lo, hi, b in self.blocks if lo <= address < hi})
        result = dict(register_names=names, declared_blocks=blocks)
        if len(names) > 1:
            result['ambiguous'] = True
        return result


def _imm(op):
    from capstone import arm
    return op.imm if op.type == arm.ARM_OP_IMM else None


def translate(target, iomap):
    if not iomap:
        return target
    for virt, phys, size in iomap:
        if virt <= target < virt + size:
            return phys + (target - virt)
    return None


def scan(data, load, ranges, thumb=False, window=DEFAULT_WINDOW, iomap=(), entries=(), regmap=None):
    """Return a deterministic list of MMIO candidate accesses."""
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, CS_GRP_JUMP, CS_GRP_CALL, CS_GRP_RET, arm
    if len(data) > LIMIT:
        raise ValueError('component exceeds 64 MiB')
    if load % 2 or (not thumb and load % 4):
        raise ValueError('load address misaligned for instruction set')
    if load + len(data) > 1 << 32:
        raise ValueError('component does not fit the 32-bit address space at this load address')
    for lo, hi in ranges:
        if hi > len(data) or (not thumb and (lo % 4 or hi % 4)):
            raise ValueError('scan range outside component or misaligned')
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB if thumb else CS_MODE_ARM)
    md.detail = True
    regmap = regmap or RegisterMap()
    def stream():
        """Yield instructions range by range without retaining them (bounded memory)."""
        for lo, hi in ranges:
            pos = lo
            while pos < hi:
                got = False
                for ins in md.disasm(data[pos:min(hi, pos + 0x10000)], load + pos):
                    pos = ins.address - load + ins.size
                    got = True
                    yield ins
                if not got or pos < hi and (pos - lo) % 0x10000:
                    # Undecodable word (data in code): skip and resynchronise.
                    if not got:
                        pos += 2 if thumb else 4

    # Pass 1: branch targets break dataflow (incoming state is unknown there).
    targets = set(entries)
    if thumb:
        lite = Cs(CS_ARCH_ARM, CS_MODE_THUMB); lite.detail = True
        md, keep = lite, md
        for ins in stream():
            if (ins.group(CS_GRP_JUMP) or ins.group(CS_GRP_CALL)) and ins.operands and ins.operands[0].type == arm.ARM_OP_IMM:
                targets.add(ins.operands[0].imm)
        md = keep
    else:
        for lo, hi in ranges:
            for off in range(lo, hi, 4):
                w = struct.unpack_from('<I', data, off)[0]
                if w & 0x0e000000 == 0x0a000000:
                    imm = w & 0xffffff
                    imm = imm - (1 << 24) if imm & 0x800000 else imm
                    t = load + off + 8 + 4 * imm
                    targets.add(t + (2 if w >> 28 == 15 and w & (1 << 24) else 0))
    results = []
    state = {}
    prev_end = None
    for ins in stream():
        if ins.address in targets or ins.address != prev_end:
            state = {}
        prev_end = ins.address + ins.size
        ops = ins.operands
        name = ins.mnemonic.split('.')[0]
        cond = ins.cc not in (arm.ARM_CC_AL, arm.ARM_CC_INVALID)
        regs = lambda i: ins.reg_name(ops[i].reg) if i < len(ops) and ops[i].type == arm.ARM_OP_REG else None
        pc = ins.address + (4 if thumb else 8)
        # ----- memory accesses -----
        if name.startswith(('ldr', 'str')) and len(ops) >= 2 and ops[-1].type == arm.ARM_OP_MEM:
            mem = ops[-1].mem
            base = ins.reg_name(mem.base) if mem.base else None
            rt = regs(0)
            width = 8 if name[3:4] == 'b' or name.startswith(('ldrsb', 'strb')) else \
                16 if name[3:4] == 'h' or name.startswith('ldrsh') else 64 if name[3:4] == 'd' else 32
            addr = None
            if base == 'pc' and mem.index == 0:
                lit = (pc & ~3) + mem.disp
                off = lit - load
                if 0 <= off <= len(data) - 4 and name == 'ldr' and rt != 'pc':
                    state[rt] = struct.unpack_from('<I', data, off)[0]
                    continue
            elif base in state and mem.index == 0 and len(ops) == 2 and not ins.writeback:
                addr = (state[base] + mem.disp) & 0xffffffff
            if addr is not None:
                phys = translate(addr, iomap)
                if phys is not None and window[0] <= phys < window[1]:
                    entry = dict(offset=ins.address - load, address=ins.address, target=addr, physical=phys,
                                 access='write' if name.startswith('str') else 'read', width=width,
                                 conditional=cond, instruction=f'{ins.mnemonic} {ins.op_str}')
                    if entry['access'] == 'write' and rt in state:
                        entry['value'] = state[rt]
                    entry.update(regmap.describe(phys))
                    results.append(entry)
            if name.startswith('ldr'):
                # Every register a load writes (two for ldrd) loses its known value.
                for r in [rt] + [ins.reg_name(x) for x in ins.regs_access()[1]]:
                    if r:
                        state.pop(r, None)
            if ins.writeback and base:
                state.pop(base, None)
            if rt == 'pc':
                state = {}
            continue
        # ----- dataflow -----
        dst = regs(0)
        new = None
        if name in ('mov', 'movw', 'mvn', 'movs', 'mvns') and len(ops) == 2:
            if ops[1].type == arm.ARM_OP_IMM:
                new = ops[1].imm & 0xffffffff
                if name.startswith('mvn'):
                    new = ~new & 0xffffffff
            elif regs(1) in state and name.startswith('mov') and not ops[1].shift.type:
                new = state[regs(1)]
        elif name == 'movt' and dst in state and ops[1].type == arm.ARM_OP_IMM:
            new = (state[dst] & 0xffff) | ((ops[1].imm & 0xffff) << 16)
        elif name in ('add', 'sub', 'orr', 'bic', 'eor', 'lsl', 'adds', 'subs', 'orrs', 'bics', 'lsls') \
                and len(ops) == 3 and ops[2].type == arm.ARM_OP_IMM and regs(1) in state:
            a, b = state[regs(1)], ops[2].imm & 0xffffffff
            op = name.rstrip('s') if name not in ('bics',) else 'bic'
            new = {'add': a + b, 'sub': a - b, 'orr': a | b, 'bic': a & ~b, 'eor': a ^ b,
                   'lsl': a << (b & 31)}[op] & 0xffffffff
        elif name in ('add', 'sub') and len(ops) == 3 and regs(1) == 'pc' and ops[2].type == arm.ARM_OP_IMM:
            new = ((pc & ~3) + (ops[2].imm if name == 'add' else -ops[2].imm)) & 0xffffffff
        if ins.group(CS_GRP_CALL):
            # Accessor helpers (e.g. writel(val, addr)) receive register addresses as
            # arguments; record window constants in r0-r3 with the callee and the
            # other constant arguments. Role (address vs value) is NOT inferred.
            callee = ops[0].imm & 0xffffffff if ops and ops[0].type == arm.ARM_OP_IMM else None
            args = {r: state[r] for r in ('r0', 'r1', 'r2', 'r3') if r in state}
            for r, v in sorted(args.items()):
                phys = translate(v, iomap)
                if phys is not None and window[0] <= phys < window[1]:
                    entry = dict(offset=ins.address - load, address=ins.address, target=v, physical=phys,
                                 access='call-arg', argument=r, callee=callee, conditional=cond,
                                 other_constant_args={k: x for k, x in sorted(args.items()) if k != r},
                                 instruction=f'{ins.mnemonic} {ins.op_str}')
                    entry.update(regmap.describe(phys))
                    results.append(entry)
            for r in CALL_CLOBBER:
                state.pop(r, None)
            continue
        if ins.group(CS_GRP_JUMP) or ins.group(CS_GRP_RET) or 'pc' in (dst,):
            if not cond:
                state = {}
            continue
        if name.startswith(('pop', 'ldm', 'stm', 'push')):
            # Loaded registers, a written-back base and sp lose their known values;
            # loading pc is a control transfer.
            written = {ins.reg_name(r) for r in ins.regs_access()[1]}
            if name.startswith(('pop', 'ldm')):
                written |= {ins.reg_name(o.reg) for o in ops if o.type == arm.ARM_OP_REG}
            if ins.writeback and ops and ops[0].type == arm.ARM_OP_REG:
                written.add(ins.reg_name(ops[0].reg))
            if 'pc' in written and not cond:
                state = {}
            for r in written:
                state.pop(r, None)
            continue
        # Any other written register becomes unknown. Conditional writes poison as well.
        written = [ins.reg_name(r) for r in ins.regs_access()[1]]
        for r in written:
            state.pop(r, None)
        if new is not None and dst and not cond:
            state[dst] = new
    return results


def summarise(accesses):
    by = {}
    for a in accesses:
        s = by.setdefault(a['physical'], dict(physical=a['physical'], reads=0, writes=0, call_args=0, values=set(),
                                              register_names=a.get('register_names', []),
                                              declared_blocks=a.get('declared_blocks', [])))
        s[{'read': 'reads', 'write': 'writes', 'call-arg': 'call_args'}[a['access']]] += 1
        if 'value' in a:
            s['values'].add(a['value'])
    out = []
    for k in sorted(by):
        s = by[k]
        s['values'] = sorted(s['values'])
        out.append(s)
    return out


def run(path, load, ranges, thumb=False, window=DEFAULT_WINDOW, iomap=(), functions=None, model=None):
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise ValueError('expected regular component no larger than 64 MiB')
    data = path.read_bytes()
    entries = []
    if functions:
        entries = sorted({f['address'] for f in functions})
    ranges = ranges or [(0, len(data) - len(data) % 4)]
    acc = scan(data, load, ranges, thumb, window, iomap, entries, RegisterMap(model))
    return dict(format_version=1, tool='mmio_refs.py', component_sha256=hashlib.sha256(data).hexdigest(),
                component_size=len(data), load_address=load, instruction_set='T32' if thumb else 'A32',
                ranges=[list(r) for r in ranges], window=list(window), io_map=[list(m) for m in iomap],
                coordinate_note='offset=file offset; address=load+offset (assumed); physical=translated target',
                accesses=acc, summary=summarise(acc))


def nearest_function(functions, address):
    if not functions:
        return None
    starts = [f['address'] for f in functions]
    i = bisect.bisect_right(starts, address) - 1
    if i < 0:
        return None
    f = functions[i]
    if f.get('size') and address >= f['address'] + f['size']:
        return None
    return f['name']


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('component', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--load', type=parse_int, required=True, help='address of file offset 0 (assumption)')
    p.add_argument('--range', type=parse_range, action='append', default=[], help='file-offset start:end; repeatable')
    p.add_argument('--thumb', action='store_true')
    p.add_argument('--window', type=parse_range, default=DEFAULT_WINDOW, help='physical start:end')
    p.add_argument('--io-map', type=parse_iomap, action='append', default=[])
    p.add_argument('--functions', type=Path, help='JSON list of {address,name,size?} (e.g. from kallsyms)')
    p.add_argument('--register-model', type=Path, default=Path(__file__).resolve().parents[1] / 'registers/canonical/hardware.json')
    a = p.parse_args()
    functions = json.loads(a.functions.read_text()) if a.functions else None
    if functions:
        functions = sorted(functions, key=lambda f: f['address'])
    model = json.loads(a.register_model.read_text()) if a.register_model and a.register_model.exists() else None
    result = run(a.component, a.load, a.range, a.thumb, a.window, a.io_map, functions, model)
    if functions:
        for x in result['accesses']:
            x['function'] = nearest_function(functions, x['address'])
    a.output.write_text(json.dumps(result, indent=1) + '\n')


if __name__ == '__main__':
    main()
