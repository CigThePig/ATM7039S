# V3 session retrospective (OBS-001, 2026-11-27)

One owner-operated, read-only runtime capture on an original RG35XX with a spare Koriki v1.0 card. Result: **authenticated-complete**, 42 of 45 items, 12 of 12 essential, no integrity errors. The parser's "authenticated" is an integrity classification, not proof of device identity or of the procedure followed (see the attestations in `evidence/observations.json`).

## 1. What V3 established

* Four Cortex-A9 r4p1 cores online; the count comes from the SCU, not the two-node device tree (CPU-003).
* 256 MiB handed to Linux; the other memory numbers are reservations and later accounting, not contradictions (MEM-011).
* Console ttyS3; the kernel uses U-Boot's arguments unchanged; uEnv.txt is applied; the GPIOC6 strap reads high (`allenS500=1`).
* **The boot card in TF1 is on the SD2 controller (`0xB0238000`).** Combined with offline emulation, the whole chain is now known: block-0 code 2 → AFI `0x22` → `emmcboot` → U-Boot `mmc 1:1` → `boot_dev=sd2` (BOOT-022, [report](sd2-boot-path-reconciliation.md)).
* CPU frequency policy: one 10-step kernel table, capped at 1008 MHz by Koriki's `S02overclock` (CLK-006).
* Koriki writes to its root filesystem on every boot, through a double read-write loop mount (FW-021).
* The bundled PowerVR DDK (3625561) loads and matches its userspace; SGX revision 115 is reported.
* Every MMIO resource the drivers claimed is already in the canonical model (MAP-002).

## 2. What V3 contradicted

* **P-AFI-BOOTDEV and P-BOOTARGS** (preregistered as unexpected outcomes, kept as recorded): `boot_dev=sd2`, not `sd0`. The reconstruction had assumed TF1 = SD0 and followed the code-0 branch.
* **BOOT-016's U-Boot mapping** for this unit (it describes the AFI `0x20` path, which this unit does not take) and the PR #5 statement that a working SD boot needs code 0 (BOOT-012).
* **The preflight's assumption** that `boot/BATOCERA` stays byte-identical after the first boot.
* Minor: P-UENV's preregistered wording says uEnv.txt was imported by `mmcboot`; on this unit it was `emmcboot` (both import it). The prediction outcome itself (uEnv applied) stands.

## 3. What V3 could not establish

Boot ROM behaviour, the AFI bytes, U-Boot's console, DRAM size/training and the physical DRAM geometry, the CMU bit and strap level as measured values, safe frequency or voltage limits, the GPU model or clock, the board revision (no silkscreen inspection; "V6C" is a firmware string), whether NAND/eMMC is fitted but not enumerated, and whether the card's raw loader region matched the image (not checked in this session).

## 4. Problems during the session (what went wrong for the operator)

| # | Problem | Root cause |
|---|---|---|
| 1 | Dependency install failed (Windows permissions) | global `pip install` |
| 2 | `UnicodeDecodeError` | Windows default code page, not UTF-8 |
| 3 | Firmware download looked frozen | no progress output |
| 4 | Shutdown instructions unclear | guide wording |
| 5 | Placeholder commands copied literally | guide used `<LETTER>`-style placeholders |
| 6 | Boot partition got no drive letter; Windows showed the unreadable Linux partition; letters changed | drive-letter based tooling |
| 7 | Early diagnostic aborted on the unreadable partition | discovery aborted on the first failing volume |
| 8 | Multiline PowerShell paste ran commands out of order | copy-paste workflow |
| 9 | Raw Python tracebacks | no error handling for operators |
| 10 | First rootfs diagnostic took over an hour and slowed Lightroom; lost a completed scan when a letter changed | random-access parsing through the FAT layer on the card, no checkpoints |
| 11 | A re-downloaded script got a duplicate filename and the old version ran | manual file management |
| 12 | Screenshots and custom commands had to be exchanged | no self-explaining tool; no diagnostic bundle |
| 13 | Preflight `card-rootfs FAIL` was a dead end | byte-hash check applied after a boot that legitimately changes the container |

## 5. What PR #8 fixes

| # | Fix |
|---|---|
| 1, 2 | `ATM7039S-Lab.cmd` / `start-lab.sh` create a project-local `.venv-lab` (no admin, no global pip), force UTF-8, and choose a tested Python (3.11–3.13). CI found and fixed a second instance of this problem: Windows' `py -3` picking a too-new Python. |
| 3 | Every long operation shows phase, bytes, percent, rate and time left (only when the total is known), plus a heartbeat; downloads resume (HTTP Range) after any interruption. |
| 4 | The lab shows the exact shutdown action (START > QUIT > SHUTDOWN) as a checklist line. |
| 5, 8, 11 | No commands to type or paste: one page, one step at a time. The lab copies the capture script to the card itself (after a button press), verifies it and refuses other script versions. |
| 6, 7 | Cards are found by disk identity and the pinned partition geometry, not letters or labels; every check re-discovers the card, so changed letters are harmless; unreadable volumes are recorded individually; ambiguity fails closed; a different card is refused. |
| 9, 12 | Plain-language errors (what happened, was anything lost, is it safe, what next). Unexpected errors produce a redacted diagnostic bundle automatically. |
| 10 | Verified sequential local copy (2.7 s for the 2.4 GB container on SSD) then a resumable SQLite-checkpointed scan (6.5 s; 7.0 s in quiet mode), against 1,398 s for the same scan through the FAT layer. Quiet mode by default, pause/stop, below-normal priority. |
| 13 | Phase-aware root filesystem verification: fresh card = byte hash; prepared = semantic comparison with the pristine tree under evidence-derived first-boot rules; post-capture = comparison with the checked prepared baseline. Unexplained changes still fail closed. |

Session state persists across restarts; physical steps are recorded only when the operator confirms each checklist line.

## 6. Still open

* The lab has been tested with simulated Windows storage, real ext4 fixtures and Windows CI runners, **not with a real card in a real Windows card reader**. The first real use is itself a test of the tooling.
* The raw boot-region read on Windows needs one administrator approval (UAC); its elevated path has not run on real hardware.
* Flashing still uses balenaEtcher (verified writes); the lab does not write images itself, by design.
* `/run/initctl` and `/run/utmp` types are predicted from sysvinit; the next prepared-card check confirms or refutes them (a mismatch fails closed, so the operator will hear about it).
* C-PREDRAM-PATH: re-run the DRAM-stage emulation for boot code 2.
* macOS disk discovery is not implemented (manual `--card` paths work).

## 7. Before the next physical test

1. Review and merge this PR; let CI pass on Windows and Linux.
2. Decide what the next test is (see [next hardware research](next-hardware-research.md)); V3 does not need repeating unless confirming the lab on real hardware is itself wanted.
3. If V3 is rerun to prove the tooling, the operator needs: the spare card, a card reader, balenaEtcher, and about 30 minutes, most of it waiting.
