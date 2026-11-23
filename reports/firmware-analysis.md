# Acquired firmware and reproducible analysis

This phase acquired a complete **original-RG35XX Koriki v1.0** image and a historical V6C boot-fix archive from the project's GitHub release assets. They are public CFW artifacts. Stock ancestry is reported by community documentation but is not independently established by a stock-image hash match. No full GarlicOS 1.4.9 or Anbernic stock image was acquired.

## Acquisition identity

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `koriki-rg35xx-v1.0_20231112.img.gz` | 935,244,267 | `1ec91d71e28bffd865157844f87c4826ed8257c0ef417fd07538c1f7d57377ea` |
| Expanded image | 4,303,355,904 | `d5bd300740884d80faee2fd3ae70d91f86e6a316610c56efc0e1f7545539d6ae` |
| `bootfix_for_revision_v6c.zip` | 5,522,996 | `d14273634264eaced0daa0f8b2d7160d21c6b0aeb35b8decee5553c5ec35617c` |

Exact URLs and expansion limits are in [acquisitions.json](../evidence/firmware/acquisitions.json). Hashes pin the inspected content even if a release tag or asset changes. They identify bytes, not vendor authentication or redistribution rights.

## Disk layout

The MBR uses 512-byte sectors. Entries are non-overlapping and within the image:

| Entry | Declared type | Start LBA | Sectors | Byte offset | Bytes |
|---|---|---:|---:|---:|---:|
| 1, active | `0x0c` FAT32 LBA | 16,384 | 6,291,456 | `0x800000` | 3,221,225,472 |
| 2 | `0x82` Linux swap | 6,307,840 | 1,048,576 | `0xc0800000` | 536,870,912 |
| 3 | `0x83` Linux | 7,356,416 | 1,048,576 | `0xe0800000` | 536,870,912 |

These type labels are MBR declarations; the analysis does not claim a complete filesystem audit of entries 2 and 3. A raw analysis window starts at `0x200200`; a CRC-valid U-Boot uImage starts at `0x300000`. Thus the historical recipe offsets now have direct evidence in **one release**, without assuming stock or every CFW uses them.

## Boot components

| Component | Observation |
|---|---|
| Early-region window | DDR/test diagnostic strings and an AFI writer; no established file boundary or reset-vector mapping |
| U-Boot | 726,396 bytes including header; valid header/data CRC; load `0x05000000`, entry `0x05000040`; embedded valid 16,284-byte FDT |
| `/uImage` | Valid uImage named Linux-3.10.37; load/entry `0x8000`; 5,541,408-byte payload |
| `/adb_uImage` | Separate 5,540,848-byte image; also named Linux-3.10.37; not assumed interchangeable |
| `/KERNEL.DTB` | 28,111 bytes; independently decoded with vendor DTC and custom FDT parser, zero property differences |
| Battery DTBs | Both 2100mAh and 2600mAh variants present; does not prove battery wiring or gauge accuracy |
| `/RAMDISK.IMG` | Valid outer uImage, compression ID zero; payload is a valid gzip stream expanding to a newc CPIO magic, not executed |
| `/uEnv.txt` | Selects `os_type linux` and bootargs including `earlyprintk clk_ignore_unused selinux=0 init=/init`; no `powersave` argument in this file |
| `/BOOT/BATOCERA` | ext4 filesystem stored as a FAT file; 2,411,724,800 bytes; separately hashed and inspected with dissect.extfs |

The kernel has an internal gzip stream at uImage offset `0x44b4`. Bounded expansion yields 11,533,588 bytes and a version string for 3.10.37, GCC 4.9.4 (Linaro 4.9-2017.01), build #75 dated July 17, 2023. The expanded hash and exact string offset are in [kernel-payload.json](../evidence/firmware/kernel-payload.json). Outer compression ID zero does not imply the embedded zImage is uncompressed.

The V6C archive kernel is byte-identical to `/uImage` in the full release; its DTB differs. The release default DTB differs from the previous repository GPU DTB at four nodes: root and the ATC2603C audio, capacity-gauge and power nodes. These differences are artifact comparisons, not independently verified board properties. Source history and release hashes remain necessary to establish provenance.

## Reproduce

Use a scratch directory with at least 6 GiB free for the compressed and expanded image. Third-party firmware stays outside commits.

```sh
python -m venv /tmp/atm-analysis
/tmp/atm-analysis/bin/pip install -r requirements-dev.txt -r requirements-firmware.txt
python tools/acquire_firmware.py koriki-v1.0-release /path/to/inputs --expand
python tools/acquire_firmware.py koriki-v6c-release /path/to/inputs
/tmp/atm-analysis/bin/python tools/firmware_catalogue.py /path/to/inputs/koriki-v1.0.img evidence/firmware/koriki-v1.0-plan.json /tmp/disk-manifest.json --extract /tmp/new-components
/tmp/atm-analysis/bin/python tools/rootfs_catalogue.py /path/to/inputs/koriki-v1.0.img evidence/firmware/koriki-v1.0-plan.json /tmp/rootfs-manifest.json --extract /tmp/new-rootfs-components
python tools/boot_payloads.py /tmp/new-components/uImage /tmp/kernel-payload.json
python tools/arm_refs.py /tmp/new-components/early-region.bin /tmp/early-refs.json --start 0x6500 --end 0x65d0
```

The output manifests are deterministic and can be compared directly with committed JSON. Extraction refuses existing filenames. To reproduce the U-Boot reference inventory, remove its 64-byte header into a separate scratch component, then use `--start 0x4194 --end 0x42d0`. The payload hash is recorded in the reference inventory. All files are static inputs; nothing is mounted or run.

The FAT reader is bounded to its partition, selected files are capped at 32 MiB, gzip output at 64 MiB per stream, and acquisition expansion at the exact manifest length with an 8 GiB ceiling. Mature parsers are still untrusted-input software: use a process-level timeout/memory limit for unfamiliar images. GPT, extended partitions, FIT handling, arbitrary encrypted loaders, complete CPIO extraction and filesystem recovery remain unsupported and are not silently guessed.
