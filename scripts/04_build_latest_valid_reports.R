# scripts/04_build_latest_valid_reports.R
# Build one latest-valid report row per SNF provider.

build_snf_latest_valid_reports <- function(provider_year, cfg = snf_v041_config()) {
  snf_v041_prepare_dirs(cfg)

  latest_valid <- provider_year |>
    snf_latest_valid_provider_year() |>
    dplyr::mutate(
      latest_valid_rule = dplyr::case_when(
        dplyr::coalesce(.data$valid_core_benchmark, TRUE) & .data$report_period_status == "plausible" ~ "valid_core_plausible_report_period",
        dplyr::coalesce(.data$valid_core_benchmark, TRUE) ~ "valid_core_irregular_report_period",
        TRUE ~ "latest_available_with_core_quality_flags"
      )
    ) |>
    snf_clean_numeric_for_json()

  saveRDS(latest_valid, cfg$latest_valid_output)
  readr::write_csv(latest_valid, file.path(cfg$processed_dir, "snf_latest_valid_reports_v041.csv"))

  diagnostics <- provider_year |>
    dplyr::group_by(.data$state) |>
    dplyr::summarise(
      provider_year_rows = dplyr::n(),
      providers = dplyr::n_distinct(.data$provider_ccn),
      min_source_year = suppressWarnings(min(.data$source_year, na.rm = TRUE)),
      max_source_year = suppressWarnings(max(.data$source_year, na.rm = TRUE)),
      valid_core_rows = sum(dplyr::coalesce(.data$valid_core_benchmark, TRUE), na.rm = TRUE),
      plausible_report_period_rows = sum(.data$report_period_status == "plausible", na.rm = TRUE),
      .groups = "drop"
    )
  readr::write_csv(diagnostics, file.path(cfg$processed_dir, "snf_provider_year_diagnostics_v041.csv"))

  message("Latest-valid reports written: ", cfg$latest_valid_output)
  latest_valid
}
