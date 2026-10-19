"""Reproducible descriptive research summaries from frozen API-derived data."""
import json,statistics
from datetime import date
from pathlib import Path
from analytics import CAT,YEARS,dataset,eligible,metric,finite
def med(v):return statistics.median(v) if len(v)>=5 else None
rural=[]
for y in YEARS:
 for group in ['CAH','Other rural','Urban']:
  rows=[r for r in dataset(y).values() if eligible(r) and r['providerType']=='1'
        and ('CAH' if r['kind']=='CAH' else 'Other rural' if r['rural']=='R' else 'Urban' if r['rural']=='U' else 'Unknown')==group]
  margins=[metric('totalMargin',r) for r in rows];margins=[v for v in margins if finite(v)]
  rural.append({'year':y,'group':group,'hospitals':len(rows),'validMargins':len(margins),
    'medianMarginPct':100*med(margins) if len(margins)>=5 else None,
    'lossPct':100*sum(v<0 for v in margins)/len(margins) if len(margins)>=5 else None})
before=dataset(2019);after=dataset(2024);capacity=[];workforce=[]
for c,b in after.items():
 a=before.get(c)
 if not a or not eligible(a) or not eligible(b) or a['providerType']!='1' or b['providerType']!='1' or a['end']>=b['begin']:continue
 if finite(a['beds']) and a['beds']>0 and finite(b['beds']) and b['beds']>=0:
  capacity.append({'ccn':c,'hospital':b['name'],'state':b['state'],'beds2019':a['beds'],'beds2024':b['beds'],'bedChange':b['beds']-a['beds']})
 f0=metric('payrollFte',a);f1=metric('payrollFte',b);d0=metric('patientDays',a);d1=metric('patientDays',b)
 if all(finite(v) and v>0 for v in [f0,f1,d0,d1]):
  workforce.append({'ccn':c,'hospital':b['name'],'state':b['state'],'fte2019':f0,'fte2024':f1,
    'fteGrowthPct':100*(f1/f0-1),'patientDaysGrowthPct':100*(d1/d0-1),
    'daysPerFteGrowthPct':100*((d1/f1)/(d0/f0)-1)})
capacity.sort(key=lambda r:(r['bedChange'],r['ccn']))
workforce.sort(key=lambda r:(-r['daysPerFteGrowthPct'],r['ccn']))
payload={'catalogSha256':CAT['catalogSha256'],'baseline':2019,'endpoint':2024,'ruralFinance':rural,
 'capacity':{'matchedHospitals':len(capacity),'beds2019':sum(r['beds2019'] for r in capacity),'beds2024':sum(r['beds2024'] for r in capacity),'largestReductions':[r for r in capacity if r['bedChange']<0][:25]},
 'workforce':{'matchedHospitals':len(workforce),'hospitalsWithDaysGrowingFasterThanFte':sum(r['daysPerFteGrowthPct']>0 for r in workforce),
   'medianFteGrowthPct':med([r['fteGrowthPct'] for r in workforce]),'medianPatientDaysGrowthPct':med([r['patientDaysGrowthPct'] for r in workforce]),
   'largestWorkloadIncreases':[r for r in workforce if r['daysPerFteGrowthPct']>0][:25]},
 'notes':['General short-term hospital reports including CAHs; report complex may span campuses.',
  'Rural finance uses changing annual cohorts; endpoints use matched CCNs, eligible nonoverlapping fiscal periods and valid inputs.',
  'No causal, closure, shortage, acuity, inflation or occupational staffing adjustment. Extreme changes require reporting-boundary review.',
  'Patient days per all-occupation payroll FTE omits outpatient work. Missing and zero FTE denominators are excluded.',
  'Workforce sources may be refreshed later than the frozen financial snapshot; exact report ID, CCN and fiscal-period joins do not establish same revision vintage.'],
 'sources':{'financial':CAT['sources'],'workforce':CAT['workforceSources']}}
(Path(__file__).resolve().parents[1]/'docs/hospitals/lab/policy.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:{x:y for x,y in v.items() if not isinstance(y,list)} for k,v in payload.items() if k in ['capacity','workforce']},indent=2))
