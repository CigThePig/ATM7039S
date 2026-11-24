"""Synthetic-fixture tests for the stock-firmware tools. No firmware or network needed."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid
import zipfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import actions_loader as al
import acquire_firmware as acq
import apply_firmware_registers as afr
import archive_members as am
import image_inventory as ii
import kernel_compare as kc
import map_accesses as ma
import mmio_refs as mr
import validate_firmware as vf
import ghidra_headless as gh

ROOT = Path(__file__).resolve().parents[1]
BASIC = uuid.UUID('ebd0a0a2-b9e5-4433-87c0-68b6b72699c7')


def words(*w):
    return struct.pack(f'<{len(w)}I', *w)


def gpt_image(parts, sectors=256, declared=None, break_header=False, break_entries=False):
    """Build a GPT disk image in memory. parts: list of (name, first_lba, last_lba)."""
    declared = declared or sectors
    img = bytearray(sectors * 512)
    mbr = bytearray(512)
    mbr[446 + 4] = 0xee
    struct.pack_into('<II', mbr, 446 + 8, 1, min(declared - 1, 0xffffffff))
    mbr[510:512] = b'\x55\xaa'
    img[:512] = mbr
    entries = bytearray(128 * 128)
    for i, (name, first, last) in enumerate(parts):
        e = bytearray(128)
        e[:16] = BASIC.bytes_le
        e[16:32] = uuid.UUID(int=i + 1).bytes_le
        struct.pack_into('<QQQ', e, 32, first, last, 0)
        e[56:56 + 2 * len(name)] = name.encode('utf-16le')
        entries[i * 128:(i + 1) * 128] = e
    if break_entries:
        entries[0] ^= 1
    ecrc = zlib.crc32(bytes(entries))
    if break_entries:
        entries[0] ^= 1
    h = bytearray(512)
    h[:8] = b'EFI PART'
    struct.pack_into('<IIIIQQQQ', h, 8, 0x10000, 92, 0, 0, 1, declared - 1, 34, declared - 34)
    h[56:72] = uuid.UUID(int=99).bytes_le
    struct.pack_into('<QIII', h, 72, 2, 128, 128, ecrc)
    struct.pack_into('<I', h, 16, zlib.crc32(bytes(h[:92])) ^ (1 if break_header else 0))
    img[512:1024] = h
    img[1024:1024 + len(entries)] = entries
    return img


class ImageInventoryTests(unittest.TestCase):
    def write(self, data):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        p = d / 'disk.img'
        p.write_bytes(bytes(data))
        return p

    def test_gpt_partitions_and_raw_region(self):
        img = gpt_image([('MISC', 64, 95), ('SYSTEM', 96, 191)])
        img[40 * 512:40 * 512 + 4] = b'\x27\x05\x19\x56'
        inv = ii.inventory(self.write(img))
        t = inv['partition_table']
        self.assertEqual(t['scheme'], 'gpt')
        self.assertEqual([(p['name'], p['offset'], p['size']) for p in t['partitions']],
                         [('MISC', 64 * 512, 32 * 512), ('SYSTEM', 96 * 512, 96 * 512)])
        raw = [r for r in inv['raw_regions'] if r.get('signatures')]
        self.assertTrue(any(s['kind'] == 'uImage' and s['offset'] == 40 * 512 for r in raw for s in r['signatures']))

    def test_gpt_metadata_not_reported_as_raw(self):
        inv = ii.inventory(self.write(gpt_image([('A', 64, 95)])))
        self.assertEqual(inv['raw_regions'], [])
        img = gpt_image([('A', 64, 95)])
        img[40 * 512] = 1
        regions = ii.inventory(self.write(img))['raw_regions']
        self.assertEqual([(r['offset'], r['size']) for r in regions], [(40 * 512, 512)])

    def test_corrupt_header_and_entries_rejected(self):
        with self.assertRaisesRegex(ValueError, 'header CRC'):
            ii.inventory(self.write(gpt_image([('A', 64, 95)], break_header=True)))
        with self.assertRaisesRegex(ValueError, 'entry array CRC'):
            ii.inventory(self.write(gpt_image([('A', 64, 95)], break_entries=True)))

    def test_truncated_image_needs_explicit_flag(self):
        img = gpt_image([('MISC', 64, 95), ('ROMS', 128, 4000)], sectors=256, declared=8192)
        with self.assertRaisesRegex(ValueError, 'allow-truncated'):
            ii.inventory(self.write(img))
        inv = ii.inventory(self.write(img), allow_truncated=True)
        t = inv['partition_table']
        self.assertTrue(t['truncated_image'])
        self.assertEqual([p['name'] for p in t['partitions']], ['MISC'])
        self.assertEqual(t['partitions_beyond_image'][0]['name'], 'ROMS')

    def test_partial_partition_not_scanned_as_raw(self):
        img = gpt_image([('MISC', 64, 95), ('ROMS', 128, 4000)], sectors=256, declared=8192)
        img[128 * 512:128 * 512 + 8] = b'ANDROID!'
        inv = ii.inventory(self.write(img), allow_truncated=True)
        self.assertEqual(inv['partition_table']['partitions_beyond_image'][0]['in_image_bytes'], 128 * 512)
        self.assertFalse(any(r['offset'] + r['size'] > 128 * 512 for r in inv['raw_regions']))

    def test_overlap_and_usable_range(self):
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            ii.inventory(self.write(gpt_image([('A', 64, 120), ('B', 100, 150)])))
        with self.assertRaisesRegex(ValueError, 'usable'):
            ii.inventory(self.write(gpt_image([('A', 10, 20)])))

    def test_truncated_partitions_still_checked_for_overlap(self):
        img = gpt_image([('A', 64, 4000), ('B', 96, 127)], sectors=256, declared=8192)
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            ii.inventory(self.write(img), allow_truncated=True)

    def test_hybrid_mbr_and_odd_length(self):
        img = gpt_image([('A', 64, 95)])
        img[446 + 16 + 4] = 0x0c
        struct.pack_into('<II', img, 446 + 16 + 8, 64, 32)
        with self.assertRaisesRegex(ValueError, 'hybrid'):
            ii.inventory(self.write(img))
        with self.assertRaisesRegex(ValueError, 'multiple of 512'):
            ii.inventory(self.write(gpt_image([('A', 64, 95)]) + b'x'))

    def test_expected_hash_enforced(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            ii.inventory(self.write(gpt_image([('A', 64, 95)])), expected_sha256='0' * 64)

    @unittest.skipUnless(shutil.which('mke2fs'), 'mke2fs not available')
    def test_ext4_walk_hash_and_extract(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / 'root/etc').mkdir(parents=True)
        (d / 'root/etc/init.rc').write_text('on boot\n')
        (d / 'root/link').symlink_to('etc/init.rc')
        fs = d / 'fs.img'
        subprocess.run(['mke2fs', '-q', '-F', '-t', 'ext4', '-b', '1024', '-d', str(d / 'root'), str(fs), '2048'],
                       check=True, capture_output=True)
        img = gpt_image([('SYSTEM', 64, 64 + 4095)], sectors=64 + 4096 + 40)
        img[64 * 512:64 * 512 + fs.stat().st_size] = fs.read_bytes()
        p = self.write(img)
        inv = ii.inventory(p)
        part = inv['partitions'][0]
        self.assertEqual(part['filesystem'], 'ext4')
        rec = next(f for f in part['files'] if f['path'] == '/etc/init.rc')
        self.assertEqual(rec['sha256'], hashlib.sha256(b'on boot\n').hexdigest())
        self.assertEqual(next(f for f in part['files'] if f['path'] == '/link')['target'], 'etc/init.rc')
        lst = d / 'list.txt'
        lst.write_text('SYSTEM:/etc/init.rc\n')
        out = ii.extract(p, inv, lst, d / 'out')
        self.assertEqual((d / 'out' / out[0]['output']).read_bytes(), b'on boot\n')
        lst.write_text('SYSTEM:/../etc/init.rc\n')
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            ii.extract(p, inv, lst, d / 'out2')
        self.assertEqual(ii.inventory(p), inv, 'inventory must be deterministic')


class ArchiveTests(unittest.TestCase):
    def zip_with(self, members):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        p = d / 'a.zip'
        with zipfile.ZipFile(p, 'w') as z:
            for name, data, attr in members:
                info = zipfile.ZipInfo(name)
                if attr:
                    info.external_attr = attr << 16
                z.writestr(info, data)
        return p, d

    def test_traversal_and_absolute_names_rejected(self):
        for bad in ('../evil', '/abs', 'a\\b', 'C:x'):
            p, _ = self.zip_with([(bad, b'x', 0)])
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                am.list_members(p)

    def test_symlink_member_not_extracted(self):
        p, d = self.zip_with([('link', b'target', 0o120777)])
        with self.assertRaisesRegex(ValueError, 'regular file'):
            am.extract(p, 'link', d / 'out')

    def test_ceiling_and_hash(self):
        p, d = self.zip_with([('img', b'A' * 4096, 0)])
        with self.assertRaisesRegex(ValueError, 'ceiling'):
            am.extract(p, 'img', d / 'out', limit=100)
        r = am.extract(p, 'img', d / 'out2')
        self.assertEqual(r['sha256'], hashlib.sha256(b'A' * 4096).hexdigest())
        with self.assertRaises(FileExistsError):
            am.extract(p, 'img', d / 'out2')

    def test_existing_destination_preserved_on_non_zip_path(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        out = d / 'out'
        out.mkdir()
        (out / 'img').write_bytes(b'earlier evidence')
        fake = dict(container='rar5', members=[dict(name='img', size=4, directory=False, special=False)])
        orig = am.list_members
        am.list_members = lambda path: fake
        try:
            with self.assertRaises(FileExistsError):
                am.extract(d / 'a.rar', 'img', out)
        finally:
            am.list_members = orig
        self.assertEqual((out / 'img').read_bytes(), b'earlier evidence')

    def test_normalised_member_names_extract_by_stored_spelling(self):
        p, d = self.zip_with([('./sub//disk.img', b'C' * 10, 0)])
        self.assertEqual([m['name'] for m in am.list_members(p)['members']], ['sub/disk.img'])
        self.assertEqual(am.extract(p, 'sub/disk.img', d / 'o1')['size'], 10)
        self.assertEqual(am.extract(p, './sub//disk.img', d / 'o2')['size'], 10)

    def test_verbose_extractor_stderr_does_not_deadlock(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        tool = d / 'noisy.py'
        tool.write_text('import sys\nsys.stderr.write("x" * (1 << 20)); sys.stderr.flush()\nsys.stdout.write("DATA")\n')
        fake = dict(container='rar5', members=[dict(name='img', archive_name='img', size=4, directory=False, special=False)])
        orig_list, orig_cmds = am.list_members, am._stream_commands
        am.list_members = lambda path: fake
        am._stream_commands = lambda kind, path, name: [[sys.executable, '-I', str(tool)]]
        try:
            r = am.extract(d / 'a.rar', 'img', d / 'out')
        finally:
            am.list_members, am._stream_commands = orig_list, orig_cmds
        self.assertEqual((r['size'], (d / 'out/img').read_bytes()), (4, b'DATA'))

    def test_unknown_container(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / 'x').write_bytes(b'NOTANARCHIVE')
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            am.list_members(d / 'x')

    def test_acquisition_expansion_checks_member_hash(self):
        p, d = self.zip_with([('disk.img', b'B' * 1000, 0)])
        item = dict(compression='zip', expanded_member='disk.img', expanded_filename='out.img',
                    expanded_size=1000, expanded_sha256=hashlib.sha256(b'B' * 1000).hexdigest())
        self.assertEqual(acq.expand(item, p, d).read_bytes(), b'B' * 1000)
        bad = dict(item, expanded_filename='bad.img', expanded_sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            acq.expand(bad, p, d)
        self.assertFalse((d / 'bad.img').exists())
        with self.assertRaisesRegex(ValueError, 'no safe'):
            acq.expand(dict(item, compression='lzma', expanded_filename='z'), p, d)


MOVW_R0_A0 = 0xE30000A0      # movw r0, #0xa0
MOVT_R0_B016 = 0xE34B0016    # movt r0, #0xb016
LDR_R1_R0 = 0xE5901000       # ldr r1, [r0]
MOV_R2_5 = 0xE3A02005        # mov r2, #5
STR_R2_R0_8 = 0xE5802008     # str r2, [r0, #8]
BX_LR = 0xE12FFF1E


class MmioTests(unittest.TestCase):
    MODEL = dict(blocks=[dict(id='b', base=0xb0160000, size=None, registers=[
        dict(name='CMU_DEVCLKEN0', offset=0xa0), dict(name='CMU_DEVRST0', offset=0xa8)])])

    def test_constant_propagation_read_and_write(self):
        code = words(MOVW_R0_A0, MOVT_R0_B016, LDR_R1_R0, MOV_R2_5, STR_R2_R0_8, BX_LR)
        acc = mr.scan(code, 0x1000, [(0, len(code))], regmap=mr.RegisterMap(self.MODEL))
        self.assertEqual([(a['access'], a['physical'], a.get('value')) for a in acc],
                         [('read', 0xb01600a0, None), ('write', 0xb01600a8, 5)])
        self.assertEqual(acc[1]['register_names'], ['CMU_DEVRST0'])
        self.assertEqual(acc[1]['offset'], 0x10)
        self.assertEqual(acc[1]['address'], 0x1010)

    def test_io_map_translation_required_for_virtual_addresses(self):
        code = words(0xE59F3004, 0xE5930000, BX_LR, 0xF81600A0)  # ldr r3,=0xf81600a0; ldr r0,[r3]
        self.assertEqual(mr.scan(code, 0xc0008000, [(0, 12)]), [])
        acc = mr.scan(code, 0xc0008000, [(0, 12)], iomap=[(0xf8000000, 0xb0000000, 0x04000000)])
        self.assertEqual((acc[0]['target'], acc[0]['physical']), (0xf81600a0, 0xb01600a0))

    def test_branch_target_discards_state(self):
        # b +0 (to next+4) makes the store a branch target with unknown incoming registers.
        code = words(MOVW_R0_A0, MOVT_R0_B016, 0xEAFFFFFF, STR_R2_R0_8, BX_LR)
        self.assertEqual(mr.scan(code, 0, [(0, len(code))]), [])

    def test_ldrd_invalidates_both_destinations(self):
        # mov r1,#5 ; movw r2,#0xa8 ; movt r2,#0xb016 ; ldrd r0,r1,[r4] ; str r1,[r2]
        code = words(0xE3A01005, 0xE30020A8, 0xE34B2016, 0xE1C400D0, 0xE5821000, BX_LR)
        acc = mr.scan(code, 0, [(0, len(code))])
        self.assertEqual([(a['access'], a['physical']) for a in acc], [('write', 0xb01600a8)])
        self.assertNotIn('value', acc[0])

    def test_literal_pc_load_is_a_control_transfer(self):
        # movw/movt r0=0xb01600a0 ; ldr pc,[pc,#4] ; str r2,[r0] (not fall-through) ; bx lr ; .word target
        code = words(MOVW_R0_A0, MOVT_R0_B016, 0xE59FF004, 0xE5802000, BX_LR, 0x00001234)
        self.assertEqual(mr.scan(code, 0, [(0, 0x14)]), [])

    def test_store_multiple_writeback_invalidates_base(self):
        # r0=0xb01600a0 ; stmia r0!,{r1} ; str r2,[r0]
        code = words(MOVW_R0_A0, MOVT_R0_B016, 0xE8A00002, 0xE5802000, BX_LR)
        self.assertEqual(mr.scan(code, 0, [(0, len(code))]), [])

    def test_ip_clobbered_by_calls(self):
        # movw ip,#0xa8 ; movt ip,#0xb016 ; bl (to the bx lr) ; str r2,[ip]
        code = words(0xE300C0A8, 0xE34BC016, 0xEB000000, 0xE58C2000, BX_LR)
        self.assertEqual(mr.scan(code, 0, [(0, len(code))]), [])

    def test_default_thumb_range_keeps_final_halfword(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        # movw r0,#0xa0 ; movt r0,#0xb016 ; str r1,[r0]  (10 bytes of T32)
        (d / 't.bin').write_bytes(bytes.fromhex('40f2a000') + bytes.fromhex('cbf21600') + bytes.fromhex('0160'))
        r = mr.run(d / 't.bin', 0x1000, [], thumb=True)
        self.assertEqual(r['ranges'], [[0, 10]])
        self.assertEqual([(a['access'], a['physical']) for a in r['accesses']], [('write', 0xb01600a0)])

    def test_narrow_store_value_masked_to_width(self):
        # movw r1,#0x1234 ; movw r0,#0xa0 ; movt r0,#0xb016 ; strb r1,[r0] ; strh r1,[r0]
        code = words(0xE3011234, MOVW_R0_A0, MOVT_R0_B016, 0xE5C01000, 0xE1C010B0, BX_LR)
        acc = mr.scan(code, 0, [(0, len(code))])
        self.assertEqual([(a['width'], a['value']) for a in acc], [(8, 0x34), (16, 0x1234)])

    def test_thumb_cbz_target_discards_state(self):
        # cbz r2, L ; movw r0,#0xa0 ; movt r0,#0xb016 ; L: str r1,[r0] ; bx lr
        code = bytes.fromhex('1ab1') + bytes.fromhex('40f2a000') + bytes.fromhex('cbf21600') + bytes.fromhex('0160') + bytes.fromhex('7047')
        self.assertEqual(mr.scan(code, 0, [(0, len(code))], thumb=True), [])

    def test_call_argument_recorded(self):
        # mov r0,#4 ; movw r1,#4 ; movt r1,#0xb01c ; bl +0x100
        code = words(0xE3A00004, 0xE3001004, 0xE34B101C, 0xEB00003D, BX_LR)
        acc = mr.scan(code, 0xb4060000, [(0, len(code))])
        self.assertEqual(acc[0]['access'], 'call-arg')
        self.assertEqual((acc[0]['argument'], acc[0]['physical'], acc[0]['other_constant_args']), ('r1', 0xb01c0004, {'r0': 4}))
        self.assertEqual(acc[0]['callee'], 0xb4060000 + 12 + 8 + 4 * 0x3D)

    def test_invalid_coordinates_rejected(self):
        code = words(BX_LR)
        with self.assertRaisesRegex(ValueError, 'misaligned'):
            mr.scan(code, 0x1002, [(0, 4)])
        with self.assertRaisesRegex(ValueError, 'outside'):
            mr.scan(code, 0, [(0, 8)])
        with self.assertRaisesRegex(ValueError, '32-bit'):
            mr.scan(code, 0xfffffffc + 4, [(0, 4)])

    def test_ambiguous_register_names_flagged(self):
        model = dict(blocks=[dict(id='a', base=0xb0000000, size=None, registers=[dict(name='X', offset=0)]),
                             dict(id='b', base=0xb0000000, size=None, registers=[dict(name='Y', offset=0)])])
        d = mr.RegisterMap(model).describe(0xb0000000)
        self.assertTrue(d['ambiguous'])
        self.assertEqual(d['register_names'], ['X', 'Y'])

    def test_deterministic(self):
        code = words(MOVW_R0_A0, MOVT_R0_B016, LDR_R1_R0, BX_LR)
        self.assertEqual(mr.scan(code, 0, [(0, 16)]), mr.scan(code, 0, [(0, 16)]))


class KernelCompareTests(unittest.TestCase):
    def test_normalised_bodies_ignore_branch_offsets_and_pointers(self):
        base = 0xc0008000
        f = words(0xE92D4010, 0xEB000010, 0xE59F0000, BX_LR, 0xc0123456)
        g = words(0xE92D4010, 0xEB000999, 0xE59F0000, BX_LR, 0xc0abcdef)
        h = words(0xE92D4010, 0xEB000010, 0xE59F0004, BX_LR, 0xc0123456)
        self.assertEqual(kc.normalised(f, base, base, 20), kc.normalised(g, base, base, 20))
        self.assertNotEqual(kc.normalised(f, base, base, 20), kc.normalised(h, base, base, 20))
        self.assertIsNone(kc.normalised(f, base, base + 2, 8))

    def test_compare_and_duplicate_statics_excluded(self):
        a = words(*[BX_LR] * 8)
        sa = [(0xc0008000, 'T', 'one'), (0xc0008008, 't', 'dup'), (0xc0008010, 't', 'dup'), (0xc0008018, 'T', 'end')]
        sb = [(0xc0008000, 'T', 'one'), (0xc0008008, 'T', 'two.isra.3'), (0xc0008018, 'T', 'end')]
        r = kc.compare(a, sa, a, sb, names_of_interest=['one', 'two'])
        self.assertEqual(r['common'], 1)
        self.assertEqual(r['ambiguous_names_excluded'], dict(a=1, b=0))
        self.assertEqual(r['b_only_base_names'], ['two'])
        self.assertEqual(kc.base_name('x.isra.1.constprop.4'), 'x')

    def test_malformed_symbol_file(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / 's').write_text('c0008000 T\n')
        with self.assertRaisesRegex(ValueError, 'malformed'):
            kc.load_symbols(d / 's')


def loader_fixture():
    data = bytearray(64 * 512)
    data[0:8] = words(0xE3A00001, BX_LR)

    def seal(tag_offset, start):
        data[tag_offset:tag_offset + 8] = al.TAG
        data[tag_offset + 8:tag_offset + 12] = b'\0' * 4
        struct.pack_into('<I', data, tag_offset + 8, al.checksum(bytes(data), start, tag_offset))
    seal(0x1f4, 0)
    p = 0x2000
    data[p:p + 4] = b'PACK'
    struct.pack_into('<I', data, p + 0x3c, 2)
    for slot, (name, size, off, load) in enumerate([('bootloader.bin', 40, 0, 0xb4060000), ('bootloader.ini', 2, 18, 0xb4062400)]):
        e = p + 0x40 + 0x80 * slot
        data[e:e + len(name)] = name.encode()
        struct.pack_into('<3I', data, e + 16, size, off, load)
    ini = 0x2400
    data[ini:ini + 4] = b'1.1\0'
    data[ini + 0x0e] = 3
    struct.pack_into('<I', data, ini + 0x10, 115200)
    struct.pack_into('<HxxH', data, ini + 0x1c, 468, 256)
    data[ini + 0x24:ini + 0x2b] = bytes([1, 1, 0x10, 0x48, 2, 2, 9])
    data[0x3000:0x3004] = b'CODE'
    seal(0x4ff4, 0x2c00)
    return data


class ActionsLoaderTests(unittest.TestCase):
    def test_trailers_pack_and_dram_record(self):
        r = al.parse(bytes(loader_fixture()))
        self.assertEqual([t['valid'] for t in r['trailers']], [True, True])
        self.assertEqual(r['trailers'][0]['earliest_valid_start'], 0)
        self.assertEqual([m['name'] for m in r['pack']['members']], ['bootloader.bin', 'bootloader.ini'])
        self.assertEqual(r['pack']['members'][1]['byte_range'], [18 * 512, 20 * 512])
        d = r['dram_config']
        self.assertEqual((d['ddr_clock_mhz'], d['capacity_mib'], d['bus_width_bits_as_printed'], d['rdodt'], d['drv'], d['uart_baudrate']),
                         (468, 256, 16, 2, 9, 115200))

    def test_corrupt_checksum_detected(self):
        data = loader_fixture()
        data[4] ^= 0xff
        self.assertFalse(al.parse(bytes(data))['trailers'][0]['valid'])

    def test_bad_pack_entries_rejected(self):
        data = loader_fixture()
        data[0x2040:0x2042] = b'..'
        data[0x2042] = ord('/')
        with self.assertRaisesRegex(ValueError, 'name'):
            al.parse(bytes(data))
        data = loader_fixture()
        struct.pack_into('<I', data, 0x203c, 3)
        with self.assertRaisesRegex(ValueError, 'shorter'):
            al.parse(bytes(data))
        with self.assertRaises(ValueError):
            al.checksum(b'\0' * 16, 2, 4)


HEADER = '''
struct lane {
    u32 gcr;
    u32 gsr[2];
};
struct ctl {
    u32 scfg;   /* comment */
    u32 sctl;
    u32 reserved[2];
    struct lane dx[2];
};
'''


class MapAccessTests(unittest.TestCase):
    def test_struct_layout_with_nesting(self):
        lay, size = ma.struct_layout(HEADER, 'ctl')
        self.assertEqual(size, 16 + 2 * 12)
        self.assertEqual((lay[4], lay[16], lay[32]), ('sctl', 'dx[0].gcr', 'dx[1].gsr[0]'))
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            ma.struct_layout('struct x { u64 y; };', 'x')

    def test_helper_roles(self):
        lay, size = ma.struct_layout(HEADER, 'ctl')
        refs = dict(component_sha256='0' * 64, accesses=[
            dict(offset=0, physical=0xb01c0004, access='call-arg', argument='r1', callee=0x100, other_constant_args={'r0': 7}),
            dict(offset=4, physical=0xb01c0010, access='call-arg', argument='r0', callee=0x200, other_constant_args={'r1': 1}),
            dict(offset=8, physical=0xb01c0100, access='write', value=3),
            dict(offset=12, physical=0xb01c0000, access='call-arg', argument='r0', callee=0x300, other_constant_args={})])
        r = ma.map_accesses(refs, [('C', 0xb01c0000, lay, 0x200)], write_helpers=[(0x100, 'r0', 'r1')], set_helpers=[(0x200, 'r0', 'r1')])
        seq = r['sequence']
        self.assertEqual((seq[0]['register'], seq[0]['operation'], seq[0]['value']), ('sctl', 'write', '0x7'))
        self.assertEqual((seq[1]['register'], seq[1]['operation'], seq[1]['mask']), ('dx[0].gcr', 'set-bits', '0x1'))
        self.assertIsNone(seq[2]['register'])
        self.assertEqual(seq[3]['operation'], 'call:0x300')
        self.assertEqual((r['named'], r['unnamed']), (3, 1))


class CuratedRegisterTests(unittest.TestCase):
    def model(self):
        return dict(blocks=[dict(id='candidate:X', base=0xb0000000, size=None, evidence=[dict(source='s')],
                                 registers=[dict(id='reg:A', name='A', offset=0, evidence=[dict(source='s')])])])

    def curated(self):
        return dict(new_blocks=[dict(id='firmware:NEW', base=0xb01c0000, size=None, evidence=[dict(source='t')], registers=[])],
                    extra_registers=[dict(block_id='candidate:X', registers=[dict(id='reg:B', name='B', offset=4, evidence=[])])],
                    register_evidence=[dict(block_id='candidate:X', register='A', evidence=[dict(source='t', curated=afr.TAG)])])

    def test_idempotent(self):
        once = afr.apply(self.model(), self.curated())
        twice = afr.apply(json.loads(json.dumps(once)), self.curated())
        self.assertEqual(once, twice)
        self.assertEqual([b['id'] for b in once['blocks']], ['candidate:X', 'firmware:NEW'])
        self.assertEqual(len(once['blocks'][0]['registers'][0]['evidence']), 2)

    def test_unknown_or_duplicate_targets_rejected(self):
        bad = self.curated()
        bad['register_evidence'][0]['register'] = 'missing'
        with self.assertRaisesRegex(ValueError, 'unknown register'):
            afr.apply(self.model(), bad)
        dup = self.curated()
        dup['extra_registers'][0]['registers'][0]['offset'] = 0
        with self.assertRaisesRegex(ValueError, 'duplicates'):
            afr.apply(self.model(), dup)

    def test_repository_model_already_applied(self):
        model = json.loads((ROOT / 'registers/canonical/hardware.json').read_text())
        curated = json.loads(afr.CURATED.read_text())
        self.assertEqual(afr.apply(json.loads(json.dumps(model)), curated), model)
        for b in model['blocks']:
            if b['id'].startswith('firmware:'):
                self.assertTrue(all(not r['hardware_validated'] and r['access'] == 'unknown' and r['reset'] is None
                                    for r in b['registers']))


class GhidraCommandTests(unittest.TestCase):
    def test_raw_import_requires_explicit_base_and_exports_no_decompilation(self):
        with self.assertRaisesRegex(ValueError, 'base'):
            gh.command('/g', '/p', 'c.bin', 'o.json')
        cmd = gh.command('/g', '/p', 'c.bin', 'o.json', base=0xb4060000, entries=['0xb4060000'])
        self.assertIn('-loader-baseAddr', cmd)
        self.assertEqual(cmd[cmd.index('-loader-baseAddr') + 1], '0xb4060000')
        self.assertIn('-deleteProject', cmd)
        self.assertEqual(cmd[cmd.index('-postScript') + 1], 'ExportAnalysis.java')
        src = (ROOT / 'tools/ghidra/ExportAnalysis.java').read_text()
        self.assertNotIn('DecompInterface', src)


class StockManifestValidationTests(unittest.TestCase):
    def test_repository_stock_manifests_valid(self):
        self.assertEqual(vf.validate(ROOT), [])

    def test_out_of_bounds_inventory_detected(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / 'evidence/firmware').mkdir(parents=True)
        inv = dict(size=1024 * 512, sha256='a' * 64, raw_regions=[dict(offset=0, size=4096 * 512, sha256='b' * 64)],
                   partition_table=dict(partitions=[dict(index=1, offset=512, size=2048 * 512)]), partitions=[])
        (d / 'evidence/firmware/stock-x-inventory.json').write_text(json.dumps(inv))
        errs = vf.stock_index(d, {})
        self.assertTrue(any('partition outside' in e for e in errs))
        self.assertTrue(any('raw region outside' in e for e in errs))


if __name__ == '__main__':
    unittest.main()
