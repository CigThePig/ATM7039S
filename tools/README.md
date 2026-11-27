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
| `device/capture.sh [PARENT]` | POSIX/BusyBox read-only collector for test V3 (script version 3); `--list` prints the allowlist | Fixed allowlist only; size-bounded reads; per-item status; device tree only from approved kernel paths; writes only its own new output folder; no `/dev`, I2C, power_supply, debugfs or writes |
| `runtime_capture.py CAPTURE OUT [--report MD] [--reference-dtb DTB]` | Authenticates the capture (script hash, version, allowlist, manifest, item hashes, `DONE`, write failures) or quarantines it; reads the device-tree tar without extracting it; structural DT, memory, boot-argument and storage models; evaluates every prediction; redacted JSON and Markdown | Hints are not findings; a capture describes one boot of one board |
| `v3_preflight.py [--image] [--archive] [--boot-dir] [--share-dir] [--boot-region / --windows-boot-letter / --card-device] [--json]` | Offline go/no-go: registered script and safety lint, pinned image and every catalogued component, `SFVD` marker, BusyBox applets, prepared-card files, raw card head | Verification only; never writes to an image or card |
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

## Stock-firmware and binary-analysis tools

Install `requirements-dev.txt`, `requirements-firmware.txt` and `capstone==5.0.6` in an isolated venv. RAR extraction needs `bsdtar` (libarchive) or `unar`. Ghidra is optional (11.4.2 headless with JDK 21 was used). Every tool reads ordinary files, writes only new outputs, and never executes input code. Tests use synthetic fixtures (`tests/test_stock_tools.py`).

| Tool | Purpose | Deliberate limits |
|---|---|---|
| `acquire_firmware.py SOURCE OUT [--filename F] [--expand]` | Now also expands ZIP/RAR/7z by one pinned `expanded_member`, checked against the expanded SHA-256; `--filename` selects among several entries of one source; `max_bytes` raises the 8 GiB ceiling per entry | One named member only; never auto-extracts archives |
| `archive_members.py list/extract` | Safe member listing and single-member streaming extraction (zipfile; bsdtar → unar → 7z fallback for RAR) | Rejects traversal, absolute/backslash/drive names, duplicates, symlinks/devices, oversize; deletes partial output |
| `image_inventory.py IMAGE OUT [--summary-only P] [--include P:/prefix] [--allow-truncated] [--extract LIST DIR]` | MBR or GPT (CRCs, backup header, bounds, overlap), hashed raw regions with signatures, full FAT/ext file hashing, bounded extraction verified against the inventory hash | Truncated GPT images need an explicit flag; partitions past the end are listed, not read; out-of-scope partitions can be counted only |
| `actions_loader.py REGION OUT` | Actions raw-loader parser: ActBrm trailer checksum rule, PACK directory, `bootloader.ini` DRAM/UART record | Layout recovered from observed releases, not a vendor spec |
| `mmio_refs.py COMP OUT --load A [--range S:E] [--io-map V:P:S] [--functions F]` | Capstone A32/T32 sweep with constant propagation; MMIO loads/stores and accessor call arguments; canonical-model name lookup with ambiguity flag | Dataflow reset at branch targets and calls; candidates, not proven executions |
| `map_accesses.py REFS OUT --block L:BASE:HDR:STRUCT[:SPAN] [--write/read/set/clear/rmw-helper ...]` | Names accesses from a public C register struct, in program order, with declared helper semantics | u32/array/nested-struct members only; names are layout hypotheses |
| `kernel_compare.py A SYMS_A B SYMS_B OUT` | Function sets, sizes and normalised-body equality (A32 branch immediates and kernel-VA literals masked), GCC-suffix-normalised name diffs | Sizes are upper bounds; body inequality is not behavioural difference |
| `ghidra_headless.py COMP OUT --ghidra DIR --base A [--entry E]` + `ghidra/*.java` | Throw-away Ghidra project; exports function extents, call edges and window constants | Never exports decompiler output or disassembly text |
| `apply_firmware_registers.py` | Idempotently merges `registers/curated/firmware-observations.json` into the canonical model (also run by `build_dataset.py`) | Never sets widths, access, reset or hardware validation |

### DRAM timing reconstruction (2026-11-25)

Needs `unicorn` and `z3-solver` (pinned in `requirements-firmware.txt`) besides Capstone. See [the report](../reports/ddr-timing-reconstruction.md).

| Tool | Purpose | Deliberate limits |
|---|---|---|
| `ddr_emulate.py REGION OUT [--image-offset 0x200200] [--scenario S] [--reset-seed N] [--record firmware\|primary\|second]` | Bounded Unicorn emulation of the loader's ini copy, record selection, DRAM routine `0xb40673f4` and write-back; logs every MMIO write with its firmware call site, every read with the oracle rule that answered it, and the console lines | ≤ 2 M instructions; delay and printf stubbed; peripheral reads come from declared oracle rules and named hardware hypotheses, never from hardware |
| `ddr_symbolic.py REGION OUT [--clock-range LO:HI] [--evaluate-clock C]` | Own A32 interpreter over Capstone with z3 terms; clock symbolic; forks on input-dependent branches and reports each path's clock intervals and per-write expressions | Implements only the instruction classes used (raises otherwise); division helpers modelled and validated separately |
| `ddr_model.py` (library) | Readable DDR3 model: named timing quantities, packed registers and the full write sequence with provenance class, formula and call order; `run(rec, hw, mode=1)` models the resume pass (PR #6) | DDR3 branch only; hardware outcomes and reset values are explicit inputs |
| `ddr_timing.py OUT --loader NAME=PATH \| --image NAME=PATH [--sweep-step N] [--no-symbolic]` | Runs all three, sweeps clocks, hardware hypotheses and reset seeds, classifies each write differentially, compares releases; writes `stock-ddr-timing.json` | Output holds values, formulas and addresses only; no firmware bytes or disassembly |

```sh
python tools/ddr_timing.py evidence/firmware/stock-ddr-timing.json --loader stock-221203=loader-221203.bin \
  --loader stock-221223=loader-221223.bin --loader stock-230309=loader-230309.bin --image stock-20231014=stock-20231014.img
ATM7039S_STOCK_LOADERS=DIR python -m unittest tests.test_ddr_timing -v
```

Reproduce the stock analysis from an externally supplied image (hashes in `evidence/firmware/acquisitions.json`):

```sh
python tools/image_inventory.py stock-20231014.img inv.json --include ROMS:/CFW
python -c "f=open('stock-20231014.img','rb');f.seek(0x200200);open('loader.bin','wb').write(f.read(448*512))"
python tools/actions_loader.py loader.bin loaders.json
python -c "open('bootloader.bin','wb').write(open('loader.bin','rb').read()[:0x33c00])"
python tools/mmio_refs.py bootloader.bin refs.json --load 0xb4060000 --range 0x0:0x400 --range 0x2400:0x3800 --range 0x5400:0x19000
python tools/map_accesses.py refs.json ddr.json --block uPCTL:0xb01c0000:ddr_rk3288.h:rk3288_ddr_pctl:0x8000 \
  --block PUBL:0xb01c8000:ddr_rk3288.h:rk3288_ddr_publ:0x8000 --write-helper 0xb40670e8:r0:r1 --read-helper 0xb40670f0:r0 \
  --clear-helper 0xb4067120:r0:r1 --set-helper 0xb4067140:r0:r1 --rmw-helper 0xb40670f8:r0:r1:r2
```

Compare outputs with `evidence/firmware/stock-loaders.json` and `stock-ddr-sequence.json`. The kernel scans use `--load 0xc0008000 --io-map 0xf8000000:0xb0000000:0x04000000` with function boundaries from `kallsyms.py`.

### Stock boot-chain reconstruction (PR #5)

Needs `capstone`, `unicorn` and `pyfatfs` (`requirements-firmware.txt`). See [the report](../reports/stock-boot-chain-reconstruction.md).

| Tool | Purpose | Deliberate limits |
|---|---|---|
| `boot_chain.py analyze IMAGE OUT --release NAME [--sha256 H] [--ram-mib N \| --dram-scenario NAME]` | Re-derives the chain from one image. Anchors are strings and literals, not fixed addresses. Emulates loader block 0 (per clock-bit hypothesis), bootloader.bin main to the app.bin jump (ROM read service served from the image), the boot-code→AFI map, U-Boot `check_boot_flag` with real getters, the bootargs helper, `owl_boot_fdt_setup` and `image_setup_linux` on the shipped DTB. Static decoding covers env storage, `init_sequence_r`, `boot_jump_linux`, `cleanup_before_linux`, strap and autoboot. Data parsing covers GPT/MBR, FAT boot files, uImage and uEnv | Every emulation lists its models. Unmodelled MMIO reads abort. DRAM outcome is a parameter, or derived from the loader's own DRAM code under a named synthetic `dram_complete.py` scenario. app.bin is analysed statically only |
| `boot_chain.py compare A.json B.json … OUT` | Component hashes and boot-behaviour equality across releases | Equality of traced behaviour, not of whole binaries |
| `boot_chain.py sfvd IMAGE` | Reports the `SFVD` marker at disk `0x202a00`; exit 1 means app.bin would rewrite the 20-sector `bootloader.ini` region on boot (BOOT-014) | Byte check of the stock loader layout only |
| `boot_chain.py trace A.json … OUT` | Builds `evidence/firmware/stock-boot-chain.json`: stages S0–S7 (component hash, function, inputs with disk offsets, destinations, lengths, validation, transition, method, confidence), comparison and compacted per-release results | Stock releases form the comparison; other firmware is reported separately |

Tests: `tests/test_boot_chain.py` covers hand-encoded A32 fixtures (call tracking, string anchors, a synthetic `check_boot_flag` executed with its getter, emulator MMIO/stub rules) and evidence consistency. Set `ATM_FIRMWARE_DIR` to a folder holding the pinned `stock-*.img` / `koriki-v1.0.img` to re-derive the committed evidence (about 30 s).

### DRAM subsystem completion (PR #6)

| Tool | Purpose | Limits |
|---|---|---|
| `dram_complete.py evidence OUT --loader NAME=PATH … [--quick]` | Extends the PR #4 Unicorn harness: the DRAM caller `0xb40665d0` end to end (PMIC register file behind the loader's I2C accessors), the resume path `0xb40664e4`/`0xb4067094`/mode 1, the memory test `0xb406631c` on sparse fault-injectable RAM, explicit PUBL/uPCTL failure scenarios, the LPDDR branch, a DMM decode geometry study and the DRAM → AFI → U-Boot handoff; independent models for mode 1 and the memory test. Writes `stock-dram-complete.json` | Every PMIC, PUBL, uPCTL and DRAM response is synthetic and logged; unbounded firmware polls are reported, not resolved. About 4 minutes per release |
| `dram_complete.py resume LOADER --case NAME` / `memtest LOADER --capacity N --ram wrap:MiB` | One resume case or memory-test run, as JSON | Same models |

Tests: `tests/test_dram_complete.py` (models, boundary values, committed evidence, harness RAM/fault mechanics on hand-encoded A32). `ATM7039S_STOCK_LOADERS=DIR` re-runs the firmware-backed comparisons.

### Pre-DRAM reconstruction (PR #9)

| Command | What it does | Limits |
|---|---|---|
| `predram_analysis.py evidence OUT --image NAME=IMG … [--reference NAME]` | Verifies each whole image against the acquisition manifest and builds a recursive-descent call graph from `0xb4065400` to the DRAM boundary `0xb40690b8`, with constant tracking, boot-code references, annotated bit-indexed helpers and instruction-anchored structure facts. It runs bounded Unicorn traces of main for boot codes 0/2 and a few scenarios (seed, loopback, handshake off, PMIC status), re-runs `dram_complete.run_caller` for codes 0/2 and compares releases. Writes `evidence/firmware/sd2-predram.json` (deterministic) | Static reachability is not execution. Every peripheral read follows a named synthetic rule. Stubs only printf, the Boot ROM read service and the I2C transaction layer. About 10 s per release |
| `predram_analysis.py trace IMG --boot-code N [--scenario loopback]` / `graph IMG` | Readable event list / call graph for one image | Same models |

Tests: `tests/test_predram.py` covers synthetic A32 fixtures (calls, tail calls, indirect calls, branches, constant tracking, data words, hangs, unsupported jumps, helper formulas, MMIO rules) and the committed evidence. `ATM_FIRMWARE_DIR=DIR` regenerates the evidence and checks helper formulas against execution.

### ADFU loopback (PR #9, part 2)

| Command / API | What it does | Limits |
|---|---|---|
| `adfu_analysis.py evidence OUT --sources SRC --image NAME=IMG …` | Hash-verifies images and the routine's regions. Checks 46 instruction anchors. Runs 41 routine-level scenarios of `0xb4069254` against an independent `reference_model`, plus a stalled-timer run, whole-path runs of main, `dram_complete.run_caller(boot_code=2, gpio=…)` and the bounded `0xb40691a4` re-entry. Surveys the pinned vendor pinctrl/DTS/header lines and the shipped DTBs. Writes `evidence/firmware/adfu-loopback.json` (deterministic) | Synthetic GPIO/PMIC/timer responses. Model and reference share the GPIO assumptions. ROM code is never invented. About 2 minutes |
| `adfu_analysis.py run IMG --boot-code N --arg A --pmic S --input const0\|const1\|follow\|invert\|delay\|prbs:SEED` | One scenario with its firmware/reference comparison | Same |
| `gpio_model.GpioModel(initial=…, inputs={pin: rule}, read_semantics='mixed'\|'latch', strict=True)` | Synthetic GPIO/pad window for `predram_analysis.Trace(gpio=…)` and `dram_complete.Harness/run_caller(gpio=…)` | Every assumption in `GpioModel.assumptions()` |

Tests: `tests/test_adfu_analysis.py`. `ATM_FIRMWARE_DIR` re-runs scenarios. With `ATM_SOURCES_DIR` as well, it regenerates the whole evidence file.

### V3 operator recovery

**The lab (Windows/Linux; macOS uses the manual procedure)** (`ATM7039S-Lab.cmd`, `start-lab.sh` → `lab_launch.py` → `python -m v3lab`) runs the whole computer side of a V3 session; see [v3lab/README.md](v3lab/README.md). `boot_chain.py boot-path IMAGE OUT --release R --observation evidence/observations/OBS-001.json` executes every boot-device hypothesis end to end and compares the resulting command line with an observation ([report](../reports/sd2-boot-path-reconciliation.md)). `v3_preflight.py --phase auto|fresh|prepared|post-capture [--image] [--baseline]` checks the card's root filesystem by byte hash before the first boot and semantically afterwards. `v3_rootfs_review.py --phase prepared|post-capture` (3.0) is the stand-alone form of that check with a private report in `lab-data/rootfs-review/`; the 2.x diagnostic used during OBS-001 is superseded (its report stays as evidence). `v3_operator.ps1` is a legacy fallback.

## SD2 DRAM caller comparison

`sd2_dram_analysis.py` executes the DRAM caller and main's continuation decision in Unicorn with new synthetic PMIC, RAM, GPIO and training state for each boot code. `--firmware-dir FW` selects a directory of hash-pinned expanded images. The evidence command verifies all five images; the other execution commands accept `--release` and default to Koriki v1.0.

```sh
python tools/sd2_dram_analysis.py list
python tools/sd2_dram_analysis.py run --firmware-dir FW --scenario reference --detail
python tools/sd2_dram_analysis.py run --firmware-dir FW --scenario mixed-gpio-resume --boot-code 2
python tools/sd2_dram_analysis.py suite --firmware-dir FW --release stock-20231014 --group resume
python tools/sd2_dram_analysis.py evidence --firmware-dir FW OUT.json
```

`run` without `--boot-code` compares both paths. The `run` and `suite` commands support repeatable `--mmio ADDRESS=WORD` and a stage `--limit`. `suite --group` accepts `cold`, `resume`, `memory`, `gpio`, `geometry`, `control` or `all`. The [report](../reports/sd2-dram-reconstruction.md) explains each terminal outcome, raw trace and result field. Set `ATM_FIRMWARE_DIR=FW` to enable the optional five-release evidence regeneration tests in `tests/test_sd2_dram_analysis.py`.

## Unified boot chain

`unified_boot_chain.py` verifies a locally available pinned image and follows the supported SD path through the pre-kernel boundary. Run `python tools/unified_boot_chain.py list` for releases and scenarios. Use `run --firmware-dir FW --coverage --compare-obs` for the reference, `run --detail --output trace.json` with a firmware directory for local events and snapshots, and `evidence --firmware-dir FW OUT.json` to regenerate the combined results. [Architecture and command details](../docs/boot-chain-emulation.md)

## Bootloader initialization contract

| Command | Purpose |
|---|---|
| `python tools/bootloader_contract.py generate` | Generate the structured contract and Markdown operation reference from the curated source and pinned evidence |
| `python tools/bootloader_contract.py validate` | Check deterministic outputs, evidence and operand references, conditional edges, event order, terminal paths and delivered state |
| `python tools/bootloader_contract.py compare` | Show configuration and selected reference results across the five pinned releases |
| `ATM_FIRMWARE_DIR=FW python tools/bootloader_contract.py replay --check` | Execute 16 selected cases from pinned expanded images and compare the ordered artifact byte for byte |

The `replay` command without `--check` regenerates the trace. Ordinary validation runs without firmware or emulator dependencies. [Reproduction and scope](../docs/bootloader-initialization-contract.md#18-dependencies-provenance-and-reproduction)
