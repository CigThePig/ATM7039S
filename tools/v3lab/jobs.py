"""Progress reporting, cooperative cancellation, pause/resume and background throttling.

Every long operation in the lab receives a Job. It reports progress through it and
calls job.checkpoint() regularly: that is where pause, cancel and the low-impact
throttle take effect. A Job never guesses a total it does not know; ETA and percent
are only reported when the total is known.
"""
import os
import sys
import threading
import time


class Cancelled(Exception):
    """The operator (or a test) asked the operation to stop. Completed work is kept."""


MODES = {
    # Quiet: keep the computer usable (Lightroom, browsers). Sleep after each chunk so the
    # disk and one CPU core are never saturated. Fast: no throttle beyond low priority.
    'quiet': dict(max_bytes_per_s=40 * 1024 * 1024, yield_s=0.002),
    'fast': dict(max_bytes_per_s=None, yield_s=0.0),
}


class Job:
    def __init__(self, name, mode='quiet', clock=time.monotonic, sleep=time.sleep):
        self.name = name
        self.mode = mode if mode in MODES else 'quiet'
        self._clock, self._sleep = clock, sleep
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self.phase = 'starting'
        self.done = 0
        self.total = None
        self.unit = 'items'
        self.started = self._clock()
        self._window = []          # (time, done) samples for the rate estimate
        self.state = 'running'     # running | paused | cancelling | finished | failed | cancelled
        self.message = ''
        self.last_beat = self.started
        self._throttle_t0 = self.started
        self._throttle_bytes = 0

    # ---- operator controls (any thread)
    def cancel(self):
        self._cancel.set()
        self._resume.set()
        with self._lock:
            if self.state in ('running', 'paused'):
                self.state = 'cancelling'

    def pause(self):
        with self._lock:
            if self.state == 'running':
                self._resume.clear()
                self.state = 'paused'

    def resume(self):
        with self._lock:
            if self.state == 'paused':
                self.state = 'running'
        self._resume.set()

    def set_mode(self, mode):
        if mode in MODES:
            self.mode = mode

    @property
    def cancelled(self):
        return self._cancel.is_set()

    # ---- worker side
    def start_phase(self, phase, total=None, unit='items'):
        with self._lock:
            self.phase, self.total, self.unit, self.done = phase, total, unit, 0
            self._window = [(self._clock(), 0)]
        self.checkpoint()

    def advance(self, n=1, nbytes=0):
        with self._lock:
            self.done += n
            now = self._clock()
            self.last_beat = now
            self._window.append((now, self.done))
            if len(self._window) > 64:
                self._window = self._window[-64:]
        if nbytes:
            self._throttle(nbytes)
        self.checkpoint()

    def checkpoint(self):
        """Honour pause and cancel. Called between units of work, never mid-write."""
        if self._cancel.is_set():
            raise Cancelled(self.name)
        if not self._resume.is_set():
            self._resume.wait()
            if self._cancel.is_set():
                raise Cancelled(self.name)
        self.last_beat = self._clock()

    def _throttle(self, nbytes):
        cfg = MODES[self.mode]
        if cfg['yield_s']:
            self._sleep(cfg['yield_s'])
        cap = cfg['max_bytes_per_s']
        if not cap:
            return
        self._throttle_bytes += nbytes
        elapsed = self._clock() - self._throttle_t0
        ahead = self._throttle_bytes / cap - elapsed
        if ahead > 0:
            self._sleep(min(ahead, 1.0))
        if elapsed > 5:
            self._throttle_t0, self._throttle_bytes = self._clock(), 0

    # ---- reporting
    def rate(self):
        with self._lock:
            w = list(self._window)
        if len(w) < 2 or w[-1][0] - w[0][0] <= 0:
            return None
        return (w[-1][1] - w[0][1]) / (w[-1][0] - w[0][0])

    def snapshot(self):
        r = self.rate()
        with self._lock:
            total, done = self.total, self.done
            pct = (100.0 * done / total) if total else None
            eta = ((total - done) / r) if (total and r and r > 0) else None
            return dict(name=self.name, phase=self.phase, done=done, total=total, unit=self.unit,
                        percent=None if pct is None else round(min(pct, 100.0), 1),
                        rate_per_s=None if r is None else round(r, 1), eta_s=None if eta is None else round(eta),
                        state=self.state, mode=self.mode, message=self.message,
                        elapsed_s=round(self._clock() - self.started), heartbeat_age_s=round(self._clock() - self.last_beat, 1))


def low_priority():
    """Lower this process's CPU (and, where supported, I/O) priority. Returns a short note."""
    try:
        if sys.platform == 'win32':
            import ctypes
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.GetCurrentProcess.restype = ctypes.c_void_p
            k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            # BELOW_NORMAL_PRIORITY_CLASS; PROCESS_MODE_BACKGROUND_BEGIN would also lower I/O,
            # but Windows applies it only to the calling thread's process in some versions.
            if not k.SetPriorityClass(k.GetCurrentProcess(), 0x4000):
                return 'priority unchanged'
            return 'below-normal CPU priority'
        os.nice(10)
        try:
            import subprocess
            subprocess.run(['ionice', '-c3', '-p', str(os.getpid())], capture_output=True, timeout=5)
        except (OSError, Exception):
            pass
        return 'nice +10'
    except Exception as e:  # never fail an operation because priority could not change
        return f'priority unchanged ({type(e).__name__})'


def human_bytes(n):
    if n is None:
        return '?'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(n) < 1024 or unit == 'TiB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024
