"""Crash-safe local storage: atomic files, single-instance locks, verified hashing and copying.

Rules used everywhere in the lab:
* a result file appears under its final name only after it has been completely written
  and flushed (write to NAME.partial, fsync, os.replace);
* a partial file is never read as an input;
* expensive results are keyed by the SHA-256 of their inputs, so a different card or
  image can never reuse another one's checkpoint.
"""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil

CHUNK = 4 * 1024 * 1024


class StoreError(RuntimeError):
    pass


def atomic_write_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.partial')
    with open(tmp, 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path, obj):
    atomic_write_bytes(path, (json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False) + '\n').encode('utf-8'))


def read_json(path, default=None):
    """Read a JSON file written by atomic_write_json. A corrupt file raises StoreError."""
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeDecodeError) as e:
        raise StoreError(f'{path.name} is damaged ({e}); it was kept, not overwritten') from e


@contextlib.contextmanager
def instance_lock(path):
    """Exclusive, non-blocking lock. The OS releases it if the process dies."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, 'a+b')
    try:
        if f.seek(0, 2) == 0:
            f.write(b'0')
            f.flush()
        if os.name == 'nt':
            import msvcrt
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as e:
                raise StoreError('another copy of the lab is already working on this; close it first') from e
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                raise StoreError('another copy of the lab is already working on this; close it first') from e
        try:
            yield
        finally:
            if os.name == 'nt':
                import msvcrt
                f.seek(0)
                with contextlib.suppress(OSError):
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)
    finally:
        f.close()


def sha256_file(path, job=None, size=None):
    """SHA-256 of a file, reporting bytes to the job and honouring pause/cancel."""
    h = hashlib.sha256()
    path = Path(path)
    total = size if size is not None else path.stat().st_size
    if job:
        job.start_phase(f'checking {path.name}', total, 'bytes')
    with open(path, 'rb') as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
            if job:
                job.advance(len(b), nbytes=len(b))
    return h.hexdigest()


def free_space(path):
    p = Path(path)
    while not p.exists():
        p = p.parent
    return shutil.disk_usage(p).free


def require_space(path, need, what):
    free = free_space(path)
    if free < need:
        raise StoreError(f'not enough free space for {what}: need {need // 2**20:,} MiB, '
                         f'{free // 2**20:,} MiB free on the drive holding {Path(path)}')


def verified_copy(src_open, dest, size, expected_sha=None, job=None, label='copy', stamp=None):
    """Copy a stream of known size to dest; publish only after the bytes are verified.

    src_open: callable returning a binary file object positioned at 0.
    stamp: optional callable returning an identity of the source (size, mtime, ...)
           compared before and after, so a card that is swapped or rewritten during the
           copy is detected instead of silently mixed.
    """
    dest = Path(dest)
    require_space(dest.parent, size + 64 * 2**20, label)
    tmp = dest.with_name(dest.name + '.partial')
    before = stamp() if stamp else None
    h = hashlib.sha256()
    done = 0
    if job:
        job.start_phase(label, size, 'bytes')
    try:
        with src_open() as src, open(tmp, 'wb') as out:
            while done < size:
                b = src.read(min(CHUNK, size - done))
                if not b:
                    raise StoreError(f'{label}: the source ended after {done:,} of {size:,} bytes '
                                     '(card removed or file truncated?)')
                out.write(b)
                h.update(b)
                done += len(b)
                if job:
                    job.advance(len(b), nbytes=len(b))
            if src.read(1):
                raise StoreError(f'{label}: the source is larger than expected')
            out.flush()
            os.fsync(out.fileno())
        if stamp and stamp() != before:
            raise StoreError(f'{label}: the source changed while it was being copied; nothing was kept')
        digest = h.hexdigest()
        if expected_sha and digest != expected_sha:
            raise StoreError(f'{label}: SHA-256 {digest} does not match the expected {expected_sha}')
        if job:
            job.message = 're-reading the local copy to confirm it was written correctly'
        if sha256_file(tmp) != digest:
            raise StoreError(f'{label}: the local copy failed read-back verification (disk problem?)')
        os.replace(tmp, dest)
        return digest
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise
