# scripts/07_export_national_facility_index.R
# Export a lightweight nationwide facility index for search/SEO/product discovery.
# This deliberately avoids calculating peer benchmarks for every facility.

export_national_facility_index <- function(latest_valid, cfg = snf_v041_config()) {
  snf_v041_prepare_dirs(cfg)
  index <- latest_valid |>
    dplyr::arrange(.data$state, .data$facility_name, .data$provider_ccn) |>
    dplyr::transmute(
      provider_ccn = as.character(.data$provider_ccn),
      facility_name, city, county, state, zip_code, cbsa, rural_urban,
      type_of_control, total_beds, bed_size_band, snf_nf_mix,
      source_year, fiscal_year, fiscal_year_end_date, report_period_status,
      occupancy_rate, medicare_day_share, medicaid_day_share,
      net_patient_revenue_per_day, operating_expense_per_day,
      patient_service_margin, total_margin,
      salary_cost_per_day, contract_labor_per_day, contract_labor_ratio,
      total_labor_cost_per_day, labor_cost_share_of_operating_expense,
      days_cash_on_hand, current_ratio, valid_core_benchmark, data_quality_flags
    ) |>
    snf_clean_numeric_for_json()

  readr::write_csv(index, file.path(cfg$dashboard_dir, "national_facility_index_all.csv"))
  jsonlite::write_json(
    index,
    file.path(cfg$dashboard_dir, "national_facility_index_all.json"),
    dataframe = "rows", auto_unbox = TRUE, na = "null", pretty = FALSE
  )
  message("National facility index exported: ", nrow(index), " facilities")
  invisible(index)
}
