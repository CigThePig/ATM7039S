#!/usr/bin/env python3
"""Bounded ARM A32 immediate-branch and PC-literal inventory (not a disassembler).

Code/data and entry points must be established separately. No Thumb decoding,
control-flow recovery, execution, peripheral semantics, or load-base inference.
Offsets and branch targets are component-relative, not memory addresses.
"""
import argparse
import json
from pathlib import Path
import struct
import research as r


def inventory(data, start, end):
    if start < 0 or start % 4 or end % 4 or not start < end <= len(data):
        raise ValueError('range must be aligned and within component')
    refs = []
    for off in range(start, end, 4):
        word = struct.unpack_from('<I', data, off)[0]
        cond = word >> 28
        # Exclude unconditional-extension encodings such as BLX immediate.
        if cond == 15:
            continue
        if word & 0x0e000000 == 0x0a000000:
            imm = word & 0xffffff
            if imm & 0x800000:
                imm -= 1 << 24
            target = off + 8 + 4*imm
            refs.append(dict(offset=off, kind='branch-link' if word & (1 << 24) else 'branch',
                             condition=cond, target_offset=target,
                             target_in_component=0 <= target < len(data)))
        # LDR Rt,[PC,+/-imm12], preindexed, word, no writeback.
        if word & 0x0f7f0000 == 0x051f0000:
            addr = off+8 + ((word & 0xfff) if word & (1 << 23) else -(word & 0xfff))
            entry = dict(offset=off, kind='literal-load', condition=cond,
                         register=(word >> 12) & 15, literal_offset=addr)
            if 0 <= addr <= len(data)-4:
                entry['value'] = struct.unpack_from('<I', data, addr)[0]
            else:
                entry['error'] = 'literal outside component'
            refs.append(entry)
    return dict(size=len(data), sha256=r.sha(data), range_start=start, range_end=end,
                coordinate_space='component-relative bytes; A32 PC=instruction+8', references=refs)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--start', type=lambda x:int(x,0), required=True)
    p.add_argument('--end', type=lambda x:int(x,0), required=True)
    a = p.parse_args()
    if not a.input.is_file() or a.input.stat().st_size > 32*1024*1024:
        raise ValueError('expected regular component <=32 MiB')
    a.output.write_text(json.dumps(inventory(a.input.read_bytes(),a.start,a.end),indent=2)+'\n')
