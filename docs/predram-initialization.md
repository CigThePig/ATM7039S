# Pre-DRAM initialization of the stock early loader

Technical reference for the code that runs between the Boot ROM handing control to loader block 0 and the cold DRAM init call `0xb40690b8`. Scope: the original RG35XX (ATM7039S), stock 221203/221223/230309/20231014 and Koriki v1.0 (loader identical to 230309). All addresses are SRAM VAs; `bootloader.bin` offset = VA − `0xb4060000`.

Evidence: [`evidence/firmware/sd2-predram.json`](../evidence/firmware/sd2-predram.json), produced by [`tools/predram_analysis.py`](../tools/predram_analysis.py). Findings **BOOT-024, BOOT-025, CLK-007, UART-004, PMIC-002, GPIO-002** (refines BOOT-021). Full report: [reports/sd2-predram-reconstruction.md](../reports/sd2-predram-reconstruction.md).

**Evidence limits.** Instruction facts are decoded from pinned images. Execution facts come from Unicorn runs where every peripheral read follows a named synthetic rule. None of this was observed on hardware, and none of it is a safe initialization recipe. Register names are labels from related-SoC headers (`candidate:` blocks), not verified ATM7039S semantics.

## Sequence

| # | Function | What it does before DRAM | Depends on | Boot code |
|---|---|---|---|---|
| 0 | block 0 `0xb4060000` | reads `0xb01600a0`: bit 7 → code 2, else bit 4 → code 0, else SRAM `0xb4060408` test → 4/5; stores the code at `0xb4064c00`; codes 0/2: ROM service r9=4, sector `0x102b`, 0x50 sectors → `0xb4065400`, `blx` | Boot ROM state | produces |
| 1 | main `0xb4065400` | memset `0xb4070800..0xb407087b` (globals) | — | |
| 2 | load_ini `0xb4065d04(code)` | codes 0/2: disk `0x202600`, 8 sectors → `0xb4062400` via `0xb4065bac` → `0xb4065b24` → ROM service | ROM service | same for 0/2 |
| 3 | dram_caller `0xb40665d0(ini, 0)` → ini_to_globals `0xb4065ff8` | ini → globals (table below) | 2 | |
| 4 | timer_init `0xb4069440(0)` | gate `0xb01600a4` bit 27; `0xb0168008/10/0c` := 0 (twice); `0xb0168008` := 4 | — | |
| 5 | uart_init `0xb4066784(3, 115200, 0)` | gate `0xb01600a4` bit 19; reset `0xb01600ac` bit 15 clear / 1 µs / set; `0xb0126000` := `0x8003`; `0xb01600b0` := 25; **no pin-mux write** | 4 (delay) | |
| 6 | get_boot_code == 5 → spinand_restore `0xb40663f8` | not taken for 0/2 | | 5 only |
| 7 | ini_print `0xb40661b0`, ini_version_check `0xb4066194` | prints `row_col`, `ddr_cap`, `bootdev= 0x22` (ini byte), `scan`; ini must start `"1.1"` else return −1 → ADFU | 5 | |
| 8 | board_mfp_init `0xb406a608(ini+0x0d = 1)` | `0xb01b0048`: clear `0xe39e0`, set `0x619c0` | | |
| 9 | pmu_init `0xb40699e8(cfg, sp+4, 2)` → pmu_detect `0xb4069890` | clock-out select, I2C1 bus set-up, PMIC id checks, regulator writes, suspend flags (PMIC table) | 4 | |
| 10 | adfu_check `0xb4069254(ini word +0x14 = 1)` | PMIC reg `0x35` bit 1 → ADFU; **code ≠ 0: GPIO loopback test** | 4, 9 | **differs** |
| 11 | publish_globals `0xb406622c` | pointers → `0xb4064c60..0xb4064c74` | | |
| 12 | resume test `0xb4066688` | `[0xb4070874]` and `[0xb4070878]` ≠ 0 → return 2 → resume_entry `0xb40664e4` | 9 | |
| 13 | second record `0xb40666ac` | ini+0x2c ≠ 0 → 12 bytes `0xb407084c` → `0xb4070820` | | |
| — | **boundary** `0xb40690b8(0xb4070820)` | clears mode bytes `0xb4070804/5`, tail-calls `0xb40673f4` | | same argument |

Exits before the boundary: return −1 (ini version) → `0xb4065494` → `0xb40693e0` → `0xb40691a4`; adfu_check → `0xb40691a4`; return 2 → resume; permanent loops at `0xb40699c4` (PMIC id), `0xb4069f2c` (version 0), `0xb406a194` (init error).

## Globals written from bootloader.ini

| ini | Global | Use |
|---|---|---|
| +0x0c | `0xb407081c` | printed as `bootdev=` only (0x22 in every release; not the AFI value) |
| +0x0d | `0xb4070810` | board_mfp_init index |
| +0x0e / +0x0f / +0x10 | `0xb407082c` / `0xb4070830` / `0xb4070834` | UART index / pad / baud, later AFI bytes 6/7/8 |
| +0x14 (word) | argument | adfu_check enable (1) |
| +0x18 / +0x19 / +0x1a / +0x1b | `0xb4070858` [0] / [1] / +4 / +8 | PMIC I2C bus (1) / ? / ? / reg 0x14 adjust (3 → 9) |
| +0x1c.. (12-byte map) | `0xb4070820` | primary DRAM record |
| +0x4c.. | `0xb407084c` | second record (used when +0x2c ≠ 0) |
| — | `0xb4070800` | UART table entry pointer; `0xb407080c` timer index |

## Boot code 0 vs 2

The boot-code word is read pre-DRAM by load_ini/storage dispatch (same branch for 0 and 2), by dram_caller (`== 5` only) and by adfu_check (`!= 0`). Only adfu_check differs:

1. `0xb01b0064 &= ~(1 << 17)` (not restored)
2. save `0xb01b0018` (OUTEN C) and `0xb01b001c` (INEN C); C10 → input, C11 → output
3. 32 times: `0xb01b0020` bit 11 := next bit of `0x55aa55aa` (LSB first); `delay_ms(1)`; sample bit 10
4. restore OUTEN/INEN; data bit 11 stays at the last pattern bit (0)
5. sampled word == `0x55aa55aa` → "Prepare to entry ADFU mode" → `0xb40691a4`

So code 2 adds about 32 ms of requested delay and leaves two bits changed.

**Refined in the ADFU reconstruction** ([report](../reports/adfu-loopback-reconstruction.md), BOOT-026/027, GPIO-003/004):
* The guard is strictly `code != 0`; a failed PMIC read (`0xffff`) also enters ADFU.
* The loop always completes all 32 iterations and needs an exact echo.
* C10/C11 are the **SD0 DAT0/DAT1** pads (vendor pinctrl data), so the test runs on the TF2 slot. PULLCTL1 bit 17 is SD0_D0's pull-up field.
* Whether the other bits of `0xb01b0020` survive depends on the unknown GPIO read semantics.
* No later loader code uses the changed bits.

A reusable synthetic GPIO model is in `tools/gpio_model.py`. Under emulation, codes 0 and 2 give identical sequences otherwise, both up to `0xb40690b8` and (with the PR #6 harness, reference scenario) through DRAM init. The AFI `boot_dev` written after DRAM init is `0x20` vs `0x22`.

The [extended SD2 DRAM comparison](../reports/sd2-dram-reconstruction.md) re-executes both code paths with seeded GPIO, PMIC, DRAM and fault scenarios across five releases. The ordered trace records matching DRAM entry and downstream access data with the explicitly modeled loopback latch/pull differences.

## Timer and delays (CLK-007)

* Timer n control word: `0xb0168008 + 12n`; count word: control + 8. The loader uses n = 0.
* `delay_us(n)` `0xb40693f8`: waits until `(int32)(count − (start + 24n)) ≥ 0`. Wrap-safe, but unbounded if the counter stops.
* `delay_ms(n)` `0xb4069434` = `delay_us(1000n)`.
* Pre-DRAM users: UART reset pulse (1 µs), clock-out wait (300 µs, skipped if `0xb0160084` bit 0 is already set), I2C transfer timeout (≤ 501 ms per transfer), code-2 GPIO test (32 ms).
* "24 MHz" is the firmware's constant, not a measurement.

## UART (UART-004)

Table `0xb406b520` (24 × 0x30 bytes): index, pad, gate bit, reset bit, base, divider register, then up to three `{address, clear, set}` mux entries. UART3/pad 0 = entry 14: base `0xb0126000`, divider `0xb01600b0`, gate bit 51, reset bit 47, **no mux entries**. The divider is `24000000/(8·baud) − 1` = 25 (115384.6 baud if the clock is 24 MHz). TX waits while status bit 6 is set, writes base+8, then waits for bit 10. Both polls are unbounded. putc sends CR before LF.

## PMIC (PMIC-002)

The PMIC is type 2, on I2C bus 1 (`0xb0174000`), slave `0x65`, with 16-bit big-endian registers. This matches the `atc2603c` DT node (PMIC-001), so the device identity is inferred.

| Step | Access |
|---|---|
| clock-out select (1) `0xb4069710` | `0xb01b004c` bit 30 clear; `0xb0160084` bit 0 set (+300 µs); `0xb01b0084[31:30]=2`; `0xb01600d0=0x8000002d`; `0xb01b0090=0x10`; `0xb01b0094=0x20000000` |
| bus 1 select `0xb406a788` | `0xb01b004c` clear `0x50000`; gate `0xb01600a4` bit 15; `0xb01b0068 \|= 0x600`; `0xb0174004 = 0x10` |
| identity | reg 0xff must read `0x00ca` (retry with clock-out (0), then GPIO 90 pulse); probe 0x65; reg 0x32 must read `0x1bc0` (else hang) |
| init (cold path) | 0x51 \|= 0x800; 0x39 &= 0x7fff; 0x11 = 0xe84f; 0x12 = 0x68cc; 0x14 = 0x80ca \| (adj << 8); 0x15 = 0xe8ce; 0x16 = 0x334b; 0x29 &= 0x7fc5; read 0x03 (s2 flag); 0x00 = (0x00 & 0x1f) \| 0xe0c0 |
| adfu_check | read 0x35 (bit 1 → write back & ~3, ADFU) |

The electrical meaning of these writes is **unknown**. Do not read them as voltages.

## Execution environment

* Set by the firmware: A32 state throughout; the globals are cleared; ini is reloaded. Nothing before DRAM init touches CP15. SCTLR.I is changed after DRAM init (or on the ADFU exit). VBAR is written only on the ADFU exit.
* Inherited from the Boot ROM (unknown): SP, CPU mode, IRQ/FIQ masks, vectors, MMU/caches, all clock and pin-mux state, and the ROM service code in SRAM `0xb4060400..0xb4061e00`.
* Emulator choices (not facts): SP `0xb409f000`, CPSR `0x1d3`, and synthetic reads (see `synthetic_rules`). Measured stack depth: 136 bytes.

SRAM map: `0xb4060000` block 0 · `0xb4060300` AFI · `0xb4060400..0xb4061e00` ROM code (absent from image) · `0xb4062400` ini · `0xb4064c00` boot code · `0xb4064c60..c78` pointer table · `0xb4065400..0xb4093c00` bootloader.bin · `0xb406ba10` I2C bus cache · `0xb4070800..0xb407087c` globals.

## Reproduce

```sh
python tools/acquire_firmware.py koriki-v1.0-release FW --expand          # and the four stock entries (--filename ...)
python tools/predram_analysis.py evidence OUT.json --reference koriki-v1.0 \
    --image koriki-v1.0=FW/koriki-v1.0.img --image stock-221203=FW/stock-221203.img ...
python tools/predram_analysis.py trace FW/koriki-v1.0.img --boot-code 2       # readable event list
ATM_FIRMWARE_DIR=FW python -m unittest tests.test_predram -v
```
