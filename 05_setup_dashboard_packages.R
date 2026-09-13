# Install packages needed for the static selector dashboard and client report.
# v0.11 fix: ensure_packages() is defined in snf_api_helpers.R, so source it first.
source("R/snf_api_helpers.R")
source("R/snf_clean_helpers.R")

ensure_packages(c(
  "dplyr", "tidyr", "readr", "stringr", "tibble", "purrr", "jsonlite",
  "scales", "ggplot2", "plotly", "DT", "htmltools", "bslib", "gt", "glue", "quarto"
))
message("Dashboard/report package setup complete.")
