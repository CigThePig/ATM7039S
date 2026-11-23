#!/usr/bin/env python3
"""Recover the kallsyms symbol table from a decompressed 32-bit ARM Linux Image.

Targets the absolute-address layout used by 3.x kernels (kallsyms_addresses,
kallsyms_num_syms, kallsyms_names, kallsyms_markers, kallsyms_token_table,
kallsyms_token_index). The input is read as bytes only; nothing is executed.
Validate against a System.map from a build of the same layout before relying on
the output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

LIMIT = 64 * 1024 * 1024


def find_token_table(data):
    """Return (token_table_offset, token_index_offset, tokens)."""
    n = len(data)
    for p in range(0, n - 512, 2):
        if data[p] or data[p + 1]:
            continue
        idx = struct.unpack_from('<256H', data, p)
        if idx[1] == 0 or any(idx[i] >= idx[i + 1] for i in range(255)) or idx[255] > 0x1000:
            continue
        # Direct solve: try each table start that satisfies all NUL positions.
        lo = max(0, p - idx[255] - 80)
        for t in range(p - idx[255] - 2, lo, -1):
            if all(data[t + idx[i] - 1] == 0 for i in range(1, 256)) and data[t + idx[255]:p].find(b'\0') >= 1:
                tokens = []
                for i in range(256):
                    end = data.index(b'\0', t + idx[i])
                    tokens.append(data[t + idx[i]:end].decode('latin1'))
                if all(tokens):
                    return t, p, tokens
    raise ValueError('kallsyms token index not found')


def find_num_syms(data, before, lo_addr=0xc0000000, hi_addr=0xd0000000):
    """Find kallsyms_num_syms by its preceding sorted address array."""
    for q in range(before - 4, max(0, before - 32 * 1024 * 1024), -4):
        n = struct.unpack_from('<I', data, q)[0]
        if not 1000 <= n <= 400000 or q - 4 * n < 0:
            continue
        a = q - 4 * n
        # Allow alignment padding between the address array and num_syms.
        for pad in (0, 4, 8, 12):
            start = a - pad
            if start < 0:
                continue
            head = struct.unpack_from('<64I', data, start)
            tail = struct.unpack_from('<64I', data, start + 4 * (n - 64))
            if all(lo_addr <= x < hi_addr for x in head + tail) and list(head) == sorted(head) and list(tail) == sorted(tail):
                addrs = struct.unpack_from(f'<{n}I', data, start)
                if all(addrs[i] <= addrs[i + 1] for i in range(n - 1)):
                    return q, n, addrs
    raise ValueError('kallsyms_num_syms not found')


def extract(data):
    if len(data) > LIMIT:
        raise ValueError('image exceeds 64 MiB')
    table, index, tokens = find_token_table(data)
    q, n, addrs = find_num_syms(data, table)
    # The kallsyms generator aligns each table; skip zero padding to the next 16-byte boundary.
    p = q + 4
    aligned = (p + 15) & ~15
    if not any(data[p:aligned]):
        p = aligned
    symbols = []
    for i in range(n):
        length = data[p]
        if p + 1 + length > table:
            raise ValueError('kallsyms names overrun')
        name = ''.join(tokens[b] for b in data[p + 1:p + 1 + length])
        p += 1 + length
        symbols.append(dict(address=addrs[i], type=name[:1], name=name[1:]))
    return dict(token_table_offset=table, token_index_offset=index, num_syms_offset=q, num_syms=n,
                names_end=p, symbols=symbols)


def summarise(result, image):
    syms = result['symbols']
    names = sorted({(s['type'].lower(), s['name']) for s in syms})
    digest = hashlib.sha256('\n'.join(f'{t} {n}' for t, n in names).encode()).hexdigest()
    return dict(image_sha256=hashlib.sha256(image).hexdigest(), num_syms=result['num_syms'],
                offsets={k: result[k] for k in ('token_table_offset', 'token_index_offset', 'num_syms_offset')},
                text_start=min((s['address'] for s in syms if s['name'] == '_text'), default=None),
                name_set_sha256=digest)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--symbols', type=Path, help='also write "address type name" lines')
    a = p.parse_args()
    data = a.image.read_bytes()
    result = extract(data)
    a.output.write_text(json.dumps(summarise(result, data), indent=2) + '\n')
    if a.symbols:
        a.symbols.write_text(''.join(f"{s['address']:08x} {s['type']} {s['name']}\n" for s in result['symbols']))


if __name__ == '__main__':
    main()
