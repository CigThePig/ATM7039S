"""Start the ATM7039S lab: set up a private Python environment once, then open the lab.

Standard library only, so it runs on a fresh Python. It never needs administrator rights:
the environment lives in .venv-lab inside the project folder. It is started by
ATM7039S-Lab.cmd (Windows, double-click) or start-lab.sh (Linux/macOS).
"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / '.venv-lab'
REQ = ROOT / 'requirements-lab.txt'
LOG = ROOT / 'lab-data' / 'logs' / 'setup.log'


def say(msg):
    print(msg, flush=True)


def venv_python():
    return VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main():
    if sys.version_info < (3, 11):
        say('This lab needs Python 3.11 or newer. You have ' + sys.version.split()[0] + '.\n'
            'Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), then start the lab again.')
        return 2
    LOG.parent.mkdir(parents=True, exist_ok=True)
    want = hashlib.sha256(REQ.read_bytes() + sys.version.encode()).hexdigest()
    stamp = VENV / 'lab-requirements.sha256'
    py = venv_python()
    if not py.exists() or not stamp.exists() or stamp.read_text().strip() != want:
        say('Setting up the lab (one time, about a minute). Nothing is installed outside this folder.')
        try:
            if not py.exists():
                venv.EnvBuilder(with_pip=True, clear=True).create(VENV)
            with open(LOG, 'a', encoding='utf-8') as log:
                cmd = [str(py), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '-r', str(REQ)]
                say('  installing helper libraries…')
                r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'PYTHONUTF8': '1'})
            if r.returncode:
                say(f'Setting up the helper libraries failed. Details are in {LOG}.\n'
                    'Check the internet connection and start the lab again. If it fails twice, send that file.')
                return 1
            stamp.write_text(want)
            say('  done.')
        except OSError as e:
            say(f'Could not create the lab environment in {VENV}: {e}\n'
                'Move the project folder somewhere you can write to (for example Documents) and try again.')
            return 1
    env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONPATH': str(ROOT / 'tools')}
    return subprocess.call([str(py), '-X', 'utf8', '-m', 'v3lab', *sys.argv[1:]], cwd=str(ROOT), env=env)


if __name__ == '__main__':
    raise SystemExit(main())
