import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import research as r
from audit_sources import audit
from compare_layouts import compare as layout_compare

def dtb(properties):
 strings=b'';body=struct.pack('>I',1)+b'\0'*4
 for name,value in properties.items():
  off=len(strings);strings+=name.encode()+b'\0'
  body+=struct.pack('>III',3,len(value),off)+value+b'\0'*((-len(value))%4)
 body+=struct.pack('>II',2,9)
 offstruct=56;offstrings=offstruct+len(body);total=offstrings+len(strings)
 return struct.pack('>10I',0xd00dfeed,total,offstruct,offstrings,40,17,16,0,len(strings),len(body))+b'\0'*16+body+strings

class TreeTests(unittest.TestCase):
 def test_string_lists_and_boolean(self):
  n=r.dts('/dts-v1/; / { compatible="a\\0b"; gpio-controller; };')[0]
  self.assertEqual(n['properties'],{'compatible':['a','b'],'gpio-controller':True})
 def test_comments_in_string(self):
  self.assertEqual(r.dts('/ { model="https://a/*b*/"; };')[0]['properties']['model'],['https://a/*b*/'])
 def test_geometry(self):
  x=r.dts('/ { #address-cells=<2>; #size-cells=<2>; ram@1 {reg=<1 0 0 4096>;}; bus {#address-cells=<1>; #size-cells=<0>; chip@65 {reg=<0x65>;};};};')
  a=r.ranges(x);self.assertEqual(a[0]['address'],0x100000000);self.assertEqual(a[1]['size'],None)
 def test_includes_rejected(self):
  with self.assertRaises(ValueError):r.dts('/include/ "x.dtsi"')
 def test_macros_rejected(self):
  with self.assertRaises(ValueError):r.dts('/ {reg=<BASE 4>;};')
 def test_bad_geometry(self):
  with self.assertRaises(ValueError):r.ranges(r.dts('/ {#address-cells=<1>;#size-cells=<1>;dev {reg=<1>;};};'))
 def test_duplicate_property(self):
  with self.assertRaises(ValueError):r.dts('/ {reg=<1 2>; reg=<3 4>;};')
 def test_unclosed(self):
  with self.assertRaises(ValueError):r.dts('/ { foo { reg=<0 4>; };')
 def test_fdt_minimal(self):
  b=dtb({'compatible':b'actions,test\0','#address-cells':struct.pack('>I',1)})
  self.assertEqual(r.fdt(b)['nodes'][0]['properties']['compatible'],['actions,test'])
 def test_fdt_truncated(self):
  with self.assertRaises(ValueError):r.fdt(dtb({})[:-1])
 def test_fdt_bad_string_offset(self):
  b=bytearray(dtb({'model':b'x\0'}));struct.pack_into('>I',b,72,0xffff)
  with self.assertRaises(ValueError):r.fdt(b)
 def test_fdt_bad_reservation(self):
  b=bytearray(dtb({}));struct.pack_into('>I',b,16,len(b))
  with self.assertRaises(ValueError):r.fdt(b)
 def test_fdt_missing_end(self):
  b=bytearray(dtb({}));struct.pack_into('>I',b,68,4)
  with self.assertRaises(ValueError):r.fdt(b)
 def test_comparison_ignores_metadata(self):
  a=[{'path':'/','line':1,'properties':{'model':['x']}}];b=[{'path':'/','offset':7,'properties':{'model':{'bytes':'7800'}}}]
  self.assertEqual(r.compare(a,b),[])
 def test_comparison_detects_disabled(self):
  a=r.dts('/ {status="okay";};');b=r.dts('/ {status="disabled";};');self.assertEqual(len(r.compare(a,b)),1)

class ConstantTests(unittest.TestCase):
 def test_hex_suffix(self):self.assertEqual(r.number('0xFFUL'),255)
 def test_expression_length(self):
  with self.assertRaises(ValueError):r.number('1+'*1024+'1')
 def test_forward_reference(self):
  c=r.constants('#define REG (BASE+0x10)\n#define BASE 0xB0000000\n','x')['definitions']
  self.assertEqual(c[0]['value'],0xb0000010)
 def test_bit_masks(self):
  self.assertEqual(r.number('GENMASK(6,4) | BIT(12)'),0x1070)
 def test_unsupported_function_preserved(self):
  c=r.constants('#define REG CALL(4)\n#define FUNC(x) (x+1)','x');self.assertEqual(len(c['unresolved']),1)
 def test_no_code_execution(self):
  with self.assertRaises(ValueError):r.number('__import__("os").system("false")')
 def test_shift_limit(self):
  with self.assertRaises(ValueError):r.number('1 << 99999999')
 def test_alias_preserved(self):
  c=r.constants('#define A 4\n#define B 4','x');self.assertEqual(len(c['definitions']),2)

class FirmwareTests(unittest.TestCase):
 def test_mbr_out_of_bounds(self):
  b=bytearray(512);b[510:]=b'\x55\xaa';b[450]=0x83;struct.pack_into('<II',b,454,10,100)
  x=r.firmware(b);self.assertFalse(x['mbr'][0]['in_bounds'])
 def test_uimage_crc(self):
  payload=b'test payload';h=bytearray(64);struct.pack_into('>7I',h,0,0x27051956,0,0,len(payload),0x1000,0x1000,zlib.crc32(payload));h[28:32]=bytes([5,2,2,0]);h[32:36]=b'Test';struct.pack_into('>I',h,4,zlib.crc32(h))
  b=h+payload;self.assertTrue(r.firmware(b)['candidates'][0]['valid']);b[-1]^=1;self.assertFalse(r.firmware(b)['candidates'][0]['valid'])
 def test_embedded_fdt(self):
  x=r.firmware(b'padding'+dtb({}));self.assertEqual(x['candidates'][0]['offset'],7);self.assertTrue(x['candidates'][0]['valid'])
 def test_fake_magic(self):
  self.assertFalse(r.firmware(b'\xd0\x0d\xfe\xed')['candidates'][0]['valid'])
 def test_short_elf(self):
  self.assertFalse(r.firmware(b'\x7fELF')['candidates'][0]['valid'])

class DatasetTests(unittest.TestCase):
 def test_schema_and_evidence(self):self.assertEqual(r.validate(r.ROOT)['errors'],[])
 def test_generated_current(self):r.generate(r.ROOT,True)
 def test_uart_mask_source_scope(self):
  model=json.loads((r.ROOT/'registers/canonical/hardware.json').read_text());block=next(b for b in model['blocks'] if b['id']=='candidate:UART0_BASE');reg=next(x for x in block['registers'] if x['name']=='UART0_CTL');field=next(x for x in reg['fields'] if x['name']=='OWL_UART_CTL_EN');self.assertEqual(field['mask'],1<<15);self.assertEqual(field['scope'],'S500-source');self.assertEqual(field['confidence'],'inferred')
 def test_mmio_does_not_include_i2c_address(self):
  model=json.loads((r.ROOT/'registers/canonical/hardware.json').read_text());self.assertFalse(any(x['base']==0x65 for x in model['blocks']))
 def test_known_gpu_difference(self):
  a=json.loads((r.ROOT/'evidence/gist-tree.json').read_text());b=json.loads((r.ROOT/'evidence/batocera-2100-tree.json').read_text());diff=r.compare(a['nodes'],b['nodes']);self.assertEqual(len(diff),9);self.assertIn('/gpu@b0300000',[x['path'] for x in diff])
 def test_layout_comparison_retains_irq_difference(self):
  a={'ranges':[dict(path='/a',size=4,address=1,interrupts_raw=[0,1,4])]};b={'ranges':[dict(path='/b',size=8,address=1,interrupts_raw=[0,2,4])]}
  self.assertFalse(layout_compare(a,b)[0]['irq_cells_equal'])
 def test_no_hardware_validation_claim(self):
  self.assertFalse(any(x['hardware_validated'] for x in json.loads((r.ROOT/'evidence/findings.json').read_text())))
 def test_target_register_promotion_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   import shutil
   for folder in ['evidence','registers']:shutil.copytree(r.ROOT/folder,root/folder)
   p=root/'registers/canonical/hardware.json';x=json.loads(p.read_text());reg=next(b['registers'][0] for b in x['blocks'] if b['registers']);reg['confidence']='verified';reg['scope']='ATM7039S-hardware';r.save(p,x)
   self.assertTrue(any('unvalidated target' in e for e in r.validate(root)['errors']))

class AuditTests(unittest.TestCase):
 def fixture(self,tmp):
  root=Path(tmp)/'repo';inp=Path(tmp)/'inputs';(root/'evidence').mkdir(parents=True);(root/'registers/canonical').mkdir(parents=True);inp.mkdir()
  (inp/'source.txt').write_text('one\ntwo\n')
  r.save(root/'evidence/files.json',[dict(source='test',path='source.txt',sha256=r.sha(b'one\ntwo\n'),size=8)])
  r.save(root/'evidence/findings.json',[dict(evidence=[dict(source='test',path='source.txt',line_start=1,line_end=2)])])
  r.save(root/'registers/canonical/hardware.json',dict(blocks=[]));return root,inp
 def test_audit_exact(self):
  with tempfile.TemporaryDirectory() as tmp:
   root,inp=self.fixture(tmp);self.assertEqual(audit(inp,root)['errors'],[])
 def test_audit_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as tmp:
   root,inp=self.fixture(tmp);(inp/'source.txt').write_text('changed');self.assertTrue(any('hash/size' in x for x in audit(inp,root)['errors']))
 def test_audit_line_bounds(self):
  with tempfile.TemporaryDirectory() as tmp:
   root,inp=self.fixture(tmp);r.save(root/'evidence/findings.json',[dict(evidence=[dict(source='test',path='source.txt',line_start=1,line_end=3)])]);self.assertTrue(any('invalid evidence lines' in x for x in audit(inp,root)['errors']))
 def test_audit_uncatalogued(self):
  with tempfile.TemporaryDirectory() as tmp:
   root,inp=self.fixture(tmp);r.save(root/'evidence/findings.json',[dict(evidence=[dict(source='test',path='missing.txt')])]);self.assertTrue(any('uncatalogued' in x for x in audit(inp,root)['errors']))

if __name__=='__main__':unittest.main()
