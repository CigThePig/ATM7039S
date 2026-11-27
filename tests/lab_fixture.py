"""An offline, simulated V3 world for the lab: synthetic firmware evidence, a simulated card
reader and card volumes, and the operator's V3 failure modes (drive letters that move or
vanish, an unreadable swap partition, extra cards, a card pulled mid-copy).

Nothing here is real firmware or a hardware measurement. The synthetic project root holds
its own small catalogue, so the lab's real checks run unchanged against invented bytes.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / 'fixtures'
sys.path.insert(0, str(ROOT / 'tools'))

from v3lab import disks, rootfs  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_research import dtb  # noqa: E402

BOOT_FILES = {'uImage': b'synthetic kernel\n' * 50, 'adb_uImage': b'synthetic adb kernel\n' * 40,
              'KERNEL.DTB': dtb({'model': b'synthetic\0', 'compatible': b'actions,gs705a\0'}), 'RAMDISK.IMG': b'synthetic ramdisk' * 20,
              'uEnv.txt': b'bootargs=earlyprintk clk_ignore_unused selinux=0 init=/init  \n',
              'batocera-boot.conf': b'# synthetic\nautoresize=true\nsharedevice=INTERNAL\n',
              '2100mAh-gpu.dtb': b'dtb 2100', '2600mAh-gpu.dtb': b'dtb 2600'}
COMPONENT_IDS = {'uImage': 'uImage', 'adb_uImage': 'adb_uImage', 'KERNEL.DTB': 'kernel.dtb', 'RAMDISK.IMG': 'ramdisk.img',
                 'uEnv.txt': 'uEnv.txt', 'batocera-boot.conf': 'batocera-boot.conf', '2100mAh-gpu.dtb': '2100mAh-gpu.dtb',
                 '2600mAh-gpu.dtb': '2600mAh-gpu.dtb'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def container(name):
    return gzip.open(FIX / f'lab-rootfs-{name}.ext4.gz').read()


def raw_head(tamper=False):
    """4 MiB 'card head': synthetic loader window, synthetic U-Boot and the SFVD marker."""
    b = bytearray(4 * 1024 * 1024)
    for i in range(0x200200, 0x201200):
        b[i] = (i * 7) & 0xff
    b[0x202a00:0x202a04] = b'SFVD'
    b[0x300000:0x300040] = struct.pack('>IIIIIIIBBBB32s', 0x27051956, 0, 0, 0x40, 0x5000000, 0x5000040, 0, 5, 2, 5, 0, b'synthetic')
    b[0x300040:0x300080] = b'U' * 64
    if tamper:
        b[0x200300] ^= 0xff
    return bytes(b)


def make_root(base):
    """A synthetic ATM7039S checkout: real code and capture script, invented firmware evidence."""
    base = Path(base)
    for d in ('evidence/firmware', 'device'):
        (base / d).mkdir(parents=True, exist_ok=True)
    for f in ('device/capture.sh', 'device/capture-versions.json', 'evidence/predictions.json'):
        shutil.copy(ROOT / f, base / f)
    for f in (ROOT / 'evidence/firmware').glob('*.json'):   # the parser's reference data; overridden below
        shutil.copy(f, base / 'evidence/firmware' / f.name)
    pristine = container('pristine')
    head = raw_head()
    comps = [dict(id='early-region.bin', location=dict(kind='disk-region', offset=0x200200, size=0x1000), sha256=sha(head[0x200200:0x201200])),
             dict(id='u-boot.uimage', location=dict(kind='disk-region', offset=0x300000, size=0x80), sha256=sha(head[0x300000:0x300080]))]
    for name, data in BOOT_FILES.items():
        comps.append(dict(id=COMPONENT_IDS[name], location=dict(kind='fat-file', partition=1, path='/' + name), sha256=sha(data), size=len(data)))
    cat = dict(format_version=1, source='koriki-v1.0-release', release='synthetic', size=0, sha256='0' * 64, sector_size=512,
               partitions=[dict(index=1, type='0xc', offset=disks.BOOT_OFFSET, size=disks.BOOT_SIZE)], components=comps)
    (base / 'evidence/firmware/koriki-v1.0.json').write_text(json.dumps(cat))
    rootcat = dict(format_version=1, source='koriki-v1.0-release', image_sha256='0' * 64, container_path='/BOOT/BATOCERA',
                   container_size=len(pristine), container_sha256=sha(pristine), components=[])
    (base / 'evidence/firmware/koriki-v1.0-rootfs.json').write_text(json.dumps(rootcat))
    real_policy = json.loads((ROOT / 'evidence/firmware/koriki-v1.0-first-boot.json').read_text(encoding='utf-8'))
    m = manifest(pristine)
    real_policy.update(container_sha256=sha(pristine), pristine_manifest=dict(real_policy['pristine_manifest'],
                       paths=len(m.entries), digest=m.digest()))
    (base / 'evidence/firmware/koriki-v1.0-first-boot.json').write_text(json.dumps(real_policy))
    acq = [dict(source='koriki-v1.0-release', filename='koriki-v1.0.img.gz', url='https://example.invalid/koriki.img.gz',
                size=10, sha256='1' * 64, compression='gzip', expanded_filename='koriki-v1.0.img', expanded_size=10, expanded_sha256='2' * 64)]
    (base / 'evidence/firmware/acquisitions.json').write_text(json.dumps(acq))
    return base


def manifest(data, name='m'):
    import tempfile
    from dissect.extfs import ExtFS
    with tempfile.TemporaryDirectory() as t:
        return rootfs.scan(ExtFS(io.BytesIO(data)), sha(data), Path(t) / f'{name}.sqlite')


class Card:
    """A simulated spare card: boot and SHARE volumes are plain folders on this computer."""

    def __init__(self, base, size=64_000_000_000, model='Generic SD Reader'):
        self.base = Path(base)
        self.size, self.model = size, model
        self.boot = self.base / 'boot-volume'
        self.share = self.base / 'share-volume'
        self.state = 'blank'
        self.boot_letter, self.share_letter = 'E', 'F'
        self.connected = True
        self.head = raw_head()

    def flash(self):
        if self.boot.exists():
            shutil.rmtree(self.boot)
        if self.share.exists():
            shutil.rmtree(self.share)
        self.boot.mkdir(parents=True)
        for name, data in BOOT_FILES.items():
            (self.boot / name).write_bytes(data)
        (self.boot / 'boot').mkdir()
        (self.boot / 'boot' / 'BATOCERA').write_bytes(container('pristine'))
        (self.boot / 'boot' / 'autoresize').write_bytes(b'')
        (self.boot / 'boot' / 'REBOOT').write_bytes(b'')
        (self.boot / 'boot' / 'batocera.board').write_bytes(b'rg35xx\n')
        self.state = 'fresh'

    def first_boot(self, variant='prepared'):
        (self.boot / 'boot' / 'BATOCERA').write_bytes(container(variant))
        (self.boot / 'boot' / 'autoresize').unlink(missing_ok=True)
        (self.boot / 'boot' / 'REBOOT').write_bytes(b'1\n')
        self.share.mkdir(parents=True, exist_ok=True)
        self.state = 'booted'

    def capture_boot(self, capture_dir=None, variant='postcapture'):
        (self.boot / 'boot' / 'BATOCERA').write_bytes(container(variant))
        if capture_dir:
            dest = self.share / 'roms' / 'ports' / Path(capture_dir).name
            shutil.copytree(capture_dir, dest)

    def disk(self):
        """This card as the Windows inventory would describe it."""
        parts = []
        if self.state == 'blank':
            parts = [dict(Number=1, Offset=1048576, Size=self.size - 1048576, MbrType=12, DriveLetter=self.boot_letter,
                          Label='', FileSystem='FAT32')]
        else:
            p3size = disks.SHARE_SIZE_PRISTINE if self.state == 'fresh' else self.size - disks.SHARE_OFFSET
            parts = [dict(Number=1, Offset=disks.BOOT_OFFSET, Size=disks.BOOT_SIZE, MbrType=12, DriveLetter=self.boot_letter or '',
                          Label='BATOCERA', FileSystem='FAT32'),
                     dict(Number=2, Offset=disks.SWAP_OFFSET, Size=disks.SWAP_SIZE, MbrType=130, DriveLetter='', Label=None, FileSystem=None),
                     dict(Number=3, Offset=disks.SHARE_OFFSET, Size=p3size, MbrType=12 if self.state == 'booted' else 131,
                          DriveLetter=(self.share_letter or '') if self.state == 'booted' else 'G',
                          Label='SHARE' if self.state == 'booted' else None, FileSystem='FAT32' if self.state == 'booted' else None)]
        return dict(Number=3, Model=self.model, BusType='USB', Size=self.size, IsBoot=False, IsSystem=False, IsOffline=False,
                    PartitionStyle='MBR', Signature=1234, Partitions=parts)


class World:
    """The computer: a system disk, optional extra disks, and the card reader."""

    def __init__(self, base):
        self.base = Path(base)
        self.card = Card(self.base / 'card')
        self.extra = []
        self.system = dict(Number=0, Model='NVMe SSD', BusType='NVMe', Size=1_000_000_000_000, IsBoot=True, IsSystem=True,
                           PartitionStyle='GPT', Partitions=[dict(Number=1, Offset=1048576, Size=999_000_000_000, MbrType=None,
                                                                  DriveLetter='C', Label='Windows', FileSystem='NTFS')])

    def mounts(self):
        m = {}
        if self.card.connected and self.card.boot_letter:
            m[self.card.boot_letter + ':\\'] = self.card.boot
        if self.card.connected and self.card.share_letter:
            m[self.card.share_letter + ':\\'] = self.card.share
        return m

    def probe(self, mount):
        target = self.mounts().get(mount)
        if mount == 'G:\\':
            return False, 'OSError: You need to format the disk in drive G: before you can use it.'
        if target is None:
            return (True, None) if mount == 'C:\\' else (False, 'FileNotFoundError: not mounted')
        return (True, None) if target.exists() else (False, 'OSError: not ready')

    def raw(self):
        disks_raw = [self.system] + self.extra + ([self.card.disk()] if self.card.connected else [])
        return disks_raw

    def inventory(self):
        found = disks.normalize_windows(self.raw(), probe=self.probe)
        m = self.mounts()
        for d in found:
            for p in d['partitions']:
                if p['mount'] in m:
                    p['mount'] = str(m[p['mount']])
        return found

    def raw_reader(self, card):
        if not self.card.connected:
            raise OSError('the card is not connected')
        return self.card.head
