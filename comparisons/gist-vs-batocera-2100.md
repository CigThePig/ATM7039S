# Gist versus published 2100mAh GPU DTB

Properties compared as serialized bytes, ignoring line numbers, property order, and DTB offsets. This comparison does not establish independent provenance.

| Node | Changed properties |
|---|---|
| `/gpu@b0300000` | `status` |
| `/i2c@b0174000/atc2603c@65/atc260x-audio` | `earphone_detect2_gpios` |
| `/i2c@b0174000/atc2603c@65/atc260x-cap-gauge` | `ocv_soc_00`, `ocv_soc_10`, `ocv_soc_20`, `ocv_soc_30`, `ocv_soc_40`, `ocv_soc_50`, `ocv_soc_60`, `ocv_soc_70`, `ocv_soc_80`, `ocv_soc_90`, `terminal_voltage` |
| `/i2c@b0174000/atc2603c@65/atc260x-power` | `boot_cap_threshold`, `charger_led2_ctl`, `charger_led_ctl`, `inner_charger_led_ctl`, `low_power_led2_ctl`, `work_led2_ctl` |
| `/lcd0@b02a0000` | `lcd_spics2_gpios` |
| `/monitor` | `vbus_otg_en_gpios` |
| `/usb@b0600000` | `port0_host_plug_detect` |
| `/usb@b0700000` | `port1_host_plug_detect` |
| `/wifi_bt_power_ctl` | `status` |
