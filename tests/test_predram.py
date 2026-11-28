"""tools/predram_analysis.py: pre-DRAM reconstruction of the stock early loader (PR #9).

Three groups:

* Synthetic - hand-encoded A32 words in an otherwise empty loader image. No firmware needed.
* Evidence - consistency of the committed evidence/firmware/sd2-predram.json with the other manifests and
  with the evidence rules (no firmware needed).
* FirmwareBacked - skipped unless ATM_FIRMWARE_DIR holds the pinned expanded images (koriki-v1.0.img,
  stock-*.img; tools/acquire_firmware.py --expand). Re-derives the committed evidence.
"""
import json
import os
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

try:
    import capstone  # noqa: F401
    import unicorn  # noqa: F401
    HAVE_ARM = True
except ImportError:
    HAVE_ARM = False

EVIDENCE = ROOT / 'evidence/firmware/sd2-predram.json'
BASE = 0xB4060000


# ----------------------------------------------------------------------------- a tiny A32 encoder
def bl(pc, target, cond=0xE):
    return (cond << 28) | 0x0B000000 | (((target - pc - 8) >> 2) & 0xFFFFFF)


def b(pc, target, cond=0xE):
    return (cond << 28) | 0x0A000000 | (((target - pc - 8) >> 2) & 0xFFFFFF)


def ldr_lit(pc, rd, lit):
    return 0xE59F0000 | (rd << 12) | (lit - pc - 8)


PUSH_R4_LR, POP_R4_PC, BX_LR = 0xE92D4010, 0xE8BD8010, 0xE12FFF1E
CMP_R0_0 = 0xE3500000
MOV = lambda rd, imm: 0xE3A00000 | (rd << 12) | imm      # imm < 256
STR_R0_R1 = 0xE5810000                                     # str r0, [r1]
STR_R0_R2 = 0xE5820000                                     # str r0, [r2]
LDR_R0_R1 = 0xE5910000                                     # ldr r0, [r1]
BLX_R3 = 0xE12FFF33
MCR_VBAR_R1 = 0xEE0C1F10                                   # mcr p15, 0, r1, c12, c0, 0
SELF = 0xEAFFFFFE                                          # b .
LDR_PC_R0 = 0xE590F000                                     # ldr pc, [r0]
EQ = 0x0


class Image:
    """448-sector loader image; words placed at SRAM VAs."""

    def __init__(self):
        from predram_analysis import LOADER_SIZE
        self.data = bytearray(LOADER_SIZE)

    def put(self, va, words):
        for k, w in enumerate(words):
            struct.pack_into('<I', self.data, va - BASE + 4 * k, w & 0xFFFFFFFF)
        return va + 4 * len(words)

    def code(self):
        import predram_analysis as P
        return P.Code(bytes(self.data))


MAIN = 0xB4065400
F1, F2, F3 = 0xB4065600, 0xB4065700, 0xB4065800


def program():
    """main: calls F1, F2, F3 (indirect) and the write32 helper 0xb4069194 with constant arguments; F1 branches
    on r0 and tail-calls F2; F2 stores to an unknown pointer; F3 hangs."""
    im = Image()
    m = MAIN
    lit = MAIN + 0x100
    words = [
        PUSH_R4_LR,
        bl(m + 4, F1),
        ldr_lit(m + 8, 1, lit),          # r1 = 0xb0168008
        MOV(0, 4),                        # r0 = 4
        bl(m + 16, 0xB4069194),           # write32(4, 0xb0168008) via accessor
        ldr_lit(m + 20, 1, lit + 4),      # r1 = 0xb4064c00 (boot code word)
        LDR_R0_R1,                        # r0 = boot code
        bl(m + 28, F2),                   # passes the boot code in r0
        ldr_lit(m + 32, 3, lit + 8),      # r3 = F3
        BLX_R3,                           # resolved indirect call
        0xE12FFF34,                       # blx r4 (unknown): unresolved indirect call
        ldr_lit(m + 44, 1, lit),
        MOV(0, 7),
        STR_R0_R1,                        # direct str to 0xb0168008
        POP_R4_PC,
    ]
    im.put(m, words)
    im.put(lit, [0xB0168008, 0xB4064C00, F3])
    im.put(F1, [CMP_R0_0, b(F1 + 4, F1 + 12, EQ), BX_LR, b(F1 + 12, F2)])
    im.put(F2, [STR_R0_R2, b(F2 + 4, F2 + 12), 0xB4064C00, BX_LR])   # skips an inline data word
    im.put(F3, [MCR_VBAR_R1, SELF])
    im.put(0xB4069194, [STR_R0_R1, BX_LR])
    return im


@unittest.skipUnless(HAVE_ARM, 'capstone/unicorn not installed')
class Synthetic(unittest.TestCase):
    def setUp(self):
        import predram_analysis as P
        self.P = P
        self.im = program()
        self.code = self.im.code()
        self.funcs = P.call_graph(self.code, roots=(MAIN,), stop_at=())

    def test_direct_calls_tail_call_and_indirect(self):
        P, f = self.P, self.funcs
        targets = {c['target'] for c in f[MAIN]['calls']}
        self.assertTrue({P.h32(F1), P.h32(F2), P.h32(0xB4069194), P.h32(F3)} <= targets)
        ind = [c for c in f[MAIN]['calls'] if c.get('indirect')]
        self.assertEqual([(c['target'], c['resolved']) for c in ind], [(P.h32(F3), True), (None, False)])
        tail = [c for c in f[F1]['calls'] if c.get('tail')]
        self.assertEqual([c['target'] for c in tail], [P.h32(F2)])

    def test_conditional_branch_and_compare(self):
        br = [x for x in self.funcs[F1]['branches'] if x.get('condition')]
        self.assertEqual(len(br), 1)
        self.assertEqual(br[0]['condition'], 'eq')
        self.assertIn('cmp r0, #0', br[0]['compare'])

    def test_constant_tracking_resolves_mmio_store_and_accessor(self):
        rows = self.P.static_accesses(self.code, self.funcs)
        direct = [r for r in rows if r['via'] is None and r['address'] == '0xb0168008']
        self.assertEqual([(r['access'], r['value'], r['evidence']) for r in direct], [('write', '0x00000007', 'decoded')])
        via = [r for r in rows if r['via'] == '0xb4069194']
        self.assertEqual([(r['address'], r['value']) for r in via], [('0xb0168008', '0x00000004')])
        self.assertTrue(via[0]['evidence'].startswith('decoded (accessor'))

    def test_unresolved_pointer_access_is_kept_as_expression(self):
        acc = [a for a in self.funcs[F2]['accesses'] if a['access'] == 'write']
        self.assertEqual(acc[0]['region'], 'unresolved')
        self.assertEqual(acc[0]['expression'], '[r2]')

    def test_boot_code_use_versus_data_word(self):
        refs = self.P.boot_code_references(self.code, self.funcs)
        kinds = {(r['kind'], r.get('callee')) for r in refs['references']}
        self.assertIn(('passed as r0', self.P.h32(F2)), kinds)
        self.assertIn(('direct read', None), {(r['kind'], None) for r in refs['references']})
        lits = {r['at'] for r in refs['literal_words']}
        self.assertIn(self.P.h32(F2 + 8), lits)                # inline data word: listed as a literal only

    def test_data_word_is_not_decoded_as_code(self):
        r = self.funcs[F2]
        self.assertEqual(r['instructions'], 3)                  # str, b, bx lr - not the data word
        self.assertTrue(r['noncontiguous'])

    def test_system_instruction_and_hang(self):
        r = self.funcs[F3]
        self.assertEqual([s['meaning'] for s in r['sysops']], ['VBAR write'])
        self.assertTrue(any(x.get('kind') == 'self-loop (hang)' for x in r['branches']))

    def test_unsupported_computed_jump_is_reported(self):
        im = Image()
        im.put(MAIN, [LDR_PC_R0])
        f = self.P.call_graph(im.code(), roots=(MAIN,), stop_at=())
        self.assertIn('unresolved computed jump at 0xb4065400', f[MAIN]['notes'])

    def test_helper_formulas(self):
        H = self.P.helper_address
        self.assertEqual(H(0xB406A6AC, 0x3B), [(0xB01600A4, 1 << 27, 1 << 27)])     # timer gate
        self.assertEqual(H(0xB406A6AC, 51), [(0xB01600A4, 1 << 19, 1 << 19)])      # UART3 gate
        self.assertEqual(H(0xB406A728, 47), [(0xB01600AC, 1 << 15, 0), (0xB01600AC, 1 << 15, 1 << 15)])
        self.assertEqual(H(0xB406ACE0, 0x5A, 1)[2], (0xB01B0020, 1 << 26, 1 << 26))  # GPIO C26 data
        self.assertIsNone(H(0xB406A6AC, None))

    def test_baud_divisor(self):
        d = self.P.baud_divisor(115200)
        self.assertEqual((d['quotient'], d['written']), (26, 25))
        self.assertAlmostEqual(d['implied_baud_if_24MHz'], 115384.6)

    def test_trace_stops_at_dram_boundary_and_on_hangs(self):
        P = self.P
        for words, expect in (([bl(MAIN, P.DRAM_COLD)], 'DRAM init entry'), ([SELF], 'self-loop (hang)')):
            im = Image()
            im.put(MAIN, words)
            code = im.code()
            funcs = P.call_graph(code)
            t, res = P.run_trace(bytes(im.data), None, code, funcs, 2)
            self.assertTrue(res['stopped'].startswith(expect), res)
            self.assertIsNone(res['error'])

    def test_mmio_rules_are_explicit(self):
        P = self.P
        im = Image()
        im.put(MAIN, [SELF])
        code = im.code()
        for scen, written, expect in (('no-loopback', 0x800, 0x800), ('loopback', 0x800, 0xC00),
                                      ('loopback', 0x000, 0x000)):
            t = P.Trace(bytes(im.data), None, code, {}, 2, scenario=scen)
            t.mem[0xB01B0020] = written
            self.assertEqual(t._mmio_read(0xB01B0020, 4), expect)
            self.assertEqual(t.events[-1]['rule'], 'gpio_cdat')
        t = P.Trace(bytes(im.data), None, code, {}, 0, seed=0xFFFFFFFF)
        self.assertEqual(t._mmio_read(0xB01B0048, 4), 0xFFFFFFFF)
        self.assertEqual(t.events[-1]['rule'], 'seeded')
        a, b2 = t._mmio_read(0xB0168010, 4), t._mmio_read(0xB0168010, 4)
        self.assertEqual(b2 - a, 24)


def load():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))


class Evidence(unittest.TestCase):
    def setUp(self):
        self.d = load()

    def test_required_sections(self):
        for k in ('releases', 'tool_versions', 'boundary', 'execution_environment', 'call_graph', 'predram_graph',
                  'boot_code', 'config_inputs', 'structure', 'uart', 'board', 'runs', 'code0_vs_code2',
                  'dram_stage_code0_vs_code2', 'seed_dependence', 'register_inventory', 'static_only_accesses',
                  'release_comparison', 'synthetic_rules', 'emulation_audit', 'unknowns', 'findings'):
            self.assertIn(k, self.d, k)

    def test_release_identities_match_manifests(self):
        acq = {x['expanded_filename']: x for x in json.loads((ROOT / 'evidence/firmware/acquisitions.json').read_text())
               if 'expanded_filename' in x}
        loaders = json.loads((ROOT / 'evidence/firmware/stock-loaders.json').read_text())['loaders']
        self.assertEqual(set(self.d['releases']), {'koriki-v1.0', 'stock-221203', 'stock-221223', 'stock-230309',
                                                   'stock-20231014'})
        for rel, i in self.d['releases'].items():
            e = acq[i['file']]
            self.assertTrue(i['verified'])
            self.assertEqual(i['actual_sha256'], e['expanded_sha256'])
            self.assertEqual(i['expected_sha256'], e['expanded_sha256'])
            self.assertEqual(i['loader_sha256'], loaders[rel]['sha256'], rel)
        self.assertEqual(len({i['bootloader_code_sha256'] for i in self.d['releases'].values()}), 1)

    def test_findings_exist(self):
        ids = {f['id'] for f in json.loads((ROOT / 'evidence/findings.json').read_text())}
        self.assertTrue(set(self.d['findings']) <= ids, set(self.d['findings']) - ids)

    def test_brief_functions_present_in_the_graph(self):
        g = self.d['call_graph']
        for va in ('0xb4065400', '0xb4065ff8', '0xb40665d0', '0xb4069440', '0xb4066784', '0xb406a608', '0xb40699e8',
                   '0xb4069254', '0xb406622c', '0xb40664f0', '0xb40691a4'):
            self.assertTrue(g[va]['analysed'], va)
        self.assertFalse(g['0xb40673f4']['analysed'])        # the DRAM routine is recorded, not entered
        self.assertEqual(g['0xb40690b8']['callees'], ['0xb40673f4'])
        self.assertIn('0xb40690b8', g['0xb40665d0']['callees'])

    def test_boot_code_divergence_is_confined_to_adfu_check(self):
        inv = self.d['register_inventory']
        only2 = [r for r in inv if r['boot_code_condition'] == 'code 2 only']
        self.assertTrue(only2)
        self.assertEqual({r['function_name'] for r in only2}, {'adfu_check'})
        self.assertTrue(all(int(r['register_address'], 16) >> 12 == 0xB01B0 for r in only2))
        self.assertFalse([r for r in inv if r['boot_code_condition'] == 'code 0 only'])
        diff = self.d['code0_vs_code2']
        self.assertEqual([x['change'] for x in diff], ['insert'])
        self.assertTrue(all('[adfu_check]' in k or '[timer_count]' in k for k, _ in diff[0]['code2']))
        self.assertTrue(self.d['dram_stage_code0_vs_code2']['differences_confined_to_gpio_block'])
        self.assertEqual(self.d['dram_stage_code0_vs_code2']['afi_boot_dev'], [0x20, 0x22])
        cons = [c for c in self.d['boot_code']['consumers'] if c['pre_dram'] and c['codes_0_2_differ']]
        self.assertEqual(len(cons), 1)

    def test_runs_and_exits(self):
        r = self.d['runs']
        for lab in ('code0', 'code2', 'code0-loopback', 'code2-handshake-disabled'):
            self.assertTrue(r[lab]['result']['stopped'].startswith('DRAM init entry'), lab)
            self.assertIsNone(r[lab]['result']['error'], lab)
        for lab in ('code2-loopback', 'code2-pmu-status-bit1'):
            self.assertTrue(r[lab]['result']['stopped'].startswith('ROM re-entry'), lab)
        self.assertEqual(r['code2']['delays_requested_us'] - r['code0']['delays_requested_us'], 32000)
        self.assertEqual(r['code0']['printed'], r['code2']['printed'])
        self.assertEqual(r['code0']['pmic'], r['code2']['pmic'])

    def test_structure_facts_found(self):
        def walk(o):
            if isinstance(o, dict):
                if 'found' in o:
                    yield o
                else:
                    for v in o.values():
                        yield from walk(v)
            elif isinstance(o, list):
                for v in o:
                    yield from walk(v)
        facts = list(walk(self.d['structure']))
        self.assertGreater(len(facts), 30)
        self.assertEqual([f for f in facts if not f['found']], [])
        self.assertEqual(self.d['structure']['adfu_check']['pattern']['literal'], '0x55aa55aa')
        self.assertEqual(self.d['structure']['adfu_check']['pmic_status_register']['value'], '0x00000035')

    def test_inventory_fields_and_evidence_types(self):
        req = {'release', 'function_address', 'instruction_address', 'execution_phase', 'boot_code_condition',
               'register_address', 'access_width', 'access_type', 'register_identity', 'evidence_type', 'confidence'}
        for r in self.d['register_inventory']:
            self.assertTrue(req <= set(r), r)
            self.assertTrue(r['evidence_type'].startswith('executed'))
            if r['access_type'] == 'read':
                self.assertIn(r['read_value_source'], self.d['synthetic_rules'])
            self.assertTrue('related-SoC label' in r['register_identity'] or r['register_identity'].startswith('unknown'))
        for r in self.d['static_only_accesses']:
            self.assertTrue(r['evidence_type'].startswith('static-path'))

    def test_release_comparison(self):
        rc = self.d['release_comparison']
        self.assertTrue(rc['all_function_code_identical'])
        self.assertTrue(all(rc['data_tables_identical'].values()))
        self.assertTrue(all(v['identical'] for v in rc['executed_event_sequences'].values()))
        self.assertIn('None', rc['normalisation'])
        # 20231014's ODT/drive bytes differ and reach the DRAM boundary argument; nothing pre-DRAM consumes them
        arg = rc['dram_boundary_argument_code2']
        self.assertNotEqual(arg['stock-20231014']['record_bytes'], arg['koriki-v1.0']['record_bytes'])

    def test_seed_dependence_is_reported(self):
        for k, v in self.d['seed_dependence'].items():
            self.assertIn('control_flow_identical', v)
        # the 300 us PMIC clock-out wait depends on an unknown reset value (0xb0160084 bit 0)
        self.assertFalse(self.d['seed_dependence']['0']['control_flow_identical'])

    def test_no_private_paths_or_payloads(self):
        text = EVIDENCE.read_text(encoding='utf-8')
        for pat in (r'/home/', r'/tmp/', r'/root/', r'[A-Za-z]:\\\\', r'/Users/'):
            self.assertIsNone(re.search(pat, text), pat)
        for m in re.finditer(r'"([0-9a-f]{300,})"', text):
            self.fail('long hex blob in evidence: %d chars' % len(m.group(1)))

    def test_observation_and_emulation_are_separate(self):
        text = EVIDENCE.read_text(encoding='utf-8')
        self.assertNotIn('hardware_validated": true', text)
        self.assertNotIn('OBS-', json.dumps(self.d['register_inventory']))
        self.assertIn('synthetic', self.d['dram_stage_code0_vs_code2']['method'])

    def test_predram_contradiction_stays_open(self):
        c = {x['id']: x for x in json.loads((ROOT / 'evidence/contradictions.json').read_text())}
        self.assertFalse(c['C-PREDRAM-PATH']['status'].lower().startswith('resolved'))


FW = os.environ.get('ATM_FIRMWARE_DIR')


@unittest.skipUnless(FW and HAVE_ARM, 'set ATM_FIRMWARE_DIR to the directory holding the pinned images')
class FirmwareBacked(unittest.TestCase):
    def test_regeneration_matches_committed_evidence(self):
        import predram_analysis as P
        committed = load()
        imgs = {r: Path(FW) / i['file'] for r, i in committed['releases'].items()}
        if not all(p.exists() for p in imgs.values()):
            self.skipTest('needs all five pinned images in ATM_FIRMWARE_DIR')
        docs = {r: P.analyse_release(str(p), r) for r, p in imgs.items()}
        new = json.loads(json.dumps(P.evidence(docs, committed['reference_release'])))
        for k in committed:
            if k != 'tool_versions':
                self.assertEqual(new[k], committed[k], k)

    def test_annotated_helpers_agree_with_execution(self):
        import predram_analysis as P
        path = Path(FW) / 'koriki-v1.0.img'
        if not path.exists():
            self.skipTest('needs koriki-v1.0.img')
        doc = P.analyse_release(str(path), 'koriki-v1.0')
        static = [r for r in P.static_accesses(doc['code'], doc['funcs']) if r['address']]
        executed = {}
        for lab in ('code0', 'code2'):
            for r in P.executed_accesses(doc['traces'][lab], 0, lab):
                executed.setdefault(r['instruction'], set()).add(r['address'])
        checked = 0
        for s in static:
            if s['instruction'] in executed:
                self.assertIn(s['address'], executed[s['instruction']], s)
                checked += 1
        self.assertGreater(checked, 20)
