# V3 with the lab — quick start

You do the hands-on parts. The computer does all the checking and tells you what to do next.

**Before you start:** the working GarlicOS card and the failing factory card stay in a drawer. Mark or label the spare card/case so you can tell identical cards apart. You need the spare microSD card (at least 8 GB), a card reader, the handheld, and [balenaEtcher](https://etcher.balena.io/) installed. You need [Python 3.12](https://www.python.org/downloads/) installed once (tick "Add python.exe to PATH").

## Start

The guided lab currently supports Windows and Linux. **macOS users:** follow the [manual V3 procedure](V3-STEP-BY-STEP.md); automated disk discovery is not implemented on macOS.

Double-click **`ATM7039S-Lab.cmd`** in the project folder. (Linux: `./start-lab.sh`.)

For a fresh lab allow about **13 GiB (14 GB) of free local space**. The lab calculates the actual additional requirement from pinned firmware sizes, reusable verified files, both card snapshots and a safety margin. It rechecks before flashing and before the capture script is installed. Do not delete an active session's files to make room.

The first start sets itself up (about a minute). A page opens in your web browser. Keep the small black window open while you work.

## Then

Read the big title on the page and do that one thing. That's it.

* Grey "The computer does this" steps start by themselves. You can keep using the computer; press **Pause** or **Stop** if you need it to be quiet. Stopping never loses finished work.
* Yellow "You do this" steps show a short checklist. Tick each line when it is true, then press **Done**.
* If something is wrong, a red box says what happened, whether anything was lost, whether it is safe, and what to do next.

If shutdown cannot be confirmed, stop and seek review; do not use a long power hold as a normal shutdown. You can close everything and come back another day: double-click the file again and it continues where you stopped (sessions from the earlier lab format must start afresh; preserve those records). If you plug the card into a different USB port or Windows gives it a different letter, that's fine.

## The physical steps, so you know what's coming

1. Put the spare card in the computer's card reader (only that card).
2. Write it with balenaEtcher (the lab shows the file and removable disk; stop unless exactly one target is present and it is your marked spare). If Windows asks to format anything: **Cancel**.
3. Put the card back in the computer for a check.
4. Card into **TF1** of the handheld, **TF2 empty**, **no charging cable**. Switch on, wait for the game menu (first time takes a few minutes), then **Volume Up + Power together; wait for the screen and power indicator to go off, then another 10 seconds**.
5. Card back into the computer. The lab checks it and puts the capture script on it (you press one button).
6. Card into TF1 again, same rules. Switch on, go to SimpleMenu **apps and games → GAMES**, start **ATM7039S-capture** once, wait until it says it finished, then **Volume Up + Power together; wait for the screen and power indicator to go off, then another 10 seconds**.
7. Card back into the computer. The lab copies and checks the results.

Afterwards the page tells you which file is safe to send (`summary.md`). Keep the `private` folder private.

## If you are stuck

Press **More options → Make a diagnostic bundle** and send that zip file. Raw captures and firmware are excluded, but error messages can contain private information. Open the ZIP and review every file before sharing.

The detailed manual procedure (only if the lab cannot be used) is [V3-STEP-BY-STEP.md](V3-STEP-BY-STEP.md).

On USB readers the software may not be able to distinguish two physically identical cards. Your label and confirmation are essential; the lab checks the prepared card's contents again before writing. A third read-only administrator prompt is expected after capture on Windows.

### Linux card access

Before you flash, the lab checks that your account can open the identified spare **whole disk** read-only. Linux may deny this even if its files are mounted. If the lab blocks you, ask your system administrator to grant read-only access to that specific device (not a partition); do not run the whole lab as root or change permissions on unrelated disks. The permission can disappear when the card is unplugged, so the raw checks also explain how to recover if access is lost. All three raw checks remain mandatory. Never flash while the lab reports a blocked target.

Use either the browser or the CLI with a given lab-data folder, not both at once. The Windows PowerShell fallback uses the same local Python environment created by its Setup action.
