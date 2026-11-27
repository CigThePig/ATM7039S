# SD2 DRAM initialization, training and memory detection

The executed memory-init caller reproduced the earlier SD0 findings on the reconstructed SD2 path across five verified firmware releases. In ordinary continuation, the SD2 GPIO loopback completed and the two runs agreed on DRAM operations, capacity, return path and AFI size. The AFI boot-device byte was `0x20` for code 0 and `0x22` for code 2. The matrix executed 52 paired scenarios per release, with matching results in 255 of 260 pairs after accounting for the named differences. All five remaining pairs are the exact-echo control, which sent code 2 to recovery before DRAM. Evidence is in [sd2-dram-comparison.json](../evidence/firmware/sd2-dram-comparison.json).

## 1. Research scope and provenance

The comparison asks whether the early loader's code-2 GPIO effects carry into DRAM initialization, including unsuccessful or resumed initialization. The hardware hypotheses cover ranks, bus widths, status responses, RAM aliases, faults, wake state and GPIO input behavior. All execution and memory writes occurred in emulators.

| Release ID | Acquisition | Role |
|---|---|---|
| `koriki-v1.0` | Koriki v1.0, `koriki-v1.0.img.gz` | Reference for OBS-001 and the isolated DMM baseline |
| `stock-221203` | Anbernic 221203 | Independently executed caller matrix |
| `stock-221223` | Anbernic 221223 | Independently executed caller matrix |
| `stock-230309` | Anbernic 230309 | Independently executed caller matrix |
| `stock-20231014` | Anbernic 20231014 | Independently executed matrix with changed ODT/drive input |

The tool checks the whole expanded image's SHA-256 and length against the pinned acquisitions, then reads 448 sectors from disk offset `0x200200`. It records the verified image and loader hashes, block 0, the bootloader-code region, narrower function and literal ranges, tool versions, and each record's shipped bytes. Function and literal checks include the main dispatch, INI helpers, both DRAM wrappers, embedded tables, ADFU checks and AFI writer. The stored boot code is the SRAM word at `0xb4064c00`. The getter at `0xb40664f0` loads it at `0xb40664f4`. The caller reads it for the medium check, the ADFU guard when applicable, and the AFI wrapper when reached.

## 2. Execution and assumptions

The harness supplies the INI SRAM image, cleared globals and boot word at main `0xb4065420`. The actual instructions call `0xb40665d0` with `r1=0`, run timer setup, board initialization, PMIC initialization and the ADFU decision, select the DRAM path, and execute main's dispatch on return. The earlier [pre-DRAM study](sd2-predram-reconstruction.md) covers the block-0 and storage sequence preceding this entry. The desired next-stage boundary is main `0xb4065440`, before it sets the instruction cache and loads the next stages. Main's early recovery dispatch is `0xb4065494`. The separately verified [ADFU study](adfu-loopback-reconstruction.md) covers the ROM re-entry sequence after `0xb40691a4`.

The PR #6 harness supplies a synthetic PMIC register file at the accessors, a status oracle for PUBL/uPCTL, and sparse DRAM. PMIC detection, transport, UART/printf and elapsed-time execution have explicit stubs. The GPIO clock advances by the requested delay. The primary model returns C10 low, while additional scenarios vary initial GPIO, C10 input and data readback. Unimplemented GPIO-window addresses use fall-through RAM-like storage per address, seeded or zero before the first write. Other unknown MMIO reset values use a declared seed. Each such access is visible in the detailed trace and the compact unsupported/synthetic access summary.

Both boot codes receive newly constructed CPU, PMIC, GPIO, training and RAM state. Each instruction budget starts at the supplied entry, restarts at normal ADFU return, and restarts again before resume if main dispatches there. This gives both paths the same observation interval for indefinite downstream polls despite the extra GPIO sequence. Poll names require verified firmware sites. Any other bound expiry is a generic instruction-limit outcome.

## 3. Ordered comparison

The trace uses actual hook order for MMIO reads and writes, PMIC accessor transactions, synthetic RAM accesses and watched SRAM loads and stores. Every event carries width, operation, address, value, instruction PC, attributed accessor call site when available, phase and the rule that produced a synthetic read. Identical adjacent events use lossless run-length encoding. The evidence preserves raw hashes before applying three exact comparison rules:

| Difference | Rule |
|---|---|
| GPIO loopback | Omit the identified 32-bit reads and writes at each verified ADFU GPIO accessor site and address. Compare the omitted ordered values separately against the independent ADFU model. |
| Boot word | Canonicalize the expected numeric boot word only at the getter load and one of its three verified call sites. Verify the observed word and sites for the path taken. |
| AFI boot device | Canonicalize `0x20` and `0x22` only at the byte store `0xb4066538` to `0xb4060305`. Compare the unmodified AFI bytes and list each changed byte offset. |

The first unequal ordered event is retained for raw and normalized traces. Boundary state covers startup, before and immediately after ADFU, cold and resume entry, controller/PHY programming, each training request and outcome, DFI, capacity/final DMM setup, diagnostic return, write-back, AFI and the terminal boundary where reached. CPU snapshots record r0–r12, SP, LR and CPSR. Normal return from ADFU can leave different caller-saved registers, LR and NZCV flags. The comparison retains the exact deltas at `0xb4066684` and requires CPU state to agree at the later shared boundaries. Stored configuration geometry can bypass the alias probe even though it crosses the capacity-calculation phase. At each common boundary the tool records raw state hashes and any state delta. Entry register comparisons account explicitly for the persistent GPIO bits. Full snapshots and raw events are available through `run --detail`.

The modeled peripheral register state agrees at ADFU entry. It agrees again on normal return at `0xb4066684` with the boot word and named GPIO values represented separately. From DRAM entry, firmware register, PMIC and RAM accesses agree in the paired traces until AFI's device-byte store or the actual exit boundary. The exact-echo control diverges at recovery by design.

## 4. Cold initialization and training

The cold wrapper at `0xb40690b8` leads to the core at `0xb40673f4`. The shipped detection record requests 468 MHz and uses automatic rank detection. The traces retain PLL, clock gate and reset programming, DMM configuration, controller state and PHY requests. The observed ordering agreed for both boot codes.

| Synthetic condition | Result in both continuing paths |
|---|---|
| One x16 rank | The initial two-rank attempt gets PGSR `0x3f`. One-rank retry gets `0x1f`. DMM `0x202c`, 256 MiB, diagnostic passes. |
| Two x16 ranks | First attempt succeeds with two chip selects. DMM `0x213c`, 512 MiB. |
| Patched automatic width | The attempted (rank count, width) sequence is (2, 32), (1, 32), (2, 16), (1, 16). The last attempt succeeds under the x16 single-rank hypothesis. |
| Lane status nonzero | The first attempt prints its synthetic DXGSR words and the single-rank retry succeeds. |
| Persistent training error | Returns `0x1017fa11` after two attempts. |
| Missing ZQ, initial PHY or DFI readiness | Internal codes `0x2a00fa11`, `0x9a00fa11`, `0xdf00fa11` respectively return as `0x1747fa11`. An initial dual-rank DFI timeout takes the rank retry, then returns the DFI failure. |
| PGSR never reaches the init-complete value | Emulator stops in the firmware's unbounded PGSR poll. |
| PGSR `0x5f` after training | Firmware loops waiting for `0x1f` or `0x3f`. |
| Controller stuck before Config | Emulator stops in the uPCTL state poll. |
| Patched LPDDR-type record | Executes the alternative PIR/programming branch with synthetic responses on both codes. This expands instruction coverage under a hypothetical record. |

The PGSR, DFI, ZQ and DXGSR values are explicitly supplied by software. The paired comparison does not measure analog margin, timing or training feasibility.

## 5. Configuration records, capacity and write-back

The caller copies the primary INI record at `+0x1c` and the detection record at `+0x4c` into globals. On cold boot, nonzero `ini+0x2c` executes the copy of the secondary record over the primary working globals. The synthetic selector-zero case executes the primary path and keeps the shipped geometry. Resume bypasses this selection and takes the persisted primary. Raw records in the evidence retain clock, capacity, width, chip select, type, row/column and ODT/drive fields.

The firmware can write detected values back to the primary record in SRAM on success and also rewrite it after a returned initialization failure. The trace counts actual stores to `ini+0x1c` through `+0x2b` and retains the selector and second record. Later storage persistence involves app.bin and its SFVD check, covered in the [stock boot-chain analysis](stock-boot-chain-reconstruction.md).

The alias probe's limits remain important. Column search can saturate at its highest code. A missing row alias can leave row code zero. The inherited PR #4 envelope produced 128 MiB for the synthetic unsupported-row case and 1024 MiB for the unsupported-column case. The patched x32/two-rank geometry overflow reaches internal `0xc000fa11` and returns `0x1747fa11`; this differs from the unreachable exponent-32 guard in the row-search loop. Both codes have the same result in each tested capacity case.

## 6. Geometry and diagnostic

The isolated baseline executes the firmware's mode-0 wrapper for 180 combinations of rank count, bank count, row and column width and three DMM orders. It supplies the selected record, then calls write-back and the test after a successful return. Nine representatives also run through the paired caller, including a boundary outside the isolated matrix. The evidence groups observable outcomes by return code, reported capacity, row/column code, chip-select count and diagnostic message. There are 64 observable outcome groups. The firmware over- or underreported capacity in 128 cases, and the diagnostic passed in 73 of those. All eight caller cases also present in the isolated matrix reproduce the isolated outcome.

| Device and DMM hypothesis | Implication |
|---|---|
| One x16 rank, 8 banks, 10 columns, 14 rows, col → bank → row | Consistent with the shipped primary record, expected DDR3 geometry and a modeled 256 MiB result. |
| One x16 rank, 4 banks, 10 columns, 14 rows, col → bank → row | Firmware-equivalent output within the model. Four banks conflict with the stated single DDR3 device hypothesis. |
| One x16 rank, 8 banks, 10 columns and 12 rows, col → bank → row | Can be overreported and pass the diagnostic. An apparent pass has limited power to reject alias hypotheses. |
| One x16 rank, 8 banks, 10 columns and 13 rows, col → bank → row | The representative 128 MiB configuration gives a result that can be distinguished from the shipped 256 MiB record under this decode model. |
| col → row → bank or bank → col → row | The 180-case matrix rejects these specific models as reproductions of the shipped record. Address mappings outside the tested orders and widths remain open. |
| Two trainable ranks | The reference rank-detection case reports 512 MiB. A physically present rank that cannot train under the selected configuration remains observationally ambiguous. |

| Firmware-visible comparison | Result |
|---|---|
| 64 MiB (12 rows) vs 128 MiB (13 rows), col → bank → row | Both report 128 MiB, `rcc=0x08`, one chip select and a passing diagnostic. |
| 128 MiB (4 banks) vs 256 MiB (8 banks), 10 columns/14 rows, col → bank → row | Both report 256 MiB, `rcc=0x48`, one chip select and a passing diagnostic. Both match the shipped primary bytes. |
| 256 MiB, 10 columns/14 rows/8 banks, across the three tested decode orders | Col → bank → row reports 256 MiB and passes. Bank → col → row reports 512 MiB and passes. Col → row → bank reports 1024 MiB and fails the diagnostic. |
| Extended 12-column/17-row case, col → bank → row | The 8192 MiB modeled geometry reports 2048 MiB and passes. This case is outside the isolated matrix. |

The evidence supports high confidence in the instruction-level non-identifiability result and only inferential confidence in the DDR3 x16 single-rank geometry. The actual DRAM marking, address-map documentation and early training results would distinguish the remaining physical possibilities.

The diagnostic uses `N = (MiB << 18) mod 2^32` 32-bit words. It writes and checks power-of-two word indices from 4 below N, then tests word indices `0x10 + k * 0x41114` below N. Each write uses the word index as its value and the first incorrect read terminates the test. The traces include access counts, the result, console text and ordering. The independent software model replays each applicable diagnostic sequence and compares values, addresses and messages. A 128 MiB wrap inside a reported 256 MiB range can pass. A 128 MiB open tail, selected dropped writes, stuck bits or injected read errors can produce failures. When initialization succeeds and the diagnostic reports a failure, main still reaches the next-stage boundary.

One oracle defect surfaced with selector zero. With two DMM writes and no alias probe, the legacy fallback used the write count to assume column-sized addressing during the diagnostic. That artificially wrapped the test at the column span. The new comparison uses the whole modeled rank during the diagnostic. Explicit DMM models continue to apply their own address decoding. PR #6 evidence still regenerates with its original harness.

## 7. Failure, recovery and resume

The caller reaches SRAM write-back and the AFI writer after the returned cold error paths above. Main then executes its conditional branch to recovery and the run stops there. A valid AFI magic value and even a fresh store therefore provide insufficient evidence of usable memory. A bad INI version reaches main recovery before DRAM. PMIC status bit 1 and a synthetic read error for register `0x35` stop both codes at early ADFU. The GPIO exact-echo control stops code 2 there. These controls record no DRAM entry or AFI store.

The ordinary resume, S4-origin, missing vector, training/ZQ failures, alarm-driven checks, bit-31 wake case, stale capacity, inconsistent chip select, early PMIC ADFU and unsupported PMIC version cases were exercised for both codes. Mode 1 uses the primary record. A patched 512 MiB capacity is used as stored and can reach the vector. The inconsistent chip-select record can likewise continue despite a nonsensical DMM configuration. Valid resume branches to the synthetic vector and stops before its first instruction. A high vector bit without alarm wake is cleared before transfer. The alarm case reaches power-off after self-refresh; failed mode-1 cases reach the recovery-alarm and modeled power-off path. The tool captures PMIC reads/writes, vector flags, protection against unmodeled vector execution, PREA/REF commands, final register state and terminal PC. Resume produces no AFI stores. Timing and PIR differences between the cold and resume algorithms agree for a given mode across boot codes.

### C-RESUME-DRAMRST

Both boot codes write PIR `0x3f` in the same resume sequence. This sets bit 5 while bit 6 is clear. The observed firmware reset, training and refresh sequence plus the eventual kernel-vector handoff establish the intended preservation flow. The electrical DDR3 RESET# behavior is still open.

| Public source | Observation | Applicability |
|---|---|---|
| Pinned U-Boot RK3288 [header](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L274) and [driver](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/drivers/ram/rockchip/sdram_rk3288.c#L388) | Related uPCTL/PUBL layout, PIR offset 4 and PGSR offset 12. The cold DDR3 path requests DRAMRST and DRAMINIT together. | Related IP layout. The examined code supplies a cold initialization example and no verified ATM7039S PHY revision. |
| [Microchip SAMA7D6 DDR3PHY PIR](https://onlinedocs.microchip.com/oxy/GUID-82119957-1E11-4B69-84AC-EF0EA08F5595-en-US-5/GUID-17C1D14E-6C75-4D58-95E6-CE141F571720.html) | PIR offset 4, DRAMRST at bit 5 and DRAMINIT at bit 6. Its DDR3 reset output can be triggered independently and is held low for the specified reset interval. | Direct documentation for the SAMA7D6 PHY. The section gives no matching ATM7039S revision. It rules out using a matching register layout alone to assume that bit 6 gates reset. |

A revision-specific ATM7039S PHY document or vendor retention implementation could narrow this further. The earlier LPDDR instruction analysis also observes `0x3f` in mode 1. LPDDR lacks a DDR3 RESET# output, so the literal alone is insufficient to generalize its effect across modes or PHY integrations.

## 8. GPIO state and downstream dependencies

In the synthetic mixed and latch readback models, the test restores both GPIO direction registers. It clears PULLCTL1 bit 17 and leaves CDAT bit 11 low. The remaining CDAT bits depend on input/latch semantics. Zero, all-ones and mixed seeds, nonmatching low, inverted and near-echo inputs, and a latch-only input assumption were exercised. The comparison also seeds `0xb01b00b4` independently to track its retained upper bits. The core writes that pad-region word under both boot codes. It is a separate register from the direction, data and pull addresses that the ADFU test changes.

No subsequent caller access to the four affected addresses was observed in any executed cold, failure, retry or resume path. The static scan identifies pre-ADFU PMIC detection GPIO accesses on conditional paths and 122 unresolved accesses in the cold DRAM subtree. PMIC detection remains stubbed here and is covered by the earlier pre-DRAM research. Dynamic hooks capture direct and computed accesses on executed paths. Neither method establishes the absence of an electrical effect or covers a later stage. `C-PREDRAM-PATH` records that distinction.

## 9. AFI handoff and cross-release behavior

AFI scratch starts at a declared synthetic seed (zero in the matrix). The AFI wrapper `0xb4066588` reads the boot code and calls the writer at `0xb4066500`. The reference code-0 record is `414649000020030000c2010000000010` and code 2 produces `414649000022030000c2010000000010`. Decoding gives boot mode 0, UART 3 pad 0 at 115200 baud, and `ddr_size=0x10000000` for both. The AFI size conversion uses the record's 16-bit capacity shifted by 20 with 32-bit truncation. Failed cold initialization can store `ddr_size=0x80000000` from the working record. The main continuation decision governs whether those bytes could reach a later consumer.

221203, 221223 and 230309 reproduce all 52 Koriki pairs exactly. Both boot codes were independently executed on every release for all caller scenarios. The loader code/literal comparisons allow sharing the instruction interpretation. 20231014 changes both records' ODT/drive bytes from `01 01 0c` to `02 02 09`. In the reference comparison this changes MR1 from `0x06` to `0x42` and ZQ0CR1 from `0x4c` to `0x29` and changes diagnostic console and SRAM INI bytes. Some bounded polls have different event counts or final PCs because the variant executes a different number of programming instructions before the poll. The raw cross-release deltas include the first unequal event and the observed value or count differences by site. The whole-caller comparison runs are independent of this cross-release grouping.

## 10. Model validation and OBS-001

The independent `ddr_model` computes mode-0 and mode-1 write sequences, timing fields and record results for the applicable DDR3 inputs. Each compared sequence uses the actual entry record and relevant modeled seeds. The synthetic geometry and probe outputs are shared assumptions. The separate diagnostic model gives a second check of the memory accesses and first-failure cases. The evidence also records internal and expected returned codes, and independent GPIO ordering, state and recovery checks.

OBS-001 directly gives a Linux `boot_dev=sd2`, a boot card on controller `0xb0238000`, the complete command line, and a DT/System RAM range of `0x00000000..0x0fffffff`. Its kernel memory accounts separately for 237548 KiB MemTotal, the boot-time memory line and reservations. Projecting the synthetic reference AFI through the separately reconstructed U-Boot handoff yields the same DT memory bank. The full SD2 command-line match comes from the earlier pinned boot-path experiment. Boot code 2 and AFI `0x22` remain an inference for the physical observation, which has no live AFI, electrical training, actual rank, PCB pad readback, PMIC voltage, Boot ROM state or early serial measurements. OBS-001's original predictions and outcomes remain in its capture record.

## 11. Handoff and reproducibility

An independent cold bootloader design can use the recovered record flow, programming sequence, error logic and AFI layout for the reconstructed SD2 path. The remaining hardware dependencies include ROM state, the actual DRAM part and DMM decoding, regulator behavior, tuning and retention. The geometry hypothesis stays an inference. No app.bin or U-Boot integration is required to consume the result format.

`run` emits a versioned result with the firmware identity and experimental inputs. A single result includes executed boot code and reads (in detailed trace), classified outcome, terminal PC, caller and DRAM return codes, the main continuation boundary, actual AFI bytes and stores, selected and final records, capacity when the DRAM routine succeeds, diagnostic status, and unsupported responses. In resume, that capacity is taken from the persisted record. A later boot-chain module should require a cold outcome and main continuation before consuming the generated AFI. Write-back and AFI flags are based on actual SRAM stores, distinct from value equality. The committed evidence keys each release/scenario to an independent result digest in `distinct_pairs`.

```sh
python -m pip install -r requirements-firmware.txt
python tools/sd2_dram_analysis.py list
python tools/sd2_dram_analysis.py run --firmware-dir FW --release koriki-v1.0 --scenario reference --detail
python tools/sd2_dram_analysis.py run --firmware-dir FW --scenario mixed-gpio-bus-retry --boot-code 2 --mmio 0xb01b00b4=0x80000000
python tools/sd2_dram_analysis.py suite --firmware-dir FW --release stock-20231014 --group resume
python tools/sd2_dram_analysis.py suite --firmware-dir FW --group geometry
python tools/sd2_dram_analysis.py evidence --firmware-dir FW OUT.json
ATM_FIRMWARE_DIR=FW python -m unittest tests.test_sd2_dram_analysis -v
```

`FW` holds the five expanded images named in the acquisition manifest. `ATM7039S_STOCK_LOADERS` is the historical directory of `loader-<release>.bin` extracts, each 448 sectors at disk offset `0x200200`. `ATM_SOURCES_DIR` holds the pinned source trees for the historical ADFU audit. See [the persistent research handoff](pr9-research-progress.md) for validation and follow-up context.

## Unified follow-up

The later unified tool reuses this comparison harness and adds live block-0, pre-DRAM and cold post-DRAM state. The original stage results and evidence remain reproducible independently. [Unified research](unified-boot-chain-reconstruction.md)
