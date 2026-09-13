# run_national_v1.R
# One-command national SNF v1 build.
# Core public-use metrics remain the stable production source while raw HCRIS
# 2540-10/2540-24 is ingested and coordinate mappings are verified.

source("00_setup_packages.R")
source("01_pull_clean_snf_cost_reports.R")
source("02_create_snf_metric_table.R")

# Optional raw HCRIS current-year layer. This may download very large files.
if (tolower(Sys.getenv("SNF_RAW_HCRIS", unset = "false")) %in% c("1", "true", "yes", "y")) {
  source("scripts/01_discover_raw_hcris_manifest.R")
  source("scripts/01_ingest_raw_hcris.R")
  source("scripts/01_build_hcris_report_inventory.R")
}

# Build a lightweight nationwide search/index artifact without benchmarking all facilities.
source("09_build_national_facility_index.R")

# A target CCN makes this an on-demand national paid-report build.
if (nzchar(Sys.getenv("SNF_TARGET_CCNS", unset = ""))) {
  source("08_build_national_report_data.R")
} else {
  message("Base national provider-year data is ready. Set SNF_TARGET_CCNS to build target report data.")
}
