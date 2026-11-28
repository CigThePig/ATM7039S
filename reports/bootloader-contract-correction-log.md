# Bootloader contract correction log

Persistent working log for the corrective assignment on PR #9 (`sd2-predram-reconstruction`). Entries are appended in order. The [verification report](bootloader-contract-verification.md) is the reviewed summary.

## Checkpoint A: baseline (2026-11-28)

* Branch head `984d2232c6d783762b1d3cef2c8fc5edb6448ac9`, equal to the independently reviewed revision. No intervening commits, so no finding was already addressed.
* Environment: Python 3.13.18, 15 GiB RAM, 60 GiB free disk. Installed `requirements-dev.txt` and `requirements-firmware.txt` (unicorn 2.1.4, capstone 5.0.6). Installed `7zip`/`7zip-rar` for the RAR5 stock image.
* No firmware cache existed in the fresh container. Acquired `koriki-v1.0` with `tools/acquire_firmware.py --expand`: whole-image SHA-256 `d5bd3007…d6ae` verified by the tool. Compressed copy deleted after verification. `stock-20231014` acquisition started.
* Only the contract replay and firmware-backed test classes need images. Contract replay uses `koriki-v1.0` and `stock-20231014` only.
* `python tools/bootloader_contract.py validate`: 16 cases, 65 checked operations, 1,304 checks, 63 ordered dependencies.
* `python -m unittest tests.test_bootloader_contract`: 20 tests, OK, 1 skipped (firmware class).
* `python -m unittest discover -s tests`: 532 tests, OK, 30 skipped (firmware, pinned sources, Windows-only paths).

## Investigation: DRAM bus selector (finding 1)

Static instructions of the verified Koriki loader (SHA-256 `a3a56aca…67a1`, base `0xb4060000`):

* `0xb4067434..0xb4067464` (cold mode only, mode byte `[0xb4070804]` zero): `[sp+0x40] = input < 2 ? input : 2` and working byte `+4 = (input == 1)` via `sub lr,r2,#1; rsbs ip,lr,#0; adc fp,ip,lr`.
* `0xb4067418..0xb4067438`: `[sp+0x30] = input_cs` when `input_cs <= 2`, else 0. Working cs is 1 when the input is 1, otherwise 2.
* `0xb4068f34..0xb4068f5c`: only internal code `0x1017fa11` (PGSR `0x3f` after training PIR at `0xb40687a8`) reaches the retry test. Codes `0x2a00fa11` (ZQ), `0x9a00fa11` (PHY init), `0xdf00fa11` (DFI init complete, `0xb01c02c0` bit 0), `0xc000fa11` (capacity exponent) and `0xf000fa11` print and return `0x1747fa11`.
* `0xb4068fa4..0xb406901c`: rank retry when `[sp+0x30]==0` and working cs 2; otherwise width retry when `[sp+0x40]==2` and working byte 0, which sets the byte to 1 and restores cs 2 when ranks are automatic.
* `0xb4069020..0xb4069034`: on a persistent training failure the working cs byte is set to `[sp+0x30]` and the bus byte to `[sp+0x40]`. Other failure codes leave the last attempt's values.

Firmware-backed matrix (scratch, 96 runs: input bus {0,1,2,3,0x80,0xff} × input cs {0,1,2,3} × synthetic width {16,32} × synthetic ranks {1,2}) through `sd2_dram_analysis.execute`: attempt sequences and success agree with `ddr_model.run` in all 96. Selector 0 on x16-only hardware fails after x32 attempts with no x16 retry.

Conclusion: the specification statement "0 auto x32 then x16" is wrong. Status: confirmed.

## Investigation: capacity operand (finding 2)

* `ddr_model.capacity_probe`: `n = row + col + (x16 ? 1 : 2) + cs + 0x17`, reject `n > 31`, eight-bank `2^(n-20)` MiB, otherwise `3·2^(n-22)` MiB.
* Firmware-backed scratch runs with patched rcc (probe skipped when `rcc & 0xcc != 0`) and probe runs: 20 of 20 agree with the model. Examples: 32 MiB minimum; 256/512/512/1024 MiB for (x16,1), (x32,1), (x16,2), (x32,2) at row 1 col 2; 2048 MiB at operand sum 8; sum 9 and 10 return `0x1747fa11` after `Fail: 0xc000fa11.`; bank codes 1–3 give 192 MiB at the reference geometry.
* With raw selector substitution x32 (working byte 0) gives 128 MiB instead of 512 MiB. Status: confirmed.

## Additional discrepancy A1: DFI retry transition

`retry_transitions[1]` claims a DFI timeout on an eligible first attempt re-enters the full sequence. Instructions show `0xdf00fa11` returns without retry. The historical `dfi-timeout` scenario retried because its first (two-rank) attempt failed training, then the one-rank attempt timed out in DFI and returned. Status: confirmed specification error.

## Additional discrepancy A2: reference value semantics

`configuration_fields.*.reference` lists mix `[primary, secondary]` (capacity, cs, rcc) with `[pre-20231014, 20231014]` (ODT, drive). Ambiguous; replaced by keyed structured values.

## Checkpoint B/C: semantic corrections and validator hardening

* `specifications/bootloader-initialization.json`: structured `semantics` (dram-bus, dram-rank, dram-retry, dram-capacity, dram-timing), keyed release references, INI and working placement, AFI field objects with consumer/generation/admission rules, SRAM range objects with basis, stages, derivations and declared overlaps, `attempts`, explicit boundary windows, state-check roles, branch `confirm_absent` and `dram_terminal_pc`.
* `tools/contract_semantics.py` (new): interpreter plus checks against the firmware matrix, `ddr_model`, historical evidence, the trace and executed getters. `generate`/`check` reproduce `evidence/firmware/dram-selector-semantics.json` (240 runs, instruction and literal audit of both contract releases; the DRAM routine is byte-identical in both).
* `tools/bootloader_contract.py`: fail-closed windows, RLE clipping, `Observation`, doubled-scale ordering, per-attempt validation with retry prediction, forbidden-anchor scan, `sources` mode, generated contract tables.
* Additional discrepancy A3 (found by a new negative control): a required attempt operation was satisfied by any one of its anchors. Removing both reset writes from attempt 2 passed because the reset delay request remained. Fixed: each unbounded access check of a required operation must recur inside every attempt.
* Additional discrepancy A4: `phy-reset-poll` did not apply to `phy-poll` although the raw trace shows the PHY-ready read (event 656, value 7) before the unbounded wait. Condition extended, with the two adjacent dependencies.
* Additional discrepancy A5: `boot-select` mixes the block-0 store and the early loader's later read of the code word, so only its first occurrence precedes `load-early`. `first-before-first` now requires an explicit `occurrence_justification` and is rejected for DRAM operations.
* Pinned sources: all five references (three Linux, two new U-Boot AFI references) verified by git blob SHA-1 and line bounds against files fetched at the ledger revisions into a local `ATM_SOURCES_DIR`.
* Tests: `tests.test_contract_semantics` 49 tests, OK, 1 skipped (firmware); `tests.test_bootloader_contract` 51 tests, OK, 1 skipped (firmware).
