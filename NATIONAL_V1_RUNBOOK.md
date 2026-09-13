# SNF Benchmarking National v1 runbook

This branch separates two production concerns:

1. **Stable national analytics now** — CMS Skilled Nursing Facility Cost Report public-use data feeds the existing metric, peer, trend, labor-cost, and commercial report engine.
2. **Current/full HCRIS expansion** — raw CMS HCRIS `RPT`, `NMRC`, and `ALPHNMRC` files for CMS-2540-10 and CMS-2540-24 are ingested separately. Worksheet coordinates are promoted into production only after they are verified.

## First national paid report

From the project root:

```r
Sys.setenv(SNF_TARGET_CCN = "465095")
source("render_national_paid_report.R")
```

If the core national metric table is already present locally, the report builder reuses it. Otherwise it refreshes the CMS public-use cost-report pipeline first.

The result is written to:

```text
outputs/national_client_reports/snf_benchmark_<CCN>.html
```

## Peer group modes

The commercial report supports three peer-selection modes. The target facility is always excluded from its own peer distribution.

### 1. Automatic matched peers

This is the default. The engine starts with same-state + same urban/rural classification + same bed-size band, then uses documented broader fallbacks when the cohort is too small.

```r
Sys.setenv(
  SNF_TARGET_CCN = "465095",
  SNF_PEER_MODE = "auto"
)
source("render_national_paid_report.R")
```

### 2. User-defined filters

Filters can be combined. Omitted filters are not applied.

```r
Sys.setenv(
  SNF_TARGET_CCN = "465095",
  SNF_PEER_MODE = "filters",
  SNF_PEER_STATES = "UT,ID,WY",
  SNF_PEER_RURAL_URBAN = "Urban",
  SNF_PEER_BED_SIZE_BANDS = "50-99,100-149",
  SNF_PEER_MIN_BEDS = "60",
  SNF_PEER_MAX_BEDS = "140"
)
source("render_national_paid_report.R")
```

Ownership/control can also be filtered using the exact values in the cost-report data:

```r
Sys.setenv(SNF_PEER_CONTROLS = "For profit")
```

### 3. Explicit facility list

Use this when a customer knows exactly which facilities they regard as competitors or comparators.

```r
Sys.setenv(
  SNF_TARGET_CCN = "465095",
  SNF_PEER_MODE = "explicit",
  SNF_PEER_CCNS = "465003,465006,465020,465049"
)
source("render_national_paid_report.R")
```

The generated report records the peer mode, peer definition, peer count, and a facility list so the benchmark can be reproduced and reviewed.

## Refresh the stable national public-use dataset and facility index

```r
source("run_national_v1.R")
```

The CMS Data Catalog exposes annual Skilled Nursing Facility Cost Report public-use distributions. The code discovers the available years dynamically instead of hard-coding a last year.

## Raw HCRIS smoke test

Raw HCRIS cell files are large. First prove manifest discovery and the report table only:

```r
Sys.setenv(
  SNF_HCRIS_MIN_YEAR = "2025",
  SNF_HCRIS_MAX_YEAR = "2025",
  SNF_HCRIS_FORMS = "CMS-2540-24",
  SNF_HCRIS_YEARS = "2025",
  SNF_HCRIS_INCLUDE_CELLS = "false"
)
source("scripts/01_discover_raw_hcris_manifest.R")
source("scripts/01_ingest_raw_hcris.R")
source("scripts/01_build_hcris_report_inventory.R")
```

After that succeeds, set `SNF_HCRIS_INCLUDE_CELLS=true` when numeric/alphanumeric cell partitions are actually needed. CMS raw HCRIS annual ZIP files contain a report table plus numeric and alphanumeric cell tables; the cell tables link to reports by `RPT_REC_NUM`.

## Build the 2540-10 coordinate audit

Once an overlapping 2540-10 raw numeric partition and the curated public-use file are present:

```r
Sys.setenv(SNF_COORDINATE_YEAR = "2024")
source("scripts/01_infer_hcris_coordinate_candidates.R")
```

This writes `data/processed/hcris/snf_254010_coordinate_candidates.csv`. It ranks worksheet/line/column combinations whose raw HCRIS values repeatedly match selected public-use fields. **The output is not automatically trusted.** Candidate coordinates must be checked against CMS form instructions before being marked `verified` in `data/config/snf_hcris_metric_coordinates.csv`.

That verified semantic crosswalk is the bridge to CMS-2540-24 and, later, to HHA, hospice, hospital, FQHC/RHC, ESRD, and other HCRIS provider forms.

## Environment variables

- `SNF_TARGET_CCN` — one facility for commercial report rendering
- `SNF_TARGET_CCNS` — one or more comma-separated facilities for data build
- `SNF_REFRESH_BASE` — force a refresh of the stable public-use metric layer
- `SNF_DASHBOARD_STATE` — `UT` for legacy dashboard; `ALL` for national target builds
- `SNF_OUTPUT_PREFIX` — defaults to `utah`; national report build uses `national`
- `SNF_PEER_MODE` — `auto`, `filters`, or `explicit`
- `SNF_PEER_CCNS` — comma-separated explicit peer CCNs
- `SNF_PEER_STATES` — comma-separated state abbreviations for filter mode
- `SNF_PEER_RURAL_URBAN` — comma-separated rural/urban classifications for filter mode
- `SNF_PEER_BED_SIZE_BANDS` — comma-separated bed-size bands for filter mode
- `SNF_PEER_CONTROLS` — comma-separated ownership/control values for filter mode
- `SNF_PEER_MIN_BEDS` / `SNF_PEER_MAX_BEDS` — optional numeric bed bounds
- `SNF_PEER_MINIMUM` — minimum cohort size used by automatic matching before falling back
- `SNF_HCRIS_MIN_YEAR` / `SNF_HCRIS_MAX_YEAR` — raw HCRIS discovery range
- `SNF_HCRIS_FORMS` — e.g. `CMS-2540-10,CMS-2540-24`
- `SNF_HCRIS_YEARS` — comma-separated raw download years
- `SNF_HCRIS_INCLUDE_CELLS` — false for report-table-only testing; true for NMRC/ALPHNMRC partitions
- `SNF_HCRIS_REFRESH` — force redownload of raw ZIPs
- `SNF_COORDINATE_YEAR` — overlapping 2540-10 year used for coordinate inference

## Data that must stay out of Git

Do not commit raw CMS ZIPs, raw/processed RDS or Parquet files, rendered outputs, `.env`, `.Renviron`, AWS credentials, API keys, or private keys.
