# scripts/01_infer_hcris_coordinate_candidates.R
# Infer *candidate* 2540-10 raw HCRIS coordinates by matching curated public-use
# fields to raw numeric-cell values across overlapping reports.
# Candidates MUST be verified against CMS form instructions before production use.

source("R/snf_api_helpers.R")
source("R/snf_clean_helpers.R")
source("R/snf_hcris_raw_helpers.R")
ensure_packages(c("dplyr", "purrr", "readr", "stringr", "tibble"))

puf_path <- "data/raw/snf_raw.rds"
if (!file.exists(puf_path)) stop("Missing curated public-use input: ", puf_path, ". Run 01_pull_clean_snf_cost_reports.R first.")
puf <- readRDS(puf_path)

coord_year <- suppressWarnings(as.integer(Sys.getenv("SNF_COORDINATE_YEAR", unset = "2024")))
if (is.na(coord_year)) coord_year <- 2024L
form_id <- "CMS-2540-10"

rpt_path <- "data/processed/hcris/snf_hcris_rpt.parquet"
rpt_rds <- sub("\\.parquet$", ".rds", rpt_path)
if (file.exists(rpt_path) && requireNamespace("arrow", quietly = TRUE)) {
  rpt <- tibble::as_tibble(arrow::read_parquet(rpt_path))
} else if (file.exists(rpt_rds)) {
  rpt <- readRDS(rpt_rds)
} else {
  stop("Missing raw HCRIS report table. Run scripts/01_ingest_raw_hcris.R first.")
}
rpt <- rpt |> dplyr::filter(.data$form_id == form_id, .data$source_year == coord_year)
nmrc <- snf_hcris_read_partitions("data/processed/hcris", "nmrc", form_id = form_id, source_year = coord_year)

field_specs <- list(
  total_beds = list(aliases = c("number_of_beds", "total_number_of_beds", "total_beds"), regex = "^(number|total).*beds$"),
  total_days = list(aliases = c("total_days_total", "total_days"), regex = "^total_days_total$|^total_days$"),
  medicare_days = list(aliases = c("total_days_title_xviii", "total_days_medicare", "medicare_days"), regex = "total.*days.*title.*xviii|medicare.*days"),
  medicaid_days = list(aliases = c("total_days_title_xix", "total_days_medicaid", "medicaid_days"), regex = "total.*days.*title.*xix|medicaid.*days"),
  net_patient_revenue = list(aliases = c("net_patient_revenue"), regex = "net.*patient.*revenue"),
  operating_expense = list(aliases = c("less_total_operating_expense", "total_operating_expense", "operating_expense"), regex = "operating.*expense"),
  adjusted_salaries = list(aliases = c("total_salaries_adjusted", "adjusted_salaries"), regex = "salaries.*adjusted|adjusted.*salaries"),
  wage_related_costs = list(aliases = c("wage_related_costs"), regex = "wage.*related.*cost"),
  contract_labor = list(aliases = c("contract_labor"), regex = "contract.*labor"),
  cash = list(aliases = c("cash", "cash_on_hand"), regex = "^cash$|cash.*hand"),
  current_assets = list(aliases = c("total_current_assets", "current_assets"), regex = "current.*assets"),
  current_liabilities = list(aliases = c("total_current_liabilities", "current_liabilities"), regex = "current.*liabilities"),
  total_assets = list(aliases = c("total_assets"), regex = "^total_assets$"),
  total_liabilities = list(aliases = c("total_liabilities"), regex = "^total_liabilities$")
)

ccn_col <- first_existing_col(puf, c("provider_ccn", "ccn", "cms_certification_number", "cms_certification_number_ccn", "provider_number"), regex = "(^|_)ccn$|certification.*number|provider.*number")
fy_end_col <- first_existing_col(puf, c("fiscal_year_end_date", "fy_end_date", "fiscal_period_end_date"), regex = "fiscal.*end.*date|fy.*end.*date")
if (is.na(ccn_col)) stop("Could not resolve CCN in public-use file.")

puf_key <- tibble::tibble(
  provider_ccn = stringr::str_pad(as.character(puf[[ccn_col]]), 6, pad = "0"),
  fy_end_dt = if (!is.na(fy_end_col)) parse_cms_date(puf[[fy_end_col]]) else puf$fiscal_year_end_date_clean,
  puf_row = seq_len(nrow(puf))
)

rpt_key <- rpt |>
  dplyr::transmute(.data$rpt_rec_num, provider_ccn = .data$prvdr_num, fy_end_dt = .data$fy_end_dt) |>
  dplyr::inner_join(puf_key, by = c("provider_ccn", "fy_end_dt"))

max_reports <- suppressWarnings(as.integer(Sys.getenv("SNF_COORDINATE_SAMPLE", unset = "250")))
if (is.na(max_reports) || max_reports < 20) max_reports <- 250L
rpt_key <- rpt_key |> dplyr::slice_head(n = max_reports)

candidate_rows <- purrr::imap_dfr(field_specs, function(spec, semantic_field) {
  puf_col <- first_existing_col(puf, spec$aliases, regex = spec$regex)
  if (is.na(puf_col)) return(NULL)
  puf_values <- suppressWarnings(as.numeric(puf[[puf_col]]))
  targets <- rpt_key |>
    dplyr::transmute(.data$rpt_rec_num, target = puf_values[.data$puf_row]) |>
    dplyr::filter(!is.na(.data$target), is.finite(.data$target))
  if (nrow(targets) < 10) return(NULL)

  nmrc |>
    dplyr::semi_join(targets, by = "rpt_rec_num") |>
    dplyr::inner_join(targets, by = "rpt_rec_num") |>
    dplyr::filter(!is.na(.data$itm_val_num), is.finite(.data$itm_val_num)) |>
    dplyr::mutate(
      abs_diff = abs(.data$itm_val_num - .data$target),
      tolerance = pmax(0.01, abs(.data$target) * 1e-8),
      is_match = .data$abs_diff <= .data$tolerance
    ) |>
    dplyr::group_by(.data$wksht_cd, .data$line_num, .data$clmn_num) |>
    dplyr::summarise(
      compared_reports = dplyr::n_distinct(.data$rpt_rec_num),
      matches = sum(.data$is_match, na.rm = TRUE),
      match_rate = .data$matches / .data$compared_reports,
      median_abs_diff = stats::median(.data$abs_diff, na.rm = TRUE),
      .groups = "drop"
    ) |>
    dplyr::filter(.data$matches >= 3) |>
    dplyr::arrange(dplyr::desc(.data$match_rate), dplyr::desc(.data$matches), .data$median_abs_diff) |>
    dplyr::slice_head(n = 10) |>
    dplyr::mutate(semantic_field = semantic_field, puf_column = puf_col, source_year = coord_year, .before = 1)
})

dir.create("data/processed/hcris", recursive = TRUE, showWarnings = FALSE)
readr::write_csv(candidate_rows, "data/processed/hcris/snf_254010_coordinate_candidates.csv")
message("Coordinate candidates written: data/processed/hcris/snf_254010_coordinate_candidates.csv")
message("These are inference candidates only. Verify against CMS form instructions before approving a production crosswalk.")
invisible(candidate_rows)
