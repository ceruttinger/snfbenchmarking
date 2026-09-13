# 09_build_national_facility_index.R
# Create the nationwide facility search/index artifact without computing benchmarks.
source("scripts/00_config.R")
source("R/snf_v041_helpers.R")
source("scripts/02_build_provider_year_public.R")
source("scripts/04_build_latest_valid_reports.R")
source("scripts/07_export_national_facility_index.R")

Sys.setenv(SNF_DASHBOARD_STATE = "ALL", SNF_OUTPUT_PREFIX = "national")
cfg <- snf_v041_config()
provider_year <- build_snf_provider_year_public(cfg)
latest_valid <- build_snf_latest_valid_reports(provider_year, cfg)
national_index <- export_national_facility_index(latest_valid, cfg)
invisible(national_index)
