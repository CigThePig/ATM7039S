"""tools/v3_preflight.py: synthetic checks everywhere, the pinned image when ATM_FIRMWARE_DIR has it."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import card_boot_read as raw
import v3_preflight as pf  # noqa: E402
import capture_fixture as cf  # noqa: E402

SCRIPT = ROOT / 'device/capture.sh'


def by_id(results):
    return {r['id']: r for r in results}


def image():
    folder = os.environ.get('ATM_FIRMWARE_DIR')
    p = Path(folder) / 'koriki-v1.0.img' if folder else None
    return p if p and p.is_file() else None


class ScriptChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_repository_script_passes(self):
        r = by_id(pf.check_script(SCRIPT))
        self.assertEqual({k: v['status'] for k, v in r.items()},
                         {'script-registered': 'PASS', 'script-allowlist': 'PASS', 'script-lint': 'PASS', 'script-format': 'PASS'})

    def test_modified_script_fails(self):
        p = self.tmp / 'capture.sh'
        p.write_text(SCRIPT.read_text() + '\n# local edit\n')
        self.assertEqual(by_id(pf.check_script(p))['script-registered']['status'], 'FAIL')

    def test_superseded_version_warns(self):
        v2 = next(v for v in json.loads((ROOT / 'device/capture-versions.json').read_text()) if v['version'] == 2)
        self.assertEqual(v2['status'], 'superseded')

    def test_crlf_script_flagged(self):
        """A CRLF copy has a different hash, so it is already unregistered; the format check explains why."""
        data = SCRIPT.read_bytes().replace(b'\n', b'\r\n')
        p = self.tmp / 'capture.sh'
        p.write_bytes(data)
        self.assertEqual(by_id(pf.check_script(p))['script-registered']['status'], 'FAIL')


class CardChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.share = self.tmp / 'SHARE'
        (self.share / 'roms/ports').mkdir(parents=True)

    def test_prepared_share(self):
        shutil.copy(SCRIPT, self.share / 'roms/ports/ATM7039S-capture.sh')
        r = by_id(pf.check_share_dir(self.share))
        self.assertEqual(r['card-script']['status'], 'PASS')
        self.assertEqual(r['card-earlier-captures']['status'], 'PASS')
        self.assertNotIn('card-script-name', r)

    def test_unsafe_name_extra_scripts_and_old_captures(self):
        shutil.copy(SCRIPT, self.share / 'roms/ports/ATM capture.sh')
        (self.share / 'roms/ports/other.sh').write_text('#!/bin/sh\n')
        (self.share / 'roms/ports/atm-capture-1970-1-0').mkdir()
        r = by_id(pf.check_share_dir(self.share))
        self.assertEqual(r['card-script']['status'], 'WARN')
        self.assertEqual(r['card-script-name']['status'], 'FAIL')
        self.assertEqual(r['card-earlier-captures']['status'], 'WARN')

    def test_macos_metadata(self):
        shutil.copy(SCRIPT, self.share / 'roms/ports/ATM7039S-capture.sh')
        (self.share / 'roms/ports/._ATM7039S-capture.sh').write_bytes(b'\0\x05\x16\x07')
        r = by_id(pf.check_share_dir(self.share))
        self.assertEqual(r['card-script']['status'], 'PASS')
        self.assertEqual(r['card-macos-files']['status'], 'WARN')
        boot = self.tmp / 'BOOT'
        boot.mkdir()
        (boot / '.Spotlight-V100').mkdir()
        (boot / '._uImage').write_bytes(b'x')
        self.assertEqual(by_id(pf.check_boot_dir(boot))['card-boot-extra']['status'], 'PASS')

    def test_missing_ports_folder(self):
        shutil.rmtree(self.share / 'roms')
        self.assertEqual(pf.check_share_dir(self.share)[0]['status'], 'FAIL')

    def test_wrong_script(self):
        (self.share / 'roms/ports/capture.sh').write_text('#!/bin/sh\necho hi\n')
        self.assertEqual(by_id(pf.check_share_dir(self.share))['card-script']['status'], 'FAIL')

    def test_boot_dir(self):
        boot = self.tmp / 'BOOT'
        (boot / 'boot').mkdir(parents=True)
        (boot / 'UENV.TXT').write_bytes(cf.UENV.encode('utf-8'))  # FAT is case-insensitive
        (boot / 'batocera-boot.conf').write_text('overclocking=extreme\n')
        (boot / 'boot/autoresize').write_text('')
        (boot / 'experimental.dtb').write_bytes(b'x')
        r = by_id(pf.check_boot_dir(boot))
        self.assertEqual(r['card-boot:uEnv.txt']['status'], 'PASS')
        self.assertEqual(r['card-boot:uImage']['status'], 'FAIL')
        self.assertEqual(r['card-boot:batocera-boot.conf']['status'], 'FAIL')
        self.assertEqual(r['card-overclocking']['status'], 'FAIL')
        self.assertEqual(r['card-boot-extra']['status'], 'WARN')
        self.assertEqual(r['card-first-boot']['status'], 'WARN')
        self.assertEqual(r['card-rootfs']['status'], 'FAIL')

    def test_card_rootfs(self):
        repo = self.tmp / 'repo'
        shutil.copytree(ROOT / 'evidence', repo / 'evidence')
        boot = self.tmp / 'BOOT2'
        (boot / 'BOOT').mkdir(parents=True)
        self.assertEqual(pf.check_card_rootfs(boot, repo)[0]['status'], 'FAIL')  # missing
        data = b'rootfs stand-in'
        (boot / 'BOOT/BATOCERA').write_bytes(data)
        self.assertIn('bytes, catalogued', pf.check_card_rootfs(boot, repo)[0]['detail'])
        cat = repo / 'evidence/firmware/koriki-v1.0-rootfs.json'
        c = json.loads(cat.read_text())
        c.update(container_size=len(data), container_sha256=hashlib.sha256(data).hexdigest())
        cat.write_text(json.dumps(c))
        self.assertEqual(pf.check_card_rootfs(boot, repo)[0]['status'], 'PASS')
        (boot / 'BOOT/BATOCERA').write_bytes(b'rootfs stand-iN')
        self.assertIn('DIFFERS', pf.check_card_rootfs(boot, repo)[0]['detail'])

    def test_boot_region_without_sfvd(self):
        dump = self.tmp / 'head.bin'
        dump.write_bytes(bytes(0x400000))
        r = by_id(pf.check_boot_region(dump))
        self.assertEqual(r['card-raw:sfvd']['status'], 'FAIL')
        self.assertIn('MISSING', r['card-raw:sfvd']['detail'])
        self.assertEqual(r['card-raw:early-region.bin']['status'], 'FAIL')

    def test_boot_region_too_short(self):
        dump = self.tmp / 'head.bin'
        dump.write_bytes(bytes(4096))
        r = by_id(pf.check_boot_region(dump))
        self.assertIn('too short', r['card-raw:u-boot.uimage']['detail'])
        self.assertNotIn('card-raw:sfvd', r)

    def test_applet_table(self):
        names = b'\x01[\x00[[\x00' + b'\x00'.join(n.encode() for n in sorted(pf.REQUIRED_APPLETS + ['awk', 'ls'] * 3)) + b'\x00\x00\x01'
        got = pf.busybox_applets(names)
        self.assertTrue(set(pf.REQUIRED_APPLETS) <= set(got))
        self.assertIsNone(pf.busybox_applets(b'nothing here'))


class RawCardChecks(unittest.TestCase):
    def test_windows_drive_resolution(self):
        info = dict(Number=7, Bus='USB', IsBoot=False, IsSystem=False,
                    Offset=raw.BOOT_OFFSET, PartitionSize=raw.BOOT_SIZE,
                    DiskSize=16000000000)
        with patch.object(raw.subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, json.dumps(info), '')
            self.assertEqual(raw.windows_disk_number('e:'), 7)
            self.assertIn("Get-Partition -DriveLetter 'E'", run.call_args.args[0][-1])
            for change in (dict(IsBoot=True), dict(IsSystem=True), dict(Bus='NVMe'),
                           dict(Offset=0), dict(Number=None), dict(PartitionSize=1)):
                run.return_value.stdout = json.dumps(info | change)
                with self.assertRaises(ValueError):
                    raw.windows_disk_number('E')
            run.reset_mock()
            with self.assertRaises(ValueError):
                raw.windows_disk_number('E; write')
            run.assert_not_called()

    def test_raw_bytes_no_dump(self):
        data = bytearray(raw.HEAD_SIZE)
        data[0x202a00:0x202a04] = b'SFVD'
        r = by_id(pf.check_boot_bytes(data))
        self.assertEqual(r['card-raw:sfvd']['status'], 'PASS')
        self.assertEqual(r['card-raw:early-region.bin']['status'], 'FAIL')

    def test_raw_read_failure_is_fail(self):
        from types import SimpleNamespace
        args = SimpleNamespace(script=SCRIPT, archive=None, image=None, boot_dir=None,
                               share_dir=None, boot_region=None, windows_boot_letter='E',
                               card_device=None)
        with patch.object(raw, 'read_windows_card', side_effect=OSError('access denied')):
            self.assertEqual(by_id(pf.run(args))['card-raw:read']['status'], 'FAIL')

    def test_json_utf8_and_ascii_console(self):
        import research
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'summary.json'
            research.save(path, {'text': '\u2714\u2718'})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['text'], '\u2714\u2718')
            out = Path(d) / 'preflight.json'
            r = subprocess.run([sys.executable, str(ROOT / 'tools/v3_preflight.py'),
                                '--json', str(out)], env=dict(os.environ, PYTHONIOENCODING='ascii'),
                               capture_output=True, text=True, encoding='ascii')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.is_file())

@unittest.skipUnless(image(), 'needs ATM_FIRMWARE_DIR with the expanded koriki-v1.0.img')
class PinnedImageChecks(unittest.TestCase):
    def test_pinned_image_passes(self):
        results = pf.check_image(image())
        bad = [r for r in results if r['status'] != 'PASS']
        self.assertEqual(bad, [])
        r = by_id(results)
        self.assertTrue(r['sfvd']['sfvd']['present'])
        self.assertIn('all present', r['busybox-applets']['detail'])

    def test_card_head_from_image_passes_and_tamper_fails(self):
        with tempfile.TemporaryDirectory() as d, open(image(), 'rb') as f:
            head = f.read(4 * 1024 * 1024)
            p = Path(d) / 'head.bin'
            p.write_bytes(head)
            self.assertTrue(all(x['status'] == 'PASS' for x in pf.check_boot_region(p)))
            tampered = bytearray(head)
            tampered[0x202a00:0x202a04] = b'\0\0\0\0'
            p.write_bytes(bytes(tampered))
            r = by_id(pf.check_boot_region(p))
            self.assertEqual(r['card-raw:sfvd']['status'], 'FAIL')
            self.assertEqual(r['card-raw:early-region.bin']['status'], 'FAIL')
            self.assertEqual(r['card-raw:u-boot.uimage']['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()
