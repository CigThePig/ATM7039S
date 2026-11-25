#!/usr/bin/env python3
"""Offline preflight for hardware test V3. Verification only: it never writes to an image or a card.

Run it on a computer before (and, optionally, after) the physical session:

    python tools/v3_preflight.py                          # the capture package only
    python tools/v3_preflight.py --image INPUTS/koriki-v1.0.img [--archive INPUTS/koriki-v1.0.img.gz]
    python tools/v3_preflight.py --boot-dir /media/BOOT --share-dir /media/SHARE   # the prepared card
    python tools/v3_preflight.py --boot-region card-head.bin   # optional raw read of the card's first 4 MiB

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
import json
from pathlib import Path
import re
import shutil
import sys

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
    return next(x for x in json.loads((root / 'evidence/firmware/acquisitions.json').read_text()) if x['source'] == SOURCE)


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
    plan = json.loads((root / 'evidence/firmware/koriki-v1.0-plan.json').read_text())
    committed = json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text())
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
    cat = json.loads((root / 'evidence/firmware/koriki-v1.0-rootfs.json').read_text())
    committed = json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text())
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


def check_boot_dir(folder, root=ROOT):
    out = []
    folder = Path(folder)
    comps = {c['id']: c for c in json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text())['components']}
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
        vals = rc.conf_values(conf.read_text(errors='replace'))
        oc = vals.get('overclocking')
        out.append(result('card-overclocking', 'PASS' if oc in (None, 'none') else 'FAIL',
                          'overclocking unset' if oc is None else f'overclocking={oc}: must stay unset for the baseline'))
    extra = sorted(p.name for p in folder.iterdir() if p.name.lower() not in {n.lower() for n in BOOT_FILES}
                   | {'boot', 'tools', 'boot_logo.bmp.gz', 'system volume information'})
    out.append(result('card-boot-extra', 'WARN' if extra else 'PASS',
                      ('files not in the pinned image: ' + ', '.join(extra)) if extra else 'no extra top-level files'))
    marker = folder / 'boot' / 'autoresize'
    out.append(result('card-first-boot', 'PASS' if not marker.exists() else 'WARN',
                      'first boot completed (boot/autoresize removed by S02resize)' if not marker.exists() else
                      'boot/autoresize still present: boot the card once and power off before copying the script'))
    return out


def check_share_dir(folder, root=ROOT):
    out = []
    ports = Path(folder) / 'roms' / 'ports'
    if not ports.is_dir():
        return [result('card-ports', 'FAIL', f'{ports} does not exist: create roms/ports on the SHARE partition')]
    current = next(v for v in rc.known_versions(root) if v['status'] == 'current')
    scripts = sorted(p for p in ports.iterdir() if p.is_file() and p.suffix.lower() == '.sh')
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
    comps = {c['id']: c for c in json.loads((root / 'evidence/firmware/koriki-v1.0.json').read_text())['components']}
    data = Path(path).read_bytes()
    out = []
    for cid in ('early-region.bin', 'u-boot.uimage'):
        loc = comps[cid]['location']
        window = data[loc['offset']:loc['offset'] + loc['size']]
        if len(window) != loc['size']:
            out.append(result('card-raw:' + cid, 'FAIL', f'dump too short: needs at least {loc["offset"] + loc["size"]} bytes'))
            continue
        ok = hashlib.sha256(window).hexdigest() == comps[cid]['sha256']
        out.append(result('card-raw:' + cid, 'PASS' if ok else 'FAIL',
                          f"{cid} on the card {'equals' if ok else 'DIFFERS from'} the catalogue"))
    if len(data) >= 0x204e00:
        import boot_chain
        sf = boot_chain.sfvd_status(path)
        out.append(result('card-raw:sfvd', 'PASS' if sf['present'] else 'FAIL',
                          f"SFVD marker on the card: {'present' if sf['present'] else 'MISSING (bootloader.ini will be rewritten)'}"))
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
        results += check_boot_dir(args.boot_dir, root)
    if args.share_dir:
        results += check_share_dir(args.share_dir, root)
    if args.boot_region:
        results += check_boot_region(args.boot_region, root)
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--script', type=Path, default=ROOT / 'device/capture.sh')
    p.add_argument('--image', type=Path, help='expanded koriki-v1.0.img')
    p.add_argument('--archive', type=Path, help='downloaded koriki-v1.0.img.gz')
    p.add_argument('--boot-dir', type=Path, help="mounted first (boot) partition of the prepared card")
    p.add_argument('--share-dir', type=Path, help='mounted SHARE partition of the prepared card')
    p.add_argument('--boot-region', type=Path, help='raw read of the card from byte 0, at least 4 MiB')
    p.add_argument('--json', type=Path, help='also write the results as JSON')
    a = p.parse_args()
    results = run(a)
    width = max(len(r['id']) for r in results)
    for r in results:
        print(f"{r['status']:<4}  {r['id']:<{width}}  {r['detail']}")
    fails = [r for r in results if r['status'] == 'FAIL']
    warns = [r for r in results if r['status'] == 'WARN']
    print(f"\n{len(fails)} FAIL, {len(warns)} WARN. " + ('Not ready: fix every FAIL.' if fails else
          'No FAIL. Resolve any WARN, then follow device/README.md.'))
    if a.json:
        a.json.write_text(json.dumps(results, indent=2) + '\n')
    raise SystemExit(1 if fails else 0)


if __name__ == '__main__':
    main()
