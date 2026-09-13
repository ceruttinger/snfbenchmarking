# 00_setup_packages.R
# Run this once if you do not already have the required packages.

required <- c(
  "httr2", "jsonlite", "purrr", "dplyr", "tibble", "stringr", "readr",
  "janitor", "lubridate", "tidyr", "ggplot2", "scales", "xml2", "rvest"
)

optional <- c("arrow")

install_if_missing <- function(pkgs) {
  missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0) install.packages(missing)
}

install_if_missing(required)
message("Required packages installed or already available.")
message("Optional but recommended for parquet files: install.packages('arrow')")
