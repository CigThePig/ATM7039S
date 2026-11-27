"""Phase-aware review of a Koriki card's root filesystem (boot/BATOCERA). Read-only toward the card.

Version 3 replaces the 2.x session diagnostic used during OBS-001 (whose report
evidence/observations/OBS-001-rootfs.json stays as historical evidence). It uses the same
verifier as the lab (tools/v3lab/rootfs.py): a verified local copy of the container, a
resumable semantic scan, and comparison under the evidence-derived first-boot policy
(evidence/firmware/koriki-v1.0-first-boot.json). Unexplained changes fail; nothing is
whitelisted by hash.

    python tools/v3_rootfs_review.py --phase prepared --image inputs/koriki-v1.0.img
    python tools/v3_rootfs_review.py --phase post-capture --baseline lab-data/rootfs-review/card-prepared.json
    python tools/v3_rootfs_review.py --card E:/boot/BATOCERA ...      # instead of automatic discovery

Most operators never run this directly: the lab (ATM7039S-Lab.cmd) does it as part of the session.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from v3lab import disks, rootfs  # noqa: E402
from v3lab.jobs import Job, low_priority  # noqa: E402
from v3lab.steps import Env, pristine_manifest, scan_file  # noqa: E402
from v3lab.store import StoreError, atomic_write_json, instance_lock, read_json, verified_copy  # noqa: E402

VERSION = '3.0'


def say(*a):
    print(*a, flush=True)


def find_card_container(explicit, env):
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise StoreError(f'{p} does not exist (check the drive letter)')
        return p
    found = disks.identify(env.inventory())
    if found['status'] not in ('found',):
        raise StoreError('could not identify exactly one Koriki card: ' + '; '.join(found.get('problems') or [found['status']]) +
                         '. Insert only the test card, or pass --card PATH/boot/BATOCERA.')
    boot = Path(found['boot_mount'])
    for d in boot.iterdir():
        if d.name.lower() == 'boot':
            for f in d.iterdir():
                if f.name.lower() == 'batocera':
                    return f
    raise StoreError('boot/BATOCERA is missing from the card')


def review(env, phase, card=None, image=None, baseline=None, job=None):
    job = job or Job('rootfs review', 'quiet')
    rootcat = env.json('evidence/firmware/koriki-v1.0-rootfs.json')
    if phase == 'prepared':
        base = pristine_manifest(env, job, image=image)
    else:
        if not baseline:
            raise StoreError('post-capture review needs --baseline (the card manifest saved by the prepared review)')
        base = rootfs.Manifest.from_json(read_json(baseline))
    src = find_card_container(card, env)
    size = src.stat().st_size
    if size != rootcat['container_size']:
        raise StoreError(f'boot/BATOCERA is {size:,} bytes; the firmware has {rootcat["container_size"]:,}')
    snap = env.cache / 'card-snapshots' / f'review-{phase}.ext4'
    snap.parent.mkdir(parents=True, exist_ok=True)

    def stamp():
        st = src.stat()
        return (st.st_size, st.st_mtime_ns)
    digest = verified_copy(lambda: open(src, 'rb'), snap, size, job=job, label='copying the card root filesystem', stamp=stamp)
    cur = scan_file(env, snap, digest, job, 'card')
    report = rootfs.compare(base, cur, rootfs.load_policy(env.root), phase)
    report['tool'] = f'v3_rootfs_review.py {VERSION}'
    out = env.data / 'rootfs-review'
    atomic_write_json(out / f'report-{phase}.json', report)
    # Failed or review-only manifests must never be offered as approved baselines.
    if report['verdict'] == 'PASS':
        atomic_write_json(out / f'card-{phase}.json', cur.to_json())
    else:
        (out / f'card-{phase}.json').unlink(missing_ok=True)
    return report, out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--phase', choices=['prepared', 'post-capture'], default='prepared')
    p.add_argument('--card', help='explicit path to boot/BATOCERA on the mounted card (default: find the card)')
    p.add_argument('--image', type=Path, help='pinned koriki-v1.0.img (default: the lab\'s verified download)')
    p.add_argument('--baseline', type=Path, help='post-capture: card-prepared.json written by the prepared review')
    p.add_argument('--data', type=Path, default=ROOT / 'lab-data', help='private working folder (git-ignored)')
    p.add_argument('--fast', action='store_true', help='do not throttle disk reads (default is quiet, background-friendly)')
    a = p.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    env = Env(root=ROOT, data=a.data)
    say(f'Root filesystem review {VERSION}: reads the card, writes only to {a.data}. {low_priority()}.')
    try:
        with instance_lock(a.data / 'rootfs-review.lock'):
            report, out = review(env, a.phase, a.card, a.image, a.baseline, Job('review', 'fast' if a.fast else 'quiet'))
    except KeyboardInterrupt:
        say('Stopped. Run the same command again to continue; finished work is reused.')
        return 130
    except (StoreError, rootfs.RootfsError, OSError) as e:
        say(f'Could not finish: {e}\nNothing on the card was changed. Finished local work is kept; fix the problem and run again.')
        return 1
    for line in rootfs.summarize(report):
        say(line)
    say(f'Private report: {out / ("report-" + a.phase + ".json")}')
    return 0 if report['verdict'] == 'PASS' else (2 if report['verdict'] == 'REVIEW' else 1)


if __name__ == '__main__':
    raise SystemExit(main())
