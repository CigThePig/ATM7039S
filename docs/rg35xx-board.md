# RG35XX board configuration observations

These are property values from the public gist, not a schematic or package pinout. Numbers identify software GPIO offsets within a controller. Polarity values are preserved raw because vendor conventions and comments require review. Disabled inherited nodes are not evidence of fitted components. Findings PMIC-001, GPIO-001, LCD-001, MMC-001, GPU-001.

| Node / property | Controller | GPIO offset | Raw flag cells | Source line |
|---|---|---|---|---|
| `/i2c@b0174000/atc2603c@65/atc260x-audio` / `earphone_detect_gpios` | `/gpio@b01b0000` | `28` | `[0]` | 255 |
| `/i2c@b0174000/atc2603c@65/atc260x-audio` / `speaker_en_gpios` | `/gpio@b01b0000` | `40` | `[1]` | 255 |
| `/mmc@b0230000` / `card_detect_gpios` | `/gpio@b01b0000` | `41` | `[0]` | 602 |
| `/isp@b0270000` / `dvdd-gpios` | `/gpio@b01b0000` | `57` | `[0]` | 675 |
| `/isp@b0270000` / `pwdn-rear-gpios` | `/gpio@b01b0000` | `73` | `[0]` | 675 |
| `/isp@b0270000` / `pwdn-front-gpios` | `/gpio@b01b0000` | `70` | `[0]` | 675 |
| `/isp@b0270000` / `rear-reset-gpios` | `/gpio@b01b0000` | `114` | `[1]` | 675 |
| `/lcd0@b02a0000` / `lcd_power_gpios` | `/gpio@b01b0000` | `36` | `[0]` | 1143 |
| `/lcd0@b02a0000` / `lcd_reset_gpios` | `/gpio@b01b0000` | `35` | `[0]` | 1143 |
| `/lcd0@b02a0000` / `lcd_spics_gpios` | `/gpio@b01b0000` | `17` | `[1]` | 1143 |
| `/lcd0@b02a0000` / `lcd_spiclk_gpios` | `/gpio@b01b0000` | `120` | `[1]` | 1143 |
| `/lcd0@b02a0000` / `lcd_spidat_gpios` | `/gpio@b01b0000` | `121` | `[1]` | 1143 |
| `/monitor` / `vbus_otg_en_gpios` | `/gpio@b01b0000` | `78` | `[0]` | 1317 |
| `/matrix_keypad@0` / `row-gpios` | `/gpio@b01b0000` | `45` | `[0, 12, 46, 0]` | 1366 |
| `/matrix_keypad@0` / `col-gpios` | `/gpio@b01b0000` | `50` | `[0, 12, 51, 0, 12, 48, 0, 12, 47, 0]` | 1366 |
| `/wifi_bt_power_ctl` / `wifi_bt_power_gpios` | `/i2c@b0174000/atc2603c@65/atc260x_sgpio` | `5` | `[0]` | 1390 |
| `/wifi_bt_power_ctl` / `wifi_en_gpios` | `/gpio@b01b0000` | `90` | `[0]` | 1390 |
| `/wifi_bt_power_ctl` / `bt_en_gpios` | `/gpio@b01b0000` | `91` | `[0]` | 1390 |
| `/wifi_bt_power_ctl` / `wifi_wakeup_host_gpios` | `/gpio@b01b0000` | `115` | `[0]` | 1390 |
| `/ctp_detect` / `reset_gpios` | `/gpio@b01b0000` | `35` | `[1]` | 1424 |

Array-valued row/column GPIO properties can contain several tuples; the displayed remaining cells are deliberately raw rather than guessed. The complete properties and phandles are in `evidence/gist-tree.json`. A status omitted from a node means available by DT rules; ancestor status still controls availability. No package ball numbers are assigned.

## Board observations

`sdboot` points to MMC0; MMC0/MMC2 are marked okay and MMC1 disabled. That is not yet a physical slot label map. I2C1/0x65 contains ATC2603C functions, including audio and battery gauge. The LCD uses RGB with GPIO control properties and a 640×480 mode. Exact supply/polarity and fitted-part identities remain unmeasured.

The published GPU DTB changes nine nodes, including gauge calibration, additional headphone/panel control, USB detection and GPU status. See the [property-level comparison](../comparisons/gist-vs-batocera-2100.md). Do not apply battery-named DTBs solely by filename.

The source RG35XX DTS includes contradictory comments and duplicate LCD power properties; it is not treated as an electrically authoritative schematic. No diagnostic serial pad, connector voltage or safe probe point was established.
