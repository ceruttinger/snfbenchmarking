/* Longitudinal comparisons preserve missing observations and reporting periods. */
(function(root){
  'use strict';
  const M=typeof module!=='undefined'&&module.exports?require('./metrics.js'):root.HospitalMetrics;
  const annual=field=>r=>M.eligible(r)&&Number.isFinite(r[field])?r[field]*365.25/r.reportDays:null;
  const metrics={...M.metrics,
    beds:{label:'Reported beds',format:'number',get:r=>Number.isFinite(r.beds)?r.beds:null},
    discharges:{label:'Discharges · annualized',format:'number',get:annual('discharges')},
    patientDays:{label:'Patient days · annualized',format:'number',get:annual('days')},
    revenue:{label:'Net patient revenue · annualized',format:'money',get:annual('netPatientRevenue')},
    expense:{label:'Operating expense · annualized',format:'money',get:annual('operatingExpense')}
  };
  function quantile(a,p){const v=a.filter(Number.isFinite).sort((a,b)=>a-b);if(!v.length)return null;const i=(v.length-1)*p,l=Math.floor(i);return v[l]+(v[Math.ceil(i)]-v[l])*(i-l);}
  function comparable(previous,current){return !!(previous?.report&&current?.report&&current.year===previous.year+1&&M.eligible(previous.report)&&M.eligible(current.report)&&Date.parse(current.report.begin)-Date.parse(previous.report.end)>0&&Date.parse(current.report.begin)-Date.parse(previous.report.end)<=60*86400000);}
  function series(data,target,filters,peerIds,key,mode){
    const metric=metrics[key],fixed=new Set(peerIds),ordered=data.slice().sort((a,b)=>a.year-b.year);
    if(mode==='balanced')for(const d of ordered){const present=new Set(d.records.filter(r=>M.eligible(r)&&Number.isFinite(metric.get(r))).map(r=>r.ccn));for(const id of fixed)if(!present.has(id))fixed.delete(id);}
    const result=ordered.map(d=>{
      const report=d.records.find(r=>r.ccn===target.ccn),group=mode==='dynamic'?(report?M.cohort(d.records,report,filters):[]):d.records.filter(r=>fixed.has(r.ccn));
      const eligible=group.filter(M.eligible),values=eligible.map(metric.get).filter(Number.isFinite),value=report&&M.eligible(report)?metric.get(report):null,median=values.length>=5?M.median(values):null;
      return {year:d.year,report,value,median,low:values.length>=5?quantile(values,.25):null,high:values.length>=5?quantile(values,.75):null,valid:values.length,eligible:eligible.length,defined:mode==='dynamic'?group.length:fixed.size,gap:Number.isFinite(value)&&Number.isFinite(median)?value-median:null,percentile:values.length>=5?M.percentile(value,values):null};
    });
    result.forEach((r,i)=>{const p=result[i-1];r.change=comparable(p,r)&&Number.isFinite(p.value)&&Number.isFinite(r.value)?r.value-p.value:null;r.growth=['number','money'].includes(metric.format)&&Number.isFinite(r.change)&&p.value>0?r.change/p.value:null;r.peerChange=p&&r.year===p.year+1&&Number.isFinite(p.median)&&Number.isFinite(r.median)?r.median-p.median:null;r.gapChange=Number.isFinite(r.change)&&Number.isFinite(p?.gap)&&Number.isFinite(r.gap)?r.gap-p.gap:null;});
    return result;
  }
  const api={metrics,series,quantile,comparable};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.HospitalHistory=api;
})(typeof window!=='undefined'?window:globalThis);
