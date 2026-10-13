# Hospital benchmarking pilot

National hospital module at `/hospitals/` on the existing SNF GitHub Pages site.

## API-only data access

Run `python hospitals/build_data.py`. The builder queries official CMS JSON APIs for the 2022 and 2023 Hospital Provider Cost Report datasets, using selected fields, stable report-ID ordering and 1,000-row pages. Raw responses remain in memory. No raw CSV/ZIP distributions are downloaded or saved. Only the derived dashboard cache and manifest are published. The manifest retains API URLs, timestamps, record checksums and selection counts. The page identifies the cache refresh time; it does not claim live queries.

## Defined peer groups

Target selection is independent of the peer definition. Geography supports national, Census region, state, county and city (county/city always state-scoped). Category, clinical provider type, ownership group, specific type of control, rural/urban classification, bed bands and numeric bed limits can be combined. Individual peers can be excluded and exclusions cleared. Defaults are national, same category, same clinical type and same bed band. All controls combine with AND; contradictory choices produce an explicit empty cohort. Diverse hospital groups receive a clinical-comparability warning.

All nine metric cards, distributions and comparison exports use one authoritative cohort. The target CCN is excluded. Peer-list search only changes the displayed membership list; it does not change the cohort. A full peer-list export retains the definition and members. History uses fixed selected peer CCNs, with eligible reports and valid values counted separately by year. Async history results are invalidated when the definition changes.

## Definitions and validation

One representative report per CCN/source dataset: prefer a 300–430-day report, then longest duration, latest end date and highest report ID. Five valid peers required per benchmark. Peer medians are unweighted; percentile ties use midpoint ranks. Missing inputs and nonpositive denominators remain unavailable. Occupancy outside 0–100% is excluded. Comparisons are not adjusted for clinical case mix, teaching or local wages. Native report periods and reporting-complex scope remain visible.

Patient-service margin differs from RAND operating margin. Total margin uses RAND’s documented definition with CMS fields. RAND observation files, ownership links and claims-based prices are not loaded.

Run `node hospitals/test_metrics.cjs` and `python hospitals/test_api.py`. Serve `docs` through HTTP for browser verification. Modern-browser DecompressionStream support is required.
