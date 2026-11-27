"""Offline specification checks and optional execution against hash-pinned firmware."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import bootloader_contract as contract


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = contract.ROOT
        cls.spec = contract.read(root / contract.CONTRACT)
        cls.timeline = contract.read(root / contract.TRACE)
        cls.history = contract.read(root / contract.HISTORY)

    def validate(self, *, spec=None, timeline=None):
        return contract.validate_trace(self.spec if spec is None else spec,
                                       self.timeline if timeline is None else timeline, self.history)

    def test_committed_outputs_rebuild_and_validate(self):
        report = contract.check_generated(contract.ROOT)
        self.assertEqual(report['cases'], 16)
        self.assertGreaterEqual(report['operations'], 50)
        self.assertGreaterEqual(report['checked_ordered_dependencies'], 40)

    def test_required_consumer_and_cpu_dependencies(self):
        graph = self.spec['dependencies']
        for left, right, relation in (
            ('timer', 'delay', 'firmware-data'),
            ('power-state', 'resume-record', 'firmware-data'),
            ('train-passed', 'dfi-ready', 'firmware-control'),
            ('controller-go', 'capacity-detect', 'firmware-control'),
            ('capacity-detect', 'capacity-final', 'firmware-data'),
            ('boot-select', 'afi-produce', 'firmware-data'),
            ('afi-produce', 'afi-consume', 'firmware-data'),
            ('device-tree', 'linux-entry', 'firmware-data'),
            ('uart-output', 'cold-record', 'ordering-only'),
            ('gpio-loopback', 'dram-gates-off', 'unresolved'),
        ):
            edge = graph[f'{left}--{right}']
            self.assertEqual((edge['from'], edge['to'], edge['relation']), (left, right, relation))
            self.assertTrue(edge['evidence'])

    def test_bank_and_profile_scope(self):
        self.assertEqual(self.spec['profiles']['d']['dependencies'], ['b'])
        self.assertIn('uboot-reservations', self.spec['profiles']['c']['blockers'])
        self.assertNotIn('uboot-reservations', self.spec['profiles']['a']['blockers'])
        self.assertIsNone(self.spec['interfaces']['rom']['physical_sram_extent'])
        self.assertEqual(self.spec['uncertainties']['resume-reset']['status'], 'open')
        self.assertEqual(self.spec['interfaces']['afi']['magic_checked_bytes'], 3)
        self.assertIsNone(self.timeline['startup_audit']['runtime_reservations'])
        self.assertEqual(self.timeline['startup_audit']['literals']['0x5003744'], '0x50ffff0')

    def test_retry_runs_repeat_ordered_programming(self):
        raw = self.timeline['events']['koriki-v1.0/sd2-reference']
        events = [(row[7], row[5]) for _, row in raw if row[1] == 'mmio']
        milestones = [0xB406800C, 0xB4068018, 0xB4068024, 0xB4068038, 0xB406804C,
                      0xB4068060, 0xB40680D8, 0xB40680EC, 0xB4068100, 0xB4068654,
                      0xB40686A8, 0xB4068700, 0xB4068708, 0xB406879C, 0xB40687A4]
        relevant = [(site, value) for site, value in events if site in milestones]
        self.assertEqual([site for site, _ in relevant], milestones * 2)
        training = [value for site, value in relevant if site == 0xB40687A4]
        self.assertEqual(training, [0x3F, 0x1F])

    def test_instrumented_delays_keep_their_execution_boundary(self):
        prefix = 'koriki-v1.0/'
        for medium, count in [('sd2', 32), ('sd0', 0)]:
            key = f'{prefix}{medium}-reference'
            case = self.timeline['cases'][key]
            delays = [event for event in case['supplemental'] if event['kind'] == 'delay-us']
            self.assertEqual(sum(d['value'] == 1000 and d['site'] == 0xB4069364
                                 and d['method'] == 'executed timer poll' for d in delays), count)
            reset = next(d for d in delays if d['site'] == 0xB406802C)
            self.assertEqual((reset['value'], reset['method']), (10, 'delay stub'))
            index = reset['event_index']
            raw = list(contract.indexed_events(self.timeline['events'][key]))
            previous = next(event for start, repeat, event in raw if start <= index - 1 < start + repeat)
            self.assertEqual((previous['site'], previous['address']), (0xB4068024, 0xB01600A8))

    def test_rom_storage_requests_and_failure_admission(self):
        cases = self.timeline['cases']
        ref = cases['koriki-v1.0/sd2-reference']['result']
        self.assertEqual([(r['lba'], r['sectors'], r['destination']) for r in ref['storage_reads'][:5]], [
            (0x102B, 80, '0xb4065400'), (0x1013, 8, '0xb4062400'),
            (0x10C9, 248, '0x1000'), (0x1800, 1, '0x300000'), (0x1800, 256, '0x5000000')])
        failed = cases['koriki-v1.0/training-failure']['result']
        self.assertTrue(failed['dram']['afi']['generated'])
        self.assertEqual(failed['dram']['record_final']['capacity_mib'], 2048)
        self.assertEqual(failed['stages']['uboot-entry']['status'], 'blocked')
        diag = cases['koriki-v1.0/diagnostic-failure']['result']
        self.assertEqual(diag['dram']['memory_test']['status'], 'failed')
        self.assertEqual(diag['stages']['linux-entry']['status'], 'completed')
        self.assertTrue(diag['warning'])

    def test_missing_required_operation(self):
        bad = deepcopy(self.spec)
        bad['operations']['afi-produce']['checks'] = []
        with self.assertRaisesRegex(ValueError, r'missing operation.*afi-produce'):
            self.validate(spec=bad)

    def test_swapped_observed_order(self):
        bad = deepcopy(self.spec)
        edge = bad['dependencies']['post-dram-clock--load-app-uboot']
        edge['from'], edge['to'] = edge['to'], edge['from']
        with self.assertRaisesRegex(ValueError, 'swapped ordering'):
            self.validate(spec=bad)

    def test_wrong_register_address_or_width(self):
        for field, value in [('address', 0xB01600A4), ('width', 2)]:
            bad = deepcopy(self.spec)
            bad['operations']['boot-select']['checks'][0]['match'][field] = [value]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'access lacks register reference'):
                self.validate(spec=bad)

    def test_wrong_rmw_masks(self):
        bad = deepcopy(self.spec)
        bad['operations']['board-mux']['checks'][0]['rmw']['set'] = 0
        with self.assertRaisesRegex(ValueError, 'board-mux: RMW mismatch'):
            self.validate(spec=bad)

    def test_unexplained_cycle(self):
        bad = deepcopy(self.spec)
        edge = bad['dependencies']['train-passed--dfi-ready']
        bad['dependencies']['dfi-ready--train-passed'] = {**edge, 'from': 'dfi-ready', 'to': 'train-passed'}
        with self.assertRaisesRegex(ValueError, 'dependency cycle'):
            self.validate(spec=bad)

    def test_unknown_evidence_selection(self):
        bad = contract.read(contract.ROOT / contract.INPUT)
        bad['evidence']['unified']['pointer'] = ['nonexistent']
        with self.assertRaises(KeyError):
            contract.build_contract(contract.ROOT, bad)

    def test_unknown_operation_evidence_id(self):
        bad = deepcopy(self.spec)
        bad['operations']['timer']['evidence'].append('imaginary-clock-evidence')
        with self.assertRaisesRegex(ValueError, 'unknown evidence'):
            self.validate(spec=bad)

    def test_resolved_unknown_rejected(self):
        bad = deepcopy(self.spec)
        bad['uncertainties']['rom-entry-state']['resolution'] = 'use the emulator defaults'
        with self.assertRaisesRegex(ValueError, 'unsupported resolution'):
            self.validate(spec=bad)

    def test_condition_contradicts_actual_execution(self):
        bad = deepcopy(self.spec)
        bad['operations']['gpio-loopback']['checks'][0]['when'] = {'medium': ['sd0']}
        with self.assertRaisesRegex(ValueError, 'gpio-loopback: event match'):
            self.validate(spec=bad)

    def test_failed_outcome_presented_as_success(self):
        bad = deepcopy(self.timeline)
        result = bad['cases']['koriki-v1.0/zq-failure']['result']
        result['terminal']['outcome'] = 'linux-entry-boundary'
        with self.assertRaisesRegex(ValueError, 'historical outcome or delivered state differs'):
            self.validate(timeline=bad)

    def test_inferred_value_labeled_physical(self):
        bad = deepcopy(self.spec)
        bad['operations']['boot-select']['evidence_classification'] = 'physical-observation'
        with self.assertRaisesRegex(ValueError, 'evidence does not support'):
            self.validate(spec=bad)

    def test_private_path_or_duplicate_id(self):
        bad = deepcopy(self.spec)
        bad['limitations'].append('/home/operator/secret-name')
        with self.assertRaisesRegex(ValueError, 'private local path'):
            self.validate(spec=bad)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            json.loads('{"uart":1,"uart":2}', object_pairs_hook=contract.unique_keys)

    def test_data_no_encoded_firmware_payload(self):
        for values in self.timeline['events'].values():
            for _, row in values:
                if row[1] == 'storage':
                    self.assertRegex(row[5], '^[a-f0-9]{64}$')
                else:
                    self.assertTrue(row[5] is None or isinstance(row[5], int))
        self.assertTrue(all(v['file'] == f'{k}.img' for k, v in self.spec['firmware'].items()))


FW = os.environ.get('ATM_FIRMWARE_DIR')
HAVE_EXECUTION_TOOLS = all(importlib.util.find_spec(name) for name in ('capstone', 'unicorn', 'pyfatfs'))


@unittest.skipUnless(FW and HAVE_EXECUTION_TOOLS, 'set ATM_FIRMWARE_DIR to the pinned expanded images')
class FirmwareBackedContractTests(unittest.TestCase):
    def test_replay_is_byte_identical(self):
        root = contract.ROOT
        spec = contract.read(root / contract.CONTRACT)
        timeline = contract.replay(root, spec, Path(FW))
        self.assertEqual(contract.trace_bytes(timeline), (root / contract.TRACE).read_bytes())
        self.assertEqual(contract.validate_trace(spec, timeline, contract.read(root / contract.HISTORY))['cases'], 16)
