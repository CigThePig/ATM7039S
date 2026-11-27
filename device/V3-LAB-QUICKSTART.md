# V3 with the lab — quick start

You do the hands-on parts. The computer does all the checking and tells you what to do next.

**Before you start:** the working GarlicOS card and the failing factory card stay in a drawer. You need the spare microSD card (at least 8 GB), a card reader, the handheld, and [balenaEtcher](https://etcher.balena.io/) installed. You need [Python 3.12](https://www.python.org/downloads/) installed once (tick "Add python.exe to PATH").

## Start

Double-click **`ATM7039S-Lab.cmd`** in the project folder. (Linux/macOS: `./start-lab.sh`.)

The first start sets itself up (about a minute). A page opens in your web browser. Keep the small black window open while you work.

## Then

Read the big title on the page and do that one thing. That's it.

* Grey "The computer does this" steps start by themselves. You can keep using the computer; press **Pause** or **Stop** if you need it to be quiet. Stopping never loses finished work.
* Yellow "You do this" steps show a short checklist. Tick each line when it is true, then press **Done**.
* If something is wrong, a red box says what happened, whether anything was lost, whether it is safe, and what to do next.

You can close everything and come back another day: double-click the file again and it continues where you stopped. If you plug the card into a different USB port or Windows gives it a different letter, that's fine.

## The physical steps, so you know what's coming

1. Put the spare card in the computer's card reader (only that card).
2. Write it with balenaEtcher (the lab shows which file and which disk). If Windows asks to format anything: **Cancel**.
3. Put the card back in the computer for a check.
4. Card into **TF1** of the handheld, **TF2 empty**, **no charging cable**. Switch on, wait for the game menu (first time takes a few minutes), then **START > QUIT > SHUTDOWN**.
5. Card back into the computer. The lab checks it and puts the capture script on it (you press one button).
6. Card into TF1 again, same rules. Switch on, open **PORTS**, start **ATM7039S-capture** once, wait until it says it finished, then **START > QUIT > SHUTDOWN**.
7. Card back into the computer. The lab copies and checks the results.

Afterwards the page tells you which file is safe to send (`summary.md`). Keep the `private` folder private.

## If you are stuck

Press **More options → Make a diagnostic bundle** and send that zip file. It contains no card data or personal details.

The detailed manual procedure (only if the lab cannot be used) is [V3-STEP-BY-STEP.md](V3-STEP-BY-STEP.md).
