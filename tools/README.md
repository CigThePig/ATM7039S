# Reproducible offline analysis tools

Python 3.11+ is sufficient for extraction. Schema validation requires `jsonschema`; HTML rendering also requires `Markdown`. Install the pinned dependencies in a virtual environment:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

All tools read ordinary files. They do not open block devices, mount images, execute input files, perform ADB operations, flash firmware or access the handheld. The analysis CLI accepts files up to 512 MiB; extract components from larger archives first. Source retrieval is a separate explicit network command with a 32 MiB per-file limit and exact hash verification.

## Commands and outputs

| Command | Input | Output / behavior |
|---|---|---|
| `research.py tree input output.json` | Flattened numeric DTS or v17+ FDT | Nodes, raw properties, source lines or offsets, compatible/status/dependencies, parent-bus reg tuples and reservations |
| `research.py constants input.h output.json` | C source/header | Resolved integer definitions, masks, expressions, exact lines; unresolved definitions retained |
| `research.py firmware component output.json` | Ordinary file | SHA-256, length, MBR entries/bounds, embedded FDT candidates, legacy uImage CRC/load metadata and ELF identities |
| `research.py compare left.json right.json diff.json` | Two tree outputs | Byte-normalized property differences; ignores ordering/line/DTB-offset metadata |
| `compare_layouts.py left.json right.json output.json` | Two tree outputs | Numeric base matches with sizes/IRQ differences preserved; no compatibility assertion |
| `research.py validate` | Repository ledgers and canonical data | Schema, source IDs, duplicates, confidence checks; overlap/alias warnings |
| `research.py generate [--check]` | Canonical hardware JSON | Register Markdown, CSV, candidate C header; `--check` fails on stale outputs |
| `audit_sources.py inputs` | Retrieved input files | Checks file hashes/sizes and evidence path/line bounds |
| `fetch_sources.py inputs` | Pinned manifest + public URLs | Downloads exact input files; aborts on size/hash mismatch; does not execute them |
| `build_dataset.py inputs` | Pinned source checkouts or manifest-verified files | Rebuilds source-derived tree/register/artifact datasets and generated reference |
| `render_catalogue.py` | Source/findings JSON | Human-readable evidence indexes |
| `render_html.py` | Maintained Markdown | Local `site/` HTML; no deployment/publication |

DTS support deliberately excludes unexpanded includes, macros, overlays and phandle labels in values. Use a real DTC for those. Numbers in flattened cells are decoded with immediate parent `#address-cells`/`#size-cells`. The tool does not translate `ranges`, derive Linux IRQ numbers, infer register semantics, or decide whether a parent node disables a child. Full raw node properties preserve these dependencies for review. FDT string interpretation is conservative; unknown properties remain cells/bytes. Property comparison normalizes bytes rather than assuming their semantic type.

The constant extractor is not a C preprocessor. It handles literal arithmetic, references, shifts, bitwise expressions, `BIT` and `GENMASK`; function-like macro definitions, complex expressions and unresolved conditions remain unresolved. It reports source definitions across branches, not necessarily the active compiled configuration. Never treat an unrelated definition containing `BASE` as target silicon evidence.

The firmware scanner checks structure, not trust. ELF results validate identity only. GPT, filesystem extraction, decompression, new FIT/uImage formats and code decompilation are not implemented. It does not reconstruct function behavior from magic bytes. The present artifact database contains standalone components, not a complete firmware image.

## Rebuild the source-derived database

Use an external scratch directory, excluded from commits:

```sh
python tools/fetch_sources.py /path/to/inputs
python tools/audit_sources.py /path/to/inputs
python tools/build_dataset.py /path/to/inputs
python tools/research.py generate --check
python tools/render_catalogue.py
python -m unittest discover -s tests -v
```

`build_dataset.py` verifies repository HEADs when given full clones, or all corresponding manifest hashes when given individual files. The curated claims/contradictions and independently compiled mainline comparison are maintained separately; rebuilding the extracted map does not rewrite scientific judgments.

## Independent DTC validation and mainline comparison

A DTC was built from the pinned vendor kernel's shipped parser/lexer sources, using host GCC with `-fcommon`. The following equivalent commands require that checkout and a host C compiler:

```sh
mkdir -p /path/to/dtc-build
cp /path/to/s500_kernel/scripts/dtc/dtc-parser.tab.h_shipped /path/to/dtc-build/dtc-parser.tab.h
gcc -fcommon -O2 -I /path/to/dtc-build -I /path/to/s500_kernel/scripts/dtc -I /path/to/s500_kernel/scripts/dtc/libfdt /path/to/s500_kernel/scripts/dtc/{dtc,flattree,fstree,data,livetree,treesource,srcpos,checks,util}.c -x c /path/to/s500_kernel/scripts/dtc/dtc-lexer.lex.c_shipped /path/to/s500_kernel/scripts/dtc/dtc-parser.tab.c_shipped -o /path/to/dtc-build/dtc
/path/to/dtc-build/dtc -I dtb -O dts /path/to/2100mAh-gpu.dtb -o /path/to/decoded.dts
python tools/research.py tree /path/to/decoded.dts /path/to/independent.json
python tools/research.py compare evidence/batocera-2100-tree.json /path/to/independent.json /path/to/difference.json
```

The observed `difference.json` is `[]`. This validates the custom decoder's property output against DTC on this artifact, not the board's electrical behavior.

For the mainline S500 comparison, prepend `/dts-v1/;` to the pinned `arch/arm/boot/dts/actions/owl-s500.dtsi`, preprocess with host `cpp -nostdinc -undef -D__DTS__ -x assembler-with-cpp -I /path/to/linux/include`, then compile using DTC. Bindings under `include/dt-bindings/` must be available. Parse the resulting FDT with `research.py tree`, then use `compare_layouts.py`. The saved output is `evidence/mainline-s500-tree.json`; source revision is in `sources.json`. The synthetic standalone FDT is not a bootable RG35XX DTB.

## Errors and tests

Malformed/truncated FDTs, invalid reg geometry, unsupported flattened DTS syntax, duplicate properties, hash mismatches and stale generated files fail explicitly. Unit tests generate representative binary fixtures in memory, including valid/invalid uImages, FDTs and MBR entries, and also check differences against the real extracted board datasets. `unittest discover -s tests -v` and CI execute the tests without network or hardware access.

## Runtime capture tools

| Tool | Purpose | Deliberate limits |
|---|---|---|
| `device/capture.sh [PARENT]` | POSIX/BusyBox read-only collector for test V3; `--list` prints the allowlist | Fixed allowlist only; writes only its own output folder; no `/dev/mem`, I2C, power_supply, debugfs or writes |
| `runtime_capture.py CAPTURE OUT` | Verifies item hashes, script version and allowlist; parses CPU/memory/storage/display/config/FDT; links kernel and DTB to catalogued firmware; CPU outcome hint | Hints are not findings; a capture describes one boot of one board |
| `evidence/predictions.json` | Pre-registered outcomes for each V3 question; the parser may only return a declared outcome | Outcomes are hints for review, not findings |
| `validate_observations.py` | JSON Schemas for sources/findings/contradictions/observations; observation-to-firmware/tool/summary links; hardware findings must cite observations | Called by `research.py validate`; checks records, not the truth of observations |

Tests run the real script against a synthetic export tree (`ATM_CAPTURE_ROOT`) and check tampering, allowlist drift, unknown script versions, prediction outcomes, serial-number/MAC redaction and ledger links. See the [operator guide](../device/README.md).

## Full-image continuation tools

See [firmware reproduction](../reports/firmware-analysis.md) for exact commands and pinned public inputs. Install optional dependencies in an isolated venv with `requirements-firmware.txt`; ordinary evidence validation and unit tests do not require network or firmware downloads. CI installs these dependencies to exercise a synthetic FAT image as well.

| Tool | Purpose | Deliberate limits |
|---|---|---|
| `acquire_firmware.py SOURCE OUT [--expand]` | Stream hash/size-pinned release assets; exact bounded gzip expansion | 8 GiB ceiling; never overwrites existing files or auto-extracts ZIP members |
| `firmware_catalogue.py IMAGE PLAN OUT [--extract DIR]` | Stream whole-image SHA, strict primary MBR, selected raw/uImage/FAT files | 32 MiB selected files, partition-bounded read-only FAT; rejects GPT/extended MBR |
| `rootfs_catalogue.py IMAGE PLAN OUT [--extract DIR]` | Hash nested ext4 rootfs, selected regular inodes, ELF metadata | No mount, symlink output, recursive extraction, native execution or library loading |
| `boot_payloads.py COMPONENT OUT` | Bounded internal gzip identification, expanded hashes/version strings | 64 MiB per stream, max 256 candidates; no claimed behavior from strings |
| `arm_refs.py COMPONENT OUT --start N --end N` | A32 direct branches and PC-relative word literals | Offset coordinates; not a disassembler or code/data classifier; no Thumb support |
| `kallsyms.py IMAGE OUT [--symbols FILE]` | Recover the 3.x absolute-address kallsyms table from a decompressed ARM Image; summary with name-set hash | Heuristic table location; validated against a build System.map; no Thumb/relative-base layouts; not a disassembler |
| `validate_firmware.py` | Binary finding hash/range links and manifest integrity | Checks retained evidence, not hardware or availability of external inputs |

The S500 CMU comparison fields are curated in `comparisons/cmu-fields.json` and applied by build_dataset.py without promoting target register reset/access values. Regeneration now preserves extra curated source/file provenance records; the previous builder would have silently dropped new records outside its fixed extraction list. This correction has a regression test.
