"""Re-derive PR #7's offline firmware findings (FW-018, FW-019, FW-020, STOR-002, UI-003) from the pinned image.

Skipped unless ATM_FIRMWARE_DIR holds the expanded koriki-v1.0.img (tools/acquire_firmware.py --expand).
Reads bytes only; nothing from the image is executed.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import research  # noqa: E402

KERNEL_STREAM = '5883f67328823b10e2e82576d5e043a3ff4c78b2095644250008bf640622fc5e'
TEXT_BASE = 0xc0008000


def image():
    folder = os.environ.get('ATM_FIRMWARE_DIR')
    p = Path(folder) / 'koriki-v1.0.img' if folder else None
    return p if p and p.is_file() else None


def fat_file(path):
    from firmware_catalogue import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    with open(image(), 'rb') as raw, PyFatBytesIOFS(Window(raw, 8388608, 3221225472)) as fs:
        with fs.openbin(path) as f:
            return f.read()


def rootfs_file(path):
    from firmware_catalogue import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    from dissect.extfs import ExtFS
    with open(image(), 'rb') as raw, PyFatBytesIOFS(Window(raw, 8388608, 3221225472)) as fs:
        with fs.openbin('/BOOT/BATOCERA') as f:
            node = ExtFS(f).get(path)
            return node.open().read(node.size)


@unittest.skipUnless(image(), 'needs ATM_FIRMWARE_DIR with the expanded koriki-v1.0.img')
class KernelFindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads((ROOT / 'evidence/firmware/kernel-payload.json').read_text())
        uimage = fat_file('/uImage')
        off = payload['gzip_streams'][0]['offset']
        cls.img = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(uimage[off:])
        assert hashlib.sha256(cls.img).hexdigest() == KERNEL_STREAM
        import kallsyms
        cls.syms = {s['name']: s['address'] for s in kallsyms.extract(cls.img)['symbols']}

    def test_fw018_empty_builtin_cmdline(self):
        va = self.syms['default_command_line']
        self.assertEqual(va, 0xc0a62d00)
        self.assertEqual(self.img[va - TEXT_BASE:va - TEXT_BASE + 1024], bytes(1024))

    def test_fw018_no_ikconfig_procfs_devicetree_only(self):
        self.assertNotIn(b'IKCFG_ST', self.img)
        self.assertFalse(any('ikconfig' in n for n in self.syms))
        self.assertIn('proc_device_tree_init', self.syms)
        self.assertIn('proc_device_tree_add_node', self.syms)
        for absent in ('of_fdt_raw_init', 'of_node_add', '__of_attach_node_sysfs'):
            self.assertNotIn(absent, self.syms)

    def test_fw018_log_buffer(self):
        va = self.syms['log_buf_len']
        self.assertEqual(struct.unpack_from('<I', self.img, va - TEXT_BASE)[0], 131072)

    def test_fw019_and_stor002_strings(self):
        for s in (b'Reserved memory %uMB', b'Memory: %luk/%luk available, %luk reserved, %luK highmem',
                  b'%s,sd0 as boot card,sd0 name tsd_card', b'force sd2(emmc) host emmc_boot_card'):
            self.assertIn(s, self.img)


@unittest.skipUnless(image(), 'needs ATM_FIRMWARE_DIR with the expanded koriki-v1.0.img')
class BootFileFindings(unittest.TestCase):
    def test_fw019_dtb_memory_description(self):
        t = research.fdt(fat_file('/KERNEL.DTB'))
        nodes = {n['path']: n['properties'] for n in t['nodes']}
        self.assertEqual((nodes['/']['#address-cells'], nodes['/']['#size-cells']), ([1], [1]))
        self.assertEqual(nodes['/memory']['reg'], [0, 0])
        self.assertNotIn('/reserved-memory', nodes)
        self.assertEqual(t['reservations'], [])
        self.assertEqual(nodes['/reserved/normal']['dma_heap_size'], [128])

    def test_fw020_and_ui003_scripts(self):
        checkfat = rootfs_file('/etc/init.d/S03checkfat').decode()
        self.assertIn('fsck.vfat -aw $DEVICE', checkfat)
        invoker = rootfs_file('/usr/bin/cmd_invoker.dge').decode()
        self.assertIn('eval "$LAUNCH_COMMAND" &', invoker)
        self.assertIn('LAUNCH_COMMAND="$3"', invoker)
        populate = rootfs_file('/etc/init.d/S08populate').decode()
        self.assertIn('mount /dev/mmcblk0p3 /userdata', populate)
        perf = rootfs_file('/etc/init.d/S03performance').decode()
        self.assertIn('/sys/devices/b0238000.mmc/mmc_host/mmc0/emmc_boot_card/block/mmcblk0', perf)


if __name__ == '__main__':
    unittest.main()


@unittest.skipUnless(image(), 'needs ATM_FIRMWARE_DIR with the expanded koriki-v1.0.img')
class RealDeviceTreeCapture(unittest.TestCase):
    """The real KERNEL.DTB, with U-Boot's reconstructed fixups (BOOT-017), laid out as a 3.10 procfs tree."""

    def test_capture_and_reference_comparison(self):
        import shutil
        import subprocess
        import tempfile
        sys.path.insert(0, str(ROOT / 'tests'))
        import capture_fixture as cf
        import runtime_capture as rc
        dtb = fat_file('/KERNEL.DTB')
        tree = rc.dt_from_fdt(dtb)
        ref = rc.koriki_handoff()
        tree['nodes']['/memory']['reg'] = cf.be32(*ref['memory_reg'])
        tree['nodes']['/chosen']['bootargs'] = ref['bootargs'][0].encode() + b'\0'
        tree['nodes']['/chosen']['linux,initrd-start'] = cf.be32(ref['initrd_start'])
        tree['nodes']['/chosen']['linux,initrd-end'] = cf.be32(ref['initrd_end'])
        files = {}
        for node, props in tree['nodes'].items():
            base = node.lstrip('/')
            files[base] = None
            files[(base + '/' if base else '') + 'name'] = (node.rsplit('/', 1)[-1].split('@')[0] or '').encode() + b'\0'
            for k, v in props.items():
                files[(base + '/' if base else '') + k] = v
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cf.build(d / 'root', cmdline=ref['bootargs'][0], dt='absent')
            cf.write_tree(d / 'root/proc/device-tree', files)
            (d / 'ref.dtb').write_bytes(dtb)
            subprocess.run(['sh', str(ROOT / 'device/capture.sh'), str(d / 'out')], check=True, capture_output=True,
                           env={'PATH': '/usr/bin:/bin', 'ATM_CAPTURE_ROOT': str(d / 'root')})
            cap = next((d / 'out').glob('atm-capture-*'))
            size = (cap / 'items/device-tree.tar').stat().st_size
            r = rc.parse(cap, reference_dtb=d / 'ref.dtb')
        self.assertEqual(r['capture']['errors'], [])
        self.assertLess(size, 2 * 1024 * 1024)
        cmp = r['summary']['device_tree_vs_reference']
        self.assertTrue(any(c['id'] == 'kernel.dtb' for c in cmp['reference_catalogued']))
        self.assertEqual(cmp['changed'], ['/chosen/bootargs', '/memory/reg'])
        self.assertEqual(cmp['added'], ['/chosen/linux,initrd-end', '/chosen/linux,initrd-start'])
        self.assertEqual(cmp['removed'], [])
        got = {p['id']: p['outcome'] for p in r['predictions']}
        self.assertEqual((got['P-RAM'], got['P-INITRD'], got['P-CMDLINE-SRC']), ('reference-256mib', 'as-reconstructed', 'chosen-used'))
        self.assertTrue(r['summary']['device_tree']['index_check']['consistent'])
