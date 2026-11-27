# Running hardware test V3: the complete step-by-step procedure

> **Fallback procedure.** Use [the lab](V3-LAB-QUICKSTART.md) (`ATM7039S-Lab.cmd`) instead whenever possible: it automates every computer step here, finds candidate cards by geometry and available media identity (mark the spare card to distinguish identical cards), keeps progress across restarts and replaces the byte-level `card-rootfs` check, which always fails after the first boot, with the phase-aware check. If you do follow this guide, run step 5.4 with `--image` so the prepared card is compared semantically: `python tools/v3_preflight.py --boot-dir … --share-dir … --image inputs/koriki-v1.0.img`.

This guide takes you from nothing to a finished, checked V3 capture. Follow it **in order** and do **every** step, including the ones that look unnecessary. Every step says what to do, what you should see, and what to do if you see something else.

* **What V3 is:** you boot a spare microSD card with an unmodified copy of the Koriki v1.0 firmware on the original RG35XX handheld. You then run one small script that **only reads** information the running system already reports, and saves it to the card. Afterwards you check and analyse that information on a computer.
* **What V3 is not:** the capture does not change persistent settings or flash the handheld. Koriki itself writes to the spare card and may change runtime clock policy. Rollback is strongly supported, not yet proven on hardware.
* **Permission:** the device owner must have approved this session **before** you start. This guide is not that approval.
* **Time needed:** about 1–2 hours, most of it downloading and writing the card.

Shorter references: [device/README.md](README.md) (operator guide) and [the readiness report](../reports/v3-hardware-validation-readiness.md) (why each step exists).

---

## Golden rules (read them twice)

1. **Never use the owner's own cards.** The owner's working GarlicOS card and the old failing factory card must not be inserted into the computer or the handheld at any point in this procedure. Put them in a separate drawer before you start.
2. **Use one new or spare microSD card, 8 GB or larger.** Everything on it will be erased. The firmware image is 4.30 GB, so a "4 GB" card is too small.
3. **The second card slot (TF2) stays empty the whole time.**
4. **No charging cable** in the handheld while it is switched on for this test.
5. **Do not change any setting** on the handheld: CPU, overclocking, display, Wi-Fi, anything.
6. **Run the capture exactly once.**
7. **After the capture, the card goes straight to the computer.** Do not switch the handheld on with this card again until the results are copied off.
8. **If anything looks different from this guide, stop**, write down what you saw, and ask. Do not improvise.
9. **Never click "Format"** when a computer offers to format the card, and never let it "scan and fix" the card.

---

## Part 0: What you need

Tick each item before you start.

| ✓ | Item | Notes |
|---|---|---|
| ☐ | The original Anbernic RG35XX (2022–2023, Actions ATM7039S chip) | Not the RG35XX Plus, H, SP, 2024 or any other model. |
| ☐ | Its battery charged to at least half | Charge it **before** the session, then unplug the cable. |
| ☐ | One spare microSD card, 8 GB or larger | Brand-name, known to work. Everything on it will be erased. |
| ☐ | A microSD card reader for the computer | Built-in slot or USB reader. |
| ☐ | A computer: Windows 10/11, macOS or Linux | Allow about **14 GB (13 GiB) of free local disk space** for firmware and verification snapshots, internet access, and permission to install programs. |
| ☐ | About 1 GB of download allowance | The firmware download is 935 MB. |
| ☐ | Pen and paper, or a text file, for notes | You will write down times and what you saw (template in Appendix B). |

The owner's two cards are **not** on this list on purpose.

---

## Part 1: Set up the computer (one time only)

### 1.1 Install Python 3.11 (recommended; CI-tested minor version)

* **Windows:** download a Python 3.11 installer from https://www.python.org/downloads/. Run it, **tick "Add python.exe to PATH"** on the first screen, then click "Install Now".
* **macOS:** download a Python 3.11 installer from https://www.python.org/downloads/ and run it.
* **Linux:** use your distribution's Python 3.11 or newer (for example `sudo apt install python3 python3-pip python3-venv` on Ubuntu 24.04).

Check it. Open a terminal: on Windows press Start, type `PowerShell`, press Enter; on macOS open Applications → Utilities → Terminal; on Linux open any terminal. Then type:

```
python --version
```

On macOS and Linux type `python3 --version` instead. Prefer `Python 3.11.x`; newer versions are not the CI baseline and may lack compatible pinned dependency wheels. **If the number is lower than 3.11, or the command is not found, stop and fix the installation first.**

In the rest of this guide, commands are written with `python`. **On macOS and Linux, type `python3` wherever this guide says `python`.**

### 1.2 Install balenaEtcher (the program that writes the card)

Download it from https://etcher.balena.io/ and install it. (Linux users who prefer `dd` may use it, but Etcher is recommended because it verifies the write.)

### 1.3 Get the project files

The files you need are in the GitHub repository **CigThePig/ATM7039S**.

* Until PR #7 is merged, they are on the branch **`ccr-55174f02-sd1ct4`**: https://github.com/CigThePig/ATM7039S/tree/ccr-55174f02-sd1ct4
* After PR #7 is merged, use the **`main`** branch: https://github.com/CigThePig/ATM7039S

To download them:

1. Open the link above in a web browser.
2. Click the green **"Code"** button, then **"Download ZIP"**.
3. Unzip the downloaded file into a folder you can find again, for example your Documents folder. You get a folder such as `ATM7039S-ccr-55174f02-sd1ct4` (or `ATM7039S-main`).
4. **In this guide, that folder is called the project folder.**

Use the ZIP download, especially on Windows. Downloading single files through the browser can rename them or change their line endings, and the capture script must stay byte-for-byte identical.

Inside the project folder you will use:

| Path | What it is |
|---|---|
| `device/capture.sh` | **The capture script.** This is the only file you copy onto the card. |
| `tools/acquire_firmware.py` | Downloads and checks the firmware image. |
| `tools/v3_preflight.py` | Checks the image, the script and the prepared card. |
| `tools/runtime_capture.py` | Checks and analyses the capture afterwards. |

### 1.4 Open a terminal in the project folder

* **Windows:** open the project folder in File Explorer, click the address bar, type `powershell` and press Enter.
* **macOS:** open Terminal, type `cd ` (with a space after it), drag the project folder onto the Terminal window, and press Enter.
* **Linux:** open a terminal and `cd` into the project folder.

Check that you are in the right place:

```
python tools/v3_preflight.py --help
```

You should see a help text that starts with `usage: v3_preflight.py`. If you see "No such file", you are not in the project folder; repeat 1.4.

**Every command from here on is typed in this terminal, in the project folder, except the elevated terminal explicitly required for raw-card reads.**

Create a new private local results folder outside the project and cloud sync now. Replace `RESULTS` in every command with its actual path, keeping quotes. Do not put results on the SD card.

### 1.5 Install the helper libraries

```
python -m pip install -r requirements-dev.txt -r requirements-firmware.txt
```

On Windows, if installation reports Access is denied, use `python -m pip install --user -r requirements-dev.txt -r requirements-firmware.txt` in the normal terminal. If Python reports a UnicodeDecodeError, run `$env:PYTHONUTF8 = '1'` and retry. Do not upgrade pip merely for this test.

Wait until it finishes. The last line should say `Successfully installed …`, or that the requirements are already satisfied. Warnings about pip versions can be ignored. **A red line containing `ERROR` is not OK: stop and ask.**

---

## Part 2: Download and check the firmware

### 2.1 Download the Koriki v1.0 image

```
python tools/acquire_firmware.py koriki-v1.0-release inputs --expand
```

* This creates a folder `inputs` in the project folder. It downloads `koriki-v1.0.img.gz` (935,244,267 bytes) and unpacks it to `koriki-v1.0.img` (4,303,355,904 bytes).
* It takes a few minutes and shows nothing while it works. **Wait.**
* When it is done it prints exactly: `Verified koriki-v1.0-release`
* If it prints anything with `mismatch`, or an error: delete the `inputs` folder and run the command again once. If it fails twice, stop and ask.

### 2.2 Check the image, the firmware components and the script

```
python tools/v3_preflight.py --image inputs/koriki-v1.0.img --archive inputs/koriki-v1.0.img.gz --json "RESULTS/preflight-image.json"
```

It takes about 10–30 seconds. The **last line must be exactly**:

```
0 FAIL, 0 WARN. No FAIL. Resolve any WARN, then follow device/README.md.
```

Above it you should see checks all starting with `PASS`: the script checks, the archive, the image, the components from `2100mAh-gpu.dtb` to `uImage`, `sfvd`, `rootfs-files` and `busybox-applets`.

* **Any `FAIL` or unresolved `WARN`: stop. Do not continue.** Copy the whole output into your notes and ask.
* A `FAIL` on the `sfvd` line is especially important. It means the loader would rewrite part of the card on every boot. That image must not be used, and the tool will not repair it.

---

## Part 3: Write the spare card

### 3.1 Make sure only the spare card can be chosen

1. **Unplug every USB stick, external drive and memory card** from the computer.
2. Check again that the owner's two cards are in the separate drawer.
3. Insert **only the spare card** into the card reader.

### 3.2 Write the image with balenaEtcher

1. Start balenaEtcher.
2. **"Flash from file"** → choose `inputs/koriki-v1.0.img` in the project folder. Choose the `.img` file, not the `.gz` file.
3. **"Select target"**: exactly one drive should be listed, with the size of your spare card (an 8 GB card shows as about 7.9 GB, a 16 GB card as about 15.9 GB).
   * If more than one drive is listed, or the size is not your card's: **cancel, unplug everything else, start again.**
   * Never tick "Show hidden" or select a drive marked as a system drive.
4. Click **"Flash!"**. Enter your computer password if asked.
5. Wait for **"Flash Complete!"**. Etcher verifies the write automatically. If it reports a verification failure, use a different card and start Part 3 again.

**Linux with `dd` instead (experienced users only):** run `lsblk -o NAME,SIZE,MODEL,TRAN,RM` before and after inserting the card. The new removable entry, for example `sdX`, is the card. Then run `sudo dd if=inputs/koriki-v1.0.img of=/dev/sdX bs=4M conv=fsync status=progress`. Get `of=` wrong and you erase another disk.

### 3.3 What the computer may say afterwards (important)

After writing, the computer may show pop-ups about the card:

* **Windows:** "You need to format the disk in drive X: before you can use it" → click **Cancel**. One partition is a Linux swap area that Windows cannot read; that is normal. "Do you want to scan and fix?" → choose **Continue without scanning** (or close the dialog).
* **macOS:** "The disk you inserted was not readable by this computer" → click **Ignore**.
* **Never click "Format", "Initialize", "Scan" or "Repair".**

Keep the card inserted until the raw check in 3.4 passes. To eject afterwards: Windows: right-click the drive → **Eject**; macOS: drag it to the Bin / click ⏏; Linux: use your file manager's eject button. Remove the card only after 3.4.

---

### 3.4 Mandatory raw boot-region verification (before the first boot)

Check the actual card's loader and U-Boot hashes and SFVD marker independently of the computer image. If Etcher already ejected the card, unplug and reinsert it, dismissing any format/repair prompts. No raw dump is saved.

**Windows:** find the spare card's boot partition (containing `uImage` and `KERNEL.DTB`) in File Explorer and note its letter. Open PowerShell as administrator and navigate to the project folder with `Set-Location "YOUR PROJECT FOLDER"`. If the partition has no letter or you cannot identify it, stop and ask; do not initialize or format anything.

```
python tools/v3_preflight.py --windows-boot-letter E --json "RESULTS/preflight-raw-before-first-boot.json"
```

Replace E with the actual boot partition letter. The helper resolves the disk via Windows Storage cmdlets, rejects system/boot disks, non-USB/SD/MMC disks and unexpected partition layouts, and opens the physical disk read-only. Access denied or an unsupported reader means stop and ask, not disable safeguards.

**Linux/macOS:** identify the newly inserted whole card (not a partition) with `lsblk -o NAME,SIZE,MODEL,TRAN,RM` or `diskutil list`. Confirm its identity and size. Use the read-only helper with the actual device (macOS example: /dev/rdiskN); use your Python environment with sufficient read permission.

```
python3 tools/v3_preflight.py --card-device /dev/sdX --json "RESULTS/preflight-raw-before-first-boot.json"
```

All three `card-raw:` checks (early-region.bin, u-boot.uimage, sfvd) must PASS with 0 FAIL and 0 WARN. Image SKIP is expected because Part 2 checked it already. If any check fails or is missing, **do not boot**. Eject safely, then return to the normal terminal.

---

## Part 4: First boot (lets the firmware finish preparing the card)

1. Make sure the handheld is **switched off**, the **charging cable is unplugged**, and **both card slots are empty**.
2. Find the two card slots. They are labelled **TF1** and **TF2**. Insert the spare card into **TF1**. Leave TF2 empty.
   * If you cannot find the TF1/TF2 labels, or you are not sure which slot is TF1, **stop and ask**. Do not guess.
3. Switch the handheld on with its power button.
4. The first boot is slower. You will see a screen titled **"Resizing Partition"** that says **"Do not switch off your device!"**, with a list of steps (Syncing disk data, Checking disk table, … Formatting partition as FAT32 …). **Do not touch anything. Wait** until the menu (SimpleMenu) appears. This can take a few minutes.
5. When the menu appears, **switch the handheld off normally** with Volume Up + Power together, the documented shutdown shortcut in the [exact Koriki v1.0 release notes](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0). A short Power press suspends/resumes; do not use it. This shortcut is documented, not yet observed on this device. Wait until the screen and power indicator are off, then another 10 seconds. If shutdown cannot be confirmed, stop and seek advice. A long Power hold is an emergency fallback only, may interrupt writes, and must be recorded; do not proceed to capture without review.
6. Write in your notes: date, time, "first boot completed", and anything unusual.
7. Remove the card from TF1.

**If the resize screen shows an error, or the handheld reboots repeatedly:** switch off, note what you saw, and stop. The card may be faulty; you could start again from Part 3 with a different spare card.

---

## Part 5: Put the capture script on the card

### 5.1 Open the card on the computer

Insert the card into the computer (dismiss any Format/Scan pop-up as in 3.3). You should now see **two** readable drives from the card:

| Drive | How to recognise it | What you do with it |
|---|---|---|
| **Boot partition** (about 3 GB) | Contains `uImage`, `KERNEL.DTB`, `RAMDISK.IMG`, `uEnv.txt`, `batocera-boot.conf` and folders `BOOT`, `TOOLS` | **Do not change anything here.** You only read from it, in 5.4 and Part 9. |
| **SHARE** | Named `SHARE`; contains folders such as `roms`, `system`, `bios` | You copy the script here. |

Write down where each drive appears:

* Windows: drive letters, for example boot = `E:` and SHARE = `F:`.
* macOS: usually `/Volumes/<name>` and `/Volumes/SHARE`. Run `ls /Volumes` in Terminal to see the names.
* Linux: usually `/media/<your-user>/<name>` and `/media/<your-user>/SHARE`.

**In the commands below, replace `BOOTDRIVE` and `SHAREDRIVE` with what you wrote down.**

If you only see the boot partition and no `SHARE`, the first boot did not finish. Go back to Part 4 once. If `SHARE` is still missing, stop and ask.

### 5.2 Create the `roms/ports` folder

On `SHARE` there is a folder `roms`. Inside `roms`, create a folder named exactly **`ports`** (lower case) if it does not already exist. The result must be `SHARE/roms/ports/`.

### 5.3 Copy the script, under the exact name `ATM7039S-capture.sh`

Use the terminal (still in the project folder). Copying in a terminal avoids hidden extensions, renamed files and macOS extra files. Type the line for your system, with your drive in place of `SHAREDRIVE`.

* **Windows (PowerShell):** `Copy-Item device\capture.sh F:\roms\ports\ATM7039S-capture.sh`, with `F:` replaced by your SHARE drive letter.
* **macOS:** `cp -X device/capture.sh /Volumes/SHARE/roms/ports/ATM7039S-capture.sh`. The `-X` stops macOS from creating a hidden `._ATM7039S-capture.sh` file, which would show up as a second, broken menu entry.
* **Linux:** `cp device/capture.sh /media/<your-user>/SHARE/roms/ports/ATM7039S-capture.sh`

Rules for this file:

* **Do not open it in any editor**, not even to look. Saving it, even unchanged, can change its line endings, and the check will fail.
* The name must be exactly `ATM7039S-capture.sh`: no spaces, no extra `.txt`. The handheld's launcher runs the file by its name, and spaces break it.
* `roms/ports` must contain **only this one** `.sh` file.

### 5.4 Check the prepared card

```
python tools/v3_preflight.py --boot-dir BOOTDRIVE --share-dir SHAREDRIVE --phase prepared --image inputs/koriki-v1.0.img --json "RESULTS/preflight-prepared.json"
```

Examples:

* Windows: `python tools/v3_preflight.py --boot-dir E:\ --share-dir F:\ --phase prepared --image inputs/koriki-v1.0.img --json "RESULTS/preflight-prepared.json"`
* macOS: `python3 tools/v3_preflight.py --boot-dir "/Volumes/NO NAME" --share-dir /Volumes/SHARE --phase prepared --image inputs/koriki-v1.0.img --json "RESULTS/preflight-prepared.json"`. Put quotes around a name that contains spaces.

The last line must say **`0 FAIL, 0 WARN`**. You should see `PASS` for:

* `card-boot:` and each of the 8 boot files;
* `card-rootfs` (the firmware's 2.4 GB root filesystem file is checked, so this step takes one to a few minutes);
* `card-overclocking` (`overclocking unset`);
* `card-boot-extra`;
* `card-first-boot`;
* `card-script` (`ATM7039S-capture.sh is capture script version 3`);
* `card-earlier-captures`;
* `card-free-space`.

What to do if it reports a problem:

| Message | What to do |
|---|---|
| `card-boot:… DIFFERS` or `missing` | Stop; preserve the card and report the mismatch. |
| `card-rootfs FAIL` | Do not boot or reflash automatically. After the first boot the container legitimately changes (FW-021); `v3_preflight.py --image …` compares it semantically with the first-boot rules. A FAIL there means an **unexplained** change: keep the card as it is and send the report (`python tools/v3_rootfs_review.py --phase prepared --image …` writes it to `lab-data/rootfs-review/`). |
| `card-overclocking FAIL` | Do not edit the file by hand. Start again from Part 3. |
| `card-first-boot WARN` | The first boot did not finish. Repeat Part 4. |
| `card-script FAIL` | The copied file is not the registered script. Delete it, then repeat 5.3 exactly. |
| `card-script-name FAIL` | Wrong file name. Delete the file and repeat 5.3. |
| `card-macos-files WARN` | In Terminal: `dot_clean -m /Volumes/SHARE/roms/ports`, then run 5.4 again. |
| `card-boot-extra WARN` | Files were added to the boot partition. Write down their names and ask. |

Before proceeding, save the checked prepared filesystem manifest: `python tools/v3_rootfs_review.py --phase prepared --image inputs/koriki-v1.0.img --card BOOTDRIVE/boot/BATOCERA` (replace BOOTDRIVE with the mounted boot partition). Only a PASS publishes `lab-data/rootfs-review/card-prepared.json`; preserve that file for Part 11. Do not repeat this prepared review on the card after capture.

### 5.5 Mandatory repeat of the raw-card check

Repeat Part 3.4 on the prepared card, confirming its current boot letter/device. Save as `preflight-raw-prepared.json`. All three raw checks must PASS with 0 FAIL and 0 WARN. A mismatch means stop, not repair.

### 5.6 Eject

Eject both drives of the card properly (see the ejection instructions in 3.3), then remove the card.

---

## Part 6: Before switching on (final checklist)

Read each line aloud and tick it.

| ✓ | Check |
|---|---|
| ☐ | The owner has approved this session (date and scope written in your notes). |
| ☐ | The handheld is off. |
| ☐ | The charging cable is **unplugged** from the handheld. |
| ☐ | **TF2 is empty.** |
| ☐ | The prepared spare card is in **TF1**. |
| ☐ | The owner's two cards are in the drawer, not near the handheld. |
| ☐ | Nobody has changed any setting on the handheld since Part 4. |
| ☐ | You have your notes ready and know the current time. |

---

## Part 7: Run the capture (once)

1. Switch the handheld on. **Write down the time.**
2. Wait for SimpleMenu to appear. Do not open anything yet.
3. In SimpleMenu, switch to the section group called **"apps and games"**. Use SimpleMenu's normal way of changing section groups; the button for this has not been checked offline. Do not open any other app or setting while you look for it. If you cannot find the group, **stop** (use Volume Up + Power to shut down) and ask.
4. In "apps and games", open the list **GAMES**.
5. Find the entry **ATM7039S-capture**.
   * **If it is not there: stop.** Switch off normally. Do not try any other way of starting it (no file managers, terminals, ADB or other apps). Write down what the GAMES list shows.
   * If you see two similar entries, for example one starting with `._`, stop and ask. That is a leftover macOS file (see 5.3 and 5.4).
6. Select **ATM7039S-capture** and launch it **once**, the same way you would launch a game. **Write down the time.**
7. **No progress screen is expected.** Static launcher analysis predicts that the menu disappears, the screen may stay dark or unchanged, and the menu comes back when the script exits. Under a minute is an estimate, not a measured hardware result.
8. **Do not press any button while you wait. Wait at least 3 minutes** before deciding that something is wrong.
9. When the menu is back, write down the time and "menu returned".

**If something unexpected happens:**

| You see | Do this |
|---|---|
| The menu comes back immediately, within 1–2 seconds | Do **not** launch it again. Switch off normally (Part 8). On the computer, check for an `atm-capture-…` folder (Part 9). Write down what happened. |
| Nothing comes back after 5 minutes | Write down the time and exactly what is on screen. Try the documented Volume Up + Power shutdown shortcut. If unresponsive, a long power-button hold is an emergency fallback that can interrupt writes. Only remove the card once power is off; record any forced shutdown. Take the card to the computer (Part 9). **Do not retry.** |
| The handheld restarts by itself | Let it reach the menu, **do not launch anything**, switch off normally (Volume Up + Power). Write it down. Go to Part 9. |
| Anything else unusual (error text, strange screen) | Photograph or write down the exact text. Then follow the line above that fits best. |

**Things you must not do during the test:** open other apps or games, open settings, connect Wi-Fi or USB, plug in the charger, use sleep or suspend, insert anything into TF2, change CPU or display settings, or run the capture a second time "to be sure".

---

## Part 8: Switch off

1. Switch off normally with **Volume Up + Power** as in Part 4. Do not use sleep or suspend. If normal shutdown cannot be confirmed, stop and seek advice; a long power-button hold is an emergency fallback only. Even after the script flushes its files, Koriki can have pending writes. Record forced shutdown and treat the capture as potentially incomplete.
2. Wait 10 seconds after the screen and power indicator are off.
3. Remove the card from TF1.
4. **Do not switch the handheld on again with this card.** On every boot, Koriki runs an automatic repair of the SHARE partition, which could damage or delete an unfinished capture.

---

## Part 9: Copy the results to the computer

1. Use the private results folder created in Part 1 (outside the project and cloud sync).
2. Insert the card into the computer (dismiss any Format/Scan pop-up as in 3.3).
3. Open `SHARE/roms/ports/`. You should see:
   * `ATM7039S-capture.sh` (the script);
   * **one new folder** named like `atm-capture-20231112T101500Z-1234-0`, the date and time as the handheld's clock saw it, then two numbers. The date may be wrong if the handheld's clock is not set; that is normal.
4. **Copy (do not move) the whole `atm-capture-…` folder** into your private results folder.
5. **Do not open, edit, rename or delete anything inside the copied folder.** Opening a text file in an editor and saving it would break the checks.
6. If there is **no** `atm-capture-…` folder, write that down and stop. If there are **several**, copy all of them and write that down.

Keep the card in the computer for Part 11.

---

## Part 10: Check and analyse the capture

In the terminal, in the project folder, type the line below with these three replacements:

* `RESULTS` → your private results folder;
* `atm-capture-…` → the exact folder name;
* `BOOTDRIVE` → the card's boot partition.

```
python tools/runtime_capture.py RESULTS/atm-capture-... RESULTS/summary.json --report RESULTS/summary.md --reference-dtb BOOTDRIVE/KERNEL.DTB
```

Windows example (one line):

```
python tools\runtime_capture.py "C:\Users\me\Documents\RG35XX-V3\atm-capture-20231112T101500Z-1234-0" "C:\Users\me\Documents\RG35XX-V3\summary.json" --report "C:\Users\me\Documents\RG35XX-V3\summary.md" --reference-dtb E:\KERNEL.DTB
```

The command prints a short summary. Look at the line `"state":`.

| `state` | Meaning | What to do |
|---|---|---|
| `authenticated-complete` | Everything was collected and nothing was altered. | Continue with Part 11. |
| `authenticated-partial` | Nothing was altered, but some important items could not be collected. They are listed under `essential_not_ok`. | Continue; mention the list when you hand over the results. |
| `quarantined` | The capture failed an integrity check and **cannot be used as evidence**. The reasons are under `errors`. | Write down the errors. Do **not** run the capture again on your own; ask first. |

You may also see `"admissible_as_evidence": true`, which is what you want, and a list of `predictions` with short outcome names. You do not need to interpret them; the analysis is done later. Open `summary.md` to read a human-friendly version.

---

## Part 11: Re-check the card

With the card still in the computer:

```
python tools/v3_preflight.py --boot-dir BOOTDRIVE --share-dir SHAREDRIVE --phase post-capture --baseline lab-data/rootfs-review/card-prepared.json --json "RESULTS/preflight-after.json"
```

* **Expected now:** one `WARN` on `card-earlier-captures`, because the new capture folder is on the card. That is fine.
* **Any `FAIL` or unexpected `WARN` must be reported**, including rootfs and boot configuration mismatches.
* Repeat Part 3.4 after copying the capture off, using `preflight-raw-after.json`. All three raw checks must still PASS. Report any failure or missing check; do not repair or boot again.

Then eject the card. Keep it unchanged and switched off until the results have been reviewed. Do not reuse it yet.

---

## Part 12: Privacy, and handing over the results

**Private: never share or upload.** Keep these only in your private results folder:

* the `atm-capture-…` folder (it contains the handheld's serial number);
* Any raw card dump made separately (the new helper does not create one).

**Shareable:** these are redacted, with serial numbers, card IDs and network addresses removed. Read them once before sharing anyway.

* `summary.json`
* `summary.md`

Hand over:

1. `summary.json` and `summary.md`;
2. the six saved preflight JSON files (image, raw before first boot, prepared, raw prepared, after, raw after). Review paths and identifiers before sharing; include any error output and note missing files;
3. your notes (Appendix B), including every time you wrote down and anything that differed from this guide;
4. the board revision **only if it is already known**. Otherwise write `unknown`. **Do not open the handheld to find out.**

The maintainers then record the observation in the repository (`evidence/observations.json`). You do not need to do that yourself.

---

## Appendix A: Quick troubleshooting index

| Problem | Where |
|---|---|
| Python too old or not found | 1.1 |
| `No such file` when running a tool | 1.4: you are not in the project folder |
| Download fails or prints `mismatch` | 2.1 |
| Any `FAIL` in the image check | 2.2: stop |
| Etcher shows more than one drive | 3.1 |
| Computer offers to format or scan the card | 3.3: Cancel, never format |
| Resize screen errors or keeps rebooting | Part 4, last paragraph |
| No SHARE drive | 5.1 |
| Card check fails | table in 5.4 |
| No ATM7039S-capture entry | Part 7, step 5 |
| Menu does not come back | table in Part 7 |
| `quarantined` | Part 10 |

## Appendix B: Notes template (copy into a text file and fill in)

```
V3 session notes
Approved by (role) / date / scope:
Person running the test:
Computer OS:
Spare card brand / size:
Project files from: branch ______ downloaded on ______

2.2 image check result (last line):
Part 4 first boot: start time ____  menu appeared ____  switched off ____ (normal shortcut / emergency forced shutdown)
Anything unusual on first boot:
5.4 card check result (last line):
3.4 raw before first boot result:
5.5 raw prepared result:
Part 11 raw after result:

Part 6 checklist all ticked? yes/no
Part 7: power on ____  launched ____  menu returned ____
What the screen did while waiting:
Anything unusual:
Part 8: switched off ____ (normal shortcut / emergency forced shutdown)
Part 9: capture folder name(s):
Part 10: state = ____________  errors/essential_not_ok:
Part 11 card re-check result:
Board revision (only if already known, else "unknown"):
Deviations from the guide (anything at all):
```

## Appendix C: What the capture reads and why it is safe

The script reads a fixed list of status files that the running Linux kernel already provides (`/proc` and `/sys`), plus two small settings files on the boot partition. It runs two harmless commands (`uname -a` and `dmesg`). It writes only one new folder next to itself on the card.

It never writes to the system, never opens hardware devices, never mounts anything, never changes CPU, clock, power, display or battery settings, and does not read the memory card's own serial number. The full list is in [device/README.md](README.md). The safety review is in [the readiness report](../reports/v3-hardware-validation-readiness.md), section 7.

## Appendix D: What this test cannot tell you

The capture shows what the boot chain handed to Linux. It cannot show:

* the very early start-up messages from the handheld's chip and bootloader;
* the memory chip's setup and test;
* the physical amount of memory fitted;
* whether there is storage that Linux does not see.

Those need a different, separately approved test. A missing item in the results means "not collected", never "broken".

## Windows operator helper

From the project folder, use `powershell -NoProfile -File tools/v3_operator.ps1 -Action Setup`, `-Action Prepared`, or `-Action Analyse -CaptureFolder 'C:\path\to\private\atm-capture-...'`, or `-Action Postflight`. This helper detects labelled mounted partitions on the same disk, saves local outputs, and never formats, flashes, boots or copies the capture script to a card. It does not replace mandatory raw checks or the owner's checklist. The rootfs diagnostic stages verified local snapshots, requires about 5 GB extra space, saves progress in a gitignored cache, and can be restarted with the same command. Its private reports are in `lab-data/rootfs-review/`; it is not an automatic preflight override. See [OBS-001 report](../reports/v3-first-hardware-capture.md).
