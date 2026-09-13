# R/snf_v041_helpers.R
# Shared helper functions for the SNF dashboard v0.41 data layer.

snf_clean_numeric_for_json <- function(df) {
  df |>
    dplyr::mutate(dplyr::across(dplyr::where(is.numeric), ~ ifelse(is.finite(.x), .x, NA_real_)))
}

snf_state_values <- function(state_filter) {
  state_filter <- toupper(trimws(as.character(state_filter)))
  if (length(state_filter) == 0 || is.na(state_filter) || state_filter %in% c("", "ALL", "US", "USA", "NATIONAL")) {
    return(character(0))
  }
  state_name <- state.name[match(state_filter, state.abb)]
  unique(stats::na.omit(c(state_filter, toupper(state_name))))
}

snf_filter_state <- function(df, state_filter) {
  vals <- snf_state_values(state_filter)
  if (length(vals) == 0) return(df)
  df |> dplyr::filter(toupper(.data$state) %in% vals)
}

snf_sum_with_na <- function(...) {
  mat <- cbind(...)
  out <- rowSums(mat, na.rm = TRUE)
  out[rowSums(!is.na(mat)) == 0] <- NA_real_
  out
}

snf_safe_metric_value <- function(df, metric) {
  if (!metric %in% names(df)) return(rep(NA_real_, nrow(df)))
  as.numeric(df[[metric]])
}

snf_bool <- function(x) {
  if (is.logical(x)) return(x)
  x_chr <- toupper(trimws(as.character(x)))
  dplyr::case_when(
    x_chr %in% c("TRUE", "T", "1", "YES", "Y") ~ TRUE,
    x_chr %in% c("FALSE", "F", "0", "NO", "N") ~ FALSE,
    TRUE ~ NA
  )
}

snf_safe_q <- function(x, p) {
  x <- x[!is.na(x) & is.finite(x)]
  if (length(x) == 0) return(NA_real_)
  as.numeric(stats::quantile(x, probs = p, na.rm = TRUE, names = FALSE))
}

snf_safe_median <- function(x) {
  x <- x[!is.na(x) & is.finite(x)]
  if (length(x) == 0) return(NA_real_)
  stats::median(x, na.rm = TRUE)
}

snf_safe_percentile <- function(x, value) {
  x <- x[!is.na(x) & is.finite(x)]
  value <- suppressWarnings(as.numeric(value[[1]]))
  if (length(x) == 0 || is.na(value) || !is.finite(value)) return(NA_real_)
  mean(x <= value)
}

snf_report_period_status <- function(report_days) {
  dplyr::case_when(
    is.na(report_days) ~ "missing",
    report_days < 300 ~ "short",
    report_days > 430 ~ "long",
    TRUE ~ "plausible"
  )
}

snf_latest_valid_provider_year <- function(provider_year) {
  provider_year |>
    dplyr::mutate(
      valid_core_benchmark = dplyr::coalesce(.data$valid_core_benchmark, TRUE),
      report_period_status = if ("report_period_status" %in% names(provider_year)) .data$report_period_status else snf_report_period_status(.data$report_days),
      latest_valid_priority = dplyr::case_when(
        .data$valid_core_benchmark & .data$report_period_status == "plausible" ~ 1L,
        .data$valid_core_benchmark ~ 2L,
        TRUE ~ 3L
      ),
      fiscal_year_end_date_sort = suppressWarnings(as.Date(.data$fiscal_year_end_date))
    ) |>
    dplyr::arrange(
      .data$provider_ccn,
      .data$latest_valid_priority,
      dplyr::desc(.data$source_year),
      dplyr::desc(.data$fiscal_year_end_date_sort),
      dplyr::desc(.data$total_days)
    ) |>
    dplyr::group_by(.data$provider_ccn) |>
    dplyr::slice(1) |>
    dplyr::ungroup() |>
    dplyr::select(-dplyr::any_of(c("latest_valid_priority", "fiscal_year_end_date_sort")))
}

snf_get_peer_ids <- function(target_row, latest_df, peer_minimum = 5L) {
  target_state <- as.character(target_row$state[[1]])
  target_rural <- as.character(target_row$rural_urban[[1]])
  target_bed_band <- as.character(target_row$bed_size_band[[1]])
  target_ccn <- as.character(target_row$provider_ccn[[1]])

  has_value <- function(x) length(x) > 0 && !is.na(x) && nzchar(trimws(x))

  base <- latest_df |>
    dplyr::filter(as.character(.data$provider_ccn) != target_ccn) |>
    dplyr::filter(dplyr::coalesce(.data$valid_core_benchmark, TRUE))

  same_state <- if (has_value(target_state)) {
    base |> dplyr::filter(.data$state == target_state)
  } else {
    base[0, , drop = FALSE]
  }

  filter_match <- function(df, use_rural = FALSE, use_bed = FALSE) {
    out <- df
    if (use_rural && has_value(target_rural)) out <- out |> dplyr::filter(.data$rural_urban == target_rural)
    if (use_bed && has_value(target_bed_band)) out <- out |> dplyr::filter(.data$bed_size_band == target_bed_band)
    out
  }

  candidates <- list(
    list(df = filter_match(same_state, TRUE, TRUE), label = "Same state + same rural/urban + same bed-size band"),
    list(df = filter_match(same_state, FALSE, TRUE), label = "Same state + same bed-size band fallback"),
    list(df = filter_match(same_state, TRUE, FALSE), label = "Same state + same rural/urban fallback"),
    list(df = same_state, label = "Same state fallback"),
    list(df = filter_match(base, TRUE, TRUE), label = "National same rural/urban + same bed-size band fallback"),
    list(df = filter_match(base, FALSE, TRUE), label = "National same bed-size band fallback"),
    list(df = filter_match(base, TRUE, FALSE), label = "National same rural/urban fallback"),
    list(df = base, label = "National fallback")
  )

  for (candidate in candidates) {
    ids <- unique(as.character(candidate$df$provider_ccn))
    ids <- ids[!is.na(ids) & nzchar(ids)]
    if (length(ids) >= peer_minimum) {
      return(list(ids = ids, definition = candidate$label))
    }
  }

  ids <- unique(as.character(base$provider_ccn))
  ids <- ids[!is.na(ids) & nzchar(ids)]
  list(ids = ids, definition = "All available national peers (small peer universe)")
}

snf_benchmark_one_metric <- function(target_row, peer_group, metric_row) {
  metric <- metric_row$metric[[1]]
  target_value <- if (metric %in% names(target_row)) target_row[[metric]][[1]] else NA_real_
  vals <- if (metric %in% names(peer_group)) peer_group[[metric]] else numeric(0)
  peer_median <- snf_safe_median(vals)

  tibble::tibble(
    provider_ccn = target_row$provider_ccn[[1]],
    metric = metric,
    label = metric_row$label[[1]],
    format = metric_row$format[[1]],
    domain = metric_row$domain[[1]],
    higher_is_better = metric_row$higher_is_better[[1]],
    target_value = as.numeric(target_value),
    peer_n = sum(!is.na(vals) & is.finite(vals)),
    peer_p10 = snf_safe_q(vals, 0.10),
    peer_p25 = snf_safe_q(vals, 0.25),
    peer_median = peer_median,
    peer_p75 = snf_safe_q(vals, 0.75),
    peer_p90 = snf_safe_q(vals, 0.90),
    target_percentile = snf_safe_percentile(vals, target_value),
    difference_from_peer_median = as.numeric(target_value - peer_median)
  )
}

snf_trend_delta <- function(tdf, metric, years_back = 3) {
  z <- tdf |>
    dplyr::filter(.data$metric == metric) |>
    dplyr::arrange(.data$source_year)
  if (nrow(z) == 0) return(NA_real_)
  latest_y <- suppressWarnings(max(z$source_year, na.rm = TRUE))
  if (!is.finite(latest_y)) return(NA_real_)
  latest_v <- z |>
    dplyr::filter(.data$source_year == latest_y) |>
    dplyr::slice_tail(n = 1) |>
    dplyr::pull(.data$target_value)
  prior <- z |>
    dplyr::filter(.data$source_year <= latest_y - years_back) |>
    dplyr::slice_tail(n = 1)
  if (length(latest_v) == 0 || nrow(prior) == 0) return(NA_real_)
  as.numeric(latest_v[[1]] - prior$target_value[[1]])
}
