"""Run device/capture.sh under Koriki v1.0's own BusyBox through qemu-user.

Needs the pinned, expanded Koriki v1.0 image (ATM_FIRMWARE_DIR/koriki-v1.0.img,
from tools/acquire_firmware.py --expand) and qemu-arm-static or qemu-arm.
Nothing from the image is executed natively: BusyBox and its four libraries
are copied, by verified rootfs path, into a scratch sysroot and run under
qemu-user emulation as an unprivileged-equivalent child of the test.

The shell and every applet run the target code. Applets are reached through
small host wrapper scripts on PATH that call qemu again, because BusyBox ash
on this image is not built to run its applets internally.
"""
import hashlib
import os
from pathlib import Path
import shutil
import stat

IMAGE_SHA256 = 'd5bd300740884d80faee2fd3ae70d91f86e6a316610c56efc0e1f7545539d6ae'
# Files copied from the rootfs; each must match its hash in evidence/firmware/koriki-v1.0-rootfs.json.
LIBS = ['/lib/ld-linux-armhf.so.3', '/lib/libc.so.6', '/lib/libresolv.so.2', '/lib/libm.so.6']
CATALOGUE = Path(__file__).resolve().parents[1] / 'evidence/firmware/koriki-v1.0-rootfs.json'
APPLETS = ['sh', 'ash', 'cat', 'head', 'tail', 'wc', 'tr', 'cut', 'sed', 'grep', 'find', 'tar', 'readlink', 'sha256sum',
           'date', 'id', 'mkdir', 'rm', 'dirname', 'basename', 'sync', 'uname', 'dmesg', 'busybox', 'printf', 'sort',
           'od', 'ls', 'test', '[', 'pwd', 'echo', 'env', 'true', 'false', 'expr', 'touch']


def qemu():
    for name in ('qemu-arm-static', 'qemu-arm'):
        path = shutil.which(name)
        if path:
            return path
    return None


def image_path():
    folder = os.environ.get('ATM_FIRMWARE_DIR')
    if not folder:
        return None
    p = Path(folder) / 'koriki-v1.0.img'
    return p if p.is_file() else None


def prepare(scratch):
    """Build scratch/sysroot and scratch/bin. Returns (bin_dir, busybox_banner_sha) or raises."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from firmware_catalogue import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    from dissect.extfs import ExtFS
    img = image_path()
    q = qemu()
    if img is None or q is None:
        raise FileNotFoundError('Koriki v1.0 image or qemu-user not available')
    if img.stat().st_size != 4303355904:
        raise ValueError('unexpected Koriki image size')
    import json
    expected = {c['path']: c['sha256'] for c in json.loads(CATALOGUE.read_text())['components']}
    scratch = Path(scratch)
    sysroot = scratch / 'sysroot'
    (sysroot / 'lib').mkdir(parents=True)
    (sysroot / 'bin').mkdir()
    with img.open('rb') as raw, PyFatBytesIOFS(Window(raw, 8388608, 3221225472)) as fs:
        with fs.openbin('/BOOT/BATOCERA') as rootfs:
            ext = ExtFS(rootfs)
            for path in LIBS + ['/bin/busybox']:
                node = ext.get(path)
                if node.filetype != 0x8000 or not 0 < node.size < 4 * 1024 * 1024:
                    raise ValueError('unexpected rootfs entry ' + path)
                data = node.open().read(node.size)
                if hashlib.sha256(data).hexdigest() != expected.get(path):
                    raise ValueError('rootfs file does not match the catalogue: ' + path)
                dest = sysroot / path.lstrip('/')
                dest.write_bytes(data)
                dest.chmod(0o755)
    bindir = scratch / 'bin'
    bindir.mkdir()
    busybox = sysroot / 'bin/busybox'
    for applet in APPLETS:
        w = bindir / applet
        w.write_text(f'#!/bin/sh\nexec "{q}" -L "{sysroot}" -0 {applet} "{busybox}" "$@"\n')
        w.chmod(w.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    digest = hashlib.sha256(busybox.read_bytes()).hexdigest()
    return bindir, q, sysroot, digest


def shell_command(q, sysroot, script, *args):
    """argv that runs script under the target BusyBox ash."""
    return [q, '-L', str(sysroot), '-0', 'sh', str(Path(sysroot) / 'bin/busybox'), str(script), *map(str, args)]
