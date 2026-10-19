"""API-only workforce sidecar, exact report-ID/CCN/period joins to frozen finances.

Raw API responses stay in memory. Never substitute another report for missing IDs.
"""
import gzip,hashlib,json,sys,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hospitals'))
from build_data import URLS,number,parse_date
FIELDS={'payrollFte':'FTE - Employees on Payroll',
        'residentFte':'Number of Interns and Residents (FTE)',
        'salaries':'Total Salaries From Worksheet A'}
IDENTITY=['rpt_rec_num','Provider CCN','Fiscal Year Begin Date','Fiscal Year End Date']

def join_report(r,row):
 return (str(r['reportId'])==str(row['rpt_rec_num'])
   and r['ccn']==row['Provider CCN'].strip().zfill(6)
   and r['begin']==parse_date(row['Fiscal Year Begin Date']).date().isoformat()
   and r['end']==parse_date(row['Fiscal Year End Date']).date().isoformat())

def clean(v):
 n=number(v)
 return n if n is not None and n>=0 else None

def build():
 out=ROOT/'docs/hospitals/workforce';out.mkdir(exist_ok=True)
 audit={}
 for year,url in sorted(URLS.items()):
  offset=0;rows=[];seen=set()
  while True:
   q=urlencode({'size':1000,'offset':offset,'sort':'rpt_rec_num','column':','.join(IDENTITY+list(FIELDS.values()))})
   for attempt in range(4):
    try:
     with urlopen(Request(url+'?'+q,headers={'Accept':'application/json'}),timeout=60) as response:page=json.load(response)
     break
    except Exception:
     if attempt==3:raise
     time.sleep(2**attempt)
   if not isinstance(page,list):raise ValueError('Expected API array')
   for r in page:
    if not all(k in r for k in IDENTITY+list(FIELDS.values())):raise ValueError('Missing workforce API fields')
    if str(r['rpt_rec_num']) in seen:raise ValueError('Repeated report across API pages')
    seen.add(str(r['rpt_rec_num']))
   rows.extend(page)
   if len(page)<1000:break
   offset+=len(page)
   if offset>100000:raise ValueError('Unexpected pagination')
  with gzip.open(ROOT/f'docs/hospitals/data-{year}.json.gz','rt') as f:financial=json.load(f)
  raw={str(r['rpt_rec_num']):r for r in rows};derived=[];counts=Counter()
  for values in financial['rows']:
   r=dict(zip(financial['columns'],values));match=raw.get(str(r['reportId']))
   ok=bool(match and join_report(r,match));counts['matchedReports' if ok else 'unmatchedReports']+=1
   vals=[clean(match[field]) if ok else None for field in FIELDS.values()]
   for key,v in zip(FIELDS,vals):
    if v is not None:counts[key+'Valid']+=1
   derived.append([r['ccn'],str(r['reportId']),*vals])
  sha=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  payload={'year':year,'columns':['ccn','reportId',*FIELDS],'rows':derived,
   'source':url,'queriedAt':datetime.now(timezone.utc).isoformat(),'apiRecordsSha256':sha,
   'inputReports':len(rows),'selectedReports':len(derived),'coverage':dict(counts),
   'join':'Exact report ID + CCN + fiscal begin/end against existing financial snapshot. Unmatched reports remain null.',
   'fields':FIELDS,'missingPolicy':'Blank, nonfinite and negative values unavailable; reported zero retained. No imputation.'}
  (out/f'data-{year}.json.gz').write_bytes(gzip.compress(json.dumps(payload,separators=(',',':'),allow_nan=False).encode(),mtime=0))
  audit[str(year)]={k:v for k,v in payload.items() if k not in ['rows','columns']}
  print(year,json.dumps(payload['coverage']),flush=True)
 (out/'manifest.json').write_text(json.dumps(audit,indent=2)+'\n')
if __name__=='__main__':build()
