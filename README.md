# SNF HCRIS Pipeline v0.1

Patch note: v0.1 updates the CMS date parser so fiscal-year begin/end dates can parse ISO dates, M/D/Y dates, timestamps, abbreviated month dates, and occasional Excel serial dates.

# SNF HCRIS Analytic Pipeline Prototype

This is the first-pass analytic pipeline for Skilled Nursing Facility cost report analytics.
It is designed to create a clean, longitudinal facility-year table from CMS SNF Cost Report public-use files and produce an initial Utah validation benchmark.

## What this does

1. Reads the CMS `data.json` catalog.
2. Finds the `Skilled Nursing Facility Cost Report` dataset.
3. Pulls yearly CSV distributions, defaulting to 2011 onward.
4. Cleans names, dates, and numeric-looking fields.
5. Creates a first-pass SNF facility-year metric table.
6. Produces a Utah target-facility peer comparison and trend plots.

## Files

- `00_setup_packages.R` — installs required R packages.
- `01_pull_clean_snf_cost_reports.R` — pulls and cleans CMS SNF cost report data.
- `02_create_snf_metric_table.R` — calculates first-pass analytic metrics.
- `03_validate_utah_snf_metrics.R` — creates a Utah validation benchmark and trend plots.
- `run_all.R` — convenience script to run all steps.
- `R/snf_api_helpers.R` — CMS API/catalog helper functions.
- `R/snf_clean_helpers.R` — cleaning, column resolution, and metric helper functions.
- `metric_dictionary_snf_v0.csv` — first-pass metric definitions.

## Recommended first run

Open R or RStudio in this project folder and run:

```r
source("00_setup_packages.R")
source("01_pull_clean_snf_cost_reports.R")
source("02_create_snf_metric_table.R")
source("03_validate_utah_snf_metrics.R")
```

Or run everything with:

```r
source("run_all.R")
```

## Optional environment variables

You can set these before running the scripts:

```r
Sys.setenv(SNF_MIN_YEAR = "2011")
Sys.setenv(SNF_MAX_YEAR = "2023")
Sys.setenv(SNF_VALIDATE_STATE = "UT")
Sys.setenv(SNF_TARGET_CCN = "")
```

For a faster smoke test, pull only one year:

```r
Sys.setenv(SNF_MIN_YEAR = "2023")
Sys.setenv(SNF_MAX_YEAR = "2023")
source("01_pull_clean_snf_cost_reports.R")
source("02_create_snf_metric_table.R")
source("03_validate_utah_snf_metrics.R")
```

## What to verify after running Step 1

Check these files:

- `data/raw/snf_cms_manifest.csv`
- `data/processed/snf_rows_by_source_year.csv`
- `data/processed/snf_column_audit.csv`
- `data/processed/snf_cost_reports_clean.rds`
- `data/processed/snf_cost_reports_clean_sample_1000_rows.csv`

You are looking for:

1. Rows were pulled for each expected year.
2. The row count by year looks plausible and does not have obvious missing years.
3. Fiscal date fields parsed correctly.
4. Important columns exist in the column audit, especially CCN, facility name, state, beds, days, revenue, expense, and cost fields.

## What to verify after running Step 2

Check these files:

- `data/processed/snf_metric_resolved_columns.csv`
- `data/processed/snf_metric_summary.csv`
- `data/processed/snf_facility_year_metrics.rds`
- `data/processed/snf_facility_year_metrics_sample_5000_rows.csv`

The most important file is `snf_metric_resolved_columns.csv`.
If a field has `found = FALSE`, the script could not confidently map it to the CMS column names.
That is not necessarily a failure; it tells us which aliases need to be adjusted after seeing the real data.

## What to verify after running Step 3

Check these files:

- `outputs/validation/utah_validation_summary.txt`
- `outputs/validation/utah_target_peer_benchmark.csv`
- `outputs/validation/trend_occupancy_rate.png`
- `outputs/validation/trend_medicare_day_share.png`
- `outputs/validation/trend_medicaid_day_share.png`
- `outputs/validation/trend_net_patient_revenue_per_day.png`
- `outputs/validation/trend_cost_per_day.png`
- `outputs/validation/trend_patient_service_margin.png`
- `outputs/validation/trend_contract_labor_ratio.png`
- `outputs/validation/trend_days_cash_on_hand.png`

You should verify:

1. The selected target facility is a real Utah SNF.
2. The peer count is reasonable.
3. Occupancy values generally fall between 0% and 100%, allowing occasional odd cost-report outliers.
4. Revenue/day and cost/day are not wildly nonsensical for most facilities.
5. Trend plots show sensible year-to-year patterns.

## Expected first issues

Expect some column mappings to need adjustment after the first real run. CMS field names sometimes differ from intuitive names. The script writes `snf_metric_resolved_columns.csv` specifically so we can inspect and update aliases quickly.

## Next development step

After this runs cleanly, the next step is to turn the metric table into a small Shiny prototype with:

1. Facility selector
2. Peer group controls
3. Benchmark snapshot table
4. Longitudinal trend tab
5. Strategy flags


## v0.2 notes

This version adds `snf_data_quality_flag_counts.csv`, `valid_core_benchmark`, and `total_margin`. The validation benchmark now uses `operating_expense_per_day` as the preferred cost/expense trend metric and keeps `reported_costs_per_day` for audit. `net_margin` remains in the analytic table but is not used in the default benchmark because `total_income` can produce misleading 100% ratios in some PUF rows.


## v0.4 note

This version adds report-period diagnostics:

- `data/processed/snf_report_period_diagnostics.csv`
- `data/processed/snf_report_period_problem_sample.csv`

It also separates core denominator/data-quality problems from report-period warnings. Liquidity/day metrics now use actual `report_days` when the period is plausible (300–430 days) and a 365-day fallback when the report period is missing or suspicious. Rows using the fallback are flagged with `used_365_day_rate_fallback` so these can be reviewed before final dashboard production.


## v0.4 note

This version fixes CMS CSV date parsing for U.S. `m/d/Y` fiscal-year fields such as `10/01/2022`. Earlier versions could misread those as year-first dates and create unrealistic report periods.

# Static Quarto Dashboard Prototype

This v0.5 package adds the first static Quarto dashboard prototype for Utah SNF strategic benchmarking.

## New files

| File | Purpose |
|---|---|
| `04_setup_dashboard_packages.R` | Installs packages needed to render the dashboard |
| `04_prepare_dashboard_data.R` | Creates a smaller Utah dashboard extract from the full metric table |
| `dashboard_snf_utah.qmd` | Static Quarto dashboard prototype |
| `_quarto.yml` | Quarto website/project configuration |
| `render_dashboard.R` | One-command dashboard render helper |

## Required input

Before rendering the dashboard, make sure this file exists:

```text
data/processed/snf_facility_year_metrics.rds
```

You created this file by running the full longitudinal pipeline through Step 2.

## First dashboard render

In RStudio, from the project root:

```r
source("04_setup_dashboard_packages.R")
source("04_prepare_dashboard_data.R")
quarto::quarto_render("dashboard_snf_utah.qmd")
```

The rendered static dashboard should appear under:

```text
outputs/dashboard_site/
```

## Render a specific facility

To render the dashboard for a specific CCN:

```r
quarto::quarto_render(
  "dashboard_snf_utah.qmd",
  execute_params = list(target_ccn = "465095")
)
```

Or set the environment variable and use the helper:

```r
Sys.setenv(SNF_TARGET_CCN = "465095")
source("render_dashboard.R")
```

## Important static-dashboard limitation

This is a static dashboard. The facility target is selected at render time, not by server-side Shiny logic after the page is published. The dashboard includes a searchable facility index so you can choose another CCN, re-render the HTML, and publish the updated static file.

A later version can add more browser-side JavaScript interactivity, but this version is intentionally simple and reliable.

## v0.6 dashboard/report additions

See `README_DASHBOARD_V0_6.md`.

Quick test:

```r
source("05_setup_dashboard_packages.R")
source("05_prepare_selector_data.R")
quarto::quarto_render("dashboard_snf_utah_selector.qmd")
quarto::quarto_render("client_report_snf_facility.qmd", execute_params = list(target_ccn = "465095"))
```


## v0.7 local dashboard fix

The Utah selector dashboard now inlines the dashboard JSON data into the rendered HTML. This fixes the issue where opening the HTML locally showed an empty dropdown and empty tabs because browser-side `fetch()` could not load local JSON files.

Render with:

```r
source("05_setup_dashboard_packages.R")
source("05_prepare_selector_data.R")
quarto::quarto_render("dashboard_snf_utah_selector.qmd")
browseURL("outputs/dashboard_site/dashboard_snf_utah_selector.html")
```


## v0.9 note

The website navigation now shows only the Utah Explorer and Client Report Template. To make the explorer open a polished client report for the selected facility in a fully static site, run `source("render_all_client_reports.R")` after preparing the selector data. This pre-renders one HTML report per Utah facility.


Additional patch notes: `README_DASHBOARD_V0_10.md`.

## v0.12 note

This version fixes the `ensure_packages()` setup error by sourcing `R/snf_api_helpers.R` inside `05_setup_dashboard_packages.R`.


## v0.12 note

Use `README_DASHBOARD_V0_12.md` for the patched client-report batch renderer. Render one report first with `SNF_REPORT_CCNS = "465095"`, then render all reports.


## v0.13 note

See `README_DASHBOARD_V0_13.md` for static navigation fixes between the Utah Explorer and pre-rendered client reports.


## v0.14 note

The Utah Explorer now includes a prominent `Open pre-rendered report` button in the main Facility snapshot panel, not only in the dashboard sidebar. This is easier to see and should avoid confusion if the sidebar controls are compressed or below the fold.

## v0.16 note

v0.16 cleans up the Utah Explorer Profile tab layout only. You do not need to rerender all client reports unless you want report-template changes or need the report files present in this folder.


## v0.17 note

This version fixes the Explorer sidebar overlay issue by reserving a left-column space for the main dashboard sections. No client report rerender is required for testing the Explorer layout.

## v0.18 note

The Utah Explorer now uses a custom fixed sidebar instead of Quarto's built-in sidebar to prevent sidebar overlap with the main dashboard content.


## v0.22 note

This version fixes the excessive gap between the custom sidebar and the main Explorer content. It is an Explorer-only layout patch; client reports do not need to be regenerated.


## v0.22 note

Benchmark tab peer group box is now forced above the table rather than appearing as a side panel. No client report rerender is needed.


## v0.22

Trends tab cleanup: one larger peer-comparison trend chart with payer-mix metrics included in the selector. The separate target-only payer mix chart was removed.

## v0.23

Trend chart now draws the target facility line only for valid target report years, while leaving peer median/IQR visible across the full period.



## v0.25

The Trends tab now uses internal tabs for `Chart` and `Metric explanation`, so the chart is not pushed down by long metric-definition text.

## v0.24

Adds metric definitions and interpretation guidance to the Benchmark and Trends tabs. Run `05_prepare_selector_data.R` again so the expanded metric dictionary is written to JSON, then render the Explorer. Client reports do not need to be rerendered for this change.


## v0.26

- Forces Trends tab internal buttons (`Chart` and `Metric explanation`) to display side by side.
- Explorer-only patch; no report rerender needed.


## Latest layout note

v0.29 widens and compacts the Facility index table so all columns are visible on desktop screens.


## v0.29

Facility index now supports per-column search/filtering and click-to-sort column headers.

## v0.30

Facility index enhancement:
- Added Urban/rural column.
- Added Urban/rural dropdown filter.
- No client report rerender needed.


## v0.31 notes

- Facility index tab now uses full width without the target-facility sidebar.
- Benchmark tab now has internal `Table` and `Metric explanation` tabs.
- Client reports do not need to be rerendered for this Explorer-only layout change.


## v0.32 update

Facility index tab now hides the custom left sidebar using robust tab-state detection. No client report rerender needed.


## v0.33 update

- Moves the **Open pre-rendered report** button into the left sidebar under the existing data notes.
- Removes the report button from the Profile tab body.
- No client report rerender needed.


## v0.34

Removed the client report pre-rendered notice/back button; top navigation remains.

## v0.37 portfolio demo note

Use `99_render_portfolio_demo_release.R` to create a public portfolio version limited to a small, diverse set of demo facilities. The demo facilities remain benchmarked against the full Utah peer population, but only the selected facilities appear in the public selector and only those client reports are rendered/copied.


## v0.38 deployment patch

Fixes the portfolio copy step for the public demo release script and removes a harmless facility-selection warning.


## v0.39 deployment styling note

The Explorer dashboard is rendered with embedded resources so the public portfolio deployment keeps the Quarto dashboard header and navigation styling.


## v0.40

Added CMS HCRIS source notes to the Explorer sidebar and to the bottom of each pre-rendered facility report.
# snfbenchmarking
