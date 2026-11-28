"""Semantic checks of the structured initialization contract against independent references.

Each mutation test changes one structured definition and calls the semantic
check that owns it, so a generated-file, trace-hash or schema failure cannot
stand in for the protection being tested.
"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import bootloader_contract as contract
import contract_semantics as cs

FW = os.environ.get('ATM_FIRMWARE_DIR')
HAVE_EXECUTION_TOOLS = all(importlib.util.find_spec(name) for name in ('capstone', 'unicorn', 'pyfatfs'))


class Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = contract.ROOT
        cls.spec = contract.read(root / contract.CONTRACT)
        cls.trace = contract.read(root / contract.TRACE)
        cls.history = contract.read(root / contract.HISTORY)
        cls.selector = contract.read(root / cs.SEMANTICS_EVIDENCE)
        cls.sem = cls.spec['semantics']

    def run_row(self, run_id, release='koriki-v1.0'):
        row, = (r for r in self.selector['runs'] if r['id'] == run_id and r['release'] == release)
        return row['observed']


class DramSelectorSemantics(Fixtures):
    def test_bus_selector_rules(self):
        rules = {(r['input_min'], r['input_max']): r for r in self.sem['dram-bus']['rules']}
        self.assertEqual((rules[0, 0]['initial_width_bits'], rules[0, 0]['automatic_width_fallback']), (32, False))
        self.assertEqual((rules[1, 1]['initial_width_bits'], rules[1, 1]['automatic_width_fallback']), (16, False))
        self.assertEqual((rules[2, 255]['initial_width_bits'], rules[2, 255]['automatic_width_fallback']), (32, True))
        for value in (3, 0x80, 0xFF):
            self.assertTrue(cs.rule_for(self.sem['dram-bus']['rules'], value, 'bus')['automatic_width_fallback'])

    def test_fixed_x32_failure_never_receives_x16_retry(self):
        # Firmware execution: selector 0 on hardware that trains only x16.
        for cs_in in cs.SELECTOR_CS:
            for ranks in (1, 2):
                for release in cs.SEMANTIC_RELEASES:
                    run = self.run_row(f'selector-b0-cs{cs_in}-x16-r{ranks}', release)
                    self.assertEqual({w for _, w in run['attempts']}, {32})
                    self.assertEqual(run['dram_return'], '0x1017fa11')
        self.assertEqual(cs.attempts(self.sem, 0, 0, cs.trains_with(16, 2))['attempts'], [(2, 32), (1, 32)])

    def test_fixed_x16_and_automatic_selectors(self):
        self.assertEqual(self.run_row('selector-b1-cs0-x32-r1')['attempts'], [[2, 16], [1, 16]])
        self.assertEqual(self.run_row('selector-b2-cs0-x16-r1')['attempts'], [[2, 32], [1, 32], [2, 16], [1, 16]])
        for bus in (3, 0x80, 0xFF):
            self.assertEqual(self.run_row(f'selector-b{bus}-cs0-x16-r1')['attempts'],
                             [[2, 32], [1, 32], [2, 16], [1, 16]])

    def test_rank_detection_with_fixed_and_automatic_width(self):
        # Automatic ranks, fixed x16 width (the shipped secondary record).
        self.assertEqual(self.run_row('selector-b1-cs0-x16-r1')['attempts'], [[2, 16], [1, 16]])
        # Automatic ranks and width: rank retry first, then width with ranks restarted at 2.
        self.assertEqual(self.run_row('selector-b2-cs0-x16-r2')['attempts'], [[2, 32], [1, 32], [2, 16]])
        # Explicit ranks with automatic width.
        self.assertEqual(self.run_row('selector-b2-cs2-x16-r2')['attempts'], [[2, 32], [2, 16]])
        self.assertEqual(self.run_row('selector-b2-cs1-x16-r1')['attempts'], [[1, 32], [1, 16]])
        # Explicit two ranks cannot fall back to one.
        self.assertEqual(self.run_row('selector-b1-cs2-x16-r1')['attempts'], [[2, 16]])

    def test_input_and_working_selectors_are_distinct(self):
        # Input 3 succeeds at x32 with two ranks: working byte 0 (x32) and cs 2.
        success = self.run_row('selector-b3-cs3-x32-r2')
        self.assertEqual((success['record_final']['bus_sel'], success['record_final']['cs']), (0, 2))
        # Input 3 on one x16 rank reaches the fourth attempt; working byte 1 (x16) and cs 1.
        fallback = self.run_row('selector-b3-cs3-x16-r1')
        self.assertEqual((fallback['attempts'][-1], fallback['record_final']['bus_sel'], fallback['capacity_mib']),
                         ([1, 16], 1, 256))
        # Persistent training failure writes back min(bus, 2), the cs input when at most 2, else 0.
        terminal = self.run_row('selector-b2-cs2-x16-r1')
        self.assertEqual((terminal['record_final']['bus_sel'], terminal['record_final']['cs'], terminal['dram_return']),
                         (2, 2, '0x1017fa11'))
        zero = self.run_row('selector-b0-cs3-x16-r1')
        self.assertEqual((zero['record_final']['bus_sel'], zero['record_final']['cs']), (0, 0))

    def test_automatic_width_then_normalization(self):
        run = self.run_row('selector-b2-cs0-x16-r1')
        self.assertEqual((run['record_final']['bus_sel'], run['record_final']['cs'], run['capacity_mib']), (1, 1, 256))

    def test_dfi_timeout_does_not_retry(self):
        retry = self.sem['dram-retry']
        self.assertEqual(retry['eligible_internal_codes'], ['0x1017fa11'])
        self.assertIn('0xdf00fa11', retry['collapsed_internal_codes'])
        self.assertEqual([t['from_operation'] for t in self.spec['retry_transitions']], ['train'])

    def test_semantics_agree_with_all_references(self):
        stats = cs.check_dram_semantics(self.spec)
        self.assertEqual(stats['firmware_rows'], 240)
        self.assertGreater(stats['model_comparisons'], 12000)
        self.assertGreaterEqual(stats['historical_checks'], 30)
        self.assertEqual(stats['audited_instructions'], 80)


class CapacitySemantics(Fixtures):
    def test_required_eight_bank_examples(self):
        for width, ranks, mib in ((16, 1, 256), (32, 1, 512), (16, 2, 512), (32, 2, 1024)):
            with self.subTest(width=width, ranks=ranks):
                self.assertEqual(cs.capacity(self.sem, 0x48, width, ranks), (mib, None))
                self.assertEqual(cs.model_capacity(0x48, width, ranks)[0], mib)
                bus = 1 if width == 16 else 0
                run = self.run_row(f'capacity-b{bus}-cs{ranks}-rcc48-x32-r2-c10-r14')
                self.assertEqual(run['capacity_mib'], mib)
        # The x32 working selector is zero; the operand is two.
        self.assertEqual(self.sem['dram-bus']['capacity_width_operand'], {'16': 1, '32': 2})

    def test_exponent_bounds(self):
        self.assertEqual(self.run_row('capacity-b1-cs1-rcc00-x16-r1-c8-r13')['capacity_mib'], 32)
        self.assertEqual(cs.capacity(self.sem, 0x00, 16, 1), (32, None))
        self.assertEqual(self.run_row('capacity-b1-cs1-rcccc-x32-r2-c10-r14')['capacity_mib'], 2048)
        self.assertEqual(cs.capacity(self.sem, 0xCC, 16, 1), (2048, None))
        rejected = self.run_row('capacity-b1-cs2-rcccc-x32-r2-c10-r14')
        self.assertEqual((rejected['internal_codes'][-1], rejected['dram_return'], rejected['capacity_mib']),
                         ('0xc000fa11', '0x1747fa11', None))
        self.assertEqual(cs.capacity(self.sem, 0xCC, 16, 2), (None, '0xc000fa11'))

    def test_nonzero_bank_encodings(self):
        for rcc in (0x49, 0x4A, 0x4B):
            run = self.run_row(f'capacity-b1-cs1-rcc{rcc:02x}-x32-r2-c10-r14')
            self.assertEqual(run['capacity_mib'], 192)
            self.assertEqual(cs.capacity(self.sem, rcc, 16, 1), (192, None))
        # Sub-256 MiB nonzero-bank results wrap the final DCU_CFG term.
        self.assertIn('0xffffff2c', self.run_row('capacity-b1-cs1-rcc49-x32-r2-c10-r14')['dcu_print'])

    def test_probe_without_alias_reports_row_code_zero(self):
        comparison = contract.read(contract.ROOT / 'evidence/firmware/sd2-dram-comparison.json')
        run = comparison['distinct_pairs'][comparison['releases']['koriki-v1.0']['pairs']['unsupported-geometry-rows']]['runs']['2']
        rcc = run['record_final']['rcc']
        self.assertEqual(rcc >> 6, 0)
        self.assertEqual(cs.capacity(self.sem, rcc, 16, 1), (run['capacity_mib'], None))

    def test_raw_selector_substitution_detected(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-bus']['capacity_width_operand'] = {'16': 1, '32': 0}
        self.assertEqual(cs.capacity(bad['semantics'], 0x48, 32, 1), (128, None))
        with self.assertRaisesRegex(ValueError, 'capacity semantics disagree with ddr_model'):
            cs.check_dram_semantics(bad)

    def test_eight_bank_formula_not_generalized(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-capacity']['bank_branches'] = [
            dict(self.sem['dram-capacity']['bank_branches'][0], bank_codes=[0, 1, 2, 3])]
        with self.assertRaisesRegex(ValueError, 'capacity semantics disagree'):
            cs.check_dram_semantics(bad)


class MutationsOfReviewedDefects(Fixtures):
    """Representative versions of the six reviewed defects, each caught by its owning check."""

    def test_finding_1_selector_zero_automatic(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-bus']['rules'][0]['automatic_width_fallback'] = True
        with self.assertRaisesRegex(ValueError, 'semantics disagree with ddr_model for bus 0'):
            cs.check_dram_semantics(bad)

    def test_finding_1_rule_partition(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-bus']['rules'][2]['input_max'] = 254
        with self.assertRaisesRegex(ValueError, 'partition'):
            cs.check_dram_semantics(bad)

    def test_finding_1_dfi_retry(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-retry']['eligible_internal_codes'].append('0xdf00fa11')
        bad['semantics']['dram-retry']['collapsed_internal_codes'].remove('0xdf00fa11')
        with self.assertRaisesRegex(ValueError, 'DFI timeout must follow a training retry'):
            cs.check_dram_semantics(bad)

    def test_finding_2_raw_selector_operand(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-bus']['capacity_width_operand']['32'] = 0
        with self.assertRaisesRegex(ValueError, 'capacity'):
            cs.check_dram_semantics(bad)

    def test_finding_3_cited_instruction(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-capacity']['instructions'][4][1] = 'movne ip, #0'
        with self.assertRaisesRegex(ValueError, 'differs from the audited'):
            cs.check_dram_semantics(bad)

    def test_finding_3_working_selector_contradiction(self):
        bad = deepcopy(self.spec)
        bad['semantics']['dram-bus']['rules'][0]['working_bus_selector'] = 1
        with self.assertRaisesRegex(ValueError, 'working selector disagrees'):
            cs.check_dram_semantics(bad)


class ConfigurationRecord(Fixtures):
    def check(self, spec):
        return cs.check_configuration(spec, self.history, self.trace)

    def test_committed_layout(self):
        self.assertGreater(self.check(self.spec), 400)
        fields = self.spec['configuration_fields']
        self.assertEqual((fields['dram-bus']['ini_offsets'], fields['dram-bus']['offset']),
                         ({'primary': 0x24, 'secondary': 0x54}, 4))
        self.assertEqual(fields['dram-mhz']['ini_slot_width'], 4)

    def test_wrong_working_offset(self):
        bad = deepcopy(self.spec)
        bad['configuration_fields']['dram-bus']['offset'] = 5
        with self.assertRaisesRegex(ValueError, 'overlap or leave gaps'):
            self.check(bad)

    def test_wrong_width(self):
        bad = deepcopy(self.spec)
        bad['configuration_fields']['dram-mhz']['width'] = 1
        with self.assertRaisesRegex(ValueError, 'overlap or leave gaps'):
            self.check(bad)

    def test_wrong_ini_offset(self):
        bad = deepcopy(self.spec)
        bad['configuration_fields']['dram-rcc']['ini_offsets'] = {'primary': 0x28, 'secondary': 0x58}
        with self.assertRaisesRegex(ValueError, 'slots overlap|placement differs'):
            self.check(bad)

    def test_swapped_fields(self):
        bad = deepcopy(self.spec)
        f = bad['configuration_fields']
        f['dram-bus']['offset'], f['dram-cs']['offset'] = 5, 4
        with self.assertRaisesRegex(ValueError, 'reference differs from the executed working copy'):
            self.check(bad)

    def test_wrong_release_reference(self):
        bad = deepcopy(self.spec)
        bad['configuration_fields']['dram-rd-odt']['reference'][1]['primary'] = 1
        with self.assertRaisesRegex(ValueError, 'stock-20231014 dram-rd-odt'):
            self.check(bad)

    def test_wrong_ini_field_offset(self):
        bad = deepcopy(self.spec)
        bad['configuration_fields']['uart-index']['offset'] = 15
        with self.assertRaisesRegex(ValueError, 'uart-index: reference'):
            self.check(bad)


class AfiInterface(Fixtures):
    def check(self, spec=None, trace=None):
        return cs.check_afi(spec or self.spec, trace or self.trace, self.history)

    def test_committed_layout_and_consumers(self):
        self.assertEqual(self.check(), 13)
        afi = self.spec['interfaces']['afi']
        self.assertEqual([(r['offset'], r['width'], r['field']) for r in afi['format']], [
            (0, 3, 'magic'), (3, 1, 'reserved_byte_3'), (4, 1, 'boot_mode'), (5, 1, 'boot_dev'),
            (6, 1, 'uart_index'), (7, 1, 'uart_pad'), (8, 4, 'uart_baud'), (12, 4, 'capacity_bytes')])

    def mutate(self, **changes):
        bad = deepcopy(self.spec)
        for row in bad['interfaces']['afi']['format']:
            row.update(changes.get(row['field'], {}))
        return bad

    def test_swapped_mode_and_device(self):
        with self.assertRaisesRegex(ValueError, 'AFI boot device|boot mode'):
            self.check(self.mutate(boot_mode={'offset': 5}, boot_dev={'offset': 4}))

    def test_wrong_offset_or_width(self):
        with self.assertRaisesRegex(ValueError, 'overlap, leave gaps'):
            self.check(self.mutate(uart_baud={'offset': 9}))
        with self.assertRaisesRegex(ValueError, 'overlap, leave gaps|encodings'):
            self.check(self.mutate(capacity_bytes={'width': 2}))

    def test_wrong_byte_order(self):
        bad = deepcopy(self.spec)
        bad['interfaces']['afi']['format'][6]['encoding'] = 'u32be'
        with self.assertRaisesRegex(ValueError, 'encodings'):
            self.check(bad)

    def test_wrong_magic_length(self):
        bad = deepcopy(self.spec)
        bad['interfaces']['afi']['consumer']['magic_checked_bytes'] = 4
        with self.assertRaisesRegex(ValueError, 'distinctive-reserved-byte|disagrees with executed'):
            self.check(bad)

    def test_wrong_capacity_conversion(self):
        bad = deepcopy(self.spec)
        bad['interfaces']['afi']['capacity_shift'] = 10
        with self.assertRaisesRegex(ValueError, 'capacity conversion'):
            self.check(bad)

    def test_linux_requirement_rejected(self):
        bad = deepcopy(self.spec)
        bad['interfaces']['afi']['required_by_linux'] = True
        with self.assertRaisesRegex(ValueError, 'not a Linux boot requirement'):
            self.check(bad)

    def test_failed_initialization_not_admitted(self):
        bad = deepcopy(self.trace)
        stage = bad['cases']['koriki-v1.0/training-failure']['result']['stages']['uboot-afi-and-ram']
        stage['status'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'consumed although the structured admission rule rejects it'):
            self.check(trace=bad)
        loose = deepcopy(self.spec)
        loose['interfaces']['afi']['admission']['dram_return'] = '0x1017fa11'
        with self.assertRaisesRegex(ValueError, 'consumed although'):
            self.check(spec=loose)

    def test_generation_rule(self):
        bad = deepcopy(self.trace)
        bad['cases']['koriki-v1.0/resume']['result']['dram']['afi']['generated'] = True
        with self.assertRaisesRegex(ValueError, 'AFI generation contradicts'):
            self.check(trace=bad)

    def test_store_crossing_a_field(self):
        afi = deepcopy(self.spec['interfaces']['afi'])
        afi['format'][6:7] = [dict(afi['format'][6], width=2), dict(afi['format'][6], offset=10, width=2, field='x')]
        events = list(contract.indexed_events(self.trace['events']['koriki-v1.0/sd2-reference']))
        with self.assertRaisesRegex(ValueError, 'crosses declared fields'):
            cs.check_afi_stores(afi, 'sd2', events)


class SramLayout(Fixtures):
    def check(self, spec):
        return cs.check_sram(spec, self.trace)

    def ranges(self, spec):
        return {r['id']: r for r in spec['interfaces']['sram-layout']['ranges']}

    def test_committed_layout(self):
        self.assertGreater(self.check(self.spec), 30)
        layout = self.spec['interfaces']['sram-layout']
        self.assertIsNone(layout['physical_extent'])
        self.assertEqual(layout['emulator_mapping_basis'], 'emulator-assumption')

    def test_incorrect_length_and_endpoint(self):
        bad = deepcopy(self.spec)
        self.ranges(bad)['reloaded-ini']['end'] += 0x200
        with self.assertRaisesRegex(ValueError, 'sector-derived end'):
            self.check(bad)
        bad = deepcopy(self.spec)
        r = self.ranges(bad)['early-loader-installation']
        r['end'] -= 0x200
        r['derivation']['sectors'] -= 1
        with self.assertRaisesRegex(ValueError, 'observed transfer 0 differs'):
            self.check(bad)

    def test_reversed_and_out_of_range(self):
        bad = deepcopy(self.spec)
        r = self.ranges(bad)['boot-code']
        r['start'], r['end'] = r['end'], r['start']
        with self.assertRaisesRegex(ValueError, 'reversed'):
            self.check(bad)
        bad = deepcopy(self.spec)
        r = self.ranges(bad)['loader-globals']
        r['start'], r['end'] = 0xB40A0000, 0xB40A007C
        with self.assertRaisesRegex(ValueError, 'outside the modeled SRAM mapping'):
            self.check(bad)

    def test_physical_extent_not_generalized(self):
        bad = deepcopy(self.spec)
        bad['interfaces']['sram-layout']['physical_extent'] = bad['interfaces']['sram-layout']['emulator_mapping']
        with self.assertRaisesRegex(ValueError, 'physical SRAM extent'):
            self.check(bad)
        bad = deepcopy(self.spec)
        bad['interfaces']['sram-layout']['emulator_mapping_basis'] = 'physical'
        with self.assertRaisesRegex(ValueError, 'not physical evidence'):
            self.check(bad)

    def test_unexplained_simultaneous_overlap(self):
        bad = deepcopy(self.spec)
        r = self.ranges(bad)['pointer-table']
        r['start'], r['end'], r['derivation']['bytes'] = 0xB4064C00, 0xB4064C18, 0x18
        with self.assertRaisesRegex(ValueError, 'unexplained SRAM overlap'):
            self.check(bad)

    def test_overlap_relations_checked(self):
        bad = deepcopy(self.spec)
        for row in bad['interfaces']['sram-layout']['overlaps']:
            if row['b'] == 'reloaded-ini' and row['relation'] == 'containment':
                row['a'], row['b'] = row['b'], row['a']
        with self.assertRaisesRegex(ValueError, 'not geometric containment'):
            self.check(bad)
        bad = deepcopy(self.spec)
        for row in bad['interfaces']['sram-layout']['overlaps']:
            if row['b'] == 'afi':
                row['relation'] = 'stage-reuse'
        self.ranges(bad)['recovery-copy-destination']['stages'].append('uboot')
        with self.assertRaisesRegex(ValueError, 'reuse ranges share a live stage'):
            self.check(bad)

    def test_undeclared_store_owner(self):
        bad = deepcopy(self.spec)
        bad['interfaces']['sram-layout']['ranges'] = [r for r in bad['interfaces']['sram-layout']['ranges']
                                                      if r['id'] not in ('afi', 'recovery-copy-destination')]
        bad['interfaces']['sram-layout']['overlaps'] = [o for o in bad['interfaces']['sram-layout']['overlaps']
                                                        if 'recovery-copy-destination' not in (o['a'], o['b'])]
        with self.assertRaisesRegex(ValueError, 'has no declared range'):
            self.check(bad)


class TimingAndStatic(Fixtures):
    def test_timing_inputs(self):
        self.assertGreater(cs.check_timing(self.spec, self.trace), 1000)
        bad = deepcopy(self.spec)
        bad['semantics']['dram-timing']['trfc_classes'][1]['ns'] = 170
        with self.assertRaisesRegex(ValueError, 'tRFC classes differ'):
            cs.check_timing(bad, self.trace)
        bad = deepcopy(self.spec)
        bad['semantics']['dram-bus']['capacity_width_operand']['32'] = 0
        with self.assertRaises((ValueError, ZeroDivisionError)):
            cs.check_timing(bad, self.trace)

    def test_static_operations(self):
        self.assertEqual(cs.check_static_operations(self.spec, self.trace),
                         ['clock-basis', 'delay', 'globals', 'publish-pointers', 'uart-output', 'uboot-relocate'])
        bad = deepcopy(self.spec)
        bad['operations']['uart-output']['static_instructions'][1][1] = 'tst r0, #0x80'
        with self.assertRaisesRegex(ValueError, 'uart-output: static instruction'):
            cs.check_static_operations(bad, self.trace)
        bad = deepcopy(self.spec)
        bad['operations']['globals']['static_literals'][1][1] = 0x80
        with self.assertRaisesRegex(ValueError, 'globals: literal'):
            cs.check_static_operations(bad, self.trace)


class LinuxHandoff(Fixtures):
    def test_reference_fdt_reservation_does_not_cover_final_blob(self):
        self.assertEqual(cs.check_linux_handoff(self.spec, self.trace), 5)
        dt = self.trace['cases']['koriki-v1.0/sd2-reference']['result']['stages']['device-tree']['state']
        self.assertEqual((dt['dt_memreserve'][0], dt['fdt_totalsize_after']), (['0x3800000', '0x7000'], 0x7080))
        bad = deepcopy(self.spec)
        bad['interfaces']['arm-linux-dt']['reference_fdt_reservation']['covers_final_blob'] = True
        with self.assertRaisesRegex(ValueError, 'FDT reservation coverage is False'):
            cs.check_linux_handoff(bad, self.trace)


SRC = os.environ.get('ATM_SOURCES_DIR')


class PinnedSources(unittest.TestCase):
    def test_references_name_ledger_revisions(self):
        report = contract.verify_sources(contract.ROOT, contract.ROOT / 'nonexistent-source-tree')
        self.assertEqual(set(report.values()), {'unavailable'})

    @unittest.skipUnless(SRC, 'set ATM_SOURCES_DIR to verify pinned source files')
    def test_pinned_files_match(self):
        report = contract.verify_sources(contract.ROOT, Path(SRC))
        self.assertNotIn('unavailable', report.values(), report)


@unittest.skipUnless(FW and HAVE_EXECUTION_TOOLS, 'set ATM_FIRMWARE_DIR to the pinned expanded images')
class FirmwareBackedSemantics(unittest.TestCase):
    def test_selector_matrix_reproduces(self):
        doc = cs.execute(Path(FW))
        self.assertEqual(cs.formatted(doc), (contract.ROOT / cs.SEMANTICS_EVIDENCE).read_bytes())


if __name__ == '__main__':
    unittest.main()
