# Next hardware research: candidates after V3 (proposal only)

**Nothing here is authorized.** Each candidate needs the owner's separate, explicit approval, and V4–V7 keep the safety review and approval requirements in [hardware-validation-plan.md](hardware-validation-plan.md). This page ranks what is worth asking for, by information gained per unit of operator effort and risk, now that OBS-001 and the PR #8 offline work have answered the boot-path question.

## Ranking

| Rank | Candidate | Information gain | Operator effort | Physical risk | Verdict |
|---|---|---|---|---|---|
| 1 | **V3b: repeat V3 with the lab** (same card or a fresh spare) | Proves the new tooling on real Windows hardware; confirms the predicted `/run/initctl`/`/run/utmp` types; records the raw boot-region check OBS-001 lacked; optional extra read-only items (`/proc/bootdev`) | ~30 min, mostly waiting; no new skills | Same as V3 (read-only capture on a spare card) | Best next step if a physical session happens at all |
| 2 | **V7 (offline part): board photos** of both PCB sides, taken by the owner | Board revision (silkscreen), candidate UART3 test pads, DRAM chip markings (geometry, MEM-006) | ~10 min with the back cover off; **opening the case is a physical action that needs its own approval** | Low if done carefully; ESD and ribbon-cable risk; reversible | High value for DRAM and serial planning; no electrical contact |
| 3 | **Early serial capture (UART3)** | Loader DRAM training log (`DRAM init …`, `Ok:DCU_CFG`, capacity), `bootdev= 0x22`, U-Boot `emmc boot` and MMC messages, PMIC status — the largest single block of unobserved boot behaviour | High: needs pads identified (rank 2), a 3.3 V-or-lower USB-UART adapter of the right voltage, and fine soldering or probes | Moderate: wrong voltage or a slip can damage the board; not fully reversible if pads lift | Do not attempt before rank 2 and a written plan |
| 4 | V5 passive display observation | Panel refresh/scanout | Low | None | Low priority for the bootloader goal |
| 5 | V6 external power observation | Charging behaviour | Low–moderate | Meter may alter negotiation | Low priority |
| — | V4 spare-card source-kernel boot | Tests a rebuilt kernel | High | Boot/storage risk on spare | Premature: needs build review first |

Not proposed: any register write, clock/voltage/DRAM-timing change, overclock, destructive memory test, writes to the boot loader, or use of the owner's GarlicOS or failing factory cards.

## 1. V3b — repeat the capture with the lab

* **Question:** does the computer-side workflow work on the owner's real PC and card reader, and do the first-boot predictions hold? Secondary: record the raw loader/U-Boot comparison and the predicted file types.
* **Existing evidence:** OBS-001 (complete), the lab's simulated-session tests and Windows CI.
* **Why offline is insufficient:** real Windows storage stacks, real card readers and the operator's environment cannot be simulated faithfully; the `/run` entry types are predictions.
* **Equipment:** the PC, a card reader, a spare microSD card (4.3 GB minimum), balenaEtcher, the handheld.
* **Operator effort:** double-click `ATM7039S-Lab.cmd`, then follow one-line steps; about 10 physical actions.
* **Risk / reversibility:** identical to V3; the spare card is rewritten, nothing else.
* **Expected outcomes:** prepared-card check PASS with the four known changes; capture authenticated-complete; post-capture PASS against the prepared baseline.
* **Success criteria:** every computer step passes without manual commands; diagnostic bundle not needed.
* **Stop conditions:** any lab FAIL (it blocks automatically); more than one card detected; Windows offers to format a disk (press Cancel and stop).
* **Tooling:** done (this PR). Optional addition before the session: a capture-script v4 that also reads `/proc/bootdev` and `/proc/zoneinfo`; that is a new script version and needs registration and review.

## 2. V7 offline part — board photographs

* **Question:** board revision; candidate UART3 pads; DRAM and PMIC part markings.
* **Existing evidence:** DT and AFI say the console is UART3 on pad set 0 (P-CONSOLE). The "UART over TF2" lead in [serial-console.md](../docs/serial-console.md) concerns **UART5** on the SD0/TF2 pins, so a TF2 breakout would most likely **not** carry the boot console (inference).
* **Why offline is insufficient:** no trustworthy public board photos for the original RG35XX revision of this unit were found.
* **Equipment:** phone camera, small screwdriver, ESD care.
* **Effort / risk:** low; reversible; opening the case needs explicit approval.
* **Success:** sharp, labelled photos of both sides; silkscreen readable.
* **Stop:** any resistance from cables or clips; any doubt about reassembly.
* **Tooling:** none needed; a photo checklist can be added to the lab later.

## 3. Early serial capture

* **Question:** what the loader and U-Boot print on the real device (DRAM training, AFI, boot branch).
* **Existing evidence:** PR #6 predicts the exact loader console lines; PR #8 predicts `bootdev= 0x22`, `bootmode = 0`, `emmc boot`, and `slot:0, error mmc_init` when TF2 is empty (BOOT-023).
* **Why offline is insufficient:** DRAM training results and ROM behaviour are hardware state.
* **Requirements before approval:** pads identified from photos; signal voltage established; adapter chosen; a written procedure with a reviewed wiring photo; a capture tool that only listens (115200 8N1, receive only).
* **Risk:** the main physical risk of the whole project so far. Treat as a separate decision.

## What offline work should happen first

1. C-PREDRAM-PATH: re-run the DRAM-stage emulation with boot code 2 and compare with code 0.
2. Optional capture-script v4 (read-only additions above), registered and linted like v3.
3. A photo-review checklist for rank 2.
