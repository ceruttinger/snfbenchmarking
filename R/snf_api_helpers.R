# SNF HCRIS API helper functions
# Project: SNF cost report analytic pipeline

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || (length(x) == 1 && is.na(x))) y else x
}

ensure_packages <- function(pkgs) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) {
    stop(
      "Missing required packages: ", paste(missing, collapse = ", "),
      "\nInstall them with: install.packages(c(",
      paste(sprintf('"%s"', missing), collapse = ", "), "))",
      call. = FALSE
    )
  }
}

cms_get_snf_manifest <- function(
    catalog_url = "https://data.cms.gov/data.json",
    min_year = 2011,
    max_year = NULL,
    prefer = c("CSV", "API")
) {
  ensure_packages(c("httr2", "jsonlite", "purrr", "dplyr", "tibble", "stringr", "readr"))
  prefer <- match.arg(prefer)

  message("Reading CMS catalog: ", catalog_url)
  catalog <- httr2::request(catalog_url) |>
    httr2::req_user_agent("snf-hcris-dashboard-prototype/0.1") |>
    httr2::req_perform() |>
    httr2::resp_body_json(simplifyVector = FALSE)

  datasets <- catalog$dataset
  snf_idx <- which(vapply(datasets, function(x) identical(x$title, "Skilled Nursing Facility Cost Report"), logical(1)))
  if (length(snf_idx) == 0) stop("Could not find 'Skilled Nursing Facility Cost Report' in CMS data.json catalog.")

  snf <- datasets[[snf_idx[1]]]
  dists <- snf$distribution

  manifest_all <- purrr::map_dfr(dists, function(d) {
    title <- d$title %||% NA_character_
    temporal <- d$temporal %||% NA_character_
    year_from_title <- stringr::str_extract(title, "\\d{4}(?=-\\d{2}-\\d{2})")
    year_from_temporal <- stringr::str_extract(temporal, "^\\d{4}")
    year_chr <- dplyr::coalesce(year_from_title, year_from_temporal)
    year <- suppressWarnings(as.integer(year_chr))

    tibble::tibble(
      dataset_title = snf$title %||% NA_character_,
      source_year = year,
      format = d$format %||% NA_character_,
      description = d$description %||% NA_character_,
      title = title,
      modified = d$modified %||% NA_character_,
      temporal = temporal,
      access_url = d$accessURL %||% NA_character_,
      download_url = d$downloadURL %||% NA_character_,
      resources_api = d$resourcesAPI %||% NA_character_
    )
  }) |>
    dplyr::filter(!is.na(.data$source_year), .data$source_year >= min_year)

  if (!is.null(max_year)) {
    manifest_all <- manifest_all |> dplyr::filter(.data$source_year <= max_year)
  }

  manifest <- manifest_all |>
    dplyr::mutate(
      priority = dplyr::case_when(
        prefer == "CSV" & .data$format == "CSV" ~ 1L,
        prefer == "CSV" & .data$format == "API" ~ 2L,
        prefer == "API" & .data$format == "API" ~ 1L,
        prefer == "API" & .data$format == "CSV" ~ 2L,
        TRUE ~ 99L
      ),
      source_url = dplyr::if_else(.data$format == "CSV", .data$download_url, .data$access_url)
    ) |>
    dplyr::filter(!is.na(.data$source_url), .data$source_url != "") |>
    dplyr::arrange(.data$source_year, .data$priority) |>
    dplyr::group_by(.data$source_year) |>
    dplyr::slice(1) |>
    dplyr::ungroup() |>
    dplyr::arrange(.data$source_year)

  if (nrow(manifest) == 0) stop("CMS catalog was found, but no usable CSV/API distributions were found.")

  manifest
}

cms_pull_api_table <- function(base_url, page_size = 5000, max_pages = Inf) {
  ensure_packages(c("httr2", "jsonlite", "purrr", "dplyr", "tibble"))

  stats_url <- paste0(base_url, "/stats")
  stats <- httr2::request(stats_url) |>
    httr2::req_user_agent("snf-hcris-dashboard-prototype/0.1") |>
    httr2::req_perform() |>
    httr2::resp_body_json(simplifyVector = TRUE)

  total_rows <- suppressWarnings(as.integer(stats$total_rows %||% stats$totalRows %||% stats$count))
  if (is.na(total_rows)) stop("Could not determine total rows from CMS API stats endpoint: ", stats_url)

  offsets <- seq(0, total_rows - 1, by = page_size)
  if (is.finite(max_pages)) offsets <- head(offsets, max_pages)

  purrr::map_dfr(offsets, function(offset) {
    url <- paste0(base_url, "?size=", page_size, "&offset=", offset)
    message("  API offset ", offset, " of ", total_rows)
    out <- httr2::request(url) |>
      httr2::req_user_agent("snf-hcris-dashboard-prototype/0.1") |>
      httr2::req_perform() |>
      httr2::resp_body_json(simplifyVector = TRUE)

    tibble::as_tibble(out)
  })
}

cms_read_distribution <- function(row, page_size = 5000, max_pages = Inf) {
  ensure_packages(c("readr", "dplyr", "tibble"))

  fmt <- row$format[[1]]
  url <- row$source_url[[1]]

  message("Pulling ", row$source_year[[1]], " via ", fmt)

  if (identical(fmt, "CSV")) {
    df <- readr::read_csv(
      url,
      col_types = readr::cols(.default = readr::col_character()),
      show_col_types = FALSE,
      progress = TRUE
    )
  } else if (identical(fmt, "API")) {
    df <- cms_pull_api_table(url, page_size = page_size, max_pages = max_pages)
  } else {
    stop("Unsupported format: ", fmt)
  }

  df |>
    dplyr::mutate(
      source_year = row$source_year[[1]],
      source_title = row$title[[1]],
      source_format = fmt,
      source_url = url,
      source_modified = row$modified[[1]],
      pull_timestamp = as.character(Sys.time())
    )
}

save_if_arrow_available <- function(df, path) {
  if (requireNamespace("arrow", quietly = TRUE)) {
    arrow::write_parquet(df, path)
    TRUE
  } else {
    message("Package 'arrow' not installed; skipping parquet write: ", path)
    FALSE
  }
}
