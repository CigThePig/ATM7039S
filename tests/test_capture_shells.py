"""Run the real device/capture.sh under every available POSIX shell and parse the result.

dash and bash --posix run everywhere. A host BusyBox runs when installed. Koriki v1.0's own
BusyBox 1.36.1 ash and applets run under qemu-user when ATM_FIRMWARE_DIR holds the pinned
image (tests/target_busybox.py); that is the closest offline stand-in for the device.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import runtime_capture as rc  # noqa: E402
import capture_fixture as cf  # noqa: E402
import target_busybox as tb  # noqa: E402
from test_runtime_capture import outcomes, statuses  # noqa: E402

SCRIPT = ROOT / 'device/capture.sh'
EXPECTED = {'P-CONSOLE': 'ttys3', 'P-BOOTARGS': 'match', 'P-CMDLINE-SRC': 'chosen-used', 'P-RAM': 'reference-256mib',
            'P-INITRD': 'as-reconstructed', 'P-BOOTDEV': 'boot-card-on-b0238000', 'P-NAND': 'boot-card-only',
            'P-CPU': 'software-cap', 'P-DRAM-LOG': 'requires-early-serial'}


class ShellPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def check(self, argv, env, name):
        root = cf.build(self.tmp / (name + '-root'), dt='symlink')
        out = self.tmp / (name + '-out')
        e = dict(env, ATM_CAPTURE_ROOT=str(root))
        proc = subprocess.run([*argv, str(SCRIPT), str(out)], env=e, capture_output=True, text=True, timeout=900)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, '', 'the script must not emit shell warnings')
        result = rc.parse(next(out.glob('atm-capture-*')))
        self.assertEqual(result['capture']['errors'], [])
        self.assertEqual(result['capture']['state'], 'authenticated-complete')
        got = outcomes(result)
        self.assertEqual({k: got[k] for k in EXPECTED}, EXPECTED)
        self.assertEqual(statuses(result)['device-tree'], 'ok')
        return result

    def test_dash(self):
        if not shutil.which('dash'):
            self.skipTest('dash not installed')
        self.check(['dash'], {'PATH': '/usr/bin:/bin'}, 'dash')

    def test_bash_posix(self):
        if not shutil.which('bash'):
            self.skipTest('bash not installed')
        self.check(['bash', '--posix'], {'PATH': '/usr/bin:/bin'}, 'bash')

    def test_host_busybox(self):
        bb = shutil.which('busybox')
        if not bb:
            self.skipTest('host busybox not installed')
        bindir = self.tmp / 'bb'
        bindir.mkdir()
        listed = subprocess.run([bb, '--list'], capture_output=True, text=True).stdout.split()
        for applet in listed:
            os.symlink(bb, bindir / applet)
        r = self.check([bb, 'sh'], {'PATH': str(bindir), 'ATM_CAPTURE_PATH': str(bindir)}, 'busybox')
        self.assertTrue(r['capture']['environment']['busybox'].startswith('BusyBox'))

    def test_koriki_busybox_under_qemu(self):
        try:
            bindir, q, sysroot, digest = tb.prepare(self.tmp / 'target')
        except (FileNotFoundError, ImportError) as e:
            self.skipTest(f'needs ATM_FIRMWARE_DIR with koriki-v1.0.img and qemu-user: {e}')
        argv = tb.shell_command(q, sysroot, 'X')[:-1]
        r = self.check(argv, {'PATH': str(bindir), 'ATM_CAPTURE_PATH': str(bindir)}, 'koriki')
        self.assertEqual(r['capture']['environment']['busybox'], 'BusyBox v1.36.1 (2023-10-18 02:27:37 UTC) multi-call binary.')
        self.assertEqual(r['capture']['environment']['head_c'], 'yes')


class ShellcheckTests(unittest.TestCase):
    def test_shellcheck_clean(self):
        sc = shutil.which('shellcheck')
        if not sc:
            self.skipTest('shellcheck not installed (pip install shellcheck-py)')
        for dialect in ('sh', 'dash'):
            proc = subprocess.run([sc, '-s', dialect, str(SCRIPT)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_syntax_under_every_shell(self):
        for shell in ('sh', 'dash', 'bash', 'busybox'):
            path = shutil.which(shell)
            if not path:
                continue
            argv = [path, 'sh', '-n'] if shell == 'busybox' else [path, '-n']
            with self.subTest(shell=shell):
                subprocess.run([*argv, str(SCRIPT)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
