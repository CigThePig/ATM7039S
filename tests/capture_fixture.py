"""Synthetic RG35XX-like kernel export trees for exercising device/capture.sh.

Every value here is illustrative and chosen to resemble Koriki v1.0's
reconstructed boot (BOOT-017) or a deliberate variation of it. None of it is a
hardware measurement; captures made from these trees carry fixture_root and
are refused as evidence by tools/validate_observations.py.

build(base, **options) writes a tree under base. The defaults describe the
reference scenario: 256 MiB handed over, two CPU nodes, SCU reporting four
cores, boot card on b0238000, TF2 empty, device tree exported as a procfs
directory (as on the 3.10 kernel), no /sys/firmware/fdt, no /proc/config.gz.
"""
import gzip
import json
import os
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
KORIKI_VERSION = json.loads((ROOT / 'evidence/firmware/kernel-payload.json').read_text())['gzip_streams'][0]['linux_version_strings'][0]['text']
BOOTARGS = ('console=ttyS3 earlyprintk clk_ignore_unused selinux=0 init=/init   androidboot.dvfslevel=0x705x '
            'androidboot.bootdev=sd boot_dev=sd0')
SERIAL = 'SECRET123ABC'
# Koriki v1.0 /uEnv.txt (121 bytes, catalogued in koriki-v1.0.json).
UENV = '# Ramdisk boot (ramdisk.img)\nuenvcmd=setenv os_type linux;\nbootargs=earlyprintk clk_ignore_unused selinux=0 init=/init  \n'


def be32(*values):
    return b''.join(struct.pack('>I', v) for v in values)


def cstr(*values):
    return b''.join(v.encode() + b'\0' for v in values)


def device_tree(memory_nodes=None, address_cells=1, size_cells=1, bootargs=BOOTARGS, initrd=(0x2000000, 0x23a43b1),
                cpus=2, extra=None):
    """Return {path: bytes or None (directory)} for a procfs-style device tree."""
    if memory_nodes is None:
        memory_nodes = {'memory': [(0, 0x10000000)]}

    def cells(value, n):
        return b''.join(struct.pack('>I', (value >> (32 * (n - 1 - i))) & 0xffffffff) for i in range(n))

    nodes = {
        '': None,
        '#address-cells': be32(address_cells),
        '#size-cells': be32(size_cells),
        'compatible': cstr('actions,gs705a', 'actions,atm7059a'),
        'model': cstr('RG35XX ATM7039 based handheld gaming console (V6C)'),
        'name': b'\0',
        'chosen': None,
        'chosen/name': cstr('chosen'),
        'cpus': None,
        'cpus/#address-cells': be32(1),
        'cpus/#size-cells': be32(0),
        'reserved': None,
        'reserved/normal': None,
        'reserved/normal/fb_heap_size': be32(8),
        'reserved/normal/dma_heap_size': be32(128),
        'reserved/tiny': None,
        'reserved/tiny/fb_heap_size': be32(9),
        'reserved/tiny/dma_heap_size': be32(32),
        'aliases': None,
        'aliases/mmc0': cstr('/mmc@b0230000'),
        'aliases/mmc2': cstr('/mmc@b0238000'),
        'mmc@b0230000': None,
        'mmc@b0230000/status': cstr('okay'),
        'mmc@b0230000/card_type': cstr('memory'),
        'mmc@b0238000': None,
        'mmc@b0238000/status': cstr('okay'),
        'mmc@b0238000/card_type': cstr('memory'),
        'serial@b0126000': None,
        'serial@b0126000/status': cstr('okay'),
    }
    if bootargs is not None:
        nodes['chosen/bootargs'] = bootargs.encode() + b'\0'
    if initrd:
        nodes['chosen/linux,initrd-start'] = be32(initrd[0])
        nodes['chosen/linux,initrd-end'] = be32(initrd[1])
    for i in range(cpus):
        nodes[f'cpus/cpu@{i}'] = None
        nodes[f'cpus/cpu@{i}/device_type'] = cstr('cpu')
        nodes[f'cpus/cpu@{i}/compatible'] = cstr('arm,cortex-a9')
        nodes[f'cpus/cpu@{i}/reg'] = be32(i)
    for name, banks in memory_nodes.items():
        nodes[name] = None
        nodes[name + '/device_type'] = cstr('memory')
        nodes[name + '/reg'] = b''.join(cells(a, address_cells) + cells(s, size_cells) for a, s in banks)
    nodes.update(extra or {})
    return nodes


def write_tree(base, tree):
    for rel, value in sorted(tree.items()):
        p = base / rel if rel else base
        if value is None:
            p.mkdir(parents=True, exist_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(value)


DMESG_LINES = [
    '[    0.000000] Booting Linux on physical CPU 0x0',
    '[    0.000000] {version}',
    '[    0.000000] Machine: gs705a, model: RG35XX ATM7039 based handheld gaming console (V6C)',
    '[    0.000000] Reserved memory 42MB',
    '[    0.000000] Memory policy: ECC disabled, Data cache writealloc',
    '[    0.000000] Kernel command line: {cmdline}',
    '[    0.000000] Memory: {mem_avail}k/{mem_total}k available, {mem_reserved}k reserved, 0K highmem',
    '[    0.010000] owl_smp_init_cpus(): ncores {ncores}',
    '[    0.050000] CPU1: Booted secondary processor',
    '[    0.060000] Brought up {smp} CPUs',
    '[    0.060000] SMP: Total of {smp} processors activated (4800.00 BogoMIPS).',
    '[    0.300000] Freeing initrd memory: 3728K',
    '[    1.200000] acts_mmc_probe,sd0 as boot card,sd0 name tsd_card',
    '[    1.300000] mmc0: new high speed SDHC card at address 0007',
    '[    2.000000] usb0: HOST MAC 02:11:22:33:44:55',
]


def dmesg_text(cmdline, ncores=4, smp=2, mem_total=262144, mem_avail=211000, extra=()):
    lines = [x.format(version=KORIKI_VERSION, cmdline=cmdline, ncores=ncores, smp=smp, mem_total=mem_total,
                      mem_avail=mem_avail, mem_reserved=mem_total - mem_avail) for x in DMESG_LINES]
    if ncores is None:
        lines = [x for x in lines if 'ncores' not in x]
    return '\n'.join(list(lines) + list(extra)) + '\n'


def storage(base, scenario='boot-card'):
    """sysfs block/mmc layout. Scenarios: boot-card, second-card, emmc, unknown-type, nand, no-links, mismatch."""
    dev = base / 'sys/devices'
    block, bus, hosts = base / 'sys/block', base / 'sys/bus/mmc/devices', base / 'sys/class/mmc_host'
    for d in (block, bus, hosts):
        d.mkdir(parents=True, exist_ok=True)
    parts = ['major minor  #blocks  name', '']

    def card(ctrl, host, cardname, disk, ctype, sectors, major_minor):
        hostdir = dev / f'{ctrl}.mmc/mmc_host/{host}'
        carddir = hostdir / cardname
        diskdir = carddir / 'block' / disk
        diskdir.mkdir(parents=True, exist_ok=True)
        for k, v in dict(removable='0', ro='0', size=str(sectors), dev=major_minor, ext_range='8').items():
            (diskdir / k).write_text(v + '\n')
        if ctype is not None:
            (carddir / 'type').write_text(ctype + '\n')
        (carddir / 'name').write_text('SD16G\n')
        (carddir / 'manfid').write_text('0x000003\n')
        (carddir / 'oemid').write_text('0x5344\n')
        (carddir / 'serial').write_text('0x' + SERIAL + '\n')  # must never be captured
        (carddir / 'cid').write_text('035344534431364780' + SERIAL + '\n')
        os.symlink('../../../' + cardname, diskdir / 'device')
        if scenario != 'no-links':
            os.symlink(f'../devices/{ctrl}.mmc/mmc_host/{host}/{cardname}/block/{disk}', block / disk)
            os.symlink(f'../../../devices/{ctrl}.mmc/mmc_host/{host}/{cardname}', bus / cardname)
        else:
            (block / disk).mkdir()
            (block / disk / 'removable').write_text('0\n')
        if not (hosts / host).exists() and scenario != 'no-links':
            os.symlink(f'../../devices/{ctrl}.mmc/mmc_host/{host}', hosts / host)
        major, minor = major_minor.split(':')
        parts.append(f' {major:>4} {minor:>8} {sectors // 2:>10} {disk}')
        parts.append(f' {major:>4} {int(minor) + 1:>8} {3145728:>10} {disk}p1')

    boot_ctrl = 'b0230000' if scenario == 'mismatch' else 'b0238000'
    card(boot_ctrl, 'mmc0', 'emmc_boot_card', 'mmcblk0', None if scenario == 'unknown-type' else 'SD', 31116288, '179:0')
    if scenario == 'second-card':
        card('b0230000', 'mmc1', 'sd_card', 'mmcblk1', 'SD', 62333952, '179:8')
    if scenario == 'emmc':
        card('b0230000', 'mmc1', 'sd_card', 'mmcblk1', 'MMC', 15269888, '179:8')
    for i in range(2):
        d = dev / f'virtual/block/loop{i}'
        d.mkdir(parents=True, exist_ok=True)
        (d / 'removable').write_text('0\n')
        (d / 'size').write_text('0\n')
        os.symlink(f'../devices/virtual/block/loop{i}', block / f'loop{i}')
        parts.append(f'    7 {i:>8} {0:>10} loop{i}')
    if scenario == 'nand':
        d = dev / 'virtual/block/nand0'
        d.mkdir(parents=True)
        (d / 'removable').write_text('0\n')
        os.symlink('../devices/virtual/block/nand0', block / 'nand0')
        parts.append(f'   93 {0:>8} {4194304:>10} nand0')
    (base / 'proc').mkdir(parents=True, exist_ok=True)
    (base / 'proc/partitions').write_text('\n'.join(parts) + '\n')


def build(base, *, cmdline=None, dt='dir', dt_tree=None, cpus=('0-1', '0-1', '0-1', ''), ncores=4, smp=2,
          iomem=None, meminfo_total=211000, mem_total=262144, storage_scenario='boot-card', kconfig=None,
          fdt=None, missing=(), dmesg_extra=(), boot_conf_extra='', kernel_version=KORIKI_VERSION):
    """Write a fixture tree. dt: dir | symlink | absolute-link | escape | absent."""
    base = Path(base)
    if cmdline is None:
        cmdline = BOOTARGS + ' androidboot.serialno=' + SERIAL
    if iomem is None:
        iomem = ('00000000-0fffffff : System RAM\n  00008000-0074ffff : Kernel code\n  00790000-0087ffff : Kernel data\n'
                 'b0120000-b0121fff : serial\nb0126000-b0127fff : serial\n')
    files = {
        'proc/version': kernel_version + '\n',
        'proc/cmdline': cmdline + '\n',
        'proc/uptime': '42.10 60.00\n',
        'proc/cpuinfo': ('processor\t: 0\nmodel name\t: ARMv7 Processor rev 1 (v7l)\nCPU part\t: 0xc09\n\n'
                         'processor\t: 1\nmodel name\t: ARMv7 Processor rev 1 (v7l)\nCPU part\t: 0xc09\n\n'
                         'Hardware\t: gs705a\nRevision\t: 0000\nSerial\t\t: 1234abcd5678ef90\n'),
        'proc/meminfo': f'MemTotal:         {meminfo_total} kB\nMemFree:          100000 kB\nCmaTotal:        0 kB\n',
        'proc/iomem': iomem,
        'proc/interrupts': '           CPU0       CPU1\n 29:        100          0       GIC  serial\n',
        'proc/modules': 'pvrsrvkm 258640 3 - Live 0xbf000000 (O)\n',
        'proc/mounts': ('/dev/mmcblk0p1 /boot vfat rw,relatime 0 0\n/dev/loop0 / squashfs ro 0 0\n'
                        '/dev/mmcblk0p3 /userdata vfat rw,relatime 0 0\n'),
        'proc/fb': '0 owl_fb\n',
        'proc/pvr/version': 'Version 1.14.3625561\n',
        'sys/devices/system/cpu/kernel_max': '3\n',
        'sys/devices/system/cpu/possible': cpus[0] + '\n',
        'sys/devices/system/cpu/present': cpus[1] + '\n',
        'sys/devices/system/cpu/online': cpus[2] + '\n',
        'sys/devices/system/cpu/offline': cpus[3] + '\n',
        'sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies': '240000 504000 720000 1008000\n',
        'sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq': '240000\n',
        'sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq': '1488000\n',
        'sys/devices/system/cpu/cpu0/cpufreq/scaling_governor': 'performance\n',
        'sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq': '1008000\n',
        'sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq': '240000\n',
        'sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq': '1008000\n',
        'sys/devices/system/cpu/cpu0/cpufreq/scaling_driver': 'owl-cpufreq\n',
        'sys/class/graphics/fb0/name': 'owl_fb\n',
        'sys/class/graphics/fb0/mode': 'U:640x480p-60\n',
        'sys/class/graphics/fb0/virtual_size': '640,960\n',
        'sys/class/graphics/fb0/bits_per_pixel': '32\n',
        'sys/class/graphics/fb0/stride': '2560\n',
        'etc/os-release': 'NAME=Buildroot\nVERSION=2023.02\n',
        'usr/share/simplemenu/Koriki/version.txt': '1.2\n',
        'boot/uEnv.txt': UENV,
        'boot/batocera-boot.conf': 'sharedevice=INTERNAL\nautoresize=true\n' + boot_conf_extra,
        '.cmd/uname': 'Linux RG35XX 3.10.37 #75 SMP PREEMPT Mon Jul 17 20:23:47 UTC 2023 armv7l GNU/Linux\n',
        '.cmd/dmesg': dmesg_text(cmdline, ncores=ncores, smp=smp, mem_total=mem_total, extra=dmesg_extra),
    }
    for rel, content in files.items():
        if rel in missing:
            continue
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    if kconfig is not None:
        (base / 'proc/config.gz').write_bytes(gzip.compress(kconfig.encode()))
    if fdt is not None:
        (base / 'sys/firmware').mkdir(parents=True, exist_ok=True)
        (base / 'sys/firmware/fdt').write_bytes(fdt)
    storage(base, storage_scenario)
    # U-Boot writes the same string into /chosen/bootargs that the kernel then reports.
    tree = dt_tree if dt_tree is not None else device_tree(bootargs=cmdline)
    if dt == 'dir':
        write_tree(base / 'proc/device-tree', tree)
    elif dt in ('symlink', 'absolute-link'):
        write_tree(base / 'sys/firmware/devicetree/base', tree)
        target = '../sys/firmware/devicetree/base' if dt == 'symlink' else str(base / 'sys/firmware/devicetree/base')
        os.symlink(target, base / 'proc/device-tree')
    elif dt == 'escape':
        write_tree(base / 'elsewhere', tree)
        (base / 'elsewhere/secret').write_text('outside the device tree\n')
        os.symlink('../elsewhere', base / 'proc/device-tree')
    return base
