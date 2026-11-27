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
    text = MAC.sub('<mac>', text)
    text = re.sub(r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<uuid>', text)
    text = re.sub(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', '<ipv4>', text)
    text = re.sub(r'(?i)(?<![\w:])(?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}(?![\w:])', '<ipv6>', text)
    text = re.sub(r'(?i)\b(serial(?:number|no)?|cid|uniqueid|hostname)\s*[:=]\s*["\']?[^\s,"\']+', r'\1=<redacted>', text)
    return text


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
        # Keep status and check codes; raw free-text error/detail fields and paths
        # may contain private names, so do not include the full session in a bundle.
        files['session.json'] = json.dumps(dict(id=view['id'], test=view['test'], current=view['current'],
            finished=view['finished'], steps=[dict(id=s['id'], status=s['status'],
                runs=[dict(ok=r['ok'], at_utc=r['at_utc'],
                    checks=[dict(id=x.get('id'), status=x.get('status')) for x in r.get('details', {}).get('checks', [])])
                    for r in runs[s['id']]]) for s in view['steps']],
            deviations=[dict(kind=d.get('kind'), step=d.get('step'), at_utc=d.get('at_utc')) for d in session.data['deviations']]), indent=2)
        for name in ('rootfs-prepared.json', 'rootfs-post-capture.json'):
            p = session.dir / name
            if p.exists():
                r = json.loads(p.read_text(encoding='utf-8'))
                files[name] = json.dumps({k: r.get(k) for k in ('phase','verdict','counts','policy','coverage')}, indent=2)
    if disk_view is not None:
        files['disks.json'] = json.dumps(dict(status=disk_view.get('status'), stage=disk_view.get('stage'),
            candidate_present=bool(disk_view.get('card')), rejected_count=len(disk_view.get('rejected', []))), indent=2)
    log = data_dir / 'logs' / 'lab.log'
    if log.exists():
        lines = log.read_text(encoding='utf-8', errors='replace').splitlines()[-2000:]
        files['lab.log'] = '\n'.join(lines)
    ck = data_dir / 'cache'
    if ck.exists():
        sizes = [p.stat().st_size for p in ck.rglob('*') if p.is_file()]
        files['cache-listing.json'] = json.dumps(dict(files=len(sizes), bytes=sum(sizes)), indent=1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, scrub(text))
        z.writestr('README.txt', 'ATM7039S lab diagnostic bundle. Raw captures and firmware are excluded. Redaction is best-effort; '
                                 'logs and error messages can contain unexpected private information. Review every file before sharing.\n')
    tmp = path.with_name(path.name + '.partial')
    tmp.write_bytes(buf.getvalue())
    os.replace(tmp, path)
    return path
