#!/usr/bin/env python3
"""Map mmio_refs.py accesses onto a published register layout, in program order.

A layout is computed from a C struct made only of ``u32 name;``, ``u32 name[N];``
and nested ``struct other name[N];`` members (enough for vendor register
structs such as U-Boot's Rockchip DesignWare uPCTL/PUBL definitions). Nothing
is preprocessed; unsupported member syntax is an error rather than a guess.

Accessor helpers are declared explicitly, because their argument roles cannot
be inferred safely: ``--write-helper ADDR:VALUE_REG:ADDRESS_REG``,
``--read-helper ADDR:ADDRESS_REG``, ``--set-helper ADDR:ADDRESS_REG:MASK_REG``,
``--clear-helper ADDR:ADDRESS_REG:MASK_REG`` and
``--rmw-helper ADDR:ADDRESS_REG:CLEAR_REG:SET_REG`` (all repeatable). Calls to
other functions stay as ``call:<target>``.

A match between observed offsets and a public layout supports the hypothesis
that the hardware block has that layout; it does not prove IP identity, field
semantics, reset values or that the target silicon matches the other vendor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

MEMBER = re.compile(r'^(?:volatile\s+)?u32\s+(\w+)(?:\[(\d+)\])?;$')
NESTED = re.compile(r'^struct\s+(\w+)\s+(\w+)\[(\d+)\];$')


def struct_layout(source, name, _depth=0):
    if _depth > 4:
        raise ValueError('struct nesting too deep')
    m = re.search(r'struct\s+' + re.escape(name) + r'\s*\{(.*?)\};', source, re.S)
    if not m:
        raise ValueError('struct not found: ' + name)
    layout, off = {}, 0
    for raw in m.group(1).splitlines():
        line = re.sub(r'/\*.*?\*/|//.*', '', raw).strip()
        if not line:
            continue
        mm, mn = MEMBER.match(line), NESTED.match(line)
        if mm:
            n = int(mm.group(2) or 1)
            for i in range(n):
                layout[off + 4 * i] = mm.group(1) + (f'[{i}]' if mm.group(2) else '')
            off += 4 * n
        elif mn:
            sub, size = struct_layout(source, mn.group(1), _depth + 1)
            for i in range(int(mn.group(3))):
                for k, v in sub.items():
                    layout[off + k] = f'{mn.group(2)}[{i}].{v}'
                off += size
        else:
            raise ValueError('unsupported struct member: ' + line)
    return layout, off


def map_accesses(refs, blocks, write_helpers=(), read_helpers=(), set_helpers=(), clear_helpers=(), rmw_helpers=()):
    """blocks: list of (label, base, layout dict, size). Helper tuples start with the callee address."""
    roles = {}
    for addr, value_reg, addr_reg in write_helpers:
        roles[addr] = ('write', addr_reg, {'value': value_reg})
    for addr, addr_reg in read_helpers:
        roles[addr] = ('read', addr_reg, {})
    for addr, addr_reg, mask_reg in set_helpers:
        roles[addr] = ('set-bits', addr_reg, {'mask': mask_reg})
    for addr, addr_reg, mask_reg in clear_helpers:
        roles[addr] = ('clear-bits', addr_reg, {'mask': mask_reg})
    for addr, addr_reg, clear_reg, set_reg in rmw_helpers:
        roles[addr] = ('read-modify-write', addr_reg, {'clear': clear_reg, 'set': set_reg})
    out = []
    for a in sorted(refs['accesses'], key=lambda x: (x['offset'], x.get('argument', ''))):
        p = a['physical']
        blk = next(((lbl, base, lay) for lbl, base, lay, size in blocks if base <= p < base + size), None)
        if not blk:
            continue
        lbl, base, lay = blk
        op, operands = a['access'], {}
        if a.get('value') is not None:
            operands['value'] = a['value']
        if op == 'call-arg':
            callee = a.get('callee')
            role = roles.get(callee)
            if role and a['argument'] == role[1]:
                op = role[0]
                operands = {k: a['other_constant_args'][r] for k, r in role[2].items() if r in a['other_constant_args']}
            else:
                op = 'call:' + (hex(callee) if callee is not None else 'indirect')
        entry = dict(offset=a['offset'], block=lbl, register_offset=p - base,
                     register=lay.get(p - base), operation=op)
        entry.update({k: f'0x{v:x}' for k, v in operands.items()})
        out.append(entry)
    named = sum(1 for e in out if e['register'])
    return dict(format_version=1, tool='map_accesses.py', component_sha256=refs['component_sha256'],
                accesses=len(out), named=named, unnamed=len(out) - named, sequence=out)


def _addr_spec(text, parts):
    xs = text.split(':')
    if len(xs) != parts:
        raise argparse.ArgumentTypeError('bad helper specification')
    return (int(xs[0], 0), *xs[1:])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('refs', type=Path, help='mmio_refs.py output')
    p.add_argument('output', type=Path)
    p.add_argument('--block', action='append', required=True, metavar='LABEL:BASE:HEADER:STRUCT[:SPAN]',
                   help='SPAN (bytes) widens the matched window past the struct so out-of-layout accesses are reported, not dropped')
    p.add_argument('--write-helper', action='append', default=[], type=lambda t: _addr_spec(t, 3))
    p.add_argument('--read-helper', action='append', default=[], type=lambda t: _addr_spec(t, 2))
    p.add_argument('--set-helper', action='append', default=[], type=lambda t: _addr_spec(t, 3))
    p.add_argument('--clear-helper', action='append', default=[], type=lambda t: _addr_spec(t, 3))
    p.add_argument('--rmw-helper', action='append', default=[], type=lambda t: _addr_spec(t, 4))
    a = p.parse_args()
    blocks, provenance = [], []
    for spec in a.block:
        parts = spec.split(':')
        if len(parts) not in (4, 5):
            raise SystemExit('bad --block specification: ' + spec)
        label, base, header, struct = parts[:4]
        text = Path(header).read_text()
        lay, size = struct_layout(text, struct)
        span = max(size, int(parts[4], 0)) if len(parts) == 5 else size
        blocks.append((label, int(base, 0), lay, span))
        provenance.append(dict(label=label, base=base, struct=struct, header_sha256=hashlib.sha256(text.encode()).hexdigest(),
                               layout_bytes=size, matched_span=span))
    r = map_accesses(json.loads(a.refs.read_text()), blocks, a.write_helper, a.read_helper, a.set_helper,
                     a.clear_helper, a.rmw_helper)
    r['layouts'] = provenance
    a.output.write_text(json.dumps(r, indent=1) + '\n')
    print(f"{r['named']}/{r['accesses']} accesses named")


if __name__ == '__main__':
    main()
