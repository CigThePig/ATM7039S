"""Regression tests for the PR #6 DRAM reconstruction (tools/dram_complete.py, ddr_model mode 1).

Without firmware these tests check the independent models against each other, against
boundary values, and against the committed firmware-derived evidence
(evidence/firmware/stock-dram-complete.json). The harness itself is exercised on
synthetic ARM code. Tests that re-run the firmware need ATM7039S_STOCK_LOADERS
(a directory with loader-<release>.bin, 448 sectors from disk offset 0x200200).
"""
import json
import os
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ddr_model as dm  # noqa: E402

EVIDENCE_PATH = ROOT / 'evidence/firmware/stock-dram-complete.json'
EVIDENCE = json.loads(EVIDENCE_PATH.read_text())
RELEASES = ('stock-221203', 'stock-221223', 'stock-230309', 'stock-20231014')

try:
    import unicorn  # noqa: F401
    import capstone  # noqa: F401
    HAVE_ENGINES = True
except ImportError:  # pragma: no cover
    HAVE_ENGINES = False

if HAVE_ENGINES:
    import dram_complete as dc
    import ddr_emulate as de
else:  # pragma: no cover
    dc = de = None

LOADERS = os.environ.get('ATM7039S_STOCK_LOADERS')


def need_dc(test):
    return unittest.skipUnless(HAVE_ENGINES, 'unicorn/capstone not installed')(test)


@need_dc
class TestMemtestModel(unittest.TestCase):
    """Properties of the reconstructed 0xb406631c algorithm (independent model, no firmware)."""

    def test_access_counts_for_256_mib(self):
        prints, acc, verdict = dc.memtest_model(256, dc.Ram('wrap', 256 << 20))
        self.assertEqual(verdict, 'ok')
        w = [a for k, a, _ in acc if k == 'w']
        self.assertEqual(len(w), 24 + 252)            # phase A: i = 4 .. 2^25; phase B: 252 stride points
        self.assertEqual(w[:3], [0x10, 0x20, 0x40])
        self.assertEqual(max(w[:24]), 0x8000000)       # phase A stops at half the claimed capacity
        self.assertEqual(w[24], 0x40)
        self.assertLess(max(w), 256 << 20)
        self.assertEqual(prints, ['==ddr_test 256 MB ==', '== ok=='])

    def test_value_equals_word_address(self):
        _, acc, _ = dc.memtest_model(256, dc.Ram('wrap', 256 << 20))
        for k, a, v in acc:
            self.assertEqual(a, 4 * v)

    def test_single_bit_overestimate_is_invisible(self):
        """A device half the claimed size (wrap-around) passes: the highest phase-A address aliases byte 0,
        which is never written, and the 0x104450 stride never aliases inside 256 entries."""
        for claimed in (128, 256, 512, 1024, 2048):
            _, _, v = dc.memtest_model(claimed, dc.Ram('wrap', (claimed // 2) << 20))
            self.assertEqual(v, 'ok', claimed)

    def test_two_bit_overestimate_is_detected_in_phase_a(self):
        for claimed in (256, 512, 1024):
            prints, _, v = dc.memtest_model(claimed, dc.Ram('wrap', (claimed // 4) << 20))
            self.assertEqual(v, 'addr-fail')
            i = (claimed << 18) // 4                  # first phase-A index whose address aliases a later write
            self.assertEqual(prints[-1], f'addr:ddr_test fail {i}, 0x{2 * i:x} ')

    def test_phase_b_never_aliases_under_wrap(self):
        _, acc, _ = dc.memtest_model(2048, dc.Ram('wrap', 2048 << 20))
        n_a = ((2048 << 18).bit_length() - 1) - 2         # phase-A writes: i = 2^2 .. 2^28
        b = [a for k, a, _ in acc if k == 'w'][n_a:]
        self.assertEqual(b[0], 0x40)
        for size_mib in (16, 32, 64, 128):
            self.assertEqual(len({a % (size_mib << 20) for a in b}), len(b))

    def test_degenerate_sizes(self):
        for cap in (0, 16384, 32768):                   # N = cap << 18 wraps to 0 in 32 bits
            p, acc, v = dc.memtest_model(cap, dc.Ram('wrap', 256 << 20))
            self.assertEqual((v, acc), ('ok', []), cap)
        _, _, v = dc.memtest_model(4096, dc.Ram('wrap', 256 << 20))
        self.assertEqual(v, 'outside-dram-window 0x80000000')

    def test_faults(self):
        self.assertEqual(dc.memtest_model(256, dc.Ram('wrap', 256 << 20, stuck_low=1 << 20))[2], 'addr-fail')
        self.assertEqual(dc.memtest_model(256, dc.Ram('wrap', 256 << 20, write_drop=(0x1004,)))[2], 'ok')
        self.assertEqual(dc.memtest_model(256, dc.Ram('wrap', 256 << 20, write_drop=(0x40 + 0x104450,)))[2], 'data-fail')
        self.assertEqual(dc.memtest_model(256, dc.Ram('open', 128 << 20))[2], 'addr-fail')


@need_dc
class TestConversionsAndCodes(unittest.TestCase):

    def test_afi_size_conversion(self):
        self.assertEqual(dc.afi_ddr_size(256), 0x10000000)
        self.assertEqual(dc.afi_ddr_size(2048), 0x80000000)
        self.assertEqual(dc.afi_ddr_size(4096), 0)       # 32-bit overflow
        self.assertEqual(dc.afi_ddr_size(0x1FFFF), dc.afi_ddr_size(0xFFFF))

    def test_uboot_rule(self):
        afi = dict(magic_ok=True, ddr_size=0x10000000, boot_mode=0)
        self.assertEqual(dc.uboot_ram_size(afi)['gd_ram_size'], 0x10000000)
        for size in (0, 7 << 20):
            r = dc.uboot_ram_size(dict(magic_ok=True, ddr_size=size, boot_mode=0))
            self.assertEqual((r['gd_ram_size'], r['fallback']), (0x1F000000, True))
        self.assertEqual(dc.uboot_ram_size(dict(magic_ok=True, ddr_size=8 << 20, boot_mode=0))['gd_ram_size'], 8 << 20)
        r = dc.uboot_ram_size(dict(magic_ok=False, ddr_size=0x10000000, boot_mode=0))
        self.assertEqual((r['gd_ram_size'], r['boot_mode']), (0x1F000000, 1))

    def test_uboot_rule_matches_pr5_evidence(self):
        bc = json.loads((ROOT / 'evidence/firmware/stock-boot-chain.json').read_text())
        self.assertIn('0x1f000000', json.dumps(bc).lower())

    def test_code_collapse(self):
        self.assertEqual(dc.returned_code(0x1017FA11), 0x1017FA11)
        for c in (0x2A00FA11, 0x9A00FA11, 0xDF00FA11, 0xF000FA11, 0xC000FA11):
            self.assertEqual(dc.returned_code(c), 0x1747FA11)
        self.assertEqual(dc.returned_code(0), 0)


class TestModeOneModel(unittest.TestCase):
    """ddr_model.run(mode=1) against the committed emulation of the firmware's resume pass."""

    def setUp(self):
        mc = EVIDENCE['mode_comparison']
        r = mc['mode1']['record']
        self.rec = dm.Record(r['clock_mhz'], r['capacity_mib'], r['bus_sel'], r['cs'], r['type'], r['rcc'], r['rdodt'],
                             r['wrodt'], r['drv'])
        self.diff = {d['register']: d for d in mc['differing_registers']}
        self.model = dm.run(self.rec, dm.Hardware(reset=dm.ResetAll(0)), mode=1)

    def test_resume_uses_stored_record(self):
        self.assertEqual((self.rec.clock_mhz, self.rec.capacity_mib, self.rec.cs, self.rec.rcc), (468, 256, 1, 0x48))
        self.assertEqual(self.model['prints'], EVIDENCE['mode_comparison']['mode1']['prints'])

    def test_differing_registers(self):
        got = {}
        for w in self.model['writes']:
            got.setdefault(w.register, []).append(hex(w.value))
        for name, d in self.diff.items():
            self.assertEqual(got.get(name), d['mode1'], name)

    def test_mode1_specific_values(self):
        last = {w.register: w.value for w in self.model['writes']}
        self.assertEqual(last['PUBL.PTR2'], 46)              # F / 10
        self.assertEqual(last['uPCTL.TRFC'], 75)             # 160 ns class: density 256 MiB, not 2048
        pirs = [w.value for w in self.model['writes'] if w.register == 'PUBL.PIR']
        self.assertEqual(pirs, [0x10000000, 0x3F, 0x81])
        mcmd = [w.value & 0xF for w in self.model['writes'] if w.register == 'uPCTL.MCMD']
        self.assertEqual(mcmd, [1] * 8 + [2] * 8 + [0, 1] + [2] * 8)

    def test_no_retry_in_mode1(self):
        r = dm.run(self.rec, dm.Hardware(ranks=0), mode=1)
        self.assertTrue(r['result'].startswith('0x1017fa11'))
        self.assertEqual(sum(1 for p in r['prints'] if p.startswith('DRAM init')), 1)

    def test_mode0_unchanged(self):
        ev = json.loads((ROOT / 'evidence/firmware/stock-ddr-timing.json').read_text())
        r = ev['releases']['stock-20231014']['bootloader_ini']['second_record']
        m = dm.run(dm.Record(**r), dm.Hardware(ranks=1, width=16, col_code=2, row_code=1, reset=dm.ResetAll(0)))
        self.assertEqual(m['prints'][-1], 'Ok:DCU_CFG:0x202c,256MByte Cap.')


class TestProbeCorrection(unittest.TestCase):
    """C-PROBE-NOALIAS: a row probe without an alias gives r = 0, not an error."""

    def rec(self, bus_sel=1):
        return dm.Record(468, 0, bus_sel, 0, 0x10, 0, 2, 2, 9)

    def test_no_row_alias_reports_13_rows(self):
        m = dm.run(self.rec(), dm.Hardware(col_code=2, row_code=None))
        self.assertEqual(m['result'], '0x0')
        self.assertEqual(m['param_after']['capacity_mib'], 128)

    def test_f000fa11_unreachable(self):
        """Exponent 31 always ends the row search before 32, for every bus, column code and probe result."""
        for bus_sel in (0, 1):
            for c in range(4):
                for r in (None, 0, 1, 2, 3):
                    m = dm.run(self.rec(bus_sel), dm.Hardware(width=32, col_code=c, row_code=r))
                    self.assertNotIn('0xf000fa11', m['result'], (bus_sel, c, r))
        m = dm.run(self.rec(bus_sel=0), dm.Hardware(width=32, col_code=3, row_code=None))
        self.assertEqual(m['param_after']['capacity_mib'], 2048)          # x32, c = 3: exponent 31 at k = 2

    def test_committed_scenarios(self):
        t = EVIDENCE['training']
        self.assertEqual(t['unsupported-geometry-rows']['prints'][-1], 'Ok:DCU_CFG:0x200c,128MByte Cap.')
        self.assertEqual(t['unsupported-geometry-cols']['prints'][-1], 'Ok:DCU_CFG:0x234e,1024MByte Cap.')


class TestCommittedEvidence(unittest.TestCase):

    def test_releases_and_identity(self):
        self.assertEqual(tuple(EVIDENCE['releases']), RELEASES)
        self.assertEqual(len({r['code_sha256'] for r in EVIDENCE['releases'].values()}), 1)
        self.assertEqual(len({json.dumps(r['function_hashes'], sort_keys=True) for r in EVIDENCE['releases'].values()}), 1)
        for k, v in EVIDENCE['identical_across_releases'].items():
            self.assertTrue(v, k)

    def test_mode1_sweep_all_releases(self):
        for rel, s in EVIDENCE['mode1_model_sweep_all'].items():
            self.assertEqual((s['count'], s['mismatches']), (1101, []), rel)

    def test_memtest_model_equals_emulation(self):
        for name, row in EVIDENCE['memtest'].items():
            self.assertTrue(row['model_equals_emulation'] or row['model_verdict'].startswith('outside'), name)
            self.assertEqual(row['model_verdict'], row['emulated_verdict'], name)

    @need_dc
    def test_memtest_cases_reproduced_by_model(self):
        for name, cap, ram, _ in dc.MEMTEST_CASES:
            prints, acc, verdict = dc.memtest_model(cap, ram)
            row = EVIDENCE['memtest'][name]
            self.assertEqual((prints, verdict), (row['model_prints'], row['model_verdict']), name)
            self.assertEqual(dc.memtest_summary(acc), row['model_accesses'], name)

    def test_training_outcomes(self):
        t = EVIDENCE['training']
        self.assertEqual(t['reference']['return_value'], '0x0')
        self.assertEqual(t['persistent-training-failure']['return_value'], '0x1017fa11')
        for k in ('zq-timeout', 'phy-init-timeout', 'dfi-timeout'):
            self.assertEqual(t[k]['return_value'], '0x1747fa11', k)
        for k, site in (('dram-init-hang', '0xb4068708'), ('training-other-status', '0xb40687a4'),
                        ('controller-stuck-config', '0xb4067220')):
            self.assertEqual(t[k]['stopped']['last_read']['site'], site, k)

    def test_resume_outcomes(self):
        r = EVIDENCE['resume']
        self.assertEqual(r['cold-no-s2-flag']['caller']['return_value'], '0x0')
        self.assertTrue(r['cold-no-s2-flag']['caller']['afi_written'])
        v = r['resume-valid']
        self.assertEqual(v['caller']['return_value'], '0x2')
        self.assertFalse(v['caller']['afi_written'])
        self.assertFalse(v['caller']['memtest_called'])
        self.assertEqual(v['resume']['stopped']['name'], 'resume vector (jump target)')
        self.assertEqual(v['pir_sequence'], ['0x10000000', '0x3f', '0x81'])
        for k in ('resume-training-failure', 'resume-zq-timeout', 'resume-alarm-check'):
            self.assertEqual(r[k]['resume']['stopped']['name'], 'PMIC power-off (never returns)', k)
        fail = r['resume-training-failure']
        self.assertIn({'reg': '0x3', 'value': '0x10'}, fail['pmic_writes'])          # S2 flag re-armed
        self.assertIn('re-wakeup at 13:0:1', fail['prints'])                          # RTC + 3 s
        self.assertIn('selfrefresh_entry', r['resume-alarm-check']['functions'])
        self.assertNotIn('selfrefresh_entry', fail['functions'])
        for k in ('s2-but-from-s4', 's2-vector-zero'):
            self.assertEqual(r[k]['caller']['return_value'], '0x0', k)
        self.assertEqual(r['adfu-request']['caller']['stopped']['name'], 'ROM re-entry 0xb40691a4 (ADFU)')
        self.assertTrue(r['pmic-version-zero']['caller']['stopped']['kind'].startswith('unbounded'))

    def test_handoff(self):
        h = EVIDENCE['handoff']
        self.assertEqual(h['reference']['uboot']['memory_reg'], [0, 0x10000000])
        self.assertFalse(h['training-failure']['uboot_reached'])
        self.assertEqual(h['training-failure']['afi']['ddr_size'], 0x80000000)   # written before the ADFU exit
        self.assertEqual(h['memtest-fails']['uboot']['gd_ram_size'], 0x10000000)   # memory test result ignored

    def test_geometry(self):
        g = EVIDENCE['geometry']
        ddr3 = [r for r in g['produce_shipped_record'] if r['banks'] == 8]
        self.assertEqual([(r['order'], r['ranks'], r['col_bits'], r['row_bits']) for r in ddr3],
                         [('col-bank-row', 1, 10, 14)])
        self.assertTrue(all(r['order'] == 'col-bank-row' for r in g['produce_shipped_record']))
        self.assertGreater(len(g['capacity_misreported_but_memtest_ok']), 0)

    def test_lpddr_branch(self):
        d = EVIDENCE['lpddr']['differs_from_ddr3_at_468MHz_mode0']
        self.assertEqual(d['type0x11']['PUBL.DCR'], ['0xb', '0x1000000c'])
        self.assertEqual(d['type0x02']['PUBL+0x3fc (outside ddr_rk3288.h)'], [None, '0x1'])
        self.assertNotIn('PUBL+0x3fc (outside ddr_rk3288.h)', d['type0x12'])
        runs = EVIDENCE['lpddr']['runs']
        self.assertEqual(runs['type0x11-468MHz-mode0']['pir'][1], '0x5f')
        self.assertEqual(runs['type0x11-468MHz-mode1']['pir'][1], '0x3f')

    def test_no_local_paths(self):
        text = EVIDENCE_PATH.read_text()
        self.assertNotIn('/home/', text)
        self.assertNotIn('/tmp/', text)
        self.assertLess(len(text), 1_000_000)

    def test_looping_console_collapsed(self):
        p = EVIDENCE['resume']['pmic-version-zero']['prints']
        self.assertTrue(any(x.startswith('pmu ver=0 not support [repeated ') for x in p))


@need_dc
class TestHarnessOnSyntheticCode(unittest.TestCase):
    """The RAM model and fault injection, on a few hand-encoded instructions (no firmware)."""

    CODE = 0xB4065400

    def run_code(self, words, ram, r0=0, r1=0, r3=0):
        blob = bytearray(de.BL_SIZE)
        off = self.CODE - de.BASE
        for i, w in enumerate(words):
            struct.pack_into('<I', blob, off + 4 * i, w)
        h = dc.Harness(bytes(blob), ram=ram, limit=1000, clear_globals=False)
        h.ram_everywhere = True
        h.setreg('r3', r3)
        h.setreg('sp', de.STACK_TOP)
        h.setreg('lr', de.SENTINEL)
        h.setreg('r0', r0)
        h.setreg('r1', r1)
        h.uc.emu_start(self.CODE, de.SENTINEL, count=1000)
        return h

    # str r1, [r0]; ldr r2, [r3]; bx lr
    PROG = [0xE5801000, 0xE5932000, 0xE12FFF1E]

    def test_wrap_alias(self):
        h = self.run_code(self.PROG, dc.Ram('wrap', 0x1000), r0=0x1010, r1=0xCAFE, r3=0x10)
        self.assertEqual(h.reg('r2'), 0xCAFE)

    def test_open_floats(self):
        h = self.run_code(self.PROG, dc.Ram('open', 0x1000, float_value=0x5A5A5A5A), r0=0x1010, r1=1, r3=0x1010)
        self.assertEqual(h.reg('r2'), 0x5A5A5A5A)

    def test_injected_faults(self):
        h = self.run_code(self.PROG, dc.Ram('wrap', 0x10000, read_xor={0x20: 0x80}), r0=0x20, r1=1, r3=0x20)
        self.assertEqual(h.reg('r2'), 0x81)
        h = self.run_code(self.PROG, dc.Ram('wrap', 0x10000, write_drop=(0x20,)), r0=0x20, r1=7, r3=0x20)
        self.assertEqual(h.reg('r2'), 0)
        h = self.run_code(self.PROG, dc.Ram('wrap', 0x10000, stuck_high=0x100), r0=0x20, r1=1, r3=0x20)
        self.assertEqual(h.reg('r2'), 0x101)

    def test_dmm_decode_ignores_missing_row_bits(self):
        dev = dc.DmmDevice(col_bits=10, row_bits=13, bank_log2=3, ranks=1)
        ram = dc.Ram('dmm', device=dev, float_value=0)
        blob_ram = ram
        h = self.run_code(self.PROG, blob_ram, r0=(1 << 27) + 0x40, r1=0x1234, r3=0x40)
        # DCU_CFG reads 0 here: columns 8, rows 13; byte bit 27 is row bit 15 -> not decoded by a 13-row device
        self.assertEqual(h.reg('r2'), 0x1234)


@unittest.skipUnless(HAVE_ENGINES and LOADERS, 'set ATM7039S_STOCK_LOADERS')
class TestFirmwareBacked(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        d = Path(LOADERS)
        cls.loaders = {r: de.load_region(d / f'loader-{r.split("-", 1)[1]}.bin') for r in RELEASES
                       if (d / f'loader-{r.split("-", 1)[1]}.bin').exists()}
        if not cls.loaders:
            raise unittest.SkipTest('no loader-<release>.bin in ATM7039S_STOCK_LOADERS')

    def test_quick_sections_regenerate(self):
        for rel, L in self.loaders.items():
            doc = dc.analyse(L, rel, quick=True)
            self.assertEqual(doc['code_sha256'], EVIDENCE['releases'][rel]['code_sha256'])
            ev = json.loads(json.dumps(dc._compact(doc)))
            for k in ('memtest', 'training', 'resume', 'unreachable_subflag', 'handoff'):
                if rel == EVIDENCE['reference_release']:
                    self.assertEqual(ev[k], EVIDENCE[k], f'{rel} {k}')
                else:   # committed sections are the reference release; others differ only in ini ODT/drive effects
                    self.assertEqual(dc.normalise_ini_odt(ev[k]), dc.normalise_ini_odt(EVIDENCE[k]), f'{rel} {k}')
            self.assertEqual(json.loads(json.dumps(ev['mode_comparison'])),
                             EVIDENCE['per_release_differences'][rel]['mode_comparison'], rel)

    def test_mode1_model_sampled(self):
        for rel, L in self.loaders.items():
            r = dc.mode1_model_sweep(L, clocks=range(100, 1201, 37))
            self.assertEqual(r['mismatches'], [], rel)

    def test_boot_chain_derives_ram_size(self):
        import boot_chain
        L = self.loaders.get('stock-20231014') or next(iter(self.loaders.values()))
        mib, info = boot_chain.dram_scenario_capacity(L, 'reference')
        self.assertEqual(mib, 256)
        self.assertEqual(info['afi_ddr_size'], '0x10000000')
        with self.assertRaises(SystemExit):
            boot_chain.dram_scenario_capacity(L, 'persistent-training-failure')


if __name__ == '__main__':
    unittest.main()
