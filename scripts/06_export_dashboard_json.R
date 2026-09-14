# scripts/06_export_dashboard_json.R
# Export v0.41 dashboard CSV/JSON files. Output prefix is configurable (default: utah).

build_snf_strategy_flags <- function(facility_index, benchmarks, trends) {
  bench_value <- function(b, metric, col) {
    z <- b |> dplyr::filter(.data$metric == .env$metric) |> dplyr::slice(1)
    if (nrow(z) == 0 || !(col %in% names(z))) return(NA_real_)
    suppressWarnings(as.numeric(z[[col]][[1]]))
  }
  add_flag <- function(provider_ccn, severity, domain, title, detail, metric = NA_character_) {
    tibble::tibble(provider_ccn, severity, domain, title, detail, metric)
  }

  flag_rows <- list()
  idx <- 1L

  for (target_id in facility_index$provider_ccn) {
    b <- benchmarks |> dplyr::filter(.data$provider_ccn == target_id)
    tdf <- trends |> dplyr::filter(.data$provider_ccn == target_id)
    f <- list()

    occ <- bench_value(b, "occupancy_rate", "target_value")
    occ_med <- bench_value(b, "occupancy_rate", "peer_median")
    occ_delta <- snf_trend_delta(tdf, "occupancy_rate", 3)
    if (!is.na(occ) && !is.na(occ_med) && occ < occ_med - 0.05) f <- append(f, list(add_flag(target_id, "Risk", "Utilization", "Occupancy trails peers", "Latest occupancy is more than five percentage points below the peer median.", "occupancy_rate")))
    if (!is.na(occ_delta) && occ_delta < -0.05) f <- append(f, list(add_flag(target_id, "Watch", "Utilization", "Occupancy has declined", "Occupancy is down more than five percentage points from roughly three years earlier.", "occupancy_rate")))
    if (!is.na(occ) && !is.na(occ_med) && occ > occ_med + 0.05) f <- append(f, list(add_flag(target_id, "Strength", "Utilization", "Occupancy leads peers", "Latest occupancy is more than five percentage points above the peer median.", "occupancy_rate")))

    adc <- bench_value(b, "average_daily_census", "target_value")
    adc_med <- bench_value(b, "average_daily_census", "peer_median")
    if (!is.na(adc) && !is.na(adc_med) && adc < adc_med * 0.75) f <- append(f, list(add_flag(target_id, "Watch", "Utilization", "Average daily census is small versus peers", "Average daily census is less than roughly 75% of the peer median, which can raise fixed cost per day.", "average_daily_census")))

    med <- bench_value(b, "medicare_day_share", "target_value")
    med_peer <- bench_value(b, "medicare_day_share", "peer_median")
    if (!is.na(med) && !is.na(med_peer) && med < med_peer - 0.03) f <- append(f, list(add_flag(target_id, "Watch", "Payer mix", "Medicare skilled mix is below peers", "Medicare day share is at least three percentage points below the peer median; referral capture may deserve review.", "medicare_day_share")))
    if (!is.na(med) && !is.na(med_peer) && med > med_peer + 0.03) f <- append(f, list(add_flag(target_id, "Strength", "Payer mix", "Medicare skilled mix leads peers", "Medicare day share is at least three percentage points above the peer median.", "medicare_day_share")))

    mcaid <- bench_value(b, "medicaid_day_share", "target_value")
    mcaid_peer <- bench_value(b, "medicaid_day_share", "peer_median")
    if (!is.na(mcaid) && !is.na(mcaid_peer) && mcaid > mcaid_peer + 0.05) f <- append(f, list(add_flag(target_id, "Watch", "Payer mix", "Medicaid dependence is higher than peers", "Medicaid day share is more than five percentage points above the peer median.", "medicaid_day_share")))

    rev <- bench_value(b, "net_patient_revenue_per_day", "target_value")
    rev_peer <- bench_value(b, "net_patient_revenue_per_day", "peer_median")
    exp <- bench_value(b, "operating_expense_per_day", "target_value")
    exp_p75 <- bench_value(b, "operating_expense_per_day", "peer_p75")
    spread <- bench_value(b, "revenue_expense_spread_per_day", "target_value")
    if (!is.na(rev) && !is.na(rev_peer) && rev > rev_peer) f <- append(f, list(add_flag(target_id, "Strength", "Revenue", "Revenue per day is above peers", "Net patient revenue per resident day is above the peer median.", "net_patient_revenue_per_day")))
    if (!is.na(exp) && !is.na(exp_p75) && exp > exp_p75) f <- append(f, list(add_flag(target_id, "Watch", "Cost", "Operating expense is high", "Operating expense per resident day is above the peer 75th percentile.", "operating_expense_per_day")))
    if (!is.na(spread) && spread < 0) f <- append(f, list(add_flag(target_id, "Risk", "Margin", "Revenue-expense spread is negative", "Net patient revenue per resident day is below operating expense per resident day.", "revenue_expense_spread_per_day")))

    psm <- bench_value(b, "patient_service_margin", "target_value")
    psm_peer <- bench_value(b, "patient_service_margin", "peer_median")
    if (!is.na(psm) && psm < 0) f <- append(f, list(add_flag(target_id, "Risk", "Margin", "Patient service margin is negative", "The latest cost report shows a negative patient service margin.", "patient_service_margin")))
    if (!is.na(psm) && !is.na(psm_peer) && psm > psm_peer + 0.03) f <- append(f, list(add_flag(target_id, "Strength", "Margin", "Margin leads peers", "Patient service margin is at least three percentage points above the peer median.", "patient_service_margin")))

    clr <- bench_value(b, "contract_labor_ratio", "target_value")
    clr_p75 <- bench_value(b, "contract_labor_ratio", "peer_p75")
    tlc <- bench_value(b, "total_labor_cost_per_day", "target_value")
    tlc_p75 <- bench_value(b, "total_labor_cost_per_day", "peer_p75")
    labor_share <- bench_value(b, "labor_cost_share_of_operating_expense", "target_value")
    labor_share_p75 <- bench_value(b, "labor_cost_share_of_operating_expense", "peer_p75")
    if (!is.na(clr) && ((!is.na(clr_p75) && clr > clr_p75) || clr > 0.10)) f <- append(f, list(add_flag(target_id, "Watch", "Labor", "Contract labor reliance is elevated", "Contract labor ratio is above the peer 75th percentile or above 10%.", "contract_labor_ratio")))
    if (!is.na(tlc) && !is.na(tlc_p75) && tlc > tlc_p75) f <- append(f, list(add_flag(target_id, "Watch", "Labor", "Total labor cost per day is high", "Combined salary, wage-related, and contract labor cost per resident day is above the peer 75th percentile.", "total_labor_cost_per_day")))
    if (!is.na(labor_share) && !is.na(labor_share_p75) && labor_share > labor_share_p75) f <- append(f, list(add_flag(target_id, "Watch", "Labor", "Labor share of expense is high", "Broad labor cost share of operating expense is above the peer 75th percentile.", "labor_cost_share_of_operating_expense")))

    cash <- bench_value(b, "days_cash_on_hand", "target_value")
    cash_p25 <- bench_value(b, "days_cash_on_hand", "peer_p25")
    if (!is.na(cash) && ((!is.na(cash_p25) && cash < cash_p25) || cash < 30)) f <- append(f, list(add_flag(target_id, "Risk", "Liquidity", "Liquidity appears thin", "Days cash on hand is below the peer 25th percentile or below 30 days.", "days_cash_on_hand")))

    if (length(f) == 0) {
      f <- list(add_flag(target_id, "Context", "Summary", "No major rule-based flags", "The first-pass rules did not identify a major utilization, margin, labor, or liquidity flag. Review detailed metrics before drawing conclusions.", NA_character_))
    }
    flag_rows[[idx]] <- dplyr::bind_rows(f)
    idx <- idx + 1L
  }

  dplyr::bind_rows(flag_rows)
}

export_snf_dashboard_json <- function(provider_year, latest_valid, metric_specs, peer_outputs, cfg = snf_v041_config()) {
  snf_v041_prepare_dirs(cfg)

  prefix <- cfg$output_prefix
  latest_state <- snf_filter_state(latest_valid, cfg$state_filter)

  facility_index <- latest_state |>
    dplyr::arrange(.data$facility_name, .data$city, .data$provider_ccn) |>
    dplyr::transmute(
      provider_ccn,
      display_name = paste0(.data$facility_name, " — ", .data$city, " (", .data$provider_ccn, ")"),
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
      source_year,
      fiscal_year,
      report_days,
      report_period_status,
      latest_valid_rule,
      total_days,
      average_daily_census,
      occupancy_rate,
      medicare_day_share,
      medicaid_day_share,
      other_day_share,
      net_patient_revenue_per_day,
      operating_expense_per_day,
      revenue_expense_spread_per_day,
      patient_service_margin,
      total_margin,
      net_income_per_day,
      salary_cost_per_day,
      contract_labor_per_day,
      contract_labor_ratio,
      total_labor_cost_per_day,
      labor_cost_share_of_operating_expense,
      days_cash_on_hand,
      current_ratio,
      valid_core_benchmark,
      data_quality_flags,
      data_layer_version
    ) |>
    snf_clean_numeric_for_json()

  if (length(cfg$target_ccns) > 0) {
    facility_index <- facility_index |>
      dplyr::filter(as.character(.data$provider_ccn) %in% cfg$target_ccns)
  }

  demo_ccn_filter <- Sys.getenv("SNF_DEMO_CCNS", unset = "")
  if (nzchar(demo_ccn_filter)) {
    demo_ccns <- trimws(strsplit(demo_ccn_filter, ",")[[1]])
    facility_index <- facility_index |>
      dplyr::filter(as.character(.data$provider_ccn) %in% demo_ccns)
    if (nrow(facility_index) == 0) {
      stop("SNF_DEMO_CCNS was set, but none of those CCNs were found in the latest-valid facility index.")
    }
    message("Public demo mode: limiting selector/reports to ", nrow(facility_index), " facilities.")
  }

  readr::write_csv(facility_index, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_index.csv")))
  jsonlite::write_json(facility_index, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_index.json")), dataframe = "rows", auto_unbox = TRUE, na = "null", pretty = FALSE)

  benchmarks <- peer_outputs$benchmarks |>
    dplyr::filter(.data$provider_ccn %in% facility_index$provider_ccn) |>
    snf_clean_numeric_for_json()
  peer_lookup <- peer_outputs$peer_lookup |>
    dplyr::filter(.data$provider_ccn %in% facility_index$provider_ccn)

  readr::write_csv(benchmarks, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_benchmarks.csv")))
  jsonlite::write_json(benchmarks, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_benchmarks.json")), dataframe = "rows", auto_unbox = TRUE, na = "null", pretty = FALSE)
  readr::write_csv(peer_lookup, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_peer_lookup.csv")))

  metric_specs_display <- metric_specs |>
    dplyr::filter(dplyr::coalesce(.data$display_in_dashboard, TRUE)) |>
    dplyr::filter(.data$metric %in% names(provider_year))

  state_provider_year <- snf_filter_state(provider_year, cfg$state_filter)

  trend_rows <- vector("list", nrow(facility_index))
  for (i in seq_len(nrow(facility_index))) {
    target_id <- facility_index$provider_ccn[[i]]
    pg <- peer_lookup |> dplyr::filter(.data$provider_ccn == target_id) |> dplyr::slice(1)
    peer_ids <- unlist(strsplit(pg$peer_ccns[[1]], ",", fixed = TRUE))
    target_history <- state_provider_year |> dplyr::filter(.data$provider_ccn == target_id)
    peer_history <- state_provider_year |> dplyr::filter(.data$provider_ccn %in% peer_ids)

    trend_rows[[i]] <- purrr::map_dfr(seq_len(nrow(metric_specs_display)), function(j) {
      mr <- metric_specs_display |> dplyr::slice(j)
      metric <- mr$metric[[1]]
      peer_year <- peer_history |>
        dplyr::filter(!is.na(.data[[metric]]), is.finite(.data[[metric]])) |>
        dplyr::group_by(.data$source_year) |>
        dplyr::summarise(
          peer_p25 = snf_safe_q(.data[[metric]], 0.25),
          peer_median = snf_safe_median(.data[[metric]]),
          peer_p75 = snf_safe_q(.data[[metric]], 0.75),
          .groups = "drop"
        )
      target_year <- target_history |>
        dplyr::transmute(
          source_year,
          target_value = .data[[metric]],
          target_valid_report = dplyr::coalesce(.data$valid_core_benchmark, FALSE),
          target_total_days = as.numeric(.data$total_days),
          target_has_report = dplyr::coalesce(.data$valid_core_benchmark, FALSE) & !is.na(as.numeric(.data$total_days)) & is.finite(as.numeric(.data$total_days)) & as.numeric(.data$total_days) > 0
        )
      dplyr::full_join(peer_year, target_year, by = "source_year") |>
        dplyr::arrange(.data$source_year) |>
        dplyr::mutate(
          provider_ccn = target_id,
          metric = .env$metric,
          label = mr$label[[1]],
          format = mr$format[[1]],
          domain = mr$domain[[1]],
          higher_is_better = mr$higher_is_better[[1]],
          peer_definition = pg$peer_definition[[1]],
          peer_count = pg$peer_count[[1]],
          .before = 1
        )
    })
  }

  trends <- dplyr::bind_rows(trend_rows) |>
    snf_clean_numeric_for_json()
  readr::write_csv(trends, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_trends.csv")))
  jsonlite::write_json(trends, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_trends.json")), dataframe = "rows", auto_unbox = TRUE, na = "null", pretty = FALSE)

  flags <- build_snf_strategy_flags(facility_index, benchmarks, trends)
  readr::write_csv(flags, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_strategy_flags.csv")))
  jsonlite::write_json(flags, file.path(cfg$dashboard_dir, paste0(prefix, "_facility_strategy_flags.json")), dataframe = "rows", auto_unbox = TRUE, na = "null", pretty = FALSE)

  default_target <- facility_index |>
    dplyr::filter(!is.na(.data$total_days), dplyr::coalesce(.data$valid_core_benchmark, TRUE)) |>
    dplyr::arrange(dplyr::desc(.data$total_days)) |>
    dplyr::slice(1)
  readr::write_csv(default_target, file.path(cfg$dashboard_dir, paste0(prefix, "_dashboard_default_target.csv")))

  message("Dashboard data exported to: ", cfg$dashboard_dir)
  list(
    facility_index = facility_index,
    benchmarks = benchmarks,
    trends = trends,
    flags = flags,
    peer_lookup = peer_lookup,
    default_target = default_target
  )
}
