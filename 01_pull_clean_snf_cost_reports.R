# 01_pull_clean_snf_cost_reports.R
# Pull and clean CMS Skilled Nursing Facility Cost Report public use files.

source("R/snf_api_helpers.R")
source("R/snf_clean_helpers.R")

ensure_packages(c(
  "httr2", "jsonlite", "purrr", "dplyr", "tibble", "stringr", "readr", "janitor", "lubridate"
))

min_year <- as.integer(Sys.getenv("SNF_MIN_YEAR", "2011"))
max_year_env <- Sys.getenv("SNF_MAX_YEAR", "")
max_year <- if (max_year_env == "") NULL else as.integer(max_year_env)
prefer <- Sys.getenv("SNF_SOURCE_PREFER", "CSV")
max_pages_env <- Sys.getenv("SNF_MAX_API_PAGES", "")
max_pages <- if (max_pages_env == "") Inf else as.integer(max_pages_env)

raw_dir <- "data/raw"
processed_dir <- "data/processed"
dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(processed_dir, recursive = TRUE, showWarnings = FALSE)

manifest <- cms_get_snf_manifest(
  min_year = min_year,
  max_year = max_year,
  prefer = prefer
)

readr::write_csv(manifest, file.path(raw_dir, "snf_cms_manifest.csv"))
message("Manifest written to data/raw/snf_cms_manifest.csv")
message("Years to pull: ", paste(manifest$source_year, collapse = ", "))

snf_raw <- purrr::map_dfr(seq_len(nrow(manifest)), function(i) {
  cms_read_distribution(manifest[i, ], max_pages = max_pages)
})

readr::write_csv(utils::head(snf_raw, 1000), file.path(raw_dir, "snf_raw_sample_1000_rows.csv"))
saveRDS(snf_raw, file.path(raw_dir, "snf_raw.rds"))
message("Raw RDS written to data/raw/snf_raw.rds")

snf_clean <- snf_raw |>
  janitor::clean_names() |>
  dplyr::mutate(dplyr::across(dplyr::where(is.character), ~ dplyr::na_if(trimws(.x), "")))

fy_begin_col <- first_existing_col(
  snf_clean,
  aliases = c("fiscal_year_begin_date", "fy_begin_date", "fiscal_period_begin_date"),
  regex = "fiscal.*begin.*date|fy.*begin.*date"
)
fy_end_col <- first_existing_col(
  snf_clean,
  aliases = c("fiscal_year_end_date", "fy_end_date", "fiscal_period_end_date"),
  regex = "fiscal.*end.*date|fy.*end.*date"
)

if (!is.na(fy_begin_col)) snf_clean$fiscal_year_begin_date_raw <- as.character(snf_clean[[fy_begin_col]])
if (!is.na(fy_end_col)) snf_clean$fiscal_year_end_date_raw <- as.character(snf_clean[[fy_end_col]])

if (!is.na(fy_begin_col)) snf_clean[[fy_begin_col]] <- parse_cms_date(snf_clean[[fy_begin_col]])
if (!is.na(fy_end_col)) snf_clean[[fy_end_col]] <- parse_cms_date(snf_clean[[fy_end_col]])

snf_clean <- convert_numeric_candidates(snf_clean)

if (!is.na(fy_begin_col) && !is.na(fy_end_col)) {
  snf_clean <- snf_clean |>
    dplyr::mutate(
      fiscal_year_begin_date_clean = .data[[fy_begin_col]],
      fiscal_year_end_date_clean = .data[[fy_end_col]],
      report_days = as.numeric(.data$fiscal_year_end_date_clean - .data$fiscal_year_begin_date_clean + 1),
      fiscal_year = lubridate::year(.data$fiscal_year_end_date_clean)
    )
} else {
  warning("Could not find fiscal year begin/end date columns. report_days and fiscal_year were not created from dates.")
  snf_clean <- snf_clean |>
    dplyr::mutate(
      fiscal_year_begin_date_clean = as.Date(NA),
      fiscal_year_end_date_clean = as.Date(NA),
      report_days = NA_real_,
      fiscal_year = .data$source_year
    )
}

if ("report_days" %in% names(snf_clean)) {
  report_period_diagnostics <- snf_clean |>
    dplyr::group_by(.data$source_year) |>
    dplyr::summarise(
      rows = dplyr::n(),
      missing_report_days = sum(is.na(.data$report_days)),
      short_report_period = sum(!is.na(.data$report_days) & .data$report_days < 300),
      plausible_report_period = sum(!is.na(.data$report_days) & .data$report_days >= 300 & .data$report_days <= 430),
      long_report_period = sum(!is.na(.data$report_days) & .data$report_days > 430),
      min_report_days = suppressWarnings(min(.data$report_days, na.rm = TRUE)),
      p01_report_days = suppressWarnings(stats::quantile(.data$report_days, 0.01, na.rm = TRUE, names = FALSE)),
      p25_report_days = suppressWarnings(stats::quantile(.data$report_days, 0.25, na.rm = TRUE, names = FALSE)),
      median_report_days = suppressWarnings(stats::median(.data$report_days, na.rm = TRUE)),
      p75_report_days = suppressWarnings(stats::quantile(.data$report_days, 0.75, na.rm = TRUE, names = FALSE)),
      p99_report_days = suppressWarnings(stats::quantile(.data$report_days, 0.99, na.rm = TRUE, names = FALSE)),
      max_report_days = suppressWarnings(max(.data$report_days, na.rm = TRUE)),
      .groups = "drop"
    )
  readr::write_csv(report_period_diagnostics, file.path(processed_dir, "snf_report_period_diagnostics.csv"))

  id_cols_for_sample <- intersect(
    c("source_year", "provider_ccn", "facility_name", "city", "state_code",
      "fiscal_year_begin_date_raw", "fiscal_year_end_date_raw",
      "fiscal_year_begin_date_clean", "fiscal_year_end_date_clean", "report_days"),
    names(snf_clean)
  )

  report_period_problem_sample <- snf_clean |>
    dplyr::filter(is.na(.data$report_days) | .data$report_days < 300 | .data$report_days > 430) |>
    dplyr::select(dplyr::all_of(id_cols_for_sample)) |>
    utils::head(100)
  readr::write_csv(report_period_problem_sample, file.path(processed_dir, "snf_report_period_problem_sample.csv"))
}

column_audit <- tibble::tibble(
  column = names(snf_clean),
  class = vapply(snf_clean, function(x) paste(class(x), collapse = "/"), character(1)),
  missing_n = vapply(snf_clean, function(x) sum(is.na(x)), integer(1)),
  non_missing_n = vapply(snf_clean, function(x) sum(!is.na(x)), integer(1))
)
readr::write_csv(column_audit, file.path(processed_dir, "snf_column_audit.csv"))

saveRDS(snf_clean, file.path(processed_dir, "snf_cost_reports_clean.rds"))
write_parquet_ok <- save_if_arrow_available(snf_clean, file.path(processed_dir, "snf_cost_reports_clean.parquet"))
readr::write_csv(utils::head(snf_clean, 1000), file.path(processed_dir, "snf_cost_reports_clean_sample_1000_rows.csv"))

summary_tbl <- snf_clean |>
  dplyr::count(.data$source_year, name = "rows") |>
  dplyr::arrange(.data$source_year)
readr::write_csv(summary_tbl, file.path(processed_dir, "snf_rows_by_source_year.csv"))

message("\nStep 1 complete.")
message("Rows pulled: ", nrow(snf_clean))
message("Columns: ", ncol(snf_clean))
message("Clean data: data/processed/snf_cost_reports_clean.rds")
if (write_parquet_ok) message("Parquet data: data/processed/snf_cost_reports_clean.parquet")
message("Column audit: data/processed/snf_column_audit.csv")
message("Rows by source year: data/processed/snf_rows_by_source_year.csv")
