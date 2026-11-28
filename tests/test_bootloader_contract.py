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


class Layered(unittest.TestCase):
    """Drive one validation layer on copied fixtures, so trace hashes cannot mask the defect."""

    @classmethod
    def setUpClass(cls):
        root = contract.ROOT
        cls.spec = contract.read(root / contract.CONTRACT)
        cls.timeline = contract.read(root / contract.TRACE)
        cls.history = contract.read(root / contract.HISTORY)

    def facts(self, key):
        release, name = key.split('/')
        return contract.facts_for(release, self.history['scenarios'][release][name])

    def case(self, key, timeline=None):
        case = deepcopy((timeline or self.timeline)['cases'][key])
        rows = deepcopy((timeline or self.timeline)['events'][key])
        return case, rows

    def observe(self, key, spec=None, case=None, rows=None):
        spec = spec or self.spec
        if case is None:
            case, rows = self.case(key)
        events = list(contract.indexed_events(rows))
        return events, contract.case_observations(spec, self.facts(key), case, events)

    def attempts(self, key, spec=None, case=None, rows=None):
        spec = spec or self.spec
        if case is None:
            case, rows = self.case(key)
        events, (found, positions, _, _) = self.observe(key, spec, case, rows)
        return contract.check_attempts(spec, key, self.facts(key), case, events, positions, found)

    def branch(self, key, spec=None, case=None, rows=None):
        spec = spec or self.spec
        if case is None:
            case, rows = self.case(key)
        events, (_, _, executed, absent) = self.observe(key, spec, case, rows)
        return contract.check_branch(spec, key, self.facts(key), case, events, executed, absent)


class BoundaryWindows(Layered):
    BOUNDS = [['terminal', 0xB4065400, 2], ['before-adfu', 0xB4069254, 6], ['training-request', 1, 8],
              ['training-request', 1, 10], ['caller-finishing', 0xB406674C, 12]]

    def test_existing_boundary(self):
        self.assertEqual(contract.window_of({'window': {'before': {'phase': 'before-adfu', 'occurrence': 'only'}}},
                                            self.BOUNDS, 't'), (0, 6))

    def test_missing_lower_and_upper_boundaries_fail_closed(self):
        for side in ('after', 'before'):
            with self.subTest(side=side), self.assertRaisesRegex(ValueError, 'required boundary after-adfu is absent'):
                contract.window_of({'window': {side: {'phase': 'after-adfu', 'occurrence': 'only'}}}, self.BOUNDS, 't')

    def test_reversed_order(self):
        rule = {'after': {'phase': 'caller-finishing', 'occurrence': 'only'},
                'before': {'phase': 'before-adfu', 'occurrence': 'only'}}
        with self.assertRaisesRegex(ValueError, 'reversed'):
            contract.window_of({'window': rule}, self.BOUNDS, 't')

    def test_repeated_boundary_needs_explicit_occurrence(self):
        with self.assertRaisesRegex(ValueError, 'occurs 2 times; window is ambiguous'):
            contract.window_of({'window': {'after': {'phase': 'training-request', 'occurrence': 'only'}}}, self.BOUNDS, 't')
        for occurrence, index in (('first', 8), ('last', 10), (2, 10)):
            rule = {'window': {'after': {'phase': 'training-request', 'occurrence': occurrence}}}
            self.assertEqual(contract.window_of(rule, self.BOUNDS, 't'), (index, None))
        with self.assertRaisesRegex(ValueError, 'occurrence 3 is absent'):
            contract.window_of({'window': {'after': {'phase': 'training-request', 'occurrence': 3}}}, self.BOUNDS, 't')

    def test_explicit_alternate_boundary(self):
        rule = {'phase': 'after-adfu', 'occurrence': 'only', 'else': {'phase': 'caller-finishing', 'occurrence': 'only'}}
        self.assertEqual(contract.window_of({'window': {'before': rule}}, self.BOUNDS, 't'), (0, 12))

    def test_empty_valid_interval(self):
        rule = {'after': {'phase': 'before-adfu', 'occurrence': 'only'},
                'before': {'phase': 'before-adfu', 'occurrence': 'only'}}
        window = contract.window_of({'window': rule}, self.BOUNDS, 't')
        self.assertEqual(window, (6, 6))
        rows = list(contract.indexed_events([[20, ['p', 'mmio', 'r', 1, 4, 0, 2, 2, None, None]]]))
        self.assertEqual(contract.select_events(rows, {'address': [1]}, window), [])

    def test_rle_run_intersecting_boundaries(self):
        rows = list(contract.indexed_events([[3, ['p', 'mmio', 'w', 7, 4, 1, 9, 9, None, None]],
                                             [10, ['p', 'mmio', 'r', 8, 4, 0, 9, 9, None, None]]]))
        selected = contract.select_events(rows, {'address': [8]}, (5, 9))
        self.assertEqual([(start, count) for start, count, _ in selected], [(5, 4)])
        check = {'kind': 'event', 'match': {'address': [8]}, 'count': [4, 4],
                 'window': {'after': {'phase': 'a', 'occurrence': 'only'}, 'before': {'phase': 'b', 'occurrence': 'only'}}}
        obs = contract.check_access('op', check, rows, [['a', 0, 5], ['b', 0, 9]], [], {})
        self.assertEqual(obs.execution_positions, [11, 13, 15, 17])
        check['count'] = [10, 10]
        with self.assertRaisesRegex(ValueError, 'count 4'):
            contract.check_access('op', check, rows, [['a', 0, 5], ['b', 0, 9]], [], {})

    def test_invalid_ini_timer_uses_explicit_alternate(self):
        timer = self.spec['operations']['timer']['checks'][1]
        self.assertEqual(timer['window']['before']['else']['phase'], 'caller-finishing')
        self.observe('koriki-v1.0/invalid-ini')
        bad = deepcopy(self.spec)
        del bad['operations']['timer']['checks'][1]['window']['before']['else']
        with self.assertRaisesRegex(ValueError, 'timer: required boundary before-adfu is absent'):
            self.observe('koriki-v1.0/invalid-ini', bad)

    def test_recovery_timer_reinitialization_excluded(self):
        bad = deepcopy(self.spec)
        del bad['operations']['timer']['checks'][1]['window']
        for key in ('koriki-v1.0/gpio-adfu', 'koriki-v1.0/pmic-read-error'):
            self.observe(key)
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'timer: event match.*count 2'):
                self.observe(key, bad)


class PerAttemptValidation(Layered):
    KEY = 'koriki-v1.0/sd2-reference'

    def second_attempt(self, rows, case):
        starts = [b[2] for b in case['boundaries'] if b[0] == 'controller-phy-programming']
        return starts[1]

    def row_at_site(self, rows, site, after):
        index = 0
        for pos, (count, values) in enumerate(rows):
            if index >= after and values[7] == site:
                return pos
            index += count
        raise AssertionError(site)

    def test_committed_attempts(self):
        covered = self.attempts(self.KEY)
        self.assertIn('dram-reset--dram-pll-enable', covered)
        self.assertEqual(len(contract.attempt_intervals(self.spec, self.case(self.KEY)[0])), 2)
        self.assertEqual(len(contract.attempt_intervals(self.spec, self.case('koriki-v1.0/training-failure')[0])), 2)

    def swap_rows(self, first_site, second_site):
        case, rows = self.case(self.KEY)
        start = self.second_attempt(rows, case)
        a, b = self.row_at_site(rows, first_site, start), self.row_at_site(rows, second_site, start)
        rows[a], rows[b] = rows[b], rows[a]
        return case, rows

    def test_second_attempt_ordering_only(self):
        case, rows = self.swap_rows(0xB4068024, 0xB406804C)    # PLL word before the reset clear in attempt 2
        with self.assertRaisesRegex(ValueError, 'attempt 2 .*swapped ordering for dram-reset--dram-pll-enable'):
            self.attempts(self.KEY, case=case, rows=rows)

    def test_training_before_phy_setup(self):
        case, rows = self.swap_rows(0xB40681BC, 0xB406879C)
        with self.assertRaisesRegex(ValueError, 'attempt 2 .*(swapped ordering|without prerequisite)'):
            self.attempts(self.KEY, case=case, rows=rows)

    def test_missing_reset_in_second_attempt(self):
        case, rows = self.case(self.KEY)
        start = self.second_attempt(rows, case)
        for site in (0xB4068024, 0xB4068038):
            rows[self.row_at_site(rows, site, start)][1][7] = 0xB40600F0
        with self.assertRaisesRegex(ValueError, 'attempt 2 .*required operation dram-reset lacks access at site 0xb4068024'):
            self.attempts(self.KEY, case=case, rows=rows)

    def test_retry_without_eligible_failure(self):
        case, rows = self.case(self.KEY)
        bounds = case['boundaries']
        first = next(i for i, b in enumerate(bounds) if b[0] == 'training-dterr')
        bounds[first] = ['training-passed', 0xB40687B8, bounds[first][2]]
        case['result']['dram']['training'][0]['pgsr_response'] = '0x1f'
        with self.assertRaisesRegex(ValueError, 'retry after a non-retryable trained attempt'):
            self.attempts(self.KEY, case=case, rows=rows)

    def test_failed_attempt_labelled_successful(self):
        case, rows = self.case(self.KEY)
        case['result']['dram']['training'][0]['pgsr_response'] = '0x1f'
        with self.assertRaisesRegex(ValueError, 'differs from the recorded training results'):
            self.attempts(self.KEY, case=case, rows=rows)

    def test_incorrect_retry_configuration(self):
        case, rows = self.case(self.KEY)
        start = self.second_attempt(rows, case)
        rows[self.row_at_site(rows, 0xB40686D8, start)][1][5] = 0x18C2E02
        case['result']['dram']['training'][1]['ranks'] = 2
        with self.assertRaisesRegex(ValueError, 'attempt 2 ranks 2 differs from retry rules 1'):
            self.attempts(self.KEY, case=case, rows=rows)

    def test_excess_retry_count(self):
        case, rows = self.case(self.KEY)
        raw = bytearray.fromhex(case['result']['dram']['ini_initial']['secondary'])
        raw[9] = 1    # fixed one rank: the executed second attempt is no longer permitted
        case['result']['dram']['ini_initial']['secondary'] = raw.hex()
        with self.assertRaisesRegex(ValueError, 'did not execute|retry rules predict|differs from retry rules'):
            self.attempts(self.KEY, case=case, rows=rows)
        bad = deepcopy(self.spec)
        bad['semantics']['dram-retry']['max_attempts'] = 1
        with self.assertRaisesRegex(ValueError, 'exceed the attempt bound'):
            self.attempts(self.KEY, spec=bad)

    def test_valid_early_failure_omits_later_operations(self):
        key = 'koriki-v1.0/zq-failure'
        self.attempts(key)
        case, rows = self.case(key)
        start = contract.attempt_intervals(self.spec, case)[0]['start']
        pos = self.row_at_site(rows, 0xB4068654, start)
        rows.insert(pos, [1, ['controller-phy-programming', 'mmio', 'w', 0xB01C8004, 4, 0x81, 0xB40670E8,
                                  0xB406879C, None, None]])
        with self.assertRaisesRegex(ValueError, 'programming-failure.*forbidden operation (dram-init|train) present'):
            self.attempts(key, case=case, rows=rows)


class ExecutionEvidence(Layered):
    def test_state_roles(self):
        value = contract.Observation('value')
        self.assertTrue(value.assertion_passed and not value.execution_observed and not value.absence_confirmed)
        executed = contract.Observation('execution', state_execution=True)
        self.assertTrue(executed.execution_observed)
        absent = contract.Observation('absence', absence_confirmed=True)
        self.assertTrue(absent.absence_confirmed and not absent.execution_observed)

    def test_successful_absence_assertion_is_not_execution(self):
        result = self.timeline['cases']['koriki-v1.0/training-failure']['result']
        check = {'kind': 'state', 'path': ['stages', 'linux-entry', 'status'], 'equals': 'blocked',
                 'role': 'absence', 'stage': 'linux-entry'}
        obs = contract.check_access('linux-entry', check, [], [], [], result)
        self.assertTrue(obs.assertion_passed and obs.absence_confirmed)
        self.assertFalse(obs.execution_observed)
        self.assertEqual(obs.execution_positions, [])

    def test_failed_state_assertion(self):
        result = self.timeline['cases']['koriki-v1.0/training-failure']['result']
        check = {'kind': 'state', 'path': ['stages', 'linux-entry', 'status'], 'equals': 'completed', 'role': 'value'}
        with self.assertRaisesRegex(ValueError, "was 'blocked'"):
            contract.check_access('linux-entry', check, [], [], [], result)

    def test_execution_state_from_blocked_stage_rejected(self):
        result = self.timeline['cases']['koriki-v1.0/training-failure']['result']
        check = {'kind': 'state', 'path': ['stages', 'linux-entry', 'status'], 'equals': 'blocked',
                 'role': 'execution', 'stage': 'linux-entry', 'stage_status': ['completed']}
        with self.assertRaisesRegex(ValueError, 'execution state claimed from stage linux-entry with status blocked'):
            contract.check_access('linux-entry', check, [], [], [], result)

    def test_blocked_linux_entry_cannot_satisfy_required_execution(self):
        bad = deepcopy(self.spec)
        branch = bad['branches']['cold-failed']
        branch['forbids'].remove('linux-entry')
        branch['confirm_absent'] = []
        branch['requires'].append('linux-entry')
        with self.assertRaisesRegex(ValueError, 'terminal branch missing linux-entry'):
            self.branch('koriki-v1.0/training-failure', bad)

    def test_failure_branches_confirm_linux_absence(self):
        for key in ('koriki-v1.0/training-failure', 'koriki-v1.0/gpio-adfu', 'koriki-v1.0/invalid-ini',
                    'koriki-v1.0/resume', 'koriki-v1.0/resume-power-off', 'koriki-v1.0/phy-poll',
                    'koriki-v1.0/rom-failure', 'koriki-v1.0/sd2-64m-storage-limit', 'koriki-v1.0/sfvd-absent',
                    'koriki-v1.0/zq-failure', 'koriki-v1.0/pmic-read-error'):
            with self.subTest(key=key):
                self.assertEqual(self.branch(key), 1)
        bad = deepcopy(self.spec)
        bad['operations']['linux-entry']['checks'][10]['when']['scenario'].remove('zq-failure')
        with self.assertRaisesRegex(ValueError, 'lacks a positive absence check for linux-entry'):
            self.branch('koriki-v1.0/zq-failure', bad)

    def test_successful_branch_with_downstream_execution(self):
        self.assertEqual(self.branch('koriki-v1.0/sd2-reference'), 0)

    def test_forbidden_operation_present(self):
        case, rows = self.case('koriki-v1.0/training-failure')
        case['boundaries'].append(['terminal', 0xB4065440, case['boundaries'][-1][2]])
        # The scenario's own zero-count check catches this first.
        with self.assertRaisesRegex(ValueError, 'cold-continue: boundary match.*count 1, expected 0..0'):
            self.branch('koriki-v1.0/training-failure', case=case, rows=rows)
        # Without it, the branch's forbidden-operation scan still rejects the continuation.
        bad = deepcopy(self.spec)
        bad['operations']['cold-continue']['checks'] = [
            c for c in bad['operations']['cold-continue']['checks'] if c['count'] != [0, 0]]
        with self.assertRaisesRegex(ValueError, 'reached forbidden cold-continue'):
            self.branch('koriki-v1.0/training-failure', bad, case=case, rows=rows)

    def test_forbidden_operation_detected_without_applicable_check(self):
        # phy-poll has no applicable train check; the anchor scan still finds an inserted PIR.
        case, rows = self.case('koriki-v1.0/phy-poll')
        rows.insert(-1, [1, ['x', 'mmio', 'w', 0xB01C8004, 4, 0x81, 0xB40670E8, 0xB406879C, None, None]])
        with self.assertRaisesRegex(ValueError, 'reached forbidden train'):
            self.branch('koriki-v1.0/phy-poll', case=case, rows=rows)

    def test_wrong_terminal_continuation(self):
        bad = deepcopy(self.spec)
        bad['branches']['cold-failed']['dram_terminal_pc'] = '0xb4065440'
        with self.assertRaisesRegex(ValueError, 'expects DRAM terminal 0xb4065440'):
            self.branch('koriki-v1.0/training-failure', bad)

    def test_structure_rejects_unjustified_first_occurrence_and_non_dram_attempts(self):
        bad = deepcopy(self.spec)
        del bad['dependencies']['boot-select--load-early']['occurrence_justification']
        with self.assertRaisesRegex(ValueError, 'first-occurrence ordering needs a justification'):
            contract.check_structure(bad, self.history)
        bad = deepcopy(self.spec)
        bad['dependencies']['timer--uart-reset']['trace_order'] = 'per-attempt'
        with self.assertRaisesRegex(ValueError, 'per-attempt ordering applies to DRAM'):
            contract.check_structure(bad, self.history)
        bad = deepcopy(self.spec)
        bad['dependencies']['dram-reset--dram-pll-enable']['trace_order'] = 'first-before-first'
        bad['dependencies']['dram-reset--dram-pll-enable']['occurrence_justification'] = 'x'
        with self.assertRaisesRegex(ValueError, 'cannot span DRAM attempts'):
            contract.check_structure(bad, self.history)

    def test_structure_rejects_state_role_errors(self):
        bad = deepcopy(self.spec)
        del bad['operations']['linux-entry']['checks'][0]['role']
        with self.assertRaises((ValueError, KeyError)):
            contract.check_structure(bad, self.history)
        bad = deepcopy(self.spec)
        check = bad['operations']['linux-entry']['checks'][10]
        check['equals'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'absence must assert a stage that did not run'):
            contract.check_structure(bad, self.history)

    def test_branch_must_require_or_confirm_linux(self):
        bad = deepcopy(self.spec)
        bad['branches']['bad-ini']['confirm_absent'] = []
        with self.assertRaisesRegex(ValueError, 'require Linux entry or confirm its absence'):
            contract.check_structure(bad, self.history)


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
