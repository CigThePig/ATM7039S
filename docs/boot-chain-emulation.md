# Causal boot-chain emulation

[Research report](../reports/unified-boot-chain-reconstruction.md) · [Structured evidence](../evidence/firmware/unified-boot-chain.json)

## Machine boundaries

| Boundary | Data carried | Coverage |
| --- | --- | --- |
| Block 0 to `app.bin` and U-Boot entry | Live A32 CPU, SRAM, stack, loaded DRAM, MMIO writes, PMIC, GPIO and timer state | One Unicorn machine. ROM reads, device responses and parts of the console are modeled. |
| Loader to bounded U-Boot consumers | Loaded payload hash and bytes, raw AFI, detected capacity, pin-mux word | Independent A32 calls with validated inputs. Runtime startup and relocation state are unavailable. |
| U-Boot to boot scripts | Actual `gd+0x34` size, boot-flag environment mutations, MMC registration and card-init status | Scripts and FAT reads use the bounded offline model. |
| Boot scripts to FDT and Linux entry | Actual DTB and boot image buffers, environment, RAM bank, modeled reservations and board data | `image_setup_linux`, libfdt, `boot_jump_linux` and cleanup execute. The kernel transfer is intercepted at the entry address. |

A cold outcome must include valid returns, the actual `0xb4065440` branch and exactly 16 produced AFI bytes. Resume and recovery have their own terminal states. A failed diagnostic can continue when firmware reaches the cold branch.

The Koriki SD2 fixups leave a final FDT size of `0x7080` bytes and a stock FDT reservation of `0x7000` bytes, both at `0x03800000`. An independent loader should reserve the final blob size. The full U-Boot runtime allocation map remains open. The next offline study should derive the relocated code, stack, global data and allocation ranges, then check those intervals against the kernel load and decompression envelope, final DTB and initrd placements. [Initialization contract](bootloader-initialization-contract.md#15-arm-linux-handoff)

## State envelope

The version, stage, method, verified image SHA-256, scenario digest, predecessor digest and payload are canonical JSON hashed with SHA-256. The next stage validates the predecessor before it runs. The same loader machine is checked against the preceding state summary. Full CPU snapshots include PC, SP, LR, CPSR and general registers. Reported SCTLR and VBAR are Unicorn register values. The payload retains exact AFI and INI records, hardware summaries and hashes of SRAM, stack window, full MMIO and ordered events where available.

The machine retains the corresponding byte buffers in memory. Evidence includes hashes and selected content. `run --detail` adds ordered loader events and phase snapshots without executable bytes or raw SRAM/DRAM dumps. The record represents physical ROM, reset, analog state, relocation and missing board information as unknown or modeled.

## Use

```sh
python tools/unified_boot_chain.py list
python tools/unified_boot_chain.py run --firmware-dir FW --medium sd2 --strap high --coverage --compare-obs
python tools/unified_boot_chain.py run --firmware-dir FW --scenario resume --detail --output resume.json
python tools/unified_boot_chain.py suite --firmware-dir FW
```

`ATM_FIRMWARE_DIR` can replace `--firmware-dir`. The suite uses both SD references on each release with focused controls on Koriki. The tool checks the acquisition hashes and accepts ordinary files. See the [research report](../reports/unified-boot-chain-reconstruction.md#22-reproduction) for regeneration and test commands.
