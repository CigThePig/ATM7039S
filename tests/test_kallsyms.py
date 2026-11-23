from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import kallsyms  # noqa: E402

# Token 0..25 are letters, 26 is '_', the rest are two-character fillers.
TOKENS = [chr(97 + i) for i in range(26)] + ['_'] + [f'q{i:03d}' for i in range(229)]
TYPES = {'T': 200, 't': 201, 'D': 202}
for k, v in TYPES.items():
    TOKENS[v] = k


def encode(type_, name):
    idx = [TYPES[type_]] + [TOKENS.index(c) for c in name]
    return bytes([len(idx)] + idx)


def image(symbols, pad_names=True):
    """Build a 3.x-style absolute-address kallsyms block inside filler bytes."""
    n = len(symbols)
    blob = bytearray(b'\xaa' * 256)
    blob += b''.join(struct.pack('<I', a) for a, _, _ in symbols)
    blob += struct.pack('<I', n)
    if pad_names:
        while len(blob) % 16:
            blob += b'\0'
    for a, t, name in symbols:
        blob += encode(t, name)
    while len(blob) % 16:
        blob += b'\0'
    blob += struct.pack('<I', 0)          # markers
    while len(blob) % 16:
        blob += b'\0'
    table = len(blob)
    offsets = []
    for tok in TOKENS:
        offsets.append(len(blob) - table)
        blob += tok.encode() + b'\0'
    while len(blob) % 16:
        blob += b'\0'
    blob += struct.pack('<256H', *offsets)
    blob += b'\xbb' * 256
    return bytes(blob)


SYMS = [(0xc0008000 + 4 * i, 'T' if i % 3 else 't', name) for i, name in enumerate(
    ['stext', 'start_kernel', 'owl_smp_init_cpus', 'cpu_up', 'scu_get_core_count'] * 400)]


class KallsymsTests(unittest.TestCase):
    def test_roundtrip(self):
        r = kallsyms.extract(image(SYMS))
        self.assertEqual(r['num_syms'], len(SYMS))
        self.assertEqual([(s['address'], s['type'], s['name']) for s in r['symbols']], SYMS)

    def test_unpadded_names(self):
        r = kallsyms.extract(image(SYMS, pad_names=False))
        self.assertEqual(r['symbols'][2]['name'], 'owl_smp_init_cpus')

    def test_missing_table(self):
        with self.assertRaisesRegex(ValueError, 'token index'):
            kallsyms.extract(b'\x11' * 4096)

    def test_unsorted_addresses_rejected(self):
        bad = [(0xc0009000 - 4 * i, t, n) for i, (_, t, n) in enumerate(SYMS)]
        with self.assertRaisesRegex(ValueError, 'num_syms'):
            kallsyms.extract(image(bad))

    def test_summary_is_order_independent(self):
        data = image(SYMS)
        s = kallsyms.summarise(kallsyms.extract(data), data)
        self.assertEqual(s['num_syms'], len(SYMS))
        self.assertRegex(s['name_set_sha256'], '^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
