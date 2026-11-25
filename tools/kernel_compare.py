#!/usr/bin/env python3
"""Compare two 32-bit ARM kernels by recovered symbols and normalised function bodies.

Inputs are decompressed Images plus "address type name" symbol files (from
kallsyms.py --symbols). Function extents are derived from the next distinct
text-symbol address, so sizes are *upper bounds* that include alignment
padding and any trailing literal pool.

Normalised body hash (A32 only): every 32-bit word is kept except that
  * B/BL immediates (bits 23:0 of a branch encoding) are zeroed, and
  * words that fall inside the kernel virtual range (default 0xc0000000-0xd0000000)
    are replaced by a placeholder, since they are almost always link-time
    pointers in literal pools.
Two functions with equal normalised hashes are very likely the same source
compiled the same way, laid out at different addresses. Unequal hashes do NOT
show different behaviour: compiler version, inlining and configuration all
change code. Results are evidence for triage, not semantic equivalence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

KVA = (0xc0000000, 0xd0000000)


def load_symbols(path):
    syms = []
    for line in path.read_text().splitlines():
        parts = line.split(None, 2)
        if len(parts) != 3:
            raise ValueError('malformed symbol line: ' + line[:80])
        syms.append((int(parts[0], 16), parts[1], parts[2]))
    return syms


def functions(syms, text_base):
    """Map name -> (address, size) for unique global/local text symbols."""
    text = sorted({(a, n) for a, t, n in syms if t in 'tT' and a >= text_base}, key=lambda x: (x[0], x[1]))
    addrs = sorted({a for a, _ in text})
    nxt = {a: b for a, b in zip(addrs, addrs[1:])}
    out, dup = {}, set()
    for a, n in text:
        if n in out:
            dup.add(n)
            continue
        if a in nxt:
            out[n] = (a, nxt[a] - a)
    for n in dup:
        out.pop(n, None)  # ambiguous static names are excluded rather than guessed
    return out, sorted(dup)


def normalised(image, base, addr, size, kva=KVA):
    off = addr - base
    if off < 0 or off + size > len(image) or addr % 4 or size % 4:
        return None
    words = struct.unpack_from(f'<{size // 4}I', image, off)
    h = hashlib.sha256()
    for w in words:
        if (w >> 28) != 0xf and (w & 0x0e000000) == 0x0a000000:
            w &= 0xff000000
        elif kva[0] <= w < kva[1]:
            w = 0xdeadbeef
        h.update(struct.pack('<I', w))
    return h.hexdigest()


SUFFIX = re.compile(r'(\.(isra|constprop|part|clone|lto_priv|cold)\.\d+)+$|\.\d+$')


def base_name(name):
    """Strip GCC clone/local-label suffixes (e.g. foo.isra.3.constprop.7 -> foo)."""
    return SUFFIX.sub('', name)


def compare(img_a, syms_a, img_b, syms_b, base=0xc0008000, names_of_interest=()):
    fa, dup_a = functions(syms_a, base)
    fb, dup_b = functions(syms_b, base)
    common = sorted(set(fa) & set(fb))
    same_size = [n for n in common if fa[n][1] == fb[n][1]]
    same_body = []
    if img_a is not None and img_b is not None:
        for n in same_size:
            ha = normalised(img_a, base, *fa[n]); hb = normalised(img_b, base, *fb[n])
            if ha and ha == hb:
                same_body.append(n)
    result = dict(format_version=1, tool='kernel_compare.py', text_base=hex(base),
                  a_functions=len(fa), b_functions=len(fb), common=len(common),
                  a_only=sorted(set(fa) - set(fb)), b_only=sorted(set(fb) - set(fa)),
                  common_same_size=len(same_size), common_same_normalised_body=len(same_body) if img_a is not None else None,
                  ambiguous_names_excluded=dict(a=len(dup_a), b=len(dup_b)))
    ba = {base_name(n) for n in fa} | {base_name(n) for n in dup_a}
    bb = {base_name(n) for n in fb} | {base_name(n) for n in dup_b}
    result.update(a_only_base_names=sorted(ba - bb), b_only_base_names=sorted(bb - ba),
                  note='a_only/b_only compare exact names; *_base_names strip GCC clone suffixes first')
    if names_of_interest:
        result['names_of_interest'] = {n: dict(in_a=n in fa, in_b=n in fb,
                                             same_size=n in fa and n in fb and fa[n][1] == fb[n][1])
                                       for n in sorted(names_of_interest)}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('image_a', type=Path); p.add_argument('symbols_a', type=Path)
    p.add_argument('image_b', type=Path); p.add_argument('symbols_b', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--base', type=lambda x: int(x, 0), default=0xc0008000, help='virtual address of Image offset 0')
    p.add_argument('--names', type=Path, help='newline-separated function names to report individually')
    a = p.parse_args()
    names = [x.strip() for x in a.names.read_text().splitlines() if x.strip()] if a.names else ()
    r = compare(a.image_a.read_bytes(), load_symbols(a.symbols_a), a.image_b.read_bytes(), load_symbols(a.symbols_b),
                a.base, names)
    r['image_a_sha256'] = hashlib.sha256(a.image_a.read_bytes()).hexdigest()
    r['image_b_sha256'] = hashlib.sha256(a.image_b.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(r, indent=1) + '\n')
    print(json.dumps({k: v for k, v in r.items() if not isinstance(v, (list, dict))}))


if __name__ == '__main__':
    main()
