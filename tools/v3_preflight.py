#!/usr/bin/env python3
"""Offline preflight for hardware test V3. Verification only: it never writes to an image or a card.

Run it on a computer before (and, optionally, after) the physical session:

    python tools/v3_preflight.py                          # the capture package only
    python tools/v3_preflight.py --image INPUTS/koriki-v1.0.img [--archive INPUTS/koriki-v1.0.img.gz]
    python tools/v3_preflight.py --boot-dir /media/BOOT --share-dir /media/SHARE   # the prepared card
    python tools/v3_preflight.py --boot-region card-head.bin   # existing raw read of the card's first 4 MiB

Checks, each reported as PASS, FAIL, WARN or SKIP:

* device/capture.sh is the registered current version, its allowlist matches, and a static
  safety lint finds no prohibited operation;
* the archive and the expanded image match their pinned size and SHA-256;
* the loader window, U-Boot, kernel, DTBs, RAM disk, uEnv.txt and batocera-boot.conf inside the
  image equal the catalogued components (no experimental bootloader, kernel, DTB or overclock);
* the SFVD marker is present (otherwise app.bin rewrites bootloader.ini on boot: a material
  baseline risk, reported and never repaired);
* the BusyBox in the image provides every applet the capture script uses;
* on a mounted, prepared card: the boot files are unchanged, overclocking is unset, exactly one
  registered capture script sits in roms/ports under a safe name, and no earlier capture is left;
* on a raw read of the card's first 4 MiB: the loader window and U-Boot are byte-identical to
  the catalogue and the SFVD marker is still present.

Exit status 0 means no FAIL. WARN items need a human decision before the session.
"""
import argparse
import hashlib
import os
import json
from pathlib import Path
import re
import shutil
import sys
import card_boot_read

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_capture as rc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'koriki-v1.0-release'
# Applets and external programs device/capture.sh calls. Shell builtins (printf, [, pwd, cd,
# command, read, echo) are part of ash itself.
REQUIRED_APPLETS = ['sh', 'cat', 'head', 'wc', 'tr', 'sed', 'grep', 'find', 'tar', 'readlink', 'sha256sum', 'date',
                    'id', 'mkdir', 'rm', 'dirname', 'sync', 'uname', 'dmesg']
# Boot-partition files a prepared card must keep byte for byte (FAT names are case-insensitive).
BOOT_FILES = {'uImage': 'uImage', 'adb_uImage': 'adb_uImage', 'KERNEL.DTB': 'kernel.dtb', 'RAMDISK.IMG': 'ramdisk.img',
              'uEnv.txt': 'uEnv.txt', 'batocera-boot.conf': 'batocera-boot.conf', '2100mAh-gpu.dtb': '2100mAh-gpu.dtb',
              '2600mAh-gpu.dtb': '2600mAh-gpu.dtb'}
SAFE_SCRIPT_NAME = re.compile(r'[A-Za-z0-9._-]+\.sh')
# Files and folders computers add to FAT cards on their own (Windows, macOS).
OS_METADATA = {'system volume information', '.spotlight-v100', '.fseventsd', '.trashes', '.ds_store', '.temporaryitems'}


def os_metadata(name):
    return name.lower() in OS_METADATA or name.startswith('._')

# Static lint: none of these may appear in the script outside comments.
PROHIBITED = [
    (r'/dev/(?!null\b)', 'opens a device node other than /dev/null'),
    (r'\b(?:devmem|i2c(?:detect|get|set|dump|transfer)|insmod|modprobe|rmmod|mount|umount|swapon|swapoff|'
     r'hwclock|fsck|mkfs|fdisk|dd|hdparm|reboot|poweroff|halt|chmod|chown|setserial|cpufreq-set)\b', 'prohibited command'),
    (r'>\s*"?/(?:sys|proc)/', 'writes to /sys or /proc'),
    (r'power_supply|cpuinfo_cur_freq|/sys/kernel/debug|/proc/kmsg|regulator', 'reads an excluded interface'),
    (r'\becho\s+[0-9a-z]+\s*>\s*\S*(?:online|scaling|brightness|governor)', 'changes runtime state'),
]


def result(rid, status, detail, **extra):
    return dict(id=rid, status=status, detail=detail, **extra)


def code_lines(text):
    """Script lines with comments and the here-document README removed."""
    out, in_doc = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if in_doc:
            if line.strip() == 'EOF':
                in_doc = False
            continue
        if "<<'EOF'" in line:
            in_doc = True
        stripped = line.split('#', 1)[0] if not line.lstrip().startswith('#!') else ''
        out.append((n, stripped))
    return out


def script_lint(text):
    issues = []
    body = text.split("dmesg|cmd|dmesg'", 1)[-1]
    offset = text[:len(text) - len(body)].count('\n')
    for n, line in code_lines(body):
        for pattern, why in PROHIBITED:
            if re.search(pattern, line):
                issues.append(f'line {n + offset}: {why}: {line.strip()}')
    for entry in rc.script_allowlist(text):
        ident, kind, target = entry.split('|')
        if kind not in ('file', 'cmd', 'probe', 'tree', 'treeindex'):
            issues.append(f'allowlist {ident}: unknown kind {kind}')
        if re.search(r'/dev/|i2c|power_supply|debug|kmsg|cpuinfo_cur_freq|regulator|/clk', target):
            issues.append(f'allowlist {ident}: excluded target {target}')
        if kind == 'cmd' and target not in ('uname -a', 'dmesg'):
            issues.append(f'allowlist {ident}: command {target!r} is not a reviewed fixed command')
        if not rc.SAFE_ID.fullmatch(ident) or ident != ident.lower():
            issues.append(f'allowlist {ident}: id is not a lower-case FAT-safe name')
    ids = [e.split('|', 1)[0] for e in rc.script_allowlist(text)]
    if len({i.lower() for i in ids}) != len(ids):
        issues.append('allowlist ids collide on a case-insensitive filesystem')
    return issues


def check_script(path, root=ROOT):
    out = []
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    versions = rc.known_versions(root)
    v = next((x for x in versions if x['sha256'] == digest), None)
    if v is None:
        out.append(result('script-registered', 'FAIL', f'{path} (sha256 {digest}) is not a registered capture script version'))
        return out
    status = 'PASS' if v['status'] == 'current' else 'WARN'
    out.append(result('script-registered', status, f"capture script version {v['version']} ({v['status']}), sha256 {digest}",
                      sha256=digest, version=v['version']))
    text = data.decode('utf-8', errors='replace')
    if rc.script_allowlist(text) != v['allowlist']:
        out.append(result('script-allowlist', 'FAIL', 'embedded allowlist differs from the registered one'))
    else:
        out.append(result('script-allowlist', 'PASS', f"{len(v['allowlist'])} allowlist entries match the registry"))
    issues = script_lint(text)
    out.append(result('script-lint', 'FAIL' if issues else 'PASS', '; '.join(issues) or 'no prohibited operation found'))
    if data.startswith(b'#!/bin/sh\n') and b'\r\n' not in data:
        out.append(result('script-format', 'PASS', '#!/bin/sh shebang, Unix line endings'))
    else:
        out.append(result('script-format', 'FAIL', 'needs a #!/bin/sh first line and Unix (LF) line endings; '
                                                     'an editor or download may have converted it'))
    return out


def acquisition(root=ROOT):
    return next(x for x in json.loads((root / 'evidence/firmware/acquisitions.json').read_text(encoding='utf-8')) if x['source'] == SOURCE)


def file_sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def check_archive(path, root=ROOT):
    a = acquisition(root)
    size = Path(path).stat().st_size
    digest = file_sha(path)
    ok = size == a['size'] and digest == a['sha256']
    return [result('archive', 'PASS' if ok else 'FAIL', f'{Path(path).name}: {size} bytes, sha256 {digest}'
                   + ('' if ok else f" (expected {a['size']} bytes, {a['sha256']})"))]


def busybox_applets(data):
    """Applet names from BusyBox's packed, sorted name table, without running it."""
    p = data.find(b'[\0[[\0')
    if p < 0:
        return None
    names = []
    while True:
        q = data.index(b'\0', p)
        word = data[p:q]
        if not word or not re.fullmatch(rb'[\x21-\x7e]+', word):
            break
        names.append(word.decode())
        p = q + 1
    return names if len(names) > 20 else None


def check_image(path, root=ROOT):
    """Catalogue the image afresh with the committed plan and compare every component."""
    import firmware_catalogue
    out = []
    a = acquisition(root)
    p = Path(path)
    if p.stat().st_size != a['expanded_size']:
        return [result('image', 'FAIL', f"{p.name} is {p.stat().st_size} bytes, expected {a['expanded_size']}")]
    plan = json.loads((root / 'evidence/firmware/koriki-v1.0-plan.json').read_text(encoding='utf-8'))
    committed = json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text(encoding='utf-8'))
    try:
        fresh = firmware_catalogue.catalogue(p, plan)
    except ValueError as e:
        return [result('image', 'FAIL', f'{p.name}: {e}')]
    out.append(result('image', 'PASS', f"{p.name}: sha256 {fresh['sha256']} equals the pinned Koriki v1.0 image"))
    want = {c['id']: c['sha256'] for c in committed['components']}
    got = {c['id']: c['sha256'] for c in fresh['components']}
    bad = sorted(k for k in want if got.get(k) != want[k])
    labels = {'early-region.bin': 'loader window 0x200200-0x300000 (block 0, bootloader.ini, bootloader.bin, app.bin)',
              'u-boot.uimage': 'U-Boot 2015.04 uImage at 0x300000'}
    for k in sorted(want):
        out.append(result('component:' + k, 'FAIL' if k in bad else 'PASS',
                          f"{labels.get(k, k)}: {'differs from' if k in bad else 'equals'} the catalogue ({want[k][:16]}…)"))
    import boot_chain
    sf = boot_chain.sfvd_status(p)
    out.append(result('sfvd', 'PASS' if sf['present'] else 'FAIL',
                      f"SFVD marker at {sf['marker_disk_offset']}: {'present' if sf['present'] else 'MISSING'}, value "
                      f"{sf['value']}. " + ('No loader write-back expected (BOOT-014).' if sf['present'] else
                      'Material baseline risk: app.bin would rewrite bootloader.ini on every boot. Do not use this image; '
                      'the preflight does not repair it.'), sfvd=sf))
    out += check_rootfs(p, root)
    return out


def check_rootfs(image, root=ROOT):
    """Compare catalogued rootfs files and confirm the BusyBox applets the script needs."""
    from firmware_catalogue import Window
    from pyfatfs.PyFatFS import PyFatBytesIOFS
    from dissect.extfs import ExtFS
    cat = json.loads((root / 'evidence/firmware/koriki-v1.0-rootfs.json').read_text(encoding='utf-8'))
    committed = json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text(encoding='utf-8'))
    part = next(x for x in committed['partitions'] if x['index'] == 1)
    out, bad = [], []
    with open(image, 'rb') as raw, PyFatBytesIOFS(Window(raw, part['offset'], part['size'])) as fs:
        with fs.openbin(cat['container_path']) as f:
            ext = ExtFS(f)
            busybox = None
            for c in cat['components']:
                node = ext.get(c['path'])
                data = node.open().read(node.size)
                if hashlib.sha256(data).hexdigest() != c['sha256']:
                    bad.append(c['id'])
                if c['id'] == 'busybox':
                    busybox = data
    out.append(result('rootfs-files', 'FAIL' if bad else 'PASS',
                      f"{len(cat['components'])} catalogued rootfs files " + (f'differ: {bad}' if bad else 'match')))
    applets = busybox_applets(busybox) if busybox else None
    if applets is None:
        out.append(result('busybox-applets', 'WARN', 'could not read the BusyBox applet table'))
    else:
        missing = [x for x in REQUIRED_APPLETS if x not in applets]
        out.append(result('busybox-applets', 'FAIL' if missing else 'PASS',
                          f'BusyBox provides {len(applets)} applets; required by the script: '
                          + (f'missing {missing}' if missing else 'all present (' + ', '.join(REQUIRED_APPLETS) + ')')))
    return out


def find_ci(folder, name):
    """Case-insensitive lookup in one directory (FAT ignores case)."""
    for p in Path(folder).iterdir():
        if p.name.lower() == name.lower():
            return p
    return None


def check_boot_dir_files(folder, root=ROOT):
    """Byte checks of the boot partition's top-level files; they never change on boot."""
    out = []
    folder = Path(folder)
    comps = {c['id']: c for c in json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text(encoding='utf-8'))['components']}
    for name, cid in BOOT_FILES.items():
        p = find_ci(folder, name)
        if p is None:
            out.append(result('card-boot:' + name, 'FAIL', f'{name} missing from the boot partition'))
            continue
        digest = file_sha(p)
        ok = digest == comps[cid]['sha256']
        out.append(result('card-boot:' + name, 'PASS' if ok else 'FAIL',
                          f"{name} {'equals' if ok else 'DIFFERS from'} the catalogued file"))
    conf = find_ci(folder, 'batocera-boot.conf')
    if conf:
        vals = rc.conf_values(conf.read_text(encoding='utf-8', errors='replace'))
        oc = vals.get('overclocking')
        out.append(result('card-overclocking', 'PASS' if oc in (None, 'none') else 'FAIL',
                          'overclocking unset' if oc is None else f'overclocking={oc}: must stay unset for the baseline'))
    extra = sorted(p.name for p in folder.iterdir() if p.name.lower() not in {n.lower() for n in BOOT_FILES}
                   | {'boot', 'tools', 'boot_logo.bmp.gz'} and not os_metadata(p.name))
    out.append(result('card-boot-extra', 'WARN' if extra else 'PASS',
                      ('files not in the pinned image: ' + ', '.join(extra)) if extra else 'no extra top-level files'))
    return out


def check_boot_dir(folder, root=ROOT, phase='auto', image=None, baseline=None, cache=None):
    """Boot partition checks. The root filesystem check depends on the card's phase.

    fresh (boot/autoresize still present): boot/BATOCERA must equal the catalogue byte for byte.
    prepared/post-capture: Koriki has booted and written to boot/BATOCERA, so it is compared
    semantically (tools/v3lab/rootfs.py) with the pristine tree rebuilt from --image, or with a
    --baseline manifest saved when the prepared card was checked. Without either, the check
    FAILs with an explanation instead of pretending to verify.
    """
    folder = Path(folder)
    out = check_boot_dir_files(folder, root)
    marker = folder / 'boot' / 'autoresize'
    booted = not marker.exists()
    if phase == 'auto':
        phase = 'prepared' if booted else 'fresh'
    if phase == 'fresh':
        out += check_card_rootfs(folder, root)
    else:
        out += check_card_rootfs_semantic(folder, root, phase, image, baseline, cache)
    out.append(result('card-first-boot', 'PASS' if booted else 'WARN',
                      'first boot completed (boot/autoresize removed by S02resize)' if booted else
                      'boot/autoresize still present: boot the card once and power off before copying the script'))
    return out


def check_card_rootfs_semantic(folder, root, phase, image=None, baseline=None, cache=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from v3lab import rootfs as rf
    from v3lab.steps import Env, scan_file, pristine_manifest
    from v3lab.store import StoreError, read_json, verified_copy
    from v3lab.jobs import Job
    try:
        env = Env(root=Path(root), data=Path(cache) if cache else Path(root) / 'lab-data')
        if phase == 'prepared':
            if not image:
                return [result('card-rootfs', 'FAIL', 'the card has booted, so boot/BATOCERA must be compared with the original '
                               'tree: pass --image koriki-v1.0.img (or use the lab, which does this automatically)')]
            base = pristine_manifest(env, Job('preflight', 'fast'), image=Path(image))
        else:
            if not baseline:
                return [result('card-rootfs', 'FAIL', 'post-capture checks need --baseline, the manifest saved when the '
                               'prepared card was checked')]
            base = rf.Manifest.from_json(read_json(baseline))
        b = find_ci(folder, 'boot')
        c = find_ci(b, 'BATOCERA') if b else None
        if not c:
            return [result('card-rootfs', 'FAIL', 'boot/BATOCERA (the root filesystem) is missing from the boot partition')]
        snap = env.cache / 'card-snapshots' / 'preflight.ext4'
        snap.parent.mkdir(parents=True, exist_ok=True)
        digest = verified_copy(lambda: open(c, 'rb'), snap, c.stat().st_size, label='card root filesystem')
        cur = scan_file(env, snap, digest, Job('preflight', 'fast'), 'card')
        rep = rf.compare(base, cur, rf.load_policy(root), phase)
    except (StoreError, rf.RootfsError, OSError) as e:
        return [result('card-rootfs', 'FAIL', f'semantic root filesystem check could not run: {e}')]
    status = {'PASS': 'PASS', 'REVIEW': 'FAIL', 'FAIL': 'FAIL'}[rep['verdict']]
    return [result('card-rootfs', status, ' '.join(rf.summarize(rep)), report=rep)]


def check_card_rootfs(folder, root=ROOT):
    """The root filesystem container on the card (boot/BATOCERA) must equal the catalogued one.

    It holds the init scripts, launcher and BusyBox the safety analysis read, so the top-level
    boot files matching is not enough. Hashing it reads about 2.4 GB from the card.
    """
    cat = json.loads((root / 'evidence/firmware/koriki-v1.0-rootfs.json').read_text(encoding='utf-8'))
    boot = find_ci(folder, 'boot')
    container = find_ci(boot, 'BATOCERA') if boot is not None and boot.is_dir() else None
    if container is None or not container.is_file():
        return [result('card-rootfs', 'FAIL', 'boot/BATOCERA (the root filesystem) is missing from the boot partition')]
    size = container.stat().st_size
    if size != cat['container_size']:
        return [result('card-rootfs', 'FAIL', f"boot/BATOCERA is {size} bytes, catalogued {cat['container_size']}")]
    digest = file_sha(container)
    ok = digest == cat['container_sha256']
    return [result('card-rootfs', 'PASS' if ok else 'FAIL',
                   'boot/BATOCERA ' + ('equals' if ok else 'DIFFERS from') + ' the catalogued root filesystem' +
                   ('' if ok else '; the card has not been booted (boot/autoresize present), so no change is expected: do not boot it, write it again'),
                   sha256=digest, expected_sha256=cat['container_sha256'])]


def check_share_dir(folder, root=ROOT):
    out = []
    ports = Path(folder) / 'roms' / 'ports'
    if not ports.is_dir():
        return [result('card-ports', 'FAIL', f'{ports} does not exist: create roms/ports on the SHARE partition')]
    current = next(v for v in rc.known_versions(root) if v['status'] == 'current')
    apple = sorted(p.name for p in ports.iterdir() if p.name.startswith('._'))
    if apple:
        out.append(result('card-macos-files', 'WARN', 'macOS metadata files in roms/ports would show up as extra menu '
                          'entries: ' + ', '.join(apple) + '. Delete them (dot_clean -m on the folder, or rm).'))
    scripts = sorted(p for p in ports.iterdir() if p.is_file() and p.suffix.lower() == '.sh' and not p.name.startswith('._'))
    matches = [p for p in scripts if file_sha(p) == current['sha256']]
    if len(matches) == 1 and len(scripts) == 1:
        out.append(result('card-script', 'PASS', f'{matches[0].name} is capture script version {current["version"]}'))
    elif not matches:
        out.append(result('card-script', 'FAIL', 'no .sh file in roms/ports matches the current capture script '
                                                 f'(sha256 {current["sha256"][:16]}…)'))
    else:
        out.append(result('card-script', 'WARN', 'other .sh files are also listed in roms/ports: '
                                                 + ', '.join(p.name for p in scripts)))
    for p in matches:
        if not SAFE_SCRIPT_NAME.fullmatch(p.name):
            out.append(result('card-script-name', 'FAIL', f'{p.name!r}: SimpleMenu runs the path through eval (UI-003); '
                                                          'use letters, digits, dot, dash or underscore only'))
    earlier = sorted(p.name for p in ports.iterdir() if p.is_dir() and p.name.startswith('atm-capture-'))
    out.append(result('card-earlier-captures', 'WARN' if earlier else 'PASS',
                      ('earlier capture folders present (copy them off first; they are kept, never reused): '
                       + ', '.join(earlier)) if earlier else 'no earlier capture folders'))
    free = shutil.disk_usage(folder).free
    out.append(result('card-free-space', 'PASS' if free >= 64 * 1024 * 1024 else 'FAIL',
                      f'{free // (1024 * 1024)} MiB free on SHARE (a capture needs about 2 MiB; 64 MiB required)'))
    return out


def check_boot_region(path, root=ROOT):
    """A raw read of the card from offset 0, at least through the end of U-Boot."""
    with open(path, 'rb') as f:
        return check_boot_bytes(f.read(card_boot_read.HEAD_SIZE), root)


def check_boot_bytes(data, root=ROOT):
    comps = {c['id']: c for c in json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text(encoding='utf-8'))['components']}
    out = []
    for cid in ('early-region.bin', 'u-boot.uimage'):
        loc = comps[cid]['location']
        window = data[loc['offset']:loc['offset'] + loc['size']]
        if len(window) != loc['size']:
            out.append(result('card-raw:' + cid, 'FAIL', f'dump too short: needs at least {loc["offset"] + loc["size"]} bytes'))
            continue
        ok = hashlib.sha256(window).hexdigest() == comps[cid]['sha256']
        out.append(result('card-raw:' + cid, 'PASS' if ok else 'FAIL',
                          f"{cid} on the card {'equals' if ok else 'DIFFERS from'} the catalogue",
                          sha256=hashlib.sha256(window).hexdigest()))
    if len(data) >= 0x204e00:
        present = data[0x202a00:0x202a04] == b'SFVD'
        out.append(result('card-raw:sfvd', 'PASS' if present else 'FAIL',
                          f"SFVD marker on the card: {'present' if present else 'MISSING (bootloader.ini will be rewritten)'}",
                          sha256=hashlib.sha256(data[0x202a00:0x202a04]).hexdigest()))
    else:
        out.append(result('card-raw:sfvd', 'FAIL', 'raw read too short to check SFVD'))
    return out


def run(args, root=ROOT):
    results = check_script(args.script, root)
    results.append(result('procedure', 'PASS', 'TF2 empty, no charging cable, overclocking unset and a spare card '
                                               'are procedural conditions: confirm them in person (device/README.md)'))
    if args.archive:
        results += check_archive(args.archive, root)
    if args.image:
        results += check_image(args.image, root)
    else:
        results.append(result('image', 'SKIP', 'no --image given: firmware components not verified'))
    if args.boot_dir:
        try:
            results += check_boot_dir(args.boot_dir, root, getattr(args, 'phase', 'auto'), args.image,
                                      getattr(args, 'baseline', None))
        except (OSError, ValueError) as e:
            results.append(result('card-boot:access', 'FAIL', f'Cannot read boot partition: {e}. Check the BATOCERA drive letter; do not format.'))
    if args.share_dir:
        try:
            results += check_share_dir(args.share_dir, root)
        except (OSError, ValueError) as e:
            results.append(result('card-share:access', 'FAIL', f'Cannot read SHARE partition: {e}. Check drive letter; do not format.'))
    if args.boot_region or getattr(args, 'windows_boot_letter', None) or getattr(args, 'card_device', None):
        try:
            if args.boot_region:
                results += check_boot_region(args.boot_region, root)
            elif getattr(args, 'windows_boot_letter', None):
                results += check_boot_bytes(card_boot_read.read_windows_card(args.windows_boot_letter), root)
            else:
                results += check_boot_bytes(card_boot_read.read_posix_card(args.card_device), root)
        except (OSError, ValueError) as e:
            results.append(result('card-raw:read', 'FAIL', f'{e}; do not boot the card'))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--script', type=Path, default=ROOT / 'device/capture.sh')
    p.add_argument('--image', type=Path, help='expanded koriki-v1.0.img')
    p.add_argument('--archive', type=Path, help='downloaded koriki-v1.0.img.gz')
    p.add_argument('--boot-dir', type=Path, help="mounted first (boot) partition of the prepared card")
    p.add_argument('--share-dir', type=Path, help='mounted SHARE partition of the prepared card')
    raw = p.add_mutually_exclusive_group()
    raw.add_argument('--boot-region', type=Path, help='existing raw read of the card from byte 0, at least 4 MiB')
    raw.add_argument('--windows-boot-letter', help='Windows: spare card boot partition drive letter (e.g. E); administrator required')
    raw.add_argument('--card-device', help='Linux/macOS: confirmed whole spare card device; read-only')
    p.add_argument('--phase', choices=['auto', 'fresh', 'prepared', 'post-capture'], default='auto',
                   help='card phase for the root filesystem check (auto: fresh if boot/autoresize exists, else prepared)')
    p.add_argument('--baseline', type=Path, help='post-capture: manifest saved when the prepared card was checked')
    p.add_argument('--json', type=Path, help='also write the results as JSON')
    a = p.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    results = run(a)
    width = max(len(r['id']) for r in results)
    for r in results:
        print(f"{r['status']:<4}  {r['id']:<{width}}  {r['detail']}")
    fails = [r for r in results if r['status'] == 'FAIL']
    warns = [r for r in results if r['status'] == 'WARN']
    print(f"\n{len(fails)} FAIL, {len(warns)} WARN. " + ('Not ready: fix every FAIL.' if fails else
          'No FAIL. Resolve any WARN, then follow device/README.md.'))
    if a.json:
        a.json.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(1 if fails else 0)


if __name__ == '__main__':
    main()
