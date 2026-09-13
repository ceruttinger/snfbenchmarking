# scripts/01_discover_raw_hcris_manifest.R
# Discover current CMS raw HCRIS SNF files for both 2540-10 and 2540-24.

source("R/snf_api_helpers.R")
source("R/snf_hcris_raw_helpers.R")
ensure_packages(c("readr", "dplyr", "xml2", "rvest", "purrr", "stringr", "tibble"))

min_year <- suppressWarnings(as.integer(Sys.getenv("SNF_HCRIS_MIN_YEAR", unset = "2023")))
max_year_raw <- Sys.getenv("SNF_HCRIS_MAX_YEAR", unset = "")
max_year <- if (nzchar(max_year_raw)) suppressWarnings(as.integer(max_year_raw)) else NULL

manifest <- snf_hcris_discover_manifest(min_year = min_year, max_year = max_year)
dir.create("data/raw/hcris", recursive = TRUE, showWarnings = FALSE)
readr::write_csv(manifest, "data/raw/hcris/snf_hcris_raw_manifest.csv")
message("Raw HCRIS manifest written: data/raw/hcris/snf_hcris_raw_manifest.csv")
print(manifest)
invisible(manifest)
