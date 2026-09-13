# render_national_paid_report.R
# Render the standalone commercial national SNF benchmark report.
# Usage:
#   Sys.setenv(SNF_TARGET_CCN = "465095")
#   source("render_national_paid_report.R")

source("05_setup_dashboard_packages.R")
target_ccn <- trimws(Sys.getenv("SNF_TARGET_CCN", unset = ""))
if (!nzchar(target_ccn)) stop("Set SNF_TARGET_CCN before rendering.")

metric_input <- "data/processed/snf_facility_year_metrics.rds"
refresh_base <- tolower(Sys.getenv("SNF_REFRESH_BASE", unset = "false")) %in% c("1", "true", "yes", "y")
if (!file.exists(metric_input) || refresh_base) {
  source("00_setup_packages.R")
  source("01_pull_clean_snf_cost_reports.R")
  source("02_create_snf_metric_table.R")
}

Sys.setenv(
  SNF_TARGET_CCNS = target_ccn,
  SNF_DASHBOARD_STATE = "ALL",
  SNF_OUTPUT_PREFIX = "national"
)
source("08_build_national_report_data.R")

quarto::quarto_render(
  "client_report_snf_national.qmd",
  execute_params = list(target_ccn = target_ccn, data_prefix = "national")
)

source_html <- "client_report_snf_national.html"
out_dir <- file.path("outputs", "national_client_reports")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_file <- file.path(out_dir, paste0("snf_benchmark_", target_ccn, ".html"))
if (!file.exists(source_html)) stop("Quarto completed but expected report was not found: ", source_html)
file.copy(source_html, out_file, overwrite = TRUE)
message("National paid report rendered: ", out_file)
invisible(out_file)
