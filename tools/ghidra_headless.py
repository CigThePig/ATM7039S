#!/usr/bin/env python3
"""Run Ghidra headless on one component and export a publishable summary.

Imports a raw (BinaryLoader) or ELF component into a throw-away project outside
the repository, optionally seeds entry points, runs auto-analysis and writes
function extents, call edges and window constants via ExportAnalysis.java.
No decompiler output or disassembly text is written. Ghidra is located through
``--ghidra`` or ``$GHIDRA_INSTALL_DIR``; the version and component hash are
recorded alongside the result.

The supplied load address is an *analysis assumption*; it is stored with the
result so file offsets can always be recovered (offset = address - base).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def command(ghidra, project, component, out, base=None, language='ARM:LE:32:v7', entries=(), window=None, raw=True, timeout=3600):
    cmd = [str(Path(ghidra) / 'support' / 'analyzeHeadless'), str(project), 'p', '-import', str(component),
           '-scriptPath', str(HERE / 'ghidra'), '-deleteProject', '-analysisTimeoutPerFile', str(timeout)]
    if raw:
        if base is None:
            raise ValueError('raw import requires a base address')
        cmd += ['-loader', 'BinaryLoader', '-loader-baseAddr', hex(base), '-processor', language]
    if entries:
        cmd += ['-preScript', 'SeedEntries.java', *entries]
    cmd += ['-postScript', 'ExportAnalysis.java', str(out)]
    if window:
        cmd += [hex(window[0]), hex(window[1])]
    return cmd


def run(ghidra, component, out, base=None, language='ARM:LE:32:v7', entries=(), window=None, raw=True):
    data = component.read_bytes()
    with tempfile.TemporaryDirectory(prefix='atm-ghidra-') as tmp:
        cmd = command(ghidra, tmp, component, out, base, language, entries, window, raw)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if proc.returncode or not out.exists():
            raise RuntimeError('Ghidra failed:\n' + proc.stdout[-2000:] + proc.stderr[-2000:])
    result = json.loads(out.read_text())
    result['functions'].sort(key=lambda f: int(f['entry'], 16))
    result.update(component_sha256=hashlib.sha256(data).hexdigest(), component_size=len(data),
                  analysis_base=None if base is None else hex(base), seeded_entries=list(entries),
                  ghidra_install=Path(ghidra).name)
    out.write_text(json.dumps(result, indent=1) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('component', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--ghidra', default=os.environ.get('GHIDRA_INSTALL_DIR'))
    p.add_argument('--base', type=lambda x: int(x, 0))
    p.add_argument('--language', default='ARM:LE:32:v7')
    p.add_argument('--elf', action='store_true', help='use Ghidra ELF loader instead of raw binary')
    p.add_argument('--entry', action='append', default=[], help='hex entry; prefix t: for Thumb')
    p.add_argument('--window', nargs=2, type=lambda x: int(x, 0))
    a = p.parse_args()
    if not a.ghidra:
        raise SystemExit('Ghidra not found: pass --ghidra or set GHIDRA_INSTALL_DIR')
    if not a.component.is_file():
        raise SystemExit('component must be a regular file')
    r = run(a.ghidra, a.component, a.output.resolve(), a.base, a.language, a.entry, a.window, not a.elf)
    print(f"{len(r['functions'])} functions exported")


if __name__ == '__main__':
    main()
