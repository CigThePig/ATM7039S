# Bootloader initialization contract: corrective verification

This report records the correction of the independently reviewed [initialization contract](../docs/bootloader-initialization-contract.md). It establishes which of its statements agree with the firmware research, and states what each automated check protects. The working [correction log](bootloader-contract-correction-log.md) keeps the chronological record. All work was offline. No hardware, card, block device, UART or recovery mode was touched.

## 1. Reviewed revision and scope

| Item | Value |
|---|---|
| Reviewed revision | `984d2232c6d783762b1d3cef2c8fc5edb6448ac9` on `sd2-predram-reconstruction` |
| Branch state before work | Equal to the reviewed revision; no finding had been addressed |
| Scope | Specification semantics, validator, generated artifacts and documentation. Firmware model, historical evidence and the raw ordered timeline are unchanged |
| Firmware used | `koriki-v1.0` (`d5bd3007…d6ae`) and `stock-20231014` (`e5f61b7d…6ec8`), whole-image hashes verified by `acquire_firmware.py`. Their DRAM routines `0xb40673f4..0xb40690d0` are byte-identical |
| Pinned sources | Three Linux files and two Actions U-Boot AFI files fetched at ledger revisions; all git blob SHA-1 values and line bounds verified |

## 2. Dispositions of the six findings

| # | Finding | Status | Automated protection |
|---|---|---|---|
| 1 | Bus selector 0 described as automatic x32 then x16 | **Confirmed and corrected** | `semantics.dram-bus` is compared with 240 loader executions, 12,224 `ddr_model` runs and historical SD2 runs; mutation `rules[0].automatic_width_fallback = true` fails |
| 2 | Capacity formula used the raw bus selector | **Confirmed and corrected** | `semantics.dram-capacity` uses `capacity_width_operand`. Mutation `{"32": 0}` yields 128 MiB for x32 and fails against the model and firmware rows |
| 3 | Validator lacked semantic checks | **Confirmed and corrected, with stated limits** | `tools/contract_semantics.py` checks DRAM selection, retry, capacity, record layout, timing inputs, AFI, SRAM, static instructions, FDT reservation and pinned sources against independent references (§6) |
| 4 | Missing trace boundaries silently broadened checks | **Confirmed and corrected** | Named windows fail when a boundary is absent, ambiguous or reversed; RLE runs are clipped. The invalid-INI timer check uses an explicit `caller-finishing` alternative |
| 5 | First-occurrence ordering across DRAM retries | **Confirmed and corrected** | Attempt-local validation of 14 DRAM edges, required/forbidden operations per outcome, and retry prediction from the input record |
| 6 | Negative state assertions counted as execution | **Confirmed and corrected** | `Observation` separates execution, value and absence. Regression: requiring `linux-entry` on `cold-failed` now fails with `terminal branch missing linux-entry` |

## 3. Finding 1: bus-width selection

Instructions of the verified loader, cold mode only (resume flag `[0xb4070804]` zero):

```text
0xb4067434  ldrb r2, [r4, #4]        input selector (INI +0x24 / +0x54)
0xb406743c  sub lr, r2, #1
0xb4067440  cmp r2, #2 ; movlo r3, r2 ; movhs r3, #2 ; str r3, [sp, #0x40]   retained = min(input, 2)
0xb4067450  rsbs ip, lr, #0 ; adc fp, ip, lr ; strb fp, [r4, #4]            working = (input == 1)
0xb4068f58  cmp r1, r5 (0x1017fa11)  only the training error reaches the retry test
0xb4068fac  rank retry when [sp+0x30] == 0 and working cs == 2
0xb4068fd8  width retry when [sp+0x40] == 2 and working byte == 0; cs := 2 if ranks automatic
0xb4069020  persistent failure: cs byte := [sp+0x30], bus byte := [sp+0x40]
```

| Input selector | Initial width | Automatic fallback | Working byte | Byte after persistent training failure |
|---|---|---|---|---|
| 0 | x32 | no | 0 | 0 |
| 1 | x16 | no | 1 | 1 |
| 2..255 | x32 | yes, to x16 | 0, then 1 | 2 |

The ranks rule is: 1 or 2 fixed, 0 and 3..255 automatic (two, then one), with a failure write-back of the input when ≤ 2 and 0 otherwise. Rank retry precedes width retry, and a width retry restarts automatic ranks at two. With every attempt failing, input bus 2 / cs 0 tries (2,x32), (1,x32), (2,x16), (1,x16); bus 0 / cs 0 tries (2,x32), (1,x32) and returns `0x1017fa11`.

Firmware-backed check: 96 selector rows per release (bus 0, 1, 2, 3, 0x80, 0xff × cs 0–3 × synthetic x16/x32 × one/two ranks). In all 192 rows the attempts, return code and final working bytes agree with the structured rules. Every selector-0 row on x16-only hardware fails after x32 attempts only. The independent model agrees on attempt order and success across 256 bus values × 6 cs values and 256 cs values × 5 bus values for four hardware cases. The model does not implement the failure write-back. That property is verified against the firmware rows and the historical `training-failure` record (`cs = 0`, `bus = 1`).

## 4. Finding 2: capacity arithmetic

Instructions `0xb4068df8..0xb4068e70`:

```text
e = (rcc >> 6) + ((rcc & 0xc) >> 2) + 0x18 + (working ? 1 : 2) + (cs - 1)     movne ip,#1 / moveq ip,#2
e > 31  -> internal 0xc000fa11, returned 0x1747fa11
bank code 0: ((0x10000 << (e - 20)) >> 16) MiB = 2^(row + col + operand + cs + 3)
bank code 1..3: (((3 << (e - 20)) << 14) >> 16) MiB = 3 * 2^(row + col + operand + cs + 1)
```

Names: `input_bus_selector` (INI byte), `retained_selector` (`[sp+0x40]`), `working_bus_selector` (record +4), `bus_width_bits` (32 for working 0, 16 for 1), and `capacity_width_operand` (1 for x16, 2 for x32, also the density divisor). The operand differs from the working selector for x32 (2 versus 0). The shipped x16 reference concealed the error because both equal one.

| Case (firmware rows) | Result |
|---|---|
| row 1, col 2, x16, 1 rank | 256 MiB |
| row 1, col 2, x32, 1 rank | 512 MiB |
| row 1, col 2, x16, 2 ranks | 512 MiB |
| row 1, col 2, x32, 2 ranks | 1024 MiB |
| Minimum: probe of an 8-column/13-row device, x16, 1 rank | 32 MiB (e = 25) |
| Maximum accepted: rcc `0xcc`, x16, 1 rank | 2048 MiB (e = 31) |
| Rejected: rcc `0xcc`, x16, 2 ranks or x32 | `Fail: 0xc000fa11.`, returned `0x1747fa11` |
| Bank codes 1, 2, 3 at the reference geometry | 192 MiB each |

Twenty-four capacity rows per release agree with the structured arithmetic and the model. The bank code always comes from the record. When `rcc & 0xcc != 0` the stored geometry is used unchanged. The no-alias probe limitation is retained: the historical 17-row case reports row code 0 and 128 MiB. A newly recorded quirk is that nonzero-bank capacities below 256 MiB wrap the final DCU_CFG term to `0xffffff2c`. The formula describes firmware arithmetic and is not a physical geometry formula.

## 5. Implementation changes

| Artifact | Change |
|---|---|
| `specifications/bootloader-initialization.json` | Structured `semantics` (bus, rank, retry, capacity, timing) with cited instructions; keyed per-release `reference` values; INI primary/secondary offsets, slot widths and endianness; two missing INI bytes (+0x19, +0x1a, significance open); AFI field objects with generation, admission and consumer rules; SRAM range objects with basis, stages, derivations and declared overlaps; `attempts`; explicit windows; state-check roles; `confirm_absent` and `dram_terminal_pc` on branches; static instruction bindings; FDT reservation fact. The DFI retry transition was removed |
| `specifications/bootloader-source-references.json` | Added `uboot-afi-layout` and `uboot-afi-getters` with verified blob hashes |
| `evidence/firmware/dram-selector-semantics.json` | New firmware-backed evidence: 240 runs, instruction audit and literal audit of both releases |
| `tools/contract_semantics.py` | New interpreter and semantic checks; `generate`/`check` modes for the firmware matrix |
| `tools/bootloader_contract.py` | Windows, RLE clipping, `Observation`, attempt validation, forbidden-anchor scan, branch checks, generated document tables, `sources` mode, extended statistics |
| Documentation | Corrected contract text with generated tables; dependency report; tool reference; one clarification in the historical DRAM report; this report and the handoff |

## 6. Semantic validation and independent references

| Property | Independent reference | Status |
|---|---|---|
| Bus/rank normalization, retry order, failure write-back | Loader execution (240 rows), cited-instruction audit, `ddr_model`, historical SD2 runs and unified failure record | Semantically verified |
| Capacity arithmetic and overflow | Loader execution, `ddr_model.capacity_probe`, historical overflow case | Verified for the stated branches |
| Record layout | Executed working copies of all five releases, raw INI bytes in 14 traced cases, observed write-back | Verified; tail byte and +0x19/+0x1a significance curated as open |
| Timing inputs | `ddr_model.timings` over 5,120 combinations, PLL words in every traced attempt | Verified as firmware arithmetic |
| AFI layout and consumers | Firmware SRAM stores, INI fields, working capacity, executed U-Boot getters and four isolated controls, pinned `owl_afi.h`/`owl_afi.c` | Verified |
| SRAM ranges | Observed transfer sizes, observed SRAM stores, historical pre-DRAM map | Ranges verified as observed or static; physical extent unresolved |
| Static operations | Re-disassembled loader instructions and literals; U-Boot startup audit | `clock-basis`, `delay`, `globals`, `publish-pointers`, `uart-output`, `uboot-relocate` |
| Register names, implementation classes, profile maturity | Curated interpretation | Not semantically verified |

The structured definitions are never compared with their own rendering. The tables in the contract document are generated from the verified definitions, and staleness is a validation error.

## 7. Trace boundaries

Checks restricted by boundaries use a check-level `window` with named `after`/`before` boundaries. Each names an explicit occurrence (`only`, `first`, `last` or an index) and an optional explicit `else`. An absent boundary without `else`, a repeated boundary under `only`, or a reversed interval raises an error. Empty intervals are valid. Matching clips each RLE run to the window and counts only the included repetitions. The two committed windows are the `timer` control write and `power-state`, both before `before-adfu`. On invalid INI the timer window resolves to `caller-finishing`. Without the window, `gpio-adfu` and `pmic-read-error` report two timer initializations, the second in recovery.

## 8. Retry-order validation

Attempts are identified from `controller-phy-programming` boundaries and end at the next attempt or DRAM exit boundary. Each attempt is classified by its own boundaries. Its configuration comes from the PGCR write `0xb40686d8` (rank enables) and DX2GCR bit 0 (`0xb406862c`). The validator applies these rules:

* each attempt contains the programming prefix (gates, reset, PLL, PHY reset, PHY timing), and every unbounded access of each required operation recurs inside it;
* a training error needs ZQ, PHY ready, DRAM init and training, and excludes `train-passed`, DFI, controller timing, GO and capacity;
* a programming failure excludes DRAM init and training. An unbounded poll excludes training;
* the 14 attempt-local edges are ordered inside each attempt;
* only training-error attempts may be followed by another attempt, resume never retries, and the retry rules applied to the input record must reproduce the executed attempt count, configurations and final working bytes. They must also agree with the recorded training results.

The committed evidence contains 20 attempts in 16 traces. The global first-occurrence comparisons were replaced by `last-before-first` except one non-DRAM edge with a recorded justification.

## 9. Execution, value and absence evidence

A state check now has a `role`. An `execution` check needs a positive predicate from a named stage whose status is `completed` (or `terminal` where stated). A `value` check never counts as execution. An `absence` check asserts that a named stage did not run. Zero-count trace checks exclude one access pattern but do not confirm an operation's absence. All nine non-Linux branches forbid `linux-entry` and require a positive absence check. Forbidden operations are also searched for by their positive anchors regardless of scenario conditions, so a forbidden operation with no applicable check is still detected. Each branch also states its DRAM terminal PC.

## 10. Additional discrepancies

| ID | Statement | Evidence | Resolution |
|---|---|---|---|
| A1 | DFI timeout can retry on an eligible first attempt | `0xdf00fa11` returns `0x1747fa11` at `0xb4068f50`; historical `dfi-timeout` retried after a two-rank training error | Corrected; retry transition removed; check against the historical case |
| A2 | `reference` lists mixed primary/secondary and release ordering | Executed working copies per release | Replaced by keyed release groups, checked per release |
| A3 | Per-attempt requirements satisfied by any anchor | New negative control (reset writes removed, delay kept) | Unbounded access checks must recur in every attempt |
| A4 | `phy-reset-poll` did not cover `phy-poll` | Event 656 reads PHY ready before the unbounded wait | Condition and two dependency conditions extended |
| A5 | `boot-select` precedes `load-early` only in its first occurrence | Early loader reads the code word at `0xb4065414` after installation | Explicit justified first-occurrence edge |
| A6 | FDT "aligned reservation 0x7000" implied coverage | Executed U-Boot: `/memreserve/` `0x7000`, final totalsize `0x7080` | Corrected; structured fact checked in five Linux-entry traces |
| A7 | PMIC data "big-endian" | The trace intercepts at the accessor and cannot observe the wire | Qualified as static |
| A8 | UART divisor `floor(24 MHz/(8·baud)) − 1` | Audited helper subtracts only for a nonzero quotient; baud 0 returns −1 | Qualified |
| A9 | Persistent training failure restores selectors | Instructions `0xb4069020..34`; firmware rows | Added to semantics and documentation |
| A10 | Nonzero-bank capacities below 256 MiB | DCU_CFG `0xffffff2c` in firmware rows | Recorded as a limitation |

The targeted audit also re-derived the following without discrepancy: the timer setup sequence, the signed delay compare and the millisecond scaling, DDR clock rounding and the PLL word, the 468 MHz timing values and the resume tRFC of 75, the memory diagnostic word count, sample counts and stride, PMIC register values at the accessor, storage sector counts and destinations, AFI bytes, U-Boot memory fallback, ARM Linux register and cache state, and the initrd bounds.

## 11. Regression and mutation tests

`tests/test_contract_semantics.py` (50 tests) covers selector, rank and fallback rules, input versus working selectors, the four capacity examples, exponent bounds, bank codes, no-alias probing, raw-selector substitution, generalization of the eight-bank formula, record offsets, widths, swaps and release references, AFI layout, byte order, magic length, capacity conversion, the Linux-requirement claim, failed-initialization admission and field-crossing stores, SRAM length, endpoints, reversal, extent, overlap and ownership, timing classes, static bindings, FDT coverage, and pinned sources. `tests/test_bootloader_contract.py` (51 tests) adds windows, RLE clipping, the invalid-INI and recovery timer cases, attempt mutations (second-attempt swap, missing reset, early training, retry without eligible failure, wrong configuration, excess attempts, mislabelled outcome, valid early failure) and the execution-evidence regressions. Each mutation test drives the layer that owns the protection on copied fixtures, so a trace-hash or generated-file mismatch cannot stand in for the semantic check.

| Run | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Contract modules without firmware or sources | 98 | 0 | 3 (two firmware-backed, one pinned sources) |
| Contract modules with `ATM_FIRMWARE_DIR` and `ATM_SOURCES_DIR` | 101 | 0 | 0 |
| Full repository suite, then research validation and rendering | see §14 | | |

## 12. Historical compatibility

No historical tool, model or evidence file changed. `evidence/firmware/boot-initialization-trace.json` is byte-identical to the reviewed revision, and a fresh firmware replay reproduces it byte for byte. The replay also re-executes 16 unified boot-chain scenarios and compares each with its archived summary. The generated contract JSON changed because its source specification changed. OBS-001 and its preregistered predictions are untouched.

## 13. Firmware-backed reproduction

| Command | Result |
|---|---|
| `ATM_FIRMWARE_DIR=FW python tools/bootloader_contract.py replay --check` | Byte-identical; 16 cases |
| `ATM_FIRMWARE_DIR=FW python tools/contract_semantics.py check` | Byte-identical; 240 runs and the instruction and literal audit |
| `ATM_SOURCES_DIR=SRC python tools/bootloader_contract.py sources` | Five of five verified |
| Historical firmware-backed suites | §14 |

## 14. Validation status

See the [research handoff](pr9-research-progress.md#corrective-verification-of-the-initialization-contract) for the final ordinary, research and historical regression results recorded at commit time.

## 15. Remaining uncertainties

Semantic agreement with firmware does not resolve physical questions. The following remain open: the authentic Boot ROM entry state (the only operation without any check), physical SRAM extent and ROM work areas, medium-specific ROM behavior, PMIC identity and rails, physical DRAM geometry and real PHY training, controller/PHY revision, GPIO electrical and mux semantics, U-Boot runtime relocation and reservations, `C-RESUME-DRAMRST`, and modern Linux platform prerequisites. `memory-plan` is checked only by a value assertion. Synthetic hardware decides every training and alias outcome in the selector matrix. The model's agreement covers software decisions, not analog behavior. The contract is an offline engineering reference and does not authorize flashing or executing a replacement bootloader.

## 16. Reproduction

```sh
python tools/bootloader_contract.py generate
python tools/bootloader_contract.py validate
python -m unittest tests.test_contract_semantics tests.test_bootloader_contract -v
ATM_FIRMWARE_DIR=FW python tools/bootloader_contract.py replay --check
ATM_FIRMWARE_DIR=FW python tools/contract_semantics.py check
ATM_SOURCES_DIR=SRC python tools/bootloader_contract.py sources
ATM_FIRMWARE_DIR=FW ATM_SOURCES_DIR=SRC python -m unittest tests.test_contract_semantics tests.test_bootloader_contract -v
```

`FW` holds `koriki-v1.0.img` and `stock-20231014.img` from `tools/acquire_firmware.py … --expand`. `SRC` holds `linux/` and `u-boot_s500/` trees, or the referenced files at those paths, at the ledger revisions.
