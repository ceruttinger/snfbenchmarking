"""National cross-category CMS organizational ownership; exact IDs only.

Catalog input is metadata, API responses remain in RAM, retained file is derived
organization-only evidence. No names of individual owners or addresses retained.
"""
import hashlib,json,re,time
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from ownership_roles import classify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/hospitals/lab'
CATALOG=json.loads((ROOT/'ai/network-sources.json').read_text())
PAIRS={'SNF':'Skilled Nursing Facility','Home health':'Home Health Agency','Hospice':'Hospice','FQHC':'Federally Qualified Health Center','RHC':'Rural Health Clinic'}
EF=['ENROLLMENT ID','ASSOCIATE ID','CCN','NPI','ORGANIZATION NAME','DOING BUSINESS AS NAME','STATE','CITY','PROVIDER TYPE TEXT']
OF=['ENROLLMENT ID','ASSOCIATE ID','ASSOCIATE ID - OWNER','ORGANIZATION NAME - OWNER','ROLE CODE - OWNER','ROLE TEXT - OWNER','ASSOCIATION DATE - OWNER','PERCENTAGE OWNERSHIP','PRIVATE EQUITY COMPANY - OWNER','REIT - OWNER']
def fetch(source,fields,filters=None):
 rows=[];offset=0
 while True:
  url=source['url']+'?'+urlencode({'size':5000,'offset':offset,'sort':fields[0],'column':','.join(fields),**(filters or {})})
  for attempt in range(4):
   try:
    with urlopen(Request(url,headers={'Accept':'application/json'}),timeout=75) as f:page=json.load(f)
    break
   except Exception:
    if attempt==3:raise
    time.sleep(2**attempt)
  if not isinstance(page,list) or any(set(fields)-set(r) for r in page):raise ValueError('Unexpected CMS schema')
  rows.extend(page)
  if len(page)<5000:break
  offset+=len(page)
  if offset>1000000:raise ValueError('Unexpected pagination size')
 source['inputRows']=len(rows);source['queriedAt']=datetime.now(timezone.utc).isoformat();source['sha256']=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 print(source['title'],len(rows),flush=True);return rows
def pct(v):
 try:n=float(v);return n if 0<=n<=100 else None
 except (ValueError,TypeError):return None
def relation(role):return classify(role)
def build():
 sources={};facilities=[];assertions=[];coverage=[];events=[]
 hospital=json.loads((OUT/'providers.json').read_text())
 for p in hospital['providers']:
  facilities.append({'id':p['ccn'],'category':'Hospital','ccn':p['ccn'],'enrollmentId':p['enrollmentId'],'associateId':p['associateId'],'npi':p['npi'],'name':p['dba'] or p['legalName'],'legalName':p['legalName'],'state':p['state'],'city':p['city'],'sourceId':'hospital:enrollments'})
 for a in hospital['relationships']:
  assertions.append({'facilityId':a['ccn'],'category':'Hospital','enrollmentId':a['enrollmentId'],'ownerAssociateId':a['ownerAssociateId'],'ownerName':a['ownerName'],'role':a['role'],'roleCode':a['roleCode'],'percentage':pct(a['percentage']),'associationDate':a['associationDate'],'relationship':classify(a['role']),'sourceId':'hospital:owners','sourceVintage':a['sourceVintage']})
 for k,s in hospital['sources'].items():sources['hospital:'+k]={**s,'title':'Hospital '+k,'sha256':hospital['snapshotSha256'],'queriedAt':hospital['queriedAt']}
 coverage.append({'category':'Hospital','facilities':len({p['ccn'] for p in hospital['providers']}),'organizationalAssertions':len(hospital['relationships']),'ownershipCoverage':'Organizational disclosures','vintage':hospital['sources']['owners']['vintage']})
 for category,title in PAIRS.items():
  es={**CATALOG[title+' Enrollments']};os={**CATALOG[title+' All Owners']};enroll=fetch(es,EF);owners=fetch(os,OF);sources[category+':enrollments']=es;sources[category+':owners']=os
  byid=defaultdict(list);kept=0;excluded=0;seen=set()
  for r in enroll:
   c=r['CCN'].strip().zfill(6)
   if not re.fullmatch(r'\d{6}',c) or not r['ORGANIZATION NAME'].strip():continue
   p={'id':category+':'+c,'category':category,'ccn':c,'enrollmentId':r['ENROLLMENT ID'],'associateId':r['ASSOCIATE ID'],'npi':r['NPI'],'name':r['DOING BUSINESS AS NAME'] or r['ORGANIZATION NAME'],'legalName':r['ORGANIZATION NAME'],'state':r['STATE'],'city':r['CITY'],'sourceId':category+':enrollments'}
   facilities.append(p);byid[p['enrollmentId']].append(p)
  for r in owners:
   if not r['ORGANIZATION NAME - OWNER'].strip() or not r['ASSOCIATE ID - OWNER'].strip():excluded+=1;continue
   for p in byid.get(r['ENROLLMENT ID'],[]):
    if r['ASSOCIATE ID']!=p['associateId']:raise ValueError('Enrollment/associate crosswalk disagreement')
    a={'facilityId':p['id'],'category':category,'enrollmentId':p['enrollmentId'],'ownerAssociateId':r['ASSOCIATE ID - OWNER'],'ownerName':r['ORGANIZATION NAME - OWNER'],'role':r['ROLE TEXT - OWNER'],'roleCode':r['ROLE CODE - OWNER'],'percentage':pct(r['PERCENTAGE OWNERSHIP']),'associationDate':r['ASSOCIATION DATE - OWNER'],'relationship':relation(r['ROLE TEXT - OWNER']),'sourceId':category+':owners','sourceVintage':os['vintage']}
    identity=json.dumps(a,sort_keys=True)
    if identity in seen:continue
    seen.add(identity);assertions.append(a);kept+=1
  coverage.append({'category':category,'facilities':len({p['id'] for values in byid.values() for p in values}),'enrollmentRowsQueried':len(enroll),'retainedEnrollmentRows':sum(len(v) for v in byid.values()),'omittedEnrollmentRows':len(enroll)-sum(len(v) for v in byid.values()),'organizationalAssertions':kept,'omittedIndividualOrUnidentifiedRows':excluded,'ownershipCoverage':'Organizational disclosures','vintage':os['vintage']})
 cs={**CATALOG['Hospital Change of Ownership']};fields=[k for k in cs['columns'] if k not in ['MULTIPLE NPI FLAG - BUYER','MULTIPLE NPI FLAG - SELLER']];rows=fetch(cs,fields);sources['hospital:chow']=cs
 for r in rows:
  event={'effectiveDate':r['EFFECTIVE DATE'],'eventType':r['CHOW TYPE TEXT'],'buyerCcn':r['CCN - BUYER'].zfill(6),'sellerCcn':r['CCN - SELLER'].zfill(6),'buyerAssociateId':r['ASSOCIATE ID - BUYER'],'sellerAssociateId':r['ASSOCIATE ID - SELLER'],'buyerName':r['ORGANIZATION NAME - BUYER'],'sellerName':r['ORGANIZATION NAME - SELLER'],'buyerEnrollmentId':r['ENROLLMENT ID - BUYER'],'sellerEnrollmentId':r['ENROLLMENT ID - SELLER'],'sourceId':'hospital:chow'}
  event['id']=hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest();events.append(event)
 # ESRD and CMHC: exact institutional enrollment identities, no ownership inference.
 generic='https://data.cms.gov/data-api/v1/dataset/2457ea29-fc82-48b0-86ec-3b0755de7515/data'
 for category,code in [('Renal','00-03'),('CMHC','00-01')]:
  s={'url':generic,'title':'CMS Medicare FFS enrollment · '+category,'vintage':'2026-07-01'};fs=['ENRLMT_ID','PECOS_ASCT_CNTL_ID','NPI','PROVIDER_TYPE_CD','PROVIDER_TYPE_DESC','STATE_CD','ORG_NAME'];rows=fetch(s,fs,{'filter[PROVIDER_TYPE_CD]':code});sources[category+':enrollments']=s
  for r in rows:
   if r['PROVIDER_TYPE_CD']!=code:raise ValueError('Provider category API filter mismatch')
   if not r['ORG_NAME'].strip():continue
   facilities.append({'id':category+':'+r['ENRLMT_ID'],'category':category,'ccn':'','enrollmentId':r['ENRLMT_ID'],'associateId':r['PECOS_ASCT_CNTL_ID'],'npi':r['NPI'],'name':r['ORG_NAME'],'legalName':r['ORG_NAME'],'state':r['STATE_CD'],'city':'','sourceId':category+':enrollments'})
  coverage.append({'category':category,'facilities':sum(p['category']==category for p in facilities),'organizationalAssertions':0,'ownershipCoverage':'Enrollment only; ownership unavailable in this layer','vintage':s['vintage']})
 result={'sources':sources,'facilities':facilities,'assertions':assertions,'events':list({e['id']:e for e in events}.values()),'coverage':coverage,'queriedAt':datetime.now(timezone.utc).isoformat(),
 'limitations':['Institutional roster rows with missing/nonnumeric six-character CCNs or missing legal organization names are omitted; coverage is retained CCN units, not a complete site census. Renal and CMHC counts use enrollment IDs, not CCNs or physical sites.','Security, mortgage, ADP and trustee roles are associations, not assumed ownership or control.','Exact CMS associate IDs link disclosed organizations across categories; similar names are never merged.','No complete ultimate-parent hierarchy. Direct/indirect roles and percentages must not be summed across tiers.','Different source vintages; current disclosures are not historical ownership intervals.','CHOW is self-reported event evidence, not a continuous ownership history or causal attribution.','Renal and CMHC have enrollment identity only; missing ownership is unknown.','Only organizational owners are retained. Financial benchmarking still covers hospitals only.']}
 result['snapshotSha256']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();(OUT/'network.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps(coverage,indent=2))
if __name__=='__main__':build()
