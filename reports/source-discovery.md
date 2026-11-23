# Source discovery log and exclusions

Session date: 2026-11-22. All repository identities and examined file hashes are in the catalogue. This log describes actual searches and inspections, not exhaustive coverage of the internet.

## Search and inspection performed

| Query / route | Outcome | Evidence treatment |
|---|---|---|
| Exact ATM7039S + datasheet / S500 / RG35XX kernel | Manufacturer 2015 filing found, plus product/distributor claims | Manufacturer row retained; no distributor PDF claim accepted as a manual |
| Supplied 2013 SEC filing | Historical ATM7039 data, apparent 60-bit wording | Separate variant and contradiction record |
| Exact S500 datasheet / user manual / Cubieboard6 | 329-page manufacturer-branded S500 PDF mirror retrieved | Hashed and catalogued as related-chip document; not target TRM; not redistributed |
| Supplied macromorgan gist | Full DTS obtained with gist revision metadata | All nodes/properties extracted; no extraction provenance asserted |
| rg35xx-cfw GitHub organization | Enumerated repositories and branches | Relevant rg35xx kernel and rg35xx-koriki-wip Batocera branch checked out, not just default master |
| s500_kernel | Kernel version, board DTS/defconfig, SMP/memory and selected PowerVR paths inspected | Pinned source observations; no cross build/boot claim |
| u-boot_s500 | Build/source pin, AFI and MMC definitions | Source availability distinguished from separate early loader |
| Batocera board/package recipes | Disk offsets, kernel build, DTB, GPU package | Recipe intent distinguished from actual release bytes |
| Published 2100mAh GPU DTB and historical GPIO module | Decoded DTB; read module metadata; hashes recorded | Two components, not a whole firmware analysis |
| Tinyhack + stock SDL demo | Boot/application report followed; input handling inspected | Reported behavior versus reproduced static source distinguished |
| KNULLI current wiki + historical release search | Current unsupported notice alongside older WIP claims | Temporal contradiction retained; original and H700 pages separated |
| Upstream Linux Owl | Pinned v6.12 DTS, CMU/pinctrl/DMA/I2C/MMC/UART/timer/power-domain/GPU scope | Reproducible baseline; not exhaustive latest-kernel audit |
| SGX544 open driver research | reMESA and migrated SGX544 history found and pinned | Early research distinguished from working target acceleration |
| ATM7039S + SDK / Kaiboer | Historic TV-box lead found in secondary coverage | Lead only; no acquired SDK/firmware or electrical claim derived |

## Provenance limits

The gist's single revision dates to December 2022; its content resembles a decompiled tree, but no original image hash or documented extraction was supplied there. The later battery/GPU DTB has nine changed nodes and extensive matching properties; this is evidence of close software ancestry, not two independent hardware measurements.

The Koriki default repository contains mixed platform material; files named for other handhelds and an unrelated Wi-Fi log were not used to establish ATM7039S hardware facts. Source availability in the vendor kernel is heterogeneous. S500 source/master and rg35xx branches must not be interchanged without pinning.

## Not yet completed

No Wayback snapshot acquisition, exhaustive mailing-list history, non-English SDK translation, OEM tablet/TV-box image acquisition or authenticated full ATM7039S TRM retrieval was completed. A search-engine hit, PDF-looking distributor URL or forum assertion was never promoted to a verified hardware claim. Historic mirrors and multilingual sources remain explicit continuation tasks.
