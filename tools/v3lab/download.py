"""Resumable, verified download and expansion of pinned firmware.

* A download continues from its .partial file (HTTP Range) after the window, the program
  or the computer was closed. The .partial file carries a small sidecar naming the URL,
  size and hash it belongs to, so a partial file for a different input is discarded.
* Nothing is published under the final name until its size and SHA-256 match the pinned
  manifest. A verified file is remembered by (size, mtime) so it is not re-hashed on every
  start; any change to the file forces a full re-check.
* Expansion streams the gzip archive with progress measured in compressed bytes (the
  only total known in advance), checks the exact expanded size and hash, and restarts
  cleanly if interrupted: gzip cannot be resumed mid-stream, and a restart is correct.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from .store import StoreError, atomic_write_json, read_json, require_space, sha256_file

CHUNK = 1024 * 1024


def _marker(path):
    return Path(str(path) + '.verified.json')


def is_verified(path, size, sha):
    """True if path is the pinned file. Uses the cached verification when the file is untouched."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size != size:
        return False
    st = path.stat()
    m = None
    try:
        m = read_json(_marker(path))
    except StoreError:
        m = None
    return bool(m and m.get('sha256') == sha and m.get('size') == size and m.get('mtime_ns') == st.st_mtime_ns)


def mark_verified(path, sha):
    st = Path(path).stat()
    atomic_write_json(_marker(path), dict(sha256=sha, size=st.st_size, mtime_ns=st.st_mtime_ns))


def verify_existing(path, size, sha, job=None):
    path = Path(path)
    if is_verified(path, size, sha):
        return True
    if not path.is_file() or path.stat().st_size != size:
        return False
    if sha256_file(path, job) == sha:
        mark_verified(path, sha)
        return True
    return False


def download(url, dest, size, sha, job=None, opener=urllib.request.urlopen, timeout=60):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if verify_existing(dest, size, sha, job):
        return dict(status='reused', path=str(dest))
    if dest.exists():
        bad = dest.with_name(dest.name + '.rejected')
        os.replace(dest, bad)
    part = dest.with_name(dest.name + '.partial')
    side = Path(str(part) + '.json')
    ident = dict(url=url, size=size, sha256=sha)
    try:
        prev = read_json(side)
    except StoreError:
        prev = None
    if part.exists() and (prev != ident or part.stat().st_size > size):
        part.unlink()
    atomic_write_json(side, ident)
    have = part.stat().st_size if part.exists() else 0
    require_space(dest.parent, size - have + 64 * 2**20, 'the firmware download')
    if job:
        job.start_phase('downloading the firmware', size, 'bytes')
        job.done = have
        job.message = f'continuing from {have // 2**20} MiB' if have else ''
    if have < size:
        req = urllib.request.Request(url, headers={'User-Agent': 'ATM7039S-lab', **({'Range': f'bytes={have}-'} if have else {})})
        try:
            resp = opener(req, timeout=timeout)
        except urllib.error.URLError as e:
            raise StoreError(f'could not reach the download server ({e.reason}); the {have // 2**20} MiB already downloaded are kept') from e
        with resp:
            code = getattr(resp, 'status', None) or resp.getcode()
            mode = 'ab'
            if have and code != 206:
                have, mode = 0, 'wb'      # server ignored Range: start again from zero
                if job:
                    job.done = 0
            with open(part, mode) as out:
                while True:
                    if job:
                        job.checkpoint()
                    b = resp.read(CHUNK)
                    if not b:
                        break
                    out.write(b)
                    have += len(b)
                    if have > size:
                        raise StoreError('the server sent more data than the pinned file has; the download was discarded')
                    if job:
                        job.advance(len(b), nbytes=len(b))
                out.flush()
                os.fsync(out.fileno())
        if have != size:
            raise StoreError(f'the download stopped at {have // 2**20} of {size // 2**20} MiB; start again to continue')
    if job:
        job.message = 'checking the downloaded file'
    digest = sha256_file(part, job)
    if digest != sha:
        part.unlink()
        raise StoreError('the downloaded file does not match the pinned SHA-256; it was deleted. Try again; '
                         'if it happens twice, the release on the server has changed and must not be used')
    os.replace(part, dest)
    side.unlink(missing_ok=True)
    mark_verified(dest, sha)
    return dict(status='downloaded', path=str(dest))


class _Counting:
    def __init__(self, f, job):
        self.f, self.job = f, job

    def read(self, n=-1):
        b = self.f.read(n)
        if self.job and b:
            self.job.advance(len(b), nbytes=len(b))
        return b

    def __getattr__(self, k):
        return getattr(self.f, k)


def expand_gzip(archive, dest, size, sha, job=None, compressed_size=None):
    dest = Path(dest)
    if verify_existing(dest, size, sha, job):
        return dict(status='reused', path=str(dest))
    require_space(dest.parent, size + 64 * 2**20, 'the unpacked firmware image')
    part = dest.with_name(dest.name + '.partial')
    part.unlink(missing_ok=True)
    h = hashlib.sha256()
    total = 0
    if job:
        job.start_phase('unpacking the firmware', compressed_size or Path(archive).stat().st_size, 'bytes')
    try:
        with open(archive, 'rb') as raw:
            src = gzip.GzipFile(fileobj=_Counting(raw, job), mode='rb')
            with open(part, 'wb') as out:
                while True:
                    if job:
                        job.checkpoint()
                    b = src.read(CHUNK)
                    if not b:
                        break
                    total += len(b)
                    if total > size:
                        raise StoreError('the archive unpacks to more data than the pinned image')
                    h.update(b)
                    out.write(b)
                out.flush()
                os.fsync(out.fileno())
        if total != size or h.hexdigest() != sha:
            raise StoreError('the unpacked image does not match the pinned size and SHA-256')
        os.replace(part, dest)
        mark_verified(dest, sha)
        return dict(status='expanded', path=str(dest))
    except BaseException:
        part.unlink(missing_ok=True)
        raise


def manifest_entry(root, source='koriki-v1.0-release'):
    items = json.loads((Path(root) / 'evidence/firmware/acquisitions.json').read_text(encoding='utf-8'))
    return next(x for x in items if x['source'] == source)
