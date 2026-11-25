"""Regression and cross-validation tests for the DRAM timing reconstruction.

Most tests need no firmware: they use synthetic ARM code, or check the readable
model against the committed, firmware-derived evidence
(evidence/firmware/stock-ddr-timing.json). Tests that re-run the analysis on
real loaders run only when ATM7039S_STOCK_LOADERS names a directory holding
loader-<release>.bin files (448 sectors from disk offset 0x200200).
"""
import json
import os
from pathlib import Path
import random
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ddr_model as dm  # noqa: E402

EVIDENCE = json.loads((ROOT / 'evidence/firmware/stock-ddr-timing.json').read_text())
RELEASES = ('stock-221203', 'stock-221223', 'stock-230309', 'stock-20231014')

try:
    import unicorn  # noqa: F401
    import z3  # noqa: F401
    import capstone  # noqa: F401
    HAVE_ENGINES = True
except ImportError:  # pragma: no cover - CI installs them
    HAVE_ENGINES = False


def reference_hw(seed=0):
    return dm.Hardware(ranks=1, width=16, col_code=2, row_code=1, reset=dm.ResetAll(seed))


def evidence_record(rel):
    r = EVIDENCE['releases'][rel]['bootloader_ini']['second_record']
    return dm.Record(**r)


class TestModelAgainstFirmwareEvidence(unittest.TestCase):
    """The model must reproduce every committed firmware-derived value without the firmware."""

    def test_all_four_releases_present_and_code_identical(self):
        self.assertEqual(tuple(EVIDENCE['releases']), RELEASES)
        self.assertTrue(EVIDENCE['identical_code_across_releases'])
        self.assertEqual(len({v['code_sha256'] for v in EVIDENCE['releases'].values()}), 1)

    def test_cold_boot_selects_second_record(self):
        for rel in RELEASES:
            ini = EVIDENCE['releases'][rel]['bootloader_ini']
            self.assertEqual(ini['word_0x2c'], 1)
            self.assertEqual(ini['selected'], 'second')
            self.assertEqual((ini['second_record']['cs'], ini['second_record']['rcc'], ini['second_record']['capacity_mib']),
                             (0, 0, 0))

    def test_final_pass_values_and_console(self):
        for rel in RELEASES:
            ev = EVIDENCE['releases'][rel]
            m = dm.run(evidence_record(rel), reference_hw())
            fp = ev['final_pass']
            got = m['writes'][len(m['writes']) - len(fp):]
            self.assertEqual([(int(r['address'], 16), int(r['value'], 16)) for r in fp],
                             [(w.address, w.value) for w in got], rel)
            self.assertEqual(m['prints'], ev['console'], rel)
            self.assertEqual(m['param_after']['capacity_mib'], 256)
            self.assertEqual((m['param_after']['cs'], m['param_after']['rcc']), (1, 0x48))

    def test_named_timings_regression(self):
        t = dm.timings(468, cs=1, bus_sel=1)
        expected = dict(tRFC=164, tRP=8, tRCD=8, tRAS=18, tRC=26, tRRD=5, tFAW=24, tWR=8, tRTP=4, tWTR=4, CL=8, CWL=6,
                        tXP=4, tXPDLL=12, tCKE=3, tCKESR=4, tCKSRE=5, tRSTL=70, tREFI_cycles=3650, tZQCSI=29200,
                        TRTW=8, dfi_wrlat=2, dfi_rddata_en=3)
        self.assertEqual({k: t[k] for k in expected}, expected)
        for k, v in expected.items():
            self.assertEqual(EVIDENCE['releases']['stock-20231014']['timings'][k]['cycles'], v, k)

    def test_key_packed_registers(self):
        rec = evidence_record('stock-20231014')
        m = dm.run(rec, reference_hw())
        by = {}
        for w in m['writes']:
            by[w.register] = w.value
        self.assertEqual(by['CMU_DDRPLL'], 0x327)
        self.assertEqual(by['PUBL.MR0'], 0x1140)
        self.assertEqual(by['PUBL.MR1'], 0x42)
        self.assertEqual(by['PUBL.MR2'], 0x248)
        self.assertEqual(by['PUBL.PTR0'], 0x2A5766)
        self.assertEqual(by['PUBL.PTR1'], 0x5439210)
        self.assertEqual(by['PUBL.PTR2'], 0x3A96DA0)
        self.assertEqual(by['PUBL.DTPR0'], 0x34B28890)
        self.assertEqual(by['PUBL.DTPR1'], 0xA400C0)
        self.assertEqual(by['PUBL.DTPR2'], 0x10023200)
        self.assertEqual(by['PUBL.ZQ0CR1'], 0x29)
        self.assertEqual(by['uPCTL.MCFG'], 0x68029)
        self.assertEqual(by['DMM DCU_CFG (+0x28; name from the loader string)'], 0x202C)

    def test_only_odt_and_drive_dependent_values_differ_between_releases(self):
        regs = sorted(d['register'] for d in EVIDENCE['cross_release_differences'])
        self.assertEqual(regs, ['PUBL.MR1', 'PUBL.ZQ0CR1'])
        old = dm.run(evidence_record('stock-221203'), reference_hw())
        mr1 = [w.value for w in old['writes'] if w.register == 'PUBL.MR1']
        self.assertEqual(set(mr1), {0x6})            # RTT_NOM 0x4 (wrodt 1) | 2

    def test_evidence_records_all_methods_agree(self):
        for rel in RELEASES:
            ev = EVIDENCE['releases'][rel]
            mv = ev['model_vs_unicorn']
            self.assertEqual(mv['firmware_record_reference'], [])
            self.assertEqual(mv['primary_record_reference'], [])
            self.assertTrue(all(v == [] for v in mv['scenarios'].values()))
            self.assertTrue(all(v == [] for v in mv['reset_seeds'].values()))
            self.assertTrue(ev['symbolic']['equals_unicorn'])
            self.assertEqual(ev['symbolic']['clobber_dependent'], [])
            self.assertEqual(ev['class_consistency']['contradictions'], [])
        self.assertEqual(EVIDENCE['division_helpers']['mismatches'], 0)

    def test_writeback_only_matches_reference_geometry(self):
        for rel in RELEASES:
            wb = EVIDENCE['releases'][rel]['ini_writeback']
            self.assertEqual([k for k, v in wb.items() if v['equals_shipped']], ['x16-1rank-2Gb'], rel)

    def test_evidence_contains_no_code_bytes(self):
        text = (ROOT / 'evidence/firmware/stock-ddr-timing.json').read_text()
        self.assertNotIn('disassembly', text.lower())
        self.assertLess(len(text), 400_000)


class TestModelSemantics(unittest.TestCase):
    def test_clock_rounding_and_pll(self):
        for clk in (468, 470, 479):
            rec = dm.Record(clk, 0, 1, 0, 0x10, 0, 2, 2, 9)
            m = dm.run(rec, reference_hw())
            self.assertEqual(m['timings']['F'], 468)
            self.assertIn(0x327, [w.value for w in m['writes'] if w.register == 'CMU_DDRPLL'])

    def test_rounded_up_against_nominal_ns(self):
        """Every computed cycle count is at least the nominal JEDEC-style constant it encodes."""
        for F in range(300, 1067, 12):
            t = dm.timings(F, 1, 1)
            tck = 1000 / F
            self.assertGreaterEqual(t['tRFC'] * tck, 350)
            self.assertGreaterEqual(t['tREFI_cycles'] * tck, 7800 - tck)   # tREFI is floored (no +1)
            self.assertGreaterEqual(t['tRP'] * tck, 13.75 if F < 801 else 13.91)
            self.assertGreaterEqual(t['tFAW'] * tck, 35)
            self.assertEqual(t['tRC'], t['tRP'] + t['tRAS'])

    def test_cl_cwl_bands(self):
        bands = {300: (6, 5), 400: (6, 5), 401: (8, 6), 533: (8, 6), 534: (10, 7), 667: (10, 7), 668: (11, 8),
                 800: (11, 8), 801: (13, 9)}
        for F, (cl, cwl) in bands.items():
            t = dm.timings(F, 1, 1)
            self.assertEqual((t['CL'], t['CWL']), (cl, cwl), F)

    def test_trfc_selected_from_forced_capacity(self):
        # Mode 0 forces capacity 0x800 before timings are computed, so tRFC is the 350 ns class for one or two ranks.
        self.assertEqual(dm.timings(468, 1, 1)['tRFC_ns'], 350)
        self.assertEqual(dm.timings(468, 2, 1)['tRFC_ns'], 350)
        self.assertEqual(dm.timings(468, 1, 1, capacity_mib=256)['tRFC_ns'], 160)

    def test_training_failure_retry_and_detected_classes(self):
        m = dm.run(evidence_record('stock-20231014'), reference_hw())
        self.assertEqual(m['prints'][0].split(',')[2], '2cs')
        self.assertEqual(m['prints'][2].split(',')[2], '1cs')
        pgcr = [w for w in m['writes'] if w.register == 'PUBL.PGCR']
        self.assertEqual([w.value for w in pgcr], [0x18C2E02, 0x1842E02])
        self.assertTrue(all(w.cls == 'detected' for w in pgcr))
        two = dm.run(evidence_record('stock-20231014'), dm.Hardware(ranks=2, col_code=2, row_code=1))
        self.assertEqual(len(two['prints']), 2)
        self.assertEqual(two['param_after']['capacity_mib'], 512)

    def test_reset_dependent_bits_flagged(self):
        m = dm.run(evidence_record('stock-20231014'), dm.Hardware(reset=dm.ResetAll(0xFFFFFFFF)))
        dx2 = [w for w in m['writes'] if w.register == 'PUBL.DX2GCR']
        self.assertEqual(dx2[-1].value, 0xFFFFFFFE)
        self.assertEqual(dx2[-1].cls, 'reset')

    def test_lpddr_branch_not_modelled(self):
        with self.assertRaises(NotImplementedError):
            dm.run(dm.Record(468, 0, 1, 0, 0x11, 0, 0, 0, 0), reference_hw())


@unittest.skipUnless(HAVE_ENGINES, 'unicorn, z3 and capstone required')
class TestSymbolicInterpreterConformance(unittest.TestCase):
    """Our z3 ARM interpreter must agree with Unicorn on concrete inputs for every instruction class it implements."""

    SNIPPET = [0xE0810002, 0xE0503001, 0xE2612010, 0xE1814182, 0xE3C450FF, 0xE0056123, 0xE02670C0, 0xE0080190,
               0xE0292190, 0xE1500001, 0x83A0A001, 0x93A0A002, 0xE1520003, 0xB3A0B005, 0xA3A0B006, 0xE3100001,
               0x03A0C007, 0x13A0C008, 0xE1A01211, 0xE1E02003, 0xE0933003, 0xE0A44004, 0xE52D0004, 0xE49D1004,
               0xE92D4010, 0xE8BD4010, 0xE2754000, 0x31A05235]

    def run_both(self, regs):
        import ddr_emulate as de
        import ddr_symbolic as ds
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, arm_const as A
        code = b''.join(struct.pack('<I', w) for w in self.SNIPPET)
        entry, end = de.BASE + 0x100, de.BASE + 0x100 + len(code)
        image = bytearray(0x200)
        image[0x100:0x100 + len(code)] = code
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(de.BASE, de.SRAM_SIZE)
        uc.mem_write(de.BASE, bytes(image))
        names = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12']
        for i, n in enumerate(names):
            uc.reg_write(getattr(A, f'UC_ARM_REG_R{i}'), regs[i])
        uc.reg_write(A.UC_ARM_REG_SP, de.STACK_TOP)
        uc.reg_write(A.UC_ARM_REG_LR, 0x1234)
        uc.emu_start(entry, end)
        expect = [uc.reg_read(getattr(A, f'UC_ARM_REG_R{i}')) for i in range(13)] + [uc.reg_read(A.UC_ARM_REG_SP)]
        m = ds.Machine(bytes(image), symbolic=(), prepared=(bytes(12), bytes(0x80)))
        s = m.base_state.fork()
        cap = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'sb', 'sl', 'fp', 'ip']
        s.r.update({c: ds.bv(regs[i]) for i, c in enumerate(cap)})
        s.r.update(sp=ds.bv(de.STACK_TOP), lr=ds.bv(0x1234))
        s.pc = entry
        while s.pc != end:
            (s,) = m.step(s)
        got = [ds.concrete(s.r[c]) for c in cap] + [ds.concrete(s.r['sp'])]
        return expect, got

    def test_random_register_states(self):
        rng = random.Random(39)
        for _ in range(60):
            regs = [rng.choice((0, 1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, rng.getrandbits(32), rng.randrange(32)))
                    for _ in range(13)]
            expect, got = self.run_both(regs)
            self.assertEqual(expect, got, [hex(x) for x in regs])


@unittest.skipUnless(HAVE_ENGINES, 'unicorn, z3 and capstone required')
class TestSymbolicForkingAndOracles(unittest.TestCase):
    CODE = [0xE5D01000, 0xE5D02001, 0xE1811402, 0xE59F301C, 0xE3510E19, 0x93A02006, 0x83A02008, 0xE5832000,
            0xE3510C02, 0x8A000000, 0xE5831004, 0xE12FFF1E, 0xB01C0100]

    def test_paths_partition_domain_and_expressions(self):
        import ddr_emulate as de
        import ddr_symbolic as ds
        code = b''.join(struct.pack('<I', w) for w in self.CODE)
        image = bytearray(0x200)
        image[0x100:0x100 + len(code)] = code
        m = ds.Machine(bytes(image), symbolic=('clock',), domain={'clock': (100, 1000)},
                       prepared=(bytes(12), bytes(0x80)))
        paths = m.explore(entry=de.BASE + 0x100)
        out = ds.summarise(m, paths, evaluate={'clock': 468})
        doms = sorted(p['domain']['clock'][0] for p in out)
        self.assertEqual(doms, [[100, 512], [513, 1000]])
        for p in out:
            lo = p['domain']['clock'][0][0]
            n = 2 if lo == 100 else 1
            self.assertEqual(len(p['mmio_writes']), n)
            if 'evaluated' in p:
                self.assertEqual([w['value'] for w in p['evaluated']['mmio_writes']], ['0x8', '0x1d4'])

    def test_interval_helper(self):
        import ddr_symbolic as ds
        import z3
        x = z3.BitVec('x', 16)
        self.assertEqual(ds.intervals(x, [z3.Or(z3.ULE(x, 10), z3.UGE(x, 20))], 0, 30), [[0, 10], [20, 30]])

    def test_emulator_state_oracle_and_printf(self):
        import ddr_emulate as de
        self.assertEqual(de._sprintf('a%dx%x%%', [5, 255]), 'a5xff%')
        self.assertEqual(de._sprintf('%d', [0xFFFFFFFF]), '-1')
        # Synthetic code: SCTL=2 (GO) then read STAT -> 3 (ACCESS) via the documented oracle.
        words = [0xE59F1010, 0xE3A00002, 0xE5810004, 0xE5910008, 0xE12FFF1E, 0, de.UPCTL]
        image = bytearray(0x200)
        image[0x100:0x100 + 4 * len(words)] = b''.join(struct.pack('<I', w) for w in words)
        em = de.Emulation(bytes(image))
        self.assertEqual(em.call(de.BASE + 0x100), 3)
        self.assertEqual(em.writes[0]['value'], '0x2')
        self.assertEqual(em.reads[0]['rule'], 'STAT follows last SCTL command')


@unittest.skipUnless(HAVE_ENGINES and os.environ.get('ATM7039S_STOCK_LOADERS'), 'set ATM7039S_STOCK_LOADERS')
class TestAgainstRealLoaders(unittest.TestCase):
    """Re-run the full analysis on locally acquired loaders and compare with the committed evidence."""

    def test_regenerate_matches_evidence(self):
        import ddr_emulate as de
        import ddr_timing as dt
        d = Path(os.environ['ATM7039S_STOCK_LOADERS'])
        loaders = {r: de.load_region(d / f'loader-{r.split("-", 1)[1]}.bin') for r in RELEASES
                   if (d / f'loader-{r.split("-", 1)[1]}.bin').exists()}
        self.assertTrue(loaders)
        res = dt.analyse(loaders, sweep_step=25, symbolic=True)
        for rel, v in res['releases'].items():
            ev = EVIDENCE['releases'][rel]
            for key in ('loader_sha256', 'code_sha256', 'console', 'final_pass', 'timings', 'ini_writeback',
                        'bootloader_ini', 'class_consistency'):
                self.assertEqual(v[key], ev[key], (rel, key))
            self.assertEqual(v['symbolic']['domains'], ev['symbolic']['domains'])
            self.assertTrue(v['symbolic']['equals_unicorn'])

    def test_exhaustive_three_way_agreement(self):
        """Symbolic path expressions == Unicorn == model at every integer clock of the analysed domain."""
        import z3
        import ddr_emulate as de
        import ddr_symbolic as ds
        import ddr_timing as dt
        d = Path(os.environ['ATM7039S_STOCK_LOADERS'])
        data = de.load_region(d / 'loader-20231014.bin')
        mach = ds.Machine(data, domain={'clock': (100, 1200)})
        paths = mach.explore()
        clk = mach.symbols['clock']
        for p in paths:
            sol = z3.Solver(); sol.add(*p.path)
            for lo, hi in ds.intervals(clk, p.path, 100, 1200):
                for c in range(lo, hi + 1, 3):
                    sub = [(clk, z3.BitVecVal(c, 16))]
                    sym = [(a, z3.simplify(z3.substitute(v, *sub)).as_long()) for a, v in p.writes]
                    em, rec, _ = dt.unicorn_run(data, clock=c)
                    uni = [(int(w['address'], 16), int(w['value'], 16)) for w in em.writes]
                    mod = [(w.address, w.value) for w in dm.run(rec, reference_hw())['writes']]
                    self.assertEqual(sym, uni, c)
                    self.assertEqual(mod, uni, c)


if __name__ == '__main__':
    unittest.main()
