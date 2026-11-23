#!/usr/bin/env python3
"""Verify and parse a device/capture.sh output directory into structured JSON.

The parser reads ordinary files only. It checks capture integrity, links the
running kernel and device tree to catalogued release components, and extracts
CPU, memory, storage, display and module observations. Interpretations are
labelled hints: turning them into findings requires an observation record
(evidence/observations.json) and human review.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ITEM_LIMIT = 64 * 1024 * 1024
FORMAT_VERSION = 1


# ---------------------------------------------------------------- integrity

def script_allowlist(text):
    """Return the allowlist embedded in a capture.sh text, as a list of lines."""
    m = re.search(r"^ALLOWLIST='(.*?)'$", text, re.S | re.M)
    if not m:
        raise ValueError('capture script has no ALLOWLIST block')
    return [line for line in m.group(1).splitlines() if line]


def known_versions(root=ROOT):
    return json.loads((root / 'device/capture-versions.json').read_text())


def read_info(path):
    info = {}
    for line in path.read_text(errors='replace').splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            info[k] = v
    return info


def read_manifest(path):
    lines = path.read_text(errors='replace').splitlines()
    if not lines or lines[0].split('\t') != ['id', 'kind', 'target', 'status', 'bytes', 'sha256']:
        raise ValueError('manifest.tsv has an unexpected header')
    rows = []
    for n, line in enumerate(lines[1:], 2):
        cells = line.split('\t')
        if len(cells) != 6:
            raise ValueError(f'manifest.tsv line {n} has {len(cells)} cells')
        rows.append(dict(zip(['id', 'kind', 'target', 'status', 'bytes', 'sha256'], cells)))
    return rows


def item_path(capture, row):
    suffix = '.tar' if row['kind'] == 'tree' else '.out'
    name = row['id'] + suffix
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
        raise ValueError('unsafe item name ' + row['id'])
    return capture / 'items' / name


def verify(capture, root=ROOT):
    """Check structure, hashes and allowlist identity. Returns (report, items)."""
    capture = Path(capture)
    errors, warnings = [], []
    for required in ['capture-info.txt', 'allowlist.txt', 'manifest.tsv']:
        if not (capture / required).is_file():
            raise ValueError('capture is missing ' + required)
    if not (capture / 'DONE').is_file():
        warnings.append('DONE marker absent: capture may have been interrupted')
    info = read_info(capture / 'capture-info.txt')
    manifest_bytes = (capture / 'manifest.tsv').read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if info.get('manifest_sha256') not in (None, 'unavailable', manifest_sha):
        errors.append('manifest.tsv hash differs from capture-info.txt')
    rows = read_manifest(capture / 'manifest.tsv')
    recorded = [x for x in (capture / 'allowlist.txt').read_text().splitlines() if x]
    versions = known_versions(root)
    version = next((v for v in versions if v['sha256'] == info.get('script_sha256')), None)
    if version is None:
        errors.append('capture script hash is not a known device/capture.sh version')
    expected = version['allowlist'] if version else script_allowlist((root / 'device/capture.sh').read_text())
    if recorded != expected:
        errors.append('recorded allowlist differs from the known script version')
    if [f"{r['id']}|{r['kind']}|{r['target']}" for r in rows] != recorded:
        errors.append('manifest rows do not match the recorded allowlist order')
    items, files = {}, []
    for row in rows:
        entry = dict(id=row['id'], kind=row['kind'], target=row['target'], status=row['status'])
        path = item_path(capture, row)
        if row['status'] in ('ok', 'error') and path.is_file():
            size = path.stat().st_size
            if size > ITEM_LIMIT:
                errors.append('item exceeds size limit ' + row['id'])
                files.append(entry)
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            entry.update(bytes=size, sha256=digest)
            if row['bytes'] and int(row['bytes']) != size:
                errors.append('size mismatch ' + row['id'])
            if row['sha256'] not in ('', 'unavailable', digest):
                errors.append('hash mismatch ' + row['id'])
            if row['status'] == 'ok':
                items[row['id']] = data
        elif row['status'] == 'ok':
            errors.append('item marked ok but file absent ' + row['id'])
        err = capture / 'items' / (row['id'] + '.err')
        if err.is_file():
            entry['stderr'] = err.read_text(errors='replace')[:2000]
        files.append(entry)
    report = dict(
        capture_version=info.get('capture_version'),
        script_sha256=info.get('script_sha256'),
        script_version_known=version is not None,
        fixture_root=info.get('fixture_root'),
        uid=info.get('uid'),
        started_utc=info.get('started_utc'),
        finished_utc=info.get('finished_utc'),
        manifest_sha256=manifest_sha,
        files=files,
        errors=errors,
        warnings=warnings,
    )
    if info.get('fixture_root', 'none') != 'none':
        warnings.append('capture read a fixture root, not a live system')
    if info.get('uid') not in ('0', None):
        warnings.append('capture ran without root; iomem addresses may be zeroed')
    return report, items


# ---------------------------------------------------------------- parsers

def text(items, key):
    data = items.get(key)
    return None if data is None else data.decode('utf-8', errors='replace')


def cpulist(value):
    """Parse a kernel CPU list such as '0-1,3'. Empty string means no CPUs."""
    value = value.strip()
    cpus = []
    if not value:
        return cpus
    for part in value.split(','):
        if '-' in part:
            a, b = part.split('-', 1)
            a, b = int(a), int(b)
            if b < a:
                raise ValueError('descending CPU range ' + part)
            cpus.extend(range(a, b + 1))
        else:
            cpus.append(int(part))
    return cpus


def cmdline(value):
    tokens = value.split()
    params = {}
    for t in tokens:
        k, _, v = t.partition('=')
        params.setdefault(k, []).append(v if _ else True)
    return dict(raw=value.strip(), tokens=tokens, powersave='powersave' in params,
                maxcpus=params.get('maxcpus'), nr_cpus=params.get('nr_cpus'), mem=params.get('mem'),
                console=params.get('console'))


def cpuinfo(value):
    blocks, common, current = [], {}, None
    for line in value.splitlines():
        if ':' not in line:
            current = None
            continue
        k, v = (x.strip() for x in line.split(':', 1))
        if k == 'processor':
            current = {'processor': int(v)}
            blocks.append(current)
        elif current is not None:
            current[k] = v
        else:
            common[k] = v
    parts = sorted({b.get('CPU part') for b in blocks if b.get('CPU part')})
    return dict(processors=len(blocks), cpu_parts=parts, common=common, per_cpu=blocks)


def meminfo(value):
    out = {}
    for line in value.splitlines():
        m = re.match(r'(\S+):\s+(\d+)(?:\s+kB)?', line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def iomem(value):
    entries = []
    for line in value.splitlines():
        m = re.match(r'^( *)([0-9a-fA-F]+)-([0-9a-fA-F]+) : (.*)$', line)
        if not m:
            continue
        start, end = int(m.group(2), 16), int(m.group(3), 16)
        if end < start:
            raise ValueError('descending iomem range ' + line)
        entries.append(dict(depth=len(m.group(1)) // 2, start=start, end=end, size=end - start + 1, name=m.group(4)))
    zeroed = bool(entries) and all(e['start'] == 0 and e['end'] == 0 for e in entries)
    ram = [e for e in entries if e['depth'] == 0 and e['name'] == 'System RAM']
    return dict(entries=entries, addresses_zeroed=zeroed,
                system_ram=[dict(start=e['start'], end=e['end'], size=e['size']) for e in ram],
                system_ram_bytes=sum(e['size'] for e in ram))


DMESG_PATTERNS = {
    'linux_version': r'Linux version .*',
    'machine': r'Machine(?: model)?: .*',
    'kernel_command_line': r'Kernel command line: .*',
    'smp_ncores': r'.*ncores.*',
    'smp_total': r'SMP: Total of \d+ processors activated.*',
    'cpu_boot': r'CPU\d+: (?:Booted secondary processor|failed to come online|thread.*)',
    'memory': r'Memory: .*',
    'memory_bank': r'(?:Memory policy|On node \d+ totalpages|.*reserved.*memory.*|cma: .*|CMA: .*)',
    'mmc': r'mmc\d+: .*',
    'pvr': r'.*(?:PVR|pvrsrvkm|SGX).*',
    'afi': r'.*\bafi\b.*',
}


def dmesg(value):
    lines = []
    for raw in value.splitlines():
        m = re.match(r'^(?:<\d+>)?\[\s*(\d+\.\d+)\]\s?(.*)$', raw)
        lines.append((float(m.group(1)), m.group(2)) if m else (None, raw))
    matches = {k: [] for k in DMESG_PATTERNS}
    for t, line in lines:
        for k, pattern in DMESG_PATTERNS.items():
            if re.fullmatch(pattern, line, re.I):
                matches[k].append(dict(time=t, text=line))
    ncores = [int(m.group(1)) for x in matches['smp_ncores'] for m in [re.search(r'ncores\D*(\d+)', x['text'])] if m]
    total = [int(re.search(r'Total of (\d+)', x['text']).group(1)) for x in matches['smp_total']]
    starts_at_boot = lines and lines[0][0] is not None and lines[0][0] < 1.0
    return dict(lines=len(lines), begins_near_boot=bool(starts_at_boot), matches=matches,
                scu_ncores=ncores[0] if ncores else None, smp_activated=total[0] if total else None)


def modules(value):
    out = []
    for line in value.splitlines():
        cells = line.split()
        if len(cells) >= 3:
            out.append(dict(name=cells[0], size=int(cells[1]), refs=int(cells[2]),
                            state=cells[4] if len(cells) > 4 else None))
    return out


def mounts(value):
    out = []
    for line in value.splitlines():
        cells = line.split()
        if len(cells) >= 4:
            out.append(dict(device=cells[0], mountpoint=cells[1], fstype=cells[2], options=cells[3]))
    return out


def links(value):
    out = {}
    for line in value.splitlines():
        m = re.search(r'(\S+) -> (\S+)$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def kconfig(data):
    try:
        cfg = gzip.GzipFile(fileobj=io.BytesIO(data)).read(16 * 1024 * 1024)
    except (OSError, EOFError) as e:
        return dict(valid=False, error=str(e))
    opts = {}
    for line in cfg.decode('utf-8', errors='replace').splitlines():
        m = re.match(r'(CONFIG_\w+)=(.*)', line)
        if m:
            opts[m.group(1)] = m.group(2)
    keys = ['CONFIG_SMP', 'CONFIG_NR_CPUS', 'CONFIG_HOTPLUG_CPU', 'CONFIG_HIGHMEM', 'CONFIG_CMA',
            'CONFIG_PROC_DEVICETREE', 'CONFIG_IKCONFIG_PROC', 'CONFIG_ARCH_OWL']
    return dict(valid=True, sha256=hashlib.sha256(cfg).hexdigest(), options=len(opts),
                selected={k: opts.get(k) for k in keys})


def device_tree_dir(data):
    """Summarise a tar of /proc/device-tree without extracting it to disk."""
    out = dict(nodes=0, properties=0, cpus=[], memory_reg=None, chosen_bootargs=None)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if m.isdir():
                out['nodes'] += 1
                if re.fullmatch(r'device-tree/cpus/cpu@[0-9a-f]+', m.name):
                    out['cpus'].append(m.name.rsplit('/', 1)[1])
            elif m.isfile():
                out['properties'] += 1
                if m.name in ('device-tree/memory/reg', 'device-tree/chosen/bootargs'):
                    raw = tar.extractfile(m).read(4096)
                    if m.name.endswith('reg'):
                        out['memory_reg'] = [int.from_bytes(raw[i:i+4], 'big') for i in range(0, len(raw) - 3, 4)]
                    else:
                        out['chosen_bootargs'] = raw.rstrip(b'\0').decode('utf-8', errors='replace')
    out['cpus'].sort()
    return out


def fdt_summary(data):
    tree = research.fdt(data)
    index = {n['path']: n for n in tree['nodes']}
    cpus = sorted(n['path'] for n in tree['nodes'] if re.fullmatch(r'/cpus/cpu@[0-9a-f]+', n['path']))
    memory = [dict(path=n['path'], reg=n['properties'].get('reg')) for n in tree['nodes']
              if n['properties'].get('device_type') == ['memory']]
    chosen = index.get('/chosen', {}).get('properties', {})
    return dict(sha256=hashlib.sha256(data).hexdigest(), total_size=tree['total_size'],
                nodes=len(tree['nodes']), cpus=cpus, memory=memory, reservations=tree['reservations'],
                chosen_bootargs=chosen.get('bootargs'),
                model=index.get('/', {}).get('properties', {}).get('model'))


# ---------------------------------------------------------------- release links

def catalogued_components(root=ROOT):
    """Hashes and kernel version strings from committed firmware catalogues."""
    comps, versions = [], []
    folder = root / 'evidence/firmware'
    for p in sorted(folder.glob('*.json')):
        m = json.loads(p.read_text())
        if isinstance(m, dict):
            for c in m.get('components', []):
                comps.append(dict(manifest=str(p.relative_to(root)), id=c['id'], sha256=c['sha256']))
            for s in m.get('gzip_streams', []):
                for v in s.get('linux_version_strings', []):
                    versions.append(dict(manifest=str(p.relative_to(root)), component_sha256=m.get('sha256'), text=v['text']))
    return comps, versions


def release_link(summary, root=ROOT):
    comps, versions = catalogued_components(root)
    out = {}
    running = (summary.get('kernel_version') or '').strip()
    out['kernel_version_matches'] = [v for v in versions if v['text'].strip() == running]
    fdt = summary.get('fdt')
    if fdt and 'sha256' in fdt:
        out['fdt_matches_components'] = [c for c in comps if c['sha256'] == fdt['sha256']]
    out['note'] = ('A version-string match links the running kernel to a catalogued build; it is not a hash of the '
                   'running image. An exported FDT normally includes bootloader fixups, so a hash mismatch with the '
                   'on-card DTB is expected and must be compared property by property.')
    return out


# ---------------------------------------------------------------- interpretation hints

def cpu_hint(cpu):
    """Map observed counts onto the pre-registered outcomes in reports/cpu-topology.md."""
    scu, possible, present, online = (cpu.get(k) for k in ('scu_ncores', 'possible', 'present', 'online'))
    if None in (possible, present, online):
        return dict(outcome='incomplete', text='CPU masks missing; no classification attempted.')
    np, npr, no = len(possible), len(present), len(online)
    if scu is None:
        outcome = 'no-scu-line'
        text = 'No ncores line in dmesg (log may have rotated or kernel differs); masks recorded only.'
    elif scu >= 4 and np <= 2:
        outcome = 'software-cap'
        text = 'SCU reports >=4 cores but possible mask has <=2: suggests a software cap (powersave/nr_cpus/DT).'
    elif scu >= 4 and np >= 4 and npr >= 4 and no <= 2:
        outcome = 'policy-or-startup'
        text = 'Four possible/present but <=2 online: points to hotplug policy or secondary startup failure.'
    elif scu >= 4 and no >= 4:
        outcome = 'four-online'
        text = 'Four CPUs online at capture time.'
    elif scu == 2:
        outcome = 'scu-two'
        text = 'SCU-derived count is two: needs silicon revision/SCU interpretation research.'
    else:
        outcome = 'unclassified'
        text = 'Combination not among the pre-registered outcomes; review manually.'
    return dict(outcome=outcome, text=text, label='hint, not a finding')


# ---------------------------------------------------------------- pre-registered predictions

def load_predictions(root=ROOT):
    return json.loads((root / 'evidence/predictions.json').read_text())


def mib(n):
    return n / (1024 * 1024)


def _p_cpu(s):
    return s['cpu_hint']['outcome'], {k: s['cpu'].get(k) for k in ('scu_ncores', 'possible', 'present', 'online')}


def _p_console(s):
    if 'cmdline' not in s:
        return 'not-evaluable', {}
    consoles = s['cmdline'].get('console') or []
    if not consoles:
        return 'no-console', {}
    if len(consoles) > 1:
        return 'multiple', {'console': consoles}
    m = re.fullmatch(r'ttyS(\d+)(?:,.*)?', str(consoles[0]))
    if not m:
        return 'multiple', {'console': consoles}
    return ('enabled-uart' if int(m.group(1)) in (0, 3, 5) else 'disabled-uart'), {'console': consoles[0]}


def _p_bootdev(s):
    blocks = s.get('storage', {}).get('block_links')
    boot_dev = None
    for t in (s.get('cmdline') or {}).get('tokens', []):
        if t.startswith('boot_dev='):
            boot_dev = t.split('=', 1)[1]
    if not blocks or 'mmcblk0' not in blocks:
        return 'not-evaluable', {'boot_dev': boot_dev}
    path = blocks['mmcblk0']
    values = {'mmcblk0': path, 'boot_dev': boot_dev}
    if 'b0238000.mmc' in path:
        return 'boot-card-on-b0238000', values
    if 'b0230000.mmc' in path:
        return 'boot-card-on-b0230000', values
    return 'other', values


REMOVABLE = re.compile(r'^(mmcblk\d+(p\d+)?|loop\d+|ram\d+|zram\d+)$')


def _p_nand(s):
    text = s.get('storage', {}).get('partitions')
    if text is None:
        return 'not-evaluable', {}
    names = [line.split()[-1] for line in text.splitlines()[1:] if len(line.split()) == 4]
    other = [n for n in names if not REMOVABLE.match(n)]
    return ('other-block-device' if other else 'removable-only'), {'block_devices': names, 'non_removable': other}


def _p_ram(s):
    size = None
    source = None
    for m in (s.get('fdt') or {}).get('memory') or []:
        reg = m.get('reg')
        if isinstance(reg, list) and len(reg) >= 2 and len(reg) % 2 == 0:
            size = sum(reg[i + 1] for i in range(0, len(reg), 2))
            source = 'fdt'
    io = s.get('memory', {}).get('iomem')
    if size in (None, 0) and io and not io['addresses_zeroed'] and io['system_ram_bytes']:
        size, source = io['system_ram_bytes'], 'iomem'
    if not size:
        return 'not-evaluable', {}
    v = mib(size)
    values = {'bytes': size, 'MiB': round(v, 1), 'source': source,
              'MemTotal_kB': s.get('memory', {}).get('meminfo_kB', {}).get('MemTotal')}
    if 192 <= v <= 320:
        return 'ram-256mib-class', values
    if 384 <= v <= 544:
        return 'ram-512mib-class', values
    return 'other', values


def _p_kernel(s):
    if 'kernel_version' not in s:
        return 'not-evaluable', {}
    manifests = {Path(m['manifest']).name for m in s['release_link']['kernel_version_matches']}
    if 'kernel-payload.json' in manifests:
        return 'uimage-build', {}
    if 'adb-kernel-payload.json' in manifests:
        return 'adb-uimage-build', {}
    return 'other', {'version': s['kernel_version']}


def _p_kconfig(s):
    k = s.get('kconfig')
    if not k or not k.get('valid'):
        return 'absent', {}
    n = k['selected'].get('CONFIG_NR_CPUS')
    return ('nr-cpus-4' if n == '4' else 'nr-cpus-other'), {'CONFIG_NR_CPUS': n}


def _p_gpu(s):
    if 'modules' not in s:
        return 'not-evaluable', {}
    loaded = any(m['name'] == 'pvrsrvkm' for m in s['modules'])
    return ('pvr-loaded' if loaded else 'pvr-not-loaded'), {'pvr_version': s.get('pvr_version')}


EVALUATORS = {'P-CPU': _p_cpu, 'P-CONSOLE': _p_console, 'P-BOOTDEV': _p_bootdev, 'P-NAND': _p_nand,
              'P-RAM': _p_ram, 'P-KERNEL': _p_kernel, 'P-KCONFIG': _p_kconfig, 'P-GPU': _p_gpu}


def evaluate_predictions(summary, root=ROOT):
    out = []
    for p in load_predictions(root):
        declared = {o['id'] for o in p['outcomes']}
        fn = EVALUATORS.get(p['id'])
        if fn is None:
            raise ValueError('no evaluator for prediction ' + p['id'])
        outcome, values = fn(summary)
        if outcome not in declared:
            raise ValueError(f"evaluator for {p['id']} returned undeclared outcome {outcome}")
        out.append(dict(id=p['id'], outcome=outcome, values=values,
                        implication=next(o['implication'] for o in p['outcomes'] if o['id'] == outcome)))
    return out


# ---------------------------------------------------------------- privacy

SECRETS = [
    (re.compile(r'(androidboot\.serialno=)\S+'), r'\1<redacted>'),
    (re.compile(r'\b([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b'), '<mac-redacted>'),
]


def redact(value):
    """Remove board serial numbers and MAC addresses from summary text; raw items keep them."""
    if isinstance(value, str):
        for pattern, repl in SECRETS:
            value = pattern.sub(repl, value)
        return value
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------- driver

def parse(capture, root=ROOT):
    report, items = verify(capture, root)
    s = {}
    if 'version' in items:
        s['kernel_version'] = text(items, 'version').strip()
    if 'uname' in items:
        s['uname'] = text(items, 'uname').strip()
    if 'cmdline' in items:
        s['cmdline'] = cmdline(text(items, 'cmdline'))
    cpu = {}
    for k in ('kernel_max', 'possible', 'present', 'online', 'offline'):
        if 'cpu-' + k in items:
            v = text(items, 'cpu-' + k)
            cpu[k] = int(v) if k == 'kernel_max' else cpulist(v)
    if 'cpuinfo' in items:
        cpu['cpuinfo'] = cpuinfo(text(items, 'cpuinfo'))
    freq = {k: text(items, 'cpufreq-' + k).split() for k in ('available', 'min', 'max', 'governor') if 'cpufreq-' + k in items}
    if freq:
        cpu['cpufreq'] = freq
    if 'dmesg' in items:
        s['dmesg'] = dmesg(text(items, 'dmesg'))
        cpu['scu_ncores'] = s['dmesg']['scu_ncores']
        cpu['smp_activated'] = s['dmesg']['smp_activated']
    s['cpu'] = cpu
    s['cpu_hint'] = cpu_hint(cpu)
    mem = {}
    if 'meminfo' in items:
        mem['meminfo_kB'] = meminfo(text(items, 'meminfo'))
    if 'iomem' in items:
        mem['iomem'] = iomem(text(items, 'iomem'))
    s['memory'] = mem
    if 'modules' in items:
        s['modules'] = modules(text(items, 'modules'))
    storage = {}
    if 'mounts' in items:
        storage['mounts'] = mounts(text(items, 'mounts'))
    if 'partitions' in items:
        storage['partitions'] = text(items, 'partitions')
    for k in ('block-links', 'mmc-links'):
        if k in items:
            storage[k.replace('-', '_')] = links(text(items, k))
    s['storage'] = storage
    display = {k: text(items, k).strip() for k in items if k == 'fb' or k.startswith('fb0-')}
    if display:
        s['display'] = display
    for k in ('pvr-version', 'os-release', 'batocera-version'):
        if k in items:
            s[k.replace('-', '_')] = text(items, k).strip()
    if 'kconfig' in items:
        s['kconfig'] = kconfig(items['kconfig'])
    if 'fdt' in items:
        try:
            s['fdt'] = fdt_summary(items['fdt'])
        except ValueError as e:
            s['fdt'] = dict(error=str(e), sha256=hashlib.sha256(items['fdt']).hexdigest())
    if 'device-tree' in items:
        try:
            s['device_tree_dir'] = device_tree_dir(items['device-tree'])
        except tarfile.TarError as e:
            s['device_tree_dir'] = dict(error=str(e))
    s['release_link'] = release_link(s, root)
    predictions = redact(evaluate_predictions(s, root))
    raw_cmdline = (s.get('cmdline') or {}).get('raw', '')
    s['privacy'] = dict(serialno_in_cmdline='androidboot.serialno=' in raw_cmdline,
                        note='Summary text is redacted; raw capture items are not. Review before committing raw data.')
    s = redact(s)
    return dict(format_version=FORMAT_VERSION, capture=report, summary=s, predictions=predictions,
                limitations='Runtime exports describe one boot of one device under one firmware. Interpretations '
                            'are hints until reviewed and recorded through evidence/observations.json.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path, help='atm-capture-* directory produced by device/capture.sh')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    result = parse(a.capture)
    research.save(a.output, result)
    errs = result['capture']['errors']
    print(json.dumps(dict(errors=errs, warnings=result['capture']['warnings'],
                          predictions={p['id']: p['outcome'] for p in result['predictions']}), indent=2))
    raise SystemExit(bool(errs))


if __name__ == '__main__':
    main()
