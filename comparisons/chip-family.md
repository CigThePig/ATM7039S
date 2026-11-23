# Chip-family comparison and compatibility boundaries

Source keys resolve in the [catalogue](../evidence/catalogue.md). Confidence applies to the stated observation, never automatically to ATM7039S compatibility.

| Name | Directly inspected evidence | CPU / graphics evidence | Relationship to target | Confidence / limitation |
|---|---|---|---|---|
| ATM7039S | Actions 2015 Form 20-F product row | Quad CPU, SGX544; 32-bit DDR, BGA359, 28nm; introduced Dec 2014 | Target commercial name | Verified manufacturer statement; core revision and board implementation unmeasured |
| ATM7039 | 2013 launch + 2013/2015 filings; vendor header | Launch names quad Cortex-A9; later filing SGX544/64-bit DDR/BGA544 | Related source register candidate | Product family relation supported; register identity unproved |
| ATM7039C | RG35XX GPU compatible string | `actions,atm7039c-gpu` | Driver selector only | No authenticated separate silicon specification examined |
| ATM7059A / GS705A | RG35XX root and peripheral compatible strings | A9 nodes in board software | Vendor software ancestry/driver ABI | No proven silicon alias; do not rename target |
| ATM7059 | 2015 manufacturer product row | Quad CPU, SGX544; different package from S variant | Commercial comparison | Product row not proof ATM7059A equals ATM7039S |
| S500 | Mainline v6.12 DTS/drivers; vendor kernel/U-Boot | Four A9 nodes; manufacturer lists SGX544 | Strongest programming-layout comparison | Selected matching blocks only; not whole-chip equivalence |
| S700 | Mainline `s700.dtsi` and driver variant tables | Four Cortex-A53 nodes | Owl driver family | Different CPU architecture/variant tables; reuse per block |
| S900 | Mainline `s900.dtsi`; manufacturer filing | Four A53 nodes in DTS; G6230 in product row | Owl driver family | Different CPU/GPU generation; not SGX evidence |

Manufacturer specifications are capabilities/marketing data; they do not set safe operating parameters for the handheld. Published dates differ between announcement and shipment/product-table introduction. Preserve that distinction.

## Automated layout comparison

`rg35xx-vs-mainline-s500.json` contains 26 matching numeric-base resource pairs. That includes auxiliary resources and empty interrupt lists, so **26 does not mean 26 compatible peripherals**. It preserves differing sizes and interrupt tuples. Both trees use identity root/SOC address context for the compared root resources; the general tool intentionally does not perform bus translations.

Strong candidates include UART0–6, I2C0–3, MMC0–2, GIC, PL310, GPIO/SIRQ and DMA. A source-code offset comparison additionally supports selected CMU relationships. Candidate compatibility must still establish clocks, resets, bus attributes, power, pinmux, DMA request IDs and runtime behavior.

Counterexamples matter: the RG35XX vendor watchdog resource begins where mainline's private timer begins; CMU also appears as an auxiliary NAND/watchdog resource. GPU OMAP fallback constants are inactive in the dynamic resource path. USB names map to conflicting bases across sources. Address equality alone cannot settle these cases.

## Compatibility record discipline

For each proposed port, record supporting/contradicting evidence, differences, required tests and confidence. `reports/linux-compatibility.md` and its JSON companion implement this discipline. No candidate in this edition is classified as hardware-confirmed ATM7039S support.
