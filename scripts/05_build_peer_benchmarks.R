# scripts/05_build_peer_benchmarks.R
# Build latest-valid peer groups and percentile benchmarks.

build_snf_peer_benchmarks <- function(provider_year, latest_valid, metric_specs, cfg = snf_v041_config()) {
  snf_v041_prepare_dirs(cfg)

  metric_specs <- metric_specs |>
    dplyr::filter(dplyr::coalesce(.data$display_in_dashboard, TRUE)) |>
    dplyr::filter(.data$metric %in% names(provider_year), .data$metric %in% names(latest_valid))

  latest_state <- snf_filter_state(latest_valid, cfg$state_filter)

  if (nrow(latest_state) == 0) stop("No latest-valid rows found for state filter: ", cfg$state_filter)

  targets <- latest_state |>
    dplyr::filter(dplyr::coalesce(.data$valid_core_benchmark, TRUE)) |>
    dplyr::arrange(.data$facility_name, .data$city, .data$provider_ccn)

  if (length(cfg$target_ccns) > 0) {
    targets <- targets |> dplyr::filter(as.character(.data$provider_ccn) %in% cfg$target_ccns)
    if (nrow(targets) == 0) stop("SNF_TARGET_CCNS did not match any latest-valid facilities.")
  }

  benchmark_rows <- vector("list", nrow(targets))
  peer_lookup_rows <- vector("list", nrow(targets))

  for (i in seq_len(nrow(targets))) {
    target_row <- targets |> dplyr::slice(i)
    pg <- snf_get_peer_ids(target_row, latest_state, peer_minimum = cfg$peer_minimum)
    peer_group <- latest_state |> dplyr::filter(.data$provider_ccn %in% pg$ids)

    peer_lookup_rows[[i]] <- tibble::tibble(
      provider_ccn = target_row$provider_ccn[[1]],
      peer_definition = pg$definition,
      peer_count = length(unique(pg$ids)),
      peer_ccns = paste(unique(pg$ids), collapse = ",")
    )

    benchmark_rows[[i]] <- purrr::map_dfr(seq_len(nrow(metric_specs)), function(j) {
      snf_benchmark_one_metric(target_row, peer_group, metric_specs |> dplyr::slice(j)) |>
        dplyr::mutate(
          peer_definition = pg$definition,
          peer_count = length(unique(pg$ids)),
          .after = .data$difference_from_peer_median
        )
    })
  }

  benchmarks <- dplyr::bind_rows(benchmark_rows) |>
    snf_clean_numeric_for_json()
  peer_lookup <- dplyr::bind_rows(peer_lookup_rows)

  saveRDS(benchmarks, cfg$peer_benchmark_output)
  saveRDS(peer_lookup, cfg$peer_lookup_output)
  prefix <- cfg$output_prefix
  readr::write_csv(benchmarks, file.path(cfg$processed_dir, paste0("snf_peer_benchmarks_v041_", prefix, ".csv")))
  readr::write_csv(peer_lookup, file.path(cfg$processed_dir, paste0("snf_peer_lookup_v041_", prefix, ".csv")))

  message("Peer benchmarks written: ", cfg$peer_benchmark_output)
  list(benchmarks = benchmarks, peer_lookup = peer_lookup, latest_state = latest_state, targets = targets)
}
