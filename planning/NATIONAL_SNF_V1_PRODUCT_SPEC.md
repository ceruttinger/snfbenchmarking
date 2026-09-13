# National SNF Intelligence v1 — Product Specification

Status: implementation specification

## Product goal

Turn the existing Utah SNF HCRIS benchmarking prototype into a national, commercially sellable SNF intelligence product while preserving the current public demo during migration.

The first commercial release should answer a simple question better than a generic dashboard:

> Where is this SNF materially different from comparable facilities, how large is the difference, and what deserves investigation first?

## v1 customer

Primary early buyers:

1. SNF operators and regional leaders
2. SNF financial/operations consultants
3. Lenders, investors, brokers, and acquisition teams
4. State/national associations
5. Vendors serving SNFs who need facility intelligence

## v1 products

### Free facility profile

Purpose: SEO and lead generation.

Includes:
- facility identity and location
- ownership/chain
- bed count and occupancy context
- selected CMS ratings/staffing fields
- selected financial benchmarks
- three-year trend preview
- 1–3 automatically generated observations
- CTA to purchase full benchmark report

### Paid facility benchmark report

Initial launch target: $249–$495 per report.

Sections:
1. Executive findings
2. Facility profile
3. Matched-peer definition
4. Financial performance
5. Occupancy/utilization/payer mix
6. Labor economics
7. Department cost efficiency
8. Quality + staffing context
9. Benchmark opportunity table
10. Trend analysis
11. Data-quality/disclosure appendix
12. Metric definitions and sources

### Facility subscription

Initial target: $99/month or $999/year.

Includes:
- full facility analytics
- saved facility
- refreshed CMS data
- alerts for material changes
- report regeneration
- AI analyst over validated metrics

### Portfolio subscription

Initial target: $299/month or $2,990/year.

Includes:
- portfolio summary
- exception ranking
- facility comparison
- saved peer groups
- exports
- change monitoring

### Professional subscription

Initial target: $599/month or $5,990/year.

For consultants, lenders, vendors, analysts, and acquisition teams.

Includes:
- broad/national facility access
- advanced filters
- bulk comparisons
- export functionality
- acquisition/market screening

## v1 differentiation

Do not compete as "another CMS dashboard."

The product differentiates on:
- validated longitudinal HCRIS metrics
- matched-peer methodology rather than crude state/national averages
- transparent data-quality flags
- dollarized benchmark differences
- integration of HCRIS with Care Compare/PBJ/VBP/ownership
- narrative interpretation grounded in deterministic metrics
- automated client/board-ready reports

## Signature analysis: Visible Labor Cost

Initial analytical families:
- employee wage rate by staff type where supported
- employee labor dollars
- purchased/contract labor dollars
- purchased/contract labor hours where supported by form version
- visible labor cost per resident day
- contract-labor share
- labor cost vs matched peers
- HCRIS/PBJ staffing reconciliation
- geographic wage comparison using BLS/OEWS in a later iteration

All measures must carry form-version compatibility metadata, especially CMS-2540-10 vs CMS-2540-24.

## Peer engine v1

Default peer matching should use available characteristics in this order:

1. provider type / SNF eligibility
2. report-year compatibility
3. urban/rural status
4. bed-count band
5. ownership type
6. hospital-based status when available
7. occupancy band
8. payer-mix/case-mix variables when reliable
9. geography as a configurable constraint, not the sole peer definition

Every benchmark should expose:
- peer count
- peer definition
- target percentile
- peer median
- peer IQR where useful
- state comparison
- national comparison

Do not show unstable matched-peer results when the peer count is below the configured minimum; fall back to a broader cohort and state this explicitly.

## Benchmark opportunity engine

For each eligible metric:

benchmark_difference = target_value - peer_reference

estimated_annual_difference = benchmark_difference × relevant annual denominator

Examples:
- cost per resident day × resident days
- labor cost per hour × labor hours
- occupancy gap × available bed-days (shown as capacity difference, not guaranteed revenue)

Use language such as:
- benchmark difference
- estimated cost difference
- performance gap
- area for investigation

Avoid claims of guaranteed savings, revenue, or causality.

## AI analyst rules

The AI layer must:
- receive curated structured metrics, not raw HCRIS rows
- cite metric/source metadata in every substantive finding
- distinguish fact from interpretation
- never invent missing values
- surface data-quality limitations
- avoid clinical advice
- avoid claiming benchmark gaps are realizable savings

## Commercial release definition

National SNF v1 is commercially releasable when:

- every active U.S. SNF can be resolved to a facility profile
- longitudinal HCRIS metrics are available for supported years
- CMS-2540-10 and CMS-2540-24 are distinguished correctly
- key metrics pass automated QC
- Care Compare provider data are linked by CCN
- peer benchmarks run nationally
- one facility report can be generated automatically
- Stripe purchase can trigger report delivery
- public profile pages can be generated without embedding the national dataset in each page
- source attribution/disclaimer is displayed

## Explicit non-goals for first paid release

- full hospital/HHA/hospice product
- claims/referral intelligence competing with Trella
- full CRM
- all state Medicaid rate methodologies
- custom EHR integration
- real-time operational staffing data
- predictive clinical risk models

## Expansion path

The underlying data/metric system should be provider-type agnostic enough to support:

SNF -> HHA -> Hospice -> FQHC/RHC -> Hospital -> other HCRIS systems

The web product remains SNF-specific until SNF revenue validates the model.
