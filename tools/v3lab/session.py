"""Persistent hardware-test session: one JSON file per session, written atomically.

A session is a fixed list of steps. Each step is one of
    computer  - the lab does the work; it can always be re-run safely
    physical  - only a person can do it; the lab records the operator's confirmation
                of each checklist line, with the computer's clock time, and never infers
                that a physical action happened because a computer step succeeded
    review    - a decision the operator makes from information the lab shows

Steps unlock strictly in order. A failed computer step blocks the next one until it is
re-run and passes. Going back to an earlier step is allowed only with a reason, which is
kept in the session's deviation list.
"""
import datetime
import secrets
import time
from pathlib import Path

from . import VERSION
from .store import atomic_write_json, read_json, StoreError

FORMAT = 2


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# The V3 workflow. 'checklist' lines are confirmed one by one by the operator.
V3_STEPS = [
    dict(id='computer', kind='computer', title='Check this computer',
         short='Checks Python, the helper libraries, free space and the internet connection.'),
    dict(id='firmware', kind='computer', title='Download and check the firmware',
         short='Downloads Koriki v1.0 (about 890 MB) once, checks it and unpacks it. Resumes if interrupted.'),
    dict(id='insert-blank', kind='physical', title='Insert the spare card',
         checklist=['The working GarlicOS card and the failing factory card are put away, out of reach.',
                    'I marked the spare microSD card (for example, keep it in a labelled case) and it is in this computer\'s card reader.',
                    'No other memory card or USB stick is plugged in.']),
    dict(id='flash', kind='physical', title='Write Koriki to the spare card',
         checklist=['balenaEtcher showed "Flash Complete!" for the disk the lab named.',
                    'I took the card out and put it back into the computer.']),
    dict(id='check-fresh', kind='computer', title='Check the freshly written card',
         short='Reads the card (never writes): boot files, root filesystem and boot loader must match the firmware exactly.'),
    dict(id='first-boot', kind='physical', title='First boot on the handheld',
         checklist=['I ejected the card from this computer (Safely Remove / Eject).',
                    'The card is in slot TF1 of the RG35XX. Slot TF2 is empty.',
                    'The charging cable is NOT connected.',
                    'I switched the handheld on and waited until the game menu appeared (first boot takes a few minutes).',
                    'I shut it down with Volume Up + Power together, waited until the screen AND power indicator went off, then waited another 10 seconds.',
                    'I put that same marked spare card back in the computer. I did not use a long power hold or swap cards.']),
    dict(id='check-prepared', kind='computer', title='Check the card after its first boot',
         short='Copies the card\'s system files to this computer and checks that only the expected first-boot changes happened.'),
    dict(id='install-script', kind='computer', title='Put the capture script on the card',
         short='Copies device/capture.sh to SHARE/roms/ports/ATM7039S-capture.sh and checks the copy. This is the only file the lab writes to the card.',
         confirm='I confirm the marked spare card is inserted and will not remove it during the copy'),
    dict(id='capture', kind='physical', title='Run the capture on the handheld',
         checklist=['I ejected the card from this computer.',
                    'The card is in TF1, TF2 is empty, the charging cable is NOT connected.',
                    'I switched the handheld on, went to the SimpleMenu section group "apps and games", and opened GAMES.',
                    'I started ATM7039S-capture once, and the screen said the capture finished.',
                    'I shut it down with Volume Up + Power together, waited until the screen AND power indicator went off, then waited another 10 seconds.',
                    'I put the same marked spare card back into this computer. No forced shutdown or second capture occurred.']),
    dict(id='collect', kind='computer', title='Collect and check the results',
         short='Copies the capture folder to a private folder on this computer, verifies every file and analyses it.'),
    dict(id='postflight', kind='computer', title='Check the card after the capture',
         short='Compares the card with the checked state from before the capture.'),
    dict(id='done', kind='review', title='Finished',
         short='Results are saved privately. A redacted summary is ready to share.'),
]


class SessionError(RuntimeError):
    pass


class Session:
    def __init__(self, path, data):
        self.path, self.data = Path(path), data

    # ---- lifecycle
    @classmethod
    def create(cls, root_dir, test='V3', firmware='koriki-v1.0-release', capture_version=None):
        sid = time.strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(3)
        steps = [dict(id=s['id'], status='pending', runs=[], confirmations=[]) for s in V3_STEPS]
        steps[0]['status'] = 'ready'
        data = dict(format=FORMAT, id=sid, test=test, firmware=firmware, capture_version=capture_version,
                    created_utc=now_utc(), lab_version=VERSION, salt=secrets.token_hex(16), steps=steps,
                    deviations=[], card=None, baselines={}, outputs={}, notes=[])
        s = cls(Path(root_dir) / sid / 'session.json', data)
        s.save()
        return s

    @classmethod
    def load(cls, path):
        data = read_json(path)
        if not data or data.get('format') != FORMAT:
            raise SessionError(f'{path} is not a session this lab version understands')
        ids = [s['id'] for s in data['steps']]
        if ids != [s['id'] for s in V3_STEPS]:
            raise SessionError('this session was made by a different lab version; start a new one (the old one is kept)')
        if data.get('lab_version') != VERSION:
            data.setdefault('notes', []).append(f"{now_utc()} reopened with lab {VERSION} (created with {data.get('lab_version')})")
            data['lab_version'] = VERSION
        return cls(path, data)

    @classmethod
    def latest(cls, root_dir):
        root_dir = Path(root_dir)
        if not root_dir.is_dir():
            return None
        found = sorted(p for p in root_dir.glob('*/session.json'))
        for p in reversed(found):
            try:
                s = cls.load(p)
            except (SessionError, StoreError):
                continue
            if not s.finished:
                return s
        return None

    def save(self):
        atomic_write_json(self.path, self.data)

    @property
    def dir(self):
        return self.path.parent

    @property
    def finished(self):
        return self.step('done')['status'] == 'complete'

    # ---- steps
    def step(self, sid):
        for s in self.data['steps']:
            if s['id'] == sid:
                return s
        raise SessionError(f'unknown step {sid}')

    @staticmethod
    def spec(sid):
        return next(s for s in V3_STEPS if s['id'] == sid)

    def current(self):
        for s in self.data['steps']:
            if s['status'] != 'complete':
                return s
        return self.data['steps'][-1]

    def _require_current(self, sid):
        cur = self.current()
        if cur['id'] != sid:
            raise SessionError(f"'{self.spec(sid)['title']}' is not the current step; the current step is "
                               f"'{self.spec(cur['id'])['title']}'")

    def record_run(self, sid, ok, summary, details=None, blocking_reason=None):
        """Result of a computer step. ok=False blocks progress until a later run passes."""
        self._require_current(sid)
        if self.spec(sid)['kind'] != 'computer':
            raise SessionError('a physical step can only be completed by the operator confirming it')
        st = self.step(sid)
        st['runs'].append(dict(at_utc=now_utc(), ok=bool(ok), summary=summary, details=details or {},
                               blocking_reason=blocking_reason))
        st['status'] = 'complete' if ok else 'blocked'
        if ok:
            self._unlock_next(sid)
        self.save()

    def confirm(self, sid, answers):
        """Physical step: answers is a list of booleans, one per checklist line, in order."""
        self._require_current(sid)
        spec = self.spec(sid)
        if spec['kind'] != 'physical':
            raise SessionError('only physical steps are confirmed by the operator')
        lines = spec['checklist']
        if not isinstance(answers, list) or len(answers) != len(lines) or not all(a is True for a in answers):
            missing = [line for i, line in enumerate(lines) if i >= len(answers) or answers[i] is not True] if isinstance(answers, list) else lines
            raise SessionError('every line has to be true before this step is done. Not confirmed: ' +
                               ' | '.join(missing or lines))
        st = self.step(sid)
        st['confirmations'].append(dict(at_utc=now_utc(), lines=lines, source='operator',
                                        note='confirmed by the operator in the lab; not observed by the computer'))
        st['status'] = 'complete'
        self._unlock_next(sid)
        self.save()

    def complete_review(self, sid):
        self._require_current(sid)
        if self.spec(sid)['kind'] != 'review':
            raise SessionError('not a review step')
        st = self.step(sid)
        st['status'] = 'complete'
        st['confirmations'].append(dict(at_utc=now_utc(), source='operator'))
        self.save()

    def _unlock_next(self, sid):
        ids = [s['id'] for s in self.data['steps']]
        i = ids.index(sid)
        if i + 1 < len(ids) and self.data['steps'][i + 1]['status'] == 'pending':
            self.data['steps'][i + 1]['status'] = 'ready'

    def go_back(self, sid, reason):
        """Re-open an earlier step (and everything after it). The reason is kept as a deviation."""
        if not reason or len(reason.strip()) < 5:
            raise SessionError('say briefly why you are going back (it is kept with the results)')
        ids = [s['id'] for s in self.data['steps']]
        if sid not in ids:
            raise SessionError(f'unknown step {sid}')
        i = ids.index(sid)
        if i > ids.index(self.current()['id']):
            raise SessionError('you can only go back, not skip ahead')
        # Once capture is confirmed (or the capture step is current), going back
        # could lead to a second launch. Preserve the session; do not replay it.
        capture_i = ids.index('capture')
        if i <= capture_i and ids.index(self.current()['id']) >= capture_i:
            raise SessionError('capture may already have been launched; do not repeat it in this session. Preserve the card and seek review.')
        old = dict(at_utc=now_utc(), step=sid, steps=[dict(s) for s in self.data['steps'][i:]],
                   baselines=dict(self.data['baselines']), outputs=dict(self.data['outputs']), card=self.data['card'])
        self.data.setdefault('history', []).append(old)
        for st in self.data['steps'][i:]:
            st.update(status='pending', runs=[], confirmations=[])
        for key, owner in {'fresh':'check-fresh', 'prepared':'check-prepared', 'post-capture':'postflight'}.items():
            if i <= ids.index(owner):
                self.data['baselines'].pop(key, None)
        for key, owner in {'firmware_image':'firmware', 'captures_before':'install-script', 'capture_private':'collect',
                           'summary':'collect', 'capture_state':'collect'}.items():
            if i <= ids.index(owner):
                self.data['outputs'].pop(key, None)
        if i <= ids.index('insert-blank'):
            self.data['card'] = None
        self.data['steps'][i]['status'] = 'ready'
        self.data['deviations'].append(dict(at_utc=now_utc(), kind='went-back', step=sid, reason=reason.strip()))
        self.save()

    def add_deviation(self, kind, text):
        self.data['deviations'].append(dict(at_utc=now_utc(), kind=kind, text=text))
        self.save()

    def view(self):
        """Public, UI-friendly description (no salt)."""
        steps = []
        for st in self.data['steps']:
            spec = self.spec(st['id'])
            last = st['runs'][-1] if st['runs'] else None
            steps.append(dict(id=st['id'], kind=spec['kind'], title=spec['title'], short=spec.get('short'),
                              checklist=spec.get('checklist'), confirm=spec.get('confirm'), status=st['status'],
                              last_summary=last and last['summary'], last_ok=last and last['ok'],
                              blocking_reason=last and last.get('blocking_reason'),
                              confirmed_utc=st['confirmations'][-1]['at_utc'] if st['confirmations'] else None))
        return dict(id=self.data['id'], test=self.data['test'], created_utc=self.data['created_utc'],
                    current=self.current()['id'], finished=self.finished, steps=steps,
                    deviations=self.data['deviations'], outputs=self.data['outputs'])
