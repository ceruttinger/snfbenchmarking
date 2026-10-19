# Twenty health policy and health services queries

These are read-only Cypher queries for the deployed HCRIS graph. Paste one code block at a time into Neo4j Browser. No APOC or parameters are required. Change `UT`, `460010`, years, and illustrative thresholds as needed. Queries were checked against the graph builder's schema; they have not been executed against the live database in this task.

Financial observations cover CMS dataset years 2017–2024. A dataset year is not necessarily a calendar year. `eligible` means a report period of 300–430 days. `metric_discharges`, `metric_patientDays`, `metric_revenue`, and `metric_expense` are annualized to 365.25 days. Monetary amounts are nominal. Medians are unweighted facility medians. Report units can be hospital complexes rather than individual campuses. Descriptive associations are not causal effects.

Most queries below use general short-term hospitals, including CAHs (`providerType='1'`). Queries 3 and 4 separate CAHs using `kind`. Current ownership/enrollment disclosures are 2026 snapshots, not historical ownership intervals. Missing ownership percentages are unknown, not zero. Shared disclosed interests are not resolved ultimate-parent health systems.

## 1. Is reporting coverage sufficient for credible comparisons over time?

```cypher
MATCH (r:CostReport)
RETURN r.datasetYear AS year, count(*) AS reports,
       count(CASE WHEN r.eligible THEN 1 END) AS eligibleReports,
       count(CASE WHEN r.eligible THEN r.metric_totalMargin END) AS validMargins,
       count(CASE WHEN r.eligible THEN r.metric_occupancy END) AS validOccupancies
ORDER BY year;
```

Check changing coverage before interpreting apparent trends. Missing reports do not establish closure.

## 2. How did utilization and margins change in a consistent hospital cohort?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.eligible AND r.providerType='1'
  AND r.metric_occupancy IS NOT NULL AND r.metric_totalMargin IS NOT NULL
WITH h, collect(r) AS reports, count(DISTINCT r.datasetYear) AS years
WHERE years=8
UNWIND reports AS r
RETURN r.datasetYear AS year, count(*) AS hospitals,
       100*percentileCont(r.metric_occupancy,0.5) AS medianOccupancyPct,
       100*percentileCont(r.metric_totalMargin,0.5) AS medianTotalMarginPct
ORDER BY year;
```

This balanced cohort reduces composition changes but excludes entrants, exits and incomplete reporters; it has survivor bias. Fiscal periods still differ.

## 3. Are rural hospitals and CAHs financially more vulnerable?

```cypher
MATCH (r:CostReport)
WHERE r.eligible AND r.providerType='1' AND r.metric_totalMargin IS NOT NULL
WITH r, CASE WHEN r.kind='CAH' THEN 'CAH'
             WHEN r.rural='R' THEN 'Other rural'
             WHEN r.rural='U' THEN 'Urban' ELSE 'Unknown' END AS group
RETURN r.datasetYear AS year, group, count(*) AS hospitals,
       100*percentileCont(r.metric_totalMargin,0.5) AS medianMarginPct,
       100.0*sum(CASE WHEN r.metric_totalMargin<0 THEN 1 ELSE 0 END)/count(*) AS lossPct
ORDER BY year, group;
```

These are changing annual cohorts, not a causal estimate of rural status or CAH payment policy.

## 4. Which hospitals reported losses in each of the last three years?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.eligible AND r.providerType='1' AND r.datasetYear IN [2022,2023,2024]
WITH h, collect(r) AS reports
WHERE size(reports)=3 AND all(x IN reports WHERE x.metric_totalMargin<0)
UNWIND reports AS r
RETURN h.id AS ccn, h.name AS hospital, h.state AS latestState,
       min(r.metric_totalMargin)*100 AS worstMarginPct,
       avg(r.metric_totalMargin)*100 AS meanMarginPct
ORDER BY meanMarginPct LIMIT 50;
```

Persistent reported losses are a screening signal, not a validated closure-risk prediction.

## 5. Where do losses and low liquidity coincide?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.datasetYear=2024 AND r.eligible AND r.providerType='1'
  AND r.metric_totalMargin<0 AND r.metric_currentRatio<1
RETURN h.id AS ccn, h.name AS hospital, h.state AS latestState,
       100*r.metric_totalMargin AS totalMarginPct,
       r.metric_currentRatio AS currentRatio, r.beds AS reportedBeds
ORDER BY currentRatio LIMIT 50;
```

Current ratio is current assets/current liabilities; it is not days cash on hand. Threshold 1 is an illustrative screen.

## 6. Which busy hospitals also face financial pressure?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.datasetYear=2024 AND r.eligible AND r.providerType='1'
  AND r.metric_occupancy>=0.85 AND r.metric_totalMargin<0
RETURN h.id AS ccn, h.name AS hospital, h.state AS latestState,
       100*r.metric_occupancy AS occupancyPct,
       100*r.metric_totalMargin AS totalMarginPct,
       r.metric_patientDays AS annualizedPatientDays
ORDER BY occupancyPct DESC LIMIT 50;
```

The 85% threshold is an exploratory filter, not a universal safe-capacity standard. Annual occupancy cannot reveal daily peaks, staffed-bed shortages or staffing ratios.

## 7. Where has reported bed capacity contracted since 2019?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(a:CostReport {datasetYear:2019}),
      (h)-[:HAS_COST_REPORT]->(b:CostReport {datasetYear:2024})
WHERE a.eligible AND b.eligible AND a.providerType='1' AND b.providerType='1'
  AND a.fiscalEnd<b.fiscalBegin AND a.beds>0 AND b.beds>=0
RETURN h.id AS ccn, h.name AS hospital, h.state AS latestState,
       a.beds AS beds2019, b.beds AS beds2024,
       b.beds-a.beds AS bedChange,
       100*(b.beds-a.beds)/a.beds AS bedChangePct
ORDER BY bedChange LIMIT 50;
```

Reported bed changes may reflect reporting boundaries or service changes; they are not necessarily physical closures or staffed-bed changes.

## 8. Which hospitals experienced the greatest growth in inpatient demand?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(a:CostReport {datasetYear:2019}),
      (h)-[:HAS_COST_REPORT]->(b:CostReport {datasetYear:2024})
WHERE a.eligible AND b.eligible AND a.providerType='1' AND b.providerType='1'
  AND a.fiscalEnd<b.fiscalBegin AND a.metric_discharges>0
  AND b.metric_discharges IS NOT NULL
RETURN h.id AS ccn, h.name AS hospital,
       a.metric_discharges AS discharges2019,
       b.metric_discharges AS discharges2024,
       100*(b.metric_discharges/a.metric_discharges-1) AS growthPct
ORDER BY growthPct DESC LIMIT 50;
```

Annualized discharges provide a workload proxy; they do not measure acuity or nursing hours required.

## 9. Where has length of stay increased most?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(a:CostReport {datasetYear:2019}),
      (h)-[:HAS_COST_REPORT]->(b:CostReport {datasetYear:2024})
WHERE a.eligible AND b.eligible AND a.providerType='1' AND b.providerType='1'
  AND a.fiscalEnd<b.fiscalBegin
  AND a.metric_lengthOfStay IS NOT NULL AND b.metric_lengthOfStay IS NOT NULL
RETURN h.id AS ccn, h.name AS hospital,
       a.metric_lengthOfStay AS los2019, b.metric_lengthOfStay AS los2024,
       b.metric_lengthOfStay-a.metric_lengthOfStay AS changeDays
ORDER BY changeDays DESC LIMIT 50;
```

Longer stays may motivate investigation of acuity, discharge barriers and post-acute capacity. This query cannot distinguish those explanations or establish workforce effects.

## 10. How has nominal expense per patient day changed?

```cypher
MATCH (r:CostReport)
WHERE r.eligible AND r.providerType='1' AND r.metric_patientDays>0
  AND r.metric_expense>=0
RETURN r.datasetYear AS year, count(*) AS hospitals,
       percentileCont(r.metric_expense/r.metric_patientDays,0.5) AS medianExpensePerPatientDay
ORDER BY year;
```

Total operating expense includes costs beyond inpatient care; this is a broad intensity proxy, not inpatient unit cost, labor cost or wages. Annual cohorts change; inflation is not removed.

## 11. Do hospitals with higher Medicaid day shares have weaker margins?

```cypher
MATCH (r:CostReport)
WHERE r.datasetYear=2024 AND r.eligible AND r.providerType='1'
  AND r.metric_medicaidShare IS NOT NULL AND r.metric_totalMargin IS NOT NULL
WITH r, CASE WHEN r.metric_medicaidShare>=0.30 THEN '30% or more'
             WHEN r.metric_medicaidShare>=0.15 THEN '15% to under 30%'
             ELSE 'Under 15%' END AS medicaidDayShare
RETURN medicaidDayShare, count(*) AS hospitals,
       100*percentileCont(r.metric_totalMargin,0.5) AS medianMarginPct
ORDER BY medicaidDayShare;
```

Illustrative bins describe reported Title XIX day share, not all Medicaid enrollment or payment adequacy. Minimum five valid hospitals is a reasonable display rule.

## 12. Which hospitals combine high uncompensated-care burden with losses?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.datasetYear=2024 AND r.eligible AND r.providerType='1'
  AND r.metric_uncompShare>=0.05 AND r.metric_totalMargin<0
RETURN h.id AS ccn, h.name AS hospital, h.state AS latestState,
       100*r.metric_uncompShare AS uncompensatedCareExpensePct,
       100*r.metric_totalMargin AS totalMarginPct
ORDER BY uncompensatedCareExpensePct DESC LIMIT 50;
```

The 5% filter is illustrative. This burden measure is uncompensated care/operating expense, not all unreimbursed Medicaid/CHIP costs.

## 13. How has reported Medicare day share changed by hospital type?

```cypher
MATCH (r:CostReport)
WHERE r.eligible AND r.metric_medicareShare IS NOT NULL
RETURN r.datasetYear AS year, r.kind AS hospitalType, count(*) AS hospitals,
       100*percentileCont(r.metric_medicareShare,0.5) AS medianMedicareDaySharePct
ORDER BY hospitalType, year;
```

Reported Title XVIII share is not a validated Medicare Advantage-inclusive measure. Differences may reflect case mix, coverage and reporting, as well as patient demand.

## 14. Which counties show declining bed capacity within matched hospitals?

```cypher
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(a:CostReport {datasetYear:2019}),
      (h)-[:HAS_COST_REPORT]->(b:CostReport {datasetYear:2024}),
      (a)-[:REPORTED_IN]->(g:Geography {kind:'county'}),
      (b)-[:REPORTED_IN]->(g)
WHERE a.eligible AND b.eligible AND a.providerType='1' AND b.providerType='1'
  AND a.fiscalEnd<b.fiscalBegin AND a.beds>=0 AND b.beds>=0
RETURN g.state AS state, g.name AS county, count(DISTINCT h) AS matchedHospitals,
       sum(a.beds) AS beds2019, sum(b.beds) AS beds2024,
       sum(b.beds-a.beds) AS bedChange
ORDER BY bedChange LIMIT 50;
```

This excludes unmatched hospitals and county movers. It is not total county capacity, beds per resident, travel access or evidence of hospital closure. County labels are reported strings, not validated FIPS geographies.

## 15. Which disclosed organizational owners link to the most hospitals?

```cypher
MATCH (h:Hospital)-[:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
RETURN o.associateId AS cmsAssociateId, o.name AS organization,
       count(DISTINCT h) AS hospitals,
       collect(DISTINCT h.state) AS latestHospitalStates
ORDER BY hospitals DESC LIMIT 30;
```

Distinct hospital counts avoid duplicate assertions. A hospital may appear under multiple disclosed owners; counts must not be summed across organizations. This is not an ultimate-parent market concentration or antitrust HHI calculation.

## 16. Which disclosed owners have a multistate footprint?

```cypher
MATCH (h:Hospital)-[:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
WITH o, count(DISTINCT h) AS hospitals, collect(DISTINCT h.state) AS states
WHERE size(states)>1
RETURN o.associateId AS cmsAssociateId, o.name AS organization,
       hospitals, size(states) AS stateCount, states
ORDER BY stateCount DESC, hospitals DESC LIMIT 30;
```

Footprints use current disclosure links and the latest available hospital location; disclosure coverage is incomplete.

## 17. Which hospitals have multiple disclosed majority-interest organizations?

```cypher
MATCH (h:Hospital)-[r:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
WHERE r.percentage>=50
WITH h, collect(DISTINCT o) AS organizations
WHERE size(organizations)>1
RETURN h.id AS ccn, h.name AS hospital,
       [o IN organizations | {associateId:o.associateId,name:o.name}] AS disclosedOrganizations
LIMIT 50;
```

This is an evidence-review queue, not proof of invalid ownership. Direct/indirect tiers and roles may coexist; percentages cannot be added across tiers. The threshold includes exactly 50% and does not establish control.

## 18. Which current disclosed-owner portfolios include hospitals with 2024 losses?

```cypher
MATCH (h:Hospital)-[:REPORTED_OWNERSHIP_INTEREST]->(o:Organization)
WITH DISTINCT h,o
MATCH (h)-[:HAS_COST_REPORT]->(r:CostReport {datasetYear:2024})
WHERE r.eligible AND r.providerType='1' AND r.metric_totalMargin IS NOT NULL
WITH o, count(*) AS hospitals,
     sum(CASE WHEN r.metric_totalMargin<0 THEN 1 ELSE 0 END) AS lossHospitals,
     percentileCont(r.metric_totalMargin,0.5) AS medianMargin
WHERE hospitals>=5
RETURN o.name AS currentDisclosedOrganization, hospitals, lossHospitals,
       100.0*lossHospitals/hospitals AS lossPct,
       100*medianMargin AS medianMarginPct
ORDER BY lossPct DESC, hospitals DESC LIMIT 30;
```

This overlays a 2026 disclosure snapshot on historical reports. It does not establish ownership in 2024, consolidated financial performance, a system margin or an acquisition effect.

## 19. What provider categories appear under an associate linked to the target hospital?

```cypher
MATCH (h:Hospital {id:'460010'})-[:HAS_OWNERSHIP_ASSERTION]->(:OwnershipAssertion)
      -[:ASSOCIATE]->(o:Organization)
WITH DISTINCT o
MATCH (o)-[:HAS_REPORTED_ENROLLMENT]->(e:ProviderEnrollment)
RETURN o.name AS disclosedAssociate, e.providerType AS providerCategory,
       count(DISTINCT e) AS enrollments, collect(DISTINCT e.state) AS states
ORDER BY enrollments DESC;
```

The loaded cross-category example is bounded: 80 enrollments for one selected associate. An exact-associate enrollment link is not a separately verified ownership assertion for every facility, an employee count or evidence of referral flows. Other targets can return few or no categories because enrichment is incomplete.

## 20. What organizational service taxonomies can we actually observe—and how incomplete is NPPES enrichment?

```cypher
MATCH (n:NPI)
OPTIONAL MATCH (n)-[:HAS_TAXONOMY]->(t:Taxonomy)
WITH n, collect(DISTINCT t.description) AS taxonomies
RETURN n.enumerationType AS enrichmentStatus, count(*) AS npiIdentifiers,
       collect({npi:n.id,name:n.legalName,taxonomies:taxonomies})[0..15] AS examples
ORDER BY npiIdentifiers DESC;
```

This graph contains organization identifiers, with only 11 organization NPI records enriched. Taxonomies describe registered organizational services, not the number or specialties of individual employed clinicians. This query is a coverage check before workforce claims.

# Workforce extension now loaded

The deployed graph now includes payroll employee FTEs, approved-program intern/resident FTEs and Worksheet A salaries for 2017–2024. All 48,193 selected financial reports matched workforce API records by report ID, CCN and fiscal dates. Nonblank values cover 47,269 payroll FTE observations, 11,557 resident FTE observations and 47,556 salary observations. Missing resident FTEs do not establish a non-teaching hospital.

Seven semantic measures are available: payrollFte, residentFte, salaries (annualized), ftePer100Beds, dischargesPerFte, patientDaysPerFte and salaryPerFte. In Neo4j, derived values use the metric_ prefix. Raw payrollFte, residentFte and salaries properties remain on CostReport. The WORKFORCE_FROM_SOURCE relationship identifies the workforce API snapshot, separately from frozen financial sources. Prior catalog lineage is retained. The six additional workforce queries are in workforce.cypher alongside this document.

Payroll FTEs are all-occupation period averages, never annualized. Patient days/discharges per payroll FTE describe inpatient workload relative to all payroll employees; they omit outpatient activity and case mix. Salary per FTE is an organization-wide nominal salary-intensity proxy with worksheet-scope differences requiring review, not RN wages, benefits or total labor costs. Neither the fields nor organizational NPPES taxonomies establish individual employment, nurse ratios, vacancies, turnover or shortages.

Use matched endpoints and balanced panels deliberately, preserve actual fiscal periods, and review extreme changes for CCN/reporting-boundary changes. Missing reports do not establish closures. Current ownership is not historical ownership. Workforce fields were refreshed later than financial inputs; even exact report-ID/period joins cannot guarantee the same revision vintage. Dollar values remain nominal, without inflation adjustment. Nonpayroll and contract-labor measures are not loaded.

Sources: [CMS Hospital API](https://data.cms.gov/provider-compliance/cost-reports/hospital-provider-cost-report/api-docs), [CMS data dictionary](https://data.cms.gov/sites/default/files/2024-03/9756088d-5280-4090-80b9-449d31ef25a3/Cost%20Report%20Data%20Dictionary%20Update.pdf), [CMS NPI documentation](https://download.cms.gov/nppes/NPI_Files.html).
