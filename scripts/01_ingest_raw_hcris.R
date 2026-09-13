# scripts/01_ingest_raw_hcris.R
# Download and normalize raw CMS HCRIS SNF RPT/NMRC/ALPHNMRC files.
# Large cell tables are written as form/year partitions instead of being held
# across multiple years in memory.

source("R/snf_api_helpers.R")
source("R/snf_hcris_raw_helpers.R")
ensure_packages(c("dplyr", "purrr", "readr", "stringr", "tibble", "httr2"))

manifest_path <- "data/raw/hcris/snf_hcris_raw_manifest.csv"
if (!file.exists(manifest_path)) source("scripts/01_discover_raw_hcris_manifest.R")
manifest <- readr::read_csv(manifest_path, show_col_types = FALSE)

forms_raw <- Sys.getenv("SNF_HCRIS_FORMS", unset = "")
years_raw <- Sys.getenv("SNF_HCRIS_YEARS", unset = "")
refresh <- tolower(Sys.getenv("SNF_HCRIS_REFRESH", unset = "false")) %in% c("1", "true", "yes", "y")
include_cells <- tolower(Sys.getenv("SNF_HCRIS_INCLUDE_CELLS", unset = "true")) %in% c("1", "true", "yes", "y")

if (nzchar(forms_raw)) {
  forms <- trimws(strsplit(forms_raw, ",", fixed = TRUE)[[1]])
  manifest <- manifest |> dplyr::filter(.data$form_id %in% forms)
}
if (nzchar(years_raw)) {
  years <- suppressWarnings(as.integer(trimws(strsplit(years_raw, ",", fixed = TRUE)[[1]])))
  manifest <- manifest |> dplyr::filter(.data$source_year %in% years)
}
if (nrow(manifest) == 0) stop("No HCRIS files remain after SNF_HCRIS_FORMS/SNF_HCRIS_YEARS filters.")

missing_url <- manifest |> dplyr::filter(is.na(.data$download_url) | !nzchar(.data$download_url))
if (nrow(missing_url) > 0) {
  print(missing_url |> dplyr::select(.data$source_year, .data$form_id, .data$landing_url))
  stop(
    "One or more HCRIS manifest rows do not have a direct ZIP URL. ",
    "Add the direct CMS ZIP URL to data/config/snf_hcris_manifest_override.csv and rerun discovery."
  )
}

dir.create("data/raw/hcris/zips", recursive = TRUE, showWarnings = FALSE)
processed_root <- "data/processed/hcris"
dir.create(processed_root, recursive = TRUE, showWarnings = FALSE)

rpt_all <- list()
count_rows <- list()
coord_inventory_rows <- list()

for (i in seq_len(nrow(manifest))) {
  row <- manifest[i, ]
  form_id <- row$form_id[[1]]
  source_year <- row$source_year[[1]]
  form_short <- gsub("CMS-", "", form_id, fixed = TRUE)
  zip_name <- paste0("snf_", gsub("-", "", form_short), "_", source_year, ".zip")
  zip_path <- file.path("data/raw/hcris/zips", zip_name)
  snf_hcris_download_zip(row$download_url[[1]], zip_path, refresh = refresh)

  message("Reading RPT: ", form_id, " FY", source_year)
  rpt <- snf_hcris_read_rpt(zip_path, source_year, form_id)
  snf_hcris_write_partition(rpt, processed_root, "rpt", form_id, source_year)
  rpt_all[[length(rpt_all) + 1L]] <- rpt
  count_rows[[length(count_rows) + 1L]] <- tibble::tibble(
    form_id = form_id, source_year = as.integer(source_year), reports = nrow(rpt)
  )

  if (include_cells) {
    message("Reading NMRC: ", form_id, " FY", source_year)
    nmrc <- snf_hcris_read_nmrc(zip_path, source_year, form_id)
    snf_hcris_write_partition(nmrc, processed_root, "nmrc", form_id, source_year)
    coord_inventory_rows[[length(coord_inventory_rows) + 1L]] <- nmrc |>
      dplyr::count(.data$form_id, .data$source_year, .data$wksht_cd, .data$line_num, .data$clmn_num, name = "rows")
    rm(nmrc)
    invisible(gc())

    message("Reading ALPHNMRC: ", form_id, " FY", source_year)
    alpha <- snf_hcris_read_alpha(zip_path, source_year, form_id)
    snf_hcris_write_partition(alpha, processed_root, "alpha", form_id, source_year)
    rm(alpha)
    invisible(gc())
  }
}

rpt <- dplyr::bind_rows(rpt_all)
snf_hcris_write_parquet(rpt, file.path(processed_root, "snf_hcris_rpt.parquet"))
readr::write_csv(dplyr::bind_rows(count_rows), file.path(processed_root, "snf_hcris_report_counts.csv"))

if (include_cells) {
  readr::write_csv(
    dplyr::bind_rows(coord_inventory_rows) |>
      dplyr::group_by(.data$form_id, .data$source_year, .data$wksht_cd, .data$line_num, .data$clmn_num) |>
      dplyr::summarise(rows = sum(.data$rows), .groups = "drop") |>
      dplyr::arrange(.data$form_id, .data$source_year, dplyr::desc(.data$rows)),
    file.path(processed_root, "snf_hcris_numeric_coordinate_inventory.csv")
  )
}

message("Raw HCRIS ingest complete. Cell tables are partitioned under data/processed/hcris/{nmrc,alpha}/.")
invisible(list(rpt = rpt, manifest = manifest))
