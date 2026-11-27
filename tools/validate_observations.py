#!/usr/bin/env python3
"""Schema and cross-reference checks for ledgers and hardware observation records.

Runs without device captures or firmware inputs. Called by `research.py validate`.
"""
import hashlib
import json
from pathlib import Path
import re

from runtime_capture import EVALUATORS, script_allowlist, script_essential

SCHEMAS = {
    'evidence/sources.json': 'evidence/schemas/sources.schema.json',
    'evidence/findings.json': 'evidence/schemas/findings.schema.json',
    'evidence/contradictions.json': 'evidence/schemas/contradictions.schema.json',
    'evidence/observations.json': 'evidence/schemas/observations.schema.json',
    'evidence/predictions.json': 'evidence/schemas/predictions.schema.json',
}


def load(root, rel):
    return json.loads((root / rel).read_text(encoding='utf-8'))


def schema_errors(root):
    import jsonschema
    errors = []
    for data, schema in SCHEMAS.items():
        validator = jsonschema.Draft202012Validator(load(root, schema))
        for e in sorted(validator.iter_errors(load(root, data)), key=lambda e: list(e.path)):
            errors.append(f"schema {data} at {'/'.join(map(str, e.path)) or '<root>'}: {e.message}")
    return errors


def firmware_index(root):
    """Image hashes -> component ids, from acquisitions and committed catalogues."""
    images = {}
    folder = root / 'evidence/firmware'
    for p in sorted(folder.glob('*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(m, dict) and 'components' in m and 'sha256' in m:
            images.setdefault(m['sha256'], set()).update(c['id'] for c in m['components'])
    acq = folder / 'acquisitions.json'
    if acq.exists():
        for a in json.loads(acq.read_text(encoding='utf-8')):
            for key in ('sha256', 'expanded_sha256'):
                if key in a:
                    images.setdefault(a[key], set())
    return images


def capture_version_errors(root):
    errors = []
    script = root / 'device/capture.sh'
    versions_path = root / 'device/capture-versions.json'
    if not script.exists() or not versions_path.exists():
        return ['device/capture.sh or device/capture-versions.json missing']
    versions = json.loads(versions_path.read_text(encoding='utf-8'))
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    current = [v for v in versions if v['sha256'] == digest]
    if not current:
        errors.append('device/capture.sh changed without a new entry in device/capture-versions.json')
    else:
        if current[0]['allowlist'] != script_allowlist(script.read_text(encoding='utf-8')):
            errors.append('device/capture-versions.json allowlist differs from device/capture.sh')
        if current[0].get('essential', []) != script_essential(script.read_text(encoding='utf-8')):
            errors.append('device/capture-versions.json essential list differs from device/capture.sh')
        if current[0].get('status') != 'current':
            errors.append('device/capture.sh matches a version not marked current')
        m = re.search(r'^CAPTURE_VERSION=(\d+)$', script.read_text(encoding='utf-8'), re.M)
        if not m or int(m.group(1)) != current[0]['version']:
            errors.append('CAPTURE_VERSION in device/capture.sh differs from its registered version')
    if len({v['version'] for v in versions}) != len(versions):
        errors.append('duplicate capture script version number')
    if len({v['sha256'] for v in versions}) != len(versions):
        errors.append('duplicate capture script hash')
    if [v['status'] for v in versions].count('current') != 1:
        errors.append('exactly one capture script version must be current')
    for v in versions:
        allow = {line.split('|', 1)[0] for line in v['allowlist']}
        missing = [x for x in v.get('essential', []) if x not in allow]
        if missing:
            errors.append(f"capture version {v['version']}: essential items not in its allowlist: {missing}")
    return errors


def cross_reference_errors(root):
    errors = []
    findings = load(root, 'evidence/findings.json')
    contradictions = load(root, 'evidence/contradictions.json')
    observations = load(root, 'evidence/observations.json')
    fids = {f['id'] for f in findings}
    obs = {}
    versions_path = root / 'device/capture-versions.json'
    tools = {v['sha256'] for v in json.loads(versions_path.read_text(encoding='utf-8'))} if versions_path.exists() else set()
    images = firmware_index(root)
    for o in observations:
        if o['id'] in obs:
            errors.append('duplicate observation ' + o['id'])
        fw = o['firmware']
        if fw['image_sha256'] not in images:
            errors.append(f"{o['id']}: firmware image hash is not a catalogued or acquired image")
        elif images[fw['image_sha256']] and fw['boot_kernel'] not in images[fw['image_sha256']]:
            errors.append(f"{o['id']}: boot_kernel {fw['boot_kernel']} is not a component of that image")
        if o['procedure']['tool'] == 'device/capture.sh' and o['procedure']['tool_sha256'] not in tools:
            errors.append(f"{o['id']}: capture tool hash is not a known device/capture.sh version")
        summary_path = root / o['capture']['summary']
        summary = None
        if not summary_path.exists():
            errors.append(f"{o['id']}: summary {o['capture']['summary']} missing")
        else:
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
            cap = summary.get('capture', {})
            if cap.get('manifest_sha256') != o['capture']['manifest_sha256']:
                errors.append(f"{o['id']}: summary manifest hash differs from observation record")
            if cap.get('errors'):
                errors.append(f"{o['id']}: summary carries capture integrity errors")
            if cap.get('fixture_root', 'none') != 'none':
                errors.append(f"{o['id']}: summary was produced from a fixture, not a device")
            if cap.get('path_override', 'none') != 'none':
                errors.append(f"{o['id']}: summary was produced with a test PATH override")
            if summary.get('format_version', 1) >= 2 and cap.get('trust') != 'authenticated':
                errors.append(f"{o['id']}: summary is not authenticated (quarantined capture)")
            if o['procedure']['tool'] == 'device/capture.sh' and cap.get('script_sha256') != o['procedure']['tool_sha256']:
                errors.append(f"{o['id']}: summary script hash differs from procedure.tool_sha256")
        obs[o['id']] = summary
    for f in findings:
        for oid in f.get('observations', []):
            if oid not in obs:
                errors.append(f"{f['id']}: cites unknown observation {oid}")
        if f.get('observations') and f['validation'] != 'hardware-observation':
            errors.append(f"{f['id']}: cites observations but validation is not hardware-observation")
        for e in f['evidence']:
            if 'observation' not in e:
                continue
            if e['observation'] not in f.get('observations', []):
                errors.append(f"{f['id']}: evidence observation {e['observation']} not listed in observations")
            summary = obs.get(e['observation'])
            if summary and 'item' in e:
                ok = {x['id'] for x in summary['capture']['files'] if x['status'] == 'ok'}
                if e['item'] not in ok:
                    errors.append(f"{f['id']}: capture item {e['item']} absent from {e['observation']}")
    cids = {c['id'] for c in contradictions}
    allowlist = {line.split('|', 1)[0] for line in script_allowlist((root / 'device/capture.sh').read_text(encoding='utf-8'))}
    seen = set()
    for p in load(root, 'evidence/predictions.json'):
        if p['id'] in seen:
            errors.append('duplicate prediction ' + p['id'])
        seen.add(p['id'])
        if p['id'] not in EVALUATORS:
            errors.append(f"{p['id']}: no evaluator in tools/runtime_capture.py")
        outcomes = [o['id'] for o in p['outcomes']]
        if len(outcomes) != len(set(outcomes)):
            errors.append(f"{p['id']}: duplicate outcome id")
        errors += [f"{p['id']}: unknown finding {x}" for x in p['findings'] if x not in fids]
        errors += [f"{p['id']}: unknown contradiction {x}" for x in p['contradictions'] if x not in cids]
        errors += [f"{p['id']}: capture item {x} not in allowlist" for x in p['capture_items'] if x not in allowlist]
        classes = [o['class'] for o in p['outcomes']]
        if p['resolvable_by_v3'] != 'no' and not {'expected', 'alternative'} & set(classes):
            errors.append(f"{p['id']}: no expected or alternative outcome")
        if 'insufficient' not in classes:
            errors.append(f"{p['id']}: no outcome for missing information")
    errors += [f"evaluator {x} has no prediction record" for x in EVALUATORS if x not in seen]
    for c in contradictions:
        for fid in c['findings']:
            if fid not in fids:
                errors.append(f"{c['id']}: unknown finding {fid}")
        for oid in c.get('observations', []):
            if oid not in obs:
                errors.append(f"{c['id']}: unknown observation {oid}")
    return errors


def validate(root):
    root = Path(root)
    errors = schema_errors(root) + capture_version_errors(root)
    if not errors:
        errors += cross_reference_errors(root)
    return errors


if __name__ == '__main__':
    result = validate(Path(__file__).resolve().parents[1])
    print(json.dumps({'errors': result}, indent=2))
    raise SystemExit(bool(result))
