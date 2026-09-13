# SNF Benchmarking National v1 runbook

This branch separates two production concerns:

1. **Stable national analytics now** — CMS Skilled Nursing Facility Cost Report public-use data feeds the existing metric, peer, trend, labor-cost, and client-report engine.
2. **Current/full HCRIS expansion** — raw CMS HCRIS `RPT`, `NMRC`, and `ALPHNMRC` files for CMS-2540-10 and CMS-2540-24 are ingested separately. Worksheet coordinates are promoted into production only after they are verified.

## First national paid report

From the project root:

```r
Sys.setenv(SNF_TARGET_CCN = "465095")
source("render_national_client_report.R")
```

The report builder sets the peer universe to the full U.S., but the existing peer algorithm still compares the target primarily with facilities in the same state, rural/urban category, and bed-size band, with documented fallbacks.

## Refresh the stable public-use dataset

```r
source("run_national_v1.R")
```

The CMS Data Catalog currently exposes the curated SNF Cost Report PUF through its latest published PUF year. The code discovers available annual distributions dynamically.

## Ingest raw HCRIS current files

Raw SNF HCRIS files are large. Start with a constrained test:

```r
Sys.setenv(
  SNF_HCRIS_MIN_YEAR = "2024",
  SNF_HCRIS_MAX_YEAR = "2025",
  SNF_HCRIS_FORMS = "CMS-2540-24",
  SNF_HCRIS_YEARS = "2025",
  SNF_HCRIS_INCLUDE_CELLS = "true"
)
source("scripts/01_discover_raw_hcris_manifest.R")
source("scripts/01_ingest_raw_hcris.R")
source("scripts/01_build_hcris_report_inventory.R")
```

CMS raw HCRIS annual ZIP files contain a report table plus numeric and alphanumeric cell tables. The report table supplies the CCN, report status, fiscal begin/end dates and report record number. Numeric/alphanumeric cells are linked by `RPT_REC_NUM`.

## Build the 2540-10 coordinate audit

Once the overlapping 2540-10 raw files and the curated public-use file are present:

```r
source("scripts/01_infer_hcris_coordinate_candidates.R")
```

This writes `data/processed/hcris/snf_254010_coordinate_candidates.csv`. It ranks worksheet/line/column combinations whose raw HCRIS values repeatedly match selected public-use fields. **The output is not automatically trusted.** Candidate coordinates must be checked against CMS form instructions before being marked `verified` in `data/config/snf_hcris_metric_coordinates.csv`.

That verified crosswalk is the bridge to CMS-2540-24 and, later, to the other HCRIS provider forms.

## Environment variables

- `SNF_TARGET_CCN` — one facility for report rendering
- `SNF_TARGET_CCNS` — one or more comma-separated facilities for data build
- `SNF_DASHBOARD_STATE` — `UT` for legacy dashboard; `ALL` for national target builds
- `SNF_OUTPUT_PREFIX` — defaults to `utah`; national report build uses `national`
- `SNF_HCRIS_MIN_YEAR` / `SNF_HCRIS_MAX_YEAR` — raw HCRIS discovery range
- `SNF_HCRIS_FORMS` — e.g. `CMS-2540-10,CMS-2540-24`
- `SNF_HCRIS_YEARS` — comma-separated raw download years
- `SNF_HCRIS_INCLUDE_CELLS` — set false for report-table-only inventory testing
- `SNF_HCRIS_REFRESH` — force redownload of raw ZIPs

## Data that must stay out of Git

Do not commit raw CMS ZIPs, raw/processed RDS or Parquet files, rendered outputs, `.env`, `.Renviron`, AWS credentials, API keys, or private keys.
