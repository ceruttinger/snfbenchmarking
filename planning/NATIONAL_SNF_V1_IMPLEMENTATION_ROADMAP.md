# National SNF Intelligence v1 — Implementation Roadmap

## Objective

Publish a national SNF product quickly enough to begin selling facility benchmark reports before the full SaaS platform is complete.

## Milestone 0 — source recovery and repository normalization

### Required
- push current R source files
- push current Quarto source files
- push helper functions and metric dictionaries
- push render/build scripts
- keep generated `docs/` output tracked for current GitHub Pages deployment
- keep large raw/processed data ignored

### Repository target structure

```text
R/
  hcris/
  provider_data/
  metrics/
  peers/
  reports/
pipeline/
config/
  datasets.yml
  metrics/
reports/
site/
tests/
planning/
docs/                # generated public site during current deployment phase
README.md
```

Do not move files merely for neatness before the current source is safely committed. First commit existing source as-is; restructure in a later commit.

## Milestone 1 — nationalize existing HCRIS pipeline

Goal: produce a validated national `snf_facility_year` analytical file while retaining the Utah validation workflow.

Tasks:
- remove state-specific assumptions from core processing
- preserve `SNF_VALIDATE_STATE` as a QA/testing parameter only
- ingest all U.S. SNF reports for supported years
- create national provider/report row-count diagnostics
- create CCN/state/year coverage diagnostics
- create one compact sample output for repository testing
- write Parquet as the production analytical format

Acceptance criteria:
- all states/territories represented where CMS data exist
- no state filter in the production metric table
- report-period QC remains functional
- existing Utah benchmark can be regenerated from the national file

## Milestone 2 — 2540-24 form support and semantic metric layer

Goal: stop relying on intuitive column aliases as the long-term metric architecture.

Tasks:
- ingest CMS-2540-24 separately from CMS-2540-10
- define form-aware source mappings
- create versioned metric dictionary
- identify metrics that are:
  - continuous across both forms
  - conceptually continuous but require coordinate/formula changes
  - available only on 2540-24
  - available only on 2540-10
- add compatibility flags to facility-year metrics
- prevent misleading trend joins across form changes

Acceptance criteria:
- same semantic metric can resolve from either form when genuinely comparable
- metrics without valid crosswalks remain missing/explicit rather than silently substituted
- automated mapping audit reports coverage by form/year

## Milestone 3 — national provider master and CMS enrichment

Goal: every commercial report resolves a cost report to current provider identity/context.

Tasks:
- ingest Provider Information (`4pq5-n9py`)
- ingest Ownership (`y2hd-n93e`)
- build provider master keyed by CCN
- add chain fields, beds, ownership, urban/rural, ratings, staffing/turnover fields
- quantify unresolved HCRIS-to-provider links
- implement safe handling of closed/historical providers

Acceptance criteria:
- current active facility lookup works nationally
- match rate and unmatched reasons are reported
- current provider information has source/update timestamps

## Milestone 4 — peer engine v1

Goal: every supported target facility gets transparent comparison cohorts.

Tasks:
- implement state cohort
- implement national cohort
- implement matched peer cohort using configurable feature rules
- minimum peer-count rule and fallback hierarchy
- calculate median/IQR/percentile for supported metrics
- version peer methodology
- create peer-quality diagnostics

Acceptance criteria:
- a user can see exactly why a peer set was selected
- cohort size is displayed
- extreme/sparse cohorts fall back safely
- results can be reproduced from a peer-method version

## Milestone 5 — Visible Labor Cost module

Goal: create a signature differentiated analysis.

Tasks:
- identify HCRIS labor metrics by form
- ingest PBJ Daily Nurse Staffing
- aggregate PBJ to facility-quarter/year measures suitable for comparison
- calculate employee/contract staffing shares where available
- reconcile PBJ staffing with HCRIS labor reporting at an analytically defensible period level
- calculate visible labor cost per resident day/hour where supported
- add labor data-quality flags

Acceptance criteria:
- no labor metric combines incompatible periods without an explicit rule
- 2540-24-specific labor detail is surfaced without pretending it exists historically
- report contains at least 3 commercially useful labor findings for facilities with sufficient data

## Milestone 6 — automated paid report v1

Goal: sell the product before building the complete SaaS shell.

Tasks:
- create national report template
- executive finding cards
- matched-peer explanation
- benchmark opportunity table
- financial + occupancy + labor + quality sections
- source/methodology appendix
- report version metadata
- PDF/HTML generation path

Acceptance criteria:
- any eligible national CCN can generate the report from one command/job
- report is understandable without the dashboard
- limitations/source periods are visible
- the report can be regenerated reproducibly from the same data release

## Milestone 7 — public national facility profiles

Goal: begin acquisition and SEO without exposing the full paid product.

Tasks:
- compact facility serving JSON
- lightweight page template
- state and chain index pages
- canonical URLs
- page titles/descriptions suitable for search
- free-vs-paid gating
- CMS source attribution and non-endorsement disclosure

Acceptance criteria:
- page size remains small
- national data are not embedded into every page
- pages render quickly from static/CDN architecture
- paid report CTA is prominent

## Milestone 8 — payments and report fulfillment

Goal: customer can pay without manual invoicing.

Tasks:
- Stripe product/price setup
- checkout flow
- report order record
- successful-payment webhook
- report generation job
- secure/time-limited delivery link
- transactional email
- failed-job handling

Acceptance criteria:
- test payment produces report delivery end-to-end
- no report is exposed publicly by order ID guessing
- failed jobs create an actionable alert

## Milestone 9 — subscription SaaS

Only after paid-report demand is demonstrated.

Tasks:
- Cognito accounts
- subscriptions
- saved facilities
- portfolios
- refresh/change alerts
- authenticated API endpoints
- AI analyst over structured metric packages

## Commercial validation alongside development

### Before report completion
- create a list of 30 target beta buyers
- prepare 3 example national reports
- interview 5–10 operators/consultants/lenders
- record which findings cause actual follow-up questions

### First revenue target
- 3 beta reports at $350–$500 each

### Second revenue target
- 10 founding annual subscriptions at approximately $999 each or equivalent portfolio/professional sales

## Expansion gate

Do not begin HHA/Hospice product engineering until at least one of the following is true:
- 10 paid SNF reports sold
- 5 annual SNF subscriptions sold
- 1 professional/portfolio account explicitly requests adjacent HCRIS verticals

Architect for additional HCRIS provider types now, but earn the right to build them through SNF revenue.
