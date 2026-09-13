# 08_build_national_report_data.R
# Build benchmark/report JSON for one or more CCNs anywhere in the U.S.
# Example:
#   Sys.setenv(SNF_TARGET_CCNS = "465095", SNF_DASHBOARD_STATE = "ALL", SNF_OUTPUT_PREFIX = "national")
#   source("08_build_national_report_data.R")

if (!nzchar(Sys.getenv("SNF_TARGET_CCNS", unset = ""))) {
  stop("Set SNF_TARGET_CCNS to one or more comma-separated CCNs before building a national report.")
}
Sys.setenv(SNF_DASHBOARD_STATE = "ALL")
Sys.setenv(SNF_OUTPUT_PREFIX = "national")
source("07_build_snf_v041_data_layer.R")
