# Source discovery continuation

## Accepted and examined

| Resource | Status and value | Scope / rights |
|---|---|---|
| Koriki v1.0 full image | Acquired, hash-identified, disk/boot/rootfs components analyzed | Original RG35XX CFW; no redistribution rights inferred |
| Koriki v0.9.1 V6C boot fix | Acquired; kernel equality and DTB difference documented | Two components plus README; no universal V6C behavior claim |
| Existing 329-page S500 v1.4 manual | Reacquired exact baseline hash; GPIO/UART gates/reset and divisor sections inspected | Related chip only; manual not redistributed |
| Additional pinned U-Boot files | AFI layout and generic boot/FDT paths inspected; six source provenance additions including packaging script | File-specific upstream licenses; analysis only |
| Additional pinned PowerVR bridge files | Envelope, transport and dispatch code inspected; five hashed paths added | Linux DDK tree, not sibling Android assumptions |
| GNU Arm 8.3-2019.03 | Acquired and executed as a host cross toolchain; archive hash recorded | No target binary execution; not exact historical compiler |

Full image and bootfix URLs are pinned in acquisitions.json. The firmware catalogue is a separate reproducible database; the old two-component artifacts.json remains a **historical standalone-component dataset**, not a count of all material now examined.

## Rejected, blocked or not established

| Lead | Disposition | Next action |
|---|---|---|
| Ariat-Tech ATM7039S.pdf | Search/opened result is a distributor quote/stock sheet, not a silicon technical manual | Do not cite as an ATM7039S register manual |
| Linaro 4.9-2017.01 archive URL | Redirected to HTML contact page; 60,125 bytes; SHA-256 `3f471f65975fa24e06db6cc80dd1d081fcbe53d7df9ea690116f58cf52d656bb` | Seek authenticated archive/mirror and verify archive format/hash |
| Original Anbernic stock download | Manufacturer download page located, package not acquired | Resolve original-model link and lawful firmware-only package; do not substitute H700 images |
| GarlicOS 1.4.9 Patreon release | Primary release page located; attachments not acquired | Acquire original-model assets before stock/Garlic comparison |
| GarlicOS rg35xxplus bootloader repository | Rejected for target use: explicitly Plus/H/SP/RG28XX | Retain model boundary |
| MinUI original-RG35XX install instructions | Located; launcher installed on stock firmware | Prioritize underlying stock components; this does not reveal ROM/DDR internals |
| Chinese ATM7039S TV-box descriptions | Leads only, secondary reporting | Establish exact device/silicon identity and original firmware before extracting claims |
| Kaiboer-related firmware | Not acquired or authenticated | Still open; no device equivalence claim |
| Newer upstream, historical Owl patch archaeology | Not systematically examined in this phase | Retain Linux v6.12 baseline; investigate separately |
| reMESA | Existing credited research retained | No new independent renderer or shader-ISA reconstruction claimed |

Primary discovery links: [Anbernic original-model page](https://win.anbernic.com/download_data/271.html), [GarlicOS original release](https://www.patreon.com/posts/76561333), [MinUI original-model instructions](https://github.com/shauninman/MinUI/blob/main/skeleton/BASE/README.txt), [rejected distributor sheet](https://www.ariat-tech.com/datasheets/2538619255/ATM7039S.pdf). These leads are not promoted into source findings merely because a search result exists.

The source catalogue now has 20 entries and 76 hashed source files. Search leads are separated from accepted sources so inaccessible advertisements do not inflate authenticated evidence. Broader archived SDK discovery, historical branches, electrical documentation and other-device firmware remain incomplete.
