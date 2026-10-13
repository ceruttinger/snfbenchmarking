'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),zlib=require('node:zlib'),path=require('node:path'),M=require('../docs/hospitals/metrics.js');
assert.equal(M.ratio(null,10),null);assert.equal(M.ratio(5,0),null);assert.equal(M.ratio(0,10),0);
assert.equal(M.metrics.patientMargin.get({patientIncome:-20,netPatientRevenue:100}),-.2);
assert.equal(M.metrics.totalMargin.get({netIncome:10,netPatientRevenue:100,otherIncome:25}),.08);
assert.equal(M.metrics.totalMargin.get({netIncome:10,netPatientRevenue:100,otherIncome:null}),null);
assert.equal(M.metrics.occupancy.get({days:101,availableDays:100}),null);
assert.equal(M.median([null,1,2,3,4]),2.5);assert.equal(M.percentile(2,[1,2,2,3]),50);
const target={ccn:'000001',kind:'STH',providerType:'1',state:'UT',rural:'1',beds:50,reportDays:365},candidate={...target,ccn:'000002'};
assert.equal(M.cohort([target,candidate,{...candidate,ccn:'000003',providerType:'12'},{...candidate,ccn:'000004',reportDays:61}],target,{}).length,1);
assert.equal(M.cohort([{...candidate,state:'CO'}],target,{state:true}).length,0);
for(const year of [2022,2023]){const p=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(__dirname,'../docs/hospitals/data-'+year+'.json.gz'))));const rows=p.rows.map(a=>Object.fromEntries(p.columns.map((k,i)=>[k,a[i]])));assert.equal(new Set(rows.map(r=>r.ccn)).size,rows.length);assert.ok(rows.length>5000);for(const r of rows){assert.match(r.ccn,/^\d{6}$/);assert.equal(r.reportDays,Math.round((Date.parse(r.end)-Date.parse(r.begin))/86400000)+1);}const sample=rows.find(r=>r.days>0&&r.availableDays>=r.days&&r.currentLiabilities>0);assert.equal(M.metrics.occupancy.get(sample),sample.days/sample.availableDays);assert.equal(M.metrics.currentRatio.get(sample),sample.currentAssets/sample.currentLiabilities);console.log(year+': '+rows.length+' unique providers validated.');}
console.log('Metric, missing-value, cohort and reporting-period checks passed.');
