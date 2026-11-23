# ATM7039S independent technical reference

A source-controlled research foundation for the Actions ATM7039S, using the **original 2022–2023 Anbernic RG35XX** as the board reference. Newer H700-based RG35XX models are outside scope.

**Status: research edition 0.1, 2026-11-22.** This is a partial manual backed by source evidence, not a complete silicon specification or tested operating-system port. No handheld, SD card, live hardware register or power setting was accessed. No firmware/library/manual binaries are redistributed. The repository was already public when this work began; its visibility was preserved.

## Start here

- [Technical reference manual](docs/technical-reference.md): 30 scoped sections, known resources and explicit unknowns.
- [Research summary](reports/research-summary.md): answers to the project's ten technical questions and work not completed.
- [Source catalogue](evidence/catalogue.md) and [findings ledger](evidence/findings.md): exact revisions, paths, line ranges, hashes, confidence and limitations.
- [Coverage matrix](reports/coverage-matrix.md), [knowledge gaps](reports/knowledge-gaps.md) and [next investigations](reports/next-investigations.md).

## What is established

Manufacturer-origin evidence explicitly distinguishes ATM7039S from ATM7039. Public board artifacts and related source provide useful resource maps, but their compatibility strings do not prove silicon equivalence. The related S500 manual and mainline drivers are valuable comparison sources; target applicability must be demonstrated block by block.

This edition records:

| Research product | Scope |
|---|---|
| 51 DT resource tuples | Software declarations; includes shared/auxiliary resources |
| 72 candidate header base groups / 1,760 register symbols | Explicit ATM7039-labelled source definitions; ATM7039S applicability inferred |
| 35 findings / 9 contradictions | Confidence and source scope retained |
| 17 sources / 65 hashed files | Pinned input provenance, not 65 independent hardware measurements |
| 9 changed DT nodes | Gist versus published 2100mAh GPU DTB |
| 26 matching numeric resource pairs | Against mainline S500; not 26 proven compatible peripherals |
| 2 public binary components inspected | DTB and historical module; no whole release image analyzed |

A manufacturer-branded **329-page S500 document** was found and catalogued, with an [inspection guide](reports/related-manual.md). It is not an ATM7039S manual. SGX544 research from reMESA was also located and attributed; its maintainer distinguishes research from a demonstrated independent SGX544 renderer.

## Deliverables

| Requested artifact | Maintained location |
|---|---|
| Technical manual | [docs/technical-reference.md](docs/technical-reference.md) |
| Machine-readable register map | [canonical JSON](registers/canonical/hardware.json), [schema](registers/schemas/hardware.schema.json), [generated reference](registers/generated/reference.md), [CSV](registers/generated/registers.csv), [candidate C constants](registers/generated/candidates.h) |
| Source/evidence database | [sources](evidence/sources.json), [files](evidence/files.json), [findings](evidence/findings.json), [contradictions](evidence/contradictions.json), [artifacts](evidence/artifacts.json) |
| Family compatibility analysis | [family matrix](comparisons/chip-family.md), [mainline comparison JSON](comparisons/rg35xx-vs-mainline-s500.json), [DT changes](comparisons/gist-vs-batocera-2100.md) |
| Boot-chain documentation | [boot and dependencies](docs/boot-chain.md) |
| Linux compatibility report | [driver assessment](reports/linux-compatibility.md), [structured report](reports/linux-compatibility.json) |
| Reusable tools | [commands, installation and reproduction](tools/README.md) |
| Coverage/gaps | [coverage](reports/coverage-matrix.md), [gaps](reports/knowledge-gaps.md) |
| Hardware validation plan | [proposed tests; none executed](reports/hardware-validation-plan.md) |
| Continuation roadmap | [ranked tasks](reports/next-investigations.md) |

## Reproduce and validate

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/research.py validate
python tools/research.py generate --check
python tools/render_catalogue.py
python tools/render_html.py
```

Open `site/index.html` for the local HTML edition. It is generated locally/through CI; no website is deployed. Machine-readable data accompanies the HTML. Mermaid diagrams render on GitHub; the standalone HTML preserves diagram source and surrounding explanatory tables.

The [validation report](reports/validation-results.md) records executed checks. Source acquisition is separate and opt-in: `python tools/fetch_sources.py /path/to/inputs`, followed by `python tools/audit_sources.py /path/to/inputs` and `python tools/build_dataset.py /path/to/inputs`. Acquired third-party inputs stay outside commits. See the tool guide for parser limitations and independent DTC reproduction.

## Reading confidence correctly

A **verified source observation** means a file or manufacturer statement actually contains the claimed information. It is not a hardware test. Related-chip definitions remain candidates even when multiple sources agree. Unknown access types, reset values, widths, package pins and electrical limits are left unknown. No percentage of the processor is claimed documented.

Do not run the generated constants against hardware. This phase authorizes offline research only; future hardware procedures require explicit approval. The owner's working GarlicOS card and failing factory card are excluded from experiments.

## Licensing and attribution

Original tools, documentation and arrangement use [MIT](LICENSE). This does not relicense referenced source, documentation or binaries. Read the [source audit](reports/licensing.md) before importing or redistributing anything.

This builds on work by macromorgan, Yohanes Nugroho/Tinyhack, rg35xx-cfw and KNULLI contributors, Actions, Imagination, upstream Linux contributors and Gama/reMESA. Contributions should preserve their provenance and distinguish existing knowledge from new analysis. See [CONTRIBUTING.md](CONTRIBUTING.md).
