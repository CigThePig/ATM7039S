"""V3 capture: the real device/capture.sh run against synthetic trees, then the real parser.

Fixture values are illustrative (tests/capture_fixture.py), never measurements.
"""
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import runtime_capture as rc  # noqa: E402
import validate_observations as vo  # noqa: E402
import capture_fixture as cf  # noqa: E402
from test_research import dtb  # noqa: E402

SCRIPT = ROOT / 'device/capture.sh'
HOST_TOOLS = ['cat', 'head', 'wc', 'tr', 'sed', 'grep', 'find', 'tar', 'readlink', 'sha256sum', 'date', 'id', 'mkdir',
              'rm', 'dirname', 'sync', 'uname', 'dmesg', 'sort']


def run_capture(root, out, shell='sh', env=None, cwd=None, check=True, script=SCRIPT, args=None):
    e = {'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)}
    e.update(env or {})
    before = set(Path(out).glob('atm-capture-*')) if Path(out).exists() else set()
    proc = subprocess.run([shell, str(script), *(args if args is not None else [str(out)])], env=e,
                          capture_output=True, text=True, cwd=cwd, timeout=300)
    if check and proc.returncode != 0:
        raise AssertionError(f'capture failed ({proc.returncode}): {proc.stderr}')
    new = sorted(set(Path(out).glob('atm-capture-*')) - before) if Path(out).exists() else []
    return (new[-1] if new else None), proc


def toolbox(folder, exclude=()):
    """A PATH directory with the host tools the script needs, minus `exclude`."""
    folder.mkdir()
    for t in HOST_TOOLS:
        if t in exclude:
            continue
        path = shutil.which(t)
        if path:
            os.symlink(path, folder / t)
    return folder


def rewrite_manifest(capture, fn):
    """Edit an item, then re-sign the manifest as a forger would (manifest hash in capture-info)."""
    fn(capture)
    m = (capture / 'manifest.tsv').read_bytes()
    info = capture / 'capture-info.txt'
    info.write_text(re.sub(r'manifest_sha256=\w+', 'manifest_sha256=' + hashlib.sha256(m).hexdigest(), info.read_text()))


def statuses(result):
    return {f['id']: f['status'] for f in result['capture']['files']}


def outcomes(result):
    return {p['id']: p['outcome'] for p in result['predictions']}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def capture(self, name='c', **fixture):
        root = cf.build(self.tmp / (name + '-root'), **fixture)
        cap, _ = run_capture(root, self.tmp / (name + '-out'))
        return cap

    def parse(self, name='c', reference_dtb=None, **fixture):
        return rc.parse(self.capture(name, **fixture), reference_dtb=reference_dtb)


# ---------------------------------------------------------------- reference scenario

class ReferenceScenarioTests(Base):
    @classmethod
    def setUpClass(cls):
        cls.ctmp = Path(tempfile.mkdtemp())
        root = cf.build(cls.ctmp / 'root')
        cls.cap, cls.proc = run_capture(root, cls.ctmp / 'out')
        cls.result = rc.parse(cls.cap)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.ctmp, ignore_errors=True)

    def test_capture_authenticated_and_complete(self):
        c = self.result['capture']
        self.assertEqual(c['errors'], [])
        self.assertEqual(c['state'], 'authenticated-complete')
        self.assertEqual(c['capture_version'], '3')
        self.assertEqual(c['capture_format'], 2)
        self.assertFalse(c['admissible_as_evidence'], 'fixture captures must never be admissible')
        self.assertIn('fixture', ' '.join(c['warnings']))
        self.assertIn('Capture complete', self.proc.stdout)

    def test_expected_outcomes(self):
        got = outcomes(self.result)
        self.assertEqual(got, {
            'P-CPU': 'software-cap', 'P-CONSOLE': 'ttys3', 'P-BOOTARGS': 'match', 'P-CMDLINE-SRC': 'chosen-used',
            'P-UENV': 'uenv-applied', 'P-AFI-BOOTDEV': 'sd0', 'P-STRAP': 'strap-low', 'P-RAM': 'reference-256mib',
            'P-INITRD': 'as-reconstructed', 'P-BOOTDEV': 'boot-card-on-b0238000', 'P-NAND': 'boot-card-only',
            'P-KERNEL': 'uimage-build', 'P-KCONFIG': 'absent', 'P-GPU': 'pvr-loaded',
            # The fixture carries the catalogued uEnv.txt but not the 2.6 KB batocera-boot.conf text.
            'P-CARDCONFIG': 'files-modified', 'P-DRAM-LOG': 'requires-early-serial'})
        declared = {p['id'] for p in rc.load_predictions()}
        self.assertEqual(set(got), declared)

    def test_device_tree_structure(self):
        dt = self.result['summary']['device_tree']
        self.assertEqual(dt['source'], 'device-tree-dir')
        self.assertEqual(dt['root_cells'], dict(address=1, size=1, address_defaulted=False, size_defaulted=False))
        self.assertEqual(dt['memory_banks'], [dict(base=0, size=0x10000000)])
        self.assertEqual(dt['cpus'], ['cpu@0', 'cpu@1'])
        self.assertEqual(dt['chosen']['initrd_start'], 0x2000000)
        self.assertTrue(dt['index_check']['consistent'])
        self.assertFalse(dt['memreserve_visible'])
        self.assertEqual(dt['vendor_heaps_MB']['/reserved/normal']['dma_heap_size'], 128)

    def test_storage_model(self):
        sm = self.result['summary']['storage_model']
        self.assertEqual(sm['boot_disk'], 'mmcblk0')
        self.assertEqual(sm['boot_controller'], 'b0238000')
        self.assertEqual(sm['block_devices']['mmcblk0']['media'], 'sd-card')
        self.assertEqual(sm['block_devices']['loop0']['kind'], 'virtual')
        self.assertEqual(sm['mmc_cards']['emmc_boot_card'], dict(type='SD', controller='b0238000'))

    def test_card_serial_and_cid_never_captured(self):
        for p in (self.cap / 'items').iterdir():
            self.assertNotIn(cf.SERIAL, p.read_bytes().decode('latin1') if 'cmdline' not in p.name and 'dmesg' not in p.name
                             and 'device-tree' not in p.name else '', p.name)
        self.assertNotIn('cid', (self.cap / 'items/mmc-sysfs.out').read_text())

    def test_summary_redacts_identifiers(self):
        text = json.dumps(self.result)
        for secret in (cf.SERIAL, '02:11:22:33:44:55', '1234abcd5678ef90'):
            self.assertNotIn(secret, text)
        self.assertTrue(self.result['summary']['privacy']['serialno_in_cmdline'])
        self.assertIn(cf.SERIAL, (self.cap / 'items/cmdline.out').read_text(), 'raw items keep identifiers')
        report = rc.render_report(self.result)
        self.assertNotIn(cf.SERIAL, report)
        self.assertIn('P-RAM', report)

    def test_card_files(self):
        f = self.result['summary']['card_files']
        self.assertIsNone(f['boot_conf']['overclocking'])
        self.assertTrue(self.result['summary']['release_link']['boot_uenv_matches'])
        self.assertTrue(self.result['summary']['release_link']['koriki_version_matches'])

    def test_bootargs_comparison(self):
        b = self.result['summary']['bootargs']
        self.assertEqual(b['exact_variant'], 0)
        self.assertEqual(b['missing_tokens'], [])
        self.assertTrue(b['cmdline_equals_chosen'])
        self.assertTrue(b['cmdline_equals_boot_log'])

    def test_capture_info_and_readme(self):
        info = rc.read_info(self.cap / 'capture-info.txt')
        self.assertEqual(info['capture_status'], 'complete')
        self.assertEqual(info['write_failures'], '0')
        self.assertEqual(info['essential_not_ok'], '')
        self.assertTrue((self.cap / 'PRIVATE-README.txt').is_file())
        self.assertTrue((self.cap / 'DONE').is_file())


# ---------------------------------------------------------------- device tree variants

class DeviceTreeTests(Base):
    def test_symlinked_export_is_followed_inside_approved_path(self):
        r = self.parse(dt='symlink')
        f = {x['id']: x for x in r['capture']['files']}
        self.assertEqual(f['device-tree']['status'], 'ok')
        self.assertIn('resolved=/sys/firmware/devicetree/base', f['device-tree']['note'])
        self.assertEqual(r['summary']['device_tree']['memory_banks'], [dict(base=0, size=0x10000000)])

    def test_absolute_link_within_root_accepted(self):
        r = self.parse(dt='absolute-link')
        self.assertEqual(statuses(r)['device-tree'], 'ok')

    def test_link_escape_rejected_not_followed(self):
        cap = self.capture(dt='escape')
        r = rc.parse(cap)
        self.assertEqual(statuses(r)['device-tree'], 'rejected')
        self.assertEqual(statuses(r)['device-tree-index'], 'rejected')
        self.assertFalse((cap / 'items/device-tree.tar').exists())
        self.assertIn('device-tree', r['capture']['essential_not_ok'])
        self.assertEqual(r['capture']['state'], 'authenticated-partial')
        self.assertEqual(rc.read_info(cap / 'capture-info.txt')['capture_status'], 'partial')
        self.assertEqual(outcomes(r)['P-RAM'], 'kernel-view-only', 'no DT must never be read as a capacity result')

    def test_missing_export(self):
        r = self.parse(dt='absent')
        self.assertEqual(statuses(r)['device-tree'], 'missing')
        self.assertEqual(outcomes(r)['P-INITRD'], 'not-evaluable')
        self.assertEqual(outcomes(r)['P-CMDLINE-SRC'], 'not-evaluable')

    def test_memory_unit_address_and_two_banks(self):
        tree = cf.device_tree(memory_nodes={'memory@0': [(0, 0x8000000), (0x8000000, 0x8000000)]})
        r = self.parse(dt_tree=tree)
        dt = r['summary']['device_tree']
        self.assertEqual([m['path'] for m in dt['memory_nodes']], ['/memory@0'])
        self.assertEqual(dt['memory_total'], 0x10000000)
        self.assertEqual(outcomes(r)['P-RAM'], 'unexpected-layout')

    def test_two_memory_nodes(self):
        tree = cf.device_tree(memory_nodes={'memory@0': [(0, 0x8000000)], 'memory@8000000': [(0x8000000, 0x8000000)]})
        dt = self.parse(dt_tree=tree)['summary']['device_tree']
        self.assertEqual(len(dt['memory_nodes']), 2)
        self.assertEqual(dt['memory_total'], 0x10000000)

    def test_two_cell_addresses(self):
        tree = cf.device_tree(address_cells=2, size_cells=2, memory_nodes={'memory': [(0, 0x10000000)]})
        r = self.parse(dt_tree=tree)
        self.assertEqual(r['summary']['device_tree']['memory_banks'], [dict(base=0, size=0x10000000)])
        self.assertEqual(outcomes(r)['P-RAM'], 'reference-256mib')

    def test_malformed_reg(self):
        tree = cf.device_tree()
        tree['memory/reg'] = b'\0\0\0\0\0\0'
        r = self.parse(dt_tree=tree)
        self.assertIn('malformed', r['summary']['device_tree']['memory_nodes'][0]['reg_state'])
        self.assertEqual(outcomes(r)['P-RAM'], 'unexpected-layout')

    def test_reserved_memory_node(self):
        tree = cf.device_tree(extra={'reserved-memory': None, 'reserved-memory/#address-cells': cf.be32(1),
                                     'reserved-memory/#size-cells': cf.be32(1), 'reserved-memory/fb@e000000': None,
                                     'reserved-memory/fb@e000000/reg': cf.be32(0xe000000, 0x800000),
                                     'reserved-memory/fb@e000000/no-map': b''})
        rm = self.parse(dt_tree=tree)['summary']['device_tree']['reserved_memory']
        self.assertEqual(rm[0]['regions'], [dict(base=0xe000000, size=0x800000)])
        self.assertTrue(rm[0]['no_map'])

    def test_conflicting_chosen(self):
        tree = cf.device_tree(bootargs='console=ttyS3 something-else')
        r = self.parse(dt_tree=tree)
        self.assertEqual(outcomes(r)['P-CMDLINE-SRC'], 'chosen-ignored')

    def test_extended_command_line(self):
        cmd = 'android ' + cf.BOOTARGS
        r = self.parse(cmdline=cmd, dt_tree=cf.device_tree(bootargs=cf.BOOTARGS))
        self.assertEqual(outcomes(r)['P-CMDLINE-SRC'], 'chosen-extended')
        self.assertEqual(outcomes(r)['P-BOOTARGS'], 'tokens-differ')

    def test_unreadable_property_recorded(self):
        root = cf.build(self.tmp / 'root')
        prop = root / 'proc/device-tree/model'
        prop.unlink()
        prop.mkdir()  # tar archives it as a node, the index lists it as a directory: consistent
        (root / 'proc/device-tree/chosen/bootargs').unlink()
        cap, _ = run_capture(root, self.tmp / 'out')
        r = rc.parse(cap)
        self.assertEqual(outcomes(r)['P-CMDLINE-SRC'], 'chosen-bootargs-absent')

    def test_index_detects_member_missing_from_tar(self):
        cap = self.capture()

        def drop(c):
            data = (c / 'items/device-tree.tar').read_bytes()
            out = io.BytesIO()
            with tarfile.open(fileobj=io.BytesIO(data)) as src, tarfile.open(fileobj=out, mode='w') as dst:
                for m in src.getmembers():
                    if m.name != './memory/reg':
                        dst.addfile(m, src.extractfile(m) if m.isfile() else None)
            (c / 'items/device-tree.tar').write_bytes(out.getvalue())
            sha = hashlib.sha256(out.getvalue()).hexdigest()
            m = c / 'manifest.tsv'
            m.write_text(re.sub(r'(device-tree\ttree\t[^\t]+\tok\t)\d+\t\w+', rf'\g<1>{len(out.getvalue())}\t{sha}', m.read_text()))
        rewrite_manifest(cap, drop)
        r = rc.parse(cap)
        self.assertEqual(r['capture']['errors'], [])
        chk = r['summary']['device_tree']['index_check']
        self.assertFalse(chk['consistent'])
        self.assertIn('/memory/reg', chk['missing_from_tar'])

    def test_reference_dtb_comparison(self):
        ref = self.tmp / 'ref.dtb'
        ref.write_bytes(dtb({'model': b'RG35XX ATM7039 based handheld gaming console (V6C)\0'}))
        cmp = self.parse(reference_dtb=ref)['summary']['device_tree_vs_reference']
        self.assertEqual(cmp['reference_catalogued'], [])
        self.assertIn('/chosen/bootargs', cmp['added'])
        self.assertNotIn('/model', cmp['changed'])

    def test_fdt_blob_used_when_directory_missing(self):
        blob = dtb({'#address-cells': b'\0\0\0\1', '#size-cells': b'\0\0\0\1'})
        r = self.parse(dt='absent', fdt=blob)
        self.assertEqual(r['summary']['device_tree']['source'], 'fdt-blob')
        self.assertTrue(r['summary']['device_tree']['memreserve_visible'])


class TarSafetyTests(unittest.TestCase):
    def tar(self, members):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w') as t:
            for name, kind, data in members:
                info = tarfile.TarInfo(name)
                if kind == 'file':
                    info.size = len(data)
                    t.addfile(info, io.BytesIO(data))
                elif kind == 'sym':
                    info.type = tarfile.SYMTYPE
                    info.linkname = data
                    t.addfile(info)
                elif kind == 'dir':
                    info.type = tarfile.DIRTYPE
                    t.addfile(info)
        return out.getvalue()

    def test_escapes_and_links_never_followed(self):
        data = self.tar([('.', 'dir', None), ('./memory', 'dir', None), ('./memory/reg', 'file', cf.be32(0, 0x10000000)),
                         ('../etc/passwd', 'file', b'x'), ('/etc/shadow', 'file', b'x'),
                         ('./chosen', 'sym', '/etc'), ('./a/../../b', 'file', b'y')])
        tree = rc.dt_from_tar(data)
        self.assertEqual(sorted(tree['unsafe']), ['../etc/passwd', './a/../../b', '/etc/shadow'])
        self.assertEqual(tree['links'], {'/chosen': '/etc'})
        self.assertEqual(rc.dt_analysis(tree)['memory_banks'], [dict(base=0, size=0x10000000)])

    def test_legacy_layout_prefix(self):
        data = self.tar([('device-tree', 'dir', None), ('device-tree/memory', 'dir', None),
                         ('device-tree/memory/reg', 'file', cf.be32(0, 0x10000000))])
        self.assertEqual(rc.dt_analysis(rc.dt_from_tar(data))['memory_total'], 0x10000000)

    def test_truncated_and_malformed_archives(self):
        data = self.tar([('./memory', 'dir', None), ('./memory/reg', 'file', cf.be32(0, 0x10000000) * 64)])
        self.assertIn('archive truncated: no end-of-archive marker', rc.dt_from_tar(data[:700])['errors'])
        self.assertEqual(rc.dt_from_tar(data)['errors'], [])
        with self.assertRaises(tarfile.TarError):
            rc.dt_from_tar(b'not a tar archive' * 40)

    def test_default_cells_when_root_omits_them(self):
        tree = rc._new_tree()
        tree['nodes']['/memory'] = {'device_type': b'memory\0', 'reg': cf.be32(0, 0x10000000)}
        a = rc.dt_analysis(tree)
        self.assertTrue(a['root_cells']['address_defaulted'])
        self.assertEqual(a['memory_total'], 0x10000000)


# ---------------------------------------------------------------- CPU, memory, storage variants

class ScenarioTests(Base):
    def test_four_core_variants(self):
        self.assertEqual(outcomes(self.parse('a', cpus=('0-3', '0-3', '0-1', '2-3'), smp=2))['P-CPU'], 'policy-or-startup')
        self.assertEqual(outcomes(self.parse('b', cpus=('0-3', '0-3', '0-3', ''), smp=4))['P-CPU'], 'four-online')
        self.assertEqual(outcomes(self.parse('c', ncores=None))['P-CPU'], 'no-scu-line')
        self.assertEqual(outcomes(self.parse('d', ncores=2))['P-CPU'], 'scu-two')
        self.assertEqual(outcomes(self.parse('e', cpus=('0-1', '0', '0-1', '')))['P-CPU'], 'inconsistent-masks')

    def test_powersave_cap_reported(self):
        r = self.parse(cmdline=cf.BOOTARGS + ' powersave', dmesg_extra=['[    0.010000] powersave now'])
        p = next(x for x in r['predictions'] if x['id'] == 'P-CPU')
        self.assertEqual(p['outcome'], 'software-cap')
        self.assertEqual(p['values']['cmdline_cpu_limits'], ['powersave'])
        self.assertTrue(p['values']['dmesg_powersave_now'])

    def test_512mib_alternative(self):
        tree = cf.device_tree(memory_nodes={'memory': [(0, 0x20000000)]})
        r = self.parse(dt_tree=tree, iomem='00000000-1fffffff : System RAM\n', mem_total=524288)
        self.assertEqual(outcomes(r)['P-RAM'], 'other-supported-size')

    def test_uboot_fallback(self):
        tree = cf.device_tree(memory_nodes={'memory': [(0, 0x1f000000)]})
        r = self.parse(dt_tree=tree, iomem='00000000-0fffffff : System RAM\n')
        self.assertEqual(outcomes(r)['P-RAM'], 'uboot-fallback')

    def test_sources_disagree(self):
        r = self.parse(iomem='00000000-1fffffff : System RAM\n')
        self.assertEqual(outcomes(r)['P-RAM'], 'sources-disagree')

    def test_cmdline_memory_limit(self):
        r = self.parse(cmdline=cf.BOOTARGS + ' mem=128M')
        self.assertEqual(outcomes(r)['P-RAM'], 'cmdline-limited')

    def test_missing_memory_maps(self):
        r = self.parse(dt='absent', missing=('proc/iomem', 'proc/meminfo'), dmesg_extra=())
        self.assertIn(outcomes(r)['P-RAM'], ('not-evaluable', 'kernel-view-only'))
        self.assertEqual(r['capture']['state'], 'authenticated-partial')

    def test_zeroed_iomem_without_root(self):
        self.assertTrue(rc.iomem('00000000-00000000 : System RAM\n')['addresses_zeroed'])

    def test_storage_scenarios(self):
        cases = {'second-card': ('additional-card', 'second-card-present'), 'emmc': ('non-removable-mmc', 'second-card-present'),
                 'unknown-type': ('type-unknown', 'boot-card-on-b0238000'), 'nand': ('other-block-device', 'boot-card-on-b0238000'),
                 'mismatch': ('boot-card-only', 'boot-card-on-b0230000')}
        for scenario, (nand, bootdev) in cases.items():
            with self.subTest(scenario=scenario):
                got = outcomes(self.parse(scenario, storage_scenario=scenario))
                self.assertEqual((got['P-NAND'], got['P-BOOTDEV']), (nand, bootdev))

    def test_probe_entry_cap_is_incomplete_not_boot_card_only(self):
        """Regression (Codex review): a NAND disk past the 64-entry probe cap must not vanish."""
        root = cf.build(self.tmp / 'root', storage_scenario='nand')
        block, parts = root / 'sys/block', root / 'proc/partitions'
        for i in range(2, 64):
            d = root / f'sys/devices/virtual/block/loop{i}'
            d.mkdir(parents=True)
            (d / 'removable').write_text('0\n')
            os.symlink(f'../devices/virtual/block/loop{i}', block / f'loop{i}')
            parts.write_text(parts.read_text() + f'    7 {i:>8} {0:>10} loop{i}\n')
        cap, _ = run_capture(root, self.tmp / 'out')
        r = rc.parse(cap)
        sm = r['summary']['storage_model']
        self.assertIn('entry-limit', sm['probe_skipped'])
        self.assertIn('nand0', sm['partitions_not_listed'])
        self.assertEqual(outcomes(r)['P-NAND'], 'incomplete')

    def test_partition_disk_missing_from_listing(self):
        r = self.parse()
        sm = r['summary']['storage_model']
        self.assertEqual(sm['partitions_not_listed'], [])
        self.assertFalse(sm['enumeration_incomplete'])

    def test_missing_sysfs_links(self):
        r = self.parse(storage_scenario='no-links')
        sm = r['summary']['storage_model']
        self.assertIsNone(sm['block_devices']['mmcblk0']['controller'])
        self.assertEqual(outcomes(r)['P-BOOTDEV'], 'other')

    def test_device_name_alone_is_not_removability(self):
        sm = rc.storage_model({'storage': {'block_links': {'mmcblk0': '../devices/b0238000.mmc/x/block/mmcblk0'},
                                           'mounts': [dict(device='/dev/mmcblk0p1', mountpoint='/boot', fstype='vfat', options='rw')]}})
        self.assertEqual(rc._p_nand({'storage_model': sm})[0], 'type-unknown')

    def test_strap_high_and_other_uart(self):
        cmd = cf.BOOTARGS.replace('0x705x ', '0x705x allenS500=1 ')
        got = outcomes(self.parse('a', cmdline=cmd))
        self.assertEqual((got['P-STRAP'], got['P-BOOTARGS']), ('strap-high', 'match'))
        got = outcomes(self.parse('b', cmdline=cf.BOOTARGS.replace('ttyS3', 'ttyS5').replace('boot_dev=sd0', 'boot_dev=sd2')))
        self.assertEqual((got['P-CONSOLE'], got['P-AFI-BOOTDEV']), ('other-enabled-uart', 'sd2'))

    def test_whitespace_only_difference(self):
        got = outcomes(self.parse(cmdline=' '.join(cf.BOOTARGS.split())))
        self.assertEqual(got['P-BOOTARGS'], 'whitespace-differs')

    def test_overclock_detected(self):
        self.assertEqual(outcomes(self.parse(boot_conf_extra='overclocking=turbo\n'))['P-CARDCONFIG'], 'overclock-set')

    def test_initrd_variants(self):
        tree = cf.device_tree(initrd=(0x2000000, 0x2100000))
        self.assertEqual(outcomes(self.parse('a', dt_tree=tree))['P-INITRD'], 'different-placement')
        self.assertEqual(outcomes(self.parse('b', dt_tree=cf.device_tree(initrd=None)))['P-INITRD'], 'absent')
        r = self.parse('c', dmesg_extra=['[    0.200000] INITRD: 0x02000000+0x003a43b1 is not a memory region - disabling initrd'])
        self.assertEqual(outcomes(r)['P-INITRD'], 'kernel-rejected')

    def test_loader_lines_in_kernel_log_flagged(self):
        r = self.parse('a', dmesg_extra=['[    0.000000] Ok:DCU_CFG:0x202c,256MByte Cap.'])
        self.assertEqual(outcomes(r)['P-DRAM-LOG'], 'loader-lines-present')
        # Kernel symbol names contain the same words (atc2603c_audio_get_pmu_status); they must not match.
        r = self.parse('b', dmesg_extra=['[    5.000000] atc2603c_audio_get_pmu_status: pa up'])
        self.assertEqual(outcomes(r)['P-DRAM-LOG'], 'requires-early-serial')

    def test_kconfig_present(self):
        r = self.parse(kconfig='CONFIG_SMP=y\nCONFIG_NR_CPUS=4\nCONFIG_CMDLINE=""\n')
        p = next(x for x in r['predictions'] if x['id'] == 'P-KCONFIG')
        self.assertEqual(p['outcome'], 'nr-cpus-4')
        self.assertEqual(p['values']['cmdline_policy'], 'bootloader /chosen bootargs only')

    def test_kconfig_unreadable(self):
        root = cf.build(self.tmp / 'root')
        (root / 'proc/config.gz').write_bytes(b'not gzip')
        cap, _ = run_capture(root, self.tmp / 'out')
        self.assertEqual(outcomes(rc.parse(cap))['P-KCONFIG'], 'unreadable')

    def test_other_kernel(self):
        self.assertEqual(outcomes(self.parse(kernel_version='Linux version 4.9.170'))['P-KERNEL'], 'other')


# ---------------------------------------------------------------- script robustness

class RobustnessTests(Base):
    def test_missing_commands_recorded(self):
        root = cf.build(self.tmp / 'root')
        tools = toolbox(self.tmp / 'bin', exclude=('tar', 'find'))
        cap, _ = run_capture(root, self.tmp / 'out', env={'ATM_CAPTURE_PATH': str(tools)})
        r = rc.parse(cap)
        st = {f['id']: f for f in r['capture']['files']}
        self.assertEqual(st['device-tree']['status'], 'unsupported')
        self.assertEqual(st['device-tree']['note'], 'tar-not-found')
        self.assertEqual(r['capture']['state'], 'authenticated-partial')
        self.assertIn('path_override', r['capture']['path_override'] and 'path_override' or '')

    def test_no_hash_tool_cannot_be_authenticated(self):
        root = cf.build(self.tmp / 'root')
        tools = toolbox(self.tmp / 'bin', exclude=('sha256sum',))
        cap, _ = run_capture(root, self.tmp / 'out', env={'ATM_CAPTURE_PATH': str(tools)})
        r = rc.parse(cap)
        self.assertEqual(r['capture']['state'], 'quarantined')
        self.assertTrue(any('SHA-256' in e for e in r['capture']['errors']))
        self.assertTrue(all(p.get('quarantined') for p in r['predictions']))

    def test_without_head_reads_unbounded_but_recorded(self):
        root = cf.build(self.tmp / 'root')
        tools = toolbox(self.tmp / 'bin', exclude=('head',))
        cap, _ = run_capture(root, self.tmp / 'out', env={'ATM_CAPTURE_PATH': str(tools)})
        r = rc.parse(cap)
        self.assertIn('head -c', ' '.join(r['capture']['warnings']))
        self.assertEqual(statuses(r)['cmdline'], 'ok')

    def test_read_failure_is_error_not_ok(self):
        root = cf.build(self.tmp / 'root')
        (root / 'proc/interrupts').unlink()
        (root / 'proc/interrupts').mkdir()  # reading a directory fails like an I/O error
        cap, _ = run_capture(root, self.tmp / 'out')
        r = rc.parse(cap)
        self.assertEqual(statuses(r)['interrupts'], 'error')
        self.assertIn('stderr', next(f for f in r['capture']['files'] if f['id'] == 'interrupts'))
        self.assertEqual(r['capture']['errors'], [])

    def test_large_item_truncated(self):
        root = cf.build(self.tmp / 'root')
        (root / 'proc/interrupts').write_bytes(b'x' * (4 * 1024 * 1024 + 100))
        cap, _ = run_capture(root, self.tmp / 'out')
        r = rc.parse(cap)
        f = next(f for f in r['capture']['files'] if f['id'] == 'interrupts')
        self.assertEqual(f['status'], 'truncated')
        self.assertEqual(f['bytes'], 4 * 1024 * 1024 + 1)

    def test_permission_denied(self):
        root = cf.build(self.tmp / 'root')
        (root / 'proc/iomem').chmod(0)
        (root / 'proc/device-tree/chosen/bootargs').chmod(0)
        out = self.tmp / 'out'
        out.mkdir()
        env = {'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)}
        cmd = ['sh', str(SCRIPT), str(out)]
        if os.geteuid() == 0:
            if not shutil.which('setpriv'):
                self.skipTest('needs a non-root user')
            os.chmod(self.tmp, 0o755)
            os.chown(out, 65534, 65534)
            cmd = ['setpriv', '--reuid=65534', '--regid=65534', '--clear-groups', *cmd]
        subprocess.run(cmd, env=env, check=True, capture_output=True, timeout=300)
        r = rc.parse(next(out.glob('atm-capture-*')))
        st = statuses(r)
        self.assertEqual(st['iomem'], 'denied')
        self.assertEqual(st['device-tree'], 'denied')
        self.assertIn('without root', ' '.join(r['capture']['warnings']))
        self.assertEqual(r['capture']['state'], 'authenticated-partial')

    def test_read_only_output_fails_cleanly(self):
        root = cf.build(self.tmp / 'root')
        out = self.tmp / 'ro'
        out.mkdir()
        out.chmod(0o555)
        cmd = ['sh', str(SCRIPT), str(out)]
        if os.geteuid() == 0:
            if not shutil.which('setpriv'):
                self.skipTest('needs a non-root user')
            os.chmod(self.tmp, 0o755)
            cmd = ['setpriv', '--reuid=65534', '--regid=65534', '--clear-groups', *cmd]
        proc = subprocess.run(cmd, env={'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)}, capture_output=True,
                              text=True, timeout=300)
        self.assertEqual(proc.returncode, 1)
        self.assertIn('cannot create a new capture folder', proc.stderr)
        self.assertEqual(list(out.iterdir()), [])

    def test_repeated_captures_distinct_and_earlier_untouched(self):
        root = cf.build(self.tmp / 'root')
        out = self.tmp / 'out'
        first, _ = run_capture(root, out)
        snapshot = {p: p.read_bytes() for p in first.rglob('*') if p.is_file()}
        second, _ = run_capture(root, out)
        self.assertNotEqual(first, second)
        self.assertEqual({p: p.read_bytes() for p in first.rglob('*') if p.is_file()}, snapshot)
        self.assertEqual(rc.parse(second)['capture']['errors'], [])

    def test_frozen_clock_still_gives_new_folders(self):
        root = cf.build(self.tmp / 'root')
        tools = toolbox(self.tmp / 'bin', exclude=('date',))
        (tools / 'date').write_text('#!/bin/sh\necho 19700101T000000Z\n')
        (tools / 'date').chmod(0o755)
        out = self.tmp / 'out'
        a, _ = run_capture(root, out, env={'ATM_CAPTURE_PATH': str(tools)})
        b, _ = run_capture(root, out, env={'ATM_CAPTURE_PATH': str(tools)})
        self.assertNotEqual(a, b)
        self.assertIn('19700101T000000Z', a.name)

    def test_no_writes_outside_output(self):
        root = cf.build(self.tmp / 'root')
        work = self.tmp / 'work'
        shutil.copy(SCRIPT, self.tmp / 'capture.sh')
        work.mkdir()

        def tree(base):
            return sorted((str(p.relative_to(base)), p.is_symlink(), p.read_bytes() if p.is_file() and not p.is_symlink() else None)
                          for p in base.rglob('*'))
        before = (tree(root), tree(self.tmp / 'work'), sorted(x.name for x in self.tmp.iterdir()))
        cap, _ = run_capture(root, self.tmp / 'out', cwd=work, script=self.tmp / 'capture.sh')
        after = (tree(root), tree(self.tmp / 'work'), sorted(x.name for x in self.tmp.iterdir() if x.name != 'out'))
        self.assertEqual(before, after)
        self.assertEqual([p.name for p in (self.tmp / 'out').iterdir()], [cap.name])

    def test_relative_output_parent(self):
        """Regression: v1 lost the device-tree tar when the output folder was relative."""
        root = cf.build(self.tmp / 'root')
        work = self.tmp / 'cwd'
        work.mkdir()
        subprocess.run(['sh', str(SCRIPT), 'out'], cwd=work, check=True, capture_output=True,
                       env={'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)})
        cap = next((work / 'out').glob('atm-capture-*'))
        self.assertEqual(statuses(rc.parse(cap))['device-tree'], 'ok')

    def test_default_output_is_script_folder(self):
        root = cf.build(self.tmp / 'root')
        ports = self.tmp / 'roms/ports'
        ports.mkdir(parents=True)
        shutil.copy(SCRIPT, ports / 'ATM7039S-capture.sh')
        subprocess.run(['sh', str(ports / 'ATM7039S-capture.sh')], check=True, capture_output=True, cwd='/',
                       env={'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)})
        self.assertEqual(len(list(ports.glob('atm-capture-*'))), 1)

    def test_launch_like_simplemenu(self):
        """cmd_invoker.dge runs `eval "$3" &` on the entry path (UI-003): the script must start by path."""
        root = cf.build(self.tmp / 'root')
        ports = self.tmp / 'roms/ports'
        ports.mkdir(parents=True)
        target = ports / 'ATM7039S-capture.sh'
        shutil.copy(SCRIPT, target)
        target.chmod(0o755)
        bash = shutil.which('bash')
        if not bash:
            self.skipTest('bash not available')
        subprocess.run([bash, '-c', 'export HOME=/tmp SDL_NOMOUSE=1; LAUNCH_COMMAND="$1"; eval "$LAUNCH_COMMAND" & wait',
                        'invoker', str(target)], check=True, capture_output=True, cwd='/',
                       env={'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)})
        cap = next(ports.glob('atm-capture-*'))
        self.assertEqual(rc.parse(cap)['capture']['errors'], [])

    def test_list_mode_reads_nothing(self):
        out = subprocess.run(['sh', str(SCRIPT), '--list'], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.splitlines(), rc.script_allowlist(SCRIPT.read_text()))


# ---------------------------------------------------------------- authentication and tampering

class AuthenticationTests(Base):
    def setUp(self):
        super().setUp()
        self.cap = self.capture()

    def errors(self):
        return rc.parse(self.cap)['capture']['errors']

    def test_tampered_item(self):
        (self.cap / 'items/cmdline.out').write_text('powersave\n')
        self.assertTrue(any('cmdline' in e for e in self.errors()))

    def test_tampered_item_with_forged_manifest_still_caught(self):
        def edit(c):
            (c / 'items/cmdline.out').write_text('powersave\n')
            m = c / 'manifest.tsv'
            m.write_text(m.read_text().replace('\tcmdline\t', '\tcmdline\t'))
        rewrite_manifest(self.cap, edit)
        self.assertTrue(any('mismatch cmdline' in e for e in self.errors()))

    def test_manifest_edit_detected(self):
        m = self.cap / 'manifest.tsv'
        m.write_text('\n'.join(m.read_text().splitlines()[:-1]) + '\n')
        self.assertTrue(any('manifest' in e for e in self.errors()))

    def test_malformed_manifest(self):
        (self.cap / 'manifest.tsv').write_text('id\tsomething\n')
        with self.assertRaisesRegex(ValueError, 'header'):
            rc.parse(self.cap)

    def test_allowlist_drift(self):
        (self.cap / 'allowlist.txt').write_text('mem|file|/dev/mem\n')
        self.assertTrue(any('allowlist' in e for e in self.errors()))

    def test_unknown_script(self):
        info = self.cap / 'capture-info.txt'
        info.write_text(re.sub('script_sha256=[0-9a-f]+', 'script_sha256=' + '0' * 64, info.read_text()))
        errs = self.errors()
        self.assertTrue(any('known device/capture.sh' in e for e in errs))
        self.assertEqual(rc.parse(self.cap)['capture']['state'], 'quarantined')

    def test_claimed_version_must_match_hash(self):
        info = self.cap / 'capture-info.txt'
        info.write_text(info.read_text().replace('capture_version=3', 'capture_version=2'))
        self.assertTrue(any('capture_version' in e for e in self.errors()))

    def test_interrupted_capture(self):
        (self.cap / 'DONE').unlink()
        r = rc.parse(self.cap)
        self.assertTrue(any('DONE marker absent' in e for e in r['capture']['errors']))
        self.assertEqual(r['capture']['state'], 'quarantined')

    def test_forged_complete_status(self):
        def edit(c):
            (c / 'items/dmesg.out').unlink()
            m = c / 'manifest.tsv'
            m.write_text(re.sub(r'dmesg\tcmd\tdmesg\tok\t\d+\t\w+', 'dmesg\tcmd\tdmesg\tmissing\t\t', m.read_text()))
        rewrite_manifest(self.cap, edit)
        self.assertTrue(any('claims complete' in e for e in self.errors()))

    def test_status_missing_with_file(self):
        def edit(c):
            (c / 'items/fdt.out').write_text('x')
        edit(self.cap)
        self.assertTrue(any('marked missing but a file exists' in e for e in self.errors()))

    def test_unexpected_files_ignored_with_warning(self):
        (self.cap / 'items/extra.out').write_text('x')
        (self.cap / 'notes.txt').write_text('x')
        r = rc.parse(self.cap)
        self.assertEqual(r['capture']['errors'], [])
        self.assertEqual(len([w for w in r['capture']['warnings'] if 'unexpected file' in w]), 2)

    def test_write_failure_flag(self):
        def edit(c):
            info = c / 'capture-info.txt'
            info.write_text(info.read_text().replace('write_failures=0', 'write_failures=1'))
        edit(self.cap)
        self.assertTrue(any('failed writes' in e for e in self.errors()))

    def test_unsafe_item_name(self):
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            rc.item_path(self.cap, dict(id='../x', kind='file'))


class LegacyCaptureTests(unittest.TestCase):
    """Captures from script versions 1-2 (manifest format 1) stay parseable."""

    def build(self, tmp, version):
        v = next(x for x in rc.known_versions() if x['version'] == version)
        cap = tmp / 'atm-capture-legacy'
        (cap / 'items').mkdir(parents=True)
        files = {'version': cf.KORIKI_VERSION + '\n', 'cmdline': cf.BOOTARGS + '\n', 'cpu-possible': '0-1\n',
                 'cpu-present': '0-1\n', 'cpu-online': '0-1\n',
                 'block-links': 'lrwxrwxrwx 1 root root 0 Jan 1 mmcblk0 -> ../devices/b0238000.mmc/mmc_host/mmc0/emmc_boot_card/block/mmcblk0\n',
                 'mounts': '/dev/mmcblk0p1 /boot vfat rw 0 0\n'}
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w') as t:
            for name in ('device-tree', 'device-tree/memory'):
                i = tarfile.TarInfo(name)
                i.type = tarfile.DIRTYPE
                t.addfile(i)
            i = tarfile.TarInfo('device-tree/memory/reg')
            i.size = 8
            t.addfile(i, io.BytesIO(cf.be32(0, 0x10000000)))
        rows = ['id\tkind\ttarget\tstatus\tbytes\tsha256']
        for line in v['allowlist']:
            ident, kind, target = line.split('|')
            data = out.getvalue() if ident == 'device-tree' else files.get(ident, '').encode() or None
            if data is None:
                rows.append(f'{ident}\t{kind}\t{target}\tmissing\t\t')
                continue
            (cap / 'items' / (ident + ('.tar' if kind == 'tree' else '.out'))).write_bytes(data)
            rows.append(f'{ident}\t{kind}\t{target}\tok\t{len(data)}\t{hashlib.sha256(data).hexdigest()}')
        (cap / 'manifest.tsv').write_text('\n'.join(rows) + '\n')
        (cap / 'allowlist.txt').write_text('\n'.join(v['allowlist']) + '\n')
        msha = hashlib.sha256((cap / 'manifest.tsv').read_bytes()).hexdigest()
        (cap / 'capture-info.txt').write_text(f"capture_version={version}\nscript_sha256={v['sha256']}\nuid=0\n"
                                              f"fixture_root=none\nmanifest_sha256={msha}\n")
        (cap / 'DONE').write_text('')
        return cap

    def test_version_2_capture(self):
        with tempfile.TemporaryDirectory() as d:
            r = rc.parse(self.build(Path(d), 2))
            self.assertEqual(r['capture']['errors'], [])
            self.assertEqual(r['capture']['capture_format'], 1)
            self.assertEqual(r['summary']['device_tree']['memory_total'], 0x10000000)
            got = outcomes(r)
            self.assertEqual(got['P-RAM'], 'reference-256mib')
            self.assertEqual(got['P-BOOTDEV'], 'boot-card-on-b0238000')
            self.assertEqual(got['P-NAND'], 'type-unknown', 'ls -l links carry no card type')


# ---------------------------------------------------------------- parser units and privacy

class ParserTests(unittest.TestCase):
    def test_cpulist(self):
        self.assertEqual(rc.cpulist('0-1,3\n'), [0, 1, 3])
        self.assertEqual(rc.cpulist('\n'), [])
        with self.assertRaises(ValueError):
            rc.cpulist('3-1')

    def test_cpu_hint_outcomes(self):
        base = dict(possible=[0, 1, 2, 3], present=[0, 1, 2, 3], online=[0, 1])
        self.assertEqual(rc.cpu_hint(dict(base, scu_ncores=4))['outcome'], 'policy-or-startup')
        self.assertEqual(rc.cpu_hint(dict(base, scu_ncores=2))['outcome'], 'scu-two')
        self.assertEqual(rc.cpu_hint(dict(base, online=[0, 1, 2, 3], scu_ncores=4))['outcome'], 'four-online')
        self.assertEqual(rc.cpu_hint(dict(possible=[0]))['outcome'], 'incomplete')

    def test_console_outcomes(self):
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('console=ttyS2,115200')})[0], 'disabled-uart')
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('quiet')})[0], 'no-console')
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('console=ttyS0 console=tty1')})[0], 'multiple')
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('console=ttyS3')})[0], 'ttys3')

    def test_dmesg_parsing(self):
        d = rc.dmesg(cf.dmesg_text(cf.BOOTARGS))
        self.assertEqual((d['scu_ncores'], d['smp_activated'], d['vendor_reserved_MB']), (4, 2, 42))
        self.assertEqual(d['memory_line']['total_kB'], 262144)
        self.assertEqual(d['command_line'], cf.BOOTARGS)
        self.assertTrue(d['matches']['boot_card'])
        r = rc.dmesg('Linux version x\nSMP: Total of 2 processors activated.\nMemory: 214MB = 214MB total\n')
        self.assertEqual(r['smp_activated'], 2)
        self.assertFalse(r['begins_near_boot'])
        self.assertEqual(r['memory_line']['banks_total_MB'], 214)

    def test_decode_reg(self):
        self.assertEqual(rc.decode_reg(cf.be32(0, 0, 0, 0x10000000), 2, 2)[0], [dict(base=0, size=0x10000000)])
        self.assertIn('malformed', rc.decode_reg(b'\0' * 12, 1, 1)[1])

    def test_kconfig_policies(self):
        def pol(text):
            return rc.kconfig(gzip.compress(text.encode()))['cmdline_policy']
        self.assertIn('replaces', pol('CONFIG_CMDLINE="console=ttyS0"\nCONFIG_CMDLINE_FORCE=y\n'))
        self.assertIn('extends', pol('CONFIG_CMDLINE="a"\nCONFIG_CMDLINE_EXTEND=y\n'))
        self.assertIn('only when', pol('CONFIG_CMDLINE="a"\n'))
        self.assertFalse(rc.kconfig(b'junk')['valid'])

    def test_redaction_variants(self):
        cases = ['androidboot.serialno=ABC123DEF', 'AndroidBoot.SerialNo=abc', 'serialno=ABC123', 'serial_number: X9Y8Z7',
                 'Serial\t\t: 1234abcd5678ef90', 'SN=0123456789', 'iSerialNumber=XYZ', 'cid 035344534431364780abcdef12',
                 'eth0: MAC 02:11:22:33:44:55', 'wlan0 02-11-22-33-44-55', 'UUID=1234-ABCD', 'PARTUUID=0001abcd-01',
                 'fs 123e4567-e89b-12d3-a456-426614174000']
        secrets = ['ABC123DEF', 'abc', 'ABC123', 'X9Y8Z7', '1234abcd5678ef90', '0123456789', 'XYZ', 'abcdef12',
                   '02:11:22:33:44:55', '02-11-22-33-44-55', '1234-ABCD', '0001abcd-01', '123e4567']
        for text, secret in zip(cases, secrets):
            with self.subTest(text=text):
                self.assertNotIn(secret, rc.redact(text))
        self.assertEqual(rc.redact('Serial\t\t: 0000000000000000'), 'Serial\t\t: 0000000000000000')
        self.assertEqual(rc.redact({'k': ['boot_dev=sd0']}), {'k': ['boot_dev=sd0']})
        self.assertNotIn('ABC', rc.redact({'androidboot.serialno=ABC': 1}))
        self.assertEqual(rc.redact('`x androidboot.serialno=ABC`'), '`x androidboot.serialno=<redacted>`')

    def test_cpuinfo_serial_replaced(self):
        info = rc.cpuinfo('processor\t: 0\n\nHardware\t: gs705a\nSerial\t\t: 1234abcd5678ef90\n')
        self.assertEqual(info['common']['Serial'], '<redacted>')

    def test_undeclared_outcome_rejected(self):
        saved = rc.EVALUATORS['P-GPU']
        rc.EVALUATORS['P-GPU'] = lambda s: ('maybe', {})
        try:
            with self.assertRaisesRegex(ValueError, 'undeclared'):
                rc.evaluate_predictions({'modules': [], 'cpu': {}, 'cpu_hint': {'outcome': 'incomplete'},
                                         'release_link': {'kernel_version_matches': []}})
        finally:
            rc.EVALUATORS['P-GPU'] = saved

    def test_every_declared_outcome_reachable_or_documented(self):
        """Each prediction declares an insufficient outcome and its evaluator handles an empty summary."""
        empty = {'cpu': {}, 'cpu_hint': rc.cpu_hint({}), 'release_link': {'kernel_version_matches': []}}
        for p in rc.load_predictions():
            with self.subTest(p=p['id']):
                outcome, _ = rc.EVALUATORS[p['id']](copy.deepcopy(empty))
                cls = next(o['class'] for o in p['outcomes'] if o['id'] == outcome)
                if p['id'] not in ('P-KCONFIG',):
                    self.assertEqual(cls, 'insufficient', f"{p['id']} returned {outcome} for an empty capture")


# ---------------------------------------------------------------- static safety

class ScriptSafetyTests(unittest.TestCase):
    def test_lint_clean(self):
        import v3_preflight
        self.assertEqual(v3_preflight.script_lint(SCRIPT.read_text()), [])

    def test_lint_catches_violations(self):
        import v3_preflight
        text = SCRIPT.read_text()
        for bad in ('cat /dev/mem > "$dest"', 'echo 1 > /sys/devices/system/cpu/cpu1/online', 'mount /dev/mmcblk1p1 /mnt',
                    'insmod x.ko', 'dd if=/dev/mmcblk0 of="$dest"', 'cat /sys/class/power_supply/battery/capacity'):
            with self.subTest(bad=bad):
                self.assertTrue(v3_preflight.script_lint(text.replace('\nexit 0\n', '\n' + bad + '\nexit 0\n')))

    def test_redirections_only_into_output(self):
        body = SCRIPT.read_text().split("dmesg|cmd|dmesg'\n", 1)[1]
        for m in re.finditer(r'(?<![0-9&<])>>?\s*("?[^\s;)|]+)', body):
            target = m.group(1).strip('"')
            self.assertTrue(target.startswith(('$OUT', '$dest', '$err', '/dev/null', '&2')), target)

    def test_probe_attributes_exclude_identifiers(self):
        text = SCRIPT.read_text()
        attrs = re.search(r'probe_attrs\(\) \{(.*?)\n\}', text, re.S).group(1)
        for word in ('serial', 'cid', 'csd', 'date', 'uevent'):
            self.assertNotRegex(attrs, rf"\b{word}\b")

    def test_versions_file_matches_script(self):
        versions = json.loads((ROOT / 'device/capture-versions.json').read_text())
        digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
        current = next(v for v in versions if v['sha256'] == digest)
        self.assertEqual(current['status'], 'current')
        self.assertEqual(current['essential'], rc.script_essential(SCRIPT.read_text()))
        self.assertEqual([v['version'] for v in versions], [1, 2, 3])

    def test_ids_fat_safe(self):
        ids = [x.split('|', 1)[0] for x in rc.script_allowlist(SCRIPT.read_text())]
        self.assertEqual(len({i.lower() for i in ids}), len(ids))
        for i in ids:
            self.assertRegex(i, r'^[a-z0-9_-]+$')


# ---------------------------------------------------------------- observation ledger

def repo_copy(dest):
    for rel in ['evidence', 'device']:
        shutil.copytree(ROOT / rel, dest / rel)
    return dest


KORIKI = json.loads((ROOT / 'evidence/firmware/koriki-v1.0.json').read_text())

OBS = {
    'id': 'OBS-001', 'date': '2026-12-01', 'plan_test': 'V3',
    'approval': {'approved_by': 'device owner', 'date': '2026-12-01', 'scope': 'V3 read-only capture on spare card'},
    'device': {'model': 'Anbernic RG35XX (original, ATM7039S)', 'board_revision': 'unknown'},
    'firmware': {'source': 'koriki-v1.0-release', 'image_sha256': KORIKI['sha256'], 'boot_kernel': 'uImage', 'modifications': ['capture.sh copied to roms/ports']},
    'media': {'description': 'spare 16 GB card', 'excluded_owner_card': False},
    'procedure': {'tool': 'device/capture.sh', 'tool_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(), 'launch': 'SimpleMenu GAMES list'},
    'capture': {'manifest_sha256': '', 'summary': 'evidence/observations/OBS-001.json', 'raw_location': 'owner archive'},
    'result': 'test record', 'limitations': 'test record',
}


class ObservationLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = repo_copy(self.tmp / 'repo')
        root = cf.build(self.tmp / 'root')
        capture, _ = run_capture(root, self.tmp / 'out')
        self.summary = rc.parse(capture)
        self.summary['capture']['fixture_root'] = 'none'  # simulate a live capture for ledger tests
        self.summary['capture']['warnings'] = []
        (self.root / 'evidence/observations/OBS-001.json').write_text(json.dumps(self.summary))
        self.obs = copy.deepcopy(OBS)
        self.obs['capture']['manifest_sha256'] = self.summary['capture']['manifest_sha256']

    def write(self, observations=None, findings_extra=None):
        (self.root / 'evidence/observations.json').write_text(json.dumps([self.obs] if observations is None else observations))
        findings = json.loads((ROOT / 'evidence/findings.json').read_text())
        if findings_extra:
            findings.append(findings_extra)
        (self.root / 'evidence/findings.json').write_text(json.dumps(findings))
        return vo.validate(self.root)

    def finding(self, **kw):
        f = {'id': 'CPU-900', 'subsystem': 'cpu', 'claim': 'x', 'confidence': 'verified', 'scope': 'runtime-observation',
             'evidence': [{'source': 'koriki-v1.0-release', 'observation': 'OBS-001', 'item': 'cpu-possible'}],
             'supporting_evidence': [], 'contradictory_evidence': [], 'validation': 'hardware-observation',
             'hardware_validated': True, 'observations': ['OBS-001'], 'limitations': 'x', 'related_findings': []}
        f.update(kw)
        return f

    def test_repository_ledgers_valid(self):
        self.assertEqual(vo.validate(ROOT), [])

    def test_valid_observation_and_finding(self):
        self.assertEqual(self.write(findings_extra=self.finding()), [])

    def test_owner_card_rejected(self):
        self.obs['media']['excluded_owner_card'] = True
        self.assertTrue(any('excluded_owner_card' in e for e in self.write()))

    def test_hardware_finding_needs_observation(self):
        f = self.finding()
        del f['observations']
        self.assertTrue(any("'observations' is a required" in e for e in self.write(findings_extra=f)))

    def test_unknown_observation_cited(self):
        f = self.finding(observations=['OBS-002'])
        f['evidence'][0]['observation'] = 'OBS-002'
        self.assertTrue(any('unknown observation' in e for e in self.write(findings_extra=f)))

    def test_missing_capture_item(self):
        f = self.finding()
        f['evidence'][0]['item'] = 'batocera-version'
        self.assertTrue(any('capture item' in e for e in self.write(findings_extra=f)))

    def test_uncatalogued_image(self):
        self.obs['firmware']['image_sha256'] = 'f' * 64
        self.assertTrue(any('not a catalogued' in e for e in self.write()))

    def test_wrong_boot_kernel(self):
        self.obs['firmware']['boot_kernel'] = 'zImage'
        self.assertTrue(any('boot_kernel' in e for e in self.write()))

    def test_manifest_mismatch(self):
        self.obs['capture']['manifest_sha256'] = '0' * 64
        self.assertTrue(any('manifest hash' in e for e in self.write()))

    def test_fixture_summary_rejected(self):
        self.summary['capture']['fixture_root'] = '/tmp/x'
        (self.root / 'evidence/observations/OBS-001.json').write_text(json.dumps(self.summary))
        self.assertTrue(any('fixture' in e for e in self.write()))

    def test_path_override_rejected(self):
        self.summary['capture']['path_override'] = '/tmp/bin'
        (self.root / 'evidence/observations/OBS-001.json').write_text(json.dumps(self.summary))
        self.assertTrue(any('PATH override' in e for e in self.write()))

    def test_quarantined_summary_rejected(self):
        self.summary['capture']['trust'] = 'quarantined'
        (self.root / 'evidence/observations/OBS-001.json').write_text(json.dumps(self.summary))
        self.assertTrue(any('not authenticated' in e for e in self.write()))

    def test_prediction_references_checked(self):
        p = self.root / 'evidence/predictions.json'
        preds = json.loads(p.read_text())
        preds[0]['findings'].append('CPU-999')
        preds[1]['capture_items'].append('dev-mem')
        preds[2]['outcomes'] = [o for o in preds[2]['outcomes'] if o['class'] != 'insufficient']
        p.write_text(json.dumps(preds))
        errors = self.write()
        self.assertTrue(any('unknown finding CPU-999' in e for e in errors))
        self.assertTrue(any('dev-mem not in allowlist' in e for e in errors))
        self.assertTrue(any('missing information' in e for e in errors))

    def test_script_change_requires_version_bump(self):
        p = self.root / 'device/capture.sh'
        p.write_text(p.read_text() + '\n# edit\n')
        self.assertTrue(any('capture-versions' in e for e in vo.validate(self.root)))

    def test_two_current_versions_rejected(self):
        p = self.root / 'device/capture-versions.json'
        v = json.loads(p.read_text())
        v[1]['status'] = 'current'
        p.write_text(json.dumps(v))
        self.assertTrue(any('exactly one' in e for e in vo.validate(self.root)))


if __name__ == '__main__':
    unittest.main()
