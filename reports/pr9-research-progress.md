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

---

# Part 2: ADFU GPIO loopback reconstruction (from `ca0cdab`)

## Completed

* Re-verified `adfu_check 0xb4069254`, `rom_reentry_adfu 0xb40691a4`, the delay/timer/PMIC accessors, `get_boot_code`, the dram_caller call site, `memcpy`, the PMIC table and strings. That is twelve regions plus literal pools, byte-identical in all five releases, and 46 instruction anchors, all matching.
* New **`tools/gpio_model.py`** (`GpioModel`) and **`tools/adfu_analysis.py`**: an independent `reference_model`, a 41-scenario matrix, a stalled-timer run, whole-path and DRAM-harness runs, a bounded re-entry run, a board-source/DTB survey and downstream analysis. Evidence: **`evidence/firmware/adfu-loopback.json`** (byte-deterministic; checked by regenerating twice).
* **Opt-in harness extensions**, defaults unchanged. `sd2-predram.json` regenerates byte-identically.
  * `predram_analysis.Trace(gpio=, timer_step=, i2c_fail_regs=, rom_copy_stub=)` and `Trace.run_function(entry, args)`; `Machine.call(..., args)`.
  * `dram_complete.Harness(..., gpio=)` and `run_caller(..., gpio=)`. The GPIO window is answered by the model, and stubbed delays advance the model clock.
* **Findings:** BOOT-026, BOOT-027, GPIO-003, GPIO-004. BOOT-025 refined. C-PREDRAM-PATH updated (still open).
* **Curated register evidence:** pinned vendor-source lines for PAD_PULLCTL1, GPIO_CDAT and MFP_CTL2.
* **Validators and tests:** `validate_firmware.adfu_checks`; `tests/test_adfu_analysis.py`.
* **Docs:** `reports/adfu-loopback-reconstruction.md`, plus updates to `docs/predram-initialization.md`, `docs/boot-chain.md`, `docs/serial-console.md`, `reports/sd2-predram-reconstruction.md`, `tools/README.md` and `README.md`.

## Important discoveries and corrections

1. **A PMIC read failure enters ADFU.** `pmic_read` returns −1 with no retry, `& 0xffff` gives `0xffff`, bit 1 is set, and it writes back `0xfffc`. Only bit 1 is examined; write-back is `status & ~3`; the PMIC path never touches GPIO.
2. **The boot-code guard is `!= 0`.** Codes 1, 4, 5 and `0x80000000` all run the test. The argument guard is a 32-bit `!= 0`.
3. **Loop details.** Always 32 iterations, with no early exit. Two CDAT writes per iteration (clear bit 11, then OR the pattern bit). The delay comes before the sample. `rx |= s << i` is LSB first. The final comparison is an exact `cmp` against a freshly loaded literal.
4. **Pins (vendor pinctrl data, pinned).**
   * GPIOC10 = `P_SD0_D0` (line 169) and GPIOC11 = `P_SD0_D1` (line 170).
   * PULLCTL1 bit 17 is `P_SD0_D0`'s pull-up field (line 2642).
   * The test therefore runs on the **TF2 slot's DAT1→DAT0**, with DAT0's pull-up removed.
   * `board_mfp_init` muxes SD0 D0/D2/D3/CMD/CLK to the vendor JTAG values *before* the test. D1 is left as the Boot ROM or reset state left it.
   * No shipped DTB uses pins 74/75 as GPIOs.
   * A fixture purpose is a hypothesis; a UART adapter on the same pair is the alternative.
5. **Persistent state.**
   * COUTEN/CINEN restored exactly.
   * PULLCTL1 bit 17 stays cleared.
   * CDAT bit 11 = 0.
   * **Other CDAT bits depend on the unknown read semantics:** unchanged if reads return the latch; rewritten with read levels for non-output pins if reads return pads.
   * Under latch semantics the loopback can never pass.
6. **Downstream.**
   * No later loader access to these registers, in either the executed paths or the constant-address scan.
   * DRAM-stage non-GPIO writes are identical for codes 0 and 2 with the GPIO model attached (reference scenario).
   * The DRAM routine writes `0xb01b00b4 = 0x3ff` for both codes.
   * app.bin `0x9430` (no direct caller found), U-Boot's SD0 init and Linux `mmc0_default` may reconfigure the pads. Not traced.
7. **ADFU exit.** `0xb40691a4` never reaches DRAM init. It copies ROM `0xffff5200` (`0x2e00` bytes) over SRAM `0xb4060000`, writes the CMU, sets VBAR and SP, and jumps. The emulator records the copy without performing it and stops at the jump.

## GPIO model and APIs

```python
from gpio_model import GpioModel, C10, C11, C
g = GpioModel(initial={C['outen']: 0, C['dat']: 0}, inputs={C10: ('follow', C11)},   # or const/invert/delay/script/
              read_semantics='mixed', strict=True)                                     # follow_except/prbs
# pre-DRAM harness
import predram_analysis as P
t = P.Trace(loader, P.Disk(img), code, P.call_graph(code), 2, gpio=g); t.run()
# DRAM harness (reference scenario), C10 low:
import dram_complete as D
out, h = D.run_caller(loader, D.Pmic(), D.TRAINING_SCENARIOS[0], boot_code=2,
                      gpio=GpioModel(inputs={C10: ('const', 0)}, strict=False))
# h.writes / h.reads include the GPIO block; g.log, g.samples, g.state(), g.passthrough describe the model side
```

* Use `strict=False` for whole-path runs: other routines legitimately access MFP_CTL2/3, PAD_DRV1, DEBUG_* and `0xb01b00b4`.
* Routine level: `adfu_analysis.routine_trace(doc, boot_code, arg, pmic_status, gpio, pmic_fail=False, timer_step=24)`.
* Scenario plus comparison: `adfu_analysis.run_scenario(doc, decoded_constants(code), name, code, arg, pmic, rule, initial, extras)`.
* Algorithm alone: `adfu_analysis.reference_model(K, ...)`.

## Scenario definitions

`adfu_analysis.SCENARIOS` lists the cases: PMIC values, guards, 12 input responses, 2 read-semantics cases and 11 initial states. All 41 agree with the reference model. The four other releases agree on the loopback and low spot checks.

## Reproduce

```sh
python tools/fetch_sources.py SRC        # rate limits may need retries; only pinctrl_data-atm7059.c, regs_map-atm7039.h
                                         # and rg35xx_atm7039.dts (vendor-kernel) are needed
python tools/adfu_analysis.py evidence evidence/firmware/adfu-loopback.json --sources SRC \
  --image koriki-v1.0=FW/koriki-v1.0.img --image stock-221203=FW/stock-221203.img \
  --image stock-221223=FW/stock-221223.img --image stock-230309=FW/stock-230309.img --image stock-20231014=FW/stock-20231014.img
ATM_FIRMWARE_DIR=FW ATM_SOURCES_DIR=SRC python -m unittest tests.test_adfu_analysis -v
```

## Validation (part 2)

| Run | Result |
|---|---|
| `python -m unittest discover -s tests` (no firmware) | 483 tests OK, 24 skipped (firmware-, qemu- or tool-dependent) |
| `ATM_FIRMWARE_DIR=FW ATM_SOURCES_DIR=SRC python -m unittest tests.test_adfu_analysis tests.test_predram tests.test_boot_chain -v` | 79 tests OK, 0 skipped. Full regeneration of both evidence files equals the committed ones |
| `ATM7039S_STOCK_LOADERS=DIR python -m unittest tests.test_dram_complete -v` (four stock loader regions) | 37 tests OK, 0 skipped. The opt-in GPIO hook leaves PR #6 behaviour unchanged |
| `adfu_analysis.py evidence`, run twice | byte-identical output |
| `predram_analysis.py evidence`, after the Trace extensions | byte-identical to the committed `sd2-predram.json` |
| `research.py validate`, `generate --check`, `render_catalogue.py`, `render_html.py` | clean (48 documents) |
| Not run here | browser and Windows CI jobs |

GitHub Actions was not observed by this session.

## Remaining uncertainties

* GPIO data-read semantics.
* GPIO-vs-MFP priority while D0 is muxed to JTAG.
* Electrical effect of the cleared pull-up.
* TF2 wiring and the fixture's existence.
* PMIC reg 0x35 meaning.
* Real timing.
* ROM code behaviour.
* Boot ROM state per medium.
* The non-reference DRAM scenarios for code 2.
* Mainline `pinctrl-s500.c` was not fetched (HTTP 429), so there is no second source for the pull field.

## Recommended next objectives

1. Fetch mainline `pinctrl-s500.c`/`pinctrl-owl.c` (pinned commit) and compare the SD0_D0 pull and mux definitions and the GPIO data-read code path.
2. Find a public S500/ATM7059 datasheet section on GPIO data reads and GPIO-vs-MFP priority. The catalogued S500 PDF (`s500-pdf`) is the first place to look. This would settle the CDAT persistence question.
3. Trace app.bin `0x9430`'s indirect callers and U-Boot's SD0 pad set-up, to state whether bit 17 is restored before Linux.
4. Optionally run the remaining PR #6 DRAM scenarios with `boot_code=2, gpio=GpioModel(...)`. This is cheap but deliberately not done.
5. Physical (not authorized): an early read-only serial log of a stock SD2 boot would show `pmu_status = 0x…` and that the loader continues past the test.

---

# SD2 DRAM caller and memory handoff comparison

## Completed experiments

- Started from reviewed PR head `1161869009bbaf62d4fa2ea516d7f6b3c5ff5c41`. Verified the expanded Koriki v1.0 and Anbernic 221203, 221223, 230309 and 20231014 images, their loader regions and instruction/literal anchors. The shared bootloader code-region SHA-256 is `6b17b88c92e4d9f90f3f123e4a340b692d001bada4f78f24889481b73adf6ea9`.
- Executed 52 pairs per release, 520 runs, through main's real DRAM caller and outcome dispatch. The 17 cold, 12 resume, nine DMM, six GPIO, five diagnostic-fault and three control cases all use independent synthetic model state in each run. The 255 matching pairs preserve raw trace hashes. All five exact-echo controls diverge at early ADFU for code 2.
- Sampled ARM registers at every phase boundary. Code 2 can leave different caller-saved registers, LR and NZCV at the ADFU return. The paired trace checks full CPU agreement from the DRAM boundary onward.
- Tested the actual boot-code getter at its caller, ADFU and AFI sites. The word resides at `0xb4064c00`; `0xb40664f0` is the getter. Normal cold code 0 and code 2 differ in the AFI device byte `0x20`/ `0x22`; both emit size `0x10000000` under the 256 MiB reference model.
- Repeated the 180-case isolated DMM study for Koriki. It gives 64 observable outcome groups, 128 wrong capacity reports and 73 wrong capacities with a passing diagnostic. The eight overlapping caller examples reproduce the isolated outcomes. The ninth extends the tested width boundary.
- Rechecked the independent models, with 140 core-programming sequence comparisons, 215 diagnostic replays, 445 internal-to-returned-code comparisons and 500 ADFU model comparisons. Each comparison is scoped by its supported inputs. The programmable status responses, device geometry and reset values remain shared assumptions.
- Under the tested seeded GPIO states, `PULLCTL1[17]` stays cleared and `CDAT[11]` stays low after code 2's normal return. No subsequently executed DRAM path consumes the persistent GPIO words. The pad-region `MEM_MARGIN_CTRL1` RMW is common to both codes. Its physical meaning is still a candidate from the vendor header.
- 221203, 221223 and 230309 reproduce all 52 Koriki pair records exactly. 20231014 has changed ODT/drive input bytes in both records, with matching changes in MR1, ZQ0CR1, console and write-back. A few instruction-budget cases have shifted final poll counts or PCs across variants. All 20231014 code-0/code-2 comparisons preserve the matching behavior and the exact-echo difference.

## Corrected assumptions and open questions

The new harness models per-rank diagnostic RAM when a patched primary record skips the alias probe. The inherited DMM-write-counter heuristic previously used column wrap during this diagnostic and produced an artificial failure. The legacy harness retains its original semantics for historic evidence reproduction. The historical geometry sweep releases Unicorn mappings as it runs, with identical result data.

`BOOT-028` records the paired caller result. `MEM-012` records the distinction between the diagnostic, AFI stores and main's actual next-stage or recovery dispatch. `C-PREDRAM-PATH` stays open for initial medium-specific ROM and physical pad/DRAM state, with the caller-level comparison completed. `C-RESUME-DRAMRST` stays open. SAMA7D6 documents a similar PIR layout with a reset action independent of DRAMINIT, so the absence of bit 6 gives no general guarantee. No public material examined identifies the ATM7039S behavior.

OBS-001 directly constrains SD2, controller `0xb0238000`, the command line and the kernel-addressable 256 MiB range. Live AFI, physical memory geometry, PMIC voltages, reset state, serial output and analog training remain unobserved.

## Handoff format and entry points

`tools/sd2_dram_analysis.py` exposes the `run`, `suite`, `evidence` and `list` commands. The single-run envelope carries `format_version`, verified `firmware`, input `assumptions`, scenario `inputs` and `result`. Use `run --boot-code 2` for a single SD2 result. Omit the boot code for a pair. Add `--detail` for ordered trace and full snapshots.

| Result field | Meaning |
|---|---|
| `boot_code`, `boot_code_observed`, `adfu` | Requested seed, readback SRAM word and executed ADFU argument/test outcome |
| `dram_entry`, `record_selection`, `record_final`, `capacity_mib` | Entry record/state, actual source of the working parameters, final decoded/raw record, capacity from a successful core return. Resume capacity comes from the stored primary. |
| `caller_return`, `dram_return`, `terminal`, `outcome` | A32 call and core return values when present, exact boundary or failure PC, and the classified run result |
| `main_continuation_boundary_reached` | Instructions arrived at main `0xb4065440`, before loading app.bin or U-Boot |
| `afi` | All 16 before/final bytes, decoded fields, observed store count, generation status and a separate changed-bytes flag |
| `ini_initial`, `ini_final`, `ini_primary_stores` | Both record byte sequences and selector, with observed SRAM primary-record store count |
| `memory_test`, `training`, `selected_mmio_final` | Diagnostic status/access counts, each training attempt and its synthetic response, selected terminal state |
| `synthetic_or_unmodelled`, `trace` | Named access assumptions and pre-normalization SHA-256 of the ordered event sequence |

A consumer can use cold `outcome`, `main_continuation_boundary_reached` and `afi.generated` together before interpreting `afi.bytes`. Some failed initialization paths store a plausible AFI before main dispatches to recovery. Diagnostic failure can still reach the loading boundary. Resume paths have their own terminal classifications and no AFI generation. A later integration can use this result API while retaining the current boot-chain tool's legacy capacity input; this work leaves that integration for separate review.

```sh
python tools/sd2_dram_analysis.py run --firmware-dir FW --scenario reference --detail
python tools/sd2_dram_analysis.py suite --firmware-dir FW --release stock-20231014 --group resume
python tools/sd2_dram_analysis.py evidence --firmware-dir FW OUT.json
ATM_FIRMWARE_DIR=FW python -m unittest tests.test_sd2_dram_analysis -v
ATM_FIRMWARE_DIR=FW ATM7039S_STOCK_LOADERS=LOADERS ATM_SOURCES_DIR=SRC \
  python -m unittest tests.test_dram_complete tests.test_ddr_timing tests.test_adfu_analysis tests.test_predram tests.test_boot_chain -v
```

The result schema, state boundaries, full assumptions, observations and source references are in the [SD2 DRAM report](sd2-dram-reconstruction.md). Local execution used Python 3.12, Unicorn 2.1.4 and Capstone 5.0.6.

## Validation in this session

| Check | Local result |
|---|---|
| `python -m unittest discover -s tests -v` | 497 tests run, 470 passed, 27 skipped without optional firmware or host tools |
| Historical firmware-backed `test_dram_complete`, `test_ddr_timing`, `test_adfu_analysis`, `test_predram` and `test_boot_chain` | 138 passed, no skips. The full PR #6 DRAM evidence regenerated byte-for-byte, including the historical clock and DMM sweeps. ADFU, pre-DRAM and boot-chain evidence also regenerated. |
| New firmware-backed comparison | Five-release byte reproduction, AFI store and resume-target controls run with verified images |
| Integrity, generation and render commands | Validation reports zero errors. Generated register products match and both Markdown catalogues and the reference site render. |
| Browser lab smoke and Linux launcher self-test | Passed with simulated browser API. The Linux self-test reported disk discovery unavailable in this environment. |
| Windows-specific checks | Preserved in GitHub Actions. Linux local execution does not cover these jobs. |

---

# Unified boot-chain reconstruction

The integrated tool starts with only block 0 and modeled Boot ROM state. Block 0's sector read installs the early loader. Main's own INI read installs the records. One live ARM machine retains the boot word, caller frames and CPU state, SRAM, pad/clock writes and synthetic PMIC registers through pre-DRAM, ADFU/resume selection, DRAM programming, capacity detection, diagnostic, primary write-back, AFI and main's branch. The real cold continuation at `0xb4065440` executes loader I-cache/clock setup, app.bin and U-Boot reads, then the SFVD-present app.bin path to `0x05000040`. Early recovery copies are recorded at the absent ROM boundary. SFVD write-back is bounded at its dispatch and records intent.

The version 1 stage envelope binds each state to the image, scenario, predecessor digest and execution method. Loader state remains live. Later bounded U-Boot routines consume the loaded U-Boot bytes, raw SRAM AFI and pin-mux word. The actual AFI size goes into `gd+0x34` and becomes input to the modeled board bank and executed FDT fixups. MMC registration, boot-flag changes and the bounded environment interpreter determine the backing disk, partition and files. Linux cleanup and the jump execute to the first-instruction boundary.

The reference controls cover stock 221203, 221223, 230309, 20231014 and Koriki v1.0. GPIOC6 high yields the exact OBS-001 Koriki SD2 command line, controller, memory and initrd ranges. Alternative same-handoff cases are recorded separately from physical observations. The 20231014 variant retains its own INI/DDR evidence. The app.bin caller at `0x9e8c` can call `0x9430`, whose SD0 branch can set PULLCTL1 bit 17. Both sites remain outside the exercised normal SFVD-present path. `C-PREDRAM-PATH` keeps its hardware and Boot ROM questions. Device-clock and resume electrical uncertainties remain open.

## Inputs to a future independent loader specification

- Establish ROM entry mode, CPU/stack, medium selection, clock gate, initial pad state and loader read contract. Preserve control-flow and sector identities for early config and stage loading.
- Audit timer frequency and delay loops, UART clock/reset/divider, I2C clock/pads, PMIC identity and pending/wake bits, register write sequence, and the exact recovery priority and pad operations.
- Document record selection, cold vs resume entry, clock/PLL, DDR reset, PHY/ZQ/training, controller transitions, DMM geometry, diagnostic coverage, return paths, SRAM write-back and the AFI sequence with their known or unknown initial conditions.
- Account for post-DRAM clock/cache setup, app.bin CHIPID and SFVD gates, U-Boot startup and relocation reservations, AFI consumers, pin mux, MMC and environment checks, image placement, FDT reservations/fixups and final ARM register/cleanup requirements.

Continue with the [architecture reference](../docs/boot-chain-emulation.md) and [detailed report](unified-boot-chain-reconstruction.md). Reproduce via `python tools/unified_boot_chain.py evidence --firmware-dir FW OUT.json` and `ATM_FIRMWARE_DIR=FW python -m unittest tests.test_unified_boot_chain -v`. Historical tools and evidence retain their original contracts.

## Unified validation

| Check | Result |
| --- | --- |
| Ordinary Linux unit suite | 512 tests, 483 passed and 29 optional skips |
| Unified firmware-backed checks | 35 integrated scenarios across five releases, 17 Linux entry boundaries and 18 earlier terminals. Live state and byte reproduction checks passed. |
| Historical firmware-backed regression | 152 caller/DDR/ADFU/pre-DRAM/boot-chain checks and 9 V3 firmware/preflight checks passed |
| Validation and rendering | Research validation reported zero errors. Generated reference, catalogue and HTML checks passed. |
| Lab checks | Chromium smoke passed. Linux module self-test passed with simulated disk inventory. Native Windows execution is covered by the existing workflow. |

---

# Independent bootloader initialization contract

The specification is based on reviewed PR head `c525a28bd4fb1b758e5a784075e3c6a0a91d9edc`. Its tree was verified against the checkout used for preliminary experiments. The new work covers the original RG35XX, five pinned releases and one physical runtime capture, OBS-001.

- [Engineering specification](../docs/bootloader-initialization-contract.md) covers the ROM boundary, SRAM ownership, clocks, timer, UART, PMIC, board mux, DRAM, AFI, app.bin, U-Boot, storage, Linux, recovery and retention. It defines four implementation profiles from SRAM entry through independent Linux transfer.
- [Structured contract](../evidence/firmware/bootloader-initialization-contract.json) has 12 stages, 72 operation IDs, 71 curated register references, 21 configuration fields, 95 typed dependencies, ten terminal branch rules and 18 prioritized uncertainties. The curated [input](../specifications/bootloader-initialization.json) distinguishes instruction and model evidence from compatibility, conservative, board-specific and other implementation classifications. Source selections bind to paths, keys/IDs and SHA-256. Known compatibility addresses coexist with explicit unknown physical data. The pinned upstream ARM ABI and PMIC comparison have [file-level provenance](../specifications/bootloader-source-references.json).
- [Register timeline](../evidence/firmware/boot-initialization-trace.json) contains 16 focused cases. It preserves 31,059 ordered hook events in RLE, plus 614 indexed supplemental observations for delay requests, selected SRAM stores and CPU control writes. The raw access coordinate includes actual PC and distinct accessor/poll site where relevant. Later U-Boot/startup assumptions, transferred-state calls, script/FAT model and Linux-boundary state are explicit. The [generated reference](../docs/bootloader-operation-reference.md) and [dependency report](boot-initialization-dependencies.md) provide the human-readable view.
- The validator checks 1,304 assertions over 65 executed or state-checked operations and 63 ordered dependencies (figures at review revision `984d223`; superseded by the [corrective verification](#corrective-verification-of-the-initialization-contract) below). It reconstructs the exact AFI and primary INI bytes from SRAM stores, checking downstream AFI, RAM bank and entry state. It covers GPIO omission on SD0, mode-1 PIR/precharge, ZQ timeout, an unbounded PGSR control, diagnostic failure, placement failure and the SFVD-absent dispatch.
- Reverified separate SD0/SD2 post-DRAM clock words `0xb0160050`/`0xb0160058`. Re-entry restarts timer 0 and makes extra writes outside the initial timer phase. Pinned Koriki U-Boot startup statically loads initial stack `0x050ffff0`, uses r9 startup data, and computes relocation from runtime state; the actual destination and allocations remain unresolved.
- Historical unified and standalone evidence, contradictions and OBS-001 remain intact. The unified runner's only shared code change exposes an overridable loader class for replay instrumentation. Existing behavior and archived trace hashes are preserved.

## Validation and reproduction

Use the locally available verified expanded images in `ATM_FIRMWARE_DIR`, extracted stock loader regions in `ATM7039S_STOCK_LOADERS`, and pinned source tree layout in `ATM_SOURCES_DIR` for the corresponding tests. See the [tool reference](../tools/README.md#bootloader-initialization-contract).

```sh
python tools/bootloader_contract.py generate
python tools/bootloader_contract.py validate
python tools/bootloader_contract.py compare
ATM_FIRMWARE_DIR=FW python tools/bootloader_contract.py replay --check
ATM_FIRMWARE_DIR=FW python -m unittest tests.test_bootloader_contract -v
python -m unittest discover -s tests -v
python tools/research.py validate
python tools/research.py generate --check
python tools/render_catalogue.py
python tools/render_html.py
```

| Local check | Result |
|---|---|
| Ordinary unit suite | 532 tests run, 501 passed, 31 optional skips |
| Contract with pinned firmware | 20 passed including an independent byte-identical timeline regeneration |
| Contract validator | 16 scenarios, 1,304 assertions and 63 ordered dependency checks |
| Research validation and rendering | Zero validation errors. Generated register outputs and rendered catalogues clean. 54 HTML documents rendered |
| Laboratory software | Chromium smoke passed. Linux module self-test passed with simulated disk inventory |

## Highest-value remaining observations

Actual ROM entry and SRAM ownership would remove the first SRAM-only blockers. A verified board revision with DRAM markings and a stock early boot record would distinguish the plausible geometry/training outcomes. PMIC identity and stock rail behavior would qualify the electrical power sequence. A trustworthy U-Boot startup memory map would distinguish relocation and reservation requirements for profile C. No observations in this section are procedures or authorization.

Stock messages such as `--pmu- ok`, `PMU_CTL3`, `s2 flag`, `pmu_status`, `DRAM init mode0` or `mode1`, rank/width and lane `Fail:` lines, `Ok:DCU_CFG:`, `==ddr_test`, `== ok==` or diagnostic mismatch, `load fail to adfu`, and `load uboot:` would discriminate different outcomes. The `bootdev= 0x22` print is an INI field shared by both SD outcomes. For downstream medium, correlate `emmc boot`/boot flag with the actual controller and command line. Retention stays a separate qualification issue under C-RESUME-DRAMRST.

---

# Corrective verification of the initialization contract

An independent review of `984d2232c6d783762b1d3cef2c8fc5edb6448ac9` reported six issues. All six were confirmed against the actual loader instructions and corrected. The firmware reconstruction, historical DRAM experiments, unified emulator, OBS-001 and every historical evidence file are unchanged. The raw ordered timeline is byte-identical and still reproduces from firmware. Full detail is in the [verification report](bootloader-contract-verification.md), and the chronological record is in the [correction log](bootloader-contract-correction-log.md).

## Corrected semantics

- **Bus selector.** Cold input 0 is fixed x32 with no fallback, 1 is fixed x16, and 2..255 start x32 with automatic x16 fallback (`0xb4067434..0xb4067464`). The working byte encodes the attempt width (0 x32, 1 x16). A persistent training failure writes back `min(input, 2)` for bus and the cs input (0 for inputs above 2) (`0xb4069020..34`). Only internal `0x1017fa11` retries. DFI, ZQ, PHY-init and capacity failures return `0x1747fa11` immediately. The previous DFI retry transition was wrong.
- **Capacity.** `capacity_MiB = 2^(row_code + column_code + capacity_width_operand + chip_select_count + 3)` for bank code 0, with operand 1 for x16 and 2 for x32 (`0xb4068e18/1c`). Bank codes 1–3 give `3·2^(… + 1)`. Accepted exponent 25..31 (32..2048 MiB). Larger exponents return `0xc000fa11` → `0x1747fa11`.
- **Other corrections.** The FDT reservation of the reference does not cover the final blob (`0x7000` reserved, `0x7080` total). PMIC byte order is static-only. The UART divisor subtracts one only for a nonzero quotient. INI bytes +0x19/+0x1a were added as open fields. Per-release references are keyed.

## New verification architecture

- `specifications/bootloader-initialization.json` adds `semantics` (dram-bus, dram-rank, dram-retry, dram-capacity, dram-timing), structured record placement, AFI fields with generation/admission/consumer rules, SRAM ranges with basis, derivation and declared overlaps, `attempts`, explicit boundary windows, state-check roles, branch absence confirmations and terminal PCs, static instruction bindings and the FDT reservation fact.
- `tools/contract_semantics.py` interprets those definitions and compares them with `evidence/firmware/dram-selector-semantics.json`, which records 240 executions of the actual Koriki and 20231014 loaders with an instruction and literal audit. It also compares them with `tools/ddr_model.py` (12,224 combinations), historical SD2/unified evidence, firmware bytes in the trace, executed U-Boot getters and pinned sources.
- `tools/bootloader_contract.py` adds fail-closed windows with RLE clipping, an `Observation` that separates execution, value and absence, per-attempt DRAM validation with retry prediction, forbidden-anchor scanning, generated contract tables, the `sources` mode and itemized coverage statistics.

## Coverage after correction

72 operation definitions: 57 observed in the event stream, 8 executed only through stage state, 1 checked by a value assertion only (`memory-plan`), 5 bound only to audited static instructions or the U-Boot startup audit (`clock-basis`, `globals`, `publish-pointers`, `uart-output`, `uboot-relocate`), and 1 without verification (`rom-entry`, whose physical entry state is unknown). `delay` is both observed and statically bound. There are 1,350 applied checks in 16 traces. Of 95 dependencies, 49 are ordered globally and 14 within 20 executed DRAM attempts; 32 have no trace order and 3 are unresolved. Eleven failure paths confirm the absence of Linux entry. The specification no longer contains a `first-before-first` DRAM comparison.

## Reproduction

```sh
python tools/bootloader_contract.py generate
python tools/bootloader_contract.py validate
python -m unittest tests.test_contract_semantics tests.test_bootloader_contract -v
ATM_FIRMWARE_DIR=FW python tools/bootloader_contract.py replay --check
ATM_FIRMWARE_DIR=FW python tools/contract_semantics.py check
ATM_SOURCES_DIR=SRC python tools/bootloader_contract.py sources
```

`FW` needs `koriki-v1.0.img` and `stock-20231014.img` for the contract. The historical suites need all five images. `SRC` uses the `tools/build_dataset.py` folder names (`linux/`, `u-boot_s500/`).

<!-- results -->

## Open questions

The correction leaves every physical uncertainty open. These are the Boot ROM entry state, SRAM extent and ownership, medium-specific ROM behavior, PMIC identity and rails, DRAM geometry, real PHY training, controller/PHY revision, GPIO electrical semantics, U-Boot relocation and reservations, `C-RESUME-DRAMRST`, and modern Linux prerequisites. The contract is an offline engineering reference. It does not authorize physical testing or flashing.
