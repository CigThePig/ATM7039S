"""Tests for tools/boot_chain.py.

Synthetic tests hand-encode small A32 programs, so they need Capstone and Unicorn
(requirements-firmware.txt) but no firmware. Evidence tests check the committed
stock-boot-chain.json for internal and cross-file consistency. Firmware-backed
tests run only when ATM_FIRMWARE_DIR holds the pinned images (stock-230309.img,
...); they re-derive the evidence and compare it with the committed file.
"""
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

try:
    import importlib.util
    HAVE_ARM = all(importlib.util.find_spec(m) for m in ('capstone', 'unicorn'))
except ImportError:
    HAVE_ARM = False

import boot_chain as bc

EVIDENCE = ROOT / 'evidence/firmware/stock-boot-chain.json'


# ---------------------------------------------------------------- A32 encoders (subset)

def mov(rd, imm):
    return 0xE3A00000 | rd << 12 | imm


def movne(rd, imm):
    return 0x13A00000 | rd << 12 | imm


def ldr_lit(rd, pc, lit):
    off = lit - (pc + 8)
    assert 0 <= off < 0x1000
    return 0xE59F0000 | rd << 12 | off


def bl(pc, target):
    return 0xEB000000 | ((target - (pc + 8)) >> 2) & 0xFFFFFF


def beq(pc, target):
    return 0x0A000000 | ((target - (pc + 8)) >> 2) & 0xFFFFFF


PUSH = 0xE92D4010   # push {r4, lr}
POP = 0xE8BD8010    # pop {r4, pc}
BXLR = 0xE12FFF1E
MOV_R1_R0 = 0xE1A01000
CMP_R0_1 = 0xE3500001
CMP_R2_R1 = 0xE1520001
LDR_R2_R3 = 0xE5932000      # ldr r2, [r3]
LDRBEQ_R0_R3_4 = 0x05D30004  # ldrbeq r0, [r3, #4]


class Program:
    """Tiny assembler: words at increasing addresses, labels resolved in a second pass."""

    def __init__(self, base):
        self.base, self.items, self.labels = base, [], {}

    def here(self):
        return self.base + 4 * len(self.items)

    def label(self, name):
        self.labels[name] = self.here()

    def emit(self, w):
        self.items.append(w)

    def later(self, fn):
        self.items.append(fn)

    def data(self, raw):
        raw = raw + b'\0' * (-len(raw) % 4)
        for i in range(0, len(raw), 4):
            self.items.append(struct.unpack_from('<I', raw, i)[0])

    def build(self):
        out = bytearray()
        for k, it in enumerate(self.items):
            pc = self.base + 4 * k
            out += struct.pack('<I', it(pc) if callable(it) else it)
        return bytes(out)


def synthetic_uboot():
    """A check_boot_flag-shaped function plus getter, printf and setenv stubs at 0x05000040."""
    p = Program(0x05000040)
    L = p.labels
    p.emit(0)                      # padding so the function is not at the image base
    p.label('cbf')
    p.emit(PUSH)
    p.later(lambda pc: bl(pc, L['getmode']))
    p.emit(MOV_R1_R0)
    p.later(lambda pc: ldr_lit(0, pc, L['lit_fmt']))
    p.later(lambda pc: bl(pc, L['printf']))
    p.later(lambda pc: bl(pc, L['getmode']))
    p.emit(CMP_R0_1)
    p.later(lambda pc: beq(pc, L['produce']))
    p.later(lambda pc: ldr_lit(0, pc, L['lit_bootcmd']))
    p.later(lambda pc: ldr_lit(1, pc, L['lit_mmc']))
    p.later(lambda pc: bl(pc, L['setenv']))
    p.emit(mov(0, 0))
    p.emit(POP)
    p.label('produce')
    p.later(lambda pc: ldr_lit(0, pc, L['lit_bootcmd']))
    p.later(lambda pc: ldr_lit(1, pc, L['lit_ram']))
    p.later(lambda pc: bl(pc, L['setenv']))
    p.emit(mov(0, 0))
    p.emit(POP)
    for name in ('lit_fmt', 'lit_bootcmd', 'lit_mmc', 'lit_ram'):
        p.label(name)
        p.later(lambda pc, n=name: L['s_' + n[4:]])
    p.label('getmode')             # AFI getter: 1 (PRODUCE) unless "AFI" magic is present
    p.later(lambda pc: ldr_lit(3, pc, L['lit_afi']))
    p.emit(LDR_R2_R3)
    p.later(lambda pc: ldr_lit(1, pc, L['lit_magic']))
    p.emit(CMP_R2_R1)
    p.emit(movne(0, 1))
    p.emit(LDRBEQ_R0_R3_4)
    p.emit(BXLR)
    p.label('lit_afi')
    p.emit(0xB4060300)
    p.label('lit_magic')
    p.emit(0x00494641)
    p.label('printf')
    p.emit(PUSH)
    p.emit(POP)
    p.label('setenv')
    p.emit(PUSH)
    p.emit(POP)
    p.label('table')
    for _ in range(3):
        p.later(lambda pc: L['printf'])
    p.later(lambda pc: L['cbf'])
    p.later(lambda pc: L['setenv'])
    p.emit(0)
    for name, text in (('s_fmt', b'bootmode = %d\n'), ('s_bootcmd', b'bootcmd'), ('s_mmc', b'run mmcboot'),
                       ('s_ram', b'run ramboot')):
        p.label(name)
        p.data(text + b'\0')
    p.build()  # resolve labels used in string literals
    return p.build(), dict(p.labels)


def mini_fdt(nodes):
    """Build a v17 FDT from [(depth, name, {prop: bytes})] in pre-order."""
    strings, struct_b = bytearray(), bytearray()
    offs = {}

    def soff(n):
        if n not in offs:
            offs[n] = len(strings)
            strings.extend(n.encode() + b'\0')
        return offs[n]
    depth_stack = []
    for depth, name, props in nodes:
        while depth_stack and depth_stack[-1] >= depth:
            struct_b += struct.pack('>I', 2)
            depth_stack.pop()
        nm = name.encode() + b'\0'
        struct_b += struct.pack('>I', 1) + nm + b'\0' * (-len(nm) % 4)
        for k, v in props.items():
            struct_b += struct.pack('>III', 3, len(v), soff(k)) + v + b'\0' * (-len(v) % 4)
        depth_stack.append(depth)
    while depth_stack:
        struct_b += struct.pack('>I', 2)
        depth_stack.pop()
    struct_b += struct.pack('>I', 9)
    rsv = bytes(16)
    hdr_len = 40
    off_rsv = hdr_len
    off_struct = off_rsv + len(rsv)
    off_strings = off_struct + len(struct_b)
    total = off_strings + len(strings)
    hdr = struct.pack('>10I', bc.FDT_MAGIC, total, off_struct, off_strings, off_rsv, 17, 16, 0, len(strings),
                      len(struct_b))
    return hdr + rsv + bytes(struct_b) + bytes(strings)


def uimage(payload, load=0x8000, ep=0x8000, typ=2, name=b'Linux'):
    h = bytearray(struct.pack('>7I4B', bc.UIMAGE_MAGIC, 0, 0, len(payload), load, ep, zlib.crc32(payload), 5, 2,
                              typ, 0) + name.ljust(32, b'\0'))
    struct.pack_into('>I', h, 4, zlib.crc32(bytes(h)))
    return bytes(h) + payload


class Parsers(unittest.TestCase):
    def test_uenv_import_semantics(self):
        env = bc.parse_uenv('uenvcmd=setenv os_type linux;\r\n# c\nbootargs=a b\nbootargs=c=d\n\nbad\n')
        self.assertEqual(env, {'uenvcmd': 'setenv os_type linux;', 'bootargs': 'c=d'})

    def test_uimage_header_and_crc(self):
        img = uimage(b'\x01' * 100, load=0x2000000, ep=0x2000000, typ=3)
        info = bc.uimage_info(img)
        self.assertTrue(info['magic_ok'] and info['header_crc_ok'] and info['data_crc_ok'])
        self.assertEqual((info['load'], info['type'], info['size']), ('0x2000000', 3, 100))
        bad = bytearray(img)
        bad[70] ^= 1
        self.assertFalse(bc.uimage_info(bytes(bad))['data_crc_ok'])
        bad = bytearray(img)
        bad[12] ^= 1
        self.assertFalse(bc.uimage_info(bytes(bad))['header_crc_ok'])

    def test_decode_afi(self):
        a = bc.decode_afi(bc.afi_bytes(0, 0x20, 3, 0, 115200, 256 << 20))
        self.assertEqual(a, dict(magic='AFI', boot_mode=0, boot_dev='0x20', uart_index=3, uart_pad=0,
                                 uart_baudrate=115200, ddr_size='0x10000000'))

    def test_fdt_walker(self):
        fdt = mini_fdt([(0, '', {'model': b'Test board\0'}), (1, 'chosen', {'bootargs': b'a b\0'}),
                        (1, 'memory', {'reg': struct.pack('>II', 0, 0x10000000)}), (2, 'sub', {})])
        nodes = dict(bc._fdt_nodes(fdt))
        self.assertEqual(nodes['/']['model'], 'Test board')
        self.assertEqual(nodes['/chosen']['bootargs'], 'a b')
        self.assertEqual(nodes['/memory']['reg'], ['0x0', '0x10000000'])
        self.assertIn('/memory/sub', nodes)
        with self.assertRaises(ValueError):
            bc._fdt_nodes(b'\0' * 64)

    def test_bootargs_model_order(self):
        afi = dict(uart_index=3, boot_dev='0x20')
        base = 'earlyprintk clk_ignore_unused selinux=0 loglevel=4'
        self.assertEqual(bc.bootargs_model(base, afi),
                         'console=ttyS3 ' + base + ' androidboot.dvfslevel=0x705x androidboot.bootdev=sd boot_dev=sd0')
        self.assertEqual(bc.bootargs_model(base, afi, s500_strap=True, gd_flags=0x40000).split()[-5:],
                         ['androidboot.dvfslevel=0x705x', 'androidboot.mode=charger', 'allenS500=1',
                          'androidboot.bootdev=sd', 'boot_dev=sd0'])
        self.assertNotIn('allenS500=1', bc.bootargs_model(base, afi, s500_strap=True, have_strap=False))
        nand = bc.bootargs_model('', dict(uart_index=5, boot_dev='0x00'), sn='X1')
        # empty bootargs: the firmware's "%s %s" keeps the separator (double space after console=)
        self.assertEqual(nand, 'console=ttyS5  androidboot.dvfslevel=0x705x androidboot.bootdev=nand boot_dev=nand '
                               'androidboot.serialno=X1')
        self.assertTrue(bc.bootargs_model('init=/init  ', afi).startswith('console=ttyS3 init=/init   android'))

    def test_memory_map_overlaps(self):
        env = dict(kernel_addr_r='0x7fc0', ramdisk_addr_r='0x1ffffc0', fdt_addr_r='0x2000100', scriptaddr='0x4400000')
        files = {'uImage': dict(header=dict(load='0x8000', size=0x1000), decompressed_size=0x3000),
                 'ramdisk.img': dict(header=dict(size=0x1000)), 'kernel.dtb': dict(size=0x100)}
        mm = bc.memory_map(env, files, dict(load=0x5000000, size=0x100))
        self.assertTrue(mm['rows'][1]['xip'])
        pairs = {(o['a'], o['b'], o['expected']) for o in mm['overlaps']}
        self.assertIn(('ramdisk payload (initrd, in place)', 'device tree (in place, +0x3000 pad)', False), pairs)
        self.assertTrue(any(o['expected'] for o in mm['overlaps']))

    def test_mbr_partition1_and_disk_bounds(self):
        with tempfile.TemporaryFile() as f:
            img = bytearray(4096)
            struct.pack_into('<II', img, 446 + 8, 2, 6)
            img[510:512] = b'\x55\xaa'
            f.write(img)
            f.flush()
            self.assertEqual(bc.gpt_partition1(f), dict(scheme='mbr', start_lba=2, sectors=6))
            d = bc.Disk(f)
            self.assertEqual(len(d.sectors(1, 2)), 1024)
            with self.assertRaises(bc.Unmodelled):
                d.sectors(7, 2)

    def test_sfvd_marker(self):
        with tempfile.TemporaryDirectory() as d:
            img = bytearray(0x206000)
            path = Path(d) / 'x.img'
            path.write_bytes(img)
            r = bc.sfvd_status(path)
            self.assertFalse(r['present'])
            self.assertEqual((r['marker_disk_offset'], r['writeback_region']), ('0x202a00', '0x202600..0x204e00'))
            img[0x202a00:0x202a08] = b'SFVD' + struct.pack('<I', 0xc582bb73)
            path.write_bytes(img)
            r = bc.sfvd_status(path)
            self.assertTrue(r['present'])
            self.assertEqual(r['value'], '0xc582bb73')
            (Path(d) / 'short.img').write_bytes(b'\0' * 0x202000)
            with self.assertRaises(ValueError):
                bc.sfvd_status(Path(d) / 'short.img')

    def test_cformat(self):
        class E:
            def cstr(self, a):
                return {1: 'x'}.get(a, '')
        self.assertEqual(bc._cfmt('a %d %x %08x %s %%', [-1 & 0xffffffff, 255, 1], E()),
                         'a -1 ff 00000001  %')


@unittest.skipUnless(HAVE_ARM, 'capstone/unicorn not installed')
class Synthetic(unittest.TestCase):
    def setUp(self):
        data, self.L = synthetic_uboot()
        self.ub = bc.Blob(data, 0x05000040, 'synthetic')

    def test_string_anchor_and_function_bounds(self):
        self.assertEqual(bc.find_check_boot_flag(self.ub), self.L['cbf'])
        self.assertEqual(bc.function_end(self.ub, self.L['cbf']), self.L['lit_fmt'])
        calls = bc.call_log(self.ub, self.L['cbf'], self.L['lit_fmt'])
        printf = [c for c in calls if c['target'] == self.L['printf']]
        self.assertEqual(bc.describe(self.ub, printf[0]['args'][0]), 'bootmode = %d\n')
        setenv = [c for c in calls if c['target'] == self.L['setenv']]
        self.assertEqual([bc.describe(self.ub, c['args'][1]) for c in setenv], ['run mmcboot', 'run ramboot'])

    def test_check_boot_flag_emulation_uses_real_getter(self):
        res = bc.check_boot_flag_table(self.ub, self.L['cbf'])
        self.assertEqual(res['setenv'], f"0x{self.L['setenv']:x}")
        by = {(r['afi'], r['boot_mode'], r['boot_dev']): r for r in res['rows']}
        self.assertEqual(by[('absent', None, None)]['setenv'], {'bootcmd': 'run ramboot'})
        self.assertEqual(by[('absent', None, None)]['printed'], ['bootmode = 1\n'])
        self.assertEqual(by[('present', 0, '0x20')]['setenv'], {'bootcmd': 'run mmcboot'})
        self.assertEqual(by[('present', 1, '0x20')]['setenv'], {'bootcmd': 'run ramboot'})
        self.assertTrue(all(r['error'] is None for r in res['rows']))

    def test_getter_defaults(self):
        rows = bc.afi_getter_defaults(self.ub, [f"0x{self.L['getmode']:x}"])['rows']
        self.assertEqual((rows[0]['value_without_magic'], rows[0]['value_with_sd_afi']), (1, 0))

    def test_init_sequence_table_walk(self):
        r = bc.init_sequence_r(self.ub, self.L['cbf'])
        self.assertEqual(r['table'], f"0x{self.L['table']:x}..0x{self.L['table'] + 20:x}")
        self.assertEqual([e['label'] for e in r['entries']].count('check_boot_flag'), 1)

    def test_emulator_unmodelled_mmio_and_stub(self):
        p = Program(0x1000)
        p.later(lambda pc: ldr_lit(0, pc, 0x1010))
        p.emit(0xE5901000)  # ldr r1, [r0]
        p.emit(BXLR)
        p.emit(0)
        p.emit(0xB0000010)
        code = p.build()
        emu = bc.Emulator([(0x0, 0x10000, None)])
        emu.uc.mem_write(0x1000, code)
        emu.call(0x1000, sp=0x8000)
        self.assertIn('unmodelled MMIO read 0xb0000010', emu.error)
        emu = bc.Emulator([(0x0, 0x10000, None)], mmio=lambda a, s: 0x55 if a == 0xB0000010 else None)
        emu.uc.mem_write(0x1000, code)
        emu.call(0x1000, sp=0x8000)
        self.assertIsNone(emu.error)
        self.assertEqual(emu.reg(1), 0x55)
        self.assertEqual(emu.mmio_log, [dict(op='read', address='0xb0000010', value='0x55')])
        q = Program(0x2000)
        q.emit(PUSH)
        q.later(lambda pc: bl(pc, 0x2010))
        q.emit(POP)
        q.emit(0)
        q.emit(mov(0, 1))
        q.emit(BXLR)
        emu = bc.Emulator([(0x0, 0x10000, None)], stubs={0x2010: ('stub', lambda e: 42)})
        emu.uc.mem_write(0x2000, q.build())
        emu.call(0x2000, sp=0x8000)
        self.assertEqual((emu.reg(0), emu.error), (42, None))


def load_evidence():
    return json.loads(EVIDENCE.read_text())


class Evidence(unittest.TestCase):
    def setUp(self):
        self.d = load_evidence()
        self.stock = {k: v for k, v in self.d['releases'].items() if k.startswith('stock-')}

    def test_stage_chain(self):
        st = self.d['stages']
        self.assertEqual([s['id'] for s in st], [f'S{i}' for i in range(8)])
        for a, b in zip(st, st[1:]):
            self.assertEqual(b['caller'], a['id'])
        allowed = {'verified', 'strongly-supported', 'inferred', 'speculative', 'unknown'}
        self.assertTrue(all(s['confidence'] in allowed and s['method'] and s['findings'] for s in st))

    def test_hashes_match_other_manifests(self):
        loaders = json.loads((ROOT / 'evidence/firmware/stock-loaders.json').read_text())['loaders']
        uboot = json.loads((ROOT / 'evidence/firmware/stock-platform.json').read_text())['uboot']
        for rel, r in self.stock.items():
            self.assertEqual(r['components']['loader']['sha256'], loaders[rel]['sha256'])
            self.assertEqual(r['components']['uboot']['uimage_sha256'], uboot[rel]['sha256'])
        self.assertEqual(self.d['releases']['koriki-v1.0']['components']['loader']['sha256'],
                         loaders['stock-230309']['sha256'])

    def test_emulations_completed_without_unmodelled_behaviour(self):
        for rel, r in self.d['releases'].items():
            m = r['loader']['main']
            self.assertIsNone(m['error'], rel)
            self.assertEqual(m['stopped'], 'app.bin entry 0x1000', rel)
            self.assertEqual(m['r0_at_app_entry'], r['components']['uboot']['entry'], rel)
            self.assertEqual(m['afi']['magic'], 'AFI')
            for h in r['handoff']:
                self.assertIsNone(h['error'], rel)
                self.assertEqual(h['return_value'], 0)

    def test_cross_method_agreement(self):
        """Emulated owl_boot_fdt_setup + image_setup_linux equals the static/emulated-helper model."""
        for rel, r in self.d['releases'].items():
            model = [r['bootargs']['gpio_low']] + ([r['bootargs']['gpio_high']] if r['bootargs']['gpio_high'] else [])
            self.assertEqual([h['dt_chosen']['bootargs'] for h in r['handoff']], model, rel)
            self.assertEqual([h['dt_chosen_bootargs'] for h in r['handoff_bootargs']], model, rel)
            self.assertEqual(r['handoff'][0]['initrd_start'], r['memory_map']['rows'][3]['start'])

    def test_boot_decision(self):
        for rel, r in self.stock.items():
            rows = {(x['afi'], x['boot_mode'], x['boot_dev']): x['setenv'] for x in r['uboot']['check_boot_flag']['rows']}
            self.assertEqual(rows[('present', 0, '0x20')]['bootcmd'], 'run mmcboot')
            self.assertEqual(rows[('absent', None, None)]['bootcmd'], 'run ramboot')
            self.assertTrue(r['uboot']['init_sequence_r']['check_boot_flag_after_initr_env'])
            sd0 = [x for x in r['loader']['boot_code_map']['rows'] if x['code'] == 0][0]
            self.assertEqual(sd0['boot_dev'], '0x20')

    def test_release_comparison(self):
        comp = self.d['comparison']['components']
        for k in ('bootloader.bin code', 'app.bin', 'block0', 'ini 0x1000-0x1400', 'uEnv.txt'):
            self.assertTrue(comp[k]['identical'], k)
        self.assertFalse(comp['ini 0x1400-0x2800']['identical'])
        strap = {rel: r['uboot']['variant_strap']['present'] for rel, r in self.stock.items()}
        dig = {rel: r['uboot']['normalised_functions']['digest'] for rel, r in self.stock.items()}
        self.assertEqual(dig['stock-221203'], dig['stock-221223'])
        self.assertNotEqual(dig['stock-221223'], dig['stock-230309'])
        self.assertEqual(strap, {'stock-221203': False, 'stock-221223': False, 'stock-230309': True,
                                 'stock-20231014': True})

    def test_no_local_paths_or_large_blobs(self):
        text = EVIDENCE.read_text()
        self.assertNotIn('/home/', text)
        self.assertLess(len(text), 400_000)

    def test_sfvd_present_in_every_analysed_image(self):
        for rel, r in self.d['releases'].items():
            self.assertEqual(r['loader']['ini_sfvd']['magic'], 'SFVD', rel)

    def test_koriki_shares_the_stock_pre_kernel_chain(self):
        k = self.d['other_firmware']['koriki-v1.0']
        self.assertEqual((k['loader_identical_to'], k['uboot_identical_to']), ('stock-230309', 'stock-230309'))
        self.assertTrue(all('init=/init' in b for b in k['dt_chosen_bootargs']))


FW = os.environ.get('ATM_FIRMWARE_DIR')


@unittest.skipUnless(FW and HAVE_ARM, 'set ATM_FIRMWARE_DIR to the directory holding the pinned images')
class FirmwareBacked(unittest.TestCase):
    def test_reanalysis_matches_committed_evidence(self):
        acq = {x['expanded_filename']: x for x in json.loads((ROOT / 'evidence/firmware/acquisitions.json').read_text())
               if 'expanded_filename' in x}
        committed = load_evidence()['releases']
        ran = 0
        for rel, ref in committed.items():
            name = rel + '.img'
            path = Path(FW) / name
            if not path.exists():
                continue
            new = bc.compact(bc.analyze(path, rel, acq[name]['expanded_sha256']))
            for key in ('components', 'loader', 'boot_files', 'memory_map', 'bootargs', 'handoff'):
                self.assertEqual(json.loads(json.dumps(new[key])), ref[key], f'{rel}:{key}')
            ran += 1
        if not ran:
            self.skipTest('no pinned image found in ATM_FIRMWARE_DIR')


if __name__ == '__main__':
    unittest.main()
