# scripts/02_build_provider_year_public.R
# Refactor the v40 facility-year table into a v0.41 provider-year public-use layer.

build_snf_provider_year_public <- function(cfg = snf_v041_config()) {
  snf_v041_prepare_dirs(cfg)
  if (!file.exists(cfg$provider_year_input)) {
    stop("Missing provider-year input: ", cfg$provider_year_input, "\nRun 01/02 first or copy snf_facility_year_metrics.rds into data/processed/.")
  }

  provider_year <- readRDS(cfg$provider_year_input) |>
    dplyr::mutate(
      provider_ccn = as.character(.data$provider_ccn),
      source_year = as.integer(.data$source_year),
      fiscal_year = as.integer(.data$fiscal_year),
      facility_name = stringr::str_squish(as.character(.data$facility_name)),
      city = stringr::str_squish(as.character(.data$city)),
      county = stringr::str_squish(as.character(.data$county)),
      zip_code = as.character(.data$zip_code),
      state = toupper(as.character(.data$state)),
      type_of_control_code = stringr::str_squish(as.character(.data$type_of_control)),
      type_of_control = snf_type_of_control_label(.data$type_of_control_code),
      rural_urban_code = stringr::str_squish(as.character(.data$rural_urban)),
      rural_urban = snf_rural_urban_label(.data$rural_urban_code),
      bed_size_band = stringr::str_squish(as.character(.data$bed_size_band)),
      snf_nf_mix = stringr::str_squish(as.character(.data$snf_nf_mix)),
      report_period_status = snf_report_period_status(.data$report_days),
      full_year_report = .data$report_period_status == "plausible",
      average_daily_census = safe_div(.data$total_days, .data$report_days_for_rates),
      revenue_expense_spread_per_day = .data$net_patient_revenue_per_day - .data$operating_expense_per_day,
      total_labor_cost = snf_sum_with_na(.data$adjusted_salaries, .data$wage_related_costs, .data$contract_labor),
      total_labor_cost_per_day = safe_div(.data$total_labor_cost, .data$total_days),
      labor_cost_share_of_operating_expense = safe_div(.data$total_labor_cost, .data$operating_expense),
      labor_cost_share_of_total_costs = safe_div(.data$total_labor_cost, .data$total_costs),
      occupancy_rate = dplyr::coalesce(.data$occupancy_rate, safe_div(.data$total_days, .data$total_bed_days_available)),
      data_layer_version = cfg$project_version
    ) |>
    snf_clean_numeric_for_json()

  provider_master <- provider_year |>
    snf_latest_valid_provider_year() |>
    dplyr::transmute(
      provider_ccn,
      facility_name,
      city,
      county,
      state,
      zip_code,
      cbsa,
      rural_urban,
      rural_urban_code,
      type_of_control,
      type_of_control_code,
      total_beds,
      bed_size_band,
      snf_nf_mix,
      latest_source_year = source_year,
      latest_fiscal_year = fiscal_year,
      latest_fiscal_year_begin_date = fiscal_year_begin_date,
      latest_fiscal_year_end_date = fiscal_year_end_date,
      latest_report_days = report_days,
      latest_report_period_status = report_period_status,
      valid_core_benchmark,
      data_quality_flags
    )

  saveRDS(provider_year, cfg$provider_year_output)
  readr::write_csv(utils::head(provider_year, 5000), file.path(cfg$processed_dir, "snf_provider_year_public_v041_sample_5000_rows.csv"))
  saveRDS(provider_master, cfg$provider_master_output)
  readr::write_csv(provider_master, file.path(cfg$processed_dir, "snf_provider_master_v041.csv"))

  message("Provider-year public layer written: ", cfg$provider_year_output)
  message("Provider master written: ", cfg$provider_master_output)
  provider_year
}
