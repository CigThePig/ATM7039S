"""A shareable diagnostic bundle: enough for another developer (or AI) to see what happened.

Built from an allow-list, not by zipping folders: session progress and check results,
the lab log, tool and library versions, platform facts, and the redacted disk view.
Never included: the raw capture, card or firmware copies, the session salt, disk serial
numbers or signatures. Home-directory paths and the account name are replaced.
"""
import getpass
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import zipfile

from . import VERSION

PACKAGES = ['pyfatfs', 'fs', 'dissect.extfs', 'dissect.util', 'dissect.cstruct', 'jsonschema', 'pyelftools', 'capstone', 'unicorn']
MAC = re.compile(r'\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b', re.I)


def scrub(text):
    home = str(Path.home())
    for h in {home, home.replace('\\', '/'), home.replace('\\', '\\\\')}:
        if h and len(h) > 3:
            text = text.replace(h, '~')
    try:
        user = getpass.getuser()
        if user and len(user) > 2:
            text = re.sub(re.escape(user), '<user>', text, flags=re.I)
    except Exception:
        pass
    host = platform.node()
    if host and len(host) > 2:
        text = text.replace(host, '<computer>')
    return MAC.sub('<mac>', text)


def versions():
    out = {}
    for p in PACKAGES:
        try:
            out[p] = importlib.metadata.version(p)
        except importlib.metadata.PackageNotFoundError:
            out[p] = None
    return out


def build(data_dir, session=None, disk_view=None, error=None, out_dir=None):
    data_dir = Path(data_dir)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    out_dir = Path(out_dir or data_dir / 'diagnostics')
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f'ATM7039S-lab-diagnostics-{stamp}.zip'
    facts = dict(lab_version=VERSION, created=stamp, python=sys.version, executable_kind='venv' if sys.prefix != sys.base_prefix else 'system',
                 platform=platform.platform(), machine=platform.machine(), utf8_mode=bool(sys.flags.utf8_mode),
                 fs_encoding=sys.getfilesystemencoding(), packages=versions(), error=error)
    files = {'facts.json': json.dumps(facts, indent=2)}
    if session is not None:
        view = session.view()
        runs = {s['id']: s['runs'] for s in session.data['steps']}
        files['session.json'] = json.dumps(dict(view=view, runs=runs, deviations=session.data['deviations'],
                                                notes=session.data.get('notes', [])), indent=2, default=str)
        for name in ('rootfs-prepared.json', 'rootfs-post-capture.json'):
            p = session.dir / name
            if p.exists():
                files[name] = p.read_text(encoding='utf-8')
    if disk_view is not None:
        files['disks.json'] = json.dumps(disk_view, indent=2)
    log = data_dir / 'logs' / 'lab.log'
    if log.exists():
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()[-2000:]
        files['lab.log'] = '\n'.join(lines)
    ck = data_dir / 'cache'
    if ck.exists():
        listing = [dict(name=p.relative_to(ck).as_posix(), bytes=p.stat().st_size) for p in ck.rglob('*') if p.is_file()]
        files['cache-listing.json'] = json.dumps(sorted(listing, key=lambda d: d['name']), indent=1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, scrub(text))
        z.writestr('README.txt', 'ATM7039S lab diagnostic bundle. Contains no raw capture, card data or identifiers; '
                                 'paths and the account name are replaced. Safe to attach to an issue after a quick look.\n')
    tmp = path.with_name(path.name + '.partial')
    tmp.write_bytes(buf.getvalue())
    os.replace(tmp, path)
    return path
