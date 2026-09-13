# SNF HCRIS cleaning and metric helper functions

safe_parse_number <- function(x) {
  if (is.numeric(x)) return(x)
  readr::parse_number(as.character(x), na = c("", "NA", "N/A", "NULL", "null", "."))
}

safe_div <- function(num, den) {
  out <- rep(NA_real_, length(num))
  ok <- !is.na(num) & !is.na(den) & den != 0
  out[ok] <- num[ok] / den[ok]
  out
}

parse_cms_date <- function(x) {
  # CMS public files are not perfectly consistent about date serialization.
  # Critical rule: CMS cost report CSV dates like "10/01/2022" are U.S. M/D/Y,
  # not Y/M/D. Earlier versions tried ymd first and could turn 10/01/2022 into
  # 2010-01-20. This parser prioritizes unambiguous U.S. slash/dash dates.
  if (inherits(x, "Date")) return(x)

  x_chr <- trimws(as.character(x))
  x_chr[x_chr %in% c("", "NA", "N/A", "NULL", "null", ".")] <- NA_character_

  out <- as.Date(rep(NA_real_, length(x_chr)), origin = "1970-01-01")
  has_value <- !is.na(x_chr)
  if (!any(has_value)) return(out)

  is_excel_serial <- grepl("^[0-9]{5}$", x_chr) & !is.na(x_chr)
  if (any(is_excel_serial)) {
    out[is_excel_serial] <- suppressWarnings(as.Date(as.numeric(x_chr[is_excel_serial]), origin = "1899-12-30"))
  }

  still_missing <- has_value & is.na(out)
  is_iso <- still_missing & grepl("^(19|20)[0-9]{2}[-/]?[0-9]{1,2}[-/]?[0-9]{1,2}", x_chr)
  if (any(is_iso)) {
    out[is_iso] <- as.Date(suppressWarnings(lubridate::ymd(x_chr[is_iso], quiet = TRUE)))
  }

  still_missing <- has_value & is.na(out)
  is_us_slash_or_dash <- still_missing & grepl("^[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}(\\s.*)?$", x_chr)
  if (any(is_us_slash_or_dash)) {
    out[is_us_slash_or_dash] <- as.Date(suppressWarnings(lubridate::mdy(x_chr[is_us_slash_or_dash], quiet = TRUE)))
  }

  still_missing <- has_value & is.na(out)
  is_compact_ymd <- still_missing & grepl("^(19|20)[0-9]{6}$", x_chr)
  if (any(is_compact_ymd)) {
    out[is_compact_ymd] <- as.Date(suppressWarnings(lubridate::ymd(x_chr[is_compact_ymd], quiet = TRUE)))
  }

  still_missing <- has_value & is.na(out)
  is_compact_mdy <- still_missing & grepl("^[0-9]{8}$", x_chr)
  if (any(is_compact_mdy)) {
    out[is_compact_mdy] <- as.Date(suppressWarnings(lubridate::mdy(x_chr[is_compact_mdy], quiet = TRUE)))
  }

  still_missing <- has_value & is.na(out)
  if (any(still_missing)) {
    parsed <- suppressWarnings(lubridate::parse_date_time(
      x_chr[still_missing],
      orders = c(
        "mdy HMS", "mdy HM", "mdy IMS p", "mdy IM p", "mdy",
        "ymd HMS", "ymd HM", "ymd IMS p", "ymd IM p", "ymd",
        "dmy HMS", "dmy HM", "dmy",
        "b d Y", "B d Y", "d b Y", "d B Y"
      ),
      tz = "UTC",
      truncated = 0
    ))
    out[still_missing] <- as.Date(parsed)
  }

  out
}

convert_numeric_candidates <- function(df) {
  ensure_packages(c("dplyr", "readr", "stringr"))

  exclude_pattern <- paste(
    c(
      "ccn", "certification", "provider", "facility", "name", "address", "city", "state",
      "zip", "county", "cbsa", "rural", "urban", "control", "type", "date", "status",
      "source", "title", "url", "timestamp", "fiscal_year$", "report_key", "id"
    ),
    collapse = "|"
  )

  for (nm in names(df)) {
    if (stringr::str_detect(nm, exclude_pattern)) next
    if (!is.character(df[[nm]])) next

    non_missing <- df[[nm]][!is.na(df[[nm]]) & df[[nm]] != ""]
    if (length(non_missing) == 0) next

    parsed <- readr::parse_number(non_missing, na = c("", "NA", "N/A", "NULL", "null", "."))
    parse_rate <- mean(!is.na(parsed))

    if (!is.na(parse_rate) && parse_rate >= 0.80) {
      df[[nm]] <- safe_parse_number(df[[nm]])
    }
  }

  df
}

first_existing_col <- function(df, aliases = character(), regex = NULL, required = FALSE, label = NULL) {
  nms <- names(df)
  aliases <- aliases[!is.na(aliases) & aliases != ""]
  exact <- aliases[aliases %in% nms]
  if (length(exact) > 0) return(exact[[1]])

  if (!is.null(regex)) {
    hits <- nms[stringr::str_detect(nms, regex)]
    if (length(hits) > 0) return(hits[[1]])
  }

  if (required) {
    stop("Missing required column", if (!is.null(label)) paste0(" for ", label) else "", call. = FALSE)
  }
  NA_character_
}

val <- function(df, col) {
  if (is.na(col) || !col %in% names(df)) return(rep(NA_real_, nrow(df)))
  if (is.numeric(df[[col]])) return(df[[col]])
  safe_parse_number(df[[col]])
}

chr_val <- function(df, col) {
  if (is.na(col) || !col %in% names(df)) return(rep(NA_character_, nrow(df)))
  as.character(df[[col]])
}

make_bed_size_band <- function(beds) {
  dplyr::case_when(
    is.na(beds) ~ NA_character_,
    beds < 50 ~ "<50",
    beds < 100 ~ "50-99",
    beds < 150 ~ "100-149",
    TRUE ~ "150+"
  )
}

make_snf_nf_mix <- function(snf_days, nf_days, total_days) {
  snf_share <- safe_div(snf_days, total_days)
  nf_share <- safe_div(nf_days, total_days)
  dplyr::case_when(
    is.na(total_days) | total_days <= 0 ~ NA_character_,
    !is.na(snf_share) & snf_share >= 0.75 ~ "SNF-dominant",
    !is.na(nf_share) & nf_share >= 0.75 ~ "NF-dominant",
    !is.na(snf_share) | !is.na(nf_share) ~ "Mixed SNF/NF",
    TRUE ~ NA_character_
  )
}

metric_percentile <- function(x, value) {
  x <- x[!is.na(x)]
  value <- value[[1]]
  if (length(x) == 0 || is.na(value)) return(NA_real_)
  mean(x <= value) * 100
}
