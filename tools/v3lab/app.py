"""The lab controller and its local web interface.

The interface is a single page served by Python's standard library on 127.0.0.1 only.
Every state-changing request must carry a per-launch random token and a matching Host
header, so other web pages and other computers cannot drive it. Long work runs in one
background thread; the page polls for progress, so the window never freezes and the
computer stays usable.
"""
import http.server
import json
import logging
import logging.handlers
import secrets
import socketserver
import threading
import time
import traceback
from pathlib import Path

from . import VERSION, diagnostics, disks, steps
from .jobs import Cancelled, Job, low_priority
from .session import Session, SessionError, V3_STEPS
from .store import StoreError, instance_lock

FRIENDLY = (StoreError, SessionError, disks.DiscoveryError)


def setup_logging(data):
    (data / 'logs').mkdir(parents=True, exist_ok=True)
    log = logging.getLogger('v3lab')
    target = str((data / 'logs' / 'lab.log').resolve())
    for h in list(log.handlers):
        if getattr(h, 'baseFilename', None) != target:
            log.removeHandler(h)
            h.close()
    if not log.handlers:
        h = logging.handlers.RotatingFileHandler(target, maxBytes=2_000_000, backupCount=3, encoding='utf-8')
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


class Lab:
    def __init__(self, root, data=None, env=None):
        self.root = Path(root)
        self.data = Path(data or self.root / 'lab-data')
        self.env = env or steps.Env(root=self.root, data=self.data)
        self.log = setup_logging(self.data)
        self.sessions_dir = self.data / 'sessions'
        self.session = Session.latest(self.sessions_dir)
        self.job = None
        self.thread = None
        self.problem = None
        self.last_lines = []
        self.mode = 'quiet'
        self.priority_note = None
        self._lock = threading.Lock()

    def close(self):
        """Release the log file (Windows keeps open files locked)."""
        for h in list(self.log.handlers):
            h.close()
            self.log.removeHandler(h)

    # ---- state for the page
    def state(self):
        s = self.session
        job = self.job.snapshot() if self.job else None
        busy = bool(self.thread and self.thread.is_alive())
        extra = {}
        if s and s.current()['id'] == 'flash':
            extra['flash'] = self.flash_info()
        return dict(version=VERSION, session=s.view() if s else None, job=job, busy=busy, problem=self.problem,
                    lines=self.last_lines, mode=self.mode, extra=extra, priority=self.priority_note)

    def flash_info(self):
        a, gz, img = steps._image_paths(self.env)
        removable = []
        try:
            for d in self.env.inventory():
                if not (d['is_boot'] or d['is_system']) and (d['bus'] in disks.REMOVABLE_BUSES or d.get('removable')):
                    removable.append(dict(model=d.get('model'), size_gb=round((d.get('size') or 0) / 1e9, 1), bus=d['bus']))
        except Exception as e:  # listing is advisory here; Etcher shows the authoritative list
            self.log.warning('flash listing failed: %s', e)
        return dict(image=str(img), image_ready=img.exists(), removable=removable,
                    target_unique=len(removable) == 1 and img.exists())

    # ---- actions
    def new_session(self):
        with self._lock:
            if self.thread and self.thread.is_alive():
                raise SessionError('wait for the current task to finish or stop it first')
            cv = None
            try:
                cv = next(v['version'] for v in json.loads((self.root / 'device/capture-versions.json').read_text(encoding='utf-8'))
                          if v['status'] == 'current')
            except Exception:
                pass
            self.session = Session.create(self.sessions_dir, capture_version=cv)
            self.problem, self.last_lines = None, []
            self.log.info('new session %s', self.session.data['id'])

    def run(self, step_id):
        with self._lock:
            if not self.session:
                raise SessionError('start a session first')
            if self.thread and self.thread.is_alive():
                raise SessionError('the lab is already working on something')
            cur = self.session.current()
            if cur['id'] != step_id:
                raise SessionError('that is not the current step')
            if Session.spec(step_id)['kind'] != 'computer':
                raise SessionError('this step is done by you, not the computer')
            self.problem, self.last_lines = None, []
            self.job = Job(Session.spec(step_id)['title'], self.mode)
            self.thread = threading.Thread(target=self._work, args=(step_id, self.job), daemon=True)
            self.thread.start()

    def _work(self, step_id, job):
        if self.priority_note is None:
            self.priority_note = low_priority()
        self.log.info('step %s started', step_id)
        try:
            r = self.env.runner(step_id)(self.env, self.session, job)
            self.session.record_run(step_id, r.ok, r.summary, r.details, r.blocking_reason)
            self.last_lines = r.lines
            job.state = 'finished'
            if not r.ok:
                self.problem = dict(title=r.summary, what=r.blocking_reason or r.summary,
                                    lost='Nothing was lost. Completed downloads, copies and checks are kept.',
                                    safe='Do not boot or rewrite the card because of this message. '
                                         'Fix what it says, then press Try again.',
                                    next='Read the explanation above. If it is unclear, press "Make a diagnostic bundle" and send it.')
            self.log.info('step %s finished ok=%s: %s', step_id, r.ok, r.summary)
        except Cancelled:
            job.state = 'cancelled'
            self.problem = dict(title='Stopped.', what='You stopped this task.',
                                lost='Nothing was lost: finished parts are saved and will be reused.',
                                safe='It is safe to continue later, even after restarting the computer.',
                                next='Press Start when you want to continue.')
            self.log.info('step %s cancelled', step_id)
        except FRIENDLY as e:
            job.state = 'failed'
            self._fail(step_id, str(e), known=True)
        except Exception as e:  # unexpected: keep a full traceback in the log, show a plain message
            job.state = 'failed'
            self.log.error('step %s crashed:\n%s', step_id, traceback.format_exc())
            self._fail(step_id, f'{type(e).__name__}: {e}', known=False)

    def _fail(self, step_id, text, known):
        try:
            self.session.record_run(step_id, False, 'Could not finish.', {}, text)
        except SessionError:
            pass
        bundle = None
        if not known:
            try:
                for h in self.log.handlers:
                    h.flush()
                bundle = str(diagnostics.build(self.data, self.session, error=text))
            except Exception:
                self.log.error('bundle failed:\n%s', traceback.format_exc())
        self.problem = dict(title='Could not finish this step.', what=text,
                            lost=('The capture-script copy may have created a partial file or directory. Preserve the card and inspect the result.'
                                  if step_id == 'install-script' else 'This step did not request a card write. Finished local work is kept.'),
                            safe=('Do not boot the card until the script copy is verified.' if step_id == 'install-script'
                                  else 'Preserve the card; retry this computer-side check after fixing the problem.'),
                            next='If the message does not say what to do, send the diagnostic bundle.', bundle=bundle)

    def confirm(self, step_id, answers):
        if step_id == 'flash':
            # The manual flash step asks the operator to unplug/reinsert the card.
            # Do not advance if more than one candidate remains or the image vanished.
            if not self.flash_info()['target_unique']:
                raise SessionError('exactly one removable disk and the verified image are required; do not flash')
        self.session.confirm(step_id, answers)
        self.problem, self.last_lines = None, []
        self.log.info('step %s confirmed by operator', step_id)

    def finish(self):
        self.session.complete_review('done')

    def go_back(self, step_id, reason):
        if self.thread and self.thread.is_alive():
            raise SessionError('stop the running task first')
        self.session.go_back(step_id, reason)
        self.problem = None

    def control(self, what):
        if what == 'mode-fast':
            self.mode = 'fast'
        elif what == 'mode-quiet':
            self.mode = 'quiet'
        if self.job:
            {'cancel': self.job.cancel, 'pause': self.job.pause, 'resume': self.job.resume}.get(what, lambda: None)()
            self.job.set_mode(self.mode)

    def bundle(self):
        view = None
        try:
            view = disks.public_view(disks.identify(self.env.inventory()))
        except Exception as e:
            view = dict(error=str(e))
        return str(diagnostics.build(self.data, self.session, disk_view=view))


PAGE = (Path(__file__).with_name('ui.html'))


def make_handler(lab, token, port):
    class H(http.server.BaseHTTPRequestHandler):
        server_version = 'ATM7039S-lab'

        def log_message(self, fmt, *args):
            lab.log.debug('http ' + fmt, *args)

        def _host_ok(self):
            return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

        def _send(self, code, body, ctype='application/json'):
            data = body if isinstance(body, bytes) else json.dumps(body).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', ctype + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, dict(error='forbidden'))
            if self.path.split('?')[0] == '/':
                html = PAGE.read_text(encoding='utf-8').replace('__TOKEN__', token)
                return self._send(200, html.encode('utf-8'), 'text/html')
            if self.path == '/api/state':
                return self._send(200, lab.state())
            return self._send(404, dict(error='not found'))

        def do_POST(self):
            if not self._host_ok() or self.headers.get('X-Lab-Token') != token:
                return self._send(403, dict(error='forbidden'))
            try:
                n = min(int(self.headers.get('Content-Length') or 0), 65536)
                body = json.loads(self.rfile.read(n) or b'{}')
                act = self.path.removeprefix('/api/')
                if act == 'new-session':
                    lab.new_session()
                elif act == 'run':
                    lab.run(body['step'])
                elif act == 'confirm':
                    lab.confirm(body['step'], body['answers'])
                elif act == 'finish':
                    lab.finish()
                elif act == 'back':
                    lab.go_back(body['step'], body.get('reason', ''))
                elif act == 'control':
                    lab.control(body['what'])
                elif act == 'bundle':
                    return self._send(200, dict(path=lab.bundle()))
                else:
                    return self._send(404, dict(error='unknown action'))
                return self._send(200, lab.state())
            except FRIENDLY as e:
                return self._send(409, dict(error=str(e)))
            except (KeyError, ValueError, TypeError) as e:
                return self._send(400, dict(error=f'bad request: {e}'))
    return H


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def serve(lab, port=0, open_browser=True, ready=None):
    token = secrets.token_urlsafe(24)
    with instance_lock(lab.data / 'lab.lock'):
        srv = Server(('127.0.0.1', port), None)
        real = srv.server_address[1]
        srv.RequestHandlerClass = make_handler(lab, token, real)
        url = f'http://127.0.0.1:{real}/'
        lab.log.info('lab %s listening on %s', VERSION, url)
        if ready:
            ready(url, token, srv)
        if open_browser:
            import webbrowser
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        print(f'ATM7039S lab is open in your web browser: {url}\nKeep this window open while you work. '
              'Close it (or press Ctrl+C) when you are finished; your progress is saved.', flush=True)
        try:
            srv.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            pass
        finally:
            if lab.job:
                lab.job.cancel()
            srv.server_close()
            time.sleep(0.2)
