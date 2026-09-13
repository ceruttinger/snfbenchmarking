# R/snf_hcris_raw_helpers.R
# Helpers for discovering and ingesting raw CMS HCRIS SNF files.
# Supports both CMS-2540-10 and CMS-2540-24 without hard-coding yearly ZIP URLs.

`%||%` <- function(x, y) {
  if (is.null(x) || length(x) == 0 || (length(x) == 1 && is.na(x))) y else x
}

snf_hcris_rpt_names <- function() {
  c(
    "rpt_rec_num", "prvdr_ctrl_type_cd", "prvdr_num", "npi", "rpt_stus_cd",
    "fy_bgn_dt", "fy_end_dt", "proc_dt", "initl_rpt_sw", "last_rpt_sw",
    "trnsmtl_num", "fi_num", "adr_vndr_cd", "fi_creat_dt", "util_cd",
    "npr_dt", "spec_ind", "fi_rcpt_dt"
  )
}

snf_hcris_nmrc_names <- function() {
  c("rpt_rec_num", "wksht_cd", "line_num", "clmn_num", "itm_val_num")
}

snf_hcris_alpha_names <- function() {
  c("rpt_rec_num", "wksht_cd", "line_num", "clmn_num", "itm_val_alpha")
}

snf_hcris_parse_date <- function(x) {
  x <- trimws(as.character(x))
  x[x == ""] <- NA_character_
  as.Date(x, tryFormats = c("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"))
}

snf_hcris_abs_url <- function(href, base = "https://www.cms.gov") {
  ifelse(
    grepl("^https?://", href),
    href,
    paste0(base, ifelse(startsWith(href, "/"), "", "/"), href)
  )
}

snf_hcris_form_id <- function(facility_type) {
  ft <- toupper(trimws(as.character(facility_type)))
  dplyr::case_when(
    ft %in% c("SNF-2010", "SNF-10") ~ "CMS-2540-10",
    ft %in% c("SNF-2024", "SNF-24") ~ "CMS-2540-24",
    TRUE ~ NA_character_
  )
}

snf_hcris_resolve_zip_url <- function(landing_url) {
  ensure_packages(c("rvest", "stringr"))
  if (is.na(landing_url) || !nzchar(landing_url)) return(NA_character_)

  doc <- tryCatch(rvest::read_html(landing_url), error = function(e) NULL)
  if (is.null(doc)) return(NA_character_)

  links <- rvest::html_elements(doc, "a")
  if (length(links) == 0) return(NA_character_)
  hrefs <- rvest::html_attr(links, "href")
  labels <- stringr::str_squish(rvest::html_text2(links))

  is_zip <- (!is.na(hrefs) & grepl("\\.zip(?:$|[?#])", hrefs, ignore.case = TRUE)) |
    (!is.na(labels) & grepl("\\bZIP\\b", labels, ignore.case = TRUE))
  idx <- which(is_zip & !is.na(hrefs) & nzchar(hrefs))
  if (length(idx) == 0) return(NA_character_)

  snf_hcris_abs_url(hrefs[idx[[1]]])
}

snf_hcris_read_manifest_override <- function(path) {
  if (is.null(path) || !nzchar(path) || !file.exists(path)) return(tibble::tibble())
  ensure_packages(c("readr", "dplyr", "tibble"))
  out <- readr::read_csv(path, show_col_types = FALSE)
  required <- c("source_year", "form_id", "download_url")
  missing <- setdiff(required, names(out))
  if (length(missing) > 0) {
    stop("HCRIS manifest override is missing columns: ", paste(missing, collapse = ", "))
  }
  out |>
    dplyr::transmute(
      source_year = as.integer(.data$source_year),
      facility_type = dplyr::coalesce(as.character(.data$facility_type), NA_character_),
      form_id = as.character(.data$form_id),
      landing_url = dplyr::coalesce(as.character(.data$landing_url), NA_character_),
      download_url = as.character(.data$download_url),
      discovered_from = paste0("override:", path),
      manifest_priority = 0L
    )
}

snf_hcris_discover_manifest <- function(
    page_url = "https://www.cms.gov/data-research/statistics-trends-and-reports/cost-reports/cost-reports-fiscal-year",
    min_year = 2011,
    max_year = NULL,
    override_path = Sys.getenv("SNF_HCRIS_MANIFEST_OVERRIDE", unset = "data/config/snf_hcris_manifest_override.csv")
) {
  ensure_packages(c("xml2", "rvest", "dplyr", "purrr", "stringr", "tibble", "readr"))

  doc <- rvest::read_html(page_url)
  rows <- rvest::html_elements(doc, "tr")

  discovered <- purrr::map_dfr(rows, function(row) {
    cells <- rvest::html_elements(row, "th, td")
    txt <- stringr::str_squish(rvest::html_text2(row))
    if (!grepl("SNF-(2010|10|2024|24)", txt, ignore.case = TRUE)) return(NULL)

    cell_txt <- stringr::str_squish(rvest::html_text2(cells))
    facility_hit <- cell_txt[grepl("^SNF-(2010|10|2024|24)$", cell_txt, ignore.case = TRUE)]
    if (length(facility_hit) == 0) {
      facility_hit <- stringr::str_extract(toupper(txt), "SNF-(2010|10|2024|24)")
    }
    facility_type <- facility_hit[[1]]
    form_id <- snf_hcris_form_id(facility_type)
    if (is.na(form_id)) return(NULL)

    year <- suppressWarnings(as.integer(stringr::str_extract(txt, "\\b20\\d{2}\\b")))
    if (is.na(year)) return(NULL)

    links <- rvest::html_elements(row, "a")
    hrefs <- rvest::html_attr(links, "href")
    labels <- stringr::str_squish(rvest::html_text2(links))
    idx <- which(labels == as.character(year))
    if (length(idx) == 0) idx <- which(!is.na(hrefs) & nzchar(hrefs))
    if (length(idx) == 0) return(NULL)
    landing_url <- snf_hcris_abs_url(hrefs[idx[[1]]])

    tibble::tibble(
      source_year = year,
      facility_type = facility_type,
      form_id = form_id,
      landing_url = landing_url,
      download_url = snf_hcris_resolve_zip_url(landing_url),
      discovered_from = page_url,
      manifest_priority = 1L
    )
  }) |>
    dplyr::filter(.data$source_year >= min_year)

  overrides <- snf_hcris_read_manifest_override(override_path)
  manifest <- dplyr::bind_rows(discovered, overrides) |>
    dplyr::filter(.data$source_year >= min_year)
  if (!is.null(max_year)) manifest <- manifest |> dplyr::filter(.data$source_year <= max_year)

  manifest <- manifest |>
    dplyr::arrange(.data$source_year, .data$form_id, .data$manifest_priority) |>
    dplyr::group_by(.data$source_year, .data$form_id) |>
    dplyr::slice(1) |>
    dplyr::ungroup() |>
    dplyr::arrange(.data$source_year, .data$form_id) |>
    dplyr::select(-.data$manifest_priority)

  if (nrow(manifest) == 0) stop("No raw SNF HCRIS file rows were discovered from CMS.")
  manifest
}

snf_hcris_download_zip <- function(url, destfile, refresh = FALSE) {
  ensure_packages(c("httr2"))
  if (is.na(url) || !nzchar(url) || !grepl("^https?://", url)) {
    stop(
      "No direct HCRIS ZIP URL is available for this manifest row. ",
      "Check the CMS landing page or add a row to data/config/snf_hcris_manifest_override.csv."
    )
  }
  dir.create(dirname(destfile), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(destfile) && !refresh && file.info(destfile)$size > 0) return(destfile)
  message("Downloading raw HCRIS: ", url)
  httr2::request(url) |>
    httr2::req_user_agent("snfbenchmarking.com HCRIS analytics/1.0") |>
    httr2::req_retry(max_tries = 3) |>
    httr2::req_perform(path = destfile)
  destfile
}

snf_hcris_find_member <- function(zipfile, type = c("rpt", "nmrc", "alpha")) {
  type <- match.arg(type)
  members <- utils::unzip(zipfile, list = TRUE)$Name
  members_low <- tolower(members)
  keep <- switch(
    type,
    rpt = grepl("(^|[/_])rpt([_.]|$)|rpt\\.csv$", members_low),
    nmrc = grepl("nmrc", members_low) & !grepl("alph", members_low),
    alpha = grepl("alph", members_low)
  )
  hit <- members[keep]
  if (length(hit) == 0) return(NA_character_)
  hit <- hit[order(!grepl("\\.(csv|txt)$", tolower(hit)), nchar(hit))]
  hit[[1]]
}

snf_hcris_read_zip_member <- function(zipfile, member, col_names, col_types = NULL) {
  ensure_packages(c("readr"))
  if (is.na(member) || !nzchar(member)) stop("Requested HCRIS member was not found in: ", zipfile)
  con <- unz(zipfile, member, open = "rb")
  on.exit(close(con), add = TRUE)
  readr::read_csv(
    con,
    col_names = col_names,
    col_types = col_types %||% readr::cols(.default = readr::col_character()),
    na = c("", "NA"),
    trim_ws = TRUE,
    show_col_types = FALSE,
    progress = FALSE
  )
}

snf_hcris_read_rpt <- function(zipfile, source_year, form_id) {
  member <- snf_hcris_find_member(zipfile, "rpt")
  out <- snf_hcris_read_zip_member(zipfile, member, snf_hcris_rpt_names())
  out |>
    dplyr::mutate(
      source_year = as.integer(source_year),
      form_id = form_id,
      rpt_rec_num = as.character(.data$rpt_rec_num),
      prvdr_num = stringr::str_pad(as.character(.data$prvdr_num), 6, pad = "0"),
      fy_bgn_dt = snf_hcris_parse_date(.data$fy_bgn_dt),
      fy_end_dt = snf_hcris_parse_date(.data$fy_end_dt),
      proc_dt = snf_hcris_parse_date(.data$proc_dt),
      fi_creat_dt = snf_hcris_parse_date(.data$fi_creat_dt),
      npr_dt = snf_hcris_parse_date(.data$npr_dt),
      fi_rcpt_dt = snf_hcris_parse_date(.data$fi_rcpt_dt)
    )
}

snf_hcris_read_nmrc <- function(zipfile, source_year, form_id) {
  member <- snf_hcris_find_member(zipfile, "nmrc")
  out <- snf_hcris_read_zip_member(zipfile, member, snf_hcris_nmrc_names())
  out |>
    dplyr::mutate(
      source_year = as.integer(source_year),
      form_id = form_id,
      rpt_rec_num = as.character(.data$rpt_rec_num),
      wksht_cd = trimws(as.character(.data$wksht_cd)),
      line_num = stringr::str_pad(trimws(as.character(.data$line_num)), 5, pad = "0"),
      clmn_num = stringr::str_pad(trimws(as.character(.data$clmn_num)), 4, pad = "0"),
      itm_val_num = suppressWarnings(as.numeric(.data$itm_val_num))
    )
}

snf_hcris_read_alpha <- function(zipfile, source_year, form_id) {
  member <- snf_hcris_find_member(zipfile, "alpha")
  out <- snf_hcris_read_zip_member(zipfile, member, snf_hcris_alpha_names())
  out |>
    dplyr::mutate(
      source_year = as.integer(source_year),
      form_id = form_id,
      rpt_rec_num = as.character(.data$rpt_rec_num),
      wksht_cd = trimws(as.character(.data$wksht_cd)),
      line_num = stringr::str_pad(trimws(as.character(.data$line_num)), 5, pad = "0"),
      clmn_num = stringr::str_pad(trimws(as.character(.data$clmn_num)), 4, pad = "0"),
      itm_val_alpha = trimws(as.character(.data$itm_val_alpha))
    )
}

snf_hcris_partition_dir <- function(root, table, form_id, source_year) {
  file.path(
    root,
    table,
    paste0("form_id=", gsub("[^A-Za-z0-9._-]", "_", form_id)),
    paste0("source_year=", as.integer(source_year))
  )
}

snf_hcris_write_partition <- function(df, root, table, form_id, source_year) {
  out_dir <- snf_hcris_partition_dir(root, table, form_id, source_year)
  dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
  if (requireNamespace("arrow", quietly = TRUE)) {
    path <- file.path(out_dir, "part-0001.parquet")
    arrow::write_parquet(df, path)
  } else {
    path <- file.path(out_dir, "part-0001.rds")
    saveRDS(df, path)
  }
  path
}

snf_hcris_read_partitions <- function(root, table, form_id = NULL, source_year = NULL) {
  table_root <- file.path(root, table)
  if (!dir.exists(table_root)) stop("Missing HCRIS partition directory: ", table_root)
  files <- list.files(table_root, pattern = "\\.(parquet|rds)$", recursive = TRUE, full.names = TRUE)
  if (!is.null(form_id)) {
    form_token <- paste0("form_id=", gsub("[^A-Za-z0-9._-]", "_", form_id))
    files <- files[grepl(form_token, files, fixed = TRUE)]
  }
  if (!is.null(source_year)) {
    year_token <- paste0("source_year=", as.integer(source_year))
    files <- files[grepl(year_token, files, fixed = TRUE)]
  }
  if (length(files) == 0) stop("No matching HCRIS partitions found for table=", table)

  dplyr::bind_rows(lapply(files, function(path) {
    if (grepl("\\.parquet$", path, ignore.case = TRUE)) {
      if (!requireNamespace("arrow", quietly = TRUE)) stop("Install arrow to read Parquet partition: ", path)
      tibble::as_tibble(arrow::read_parquet(path))
    } else {
      readRDS(path)
    }
  }))
}

snf_hcris_write_parquet <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  if (requireNamespace("arrow", quietly = TRUE)) {
    arrow::write_parquet(df, path)
    return(TRUE)
  }
  saveRDS(df, sub("\\.parquet$", ".rds", path))
  FALSE
}
