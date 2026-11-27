from dataclasses import replace
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import boot_chain as boot
import dram_complete as dram
import unified_boot_chain as unified
from unified_environment import Environment
from unified_loader import BoundaryError
from unified_uboot import fdt_layout, legacy_image
from tests.test_boot_chain import HAVE_ARM, mini_fdt, uimage

EVIDENCE = ROOT / 'evidence' / 'firmware' / 'unified-boot-chain.json'
FW = os.environ.get('ATM_FIRMWARE_DIR')


def result_fixture(code=2, capacity=256, magic=b'AFI\x9a'):
    raw = boot.afi_bytes(dev=0x20 | code, size=capacity << 20, magic=magic)
    return dict(boot_code=code, boot_code_observed=code, outcome='cold-success', caller_return='0x0',
                dram_return='0x0', terminal={'pc': '0xb4065440'}, main_continuation_boundary_reached=True,
                memory_test={'status': 'passed'}, capacity_mib=capacity,
                afi=dict(generated=True, stores=20, bytes=raw.hex(), decoded=dram.decode_afi(raw)))


class Contracts(unittest.TestCase):
    def test_dependency_order_and_earliest_failure(self):
        graph = unified.StageGraph('firmware-a', 'scenario')
        skipped = Mock()
        with self.assertRaisesRegex(BoundaryError, 'requires boot-rom-boundary'):
            graph.step('block-0', skipped)
        graph.step('boot-rom-boundary', lambda _: {'clock': 0x80})

        def fail(inherited):
            self.assertEqual(inherited, {'clock': 0x80})
            raise BoundaryError('rom-service-failure', 'seeded ROM error')

        graph.step('block-0', fail)
        for stage in list(unified.STAGES)[2:]:
            graph.step(stage, skipped)
        self.assertEqual(graph.terminal['outcome'], 'rom-service-failure')
        self.assertEqual(graph.evidence()['linux-entry']['blocked_by'], 'block-0')
        skipped.assert_not_called()

    def test_provenance_and_corruption_block_execution(self):
        valid = unified.State.create('boot-rom-boundary', 'image-a', 'scenario', None, {'clock': 0x80})
        self.assertEqual(valid.validate('boot-rom-boundary', 'image-a', 'scenario', None), {'clock': 0x80})
        for bad in (replace(valid, encoded=valid.encoded.replace(b'128', b'127')),
                    unified.State.create('boot-rom-boundary', 'image-b', 'scenario', None, {}),
                    unified.State.create('boot-rom-boundary', 'image-a', 'scenario', 'unexpected parent', {})):
            graph = unified.StageGraph('image-a', 'scenario')
            graph.states['boot-rom-boundary'] = bad
            downstream = Mock()
            graph.step('block-0', downstream)
            self.assertEqual(graph.terminal['outcome'], 'invalid-handoff-state')
            downstream.assert_not_called()

    def test_state_is_immutable_and_meaningful_change_affects_digest(self):
        payload = {'cpu': {'r0': 0x20}}
        state = unified.State.create('block-0', 'a', 'scenario', 'parent', payload)
        payload['cpu']['r0'] = 0x22
        tampered = unified.State.create('block-0', 'a', 'scenario', 'parent', payload)
        again = unified.State.create('block-0', 'a', 'scenario', 'parent', {'cpu': {'r0': 0x20}})
        self.assertEqual(state, again)
        self.assertNotEqual(state.sha256, tampered.sha256)
        self.assertEqual(state.validate('block-0', 'a', 'scenario', 'parent')['cpu']['r0'], 0x20)

    def test_cold_outcome_requires_real_dispatch_not_just_valid_afi(self):
        result = result_fixture()
        afibytes = unified.cold_afi(result, 2)
        self.assertEqual(afibytes[3], 0x9a)
        for key, value in (('boot_code_observed', 0), ('caller_return', '0x1'), ('dram_return', '0x5'),
                           ('main_continuation_boundary_reached', False), ('outcome', 'returned-dram-failure'),
                           ('outcome', 'resume-vector-transfer'), ('capacity_mib', 128)):
            with self.subTest(key=key, value=value), self.assertRaises(BoundaryError):
                unified.cold_afi(dict(result, **{key: value}), 2)
        result['afi']['generated'] = False
        with self.assertRaises(BoundaryError):
            unified.cold_afi(result, 2)

    def test_diagnostic_failure_is_valid_continuation_with_raw_afi(self):
        small = result_fixture(capacity=128)
        small.update(outcome='cold-success-diagnostic-failure', memory_test={'status': 'failed'})
        self.assertEqual(unified.cold_afi(small, 2)[12:], struct.pack('<I', 128 << 20))
        self.assertNotEqual(unified.cold_afi(small, 2), unified.cold_afi(result_fixture(), 2))
        small['memory_test']['status'] = 'passed'
        with self.assertRaises(BoundaryError):
            unified.cold_afi(small, 2)

    def test_image_and_fdt_validation(self):
        image = uimage(b'abcd')
        self.assertEqual(legacy_image(image, 2, 32)['size'], 4)
        for bad in (image[:-1], b'\0' * 4 + image[4:], image[:64] + b'efgh'):
            with self.assertRaises(BoundaryError):
                legacy_image(bad, 2, 32)
        dt = mini_fdt([(0, '', {'compatible': b'example,soc\0'})])
        self.assertEqual(fdt_layout(dt), (len(dt), []))
        with self.assertRaises(BoundaryError):
            fdt_layout(dt[:36] + bytes.fromhex('ffffffff') + dt[40:])

    def test_pinned_image_identity_rejected_before_emulation(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'koriki-v1.0.img').write_bytes(b'fixture')
            with self.assertRaisesRegex(ValueError, 'differs from manifest'):
                with unified.Release(directory, 'koriki-v1.0'):
                    self.fail('unverified image accepted')
            image = Path(directory) / 'koriki-v1.0.img'
            with self.assertRaisesRegex(ValueError, 'overwrite a firmware input'):
                unified.write_json_output(image, directory, b'{}')
            self.assertEqual(image.read_bytes(), b'fixture')


class ScriptModel(unittest.TestCase):
    def fixture(self, bootcmd=None):
        env = dict(
            bootcmd=bootcmd or 'if run loadenv; then env import -t 9000 ${filesize}; fi; '
                               'if test -n \\"${uenvcmd}\\"; then run uenvcmd; fi; run mboot',
            loadenv='fatload mmc 1:1 9000 uEnv.txt',
            mboot='fatload mmc 1:1 1000 uImage; fatload mmc 1:1 2000 ramdisk.img; '
                  'fatload mmc 1:1 3000 kernel.dtb; bootm 1000 2000 3000',
        )
        disk = Mock(size=8192)
        regs = [dict(slot=0, device_number=0, mmc_init='fail'),
                dict(slot=2, device_number=1, mmc_init='ok')]
        return Environment(env, 'compiled defaults', disk, regs, 2, 1 << 20)

    def test_script_uses_loaded_bytes_and_preserves_value_provenance(self):
        e = self.fixture()
        data = dict(zip(('uEnv.txt', 'uImage', 'ramdisk.img', 'kernel.dtb'),
                        (b'uenvcmd=setenv os_type linux;\nbootargs=argument  \n', b'k', b'r', b'd')))
        with (patch.object(boot, 'gpt_partition1', return_value={'start_lba': 2, 'sectors': 8}),
              patch.object(boot, 'fat_files', side_effect=lambda f, p, names: {n: (n, data[n]) for n in names})):
            e.run()
        self.assertEqual([entry.data for entry in e.bootm], [b'k', b'r', b'd'])
        self.assertEqual([entry.slot for entry in e.bootm], [2, 2, 2])
        self.assertEqual(e.values['bootargs'], 'argument  ')
        self.assertEqual(e.origins['bootargs'], 'uEnv.txt')
        self.assertEqual(e.values['os_type'], 'linux')
        self.assertIsNone(self.fixture().bootm)

    def test_missing_failed_and_unsupported_operations_block_bootm(self):
        for command, expected in (
            ('fatload mmc 0:1 1000 uImage', 'mmc-initialization-failure'),
            ('fatload mmc 1:2 1000 uImage', 'unmodelled-dependency'),
            ('bootm 1000 2000 3000', 'boot-file-loading-failure'),
            ('source 1000', 'environment-execution-failure'),
            ('run bootcmd', 'environment-execution-failure'),
        ):
            with self.subTest(command=command), self.assertRaises(BoundaryError) as raised:
                e = self.fixture(command)
                e.run()
            self.assertEqual(raised.exception.outcome, expected)
            self.assertIsNone(e.bootm)


class Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(EVIDENCE.read_bytes())
        cls.runs = cls.document['scenarios']['koriki-v1.0']

    def stage(self, scenario, stage):
        return self.runs[scenario]['stages'][stage]['state']

    def test_normal_paths_reach_linux_with_distinct_afis_and_storage(self):
        for medium, code, script, device in (('sd0', 0, 'run mmcboot', 0), ('sd2', 2, 'run emmcboot', 1)):
            name = medium + '-reference'
            self.assertEqual(self.runs[name]['terminal']['outcome'], 'linux-entry-boundary')
            self.assertEqual(self.stage(name, 'block-0')['boot_code'], code)
            raw = self.stage(name, 'uboot-entry')['afi_exact_hex']
            self.assertEqual(self.runs[name]['dram_result']['afi']['bytes'], raw)
            self.assertEqual(self.stage(name, 'device-tree')['afi_in_memory'], raw)
            self.assertEqual(self.stage(name, 'uboot-afi-and-ram')['afi']['getters']['device'], 0x20 | code)
            self.assertEqual(self.stage(name, 'boot-device')['bootcmd'], script)
            self.assertTrue(all(row['device'] == device for row in self.stage(name, 'boot-files')['images']))
            self.assertEqual(self.stage(name, 'linux-entry')['r2'], self.stage(name, 'device-tree')['ft_addr'])
        self.assertNotEqual(self.stage('sd0-reference', 'block-0')['machine']['trace'],
                            self.stage('sd2-reference', 'block-0')['machine']['trace'])

    def test_size_and_diagnostic_propagation(self):
        for case, size in (('sd2-128m', 128), ('sd2-reference', 256), ('sd2-512m', 512)):
            mem = size << 20
            self.assertEqual(self.runs[case]['dram_result']['capacity_mib'], size)
            self.assertEqual(self.stage(case, 'uboot-afi-and-ram')['afi']['gd_ram_size'], mem)
            self.assertEqual(self.stage(case, 'device-tree')['dt_memory_reg'], ['0x0', hex(mem)])
        self.assertEqual(self.runs['diagnostic-failure']['terminal']['outcome'], 'linux-entry-boundary')
        self.assertTrue(self.runs['diagnostic-failure']['diagnostic_warning'])
        self.assertTrue(self.runs['training-failure']['dram_result']['afi']['generated'])

    def test_terminal_paths_and_untouched_downstream_stages(self):
        for case, outcome, blocked in (
            ('rom-failure', 'rom-service-failure', 'early-loader-entry'),
            ('pmic-adfu', 'adfu-before-dram', 'dram-and-main-dispatch'),
            ('gpio-adfu', 'adfu-before-dram', 'dram-and-main-dispatch'),
            ('training-failure', 'returned-dram-failure', 'app-bin'),
            ('sd2-64m-storage-limit', 'invalid-memory-layout', 'app-bin'),
            ('zq-failure', 'returned-dram-failure', 'app-bin'),
            ('phy-poll', 'bounded-unbounded-poll', 'app-bin'),
            ('resume', 'resume-vector-transfer', 'load-app-and-uboot'),
            ('resume-power-off', 'resume-power-off', 'load-app-and-uboot'),
            ('sfvd-absent', 'app-unsupported', 'uboot-entry'),
            ('mmc-failure', 'mmc-initialization-failure', 'boot-files'),
            ('missing-kernel', 'boot-file-loading-failure', 'device-tree'),
            ('invalid-kernel', 'invalid-image', 'device-tree'),
            ('corrupt-dtb', 'invalid-image', 'device-tree'),
            ('unsupported-env', 'environment-execution-failure', 'boot-files'),
            ('invalid-afi', 'invalid-afi-handoff', 'mmc-registration'),
        ):
            with self.subTest(case=case):
                r = self.runs[case]
                self.assertEqual(r['terminal']['outcome'], outcome)
                self.assertEqual(r['stages'][blocked]['blocked_by'], r['terminal']['stage'])
        self.assertTrue(self.runs['gpio-adfu']['rom_reentry']['copy_requests'])
        for case in ('resume', 'resume-power-off', 'gpio-adfu'):
            self.assertFalse(self.runs[case]['dram_result']['afi']['generated'])

    def test_controls_and_observation(self):
        doc = self.document
        self.assertTrue(doc['obs_001']['sd2-reference']['all_match'])
        self.assertTrue(doc['obs_001']['sd2-c10-high']['all_match'])
        self.assertFalse(doc['obs_001']['sd2-strap-low']['all_match'])
        controls = doc['isolated_afi_controls']
        self.assertTrue(controls['missing']['fallback_used'])
        self.assertEqual(controls['below-minimum']['gd_ram_size'], 496 << 20)
        self.assertEqual(controls['at-minimum']['gd_ram_size'], 8 << 20)
        self.assertEqual(controls['distinctive-reserved-byte']['exact_hex'][6:8], 'a5')
        for release, results in doc['scenarios'].items():
            self.assertTrue(doc['firmware'][release]['verified'])
            self.assertEqual(results['sd2-reference']['terminal']['outcome'], 'linux-entry-boundary')
            self.assertEqual(results['sd0-reference']['terminal']['outcome'], 'linux-entry-boundary')


@unittest.skipUnless(FW and HAVE_ARM, 'set ATM_FIRMWARE_DIR to the five pinned expanded images')
class FirmwareBacked(unittest.TestCase):
    def test_byte_exact_reproduction(self):
        self.assertEqual(unified.evidence_bytes(unified.suite(FW)), EVIDENCE.read_bytes())

    def test_cpu_peripherals_and_records_stay_live(self):
        scenario = unified.Scenario('mixed-pads', dram_case='mixed-gpio-near-echo')
        with unified.Release(FW, unified.REFERENCE) as release:
            first = release.run(scenario, detail=True)
            reference = release.run(unified.SCENARIOS[0])
            again = release.run(scenario, detail=True)
        self.assertEqual(first, again)
        self.assertNotEqual(first['dram_result']['trace'], reference['dram_result']['trace'])
        stage = lambda name: first['stages'][name]['state']['machine']
        self.assertEqual(stage('pre-dram')['pmic'], stage('recovery-resume-decision')['pmic'])
        self.assertEqual(stage('recovery-resume-decision')['records'], stage('pre-dram')['records'])
        self.assertEqual(stage('dram-and-main-dispatch')['records'], stage('uboot-entry')['records'])
        self.assertEqual(stage('dram-and-main-dispatch')['gpio']['0xb01b0064'],
                         stage('recovery-resume-decision')['gpio']['0xb01b0064'])
        self.assertEqual(stage('uboot-entry')['afi'], first['dram_result']['afi']['bytes'])


if __name__ == '__main__':
    unittest.main()
