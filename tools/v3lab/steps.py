"""What the computer does for each step of a V3 session.

Every function here takes (env, session, job) and returns a StepResult. None of them
writes to the card except install_script, which the operator starts with a button and
which only adds one file to SHARE/roms/ports. Card paths are re-discovered immediately
before each use, so a changed drive letter is harmless; a different card is refused.
"""
import contextlib
import dataclasses
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import sys

from . import disks, rootfs
from .download import download, expand_gzip, manifest_entry, verify_existing
from .store import StoreError, atomic_write_json, read_json, require_space, sha256_file, verified_copy

GIB = 1024 ** 3


@dataclasses.dataclass
class StepResult:
    ok: bool
    summary: str
    details: dict = dataclasses.field(default_factory=dict)
    blocking_reason: str = None
    lines: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Env:
    root: Path                     # the ATM7039S checkout
    data: Path                     # lab-data/ (private, git-ignored)
    inventory: callable = disks.collect
    network_check: callable = None
    raw_reader: callable = None    # (card) -> first 4 MiB of the card, or raises
    opener: callable = None        # urllib opener for downloads (tests replace it)
    runners: dict = None           # step overrides (the offline simulation replaces 'firmware')

    def runner(self, sid):
        return (self.runners or {}).get(sid) or RUNNERS[sid]

    @property
    def cache(self):
        return self.data / 'cache'

    def tools(self):
        p = str(self.root / 'tools')
        if p not in sys.path:
            sys.path.insert(0, p)

    def json(self, rel):
        return json.loads((self.root / rel).read_text(encoding='utf-8'))


# --------------------------------------------------------------------------- helpers

def _image_paths(env):
    a = manifest_entry(env.root)
    fw = env.cache / 'firmware'
    return a, fw / a['filename'], fw / a['expanded_filename']


def _card(env, session, expect_stage):
    """Discover the card now and make sure it is the session's card."""
    found = disks.identify(env.inventory())
    view = disks.public_view(found)
    if found['status'] == 'none':
        raise StoreError('the test card is not connected. Put the spare card into the card reader.')
    if found['status'] == 'ambiguous':
        raise StoreError('more than one Koriki card is connected. Leave only the spare test card in.')
    card = found['card']
    phys = disks.fingerprint(dict(size=card['size'], model=card.get('model', ''), partitions=[]), session.data['salt'])
    known = session.data.get('card')
    if known and known.get('physical') != phys:
        raise StoreError('this is not the card this session started with (different size or reader model). '
                         'Put the session\'s spare card back in, or start a new session.')
    stage = found.get('stage') or ''
    if expect_stage == 'not-yet-booted' and stage != 'not-yet-booted':
        raise StoreError('the card has already been booted (or is not a fresh Koriki card). '
                         'If it should be fresh, write it again with balenaEtcher.')
    if expect_stage == 'booted' and not stage.startswith('booted'):
        raise StoreError('the card does not look booted yet (SHARE was not created). Do the first boot on the handheld.')
    if found['problems']:
        raise StoreError('the card was found, but: ' + '; '.join(found['problems']) +
                         '. Unplug the card, wait five seconds, plug it in again and retry. '
                         'Do not let Windows format or repair it.')
    if not known:
        session.data['card'] = dict(physical=phys, first_seen_stage=stage)
        session.save()
    return found, view


def _boot_checks(env, boot_dir, phase):
    """Byte checks of the boot partition files, plus the phase-specific BOOT/ folder rules."""
    env.tools()
    import v3_preflight as vp
    out = [r for r in vp.check_boot_dir_files(boot_dir, env.root)]
    policy = rootfs.load_policy(env.root)
    bootsub = vp.find_ci(boot_dir, 'boot')
    names = {p.name.lower(): p for p in bootsub.iterdir()} if bootsub and bootsub.is_dir() else {}
    allowed = {'batocera', 'batocera.board', 'reboot', 'autoresize'}
    extra = sorted(n for n in names if n not in allowed and not vp.os_metadata(n))
    out.append(vp.result('card-boot-folder', 'FAIL' if extra else 'PASS',
                         ('unexpected files in boot/: ' + ', '.join(extra)) if extra else 'boot/ holds only the firmware files'))
    if phase == 'fresh':
        out.append(vp.result('card-not-booted', 'PASS' if 'autoresize' in names else 'FAIL',
                             'boot/autoresize present: the card has not been booted' if 'autoresize' in names else
                             'boot/autoresize is missing, so this card has already been booted'))
    else:
        out.append(vp.result('card-first-boot', 'PASS' if 'autoresize' not in names else 'FAIL',
                             'first boot completed (S02resize removed boot/autoresize)' if 'autoresize' not in names else
                             'boot/autoresize is still there: the first boot did not finish'))
    if 'reboot' in names:
        ok = sha256_file(names['reboot']) in policy['boot_partition']['BOOT/REBOOT']['allowed_contents_sha256']
        out.append(vp.result('card-reboot-flag', 'PASS' if ok else 'FAIL',
                             'boot/REBOOT holds what the ramdisk /init writes' if ok else 'boot/REBOOT has unexpected contents'))
    return out


def _fails(results):
    return [r for r in results if r['status'] == 'FAIL']


def _container_on_card(env, boot_dir):
    env.tools()
    import v3_preflight as vp
    b = vp.find_ci(boot_dir, 'boot')
    c = vp.find_ci(b, 'BATOCERA') if b else None
    if not c or not c.is_file():
        raise StoreError('boot/BATOCERA (the system files) is missing from the card')
    return c


def _stamp(path):
    def f():
        st = Path(path).stat()
        return (st.st_size, st.st_mtime_ns)
    return f


def snapshot_card_container(env, session, boot_mount, job, label):
    """Verified sequential copy of boot/BATOCERA to this computer. Returns (local path, sha256)."""
    rootcat = env.json('evidence/firmware/koriki-v1.0-rootfs.json')
    src = _container_on_card(env, Path(boot_mount))
    size = src.stat().st_size
    if size != rootcat['container_size']:
        raise StoreError(f'boot/BATOCERA is {size:,} bytes; the firmware has {rootcat["container_size"]:,}')
    snaps = env.cache / 'card-snapshots'
    snaps.mkdir(parents=True, exist_ok=True)
    tmp = snaps / f"{session.data['id']}-{label}.ext4"
    digest = verified_copy(lambda: open(src, 'rb'), tmp, size, job=job, label=f'copying the card\'s system files ({label})',
                           stamp=_stamp(src))
    final = snaps / f'{digest}.ext4'
    if final.exists():
        tmp.unlink()
    else:
        os.replace(tmp, final)
    return final, digest


def pristine_manifest(env, job, image=None):
    """Semantic manifest of the pinned container, rebuilt from the verified image and checked
    against the committed digest."""
    policy = rootfs.load_policy(env.root)
    cached = env.cache / 'manifests' / f"pristine-{policy['container_sha256']}.json"
    with contextlib.suppress(StoreError, rootfs.RootfsError, TypeError, KeyError):
        d = read_json(cached)
        if d:
            m = rootfs.Manifest.from_json(d)
            if m.digest() == policy['pristine_manifest']['digest']:
                return m
    cat = env.json('evidence/firmware/koriki-v1.0.json')
    rootcat = env.json('evidence/firmware/koriki-v1.0-rootfs.json')
    local = env.cache / 'firmware' / 'koriki-v1.0-rootfs.ext4'
    if not verify_existing(local, rootcat['container_size'], rootcat['container_sha256'], job):
        a, gz, img = _image_paths(env)
        img = Path(image) if image else img
        if not verify_existing(img, a['expanded_size'], a['expanded_sha256'], job):
            raise StoreError('the verified firmware image is not available; run "Download and check the firmware" again')
        local.parent.mkdir(parents=True, exist_ok=True)
        verified_copy(rootfs.open_container_in_image(img, cat, rootcat), local, rootcat['container_size'],
                      rootcat['container_sha256'], job=job, label='extracting the original system files')
        from .download import mark_verified
        mark_verified(local, rootcat['container_sha256'])
    m = scan_file(env, local, rootcat['container_sha256'], job, 'original')
    if m.digest() != policy['pristine_manifest']['digest']:
        raise StoreError('the original system files do not give the committed manifest digest; the lab or the '
                         'firmware differs from what was reviewed. Stop and report this.')
    atomic_write_json(cached, m.to_json())
    return m


def scan_file(env, path, sha, job, label):
    from dissect.extfs import ExtFS
    (env.cache / 'checkpoints').mkdir(parents=True, exist_ok=True)
    db = env.cache / 'checkpoints' / f'{label}-{sha}.sqlite'
    with open(path, 'rb') as f:
        try:
            return rootfs.scan(ExtFS(f), sha, db, job=job, estimate=27112)
        except rootfs.RootfsError as e:
            if 'different filesystem or tool version' in str(e) or 'no identity' in str(e):
                db.rename(db.with_suffix('.sqlite.old'))
                f.seek(0)
                return rootfs.scan(ExtFS(f), sha, db, job=job, estimate=27112)
            raise


# --------------------------------------------------------------------------- steps

def step_computer(env, session, job):
    job.start_phase('checking this computer', 5, 'checks')
    lines, problems = [], []
    v = sys.version_info
    lines.append(f'Python {v.major}.{v.minor}.{v.micro} on {platform.system()} {platform.release()}')
    if v < (3, 11):
        problems.append('Python 3.11 or newer is needed (hashlib.file_digest). Install it from python.org.')
    job.advance()
    missing = [m for m in ('pyfatfs', 'fs', 'dissect.extfs', 'jsonschema') if importlib.util.find_spec(m.split('.')[0]) is None
               or (m == 'dissect.extfs' and importlib.util.find_spec('dissect.extfs') is None)]
    if missing:
        problems.append('missing helper libraries: ' + ', '.join(missing) + ' (start the lab with the launcher, which installs them)')
    else:
        lines.append('Helper libraries present.')
    job.advance()
    enc = sys.flags.utf8_mode or (sys.getfilesystemencoding().lower() in ('utf-8', 'utf8'))
    lines.append('UTF-8 mode on.' if enc else 'UTF-8 mode off: text files are still read as UTF-8 explicitly.')
    job.advance()
    need = 8 * GIB
    env.data.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(env.data).free
    lines.append(f'{free / GIB:.1f} GiB free where the lab keeps its files ({env.data}).')
    if free < need:
        problems.append(f'about {need / GIB:.0f} GiB of free space is needed for the firmware and card copies; '
                        f'only {free / GIB:.1f} GiB is free on that drive')
    job.advance()
    a, gz, img = _image_paths(env)
    have = img.exists() or gz.exists()
    check = env.network_check or _network_ok
    net = check()
    lines.append('Internet connection to github.com works.' if net else 'No connection to github.com.')
    if not net and not have:
        problems.append('the firmware has not been downloaded yet and github.com cannot be reached')
    job.advance()
    return StepResult(not problems, 'Computer is ready.' if not problems else 'This computer needs attention.',
                      dict(python=f'{v.major}.{v.minor}.{v.micro}', free_bytes=free, network=net),
                      '; '.join(problems) or None, lines)


def _network_ok():
    try:
        with socket.create_connection(('github.com', 443), timeout=5):
            return True
    except OSError:
        return False


def step_firmware(env, session, job):
    a, gz, img = _image_paths(env)
    lines = []
    if not verify_existing(img, a['expanded_size'], a['expanded_sha256'], job):
        kw = dict(opener=env.opener) if env.opener else {}
        r = download(a['url'], gz, a['size'], a['sha256'], job, **kw)
        lines.append('Firmware archive ' + ('was already downloaded and checked.' if r['status'] == 'reused' else 'downloaded and checked.'))
        expand_gzip(gz, img, a['expanded_size'], a['expanded_sha256'], job, compressed_size=a['size'])
        lines.append('Firmware image unpacked and checked.')
    else:
        lines.append('Firmware image already present and checked.')
    env.tools()
    import v3_preflight as vp
    job.start_phase('checking the firmware components', None, 'checks')
    results = vp.check_image(img, env.root) + vp.check_script(env.root / 'device/capture.sh', env.root)
    fails = _fails(results)
    if not fails:
        pristine_manifest(env, job)
        lines.append('Original system files rebuilt and matched to the reviewed manifest.')
    session.data['outputs']['firmware_image'] = str(img)
    return StepResult(not fails, 'Firmware is downloaded and correct.' if not fails else 'The firmware check failed.',
                      dict(checks=results), '; '.join(f"{r['id']}: {r['detail']}" for r in fails) or None, lines)


def step_check_fresh(env, session, job):
    found, view = _card(env, session, 'not-yet-booted')
    boot = Path(found['boot_mount'])
    results = _boot_checks(env, boot, 'fresh')
    rootcat = env.json('evidence/firmware/koriki-v1.0-rootfs.json')
    c = _container_on_card(env, boot)
    digest = sha256_file(c, job)
    results.append(dict(id='card-rootfs', status='PASS' if digest == rootcat['container_sha256'] else 'FAIL',
                        detail='boot/BATOCERA equals the firmware byte for byte' if digest == rootcat['container_sha256'] else
                        'boot/BATOCERA differs from the firmware although the card has not been booted'))
    results += raw_checks(env, found)
    fails = _fails(results)
    session.data['baselines']['fresh'] = dict(container_sha256=digest)
    return StepResult(not fails, 'The card was written correctly.' if not fails else 'The card does not match the firmware.',
                      dict(checks=results, card=view), '; '.join(f"{r['id']}: {r['detail']}" for r in fails) or None,
                      [f"{r['status']}  {r['detail']}" for r in results])


def raw_checks(env, found):
    """Boot loader and U-Boot on the raw card (outside any partition), plus the SFVD marker."""
    env.tools()
    import v3_preflight as vp
    reader = env.raw_reader or default_raw_reader
    try:
        data = reader(found['card'])
    except (OSError, ValueError, StoreError) as e:
        return [vp.result('card-raw:read', 'FAIL', f'the boot loader area could not be read: {e}')]
    return vp.check_boot_bytes(data, env.root)


def default_raw_reader(card):
    """Read the first 4 MiB of the card. Windows needs one administrator approval for this read."""
    import card_boot_read as cbr
    if os.name == 'nt':
        from . import elevate
        return elevate.raw_head(card['number'])
    return cbr.read_posix_card(card['path'])


def step_check_prepared(env, session, job):
    found, view = _card(env, session, 'booted')
    boot = Path(found['boot_mount'])
    results = _boot_checks(env, boot, 'prepared')
    base = pristine_manifest(env, job)
    local, digest = snapshot_card_container(env, session, found['boot_mount'], job, 'prepared')
    cur = scan_file(env, local, digest, job, 'card')
    report = rootfs.compare(base, cur, rootfs.load_policy(env.root), 'prepared')
    rep_path = session.dir / 'rootfs-prepared.json'
    atomic_write_json(rep_path, report)
    results.append(dict(id='card-rootfs', status={'PASS': 'PASS', 'REVIEW': 'WARN', 'FAIL': 'FAIL'}[report['verdict']],
                        detail='; '.join(rootfs.summarize(report)[:2])))
    results += raw_checks(env, found)
    fails = _fails(results)
    ok = not fails and report['verdict'] == 'PASS'
    if ok:
        atomic_write_json(session.dir / 'baseline-prepared.json', cur.to_json())
        session.data['baselines']['prepared'] = dict(container_sha256=digest, manifest_digest=cur.digest(),
                                                     manifest=str(session.dir / 'baseline-prepared.json'),
                                                     report=str(rep_path))
    reason = None
    if not ok:
        reason = ('; '.join(f"{r['id']}: {r['detail']}" for r in fails) or
                  'the system-file check needs review: ' + '; '.join(report['notes'] + report['health']['review']))
    return StepResult(ok, 'The card is ready for the capture script.' if ok else 'Stop: the card is not in the expected state.',
                      dict(checks=results, rootfs_report=str(rep_path), card=view), reason,
                      rootfs.summarize(report) + [f"{r['status']}  {r['detail']}" for r in results if r['id'] != 'card-rootfs'])


def step_install_script(env, session, job):
    found, view = _card(env, session, 'booted')
    share = Path(found['share_mount'])
    src = env.root / 'device/capture.sh'
    env.tools()
    import v3_preflight as vp
    pre = vp.check_script(src, env.root)
    if _fails(pre):
        return StepResult(False, 'The capture script in this checkout is not the registered one.', dict(checks=pre),
                          '; '.join(r['detail'] for r in _fails(pre)))
    ports = share / 'roms' / 'ports'
    ports.mkdir(parents=True, exist_ok=True)
    others = sorted(p.name for p in ports.iterdir() if p.suffix.lower() == '.sh' and p.name != 'ATM7039S-capture.sh')
    dest = ports / 'ATM7039S-capture.sh'
    want = sha256_file(src)
    if not dest.exists() or sha256_file(dest) != want:
        tmp = ports / 'ATM7039S-capture.sh.partial'
        shutil.copyfile(src, tmp)
        with open(tmp, 'rb+') as f:
            os.fsync(f.fileno())
        os.replace(tmp, dest)
    got = sha256_file(dest)
    results = vp.check_share_dir(share, env.root)
    fails = _fails(results) + ([dict(id='copy', detail='the copy on the card does not match')] if got != want else [])
    earlier = sorted(p.name for p in ports.iterdir() if p.is_dir() and p.name.startswith('atm-capture-'))
    session.data['outputs']['captures_before'] = earlier
    lines = [f'Copied to SHARE/roms/ports/ATM7039S-capture.sh and checked (SHA-256 {got[:12]}…).']
    if others:
        lines.append('Other scripts are also in roms/ports: ' + ', '.join(others) + '. Only start ATM7039S-capture.')
    if earlier:
        lines.append('Earlier capture folders are on the card; they are kept and will not be confused with the new one.')
    return StepResult(not fails, 'The capture script is on the card.' if not fails else 'The script could not be put on the card.',
                      dict(checks=results), '; '.join(r['detail'] for r in fails) or None, lines)


def step_collect(env, session, job):
    found, view = _card(env, session, 'booted')
    ports = Path(found['share_mount']) / 'roms' / 'ports'
    before = set(session.data['outputs'].get('captures_before') or [])
    caps = sorted(p for p in ports.iterdir() if p.is_dir() and p.name.startswith('atm-capture-') and p.name not in before)
    if not caps:
        return StepResult(False, 'No new capture folder on the card.', {}, 'no new atm-capture-* folder was found in '
                          'SHARE/roms/ports: run the capture on the handheld, then put the card back in')
    if len(caps) > 1:
        return StepResult(False, 'More than one new capture folder.', dict(folders=[p.name for p in caps]),
                          'several new capture folders exist; the session expects exactly one capture run')
    cap = caps[0]
    dest = session.dir / 'private' / cap.name
    files = sorted(p for p in cap.rglob('*') if p.is_file())
    total = sum(p.stat().st_size for p in files)
    require_space(session.dir, total + 64 * 2**20, 'the capture copy')
    job.start_phase('copying the capture', total, 'bytes')
    for p in files:
        rel = p.relative_to(cap)
        if '..' in rel.parts:
            raise StoreError('unsafe name in the capture folder')
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        size = p.stat().st_size
        verified_copy(lambda p=p: open(p, 'rb'), out, size, label=f'copying {rel}')
        job.advance(size, nbytes=size)
    env.tools()
    import runtime_capture as rc
    import research
    boot = Path(found['boot_mount'])
    import v3_preflight as vp
    dtb = vp.find_ci(boot, 'KERNEL.DTB')
    try:
        result = rc.parse(dest, env.root, reference_dtb=dtb)
    except (ValueError, OSError) as e:
        session.data['outputs'].update(capture_private=str(dest), capture_state='unreadable')
        return StepResult(False, 'The capture folder is incomplete or damaged.', dict(error=str(e)),
                          f'the capture folder is not admissible: {e}. It was copied to the private session folder; '
                          'keep the card unchanged and send the diagnostic bundle before running the capture again')
    summary = session.dir / 'summary.json'
    research.save(summary, result)
    (session.dir / 'summary.md').write_text(rc.render_report(result), encoding='utf-8')
    c = result['capture']
    session.data['outputs'].update(capture_private=str(dest), summary=str(summary), capture_state=c['state'])
    ok = c['state'] == 'authenticated-complete'
    lines = [f"Capture state: {c['state']}; {c['status_counts'].get('ok', 0)} items OK; "
             f"{len(c['essential_not_ok'])} essential items missing.",
             'The raw capture is kept private in the session folder. Share only summary.json/summary.md.']
    return StepResult(ok or c['admissible_as_evidence'], f"Capture analysed: {c['state']}.",
                      dict(state=c['state'], errors=c['errors'], warnings=c['warnings']),
                      None if (ok or c['admissible_as_evidence']) else 'the capture is not admissible: ' + '; '.join(c['errors'][:5]),
                      lines)


def step_postflight(env, session, job):
    found, view = _card(env, session, 'booted')
    boot = Path(found['boot_mount'])
    results = _boot_checks(env, boot, 'prepared')
    env.tools()
    import v3_preflight as vp
    share = Path(found['share_mount'])
    script = share / 'roms' / 'ports' / 'ATM7039S-capture.sh'
    results += vp.check_script(script, env.root) if script.exists() else [vp.result('card-script', 'FAIL', 'the capture script is no longer on the card')]
    pb = session.data['baselines'].get('prepared')
    if not pb:
        raise StoreError('no checked prepared-card baseline exists in this session')
    base = rootfs.Manifest.from_json(read_json(pb['manifest']))
    local, digest = snapshot_card_container(env, session, found['boot_mount'], job, 'post-capture')
    cur = scan_file(env, local, digest, job, 'card')
    report = rootfs.compare(base, cur, rootfs.load_policy(env.root), 'post-capture')
    report['container_unchanged_bytes'] = digest == pb['container_sha256']
    rep = session.dir / 'rootfs-post-capture.json'
    atomic_write_json(rep, report)
    results.append(dict(id='card-rootfs', status={'PASS': 'PASS', 'REVIEW': 'WARN', 'FAIL': 'FAIL'}[report['verdict']],
                        detail=('byte-identical to the checked prepared card' if report['container_unchanged_bytes'] else
                                'compared with the checked prepared card: ' + rootfs.summarize(report)[1])))
    fails = _fails(results)
    session.data['baselines']['post-capture'] = dict(container_sha256=digest, manifest_digest=cur.digest(), report=str(rep))
    return StepResult(not fails and report['verdict'] == 'PASS', 'The card is in the expected state after the capture.'
                      if not fails and report['verdict'] == 'PASS' else 'The card changed in an unexpected way during the capture.',
                      dict(checks=results), '; '.join(f"{r['id']}: {r['detail']}" for r in fails) or
                      ('; '.join(report['notes']) if report['verdict'] != 'PASS' else None),
                      rootfs.summarize(report))


RUNNERS = {'computer': step_computer, 'firmware': step_firmware, 'check-fresh': step_check_fresh,
           'check-prepared': step_check_prepared, 'install-script': step_install_script,
           'collect': step_collect, 'postflight': step_postflight}
