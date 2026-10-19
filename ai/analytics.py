"""Read-only semantic query engine. No generated SQL or model arithmetic."""
import gzip,hashlib,json,math,os,re,statistics
from datetime import date
from functools import lru_cache
from pathlib import Path
BASE=Path(os.environ.get('HOSPITAL_DATA_DIR',Path(__file__).resolve().parents[1]/'docs/hospitals'))
CAT=json.loads((BASE/'lab/semantic.json').read_text())
YEARS=CAT['years']
REGIONS={'Northeast':'CT ME MA NH RI VT NJ NY PA','Midwest':'IL IN MI OH WI IA KS MN MO NE ND SD','South':'DE FL GA MD NC SC VA DC WV AL KY MS TN AR LA OK TX','West':'AZ CO ID MT NV NM UT WY AK CA HI OR WA','Territories':'GU MP PR VI'}
class QueryError(ValueError): pass

def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def eligible(r): return bool(r) and 300<=r.get('reportDays',0)<=430
def metric(key,r):
 def calc(e):
  if 'field' in e and 'op' not in e:return r.get(e['field'])
  if e['op']=='scale':
   v=calc(e['arg']);return v*e['factor'] if finite(v) else None
  if e['op']=='annualize':return r[e['field']]*365.25/r['reportDays'] if eligible(r) and finite(r.get(e['field'])) else None
  a,b=map(calc,e['args'])
  if not finite(a) or not finite(b):return None
  return a+b if e['op']=='add' else a/b if b>0 else None
 v=calc(CAT['metrics'][key]['expression'])
 limits=CAT['metrics'][key].get('validRange')
 return v if finite(v) and (not limits or limits[0]<=v<=limits[1]) else None
@lru_cache(maxsize=8)
def dataset(year):
 with gzip.open(BASE/f'data-{year}.json.gz','rt') as f:d=json.load(f)
 records={str(r[0]):dict(zip(d['columns'],r)) for r in d['rows']}
 workforce=BASE/'workforce'/f'data-{year}.json.gz'
 if workforce.exists():
  with gzip.open(workforce,'rt') as f:w=json.load(f)
  for row in w['rows']:
   extra=dict(zip(w['columns'],row));r=records.get(extra['ccn'])
   if r and str(r['reportId'])==str(extra['reportId']):r.update({k:v for k,v in extra.items() if k not in ['ccn','reportId']})
 return records
def ownership(r):
 try:c=int(r['control'])
 except (ValueError,TypeError,KeyError):return 'unknown'
 return 'nonprofit' if c in [1,2] else 'proprietary' if 3<=c<=6 else 'government' if 7<=c<=13 else 'unknown'
def band(b):return 'unknown' if not finite(b) else 'under25' if b<25 else '25to99' if b<100 else '100to299' if b<300 else '300plus'
def cohort(rows,target,f,include_target=False):
 def match(r):
  if not eligible(r) or (not include_target and r['ccn']==target['ccn']):return False
  for dim,field in [('category','kind'),('providerType','providerType')]:
   v=f.get(dim,'same')
   if v!='any' and str(r[field])!=str(target[field] if v=='same' else v):return False
  scope=f.get('scope','national')
  if scope=='region' and r['state'] not in REGIONS.get(f.get('region'), '').split():return False
  if scope in ['state','county','city'] and r['state']!=f.get('geoState'):return False
  if scope in ['county','city'] and (not f.get(scope) or str(r.get(scope,'')).strip().lower()!=f[scope].strip().lower()):return False
  o=f.get('ownership','any')
  if o!='any' and ownership(r)!=(ownership(target) if o=='same' else o):return False
  if f.get('control','any')!='any' and str(r['control'])!=str(f['control']):return False
  if f.get('rural','any')!='any' and r['rural']!=f['rural']:return False
  size=f.get('bedBand','any')
  if size!='any' and band(r['beds'])!=(band(target['beds']) if size=='same' else size):return False
  for field,op in [('minBeds',lambda a,b:a<b),('maxBeds',lambda a,b:a>b)]:
   if f.get(field) is not None and (not finite(r.get('beds')) or op(r['beds'],f[field])):return False
  return r['ccn'] not in f.get('excluded',[])
 return [r for r in rows if match(r)]

def validate(q):
 if not isinstance(q,dict):raise QueryError('A structured query object is required.')
 allowed={'analysis','targetCcn','anchorYear','startYear','endYear','metrics','filters','mode','sortBy','direction','limit','conditions'}
 if set(q)-allowed:raise QueryError('Unsupported query fields: '+', '.join(sorted(set(q)-allowed)))
 q={'targetCcn':'460010','anchorYear':2024,'startYear':2017,'endYear':2024,'metrics':['occupancy'],'filters':{},'mode':'fixed','sortBy':'value','direction':'desc','limit':10,'conditions':[],**q}
 if q.get('analysis') not in ['trend','compare','rank','definition','coverage','ownership']:raise QueryError('Choose trend, compare, rank, definition, coverage or ownership.')
 if not isinstance(q['targetCcn'],str) or not re.fullmatch(r'\d{6}',q['targetCcn']):raise QueryError('Use a six-digit hospital CCN.')
 for k in ['anchorYear','startYear','endYear']:
  if type(q[k]) is not int or q[k] not in YEARS:raise QueryError('Supported dataset years are 2017–2024.')
 if q['startYear']>q['endYear']:raise QueryError('Start year must not exceed end year.')
 if not isinstance(q['metrics'],list) or not 1<=len(q['metrics'])<=3 or any(k not in CAT['metrics'] for k in q['metrics']):raise QueryError('Choose one to three defined semantic metrics.')
 if q['mode'] not in ['fixed','dynamic','balanced'] or q['sortBy'] not in ['value','change'] or q['direction'] not in ['asc','desc'] or type(q['limit']) is not int or not 1<=q['limit']<=25:raise QueryError('Unsupported cohort, ordering or row limit.')
 f=q['filters']
 if isinstance(f,dict):
  f={'scope':'national','category':'any' if q['analysis']=='rank' else 'same','providerType':'any' if q['analysis']=='rank' else 'same','bedBand':'any','ownership':'any',**f};q['filters']=f
 fa={'scope','region','geoState','county','city','category','providerType','ownership','control','rural','bedBand','minBeds','maxBeds','excluded'}
 if not isinstance(f,dict) or set(f)-fa:raise QueryError('Unsupported peer filters.')
 enums={'scope':['national','region','state','county','city'],'region':list(REGIONS),'category':['same','any','STH','CAH','PH','RH','LTCH','CH','RNMHC','ORD','TC'],'providerType':['same','any','1','2','3','4','5','6','7','9','10','11','12'],'ownership':['same','any','nonprofit','proprietary','government'],'control':['any']+[str(i) for i in range(1,14)],'rural':['any','R','U'],'bedBand':['same','any','under25','25to99','100to299','300plus']}
 for k,vs in enums.items():
  if k in f and f[k] not in vs:raise QueryError('Invalid '+k+' filter.')
 for k in ['minBeds','maxBeds']:
  if f.get(k) is not None and (type(f[k]) is not int or not 0<=f[k]<=50000):raise QueryError('Bed bounds must be nonnegative integers.')
 if f.get('minBeds') is not None and f.get('maxBeds') is not None and f['minBeds']>f['maxBeds']:raise QueryError('Minimum beds exceed maximum beds.')
 for k in ['city','county','geoState']:
  if k in f and (not isinstance(f[k],str) or not 1<=len(f[k])<=100):raise QueryError('Invalid geographic filter.')
 if f.get('scope') in ['state','city','county'] and not re.fullmatch('[A-Z]{2}',f.get('geoState','')):raise QueryError('State is required for state/county/city scope.')
 if f.get('scope') in ['county','city'] and not f.get(f['scope']):raise QueryError('A named county/city is required.')
 if f.get('scope','national')=='national' and any(f.get(k) for k in ['region','geoState','city','county']):raise QueryError('Geographic filters require the matching scope; national scope cannot silently ignore a state or locality.')
 if f.get('scope')=='region' and not f.get('region'):raise QueryError('A region is required.')
 if 'excluded' in f and (not isinstance(f['excluded'],list) or len(f['excluded'])>1000 or any(not isinstance(c,str) or not re.fullmatch(r'\d{6}',c) for c in f['excluded'])):raise QueryError('Invalid exclusion list.')
 if not isinstance(q['conditions'],list) or len(q['conditions'])>5:raise QueryError('Use at most five numeric conditions.')
 for c in q['conditions']:
  if not isinstance(c,dict) or set(c)!={'metric','basis','op','value'} or c['metric'] not in CAT['metrics'] or c['basis'] not in ['value','change'] or c['op'] not in ['lt','lte','gt','gte'] or not finite(c['value']):raise QueryError('Invalid numeric condition. Percentage thresholds must use fractions.')
 if q['conditions'] and q['analysis']!='rank':raise QueryError('Numeric row filters are supported only for rankings.')
 if q['analysis']=='rank' and len(q['metrics'])!=1:raise QueryError('Rank by one measure at a time.')
 return q

def quantile(values,p):
 a=sorted(values);i=(len(a)-1)*p;l=int(i);return a[l]+(a[math.ceil(i)]-a[l])*(i-l)
def percentile(v,values):return 100*(sum(x<v for x in values)+.5*sum(x==v for x in values))/len(values) if finite(v) and values else None
def comparable(a,b):return eligible(a) and eligible(b) and 0<(date.fromisoformat(b['begin'])-date.fromisoformat(a['end'])).days<=60

def trend(q,target,ids,key):
 years=list(range(q['startYear'],q['endYear']+1));fixed=set(ids)
 if q['mode']=='balanced':
  for y in years:fixed&={r['ccn'] for r in dataset(y).values() if eligible(r) and finite(metric(key,r))}
 out=[]
 for y in years:
  records=dataset(y);r=records.get(target['ccn']);group=cohort(records.values(),r,q['filters']) if q['mode']=='dynamic' and r else [] if q['mode']=='dynamic' else [records[c] for c in fixed if c in records]
  vals=[metric(key,p) for p in group if eligible(p)];vals=[v for v in vals if finite(v)];v=metric(key,r) if eligible(r) else None;med=statistics.median(vals) if len(vals)>=5 else None
  row={'year':y,'begin':r.get('begin') if r else None,'end':r.get('end') if r else None,'reportId':r.get('reportId') if r else None,'reportDays':r.get('reportDays') if r else None,'target':v,'peerMedian':med,'gap':v-med if finite(v) and finite(med) else None,'percentile':percentile(v,vals) if len(vals)>=5 else None,'validPeers':len(vals),'definedPeers':len(group) if q['mode']=='dynamic' else len(fixed),'peerP25':quantile(vals,.25) if len(vals)>=5 else None,'peerP75':quantile(vals,.75) if len(vals)>=5 else None,'change':None,'gapChange':None}
  if out and comparable(dataset(y-1).get(target['ccn']),r) and finite(v) and finite(out[-1]['target']):
   row['change']=v-out[-1]['target']
   if finite(row['gap']) and finite(out[-1]['gap']):row['gapChange']=row['gap']-out[-1]['gap']
  out.append(row)
 return out

def execute(query):
 q=validate(query);target=dataset(q['anchorYear']).get(q['targetCcn'])
 if not target and q['analysis']!='definition':raise QueryError('Target CCN has no report in the anchor dataset. Choose another anchor year.')
 result={'query':q,'catalogVersion':CAT['version'],'catalogSha256':CAT['catalogSha256'],'queryId':hashlib.sha256(json.dumps(q,sort_keys=True).encode()).hexdigest()[:16],'metrics':{k:CAT['metrics'][k] for k in q['metrics']},'warnings':['Descriptive comparison; not adjusted for case mix, teaching or wages.','Actual fiscal periods differ. Dataset year is not calendar-year standardization.','Dollar values are nominal; missing values are not zero.'],'sources':[{'year':y,**{k:CAT['sources'][str(y)][k] for k in ['source','queriedAt','apiRecordsSha256']}} for y in range(q['startYear'],q['endYear']+1)],'target':{k:target[k] for k in ['ccn','name','state','city','county']} if target else None}
 if any(k in CAT.get('workforceMetrics',[]) for k in q['metrics']):
  result['sources'] += [{'year':str(y)+' workforce',**{k:CAT['workforceSources'][str(y)][k] for k in ['source','queriedAt','apiRecordsSha256']}} for y in range(q['startYear'],q['endYear']+1)]
  result['warnings'].append('Workforce fields are a later API refresh joined to frozen finances by exact report ID, CCN and fiscal period; same report revision vintage is not guaranteed. Payroll FTEs cover all reported employee occupations. Workload per FTE is not a nursing ratio; salaries per FTE are not occupational wages. Contract labor, vacancies and clinician employment are not established.')
 if q['analysis']=='ownership':
  from providers import inspect
  result['provider']=inspect(q['targetCcn']);result['rows']=result['provider']['organizationalRelationships'];result['metrics']={};result['sources']=[{'year':'CMS '+kind+' '+src['vintage'],'source':src['url'],'queriedAt':result['provider']['queriedAt'],'apiRecordsSha256':result['provider']['snapshotSha256']} for kind,src in result['provider']['sources'].items()];result['answer']='CMS-reported organizational ownership interests and control roles for the selected hospital. Exact enrollment-ID joins are evidence of the reported association, not proof of ultimate-parent ownership. NPPES identifies the enrolled organization, not its owner.';return result
 if q['analysis']=='definition':result['rows']=[];result['answer']='Definitions and source-field lineage are shown below. Patient-service margin is not RAND operating margin.';return result
 ids=[r['ccn'] for r in cohort(dataset(q['anchorYear']).values(),target,q['filters'])]
 if q['analysis'] in ['trend','compare']:
  result['series']={k:trend(q,target,ids,k) for k in q['metrics']};result['rows']=result['series'][q['metrics'][0]] if q['analysis']=='trend' else [{**v[-1],'metric':k} for k,v in result['series'].items()];result['answer']=f"Calculated {q['analysis']} for {target['name']} ({target['ccn']}) using {q['mode']} peers. See the results, reporting periods and coverage below; peer statistics require five valid observations."
 elif q['analysis']=='coverage':
  result['rows']=[{'year':y,'reports':len(dataset(y)),'eligibleReports':sum(eligible(r) for r in dataset(y).values()),'validMetricReports':sum(eligible(r) and finite(metric(q['metrics'][0],r)) for r in dataset(y).values())} for y in range(q['startYear'],q['endYear']+1)];result['answer']='Coverage counts for published CMS API snapshots. Missing reports do not establish facility closures.'
 elif q['analysis']=='rank':
  key=q['metrics'][0];earlier=dataset(q['startYear']);matches=cohort(dataset(q['endYear']).values(),target,q['filters'],True);out=[]
  def value(r,k,basis):
   v=metric(k,r)
   if basis=='value':return v
   prev=earlier.get(r['ccn']);return v-metric(k,prev) if q['startYear']<q['endYear'] and eligible(prev) and finite(v) and finite(metric(k,prev)) else None
  for r in matches:
   checks=[]
   for c in q['conditions']:
    v=value(r,c['metric'],c['basis']);checks.append(finite(v) and {'lt':lambda:v<c['value'],'lte':lambda:v<=c['value'],'gt':lambda:v>c['value'],'gte':lambda:v>=c['value']}[c['op']]())
   v=value(r,key,q['sortBy'])
   if finite(v) and all(checks):out.append({'ccn':r['ccn'],'hospital':r['name'],'state':r['state'],'city':r['city'],'beds':r['beds'],'value':v,'basis':q['sortBy'],'begin':r['begin'],'end':r['end'],'reportId':r['reportId']})
  out.sort(key=lambda r:(-r['value'] if q['direction']=='desc' else r['value'],r['ccn']));result['rows']=out[:q['limit']];result['matchedHospitals']=len(out);result['answer']=f"Found {len(out)} eligible matching hospitals; showing {len(result['rows'])}. Rankings include the target if it matches. Changes use the selected endpoints and eligible reports, not a causal estimate."
 return result
