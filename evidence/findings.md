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

Vendor owl_smp_init_cpus reads the SCU core count, clips it to nr_cpu_ids, and forces ncores=2 when the powersave early parameter is set; powersave defaults false.

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

The gist declares MMC0 at 0xb0230000, MMC1 at 0xb0234000 and MMC2 at 0xb0238000; 0 and 2 are okay, 1 disabled.

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

The Koriki v1.0 U-Boot default environment sets bootcmd=run ramboot with ramboot=bootm ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r} (kernel_addr_r=0x7fc0, ramdisk_addr_r=0x1ffffc0, fdt_addr_r=0x03800000). The fatload- and uEnv.txt-based mmcboot/setbootenv commands exist but are not reached from bootcmd, so on the default path the kernel, ramdisk and DTB are already in memory before U-Boot runs and uEnv.txt is not imported.

**Confidence:** inferred · **Scope:** release-binary · **Validation:** static-inspection

Evidence:

- [koriki-v1.0-release](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [miaui-gpu-rg35xx / src/kernel-rg35xx/TEST_BOOT.md: 'The pre-loader reads p1:/uImage directly (U-Boot's bootcmd is ramboot, and it does not read uEnv.txt)'](https://github.com/miaui-cfw/MiaUI-GPU-RG35XX)

Limits: Static environment text: the early loader or a stored environment could override bootcmd at runtime. Implies the early loader reads the FAT partition, which has not been traced in its code. Prediction P-UENV tests it from /proc/cmdline. Contradicted by RetroArch alpha 0.1, which ships no ramdisk.img, has no root= in its DTB /chosen or kernel image, and sets root=/dev/mmcblk0p2 only in uEnv.txt, with a U-Boot that has the same ramboot bootcmd (C-UENV). Either uEnv.txt is applied by another stage or the static reading is wrong.

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
