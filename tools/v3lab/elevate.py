"""The single operation that needs administrator rights on Windows: reading the card's first 4 MiB.

The boot loader and U-Boot sit outside every partition, so Windows only lets an
administrator read them. The lab starts this module in a separate, elevated Python
process (one UAC prompt), which re-checks that the disk is a removable, non-system disk,
reads 4 MiB read-only, writes them to a private file and exits. The main lab never runs
elevated and nothing is written to the card.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def _check_disk(number, expected_size=None):
    from . import disks
    found = disks.identify(disks.collect())
    if (found.get('status') != 'found' or found['card']['number'] != number or
            (expected_size is not None and found['card']['size'] != expected_size)):
        raise SystemExit('refusing: the uniquely identified Koriki card is no longer at this disk number')


def helper_main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--disk', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--size', type=int)
    a = p.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import card_boot_read
    status = a.out.with_suffix('.status.json')
    try:
        _check_disk(a.disk, a.size)
        data = card_boot_read.read_windows_disk(a.disk)
        tmp = a.out.with_name(a.out.name + '.partial')
        tmp.write_bytes(data)
        os.replace(tmp, a.out)
        status.write_text(json.dumps(dict(ok=True)), encoding='utf-8')
    except BaseException as e:  # report every failure to the unprivileged lab
        status.write_text(json.dumps(dict(ok=False, error=f'{type(e).__name__}: {e}')), encoding='utf-8')
        raise


def raw_head(number, timeout=300, expected_size=None):
    """Run the elevated helper and return the 4 MiB it read."""
    work = Path(tempfile.mkdtemp(prefix='atm-raw-'))
    out = work / 'head.bin'
    args = ['-X', 'utf8', '-m', 'v3lab.elevate', '--disk', str(int(number)), '--out', str(out)]
    if expected_size is not None:
        args += ['--size', str(expected_size)]
    tools = str(Path(__file__).resolve().parents[1])
    q = lambda s: "'" + str(s).replace("'", "''") + "'"   # PowerShell single-quoted literal
    # Start-Process joins -ArgumentList with spaces and does not quote, so quote each argument for the
    # child's command line (paths under C:\Users\First Last\ contain spaces).
    ps_args = ','.join(q('"' + a + '"') for a in args)
    cmd = (f"$p = Start-Process -FilePath {q(sys.executable)} -ArgumentList {ps_args} "
           f"-WorkingDirectory {q(tools)} -Verb RunAs -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode")
    try:
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', cmd],
                       capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise OSError('the administrator read did not finish in time') from e
    status = out.with_suffix('.status.json')
    if not status.exists():
        raise OSError('the administrator read was not approved (the Windows prompt was declined or closed)')
    st = json.loads(status.read_text(encoding='utf-8'))
    try:
        if not st.get('ok'):
            raise OSError(st.get('error', 'the administrator read failed'))
        return out.read_bytes()
    finally:
        for f in work.iterdir():
            f.unlink()
        work.rmdir()


if __name__ == '__main__':
    helper_main()
