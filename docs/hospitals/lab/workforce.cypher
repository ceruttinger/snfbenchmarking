// 1. Coverage by year: unknown FTEs are not zero.
MATCH (r:CostReport)
RETURN r.datasetYear AS year, count(*) AS reports,
 count(r.payrollFte) AS reportedPayrollFte, count(r.residentFte) AS reportedResidentFte,
 count(r.salaries) AS reportedSalaries ORDER BY year;

// 2. Target trajectory and actual fiscal periods (all occupations).
MATCH (:Hospital {id:'460010'})-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.eligible
RETURN r.datasetYear AS year,r.fiscalBegin,r.fiscalEnd,r.payrollFte,
 r.metric_ftePer100Beds,r.metric_patientDaysPerFte,r.metric_salaryPerFte
ORDER BY year;

// 3. Workload growing faster than payroll FTEs, matched 2019/2024 reports.
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(a:CostReport {datasetYear:2019}),
 (h)-[:HAS_COST_REPORT]->(b:CostReport {datasetYear:2024})
WHERE a.eligible AND b.eligible AND a.providerType='1' AND b.providerType='1'
 AND a.fiscalEnd<b.fiscalBegin AND a.payrollFte>0 AND b.payrollFte>0
 AND a.metric_patientDays>0 AND b.metric_patientDays>0
WITH h,a,b,100*(b.payrollFte/a.payrollFte-1) AS fteGrowthPct,
 100*(b.metric_patientDays/a.metric_patientDays-1) AS patientDaysGrowthPct,
 100*(b.metric_patientDaysPerFte/a.metric_patientDaysPerFte-1) AS workloadGrowthPct
WHERE workloadGrowthPct>0
RETURN h.id AS ccn,h.name AS hospital,fteGrowthPct,patientDaysGrowthPct,workloadGrowthPct
ORDER BY workloadGrowthPct DESC LIMIT 25;

// 4. Consistent valid reporters: rural/urban payroll FTE trends.
// Each hospital is assigned its 2024 reported rural/urban category for this panel.
MATCH (h:Hospital)-[:HAS_COST_REPORT]->(anchor:CostReport {datasetYear:2024})
WHERE anchor.providerType='1'
MATCH (h)-[:HAS_COST_REPORT]->(r:CostReport)
WHERE r.eligible AND r.providerType='1' AND r.payrollFte IS NOT NULL
WITH h,anchor.rural AS anchorRural,collect(r) AS reports,count(DISTINCT r.datasetYear) AS years
WHERE years=8
UNWIND reports AS r
RETURN anchorRural,r.datasetYear AS year,count(*) AS hospitals,
 percentileCont(r.payrollFte,0.5) AS medianPayrollFte ORDER BY anchorRural,year;

// 5. Resident FTE trends among observed reporters; missing is not non-teaching.
MATCH (r:CostReport)
WHERE r.eligible AND r.residentFte IS NOT NULL
RETURN r.datasetYear AS year,count(*) AS reportingHospitals,
 sum(r.residentFte) AS reportedResidentFteTotal ORDER BY year;

// 6. Audit source timestamp and hash for a workforce observation.
MATCH (r:CostReport {ccn:'460010',datasetYear:2024})-[:WORKFORCE_FROM_SOURCE]->(s:SourceSnapshot)
RETURN r.reportId,r.fiscalBegin,r.fiscalEnd,r.payrollFte,r.salaries,s.queriedAt,s.sha256,s.url;
