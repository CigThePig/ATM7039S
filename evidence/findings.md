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
