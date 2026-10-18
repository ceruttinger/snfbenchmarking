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
for(const year of [2017,2018,2019,2020,2021,2022,2023,2024]){const p=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(__dirname,'../docs/hospitals/data-'+year+'.json.gz'))));const rows=p.rows.map(a=>Object.fromEntries(p.columns.map((k,i)=>[k,a[i]])));assert.equal(new Set(rows.map(r=>r.ccn)).size,rows.length);assert.ok(rows.length>5000);for(const r of rows){assert.match(r.ccn,/^\d{6}$/);assert.equal(r.reportDays,Math.round((Date.parse(r.end)-Date.parse(r.begin))/86400000)+1);}const sample=rows.find(r=>r.days>0&&r.availableDays>=r.days&&r.currentLiabilities>0);assert.equal(M.metrics.occupancy.get(sample),sample.days/sample.availableDays);assert.equal(M.metrics.currentRatio.get(sample),sample.currentAssets/sample.currentLiabilities);console.log(year+': '+rows.length+' unique providers validated.');}
const t={...target,rural:'U',control:'2',county:'Washington',city:'Springfield'};
const fixtures=[
 {...t,ccn:'000011',beds:99},
 {...t,ccn:'000012',beds:100},
 {...t,ccn:'000013',state:'OR'},
 {...t,ccn:'000014',state:'IL'},
 {...t,ccn:'000015',control:'4'},
 {...t,ccn:'000016',kind:'PH',providerType:'4'},
 {...t,ccn:'000017',reportDays:61},
 {...t,ccn:'000018',beds:null},
 t
];
const ids=f=>M.cohort(fixtures,t,{category:'any',providerType:'any',bedBand:'any',...f}).map(r=>r.ccn);
assert.deepEqual(ids({scope:'city',geoState:'UT',city:'springfield',minBeds:50,maxBeds:99,ownership:'nonprofit'}),['000011','000016']);
assert.deepEqual(ids({scope:'county',geoState:'UT',county:'Washington',control:'4'}),['000015']);
assert.deepEqual(ids({scope:'region',region:'Midwest'}),['000014']);
assert.deepEqual(ids({scope:'state',geoState:'UT',minBeds:99,maxBeds:100,excluded:['000012']}),['000011']);
assert.equal(ids({category:'PH',providerType:'4'}).length,1);
assert.equal(ids({category:'PH',providerType:'1'}).length,0);
assert.equal(ids({ownership:'government'}).length,0);
assert.equal(ids({minBeds:0}).includes('000018'),false);
assert.equal(ids({}).includes(t.ccn),false);
console.log('Metric, missing-value, cohort, geographic-boundary, ownership and reporting-period checks passed.');
