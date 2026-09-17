# Dialysis Benchmarking

National renal dialysis benchmarking module for the existing HCRIS provider benchmarking project.

## Sources

- CMS HCRIS Renal Dialysis Facility Cost Report, Form CMS-265-11 (2011-present release series)
- CMS dialysis facility/provider data for facility characteristics and quality enrichment

## Architecture

1. `01_pull_renal_hcris.py` downloads the CMS renal HCRIS ZIP and converts the long HCRIS files into analysis-ready source tables.
2. `02_build_dialysis_metrics.py` creates a facility-year analytic table from worksheet/line/column mappings.
3. `metric_dictionary_dialysis.csv` is the canonical metric/mapping dictionary. Mappings should be validated against the current CMS-265-11 instructions before production use.
4. `03_build_static_site.py` creates a lightweight static national benchmarking page in `docs/dialysis/`.

The first implementation deliberately keeps HCRIS worksheet coordinates visible rather than hiding them behind opaque variable names. That makes metric validation auditable.

## Run

```bash
cd dialysis
python 01_pull_renal_hcris.py
python 02_build_dialysis_metrics.py
python 03_build_static_site.py
```

## Output

- `data/raw/` downloaded/extracted HCRIS files
- `data/processed/dialysis_facility_year_metrics.csv`
- `../docs/dialysis/index.html`

## Status

This is an MVP scaffold. The metric dictionary is intentionally conservative: facility identity and report-period fields can be populated immediately from the report file; financial, utilization, treatment-volume and staffing metrics are added as CMS-265-11 worksheet coordinates are validated. Do not publish an unvalidated worksheet mapping as a production KPI.
