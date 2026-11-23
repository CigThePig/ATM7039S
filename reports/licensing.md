# Source licensing and distribution audit

This repository was empty and **already public** when inspected. Its visibility was not changed. Only original explanations, tools, factual structured observations, hashes and source links are included. No third-party driver source, firmware binary, library, PDF or disassembly is committed.

| Material | Inspected licensing evidence | Treatment |
|---|---|---|
| Original tools and prose | New work in this repository | MIT; includes documentation and original arrangement of factual datasets |
| Linux v6.12 | Per-file SPDX/notices; kernel repository | Link pinned source; extract factual definitions; no copied implementation |
| Related vendor kernel | Root COPYING and individual files; heterogeneous tree | Do not assume one license covers every blob/header; preserve per-file review |
| Selected PowerVR sysconfig.c | Explicit Dual MIT/GPLv2 notice | Establishes this file's license; does not license the userspace stack |
| U-Boot source | Build recipe labels GPLv2; source license material | Reference and build instructions only; source/blob distinction retained |
| Cubieboard GPU userspace package | Build script copies/installs separate driver distribution | Redistribution rights not independently cleared; no binaries included |
| Published RG35XX DTB/module | Public repository availability; module `.modinfo` reports GPL v2 | Metadata analyzed locally; binary excluded; metadata is not proof of full compliance/source availability |
| Macromorgan gist | No explicit license established in inspected metadata | Attribution/link plus factual property extraction; original DTS excluded |
| Tinyhack article/demo | Article rights not assumed; demo includes bundled libraries | Original paraphrase and code-path references; no bundled libraries imported |
| KNULLI wiki | Published page identifies CC BY-SA 4.0 | Link and factual state description; no verbatim article republication |
| Manufacturer SEC filings/launch | Public manufacturer-origin statements | Short factual paraphrases and citations; no copied filing |
| S500 PDF mirror | Document reserves rights | No PDF/text redistribution; hash and narrow research pointers only |
| reMESA / SGX544 history | Inspected MIT license and author attribution | Link pinned source/research; no code imported; original proprietary library inputs remain separate |

The MIT grant covers this project's original contributions, not third-party intellectual property, names, source material or firmware. Factual register names/addresses are presented with provenance; this is not a declaration that any third-party package can be relicensed. Importing licensed implementation code later requires retaining its applicable notices and satisfying its terms.

Previous contributors are credited by source identity, including macromorgan, Yohanes Nugroho/Tinyhack, rg35xx-cfw contributors, KNULLI contributors, Actions, upstream Linux contributors, Imagination and Gama/reMESA. No claim of newly discovering their prior work is intended. New results here are the reproducible cross-comparison, explicit scope/contradiction model and original tools/documentation.

Remaining audit tasks: per-file notices for any proposed imported driver, actual matching firmware licenses, provenance/rights of early bootloader and GPU libraries, and any redistribution obligations for complete future release bundles. This session does not publish or endorse those binaries.
