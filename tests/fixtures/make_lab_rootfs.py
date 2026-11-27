#!/usr/bin/env python3
"""Regenerate the synthetic Koriki-like ext4 fixtures used by the lab tests (Linux, root, e2fsprogs).

Nothing here comes from the real firmware: every file is invented. The trees mimic the
parts of the Koriki root filesystem that the first-boot policy talks about (/etc/dropbear
symlink, /run, /var/run -> ../run) plus a hard-link pair, a device node, a FIFO, an
executable and an extended attribute, so the semantic checker meets every record type.

    sudo python3 tests/fixtures/make_lab_rootfs.py

writes lab-rootfs-{pristine,prepared,postcapture,tampered,orphan}.ext4.gz next to this file.
"""
import gzip
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
FEATURES = '^metadata_csum,^metadata_csum_seed,^orphan_file,^uninit_bg,64bit,extents,flex_bg,dir_index,ext_attr,has_journal'
ENV = {**os.environ, 'E2FSPROGS_FAKE_TIME': '1700000000'}


def run(*cmd, **kw):
    subprocess.run(cmd, check=True, capture_output=True, env=ENV, **kw)


def debugfs(img, commands):
    with tempfile.NamedTemporaryFile('w', delete=False) as f:
        f.write('\n'.join(commands) + '\n')
    run('debugfs', '-w', '-f', f.name, str(img))
    os.unlink(f.name)


def tree(root):
    for d in ('etc/init.d', 'run', 'var', 'bin', 'usr/lib', 'dev', 'tmp', 'lost+found'):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / 'etc/inittab').write_text('si3::sysinit:/bin/mount -a\n')
    (root / 'etc/hostname').write_text('fixture\n')
    (root / 'etc/init.d/S50dropbear').write_text('#!/bin/sh\n# fixture stand-in for the pinned script\n')
    os.chmod(root / 'etc/init.d/S50dropbear', 0o755)
    os.symlink('/var/run/dropbear', root / 'etc/dropbear')
    os.symlink('../run', root / 'var/run')
    busybox = b'\x7fELF fixture\0' + b'\0'.join(x.encode() for x in ['[', '[[', 'cat', 'date', 'dirname', 'dmesg', 'find',
              'grep', 'head', 'id', 'mkdir', 'readlink', 'rm', 'sed', 'sh', 'sha256sum', 'sync', 'tar', 'tr', 'uname', 'wc',
              'ash', 'ls', 'mv', 'cp']) + b'\0\0'
    (root / 'bin/busybox').write_bytes(busybox)
    os.chmod(root / 'bin/busybox', 0o755)
    (root / 'usr/lib/libfixture.so.1').write_bytes(b'library ' * 3000)
    os.link(root / 'usr/lib/libfixture.so.1', root / 'usr/lib/libfixture-hardlink.so.1')
    os.mkfifo(root / 'tmp/fifo')
    os.mknod(root / 'dev/console', 0o600 | 0o020000, os.makedev(5, 1))


def make(name, mutate=None):
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / 'src'
        tree(src)
        img = Path(t) / 'fs.ext4'
        run('mkfs.ext4', '-q', '-F', '-b', '4096', '-N', '256', '-L', 'rootfs', '-U', '6e7a8b52-0b7e-4c1d-9f00-000000000001',
            '-E', 'root_owner=0:0,hash_seed=6e7a8b52-0b7e-4c1d-9f00-000000000002', '-O', FEATURES, '-d', str(src), str(img), '6M')
        debugfs(img, ['ea_set /usr/lib/libfixture.so.1 user.fixture value'])
        if mutate:
            mutate(img, Path(t))
        with open(img, 'rb') as f, gzip.GzipFile(HERE / f'lab-rootfs-{name}.ext4.gz', 'wb', mtime=0) as out:
            shutil.copyfileobj(f, out)


def first_boot(img, t):
    (t / 'utmp').write_bytes(b'\x02' + b'\0' * 383)
    debugfs(img, ['rm /etc/dropbear', 'mkdir /etc/dropbear', 'set_inode_field /etc/dropbear mode 040755',
                  'cd /run', 'mknod initctl p', 'set_inode_field /run/initctl mode 010600',
                  f'write {t / "utmp"} utmp', 'set_inode_field /run/utmp mode 0100644'])


def capture_boot(img, t):
    first_boot(img, t)
    (t / 'utmp2').write_bytes(b'\x02' + b'\x01' * 383)
    debugfs(img, ['rm /run/utmp', 'cd /run', f'write {t / "utmp2"} utmp', 'set_inode_field /run/utmp mode 0100644'])


def tampered(img, t):
    first_boot(img, t)
    (t / 'evil').write_text('#!/bin/sh\n')
    debugfs(img, ['cd /etc/init.d', f'write {t / "evil"} S99evil', 'set_inode_field /etc/init.d/S99evil mode 0100755',
                  'set_inode_field /etc/inittab mode 0100666', 'rm /usr/lib/libfixture-hardlink.so.1',
                  'ea_set /etc/hostname security.capability 01'])


def orphan(img, t):
    first_boot(img, t)
    debugfs(img, ['ssv last_orphan 12', 'ssv state 0'])


if __name__ == '__main__':
    make('pristine')
    make('prepared', first_boot)
    make('postcapture', capture_boot)
    make('tampered', tampered)
    make('orphan', orphan)
    print('written to', HERE)
