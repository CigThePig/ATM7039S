import copy
import gzip
import hashlib
import io
import json
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
from test_research import dtb  # noqa: E402

SCRIPT = ROOT / 'device/capture.sh'
KORIKI_VERSION = json.loads((ROOT / 'evidence/firmware/kernel-payload.json').read_text())['gzip_streams'][0]['linux_version_strings'][0]['text']

DMESG = """[    0.000000] Booting Linux on physical CPU 0x0
[    0.000000] {version}
[    0.000000] Machine: gs705a, model: Actions ATM7039S
[    0.000000] Memory policy: ECC disabled, Data cache writealloc
[    0.000000] Kernel command line: earlyprintk clk_ignore_unused selinux=0 init=/init
[    0.000000] Memory: 238328K/262144K available (5412K kernel code)
[    0.010000] owl_smp_init_cpus(): ncores 4
[    0.050000] CPU1: Booted secondary processor
[    0.060000] SMP: Total of 2 processors activated (4800.00 BogoMIPS).
[    1.200000] mmc0: new high speed SDHC card at address 0007
[    2.000000] usb0: MAC 02:11:22:33:44:55
""".format(version=KORIKI_VERSION)

CPUINFO = """processor\t: 0
model name\t: ARMv7 Processor rev 1 (v7l)
CPU part\t: 0xc09

processor\t: 1
model name\t: ARMv7 Processor rev 1 (v7l)
CPU part\t: 0xc09

Hardware\t: gs705a
"""

IOMEM = """00000000-0fffffff : System RAM
  00008000-005fffff : Kernel code
b0120000-b0121fff : serial
"""


def fixture(base):
    """A synthetic RG35XX-like export tree; values are illustrative, not measurements."""
    files = {
        'proc/version': KORIKI_VERSION + '\n',
        'proc/cmdline': 'console=ttyS5 earlyprintk clk_ignore_unused selinux=0 init=/init boot_dev=sd2 androidboot.serialno=SECRET123\n',
        'proc/partitions': 'major minor  #blocks  name\n\n 179        0   15558144 mmcblk0\n 179        1    3145728 mmcblk0p1\n',
        'proc/cpuinfo': CPUINFO,
        'proc/meminfo': 'MemTotal:         238328 kB\nMemFree:          100000 kB\n',
        'proc/iomem': IOMEM,
        'proc/modules': 'pvrsrvkm 258640 3 - Live 0xbf000000 (O)\n',
        'proc/mounts': '/dev/mmcblk0p1 /boot vfat ro 0 0\n',
        'proc/pvr/version': 'Version 1.14.3625561\n',
        'sys/devices/system/cpu/kernel_max': '3\n',
        'sys/devices/system/cpu/possible': '0-1\n',
        'sys/devices/system/cpu/present': '0-1\n',
        'sys/devices/system/cpu/online': '0-1\n',
        'sys/devices/system/cpu/offline': '\n',
        'sys/class/graphics/fb0/virtual_size': '640,960\n',
        '.cmd/dmesg': DMESG,
        '.cmd/uname': 'Linux RG35XX 3.10.37 #75 SMP PREEMPT armv7l GNU/Linux\n',
        '.cmd/block-links': 'lrwxrwxrwx 1 root root 0 Jan 1 00:00 mmcblk0 -> ../devices/b0238000.mmc/mmc_host/mmc0/emmc_boot_card/block/mmcblk0\n',
    }
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    (base / 'proc/config.gz').write_bytes(gzip.compress(b'CONFIG_SMP=y\nCONFIG_NR_CPUS=4\nCONFIG_HOTPLUG_CPU=y\n'))
    (base / 'sys/firmware').mkdir(parents=True, exist_ok=True)
    (base / 'sys/firmware/fdt').write_bytes(dtb({'model': b'Actions ATM7039S\0'}))
    dt = base / 'proc/device-tree'
    (dt / 'cpus/cpu@0').mkdir(parents=True)
    (dt / 'cpus/cpu@1').mkdir(parents=True)
    (dt / 'memory').mkdir(parents=True)
    (dt / 'memory/reg').write_bytes(bytes.fromhex('0000000010000000'))
    (dt / 'chosen').mkdir()
    (dt / 'chosen/bootargs').write_bytes(b'earlyprintk\0')


def run_capture(root, out):
    proc = subprocess.run(['sh', str(SCRIPT), str(out)], env={'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(root)},
                          capture_output=True, text=True, check=True)
    return next(out.glob('atm-capture-*')), proc


class CaptureScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        fixture(self.tmp / 'root')
        self.capture, _ = run_capture(self.tmp / 'root', self.tmp / 'out')

    def test_end_to_end_fixture(self):
        result = rc.parse(self.capture)
        self.assertEqual(result['capture']['errors'], [])
        s = result['summary']
        self.assertEqual(s['cpu']['possible'], [0, 1])
        self.assertEqual(s['cpu']['scu_ncores'], 4)
        self.assertEqual(s['cpu']['smp_activated'], 2)
        self.assertEqual(s['cpu']['cpuinfo']['cpu_parts'], ['0xc09'])
        self.assertEqual(s['cpu_hint']['outcome'], 'software-cap')
        self.assertFalse(s['cmdline']['powersave'])
        self.assertEqual(s['memory']['iomem']['system_ram_bytes'], 0x10000000)
        self.assertEqual(s['kconfig']['selected']['CONFIG_NR_CPUS'], '4')
        self.assertEqual(s['device_tree_dir']['cpus'], ['cpu@0', 'cpu@1'])
        self.assertEqual(s['device_tree_dir']['memory_reg'], [0, 0x10000000])
        self.assertEqual(s['fdt']['model'], ['Actions ATM7039S'])
        self.assertEqual(s['modules'][0]['name'], 'pvrsrvkm')
        self.assertTrue(s['release_link']['kernel_version_matches'])
        self.assertIn('fixture', ' '.join(result['capture']['warnings']))

    def test_predictions_evaluated(self):
        p = {x['id']: x for x in rc.parse(self.capture)['predictions']}
        self.assertEqual(p['P-CPU']['outcome'], 'software-cap')
        self.assertEqual(p['P-CONSOLE']['outcome'], 'enabled-uart')
        self.assertEqual(p['P-BOOTDEV']['outcome'], 'boot-card-on-b0238000')
        self.assertEqual(p['P-BOOTDEV']['values']['boot_dev'], 'sd2')
        self.assertEqual(p['P-NAND']['outcome'], 'removable-only')
        self.assertEqual(p['P-RAM']['outcome'], 'ram-256mib-class')
        self.assertEqual(p['P-KERNEL']['outcome'], 'uimage-build')
        self.assertEqual(p['P-KCONFIG']['outcome'], 'nr-cpus-4')
        self.assertEqual(p['P-GPU']['outcome'], 'pvr-loaded')
        self.assertEqual(p['P-UENV']['outcome'], 'uenv-applied')
        declared = {x['id']: {o['id'] for o in x['outcomes']} for x in json.loads((ROOT / 'evidence/predictions.json').read_text())}
        self.assertEqual(set(p), set(declared))

    def test_summary_redacts_serial_and_mac(self):
        result = rc.parse(self.capture)
        text = json.dumps(result)
        self.assertNotIn('SECRET123', text)
        self.assertNotIn('02:11:22:33:44:55', text)
        self.assertTrue(result['summary']['privacy']['serialno_in_cmdline'])
        self.assertIn('SECRET123', (self.capture / 'items/cmdline.out').read_text())

    def test_missing_items_are_reported_not_fatal(self):
        files = {f['id']: f['status'] for f in rc.parse(self.capture)['capture']['files']}
        self.assertEqual(files['batocera-version'], 'missing')
        self.assertEqual(files['fdt'], 'ok')

    def test_tampered_item_detected(self):
        (self.capture / 'items/cmdline.out').write_text('powersave\n')
        errors = rc.parse(self.capture)['capture']['errors']
        self.assertTrue(any('cmdline' in e for e in errors))

    def test_manifest_edit_detected(self):
        m = self.capture / 'manifest.tsv'
        m.write_text(m.read_text().replace('cmdline', 'cmdline', 1) + '')
        text = m.read_text().splitlines()
        m.write_text('\n'.join(text[:-1]) + '\n')
        errors = rc.parse(self.capture)['capture']['errors']
        self.assertTrue(any('manifest' in e for e in errors))

    def test_allowlist_drift_detected(self):
        (self.capture / 'allowlist.txt').write_text('mem|file|/dev/mem\n')
        errors = rc.parse(self.capture)['capture']['errors']
        self.assertTrue(any('allowlist' in e for e in errors))

    def test_unknown_script_rejected(self):
        info = self.capture / 'capture-info.txt'
        info.write_text(re.sub('script_sha256=[0-9a-f]+', 'script_sha256=' + '0' * 64, info.read_text()))
        errors = rc.parse(self.capture)['capture']['errors']
        self.assertTrue(any('known device/capture.sh' in e for e in errors))

    def test_list_mode_reads_nothing(self):
        out = subprocess.run(['sh', str(SCRIPT), '--list'], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.splitlines(), rc.script_allowlist(SCRIPT.read_text()))


class ScriptSafetyTests(unittest.TestCase):
    def test_allowlist_targets_are_reads(self):
        for line in rc.script_allowlist(SCRIPT.read_text()):
            ident, kind, target = line.split('|')
            self.assertIn(kind, ('file', 'cmd', 'tree'))
            self.assertRegex(ident, r'^[a-z0-9_-]+$')
            self.assertNotRegex(target, r'/dev/|i2c|power_supply|debug|kmsg|cpuinfo_cur_freq|regulator|clk')
            if kind == 'cmd':
                self.assertIn(target, ('uname -a', 'ls -l /sys/block', 'ls -l /sys/bus/mmc/devices', 'dmesg'))

    def test_redirections_only_into_output(self):
        body = SCRIPT.read_text().split("dmesg'\n", 1)[1]
        for m in re.finditer(r'(?<![0-9&])>>?\s*("?[^\s;)]+)', body):
            target = m.group(1).strip('"')
            self.assertTrue(target.startswith(('$OUT', '$dest', '$err', '/dev/null', '&2')), target)

    def test_versions_file_matches_script(self):
        versions = json.loads((ROOT / 'device/capture-versions.json').read_text())
        digest = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
        self.assertIn(digest, [v['sha256'] for v in versions])


class ParserTests(unittest.TestCase):
    def test_cpulist(self):
        self.assertEqual(rc.cpulist('0-1,3\n'), [0, 1, 3])
        self.assertEqual(rc.cpulist('\n'), [])
        with self.assertRaises(ValueError):
            rc.cpulist('3-1')

    def test_iomem_zeroed_without_root(self):
        r = rc.iomem('00000000-00000000 : System RAM\n')
        self.assertTrue(r['addresses_zeroed'])

    def test_cpu_hint_outcomes(self):
        base = dict(possible=[0, 1, 2, 3], present=[0, 1, 2, 3], online=[0, 1])
        self.assertEqual(rc.cpu_hint(dict(base, scu_ncores=4))['outcome'], 'policy-or-startup')
        self.assertEqual(rc.cpu_hint(dict(base, scu_ncores=2))['outcome'], 'scu-two')
        self.assertEqual(rc.cpu_hint(dict(base, online=[0, 1, 2, 3], scu_ncores=4))['outcome'], 'four-online')
        self.assertEqual(rc.cpu_hint(dict(possible=[0])) ['outcome'], 'incomplete')

    def test_prediction_edge_outcomes(self):
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('console=ttyS2,115200')})[0], 'disabled-uart')
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('quiet')})[0], 'no-console')
        self.assertEqual(rc._p_console({'cmdline': rc.cmdline('console=ttyS0 console=tty1')})[0], 'multiple')
        self.assertEqual(rc._p_nand({'storage': {'partitions': 'major minor #blocks name\n\n 31 0 1024 nand0\n'}})[0], 'other-block-device')
        self.assertEqual(rc._p_ram({'memory': {'iomem': rc.iomem('00000000-1effffff : System RAM\n')}})[0], 'ram-512mib-class')
        self.assertEqual(rc._p_ram({'memory': {'iomem': rc.iomem('00000000-00000000 : System RAM\n')}})[0], 'not-evaluable')

    def test_undeclared_outcome_rejected(self):
        saved = rc.EVALUATORS['P-GPU']
        rc.EVALUATORS['P-GPU'] = lambda s: ('maybe', {})
        try:
            with self.assertRaisesRegex(ValueError, 'undeclared'):
                rc.evaluate_predictions({'modules': [], 'cpu': {}, 'cpu_hint': {'outcome': 'incomplete'},
                                         'release_link': {'kernel_version_matches': []}})
        finally:
            rc.EVALUATORS['P-GPU'] = saved

    def test_dmesg_without_timestamps(self):
        r = rc.dmesg('Linux version x\nSMP: Total of 2 processors activated.\n')
        self.assertEqual(r['smp_activated'], 2)
        self.assertFalse(r['begins_near_boot'])

    def test_bad_manifest_header(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'manifest.tsv'
            p.write_text('id\tsomething\n')
            with self.assertRaisesRegex(ValueError, 'header'):
                rc.read_manifest(p)


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
        fixture(self.tmp / 'root')
        capture, _ = run_capture(self.tmp / 'root', self.tmp / 'out')
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

    def test_prediction_references_checked(self):
        p = self.root / 'evidence/predictions.json'
        preds = json.loads(p.read_text())
        preds[0]['findings'].append('CPU-999')
        preds[1]['capture_items'].append('dev-mem')
        p.write_text(json.dumps(preds))
        errors = self.write()
        self.assertTrue(any('unknown finding CPU-999' in e for e in errors))
        self.assertTrue(any('dev-mem not in allowlist' in e for e in errors))

    def test_script_change_requires_version_bump(self):
        p = self.root / 'device/capture.sh'
        p.write_text(p.read_text() + '\n# edit\n')
        self.assertTrue(any('capture-versions' in e for e in vo.validate(self.root)))


if __name__ == '__main__':
    unittest.main()
