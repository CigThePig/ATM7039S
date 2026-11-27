# tools/v3lab — the hardware-testing lab (developer notes)

Operator instructions: [device/V3-LAB-QUICKSTART.md](../../device/V3-LAB-QUICKSTART.md). This page is for people changing the lab.

## Design

* **Architecture:** Python standard-library HTTP server on `127.0.0.1`, one HTML page (`ui.html`), one background worker thread. No web framework, no GUI toolkit (Tkinter is not always installed and is hard to test in CI). The CLI (`python -m v3lab status|run|confirm|bundle|selftest`) drives the same controller for headless use.
* **Launch:** `ATM7039S-Lab.cmd` / `start-lab.sh` → `tools/lab_launch.py` (stdlib only) → project-local `.venv-lab` from `requirements-lab.txt` → `python -X utf8 -m v3lab`. No administrator rights; tested Python 3.11–3.13 (3.15 broke `dissect.cstruct` in CI).
* **Safety boundary:** the lab never writes to a card except one file, `SHARE/roms/ports/ATM7039S-capture.sh`, after a button press, verified by hash. It never flashes, formats, repairs or assigns drive letters. The only elevated operation is a read-only 4 MiB raw read on Windows (`elevate.py`, one UAC prompt per raw check, separate process).
* **Physical steps** are never inferred: they complete only when the operator ticks every checklist line (`session.py`).

| Module | Role |
|---|---|
| `jobs.py` | progress (percent/ETA only with a known total), pause/resume/cancel at checkpoints, quiet/fast throttle, low priority |
| `store.py` | atomic writes, single-instance lock, verified copies (publish after read-back hash; source-change detection) |
| `download.py` | HTTP Range resume, sidecar identity for partial files, hash-before-publish, bounded gzip expansion |
| `disks.py` | Windows Storage cmdlets / `lsblk` inventory; candidate identified by disk + pinned partition geometry; salted native SD CID when available, capacity compatibility otherwise; operator identifies identical USB-reader cards |
| `rootfs.py` | semantic ext4 manifest, health gate, SQLite-checkpointed scan, phase-aware comparison under `evidence/firmware/koriki-v1.0-first-boot.json` |
| `session.py` | persistent step state machine, operator confirmations, deviations |
| `steps.py` | the computer side of each V3 step |
| `app.py`, `ui.html` | controller, HTTP API (token + Host check), page |
| `diagnostics.py` | minimal structured, best-effort scrubbed diagnostic bundle; review before sharing |
| `elevate.py` | the one administrator read |

## Changing the first-boot policy

Rules in `koriki-v1.0-first-boot.json` must cite the pinned script or binary (path and SHA-256 inside the verified container) that makes the change, say whether an observation saw it, and constrain the result (type, mode, owner, size). Never add a rule because a card showed a change; find the firmware code that makes it first. Never whitelist a container hash.

## Tests

`tests/test_lab.py` (state machine, downloads, simulated Windows storage including V3's drive-letter failures, real ext4 fixtures, a simulated V3 session, HTTP security, bundles), `tests/test_v3_rootfs_review.py`. Fixtures: `tests/fixtures/make_lab_rootfs.py` regenerates the ext4 images (Linux, root, e2fsprogs). Simulated storage is **not** a Windows hardware integration test.

## Review hardening

The lab verifies raw loader, U-Boot and SFVD at all three checkpoints. It binds their digests to the prepared session (the entire raw head is not compared because resizing can change the partition table). Before installing the capture script it rechecks the prepared container byte hash and boot files, rediscovers the mounts, and refuses unexpected launchers. A USB reader may not expose a media-specific identity; a human must identify the marked spare, and matching capacity/content is not proof of physical identity. Never swap cards during a check. Old format-1 sessions cannot resume under format 2; their files are preserved. Going back before a possible capture is refused, and earlier pre-capture rewinds invalidate downstream baselines and preserve history. Review diagnostic ZIPs before sharing.
