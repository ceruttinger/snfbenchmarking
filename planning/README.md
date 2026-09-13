# SNF Benchmarking Product Planning

This folder contains the implementation specifications for converting the existing Utah prototype into a national commercial SNF intelligence product.

## Current planning documents

- `NATIONAL_SNF_V1_PRODUCT_SPEC.md` — customers, product tiers, report definition, differentiation, peer/AI rules
- `NATIONAL_SNF_V1_ARCHITECTURE.md` — data architecture, AWS phases, canonical HCRIS model, serving/report strategy
- `NATIONAL_SNF_V1_DATA_SOURCES.md` — initial CMS/HCRIS/PBJ/VBP/quality source inventory and ingestion order
- `NATIONAL_SNF_V1_IMPLEMENTATION_ROADMAP.md` — milestones from source recovery through first paid report and SaaS

## Immediate development dependency

The GitHub repository currently contains generated `docs/` output and the project README, but the R/Quarto source files described by the README are not present in the remote repository.

Before core refactoring:

1. commit the current local R, QMD, helper, metric-dictionary, and build/render files as-is;
2. do not commit large raw or processed CMS datasets;
3. verify the current Utah build can still be reproduced from the committed source;
4. only then begin repository restructuring and nationalization.

This avoids recreating or guessing at code that already works locally.
