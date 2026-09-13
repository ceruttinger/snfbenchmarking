# scripts/00_config.R
# Central settings for the SNF dashboard v0.41 data-layer refactor.

source("R/snf_api_helpers.R")
source("R/snf_clean_helpers.R")

ensure_packages(c("dplyr", "tidyr", "readr", "stringr", "tibble", "purrr", "jsonlite"))

snf_parse_env_list <- function(name) {
  raw <- Sys.getenv(name, unset = "")
  if (!nzchar(raw)) return(character(0))
  vals <- trimws(strsplit(raw, ",", fixed = TRUE)[[1]])
  unique(vals[nzchar(vals)])
}

snf_v041_config <- function() {
  state_filter <- Sys.getenv("SNF_DASHBOARD_STATE", unset = "UT")
  output_prefix <- Sys.getenv("SNF_OUTPUT_PREFIX", unset = "utah")
  target_ccns <- snf_parse_env_list("SNF_TARGET_CCNS")
  peer_minimum <- suppressWarnings(as.integer(Sys.getenv("SNF_PEER_MINIMUM", unset = "5")))
  if (is.na(peer_minimum) || peer_minimum < 1) peer_minimum <- 5L

  peer_mode <- tolower(trimws(Sys.getenv("SNF_PEER_MODE", unset = "auto")))
  if (!peer_mode %in% c("auto", "filters", "explicit")) peer_mode <- "auto"

  peer_min_beds <- suppressWarnings(as.numeric(Sys.getenv("SNF_PEER_MIN_BEDS", unset = "")))
  peer_max_beds <- suppressWarnings(as.numeric(Sys.getenv("SNF_PEER_MAX_BEDS", unset = "")))
  if (!is.finite(peer_min_beds)) peer_min_beds <- NA_real_
  if (!is.finite(peer_max_beds)) peer_max_beds <- NA_real_

  list(
    state_filter = state_filter,
    output_prefix = output_prefix,
    target_ccns = target_ccns,
    peer_minimum = peer_minimum,
    peer_mode = peer_mode,
    peer_ccns = snf_parse_env_list("SNF_PEER_CCNS"),
    peer_states = toupper(snf_parse_env_list("SNF_PEER_STATES")),
    peer_rural_urban = snf_parse_env_list("SNF_PEER_RURAL_URBAN"),
    peer_bed_size_bands = snf_parse_env_list("SNF_PEER_BED_SIZE_BANDS"),
    peer_controls = snf_parse_env_list("SNF_PEER_CONTROLS"),
    peer_min_beds = peer_min_beds,
    peer_max_beds = peer_max_beds,
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
    peer_benchmark_output = file.path("data/processed", paste0("snf_peer_benchmarks_v041_", output_prefix, ".rds")),
    peer_lookup_output = file.path("data/processed", paste0("snf_peer_lookup_v041_", output_prefix, ".rds"))
  )
}

snf_v041_prepare_dirs <- function(cfg = snf_v041_config()) {
  dir.create(cfg$processed_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cfg$dashboard_dir, recursive = TRUE, showWarnings = FALSE)
  dir.create(cfg$config_dir, recursive = TRUE, showWarnings = FALSE)
  invisible(cfg)
}
