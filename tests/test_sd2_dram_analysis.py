"""Ordered trace and caller controls, plus optional five-release regeneration."""
import json
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import sd2_dram_analysis as sd  # noqa: E402

EVIDENCE = ROOT / 'evidence/firmware/sd2-dram-comparison.json'
FW = os.environ.get('ATM_FIRMWARE_DIR')
try:
    import capstone  # noqa: F401
    import unicorn  # noqa: F401
    HAVE_ARM = True
except ImportError:
    HAVE_ARM = False


def event(*, domain='mmio', op='r', addr=0xB0000000, width=4, value=0, pc=1, site=1, phase='start'):
    return (phase, domain, op, addr, width, value, pc, site, None, 'fixture')


def trace(*events):
    t = sd.Trace()
    for e in events:
        t.add(e)
    return t


def branch(pc, dest, *, link=False, cond=0xE):
    return cond << 28 | (0xB if link else 0xA) << 24 | ((dest - (pc + 8)) >> 2 & 0xFFFFFF)


def fixture():
    """Hand-encoded ARM exercises the same call, return and getter stop sites."""
    out = bytearray(sd.emu.BL_SIZE)

    def emit(addr, *words):
        struct.pack_into('<' + 'I' * len(words), out, addr - sd.emu.BASE, *words)

    main, caller, getter = sd.MAIN_CALL, sd.dram.FN['caller'], sd.dram.FN['boot_code']
    first, adfu = sd.BOOT_CODE_CALL_SITES[0], sd.dram.FN['adfu_check']
    emit(main, 0xe3a01000, branch(main + 4, caller, link=True), 0xe3500000,
         branch(main + 12, sd.MAIN_LOAD, cond=0), branch(main + 16, sd.MAIN_RECOVERY))
    emit(caller, 0xe92d4000, branch(caller + 4, first))
    emit(first, branch(first, getter, link=True), 0xe1a08000, branch(first + 8, 0xB406667C))
    emit(0xB406667C, 0xe3a00001, branch(0xB4066680, adfu, link=True),
         0xe3a00000, 0xe8bd8000)
    emit(getter, 0xe59f3004, 0xe5930c00, 0xe12fff1e, 0xB4064000)
    emit(adfu, 0xe92d4000, branch(adfu + 4, 0xB40692A0))
    emit(0xB40692A0, branch(0xB40692A0, getter, link=True), 0xe8bd8000)
    return bytes(out)


class TraceTests(unittest.TestCase):
    def test_interleaving_and_run_lengths(self):
        r, w = event(), event(op='w')
        a, b = trace(r, r, w), trace(r, w, r)
        self.assertNotEqual(a.summary(), b.summary())
        self.assertEqual(sd.first_difference(a, b)['index'], 1)
        self.assertEqual(sd.first_difference(trace(r), a)['index'], 1)
        self.assertIsNone(sd.first_difference(a, trace(r, r, w)))

    def test_exact_normalizations_do_not_hide_neighboring_events(self):
        gpio = event(addr=sd.C['dat'], pc=0xB406919C, site=0xB406936C, phase='before-adfu', value=7)
        afi = event(domain='sram', op='w', addr=sd.dram.AFI + 5, width=1, pc=sd.AFI_DEVICE_STORE, value=0x22)
        getter = event(domain='sram', addr=sd.dram.BOOT_CODE, pc=sd.BOOT_CODE_LOAD,
                       site=sd.BOOT_CODE_CALL_SITES[0], value=2)
        unexplained = (gpio[:4] + (2,) + gpio[5:],  # unexpected width at allowed GPIO site
                       gpio[:7] + (gpio[7] + 4,) + gpio[8:],  # same GPIO address at a different site
                       afi[:3] + (sd.dram.AFI + 6,) + afi[4:],  # adjacent AFI field
                       getter[:5] + (4,) + getter[6:])  # wrong word in the verified getter
        result, counts = trace(gpio, afi, getter, *unexplained).normalized(2)
        self.assertEqual(counts, {'gpio': 1, 'afi': 1, 'boot_word': 1})
        self.assertEqual([e for _, e in result.runs[2:]], list(unexplained))
        self.assertEqual(result.count, 6)


@unittest.skipUnless(HAVE_ARM, 'requires Unicorn and Capstone')
class SyntheticCallerTests(unittest.TestCase):
    def test_boot_code_word_is_read_by_executed_caller(self):
        case = sd.Case('synthetic', 'control')
        a, h0 = sd.execute(fixture(), case, 0)
        b, h2 = sd.execute(fixture(), case, 2)
        c = sd.compare_runs(a, h0, b, h2)
        self.assertTrue(c['boot_code_provenance_ok'])
        self.assertEqual([[r['value'] for r in row] for row in c['boot_code_reads']], [[0, 0], [2, 2]])
        self.assertEqual(h2.reg('r8'), 2)
        self.assertEqual([x['phase'] for x in h2.boundaries], ['start', 'before-adfu', 'after-adfu', 'terminal'])
        self.assertEqual(b['outcome'], 'unmodelled-outcome')  # fixture intentionally has no DRAM
        wrong = sd.compare_runs(a, h0, a, h0)
        self.assertFalse(wrong['boot_code_provenance_ok'])

    def test_models_and_scripts_are_independent(self):
        address = 0xB01B00B4
        case = sd.Case('synthetic', 'control', sd.dram.Scenario(training=[False, True]),
                       pmic={0x35: 8}, ram=sd.dram.Ram(read_xor={0x10: 1}),
                       c10_rule=('script', [0, 1], 0), gpio_initial={sd.C['inen']: 0xa00},
                       initial_mmio={address: 0x1234})
        a = sd.ComparisonHarness(fixture(), case, 0)
        b = sd.ComparisonHarness(fixture(), case, 2)
        a.s.training[0] = True
        a.gpio.inputs[sd.C10][1][0] = 1
        a.gpio.write(sd.C['inen'], 0x400)
        a.pmic.write(0x35, 0xffff)
        a.ram.read_xor[0x10] = 42
        a.cells['sentinel'] = 1
        a.regs[address] = 0x5678
        self.assertTrue(a._training_passes())
        self.assertFalse(b._training_passes())
        self.assertTrue(b._training_passes())
        self.assertEqual(b.gpio.inputs[sd.C10][1], [0, 1])
        self.assertEqual(b.gpio.regs[sd.C['inen']], 0xa00)
        self.assertEqual(b.pmic.read(0x35), 8)
        self.assertEqual(b.ram.read_xor, {0x10: 1})
        self.assertEqual(b.cells, {})
        self.assertEqual(b._oracle(address), (0x1234, 'unsupported GPIO/pad semantics: per-address storage or zero'))
        self.assertEqual(case.scenario.training, [False, True])

    def test_seeded_execution_is_reproducible(self):
        case = sd.Case('synthetic', 'control', initial_mmio={sd.C['dat']: 0xA5})
        a, h0 = sd.execute(fixture(), case, 2)
        b, h1 = sd.execute(fixture(), case, 2)
        self.assertEqual(a, b)
        self.assertEqual(h0.ordered.runs, h1.ordered.runs)
        self.assertEqual(h0.boundaries, h1.boundaries)


class CommittedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(EVIDENCE.read_bytes())

    def pair(self, name, rel=sd.REFERENCE):
        return self.doc['distinct_pairs'][self.doc['releases'][rel]['pairs'][name]]

    def test_all_releases_and_cases_reach_expected_scope(self):
        self.assertEqual(set(self.doc['releases']), set(sd.RELEASES))
        self.assertEqual(set(self.doc['scenarios']), {case.name for case in sd.cases()})
        for rel, release in self.doc['releases'].items():
            for case in release['pairs']:
                with self.subTest(release=rel, case=case):
                    p = self.pair(case, rel)
                    self.assertTrue(p['comparison']['boot_code_provenance_ok'])
                    self.assertTrue(p['comparison']['gpio_reference_agreement'])
                    self.assertEqual(p['comparison']['same_after_expected_differences'], case != 'gpio-exact-echo')
                    for model in p['independent_models'].values():
                        if model['memory_test']:
                            self.assertTrue(model['memory_test']['matches'])
                        if model['dram_core']:
                            self.assertTrue(model['dram_core']['writes_match'])
                            self.assertIsNot(model['dram_core']['final_record_matches'], False)
                        if model['failure_mapping']:
                            self.assertTrue(model['failure_mapping']['matches'])
                    for r in p['runs'].values():
                        self.assertEqual(r['downstream_gpio_accesses'], [])
                        self.assertNotIn(r['outcome'], ('emulator-fault', 'instruction-limit', 'unmodelled-outcome'))

    def test_reference_and_training_retries(self):
        p = self.pair('reference')
        self.assertEqual(p['comparison']['afi_byte_offsets_changed'], [5])
        a, b = (p['runs'][bc] for bc in ('0', '2'))
        self.assertEqual((a['capacity_mib'], b['capacity_mib']), (256, 256))
        self.assertEqual((a['afi']['decoded']['boot_dev'], b['afi']['decoded']['boot_dev']), (0x20, 0x22))
        self.assertEqual(b['adfu']['c10_samples'], 32)
        self.assertEqual(b['record_selection'], 'secondary')
        transient = next(row for row in p['comparison']['boundaries'] if row['phase'] == 'after-adfu')
        self.assertIn('r12', transient['expected']['transient_cpu'])
        self.assertIn('cpsr', transient['expected']['transient_cpu'])
        self.assertEqual(a['dram_entry']['cpu'], b['dram_entry']['cpu'])
        self.assertEqual([t['ranks'] for t in b['training']], [2, 1])
        auto = self.pair('bus-auto-patched-record')['runs']['2']
        self.assertEqual([(t['ranks'], t['width_bits']) for t in auto['training']],
                         [(2, 32), (1, 32), (2, 16), (1, 16)])
        two = self.pair('two-ranks-first-attempt')['runs']['2']
        self.assertEqual(len(two['training']), 1)
        self.assertEqual(two['capacity_mib'], 512)

    def test_failure_with_afi_and_diagnostic_failure(self):
        for name, expected in [('persistent-training-failure', '0x1017fa11'), ('zq-timeout', '0x1747fa11'),
                               ('phy-init-timeout', '0x1747fa11'), ('dfi-timeout', '0x1747fa11'),
                               ('capacity-exponent-overflow', '0x1747fa11')]:
            for r in self.pair(name)['runs'].values():
                self.assertEqual(r['dram_return'], expected)
                self.assertEqual(r['outcome'], 'returned-dram-failure')
                self.assertTrue(r['afi']['generated'])
                self.assertIsNone(r['capacity_mib'])
                self.assertFalse(r['main_continuation_boundary_reached'])
                self.assertGreater(r['ini_primary_stores'], 0)
        for name in ('memory-test-dropped-write', 'memory-test-stuck-bit', 'memory-test-read-error',
                     'memory-test-open-tail'):
            r = self.pair(name)['runs']['2']
            self.assertEqual(r['outcome'], 'cold-success-diagnostic-failure', name)
            self.assertEqual(r['memory_test']['status'], 'failed')
            self.assertTrue(r['main_continuation_boundary_reached'])

    def test_poll_and_recovery_controls(self):
        for name in ('dram-init-hang', 'training-other-status', 'controller-stuck-config', 'pmic-version-zero'):
            r = self.pair(name)['runs']['2']
            self.assertEqual(r['outcome'], 'bounded-unbounded-poll', name)
            self.assertIsNotNone(r['terminal']['known_poll'])
            self.assertFalse(r['afi']['generated'])
        for name in ('gpio-exact-echo', 'adfu-request', 'pmic-read-error'):
            r = self.pair(name)['runs']['2']
            self.assertEqual(r['outcome'], 'adfu-before-dram')
            self.assertIsNone(r['dram_entry'])
            self.assertFalse(r['afi']['generated'])
        echo = self.pair('gpio-exact-echo')
        self.assertEqual(echo['runs']['0']['outcome'], 'cold-success')
        self.assertIsNotNone(echo['comparison']['normalized_first'])

    def test_resume_primary_record_and_no_afi(self):
        for name, outcome in [('resume-valid', 'resume-vector-transfer'),
                              ('resume-vector-bit31-no-alarm', 'resume-vector-transfer'),
                              ('resume-alarm-check', 'resume-power-off'), ('resume-zq-timeout', 'resume-power-off'),
                              ('resume-training-failure', 'resume-power-off'), ('resume-stale-capacity', 'resume-vector-transfer')]:
            for r in self.pair(name)['runs'].values():
                self.assertEqual(r['outcome'], outcome)
                self.assertEqual(r['record_selection'], 'primary')
                self.assertEqual(r['afi']['stores'], 0)
                self.assertFalse(r['main_continuation_boundary_reached'])
                if name != 'resume-zq-timeout':
                    self.assertIn('0x3f', r['pir_requests'])

    def test_geometry_and_observation_are_distinct(self):
        d = self.doc['geometry']
        self.assertEqual(d['devices'], 180)
        self.assertEqual(sum(c['hypotheses'] for c in d['observable_outcome_classes']), 180)
        self.assertTrue(d['capacity_misreported_but_memtest_ok'])
        for row in d['paired_checks'].values():
            self.assertEqual(row['caller']['0'], row['caller']['2'])
            if row['isolated'] is not None:
                self.assertEqual(row['caller']['2'], row['isolated'])
        obs = self.doc['obs_001']
        self.assertEqual(obs['controller'], '0xb0238000')
        self.assertTrue(obs['memory_property_matches'])
        self.assertTrue(obs['previous_command_line_agrees'])
        self.assertIn('live AFI', obs['unavailable'])


@unittest.skipUnless(FW and HAVE_ARM, 'set ATM_FIRMWARE_DIR to the directory holding the pinned expanded images')
class FirmwareBackedTests(unittest.TestCase):
    def test_byte_exact_regeneration(self):
        if not all((Path(FW) / f'{rel}.img').is_file() for rel in sd.RELEASES):
            self.skipTest('needs all five pinned expanded images')
        self.assertEqual(sd.evidence_bytes(sd.build_evidence(FW)), EVIDENCE.read_bytes())

    def test_afi_stores_even_when_the_final_value_is_unchanged(self):
        if not (Path(FW) / f'{sd.REFERENCE}.img').is_file():
            self.skipTest('needs pinned Koriki v1.0')
        loader, _, _ = sd.load_release(FW, sd.REFERENCE)
        case = sd.Case('afi-store-observation', 'control')
        a, h = sd.execute(loader, case, 2)
        partial, _ = sd.execute(loader, case, 2, budget=h.insns - h.budget_start - 8)
        self.assertGreater(partial['afi']['stores'], 0)
        self.assertFalse(partial['afi']['generated'])
        self.assertEqual(partial['outcome'], 'instruction-limit')
        case.afi_seed = bytes.fromhex(a['afi']['bytes'])
        b, _ = sd.execute(loader, case, 2)
        self.assertTrue(b['afi']['generated'])
        self.assertFalse(b['afi']['changed'])
        self.assertGreater(b['afi']['stores'], 0)
        case.pmic[0x35] = 2
        c, _ = sd.execute(loader, case, 2)
        self.assertTrue(c['afi']['decoded']['magic_ok'])
        self.assertFalse(c['afi']['generated'])
        self.assertFalse(c['main_continuation_boundary_reached'])
        self.assertEqual(c['outcome'], 'adfu-before-dram')

    def test_unknown_resume_address_is_not_run(self):
        if not (Path(FW) / f'{sd.REFERENCE}.img').is_file():
            self.skipTest('needs pinned Koriki v1.0')
        loader, _, _ = sd.load_release(FW, sd.REFERENCE)
        case = sd.Case('unknown-resume-target', 'control', pmic=sd.dram.resume_pmic(vector=0x00109000).initial)
        a, _ = sd.execute(loader, case, 2)
        self.assertEqual(a['terminal']['kind'], 'unmodelled resume target')
        self.assertEqual(a['terminal']['target'], '0x109000')
        self.assertFalse(a['main_continuation_boundary_reached'])


if __name__ == '__main__':
    unittest.main()
