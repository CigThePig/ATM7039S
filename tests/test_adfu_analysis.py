"""ADFU decision routine 0xb4069254 and its GPIO loopback (tools/adfu_analysis.py, tools/gpio_model.py).

* Model     - gpio_model.GpioModel and the independent reference_model on synthetic inputs (no firmware).
* Evidence  - the committed evidence/firmware/adfu-loopback.json (no firmware).
* FirmwareBacked - skipped unless ATM_FIRMWARE_DIR holds koriki-v1.0.img (and, for full regeneration, all five
  images plus ATM_SOURCES_DIR with the pinned sources from tools/fetch_sources.py).
"""
import json
import os
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from gpio_model import GpioModel, C, C10, C11, PULLCTL   # noqa: E402

EVIDENCE = ROOT / 'evidence/firmware/adfu-loopback.json'
OUTEN, INEN, DAT, PULL1 = C['outen'], C['inen'], C['dat'], PULLCTL[1]
PATTERN = 0x55AA55AA
# Constants as decoded from the firmware (asserted against the image in FirmwareBacked).
K = dict(status_register=0x35, pattern=PATTERN, compare=PATTERN, pull_register=PULL1, outen=OUTEN, inen=INEN, dat=DAT,
         loop_count=32, pull_clear=0x20000, status_mask=2, status_clear=3, delay_ms=1)


def ref(**kw):
    import adfu_analysis as A
    args = dict(boot_code=2, arg=1, pmic_status=0, initial={}, c10_rule=('const', 0))
    args.update(kw)
    return A.reference_model(K, **args)


def bits(w):
    return [(w >> i) & 1 for i in range(32)]


class Model(unittest.TestCase):
    def test_mixed_read_semantics(self):
        g = GpioModel(initial={OUTEN: 0x800, INEN: 0x400, DAT: 0x800}, inputs={C10: ('const', 1)}, undriven=0)
        self.assertEqual(g.read(DAT), 0x800 | 0x400)            # C11 latch + C10 input; others undriven 0
        g2 = GpioModel(initial={OUTEN: 0x800, INEN: 0x400, DAT: 0x800}, inputs={C10: ('const', 1)},
                       read_semantics='latch')
        self.assertEqual(g2.read(DAT), 0x800)                    # inputs invisible

    def test_follow_invert_and_windows(self):
        g = GpioModel(initial={OUTEN: 0x800, INEN: 0x400}, inputs={C10: ('follow', C11)})
        g.write(DAT, 0x800)
        self.assertEqual(g.read(DAT) & 0x400, 0x400)
        g.write(DAT, 0)
        self.assertEqual(g.read(DAT) & 0x400, 0)
        self.assertEqual(g.win, -1)
        g.advance(1000)
        g.read(DAT)
        self.assertEqual(g.win, 0)
        gi = GpioModel(initial={OUTEN: 0x800, INEN: 0x400}, inputs={C10: ('invert', C11)})
        self.assertEqual(gi.read(DAT) & 0x400, 0x400)

    def test_script_and_delay(self):
        g = GpioModel(initial={INEN: 0x400}, inputs={C10: ('script', [1, 0, 1], 0)})
        seen = []
        for _ in range(4):
            g.advance(1000)
            seen.append(g.read(DAT) >> 10 & 1)
        self.assertEqual(seen, [0, 1, 0, 1])                     # first read opens no window yet
        d = GpioModel(initial={OUTEN: 0x800, INEN: 0x400}, inputs={C10: ('delay', C11, 1500, 0)})
        d.write(DAT, 0x800)
        d.advance(1000)
        self.assertEqual(d.read(DAT) >> 10 & 1, 0)               # not yet visible
        d.advance(1000)
        self.assertEqual(d.read(DAT) >> 10 & 1, 1)

    def test_unexpected_and_passthrough(self):
        g = GpioModel()
        self.assertEqual(g.read(0xB01B0048), 0)
        g.write(0xB01B0090, 5)
        self.assertEqual([u['address'] for u in g.unexpected], ['0xb01b0048', '0xb01b0090'])
        p = GpioModel(strict=False)
        p.write(0xB01B0090, 5)
        self.assertEqual(p.read(0xB01B0090), 5)
        self.assertEqual(p.unexpected, [])
        self.assertEqual(len(p.passthrough), 2)

    def test_transitions_logged(self):
        g = GpioModel(initial={PULL1: 0xFFFFFFFF})
        g.write(PULL1, 0xFFFDFFFF)
        self.assertEqual(g.log[-1]['changed'], '0x00020000')


class Reference(unittest.TestCase):
    def test_pmic_precedence_and_writeback(self):
        for code, arg in ((0, 1), (2, 0), (2, 1)):
            r = ref(boot_code=code, arg=arg, pmic_status=0x0002, c10_rule=('follow', C11))
            self.assertTrue(r['decision'].startswith('adfu (PMIC'))
            self.assertFalse(r['gpio_test'])
            self.assertEqual(r['gpio_writes'], [])
            self.assertEqual(r['pmic_writes'], [dict(reg=0x35, value=0)])
        self.assertEqual(ref(pmic_status=0xFF06)['pmic_writes'][0]['value'], 0xFF04)   # high bits kept
        self.assertEqual(ref(pmic_status=0x0001)['pmic_writes'], [])                   # bit 0 alone is ignored
        f = ref(pmic_fail=True)
        self.assertEqual((f['decision'][:4], f['pmic_writes'][0]['value']), ('adfu', 0xFFFC))

    def test_guards(self):
        self.assertEqual(ref(boot_code=0, c10_rule=('follow', C11))['decision'], 'return (boot code 0)')
        self.assertEqual(ref(arg=0, c10_rule=('follow', C11))['decision'], 'return (argument 0)')
        for code in (1, 4, 5, 0x80000000):
            self.assertTrue(ref(boot_code=code, c10_rule=('follow', C11))['gpio_test'])

    def test_loopback_bit_order_and_all_bits(self):
        r = ref(c10_rule=('follow', C11))
        self.assertEqual(r['sent'], bits(PATTERN))
        self.assertEqual(r['received'], PATTERN)
        self.assertTrue(r['decision'].startswith('adfu (loopback'))
        self.assertEqual(r['delays_ms'], 32)
        last = ref(c10_rule=('follow_except', C11, {31: 1}))
        self.assertEqual(last['received'], PATTERN | 1 << 31)
        self.assertEqual(last['decision'], 'return (loopback mismatch)')

    def test_negative_inputs(self):
        self.assertEqual(ref()['received'], 0)
        self.assertEqual(ref(c10_rule=('const', 1))['received'], 0xFFFFFFFF)
        self.assertEqual(ref(c10_rule=('invert', C11))['received'], ~PATTERN & 0xFFFFFFFF)
        self.assertEqual(ref(c10_rule=('delay', C11, 1500, 0))['received'], (PATTERN << 1) & 0xFFFFFFFF)

    def test_latch_semantics_can_never_match(self):
        for init in ({}, {DAT: 0x400}):
            r = ref(c10_rule=('follow', C11), read_semantics='latch', initial=init)
            self.assertIn(r['received'], (0, 0xFFFFFFFF))

    def test_restore_and_persistent_state(self):
        init = {OUTEN: 0x0000F0F0, INEN: 0x00FF0F00, DAT: 0x12345678, PULL1: 0xFFFFFFFF}
        r = ref(initial=init, read_semantics='latch')
        fin = {int(a, 16): int(v, 16) for a, v in r['final'].items()}
        self.assertEqual(fin[OUTEN], init[OUTEN])
        self.assertEqual(fin[INEN], init[INEN])
        self.assertEqual(fin[PULL1], 0xFFFDFFFF)
        self.assertEqual(fin[DAT], init[DAT] & ~0x800)          # latch semantics: only bit 11 changes
        mixed = ref(initial=init)                                # mixed semantics: non-output latch bits rewritten
        self.assertNotEqual(int(mixed['final'][f'0x{DAT:08x}'], 16), init[DAT] & ~0x800)


def load():
    return json.loads(EVIDENCE.read_text(encoding='utf-8'))


EXPECTED = {
    'pmic-0x0000': 'normal', 'pmic-0x0001-bit0-only': 'normal', 'pmic-0x0002-bit1': 'ADFU',
    'pmic-0x0003-bits01': 'ADFU', 'pmic-0xff06-bit1-plus-high': 'ADFU', 'pmic-0x8005-unrelated-no-bit1': 'normal',
    'pmic-read-failure': 'ADFU', 'pmic-bit1-code0': 'ADFU', 'pmic-bit1-arg0': 'ADFU',
    'guard-code0-loopback': 'normal', 'guard-arg0-loopback': 'normal', 'input-loopback': 'ADFU',
    'input-low': 'normal', 'input-high': 'normal', 'input-inverted': 'normal', 'input-one-bit-delayed': 'normal',
    'input-wrong-last-bit': 'normal', 'input-wrong-first-bit': 'normal', 'input-matches-from-bit-8': 'normal',
    'semantics-latch-loopback': 'normal', 'init-ones-loopback': 'ADFU', 'init-mixed-loopback': 'ADFU',
}


class Evidence(unittest.TestCase):
    def setUp(self):
        self.d = load()
        self.s = {x['name']: x for x in self.d['scenarios']}

    def test_provenance(self):
        acq = {x['expanded_filename']: x for x in json.loads((ROOT / 'evidence/firmware/acquisitions.json').read_text())
               if 'expanded_filename' in x}
        for rel, i in self.d['releases'].items():
            self.assertTrue(i['verified'])
            self.assertEqual(i['actual_sha256'], acq[i['file']]['expanded_sha256'])
        self.assertEqual(len(self.d['releases']), 5)
        self.assertTrue(all(self.d['regions']['identical_across_releases'].values()))
        self.assertTrue(self.d['anchors']['all_match_in_every_release'])
        self.assertTrue(all(v['agree'] for v in self.d['other_releases_spot_check'].values()))

    def test_findings_exist(self):
        ids = {f['id'] for f in json.loads((ROOT / 'evidence/findings.json').read_text())}
        self.assertTrue(set(self.d['findings']) <= ids, set(self.d['findings']) - ids)

    def test_every_scenario_agrees_with_reference(self):
        bad = [x['name'] for x in self.d['scenarios'] if not x['comparison']['agree']]
        self.assertEqual(bad, [])
        self.assertEqual(self.d['scenario_summary']['errors'], [])
        self.assertGreaterEqual(len(self.d['scenarios']), 35)

    def test_expected_outcomes(self):
        for name, want in EXPECTED.items():
            got = self.s[name]['firmware']['outcome']
            self.assertTrue(got.startswith('ADFU' if want == 'ADFU' else 'normal return'), (name, got))

    def test_pmic_path_touches_no_gpio_and_writes_back(self):
        for name, value in (('pmic-0x0002-bit1', '0x0000'), ('pmic-0x0003-bits01', '0x0000'),
                            ('pmic-0xff06-bit1-plus-high', '0xff04'), ('pmic-read-failure', '0xfffc')):
            f = self.s[name]['firmware']
            self.assertEqual(f['gpio_write_count'], 0, name)
            self.assertEqual(f['delay_calls'], 0, name)
            self.assertEqual([p['value'] for p in f['pmic'] if p['op'] == 'w'], [value], name)
        self.assertEqual([p['op'] for p in self.s['pmic-0x0001-bit0-only']['firmware']['pmic']], ['r'])

    def test_test_scenarios_drive_pattern_and_restore_directions(self):
        for x in self.d['scenarios']:
            f = x['firmware']
            if f['gpio_write_count'] == 0:
                continue
            self.assertEqual(f['driven_bits'], bits(PATTERN), x['name'])
            self.assertEqual(f['delay_calls'], 32)
            self.assertEqual(f['delay_us_requested'], 32000)
            self.assertEqual(f['final']['GPIO_COUTEN'], f['initial']['GPIO_COUTEN'], x['name'])
            self.assertEqual(f['final']['GPIO_CINEN'], f['initial']['GPIO_CINEN'], x['name'])
            self.assertEqual(int(f['final']['PAD_PULLCTL1'], 16), int(f['initial']['PAD_PULLCTL1'], 16) & ~0x20000)
            self.assertEqual(int(f['final']['GPIO_CDAT'], 16) & 0x800, 0)
            self.assertEqual(f['unexpected_gpio_accesses'], [], x['name'])
            self.assertEqual(f['other_mmio'], [], x['name'])
            sampled = sum(b << i for i, b in enumerate(f['sampled_bits']))
            self.assertEqual(f'0x{sampled:08x}', f['received_word'])

    def test_unrelated_bits_depend_on_read_semantics(self):
        self.assertNotIn('GPIO_CDAT', self.s['init-unrelated-bits-low']['firmware']['changed'])
        self.assertIn('GPIO_CDAT', self.s['init-unrelated-bits-undriven-high']['firmware']['changed'])
        self.assertIn('GPIO_CDAT', self.s['init-mixed-low']['firmware']['changed'])

    def test_stalled_timer_is_an_emulator_bound(self):
        st = self.d['stalled_timer']
        self.assertTrue(st['outcome'].startswith('instruction budget'))
        self.assertIn('no timeout', st['note'])

    def test_adfu_never_reaches_dram(self):
        fp = {x['name']: x for x in self.d['full_path']}
        self.assertFalse(fp['main code2 ideal loopback']['reached_dram_init'])
        self.assertTrue(fp['main code2 C10 low']['reached_dram_init'])
        self.assertTrue(fp['main code0 ideal loopback']['reached_dram_init'])
        for x in fp.values():
            self.assertEqual(x['unexpected'], [])
        ds = self.d['dram_stage']
        self.assertFalse(ds['code2-loopback']['reached_dram_routine'])
        self.assertTrue(ds['code2-low']['reached_dram_routine'])
        self.assertTrue(ds['code0_vs_code2_low_non_gpio_writes_identical'])
        self.assertEqual(ds['code2-low']['writes_after_test_to_test_registers'], [])
        re_ = self.d['reentry']
        self.assertTrue(re_['stopped'].startswith('jump to 0xb4060000'))
        self.assertFalse(re_['reached_dram_init'])
        self.assertEqual(re_['sp_at_jump'], '0xb4070800')
        self.assertEqual(re_['rom_copies'], [dict(dest='0xb4060000', source='0xffff5200', length='0x00002e00')])
        self.assertIn('not performed', ' '.join(re_['events']))

    def test_board_sources_and_dtbs(self):
        src = self.d['board']['sources']
        self.assertTrue(all(x['found'] for x in src))
        meanings = ' '.join(x['meaning'] for x in src)
        self.assertIn('GPIOC10 is the P_SD0_D0 pad', meanings)
        self.assertIn('PAD_PULLCTL1 bit 17 = P_SD0_D0 pull', meanings)
        for r, v in self.d['board']['dtbs'].items():
            self.assertEqual(v['gpio_74_75_specifiers'], [], r)
        f = {x['bits']: x for x in self.d['board']['board_mfp_init_sd0_fields']['fields']}
        self.assertEqual(f['19:17']['vendor_function'], 'JTAG')
        self.assertIsNone(f['16:14']['value'])
        self.assertTrue(any(x['confidence'] == 'speculative' for x in self.d['board']['interpretation']))

    def test_assumptions_explicit_and_no_hardware_claims(self):
        text = EVIDENCE.read_text(encoding='utf-8')
        self.assertTrue(self.d['model']['assumptions'])
        self.assertNotIn('hardware_validated": true', text)
        self.assertNotIn('OBS-', text)
        for pat in (r'/home/', r'/tmp/', r'/root/', r'/Users/'):
            self.assertIsNone(re.search(pat, text), pat)
        for m in re.finditer(r'"([0-9a-f]{300,})"', text):
            self.fail('long hex blob')

    def test_contradiction_stays_open(self):
        c = {x['id']: x for x in json.loads((ROOT / 'evidence/contradictions.json').read_text())}
        self.assertFalse(c['C-PREDRAM-PATH']['status'].lower().startswith('resolved'))


FW = os.environ.get('ATM_FIRMWARE_DIR')
SRC = os.environ.get('ATM_SOURCES_DIR')


@unittest.skipUnless(FW, 'set ATM_FIRMWARE_DIR to the directory holding the pinned images')
class FirmwareBacked(unittest.TestCase):
    def setUp(self):
        import adfu_analysis as A
        p = Path(FW) / 'koriki-v1.0.img'
        if not p.exists():
            self.skipTest('needs koriki-v1.0.img')
        self.A = A
        self.doc = A.analyse(str(p), 'koriki-v1.0')

    def test_decoded_constants(self):
        self.assertEqual(self.A.decoded_constants(self.doc['code']), K)

    def test_single_scenarios_match_committed(self):
        committed = {x['name']: x for x in load()['scenarios']}
        k = self.A.decoded_constants(self.doc['code'])
        for spec in self.A.SCENARIOS:
            if spec[0] in ('input-loopback', 'pmic-read-failure', 'init-mixed-low', 'guard-code0-loopback'):
                got = json.loads(json.dumps(self.A.run_scenario(self.doc, k, *spec)))
                self.assertEqual(got, committed[spec[0]], spec[0])

    def test_full_regeneration(self):
        if not SRC:
            self.skipTest('set ATM_SOURCES_DIR for full regeneration')
        committed = load()
        imgs = {r: Path(FW) / i['file'] for r, i in committed['releases'].items()}
        if not all(p.exists() for p in imgs.values()):
            self.skipTest('needs all five images')
        docs = {r: self.A.analyse(str(p), r) for r, p in imgs.items()}
        new = json.loads(json.dumps(self.A.evidence(docs, committed['reference_release'], SRC)))
        for key in committed:
            if key != 'tool_versions':
                self.assertEqual(new[key], committed[key], key)
