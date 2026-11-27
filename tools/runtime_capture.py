#!/usr/bin/env python3
"""Verify and parse a device/capture.sh output folder into structured JSON.

The parser reads ordinary files only and never extracts an archive to disk.
It authenticates the capture (script hash, allowlist, manifest, item hashes,
completion markers), then summarises CPU, memory, boot arguments, device
tree, storage, display, module and firmware observations and evaluates every
pre-registered prediction in evidence/predictions.json.

A capture that fails authentication is *quarantined*: its summary is still
produced for diagnosis, but it is marked unusable as evidence. Prediction
outcomes are hints, not findings; turning them into findings requires an
observation record (evidence/observations.json) and human review.

    python tools/runtime_capture.py CAPTURE OUT.json [--report OUT.md] [--reference-dtb KERNEL.DTB]

Raw captures can contain the board serial number. Everything this tool writes
is redacted (see redact()); the raw folder is not.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import research  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ITEM_LIMIT = 64 * 1024 * 1024
FORMAT_VERSION = 2
TAR_MEMBER_LIMIT = 20000
PROPERTY_LIMIT = 1024 * 1024
MANIFEST_COLUMNS = {
    1: ['id', 'kind', 'target', 'status', 'bytes', 'sha256'],
    2: ['id', 'kind', 'target', 'status', 'bytes', 'sha256', 'note'],
}
STATUSES = {
    1: {'ok', 'missing', 'error', 'unavailable'},
    2: {'ok', 'missing', 'denied', 'error', 'truncated', 'unsupported', 'rejected'},
}
# Files a capture folder may contain besides items/.
TOP_LEVEL = {'capture-info.txt', 'allowlist.txt', 'manifest.tsv', 'DONE', 'PRIVATE-README.txt', 'items'}


# ---------------------------------------------------------------- integrity

def script_allowlist(text):
    """Return the allowlist embedded in a capture.sh text, as a list of lines."""
    m = re.search(r"^ALLOWLIST='(.*?)'$", text, re.S | re.M)
    if not m:
        raise ValueError('capture script has no ALLOWLIST block')
    return [line for line in m.group(1).splitlines() if line]


def script_essential(text):
    m = re.search(r"^ESSENTIAL='(.*?)'$", text, re.M)
    return m.group(1).split() if m else []


def known_versions(root=ROOT):
    return json.loads((root / 'device/capture-versions.json').read_text(encoding='utf-8'))


def read_info(path):
    info = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            info[k] = v
    return info


def read_manifest(path, fmt=None):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    header = lines[0].split('\t') if lines else []
    fmts = [f for f, cols in MANIFEST_COLUMNS.items() if cols == header]
    if not fmts or (fmt is not None and fmt not in fmts):
        raise ValueError('manifest.tsv has an unexpected header')
    cols = MANIFEST_COLUMNS[fmts[0]]
    rows = []
    for n, line in enumerate(lines[1:], 2):
        cells = line.split('\t')
        if len(cells) != len(cols):
            raise ValueError(f'manifest.tsv line {n} has {len(cells)} cells')
        rows.append(dict(zip(cols, cells)))
    return rows


SAFE_ID = re.compile(r'[a-z0-9][a-z0-9_-]*')


def item_path(capture, row):
    if not SAFE_ID.fullmatch(row['id']) and not re.fullmatch(r'[A-Za-z0-9_.-]+', row['id']):
        raise ValueError('unsafe item name ' + row['id'])
    suffix = '.tar' if row['kind'] == 'tree' else '.out'
    return capture / 'items' / (row['id'] + suffix)


def verify(capture, root=ROOT):
    """Authenticate a capture. Returns (report, items, texts) without interpreting content."""
    capture = Path(capture)
    errors, warnings = [], []
    for required in ['capture-info.txt', 'allowlist.txt', 'manifest.tsv']:
        if not (capture / required).is_file():
            raise ValueError('capture is missing ' + required)
    info = read_info(capture / 'capture-info.txt')
    versions = known_versions(root)
    version = next((v for v in versions if v['sha256'] == info.get('script_sha256')), None)
    if version is None:
        errors.append('capture script hash is not a known device/capture.sh version')
    fmt = (version or {}).get('capture_format', 1)
    claimed_fmt = int(info['capture_format']) if info.get('capture_format', '').isdigit() else 1
    if version is not None:
        if str(version['version']) != info.get('capture_version'):
            errors.append('capture_version in capture-info.txt does not match the version registered for the script hash')
        if claimed_fmt != fmt:
            errors.append('capture_format in capture-info.txt does not match the registered script version')
    else:
        fmt = claimed_fmt if claimed_fmt in MANIFEST_COLUMNS else 1
    done = (capture / 'DONE').is_file()
    if not done:
        errors.append('DONE marker absent: capture was interrupted or did not finish writing')
    manifest_bytes = (capture / 'manifest.tsv').read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if info.get('manifest_sha256') in (None, 'unavailable'):
        errors.append('capture-info.txt carries no manifest hash')
    elif info['manifest_sha256'] != manifest_sha:
        errors.append('manifest.tsv hash differs from capture-info.txt')
    rows = read_manifest(capture / 'manifest.tsv', fmt)
    recorded = [x for x in (capture / 'allowlist.txt').read_text(encoding='utf-8', errors='replace').splitlines() if x]
    if version is not None and recorded != version['allowlist']:
        errors.append('recorded allowlist differs from the known script version')
    if [f"{r['id']}|{r['kind']}|{r['target']}" for r in rows] != recorded:
        errors.append('manifest rows do not match the recorded allowlist order')
    for p in sorted(capture.iterdir()):
        if p.name not in TOP_LEVEL:
            warnings.append('unexpected file in capture folder ignored: ' + p.name)
    expected_names = set()
    items, files, texts = {}, [], {}
    for row in rows:
        entry = dict(id=row['id'], kind=row['kind'], target=row['target'], status=row['status'])
        if row.get('note'):
            entry['note'] = row['note']
        if row['status'] not in STATUSES[fmt]:
            errors.append(f"unknown status {row['status']!r} for item {row['id']}")
        try:
            path = item_path(capture, row)
        except ValueError as e:
            errors.append(str(e))
            files.append(entry)
            continue
        expected_names.update({path.name, row['id'] + '.err'})
        if path.is_file():
            size = path.stat().st_size
            if size > ITEM_LIMIT:
                errors.append('item exceeds size limit ' + row['id'])
                files.append(entry)
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            entry.update(bytes=size, sha256=digest)
            if row['bytes'] == '' or int(row['bytes']) != size:
                errors.append('size mismatch ' + row['id'])
            if row['sha256'] in ('', 'unavailable'):
                errors.append('no recorded hash for ' + row['id'])
            elif row['sha256'] != digest:
                errors.append('hash mismatch ' + row['id'])
            if row['status'] in ('ok', 'truncated'):
                items[row['id']] = data
            if row['status'] == 'missing':
                errors.append('item marked missing but a file exists ' + row['id'])
        elif row['status'] in ('ok', 'truncated'):
            errors.append(f"item marked {row['status']} but file absent " + row['id'])
        err = capture / 'items' / (row['id'] + '.err')
        if err.is_file():
            entry['stderr'] = err.read_text(encoding='utf-8', errors='replace')[:2000]
        files.append(entry)
    if (capture / 'items').is_dir():
        for p in sorted((capture / 'items').iterdir()):
            if p.name not in expected_names:
                warnings.append('unexpected file in items/ ignored: ' + p.name)
    statuses = {f['id']: f['status'] for f in files}
    essential = (version or {}).get('essential', [])
    essential_bad = [x for x in essential if statuses.get(x) != 'ok']
    if fmt >= 2:
        claimed = info.get('capture_status')
        if claimed not in ('complete', 'partial'):
            errors.append('capture-info.txt has no valid capture_status')
        elif claimed == 'complete' and essential_bad:
            errors.append('capture claims complete but essential items are not ok: ' + ' '.join(essential_bad))
        if info.get('write_failures') not in ('0',):
            errors.append('the capture script reported failed writes')
        if info.get('hash_tool') == 'none':
            errors.append('the device had no SHA-256 tool, so the capture cannot be authenticated')
        if info.get('head_c') == 'no':
            warnings.append('head -c was unavailable on the device; file reads were not size-bounded')
    test_mode = []
    if info.get('fixture_root', 'none') != 'none':
        test_mode.append('fixture_root')
        warnings.append('capture read a fixture root, not a live system')
    if info.get('path_override', 'none') != 'none':
        test_mode.append('path_override')
        warnings.append('capture ran with a test PATH override')
    if info.get('uid') not in ('0', None):
        warnings.append('capture ran without root; iomem addresses may be zeroed and some files unreadable')
    counts = {}
    for s in statuses.values():
        counts[s] = counts.get(s, 0) + 1
    report = dict(
        capture_version=info.get('capture_version'),
        capture_format=fmt,
        script_sha256=info.get('script_sha256'),
        script_version_known=version is not None,
        script_version_status=(version or {}).get('status'),
        fixture_root=info.get('fixture_root'),
        path_override=info.get('path_override', 'none'),
        uid=info.get('uid'),
        started_utc=info.get('started_utc'),
        finished_utc=info.get('finished_utc'),
        started_uptime=info.get('started_uptime'),
        finished_uptime=info.get('finished_uptime'),
        environment={k: info[k] for k in ('busybox', 'hash_tool', 'head_c', 'tar_tool', 'find_tool', 'readlink_tool',
                                          'item_limit') if k in info},
        manifest_sha256=manifest_sha,
        done_marker=done,
        status_counts=counts,
        essential=essential,
        essential_not_ok=essential_bad,
        files=files,
        errors=errors,
        warnings=warnings,
    )
    report['trust'] = 'authenticated' if not errors else 'quarantined'
    report['completeness'] = 'complete' if not essential_bad and not errors else 'partial'
    report['admissible_as_evidence'] = not errors and not test_mode
    report['state'] = ('quarantined' if errors else
                       'authenticated-complete' if not essential_bad else 'authenticated-partial')
    return report, items


# ---------------------------------------------------------------- generic parsers

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
    raw = value.rstrip('\n')
    tokens = raw.split()
    params = {}
    for t in tokens:
        k, sep, v = t.partition('=')
        params.setdefault(k, []).append(v if sep else True)

    def first(k):
        v = params.get(k)
        return v[0] if v else None
    return dict(raw=raw, tokens=tokens, powersave='powersave' in params,
                maxcpus=params.get('maxcpus'), nr_cpus=params.get('nr_cpus'), mem=params.get('mem'),
                memmap=params.get('memmap'), console=params.get('console'), boot_dev=first('boot_dev'),
                bootdev=first('androidboot.bootdev'), init=first('init'), allen_s500=first('allenS500'),
                dvfslevel=first('androidboot.dvfslevel'), initrd=params.get('initrd'),
                serialno_present='androidboot.serialno' in params)


def cpuinfo(value):
    blocks, common, current = [], {}, None
    for line in value.splitlines():
        if ':' not in line:
            current = None
            continue
        k, v = (x.strip() for x in line.split(':', 1))
        if k == 'processor':
            try:
                current = {'processor': int(v)}
            except ValueError:
                current = {'processor': v}
            blocks.append(current)
        elif current is not None:
            current[k] = v
        else:
            common[k] = v
    serial = common.get('Serial')
    if serial is not None:
        common['Serial'] = 'all-zero' if set(serial) <= {'0'} else '<redacted>'
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
    'smp_ncores': r'.*\bncores\b.*',
    'smp_total': r'SMP: Total of \d+ processors activated.*',
    'brought_up': r'Brought up \d+ CPUs?',
    'cpu_boot': r'CPU\d+: (?:Booted secondary processor|failed to come online|failed to boot.*|thread.*)',
    'powersave': r'.*powersave.*',
    'memory': r'Memory: .*',
    'memory_bank': r'(?:Memory policy|On node \d+ totalpages|.*reserved.*memory.*|Reserved memory \d+MB|cma: .*|CMA: .*|.*memory size = .*)',
    'initrd': r'(?:Freeing initrd memory.*|INITRD: .*|initrd overwritten.*|.*RAMDISK: .*)',
    'mmc': r'mmc\d+: .*',
    'boot_card': r'.*\bas boot card\b.*|.*emmc_boot_card.*|## (?:boot_dev|host_id).*',
    'pvr': r'.*(?:PVR|pvrsrvkm|SGX).*',
    'afi': r'.*\bafi\b.*',
    # Lines the stock loader prints on its own UART (PR #6). They are not
    # expected in the kernel log: the loader output is not stored anywhere
    # Linux can read. A match would need explaining, not celebrating. The formats are the
    # loader's own; bare words such as pmu_status also occur in kernel symbol names.
    'loader_dram': r'.*(?:DRAM init mode\d|DCU_CFG:|==ddr_test|== ok==|PMU_CTL3 = 0x|pmu_status = 0x|load fail to adfu|MByte Cap\.).*',
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
    starts_at_boot = bool(lines) and lines[0][0] is not None and lines[0][0] < 1.0
    mem = {}
    for x in matches['memory']:
        m = re.search(r'Memory: (\d+)k/(\d+)k available, (\d+)k reserved, (\d+)K highmem', x['text'])
        if m:
            mem.update(available_kB=int(m.group(1)), total_kB=int(m.group(2)), reserved_kB=int(m.group(3)),
                       highmem_kB=int(m.group(4)))
        m = re.search(r'Memory:((?: \d+MB)+) = (\d+)MB total', x['text'])
        if m:
            mem.update(banks_MB=[int(v[:-2]) for v in m.group(1).split()], banks_total_MB=int(m.group(2)))
    reserved_mb = [int(m.group(1)) for x in matches['memory_bank'] for m in [re.search(r'Reserved memory (\d+)MB', x['text'])] if m]
    cmd = [x['text'].split(': ', 1)[1] for x in matches['kernel_command_line']]
    return dict(lines=len(lines), begins_near_boot=starts_at_boot,
                first_timestamp=lines[0][0] if lines else None, matches=matches,
                scu_ncores=ncores[0] if ncores else None, smp_activated=total[0] if total else None,
                memory_line=mem or None, vendor_reserved_MB=reserved_mb[0] if reserved_mb else None,
                command_line=cmd[0] if cmd else None,
                powersave_now=any('powersave now' in x['text'] for x in matches['powersave']))


def modules(value):
    out = []
    for line in value.splitlines():
        cells = line.split()
        if len(cells) >= 3 and cells[1].isdigit():
            out.append(dict(name=cells[0], size=int(cells[1]), refs=int(cells[2]) if cells[2].isdigit() else None,
                            state=cells[4] if len(cells) > 4 else None))
    return out


def mounts(value):
    out = []
    for line in value.splitlines():
        cells = line.split()
        if len(cells) >= 4:
            out.append(dict(device=cells[0], mountpoint=cells[1], fstype=cells[2], options=cells[3]))
    return out


def partitions(value):
    out = []
    for line in value.splitlines()[1:]:
        cells = line.split()
        if len(cells) == 4 and cells[0].isdigit():
            out.append(dict(major=int(cells[0]), minor=int(cells[1]), blocks=int(cells[2]), name=cells[3]))
    return out


def links(value):
    """Parse legacy (capture versions 1-2) `ls -l` output into name -> link target."""
    out = {}
    for line in value.splitlines():
        m = re.search(r'(\S+) -> (\S+)$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def probe(value):
    """Parse a capture version 3 sysfs probe listing into {name: {link, attrs}}."""
    out, skipped = {}, []
    for line in value.splitlines():
        cells = line.split('\t')
        if cells[0] == 'entry' and len(cells) >= 2:
            out.setdefault(cells[1], dict(link=None, attrs={}, attr_status={}))
        elif cells[0] == 'link' and len(cells) >= 3:
            out.setdefault(cells[1], dict(link=None, attrs={}, attr_status={}))['link'] = cells[2].strip() or None
        elif cells[0] == 'attr' and len(cells) >= 5:
            e = out.setdefault(cells[1], dict(link=None, attrs={}, attr_status={}))
            e['attr_status'][cells[2]] = cells[3]
            if cells[3] == 'ok':
                e['attrs'][cells[2]] = cells[4].strip()
        elif cells[0] == 'skipped':
            skipped.append(cells[1] if len(cells) > 1 else '')
    return dict(entries=out, skipped=skipped)


KCONFIG_KEYS = ['CONFIG_SMP', 'CONFIG_NR_CPUS', 'CONFIG_HOTPLUG_CPU', 'CONFIG_HIGHMEM', 'CONFIG_CMA', 'CONFIG_VMSPLIT_3G',
                'CONFIG_PAGE_OFFSET', 'CONFIG_OF', 'CONFIG_PROC_DEVICETREE', 'CONFIG_IKCONFIG', 'CONFIG_IKCONFIG_PROC',
                'CONFIG_ARCH_OWL', 'CONFIG_CMDLINE', 'CONFIG_CMDLINE_FROM_BOOTLOADER', 'CONFIG_CMDLINE_EXTEND',
                'CONFIG_CMDLINE_FORCE', 'CONFIG_ARM_ATAG_DTB_COMPAT', 'CONFIG_ARM_APPENDED_DTB', 'CONFIG_LOG_BUF_SHIFT',
                'CONFIG_MMC', 'CONFIG_MMC_BLOCK', 'CONFIG_MTD', 'CONFIG_FB', 'CONFIG_DRM', 'CONFIG_ION', 'CONFIG_SUSPEND']


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
    selected = {k: opts.get(k) for k in KCONFIG_KEYS}
    cmd = opts.get('CONFIG_CMDLINE', '""').strip('"')
    if opts.get('CONFIG_CMDLINE_FORCE') == 'y':
        policy = 'built-in command line replaces the bootloader one' if cmd else 'forced empty command line'
    elif opts.get('CONFIG_CMDLINE_EXTEND') == 'y':
        policy = 'built-in command line extends ATAG arguments (3.10 DT boots ignore EXTEND)'
    elif cmd:
        policy = 'built-in command line used only when /chosen bootargs is empty'
    else:
        policy = 'bootloader /chosen bootargs only'
    return dict(valid=True, sha256=hashlib.sha256(cfg).hexdigest(), options=len(opts), selected=selected,
                cmdline_policy=policy)


# ---------------------------------------------------------------- device tree

def _new_tree():
    return dict(nodes={'/': {}}, links={}, unsafe=[], other=[], errors=[], truncated=[])


def dt_from_tar(data):
    """Read a device-tree tar into {'nodes': {path: {prop: bytes}}} without extracting anything.

    Accepts the capture v3 layout ('./memory/reg') and v1-2 ('device-tree/memory/reg').
    Absolute names, '..' components, links, devices and oversized members are
    recorded, never followed or materialised.
    """
    tree = _new_tree()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as tar:
        for count, m in enumerate(tar):
            if count >= TAR_MEMBER_LIMIT:
                tree['errors'].append('member limit reached')
                break
            name = m.name
            pp = PurePosixPath(name)
            if pp.is_absolute() or '..' in pp.parts or '\\' in name:
                tree['unsafe'].append(name)
                continue
            parts = [x for x in pp.parts if x not in ('.', '')]
            if parts and parts[0] == 'device-tree' and not name.startswith('./'):
                parts = parts[1:]
            path = '/' + '/'.join(parts)
            if m.isdir():
                tree['nodes'].setdefault(path, {})
            elif m.issym() or m.islnk():
                tree['links'][path] = m.linkname
            elif m.isfile():
                node, _, prop = path.rpartition('/')
                node = node or '/'
                if m.size > PROPERTY_LIMIT:
                    tree['truncated'].append(path)
                    continue
                f = tar.extractfile(m)
                value = f.read(m.size) if f else b''
                if len(value) != m.size:
                    tree['truncated'].append(path)
                tree['nodes'].setdefault(node, {})[prop] = value
            else:
                tree['other'].append(path)
    # busybox and GNU tar end an archive with two zero blocks; without them the
    # archive was cut short and members may be silently missing.
    if len(data) % 512 or data[-1024:] != bytes(1024):
        tree['errors'].append('archive truncated: no end-of-archive marker')
    for node in list(tree['nodes']):
        parent = node.rpartition('/')[0] or '/'
        while parent not in tree['nodes']:
            tree['nodes'][parent] = {}
            parent = parent.rpartition('/')[0] or '/'
    return tree


def dt_from_fdt(data):
    """Read a flattened tree into the same shape, keeping raw property bytes and /memreserve/."""
    tree = _new_tree()
    t = research.fdt(data)  # validates header, blocks and structure
    magic, total, offstruct, offstrings = struct.unpack_from('>4I', data)
    size_strings, size_struct = struct.unpack_from('>2I', data, 32)
    strings = data[offstrings:offstrings + size_strings]
    stack, p, end = [], offstruct, offstruct + size_struct
    while p + 4 <= end:
        token = struct.unpack_from('>I', data, p)[0]
        p += 4
        if token == 1:
            q = data.index(b'\0', p, end)
            name = data[p:q].decode('ascii', errors='replace')
            p = (q + 4) & ~3
            path = '/' if not stack else (stack[-1].rstrip('/') + '/' + name)
            stack.append(path)
            tree['nodes'].setdefault(path, {})
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, nameoff = struct.unpack_from('>II', data, p)
            p += 8
            q = strings.index(b'\0', nameoff)
            tree['nodes'][stack[-1]][strings[nameoff:q].decode('ascii', errors='replace')] = data[p:p + length]
            p = (p + length + 3) & ~3
        elif token == 9:
            break
    tree['reservations'] = t['reservations']
    return tree


def be_cells(raw, n):
    return int.from_bytes(raw[:4 * n], 'big') if n else 0


def decode_reg(raw, ac, sc):
    stride = 4 * (ac + sc)
    if raw is None:
        return None, 'absent'
    if stride == 0 or len(raw) % stride or not raw:
        return None, f'malformed: {len(raw)} bytes is not a multiple of {stride} ({ac}+{sc} cells)'
    return [dict(base=be_cells(raw[i:], ac), size=be_cells(raw[i + 4 * ac:], sc)) for i in range(0, len(raw), stride)], 'ok'


def prop_str(raw):
    if raw is None:
        return None
    return [x.decode('utf-8', errors='replace') for x in raw.rstrip(b'\0').split(b'\0')]


def prop_int(raw):
    if raw is None or len(raw) not in (4, 8):
        return None
    return int.from_bytes(raw, 'big')


def cells_of(props, key, default):
    raw = props.get(key)
    return (int.from_bytes(raw, 'big'), False) if raw is not None and len(raw) == 4 else (default, True)


def dt_analysis(tree):
    """Interpret structure: cells, memory nodes, reservations, /chosen, CPUs, MMC nodes."""
    nodes = tree['nodes']
    root = nodes.get('/', {})
    # Linux's defaults (OF_ROOT_NODE_*_CELLS_DEFAULT) are 1/1 when the root omits them.
    ac, ac_default = cells_of(root, '#address-cells', 1)
    sc, sc_default = cells_of(root, '#size-cells', 1)
    memory = []
    for path, props in sorted(nodes.items()):
        depth = path.count('/')
        name = path.rsplit('/', 1)[-1]
        dtype = prop_str(props.get('device_type'))
        if depth == 1 and (dtype == ['memory'] or re.fullmatch(r'memory(@[0-9a-fA-F]+)?', name)):
            banks, state = decode_reg(props.get('reg'), ac, sc)
            memory.append(dict(path=path, device_type=dtype, reg_state=state, banks=banks))
    banks = [b for m in memory for b in (m['banks'] or [])]
    reserved = []
    rm = nodes.get('/reserved-memory')
    if rm is not None:
        rac, _ = cells_of(rm, '#address-cells', ac)
        rsc, _ = cells_of(rm, '#size-cells', sc)
        for path, props in sorted(nodes.items()):
            if path.startswith('/reserved-memory/') and path.count('/') == 2:
                regs, state = decode_reg(props.get('reg'), rac, rsc)
                reserved.append(dict(path=path, reg_state=state, regions=regs, no_map='no-map' in props,
                                     size=prop_int(props.get('size')), compatible=prop_str(props.get('compatible'))))
    heaps = {}
    for path, props in sorted(nodes.items()):
        if path.startswith('/reserved/') and any(k.endswith('_heap_size') for k in props):
            heaps[path] = {k: prop_int(v) for k, v in props.items() if k.endswith('_heap_size')}
    chosen = nodes.get('/chosen')
    chosen_out = None
    if chosen is not None:
        ba = chosen.get('bootargs')
        chosen_out = dict(
            properties=sorted(k for k in chosen if k != 'name'),
            bootargs=ba.rstrip(b'\0').decode('utf-8', errors='replace') if ba is not None else None,
            initrd_start=prop_int(chosen.get('linux,initrd-start')),
            initrd_end=prop_int(chosen.get('linux,initrd-end')),
            stdout_path=prop_str(chosen.get('linux,stdout-path') or chosen.get('stdout-path')))
    cpus = sorted(p.rsplit('/', 1)[1] for p, props in nodes.items()
                  if re.fullmatch(r'/cpus/cpu@[0-9a-fA-F]+', p) and prop_str(props.get('device_type')) in (['cpu'], None))
    mmc = {p.rsplit('/', 1)[1]: (prop_str(props.get('status')) or ['(no status)'])[0]
           for p, props in sorted(nodes.items()) if re.fullmatch(r'/mmc@[0-9a-f]+', p)}
    aliases = {k: (prop_str(v) or [''])[0] for k, v in sorted(nodes.get('/aliases', {}).items()) if k.startswith(('mmc', 'serial', 'sdboot'))}
    props = sum(len([k for k in v if k != 'name']) for v in nodes.values())
    return dict(
        nodes=len(nodes), properties=props,
        root_cells=dict(address=ac, size=sc, address_defaulted=ac_default, size_defaulted=sc_default),
        model=prop_str(root.get('model')), compatible=prop_str(root.get('compatible')),
        memory_nodes=memory, memory_banks=banks,
        memory_total=sum(b['size'] for b in banks) if banks else None,
        reserved_memory=reserved, vendor_heaps_MB=heaps, chosen=chosen_out, cpus=cpus, mmc_nodes=mmc,
        aliases=aliases, links=tree['links'], unsafe_members=tree['unsafe'], other_members=tree['other'],
        truncated_properties=tree['truncated'], read_errors=tree['errors'],
        memreserve=[dict(address=r['address'], size=r['size']) for r in tree.get('reservations', [])],
        memreserve_visible='reservations' in tree)


def dt_index(value):
    out = {'d': set(), 'f': set(), 'l': set()}
    for line in value.splitlines():
        if len(line) > 2 and line[0] in out and line[1] == ' ':
            parts = [x for x in PurePosixPath(line[2:]).parts if x not in ('.',)]
            out[line[0]].add('/' + '/'.join(parts))
    return out


def dt_index_check(tree, index):
    """Compare the tar against the independent find listing of the same directory."""
    props = {(n.rstrip('/') + '/' + k) if n != '/' else '/' + k for n, v in tree['nodes'].items() for k in v}
    nodes = set(tree['nodes'])
    missing_props = sorted(index['f'] - props)
    missing_nodes = sorted(index['d'] - nodes)
    extra = sorted((props - index['f']) | (nodes - index['d']))
    return dict(consistent=not (missing_props or missing_nodes or extra), index_files=len(index['f']),
                index_dirs=len(index['d']), index_links=sorted(index['l']), missing_from_tar=missing_props + missing_nodes,
                not_in_index=extra)


def dt_compare(runtime, reference):
    """Property-level comparison of a runtime tree against the on-card DTB. Values are hashed, not copied."""
    def flat(tree):
        out = {}
        for n, props in tree['nodes'].items():
            for k, v in props.items():
                if k == 'name':  # procfs synthesises a name property; flattened trees have none
                    continue
                out[(n.rstrip('/') or '') + '/' + k] = v
        return out
    a, b = flat(reference), flat(runtime)
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    return dict(added=sorted(set(b) - set(a)), removed=sorted(set(a) - set(b)), changed=changed,
                nodes_added=sorted(set(runtime['nodes']) - set(reference['nodes'])),
                nodes_removed=sorted(set(reference['nodes']) - set(runtime['nodes'])),
                unchanged=len([k for k in set(a) & set(b) if a[k] == b[k]]))


# ---------------------------------------------------------------- firmware links

def catalogued_components(root=ROOT):
    """Hashes and kernel version strings from committed firmware catalogues."""
    comps, versions = [], []
    folder = root / 'evidence/firmware'
    for p in sorted(folder.glob('*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(m, dict):
            for c in m.get('components', []):
                comps.append(dict(manifest=p.relative_to(root).as_posix(), id=c["id"], sha256=c['sha256'], size=c.get('size')))
            for s in m.get('gzip_streams', []):
                for v in s.get('linux_version_strings', []):
                    versions.append(dict(manifest=p.relative_to(root).as_posix(), component_sha256=m.get('sha256'), text=v['text']))
    return comps, versions


def koriki_handoff(root=ROOT):
    """The reconstructed Koriki v1.0 U-Boot -> Linux handoff (BOOT-017), from committed evidence."""
    d = json.loads((root / 'evidence/firmware/stock-boot-chain.json').read_text(encoding='utf-8'))
    rel = d['releases']['koriki-v1.0']
    runs = rel['handoff']
    return dict(
        bootargs=d['other_firmware']['koriki-v1.0']['dt_chosen_bootargs'],
        initrd_start=int(runs[0]['initrd_start'], 16), initrd_end=int(runs[0]['initrd_end'], 16),
        memory_reg=[int(x, 16) for x in runs[0]['dt_memory_reg']], fdt_addr=int(runs[0]['ft_addr'], 16),
        memreserve=[[int(a, 16), int(s, 16)] for a, s in runs[0]['dt_memreserve']],
        uenv_bootargs=d['other_firmware']['koriki-v1.0']['uenv_variables']['bootargs'])


def release_link(summary, root=ROOT):
    comps, versions = catalogued_components(root)
    out = {}
    running = (summary.get('kernel_version') or '').strip()
    out['kernel_version_matches'] = [v for v in versions if v['text'].strip() == running]
    fdt = summary.get('fdt')
    if fdt and 'sha256' in fdt:
        out['fdt_matches_components'] = [c for c in comps if c['sha256'] == fdt['sha256']]
    for key, comp in (('boot_uenv', 'uEnv.txt'), ('boot_conf', 'batocera-boot.conf')):
        f = (summary.get('card_files') or {}).get(key)
        if f:
            out[key + '_matches'] = [dict(manifest=c['manifest'], id=c['id']) for c in comps
                                     if c['id'] == comp and c['sha256'] == f['sha256']]
    kv = summary.get('koriki_version_sha256')
    if kv:
        out['koriki_version_matches'] = [dict(manifest=c['manifest'], id=c['id']) for c in comps
                                         if c['id'] == 'koriki-version.txt' and c['sha256'] == kv]
    out['note'] = ('A version-string match links the running kernel to a catalogued build; it is not a hash of the '
                   'running image. The exported device tree includes bootloader fixups, so it is compared property '
                   'by property, not by hash.')
    return out


# ---------------------------------------------------------------- derived models

MIB = 1024 * 1024
CONTROLLER = re.compile(r'\b([0-9a-f]{8})\.mmc\b')
# Kernel-virtual devices are recognised by name. A /devices/virtual/ path is not enough:
# vendor NAND drivers register their disks there too.
VIRTUAL_BLOCK = re.compile(r'^(loop\d+|ram\d+|zram\d+|nbd\d+|dm-\d+)$')


def storage_model(s):
    st = s.get('storage', {})
    blocks = {}
    probe_block = st.get('block_sysfs')
    legacy = st.get('block_links')
    source = 'probe' if probe_block is not None else 'ls-links' if legacy is not None else None
    if probe_block is not None:
        for name, e in probe_block['entries'].items():
            blocks[name] = dict(link=e['link'], type=e['attrs'].get('device/type'),
                                removable_attr=e['attrs'].get('removable'), size_sectors=e['attrs'].get('size'),
                                type_status=e['attr_status'].get('device/type', 'not-read'))
    elif legacy is not None:
        for name, link in legacy.items():
            blocks[name] = dict(link=link, type=None, removable_attr=None, size_sectors=None, type_status='not-read')
    for name, b in blocks.items():
        m = CONTROLLER.search(b['link'] or '')
        b['controller'] = m.group(1) if m else None
        if name.startswith('mmcblk'):
            b['kind'] = 'mmc'
        elif re.match(r'^(mtdblock\d+|nand\w*|mtd\d+|ubiblock\S*)$', name):
            b['kind'] = 'nand-or-mtd'
        elif VIRTUAL_BLOCK.match(name):
            b['kind'] = 'virtual'
        else:
            b['kind'] = 'other'
        if b['kind'] == 'mmc':
            b['media'] = {'SD': 'sd-card', 'MMC': 'mmc-or-emmc', 'SDIO': 'sdio'}.get(b['type'], 'unknown')
    parts = st.get('partitions_parsed')
    part_names = [p['name'] for p in parts] if parts is not None else None
    boot_mount = next((m for m in st.get('mounts', []) if m['mountpoint'] == '/boot'), None)
    boot_disk = None
    if boot_mount:
        m = re.fullmatch(r'/dev/(mmcblk\d+)p\d+', boot_mount['device'])
        boot_disk = m.group(1) if m else None
    mmc_cards = {}
    if st.get('mmc_sysfs') is not None:
        for name, e in st['mmc_sysfs']['entries'].items():
            c = CONTROLLER.search(e['link'] or '')
            mmc_cards[name] = dict(type=e['attrs'].get('type'), controller=c.group(1) if c else None)
    hosts = {}
    if st.get('mmc_host_sysfs') is not None:
        for name, e in st['mmc_host_sysfs']['entries'].items():
            c = CONTROLLER.search(e['link'] or '')
            hosts[name] = c.group(1) if c else None
    disks_not_in_partitions = sorted(n for n in blocks if part_names is not None and n not in part_names)
    # Enumeration is incomplete if the probe skipped entries (64-entry cap, unsafe names) or if
    # /proc/partitions names a disk the listing does not contain. Either way an absent device
    # may simply be unlisted, so no "only the boot card" conclusion is allowed.
    skipped = sorted(set((probe_block or {}).get('skipped', [])))
    unlisted = sorted({p for p in (part_names or []) if p not in blocks
                       and not any(p.startswith(b) and re.fullmatch(r'p?\d+', p[len(b):]) for b in blocks)})
    incomplete = bool(skipped or unlisted) if source == 'probe' else bool(unlisted)
    return dict(source=source, block_devices=blocks, partition_names=part_names, boot_mount=boot_mount,
                boot_disk=boot_disk, boot_controller=(blocks.get(boot_disk) or {}).get('controller'),
                mmc_cards=mmc_cards, mmc_hosts=hosts, inconsistent=disks_not_in_partitions,
                probe_skipped=skipped, partitions_not_listed=unlisted, enumeration_incomplete=incomplete,
                note=('/sys/block/mmcblk*/removable is 0 for every MMC disk by design of the kernel MMC block '
                      'driver, so removability is judged from the card type (SD versus MMC) and the controller, '
                      'not from that attribute. Absence of an enumerated device does not prove no storage is fitted.'))


def memory_model(s):
    dt = s.get('device_tree') or {}
    mem = s.get('memory', {})
    io = mem.get('iomem')
    total_dt = dt.get('memory_total')
    banks = dt.get('memory_banks') or []
    out = dict(
        quantities=dict(
            physical_dram='not observable after boot (loader detection result; needs early UART, PR #6)',
            bootloader_reported_bytes=total_dt,
            bootloader_reported_source=dt.get('source') if total_dt is not None else None,
            device_tree_banks=banks,
            kernel_system_ram_bytes=(io['system_ram_bytes'] if io and not io['addresses_zeroed'] else None),
            kernel_system_ram_ranges=(io['system_ram'] if io and not io['addresses_zeroed'] else None),
            kernel_memory_line=(s.get('dmesg') or {}).get('memory_line'),
            memtotal_kB=(mem.get('meminfo_kB') or {}).get('MemTotal'),
            vendor_reserved_MB=(s.get('dmesg') or {}).get('vendor_reserved_MB'),
            reserved_memory_nodes=dt.get('reserved_memory'),
            vendor_heap_nodes_MB=dt.get('vendor_heaps_MB'),
            cmdline_mem=(s.get('cmdline') or {}).get('mem'),
            cmdline_memmap=(s.get('cmdline') or {}).get('memmap')),
        checks=[])
    q = out['quantities']
    checks = out['checks']
    if total_dt is not None:
        for r in q['kernel_system_ram_ranges'] or []:
            inside = any(b['base'] <= r['start'] and r['end'] < b['base'] + b['size'] for b in banks)
            checks.append(dict(check=f"System RAM {r['start']:#x}-{r['end']:#x} inside a DT /memory bank", ok=inside))
        if q['kernel_system_ram_bytes'] is not None:
            checks.append(dict(check='iomem System RAM total <= DT /memory total', ok=q['kernel_system_ram_bytes'] <= total_dt))
        line = q['kernel_memory_line'] or {}
        if 'total_kB' in line:
            checks.append(dict(check='kernel "Memory:" total <= DT /memory total', ok=line['total_kB'] * 1024 <= total_dt))
        if q['memtotal_kB'] is not None:
            checks.append(dict(check='MemTotal <= DT /memory total', ok=q['memtotal_kB'] * 1024 <= total_dt))
    if q['memtotal_kB'] is not None and q['kernel_system_ram_bytes'] is not None:
        checks.append(dict(check='MemTotal <= iomem System RAM total', ok=q['memtotal_kB'] * 1024 <= q['kernel_system_ram_bytes']))
    return out


def bootargs_model(s, root=ROOT):
    ref = koriki_handoff(root)
    c = s.get('cmdline')
    dt = (s.get('device_tree') or {}).get('chosen')
    out = dict(predicted_variants=ref['bootargs'], uenv_bootargs=ref['uenv_bootargs'])
    if not c:
        return out
    observed = c['raw']
    stripped = re.sub(r'\s*androidboot\.serialno=\S*', '', observed)
    out['observed'] = observed
    out['observed_without_serial'] = stripped
    exact = [i for i, v in enumerate(ref['bootargs']) if v == stripped]
    tok = [i for i, v in enumerate(ref['bootargs']) if v.split() == stripped.split()]
    best = min(range(len(ref['bootargs'])), key=lambda i: len(set(ref['bootargs'][i].split()) ^ set(stripped.split())))
    pred = ref['bootargs'][best].split()
    obs = stripped.split()
    out.update(exact_variant=exact[0] if exact else None, token_variant=tok[0] if tok else None, closest_variant=best,
               missing_tokens=[t for t in pred if t not in obs], extra_tokens=[t for t in obs if t not in pred],
               order_matches=[t for t in obs if t in pred] == [t for t in pred if t in obs])
    if dt is not None:
        out['chosen_bootargs'] = dt.get('bootargs')
        out['cmdline_equals_chosen'] = dt.get('bootargs') == observed if dt.get('bootargs') is not None else None
    log = (s.get('dmesg') or {}).get('command_line')
    if log is not None:
        out['cmdline_equals_boot_log'] = log == observed
    return out


# ---------------------------------------------------------------- interpretation hints

def cpu_hint(cpu):
    """Map observed counts onto the pre-registered outcomes in reports/cpu-topology.md."""
    scu, possible, present, online = (cpu.get(k) for k in ('scu_ncores', 'possible', 'present', 'online'))
    if None in (possible, present, online):
        return dict(outcome='incomplete', text='CPU masks missing; no classification attempted.', label='hint, not a finding')
    if not (set(online) <= set(present) <= set(possible)):
        return dict(outcome='inconsistent-masks', text='online is not within present, or present not within possible.',
                    label='hint, not a finding')
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
    return json.loads((root / 'evidence/predictions.json').read_text(encoding='utf-8'))


def mib(n):
    return n / MIB


def _p_cpu(s):
    c = s.get('cmdline') or {}
    caps = [t for t in c.get('tokens', []) if t == 'powersave' or t.startswith(('maxcpus=', 'nr_cpus='))]
    values = {k: s['cpu'].get(k) for k in ('scu_ncores', 'possible', 'present', 'online', 'smp_activated', 'kernel_max')}
    values.update(cmdline_cpu_limits=caps, dmesg_powersave_now=(s.get('dmesg') or {}).get('powersave_now'),
                  dt_cpu_nodes=(s.get('device_tree') or {}).get('cpus'),
                  CONFIG_NR_CPUS=((s.get('kconfig') or {}).get('selected') or {}).get('CONFIG_NR_CPUS'))
    return s['cpu_hint']['outcome'], values


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
    n = int(m.group(1))
    if n == 3:
        return 'ttys3', {'console': consoles[0]}
    return ('other-enabled-uart' if n in (0, 5) else 'disabled-uart'), {'console': consoles[0]}


def _p_bootargs(s):
    b = s.get('bootargs')
    if not b or 'observed' not in b:
        return 'not-evaluable', {}
    values = {k: b.get(k) for k in ('observed', 'closest_variant', 'missing_tokens', 'extra_tokens', 'order_matches')}
    if b['exact_variant'] is not None:
        return 'match', dict(values, variant=b['exact_variant'])
    if b['token_variant'] is not None:
        return 'whitespace-differs', dict(values, variant=b['token_variant'])
    return 'tokens-differ', values


def _p_cmdline_src(s):
    b = s.get('bootargs') or {}
    dt = s.get('device_tree')
    if 'observed' not in b or dt is None:
        return 'not-evaluable', {}
    if dt.get('chosen') is None or b.get('chosen_bootargs') is None:
        return 'chosen-bootargs-absent', {}
    values = {'cmdline_equals_boot_log': b.get('cmdline_equals_boot_log'),
              'CONFIG_CMDLINE policy': (s.get('kconfig') or {}).get('cmdline_policy')}
    chosen, observed = b['chosen_bootargs'], b['observed']
    # Vendor drivers/of/fdt.c early_init_dt_scan_chosen (FW-018): FROM_BOOTLOADER copies bootargs,
    # EXTEND appends " " + bootargs to CONFIG_CMDLINE, FORCE ignores bootargs entirely.
    if observed == chosen:
        return 'chosen-used', values
    if chosen and observed.endswith(' ' + chosen):
        return 'chosen-extended', dict(values, prefix=observed[:-len(chosen) - 1])
    return 'chosen-ignored', dict(values, chosen=chosen, cmdline=observed)


def _p_uenv(s):
    if 'cmdline' not in s:
        return 'not-evaluable', {}
    return ('uenv-applied' if 'init=/init' in s['cmdline']['tokens'] else 'uenv-not-applied'), {}


def _p_afi_bootdev(s):
    if 'cmdline' not in s:
        return 'not-evaluable', {}
    c = s['cmdline']
    values = {'boot_dev': c.get('boot_dev'), 'androidboot.bootdev': c.get('bootdev')}
    v = c.get('boot_dev')
    if v is None:
        return 'absent', values
    return {'sd0': 'sd0', 'sd2': 'sd2'}.get(v, 'other'), values


def _p_strap(s):
    if 'cmdline' not in s:
        return 'not-evaluable', {}
    v = s['cmdline'].get('allen_s500')
    if v is None:
        return 'strap-low', {}
    return ('strap-high' if v == '1' else 'other-value'), {'allenS500': v}


def _p_ram(s):
    mm = s.get('memory_model') or {}
    q = mm.get('quantities', {})
    dt = s.get('device_tree')
    values = {'bootloader_reported_bytes': q.get('bootloader_reported_bytes'),
              'device_tree_banks': q.get('device_tree_banks'),
              'iomem_system_ram_bytes': q.get('kernel_system_ram_bytes'),
              'MemTotal_kB': q.get('memtotal_kB'), 'kernel_memory_line': q.get('kernel_memory_line'),
              'cmdline_mem': q.get('cmdline_mem'), 'failed_checks': [c['check'] for c in mm.get('checks', []) if not c['ok']]}
    if q.get('cmdline_mem') or q.get('cmdline_memmap'):
        return 'cmdline-limited', values
    if dt is None or not dt.get('memory_nodes'):
        if q.get('kernel_system_ram_bytes') or q.get('memtotal_kB'):
            return 'kernel-view-only', values
        return 'not-evaluable', values
    nodes = dt['memory_nodes']
    banks = dt.get('memory_banks') or []
    if any(n['reg_state'] != 'ok' for n in nodes) or len(banks) != 1 or banks[0]['base'] != 0:
        return 'unexpected-layout', values
    if values['failed_checks']:
        return 'sources-disagree', values
    size = banks[0]['size']
    if size == 0x10000000:
        return 'reference-256mib', values
    if size == 0x1f000000:
        return 'uboot-fallback', values
    if size in (0x8000000, 0x20000000, 0x40000000):
        return 'other-supported-size', values
    return 'unexpected-layout', values


def _p_initrd(s):
    dt = s.get('device_tree')
    if dt is None or dt.get('chosen') is None:
        return 'not-evaluable', {}
    ref = s.get('handoff_reference') or koriki_handoff()
    ch = dt['chosen']
    log = [x['text'] for x in ((s.get('dmesg') or {}).get('matches') or {}).get('initrd', [])]
    values = {'initrd_start': ch.get('initrd_start'), 'initrd_end': ch.get('initrd_end'),
              'predicted': [ref['initrd_start'], ref['initrd_end']], 'boot_log': log}
    if any('disabling' in x or 'overwritten' in x for x in log):
        return 'kernel-rejected', values
    if ch.get('initrd_start') is None or ch.get('initrd_end') is None:
        return 'absent', values
    if (ch['initrd_start'], ch['initrd_end']) == (ref['initrd_start'], ref['initrd_end']):
        return 'as-reconstructed', values
    return 'different-placement', values


def _p_bootdev(s):
    sm = s.get('storage_model') or {}
    blocks = sm.get('block_devices') or {}
    if not blocks or not sm.get('boot_disk') or sm['boot_disk'] not in blocks:
        return 'not-evaluable', {'boot_disk': sm.get('boot_disk')}
    ctrl = sm.get('boot_controller')
    cards = [n for n, b in blocks.items() if b.get('kind') == 'mmc']
    values = {'boot_disk': sm['boot_disk'], 'boot_controller': ctrl, 'mmc_disks': cards,
              'boot_dev': (s.get('cmdline') or {}).get('boot_dev'),
              'kernel_boot_card_lines': [x['text'] for x in ((s.get('dmesg') or {}).get('matches') or {}).get('boot_card', [])]}
    if len(cards) > 1:
        return 'second-card-present', values
    if ctrl == 'b0238000':
        return 'boot-card-on-b0238000', values
    if ctrl == 'b0230000':
        return 'boot-card-on-b0230000', values
    return 'other', values


def _p_nand(s):
    sm = s.get('storage_model') or {}
    blocks = sm.get('block_devices')
    if not blocks:
        return 'incomplete', {'source': sm.get('source')}
    values = {n: {k: b.get(k) for k in ('kind', 'media', 'controller', 'type')} for n, b in blocks.items()}
    values = {'devices': values, 'boot_disk': sm.get('boot_disk'), 'source': sm.get('source'),
              'not_in_partitions': sm.get('inconsistent'), 'probe_skipped': sm.get('probe_skipped'),
              'partitions_not_listed': sm.get('partitions_not_listed')}
    kinds = [b['kind'] for b in blocks.values()]
    mmc = [b for b in blocks.values() if b['kind'] == 'mmc']
    if 'nand-or-mtd' in kinds or 'other' in kinds:
        return 'other-block-device', values
    if any(b.get('media') == 'mmc-or-emmc' for b in mmc):
        return 'non-removable-mmc', values
    if sm.get('enumeration_incomplete'):
        return 'incomplete', values
    if sm.get('source') != 'probe' or any(b.get('media') == 'unknown' for b in mmc):
        return 'type-unknown', values
    if len(mmc) > 1:
        return 'additional-card', values
    if len(mmc) == 1:
        return 'boot-card-only', values
    return 'incomplete', values


def _p_kernel(s):
    if 'kernel_version' not in s:
        return 'not-evaluable', {}
    manifests = {Path(m['manifest']).name for m in s['release_link']['kernel_version_matches']}
    if 'kernel-payload.json' in manifests:
        return 'uimage-build', {}
    if 'adb-kernel-payload.json' in manifests:
        return 'adb-uimage-build', {}
    if 'koriki-1031-kernel-payload.json' in manifests:
        return 'koriki-1031-build', {}
    return 'other', {'version': s['kernel_version']}


def _p_kconfig(s):
    k = s.get('kconfig')
    status = (s.get('item_status') or {}).get('kconfig', 'missing')
    if k is None and status == 'missing':
        return 'absent', {}
    if not k or not k.get('valid'):
        return 'unreadable', {'item_status': status, 'error': (k or {}).get('error')}
    n = k['selected'].get('CONFIG_NR_CPUS')
    values = {'CONFIG_NR_CPUS': n, 'cmdline_policy': k.get('cmdline_policy'),
              'CONFIG_CMDLINE': k['selected'].get('CONFIG_CMDLINE')}
    return ('nr-cpus-4' if n == '4' else 'nr-cpus-other'), values


def _p_gpu(s):
    if 'modules' not in s:
        return 'not-evaluable', {}
    loaded = any(m['name'] == 'pvrsrvkm' for m in s['modules'])
    return ('pvr-loaded' if loaded else 'pvr-not-loaded'), {'pvr_version': s.get('pvr_version')}


def _p_cardconfig(s):
    f = s.get('card_files') or {}
    rl = s.get('release_link') or {}
    if 'boot_uenv' not in f and 'boot_conf' not in f:
        return 'not-evaluable', {}
    values = {'uenv_catalogued': bool(rl.get('boot_uenv_matches')), 'conf_catalogued': bool(rl.get('boot_conf_matches')),
              'overclocking': (f.get('boot_conf') or {}).get('overclocking'),
              'missing': [k for k in ('boot_uenv', 'boot_conf') if k not in f]}
    # 'none' selects the same 1008000 kHz cap as an unset value (S02overclock).
    if values['overclocking'] not in (None, 'none'):
        return 'overclock-set', values
    if values['missing']:
        return 'partly-evaluable', values
    if values['uenv_catalogued'] and values['conf_catalogued']:
        return 'baseline-files', values
    return 'files-modified', values


def _p_dram_log(s):
    d = s.get('dmesg')
    if not d:
        return 'not-evaluable', {}
    hits = [x['text'] for x in d['matches']['loader_dram']]
    values = {'log_begins_near_boot': d['begins_near_boot']}
    if hits:
        return 'loader-lines-present', dict(values, lines=hits[:20])
    return 'requires-early-serial', values


EVALUATORS = {'P-CPU': _p_cpu, 'P-CONSOLE': _p_console, 'P-BOOTARGS': _p_bootargs, 'P-CMDLINE-SRC': _p_cmdline_src,
              'P-UENV': _p_uenv, 'P-AFI-BOOTDEV': _p_afi_bootdev, 'P-STRAP': _p_strap, 'P-RAM': _p_ram,
              'P-INITRD': _p_initrd, 'P-BOOTDEV': _p_bootdev, 'P-NAND': _p_nand, 'P-KERNEL': _p_kernel,
              'P-KCONFIG': _p_kconfig, 'P-GPU': _p_gpu, 'P-CARDCONFIG': _p_cardconfig, 'P-DRAM-LOG': _p_dram_log}


def evaluate_predictions(summary, root=ROOT):
    out = []
    for p in load_predictions(root):
        declared = {o['id']: o for o in p['outcomes']}
        fn = EVALUATORS.get(p['id'])
        if fn is None:
            raise ValueError('no evaluator for prediction ' + p['id'])
        outcome, values = fn(summary)
        if outcome not in declared:
            raise ValueError(f"evaluator for {p['id']} returned undeclared outcome {outcome}")
        o = declared[outcome]
        out.append(dict(id=p['id'], outcome=outcome, outcome_class=o.get('class'), values=values,
                        implication=o['implication'], resolvable_by_v3=p.get('resolvable_by_v3')))
    return out


# ---------------------------------------------------------------- privacy

# A redacted value ends at whitespace or a quote, so Markdown and JSON quoting survive.
TOKEN = r"""[^\s`'"]+"""
SECRETS = [
    (re.compile(r'(androidboot\.serialno=)' + TOKEN, re.I), r'\1<redacted>'),
    (re.compile(r'\b((?:serial[_-]?no|serial[_-]?number|serialnumber|iserial(?:number)?)\s*[=:]\s*)' + TOKEN, re.I), r'\1<redacted>'),
    (re.compile(r'(\bSerial\s*+:\s*+)(?!0+\b)[0-9a-fA-F]+', re.I), r'\1<redacted>'),
    (re.compile(r'(\bSN\s*[=:]\s*)' + TOKEN), r'\1<redacted>'),
    (re.compile(r'(\b(?:cid|serial)\b\s*+[=:]?\s*+)(?!(?:0x)?0+\b)(?:0x)?[0-9a-fA-F]{16,}', re.I), r'\1<redacted>'),
    (re.compile(r'\b((?:PART)?UUID=)' + TOKEN, re.I), r'\1<redacted>'),
    (re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'), '<uuid-redacted>'),
    (re.compile(r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b'), '<mac-redacted>'),
]


def redact(value):
    """Remove serial numbers, card identifiers, UUIDs and MAC addresses from output text; raw items keep them."""
    if isinstance(value, str):
        for pattern, repl in SECRETS:
            value = pattern.sub(repl, value)
        return value
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {redact(k) if isinstance(k, str) else k: redact(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------- driver

def conf_values(value):
    """Active (uncommented) key=value lines of batocera-boot.conf."""
    out = {}
    for line in value.splitlines():
        m = re.match(r'^\s*([A-Za-z0-9_.-]+)\s*=\s*(.*?)\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def parse(capture, root=ROOT, reference_dtb=None):
    report, items = verify(capture, root)
    s = {'item_status': {f['id']: f['status'] for f in report['files']}}
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
            try:
                cpu[k] = int(v) if k == 'kernel_max' else cpulist(v)
            except ValueError as e:
                cpu.setdefault('parse_errors', []).append(f'{k}: {e}')
    if 'cpuinfo' in items:
        cpu['cpuinfo'] = cpuinfo(text(items, 'cpuinfo'))
    freq = {k: text(items, 'cpufreq-' + k).split() for k in
            ('available', 'min', 'max', 'governor', 'driver', 'scaling_min', 'scaling_max', 'scaling_cur') if 'cpufreq-' + k in items}
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
        try:
            mem['iomem'] = iomem(text(items, 'iomem'))
        except ValueError as e:
            mem['iomem_error'] = str(e)
    s['memory'] = mem
    if 'modules' in items:
        s['modules'] = modules(text(items, 'modules'))
    storage = {}
    if 'mounts' in items:
        storage['mounts'] = mounts(text(items, 'mounts'))
    if 'partitions' in items:
        storage['partitions'] = text(items, 'partitions')
        storage['partitions_parsed'] = partitions(storage['partitions'])
    for k in ('block-links', 'mmc-links'):
        if k in items:
            storage[k.replace('-', '_')] = links(text(items, k))
    for k in ('block-sysfs', 'mmc-sysfs', 'mmc-host-sysfs'):
        if k in items:
            storage[k.replace('-', '_')] = probe(text(items, k))
    s['storage'] = storage
    display = {k: text(items, k).strip() for k in items if k == 'fb' or k.startswith('fb0-')}
    if display:
        s['display'] = display
    for k in ('pvr-version', 'os-release', 'batocera-version', 'koriki-version'):
        if k in items:
            s[k.replace('-', '_')] = text(items, k).strip()
    if 'koriki-version' in items:
        s['koriki_version_sha256'] = hashlib.sha256(items['koriki-version']).hexdigest()
    card = {}
    for k in ('boot-uenv', 'boot-conf'):
        if k in items:
            entry = dict(sha256=hashlib.sha256(items[k]).hexdigest(), bytes=len(items[k]))
            if k == 'boot-conf':
                vals = conf_values(text(items, k))
                entry['overclocking'] = vals.get('overclocking')
                entry['active_keys'] = sorted(vals)
            else:
                entry['text'] = text(items, k)
            card[k.replace('-', '_')] = entry
    if card:
        s['card_files'] = card
    if 'kconfig' in items:
        s['kconfig'] = kconfig(items['kconfig'])
    trees = {}
    if 'fdt' in items:
        try:
            trees['fdt'] = dt_from_fdt(items['fdt'])
            s['fdt'] = dict(sha256=hashlib.sha256(items['fdt']).hexdigest(), bytes=len(items['fdt']))
        except (ValueError, struct.error, IndexError) as e:
            s['fdt'] = dict(error=str(e), sha256=hashlib.sha256(items['fdt']).hexdigest())
    if 'device-tree' in items:
        try:
            trees['dir'] = dt_from_tar(items['device-tree'])
        except (tarfile.TarError, EOFError, ValueError) as e:
            s['device_tree_error'] = 'unreadable device-tree archive: ' + str(e)
    chosen_tree = trees.get('dir') or trees.get('fdt')
    if chosen_tree is not None:
        s['device_tree'] = dt_analysis(chosen_tree)
        s['device_tree']['source'] = 'device-tree-dir' if 'dir' in trees else 'fdt-blob'
        statuses = {f['id']: f for f in report['files']}
        s['device_tree']['capture_status'] = (statuses.get('device-tree') or {}).get('status')
        if 'dir' in trees and 'device-tree-index' in items:
            s['device_tree']['index_check'] = dt_index_check(trees['dir'], dt_index(text(items, 'device-tree-index')))
        if 'dir' in trees and 'fdt' in trees:
            s['device_tree']['dir_vs_fdt'] = dt_compare(trees['dir'], trees['fdt'])
    if reference_dtb is not None:
        data = Path(reference_dtb).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        comps, _ = catalogued_components(root)
        known = [dict(manifest=c['manifest'], id=c['id']) for c in comps if c['sha256'] == digest]
        cmp = dict(reference_sha256=digest, reference_catalogued=known)
        if chosen_tree is not None:
            cmp.update(dt_compare(chosen_tree, dt_from_fdt(data)))
        s['device_tree_vs_reference'] = cmp
    s['release_link'] = release_link(s, root)
    s['storage_model'] = storage_model(s)
    s['memory_model'] = memory_model(s)
    s['bootargs'] = bootargs_model(s, root)
    s['handoff_reference'] = koriki_handoff(root)
    predictions = evaluate_predictions(s, root)
    raw_cmdline = (s.get('cmdline') or {}).get('raw', '')
    s['privacy'] = dict(serialno_in_cmdline='androidboot.serialno=' in raw_cmdline,
                        note='This output is redacted; the raw capture folder is not. Keep the raw folder private.')
    if report['trust'] != 'authenticated':
        for p in predictions:
            p['quarantined'] = True
    result = dict(format_version=FORMAT_VERSION, capture=report, summary=s, predictions=predictions,
                  limitations='Runtime exports describe one boot of one device under one firmware. A Linux capture '
                              'cannot show Boot ROM, loader or U-Boot console output, DRAM training or the physical '
                              'DRAM size; it shows what the boot chain handed over. Interpretations are hints until '
                              'reviewed and recorded through evidence/observations.json.')
    return redact(jsonable(result))


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        items = sorted(value) if isinstance(value, set) else value
        return [jsonable(v) for v in items]
    if isinstance(value, bytes):
        return value.hex()
    return value


# ---------------------------------------------------------------- shareable report

def hexs(v):
    return f'{v:#x}' if isinstance(v, int) else ('—' if v is None else str(v))


def render_report(result):
    """A redacted, shareable Markdown summary. It never includes raw item contents."""
    c, s = result['capture'], result['summary']
    L = ['# V3 capture summary', '',
         f"**State:** {c['state']} · **admissible as evidence:** {'yes' if c['admissible_as_evidence'] else 'no'} · "
         f"script version {c['capture_version']} (format {c['capture_format']}) · manifest `{c['manifest_sha256'][:16]}…`", '']
    if c['errors']:
        L += ['## Integrity errors (capture quarantined)', ''] + [f'- {e}' for e in c['errors']] + ['']
    if c['warnings']:
        L += ['## Warnings', ''] + [f'- {w}' for w in c['warnings']] + ['']
    L += ['## Item status', '', '| Status | Count |', '|---|---:|']
    L += [f'| {k} | {v} |' for k, v in sorted(c['status_counts'].items())]
    bad = [f for f in c['files'] if f['status'] != 'ok']
    if bad:
        L += ['', 'Not collected: ' + ', '.join(f"`{f['id']}` ({f['status']})" for f in bad) + '.']
    if c['essential_not_ok']:
        L += ['', '**Essential items missing:** ' + ', '.join(c['essential_not_ok']) + '. The capture is partial.']
    L += ['', '## Predictions', '', '| Prediction | Outcome | Class | Implication |', '|---|---|---|---|']
    for p in result['predictions']:
        L.append(f"| {p['id']} | `{p['outcome']}` | {p.get('outcome_class') or ''} | {p['implication']} |")
    b = s.get('bootargs') or {}
    if 'observed' in b:
        L += ['', '## Boot arguments: reconstruction versus running kernel', '',
              '| | Value |', '|---|---|',
              f"| Predicted (BOOT-017, strap low) | `{b['predicted_variants'][0]}` |",
              f"| Predicted (strap high) | `{b['predicted_variants'][1]}` |",
              f"| `/proc/cmdline` | `{b['observed']}` |",
              f"| `/chosen/bootargs` | `{b.get('chosen_bootargs')}` |",
              f"| Equal to `/chosen` | {b.get('cmdline_equals_chosen')} |",
              f"| Missing predicted tokens | {', '.join(b['missing_tokens']) or 'none'} |",
              f"| Unpredicted tokens | {', '.join(b['extra_tokens']) or 'none'} |"]
    mm = (s.get('memory_model') or {}).get('quantities')
    if mm:
        line = mm.get('kernel_memory_line') or {}
        L += ['', '## Memory: five different quantities', '', '| Quantity | Observed | Source |', '|---|---|---|',
              f"| 1. Physical DRAM capacity | not observable | needs early UART (PR #6) |",
              f"| 2. Size the loader handed to U-Boot (AFI) | not directly observable | inferred from 3 if U-Boot did not fall back |",
              f"| 3. DT `/memory` (U-Boot fixup) | {hexs(mm.get('bootloader_reported_bytes'))} | {mm.get('bootloader_reported_source') or 'device tree not captured'} |",
              f"| 4. Kernel System RAM (`/proc/iomem`) | {hexs(mm.get('kernel_system_ram_bytes'))} | iomem |",
              f"| 4b. Kernel boot-log total | {line.get('total_kB', '—')} kB | dmesg `Memory:` |",
              f"| 5. Usable after reservations (`MemTotal`) | {mm.get('memtotal_kB', '—')} kB | meminfo |",
              f"| Vendor carve-out reported | {mm.get('vendor_reserved_MB', '—')} MB | dmesg `Reserved memory` |"]
        checks = (s.get('memory_model') or {}).get('checks') or []
        if checks:
            L += [''] + [f"- {'✔' if x['ok'] else '✘'} {x['check']}" for x in checks]
    sm = s.get('storage_model') or {}
    if sm.get('block_devices'):
        L += ['', '## Storage enumeration', '', '| Device | Kind | Media | Controller |', '|---|---|---|---|']
        for n, d in sorted(sm['block_devices'].items()):
            L.append(f"| {n} | {d.get('kind')} | {d.get('media', '')} | {d.get('controller') or ''} |")
        L += ['', f"Boot partition mounted from `{sm.get('boot_disk')}` on controller `{sm.get('boot_controller')}`.",
              '', sm['note']]
    dt = s.get('device_tree')
    if dt:
        L += ['', '## Device tree', '',
              f"Source: {dt['source']}; {dt['nodes']} nodes, {dt['properties']} properties; root cells "
              f"{dt['root_cells']['address']}/{dt['root_cells']['size']}; memory nodes "
              f"{', '.join(m['path'] for m in dt['memory_nodes']) or 'none'}."]
        if dt.get('index_check'):
            L.append(f"Tar versus independent listing consistent: {dt['index_check']['consistent']}.")
        if not dt.get('memreserve_visible'):
            L.append('`/memreserve/` entries are not exported through `/proc/device-tree`, so the DTB and initrd '
                     'reservations U-Boot adds cannot be checked from this capture.')
    L += ['', '## What this capture cannot establish', '',
          '- Boot ROM behaviour, loader and U-Boot console output, DRAM training, rank retry, the memory test result, '
          'and the physical DRAM size (P-DRAM-LOG): these need a separately approved early serial capture.',
          '- `/memreserve/` entries and U-Boot-internal decisions not reflected in the device tree or command line.',
          '- Whether any storage that Linux did not enumerate is fitted.', '',
          '_Redacted summary; the raw capture folder may contain the board serial number and stays private._', '']
    return redact('\n'.join(L))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('capture', type=Path, help='atm-capture-* directory produced by device/capture.sh')
    p.add_argument('output', type=Path, help='parsed, redacted JSON')
    p.add_argument('--report', type=Path, help='also write a redacted Markdown summary')
    p.add_argument('--reference-dtb', type=Path, help='on-card KERNEL.DTB to compare the running tree against')
    a = p.parse_args()
    result = parse(a.capture, reference_dtb=a.reference_dtb)
    research.save(a.output, result)
    if a.report:
        a.report.write_text(render_report(result), encoding='utf-8')
    c = result['capture']
    print(json.dumps(dict(state=c['state'], admissible_as_evidence=c['admissible_as_evidence'], errors=c['errors'],
                          warnings=c['warnings'], essential_not_ok=c['essential_not_ok'],
                          predictions={p['id']: p['outcome'] for p in result['predictions']}), indent=2))
    raise SystemExit(1 if c['errors'] else 0)


if __name__ == '__main__':
    main()
