# PR #9 research progress and handoff

Branch: `sd2-predram-reconstruction`, from main `1c28e36` (PR #8 merge). Draft PR: "SD2 Pre-DRAM Initialization and Unified Boot-Chain Reconstruction". Offline only: there was no hardware interaction of any kind.

## Completed

* **Firmware.** Acquired and whole-image-verified all five pinned images: Koriki v1.0 and stock 221203, 221223, 230309, 20231014. 20231014 is RAR5 and needs a RAR-capable 7-Zip (Ubuntu `7zip-rar`). Without it `archive_members.py` fails with "member length 0".
* **Tool.** Wrote `tools/predram_analysis.py`, which does static call-graph, MMIO and boot-code analysis plus bounded emulation of main for boot codes 0 and 2. It produced `evidence/firmware/sd2-predram.json`, and regeneration is byte-deterministic.
* **Findings.** Reconstructed the pre-DRAM sequence, environment, timer, UART, board MFP, PMIC and ADFU structure: BOOT-024, BOOT-025, CLK-007, UART-004, PMIC-002, GPIO-002. Refined BOOT-021.
* **Contradictions.** Narrowed C-PREDRAM-PATH (still open). Opened and resolved C-PREDRAM-LABELS.
* **Supporting changes.**
  * `dram_complete.run_caller(..., boot_code=0)`: new optional argument; default behaviour and committed evidence unchanged.
  * `validate_firmware.predram_checks`.
  * Curated register evidence for 12 registers in `registers/curated/firmware-observations.json`, applied with `apply_firmware_registers.py`.
* **Docs.** `docs/predram-initialization.md` and `reports/sd2-predram-reconstruction.md`. Updated `docs/boot-chain.md`, `docs/afi-handoff.md`, `docs/serial-console.md`, `tools/README.md` and the README.

## Newly confirmed facts (instruction level; executed facts under synthetic rules)

1. Block 0 tests `0xb01600a0` bit 7 first (code 2), then bit 4 (code 0). Codes 0 and 2 share one path into `0xb4065400`. Block 0 and main set neither SP nor CPSR nor CP15. All of that is inherited from the Boot ROM.
2. Pre-DRAM order: memset globals → load_ini (ROM service, disk `0x202600`) → ini_to_globals → timer_init(0) → uart_init(3,115200,0) → [code 5: spinand] → ini_print/"1.1" → board_mfp_init(1) → pmu_init(type 2) → adfu_check(1) → publish_globals → resume test → second record → `0xb40690b8`.
3. **Boot code 0 vs 2.** The only pre-DRAM difference is `adfu_check`'s GPIO C11→C10 32-bit loopback test with pattern `0x55aa55aa`:
   * 32 × delay_ms(1);
   * ADFU only on an exact echo;
   * leaves `0xb01b0064` bit 17 cleared and `0xb01b0020` bit 11 = 0.

   With the PR #6 harness the full DRAM-stage MMIO sequence differs only by that block.
4. **Timer 0.** Control word `0xb0168008 + 12n`, count at +8, 24 ticks/µs. delay_us is wrap-safe and unbounded.
5. **UART3/pad 0.** Gate `0xb01600a4` bit 19, reset `0xb01600ac` bit 15, control `0x8003`, divider 25 at `0xb01600b0`. **No pin-mux write.** Unbounded TX polls.
6. **PMIC type 2.** I2C1 `0xb0174000`, slave 0x65. Identity: reg 0xff = `0xca`, reg 0x32 = `0x1bc0`. Cold-path regulator writes are listed in PMIC-002. This matches the atc2603c DT node (inference).
7. **Releases.** All five are identical in pre-DRAM code, tables and executed sequences. Only the 20231014 ODT/drive record bytes differ, and they pass straight to DRAM init.

## Corrected assumptions

* BOOT-021 called it a "handshake". It is a loopback, and the status write-back clears bits 0–1.
* `boot_chain.LOADER_STUBS` labels (`0xb4069440` "PMIC/clock", `0xb4069254` "PMIC status read") are outdated. They are recorded in C-PREDRAM-LABELS and the code is unchanged, to preserve committed evidence.
* All PR #6 DRAM evidence is code 0. The new comparison shows code 2 gives the same DRAM-stage sequence in the reference scenario.
* The ini `bootdev=` byte (`0x22` in every release, including those that would boot SD0) is printed only. It is not the AFI boot device.

## Important evidence keys (`sd2-predram.json`)

| Key | Contents |
|---|---|
| `releases` | identities and hashes |
| `call_graph`, `predram_graph` | functions, edges and exits |
| `boot_code` | writers, references and consumers |
| `structure` | instruction-anchored facts (ADFU, timer, UART, I2C) |
| `runs` | eight scenarios |
| `code0_vs_code2`, `dram_stage_code0_vs_code2` | the divergence |
| `seed_dependence` | reset-value sensitivity |
| `register_inventory` | executed sites |
| `static_only_accesses` | untaken branches |
| `unresolved_static_accesses` | computed addresses not resolved |
| `release_comparison`, `emulation_audit`, `unknowns` | as named |

## Reproduce

```sh
python tools/acquire_firmware.py koriki-v1.0-release FW --expand
python tools/acquire_firmware.py anbernic-stock-archive FW --filename RG35XX-221203.zip --expand   # and the three RARs
python tools/predram_analysis.py evidence evidence/firmware/sd2-predram.json --reference koriki-v1.0 \
  --image koriki-v1.0=FW/koriki-v1.0.img --image stock-221203=FW/stock-221203.img --image stock-221223=FW/stock-221223.img \
  --image stock-230309=FW/stock-230309.img --image stock-20231014=FW/stock-20231014.img
ATM_FIRMWARE_DIR=FW python -m unittest tests.test_predram -v
python -m unittest discover -s tests -v; python tools/research.py validate; python tools/research.py generate --check
```

## Tests executed (this session, Linux, Python 3.13, Capstone 5.0.6, Unicorn 2.1.4)

| Run | Result |
|---|---|
| `python -m unittest discover -s tests` (no firmware) | 457 tests, OK, 21 skipped (firmware-, qemu- or tool-dependent, as before) |
| `ATM_FIRMWARE_DIR=FW python -m unittest tests.test_predram tests.test_boot_chain -v` (all five images) | 53 tests, OK, 0 skipped. Committed `sd2-predram.json` regenerated exactly; PR #5/#8 boot-chain evidence unchanged |
| `research.py validate` | 0 errors |
| `research.py generate --check`, `render_catalogue.py`, `render_html.py` | clean, no diff, 47 documents rendered |
| Not run here | browser (Playwright) and Windows CI jobs; `test_dram_complete` firmware-backed comparisons (`ATM7039S_STOCK_LOADERS`) |

GitHub Actions results were not observed by this session.

## Unresolved emulator assumptions

* Seeded reads of MFP/CMU/GPIO registers. Seed `0xffffffff` changes control flow once (`0xb0160084` bit 0 skips a 300 µs wait).
* I2C FIFOSTAT always succeeds, the UART never blocks and the timer always advances. Each of these hides possible hangs.
* PMIC values come from a register file (`PMIC_DEFAULTS`).
* SP and CPSR are emulator choices.
* The ROM-filled SRAM hole stays zero.

## Remaining questions and recommended next objectives

1. **GPIO C10/C11 on the RG35XX.** Search the pinned DTs, vendor pinctrl sources and board material for what these pins connect to. This decides whether the code-2 loopback can ever pass. Offline.
2. **Boot ROM state per medium.** Without ROM code this is not answerable offline. Record it as the main residual of C-PREDRAM-PATH.
3. **UART3 pin mux.** Map which MFP field selects UART3 on the ATM7039S, and check whether the reset default or board_mfp_init's `MFP_CTL2` write covers it (vendor pinctrl source, offline).
4. **PMIC register semantics.** Map the type-2 register numbers to a public ATC2603C driver (vendor kernel `atc260x`) before interpreting any regulator value.
5. **DRAM scenarios for code 2.** Optionally re-run the remaining PR #6 DRAM failure scenarios with `run_caller(..., boot_code=2)`. A cheap offline check, deliberately not done here.
6. **Physical (needs separate approval; not authorized by this work).** An early read-only serial log of a stock boot would directly show the pre-DRAM console lines listed in `runs.code2.printed`.
