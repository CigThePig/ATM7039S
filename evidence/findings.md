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

Limits: The checksum rule and directory layout are recovered from data that satisfy them, not from a specification or the Boot ROM. Which blocks the ROM loads, and in what order, is not established. The 0xb4060000 load address is now declared by the image itself, which strengthens but does not prove BOOT-004's address hypothesis (no MMU/physical map was observed).

## BOOT-010

All executable loader content (blocks at 0x0-0x2000, the PACK directory, bootloader.bin code from 0x4c00 to 0x33c00 and app.bin) is byte-identical across stock 221203, 221223, 230309 and 20231014. Only bootloader.ini differs: 20231014 changes the DRAM record from rdodt=1, wrodt=1, drv=0xc to rdodt=2, wrodt=2, drv=0x9, and a 5 KiB high-entropy area at 0x3800-0x4bff differs in every release. The Koriki v1.0 early window (0x200200-0x300000) and U-Boot uImage are byte-identical to stock 230309.

**Confidence:** verified · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / dram_config](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / dram_config; equals koriki-v1.0](https://archive.org/details/RG35XX_original_firmwares)

- [koriki-v1.0-release / equals stock-230309 disk bytes 0x200200..0x300000](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

- [koriki-v1.0-release / equals stock-230309 U-Boot](https://github.com/rg35xx-cfw/Koriki/releases/tag/koriki_rg35xx_v1.0)

Limits: The purpose of the per-release 5 KiB area is unknown; it lies at 0xb4063800, where the loader's SPI-NAND path looks for an "SFVD" parameter backup, but no read of it on the SD path was established. Whether the ODT/drive change fixes a field problem is not documented.

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

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / struct rk3288_ddr_pctl and rk3288_ddr_publ](https://github.com/u-boot/u-boot#L9-L160)

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

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PIR bits](https://github.com/u-boot/u-boot#L273-L288)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PGSR bits](https://github.com/u-boot/u-boot#L297-L306)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / PTR0-2 field shifts](https://github.com/u-boot/u-boot#L309-L319)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / SCTL/STAT states](https://github.com/u-boot/u-boot#L351-L368)

- [u-boot-mainline / arch/arm/include/asm/arch-rockchip/ddr_rk3288.h / MCFG fields](https://github.com/u-boot/u-boot#L381-L399)

- [anbernic-stock-archive / evidence/firmware/stock-ddr-timing.json (final_pass, timings, symbolic, model_vs_unicorn)](https://archive.org/details/RG35XX_original_firmwares)

Limits: Three methods agree exactly: Unicorn emulation of the instructions, our z3 interpreter over Capstone decoding (8 symbolic paths covering 100-1200 MHz, no dependence on clobbered registers), and a hand-written model (tools/ddr_model.py) at every integer clock 100-1200 MHz, for four hardware hypotheses and three reset seeds. They share the oracle rules for peripheral reads, so they validate the calculation, not the hardware: training results, ZQ codes, lane status and reset values are not known, and bits kept by read-modify-write from unknown reset values are flagged, not predicted. Register names come from the public DesignWare uPCTL/PUBL layout (IP identity is DDR-001's inference); field meanings beyond the firmware's own packing are interpretations. The LPDDR branch (type&0xf != 0) is not modelled. Never write these values to a running system.

## DDR-003

Two properties of the stock DDR3 calculation follow from DDR-002. (1) Timings are computed before capacity detection while the capacity field is forced to 2048 MiB, so the per-rank density used for tRFC is 2048 (cs=1) or 1024 (cs=2) MiB and tRFC always takes the 350 ns class, although the detected die is 2 Gb (256 MiB), for which the same table would give 160 ns. (2) MR0 is built as (CL-4)<<4 | 0x1100 | tWR<<9 with tWR in cycles (8), so the value 0x1140 has the JEDEC DDR3 write-recovery field A11:A9 = 0 and bit 12 set; read with the JESD79-3 MR0 table that is CL 8, BL8, DLL reset, precharge power-down fast exit and WR code 000.

**Confidence:** inferred · **Scope:** release-binary · **Validation:** reproducible-static-analysis

Evidence:

- [anbernic-stock-archive / DRAM routine 0xb40673f4 (tRFC table literals 110/160/260/350; MR0 packing)](https://archive.org/details/RG35XX_original_firmwares)

- [anbernic-stock-archive / evidence/firmware/stock-ddr-timing.json (timings.density_mib, tRFC_ns_selected)](https://archive.org/details/RG35XX_original_firmwares)

Limits: The values are reproduced exactly; the JEDEC reading of MR0 and the 2 Gb die size are interpretations (the latter from MEM-006's write-back agreement). Whether the PHY passes MR0 to the DRAM unchanged, and what the DRAM does with WR code 000, are not established. A longer tRFC is conservative, not an error.
