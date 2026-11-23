# Contributing evidence

Identify the exact chip, board revision, firmware image hash and source revision. A label such as `owl`, `s500`, `atm7059a` or `rg35xx` is not an equivalence proof. Original RG35XX and H700 models must never share an unqualified compatibility claim.

Add sources to `evidence/sources.json` and reproducible file hashes to `evidence/files.json`. Add a finding with exact claim, scope, confidence, source path/line range or binary hash/offset, validation and limitations. Record contradictory evidence in `evidence/contradictions.json`. A source-text observation may be verified while its applicability to ATM7039S remains inferred.

Edit register definitions only in `registers/canonical/hardware.json` or improve the reproducible extraction in `tools/build_dataset.py`; run the generator afterward. Never edit generated CSV, Markdown or headers by hand. `candidate:` entries are related-chip leads and must not be treated as safe MMIO definitions. Preserve unknown width/access/reset/field semantics rather than fill them from naming conventions.

Hardware-derived findings need an observation record in `evidence/observations.json` (schema in `evidence/schemas/observations.schema.json`), produced with a known version of `device/capture.sh` or another documented procedure. They also need explicit permission, procedure, equipment, artifacts, firmware identity and observed result. No live MMIO writes, power changes, boot modifications or SD-card experiments are authorized by this repository. The owner's failing factory card and working GarlicOS card are excluded from experimentation.

Do not contribute firmware binaries, libraries, ROM dumps, copied manuals or disassembly with uncertain redistribution rights. Link and provide extraction instructions instead. Keep third-party notices when importing licensed source; this initial release deliberately imports no driver source.

Before submitting:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/research.py validate
python tools/research.py generate --check
python tools/render_html.py
```

CI checks structural integrity and reproducibility; passing CI cannot establish a hardware fact.
