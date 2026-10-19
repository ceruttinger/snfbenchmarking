"""Bounded exact-record API audit of flagged endpoints; no raw files retained."""
import hashlib,json,sys,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from analytics import BASE,CAT,dataset
from build_workforce import clean
p=json.loads((BASE/'lab/policy.json').read_text())
ccns=list(dict.fromkeys([r['ccn'] for r in p['workforce']['reviewRecords'][:10]]+[r['ccn'] for r in p['capacity']['reviewRecords'][:5]]))
fields={'payrollFte':'FTE - Employees on Payroll','salaries':'Total Salaries From Worksheet A','beds':'Number of Beds','days':'Total Days (V + XVIII + XIX + Unknown)'}
def audit(pair):
 c,y=pair;r=dataset(y)[c];url=CAT['sources'][str(y)]['source']+'?'+urlencode({'size':2,'filter[rpt_rec_num]':r['reportId'],'column':','.join(['rpt_rec_num','Provider CCN',*fields.values()])})
 try:
  with urlopen(url,timeout=45) as f:rows=json.load(f)
  if len(rows)!=1 or rows[0]['Provider CCN'].zfill(6)!=c or str(rows[0]['rpt_rec_num'])!=str(r['reportId']):raise ValueError('Exact record mismatch')
  row=rows[0];checks=[]
  for k,field in fields.items():
   current=clean(row[field]);frozen=r.get(k)
   checks.append({'field':k,'selectedValue':frozen,'apiValue':current,'match':current==frozen})
  return {'ccn':c,'hospital':r['name'],'year':y,'reportId':str(r['reportId']),'begin':r['begin'],'end':r['end'],'checks':checks,'status':'source_values_match' if all(x['match'] for x in checks) else 'source_revision_or_difference','source':url,'apiRecordSha256':hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()}
 except Exception as e:return {'ccn':c,'year':y,'reportId':str(r['reportId']),'status':'audit_unavailable','errorType':type(e).__name__,'source':url}
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(audit,[(c,y) for c in ccns for y in [2019,2024]]))
out={'queriedAt':datetime.now(timezone.utc).isoformat(),'sampleSelection':'Top ten flagged workforce changes plus first five flagged capacity changes; two endpoints each. Bounded, non-random audit, not validation of the entire dataset.',
 'recordsChecked':len(results),'matchingSourceRecords':sum(r['status']=='source_values_match' for r in results),'results':results,
 'meaning':'Matching source values verifies extraction/calculation inputs, not correctness of the provider filing, staffing scope or employment. No flagged record is automatically cleared by this audit.'}
(BASE/'lab/validation.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
