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
  const regions={Northeast:'CT ME MA NH RI VT NJ NY PA',Midwest:'IL IN MI OH WI IA KS MN MO NE ND SD',South:'DE FL GA MD NC SC VA DC WV AL KY MS TN AR LA OK TX',West:'AZ CO ID MT NV NM UT WY AK CA HI OR WA',Territories:'GU MP PR VI'};
  function region(state){return Object.keys(regions).find(k=>regions[k].split(' ').includes(state))||'Unknown';}
  function ownership(control){const c=Number(control);return c===1||c===2?'nonprofit':c>=3&&c<=6?'proprietary':c>=7&&c<=13?'government':'unknown';}
  function cohort(rows,target,f){
    const normalized=v=>String(v||'').trim().toLowerCase();
    const category=f.category??'same',providerType=f.providerType??'same',bedBand=f.bedBand??(f.size?'same':'any');
    return rows.filter(r=>{
      if(!eligible(r)||r.ccn===target.ccn)return false;
      if(category==='same'?r.kind!==target.kind:category!=='any'&&r.kind!==category)return false;
      if(providerType==='same'?r.providerType!==target.providerType:providerType!=='any'&&r.providerType!==providerType)return false;
      if(f.state&&r.state!==target.state)return false;
      if(f.scope==='region'&&region(r.state)!==f.region)return false;
      if(['state','county','city'].includes(f.scope)&&(!f.geoState||r.state!==f.geoState))return false;
      if(f.scope==='county'&&(!f.county||normalized(r.county)!==normalized(f.county)))return false;
      if(f.scope==='city'&&(!f.city||normalized(r.city)!==normalized(f.city)))return false;
      if(f.ownership==='same'?ownership(r.control)!==ownership(target.control):f.ownership&&f.ownership!=='any'&&ownership(r.control)!==f.ownership)return false;
      if(f.control&&f.control!=='any'&&r.control!==f.control)return false;
      const rural=f.rural===true?target.rural:f.rural;
      if(rural&&rural!=='any'&&(r.rural!==rural||!['R','U'].includes(r.rural)))return false;
      if(bedBand==='same'?size(r.beds)!==size(target.beds):bedBand!=='any'&&size(r.beds)!==bedBand)return false;
      if(Number.isFinite(f.minBeds)&&(!Number.isFinite(r.beds)||r.beds<f.minBeds))return false;
      if(Number.isFinite(f.maxBeds)&&(!Number.isFinite(r.beds)||r.beds>f.maxBeds))return false;
      return !f.excluded?.includes(r.ccn);
    });
  }
  function size(b){return !Number.isFinite(b)?'unknown':b<25?'under25':b<100?'25to99':b<300?'100to299':'300plus';}
  const api={metrics,ratio,median,percentile,eligible,cohort,size,region,ownership,regions};
  if(typeof module!=='undefined'&&module.exports)module.exports=api; else root.HospitalMetrics=api;
})(typeof window!=='undefined'?window:globalThis);
