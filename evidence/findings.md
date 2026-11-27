# Findings ledger

Confidence applies to the exact claim and scope. A verified source observation is not hardware validation. All findings in this edition are unvalidated on the physical target. See `findings.json` for structured records and `contradictions.json` for unresolved conflicts.

## ID-001

Actions 2015 Form 20-F separately lists ATM7039S: quad core up to 1.6 GHz, SGX544, 32-bit DDR up to 533 MHz, BGA359, 28 nm, introduced December 2014.

**Confidence:** verified · **Scope:** manufacturer-statement · **Validation:** static-inspection

Evidence:

- [sec2015 / Products and Technology / SoC product table / ATM7039S row](https://www.sec.gov/Archives/edgar/data/1342068/000114420416096913/v436680_20f.htm)

Limits: Manufacturer product claims; not a measurement of RG35XX clock, package marking or silicon revision.

## ID-002

ATM7039 and ATM7039S have separate manufacturer product entries; naming similarity does not prove register or package compatibility.

**Confidence:** verified · **Scope:** manufacturer-statement · **Validation:** static-inspection

Evidence:

- [sec2015 / SoC product table / ATM7039 and ATM7039S rows](https://www.sec.gov/Archives/edgar/data/1342068/000114420416096913/v436680_20f.htm)

Limits: ATM7039C and ATM7059A silicon equivalence remains unestablished.

## ID-003

2013 filing writes 60 bit DDR for ATM7039, whereas the later table and 2013 launch describe 64-bit DRAM.

**Confidence:** verified · **Scope:** source-contradiction · **Validation:** static-inspection

Evidence:

- [sec2013 / SoC product table / ATM7039 row](https://www.sec.gov/Archives/edgar/data/1342068/000114420414024402/v374190_20f.htm)

- [sec2015 / SoC product table](https://www.sec.gov/Archives/edgar/data/1342068/000114420416096913/v436680_20f.htm)

- [actions-launch / ATM7039 announcement](https://www.prnewswire.com/news-releases/actions-semiconductor-launches-high-performance-owl-series-chipset-225168632.html)

Limits: Preserve the apparent typo rather than correct the historical source silently. Not ATM7039S bus-width evidence.

## DT-001

The gist root declares actions,gs705a and actions,atm7059a; model is Actions GS705A board.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L6-L8)

Limits: These are source text observations, not chip identification on Ross’s device.

## DT-002

The gist and the examined 2100mAh GPU DTB both describe cpu@0 and cpu@1 as arm,cortex-a9.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L61-L78)

- [batocera / board/batocera/actions/rg35xx/2100mAh-gpu.dtb / /cpus](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/board/batocera/actions/rg35xx/2100mAh-gpu.dtb)

Limits: Neither artifact proves the physical core count or active CPU count. Public gist extraction method is not documented.

## CPU-001

The RG35XX vendor kernel configuration enables SMP and CONFIG_NR_CPUS=4.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / arch/arm/configs/rg35xx_atm7039_defconfig](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/configs/rg35xx_atm7039_defconfig#L387-L402)

Limits: Compile-time limit does not prove that four cores are active.

## CPU-002

Vendor owl_smp_init_cpus reads the SCU core count, clips it to nr_cpu_ids, and forces ncores=2 when the powersave early parameter is set; powersave defaults false. [PR #8] OBS-001 shows ncores 4 and no powersave argument on Koriki v1.0 (CPU-003).

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / arch/arm/mach-owl/platsmp-owl.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/platsmp-owl.c#L202-L248)

Limits: Explains a possible software mechanism, not proof it ran in stock or GarlicOS. Need runtime SCU/boot log and command line.

## MEM-001

Both examined RG35XX tree artifacts have /memory reg=<0 0>.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L56-L59)

- [batocera / board/batocera/actions/rg35xx/2100mAh-gpu.dtb / /memory](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/board/batocera/actions/rg35xx/2100mAh-gpu.dtb)

Limits: A placeholder cannot establish DRAM base/size or explain exactly how stock firmware patches memory.

## MEM-002

The related vendor kernel reserves physical 0..0x3fff for DDR DQS training and allocates framebuffer/kinfo/ION areas using runtime memory limits.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / arch/arm/mach-owl/common-owl.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/common-owl.c#L220-L288)

Limits: Source behaviour is known; exact runtime addresses on ATM7039S are not measured.

## MEM-003

Related S500 U-Boot obtains DDR size through an AFI structure at source address 0xB4060300, checking the AFI magic.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [uboot / board/actions/owl/owl_afi.c](https://github.com/rg35xx-cfw/u-boot_s500/blob/0a557e37a5274d40bcd357585d4bcd3b73619371/board/actions/owl/owl_afi.c#L8-L71)

- [uboot / board/actions/owl/owl.c](https://github.com/rg35xx-cfw/u-boot_s500/blob/0a557e37a5274d40bcd357585d4bcd3b73619371/board/actions/owl/owl.c#L35-L55)

Limits: Address is a source pointer in this boot environment, not a newly verified physical MMIO or ROM region.

## MAP-001

The vendor header explicitly labels itself ATM7039 Spec Version V1.10; its base+offset definitions are related-chip candidates for ATM7039S.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / arch/arm/mach-owl/include/mach/regs_map-atm7039.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/include/mach/regs_map-atm7039.h#L1-L8)

Limits: Timestamp and revision comment are unauthenticated; numerical extraction establishes source content only.

## IRQ-001

The gist describes a Cortex-A9 GIC at distributor 0xb0021000 and CPU interface 0xb0020100.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L80-L87)

Limits: GIC SPI indexes are not Linux virtual IRQs. Decode only with the correct controller binding.

## CLK-001

Vendor header and upstream S500 clock driver agree on named CMU offsets including COREPLL 0x00, DDRPLL 0x08, GPU3DCLK 0x90 and reset/gate offsets 0xa0..0xac.

**Confidence:** strongly-supported · **Scope:** cross-source-layout · **Validation:** static-inspection

Evidence:

- [vendor-kernel / arch/arm/mach-owl/include/mach/regs_map-atm7039.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/include/mach/regs_map-atm7039.h#L27-L91)

- [linux / drivers/clk/actions/owl-s500.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/clk/actions/owl-s500.c#L31-L86)

Limits: Agreement may share vendor ancestry; compatible semantics, analog limits and ATM7039S safe rates are not proven.

## MMC-001

The gist declares MMC0 at 0xb0230000, MMC1 at 0xb0234000 and MMC2 at 0xb0238000; 0 and 2 are okay, 1 disabled. [PR #8] Slot-to-controller correspondence for the observed unit: the TF1 boot card is on SD2 (0xb0238000) (BOOT-022, STOR-003); TF2 on SD0 (0xb0230000) is inferred.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L604-L643)

Limits: Slot-to-controller correspondence needs driver/runtime confirmation; card_detect_gpios uses a vendor property.

## MMC-002

Upstream S500 tree uses the same three MMC base addresses and SPI IRQ indexes 42,43,44 as the gist.

**Confidence:** strongly-supported · **Scope:** cross-source-layout · **Validation:** static-inspection

Evidence:

- [linux / arch/arm/boot/dts/actions/owl-s500.dtsi](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/arch/arm/boot/dts/actions/owl-s500.dtsi#L295-L325)

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L604-L643)

Limits: Driver reuse remains a candidate: DMA request routing, reset, voltage, delay tuning and card detection need validation.

## USB-001

The gist declares disabled legacy USB regions at 0xb0600000 and 0xb0700000 and an enabled atm7059tc-usb node at 0xb0400000 with an additional region at 0xb040cd00.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L646-L675)

Limits: Names and status are board software evidence; do not infer connector USB3 speed or host capability from the related DWC3 code.

## GPIO-001

Gist GPIO resource is 0xb01b0000/0x40; vendor header additionally names MFP controls at +0x40..0x4c, pulls at +0x60..0x68 and GPIO interrupts from +0x204.

**Confidence:** strongly-supported · **Scope:** cross-source-layout · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L540-L550)

- [vendor-kernel / arch/arm/mach-owl/include/mach/regs_map-atm7039.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/include/mach/regs_map-atm7039.h#L2077-L2149)

Limits: The resource is not an exhaustive map. Numeric GPIO IDs do not identify package balls.

## PMIC-001

The gist places an actions,atc2603c device at I2C address 0x65 under I2C1, with regulator, power, gauge, audio and RTC child functions.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L249-L455)

Limits: Not independent confirmation of the fitted PMIC, board revision, or safe register access. The I2C address is not CPU MMIO.

## LCD-001

The gist describes RGB LCD at 0xb02a0000, a 640x480p60-labelled mode, explicit timings and panel-control GPIO properties.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L1143-L1181)

Limits: The mode label and requested refresh are not measurements. Vendor pixclock units must be checked before deriving frequency.

## GPU-001

Gist GPU node uses actions,atm7039c-gpu at 0xb0300000/0x10000, SPI index 3, status disabled; published 2100mAh DTB sets okay.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [gist / rg35xx.dts](https://gist.github.com/macromorgan/0491c853fcd28dc093945220348192c0#L1201-L1207)

- [batocera / board/batocera/actions/rg35xx/2100mAh-gpu.dtb / /gpu@b0300000](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/board/batocera/actions/rg35xx/2100mAh-gpu.dtb)

Limits: Enabling a DT node does not independently demonstrate functional acceleration.

## GPU-002

Selected Linux GPU branch configures SGXCORE=544, SGX_CORE_REV=115 and MP core count 1.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/config_kernel.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/config_kernel.h#L1-L25)

- [vendor-kernel / arch/arm/configs/rg35xx_atm7039_defconfig](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/configs/rg35xx_atm7039_defconfig#L2240-L2241)

Limits: Build target, not a hardware ID read. The sibling eurasia_km subtree has a different DDK version and must not be mistaken for the selected branch.

## GPU-003

The selected eurasia_km_linux pvrversion.h identifies DDK 1.14 build 3625561; config_kernel.mk selects PVR_SYSTEM=omap.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/include4/pvrversion.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/include4/pvrversion.h#L51-L64)

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/config_kernel.mk](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/config_kernel.mk#L1-L8)

Limits: ABI compatibility with stock/Garlic userspace was not tested.

## GPU-004

The OMAP-named glue defines dynamic platform resources, taking register base and IRQ from platform APIs in the corresponding code branch.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/syslocal.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/syslocal.h#L65-L75)

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/sysconfig.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/sysconfig.c#L200-L238)

Limits: Hard-coded OMAP fallback address 0x56000000 is not an ATM7039S GPU base.

## GPU-005

The inspected upstream Linux v6.12 DRM_POWERVR targets Series 6 and later and depends on ARM64. It is not SGX544 support.

**Confidence:** verified · **Scope:** upstream-support · **Validation:** static-inspection

Evidence:

- [linux / drivers/gpu/drm/imagination/Kconfig](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/gpu/drm/imagination/Kconfig#L1-L18)

Limits: Pinned release assessment; does not establish that every experimental SGX project is unsuitable.

## GPU-006

Selected PowerVR sysconfig.c carries explicit Dual MIT/GPLv2 licensing; userspace package separately installs binaries from cubieboard6_ubuntu_gpu_drivers.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/sysconfig.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/services4/system/omap/sysconfig.c#L1-L43)

- [batocera / package/batocera/gpu/powervr-sgx544-driver/powervr-sgx544-driver.mk](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/package/batocera/gpu/powervr-sgx544-driver/powervr-sgx544-driver.mk#L1-L30)

Limits: Do not infer a license for every DDK file or redistributed userspace binary from this one notice.

## BOOT-001

Examined Batocera genimage configuration places bootloader.img at image offset 0x200200, u-boot-dtb.img at 0x300000 and first FAT partition at 0x800000.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [batocera / board/batocera/actions/rg35xx/genimage.cfg](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/board/batocera/actions/rg35xx/genimage.cfg#L43-L59)

Limits: File-image offsets, not CPU addresses or verified ROM search rules. Recipe does not prove these exact files were shipped.

## BOOT-002

The same branch builds a kernel from rg35xx-cfw/s500_kernel origin/rg35xx and requests rg35xx_atm7039 DTS; U-Boot package pins a buildable source revision.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [batocera / configs/batocera-rg35xx.board](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/configs/batocera-rg35xx.board#L60-L96)

- [batocera / package/batocera/boot/uboot-rg35xx/uboot-rg35xx.mk](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/package/batocera/boot/uboot-rg35xx/uboot-rg35xx.mk#L1-L21)

Limits: Build recipe inspected; full cross build and boot not performed. Source U-Boot build does not account for separate early bootloader.img.

## BOOT-003

Stock researcher reports FAT uImage plus ramdisk.img, Android-style /init and init.rc, loadapp.sh and dmenu launcher chain.

**Confidence:** strongly-supported · **Scope:** reported-firmware · **Validation:** static-inspection

Evidence:

- [tinyhack / Stock RG35XX boot sequence](https://tinyhack.com/2023/12/31/reverse-engineering-rg35xx-stock-firmware/)

- [stock-demo / menu.c](https://github.com/yohanes/rg35xx-stock-sdl-demo/blob/8dbe95d60558740893a57593d792e388c0932ba9/menu.c#L55-L100)

Limits: Reported sequence; demo corroborates application environment only, not independent ROM/bootloader execution.

## INPUT-001

Demo source discovers the input device by EVIOCGNAME matching gpio-keys-polled and creates a reader thread.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [stock-demo / menu.c](https://github.com/yohanes/rg35xx-stock-sdl-demo/blob/8dbe95d60558740893a57593d792e388c0932ba9/menu.c#L55-L100)

- [stock-demo / menu.c](https://github.com/yohanes/rg35xx-stock-sdl-demo/blob/8dbe95d60558740893a57593d792e388c0932ba9/menu.c#L460-L480)

Limits: Static application-source observation, not proof that every firmware uses the same event numbers.

## ART-001

Historical gpio_keys_polled.ko metadata reports GPL v2 and vermagic 3.10.37 SMP preempt mod_unload ARMv7 p2v8.

**Confidence:** verified · **Scope:** software-observation · **Validation:** static-inspection

Evidence:

- [batocera / board/batocera/actions/rg35xx/old_overlay/fsoverlay/userdata/system/modules/gpio_keys_polled.ko / .modinfo; see evidence/artifacts.json](https://github.com/rg35xx-cfw/batocera.linux/blob/961d8abcea18017e6c6275c914f81f3b3d72c760/board/batocera/actions/rg35xx/old_overlay/fsoverlay/userdata/system/modules/gpio_keys_polled.ko)

Limits: Historical bundled module; does not identify current KNULLI or the user’s Garlic kernel. Module metadata is not source/license-compliance verification.

## KNULLI-001

Current inspected KNULLI wiki marks original RG35XX unsupported while describing stock boot/kernel dependencies and an incomplete source-built alternative.

**Confidence:** verified · **Scope:** project-documentation · **Validation:** static-inspection

Evidence:

- [knulli-wiki / docs/devices/anbernic/rg35xx.md](https://github.com/knulli-cfw/knulli.org/blob/314b26f1822c8531bed8a9cea72028b229b4436e/docs/devices/anbernic/rg35xx.md#L1-L29)

Limits: Current wiki source at pinned revision; prose is internally mixed with historical feature claims.

## FAMILY-001

Pinned mainline S500 describes Cortex-A9; S700 and S900 describe Cortex-A53; these are distinct programming targets.

**Confidence:** verified · **Scope:** source-comparison · **Validation:** static-inspection

Evidence:

- [linux / arch/arm/boot/dts/actions/owl-s500.dtsi](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/arch/arm/boot/dts/actions/owl-s500.dtsi#L27-L59)

- [linux / arch/arm64/boot/dts/actions/s700.dtsi](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/arch/arm64/boot/dts/actions/s700.dtsi#L15-L65)

- [linux / arch/arm64/boot/dts/actions/s900.dtsi](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/arch/arm64/boot/dts/actions/s900.dtsi#L15-L70)

Limits: Shared Owl driver families do not establish identical clocks, resets, DMA descriptors or GPU generations.

## GAP-001

No authenticated complete ATM7039S technical reference manual or package pinout was located in the public searches performed this session.

**Confidence:** unknown · **Scope:** search-result · **Validation:** static-inspection

Evidence:

- [sec2015 / Product table, not reference manual](https://www.sec.gov/Archives/edgar/data/1342068/000114420416096913/v436680_20f.htm)

- [tinyhack / Kernel part](https://tinyhack.com/2023/12/31/reverse-engineering-rg35xx-stock-firmware/)

Limits: Search coverage is finite; absence is not proof that no public manual exists. See reports/source-discovery.md.

## MANUAL-001

Retrieved related S500 document identifies v1.4, 2015-07-17 and contains 329 PDF pages. It is not an ATM7039S manual.

**Confidence:** verified · **Scope:** source-observation · **Validation:** static-inspection

Evidence:

- [s500-pdf / title; metadata; printed pages 62–65,114–125](https://gzhls.at/blob/ldb/9/a/e/c/e8dd47a7e48102d05772a88a11c09fc5d86e.pdf)

Limits: Manufacturer-branded mirrored artifact; authenticity not cryptographically established; no target equivalence.

## GPU-007

Pinned reMESA README states SGX544 remains research without demonstrated independent submission/rendering, distinct from SGX535 work.

**Confidence:** verified · **Scope:** source-observation · **Validation:** static-inspection

Evidence:

- [remesa / README.md](https://github.com/reMESA-devgroup/reMESA/blob/845f385cd61aa17042f9426ec8306b4386005c24/README.md#L35-L45)

- [sgx544-history / README.md](https://github.com/reMESA-devgroup/SGX544-reMESA/blob/4c1e3095e73a506bfc48bd77041d35da0d1231e6/README.md#L1-L7)

Limits: Maintainer-reported status; no independent renderer testing, no ATM7039S integration shown.

## FW-001

The acquired original-RG35XX Koriki v1.0 disk image has 4,303,355,904 bytes, three MBR entries starting at LBAs 16384, 6307840 and 7356416, and a valid legacy U-Boot uImage at disk offset 0x300000.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Whole-image and gzip hashes, MBR geometry and extraction plan are in evidence/firmware. This is one CFW release, not authenticated stock/Garlic firmware or ROM media-search behavior.

## FW-002

The Koriki v1.0 U-Boot uImage declares load 0x05000000, entry 0x05000040, compression 0, and payload size 726332; both header and payload CRC32 validate.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Header declarations are not proof of actual runtime mapping or source identity. The payload starts at uImage offset 0x40; its embedded valid FDT starts at uImage offset 0xad5e0.

## BOOT-004

In the selected early-region binary, the A32 routine at offset 0x6500 clears 16 bytes at 0xb4060300, copies three AFI magic bytes there, and stores boot-mode/device, UART fields and a size result at offsets +4 through +0xc.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Function label is analyst-assigned. Effective addresses are in firmware address space; physical translation is not established. Region start is disk offset 0x200200; its 0xffe00-byte analysis boundary is not an established loader file length.

## MEM-004

The early-region helper at offset 0x9180 combines bytes +2 and +3 of its input as a little-endian 16-bit quantity and shifts it left by 20. The AFI producer calls it with 0xb4070820 and writes the result to 0xb406030c.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: This supports a MiB-to-byte size encoding. The runtime input bytes, detected capacity, producer of that parameter block, and hardware address translation are unknown; the on-disk region does not capture runtime RAM.

## BOOT-005

Koriki v1.0 U-Boot payload routines at offsets 0x4194..0x42d0 check the first three AFI bytes and read byte fields at 0xb4060304..307 and word fields at 0xb4060308/30c, matching the inspected owl_afi.h field order.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [uboot / arch/arm/include/asm/arch-owl/owl_afi.h](https://github.com/rg35xx-cfw/u-boot_s500/blob/0a557e37a5274d40bcd357585d4bcd3b73619371/arch/arm/include/asm/arch-owl/owl_afi.h#L5-L15)

- [uboot / board/actions/owl/owl_afi.c](https://github.com/rg35xx-cfw/u-boot_s500/blob/0a557e37a5274d40bcd357585d4bcd3b73619371/board/actions/owl/owl_afi.c#L12-L70)

Limits: Payload offsets exclude the 64-byte uImage header; evidence ranges include that header. Matching this small interface does not establish that the complete release bootloader was built from the pinned source.

## FW-003

Koriki v1.0 uImage declares Linux-3.10.37, load/entry 0x8000 and compression 0. A CRC-valid embedded gzip stream at file offset 0x44b4 expands to a kernel containing a Linux 3.10.37 / Linaro GCC 4.9.4 / build #75 string.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Bounded decompression, expanded hash and version-string offset are in kernel-payload.json. This is not Linux 4.9.170 and does not identify the kernel in other releases. Outer uImage compression and internal zImage compression are separate layers.

## FW-004

The V6C boot-fix archive uImage is byte-identical to the Koriki v1.0 uImage (SHA-256 1b792401ae06904c85441a07f7e3b7fe32e80aef2a85211ef529fefee461f174), while their kernel.dtb files differ.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v6c-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v0.9.1)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v6c-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v0.9.1)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Equality establishes shared kernel bytes for these acquired artifacts; it does not prove release chronology, authorship, stock origin, or behavior on any board revision.

## GPU-008

Koriki v1.0 rootfs contains an ARM ELF32 pvrsrvkm.ko declaring vermagic 3.10.37 SMP preempt mod_unload ARMv7 p2v8, depends=drm, and an actions,atm7039c-gpu OF alias. Its selected graphics libraries use filenames 1.14.3625561.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: These are module metadata and bundled-library observations, independently checked with readelf; they do not establish loaded module, renderer, silicon revision, or complete ABI compatibility. Full hashes, paths, inodes and DT_NEEDED entries are retained.

## GPU-009

The pinned Linux DDK source defines PVRSRV_BRIDGE_PACKAGE with bridge ID, structure size, input/output pointers and sizes, and kernel-services handle; the DRM build passes this package to a dispatcher that validates the process handle for non-connect commands.

**Confidence:** verified · **Scope:** related-source-observation · **Validation:** reproducible-static-analysis

Evidence:

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/services4/include/pvr_bridge.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/services4/include/pvr_bridge.h#L312-L322)

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/services4/srvkm/env/linux/pvr_bridge_k.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/services4/srvkm/env/linux/pvr_bridge_k.c#L242-L324)

- [vendor-kernel / drivers/gpu/pvr/eurasia_km_linux/config_kernel.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/gpu/pvr/eurasia_km_linux/config_kernel.h#L40-L42)

Limits: Source ABI only. Pointer width, packing, build options and complete bridge command structures must match a real userspace/module pair before use. No IOCTL was issued.

## CLK-004

Ten reviewed S500 GPIO/UART gate and reset positions agree between manual sections 3.3.3.16..19 and Linux v6.12 owl-s500.c; the ATM7039-labelled header has matching register offsets 0xa0..0xac.

**Confidence:** verified · **Scope:** related-source-observation · **Validation:** reproducible-static-analysis

Evidence:

- [linux / drivers/clk/actions/owl-s500.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/clk/actions/owl-s500.c#L187-L187)

- [linux / drivers/clk/actions/owl-s500.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/clk/actions/owl-s500.c#L331-L370)

- [linux / drivers/clk/actions/owl-s500.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/clk/actions/owl-s500.c#L547-L563)

- [vendor-kernel / arch/arm/mach-owl/include/mach/regs_map-atm7039.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/include/mach/regs_map-atm7039.h#L66-L69)

- [s500-pdf / PDF pages 91..93 / printed pages 75..77](https://gzhls.at/blob/ldb/9/a/e/c/e8dd47a7e48102d05772a88a11c09fc5d86e.pdf)

Limits: Detailed field evidence is in comparisons/cmu-fields.json. Related access/reset values remain S500-scoped; target register widths/access/reset and compatibility remain unknown. Vendor ancestry can be shared.

## CLK-005

S500 manual section 3.3.3.7 describes UART0DIV bits 8:0 and a special value 312, whereas Linux v6.12 configures its UART0 divider at shift 0 with width 8 and no custom table.

**Confidence:** verified · **Scope:** related-source-observation · **Validation:** reproducible-static-analysis

Evidence:

- [s500-pdf / PDF page 88 / printed page 72 / section 3.3.3.7](https://gzhls.at/blob/ldb/9/a/e/c/e8dd47a7e48102d05772a88a11c09fc5d86e.pdf)

- [linux / drivers/clk/actions/owl-s500.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/drivers/clk/actions/owl-s500.c#L331-L335)

Limits: Document/source discrepancy retained; no silicon behavior, target field width or safe programming value is inferred.

## BOOT-006

Koriki v1.0 U-Boot contains a default environment with bootcmd=run ramboot and console=ttyS2,115200, and format strings console=ttyS%d, boot_dev=%s and androidboot.serialno=. The pinned source owl_boot_fdt.c prepends console=ttyS<AFI uart_index> and appends boot_dev=<AFI boot device> and androidboot.serialno=<SN item> to the kernel bootargs; owl_afi.c falls back to UART index 5 when the AFI magic is absent.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [uboot / board/actions/owl/owl_boot_fdt.c](https://github.com/rg35xx-cfw/u-boot_s500/blob/0a557e37a5274d40bcd357585d4bcd3b73619371/board/actions/owl/owl_boot_fdt.c#L181-L236)

- [uboot / board/actions/owl/owl_afi.c](https://github.com/rg35xx-cfw/u-boot_s500/blob/0a557e37a5274d40bcd357585d4bcd3b73619371/board/actions/owl/owl_afi.c#L33-L40)

Limits: String presence in the release binary is consistent with the source routine but does not prove the release was built from it. The effective console index depends on the runtime AFI uart_index, which is not determined statically; the console=ttyS2 environment variable is not referenced by the listed boot commands. /proc/cmdline on a device is expected to contain the board serial number.

## UART-001

The Koriki v1.0 KERNEL.DTB enables UART0 (0xb0120000), UART3 (0xb0126000) and UART5 (0xb012a000) and disables UART1, UART2, UART4 and UART6. /chosen bootargs and uEnv.txt contain no console= argument, and /etc/inittab respawns getty on the generic 'console' device.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Enabled DT nodes are not proof of a physical connector, pad or voltage. Which UART carries the kernel console depends on the U-Boot console= fixup (BOOT-006) at runtime.

## UART-002

In the Koriki v1.0 KERNEL.DTB, mmc@b0230000 has a second pinctrl state named share_uart2_5 that selects a uart5 function on groups mfp2_19_17/mfp2_16_14 while keeping SD0 command/clock. The vendor gl520x MMC driver switches to that state only when the node has an sdio_uart_supported property; that property is absent from this DTB.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [vendor-kernel / drivers/mmc/host/gl520x_mmc.h](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/mmc/host/gl520x_mmc.h#L15-L15)

- [vendor-kernel / drivers/mmc/host/gl520x_mmc.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/mmc/host/gl520x_mmc.c#L1609-L1630)

- [vendor-kernel / drivers/mmc/host/gl520x_mmc.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/mmc/host/gl520x_mmc.c#L1700-L1703)

Limits: Suggests a vendor 'UART over SD slot' debug mode on the TF2 controller, but with this DT the Linux driver does not use it. Pin-to-contact mapping, signal voltage and whether the early loader or U-Boot use these pads are not established. No physical test is implied.

## STOR-001

Koriki v1.0 init scripts name /sys/devices/b0238000.mmc/.../emmc_boot_card/block/mmcblk0 and /sys/devices/b0230000.mmc/.../sd_card/block/mmcblk1; the ramdisk init mounts /dev/mmcblk0p1 as the boot partition. The release DTB's nand@b0210000 node has no status property, but the decompressed release kernel contains no actions,atm7059a-nand compatible string and the rootfs ships no block or NAND modules.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Paths in scripts express the release author's expectation, not a measured probe. Absence of a NAND driver in this release means Linux here cannot write NAND; it does not prove no NAND or eMMC is fitted, nor that U-Boot (which carries nand commands) never accesses one.

## FW-005

Koriki v1.0 first-boot and every-boot scripts write to the boot card and to a TF2 card: S02resize (triggered by /BOOT/autoresize) resizes partition 3 to the end of mmcblk0, retypes it 0x0c and formats it FAT32 labelled SHARE; S08populate mounts the last partition of mmcblk1 as /userdata when one exists, otherwise mmcblk0p3, then copies default content onto it; the ramdisk init writes /boot/boot/reboot each boot.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Describes shipped script text, not an observed run. A card in the TF2 slot during testing would be mounted and written to.

## FW-006

Koriki v1.0 boot scripts change runtime device state as part of normal operation: the ramdisk init sets the cpu0 governor to performance (and, when charging at boot, interactive with a 240 MHz cap and backlight off); S02overclock writes scaling_max_freq for cpu0-3 from batocera-boot.conf 'overclocking' (default 1008000 kHz, up to 1488000 for 'extreme'); S03performance sets MMC power control on and the noop scheduler; S01adb loads USB gadget modules and sets /sys/monitor/usb_port/config/idpin_debug=1. S50dropbear starts SSH unless system.ssh.enabled=0.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: These are baseline firmware behaviours, not actions of the capture tool. Whether the 1008000 kHz default matches stock limits, and whether scaling_max_freq writes for absent CPUs fail harmlessly, are unverified.

## FW-007

Koriki v1.0 /adb_uImage contains a separate kernel build: its embedded gzip stream expands to a Linux 3.10.37 / Linaro GCC 4.9-2017.01 string with build #19 dated Jun 21 2023, versus build #75 dated Jul 17 2023 in /uImage.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Version strings separate the two builds for runtime linking (adb-kernel-payload.json); they do not describe configuration differences beyond that.

## UI-001

In Koriki v1.0 the SimpleMenu 'apps and games' section group lists .sh files from /userdata/system/.simplemenu/games/ and /userdata/roms/ports/ under GAMES and from /userdata/system/.simplemenu/apps/ under APPS.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Configuration text only; launching behaviour, executable-bit handling on FAT and whether the default section group shows it were not observed. /userdata/roms/ports/ does not exist until created.

## BUILD-001

The pinned vendor kernel (81cc77b5, rg35xx_atm7039_defconfig, no patches) builds zImage, 61 modules and DTBs with Ubuntu GCC 4.9.3 (4.9.3-13ubuntu2cross1) and binutils 2.26.1 when host tools use HOSTCFLAGS='-O2 -fcommon'. The earlier compiler-gcc8.h blocker does not apply to GCC 4.9.

**Confidence:** verified · **Scope:** source-build · **Validation:** reproducible-static-analysis

Evidence:

- [ubuntu-gcc49-cross / evidence/build/kernel-gcc493.json](https://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-4.9-cross/)

- [vendor-kernel / Makefile](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/Makefile#L1-L4)

Limits: Host build only; nothing was booted. The compiler is not the Linaro GCC 4.9-2017.01 named by the release kernels, and the output is not byte-identical to any release component.

## FW-008

Kallsyms recovered from the Koriki v1.0 /uImage show a configuration different from rg35xx_atm7039_defconfig: the release has Android USB gadget functions (adb, mtp, rndis, acm, accessory, FunctionFS), EHCI, squashfs, hibernation/swsusp, gameport and Bluetooth PCM code that the defconfig build lacks; the defconfig build has xHCI, V4L2/videobuf2, ext2, USB monitor/umonitor, tablet and FocalTech touchscreen drivers that the release lacks.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [ubuntu-gcc49-cross / evidence/build/kernel-gcc493.json](https://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-4.9-cross/)

- [vendor-kernel / arch/arm/configs/rg35xx_atm7039_defconfig](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/configs/rg35xx_atm7039_defconfig#L386-L403)

Limits: Inferred from symbol presence (tools/kallsyms.py, validated against a System.map); options are not read from an embedded config, which this kernel does not contain. Built-in versus module placement is not distinguished.

## FW-009

The Koriki v1.0 /uImage contains 122 text symbols whose names occur nowhere in the pinned rg35xx branch of rg35xx-cfw/s500_kernel (the master branch also lacks the sampled ones), including owl_chipid_*, owl_jtag_init/jtag_handler, owl_force_shutdown, atc260x_poll_hard_onoff, hard_key_* , allen_* board routines, acts_verify_keybox/acts_create_cert and drm_get_rootkey/drm_get_devicekey. CPU bring-up functions owl_smp_init_cpus (152 bytes), owl_smp_prepare_cpus, scu_get_core_count, cpu_up and arm_dt_init_cpu_maps have identical sizes in the release and the source build.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [ubuntu-gcc49-cross / evidence/build/kernel-gcc493.json](https://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-4.9-cross/)

- [vendor-kernel / arch/arm/mach-owl/platsmp-owl.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/platsmp-owl.c#L202-L248)

Limits: The release kernel was built from a vendor-derived tree that is not public in the inspected repositories; the pinned source is a partial model of it. Equal function sizes support, but do not prove, identical source for the CPU routines (CPU-002). Purpose of the security-named routines was not analysed.

## GPU-010

pvrsrvkm.ko built from the pinned source with GCC 4.9.3 has the same vermagic as the Koriki v1.0 module, identical .data (0x788) and .bss (0x20d0c) sizes, .text 0x1f57c versus 0x1f6c8, and 745 of 814 common functions of identical size; the release additionally has OMAPLFBEarlySuspendHandler and OMAPLFBEarlyResumeHandler.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [ubuntu-gcc49-cross / evidence/build/kernel-gcc493.json](https://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-4.9-cross/)

Limits: Consistent with the same DDK source built under an Android early-suspend configuration; not byte identity, and no GPU execution.

## DT-003

The rg35xx_atm7039.dtb compiled from the pinned source differs from the Koriki v1.0 KERNEL.DTB in 22 nodes. The source DTB adds vdd-core-dcdc and vdd-gpu-dcdc regulator nodes under the ATC2603C and a gpuvdd-supply on the GPU, and changes the LCD pixclock, mmc@b0230000 max_clk, USB plug-detect, vbus_otg_en and wifi_bt_power_ctl properties.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [ubuntu-gcc49-cross / evidence/build/kernel-gcc493.json](https://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-4.9-cross/)

- [vendor-kernel / arch/arm/boot/dts/rg35xx_atm7039.dts](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/boot/dts/rg35xx_atm7039.dts#L1-L20)

Limits: A source-built DTB would add CPU/GPU voltage-regulator control that the release DTB does not have. It must not be booted without separate review (V4). Electrical meaning of the regulator settings is not established.

## FW-010

Of the 122 Koriki v1.0 kernel functions absent from the pinned s500_kernel source, 20 are defined in the prebuilt arch/arm/mach-owl/libcidop archive already present in public trees (whose Makefile line is commented out) and 6 occur in an older Actions ATM7051 3.4 BSP. The remaining 96 (USB stub/upgrade gadget, gadget descriptor sysfs, Bluetooth PCM audio, dwc3 overflow handling, 'allen' LED/motor/audio board code, JTAG switching, alarm and forced-shutdown code) occur in none of 15 public branches searched across rg35xx-cfw/s500_kernel, LeMaker/linux-actions, LeMaker/android-actions, xapp-le/kernel, sparky-sbc/sparky-test and ivoszbg/linux-atm7051-3.4. The release kernel's debug strings carry an 'allen--' prefix and the release U-Boot contains 'allenS500=1', absent from the public U-Boot source.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [vendor-kernel / arch/arm/mach-owl/Makefile](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/Makefile#L18-L18)

- [lemaker-linux-actions / evidence/build/vendor-tree-search.json](https://github.com/LeMaker/linux-actions)

- [xapp-le-kernel / evidence/build/vendor-tree-search.json](https://github.com/xapp-le/kernel)

- [lemaker-android-actions / evidence/build/vendor-tree-search.json](https://github.com/LeMaker/android-actions)

- [atm7051-kernel / evidence/build/vendor-tree-search.json](https://github.com/ivoszbg/linux-atm7051-3.4)

- [sparky-test / evidence/build/vendor-tree-search.json](https://github.com/sparky-sbc/sparky-test)

Limits: Not finding the product tree in these repositories does not prove it is unpublished. The 'allen' tag is a developer or vendor label of unknown identity; no attribution to a company is made. Symbol names only; behaviour was not analysed.

## BOOT-007

Revised (PR #5): the Koriki v1.0 and stock U-Boot default environment sets bootcmd=run ramboot with ramboot=bootm ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r} (kernel_addr_r=0x7fc0, ramdisk_addr_r=0x1ffffc0, fdt_addr_r=0x03800000), but that text does not describe the card boot: check_boot_flag replaces bootcmd with run mmcboot after the environment is loaded (BOOT-015), and mmcboot imports uEnv.txt and fatloads the kernel, RAM disk and DTB before bootm (BOOT-016). The original reading, that the images are already in memory before U-Boot runs and uEnv.txt is not imported, is refuted.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [miaui-gpu-rg35xx / src/kernel-rg35xx/TEST_BOOT.md: 'The pre-loader reads p1:/uImage directly (U-Boot's bootcmd is ramboot, and it does not read uEnv.txt)'](https://github.com/miaui-cfw/MiaUI-GPU-RG35XX)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.koriki-v1.0.handoff (uEnv.txt init=/init reaches /chosen bootargs)](https://archive.org/details/RG35XX_original_firmwares)

Limits: The environment text is verified; its runtime override is reproduced by emulation (BOOT-015), not observed on hardware. History: this finding was "inferred" in PR #3 with the opposite conclusion; RetroArch alpha 0.1 (C-UENV) and Koriki's init=/init are consistent with the revision. Prediction P-UENV still provides the hardware confirmation.

## FW-011

Koriki 1.0.3.1 (koriki_batocera_rg35xx_20240105) ships a different kernel build, Linux 3.10.37 ctalon@endymion Linaro GCC 4.9-2017.01 #40 dated Dec 13 2023, with KERNEL.DTB and uEnv.txt byte-identical to Koriki v1.0. Compared by kallsyms with the v1.0 build #75, 33098 of 33178 shared text functions (99.8%) have identical sizes and all 122 vendor functions absent from the public source are present in both; the differences are configuration (build #40 adds xHCI, ext2 and joydev; build #75 has EHCI, hostap, the VDE/VCE video drivers and LED triggers).

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-1031-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_batocera_rg35xx_20240105)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-1031-release / evidence/build/vendor-tree-search.json](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_batocera_rg35xx_20240105)

Limits: Symbol-level comparison; equal sizes support but do not prove identical source. Which Koriki release first shipped build #40 and how it relates to Anbernic's stock kernel are not established; 'stock-like' is the release notes' own description.

## FW-012

MiaUI-GPU-RG35XX reconstructs the RG35XX kernel as the pinned s500_kernel 81cc77b5 plus nine patches it describes as recovered from the running vendor kernel (ctalon #40, binary only). Built here with GCC 4.9.3 and its configuration, the result contains 29 of the 96 vendor functions found in no public tree (LED/motor sysfs, gadget descriptor sysfs, allen_adjust_volume, allen_led_poll, owl_force_shutdown) and none of the USB stub gadget, Bluetooth PCM, dwc3 overflow, JTAG or DRM-key functions; 88.3% of shared text functions match the release build #75 in size, versus 88.2% for the unpatched defconfig build.

**Confidence:** verified · **Scope:** source-build · **Validation:** reproducible-static-analysis

Evidence:

- [miaui-gpu-rg35xx / src/kernel-rg35xx/build.sh, patches/0001-0009, config/rg35xx-test.config](https://github.com/miaui-cfw/MiaUI-GPU-RG35XX)

- [ubuntu-gcc49-cross / evidence/build/vendor-tree-search.json](https://archive.ubuntu.com/ubuntu/pool/universe/g/gcc-4.9-cross/)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: MiaUI's patches are an independent reconstruction, not vendor source; their own notes list unported vendor code. Built with GCC 4.9.3 rather than the Linaro 4.9.4 their script names; not booted.

## FW-013

Kernel lineage across the early original-RG35XX releases: RetroArch alpha 0.1 (Linux 3.10.37 root@30d269650fcb, Buildroot GCC 7.3.0, #4, Mar 12 2023) and Batocera Lite alpha 0.2 (root@46ffd7f4c6ac, #8, Mar 14 2023) contain none of the 122 vendor functions, and every text symbol they contain occurs in the pinned public s500_kernel source. From alpha 0.3 (Mar 24 2023) every kernel is a ctalon@endymion Linaro GCC 4.9-2017.01 build from the vendor product tree: #18 (alpha 0.3), #3 (alpha 0.4-0.6; lacks only the 44 USB stub/Android gadget functions), #65 and ADB #64 (beta 0.7/dev 0.7), #1 and #64 (beta 0.8/0.8.1), then #19, #75 and #40 in Koriki; each shares at least 99.7% of text-function sizes with Koriki v1.0 #75.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_retroarch_alpha_v0.1 p1:/uImage sha256 eb75af729b64aceabda4e9322bd5b0ef8926ec01f31eb9931764c4d3e64a2964](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_batocera_lite_alpha_v0.2 p1:/uImage sha256 f473f3dc6faa2e4a0de4d634de951ba3b288d97bef0d141cb8b91b82895f1a70](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_batocera_lite_alpha_v0.3 p1:/uImage sha256 6c074434e15d8da57bef864cc375859b2b4ecadaa0db0a527b7534c92562d142](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_batocera_lite_alpha_v0.4 p1:/uImage sha256 978de42d1cac309de81e44b2b670c35795ff96f34619598759ef26f7a029de13](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_batocera_beta_v0.7 uImage sha256 8485f4103fee21f53cd3bcdde45e110364ea0e61020e37b20504c08a32abfe4f](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_batocera_beta_v0.8 uImage sha256 18a50ab04f4e7fc1bf7f20b0ec78c39c90b97f2c6e834f267c59024b40a04c51](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

Limits: Name and size comparison of recovered kallsyms; not source identity. The two public-source builds used GCC 7.3.0, so their function sizes are not comparable to the GCC 4.9 builds. Who 'ctalon' is and how the project obtained the vendor tree are not established.

## BOOT-008

Boot components across the early releases: alpha 0.1-0.3 carry a U-Boot uImage (726,396 bytes, sha256 65fd7ee676...) that already contains allenS500=1, bootcmd=run ramboot, console=ttyS%d and androidboot.serialno=; from alpha 0.4 the U-Boot is byte-identical to Koriki v1.0's (814ce6dbe7...). The raw early-loader window (0x200200-0x300000) hashes 6631626e... through alpha 0.5 and equals Koriki v1.0's 904f92f6... from the alpha 0.5 '6.0C' board-revision test build onward.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_retroarch_alpha_v0.1 raw:0x300000 u-boot.uimage sha256 65fd7ee676e890bdeacfe30fa1d21e9129627c9fd4e54003676034eeb943f11f](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_batocera_lite_alpha_v0.4 raw:0x300000 u-boot.uimage sha256 814ce6dbe7ab66a0d6678999ecbdf1ea8ba82f9d32a80ba95f3f13ebdbeff5dd](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json early_region_sha256 per release](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Even the public-source-kernel releases used vendor bootloader binaries. The early-window hash covers padding as well as loader code; the change coinciding with the 6.0C test build fits a board-revision early-loader fix but its content was not diffed.

## BUILD-002

The RetroArch alpha 0.1 kernel is reproduced from public source: s500_kernel 81cc77b5 plus the five kernel patches of rg35xx-cfw/buildroot_s500 (rg35xx branch), rg35xx_atm7039_defconfig, GCC 7.3.0 (Bootlin stable-2018.11-1, binutils 2.29.1), built in-tree at the path embedded in the release with its build user, host, number and timestamp. The decompressed Image has exactly the release size (11,764,244 bytes); 99.92% of bytes are identical, 72,177 of 72,374 kallsyms entries match by name, type and address, and only 128 bytes differ inside code (literal-pool string pointers in 94 functions). The release toolchain's 'Buildroot 2018.11-git-g8cf4a7d' string matches buildroot_s500 master 8cf4a7d.

**Confidence:** verified · **Scope:** source-build · **Validation:** reproducible-static-analysis

Evidence:

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_retroarch_alpha_v0.1 p1:/uImage sha256 eb75af729b64aceabda4e9322bd5b0ef8926ec01f31eb9931764c4d3e64a2964](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [buildroot-s500 / configs/rg35xx_atm7039_defconfig and board/rg35xx/patches/linux at 126e6a0; evidence/build/alpha01-gcc730.json](https://github.com/rg35xx-cfw/buildroot_s500)

- [bootlin-gcc73 / toolchain used; evidence/build/alpha01-gcc730.json](https://toolchains.bootlin.com/downloads/releases/toolchains/armv7-eabihf/tarballs/armv7-eabihf--glibc--stable-2018.11-1.tar.bz2)

- [vendor-kernel / Makefile](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/Makefile#L1-L4)

Limits: Not byte-identical: binutils 2.29.1 and Buildroot 2018.08 GCC patches differ from the recipe's 2.28.1 and 2018.11-git toolchain, which changes merged-string layout. Nothing was booted. This reproduces only the March 2023 public-source kernel; the vendor-tree kernels used from alpha 0.3 onward remain unreproducible.

## DT-004

The RetroArch alpha 0.1 KERNEL.DTB differs from the DTB compiled from pinned rg35xx_atm7039.dts (81cc77b5) in two properties only: model is 'Actions GS705A board' (the value before commit 81cc77b5, which changed only that line) and atc260x-power boot_cap_threshold is 0 instead of 3.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [rg35xx-cfw-releases / evidence/firmware/early-batocera.json rg35xx_retroarch_alpha_v0.1 p1:/KERNEL.DTB sha256 e56f2f49164eb93af8621ba707b5372c61a6784fbfa99c146a2130003f166682](https://github.com/rg35xx-cfw/rg35xx-cfw.github.io/releases)

- [vendor-kernel / arch/arm/boot/dts/rg35xx_atm7039.dts](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/boot/dts/rg35xx_atm7039.dts#L1-L20)

Limits: Property-level FDT comparison with the repository parser. Unlike the Koriki DTB (DT-003), this public-source-era DTB keeps the source's vdd-core/vdd-gpu DCDC regulator nodes; whether booting them is electrically safe is not established.

## FW-014

Four Anbernic stock releases for the original RG35XX (221203, 221223, 230309 and the 20231014 dual-system image) were acquired from a community archive.org mirror and pinned by SHA-256. The manufacturer download page links a Google Drive folder whose listing shows "35XX双-20231014-EN4GB.rar" (490M, 10/16/23); the mirrored RAR is 513,778,207 bytes (489.97 MiB), its single member keeps that manufacturer name, its RAR mtime is 2023-10-16, and the kernel and U-Boot uImage timestamps inside are 2023-10-14. The 230309 image bytes equal a second, independently uploaded mirror (MD5 d3053e5d0ac98b67651e3017b7082843).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-download / RG35XX download page links Drive folder 1tJOUt3hW6VwbqgsCRb96TMQz6yRA2GAn](https://win.anbernic.com/download/270.html)

- [anbernic-drive / system + 64G ROM folder: 35XX双-20231014-EN4GB.rar, 10/16/23; Drive warning page reports 490M; download refused (quota exceeded) 2026-11-24](https://drive.google.com/drive/folders/1tJOUt3hW6VwbqgsCRb96TMQz6yRA2GAn)

- [anbernic-stock-archive / evidence/firmware/acquisitions.json entries for RG35XX-20231014-EN4GB.rar, RG35XX-64GB230309EN.rar, RG35XX-EN-221223.rar, RG35XX-221203.zip](https://archive.org/details/RG35XX_original_firmwares)

- [stock-230309-independent / 35XX-64GB230309EN.IMG MD5 metadata](https://archive.org/details/anbernicrg35xxstockfirmware)

Limits: No manufacturer checksum exists and the manufacturer file itself could not be downloaded, so byte-level authenticity is not established; agreement of name, size (to Drive's rounding), dates and an independent mirror is circumstantial. The three older images are 1 GiB truncations of 64 GB card images; partitions beyond 1 GiB are absent.

## FW-015

Stock images use GPT behind a protective MBR (header and entry-array CRCs valid; backup header valid in the full 20231014 image) with four Basic-data partitions: MISC (FAT16, OEM "MAKEBOOT", 10 MiB at 0x800000), SYSTEM (ext4 "system", 512 MiB at 0x1200000), CONFIG (ext4, 1 KiB blocks) and a FAT32 ROM partition at 0x40000000. Non-zero bytes outside partitions are the GPT, a 448-sector loader at 0x200200 and a U-Boot uImage at 0x300000. Koriki v1.0 instead uses a plain MBR with the same two raw offsets.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / partition_table and raw_regions](https://archive.org/details/RG35XX_original_firmwares)

Limits: Image-file layout only; it does not show how the Boot ROM selects media or which card the owner's unit shipped with.

## BOOT-009

The stock raw loader is a container of ActBrm-terminated blocks and a PACK directory. Each block ends with "ActBrm", 0xAA 0x55 and a 32-bit word equal to the sum of the block's little-endian words (up to that word) plus 0x1234; four such blocks validate in every release. A PACK directory at loader offset 0x2000 lists bootloader.bin (414 sectors at 0, load 0xb4060000), bootloader.ini (20 sectors at sector 18, load 0xb4062400) and app.bin (200 sectors at sector 200, load 0x00001000). The stock MISC/DMENU.BIN updater writes bootloader.img to sector 4097 with count=448, matching the observed extent.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / trailers, pack](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / bootloader.img dd seek=4097 count=448](https://archive.org/details/RG35XX_original_firmwares)

Limits: The checksum rule and directory layout are recovered from data that satisfy them, not from a specification or the Boot ROM. Which blocks the ROM loads, and in what order, is not established. The 0xb4060000 load address is now declared by the image itself, which strengthens but does not prove BOOT-004's address hypothesis (no MMU/physical map was observed). PR #5: the transitions between blocks are traced in BOOT-012/013; only block 0 is entered by the ROM on the SD paths.

## BOOT-010

All executable loader content (blocks at 0x0-0x2000, the PACK directory, bootloader.bin code from 0x4c00 to 0x33c00 and app.bin) is byte-identical across stock 221203, 221223, 230309 and 20231014. Only bootloader.ini differs: 20231014 changes the DRAM record from rdodt=1, wrodt=1, drv=0xc to rdodt=2, wrodt=2, drv=0x9, and a 5 KiB high-entropy area at 0x3800-0x4bff differs in every release. The Koriki v1.0 early window (0x200200-0x300000) and U-Boot uImage are byte-identical to stock 230309.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / dram_config](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / dram_config; equals koriki-v1.0](https://archive.org/details/RG35XX_original_firmwares)

- [koriki-v1.0-release / equals stock-230309 disk bytes 0x200200..0x300000](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / equals stock-230309 U-Boot](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: The per-release 5 KiB area lies inside bootloader.ini and is best explained by app.bin's write-back of uninitialised SRAM (BOOT-019, inferred); it lies at 0xb4063800, where the loader's SPI-NAND path looks for an "SFVD" parameter backup, but no read of it on the SD path was established. Whether the ODT/drive change fixes a field problem is not documented.

## MEM-005

The producer of the 0xb4070820 parameter block (MEM-004) is the loader routine at 0xb4065ff8, which copies fields from bootloader.ini (0xb4062400): ini+0x1c DDR clock (468 MHz) to block+0, ini+0x20 capacity (256 MiB) to block+2, and ini+0x24..0x2a bus-width selector (1, printed as x16), chip selects (1), type (0x10), rcc (0x48), rdodt, wrodt and drv to block+4..+0xa; ini+0x0e/0x0f/0x10 (UART 3, pad 0, 115200) feed the AFI UART fields. Field names come from the loader's own format string "DRAM init mode%d,type%d,%dcs,x%dbus,rcc0x%x,wrodt%d,rdodt%d,drv%x,%dMHz.@180525_R".

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / ini-to-parameter-block copy](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / DRAM init printf arguments (format string at 0xb406b1f8)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / size helper used for AFI ddr_size](https://archive.org/details/RG35XX_original_firmwares)

Limits: Static dataflow. The loader also contains capacity scan/test code ("ddr_cap", "row_col", "scan", "==ddr_test %d MB ==") and a path that rewrites block+2/+3, so the AFI ddr_size may be detected rather than configured at run time. 256 MiB is configuration, not a measurement; usable Linux memory is not established.

## DDR-001

The stock loader's DRAM bring-up function (0xb40673f4, 6,752 bytes per Ghidra) programs two blocks absent from the ATM7039-labelled header and public device trees: 0xb01c0000 and 0xb01c8000. 128 of 129 static accesses fall exactly on registers of the public DesignWare uPCTL and PUBL layouts (U-Boot ddr_rk3288.h), in a standard order: SCTL/STAT, PUBL ACIOCR/DXCCR/DSGCR, ACDLLCR DLL reset, PIR, DFI update timings (4/10/8), TOGCNT1U/TOGCNT100N, TINIT=200, POWCTL then POWSTAT, MCFG, MR1/MR2, PTR0-2, DTPR0-2, DTAR, ODT/ZQ, per-lane DXGCR (bit 0 set only on lanes 2 and 3 on some paths), PIR=0x81, all uPCTL timing registers, SCFG, DFI configuration and DXGSR status reads. Before it, CMU_DDRPLL bit 8 is cleared and CMU_DEVCLKEN0 mask 0xa / CMU_DEVRST0 mask 0x5 are toggled, which the vendor clock tree names DDRPLLEN, DDRCH0/DMAC clock and DDR/DMAC reset.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / evidence/firmware/stock-ddr-sequence.json](https://archive.org/details/RG35XX_original_firmwares)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / struct rk3288_ddr_pctl and rk3288_ddr_publ](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L9-L160)

- [vendor-kernel / arch/arm/mach-owl/clocktree-atm7059.c / DDRPLLEN, DDRCH0/DMAC enable and DDR/DMAC reset bits](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/clocktree-atm7059.c#L151-L257)

Limits: Offset agreement supports, but does not prove, DesignWare IP identity; field meanings, reset values and timing derivations are unverified for ATM7039S. Computed operand values are not recovered. These registers must never be written from a running system: they control live DRAM.

## BOOT-011

From stock 230309 onward, U-Boot reads GPIO 70 (GPIO_CDAT 0xb01b0020 bit 6) once at boot: when set it records gd->flags bit 20, prints "-----s500" and appends "allenS500=1" to bootargs; otherwise it prints "-----a7039". The kernel's __setup("allenS500=") handler allen_check_cpu_type sets a flag read by allen_get_cpu_s500, whose only callers make atc260x_power_probe use charger_led2_ctl/work_led2_ctl/low_power_led2_ctl (GPIO 78/80/79) instead of the GPIO 22/18/21 properties, and atc2603c_init use earphone_detect2_gpios. Stock 221203/221223 U-Boot and kernels, the GarlicOS kernel and Koriki v1.0's kernel lack this logic.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / uboot_variant_strap (VA 0x05025e5c, 0x05021898, 0x05004670)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / allen_check_cpu_type 0xc0a20b74; consumers atc260x_power_probe 0xc0463598, atc2603c_init 0xc0a4d4a4](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / charger_led_ctl/charger_led2_ctl etc. / /i2c@b0174000/atc2603c@65/atc260x-power](https://archive.org/details/RG35XX_original_firmwares)

Limits: The strap is sampled in code; which boards pull GPIOC6 high is unknown. "s500"/"a7039" are vendor labels: they show two board variants with different LED/earphone wiring were supported from early 2023, not that the variants use different silicon. Community reports of a hardware change around February 2023 are consistent but not proven related. Koriki v1.0 boots the identical 230309 U-Boot, so it also receives allenS500=1 on strapped boards; its kernel has no allenS500 handler, and how it chooses between its *_ctl and *_ctl_new properties was not traced.

## FW-016

All four stock kernels are Linux 3.10.37 built by flower@flower-B85M-D2V with Linaro GCC 4.7.3 (2013.04): #18 (2022-12-03), #46 (2022-12-23), #17 (2023-02-25) and #42 (2023-10-14). They contain 119 of the 122 Koriki v1.0 functions absent from public source (FW-009), lacking only bta_test_init, bta_test_waiting_turn_over and owl_get_dsi_gamma_val. 230309 and 20231014 have identical function sets and sizes and differ only in the embedded-initramfs region. By exact anchor symbols, stock (and the GarlicOS kernel) additionally contain the Actions USB port monitor (umonitor_core_init, usb_hal_set_cmu_usbpll), xHCI, USB serial and CDC-ACM host drivers, ext2, PWM LEDs, Owl CPU-hotplug policy and joydev, and lack EHCI, Bluetooth (btusb, rfcomm), fbcon, squashfs, CVBS output, the VDE/VCE video engines and i2c-dev. Binder, exFAT, dwc3 and the Android composite gadget are present in both.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / kernels, comparisons](https://archive.org/details/RG35XX_original_firmwares)

- [koriki-v1.0-release / comparison stock-20231014 vs koriki-v1.0](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Symbol-level comparison from recovered kallsyms; function sizes are upper bounds. Different compilers (4.7.3 vs 4.9.4) prevent body-level stock/Koriki comparison. The stock kernel source was not found. Subsystem presence is judged from one anchor symbol each (evidence/firmware/stock-kernels.json subsystem_anchor_presence); suffix-normalised diff lists over-report differences because inlining changes helper symbols.

## FW-017

The stock 20231014 dual-system image also carries the GarlicOS boot set (ROM partition /CFW/OS/BOOT/GARLIC): its kernel is Linux 3.10.37 by blackseraph@Pandemonium, #116, 2023-04-06, built with the same Linaro GCC 4.7.3 as stock. Of 34,640 functions it shares with stock 230309, 34,597 have equal sizes and 31,458 have equal normalised bodies; it lacks only the four allen_check_cpu_type/allen_get_cpu_s500 symbols. Its RAMDISK.IMG and def_config.bin are byte-identical to stock 221203's.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / evidence/firmware/stock-kernels.json comparison garlic-in-stock-20231014 vs stock-230309](https://archive.org/details/RG35XX_original_firmwares)

Limits: Shows GarlicOS's kernel was built from essentially the stock source tree with the stock toolchain; it does not identify the GarlicOS 1.4.9 release on the owner's card or its full root filesystem.

## GPU-011

Stock firmware does not use the SGX GPU: its KERNEL.DTB marks /gpu@b0300000 "disabled", init.rc never loads pvrsrvkm.ko or dc_owl.ko, and the SYSTEM partition has no EGL/GLES/services userspace (UI uses SDL 1.2 on /dev/fb0). The bundled pvrsrvkm.ko is a different DDK from Koriki's: "SGX_DDK_Android_RSCompute sgxddk 1.12@3052601", non-DRM (depends empty), using ION import and Android native sync and importing owl_powergate_power_on/off, module_clk_enable, regulator_set_voltage and owl_mmu_import_buffer_on_dc, whereas Koriki's is "SGX_DDK_Linux_XOrg sgxddk MAIN@3625561" built on DRM with the OMAPLFB display bridge.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / modinfo, DDK string, imports (evidence/firmware/stock-platform.json gpu)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / status disabled / /gpu@b0300000](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / /init.rc insmod lines](https://archive.org/details/RG35XX_original_firmwares)

Limits: Static; a user-installed program could still load the module. The DDK 1.12 microkernel/firmware and matching userspace are absent, so the stock module documents an ABI generation, not a working stack.

## USB-002

Stock init.rc starts the Actions USB port monitor (/sys/monitor/usb_port/config/run 5, idpin_debug 1) and later in the same boot trigger forces host role ("usb3.0 force host": idpin_debug 0, run 0, usb_con_msg USB_A_IN). adbd is declared disabled and is never started by init; device mode with mass_storage,adb (VID 10d6, PID 0c02) is only configured by ramdisk scripts usbmond.sh/usbdbg.sh that init does not call. default.prop sets ro.secure=0 and ro.debuggable=1, which starts a console shell service. The monitor driver (umonitor_*) exists in the stock kernel but not in Koriki v1.0's.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / /init.rc lines recorded in evidence/firmware/stock-platform.json init_usb; /default.prop; /usbmond.sh](https://archive.org/details/RG35XX_original_firmwares)

- [tinyhack-demo-adb / ADB_ON.sh uses the same monitor and gadget controls](https://github.com/yohanes/rg35xx-stock-sdl-demo/blob/8dbe95d60558740893a57593d792e388c0932ba9/ADB_ON.sh)

- [tinyhack / reported launcher replacement to start ADB](https://tinyhack.com/2023/12/31/reverse-engineering-rg35xx-stock-firmware/)

Limits: Explains statically why ADB needs a user script on stock (consistent with Tinyhack); actual role switching, VBUS behaviour and whether the console shell is reachable over a physical UART need a device test.

## UI-002

The stock SYSTEM partition is a reused Actions Android 4.4.2 (KOT49H) build for an ATM7051H demo board: build.prop shows "Demo_7051H-user 4.4.2 KOT49H eng.songzhining.20161121.190628", ro.product.board=atm7051H_demo_q88_hd, ro.board.platform=ATM702X, model ToyCloud, USB VID 10d6. The launcher chain is init -> /loadapp.sh -> /system/dmenu/dmenu_ln -> dmenu.bin; in the 20231014 dual-system image MISC/DMENU.BIN is a boot switcher that copies CFW/OS/BOOT/STOCK or GARLIC onto MISC and also applies bootloader.img/u-boot-dtb.img updates.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / ro.build.* and ro.product.*](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / boot set switching and updater](https://archive.org/details/RG35XX_original_firmwares)

Limits: Build properties describe the reused userspace's origin, not the SoC; "ATM702X"/"7051H" are vendor platform labels.

## DT-005

Stock KERNEL.DTB (identical in 230309 and 20231014) differs from the Koriki v1.0 KERNEL.DTB in four nodes only: the root model ("Actions GS705A board" in stock), /gpu@b0300000 status (disabled in stock, okay in Koriki) and the ATC2603C audio and power nodes, where the same alternative GPIOs are named earphone_detect2_gpios/*_led2_ctl in stock and earphone_detect_gpios_new/*_ctl_new in Koriki.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / research.py tree/compare](https://archive.org/details/RG35XX_original_firmwares)

- [koriki-v1.0-release / KERNEL.DTB](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Property-level comparison; it does not show which properties each kernel consumes beyond the code paths traced in BOOT-011.

## UART-003

Every examined loader (stock 221203, 221223, 230309, 20231014 and Koriki v1.0, which equals 230309) configures UART index 3, pad 0 and 115200 baud in bootloader.ini (+0x0e, +0x0f, +0x10); the loader routine 0xb4065ff8 copies these to 0xb407082c/0xb4070830/0xb4070834, from which the AFI uart fields are written (BOOT-004). U-Boot prepends console=ttyS<AFI uart_index> (BOOT-006) and both the stock and Koriki DTBs enable serial@b0126000 (UART3). Statically, the expected kernel console is ttyS3.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / dram_config uart_index/uart_pad/uart_baudrate (all five loaders)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / copy of ini+0x0e/0x0f/0x10](https://archive.org/details/RG35XX_original_firmwares)

Limits: Static; a later loader or U-Boot path could still override the index, and U-Boot's own environment says ttyS2. The pre-registered prediction P-CONSOLE is left unchanged; a capture of /proc/cmdline remains the test. Pads and voltage for UART3 are not mapped.

## MEM-006

On the cold-boot path the stock loader does not initialise DRAM from the bootloader.ini record that MEM-005 describes. The loader entry (0xb4065424) calls 0xb40665d0 with r1=0; after the ini copy (0xb4065ff8) that caller tests the ini word at +0x2c (value 1 in all four releases) and, when non-zero, copies the second record (ini+0x4c, packed at 0xb407084c) over 0xb4070820 with the byte copy 0xb406af64 (0xb40666ac..0xb40666e4). The second record holds 468 MHz, x16 (bus_sel 1), type 0x10, ODT/drive equal to the primary record, but cs=0, rcc=0 and capacity 0. In mode 0 (wrapper 0xb40690b8) the DRAM routine forces capacity to 0x800 (2048 MiB), tries cs=2, and on a PUBL data-training error (PGSR 0x3f, code 0x1017fa11) retries with cs=1; with rcc&0xcc==0 it then probes columns and rows by writing 0x6996 at 2^(k+9)+4 / 2^(k+0x19+col)+4 and reading DRAM address 4, and computes capacity = 2^(row+col+bus+cs+3) MiB (8-bank case). On success 0xb4066280 writes the resulting block back over the in-SRAM ini primary record.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / loader entry call 0xb40665d0(r1=0)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / ini+0x2c test and 12-byte record copy](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / mode-0 wrapper 0xb40690b8](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / DRAM routine 0xb40673f4 incl. literal pools](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / parameter block write-back 0xb4066280](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / primary (+0x1c) and second (+0x4c) DRAM records; selector word +0x2c](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-ddr-timing.json (bootloader_ini, console, ini_writeback)](https://archive.org/details/RG35XX_original_firmwares)

Limits: Instruction-level result, reproduced by bounded Unicorn emulation and an independent z3 interpreter; the training outcome, the probe result and therefore cs/rcc/capacity are hardware-dependent and were supplied by explicit hypotheses, not observed. Under a single-rank x16 2 Gb (256 MiB, 10 column / 14 row bits) hypothesis the firmware's own write-back reproduces the shipped primary record byte for byte in all four releases, and no other tested geometry does; that agreement is consistent with, but does not prove, the board's DRAM geometry. The probe result also depends on the DMM address map, which is modelled only as a wrap-around hypothesis. The resume path (mode 1, 0xb40690d0/0xb4069128) is not analysed.

## DDR-002

The DDR3 timing calculations of the stock DRAM routine 0xb40673f4 are reconstructed as closed formulas of the rounded clock F = 12*floor(clock/12) and the record fields, in five clock bands (F<=400, <=533, <668, <801, >=801). At the shipped 468 MHz (identical code in all four releases): CMU_DDRPLL 0x327 (F/12 | 0x300); tRFC 164 (350 ns class), tRP=tRCD 8 (15 ns), tRAS 18 (37.5 ns), tRC 26, tRRD 5 (10 ns), tFAW 24 (50 ns), tWR 8, tRTP=tWTR 4, CL 8, CWL 6, tXP 4, tXPDLL 12, tCKE 3, tCKESR 4, tCKSRE/X 5, tRSTL 70, tREFI 3650 cycles (7.8 us); uPCTL TOGCNT1U 0xea, TOGCNT100N 0x17, MCFG 0x68029, MCFG1 0x100, TREFI 0x7004e, TZQCSI 0x7210; PUBL PTR0 0x2a5766, PTR1 0x5439210, PTR2 0x3a96da0, DTPR0 0x34b28890, DTPR1 0xa400c0, DTPR2 0x10023200, MR0 0x1140, MR2 0x248, MR1 0x6 (221203/221223/230309, wrodt 1) or 0x42 (20231014, wrodt 2), ZQ0CR1 0x4c or 0x29; DFI write latency 2, read-data enable 3; DMM+0x80 0x598. MR1 and ZQ0CR1 are the only final-pass values that differ between releases. Every write of the final pass is attributed to a firmware call site and classed as constant, ini-derived, hardware-detected or reset-dependent.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / DRAM routine 0xb40673f4](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / division helpers 0xb406ad40/0xb406ae80](https://archive.org/details/RG35XX_original_firmwares)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PIR bits](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L273-L288)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PGSR bits](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L297-L306)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PTR0-2 field shifts](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L309-L319)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / SCTL/STAT states](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L351-L368)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / MCFG fields](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L381-L399)

- [anbernic-stock-archive / evidence/firmware/stock-ddr-timing.json (final_pass, timings, symbolic, model_vs_unicorn)](https://archive.org/details/RG35XX_original_firmwares)

Limits: Three methods agree exactly: Unicorn emulation of the instructions, our z3 interpreter over Capstone decoding (8 symbolic paths covering 100-1200 MHz, no dependence on clobbered registers), and a hand-written model (tools/ddr_model.py) at every integer clock 100-1200 MHz, for four hardware hypotheses and three reset seeds. They share the oracle rules for peripheral reads, so they validate the calculation, not the hardware: training results, ZQ codes, lane status and reset values are not known, and bits kept by read-modify-write from unknown reset values are flagged, not predicted. Register names come from the public DesignWare uPCTL/PUBL layout (IP identity is DDR-001's inference); field meanings beyond the firmware's own packing are interpretations. The LPDDR branch (type&0xf != 0) is not modelled. Never write these values to a running system.

## DDR-003

Two properties of the stock DDR3 calculation follow from DDR-002. (1) Timings are computed before capacity detection while the capacity field is forced to 2048 MiB, so the per-rank density used for tRFC is 2048 (cs=1) or 1024 (cs=2) MiB and tRFC always takes the 350 ns class, although the detected die is 2 Gb (256 MiB), for which the same table would give 160 ns. (2) MR0 is built as (CL-4)<<4 | 0x1100 | tWR<<9 with tWR in cycles (8), so the value 0x1140 has the JEDEC DDR3 write-recovery field A11:A9 = 0 and bit 12 set; read with the JESD79-3 MR0 table that is CL 8, BL8, DLL reset, precharge power-down fast exit and WR code 000.

**Confidence:** inferred · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / DRAM routine 0xb40673f4 (tRFC table literals 110/160/260/350; MR0 packing)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-ddr-timing.json (timings.density_mib, tRFC_ns_selected)](https://archive.org/details/RG35XX_original_firmwares)

Limits: The values are reproduced exactly; the JEDEC reading of MR0 and the 2 Gb die size are interpretations (the latter from MEM-006's write-back agreement). Whether the PHY passes MR0 to the DRAM unchanged, and what the DRAM does with WR code 000, are not established. A longer tRFC is conservative, not an error.

## BOOT-012

Loader block 0 (loader 0x0-0x200, linked at SRAM 0xb4060000, identical in all four stock releases) chooses a boot code from MMIO 0xb01600a0 (CMU_DEVCLKEN0 in the related S500 clock tree): bit 7 set gives code 2, bit 4 set gives code 0, neither gives a test of SRAM word 0xb4060408 against the A32 word 0xeb0001d0 (equal: code 4, otherwise code 5). It stores the code at 0xb4064c00. For codes 0 and 2 it calls SRAM 0xb4060400 with r9=4, r0=0x102b (disk sector 4139 = loader offset 0x5400), r1=0x50 sectors and r2=0xb4065400, then branches to 0xb4065400, the bootloader.bin code entry. Codes 4 and 5 call routines in loader 0x400-0x1e00 and the 0x200-0x400 reader (linked for 0xb4061200; there its call to 0xb4060140 reaches the block-0 word-sum routine and compares sum+0x1234 with the ActBrm trailer). Loader 0x400-0x1e00, including 0xb4060400, is all zero in every image, so on the SD paths the read service at 0xb4060400 is provided outside the image, by the Boot ROM; r9 selects the service. Unrecoverable failures end in blx 0xffff0140 after the console line "load fail to adfu". [PR #8] On the observed device the path taken was code 2 (bit 7), not code 0: only code 2 reproduces OBS-001's command line (BOOT-022). The earlier statement that a working SD boot requires code 0 assumed TF1 is SD0; TF1 is on SD2.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / block 0 dispatch, literal pool 0x164-0x18c](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / reader linked for 0xb4061200](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / all-zero hole containing 0xb4060400](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / "load fail to adfu" then 0xffff0140 (0xb40654a0)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.loader.block0 (Unicorn runs for each bit/signature hypothesis)](https://archive.org/details/RG35XX_original_firmwares)

Limits: The MMIO value and the SRAM word are parameters of the emulation, not observations. Which bit the Boot ROM leaves set after an SD0 boot is not observed; only code 0 leads to a working SD boot (code 2 selects run emmcboot on mmc 1, codes 4/5 select NOR/NAND readers), so a booting stock card implies the bit-4 path, while the mainline S500 clock driver names bit 4 the NAND gate and bit 5 SD0 (C-DEVCLK). ROM code, its media search, retry order and checks are not in any image and are not reconstructed. The CMU bit is inferred from the reproduced chain, not read.

## BOOT-013

bootloader.bin (entry 0xb4065400) loads every later pre-Linux stage itself, through the ROM read service (r9=4: r0=sector, r1=count, r2=destination; 0xb4065b24 splits reads into 256-sector chunks). On the SD paths (codes 0 and 2) it reads disk 0x202600 (sector 4115, 8 sectors: bootloader.ini 0x0-0x1000) to 0xb4062400 (0xb4065d04); after DRAM initialisation and the AFI write (0xb40665d0, 0xb4066588) it reads disk 0x219200 (sector 4297, 248 sectors: app.bin) to DRAM 0x1000 and verifies it with the ActBrm rule over 0x1f000 bytes (0xb4065d8c, 0xb40654c8); it then reads the U-Boot uImage header from disk 0x300000 (sector 6144) to DRAM 0x300000, takes size, load and entry from it big-endian, and reads ((size+0x1ff)>>9)+1 sectors from sector 6144 to the load address 0x05000000 (0xb4065bf0, "load uboot: load address is 0x5000000, entry point is 0x5000040"). It finally executes blx 0x1000 with r0 = U-Boot entry (0x05000040). No loader stage checks the uImage magic or CRC (neither bootloader.bin nor app.bin contains the magic, the CRC-32 polynomial or its table). The boot code maps to AFI boot_dev 0->0x20 (sd0), 1/2/6/7->0x22, 3/5->0x00, 4->0x40, always with boot_mode 0 (0xb4066588).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / bootloader.bin main and ActBrm verifier](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / chunked read, load_uboot, load_ini, load_app](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / AFI writer and boot-code map](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.loader.main (Unicorn: every storage read, console line, AFI bytes and r0 at app entry)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.loader.boot_code_map](https://archive.org/details/RG35XX_original_firmwares)

Limits: Emulated with the disk image as storage (every read succeeds), the DRAM routine replaced by a success with 256 MiB (MEM-006 hypothesis), and PMIC/clock/console helpers stubbed; those helpers do not touch the load parameters. The resume path (0xb40664e4 -> 0xb40690d0, PR #6) skips the AFI write and was not traced further. Corrects the earlier dossier statement that app.bin loads and checksums U-Boot (C-APPBIN).

## BOOT-014

app.bin (DRAM 0x1000) does not load U-Boot. Its entry saves r0 (the U-Boot entry passed by bootloader.bin) at 0xb4060018, sets CPSR to 0xd3 (SVC, IRQ and FIQ masked), calls 0x8190 and, if that returns 0, jumps to the saved address. 0x8190 reads a chip identity through 0xbc3c (MMIO 0xb01b00e0 and 0xb0150000/0xb0150004); if the check fails it prints "Error: 0xca00d001, please reburn system" and never enters U-Boot. Otherwise, when the SRAM word at 0xb4062800 (bootloader.ini+0x400) is not "SFVD", 0x806c stores "SFVD" and the value 0xc582bb73 there and writes the whole SRAM bootloader.ini image back to the boot medium: for codes 0 and 2 it tail-calls its own MMC block writer 0x851c with sector 0x1013 (disk 0x202600 = loader 0x2400), 20 sectors, source 0xb4062400 (CMD24/CMD25, CMD12); codes 4 and 5 use SPI-NOR (0x7e54) and NAND (0x7f20) writers. All four stock images and Koriki v1.0 already hold "SFVD" 0xc582bb73 at ini+0x400, so no write happens on their first boot as shipped.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / entry 0x1000-0x1034](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / write-back 0x806c and its literal pool (0x1013, 0xb4062400, 20)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / main 0x8190](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / chip/eFuse check 0xbc3c](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / SFVD record](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.loader.app_entry, app_writeback, ini_sfvd](https://archive.org/details/RG35XX_original_firmwares)

Limits: Static analysis only; app.bin was not emulated (its main touches undocumented eFuse registers). The meaning of 0xb0150000 and of the accepted chip-identity range is not established. The write-back modifies the boot card whenever the SFVD record is missing, which matters for any replacement loader and for the hardware test plan. The trigger is evaluated on every boot and compares only the 4-byte magic at disk 0x202a00; the hash-verified Koriki v1.0 V3 baseline image carries it (SFVD, 0xc582bb73), so no write is expected there. Modified boot images must preserve it or be expected to change on the card; see reports/spare-card-risk.md and boot_chain.py sfvd.

## BOOT-015

In every stock U-Boot the default bootcmd=run ramboot is replaced before autoboot. init_sequence_r (20231014: 0x05089304-0x05089374) runs check_boot_flag (20231014: 0x050076c0) after initr_env. Executed with its own AFI getters, it prints "bootmode = %d" and sets bootcmd from the AFI at 0xb4060300: boot_mode 1 (PRODUCE) or a missing "AFI" magic (the getter then returns 1) gives "run ramboot" and bootdelay 0; otherwise boot_dev 0x00/0x01 gives "run nandboot", 0x22 gives "run emmcboot", and every other value, including the loader's SD value 0x20, gives "run mmcboot" with devif=mmc. Because the setenv follows initr_env, no stored environment can keep ramboot on a normal boot. ramboot (bootm of addresses already in RAM) is therefore the PRODUCE/USB-download path, not the card boot path.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / check_boot_flag](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / init_sequence_r](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / boot_mode getter](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / default environment](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.uboot.check_boot_flag, init_sequence_r, afi_getters](https://archive.org/details/RG35XX_original_firmwares)

- [uboot / common/board_r.c](https://github.com/rg35xx-cfw/u-boot_s500#L100-L124)

Limits: Emulation replaces setenv and printf with recorders; the getters and memcmp run from the image. The AFI contents are the loader-emulation result (BOOT-013), not a capture. Matches the public source except that boot_dev 0x01 also selects NAND.

## BOOT-016

The stock kernel, RAM disk and device tree are loaded by U-Boot's mmcboot script from the microSD card. mmcargs sets devpart ${mmcdev}:${bootpart} = 0:1. mmc 0 is SD0 (0xb0230000): board_mmc_init (20231014: 0x05004108) registers enabled actions,owl-mmc nodes of U-Boot's embedded DTB in order (SD0, then SD2 at 0xb0238000) with dev_index = (reg - 0xb0230000) >> 14. Partition 1 is GPT entry 1 (MISC, LBA 16384, FAT16) on stock and MBR entry 1 (FAT32) on Koriki. setbootenv fatloads uEnv.txt to scriptaddr 0x04400000 (the stock file is named uenv.txt; U-Boot's FAT lookup is case-insensitive) and imports it with env import -t, runs uenvcmd (stock: "setenv os_type linux;", which nothing reads: the string os_type is absent from the binary), tries boot.scr (absent), then mboot fatloads uImage to kernel_addr_r 0x7fc0, ramdisk.img to ramdisk_addr_r 0x1ffffc0 and kernel.dtb to fdt_addr_r 0x03800000 and runs bootm on the three addresses. [PR #8] This describes the AFI boot_dev 0x20 path. Its registration statement is incomplete: board_mmc_init registers SD2 only when boot_dev is 0x22 (BOOT-023). OBS-001's boot took the 0x22 path: emmcboot with devpart 1:1, U-Boot mmc 1 = SD2 (0xb0238000), the same FAT file sequence (BOOT-022).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / default environment (mmcboot, mmcargs, setbootenv, mboot, addresses)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / board_mmc_init](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / embedded FDT mmc nodes](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.boot_files, uboot.embedded_fdt](https://archive.org/details/RG35XX_original_firmwares)

- [uboot / fs/fat/fat.c](https://github.com/rg35xx-cfw/u-boot_s500#L896-L1081)

- [uboot / disk/part.c](https://github.com/rg35xx-cfw/u-boot_s500#L250-L290)

Limits: The hush scripts and file names are verified data; U-Boot's FAT and partition code were not emulated, so the case-insensitive match and EFI-before-DOS partition probing rest on the pinned source plus the presence of the EFI routines in the binary. If SD0 failed to initialise, SD2 would become mmc 0 (registration order). Refutes the MiaUI statement that the pre-loader reads p1:/uImage.

## BOOT-017

Linux handoff of the stock firmware, reproduced by executing U-Boot's image_setup_linux (20231014: 0x05014c50) on the shipped files: the legacy kernel uImage (load = entry = 0x8000, uncompressed type, CRC-checked because verify=yes) is used in place because 0x7fc0+0x40 = 0x8000 (XIP); the RAM disk payload stays at 0x2000000 and the DTB at 0x03800000 because initrd_high and fdt_high are 0xffffffff. image_setup_libfdt sets /chosen bootargs, writes /memory reg = <0 ram_size>, shrinks the blob and adds /memreserve/ entries for the DTB itself and for the RAM disk, and writes linux,initrd-start/end (stock 20231014: 0x2000000/0x20a3600). owl_boot_fdt_setup (0x0500456c) then rewrites bootargs as console=ttyS<AFI uart> <uEnv.txt bootargs> androidboot.dvfslevel=0x705x [allenS500=1 when gd->flags bit 20] androidboot.bootdev=sd boot_dev=sd0 [androidboot.serialno=<SN>], i.e. for stock "console=ttyS3 earlyprintk clk_ignore_unused selinux=0 loglevel=4 androidboot.dvfslevel=0x705x androidboot.bootdev=sd boot_dev=sd0". boot_jump_linux (0x050037fc) calls cleanup_before_linux (IRQ/FIQ masked, I-cache off, D-cache and MMU off after a flush; outer-cache hooks empty) and jumps to 0x8000 with r0=0, r1=0 (bi_arch_number is never written; env machid unset) and r2=0x03800000. ram_size is the AFI ddr_size when at least 8 MiB, else 0x1f000000. [PR #8] The boot_dev term follows the AFI boot_dev (0x20 -> sd0, 0x22 -> sd2); OBS-001 ran the sd2 variant with allenS500=1, reproduced byte for byte by emulation (BOOT-022). The emulated initrd placement 0x2000000-0x23a43b1 equals OBS-001's /chosen.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / image_setup_linux](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / image_setup_libfdt](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / owl_boot_fdt_setup](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / bootargs helper (mode 1 prepend, 2 append)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / boot_jump_linux](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / cleanup_before_linux](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / dram_init](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.handoff, handoff_bootargs, bootargs, memory_map, uboot.cleanup, uboot.bi_arch_number](https://archive.org/details/RG35XX_original_firmwares)

Limits: Runtime-dependent terms are conditional: ram_size follows DRAM detection (256 MiB only under the MEM-006 hypothesis), allenS500=1 follows GPIOC6 (BOOT-011), androidboot.serialno follows read_mi_item("SN"), which was replaced by a failure; charger mode (gd->flags bit 18) and PRODUCE add other terms. The LMB was modelled as one bank without reservations, which cannot change the in-place placements. Whether the 3.10 kernel takes its command line from /chosen or from a built-in CONFIG_CMDLINE was not checked. The kernel decompressor and Linux reservations after entry are outside this trace.

## BOOT-018

Stock U-Boot stores its environment redundantly on MMC device 1 at byte offsets 0x5000 and 0x25000, 0x20000 bytes each (env_relocate_spec 20231014: 0x05009a70; offset helper 0x050098e4; find_mmc_device(1)). With U-Boot's embedded DTB, mmc 1 is the SD2 controller (eMMC slot), not the microSD card. None of the four stock images and not Koriki v1.0 holds a CRC-valid environment at those offsets of the card image. On an SD-only board the default environment is therefore used, and the bootcmd override of BOOT-015 applies regardless.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / env_relocate_spec](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / offset helper](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json releases.*.uboot.env_storage](https://archive.org/details/RG35XX_original_firmwares)

Limits: Whether an eMMC is fitted on any RG35XX board, and so whether mmc 1 exists at run time, is not established; a saveenv on such hardware would write to it.

## BOOT-019

The per-release 5 KiB high-entropy area (loader 0x3800-0x4c00) is part of bootloader.ini (ini+0x1400-0x2800), a region no traced code reads on the SD path: bootloader.bin reloads only ini 0x0-0x1000, while app.bin's write-back (BOOT-014) stores 20 sectors (ini 0x0-0x2800) from SRAM. The area is therefore best explained as uninitialised SRAM contents captured when each master card was first booted. ini+0x1000-0x1400 (SRAM 0xb4063400), identical in all releases, holds A32 code that uses the same 0xb4060400 service ABI: it reads one sector to 0xb4060000 from sectors 1, 0x1001, 0x2001 and 0x3001 (2 MiB stride), verifies it with 0xb4062e58 and records a status nibble at 0xb4071f10, consistent with a fragment of the Boot ROM's SRAM-resident media search; sector 0x1001 is where the stock loader starts (4097).

**Confidence:** inferred · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / SRAM 0xb4063400 fragment](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / per-release area](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json comparison.components (ini 0x1000-0x1400 identical, ini 0x1400-0x2800 differs)](https://archive.org/details/RG35XX_original_firmwares)

Limits: Interpretation. The area could also have been written by a vendor image tool; nothing proves it is SRAM noise, and the fragment's link to the ROM is circumstantial (same service ABI, references to absent SRAM code, the 4097 candidate). No evidence that the area is a signature or encrypted payload was found, and nothing reads it on the SD path.

## BOOT-020

Across stock 221203, 221223, 230309 and 20231014 the pre-kernel boot sequence is identical in every traced step (block 0, bootloader.bin and app.bin bytes; storage reads; AFI; check_boot_flag table; default environment; uEnv.txt; handoff placements). U-Boot 221203 and 221223 differ only in the build banner; normalised function hashes match. 230309 is a rebuild from an "sdk-s500" tree that adds the GPIOC6 strap (probe 0x05025e5c called from power_init_board after "begin to check power!" when boot_mode != 1), the allenS500=1 bootargs term and an lcd_spics2_gpios property. 20231014 differs from 230309 in one instruction of the nv3052c panel init (mov r2,#0x1e0 -> movw r2,#0x1fb at 0x0501d9e4), plus its bootloader.ini DRAM ODT/drive bytes (BOOT-010). Only the allenS500 term changes what reaches Linux.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / strap probe](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / power_init_board](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json comparison; releases.*.uboot.variant_strap](https://archive.org/details/RG35XX_original_firmwares)

Limits: Normalised hashes mask branch and literal offsets; the 221223->230309 rebuild changes layout too much for one-to-one function matching, so differences there were enumerated by string set and by the traced boot steps, not by complete function pairing. Panel-register meaning of the 20231014 change is not established.

## MEM-007

The stock loader's memory test 0xb406631c(capacity_MiB), called once from 0xb4066740 after a successful mode-0 DRAM init, computes N = capacity << 18 words and (A) stores value i at byte 4*i for i = 4, 8, 16 ... < N, then verifies them in order, printing 'addr:ddr_test fail <i>, 0x<read> ' at the first mismatch; (B) stores v = 0x10 + k*0x41114 at byte 4*v (stride 0x104450) for v < N and verifies, printing 'tmp:ddr_test fail <v>, 0x<read> '; otherwise it prints '== ok=='. It uses plain 32-bit LDR/STR, no cache, DMA or controller operation, saves nothing and restores nothing. It returns printf's value and the caller ignores it: a failure changes neither the record, the AFI nor the boot path. Because the highest phase-A address (capacity/2) aliases only the never-written byte 0, and the odd-multiple stride cannot alias within 256 points, a device half the claimed size under wrap-around passes; a quarter-size device is detected in phase A.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / memory test 0xb406631c and its literal pool](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / caller: argument from record+2/+3, return value unused](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: Unicorn execution and an independent Python model agree on console text and every access in 14 synthetic RAM scenarios (wrap/open aliasing, injected read/write faults, stuck data bits, degenerate sizes) in all four releases. The RAM models are hypotheses; a modelled pass is not evidence that physical RAM passes. Whether accesses are cached depends on the Boot ROM's SCTLR state, which is unknown; the loader enables only the I-cache, after the test.

## MEM-008

Mode 1 of the stock DRAM routine is a suspend-to-RAM resume selected by PMIC state. pmu_init (0xb40699e8, PMIC type 2 fixed at its only call 0xb4066654) reads PMU_CTL3 (PMIC reg 3); with bit 4 (s2 flag) set and PMIC reg 0x14 bit 15 set it stores reg 8 | reg 0x5d << 16 as the resume vector at 0xb4070878 and sets 0xb4070874 = 1 (alarm-wake flag 0xb4070870 from reg 1). If both words are non-zero the caller 0xb40665d0 returns 2 before the ini+0x2c record swap, the DRAM init, the memory test, the write-back and the AFI write. Main then calls 0xb40664e4 -> 0xb4067094, which runs 0xb40690d0(record, 0) once on the ini primary (persisted) record: same CMU/reset/controller/PHY programming as mode 0, but no clock rounding, no forced 2048 MiB capacity (tRFC 160 ns class), PTR2 = F/10, PIR 0x3f instead of 0x7f, 8 MCMD PREA and 8 REF before PIR 0x81 training and 8 REF before GO_STATE, no rank/bus retry and no capacity probe (DCU_CFG from stored rcc/capacity). On success 0xb4066fd4 jumps to the vector (bit 31 set and alarm wake: DRAM re-enters self-refresh via 0xb4067248 and the PMIC powers off). On any failure 0xb4066eac sets a PMIC RTC alarm 3 s ahead, sets the s2 flag again and 0xb4066bf0 powers off. The loader reaches app.bin/U-Boot on this path only if the vector returns, in which case the AFI was never written.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / resume test in the DRAM caller](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / main: call 0xb40664e4 on return 2](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / pmu_init type-2 branch: s2 flag, vector, alarm flag](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / pre-wake CMU sequence](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / power-off routine](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / alarm re-arm and resume jump](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / resume dispatcher](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / mode-1 wrappers](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / mode-1 entry in 0xb40673f4](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / mode-1 PIR and MCMD bursts](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / mode-1 refresh before GO](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / probe skipped in mode 1](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: PMIC state, PUBL/uPCTL responses and the resume vector are synthetic (dram_complete.py Scenario/Pmic). The mode-1 register sequence is reproduced exactly by an independent model at every clock 100-1200 MHz in four releases. Not established: who writes PMIC regs 8/0x5d and reg 3 bit 4 (the kernel's suspend code was not analysed), the meaning of the PMIC registers beyond the loader's own strings, and whether PIR bit 5 (DRAMRST in the related RK3288 layout) pulses RESET# during resume (C-RESUME-DRAMRST), which bears on whether DRAM contents survive.

## DDR-004

Failure handling of the stock DRAM routine 0xb40673f4: ZQ0SR0 done, PGSR&7==7 and DFISTSTAT0 ready are each polled 101 times without delay (codes 0x2a00fa11, 0x9a00fa11, 0xdf00fa11); PGSR==0xf after the init PIR, PGSR after the training PIR other than 0x1f/0x3f, MCMD completion, uPCTL state transitions (0xb4067170) and CMDTSTAT are polled without bound. Every internal code whose low 24 bits are 0x00fa11 (ZQ, PHY init, DFI, probe 0xf000fa11, capacity 0xc000fa11) is printed as 'Fail: 0x...' and returned as 0x1747fa11 (0xb4068f34..0xb4068f50); only the training error 0x1017fa11 is returned unchanged. A training error (PGSR 0x3f) prints the four DXGSR0 words and, in mode 0 only, retries the whole pass with cs 2 -> 1 and bus x32 -> x16 (order (2,x32),(1,x32),(2,x16),(1,x16) when both are automatic); with no alternative left the record's cs/bus are restored and 0x1017fa11 is returned. The column probe takes code 3 when no alias appears; the row probe ends at the first alias or at exponent 31 (so its exponent-32 error 0xf000fa11 is unreachable) and otherwise leaves row code 0 when no alias is found, so a device larger than the probe range is reported as 13 rows.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / ZQ and PHY-init polls](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / init PIR, training PIR and DFI polls](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / column and row probe loops](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / failure codes, collapse, retry logic](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / uPCTL state walker](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: All PUBL/uPCTL responses are explicitly synthetic scenarios; no training, ZQ or lane-status value of a real RG35XX is known. Poll bounds are iteration counts whose duration depends on bus timing. Corrects PR #4 (C-FAILCODE, C-PROBE-NOALIAS); the readable model now mirrors the probe exactly (48 geometries, 0 mismatches against Unicorn).

## DDR-005

The stock loader's non-DDR3 branch (record type & 0xf != 0) is an LPDDR2/LPDDR3-class path: PUBL DCR 0x1000000c (DDRMD field 4, DDRMD_LPDDR2_LPDDR3 in the public RK3288 layout) instead of 0xb, PIR 0x5f (DRAMRST omitted) instead of 0x7f, MR1/MR2/MR3 instead of MR0/MR1/MR2, DSGCR 0xf1001807, its own timing tables (tRFC 90/130/210 ns classes, read latency 3..12 by clock band) and uPCTL+0x148 = 0. The exact type byte 1 selects uPCTL MCFG memory-type 3 (LPDDR2_EN in the RK3288 layout); other non-zero low nibbles select 1, which that layout does not define; PUBL+0x3fc = 1 is written only for type byte 2. The type byte's high nibble 1 (stock value 0x10) skips the idle self-refresh setup (MCFG1 |= 0x60 or 0x20 and a wait for STAT 0x15). No shipped record selects the branch.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / type test](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / LPDDR timing calculations](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / MR0 vs MR3](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / PUBL+0x3fc, DSGCR and PIR by type](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / type high nibble: idle self-refresh](https://archive.org/details/RG35XX_original_firmwares)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / DDRMD values](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L322-L328)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / MDDR_EN/LPDDR2_EN](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L383-L384)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: Recovered by emulation for four type values and four clocks in both modes, not by an independent model. Which JEDEC LPDDR generation a type value targets, and the meaning of the MR values written, are not established. Applicability of the RK3288 register names to the ATM7039S is inferred (DDR-001).

## DDR-006

Register interpretations for the stock DRAM sequence: uPCTL+0x148 (reserved in the RK3288 layout) is TREFI_MEM_DDR3, named tref_mem_ddr3 at that offset in U-Boot's RK322x uPCTL layout, consistent with the firmware writing tREFI in memory clocks (F*78/10) for DDR3 and 0 for LPDDR; PUBL PIR values decode as CLRSR, INIT|DLLSRST|DLLLOCK|ZCAL|ITMSRST|DRAMRST|DRAMINIT (0x7f), the same without DRAMINIT (0x3f) or DRAMRST (0x5f), and INIT|QSTRN (0x81); DCR 0xb is DDRMD 3 with 8 banks. The self-refresh entry 0xb4067248 (SCTL GO, SLEEP, wait STAT 0x45 = Low_power with lp_trig 4) then writes ACIOCR 0x1bfc3c18, DXCCR 0x80c, DSGCR 0xc5fc0000, sets DMM+0 bit 1 and pulses DMM+0 bit 28. uPCTL MCFG bit 3, CMU_DDRPLL bit 9, PUBL+0x3fc and the DMM registers remain without a public definition.

**Confidence:** inferred · **Scope:** release-binary · **Validation:** static-inspection

Evidence:

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/sdram_rk322x.h / uPCTL timing registers through tref_mem_ddr3 (0x148)](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/sdram_rk322x.h#L72-L107)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PIR and PGSR bits](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L272-L306)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / SCTL/STAT encodings](https://github.com/u-boot/u-boot/blob/9d67454e920b3908529c9fc642a8c911db040896/arch/arm/include/asm/arch-rockchip/ddr_rk3288.h#L350-L368)

- [anbernic-stock-archive / self-refresh entry](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / uPCTL+0x148 write](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: Names come from Rockchip register layouts of the same DesignWare IP family; register revisions differ, and nothing here is a vendor statement about the ATM7039S. Bit-level meanings of ACIOCR/DXCCR/DSGCR/ODTCR values are not decoded; no power-on reset value is claimed.

## MEM-009

The stock capacity probe measures only the column width under its column-probe DCU_CFG setting and the total decoded address width under its row-probe setting; the bank count is taken from the record (rcc bits 1:0, 0 = 8 banks). Running the firmware's probe and memory test against 180 device geometries behind three DMM address-decode hypotheses, only an in-order column -> bank -> row decode of a single-rank device with 10 column and 14 row bits reproduces the shipped primary record (with 8 banks, i.e. a 2 Gb x16 DDR3 part; a 4-bank device would also, but is not DDR3). In 128 of the 180 runs the reported capacity differs from the device's, and 73 of those also pass the memory test (for example 12-row devices reported at twice their size).

**Confidence:** inferred · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / probe and rcc handling](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: The DMM decode (field order, configured widths 8+col code / 13+row code / 8 banks, high bits ignored, absent rank floats) is a hypothesis; the result rules decode orders out rather than proving the remaining one. Bijective address hashing inside the decoded width is indistinguishable by this firmware. The board's DRAM geometry is not observed.

## MEM-010

DRAM parameters through the stock boot: the cold path selects the ini second record (ini+0x2c = 1), detects cs/rcc/capacity, and then on success and on failure alike writes the record back over the SRAM ini primary record (0xb4066280) and writes the AFI (0xb4066588) with ddr_size = capacity << 20; after a failure the capacity still holds the forced 2048 MiB (AFI 0x80000000) but main takes the ADFU exit, so U-Boot never consumes it and app.bin never persists it. On success the memory-test result is ignored and U-Boot sets gd->ram_size = ddr_size if >= 8 MiB, else 0x1f000000, and /memory = <0 ram_size>. The persisted primary record is consumed only by the resume path (and the SPI-NAND parameter restore 0xb40663f8), which programs it without checking it; a record with a wrong capacity or cs = 0 is programmed as stored. app.bin persists the SRAM ini only when SFVD is absent (BOOT-014).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / success/failure joins before write-back and AFI](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / main: return-value dispatch and ADFU exit](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / SPI-NAND parameter restore](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / capacity to bytes](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-boot-chain.json (dram_init rule, getters)](https://archive.org/details/RG35XX_original_firmwares)

Limits: Caller-level emulation with synthetic PMIC and DRAM responses. boot_chain.py --dram-scenario derives the U-Boot input from these runs; the default --ram-mib path is unchanged. The real capacity of a board is not observed.

## BOOT-021

0xb4069254, called by the DRAM caller with the ini word +0x14 (1 in all releases) before DRAM init, is not a clock setup: it reads PMIC reg 0x35 ('pmu_status'), and if bit 1 is set clears it and enters ADFU through 0xb40691a4 (copy of ROM 0xffff5200 to SRAM, jump); otherwise, only when the ini word is non-zero and the boot code is not 0 (not SD0), it bit-bangs 32 bits on GPIO registers 0xb01b0018/1c/20 and enters ADFU if they read 0x55aa55aa. The DRAM prerequisites before 0xb40673f4 are the 24 MHz timer 0 (0xb4069440, 0xb0168008), the PMIC regulator writes of pmu_init (regs 0x51, 0x39, 0x11 0xe84f, 0x12 0x68cc, 0x14 0x80ca|(adjusted ini+0x1b)<<8, 0x15 0xe8ce, 0x16 0x334b, 0x29, 0x00) and a non-zero PMIC version register 0xdc; the DDR PLL, clock gates and resets are programmed inside the DRAM routine itself.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / ADFU checks](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / ROM re-entry](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / timer init and delays](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / pmu_init type-2 regulator writes](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-dram-complete.json](https://archive.org/details/RG35XX_original_firmwares)

Limits: The electrical meaning of the PMIC writes (likely regulator settings, possibly including the DRAM supply) is not established; the PMIC detection routine was stubbed in emulation. Corrects the PR #4 description of 0xb4069254 as a pre-DRAM clock setup (C-PREDRAM-9254). PR #9 refinement (BOOT-025): the status write-back clears bits 0 and 1 (bic #3), and the GPIO test is a loopback: bit 11 of 0xb01b0020 is driven with 0x55aa55aa while bit 10 is sampled, with OUTEN/INEN restored afterwards; 0xb01b0064 bit 17 and the data bit are not restored. pmu_detect is now executed (PMIC-002).

## FW-018

The Koriki v1.0 /uImage kernel has an empty built-in command line and no embedded configuration, and exports the device tree only through procfs. In the decompressed image the 1 KiB default_command_line initialiser (kallsyms VA 0xc0a62d00, initialised from CONFIG_CMDLINE in arch/arm/kernel/atags_parse.c) is all zero; there is no IKCFG_ST marker and no ikconfig symbol, so /proc/config.gz cannot exist; proc_device_tree_init and proc_device_tree_add_node are present (CONFIG_PROC_DEVICETREE: /proc/device-tree is a real procfs directory, not a link), while of_fdt_raw_init, of_node_add and __of_attach_node_sysfs are absent (no /sys/firmware/fdt, no /sys/firmware/devicetree). log_buf_len is 131072 (128 KiB ring buffer). The pinned vendor drivers/of/fdt.c carries a command-line backport: with CMDLINE_FROM_BOOTLOADER it copies /chosen bootargs, with CMDLINE_EXTEND it appends " " + bootargs to CONFIG_CMDLINE, with CMDLINE_FORCE it ignores bootargs; the Kconfig choice is hidden when CONFIG_CMDLINE is empty, which defaults to CMDLINE_FROM_BOOTLOADER. The kernel is therefore expected to use the bootloader-written /chosen bootargs unchanged.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / default_command_line (VA 0xc0a62d00, 1024 bytes, all zero)](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / log_buf_len (VA 0xc0aaa874) = 131072](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [vendor-kernel / drivers/of/fdt.c](https://github.com/rg35xx-cfw/s500_kernel#L671-L726)

- [vendor-kernel / arch/arm/kernel/atags_parse.c](https://github.com/rg35xx-cfw/s500_kernel#L33-L33)

- [vendor-kernel / arch/arm/Kconfig](https://github.com/rg35xx-cfw/s500_kernel#L2140-L2170)

- [vendor-kernel / arch/arm/configs/rg35xx_atm7039_defconfig](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/configs/rg35xx_atm7039_defconfig#L100-L101)

Limits: Options are inferred from symbol presence and initialised data (tools/kallsyms.py), not read from a configuration. CMDLINE_FORCE with an empty string cannot be excluded statically, but would give an empty /proc/cmdline, which V3 shows directly. The vendor fdt.c semantics are read from the pinned source tree, from which the release is not built (FW-008/009).

## FW-019

The Koriki v1.0 KERNEL.DTB describes memory with root #address-cells = #size-cells = 1 and a single node named /memory (device_type "memory", reg <0 0>), has no /reserved-memory node and no /memreserve/ entries, and carries vendor heap sizes in MiB under /reserved/tiny (fb 9, kinfo 1, carveout 0, dma 32) and /reserved/normal (fb 8, kinfo 1, carveout 64, dma 128). U-Boot replaces the /memory reg and adds /memreserve/ entries for the DTB and RAM disk (BOOT-017). The kernel prints "Reserved memory %uMB" and "Memory: %luk/%luk available, %luk reserved, %luK highmem". A 3.10 procfs export shows node properties but not the /memreserve/ block.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / /memory, /reserved](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / format strings "Reserved memory %uMB" and "Memory: %luk/%luk available, %luk reserved, %luK highmem"](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Which heap set (tiny or normal) the kernel selects, and whether the carve-outs are removed from or reserved inside System RAM, were not traced, so the expected MemTotal is not predicted numerically. The memory size in the running tree comes from U-Boot, not from this file.

## FW-020

Koriki v1.0 writes to the spare card on every boot beyond FW-005: S03checkfat unmounts /dev/mmcblk0p3 if mounted and runs fsck.vfat -aw on it (automatic repair of the SHARE partition, before S08populate mounts it), and the ramdisk init mounts the boot FAT partition read-write at /boot_root and moves it to /boot without remounting it read-only, then writes /boot_root/boot/reboot. S08populate mounts the SHARE partition with no options (vfat defaults), so files on it carry mode 0755 under the default umask. S02resize is triggered by the file /boot/boot/autoresize, which it deletes; it does not edit batocera-boot.conf.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / gzip cpio member init: do_mount, mount --move /boot_root /new_root/boot](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Script text, not an observed run. A capture interrupted by power loss can leave FAT inconsistencies that fsck.vfat -a repairs on the next boot, possibly by truncating or removing the capture files, so a capture must be copied off before the device is booted again. Reading files on /boot can update their FAT access date because the mount is read-write.

## STOR-002

The Koriki v1.0 kernel names MMC cards by role rather than by host index: it contains the strings "%s,sd0 as boot card,sd0 name tsd_card", "%s,sd2 as boot card,sd2 name tsd_card", "%s,sd0 as boot card,sd2 name card_to_card" and "force sd2(emmc) host emmc_boot_card", plus the device names emmc_boot_card and sd_card. Koriki's S03performance hard-codes /sys/devices/b0238000.mmc/mmc_host/mmc0/emmc_boot_card/block/mmcblk0 and /sys/devices/b0230000.mmc/mmc_host/mmc1/sd_card/block/mmcblk1. The pinned kernel source never sets GENHD_FL_REMOVABLE for MMC disks, so /sys/block/mmcblk*/removable reads 0 for SD cards and eMMC alike; the card type attribute (SD or MMC) distinguishes them. [PR #8] The conditions for each naming string are now traced (STOR-003): names follow the controller slot and boot_dev, not the medium.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / vendor MMC boot-card naming strings](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [vendor-kernel / drivers/mmc/card/block.c](https://github.com/rg35xx-cfw/s500_kernel#L2108-L2118)

Limits: The conditions under which each naming string is printed were not traced. Script paths express the release author's expectation, not a probe. A device name such as mmcblk0 or emmc_boot_card does not by itself say whether the medium is removable. Superseded in part by STOR-003.

## UI-003

SimpleMenu in Koriki v1.0 launches a GAMES entry through invoker.dge (static ARM binary) and cmd_invoker.dge, a bash script: for an entry whose exec is "#" it sets HOME=/userdata/system and SDL_NOMOUSE=1, runs eval "$3" & on the entry's path, polls the child every 3 s with kill -0, and restarts simplemenu when it exits. The .sh file is therefore executed directly by path (needing the execute bit, which vfat defaults provide, FW-020, and a file name without spaces or shell metacharacters, because the path is evaluated), with no terminal and no on-screen output. simplemenu also contains "echo %d > /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq" and a CPU section in config.ini (normal_speed 1008000).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / strings executeCommand, invoker.dge, scaling_max_freq](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: invoker.dge was not disassembled: the argument order it passes to cmd_invoker.dge ($1 "#/", $3 the entry path) and the working directory are inferred from cmd_invoker.dge. Whether simplemenu writes scaling_max_freq for a "#" entry, and with which value, was not traced. Not observed on hardware.

## BOOT-022

OBS-001's kernel command line is reproduced byte for byte by exactly one executed boot path of the Koriki v1.0 image (stock 230309 loader and U-Boot): loader block 0 writes boot code 2 (CMU_DEVCLKEN0 bit 7 set; BOOT-012), bootloader.bin turns it into AFI boot_mode 0, boot_dev 0x22, uart 3 with the same raw reads as the code-0 path, check_boot_flag sets bootcmd "run emmcboot", emmcargs sets devpart ${emmcdev}:${bootpart} = 1:1, U-Boot device 1 is the SD2 controller 0xb0238000 (BOOT-023), and owl_boot_fdt_setup with gd flag 0x100000 (GPIOC6 strap high) produces "console=ttyS3 earlyprintk clk_ignore_unused selinux=0 init=/init   androidboot.dvfslevel=0x705x allenS500=1 androidboot.bootdev=sd boot_dev=sd2". Of the six (boot code x strap) hypotheses run by boot_chain.py boot-path, only this one matches; code 0 (AFI 0x20, mmcboot, mmc 0:1 = SD0) gives boot_dev=sd0. The same path reads the U-Boot environment from mmc 1 = the boot card itself at byte offsets 0x5000/0x25000 (all zero in the image, so the default environment applies).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [koriki-v1.0-release / evidence/firmware/koriki-v1.0-boot-path.json hypotheses, matching](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / check_boot_flag, default environment, mmc_initialize, owl_boot_fdt_setup](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

Limits: A match between an executed path and the observed result is strong but indirect: the Boot ROM, the CMU bit it left, the AFI bytes and U-Boot's console were not observed. The match assumes the card's raw loader and U-Boot equal the image (the raw boot-region check was not supplied for OBS-001). Emulation supplies the ROM read service, DRAM outcome (256 MiB) and getenv/setenv/printf; the strap is an input, not a measurement.

## BOOT-023

U-Boot numbers MMC devices in registration order, independent of card presence: mmc_initialize (0x05023ff4) resets cur_dev_num to 0 and calls board_mmc_init (0x05004108), which returns without registering anything when the AFI boot_mode is 1, walks the enabled actions,owl-mmc nodes of its embedded DTB, maps reg to slot (reg - 0xb0230000) >> 14, saves pin-mux word 0xb01b0048 before slot 0, registers slot 2 (SD2) only when the AFI boot_dev is 0x22, and calls owl_sd_init (0x05024f04). owl_sd_init calls mmc_create (0x05023a2c), which assigns block_dev.dev = cur_dev_num++ and links the device, before mmc_init (0x05023de4); a failed mmc_init prints "slot:%d, error mmc_init" and returns -1 without unregistering (board_mmc_init then restores the SD0 pin-mux word). Executed from the image for AFI 0x20/0x22 and every SD0/SD2 mmc_init outcome: AFI 0x20 registers only SD0 as mmc 0; AFI 0x22 registers SD0 as mmc 0 and SD2 as mmc 1 whether or not SD0 has a card. An empty or failing SD0 therefore does not move SD2 to device 0.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / evidence/firmware/koriki-v1.0-boot-path.json hypotheses[].mmc_registration](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / mmc_initialize, board_mmc_init, owl_sd_init, mmc_create](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [uboot / drivers/mmc/mmc.c](https://github.com/rg35xx-cfw/u-boot_s500)

Limits: mmc_init, malloc and printf are modelled; the card-side protocol is not emulated. Corrects the registration statement in BOOT-016, which omitted the AFI 0x22 condition for SD2.

## STOR-003

Linux MMC numbering on Koriki v1.0 is chosen by the vendor kernel from the boot_dev= argument, not inherited from U-Boot. boot_dev_process (__setup "boot_dev=") maps nand/sd0/sd1/sd2/... to OWL_BOOTDEV codes (sd2 = 0x22) in g_boot_dev; proc_bootdev_init (module_init) prints "## boot_dev: 0x%x" and creates /proc/bootdev. mmc_alloc_host computes host_id = (reg - 0xB0230000) >> 14 and, when boot_dev - 0x20 == host_id, allocates host index 0 for that host (idr_alloc start 0); every other host is allocated from index 1. The host driver sets its slot id from the controller address (bit 0x4000 -> SD1, 0x8000 -> SD2, else SD0), and mmc_add_card names cards by slot: SD0 "sd_card", SD1 "<host>:<rca>", SD2 "emmc" when boot_dev is sd0 and "emmc_boot_card" otherwise. The "emmc" names are role labels from the vendor reference design (SD2 normally carries eMMC); the card's own type attribute (SD) gives the medium. OBS-001's lines "host_id: 0 ... index: 1", "host_id: 2 ... index: 0", "force sd2(emmc) host emmc_boot_card" and mmcblk0 on b0238000 are exactly this logic with boot_dev 0x22.

**Confidence:** verified · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [vendor-kernel / drivers/mmc/core/host.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/mmc/core/host.c#L433-L468)

- [vendor-kernel / drivers/mmc/core/bus.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/mmc/core/bus.c#L348-L390)

- [vendor-kernel / drivers/mmc/host/gl520x_mmc.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/mmc/host/gl520x_mmc.c#L1405-L1435)

- [vendor-kernel / arch/arm/mach-owl/bootdev-owl.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/bootdev-owl.c#L148-L180)

- [koriki-v1.0-release / kallsyms: mmc_alloc_host 0xc049fb28, mmc_add_card 0xc049f45c, acts_mmc_probe 0xc0a43724, boot_dev_process 0xc0a1bb9c, owl_get_boot_dev 0xc0022e8c](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

Limits: Binary and pinned source agree for these functions; the Koriki kernel is not a build of exactly this source revision (its cpufreq table differs, CLK-006). Linux numbering does not reveal U-Boot's numbering or which controller the Boot ROM used. TF2 being SD0 is inferred from the same logic (Koriki S03performance names b0230000 mmc1 sd_card) and was not exercised with a card in TF2.

## CPU-003

The number of CPUs Linux brings up on Koriki v1.0 comes from the Cortex-A9 SCU, not from the device tree. owl_smp_init_cpus prints "ncores %d" from scu_get_core_count, clips to nr_cpu_ids and forces 2 only when the powersave parameter is set, then marks CPUs 0..ncores-1 possible; secondaries are started through the vendor smp_ops. The release DTB lists only cpu@0 (with cpuvdd-supply and transition-latency, used by cpufreq) and cpu@1. OBS-001 shows "ncores 4", four CPUs brought up with MPIDR 0x80000000-0x80000003, possible/present/online 0-3, kernel_max 3 and no powersave argument; the two DT cpu nodes are therefore not a limit on this kernel.

**Confidence:** verified · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [vendor-kernel / arch/arm/mach-owl/platsmp-owl.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/arch/arm/mach-owl/platsmp-owl.c#L205-L232)

- [koriki-v1.0-release / /cpus](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

Limits: Four cores online under one firmware on one unit. Not established: per-core maximum stable frequency, thermal behaviour under load, behaviour of other firmware (PRODUCE/charger paths add powersave and so two cores), or that a mainline kernel needs more DT cpu nodes (it does: mainline enumerates CPUs from the DT).

## CLK-006

The ten CPU frequencies OBS-001 exposes come from a single table, cpu0_table (0xc0ad5b70), in the Koriki v1.0 kernel's data: (kHz, uV) 1488000/1375000, 1392000/1325000, 1296000/1275000, 1200000/1200000, 1104000/1175000, 1008000/1100000, 840000/1075000, 720000/1025000, 504000/1000000, 240000/975000. The pinned vendor source differs (its per-dvfslevel tables stop at 1104000 kHz), so this release is a modified build. The 1008 MHz scaling_max is set by Koriki userspace: /etc/init.d/S02overclock writes scaling_max_freq for cpu0-3 from batocera-boot.conf "overclocking" (none or unset -> 1008000; low 720000, high 1200000, turbo 1392000, extreme 1488000, powersave 240000), and the ramdisk /init selects the performance governor. androidboot.dvfslevel=0x705x is a constant string appended by U-Boot's owl_boot_fdt_setup; nothing in this kernel's command-line handling was found to parse it (the kernel's dvfslevel comes from asoc_get_dvfslevel, not from that argument).

**Confidence:** verified · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [koriki-v1.0-release / cpu0_table 0xc0ad5b70 (kallsyms), 10 x (kHz, uV)](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/koriki-v1.0-first-boot.json rootfs /etc/init.d/S02overclock sha256 95b82c727d33e405fb7d931c0889195378a40c32f5843e14b353024b75419e8c](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [vendor-kernel / drivers/cpufreq/owl-cpufreq.c](https://github.com/rg35xx-cfw/s500_kernel/blob/81cc77b59250341b9abe90ed4188cde7b7aa1eeb/drivers/cpufreq/owl-cpufreq.c#L60-L160)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

Limits: Table voltages are what the software requests from the PMIC, not measured rail voltages, and say nothing about stability, thermals or silicon margin. No frequency above the observed 1008 MHz was run or is authorized. Whether the kernel derives anything from dvfslevel on this build was not traced beyond the absence of a parser for the command-line string.

## MEM-011

OBS-001's memory quantities measure different things and are consistent: 256 MiB is the AFI ddr_size U-Boot wrote to /memory (iomem System RAM 0-0x0fffffff); "Memory: 150452k/150452k available, 111692k reserved" is the early free-page count after the boot-time reservations (kernel image, initrd 3.6 MiB, vendor "Reserved memory 32MB", 48 MiB CMA at 0x0a400000, page tables, DTB); MemTotal 237548 kB is later, after the initrd (3728 kB) and init sections are freed and CMA pages are returned to the buddy allocator (CmaFree 37572 kB still counted in MemTotal). The difference 237548 - 150452 = 87096 kB equals CMA 49152 + initrd 3728 + about 34 MiB of the vendor/init reservations being released or counted differently; the 32 MB vendor block and the CMA pool are reservations inside the 256 MiB, not extra memory. SwapTotal 524284 kB is the 512 MiB card partition, not RAM.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

- [koriki-v1.0-release / evidence/firmware/koriki-v1.0-boot-path.json hypotheses[block0_code=2].afi.ddr_size](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: The split of the remaining ~34 MiB between the vendor reservation, init memory and other boot allocations was not traced in the binary; the capture has no /proc/zoneinfo or boot-time memblock dump. Physical DRAM size and training are not observable after boot (MEM-006). For a minimal OS the relevant figure is the 256 MiB handed over, minus whatever the new kernel itself reserves; the vendor 32 MB and CMA sizes are vendor-kernel choices.

## FW-021

Koriki v1.0 writes to its root filesystem container on every boot. The ramdisk /init mounts boot/BATOCERA at /overlay_root/base, attempts an overlayfs mount (unsupported by this 3.10 kernel) and falls back to mounting the same file again, read-write, as the new root; OBS-001's mount table shows /dev/loop0 on /overlay/base and /dev/loop1 on / both ext4 rw. The /init also writes 1 to boot/REBOOT. Before inittab's "mount -a" mounts tmpfs on /run, /var and /tmp, sysvinit creates /run/initctl and /run/utmp in the container, and S50dropbear replaces the /etc/dropbear symlink with a directory. These four tree changes are exactly OBS-001's first-boot differences and are encoded, with the scripts' hashes, in evidence/firmware/koriki-v1.0-first-boot.json.

**Confidence:** verified · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [koriki-v1.0-release / cpio /init lines 51-59, 124](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/koriki-v1.0-first-boot.json rules, why_the_container_changes](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

Limits: Two simultaneous read-write mounts of one ext4 image through different loop devices are not coordinated by Linux and can corrupt it; whether Koriki ever writes through /overlay/base was not established. The types of /run/initctl and /run/utmp are predicted from sysvinit, not recorded by OBS-001.

## MAP-002

OBS-001 /proc/iomem lists the MMIO resources Koriki's drivers claimed: owl-audio-i2s 0xb0100000+0x34, pcm 0xb0110000+0x8010, owl-serial.0 0xb0120000+0x1000, i2c 0xb0174000 and 0xb0178000 (+0x4000 each), thermal 0xb01b00e8+0x8, mmc 0xb0230000 and 0xb0238000 (+0x38), dma 0xb0260000+0xd00, vde 0xb0280000+0x108, vce 0xb0288000+0x94, hdmi 0xb02c0000+0x160, de 0xb02e0000+0x100e, usb 0xb0400000+0xcd00 (dwc3.0 inside it) and b0400000.usb 0xb040cd00+0x59. No resource lies outside the canonical model's documented address blocks.

**Confidence:** verified · **Scope:** release-binary · **Validation:** hardware-observation

Evidence:

- [owner-device](https://github.com/CigThePig/ATM7039S/tree/main/evidence/observations)

Limits: A claimed resource range is what a driver asked the kernel for; it is not proof that every register in it exists or is safe to access, and absent entries (for example the GPU, which is mapped by pvrsrvkm without a named iomem entry) are not proof of absence. Only one serial port is listed, although ttyS3 is the console.

## BOOT-024

Before the cold DRAM init wrapper 0xb40690b8 the stock early loader (identical code in stock 221203, 221223, 230309, 20231014 and Koriki v1.0) runs, in this order: main 0xb4065400 clears the globals 0xb4070800..0xb407087b, reloads bootloader.ini (8 sectors, disk 0x202600 for boot codes 0 and 2) through the Boot ROM service 0xb4060400 (r9=4), then dram_caller 0xb40665d0 runs ini_to_globals 0xb4065ff8, timer_init(0) 0xb4069440, uart_init 0xb4066784 (index/baud/pad from ini+0x0e/+0x10/+0x0f), the SPI-NAND restore 0xb40663f8 only for code 5, ini_print and the "1.1" version check (else return -1 -> ADFU), board_mfp_init 0xb406a608(ini+0x0d), pmu_init 0xb40699e8(type 2) with pmu_detect 0xb4069890, adfu_check 0xb4069254(ini word +0x14), publish_globals 0xb406622c, the resume test (return 2 if 0xb4070874 and 0xb4070878 are non-zero) and the second-record copy (ini+0x2c != 0). Neither block 0 nor any of this code writes SP, CPSR, SPSR or CP15; SCTLR.I is changed only after DRAM init or on the ADFU exit, and VBAR is written (0xffff0000) only by rom_reentry_adfu 0xb40691a4, so stack, mode, interrupt masks, vectors and cache/MMU state are inherited from the Boot ROM. All analysed code is A32. The deepest pre-DRAM stack use under emulation is 136 bytes.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / main](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / dram_caller](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / ini_to_globals](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / block 0](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/sd2-predram.json call_graph, predram_graph, execution_environment, block0, runs](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Static reachability plus bounded emulation under synthetic peripheral responses (synthetic_rules); neither shows what the Boot ROM leaves in CPU state or SRAM. The SP value, exception vectors and interrupt state are unknown. The 136-byte stack depth is measured with the emulator's SP choice, not the ROM's.

## BOOT-025

The only pre-DRAM operation that differs between boot code 0 (SD0) and boot code 2 (SD2, the path OBS-001 implies) is the GPIO loopback test in adfu_check 0xb4069254: after the PMIC status check (reg 0x35, from the table halfword at 0xb406b9d4), if the ini word +0x14 is non-zero (1 in every release) and get_boot_code() != 0, it clears 0xb01b0064 bit 17, saves GPIO C OUTEN/INEN (0xb01b0018/0xb01b001c), makes bit 10 an input and bit 11 an output, then for 32 bits drives bit 11 of 0xb01b0020 with 0x55aa55aa LSB first, waits delay_ms(1) and samples bit 10; it restores OUTEN/INEN and enters ADFU (0xb40691a4) only if the sampled word equals 0x55aa55aa. On the normal return it leaves 0xb01b0064 bit 17 cleared and 0xb01b0020 bit 11 = 0, and adds 32 x 1000 us of requested delay. Executing main from 0xb4065400 with codes 0 and 2 gives event-for-event identical MMIO, PMIC, console and storage sequences apart from that inserted block; with the PR #6 DRAM harness (reference scenario) the full MMIO write and read sequences through DRAM init differ only by the same GPIO block, and the AFI boot_dev is 0x20 vs 0x22. load_ini and the storage dispatch take the same branch for codes 0 and 2. The same holds byte for byte in all five pinned releases.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / adfu_check](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / load_ini](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / storage_read_dispatch](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/sd2-predram.json code0_vs_code2, dram_stage_code0_vs_code2, structure.adfu_check, boot_code.consumers, register_inventory](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Code-level equivalence only. Hardware state may still differ between an SD0 and an SD2 boot: whatever the Boot ROM leaves (clocks, pin mux, SD controller state) is not represented, the GPIO C10/C11 wiring of the board is unknown (a loopback would send a production unit to ADFU), the elapsed time is requested, not measured, and the DRAM comparison uses synthetic PUBL/uPCTL/PMIC responses in one scenario only. Pin names C10/C11 follow the related-SoC bank layout. C-PREDRAM-PATH stays open.

## CLK-007

timer_init(0) 0xb4069440 stores the timer index at 0xb407080c, sets bit 27 of 0xb01600a4 (clk_gate_on(59); CMU_DEVCLKEN1 in the related header), writes 0 to 0xb0168008, 0xb0168010 and 0xb016800c twice, then 4 to 0xb0168008 (base 0xb0168008 + 12n; related-header names T0_CTL/T0_VAL/T0_CMP). delay_us 0xb40693f8(n) reads the count word base+8 and spins until (int32)(count - (start + 24 n)) >= 0, a wrap-safe signed comparison with no iteration bound; delay_ms(n) = delay_us(1000 n). It is the first hardware set-up of dram_caller and every pre-DRAM wait depends on it: the 1 us UART reset pulse, the 300 us PMIC clock-out wait, the I2C transfer timeout (501 x 1 ms) and the 32 x 1 ms code-2 GPIO test.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / delay_us, delay_ms, timer_init, timer_reset, timer_start](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / timer_count](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/sd2-predram.json structure.timer, register_inventory](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: 24 ticks per us is the firmware's assumption; that the timer counts up at 24 MHz from HOSC is inferred from that constant and the UART formula, not measured. A timer that does not advance would hang every delay. The emulated timer advances 24 per read (synthetic). Register names are related-SoC labels.

## UART-004

uart_init 0xb4066784(index=ini+0x0e=3, baud=ini+0x10=115200, pad=ini+0x0f=0) looks up a 24-entry table at 0xb406b520 (0x30 bytes per entry); entry 14 (UART3, pad 0) gives base 0xb0126000, divider register 0xb01600b0, clock gate bit 51 (0xb01600a4 bit 19) and reset bit 47 (0xb01600ac bit 15) and **no pin-mux writes** (other entries carry up to three MFP read-modify-writes). The routine sets the gate, pulses the reset (clear, delay_us(1), set), writes 0x8003 to base+0 and 24000000/(8*baud) - 1 = 25 to 0xb01600b0 (115384.6 baud if the clock is 24 MHz), and stores the table entry pointer at 0xb4070800. putc sends CR before LF; uart_tx waits while status (base+0xc) bit 6 is set, writes base+8, then waits until bit 10 is set; both polls are unbounded. The configuration is identical for boot codes 0 and 2 and in all five releases.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / uart_init, putc, uart_set_baud, uart_setup, uart_tx](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / UART table](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/sd2-predram.json uart, structure.uart, register_inventory](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Which pins carry UART3 TX/RX while the loader runs is not established: the loader does not program the mux for pad 0, so it relies on state set by the Boot ROM, by reset defaults or by board_mfp_init (which runs after uart_init). Status-bit meanings and the 24 MHz clock are related-SoC inferences. No physical connection is proposed.

## PMIC-002

pmu_init 0xb40699e8 is called with type 2 and the ini bytes +0x18..+0x1b; for type 2 every PMIC access goes over I2C bus ini+0x18 = 1 (controller 0xb0174000) to slave 0x65 with 16-bit big-endian registers. Bus selection 0xb406a788 (cached at 0xb406ba10) clears MFP_CTL3 (0xb01b004c) bits 16 and 18, sets 0xb0160084 bit 0 (300 us wait if it was clear), gates 0xb01600a4 bit 15, sets 0xb01b0068 bits 9-10 and writes 0x10 to I2C base+4. pmu_detect first calls 0xb4069710(1) (MFP_CTL3 bit 30 clear, 0xb01b0084 bits 31:30 = 2, 0xb01600d0 = 0x8000002d, 0xb01b0090 = 0x10, 0xb01b0094 = 0x20000000), requires reg 0xff = 0x00ca (retrying once with 0xb4069710(0), then printing "not find HOSC" and pulsing GPIO 90), probes the slave and requires reg 0x32 = 0x1bc0 (else a permanent loop). Type-2 init then writes, in order: 0x51 |= 0x800, 0x39 &= 0x7fff, 0x11 = 0xe84f, 0x12 = 0x68cc, 0x14 = 0x80ca | ((ini+0x1b adjusted) << 8) (0x89ca for ini 3), 0x15 = 0xe8ce, 0x16 = 0x334b (only if reg 0xdc > 0), 0x29 &= 0x7fc5, then reads 0x03 (s2 flag bit 4 -> resume path) and on the cold path writes 0x00 = (0x00 & 0x1f) | 0xe0c0 and clears reg 0x3f bit 3 if reg 0xdc reads 0. Version 0 hangs ("pmu ver=0 not support"). All of this is identical for boot codes 0 and 2 and in all five releases. The bus and address agree with the atc2603c node at 0x65 under I2C1 in the board DT (PMIC-001), so type 2 is most likely that device (inference).

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / pmu_init](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / pmu_detect](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / clock-out select](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / I2C bus select](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/sd2-predram.json runs.code2.pmic, register_inventory, structure.i2c](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: The PMIC transaction layer (0xb406ac10/0xb406ac60) was served by a register file, so values read from the PMIC are synthetic (pmic_defaults) and the order shown is the cold, non-resume path. No register write is converted into a voltage: the electrical meaning of regs 0x11-0x16, 0x29, 0x39, 0x51 and 0x00 is not established. The 0xb4069710 sequence looks like routing a clock to a pin for the PMIC ("not find HOSC"), which is a hypothesis.

## GPIO-002

board_mfp_init 0xb406a608(ini+0x0d) accepts 0 or 1 (larger values return -1) and does one read-modify-write from a two-entry table at 0xb406b4c8: entry 0 is 0xb01b0044 clear 0xfc000000 set 0x24000000, entry 1 is 0xb01b0048 (MFP_CTL2 in the related header) clear 0x000e39e0 set 0x000619c0. Every release ships ini+0x0d = 1. It runs after uart_init and before pmu_init and is the only board-selected register write before DRAM init.

**Confidence:** strongly-supported · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [koriki-v1.0-release / board_mfp_init](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / table](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / evidence/firmware/sd2-predram.json board, register_inventory](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: Which pin functions these fields select on the ATM7039S is not established; S500/ATM7059 pinctrl names are analogies. The reset value of the register is unknown, so the full resulting value is not known either.
