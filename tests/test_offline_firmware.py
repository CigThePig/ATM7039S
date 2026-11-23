import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import research as r
from firmware_catalogue import catalogue, mbr, region, Window, safe_name
from arm_refs import inventory
from build_dataset import preserve_extra


def disk():
    b=bytearray(4096);b[510:512]=b'\x55\xaa';b[450]=0x83
    struct.pack_into('<II',b,454,1,7)
    return b


class ImageTests(unittest.TestCase):
    def test_mbr_geometry(self):
        p=mbr(disk()[:512],4096)[0]
        self.assertEqual((p['offset'],p['size']),(512,3584))
    def test_invalid_partition_bounds(self):
        b=disk();struct.pack_into('<I',b,458,8)
        with self.assertRaisesRegex(ValueError,'bounds'):mbr(b[:512],4096)
    def test_overlapping_partitions(self):
        b=disk();b[466]=0x83;struct.pack_into('<II',b,470,2,1)
        with self.assertRaisesRegex(ValueError,'overlapping'):mbr(b[:512],4096)
    def test_gpt_explicitly_rejected(self):
        b=disk();b[450]=0xee
        with self.assertRaisesRegex(ValueError,'GPT'):mbr(b[:512],4096)
    def test_region_truncation(self):
        with self.assertRaises(ValueError):region(io.BytesIO(b'12'),0,3,3)
    def test_region_size_bound(self):
        with self.assertRaises(ValueError):region(io.BytesIO(),0,1<<30,1<<30)
    def test_partition_window_does_not_escape(self):
        w=Window(io.BytesIO(b'privateHELLOsecret'),7,5)
        self.assertEqual(w.read(999),b'HELLO');self.assertEqual(w.read(),b'')
        with self.assertRaises(ValueError):w.seek(-1)
        with self.assertRaises(ValueError):w.seek(6)
        with self.assertRaises(io.UnsupportedOperation):w.write(b'x')
    def test_component_path_traversal_rejected(self):
        for p in ['../x','a/b','..','x\\y']:
            with self.assertRaises(ValueError):safe_name(p)
    def test_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'disk';p.write_bytes(disk())
            with self.assertRaisesRegex(ValueError,'SHA-256'):catalogue(p,{'image_sha256':'bad'})
    def test_deterministic_raw_component_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'disk';b=disk();p.write_bytes(b)
            plan={'image_sha256':r.sha(b),'source':'fixture','release':'test',
                  'raw_regions':[{'id':'slice.bin','offset':512,'size':16}]}
            a=catalogue(p,plan,Path(d)/'out');self.assertEqual(a,catalogue(p,plan))
            self.assertEqual(a['components'][0]['sha256'],r.sha(bytes(16)))
            with self.assertRaises(FileExistsError):catalogue(p,plan,Path(d)/'out')
    def test_oversized_uimage_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'disk';b=disk();b[512:516]=bytes.fromhex('27051956');struct.pack_into('>I',b,524,0xffffffff);p.write_bytes(b)
            plan={'image_sha256':r.sha(b),'source':'fixture','release':'test',
                  'raw_regions':[{'id':'u','offset':512,'format':'uImage'}]}
            with self.assertRaisesRegex(ValueError,'oversized'):catalogue(p,plan)


class ArmTests(unittest.TestCase):
    def test_forward_and_negative_branch(self):
        b=struct.pack('<II',0xeb000000,0xeafffffd)
        refs=inventory(b,0,8)['references']
        self.assertEqual(refs[0]['target_offset'],8);self.assertEqual(refs[1]['target_offset'],0)
    def test_pc_literal_and_negative_displacement(self):
        b=struct.pack('<III',0xe59f0000,0xe51f1004,0xb4060300)
        refs=inventory(b,0,8)['references']
        self.assertEqual([x['value'] for x in refs],[0xb4060300]*2)
    def test_not_str_byte_load_or_blx(self):
        b=struct.pack('<III',0xe58f0000,0xe5df0000,0xfa000000)
        self.assertEqual(inventory(b,0,12)['references'],[])
    def test_alignment_rejected(self):
        with self.assertRaises(ValueError):inventory(b'12345678',1,8)
    def test_oob_literal_retained(self):
        x=inventory(struct.pack('<I',0xe59f0000),0,4)['references'][0]
        self.assertIn('error',x)
    def test_curated_sources_survive_regeneration(self):
        self.assertEqual(preserve_extra([{'id':'a','value':2}],[{'id':'a','value':1},{'id':'b'}],lambda x:x['id']),[{'id':'a','value':2},{'id':'b'}])


class OptionalFatTests(unittest.TestCase):
    def test_real_fat_roundtrip(self):
        try:
            from pyfatfs.PyFat import PyFat
            from pyfatfs.PyFatFS import PyFatFS
        except ImportError:
            self.skipTest('optional requirements-firmware.txt not installed')
        with tempfile.TemporaryDirectory() as d:
            fat=Path(d)/'fat';fat.touch()
            pf=PyFat();pf.mkfs(str(fat),fat_type=PyFat.FAT_TYPE_FAT12,size=2*1024*1024);pf.close()
            with PyFatFS(str(fat)) as fs:fs.writebytes('/test.bin',b'firmware fixture')
            b=bytearray(512)+fat.read_bytes();b[510:512]=b'\x55\xaa';b[450]=1;struct.pack_into('<II',b,454,1,(len(b)-512)//512)
            p=Path(d)/'disk';p.write_bytes(b)
            plan={'source':'fixture','release':'test','image_sha256':r.sha(b),'fat_partition':1,
                  'fat_files':[{'id':'test.bin','path':'/test.bin'}]}
            a=catalogue(p,plan)
            self.assertEqual(a['components'][0]['sha256'],r.sha(b'firmware fixture'))
            self.assertEqual(p.read_bytes(),b)

class AcquisitionTests(unittest.TestCase):
    def test_size_bomb_removed(self):
        from acquire_firmware import copy_checked
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'out'
            with self.assertRaises(ValueError):copy_checked(io.BytesIO(b'1234'),p,3,r.sha(b'123'))
            self.assertFalse(p.exists())
    def test_bad_hash_removed(self):
        from acquire_firmware import copy_checked
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'out'
            with self.assertRaises(ValueError):copy_checked(io.BytesIO(b'abc'),p,3,'0'*64)
            self.assertFalse(p.exists())
    def test_existing_input_not_replaced(self):
        from acquire_firmware import copy_checked
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'out';p.write_bytes(b'keep')
            with self.assertRaises(FileExistsError):copy_checked(io.BytesIO(b'new'),p,3,r.sha(b'new'))
            self.assertEqual(p.read_bytes(),b'keep')

class PayloadTests(unittest.TestCase):
    def test_internal_gzip_and_version_offset(self):
        import gzip
        from boot_payloads import inspect
        raw=b'abcLinux version fixture\0'
        x=inspect(b'header'+gzip.compress(raw,mtime=0))['gzip_streams'][0]
        self.assertEqual((x['offset'],x['size'],x['sha256']),(6,len(raw),r.sha(raw)))
        self.assertEqual(x['linux_version_strings'][0]['offset'],3)
    def test_corrupt_or_truncated_gzip_not_verified(self):
        import gzip
        from boot_payloads import inspect
        raw=gzip.compress(b'cpio',mtime=0)
        self.assertEqual(inspect(raw[:-1])['gzip_streams'],[])
        bad=bytearray(raw);bad[-8]^=1
        self.assertEqual(inspect(bad)['gzip_streams'],[])
    def test_expansion_limit(self):
        import gzip
        from boot_payloads import inspect
        with self.assertRaises(ValueError):inspect(gzip.compress(b'x'*2048,mtime=0),max_expanded=1024)


class EvidenceLinkTests(unittest.TestCase):
    def test_binary_offset_and_hash_tampering(self):
        import shutil
        from validate_firmware import validate
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree(r.ROOT/'evidence',root/'evidence')
            p=root/'evidence/findings.json';a=json.loads(p.read_text())
            f=next(x for x in a if x['id']=='BOOT-004');f['evidence'][0]['sha256']='0'*64;f['evidence'][0]['offset_end']=1<<30;p.write_text(json.dumps(a))
            errors=validate(root)
            self.assertTrue(any('hash mismatch' in x for x in errors))
            self.assertTrue(any('range outside' in x for x in errors))
    def test_cmu_target_properties_stay_unknown(self):
        a=json.loads((r.ROOT/'registers/canonical/hardware.json').read_text())
        b=next(x for x in a['blocks'] if x['id']=='candidate:CMU_BASE')
        reg=next(x for x in b['registers'] if x['name']=='CMU_DEVRST1')
        self.assertEqual((reg['reset'],reg['access'],reg['width']),(None,'unknown',None))
        self.assertTrue(all(x['confidence']=='inferred' for x in reg['fields']))
