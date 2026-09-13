# scripts/01_build_hcris_report_inventory.R
# Build one current report-inventory table across 2540-10 and 2540-24.

source("R/snf_api_helpers.R")
source("R/snf_hcris_raw_helpers.R")
ensure_packages(c("dplyr", "readr", "stringr", "tibble"))

read_hcris_table <- function(parquet_path, rds_path = sub("\\.parquet$", ".rds", parquet_path)) {
  if (file.exists(parquet_path) && requireNamespace("arrow", quietly = TRUE)) return(arrow::read_parquet(parquet_path))
  if (file.exists(rds_path)) return(readRDS(rds_path))
  stop("Missing raw HCRIS report table. Run scripts/01_ingest_raw_hcris.R first.")
}

rpt <- read_hcris_table("data/processed/hcris/snf_hcris_rpt.parquet") |>
  dplyr::mutate(
    provider_ccn = stringr::str_pad(as.character(.data$prvdr_num), 6, pad = "0"),
    report_days = as.numeric(.data$fy_end_dt - .data$fy_bgn_dt + 1),
    fiscal_year = as.integer(format(.data$fy_end_dt, "%Y")),
    form_priority = dplyr::case_when(
      .data$form_id == "CMS-2540-24" ~ 1L,
      .data$form_id == "CMS-2540-10" ~ 2L,
      TRUE ~ 9L
    )
  )

latest <- rpt |>
  dplyr::arrange(
    .data$provider_ccn,
    dplyr::desc(.data$fy_end_dt),
    .data$form_priority,
    dplyr::desc(.data$proc_dt),
    dplyr::desc(as.numeric(.data$rpt_rec_num))
  ) |>
  dplyr::group_by(.data$provider_ccn) |>
  dplyr::slice(1) |>
  dplyr::ungroup()

dir.create("data/processed/hcris", recursive = TRUE, showWarnings = FALSE)
saveRDS(rpt, "data/processed/hcris/snf_hcris_report_inventory.rds")
saveRDS(latest, "data/processed/hcris/snf_hcris_latest_report_by_ccn.rds")
readr::write_csv(latest, "data/processed/hcris/snf_hcris_latest_report_by_ccn.csv")
readr::write_csv(
  rpt |> dplyr::count(.data$form_id, .data$source_year, .data$rpt_stus_cd, name = "reports"),
  "data/processed/hcris/snf_hcris_inventory_diagnostics.csv"
)
message("HCRIS report inventory built: ", nrow(rpt), " reports; ", nrow(latest), " latest CCNs.")
invisible(list(all_reports = rpt, latest = latest))
