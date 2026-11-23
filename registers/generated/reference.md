# Source-observed address and register reference

Generated from `registers/canonical/hardware.json`. These are software observations and related-chip candidates; no hardware validation is claimed. Sizes are DT resources or explicit header extents, never proof of implemented registers.

| Block | Base | Resource size | Scope | Status | Registers |
|---|---|---|---|---|---|
| dt:/interrupt-controller@b0021000:0 | `0xb0021000` | 0x1000 | RG35XX-gist-software | okay | 0 |
| dt:/interrupt-controller@b0021000:1 | `0xb0020100` | 0x100 | RG35XX-gist-software | okay | 0 |
| dt:/cache-controller@b0022000:0 | `0xb0022000` | 0x1000 | RG35XX-gist-software | okay | 0 |
| dt:/twd-watchdog@b0020600:0 | `0xb0020600` | 0x100 | RG35XX-gist-software | disabled | 0 |
| dt:/twd-watchdog@b0020600:1 | `0xb0160000` | 0x20 | RG35XX-gist-software | disabled | 0 |
| dt:/serial@b0120000:0 | `0xb0120000` | 0x2000 | RG35XX-gist-software | okay | 0 |
| dt:/serial@b0122000:0 | `0xb0122000` | 0x2000 | RG35XX-gist-software | disabled | 0 |
| dt:/serial@b0124000:0 | `0xb0124000` | 0x2000 | RG35XX-gist-software | disabled | 0 |
| dt:/serial@b0126000:0 | `0xb0126000` | 0x2000 | RG35XX-gist-software | okay | 0 |
| dt:/serial@b0128000:0 | `0xb0128000` | 0x2000 | RG35XX-gist-software | disabled | 0 |
| dt:/serial@b012a000:0 | `0xb012a000` | 0x2000 | RG35XX-gist-software | okay | 0 |
| dt:/serial@b012c000:0 | `0xb012c000` | 0x2000 | RG35XX-gist-software | disabled | 0 |
| dt:/i2c@b0170000:0 | `0xb0170000` | 0x4000 | RG35XX-gist-software | okay | 0 |
| dt:/i2c@b0174000:0 | `0xb0174000` | 0x4000 | RG35XX-gist-software | okay | 0 |
| dt:/i2c@b0178000:0 | `0xb0178000` | 0x4000 | RG35XX-gist-software | okay | 0 |
| dt:/i2c@b017c000:0 | `0xb017c000` | 0x4000 | RG35XX-gist-software | disabled | 0 |
| dt:/spi@b0200000:0 | `0xb0200000` | 0x4000 | RG35XX-gist-software | disabled | 0 |
| dt:/spi@b0204000:0 | `0xb0204000` | 0x4000 | RG35XX-gist-software | disabled | 0 |
| dt:/spi@b0208000:0 | `0xb0208000` | 0x4000 | RG35XX-gist-software | okay | 0 |
| dt:/spi@b020c000:0 | `0xb020c000` | 0x4000 | RG35XX-gist-software | okay | 0 |
| dt:/gpio@b01b0000:0 | `0xb01b0000` | 0x40 | RG35XX-gist-software | okay | 0 |
| dt:/sirq@b01b0200:0 | `0xb01b0200` | 0x4 | RG35XX-gist-software | okay | 0 |
| dt:/pwm@b01b0050:0 | `0xb01b0050` | 0x10 | RG35XX-gist-software | okay | 0 |
| dt:/ethernet@b0310000:0 | `0xb0310000` | 0x10000 | RG35XX-gist-software | okay | 0 |
| dt:/mmc@b0230000:0 | `0xb0230000` | 0x38 | RG35XX-gist-software | okay | 0 |
| dt:/mmc@b0234000:0 | `0xb0234000` | 0x38 | RG35XX-gist-software | disabled | 0 |
| dt:/mmc@b0238000:0 | `0xb0238000` | 0x38 | RG35XX-gist-software | okay | 0 |
| dt:/usb@b0600000:0 | `0xb0600000` | 0x1000 | RG35XX-gist-software | disabled | 0 |
| dt:/usb@b0700000:0 | `0xb0700000` | 0x1000 | RG35XX-gist-software | disabled | 0 |
| dt:/usb@b0400000:0 | `0xb0400000` | 0xcd00 | RG35XX-gist-software | okay | 0 |
| dt:/usb@b0400000:1 | `0xb040cd00` | 0x59 | RG35XX-gist-software | okay | 0 |
| dt:/isp@b0270000:0 | `0xb0270000` | 0x400 | RG35XX-gist-software | disabled | 0 |
| dt:/isp@b0270000:1 | `0xb0160020` | 0x4 | RG35XX-gist-software | disabled | 0 |
| dt:/lcd0@b02a0000:0 | `0xb02a0000` | 0x20c | RG35XX-gist-software | okay | 0 |
| dt:/dsi@b0220000:0 | `0xb0220000` | 0x8c | RG35XX-gist-software | disabled | 0 |
| dt:/gpu@b0300000:0 | `0xb0300000` | 0x10000 | RG35XX-gist-software | disabled | 0 |
| dt:/vde@b0280000:0 | `0xb0280000` | 0x108 | RG35XX-gist-software | okay | 0 |
| dt:/vce@b0288000:0 | `0xb0288000` | 0x94 | RG35XX-gist-software | okay | 0 |
| dt:/hdmi@b02c0000:0 | `0xb02c0000` | 0x160 | RG35XX-gist-software | okay | 0 |
| dt:/hdmi_cec@b02c011c:0 | `0xb02c0000` | 0x160 | RG35XX-gist-software | okay | 0 |
| dt:/cvbs@b02b0000:0 | `0xb02b0000` | 0x80 | RG35XX-gist-software | disabled | 0 |
| dt:/de@b02e0000:0 | `0xb02e0000` | 0x100e | RG35XX-gist-software | okay | 0 |
| dt:/de@b02e0000:1 | `0xb0500108` | 0x4 | RG35XX-gist-software | okay | 0 |
| dt:/nand@b0210000:0 | `0xb0210000` | 0xb4 | RG35XX-gist-software | okay | 0 |
| dt:/nand@b0210000:1 | `0xb0160000` | 0xfc | RG35XX-gist-software | okay | 0 |
| dt:/nand@b0210000:2 | `0xb01b0000` | 0x90 | RG35XX-gist-software | okay | 0 |
| dt:/nand@b0210000:3 | `0xb0260000` | 0xd00 | RG35XX-gist-software | okay | 0 |
| dt:/dma@b0260000:0 | `0xb0260000` | 0xd00 | RG35XX-gist-software | okay | 0 |
| dt:/thermal:0 | `0xb01b00e8` | 0x8 | RG35XX-gist-software | okay | 0 |
| dt:/gl5203-audio-i2s:0 | `0xb0100000` | 0x34 | RG35XX-gist-software | okay | 0 |
| dt:/gl5203-audio-i2s:1 | `0xb0110000` | 0x8010 | RG35XX-gist-software | okay | 0 |
| candidate:SPS_PG_BASE | `0xb01b0100` | unknown | related-ATM7039-header | candidate-only | 12 |
| candidate:CMU_BASE | `0xb0160000` | unknown | related-ATM7039-header | candidate-only | 56 |
| candidate:TIMER_2HZ_BASE | `0xb0168000` | unknown | related-ATM7039-header | candidate-only | 17 |
| candidate:CHIPID_BASE | `0xb0150000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:HDCP2TX_BASE | `0xb0250000` | unknown | related-ATM7039-header | candidate-only | 38 |
| candidate:DMA_GLOBAL_BASE | `0xb0260000` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_PD0_BASE | `0xb0260000` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_PD1_BASE | `0xb0260004` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_PD2_BASE | `0xb0260008` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_PD3_BASE | `0xb026000c` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_EN0_BASE | `0xb0260010` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_EN1_BASE | `0xb0260014` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_EN2_BASE | `0xb0260018` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA_IRQ_EN3_BASE | `0xb026001c` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:DMA0_BASE | `0xb0260100` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA1_BASE | `0xb0260200` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA2_BASE | `0xb0260300` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA3_BASE | `0xb0260400` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA4_BASE | `0xb0260500` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA5_BASE | `0xb0260600` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA6_BASE | `0xb0260700` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA7_BASE | `0xb0260800` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA8_BASE | `0xb0260900` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA9_BASE | `0xb0260a00` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA10_BASE | `0xb0260b00` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:DMA11_BASE | `0xb0260c00` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:ISP_BASE | `0xb0270000` | unknown | related-ATM7039-header | candidate-only | 169 |
| candidate:DE_BASE | `0xb02e0000` | unknown | related-ATM7039-header | candidate-only | 7 |
| candidate:PATH0_BASE | `0xb02e0100` | unknown | related-ATM7039-header | candidate-only | 8 |
| candidate:PATH1_BASE | `0xb02e0200` | unknown | related-ATM7039-header | candidate-only | 8 |
| candidate:VIDEO0_BASE | `0xb02e0400` | unknown | related-ATM7039-header | candidate-only | 26 |
| candidate:VIDEO1_BASE | `0xb02e0500` | unknown | related-ATM7039-header | candidate-only | 26 |
| candidate:VIDEO2_BASE | `0xb02e0600` | unknown | related-ATM7039-header | candidate-only | 26 |
| candidate:VIDEO3_BASE | `0xb02e0700` | unknown | related-ATM7039-header | candidate-only | 26 |
| candidate:DMM_BASE | `0xb0290000` | unknown | related-ATM7039-header | candidate-only | 25 |
| candidate:NAND_BASE | `0xb0210000` | unknown | related-ATM7039-header | candidate-only | 28 |
| candidate:SD0_BASE | `0xb0230000` | unknown | related-ATM7039-header | candidate-only | 14 |
| candidate:SD1_BASE | `0xb0234000` | unknown | related-ATM7039-header | candidate-only | 14 |
| candidate:SD2_BASE | `0xb0238000` | unknown | related-ATM7039-header | candidate-only | 14 |
| candidate:SRAMI_BASE | `0xb0240000` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:SHARESRAM_CRTL_BASE | `0xb0240000` | unknown | related-ATM7039-header | candidate-only | 1 |
| candidate:USB3_REGISTER_BASE | `0xb0400000` | unknown | related-ATM7039-header | candidate-only | 219 |
| candidate:USB2_BASE | `0xb02b8000` | unknown | related-ATM7039-header | candidate-only | 224 |
| candidate:ETHERNET_BASE | `0xb0310000` | unknown | related-ATM7039-header | candidate-only | 145 |
| candidate:SPI0_BASE | `0xb0200000` | unknown | related-ATM7039-header | candidate-only | 9 |
| candidate:SPI1_BASE | `0xb0204000` | unknown | related-ATM7039-header | candidate-only | 9 |
| candidate:SPI2_BASE | `0xb0208000` | unknown | related-ATM7039-header | candidate-only | 9 |
| candidate:SPI3_BASE | `0xb020c000` | unknown | related-ATM7039-header | candidate-only | 9 |
| candidate:UART0_BASE | `0xb0120000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:UART1_BASE | `0xb0122000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:UART2_BASE | `0xb0124000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:UART3_BASE | `0xb0126000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:UART4_BASE | `0xb0128000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:UART5_BASE | `0xb012a000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:UART6_BASE | `0xb012c000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:IRC_BASE | `0xb0120050` | unknown | related-ATM7039-header | candidate-only | 6 |
| candidate:I2C0_BASE | `0xb0170000` | unknown | related-ATM7039-header | candidate-only | 11 |
| candidate:I2C1_BASE | `0xb0174000` | unknown | related-ATM7039-header | candidate-only | 11 |
| candidate:I2C2_BASE | `0xb0178000` | unknown | related-ATM7039-header | candidate-only | 11 |
| candidate:I2C3_BASE | `0xb017c000` | unknown | related-ATM7039-header | candidate-only | 11 |
| candidate:LCD_BASE | `0xb02a0000` | unknown | related-ATM7039-header | candidate-only | 22 |
| candidate:LVDS_BASE | `0xb02a0200` | unknown | related-ATM7039-header | candidate-only | 3 |
| candidate:CSI_BASE | `0xb02d0000` | unknown | related-ATM7039-header | candidate-only | 15 |
| candidate:DSI_BASE | `0xb0220000` | unknown | related-ATM7039-header | candidate-only | 29 |
| candidate:TVOUT_BASE | `0xb02b0000` | unknown | related-ATM7039-header | candidate-only | 26 |
| candidate:HDMI_BASE | `0xb02c0000` | unknown | related-ATM7039-header | candidate-only | 75 |
| candidate:I2S_SPDIF_BASE | `0xb0100000` | unknown | related-ATM7039-header | candidate-only | 13 |
| candidate:PCM0_BASE | `0xb0110000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:PCM1_BASE | `0xb0118000` | unknown | related-ATM7039-header | candidate-only | 4 |
| candidate:KEY_BASE | `0xb01a0000` | unknown | related-ATM7039-header | candidate-only | 9 |
| candidate:LENSC_BASE | `0xb0140000` | unknown | related-ATM7039-header | candidate-only | 20 |
| candidate:GPIO_MFP_PWM_BASE | `0xb01b0000` | unknown | related-ATM7039-header | candidate-only | 69 |

## dt:/interrupt-controller@b0021000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:80

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/interrupt-controller@b0021000:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:80

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/cache-controller@b0022000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:94

Interrupt cells (raw): `[0, 55, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/twd-watchdog@b0020600:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:104

Interrupt cells (raw): `[1, 14, 3841]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/twd-watchdog@b0020600:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:104

Interrupt cells (raw): `[1, 14, 3841]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b0120000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:112

Interrupt cells (raw): `[0, 29, 4]`. Dependencies: {"clock-frequency": [48000000], "pinctrl-names": ["default"], "pinctrl-0": [3]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b0122000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:122

Interrupt cells (raw): `[0, 30, 4]`. Dependencies: {"clock-frequency": [48000000], "pinctrl-names": ["default"], "pinctrl-0": [4]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b0124000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:132

Interrupt cells (raw): `[0, 31, 4]`. Dependencies: {"clock-frequency": [48000000], "pinctrl-names": ["default"], "pinctrl-0": [5]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b0126000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:142

Interrupt cells (raw): `[0, 32, 4]`. Dependencies: {"clock-frequency": [48000000], "pinctrl-names": ["default"], "pinctrl-0": [6]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b0128000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:152

Interrupt cells (raw): `[0, 33, 4]`. Dependencies: {"clock-frequency": [48000000], "pinctrl-names": ["default"], "pinctrl-0": [7]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b012a000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:162

Interrupt cells (raw): `[0, 34, 4]`. Dependencies: {"clock-frequency": [48000000]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/serial@b012c000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:170

Interrupt cells (raw): `[0, 35, 4]`. Dependencies: {"clock-frequency": [48000000], "pinctrl-names": ["default"], "pinctrl-0": [8]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/i2c@b0170000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:180

Interrupt cells (raw): `[0, 25, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/i2c@b0174000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:188

Interrupt cells (raw): `[0, 26, 4]`. Dependencies: {"clock-frequency": [400000], "pinctrl-names": ["default"], "pinctrl-0": [9]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/i2c@b0178000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:463

Interrupt cells (raw): `[0, 27, 4]`. Dependencies: {"clock-frequency": [400000], "pinctrl-names": ["default"], "pinctrl-0": [14]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/i2c@b017c000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:483

Interrupt cells (raw): `[0, 28, 4]`. Dependencies: {"clock-frequency": [400000], "pinctrl-names": ["default"], "pinctrl-0": [15]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/spi@b0200000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:506

Interrupt cells (raw): `[0, 19, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/spi@b0204000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:515

Interrupt cells (raw): `[0, 20, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/spi@b0208000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:524

Interrupt cells (raw): `[0, 21, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/spi@b020c000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:532

Interrupt cells (raw): `[0, 22, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/gpio@b01b0000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:540

Interrupt cells (raw): `[0, 36, 4, 0, 37, 4, 0, 38, 4, 0, 39, 4, 0, 40, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/sirq@b01b0200:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:553

Interrupt cells (raw): `[0, 13, 4, 0, 14, 4, 0, 15, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/pwm@b01b0050:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:563

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/ethernet@b0310000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:595

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/mmc@b0230000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:602

Interrupt cells (raw): `[0, 42, 4]`. Dependencies: {"pinctrl-names": ["default", "share_uart2_5"], "pinctrl-0": [20], "pinctrl-1": [21]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/mmc@b0234000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:619

Interrupt cells (raw): `[0, 43, 4]`. Dependencies: {"pinctrl-names": ["default"], "pinctrl-0": [22]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/mmc@b0238000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:631

Interrupt cells (raw): `[0, 44, 4]`. Dependencies: {"pinctrl-names": ["default"], "pinctrl-0": [23]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/usb@b0600000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:644

Interrupt cells (raw): `[0, 24, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/usb@b0700000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:654

Interrupt cells (raw): `[0, 61, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/usb@b0400000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:664

Interrupt cells (raw): `[0, 23, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/usb@b0400000:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:664

Interrupt cells (raw): `[0, 23, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/isp@b0270000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:675

Interrupt cells (raw): `[0, 12, 4]`. Dependencies: {"rear-reset-gpios": [12, 114, 1]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/isp@b0270000:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:675

Interrupt cells (raw): `[0, 12, 4]`. Dependencies: {"rear-reset-gpios": [12, 114, 1]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/lcd0@b02a0000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1143

Interrupt cells (raw): `[0, 45, 4]`. Dependencies: {"pinctrl-names": ["default"], "pinctrl-0": [25], "lcd_reset_gpios": [12, 35, 0]}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/dsi@b0220000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1183

Interrupt cells (raw): `[0, 51, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/gpu@b0300000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1201

Interrupt cells (raw): `[0, 3, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/vde@b0280000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1209

Interrupt cells (raw): `[0, 50, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/vce@b0288000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1215

Interrupt cells (raw): `[0, 49, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/hdmi@b02c0000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1221

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/hdmi_cec@b02c011c:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1235

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/cvbs@b02b0000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1240

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/de@b02e0000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1247

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/de@b02e0000:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1247

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/nand@b0210000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1252

Interrupt cells (raw): `[0, 41, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/nand@b0210000:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1252

Interrupt cells (raw): `[0, 41, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/nand@b0210000:2

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1252

Interrupt cells (raw): `[0, 41, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/nand@b0210000:3

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1252

Interrupt cells (raw): `[0, 41, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/dma@b0260000:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1260

Interrupt cells (raw): `[0, 57, 4, 0, 58, 4, 0, 59, 4, 0, 60, 4]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/thermal:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1266

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/gl5203-audio-i2s:0

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1302

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## dt:/gl5203-audio-i2s:1

Resource declared by a public device tree. Not a silicon extent; inherited configuration and inactive board features may remain. Interrupt-parent and parent cell geometry must be considered.

Evidence: gist:rg35xx.dts:1302

Interrupt cells (raw): `[]`. Dependencies: {}

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|

## candidate:SPS_PG_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:12

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SPS_PG_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 13 |
| SPS_RST_CTL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 14 |
| SPS_LDO_CTL | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 15 |
| SPS_BDG_CTL | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 16 |
| SPS_TEMP_CTL | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 17 |
| SPS_PG_CTL1 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 18 |
| SPS_PWR_AWK_MSK | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 19 |
| SPS_PWR_AWK_SRC | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 20 |
| SPS_PWR_CTL | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 21 |
| SPS_PWR_ISO_TIMER0 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 22 |
| SPS_PWR_ADDR | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 23 |
| SPS_PWR_ISO_TIMER1 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 24 |

## candidate:CMU_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:29

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| CMU_COREPLL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 30 |
| CMU_DEVPLL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 31 |
| CMU_DDRPLL | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 32 |
| CMU_NANDPLL | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 33 |
| CMU_DISPLAYPLL | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 34 |
| CMU_AUDIOPLL | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 35 |
| CMU_TVOUTPLL | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 36 |
| CMU_BUSCLK | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 37 |
| CMU_SENSORCLK | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 38 |
| CMU_LCDCLK | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 39 |
| CMU_DSICLK | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 40 |
| CMU_CSICLK | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 41 |
| CMU_DECLK | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 42 |
| CMU_BISPCLK | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 43 |
| CMU_BUSCLK1 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 44 |
| CMU_VDECLK | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 45 |
| CMU_VCECLK | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 46 |
| CMU_NANDCCLK | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 47 |
| CMU_SD0CLK | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 48 |
| CMU_SD1CLK | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 49 |
| CMU_SD2CLK | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 50 |
| CMU_UART0CLK | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 51 |
| CMU_UART1CLK | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 52 |
| CMU_UART2CLK | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 53 |
| CMU_PWM4CLK | `0x68` | unknown | unknown | unknown | inferred / related-ATM7039-header | 54 |
| CMU_PWM5CLK | `0x6c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 55 |
| CMU_PWM0CLK | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 56 |
| CMU_PWM1CLK | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 57 |
| CMU_PWM2CLK | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 58 |
| CMU_PWM3CLK | `0x7c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 59 |
| CMU_USBPLL | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 60 |
| CMU_ETHERNETPLL | `0x84` | unknown | unknown | unknown | inferred / related-ATM7039-header | 61 |
| CMU_CVBSPLL | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 62 |
| CMU_LENSCLK | `0x8c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 63 |
| CMU_GPU3DCLK | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 64 |
| CMU_CORECTL | `0x9c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 65 |
| CMU_DEVCLKEN0 | `0xa0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 66 |
| ↳ S500_GPIO_GATE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| CMU_DEVCLKEN1 | `0xa4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 67 |
| ↳ S500_UART0_GATE | mask `0x40` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| ↳ S500_UART1_GATE | mask `0x80` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| ↳ S500_UART2_GATE | mask `0x100` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| ↳ S500_UART6_GATE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| CMU_DEVRST0 | `0xa8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 68 |
| ↳ S500_GPIO_RESET | mask `0x8000` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| CMU_DEVRST1 | `0xac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 69 |
| ↳ S500_UART0_RESET | mask `0x20` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| ↳ S500_UART1_RESET | mask `0x40` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| ↳ S500_UART2_RESET | mask `0x80` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| ↳ S500_UART6_RESET | mask `0x10` | — | unknown on target | unknown | inferred / S500-manual-and-source |  |
| CMU_UART3CLK | `0xb0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 70 |
| CMU_UART4CLK | `0xb4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 71 |
| CMU_UART5CLK | `0xb8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 72 |
| CMU_UART6CLK | `0xbc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 73 |
| CMU_SSCLK | `0xc0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 74 |
| CMU_DIGITALDEBUG | `0xd0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 75 |
| CMU_ANALOGDEBUG | `0xd4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 76 |
| CMU_COREPLLDEBUG | `0xd8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 77 |
| CMU_DEVPLLDEBUG | `0xdc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 78 |
| CMU_DDRPLLDEBUG | `0xe0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 79 |
| CMU_NANDPLLDEBUG | `0xe4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 80 |
| CMU_DISPLAYPLLDEBUG | `0xe8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 81 |
| CMU_TVOUTPLLDEBUG | `0xec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 82 |
| CMU_DEEPCOLORPLLDEBUG | `0xf4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 83 |
| CMU_AUDIOPLL_ETHPLLDEBUG | `0xf8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 84 |
| CMU_CVBSPLLDEBUG | `0xfc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 85 |

## candidate:TIMER_2HZ_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:91

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| TWOHZ0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 92 |
| T0_CTL | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 93 |
| T0_CMP | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 94 |
| T0_VAL | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 95 |
| T1_CTL | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 96 |
| T1_CMP | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 97 |
| T1_VAL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 98 |
| TWOHZ1_CTL | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 99 |
| CPU1_ADDR | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 100 |
| CPU2_ADDR | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 101 |
| CPU3_ADDR | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 102 |
| CPU1_FLAG | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 103 |
| CPU2_FLAG | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 104 |
| CPU3_FLAG | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 105 |
| USB3_P0_CTL | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 106 |
| USB3_P1_CTL | `0x84` | unknown | unknown | unknown | inferred / related-ATM7039-header | 107 |
| USB2_ECS | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 108 |

## candidate:CHIPID_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:113

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| CHIPID_CTRL0 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 114 |
| CHIPID_DAT_1 | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 115 |
| CHIPID_CTRL1 | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 116 |
| CHIPID_CTRL2 | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 117 |

## candidate:HDCP2TX_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:122

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| HDCP2TX_CR | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 123 |
| HDCP2TX_SR | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 124 |
| HDCP2TX_PDOFIFO | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 125 |
| HDCP2TX_HMACID | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 126 |
| HDCP2TX_RTXMR | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 127 |
| HDCP2TX_RTXLR | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 128 |
| HDCP2TX_KMD3 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 129 |
| HDCP2TX_KMD2 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 130 |
| HDCP2TX_KMD1 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 131 |
| HDCP2TX_KMD0 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 132 |
| HDCP2TX_RRXMR | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 133 |
| HDCP2TX_RRXLR | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 134 |
| HDCP2TX_RNMR | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 135 |
| HDCP2TX_RNLR | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 136 |
| HDCP2TX_RIVMR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 137 |
| HDCP2TX_RIVLR | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 138 |
| HDCP2TX_EKSD3 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 139 |
| HDCP2TX_EKSD2 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 140 |
| HDCP2TX_EKSD1 | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 141 |
| HDCP2TX_EKSD0 | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 142 |
| HDCP2TX_KSD3 | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 143 |
| HDCP2TX_KSD2 | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 144 |
| HDCP2TX_KSD1 | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 145 |
| HDCP2TX_KSD0 | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 146 |
| HDCP2TX_GC3 | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 147 |
| HDCP2TX_GC2 | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 148 |
| HDCP2TX_GC1 | `0x68` | unknown | unknown | unknown | inferred / related-ATM7039-header | 149 |
| HDCP2TX_GC0 | `0x6c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 150 |
| HDCP2TX_STREAMCTR | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 151 |
| HDCP2TX_INPUTCTRMR | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 152 |
| HDCP2TX_INPUTCTRLR | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 153 |
| HDCP2TX_TSPH | `0x7c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 154 |
| HDCP2TX_TSSP | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 155 |
| HDCP2TX_INOUTFIFOCR | `0x84` | unknown | unknown | unknown | inferred / related-ATM7039-header | 156 |
| HDCP2TX_INRFIFOD | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 157 |
| HDCP2TX_INLENGTH | `0x8c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 158 |
| HDCP2TX_OUTEFIFOD | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 159 |
| HDCP2TX_OUTLENGTH | `0x94` | unknown | unknown | unknown | inferred / related-ATM7039-header | 160 |

## candidate:DMA_GLOBAL_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:165

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_NIC_QOS | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 166 |

## candidate:DMA_IRQ_PD0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:171

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_PD0 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 172 |

## candidate:DMA_IRQ_PD1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:177

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_PD1 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 178 |

## candidate:DMA_IRQ_PD2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:183

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_PD2 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 184 |

## candidate:DMA_IRQ_PD3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:189

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_PD3 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 190 |

## candidate:DMA_IRQ_EN0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:195

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_EN0 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 196 |

## candidate:DMA_IRQ_EN1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:201

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_EN1 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 202 |

## candidate:DMA_IRQ_EN2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:207

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_EN2 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 208 |

## candidate:DMA_IRQ_EN3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:213

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA_IRQ_EN3 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 214 |

## candidate:DMA0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:219

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA0_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 220 |
| DMA0_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 221 |
| DMA0_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 222 |
| DMA0_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 223 |
| DMA0_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 224 |
| DMA0_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 225 |
| DMA0_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 226 |
| DMA0_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 227 |
| DMA0_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 228 |
| DMA0_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 229 |
| DMA0_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 230 |
| DMA0_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 231 |
| DMA0_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 232 |
| DMA0_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 233 |
| DMA0_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 234 |
| DMA0_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 235 |
| DMA0_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 236 |
| DMA0_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 237 |
| DMA0_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 238 |
| DMA0_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 239 |

## candidate:DMA1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:244

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA1_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 245 |
| DMA1_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 246 |
| DMA1_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 247 |
| DMA1_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 248 |
| DMA1_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 249 |
| DMA1_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 250 |
| DMA1_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 251 |
| DMA1_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 252 |
| DMA1_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 253 |
| DMA1_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 254 |
| DMA1_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 255 |
| DMA1_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 256 |
| DMA1_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 257 |
| DMA1_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 258 |
| DMA1_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 259 |
| DMA1_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 260 |
| DMA1_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 261 |
| DMA1_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 262 |
| DMA1_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 263 |
| DMA1_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 264 |

## candidate:DMA2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:269

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA2_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 270 |
| DMA2_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 271 |
| DMA2_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 272 |
| DMA2_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 273 |
| DMA2_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 274 |
| DMA2_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 275 |
| DMA2_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 276 |
| DMA2_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 277 |
| DMA2_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 278 |
| DMA2_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 279 |
| DMA2_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 280 |
| DMA2_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 281 |
| DMA2_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 282 |
| DMA2_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 283 |
| DMA2_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 284 |
| DMA2_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 285 |
| DMA2_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 286 |
| DMA2_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 287 |
| DMA2_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 288 |
| DMA2_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 289 |

## candidate:DMA3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:294

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA3_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 295 |
| DMA3_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 296 |
| DMA3_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 297 |
| DMA3_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 298 |
| DMA3_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 299 |
| DMA3_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 300 |
| DMA3_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 301 |
| DMA3_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 302 |
| DMA3_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 303 |
| DMA3_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 304 |
| DMA3_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 305 |
| DMA3_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 306 |
| DMA3_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 307 |
| DMA3_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 308 |
| DMA3_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 309 |
| DMA3_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 310 |
| DMA3_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 311 |
| DMA3_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 312 |
| DMA3_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 313 |
| DMA3_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 314 |

## candidate:DMA4_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:319

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA4_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 320 |
| DMA4_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 321 |
| DMA4_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 322 |
| DMA4_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 323 |
| DMA4_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 324 |
| DMA4_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 325 |
| DMA4_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 326 |
| DMA4_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 327 |
| DMA4_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 328 |
| DMA4_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 329 |
| DMA4_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 330 |
| DMA4_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 331 |
| DMA4_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 332 |
| DMA4_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 333 |
| DMA4_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 334 |
| DMA4_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 335 |
| DMA4_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 336 |
| DMA4_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 337 |
| DMA4_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 338 |
| DMA4_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 339 |

## candidate:DMA5_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:344

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA5_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 345 |
| DMA5_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 346 |
| DMA5_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 347 |
| DMA5_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 348 |
| DMA5_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 349 |
| DMA5_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 350 |
| DMA5_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 351 |
| DMA5_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 352 |
| DMA5_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 353 |
| DMA5_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 354 |
| DMA5_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 355 |
| DMA5_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 356 |
| DMA5_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 357 |
| DMA5_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 358 |
| DMA5_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 359 |
| DMA5_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 360 |
| DMA5_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 361 |
| DMA5_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 362 |
| DMA5_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 363 |
| DMA5_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 364 |

## candidate:DMA6_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:369

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA6_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 370 |
| DMA6_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 371 |
| DMA6_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 372 |
| DMA6_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 373 |
| DMA6_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 374 |
| DMA6_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 375 |
| DMA6_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 376 |
| DMA6_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 377 |
| DMA6_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 378 |
| DMA6_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 379 |
| DMA6_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 380 |
| DMA6_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 381 |
| DMA6_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 382 |
| DMA6_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 383 |
| DMA6_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 384 |
| DMA6_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 385 |
| DMA6_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 386 |
| DMA6_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 387 |
| DMA6_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 388 |
| DMA6_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 389 |

## candidate:DMA7_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:394

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA7_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 395 |
| DMA7_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 396 |
| DMA7_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 397 |
| DMA7_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 398 |
| DMA7_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 399 |
| DMA7_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 400 |
| DMA7_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 401 |
| DMA7_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 402 |
| DMA7_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 403 |
| DMA7_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 404 |
| DMA7_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 405 |
| DMA7_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 406 |
| DMA7_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 407 |
| DMA7_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 408 |
| DMA7_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 409 |
| DMA7_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 410 |
| DMA7_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 411 |
| DMA7_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 412 |
| DMA7_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 413 |
| DMA7_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 414 |

## candidate:DMA8_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:419

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA8_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 420 |
| DMA8_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 421 |
| DMA8_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 422 |
| DMA8_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 423 |
| DMA8_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 424 |
| DMA8_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 425 |
| DMA8_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 426 |
| DMA8_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 427 |
| DMA8_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 428 |
| DMA8_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 429 |
| DMA8_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 430 |
| DMA8_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 431 |
| DMA8_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 432 |
| DMA8_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 433 |
| DMA8_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 434 |
| DMA8_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 435 |
| DMA8_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 436 |
| DMA8_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 437 |
| DMA8_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 438 |
| DMA8_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 439 |

## candidate:DMA9_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:444

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA9_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 445 |
| DMA9_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 446 |
| DMA9_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 447 |
| DMA9_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 448 |
| DMA9_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 449 |
| DMA9_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 450 |
| DMA9_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 451 |
| DMA9_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 452 |
| DMA9_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 453 |
| DMA9_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 454 |
| DMA9_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 455 |
| DMA9_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 456 |
| DMA9_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 457 |
| DMA9_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 458 |
| DMA9_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 459 |
| DMA9_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 460 |
| DMA9_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 461 |
| DMA9_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 462 |
| DMA9_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 463 |
| DMA9_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 464 |

## candidate:DMA10_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:469

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA10_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 470 |
| DMA10_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 471 |
| DMA10_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 472 |
| DMA10_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 473 |
| DMA10_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 474 |
| DMA10_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 475 |
| DMA10_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 476 |
| DMA10_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 477 |
| DMA10_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 478 |
| DMA10_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 479 |
| DMA10_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 480 |
| DMA10_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 481 |
| DMA10_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 482 |
| DMA10_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 483 |
| DMA10_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 484 |
| DMA10_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 485 |
| DMA10_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 486 |
| DMA10_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 487 |
| DMA10_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 488 |
| DMA10_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 489 |

## candidate:DMA11_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:494

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMA11_MODE | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 495 |
| DMA11_SOURCE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 496 |
| DMA11_DESTINATION | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 497 |
| DMA11_FRAME_LEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 498 |
| DMA11_FRAME_CNT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 499 |
| DMA11_REMAIN_FRAME_CNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 500 |
| DMA11_REMAIN_CNT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 501 |
| DMA11_SOURCE_STRIDE | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 502 |
| DMA11_DESTINATION_STRIDE | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 503 |
| DMA11_START | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 504 |
| DMA11_ACP_ATTRIBUTE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 505 |
| DMA11_CHAINED_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 506 |
| DMA11_CONSTANT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 507 |
| DMA11_LINKLIST_CTL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 508 |
| DMA11_NEXT_DESCRIPTOR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 509 |
| DMA11_CURRENT_DESCRIPTOR_NUM | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 510 |
| DMA11_INT_CTL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 511 |
| DMA11_INT_STATUS | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 512 |
| DMA11_CURRENT_SOURCE_POINTER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 513 |
| DMA11_CURRENT_DESTINATION_POINTER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 514 |

## candidate:ISP_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:519

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| ISP_CB_TIME | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 520 |
| ISP_CHANNEL_1_BA_OFFSET | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 524 |
| ISP_CHANNEL_1_ADDR0 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 527 |
| ISP_CHANNEL_1_ADDR1 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 528 |
| ISP_CHANNEL_1_ADDR2 | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 529 |
| ISP_CHANNEL_1_ADDR3 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 530 |
| ISP_CHANNEL_1_ADDR4 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 531 |
| ISP_CHANNEL_1_ADDR5 | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 532 |
| ISP_CHANNEL_1_ADDR6 | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 533 |
| ISP_CHANNEL_1_ADDR7 | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 534 |
| VNC_LUT_PORT | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 535 |
| VNC_RST | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 536 |
| ISP_LSC_LUT_PORT | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 537 |
| ISP_LSC_PIX_INC | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 538 |
| ISP_LSC_SCALING | `0x68` | unknown | unknown | unknown | inferred / related-ATM7039-header | 539 |
| ISP_LSC_CENTER0 | `0x6c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 540 |
| ISP_LSC_CENTER1 | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 541 |
| ISP_LSC_RST | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 542 |
| ISP_NR_CONTROL | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 543 |
| ISP_DPC_THRESHOLD | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 544 |
| ISP_CG_B_GAIN | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 545 |
| ISP_CG_G_GAIN | `0x94` | unknown | unknown | unknown | inferred / related-ATM7039-header | 546 |
| ISP_CG_R_GAIN | `0x98` | unknown | unknown | unknown | inferred / related-ATM7039-header | 547 |
| ISP_STAT_REGION_Y | `0xa0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 548 |
| ISP_STAT_REGION_X | `0xa4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 549 |
| ISP_STAT_HIST_Y | `0xa8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 550 |
| ISP_STAT_HIST_X | `0xac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 551 |
| ISP_WB_THRESHOLD | `0xb0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 552 |
| ISP_CSC_OFFSET1 | `0xc0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 553 |
| ISP_CSC_OFFSET2 | `0xc4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 554 |
| ISP_CSC_OFFSET3 | `0xc8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 555 |
| ISP_CSC_Y_R | `0xcc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 556 |
| ISP_CSC_Y_G | `0xd0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 557 |
| ISP_CSC_Y_B | `0xd4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 558 |
| ISP_CSC_CB_R | `0xd8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 559 |
| ISP_CSC_CB_G | `0xdc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 560 |
| ISP_CSC_CB_B | `0xe0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 561 |
| ISP_CSC_CR_R | `0xe4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 562 |
| ISP_CSC_CR_G | `0xe8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 563 |
| ISP_CSC_CR_B | `0xec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 564 |
| ISP_CSC_CONTROL | `0xf0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 565 |
| ISP_GC_COEFF_0 | `0x100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 566 |
| ISP_GC_COEFF_1 | `0x104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 567 |
| ISP_GC_COEFF_2 | `0x108` | unknown | unknown | unknown | inferred / related-ATM7039-header | 568 |
| ISP_GC_COEFF_3 | `0x10c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 569 |
| ISP_GC_COEFF_4 | `0x110` | unknown | unknown | unknown | inferred / related-ATM7039-header | 570 |
| ISP_GC_COEFF_5 | `0x114` | unknown | unknown | unknown | inferred / related-ATM7039-header | 571 |
| ISP_GC_COEFF_6 | `0x118` | unknown | unknown | unknown | inferred / related-ATM7039-header | 572 |
| ISP_GC_COEFF_7 | `0x11c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 573 |
| ISP_GC_COEFF_8 | `0x120` | unknown | unknown | unknown | inferred / related-ATM7039-header | 574 |
| ISP_GC_COEFF_9 | `0x124` | unknown | unknown | unknown | inferred / related-ATM7039-header | 575 |
| ISP_GC_COEFF_10 | `0x128` | unknown | unknown | unknown | inferred / related-ATM7039-header | 576 |
| ISP_GC_COEFF_11 | `0x12c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 577 |
| ISP_GC_COEFF_12 | `0x130` | unknown | unknown | unknown | inferred / related-ATM7039-header | 578 |
| ISP_GC_COEFF_13 | `0x134` | unknown | unknown | unknown | inferred / related-ATM7039-header | 579 |
| ISP_GC_COEFF_14 | `0x138` | unknown | unknown | unknown | inferred / related-ATM7039-header | 580 |
| ISP_GC_COEFF_15 | `0x13c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 581 |
| ISP_STAT_ADDR | `0x160` | unknown | unknown | unknown | inferred / related-ATM7039-header | 587 |
| ISP_COLOR_REPLACE1 | `0x170` | unknown | unknown | unknown | inferred / related-ATM7039-header | 588 |
| ISP_COLOR_REPLACE2 | `0x174` | unknown | unknown | unknown | inferred / related-ATM7039-header | 589 |
| ISP_COLOR_REPLACE3 | `0x178` | unknown | unknown | unknown | inferred / related-ATM7039-header | 590 |
| ISP_COLOR_REPLACE4 | `0x17c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 591 |
| ISP_COLOR_REPLACE5 | `0x180` | unknown | unknown | unknown | inferred / related-ATM7039-header | 592 |
| ISP_COLOR_REPLACE6 | `0x184` | unknown | unknown | unknown | inferred / related-ATM7039-header | 593 |
| ISP_COLOR_REPLACE7 | `0x188` | unknown | unknown | unknown | inferred / related-ATM7039-header | 594 |
| ISP_COLOR_REPLACE8 | `0x18c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 595 |
| ISP_COLOR_REPLACE9 | `0x190` | unknown | unknown | unknown | inferred / related-ATM7039-header | 596 |
| ISP_COLOR_REPLACE10 | `0x194` | unknown | unknown | unknown | inferred / related-ATM7039-header | 597 |
| ISP_COLOR_REPLACE11 | `0x198` | unknown | unknown | unknown | inferred / related-ATM7039-header | 598 |
| ISP_COLOR_REPLACE12 | `0x19c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 599 |
| ISP_COLOR_REPLACE13 | `0x1a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 600 |
| ISP_COLOR_REPLACE14 | `0x1a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 601 |
| ISP_COLOR_REPLACE15 | `0x1a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 602 |
| ISP_COLOR_REPLACE16 | `0x1ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 603 |
| ISP_CHANNEL_2_BA_OFFSET | `0x1f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 606 |
| ISP_CHANNEL_2_ADDR0 | `0x200` | unknown | unknown | unknown | inferred / related-ATM7039-header | 609 |
| ISP_CHANNEL_2_ADDR1 | `0x204` | unknown | unknown | unknown | inferred / related-ATM7039-header | 610 |
| ISP_CHANNEL_2_ADDR2 | `0x208` | unknown | unknown | unknown | inferred / related-ATM7039-header | 611 |
| ISP_CHANNEL_2_ADDR3 | `0x20c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 612 |
| ISP_CHANNEL_2_ADDR4 | `0x210` | unknown | unknown | unknown | inferred / related-ATM7039-header | 613 |
| ISP_CHANNEL_2_ADDR5 | `0x214` | unknown | unknown | unknown | inferred / related-ATM7039-header | 614 |
| ISP_CHANNEL_2_ADDR6 | `0x218` | unknown | unknown | unknown | inferred / related-ATM7039-header | 615 |
| ISP_CHANNEL_2_ADDR7 | `0x21c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 616 |
| ISP2_LSC_LUT_PORT | `0x22c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 617 |
| ISP2_LSC_PIX_INC | `0x230` | unknown | unknown | unknown | inferred / related-ATM7039-header | 618 |
| ISP2_LSC_SCALING | `0x234` | unknown | unknown | unknown | inferred / related-ATM7039-header | 619 |
| ISP2_LSC_CENTER0 | `0x238` | unknown | unknown | unknown | inferred / related-ATM7039-header | 620 |
| ISP2_LSC_CENTER1 | `0x23c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 621 |
| ISP2_LSC_RST | `0x240` | unknown | unknown | unknown | inferred / related-ATM7039-header | 622 |
| ISP2_NR_CONTROL | `0x24c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 623 |
| ISP2_DPC_THRESHOLD | `0x254` | unknown | unknown | unknown | inferred / related-ATM7039-header | 624 |
| ISP2_CG_B_GAIN | `0x25c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 625 |
| ISP2_CG_G_GAIN | `0x260` | unknown | unknown | unknown | inferred / related-ATM7039-header | 626 |
| ISP2_CG_R_GAIN | `0x264` | unknown | unknown | unknown | inferred / related-ATM7039-header | 627 |
| ISP2_STAT_REGION_Y | `0x26c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 628 |
| ISP2_STAT_REGION_X | `0x270` | unknown | unknown | unknown | inferred / related-ATM7039-header | 629 |
| ISP2_STAT_HIST_Y | `0x274` | unknown | unknown | unknown | inferred / related-ATM7039-header | 630 |
| ISP2_STAT_HIST_X | `0x278` | unknown | unknown | unknown | inferred / related-ATM7039-header | 631 |
| ISP2_WB_THRESHOLD | `0x27c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 632 |
| ISP2_CSC_OFFSET1 | `0x28c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 633 |
| ISP2_CSC_OFFSET2 | `0x290` | unknown | unknown | unknown | inferred / related-ATM7039-header | 634 |
| ISP2_CSC_OFFSET3 | `0x294` | unknown | unknown | unknown | inferred / related-ATM7039-header | 635 |
| ISP2_CSC_Y_R | `0x298` | unknown | unknown | unknown | inferred / related-ATM7039-header | 636 |
| ISP2_CSC_Y_G | `0x29c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 637 |
| ISP2_CSC_Y_B | `0x2a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 638 |
| ISP2_CSC_CB_R | `0x2a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 639 |
| ISP2_CSC_CB_G | `0x2a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 640 |
| ISP2_CSC_CB_B | `0x2ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 641 |
| ISP2_CSC_CR_R | `0x2b0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 642 |
| ISP2_CSC_CR_G | `0x2b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 643 |
| ISP2_CSC_CR_B | `0x2b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 644 |
| ISP2_CSC_CONTROL | `0x2bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 645 |
| ISP2_GC_COEFF_0 | `0x2cc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 646 |
| ISP2_GC_COEFF_1 | `0x2d0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 647 |
| ISP2_GC_COEFF_2 | `0x2d4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 648 |
| ISP2_GC_COEFF_3 | `0x2d8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 649 |
| ISP2_GC_COEFF_4 | `0x2dc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 650 |
| ISP2_GC_COEFF_5 | `0x2e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 651 |
| ISP2_GC_COEFF_6 | `0x2e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 652 |
| ISP2_GC_COEFF_7 | `0x2e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 653 |
| ISP2_GC_COEFF_8 | `0x2ec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 654 |
| ISP2_GC_COEFF_9 | `0x2f0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 655 |
| ISP2_GC_COEFF_10 | `0x2f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 656 |
| ISP2_GC_COEFF_11 | `0x2f8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 657 |
| ISP2_GC_COEFF_12 | `0x2fc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 658 |
| ISP2_GC_COEFF_13 | `0x300` | unknown | unknown | unknown | inferred / related-ATM7039-header | 659 |
| ISP2_GC_COEFF_14 | `0x304` | unknown | unknown | unknown | inferred / related-ATM7039-header | 660 |
| ISP2_GC_COEFF_15 | `0x308` | unknown | unknown | unknown | inferred / related-ATM7039-header | 661 |
| ISP2_STAT_ADDR | `0x32c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 667 |
| ISP2_COLOR_REPLACE1 | `0x33c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 668 |
| ISP2_COLOR_REPLACE2 | `0x340` | unknown | unknown | unknown | inferred / related-ATM7039-header | 669 |
| ISP2_COLOR_REPLACE3 | `0x344` | unknown | unknown | unknown | inferred / related-ATM7039-header | 670 |
| ISP2_COLOR_REPLACE4 | `0x348` | unknown | unknown | unknown | inferred / related-ATM7039-header | 671 |
| ISP2_COLOR_REPLACE5 | `0x34c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 672 |
| ISP2_COLOR_REPLACE6 | `0x350` | unknown | unknown | unknown | inferred / related-ATM7039-header | 673 |
| ISP2_COLOR_REPLACE7 | `0x354` | unknown | unknown | unknown | inferred / related-ATM7039-header | 674 |
| ISP2_COLOR_REPLACE8 | `0x358` | unknown | unknown | unknown | inferred / related-ATM7039-header | 675 |
| ISP2_COLOR_REPLACE9 | `0x35c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 676 |
| ISP2_COLOR_REPLACE10 | `0x360` | unknown | unknown | unknown | inferred / related-ATM7039-header | 677 |
| ISP2_COLOR_REPLACE11 | `0x364` | unknown | unknown | unknown | inferred / related-ATM7039-header | 678 |
| ISP2_COLOR_REPLACE12 | `0x368` | unknown | unknown | unknown | inferred / related-ATM7039-header | 679 |
| ISP2_COLOR_REPLACE13 | `0x36c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 680 |
| ISP2_COLOR_REPLACE14 | `0x370` | unknown | unknown | unknown | inferred / related-ATM7039-header | 681 |
| ISP2_COLOR_REPLACE15 | `0x374` | unknown | unknown | unknown | inferred / related-ATM7039-header | 682 |
| ISP2_COLOR_REPLACE16 | `0x378` | unknown | unknown | unknown | inferred / related-ATM7039-header | 683 |
| ISP_FREEMODE_IMAGE_SIZE | `0x398` | unknown | unknown | unknown | inferred / related-ATM7039-header | 684 |
| ISP_FREEMODE_SET | `0x39c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 685 |
| ISP_FREEMODE_ADDRESS | `0x3a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 686 |
| AF_ENABLE | `0x3a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 687 |
| AF_CTRL | `0x3a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 688 |
| AF_WP0 | `0x3ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 689 |
| AF_WP1 | `0x3b0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 690 |
| AF_WP2 | `0x3b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 691 |
| AF_WP3 | `0x3b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 692 |
| AF_WP4 | `0x3bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 693 |
| AF_WP5 | `0x3c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 694 |
| AF_WP6 | `0x3c4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 695 |
| AF_WP7 | `0x3c8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 696 |
| AF_WP8 | `0x3cc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 697 |
| AF_FV0 | `0x3d0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 698 |
| AF_FV1 | `0x3d4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 699 |
| AF_FV2 | `0x3d8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 700 |
| AF_FV3 | `0x3dc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 701 |
| AF_FV4 | `0x3e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 702 |
| AF_FV5 | `0x3e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 703 |
| AF_FV6 | `0x3e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 704 |
| AF_FV7 | `0x3ec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 705 |
| AF_FV8 | `0x3f0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 706 |
| AF_TEN_THOD | `0x3f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 707 |

## candidate:DE_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:713

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DE_INTEN | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 714 |
| DE_STAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 715 |
| DE_CRITICAL_NUM | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 716 |
| OUTPUT_CTL | `0x1000` | unknown | unknown | unknown | inferred / related-ATM7039-header | 717 |
| WB_CFG | `0x1004` | unknown | unknown | unknown | inferred / related-ATM7039-header | 718 |
| WB_ADDR | `0x1008` | unknown | unknown | unknown | inferred / related-ATM7039-header | 719 |
| FIFO_ERROR | `0x100c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 720 |

## candidate:PATH0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:725

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| PATH0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 726 |
| PATH0_BK | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 727 |
| PATH0_SIZE | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 728 |
| PATH0_E_COOR | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 729 |
| PATH0_GAMMA_IDX | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 730 |
| PATH0_GAMMA_RAM | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 731 |
| PATH0_CURSOR_FB | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 732 |
| PATH0_CURSOR_STR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 733 |

## candidate:PATH1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:738

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| PATH1_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 739 |
| PATH1_BK | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 740 |
| PATH1_SIZE | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 741 |
| PATH1_E_COOR | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 742 |
| PATH1_GAMMA_IDX | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 743 |
| PATH1_GAMMA_RAM | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 744 |
| PATH1_CURSOR_FB | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 745 |
| PATH1_CURSOR_STR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 746 |

## candidate:VIDEO0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:751

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| VIDEO0_CFG | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 752 |
| VIDEO0_ISIZE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 753 |
| VIDEO0_OSIZE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 754 |
| VIDEO0_SR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 755 |
| VIDEO0_SCOEF0 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 756 |
| VIDEO0_SCOEF1 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 757 |
| VIDEO0_SCOEF2 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 758 |
| VIDEO0_SCOEF3 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 759 |
| VIDEO0_SCOEF4 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 760 |
| VIDEO0_SCOEF5 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 761 |
| VIDEO0_SCOEF6 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 762 |
| VIDEO0_SCOEF7 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 763 |
| VIDEO0_FB_0 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 764 |
| VIDEO0_FB_1 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 765 |
| VIDEO0_FB_2 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 766 |
| VIDEO0_FB_RIGHT_0 | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 767 |
| VIDEO0_FB_RIGHT_1 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 768 |
| VIDEO0_FB_RIGHT_2 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 769 |
| VIDEO0_STR | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 770 |
| VIDEO0_CRITICAL_CFG | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 771 |
| VIDEO0_REMAPPING | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 772 |
| VIDEO0_COOR | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 773 |
| VIDEO0_ALPHA_CFG | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 774 |
| VIDEO0_CKMAX | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 775 |
| VIDEO0_CKMIN | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 776 |
| VIDEO0_BLEND | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 777 |

## candidate:VIDEO1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:782

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| VIDEO1_CFG | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 783 |
| VIDEO1_ISIZE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 784 |
| VIDEO1_OSIZE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 785 |
| VIDEO1_SR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 786 |
| VIDEO1_SCOEF0 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 787 |
| VIDEO1_SCOEF1 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 788 |
| VIDEO1_SCOEF2 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 789 |
| VIDEO1_SCOEF3 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 790 |
| VIDEO1_SCOEF4 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 791 |
| VIDEO1_SCOEF5 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 792 |
| VIDEO1_SCOEF6 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 793 |
| VIDEO1_SCOEF7 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 794 |
| VIDEO1_FB_0 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 795 |
| VIDEO1_FB_1 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 796 |
| VIDEO1_FB_2 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 797 |
| VIDEO1_FB_RIGHT_0 | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 798 |
| VIDEO1_FB_RIGHT_1 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 799 |
| VIDEO1_FB_RIGHT_2 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 800 |
| VIDEO1_STR | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 801 |
| VIDEO1_CRITICAL_CFG | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 802 |
| VIDEO1_REMAPPING | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 803 |
| VIDEO1_COOR | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 804 |
| VIDEO1_ALPHA_CFG | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 805 |
| VIDEO1_CKMAX | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 806 |
| VIDEO1_CKMIN | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 807 |
| VIDEO1_BLEND | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 808 |

## candidate:VIDEO2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:813

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| VIDEO2_CFG | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 814 |
| VIDEO2_ISIZE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 815 |
| VIDEO2_OSIZE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 816 |
| VIDEO2_SR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 817 |
| VIDEO2_SCOEF0 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 818 |
| VIDEO2_SCOEF1 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 819 |
| VIDEO2_SCOEF2 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 820 |
| VIDEO2_SCOEF3 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 821 |
| VIDEO2_SCOEF4 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 822 |
| VIDEO2_SCOEF5 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 823 |
| VIDEO2_SCOEF6 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 824 |
| VIDEO2_SCOEF7 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 825 |
| VIDEO2_FB_0 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 826 |
| VIDEO2_FB_1 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 827 |
| VIDEO2_FB_2 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 828 |
| VIDEO2_FB_RIGHT_0 | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 829 |
| VIDEO2_FB_RIGHT_1 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 830 |
| VIDEO2_FB_RIGHT_2 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 831 |
| VIDEO2_STR | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 832 |
| VIDEO2_CRITICAL_CFG | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 833 |
| VIDEO2_REMAPPING | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 834 |
| VIDEO2_COOR | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 835 |
| VIDEO2_ALPHA_CFG | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 836 |
| VIDEO2_CKMAX | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 837 |
| VIDEO2_CKMIN | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 838 |
| VIDEO2_BLEND | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 839 |

## candidate:VIDEO3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:844

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| VIDEO3_CFG | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 845 |
| VIDEO3_ISIZE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 846 |
| VIDEO3_OSIZE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 847 |
| VIDEO3_SR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 848 |
| VIDEO3_SCOEF0 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 849 |
| VIDEO3_SCOEF1 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 850 |
| VIDEO3_SCOEF2 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 851 |
| VIDEO3_SCOEF3 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 852 |
| VIDEO3_SCOEF4 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 853 |
| VIDEO3_SCOEF5 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 854 |
| VIDEO3_SCOEF6 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 855 |
| VIDEO3_SCOEF7 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 856 |
| VIDEO3_FB_0 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 857 |
| VIDEO3_FB_1 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 858 |
| VIDEO3_FB_2 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 859 |
| VIDEO3_FB_RIGHT_0 | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 860 |
| VIDEO3_FB_RIGHT_1 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 861 |
| VIDEO3_FB_RIGHT_2 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 862 |
| VIDEO3_STR | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 863 |
| VIDEO3_CRITICAL_CFG | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 864 |
| VIDEO3_REMAPPING | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 865 |
| VIDEO3_COOR | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 866 |
| VIDEO3_ALPHA_CFG | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 867 |
| VIDEO3_CKMAX | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 868 |
| VIDEO3_CKMIN | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 869 |
| VIDEO3_BLEND | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 870 |

## candidate:DMM_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:875

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DMM_SCH_CTRL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 876 |
| DMM_TO_CPU_BISP | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 877 |
| DMM_TO_VDE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 878 |
| DMM_TO_ETHERNET_DE | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 879 |
| DMM_TO_DE_CRITICAL_USB2 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 880 |
| DMM_TO_USB3_VCE | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 881 |
| DMM_TO_GPU3D_DAP | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 882 |
| DMM_TO_DMA_DMA_CRITICAL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 883 |
| DMM_INTERLEAVE_BASEADDR | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 884 |
| DMM_INTERLEAVE_FRAGMENT | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 885 |
| DMM_INTERLEAVE_CONFIG | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 886 |
| DMM_AXI_PRIORITY | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 887 |
| DMM_WATCH_ADDR | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 888 |
| DMM_WATCH_ADDR_MASK | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 889 |
| DMM_WATCH_DATA | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 890 |
| DMM_WATCH_DATA_MASK | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 891 |
| DMM_WATCH_CTRL | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 892 |
| DMM_MONITOR_CTRL | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 893 |
| DMM_PM_CTRL0 | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 894 |
| DMM_PM_CTRL1 | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 895 |
| DMM_PC0 | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 896 |
| DMM_PC1 | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 897 |
| DMM_PC2 | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 898 |
| DMM_PC3 | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 899 |
| DMM_DEBUG | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 900 |

## candidate:NAND_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:905

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| NAND_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 906 |
| NAND_STATUS | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 907 |
| NAND_CONFIG | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 908 |
| NAND_BC | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 909 |
| NAND_COLADDR | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 910 |
| NAND_ROWADDR0 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 911 |
| NAND_ROWADDR1 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 912 |
| NAND_CMD_FSM0 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 913 |
| NAND_CMD_FSM_CTL0 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 914 |
| NAND_CMD_FSM1 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 915 |
| NAND_CMD_FSM_CTL1 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 916 |
| NAND_CMD_FSM2 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 917 |
| NAND_CMD_FSM_CTL2 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 918 |
| NAND_ECCST0 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 919 |
| NAND_ECCST1 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 920 |
| NAND_ECCST2 | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 921 |
| NAND_ECCST3 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 922 |
| NAND_UDATAC0 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 923 |
| NAND_UDATAC1 | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 924 |
| NAND_UDATAC2 | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 925 |
| NAND_UDATAC3 | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 926 |
| NAND_FSM_START | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 927 |
| NAND_DATA_ENTRY | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 928 |
| NAND_CTL_STATUS | `0xa0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 930 |
| NAND_TIMING | `0xa4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 931 |
| NAND_ANALOG_CTL | `0xa8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 932 |
| NAND_CHCMD | `0xac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 933 |
| NAND_CHCMD_INTERVAL | `0xb0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 934 |

## candidate:SD0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:939

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SD0_EN | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 940 |
| ↳ OWL_SD_EN_RANE | mask `0x80000000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_SD_EN_S18EN | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_SD_EN_RESE | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_SD_EN_DAT1_S | mask `0x200` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_SD_EN_CLK_S | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_SD_EN_BSEL | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 51 |
| ↳ OWL_SD_EN_SDIOEN | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 52 |
| ↳ OWL_SD_EN_DDREN | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 53 |
| SD0_CTL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 941 |
| ↳ OWL_SD_CTL_TOUTEN | mask `0x80000000` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_SD_CTL_DELAY_MSK | mask `0xff0000` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_SD_CTL_CMDLEN | mask `0x2000` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_SD_CTL_SCC | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_SD_CTL_TS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 65 |
| ↳ OWL_SD_CTL_LBE | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 66 |
| ↳ OWL_SD_CTL_C7EN | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 67 |
| SD0_STATE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 942 |
| ↳ OWL_SD_STATE_DAT1BS | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 77 |
| ↳ OWL_SD_STATE_SDIOB_P | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 78 |
| ↳ OWL_SD_STATE_SDIOB_EN | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 79 |
| ↳ OWL_SD_STATE_TOUTE | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 80 |
| ↳ OWL_SD_STATE_BAEP | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 81 |
| ↳ OWL_SD_STATE_MEMRDY | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 82 |
| ↳ OWL_SD_STATE_CMDS | mask `0x800` | — | unknown on target | unknown | inferred / S500-source | 83 |
| ↳ OWL_SD_STATE_DAT1AS | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 84 |
| ↳ OWL_SD_STATE_SDIOA_P | mask `0x200` | — | unknown on target | unknown | inferred / S500-source | 85 |
| ↳ OWL_SD_STATE_SDIOA_EN | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 86 |
| ↳ OWL_SD_STATE_DAT0S | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 87 |
| ↳ OWL_SD_STATE_TEIE | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 88 |
| ↳ OWL_SD_STATE_TEI | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 89 |
| ↳ OWL_SD_STATE_CLNR | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 90 |
| ↳ OWL_SD_STATE_CLC | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 91 |
| ↳ OWL_SD_STATE_WC16ER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 92 |
| ↳ OWL_SD_STATE_RC16ER | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 93 |
| ↳ OWL_SD_STATE_CRC7ER | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 94 |
| SD0_CMD | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 943 |
| SD0_ARG | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 944 |
| SD0_RSPBUF0 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 945 |
| SD0_RSPBUF1 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 946 |
| SD0_RSPBUF2 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 947 |
| SD0_RSPBUF3 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 948 |
| SD0_RSPBUF4 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 949 |
| SD0_DAT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 950 |
| SD0_BLK_SIZE | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 951 |
| SD0_BLK_NUM | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 952 |
| SD0_BUF_SIZE | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 953 |

## candidate:SD1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:958

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SD1_EN | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 959 |
| ↳ OWL_SD_EN_RANE | mask `0x80000000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_SD_EN_S18EN | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_SD_EN_RESE | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_SD_EN_DAT1_S | mask `0x200` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_SD_EN_CLK_S | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_SD_EN_BSEL | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 51 |
| ↳ OWL_SD_EN_SDIOEN | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 52 |
| ↳ OWL_SD_EN_DDREN | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 53 |
| SD1_CTL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 960 |
| ↳ OWL_SD_CTL_TOUTEN | mask `0x80000000` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_SD_CTL_DELAY_MSK | mask `0xff0000` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_SD_CTL_CMDLEN | mask `0x2000` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_SD_CTL_SCC | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_SD_CTL_TS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 65 |
| ↳ OWL_SD_CTL_LBE | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 66 |
| ↳ OWL_SD_CTL_C7EN | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 67 |
| SD1_STATE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 961 |
| ↳ OWL_SD_STATE_DAT1BS | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 77 |
| ↳ OWL_SD_STATE_SDIOB_P | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 78 |
| ↳ OWL_SD_STATE_SDIOB_EN | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 79 |
| ↳ OWL_SD_STATE_TOUTE | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 80 |
| ↳ OWL_SD_STATE_BAEP | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 81 |
| ↳ OWL_SD_STATE_MEMRDY | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 82 |
| ↳ OWL_SD_STATE_CMDS | mask `0x800` | — | unknown on target | unknown | inferred / S500-source | 83 |
| ↳ OWL_SD_STATE_DAT1AS | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 84 |
| ↳ OWL_SD_STATE_SDIOA_P | mask `0x200` | — | unknown on target | unknown | inferred / S500-source | 85 |
| ↳ OWL_SD_STATE_SDIOA_EN | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 86 |
| ↳ OWL_SD_STATE_DAT0S | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 87 |
| ↳ OWL_SD_STATE_TEIE | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 88 |
| ↳ OWL_SD_STATE_TEI | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 89 |
| ↳ OWL_SD_STATE_CLNR | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 90 |
| ↳ OWL_SD_STATE_CLC | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 91 |
| ↳ OWL_SD_STATE_WC16ER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 92 |
| ↳ OWL_SD_STATE_RC16ER | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 93 |
| ↳ OWL_SD_STATE_CRC7ER | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 94 |
| SD1_CMD | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 962 |
| SD1_ARG | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 963 |
| SD1_RSPBUF0 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 964 |
| SD1_RSPBUF1 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 965 |
| SD1_RSPBUF2 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 966 |
| SD1_RSPBUF3 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 967 |
| SD1_RSPBUF4 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 968 |
| SD1_DAT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 969 |
| SD1_BLK_SIZE | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 970 |
| SD1_BLK_NUM | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 971 |
| SD1_BUF_SIZE | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 972 |

## candidate:SD2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:977

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SD2_EN | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 978 |
| ↳ OWL_SD_EN_RANE | mask `0x80000000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_SD_EN_S18EN | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_SD_EN_RESE | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_SD_EN_DAT1_S | mask `0x200` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_SD_EN_CLK_S | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_SD_EN_BSEL | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 51 |
| ↳ OWL_SD_EN_SDIOEN | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 52 |
| ↳ OWL_SD_EN_DDREN | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 53 |
| SD2_CTL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 979 |
| ↳ OWL_SD_CTL_TOUTEN | mask `0x80000000` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_SD_CTL_DELAY_MSK | mask `0xff0000` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_SD_CTL_CMDLEN | mask `0x2000` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_SD_CTL_SCC | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_SD_CTL_TS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 65 |
| ↳ OWL_SD_CTL_LBE | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 66 |
| ↳ OWL_SD_CTL_C7EN | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 67 |
| SD2_STATE | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 980 |
| ↳ OWL_SD_STATE_DAT1BS | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 77 |
| ↳ OWL_SD_STATE_SDIOB_P | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 78 |
| ↳ OWL_SD_STATE_SDIOB_EN | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 79 |
| ↳ OWL_SD_STATE_TOUTE | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 80 |
| ↳ OWL_SD_STATE_BAEP | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 81 |
| ↳ OWL_SD_STATE_MEMRDY | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 82 |
| ↳ OWL_SD_STATE_CMDS | mask `0x800` | — | unknown on target | unknown | inferred / S500-source | 83 |
| ↳ OWL_SD_STATE_DAT1AS | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 84 |
| ↳ OWL_SD_STATE_SDIOA_P | mask `0x200` | — | unknown on target | unknown | inferred / S500-source | 85 |
| ↳ OWL_SD_STATE_SDIOA_EN | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 86 |
| ↳ OWL_SD_STATE_DAT0S | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 87 |
| ↳ OWL_SD_STATE_TEIE | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 88 |
| ↳ OWL_SD_STATE_TEI | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 89 |
| ↳ OWL_SD_STATE_CLNR | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 90 |
| ↳ OWL_SD_STATE_CLC | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 91 |
| ↳ OWL_SD_STATE_WC16ER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 92 |
| ↳ OWL_SD_STATE_RC16ER | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 93 |
| ↳ OWL_SD_STATE_CRC7ER | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 94 |
| SD2_CMD | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 981 |
| SD2_ARG | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 982 |
| SD2_RSPBUF0 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 983 |
| SD2_RSPBUF1 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 984 |
| SD2_RSPBUF2 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 985 |
| SD2_RSPBUF3 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 986 |
| SD2_RSPBUF4 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 987 |
| SD2_DAT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 988 |
| SD2_BLK_SIZE | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 989 |
| SD2_BLK_NUM | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 990 |
| SD2_BUF_SIZE | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 991 |

## candidate:SRAMI_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:996

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SRAMI_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 997 |

## candidate:SHARESRAM_CRTL_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1002

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SHARESRAM_CTL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1003 |

## candidate:USB3_REGISTER_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1008

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| USB3_CAPLENGTH | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1009 |
| USB3_HCSPARAMS1 | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1010 |
| USB3_HCSPARAMS2 | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1011 |
| USB3_HCSPARAMS3 | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1012 |
| USB3_HCCPARAMS | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1013 |
| USB3_DBOFF | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1014 |
| USB3_RTSOFF | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1015 |
| USB3_USBCMD | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1016 |
| USB3_USBSTS | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1017 |
| USB3_PAGESIZE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1018 |
| USB3_DNCTRL | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1019 |
| USB3_CRCR_L | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1020 |
| USB3_CRCR_H | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1021 |
| USB3_DCBAAP_L | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1022 |
| USB3_DCBAAP_H | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1023 |
| USB3_CONFIG | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1024 |
| USB3_PORT0_PORTSC | `0x420` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1025 |
| USB3_PORT0_PORTPMSC | `0x424` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1026 |
| USB3_PORT0_PORTLI | `0x428` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1027 |
| USB3_PORT0_PORTHLPMC | `0x42c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1028 |
| USB3_PORT1_PORTSC | `0x430` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1029 |
| USB3_PORT1_PORTPMSC | `0x434` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1030 |
| USB3_PORT1_PORTLI | `0x438` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1031 |
| USB3_PORT1_PORTHLPMC | `0x43c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1032 |
| USB3_PORT2_PORTSC | `0x440` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1033 |
| USB3_PORT2_PORTPMSC | `0x444` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1034 |
| USB3_PORT2_PORTLI | `0x448` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1035 |
| USB3_PORT2_PORTHLPMC | `0x44c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1036 |
| USB3_MFINDEX | `0x460` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1037 |
| USB3_IMAN | `0x480` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1038 |
| USB3_IMOD | `0x484` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1039 |
| USB3_ERSTSZ | `0x488` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1040 |
| USB3_ERSTBA_L | `0x490` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1041 |
| USB3_ERSTBA_H | `0x494` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1042 |
| USB3_ERDP_L | `0x498` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1043 |
| USB3_ERDP_H | `0x49c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1044 |
| USB3_DB_HOST | `0x4a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1045 |
| USB3_DB_DEVICE1 | `0x4a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1046 |
| USB3_DB_DEVICE2 | `0x4a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1047 |
| USB3_DB_DEVICE3 | `0x4ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1048 |
| USB3_DB_DEVICE4 | `0x4b0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1049 |
| USB3_DB_DEVICE5 | `0x4b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1050 |
| USB3_DB_DEVICE6 | `0x4b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1051 |
| USB3_DB_DEVICE7 | `0x4bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1052 |
| USB3_DB_DEVICE8 | `0x4c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1053 |
| USB3_DB_DEVICE9 | `0x4c4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1054 |
| USB3_DB_DEVICE10 | `0x4c8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1055 |
| USB3_DB_DEVICE11 | `0x4cc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1056 |
| USB3_DB_DEVICE12 | `0x4d0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1057 |
| USB3_DB_DEVICE13 | `0x4d4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1058 |
| USB3_DB_DEVICE14 | `0x4d8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1059 |
| USB3_DB_DEVICE15 | `0x4dc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1060 |
| USB3_DB_DEVICE16 | `0x4e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1061 |
| USB3_DB_DEVICE17 | `0x4e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1062 |
| USB3_DB_DEVICE18 | `0x4e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1063 |
| USB3_DB_DEVICE19 | `0x4ec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1064 |
| USB3_DB_DEVICE20 | `0x4f0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1065 |
| USB3_DB_DEVICE21 | `0x4f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1066 |
| USB3_DB_DEVICE22 | `0x4f8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1067 |
| USB3_DB_DEVICE23 | `0x4fc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1068 |
| USB3_DB_DEVICE24 | `0x500` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1069 |
| USB3_DB_DEVICE25 | `0x504` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1070 |
| USB3_DB_DEVICE26 | `0x508` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1071 |
| USB3_DB_DEVICE27 | `0x50c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1072 |
| USB3_DB_DEVICE28 | `0x510` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1073 |
| USB3_DB_DEVICE29 | `0x514` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1074 |
| USB3_DB_DEVICE30 | `0x518` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1075 |
| USB3_DB_DEVICE31 | `0x51c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1076 |
| USB3_USBLEGSUP | `0x8a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1077 |
| USB3_USBLEGCTLSTS | `0x8a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1078 |
| USB3_SUPTPRT2_DW0 | `0x8b0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1079 |
| USB3_SUPTPRT2_DW1 | `0x8b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1080 |
| USB3_SUPTPRT2_DW2 | `0x8b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1081 |
| USB3_SUPTPRT2_DW3 | `0x8bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1082 |
| USB3_SUPTPRT3_DW0 | `0x8c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1083 |
| USB3_SUPTPRT3_DW1 | `0x8c4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1084 |
| USB3_SUPTPRT3_DW2 | `0x8c8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1085 |
| USB3_SUPTPRT3_DW3 | `0x8cc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1086 |
| USB3_DCID | `0x8d0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1087 |
| USB3_DCDB | `0x8d4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1088 |
| USB3_DCERSTSZ | `0x8d8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1089 |
| USB3_DCERSTBA_LO | `0x8e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1090 |
| USB3_DCERSTBA_HI | `0x8e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1091 |
| USB3_DCERDP_LO | `0x8e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1092 |
| USB3_DCERDP_HI | `0x8ec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1093 |
| USB3_DCCTRL | `0x8f0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1094 |
| USB3_DCSTAT | `0x8f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1095 |
| USB3_DCPORTSC | `0x8f8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1096 |
| USB3_DCECP_LO | `0x900` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1097 |
| USB3_DCECP_HI | `0x904` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1098 |
| USB3_DCDDI1 | `0x908` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1099 |
| USB3_DCDDI2 | `0x90c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1100 |
| USB3_GSBUSCFG0 | `0xc100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1101 |
| USB3_GSBUSCFG1 | `0xc104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1102 |
| USB3_GTXTHRCFG | `0xc108` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1103 |
| USB3_GRXTHRCFG | `0xc10c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1104 |
| USB3_GCTL | `0xc110` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1105 |
| USB3_GSTS | `0xc118` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1106 |
| USB3_GSNPSID | `0xc120` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1107 |
| USB3_GGPIO | `0xc124` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1108 |
| USB3_GUID | `0xc128` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1109 |
| USB3_GUCTL | `0xc12c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1110 |
| USB3_GBUSERRADDRLO | `0xc130` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1111 |
| USB3_GBUSERRADDRHI | `0xc134` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1112 |
| USB3_GPRTBIMAPL | `0xc138` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1113 |
| USB3_GPRTBIMAPH | `0xc13c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1114 |
| USB3_GHWPARAMS0 | `0xc140` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1115 |
| USB3_GHWPARAMS1 | `0xc144` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1116 |
| USB3_GHWPARAMS2 | `0xc148` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1117 |
| USB3_GHWPARAMS3 | `0xc14c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1118 |
| USB3_GHWPARAMS4 | `0xc150` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1119 |
| USB3_GHWPARAMS5 | `0xc154` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1120 |
| USB3_GHWPARAMS6 | `0xc158` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1121 |
| USB3_GHWPARAMS7 | `0xc15c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1122 |
| USB3_GBDGFIFOSPACE | `0xc160` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1123 |
| USB3_GDBGLTSSM | `0xc164` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1124 |
| USB3_GDBGLNMCC | `0xc168` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1125 |
| USB3_GDBGBMU | `0xc16c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1126 |
| USB3_GDBGLSPMUX | `0xc170` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1127 |
| USB3_GDBGLSP | `0xc174` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1128 |
| USB3_GDBGEPINFO0 | `0xc178` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1129 |
| USB3_GDBGEPINFO1 | `0xc17c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1130 |
| USB3_GPRTBIMAPLO_HS | `0xc180` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1131 |
| USB3_GPRTBIMAPHI_HS | `0xc184` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1132 |
| USB3_GPRTBIMAPLO_FS | `0xc188` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1133 |
| USB3_GPRTBIMAPHI_FS | `0xc18c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1134 |
| USB3_GUSB2CFG0 | `0xc200` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1135 |
| USB3_GUSB2CFG1 | `0xc204` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1136 |
| USB3_GUSB2I2CCTL | `0xc240` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1137 |
| USB3_GUSB2PHYACC0 | `0xc280` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1138 |
| USB3_GUSB2PHYACC1 | `0xc284` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1139 |
| USB3_GUSB3PIPECTL | `0xc2c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1140 |
| USB3_GTXFIFOSIZ0 | `0xc300` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1141 |
| USB3_GTXFIFOSIZ1 | `0xc304` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1142 |
| USB3_GTXFIFOSIZ2 | `0xc308` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1143 |
| USB3_GTXFIFOSIZ3 | `0xc30c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1144 |
| USB3_GTXFIFOSIZ4 | `0xc310` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1145 |
| USB3_GRXFIFOSIZ0 | `0xc380` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1146 |
| USB3_GRXFIFOSIZ1 | `0xc384` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1147 |
| USB3_GRXFIFOSIZ2 | `0xc388` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1148 |
| USB3_GRXFIFOSIZ3 | `0xc38c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1149 |
| USB3_GRXFIFOSIZ4 | `0xc390` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1150 |
| USB3_GEVETADR0 | `0xc400` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1151 |
| USB3_GEVNTSIZ0 | `0xc408` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1152 |
| USB3_GEVNTCOUNT0 | `0xc40c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1153 |
| USB3_DCFG | `0xc700` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1154 |
| USB3_DCTL | `0xc704` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1155 |
| USB3_DEVTEN | `0xc708` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1156 |
| USB3_DSTS | `0xc70c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1157 |
| USB3_DGCMDPAR | `0xc710` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1158 |
| USB3_DGCMD | `0xc714` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1159 |
| USB3_DALEPENA | `0xc720` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1160 |
| USB3_DEPCMDPAR2_0 | `0xc800` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1161 |
| USB3_DEPCMDPAR1_0 | `0xc804` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1162 |
| USB3_DEPCMDPAR0_0 | `0xc808` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1163 |
| USB3_DEPCMD_0 | `0xc80c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1164 |
| USB3_DEPCMDPAR2_1 | `0xc810` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1165 |
| USB3_DEPCMDPAR1_1 | `0xc814` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1166 |
| USB3_DEPCMDPAR0_1 | `0xc818` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1167 |
| USB3_DEPCMD_1 | `0xc81c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1168 |
| USB3_DEPCMDPAR2_2 | `0xc820` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1169 |
| USB3_DEPCMDPAR1_2 | `0xc824` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1170 |
| USB3_DEPCMDPAR0_2 | `0xc828` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1171 |
| USB3_DEPCMD_2 | `0xc82c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1172 |
| USB3_DEPCMDPAR2_3 | `0xc830` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1173 |
| USB3_DEPCMDPAR1_3 | `0xc834` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1174 |
| USB3_DEPCMDPAR0_3 | `0xc838` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1175 |
| USB3_DEPCMD_3 | `0xc83c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1176 |
| USB3_DEPCMDPAR2_4 | `0xc840` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1177 |
| USB3_DEPCMDPAR1_4 | `0xc844` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1178 |
| USB3_DEPCMDPAR0_4 | `0xc848` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1179 |
| USB3_DEPCMD_4 | `0xc84c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1180 |
| USB3_DEPCMDPAR2_5 | `0xc850` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1181 |
| USB3_DEPCMDPAR1_5 | `0xc854` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1182 |
| USB3_DEPCMDPAR0_5 | `0xc858` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1183 |
| USB3_DEPCMD_5 | `0xc85c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1184 |
| USB3_DEPCMDPAR2_6 | `0xc860` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1185 |
| USB3_DEPCMDPAR1_6 | `0xc864` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1186 |
| USB3_DEPCMDPAR0_6 | `0xc868` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1187 |
| USB3_DEPCMD_6 | `0xc86c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1188 |
| USB3_DEPCMDPAR2_7 | `0xc870` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1189 |
| USB3_DEPCMDPAR1_7 | `0xc874` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1190 |
| USB3_DEPCMDPAR0_7 | `0xc878` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1191 |
| USB3_DEPCMD_7 | `0xc87c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1192 |
| USB3_DEPCMDPAR2_8 | `0xc880` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1193 |
| USB3_DEPCMDPAR1_8 | `0xc884` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1194 |
| USB3_DEPCMDPAR0_8 | `0xc888` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1195 |
| USB3_DEPCMD_8 | `0xc88c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1196 |
| USB3_DEPCMDPAR2_9 | `0xc890` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1197 |
| USB3_DEPCMDPAR1_9 | `0xc894` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1198 |
| USB3_DEPCMDPAR0_9 | `0xc898` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1199 |
| USB3_DEPCMD_9 | `0xc89c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1200 |
| USB3_OCFG | `0xcc00` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1201 |
| USB3_OCTL | `0xcc04` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1202 |
| USB3_OEVEN | `0xcc08` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1203 |
| USB3_OSTS | `0xcc0c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1204 |
| USB3_CDR_KIKD | `0xcd00` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1205 |
| USB3_CDR_KP1 | `0xcd04` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1206 |
| USB3_TIMER_INIT | `0xcd08` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1207 |
| USB3_CDR_CONTROL | `0xcd0c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1208 |
| USB3_RX_OFFSET_PS | `0xcd10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1209 |
| USB3_EQ_CONTROL | `0xcd14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1210 |
| USB3_RX_OOBS_SSC0 | `0xcd18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1211 |
| USB3_CMU_SSC1 | `0xcd1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1212 |
| USB3_CMU_DEBUG_LDO | `0xcd20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1213 |
| USB3_TX_AMP_DEBUG | `0xcd24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1214 |
| USB3_Z0 | `0xcd28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1215 |
| USB3_DMR_BACR | `0xcd2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1216 |
| USB3_IER_BCSR | `0xcd30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1217 |
| USB3_BPR | `0xcd34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1218 |
| USB3_BFNR | `0xcd38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1219 |
| USB3_BENR_REV | `0xcd3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1220 |
| USB3_FLD | `0xcd40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1221 |
| USB3_CMU_PLL2_BISTDEBUG | `0xcd44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1222 |
| USB3_USB2_P0_VDCTRL | `0xcd48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1223 |
| USB3_BACKDOOR | `0xcd4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1224 |
| USB3_EXT_CTL | `0xcd50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1225 |
| USB3_EFUSE_CTR | `0xcd54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1226 |
| USB3_USB2_P1_VDCTRL | `0xcd58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1227 |

## candidate:USB2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1232

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| USB2_OTGIRQ | `0x1bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1233 |
| USB2_OTGSTATE | `0x1bd` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1234 |
| USB2_OTGCTRL | `0x1be` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1235 |
| USB2_OTGSTATUS | `0x1bf` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1236 |
| USB2_OTGIEN | `0x1c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1237 |
| USB2_TAAIDLBDIS | `0x1c1` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1238 |
| USB2_TAWAITBCON | `0x1c2` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1239 |
| USB2_TBVBUSPLS | `0x1c3` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1240 |
| USB2_TBVBUSDISPLS | `0x1c7` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1241 |
| USB2_HCEP0CTRL | `0xc0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1242 |
| USB2_HCOUT1CTRL | `0xc4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1243 |
| USB2_HCOUT2CTRL | `0xc8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1244 |
| USB2_HCOUT3CTRL | `0xcc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1245 |
| USB2_HCOUT4CTRL | `0xd0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1246 |
| USB2_HCOUT5CTRL | `0xd4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1247 |
| USB2_HCOUT0ERR | `0xc1` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1248 |
| USB2_HCOUT1ERR | `0xc5` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1249 |
| USB2_HCOUT2ERR | `0xc9` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1250 |
| USB2_HCOUT3ERR | `0xcd` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1251 |
| USB2_HCOUT4ERR | `0xd1` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1252 |
| USB2_HCOUT5ERR | `0xd5` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1253 |
| USB2_HCIN1CTRL | `0xc6` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1254 |
| USB2_HCIN2CTRL | `0xca` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1255 |
| USB2_HCIN3CTRL | `0xce` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1256 |
| USB2_HCIN4CTRL | `0xd2` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1257 |
| USB2_HCIN5CTRL | `0xd6` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1258 |
| USB2_HCIN0ERR | `0xc3` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1259 |
| USB2_HCIN1ERR | `0xc7` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1260 |
| USB2_HCIN2ERR | `0xcb` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1261 |
| USB2_HCIN3ERR | `0xcf` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1262 |
| USB2_HCIN4ERR | `0xd3` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1263 |
| USB2_HCIN5ERR | `0xd7` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1264 |
| USB2_HCPORTCTRL | `0x1ab` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1265 |
| USB2_HCFRMNRL | `0x1ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1266 |
| USB2_HCFRMNRH | `0x1ad` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1267 |
| USB2_HCFRMREMAINL | `0x1ae` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1268 |
| USB2_HCFRMREMAINH | `0x1af` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1269 |
| USB2_HCINXERRIRQ | `0x1b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1270 |
| USB2_HCOUTXERRIRQ | `0x1b6` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1271 |
| USB2_HCINXERRIEN | `0x1b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1272 |
| USB2_HCOUTXERRIEN | `0x1ba` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1273 |
| USB2_HCIN0MAXPCK | `0x1e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1274 |
| USB2_HCIN1MAXPCKL | `0x1e2` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1275 |
| USB2_HCIN2MAXPCKL | `0x1e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1276 |
| USB2_HCIN3MAXPCKL | `0x1e6` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1277 |
| USB2_HCIN4MAXPCKL | `0x1e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1278 |
| USB2_HCIN5MAXPCKL | `0x1ea` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1279 |
| USB2_HCIN1MAXPCKH | `0x1e3` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1280 |
| USB2_HCIN2MAXPCKH | `0x1e5` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1281 |
| USB2_HCIN3MAXPCKH | `0x1e7` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1282 |
| USB2_HCIN4MAXPCKH | `0x1e9` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1283 |
| USB2_HCIN5MAXPCKH | `0x1eb` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1284 |
| USB2_HCOUT1MAXPCKL | `0x3e2` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1285 |
| USB2_HCOUT2MAXPCKL | `0x3e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1286 |
| USB2_HCOUT3MAXPCKL | `0x3e6` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1287 |
| USB2_HCOUT4MAXPCKL | `0x3e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1288 |
| USB2_HCOUT5MAXPCKL | `0x3ea` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1289 |
| USB2_HCOUT1MAXPCKH | `0x3e3` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1290 |
| USB2_HCOUT2MAXPCKH | `0x3e5` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1291 |
| USB2_HCOUT3MAXPCKH | `0x3e7` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1292 |
| USB2_HCOUT4MAXPCKH | `0x3e9` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1293 |
| USB2_HCOUT5MAXPCKH | `0x3eb` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1294 |
| USB2_OUT0BC | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1295 |
| USB2_IN0BC | `0x1` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1296 |
| USB2_EP0CS | `0x2` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1297 |
| USB2_OUT1BCL | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1298 |
| USB2_OUT2BCL | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1299 |
| USB2_OUT3BCL | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1300 |
| USB2_OUT4BCL | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1301 |
| USB2_OUT5BCL | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1302 |
| USB2_OUT1BCH | `0x9` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1303 |
| USB2_OUT2BCH | `0x11` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1304 |
| USB2_OUT3BCH | `0x19` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1305 |
| USB2_OUT4BCH | `0x21` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1306 |
| USB2_OUT5BCH | `0x29` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1307 |
| USB2_OUT1CS | `0xb` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1308 |
| USB2_OUT2CS | `0x13` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1309 |
| USB2_OUT3CS | `0x1b` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1310 |
| USB2_OUT4CS | `0x23` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1311 |
| USB2_OUT5CS | `0x2b` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1312 |
| USB2_OUT1CON | `0xa` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1313 |
| USB2_OUT2CON | `0x12` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1314 |
| USB2_OUT3CON | `0x1a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1315 |
| USB2_OUT4CON | `0x22` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1316 |
| USB2_OUT5CON | `0x2a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1317 |
| USB2_IN1BCL | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1318 |
| USB2_IN2BCL | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1319 |
| USB2_IN3BCL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1320 |
| USB2_IN4BCL | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1321 |
| USB2_IN5BCL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1322 |
| USB2_IN1BCH | `0xd` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1323 |
| USB2_IN2BCH | `0x15` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1324 |
| USB2_IN3BCH | `0x1d` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1325 |
| USB2_IN4BCH | `0x25` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1326 |
| USB2_IN5BCH | `0x2d` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1327 |
| USB2_IN1CS | `0xf` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1328 |
| USB2_IN2CS | `0x17` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1329 |
| USB2_IN3CS | `0x1f` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1330 |
| USB2_IN4CS | `0x27` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1331 |
| USB2_IN5CS | `0x2f` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1332 |
| USB2_IN1CON | `0xe` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1333 |
| USB2_IN2CON | `0x16` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1334 |
| USB2_IN3CON | `0x1e` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1335 |
| USB2_IN4CON | `0x26` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1336 |
| USB2_IN5CON | `0x2e` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1337 |
| USB2_FIFO1DATA | `0x84` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1338 |
| USB2_FIFO2DATA | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1339 |
| USB2_FIFO3DATA | `0x8c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1340 |
| USB2_FIFO4DATA | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1341 |
| USB2_FIFO5DATA | `0x94` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1342 |
| USB2_EP0INDATA_W0 | `0x100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1343 |
| USB2_EP0INDATA_W1 | `0x104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1344 |
| USB2_EP0INDATA_W2 | `0x108` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1345 |
| USB2_EP0INDATA_W3 | `0x10c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1346 |
| USB2_EP0INDATA_W4 | `0x110` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1347 |
| USB2_EP0INDATA_W5 | `0x114` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1348 |
| USB2_EP0INDATA_W6 | `0x118` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1349 |
| USB2_EP0INDATA_W7 | `0x11c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1350 |
| USB2_EP0INDATA_W8 | `0x120` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1351 |
| USB2_EP0INDATA_W9 | `0x124` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1352 |
| USB2_EP0INDATA_W10 | `0x128` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1353 |
| USB2_EP0INDATA_W11 | `0x12c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1354 |
| USB2_EP0INDATA_W12 | `0x130` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1355 |
| USB2_EP0INDATA_W13 | `0x134` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1356 |
| USB2_EP0INDATA_W14 | `0x138` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1357 |
| USB2_EP0INDATA_W15 | `0x13c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1358 |
| USB2_EP0OUTDATA_W0 | `0x140` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1359 |
| USB2_EP0OUTDATA_W1 | `0x144` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1360 |
| USB2_EP0OUTDATA_W2 | `0x148` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1361 |
| USB2_EP0OUTDATA_W3 | `0x14c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1362 |
| USB2_EP0OUTDATA_W4 | `0x150` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1363 |
| USB2_EP0OUTDATA_W5 | `0x154` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1364 |
| USB2_EP0OUTDATA_W6 | `0x158` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1365 |
| USB2_EP0OUTDATA_W7 | `0x15c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1366 |
| USB2_EP0OUTDATA_W8 | `0x160` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1367 |
| USB2_EP0OUTDATA_W9 | `0x164` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1368 |
| USB2_EP0OUTDATA_W10 | `0x168` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1369 |
| USB2_EP0OUTDATA_W11 | `0x16c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1370 |
| USB2_EP0OUTDATA_W12 | `0x170` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1371 |
| USB2_EP0OUTDATA_W13 | `0x174` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1372 |
| USB2_EP0OUTDATA_W14 | `0x178` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1373 |
| USB2_EP0OUTDATA_W15 | `0x17c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1374 |
| USB2_SETUPDATA_W0 | `0x180` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1375 |
| USB2_SETUPDATA_W1 | `0x184` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1376 |
| USB2_INXIRQ | `0x188` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1377 |
| USB2_OUTXIRQ | `0x18a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1378 |
| USB2_USBIRQ | `0x18c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1379 |
| USB2_OUTXPNGIRQ | `0x18e` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1380 |
| USB2_INXIEN | `0x194` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1381 |
| USB2_OUTXIEN | `0x196` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1382 |
| USB2_USBIEN | `0x198` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1383 |
| USB2_OUTXPNGIEN | `0x19a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1384 |
| USB2_INXTOKIRQ | `0x190` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1385 |
| USB2_OUTXTOKIRQ | `0x191` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1386 |
| USB2_INXTOKIEN | `0x19c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1387 |
| USB2_OUTXTOKIEN | `0x19d` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1388 |
| USB2_IVECT | `0x1a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1389 |
| USB2_ENDPRST | `0x1a2` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1390 |
| USB2_USBCS | `0x1a3` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1391 |
| USB2_FRMNRL | `0x1a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1392 |
| USB2_FRMNRH | `0x1a5` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1393 |
| USB2_FNADDR | `0x1a6` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1394 |
| USB2_CLKGATE | `0x1a7` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1395 |
| USB2_FIFOCTRL | `0x1a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1396 |
| USB2_OUT1STADDR | `0x304` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1397 |
| USB2_OUT2STADDR | `0x308` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1398 |
| USB2_OUT3STADDR | `0x30c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1399 |
| USB2_OUT4STADDR | `0x310` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1400 |
| USB2_OUT5STADDR | `0x314` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1401 |
| USB2_IN1STADDR | `0x344` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1402 |
| USB2_IN2STADDR | `0x348` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1403 |
| USB2_IN3STADDR | `0x34c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1404 |
| USB2_IN4STADDR | `0x350` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1405 |
| USB2_IN5STADDR | `0x354` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1406 |
| USB2_USBERESET | `0x400` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1407 |
| USB2_TA_BCON_COUNT | `0x401` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1408 |
| USB2_VBUSDBCTIMERL | `0x402` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1409 |
| USB2_VBUSDBCTIMERH | `0x403` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1410 |
| USB2_VDCTRL | `0x404` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1411 |
| USB2_VDSTATE | `0x405` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1412 |
| USB2_BKDOOR | `0x406` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1413 |
| USB2_DBGMODE | `0x407` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1414 |
| USB2_SRPCTRL | `0x408` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1415 |
| USB2_USBEIRQ | `0x40a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1416 |
| USB2_USBEIEN | `0x40c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1417 |
| USB2_UDMAIRQ | `0x40e` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1418 |
| USB2_UDMAIEN | `0x40f` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1419 |
| USB2_OUTXSHORTPCKIRQ | `0x410` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1420 |
| USB2_OUTXSHORTPCKIEN | `0x412` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1421 |
| USB2_OUTXNAKCTRL | `0x414` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1422 |
| USB2_HCINXSTART | `0x416` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1423 |
| USB2_HCINXENDIRQ | `0x418` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1424 |
| USB2_HCINXENDIEN | `0x41a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1425 |
| USB2_HCIN1CNTL | `0x420` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1426 |
| USB2_HCIN2CNTL | `0x422` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1427 |
| USB2_HCIN3CNTL | `0x424` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1428 |
| USB2_HCIN4CNTL | `0x426` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1429 |
| USB2_HCIN5CNTL | `0x428` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1430 |
| USB2_HCIN1CNTH | `0x421` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1431 |
| USB2_HCIN2CNTH | `0x423` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1432 |
| USB2_HCIN3CNTH | `0x425` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1433 |
| USB2_HCIN4CNTH | `0x427` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1434 |
| USB2_HCIN5CNTH | `0x429` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1435 |
| USB2_INXBUFEMPTYIRQ | `0x440` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1436 |
| USB2_INXBUFEMPTYIEN | `0x442` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1437 |
| USB2_INXBUFEMPTYCTRL | `0x444` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1438 |
| USB2_UDMA1MEMADDR | `0x450` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1439 |
| USB2_UDMA1EPSEL | `0x454` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1440 |
| USB2_UDMA1COM | `0x455` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1441 |
| USB2_UDMA1CNTL | `0x458` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1442 |
| USB2_UDMA1CNTM | `0x459` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1443 |
| USB2_UDMA1CNTH | `0x45a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1444 |
| USB2_UDMA1REML | `0x45c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1445 |
| USB2_UDMA1REMM | `0x45d` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1446 |
| USB2_UDMA1REMH | `0x45e` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1447 |
| USB2_UDMA2MEMADDR | `0x460` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1448 |
| USB2_UDMA2EPSEL | `0x464` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1449 |
| USB2_UDMA2COM | `0x465` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1450 |
| USB2_UDMA2CNTL | `0x468` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1451 |
| USB2_UDMA2CNTM | `0x469` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1452 |
| USB2_UDMA2CNTH | `0x46a` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1453 |
| USB2_UDMA2REML | `0x46c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1454 |
| USB2_UDMA2REMM | `0x46d` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1455 |
| USB2_UDMA2REMH | `0x46e` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1456 |

## candidate:ETHERNET_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1461

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| MAC_CSR0 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1462 |
| MAC_CSR1 | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1463 |
| MAC_CSR2 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1464 |
| MAC_CSR3 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1465 |
| MAC_CSR4 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1466 |
| MAC_CSR5 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1467 |
| MAC_CSR6 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1468 |
| MAC_CSR7 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1469 |
| MAC_CSR8 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1470 |
| MAC_CSR9 | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1471 |
| MAC_CSR10 | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1472 |
| MAC_CSR11 | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1473 |
| MAC_CSR16 | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1474 |
| MAC_CSR17 | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1475 |
| MAC_CSR18 | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1476 |
| MAC_CSR19 | `0x98` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1477 |
| MAC_CSR20 | `0xa0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1478 |
| SC0 | `0x200` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1479 |
| SC1 | `0x204` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1480 |
| SC2 | `0x208` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1481 |
| SC3 | `0x20c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1482 |
| SC4 | `0x210` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1483 |
| SC5 | `0x214` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1484 |
| SC6 | `0x218` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1485 |
| SC7 | `0x21c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1486 |
| SC8 | `0x220` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1487 |
| SC9 | `0x224` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1488 |
| SC10 | `0x228` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1489 |
| SC11 | `0x22c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1490 |
| SC12 | `0x230` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1491 |
| SC13 | `0x234` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1492 |
| SC14 | `0x238` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1493 |
| SC15 | `0x23c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1494 |
| SC16 | `0x240` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1495 |
| SC17 | `0x244` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1496 |
| SC18 | `0x248` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1497 |
| SC19 | `0x24c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1498 |
| SC20 | `0x250` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1499 |
| SC21 | `0x254` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1500 |
| SC22 | `0x258` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1501 |
| SC23 | `0x25c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1502 |
| SC24 | `0x260` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1503 |
| SC25 | `0x264` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1504 |
| SC26 | `0x268` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1505 |
| SC27 | `0x26c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1506 |
| SC28 | `0x270` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1507 |
| SC29 | `0x274` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1508 |
| SC30 | `0x278` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1509 |
| SC31 | `0x27c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1510 |
| SC32 | `0x280` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1511 |
| SC33 | `0x284` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1512 |
| SC34 | `0x288` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1513 |
| SC35 | `0x28c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1514 |
| SC36 | `0x290` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1515 |
| SC37 | `0x294` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1516 |
| SC38 | `0x298` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1517 |
| SC39 | `0x29c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1518 |
| SC40 | `0x2a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1519 |
| SC41 | `0x2a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1520 |
| SC42 | `0x2a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1521 |
| SC43 | `0x2ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1522 |
| SC44 | `0x2b0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1523 |
| SC45 | `0x2b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1524 |
| SC46 | `0x2b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1525 |
| SC47 | `0x2bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1526 |
| SC48 | `0x2c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1527 |
| SC49 | `0x2c4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1528 |
| SC50 | `0x2c8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1529 |
| SC51 | `0x2cc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1530 |
| SC52 | `0x2d0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1531 |
| SC53 | `0x2d4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1532 |
| SC54 | `0x2d8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1533 |
| SC55 | `0x2dc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1534 |
| SC56 | `0x2e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1535 |
| SC57 | `0x2e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1536 |
| SC58 | `0x2e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1537 |
| SC59 | `0x2ec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1538 |
| SC60 | `0x2f0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1539 |
| SC61 | `0x2f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1540 |
| SC62 | `0x2f8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1541 |
| SC63 | `0x2fc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1542 |
| SC64 | `0x300` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1543 |
| SC65 | `0x304` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1544 |
| SC66 | `0x308` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1545 |
| SC67 | `0x30c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1546 |
| SC68 | `0x310` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1547 |
| SC69 | `0x314` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1548 |
| SC70 | `0x318` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1549 |
| SC71 | `0x31c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1550 |
| SC72 | `0x320` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1551 |
| SC73 | `0x324` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1552 |
| SC74 | `0x328` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1553 |
| SC75 | `0x32c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1554 |
| SC76 | `0x330` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1555 |
| SC77 | `0x334` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1556 |
| SC78 | `0x338` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1557 |
| SC79 | `0x33c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1558 |
| SC80 | `0x340` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1559 |
| SC81 | `0x344` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1560 |
| SC82 | `0x348` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1561 |
| SC83 | `0x34c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1562 |
| SC84 | `0x350` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1563 |
| SC85 | `0x354` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1564 |
| SC86 | `0x358` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1565 |
| SC87 | `0x35c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1566 |
| SC88 | `0x360` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1567 |
| SC89 | `0x364` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1568 |
| SC90 | `0x368` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1569 |
| SC91 | `0x36c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1570 |
| SC92 | `0x370` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1571 |
| SC93 | `0x374` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1572 |
| SC94 | `0x378` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1573 |
| SC95 | `0x37c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1574 |
| SC96 | `0x380` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1575 |
| SC97 | `0x384` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1576 |
| SC98 | `0x388` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1577 |
| SC99 | `0x38c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1578 |
| SC100 | `0x390` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1579 |
| SC101 | `0x394` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1580 |
| SC102 | `0x398` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1581 |
| SC103 | `0x39c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1582 |
| SC104 | `0x3a0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1583 |
| SC105 | `0x3a4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1584 |
| SC106 | `0x3a8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1585 |
| SC107 | `0x3ac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1586 |
| SC108 | `0x3b0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1587 |
| SC109 | `0x3b4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1588 |
| SC110 | `0x3b8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1589 |
| SC111 | `0x3bc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1590 |
| SC112 | `0x3c0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1591 |
| SC113 | `0x3c4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1592 |
| SC114 | `0x3c8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1593 |
| SC115 | `0x3cc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1594 |
| SC116 | `0x3d0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1595 |
| SC117 | `0x3d4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1596 |
| SC118 | `0x3d8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1597 |
| SC119 | `0x3dc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1598 |
| SC120 | `0x3e0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1599 |
| SC121 | `0x3e4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1600 |
| SC122 | `0x3e8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1601 |
| SC123 | `0x3ec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1602 |
| SC124 | `0x3f0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1603 |
| SC125 | `0x3f4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1604 |
| SC126 | `0x3f8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1605 |
| MAC_CTRL | `0xb0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1606 |

## candidate:SPI0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1611

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SPI0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1612 |
| SPI0_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1613 |
| SPI0_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1614 |
| SPI0_RXDAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1615 |
| SPI0_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1616 |
| SPI0_TCNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1617 |
| SPI0_SEED | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1618 |
| SPI0_TXCR | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1619 |
| SPI0_RXCR | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1620 |

## candidate:SPI1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1625

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SPI1_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1626 |
| SPI1_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1627 |
| SPI1_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1628 |
| SPI1_RXDAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1629 |
| SPI1_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1630 |
| SPI1_TCNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1631 |
| SPI1_SEED | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1632 |
| SPI1_TXCR | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1633 |
| SPI1_RXCR | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1634 |

## candidate:SPI2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1639

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SPI2_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1640 |
| SPI2_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1641 |
| SPI2_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1642 |
| SPI2_RXDAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1643 |
| SPI2_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1644 |
| SPI2_TCNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1645 |
| SPI2_SEED | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1646 |
| SPI2_TXCR | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1647 |
| SPI2_RXCR | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1648 |

## candidate:SPI3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1653

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| SPI3_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1654 |
| SPI3_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1655 |
| SPI3_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1656 |
| SPI3_RXDAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1657 |
| SPI3_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1658 |
| SPI3_TCNT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1659 |
| SPI3_SEED | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1660 |
| SPI3_TXCR | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1661 |
| SPI3_RXCR | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1662 |

## candidate:UART0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1667

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1668 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART0_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1669 |
| UART0_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1670 |
| UART0_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1671 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:UART1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1676

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART1_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1677 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART1_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1678 |
| UART1_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1679 |
| UART1_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1680 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:UART2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1685

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART2_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1686 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART2_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1687 |
| UART2_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1688 |
| UART2_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1689 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:UART3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1694

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART3_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1695 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART3_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1696 |
| UART3_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1697 |
| UART3_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1698 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:UART4_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1703

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART4_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1704 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART4_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1705 |
| UART4_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1706 |
| UART4_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1707 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:UART5_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1712

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART5_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1713 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART5_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1714 |
| UART5_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1715 |
| UART5_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1716 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:UART6_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1721

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| UART6_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1722 |
| ↳ OWL_UART_CTL_DWLS_MASK | mask `0x3` | — | unknown on target | unknown | inferred / S500-source | 32 |
| ↳ OWL_UART_CTL_STPS_2BITS | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 37 |
| ↳ OWL_UART_CTL_PRS_MASK | mask `0x70` | — | unknown on target | unknown | inferred / S500-source | 38 |
| ↳ OWL_UART_CTL_AFE | mask `0x1000` | — | unknown on target | unknown | inferred / S500-source | 44 |
| ↳ OWL_UART_CTL_TRFS_TX | mask `0x4000` | — | unknown on target | unknown | inferred / S500-source | 45 |
| ↳ OWL_UART_CTL_EN | mask `0x8000` | — | unknown on target | unknown | inferred / S500-source | 46 |
| ↳ OWL_UART_CTL_RXDE | mask `0x10000` | — | unknown on target | unknown | inferred / S500-source | 47 |
| ↳ OWL_UART_CTL_TXDE | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 48 |
| ↳ OWL_UART_CTL_RXIE | mask `0x40000` | — | unknown on target | unknown | inferred / S500-source | 49 |
| ↳ OWL_UART_CTL_TXIE | mask `0x80000` | — | unknown on target | unknown | inferred / S500-source | 50 |
| ↳ OWL_UART_CTL_LBEN | mask `0x100000` | — | unknown on target | unknown | inferred / S500-source | 51 |
| UART6_RXDAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1723 |
| UART6_TXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1724 |
| UART6_STAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1725 |
| ↳ OWL_UART_STAT_RIP | mask `0x1` | — | unknown on target | unknown | inferred / S500-source | 53 |
| ↳ OWL_UART_STAT_TIP | mask `0x2` | — | unknown on target | unknown | inferred / S500-source | 54 |
| ↳ OWL_UART_STAT_RXER | mask `0x4` | — | unknown on target | unknown | inferred / S500-source | 55 |
| ↳ OWL_UART_STAT_TFER | mask `0x8` | — | unknown on target | unknown | inferred / S500-source | 56 |
| ↳ OWL_UART_STAT_RXST | mask `0x10` | — | unknown on target | unknown | inferred / S500-source | 57 |
| ↳ OWL_UART_STAT_RFEM | mask `0x20` | — | unknown on target | unknown | inferred / S500-source | 58 |
| ↳ OWL_UART_STAT_TFFU | mask `0x40` | — | unknown on target | unknown | inferred / S500-source | 59 |
| ↳ OWL_UART_STAT_CTSS | mask `0x80` | — | unknown on target | unknown | inferred / S500-source | 60 |
| ↳ OWL_UART_STAT_RTSS | mask `0x100` | — | unknown on target | unknown | inferred / S500-source | 61 |
| ↳ OWL_UART_STAT_TFES | mask `0x400` | — | unknown on target | unknown | inferred / S500-source | 62 |
| ↳ OWL_UART_STAT_TRFL_MASK | mask `0x1f800` | — | unknown on target | unknown | inferred / S500-source | 63 |
| ↳ OWL_UART_STAT_UTBB | mask `0x20000` | — | unknown on target | unknown | inferred / S500-source | 64 |

## candidate:IRC_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1730

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| IR_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1731 |
| IR_STAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1732 |
| IR_CC | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1733 |
| IR_KDC | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1734 |
| IR_TCOUNTER | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1735 |
| IR_RCC | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1736 |

## candidate:I2C0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1741

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| I2C0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1742 |
| I2C0_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1743 |
| I2C0_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1744 |
| I2C0_ADDR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1745 |
| I2C0_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1746 |
| I2C0_RXDAT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1747 |
| I2C0_CMD | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1748 |
| I2C0_FIFOCTL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1749 |
| I2C0_FIFOSTAT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1750 |
| I2C0_DATCNT | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1751 |
| I2C0_RCNT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1752 |

## candidate:I2C1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1757

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| I2C1_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1758 |
| I2C1_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1759 |
| I2C1_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1760 |
| I2C1_ADDR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1761 |
| I2C1_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1762 |
| I2C1_RXDAT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1763 |
| I2C1_CMD | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1764 |
| I2C1_FIFOCTL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1765 |
| I2C1_FIFOSTAT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1766 |
| I2C1_DATCNT | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1767 |
| I2C1_RCNT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1768 |

## candidate:I2C2_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1773

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| I2C2_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1774 |
| I2C2_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1775 |
| I2C2_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1776 |
| I2C2_ADDR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1777 |
| I2C2_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1778 |
| I2C2_RXDAT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1779 |
| I2C2_CMD | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1780 |
| I2C2_FIFOCTL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1781 |
| I2C2_FIFOSTAT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1782 |
| I2C2_DATCNT | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1783 |
| I2C2_RCNT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1784 |

## candidate:I2C3_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1789

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| I2C3_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1790 |
| I2C3_CLKDIV | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1791 |
| I2C3_STAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1792 |
| I2C3_ADDR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1793 |
| I2C3_TXDAT | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1794 |
| I2C3_RXDAT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1795 |
| I2C3_CMD | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1796 |
| I2C3_FIFOCTL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1797 |
| I2C3_FIFOSTAT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1798 |
| I2C3_DATCNT | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1799 |
| I2C3_RCNT | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1800 |

## candidate:LCD_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1805

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| LCD0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1806 |
| LCD0_SIZE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1807 |
| LCD0_STATUS | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1808 |
| LCD0_TIM0 | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1809 |
| LCD0_TIM1 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1810 |
| LCD0_TIM2 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1811 |
| LCD0_COLOR | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1812 |
| LCD0_CPU_CTL | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1813 |
| LCD0_CPU_CMD | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1814 |
| LCD0_TEST_P0 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1815 |
| LCD0_TEST_P1 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1816 |
| LCD0_IMG_XPOS | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1817 |
| LCD0_IMG_YPOS | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1818 |
| LCD1_CTL | `0x100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1819 |
| LCD1_SIZE | `0x104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1820 |
| LCD1_TIM1 | `0x108` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1821 |
| LCD1_TIM2 | `0x10c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1822 |
| LCD1_COLOR | `0x110` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1823 |
| LCD1_CPU_CTL | `0x114` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1824 |
| LCD1_CPU_CMD | `0x118` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1825 |
| LCD1_IMG_XPOS | `0x11c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1826 |
| LCD1_IMG_YPOS | `0x120` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1827 |

## candidate:LVDS_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1832

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| LVDS_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1833 |
| LVDS_ALG_CTL0 | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1834 |
| LVDS_DEBUG | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1835 |

## candidate:CSI_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1840

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| CSI_CTRL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1841 |
| SHORT_PACKET | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1842 |
| ERROR_PENDING | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1843 |
| STATUS_PENDING | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1844 |
| LANE_STATUS | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1845 |
| CSI_PHY_T0 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1846 |
| CSI_PHY_T1 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1847 |
| CSI_PHY_T2 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1848 |
| CSI_ANALOG_PHY | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1849 |
| CONTEXT0_CFG | `0x100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1850 |
| CONTEXT0_STATUS | `0x104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1851 |
| CONTEXT1_CFG | `0x120` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1852 |
| CONTEXT1_STATUS | `0x124` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1853 |
| TEST_CONTROL | `0x130` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1854 |
| TEST_DATA | `0x134` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1855 |

## candidate:DSI_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1860

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| DSI_CTRL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1861 |
| DSI_SIZE | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1862 |
| DSI_COLOR | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1863 |
| DSI_VIDEO_CFG | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1864 |
| DSI_RGBHT0 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1865 |
| DSI_RGBHT1 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1866 |
| DSI_RGBVT0 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1867 |
| DSI_RGBVT1 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1868 |
| DSI_TIMEOUT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1869 |
| DSI_TR_STA | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1870 |
| DSI_INT_EN | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1871 |
| DSI_ERROR_REPORT | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1872 |
| DSI_FIFO_ODAT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1873 |
| DSI_FIFO_IDAT | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1874 |
| DSI_IPACK | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1875 |
| DSI_PACK_CFG | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1876 |
| DSI_PACK_HEADER | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1877 |
| DSI_TX_TRIGGER | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1878 |
| DSI_RX_TRIGGER | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1879 |
| DSI_LANE_CTRL | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1880 |
| DSI_LANE_STA | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1881 |
| DSI_PHY_T0 | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1882 |
| DSI_PHY_T1 | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1883 |
| DSI_PHY_T2 | `0x68` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1884 |
| DSI_APHY_DEBUG0 | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1885 |
| DSI_APHY_DEBUG1 | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1886 |
| DSI_SELF_TEST | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1887 |
| DSI_PHY_CTRL | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1888 |
| DSI_FT_TEST | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1889 |

## candidate:TVOUT_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1894

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| TVOUT_EN | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1895 |
| TVOUT_OCR | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1896 |
| TVOUT_STA | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1897 |
| TVOUT_CCR | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1898 |
| TVOUT_BCR | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1899 |
| TVOUT_CSCR | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1900 |
| TVOUT_PRL | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1901 |
| TVOUT_VFALD | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1902 |
| CVBS_MSR | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1903 |
| CVBS_AL_SEPO | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1904 |
| CVBS_AL_SEPE | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1905 |
| CVBS_AD_SEP | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1906 |
| CVBS_HUECR | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1907 |
| CVBS_SCPCR | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1908 |
| CVBS_SCFCR | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1909 |
| CVBS_CBACR | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1910 |
| CVBS_SACR | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1911 |
| BT_MSR0 | `0x100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1912 |
| BT_MSR1 | `0x104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1913 |
| BT_AL_SEPO | `0x108` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1914 |
| BT_AL_SEPE | `0x10c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1915 |
| BT_AP_SEP | `0x110` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1916 |
| TVOUT_DCR | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1917 |
| TVOUT_DDCR | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1918 |
| TVOUT_DCORCTL | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1919 |
| TVOUT_DRCR | `0x7c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1920 |

## candidate:HDMI_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:1925

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| HDMI_VICTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1926 |
| HDMI_VIVSYNC | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1927 |
| HDMI_VIVHSYNC | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1928 |
| HDMI_VIALSEOF | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1929 |
| HDMI_VIALSEEF | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1930 |
| HDMI_VIADLSE | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1931 |
| HDMI_AIFRAMEC | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1932 |
| HDMI_AICHSTABYTE0TO3 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1933 |
| HDMI_AICHSTABYTE4TO7 | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1934 |
| HDMI_AICHSTABYTE8TO11 | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1935 |
| HDMI_AICHSTABYTE12TO15 | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1936 |
| HDMI_AICHSTABYTE16TO19 | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1937 |
| HDMI_AICHSTABYTE20TO23 | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1938 |
| HDMI_AICHSTASCN | `0x3c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1939 |
| HDMI_VR | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1940 |
| HDMI_CR | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1941 |
| HDMI_SCHCR | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1942 |
| HDMI_ICR | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1943 |
| HDMI_SCR | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1944 |
| HDMI_LPCR | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1945 |
| HDCP_CR | `0x68` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1946 |
| HDCP_SR | `0x6c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1947 |
| HDCP_ANLR | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1948 |
| HDCP_ANMR | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1949 |
| HDCP_ANILR | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1950 |
| HDCP_ANIMR | `0x7c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1951 |
| HDCP_DPKLR | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1952 |
| HDCP_DPKMR | `0x84` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1953 |
| HDCP_LIR | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1954 |
| HDCP_SHACR | `0x8c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1955 |
| HDCP_SHADR | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1956 |
| HDCP_ICR | `0x94` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1957 |
| HDCP_KMMR | `0x98` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1958 |
| HDCP_KMLR | `0x9c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1959 |
| HDCP_MILR | `0xa0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1960 |
| HDCP_MIMR | `0xa4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1961 |
| HDCP_KOWR | `0xa8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1962 |
| HDCP_OWR | `0xac` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1963 |
| TMDS_STR0 | `0xb8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1964 |
| TMDS_STR1 | `0xbc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1965 |
| TMDS_EODR0 | `0xc0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1966 |
| TMDS_EODR1 | `0xc4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1967 |
| HDMI_ASPCR | `0xd0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1968 |
| HDMI_ACACR | `0xd4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1969 |
| HDMI_ACRPCR | `0xd8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1970 |
| HDMI_ACRPCTSR | `0xdc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1971 |
| HDMI_ACRPPR | `0xe0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1972 |
| HDMI_GCPCR | `0xe4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1973 |
| HDMI_RPCR | `0xe8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1974 |
| HDMI_RPRBDR | `0xec` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1975 |
| HDMI_OPCR | `0xf0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1976 |
| HDMI_DIPCCR | `0xf4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1977 |
| HDMI_ORP6PH | `0xf8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1978 |
| HDMI_ORSP6W0 | `0xfc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1979 |
| HDMI_ORSP6W1 | `0x100` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1980 |
| HDMI_ORSP6W2 | `0x104` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1981 |
| HDMI_ORSP6W3 | `0x108` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1982 |
| HDMI_ORSP6W4 | `0x10c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1983 |
| HDMI_ORSP6W5 | `0x110` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1984 |
| HDMI_ORSP6W6 | `0x114` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1985 |
| HDMI_ORSP6W7 | `0x118` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1986 |
| HDMI_CECCR | `0x11c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1987 |
| HDMI_CECRTCR | `0x120` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1988 |
| HDMI_CECRXCR | `0x124` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1989 |
| HDMI_CECTXCR | `0x128` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1990 |
| HDMI_CECTXDR | `0x12c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1991 |
| HDMI_CECRXDR | `0x130` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1992 |
| HDMI_CECRXTCR | `0x134` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1993 |
| HDMI_CECTXTCR0 | `0x138` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1994 |
| HDMI_CECTXTCR1 | `0x13c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1995 |
| HDMI_CRCCR | `0x140` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1996 |
| HDMI_CRCDOR | `0x144` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1997 |
| HDMI_TX_1 | `0x154` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1998 |
| HDMI_TX_2 | `0x158` | unknown | unknown | unknown | inferred / related-ATM7039-header | 1999 |
| CEC_DDC_HPD | `0x15c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2000 |

## candidate:I2S_SPDIF_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:2005

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| I2S_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2006 |
| I2S_FIFOCTL | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2007 |
| I2STX_DAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2008 |
| I2SRX_DAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2009 |
| SPDIF_HDMI_CTL | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2010 |
| SPDIF_DAT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2011 |
| SPDIF_CLSTAT | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2012 |
| SPDIF_CHSTAT | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2013 |
| HDMI_DAT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2014 |
| I2STX_DAT_DBG | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2015 |
| I2SRX_DAT_DBG | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2016 |
| I2STX_SPDIF_HDMI_CTL | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2017 |
| I2STX_SPDIF_HDMI_DAT | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2018 |

## candidate:PCM0_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:2023

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| PCM0_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2024 |
| PCM0_STAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2025 |
| PCM0_RXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2026 |
| PCM0_TXDAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2027 |

## candidate:PCM1_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:2032

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| PCM1_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2033 |
| PCM1_STAT | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2034 |
| PCM1_RXDAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2035 |
| PCM1_TXDAT | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2036 |

## candidate:KEY_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:2041

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| KEY_CTL | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2042 |
| KEY_DAT0 | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2043 |
| KEY_DAT1 | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2044 |
| KEY_DAT2 | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2045 |
| KEY_DAT3 | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2046 |
| KEY_DAT4 | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2047 |
| KEY_DAT5 | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2048 |
| KEY_DAT6 | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2049 |
| KEY_DAT7 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2050 |

## candidate:LENSC_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:2055

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| ST1_MOTOR_CTL1 | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2056 |
| ST1_MOTOR_CTL2 | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2057 |
| ST1_MOTOR_SPEED | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2058 |
| ST1_MOTOR_TRDATA | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2059 |
| ST1_MOTOR_CMD_CTL | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2060 |
| ST2_MOTOR_CTL1 | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2061 |
| ST2_MOTOR_CTL2 | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2062 |
| ST2_MOTOR_SPEED | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2063 |
| ST2_MOTOR_TRDATA | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2064 |
| ST2_MOTOR_CMD_CTL | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2065 |
| ST3_MOTOR_CTL1 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2066 |
| ST3_MOTOR_CTL2 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2067 |
| ST3_MOTOR_SPEED | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2068 |
| ST3_MOTOR_TRDATA | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2069 |
| ST3_MOTOR_CMD_CTL | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2070 |
| DC_MOTOR_CTL1 | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2071 |
| DC_MOTOR_CTL2 | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2072 |
| MOTOR_MFP_CTL | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2073 |
| MOTOR_PWM_CTL | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2074 |
| MOTOR_VD_CTL | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2075 |

## candidate:GPIO_MFP_PWM_BASE

Exact symbol/offset observation in a header labelled ATM7039 Spec V1.10. Application to ATM7039S is inferred only. Header timestamp is not validated silicon chronology. Width, reset, access and semantics remain unknown unless documented separately.

Evidence: vendor-kernel:arch/arm/mach-owl/include/mach/regs_map-atm7039.h:2080

Interrupt cells (raw): `[]`. Dependencies: Unknown on ATM7039S; consult vendor clock/reset/power code before use.

| Register | Offset | Width | Access | Reset | Confidence / scope | Source line |
|---|---|---|---|---|---|---|
| GPIO_AOUTEN | `0x0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2081 |
| GPIO_AINEN | `0x4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2082 |
| GPIO_ADAT | `0x8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2083 |
| GPIO_BOUTEN | `0xc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2084 |
| GPIO_BINEN | `0x10` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2085 |
| GPIO_BDAT | `0x14` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2086 |
| GPIO_COUTEN | `0x18` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2087 |
| GPIO_CINEN | `0x1c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2088 |
| GPIO_CDAT | `0x20` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2089 |
| GPIO_DOUTEN | `0x24` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2090 |
| GPIO_DINEN | `0x28` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2091 |
| GPIO_DDAT | `0x2c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2092 |
| GPIO_EOUTEN | `0x30` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2093 |
| GPIO_EINEN | `0x34` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2094 |
| GPIO_EDAT | `0x38` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2095 |
| MFP_CTL0 | `0x40` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2096 |
| MFP_CTL1 | `0x44` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2097 |
| MFP_CTL2 | `0x48` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2098 |
| MFP_CTL3 | `0x4c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2099 |
| PWM_CTL0 | `0x50` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2100 |
| PWM_CTL1 | `0x54` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2101 |
| PWM_CTL2 | `0x58` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2102 |
| PWM_CTL3 | `0x5c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2103 |
| PWM_CTL4 | `0x78` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2104 |
| PWM_CTL5 | `0x7c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2105 |
| PAD_PULLCTL0 | `0x60` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2106 |
| PAD_PULLCTL1 | `0x64` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2107 |
| PAD_PULLCTL2 | `0x68` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2108 |
| PAD_ST0 | `0x6c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2109 |
| PAD_ST1 | `0x70` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2110 |
| PAD_CTL | `0x74` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2111 |
| SPEED_SENSOR_CTL | `0x7c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2112 |
| PAD_DRV0 | `0x80` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2113 |
| PAD_DRV1 | `0x84` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2114 |
| PAD_DRV2 | `0x88` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2115 |
| DEBUG_SEL | `0x90` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2116 |
| DEBUG_OEN0 | `0x94` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2117 |
| DEBUG_OEN1 | `0x98` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2118 |
| DEBUG_IEN0 | `0x9c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2119 |
| DEBUG_IEN1 | `0xa0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2120 |
| MEM_MARGIN_CTRL0 | `0xb0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2121 |
| MEM_MARGIN_CTRL1 | `0xb4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2122 |
| BIST_START0 | `0xc0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2123 |
| BIST_START1 | `0xc4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2124 |
| BIST_DONE0 | `0xc8` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2125 |
| BIST_DONE1 | `0xcc` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2126 |
| BIST_FAIL0 | `0xd0` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2127 |
| BIST_FAIL1 | `0xd4` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2128 |
| INTC_EXTCTL | `0x200` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2129 |
| INTC_GPIOCTL | `0x204` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2130 |
| INTC_GPIOA_PD | `0x208` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2131 |
| INTC_GPIOA_MSK | `0x20c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2132 |
| INTC_GPIOB_PD | `0x210` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2133 |
| INTC_GPIOB_MSK | `0x214` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2134 |
| INTC_GPIOC_PD | `0x218` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2135 |
| INTC_GPIOC_MSK | `0x21c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2136 |
| INTC_GPIOD_PD | `0x220` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2137 |
| INTC_GPIOD_MSK | `0x224` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2138 |
| INTC_GPIOE_PD | `0x228` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2139 |
| INTC_GPIOE_MSK | `0x22c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2140 |
| INTC_GPIOA_TYPE0 | `0x230` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2141 |
| INTC_GPIOA_TYPE1 | `0x234` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2142 |
| INTC_GPIOB_TYPE0 | `0x238` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2143 |
| INTC_GPIOB_TYPE1 | `0x23c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2144 |
| INTC_GPIOC_TYPE0 | `0x240` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2145 |
| INTC_GPIOC_TYPE1 | `0x244` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2146 |
| INTC_GPIOD_TYPE0 | `0x248` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2147 |
| INTC_GPIOD_TYPE1 | `0x24c` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2148 |
| INTC_GPIOE_TYPE | `0x250` | unknown | unknown | unknown | inferred / related-ATM7039-header | 2149 |
