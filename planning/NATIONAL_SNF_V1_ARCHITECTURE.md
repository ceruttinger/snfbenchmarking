# National SNF Intelligence v1 — Technical Architecture

## Design principles

1. Preserve the existing Utah static demo during migration.
2. Keep R as the analytical/ETL language unless a component clearly benefits from another runtime.
3. Separate immutable raw source data from cleaned canonical data and presentation artifacts.
4. Precompute expensive facility-year metrics and common peer benchmarks.
5. Do not embed the entire national dataset in rendered HTML.
6. Make metric definitions provider-form aware so the same semantic metric can later support additional HCRIS systems.
7. Treat AI as an interpretation layer over validated structured data, not as a calculator of record.

## Target architecture

```text
CMS HCRIS / Provider Data / PBJ / VBP / ownership
                 |
                 v
        scheduled ingestion jobs
                 |
                 v
        S3 raw / immutable source
                 |
                 v
      R cleaning + normalization
                 |
                 v
       S3 canonical Parquet lake
                 |
       +---------+----------+
       |                    |
       v                    v
facility-year metrics   peer/benchmark tables
       |                    |
       +---------+----------+
                 v
         facility data package
                 |
        +--------+---------+
        |                  |
        v                  v
 public profile API    paid/report API
        |                  |
        v                  v
 CloudFront/site      report generator
                           |
                           v
                    private S3 output
```

## AWS components — phased

### Phase 1: national data + report product

Minimum services:
- S3 for raw, canonical, and report artifacts
- EventBridge for schedules
- containerized R job (ECS/Fargate, Batch, or existing compute environment)
- CloudWatch logs
- existing static site/CloudFront path if already configured

Do not introduce a permanent database merely because the dataset is national. S3 + Parquet + DuckDB is appropriate for batch analytics and keeps cost/operations low.

### Phase 2: self-service SaaS

Add:
- API Gateway
- Lambda for lightweight read APIs and checkout/report orchestration
- Cognito for account authentication
- DynamoDB for application state only: users, subscriptions, saved facilities, portfolios, report jobs
- Stripe checkout/webhooks
- SES for transactional email
- Secrets Manager / Parameter Store for credentials

### Phase 3: AI + portfolio scale

Add:
- structured AI analyst service
- cached facility intelligence documents
- alert/change-detection pipeline
- optional search/index service only if SQL/Parquet/API filtering is no longer sufficient

## S3 layout

Suggested logical structure:

```text
s3://<bucket>/
  raw/
    hcris/
      snf/
        2540-10/<release-date>/<source-files>
        2540-24/<release-date>/<source-files>
    provider-data/
      nursing-home-provider-info/<release-date>/
      ownership/<release-date>/
      pbj/<release-date>/
      vbp/<release-date>/
  canonical/
    provider/
    hcris_observation/
    report/
    facility_year/
  analytics/
    snf_facility_year/
    snf_peer_assignment/
    snf_benchmark/
    snf_opportunity/
  serving/
    facility/<ccn>.json
    state/<state>.parquet
    chain/<chain-id>.parquet
  reports/
    <customer-or-job-id>/
```

Raw files are append-only. Reprocessing should create new canonical/analytics partitions rather than overwrite raw source evidence.

## Canonical HCRIS model

### hcris_report

- provider_type
- form_id
- report_record_id
- provider_number / CCN where applicable
- fiscal_year_begin
- fiscal_year_end
- report_status
- report_date
- source_release
- source_year
- report_days
- report_quality_flags

### hcris_observation

- report_record_id
- worksheet
- line
- column
- value_type: numeric | alpha
- numeric_value
- text_value
- source_file

This long representation is the durable raw-normalized layer. Wide facility-year products are derived from it.

## Semantic metric dictionary

Create a versioned dictionary with at least:

- metric_id
- metric_name
- metric_family
- description
- unit
- directionality
- numerator_metric_id / denominator_metric_id where derived
- form_id
- worksheet
- line
- column
- effective_start
- effective_end
- transform
- validation_rule
- report_display_format
- eligible_for_peer_benchmark
- eligible_for_dollarization
- source_note

A single semantic metric may have multiple source mappings across forms. For example, one `contract_nursing_cost` metric can map separately to 2540-10 and 2540-24 coordinates.

## National provider master

Create a canonical `provider_master` keyed by CCN with:

- provider name
- legal business name
- address/city/state/ZIP
- county
- latitude/longitude
- urban/rural
- ownership type
- chain name/ID
- certified beds
- hospital-based flag
- certification date
- current activity/status
- source update date

Historical provider attributes should later be stored as slowly changing dimensions where needed, but v1 may retain current attributes plus report-year HCRIS identifiers.

## Facility-year analytical table

One row per provider/report-year observation used for commercial analytics. Suggested keys:

- ccn
- fiscal_year_end
- report_record_id
- form_id
- report_days
- data_quality_grade

Then named semantic metrics rather than worksheet coordinates.

## Peer engine

Peer assignment should be a reproducible batch process with a version ID.

Store:
- peer_method_version
- target_ccn
- target_year
- peer_ccn
- peer_year
- match_features
- distance/score where applicable
- cohort_type: matched | state | national

This allows benchmark results to be audited and reproduced after peer logic changes.

## Benchmark table

Precompute long-form benchmark output:

- target_ccn
- target_year
- metric_id
- peer_method_version
- peer_count
- target_value
- peer_median
- peer_q1
- peer_q3
- percentile
- state_median
- national_median
- benchmark_difference
- estimated_annual_difference where eligible
- benchmark_quality_flag

## Serving layer

Do not make browser clients query raw analytical tables.

For each facility, generate a compact JSON data package containing:
- profile
- current-year headline metrics
- trend series
- benchmark rows
- data-quality notes
- source timestamps
- precomputed findings candidates

Public pages receive a reduced package; authenticated products receive expanded packages.

## Report generation

Keep Quarto as the first report-generation engine.

Input:
- one structured facility data package
- customer/report metadata
- report template version

Output:
- HTML
- PDF when stable

Report files should be generated on demand or cached by facility + data release + report-template version, rather than blindly rendering thousands of multi-megabyte standalone pages whenever data refresh.

## QA gates

Every pipeline run should emit machine-readable checks for:
- expected source files present
- row counts by form/year
- duplicate report records
- report-day plausibility
- facility identity resolution rate
- metric mapping resolution rate
- metric missingness
- impossible range checks
- year-over-year extreme-change checks
- peer-count distribution
- percentage of active providers with commercial-report coverage

A failed critical QA gate should block publication of a new release.

## Migration from current static site

1. Keep current `docs/` site unchanged during data-engine work.
2. Move source code under tracked directories such as `R/`, `pipeline/`, `reports/`, and `site/` once the local source is pushed.
3. Nationalize data generation first.
4. Generate compact serving artifacts.
5. Replace embedded national data with browser/API fetches.
6. Migrate public facility pages incrementally.
7. Only remove legacy Utah-specific build paths after national release is validated.
