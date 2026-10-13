# Hospital benchmarking pilot

Static national hospital module at `/hospitals/`, hosted in the existing GitHub Pages `docs` directory. No new domain is needed. The homepage offers the existing SNF dashboard, this pilot and the dialysis scaffold. Original SNF dashboard HTML is untouched.

Real CMS Hospital Provider Cost Report public-use records from source datasets 2022 and 2023, modified October 5, 2026 and retrieved October 13, 2026. `docs/hospitals/manifest.json` retains source URLs, SHA-256 checksums, counts and selection rules. Dataset labels are not standardized calendar years.

To rebuild, download the manifest URLs as `CostReport_2022.csv` and `CostReport_2023.csv` into an input directory, then run `python hospitals/build_data.py --input-dir /absolute/path/to/input`. Standard library only. Gzip timestamps are deterministic; raw inputs are not committed.

One report per CCN/source dataset: prefer 300–430-day reports, then longest duration, latest end date, highest report ID. Peers match CCN category and provider type and exclude the target. State, rural/urban and bed-size filters are optional. Five valid peers required per metric. Facility medians are unweighted; ties use midpoint percentile ranks. Missing values and nonpositive denominators remain unavailable. Occupancy outside 0–100% is excluded. Comparisons are not adjusted for case mix, teaching or local wages.

Patient-service margin differs from RAND operating margin. Total margin uses the documented RAND definition with CMS fields. Other RAND observations, ownership links and study prices are not loaded. The UI explicitly describes these limits.

Serve `docs` through HTTP. Current-browser `DecompressionStream` is required for compressed data, with readable errors if unavailable. Run `node hospitals/test_metrics.cjs` for calculation, cohort, uniqueness and report-period checks.
