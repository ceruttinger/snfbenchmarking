# bootstrap_national_v1.R
# Install required R packages for a clean clone, verify Quarto CLI, and optionally
# render a national paid report when SNF_TARGET_CCN is set.

options(repos = c(CRAN = "https://cloud.r-project.org"))

required <- unique(c(
  # CMS/HCRIS ingestion + cleaning
  "httr2", "jsonlite", "purrr", "dplyr", "tibble", "stringr", "readr",
  "janitor", "lubridate", "tidyr", "ggplot2", "scales", "xml2", "rvest",
  # dashboard / report
  "plotly", "DT", "htmltools", "bslib", "gt", "glue", "quarto"
))

missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) {
  message("Installing missing R packages: ", paste(missing, collapse = ", "))
  install.packages(missing, dependencies = TRUE)
}

still_missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
if (length(still_missing) > 0) {
  stop(
    "These R packages are still unavailable after install: ",
    paste(still_missing, collapse = ", "),
    call. = FALSE
  )
}

message("All required R packages are available.")

quarto_cli <- Sys.which("quarto")
if (!nzchar(quarto_cli)) {
  stop(
    paste0(
      "The R package 'quarto' is installed, but the Quarto command-line program is not on PATH.\n",
      "Install Quarto for Linux from https://quarto.org/docs/get-started/ and then rerun this script."
    ),
    call. = FALSE
  )
}

message("Quarto CLI: ", quarto_cli)
message("Quarto version: ", system2(quarto_cli, "--version", stdout = TRUE)[1])

# Arrow is useful for the raw HCRIS partitioned lane but is not required for the
# first national paid-report smoke test.
if (!requireNamespace("arrow", quietly = TRUE)) {
  message("Optional package 'arrow' is not installed. That is OK for the first paid-report test.")
}

target_ccn <- trimws(Sys.getenv("SNF_TARGET_CCN", unset = ""))
if (nzchar(target_ccn)) {
  message("Bootstrap complete. Rendering national report for CCN ", target_ccn, " ...")
  source("render_national_paid_report.R")
} else {
  message("Bootstrap complete. To render a report, set SNF_TARGET_CCN and source render_national_paid_report.R.")
}
