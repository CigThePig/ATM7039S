"""python -m v3lab [open|status|next|confirm|run|bundle] — normally started by ATM7039S-Lab.cmd / start-lab.sh."""
import argparse
import json
from pathlib import Path
import sys

from .app import Lab, serve
from .session import Session, SessionError
from .store import StoreError, instance_lock

ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    p = argparse.ArgumentParser(prog='v3lab', description='ATM7039S hardware test lab (computer side).')
    p.add_argument('command', nargs='?', default='open', choices=['open', 'status', 'run', 'confirm', 'bundle', 'new', 'selftest'])
    p.add_argument('--data', type=Path, help='where the lab keeps its private files (default: lab-data/ in the project)')
    p.add_argument('--port', type=int, default=0)
    p.add_argument('--no-browser', action='store_true')
    a = p.parse_args(argv)
    if sys.platform != 'win32' and not sys.platform.startswith('linux'):
        print('The guided lab supports Windows and Linux only. On macOS use device/V3-STEP-BY-STEP.md.', file=sys.stderr)
        return 2
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    if a.command == 'selftest':
        return selftest()
    data = Path(a.data or ROOT / 'lab-data').resolve()
    try:
        # Lock before Lab.__init__ loads the last session, including for the
        # browser launcher. Every entry point shares the same data-directory lock.
        with instance_lock(data / 'lab.lock'):
            lab = Lab(ROOT, data)
            try:
                return run_locked(a, lab)
            finally:
                lab.stop_and_wait()
                lab.close()
    except (StoreError, SessionError) as e:
        print(str(e), file=sys.stderr)
        return 1


def run_locked(a, lab):
    if a.command == 'open':
        serve(lab, a.port, not a.no_browser, lock_held=True)
        return 0
    if a.command == 'new':
        lab.new_session()
    if not lab.session:
        print('No session yet. Run: python -m v3lab new')
        return 1
    cur = lab.session.current()
    spec = Session.spec(cur['id'])
    if a.command == 'status':
        v = lab.session.view()
        for s in v['steps']:
            mark = {'complete': '[x]', 'blocked': '[!]', 'ready': '[>]'}.get(s['status'], '[ ]')
            print(f"{mark} {s['title']}" + (f"  -- {s['last_summary']}" if s['last_summary'] else ''))
        print('\nNext:', spec['title'])
        for line in spec.get('checklist') or []:
            print('  -', line)
        return 0
    if a.command == 'run':
        if spec.get('confirm') and input(spec['confirm'] + '? (yes/no) ').strip().lower() not in ('y', 'yes'):
            print('No card write requested.')
            return 1
        lab.run(cur['id'])
        lab.thread.join()
        print(json.dumps(dict(problem=lab.problem, lines=lab.last_lines), indent=2))
        return 0 if not lab.problem else 1
    if a.command == 'confirm':
        if spec['kind'] != 'physical':
            print('The current step is done by the computer: python -m v3lab run')
            return 1
        answers = []
        for line in spec['checklist']:
            answers.append(input(f'{line}\n  Is this true? (yes/no) ').strip().lower() in ('y', 'yes'))
        try:
            lab.confirm(cur['id'], answers)
        except SessionError as e:
            print(e)
            return 1
        print('Recorded.')
        return 0
    if a.command == 'bundle':
        print(lab.bundle())
        return 0
    return 0


def selftest():
    """Start-up check used by CI and by the launcher: imports, UI page, disk listing, UTF-8 paths."""
    import importlib
    import tempfile
    from . import VERSION, disks
    for m in ('pyfatfs', 'fs', 'dissect.extfs', 'jsonschema'):
        importlib.import_module(m)
    page = (Path(__file__).with_name('ui.html')).read_text(encoding='utf-8')
    assert '__TOKEN__' in page
    with tempfile.TemporaryDirectory(prefix='lab selftest ü ') as t:
        lab = Lab(ROOT, Path(t))
        lab.new_session()
        assert lab.session.current()['id'] == 'computer'
        lab.close()
    try:
        n = len(disks.collect())
        listing = f'{n} disk(s) listed'
    except Exception as e:  # CI runners may not allow storage queries; report, do not fail
        listing = f'disk listing unavailable here ({type(e).__name__})'
    print(f'v3lab {VERSION} selftest OK: libraries, interface, sessions; {listing}; '
          f'filesystem encoding {sys.getfilesystemencoding()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
