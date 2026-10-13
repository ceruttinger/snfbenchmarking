/* Pure metric and cohort functions. No missing value is converted to zero. */
(function(root) {
  'use strict';
  const ratio=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)&&b>0?a/b:null;
  const metrics={
    occupancy:{label:'Occupancy',format:'percent',description:'Total reported patient days ÷ total available bed-days. Reporting scope may include components.',get:r=>{let v=ratio(r.days,r.availableDays);return v!==null&&v>=0&&v<=1?v:null;}},
    lengthOfStay:{label:'Average length of stay',format:'days',description:'Total reported patient days ÷ total discharges; an aggregate report measure.',get:r=>ratio(r.days,r.discharges)},
    patientMargin:{label:'Patient-service margin',format:'percent',description:'Reported net income from service to patients ÷ net patient revenue. Distinct from RAND operating margin.',get:r=>ratio(r.patientIncome,r.netPatientRevenue)},
    totalMargin:{label:'Total margin',format:'percent',description:'Net income ÷ (net patient revenue + total other income). RAND total-margin definition using CMS fields.',get:r=>ratio(r.netIncome,Number.isFinite(r.netPatientRevenue)&&Number.isFinite(r.otherIncome)?r.netPatientRevenue+r.otherIncome:null)},
    currentRatio:{label:'Current ratio',format:'ratio',description:'Total current assets ÷ total current liabilities.',get:r=>ratio(r.currentAssets,r.currentLiabilities)},
    leverage:{label:'Liabilities / assets',format:'percent',description:'Total liabilities ÷ total assets; not debt-only leverage.',get:r=>ratio(r.liabilities,r.assets)},
    medicareShare:{label:'Medicare day share',format:'percent',description:'Title XVIII reported days ÷ total reported days. Not a combined Medicare Advantage share.',get:r=>ratio(r.medicareDays,r.days)},
    medicaidShare:{label:'Medicaid day share',format:'percent',description:'Title XIX reported days ÷ total reported days. Not a separately validated managed-care-inclusive share.',get:r=>ratio(r.medicaidDays,r.days)},
    uncompShare:{label:'Uncompensated care / expense',format:'percent',description:'CMS cost of uncompensated care ÷ operating expense. Does not include all unreimbursed Medicaid/CHIP costs.',get:r=>ratio(r.uncompensated,r.operatingExpense)}
  };
  function median(values){let a=values.filter(Number.isFinite).sort((x,y)=>x-y),n=a.length;return n?(n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2):null;}
  function percentile(value,values){const a=values.filter(Number.isFinite);return !Number.isFinite(value)||!a.length?null:100*(a.filter(v=>v<value).length+.5*a.filter(v=>v===value).length)/a.length;}
  function eligible(r){return r.reportDays>=300&&r.reportDays<=430;}
  function cohort(rows,target,filters){return rows.filter(r=>eligible(r)&&r.ccn!==target.ccn&&r.kind===target.kind&&r.providerType===target.providerType&&(!filters.state||r.state===target.state)&&(!filters.rural||r.rural===target.rural)&&(!filters.size||size(r.beds)===size(target.beds)));}
  function size(b){return !Number.isFinite(b)?'unknown':b<25?'under25':b<100?'25to99':b<300?'100to299':'300plus';}
  const api={metrics,ratio,median,percentile,eligible,cohort,size};
  if(typeof module!=='undefined'&&module.exports)module.exports=api; else root.HospitalMetrics=api;
})(typeof window!=='undefined'?window:globalThis);
