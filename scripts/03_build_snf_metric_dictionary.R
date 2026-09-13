# scripts/03_build_snf_metric_dictionary.R
# Build the reusable SNF v0.41 metric dictionary.

build_snf_metric_dictionary <- function(provider_year, cfg = snf_v041_config()) {
  snf_v041_prepare_dirs(cfg)
  if (!file.exists(cfg$metric_dictionary_config)) {
    stop("Missing metric dictionary config: ", cfg$metric_dictionary_config)
  }

  metric_specs <- readr::read_csv(cfg$metric_dictionary_config, show_col_types = FALSE) |>
    dplyr::mutate(
      higher_is_better = snf_bool(.data$higher_is_better),
      display_in_dashboard = snf_bool(.data$display_in_dashboard),
      display_priority = suppressWarnings(as.integer(.data$display_priority))
    ) |>
    dplyr::filter(.data$metric %in% names(provider_year)) |>
    dplyr::arrange(.data$display_priority, .data$domain, .data$label)

  dashboard_metric_specs <- metric_specs |>
    dplyr::filter(dplyr::coalesce(.data$display_in_dashboard, TRUE))

  readr::write_csv(metric_specs, cfg$metric_dictionary_output)
  readr::write_csv(dashboard_metric_specs, file.path(cfg$dashboard_dir, "utah_metric_specs.csv"))
  jsonlite::write_json(dashboard_metric_specs, file.path(cfg$dashboard_dir, "utah_metric_specs.json"), dataframe = "rows", auto_unbox = TRUE, na = "null", pretty = TRUE)

  missing_metrics <- readr::read_csv(cfg$metric_dictionary_config, show_col_types = FALSE) |>
    dplyr::filter(!.data$metric %in% names(provider_year)) |>
    dplyr::select(.data$metric, .data$label, .data$source_layer, .data$module)
  readr::write_csv(missing_metrics, file.path(cfg$processed_dir, "snf_metric_dictionary_missing_fields_v041.csv"))

  message("Metric dictionary written: ", cfg$metric_dictionary_output)
  message("Dashboard metric specs written: ", file.path(cfg$dashboard_dir, "utah_metric_specs.json"))
  metric_specs
}
