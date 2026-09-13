# 02_create_snf_metric_table.R
# Create a first-pass SNF facility-year analytic metric table.

source("R/snf_api_helpers.R")
source("R/snf_clean_helpers.R")

ensure_packages(c("dplyr", "tibble", "stringr", "readr", "janitor", "lubridate", "tidyr"))

processed_dir <- "data/processed"
dir.create(processed_dir, recursive = TRUE, showWarnings = FALSE)

input_path <- file.path(processed_dir, "snf_cost_reports_clean.rds")
if (!file.exists(input_path)) {
  stop("Missing clean input file: ", input_path, "\nRun 01_pull_clean_snf_cost_reports.R first.")
}

snf <- readRDS(input_path)

# ---- Resolve likely columns after janitor::clean_names() ----
cols <- list(
  ccn = first_existing_col(snf, c("provider_ccn", "ccn", "cms_certification_number", "cms_certification_number_ccn", "provider_number"), regex = "(^|_)ccn$|certification.*number|provider.*number"),
  facility_name = first_existing_col(snf, c("facility_name", "provider_name", "name"), regex = "facility.*name|provider.*name"),
  city = first_existing_col(snf, c("city", "provider_city", "facility_city"), regex = "(^|_)city$"),
  state = first_existing_col(snf, c("state_code", "state", "provider_state"), regex = "(^|_)state(_code)?$|provider.*state"),
  zip = first_existing_col(snf, c("zip_code", "zip", "provider_zip_code", "provider_zip"), regex = "zip"),
  county = first_existing_col(snf, c("county", "county_name", "provider_county"), regex = "county"),
  cbsa = first_existing_col(snf, c("cbsa", "medicare_cbsa_number", "core_based_statistical_area"), regex = "cbsa"),
  rural_urban = first_existing_col(snf, c("rural_urban_indicator", "rural_or_urban", "urban_rural"), regex = "rural|urban"),
  type_control = first_existing_col(snf, c("type_of_control", "control_type", "ownership_type"), regex = "type.*control|control.*type|ownership"),

  total_beds = first_existing_col(snf, c("number_of_beds", "total_number_of_beds", "total_beds"), regex = "^(number|total).*beds$"),
  snf_beds = first_existing_col(snf, c("snf_number_of_beds", "number_of_snf_beds"), regex = "snf.*beds"),
  nf_beds = first_existing_col(snf, c("nf_number_of_beds", "number_of_nf_beds"), regex = "(^|_)nf.*beds"),

  total_bed_days = first_existing_col(snf, c("total_bed_days_available", "bed_days_available_total", "total_available_bed_days"), regex = "total.*bed.*days.*available|bed.*days.*available.*total"),
  snf_bed_days = first_existing_col(snf, c("snf_bed_days_available", "snf_total_bed_days_available"), regex = "snf.*bed.*days.*available"),
  nf_bed_days = first_existing_col(snf, c("nf_bed_days_available", "nf_total_bed_days_available"), regex = "(^|_)nf.*bed.*days.*available"),

  total_days = first_existing_col(snf, c("total_days_total", "total_days"), regex = "^total_days_total$|^total_days$"),
  medicare_days = first_existing_col(snf, c("total_days_title_xviii", "total_days_medicare", "medicare_days"), regex = "total.*days.*title.*xviii|medicare.*days"),
  medicaid_days = first_existing_col(snf, c("total_days_title_xix", "total_days_medicaid", "medicaid_days"), regex = "total.*days.*title.*xix|medicaid.*days"),
  other_days = first_existing_col(snf, c("total_days_other", "other_days"), regex = "total.*days.*other|other.*days"),
  snf_days = first_existing_col(snf, c("snf_days_total", "snf_total_days", "total_snf_days"), regex = "snf.*days.*total|total.*snf.*days"),
  nf_days = first_existing_col(snf, c("nf_days_total", "nf_total_days", "total_nf_days"), regex = "(^|_)nf.*days.*total|total.*nf.*days"),

  total_admissions = first_existing_col(snf, c("total_admissions_total", "admissions_total", "total_admissions"), regex = "admissions.*total|total.*admissions"),
  total_discharges = first_existing_col(snf, c("total_discharges_total", "discharges_total", "total_discharges"), regex = "discharges.*total|total.*discharges"),

  total_charges = first_existing_col(snf, c("total_charges", "charges_total"), regex = "^total_charges$|charges.*total"),
  total_costs = first_existing_col(snf, c("total_costs", "costs_total"), regex = "^total_costs$|costs.*total"),
  net_patient_revenue = first_existing_col(snf, c("net_patient_revenue"), regex = "net.*patient.*revenue"),
  operating_expense = first_existing_col(snf, c("less_total_operating_expense", "total_operating_expense", "operating_expense"), regex = "operating.*expense"),
  net_income_service = first_existing_col(snf, c("net_income_from_service_to_patients", "net_income_from_services_to_patients"), regex = "net.*income.*service.*patient"),
  total_income = first_existing_col(snf, c("total_income"), regex = "^total_income$"),
  net_income = first_existing_col(snf, c("net_income"), regex = "^net_income$"),

  adjusted_salaries = first_existing_col(snf, c("total_salaries_adjusted", "adjusted_salaries"), regex = "salaries.*adjusted|adjusted.*salaries"),
  wage_related_costs = first_existing_col(snf, c("wage_related_costs"), regex = "wage.*related.*cost"),
  contract_labor = first_existing_col(snf, c("contract_labor"), regex = "contract.*labor"),
  overhead_non_salary_costs = first_existing_col(snf, c("overhead_non_salary_costs"), regex = "overhead.*non.*salary"),

  cash = first_existing_col(snf, c("cash", "cash_on_hand"), regex = "^cash$|cash.*hand"),
  current_assets = first_existing_col(snf, c("total_current_assets", "current_assets"), regex = "current.*assets"),
  current_liabilities = first_existing_col(snf, c("total_current_liabilities", "current_liabilities"), regex = "current.*liabilities"),
  total_assets = first_existing_col(snf, c("total_assets"), regex = "^total_assets$"),
  total_liabilities = first_existing_col(snf, c("total_liabilities"), regex = "^total_liabilities$"),
  accounts_receivable = first_existing_col(snf, c("accounts_receivable", "total_accounts_receivable"), regex = "accounts.*receivable"),
  accounts_payable = first_existing_col(snf, c("accounts_payable", "total_accounts_payable"), regex = "accounts.*payable")
)

resolved_columns <- tibble::enframe(unlist(cols), name = "field", value = "resolved_column") |>
  dplyr::mutate(found = !is.na(.data$resolved_column))
readr::write_csv(resolved_columns, file.path(processed_dir, "snf_metric_resolved_columns.csv"))

# ---- Profile fields ----
ccn <- chr_val(snf, cols$ccn)
facility_name <- chr_val(snf, cols$facility_name)
city <- chr_val(snf, cols$city)
state <- chr_val(snf, cols$state)
zip_code <- chr_val(snf, cols$zip)
county <- chr_val(snf, cols$county)
cbsa <- chr_val(snf, cols$cbsa)
rural_urban <- chr_val(snf, cols$rural_urban)
type_of_control <- chr_val(snf, cols$type_control)

# ---- Numeric inputs ----
snf_beds <- val(snf, cols$snf_beds)
nf_beds <- val(snf, cols$nf_beds)
beds_sum <- rowSums(cbind(snf_beds, nf_beds), na.rm = TRUE)
beds_sum[is.na(snf_beds) & is.na(nf_beds)] <- NA_real_
total_beds <- dplyr::coalesce(val(snf, cols$total_beds), beds_sum)

snf_bed_days <- val(snf, cols$snf_bed_days)
nf_bed_days <- val(snf, cols$nf_bed_days)
bed_days_sum <- rowSums(cbind(snf_bed_days, nf_bed_days), na.rm = TRUE)
bed_days_sum[is.na(snf_bed_days) & is.na(nf_bed_days)] <- NA_real_
total_bed_days <- dplyr::coalesce(val(snf, cols$total_bed_days), bed_days_sum)

medicare_days <- val(snf, cols$medicare_days)
medicaid_days <- val(snf, cols$medicaid_days)
other_days <- val(snf, cols$other_days)
days_sum <- rowSums(cbind(medicare_days, medicaid_days, other_days), na.rm = TRUE)
days_sum[is.na(medicare_days) & is.na(medicaid_days) & is.na(other_days)] <- NA_real_
total_days <- dplyr::coalesce(val(snf, cols$total_days), days_sum)

snf_days <- val(snf, cols$snf_days)
nf_days <- val(snf, cols$nf_days)
total_admissions <- val(snf, cols$total_admissions)
total_discharges <- val(snf, cols$total_discharges)

total_charges <- val(snf, cols$total_charges)
total_costs <- val(snf, cols$total_costs)
net_patient_revenue <- val(snf, cols$net_patient_revenue)
operating_expense <- val(snf, cols$operating_expense)
net_income_service <- val(snf, cols$net_income_service)
total_income <- val(snf, cols$total_income)
net_income <- val(snf, cols$net_income)
adjusted_salaries <- val(snf, cols$adjusted_salaries)
wage_related_costs <- val(snf, cols$wage_related_costs)
contract_labor <- val(snf, cols$contract_labor)
overhead_non_salary_costs <- val(snf, cols$overhead_non_salary_costs)

cash <- val(snf, cols$cash)
current_assets <- val(snf, cols$current_assets)
current_liabilities <- val(snf, cols$current_liabilities)
total_assets <- val(snf, cols$total_assets)
total_liabilities <- val(snf, cols$total_liabilities)
accounts_receivable <- val(snf, cols$accounts_receivable)
accounts_payable <- val(snf, cols$accounts_payable)

report_days <- if ("report_days" %in% names(snf)) snf$report_days else rep(NA_real_, nrow(snf))
report_days_for_rates <- dplyr::if_else(
  !is.na(report_days) & report_days >= 300 & report_days <= 430,
  as.numeric(report_days),
  365
)
fiscal_year <- if ("fiscal_year" %in% names(snf)) snf$fiscal_year else snf$source_year
source_year <- if ("source_year" %in% names(snf)) snf$source_year else fiscal_year

metric_tbl <- tibble::tibble(
  provider_ccn = ccn,
  facility_name = facility_name,
  city = city,
  state = state,
  zip_code = zip_code,
  county = county,
  cbsa = cbsa,
  rural_urban = rural_urban,
  type_of_control = type_of_control,
  source_year = source_year,
  fiscal_year = fiscal_year,
  fiscal_year_begin_date = if ("fiscal_year_begin_date_clean" %in% names(snf)) snf$fiscal_year_begin_date_clean else as.Date(NA),
  fiscal_year_end_date = if ("fiscal_year_end_date_clean" %in% names(snf)) snf$fiscal_year_end_date_clean else as.Date(NA),
  report_days = report_days,
  report_days_for_rates = report_days_for_rates,

  total_beds = total_beds,
  snf_beds = snf_beds,
  nf_beds = nf_beds,
  bed_size_band = make_bed_size_band(total_beds),
  total_bed_days_available = total_bed_days,
  snf_bed_days_available = snf_bed_days,
  nf_bed_days_available = nf_bed_days,

  total_days = total_days,
  medicare_days = medicare_days,
  medicaid_days = medicaid_days,
  other_days = other_days,
  snf_days = snf_days,
  nf_days = nf_days,
  snf_nf_mix = make_snf_nf_mix(snf_days, nf_days, total_days),
  total_admissions = total_admissions,
  total_discharges = total_discharges,

  occupancy_rate = safe_div(total_days, total_bed_days),
  medicare_day_share = safe_div(medicare_days, total_days),
  medicaid_day_share = safe_div(medicaid_days, total_days),
  other_day_share = safe_div(other_days, total_days),
  snf_day_share = safe_div(snf_days, total_days),
  nf_day_share = safe_div(nf_days, total_days),
  admissions_per_bed = safe_div(total_admissions, total_beds),
  discharges_per_bed = safe_div(total_discharges, total_beds),
  average_length_of_stay_calc = safe_div(total_days, total_discharges),

  total_charges = total_charges,
  total_costs = total_costs,
  net_patient_revenue = net_patient_revenue,
  operating_expense = operating_expense,
  net_income_from_service_to_patients = net_income_service,
  total_income = total_income,
  net_income = net_income,
  adjusted_salaries = adjusted_salaries,
  wage_related_costs = wage_related_costs,
  contract_labor = contract_labor,
  overhead_non_salary_costs = overhead_non_salary_costs,

  net_patient_revenue_per_day = safe_div(net_patient_revenue, total_days),
  operating_expense_per_day = safe_div(operating_expense, total_days),
  reported_costs_per_day = safe_div(total_costs, total_days),
  cost_per_day = safe_div(total_costs, total_days),
  charges_per_day = safe_div(total_charges, total_days),
  cost_to_charge_ratio = safe_div(total_costs, total_charges),
  patient_service_margin = safe_div(net_income_service, net_patient_revenue),
  total_margin = safe_div(net_income, net_patient_revenue),
  net_margin = safe_div(net_income, total_income),
  net_income_per_day = safe_div(net_income, total_days),

  salary_cost_per_day = safe_div(adjusted_salaries, total_days),
  wage_related_cost_ratio = safe_div(wage_related_costs, adjusted_salaries),
  contract_labor_per_day = safe_div(contract_labor, total_days),
  contract_labor_ratio = safe_div(contract_labor, adjusted_salaries + contract_labor),
  overhead_non_salary_ratio = safe_div(overhead_non_salary_costs, total_costs),

  cash = cash,
  current_assets = current_assets,
  current_liabilities = current_liabilities,
  total_assets = total_assets,
  total_liabilities = total_liabilities,
  accounts_receivable = accounts_receivable,
  accounts_payable = accounts_payable,
  days_cash_on_hand = safe_div(cash, safe_div(operating_expense, report_days_for_rates)),
  current_ratio = safe_div(current_assets, current_liabilities),
  debt_to_assets = safe_div(total_liabilities, total_assets),
  days_accounts_receivable = safe_div(accounts_receivable, safe_div(net_patient_revenue, report_days_for_rates)),
  payables_days = safe_div(accounts_payable, safe_div(operating_expense, report_days_for_rates))
) |>
  dplyr::mutate(
    data_quality_flags = paste(
      dplyr::if_else(is.na(.data$provider_ccn), "missing_ccn", ""),
      dplyr::if_else(is.na(.data$total_days) | .data$total_days <= 0, "missing_or_invalid_total_days", ""),
      dplyr::if_else(is.na(.data$total_beds) | .data$total_beds <= 0, "missing_or_invalid_beds", ""),
      dplyr::if_else(is.na(.data$total_bed_days_available) | .data$total_bed_days_available <= 0, "missing_or_invalid_bed_days", ""),
      dplyr::if_else(!is.na(.data$occupancy_rate) & (.data$occupancy_rate < 0 | .data$occupancy_rate > 1.25), "occupancy_outlier", ""),
      dplyr::if_else(is.na(.data$report_days), "missing_report_period", ""),
      dplyr::if_else(!is.na(.data$report_days) & .data$report_days < 300, "short_report_period", ""),
      dplyr::if_else(!is.na(.data$report_days) & .data$report_days > 430, "long_report_period", ""),
      dplyr::if_else(is.na(.data$report_days) | .data$report_days < 300 | .data$report_days > 430, "used_365_day_rate_fallback", ""),
      sep = ";"
    ),
    data_quality_flags = stringr::str_replace_all(.data$data_quality_flags, ";+", ";"),
    data_quality_flags = stringr::str_replace_all(.data$data_quality_flags, "^;|;$", ""),
    data_quality_flags = dplyr::na_if(.data$data_quality_flags, ""),
    has_data_quality_flags = !is.na(.data$data_quality_flags),
    has_core_data_quality_flags = !is.na(.data$data_quality_flags) &
      stringr::str_detect(.data$data_quality_flags, "missing_ccn|missing_or_invalid_total_days|missing_or_invalid_beds|missing_or_invalid_bed_days|occupancy_outlier"),
    has_report_period_warning = !is.na(.data$data_quality_flags) &
      stringr::str_detect(.data$data_quality_flags, "missing_report_period|short_report_period|long_report_period|used_365_day_rate_fallback"),
    valid_core_benchmark = !.data$has_core_data_quality_flags
  )

flag_counts <- metric_tbl |>
  dplyr::filter(!is.na(.data$data_quality_flags)) |>
  dplyr::select(.data$provider_ccn, .data$source_year, .data$data_quality_flags) |>
  tidyr::separate_rows(.data$data_quality_flags, sep = ";") |>
  dplyr::filter(!is.na(.data$data_quality_flags), .data$data_quality_flags != "") |>
  dplyr::count(.data$data_quality_flags, name = "rows", sort = TRUE)
readr::write_csv(flag_counts, file.path(processed_dir, "snf_data_quality_flag_counts.csv"))

saveRDS(metric_tbl, file.path(processed_dir, "snf_facility_year_metrics.rds"))
save_if_arrow_available(metric_tbl, file.path(processed_dir, "snf_facility_year_metrics.parquet"))
readr::write_csv(utils::head(metric_tbl, 5000), file.path(processed_dir, "snf_facility_year_metrics_sample_5000_rows.csv"))

metric_summary <- metric_tbl |>
  dplyr::summarise(
    rows = dplyr::n(),
    facilities = dplyr::n_distinct(.data$provider_ccn, na.rm = TRUE),
    min_year = min(.data$source_year, na.rm = TRUE),
    max_year = max(.data$source_year, na.rm = TRUE),
    occupancy_nonmissing = sum(!is.na(.data$occupancy_rate)),
    revenue_per_day_nonmissing = sum(!is.na(.data$net_patient_revenue_per_day)),
    margin_nonmissing = sum(!is.na(.data$patient_service_margin)),
    contract_labor_ratio_nonmissing = sum(!is.na(.data$contract_labor_ratio)),
    quality_flagged_rows = sum(.data$has_data_quality_flags, na.rm = TRUE),
    core_quality_flagged_rows = sum(.data$has_core_data_quality_flags, na.rm = TRUE),
    report_period_warning_rows = sum(.data$has_report_period_warning, na.rm = TRUE),
    valid_core_benchmark_rows = sum(.data$valid_core_benchmark, na.rm = TRUE)
  )
readr::write_csv(metric_summary, file.path(processed_dir, "snf_metric_summary.csv"))

message("\nStep 2 complete.")
message("Metric table: data/processed/snf_facility_year_metrics.rds")
message("Column resolution: data/processed/snf_metric_resolved_columns.csv")
message("Metric summary: data/processed/snf_metric_summary.csv")
