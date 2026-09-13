# National SNF Intelligence v1 — Data Source Inventory

Last reviewed: 2026-09-12

This document defines the first national data sources for the commercial SNF product. Source identifiers and refresh behavior should be treated as configuration rather than hard-coded throughout the application.

## Tier 1 — required for first paid report

### 1. CMS HCRIS SNF cost reports

Source: CMS HCRIS Cost Reports

Required forms:
- CMS-2540-10: fiscal years 2011–2025 in the current CMS release
- CMS-2540-24: fiscal years 2024–2026 in the current CMS release

Purpose:
- revenue and expense
- utilization and resident days
- balance-sheet / liquidity metrics where supported
- department cost reporting
- wage/labor reporting
- payer/utilization variables
- longitudinal facility financial analysis

Important implementation rule:
Do not collapse 2540-10 and 2540-24 into one wide schema by assuming columns/coordinates are unchanged. Map both forms into a semantic metric dictionary.

Refresh:
- check CMS HCRIS release metadata on a schedule
- retain immutable source release copies

### 2. CMS Provider Information — Nursing Homes

Provider Data Catalog identifier: `4pq5-n9py`

Purpose:
- current provider master
- CCN
- provider/legal name
- location
- urban indicator
- ownership type
- certified beds
- chain name/ID
- Five-Star components
- staffing and turnover headline measures
- nursing case-mix values
- penalties summary fields

Refresh:
- monthly / according to CMS published update schedule

### 3. CMS Nursing Home Ownership

Provider Data Catalog identifier: `y2hd-n93e`

Purpose:
- ownership entities and relationships
- ownership type
- chain/portfolio intelligence
- future change-of-ownership monitoring

Refresh:
- monthly / according to CMS published update schedule

## Tier 2 — required for differentiated v1 analytics

### 4. Payroll Based Journal Daily Nurse Staffing

Source: CMS Data — Quality of Care

Purpose:
- daily RN/LPN/CNA and related staffing hours
- employee vs contract/agency staffing where supported
- census denominator
- HCRIS labor/staffing reconciliation
- staffing volatility and weekend patterns

Refresh:
- quarterly

Implementation note:
Use aggregate daily files for v1 unless employee-detail analytics materially improve a sellable feature. Employee-detail files are extremely large and should not be introduced merely because they exist.

### 5. Payroll Based Journal Daily Non-Nurse Staffing

Purpose:
- therapy, social work, administration and other staff categories
- departmental labor context

Refresh:
- quarterly

### 6. FY SNF VBP Facility-Level Data

Current example: FY 2026 facility-level dataset

Purpose:
- performance score
- rankings
- measure achievement/improvement scores
- incentive payment multiplier
- payment-related quality context

Refresh:
- annual program release plus any CMS revisions

### 7. SNF Quality Reporting Program Provider Data

Provider Data Catalog identifier: `fykj-qjee`

Purpose:
- SNF QRP quality/outcome measures
- additional facility performance context beyond Five-Star headline fields

Refresh:
- according to CMS published schedule

## Tier 3 — useful after first commercial release

### 8. Penalties

Provider Data Catalog identifier: `g6vv-u9sr`

Purpose:
- fines/payment denials
- regulatory risk trend
- portfolio exception flags

### 9. MDS Quality Measures

Purpose:
- detailed long-stay/short-stay resident quality measures

### 10. Medicare Claims Quality Measures

Purpose:
- risk-adjusted claims-based quality measures

### 11. Survey / deficiencies datasets

Purpose:
- inspection history
- deficiency burden
- complaint / infection control context

### 12. Nursing Home Data Collection Intervals

Provider Data Catalog identifier: `qmdc-9999`

Purpose:
- interpret measure periods correctly
- prevent mixing metrics that refer to materially different performance periods

## Tier 4 — market and labor enrichment

### 13. BLS/OEWS

Purpose:
- local RN/LPN/CNA and other occupational wage benchmarks
- compare facility-reported wage economics with local labor market

### 14. Census/ACS

Purpose:
- age 65+/85+ population
- local income and poverty
- population change
- rural/urban and market context

### 15. CMS Provider of Services / enrollment data

Purpose:
- historical provider identity/status support
- certification/provider attributes
- future provider-type expansion

## Source governance

Every source table must store:
- source system
- dataset identifier when applicable
- source URL or catalog reference
- source modified/released date
- ingestion timestamp
- source file name
- source checksum where practical
- schema version

## Publication rules

- CMS/government data should be attributed as the source.
- Product pages must not imply CMS, Medicare, or federal endorsement.
- Archived source releases should be retained so a published report can be reproduced.
- Metric period labels must make clear when HCRIS fiscal-year data are being compared with calendar/quarter/rolling quality data.

## Initial ingestion order

1. National HCRIS 2540-10
2. National HCRIS 2540-24
3. Provider Information
4. Ownership
5. PBJ Daily Nurse Staffing
6. SNF VBP
7. SNF QRP
8. Penalties / detailed quality / surveys

The first paid report should not wait for every Tier 3/Tier 4 dataset. HCRIS + provider master + ownership + PBJ/VBP are sufficient to create a materially stronger commercial product than the current Utah demo.
