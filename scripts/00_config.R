# scripts/00_config.R
# Central settings for the SNF dashboard v0.41 data-layer refactor.

source("R/snf_api_helpers.R")
source("R/snf_clean_helpers.R")

ensure_packages(c("dplyr", "tidyr", "readr", "stringr", "tibble", "purrr", "jsonlite"))

snf_v041_config <- function() {
  state_filter <- Sys.getenv("SNF_DASHBOARD_STATE", unset = "UT")
  peer_minimum <- suppressWarnings(as.integer(Sys.getenv("SNF_PEER_MINIMUM", unset = "5")))
  if (is.na(peer_minimum) || peer_minimum < 1) peer_minimum <- 5L

  list(
    state_filter = state_filter,
    peer_minimum = peer_minimum,
    project_version = "v0.41",
    processed_dir = "data/processed",
    dashboard_dir = "data/dashboard",
    config_dir = "data/config",
    provider_year_input = file.path("data/processed", "snf_facility_year_metrics.rds"),
    provider_year_output = file.path("data/processed", "snf_provider_year_public_v041.rds"),
    provider_master_output = file.path("data/processed", "snf_provider_master_v041.rds"),
    latest_valid_output = file.path("data/processed", "snf_latest_valid_reports_v041.rds"),
    metric_dictionary_config = file.path("data/config", "snf_metric_dictionary_v041.csv"),
    metric_dictionary_output = file.path("data/processed", "snf_metric_dictionary_v041.csv"),
    peer_benchmark_output = file.path("data/processed", "snf_peer_benchmarks_v041.rds"),
    peer_lookup_output = file.path("data/processed", "snf_peer_lookup_v041.rds")
  )
}

snf_v041_prepare_dirs <- function(cfg = snf_v041_config()) {
  dir.create(cfg$processed_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cfg$dashboard_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cfg$config_dir, recursive = TRUE, showWarnings = FALSE)
  invisible(cfg)
}
