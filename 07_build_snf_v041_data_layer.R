# 07_build_snf_v041_data_layer.R
# Build the SNF dashboard v0.41 refactored data layer.
#
# This is intentionally backward-compatible with v40 dashboard file names:
# it writes data/dashboard/utah_facility_index.json, utah_metric_specs.json,
# utah_facility_benchmarks.json, utah_facility_trends.json, and related CSVs.

source("scripts/00_config.R")
source("R/snf_v041_helpers.R")
source("scripts/02_build_provider_year_public.R")
source("scripts/03_build_snf_metric_dictionary.R")
source("scripts/04_build_latest_valid_reports.R")
source("scripts/05_build_peer_benchmarks.R")
source("scripts/06_export_dashboard_json.R")

cfg <- snf_v041_config()
snf_v041_prepare_dirs(cfg)

message("\nBuilding SNF dashboard data layer ", cfg$project_version, "...")
message("State filter: ", cfg$state_filter, if (length(cfg$target_ccns) > 0) paste0("; target CCNs: ", paste(cfg$target_ccns, collapse=", ")) else "")
message("Peer minimum: ", cfg$peer_minimum)

provider_year <- build_snf_provider_year_public(cfg)
metric_specs <- build_snf_metric_dictionary(provider_year, cfg)
latest_valid <- build_snf_latest_valid_reports(provider_year, cfg)
peer_outputs <- build_snf_peer_benchmarks(provider_year, latest_valid, metric_specs, cfg)
dashboard_outputs <- export_snf_dashboard_json(provider_year, latest_valid, metric_specs, peer_outputs, cfg)

summary_tbl <- tibble::tibble(
  version = cfg$project_version,
  state_filter = cfg$state_filter,
  provider_year_rows = nrow(provider_year),
  provider_count = dplyr::n_distinct(provider_year$provider_ccn),
  latest_valid_rows = nrow(latest_valid),
  dashboard_facilities = nrow(dashboard_outputs$facility_index),
  dashboard_metrics = nrow(metric_specs |> dplyr::filter(dplyr::coalesce(.data$display_in_dashboard, TRUE))),
  benchmark_rows = nrow(dashboard_outputs$benchmarks),
  trend_rows = nrow(dashboard_outputs$trends),
  strategy_flag_rows = nrow(dashboard_outputs$flags),
  built_at = as.character(Sys.time())
)
readr::write_csv(summary_tbl, file.path(cfg$processed_dir, "snf_v041_build_summary.csv"))

message("\nSNF v0.41 data layer complete.")
message("Build summary: ", file.path(cfg$processed_dir, "snf_v041_build_summary.csv"))
message("Dashboard JSON files: ", cfg$dashboard_dir)

invisible(list(
  config = cfg,
  provider_year = provider_year,
  metric_specs = metric_specs,
  latest_valid = latest_valid,
  peer_outputs = peer_outputs,
  dashboard_outputs = dashboard_outputs,
  summary = summary_tbl
))
