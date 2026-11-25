#!/usr/bin/env python3
"""Apply curated firmware register observations to the canonical register model.

Idempotent: blocks whose id starts with ``firmware:``, registers listed under
``extra_registers`` and evidence entries tagged ``"curated": "firmware-observations"``
are removed and re-added from registers/curated/firmware-observations.json.
build_dataset.py calls ``apply`` after regenerating source-derived blocks, so a
full rebuild keeps these binary-derived observations. Nothing is promoted to
hardware-validated; unknown widths/access/reset values stay unknown.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / 'registers/curated/firmware-observations.json'
TAG = 'firmware-observations'


def apply(model, curated):
    blocks = [b for b in model['blocks'] if not b['id'].startswith('firmware:')]
    extra_ids = {r['id'] for x in curated.get('extra_registers', []) for r in x['registers']}
    for b in blocks:
        b['evidence'] = [e for e in b['evidence'] if e.get('curated') != TAG]
        b['registers'] = [r for r in b['registers'] if r['id'] not in extra_ids]
        for r in b['registers']:
            r['evidence'] = [e for e in r['evidence'] if e.get('curated') != TAG]
    index = {b['id']: b for b in blocks}
    for x in curated.get('extra_registers', []):
        block = index.get(x['block_id'])
        if block is None:
            raise ValueError('unknown block ' + x['block_id'])
        have = {r['offset'] for r in block['registers']}
        for r in x['registers']:
            if r['offset'] in have:
                raise ValueError(f"{r['id']} duplicates an existing offset in {x['block_id']}")
            block['registers'].append(r)
        block['registers'].sort(key=lambda r: (r['offset'], r['name']))
    for x in curated.get('register_evidence', []):
        block = index.get(x['block_id'])
        reg = next((r for r in block['registers'] if r['name'] == x['register']), None) if block else None
        if reg is None:
            raise ValueError(f"unknown register {x['block_id']}/{x['register']}")
        reg['evidence'].extend(x['evidence'])
    blocks.extend(curated.get('new_blocks', []))  # appended; existing order is preserved
    model['blocks'] = blocks
    return model


def main():
    path = ROOT / 'registers/canonical/hardware.json'
    model = apply(json.loads(path.read_text()), json.loads(CURATED.read_text()))
    path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + '\n')
    print(f"{len(model['blocks'])} blocks, {sum(len(b['registers']) for b in model['blocks'])} registers")


if __name__ == '__main__':
    sys.exit(main())
