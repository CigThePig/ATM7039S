# Validation results

Executed locally on 2026-11-22 for edition 0.2. No target hardware test ran.

| Check | Result | Meaning |
|---|---|---|
| Unit suite with optional firmware dependencies | 66 passed | Existing parsers plus acquisition/bounds/FAT/gzip/A32/provenance/binary-evidence tests |
| Canonical schema and evidence checks | Pass, zero errors | Includes new binary component hash/range links |
| Register generation `--check` | Pass | Canonical register Markdown/CSV/C candidates are current |
| Pinned source audit | 76 files / 2,244 references, zero errors | Byte hashes/sizes and exact cited source line bounds |
| Full source dataset regeneration | Pass | Curated extra provenance and ten CMU fields survive rebuild |
| Independent release DTB decoding | Zero normalized differences | Vendor DTC versus custom decoder; not target behavior |
| GNU readelf versus pyelftools | Selected module metadata and library dependencies agree | Static ELF evidence only |
| A32 reference inventory | Selected literal/branch references agree with Capstone inspection | No complete function/control-flow or physical-map proof |
| Firmware gzip/image/component hashes | Verified | Exact identity of acquired release bytes; no manufacturer signature claim |
| Kernel/U-Boot builds | Failed, logs retained | Host DTC/compiler compatibility blockers; no final boot outputs |
| HTML generation | Pass | Searchable local reference; no website deployed |

One pre-existing GPIO register alias and six shared/overlapping DT resource pairs remain as warnings. No new reset/access/width value was promoted into target register semantics. Related-chip values are labelled separately. Successful CI and static checks cannot establish silicon behavior or authorize live MMIO.

The source/build command details are in [tools](../tools/README.md), [firmware analysis](firmware-analysis.md) and [build reproduction](build-reproduction.md). CI installs pinned optional parser dependencies and exercises generated synthetic fixtures without downloading firmware or accessing hardware. The delivered PR's Actions results are checked separately; this report does not label a local pass as a remote pass.

## 2026-11-23 additions

| Check | Result | Meaning |
|---|---|---|
| Unit suite | 97 passed | Adds capture script/parser, predictions, redaction and observation-ledger tests |
| Koriki v1.0 re-acquisition | Download and expanded hashes match `acquisitions.json` | Same bytes as the original analysis |
| Manifest regeneration | Existing disk and rootfs component records reproduced exactly; nine selected files added (init scripts, SimpleMenu config, boot config) | Extends, does not alter, earlier evidence |
| Source audit, vendor kernel and U-Boot | All hashes and cited line ranges valid, including the two new MMC driver files | Other sources not re-cloned in this run |
| Capture script | Runs under dash and under BusyBox-only applets; parser reports zero integrity errors on the resulting host capture | Script portability, not target behaviour |
| Kernel build with GCC 4.9.3 | Not run | Toolchain located and hashed; execution not permitted in this session |
