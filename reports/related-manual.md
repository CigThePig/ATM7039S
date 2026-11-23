# Related S500 manual lead

An Actions-branded **S500** document was retrieved from [this mirror](https://gzhls.at/blob/ldb/9/a/e/c/e8dd47a7e48102d05772a88a11c09fc5d86e.pdf). It identifies itself as revision 1.4, dated 2015-07-17, with 329 PDF pages. Hash and byte length are in `evidence/files.json` under `s500-pdf`.

The document contains substantial programming information, including address and boot descriptions. Its manufacturer branding is consistent with related source, but mirror provenance is not a signed authenticity guarantee. **It is not an ATM7039S manual.** No package-pin or register equivalence is assumed. Redistribution rights were not established; neither the PDF nor extracted text is committed.

Useful starting locations, using printed page numbers:

| Investigation | Printed pages |
|---|---|
| Boot/address overview | 62–65 |
| Clock/reset | 66–82 |
| Power sequencing | 83–89 |
| CPU complex | 90–93 |
| DMA/interrupts | 94–108 |
| DDR/internal-memory interfaces | 109–111 |
| SD/MMC | 114–125 |
| Graphics | 126–127 |

Future work should compare individual fields with both vendor and mainline code, recording agreements and differences. The document's scope must accompany every derived claim.
