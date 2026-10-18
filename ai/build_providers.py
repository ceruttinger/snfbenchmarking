"""Official CMS ownership/enrollment API ingestion. Organizational evidence only."""
import hashlib,json,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode
BASE=Path(__file__).resolve().parents[1]/'docs/hospitals/lab'
SOURCES={'enrollments':{'url':'https://data.cms.gov/data-api/v1/dataset/f6f6505c-e8b0-4d57-b258-e2b94133aaf2/data','vintage':'2026-08-01'},'owners':{'url':'https://data.cms.gov/data-api/v1/dataset/029c119f-f79c-49be-9100-344d31d10344/data','vintage':'2026-08-02'}}
FIELDS={'enrollments':['ENROLLMENT ID','NPI','CCN','ASSOCIATE ID','ORGANIZATION NAME','DOING BUSINESS AS NAME','CITY','STATE','ZIP CODE','PROVIDER TYPE TEXT','CAH OR HOSPITAL CCN'], 'owners':['ENROLLMENT ID','ASSOCIATE ID','ASSOCIATE ID - OWNER','TYPE - OWNER','ROLE CODE - OWNER','ROLE TEXT - OWNER','ASSOCIATION DATE - OWNER','ORGANIZATION NAME - OWNER','DOING BUSINESS AS NAME - OWNER','CITY - OWNER','STATE - OWNER','PERCENTAGE OWNERSHIP','PRIVATE EQUITY COMPANY - OWNER','REIT - OWNER','CHAIN HOME OFFICE - OWNER']}

def fetch(kind):
 result=[];offset=0
 while True:
  url=SOURCES[kind]['url']+'?'+urlencode({'size':5000,'offset':offset,'column':','.join(FIELDS[kind]),'sort':'ENROLLMENT ID'})
  for retry in range(3):
   try:
    with urlopen(Request(url,headers={'Accept':'application/json'}),timeout=60) as r:page=json.load(r)
    break
   except Exception:
    if retry==2:raise
    time.sleep(2**retry)
  if not isinstance(page,list) or any(set(FIELDS[kind])-set(r) for r in page):raise ValueError('CMS schema changed')
  result.extend(page);print(kind,len(result),flush=True)
  if len(page)<5000:break
  offset+=len(page)
  if offset>500000:raise ValueError('Unexpected CMS result size')
 return result

def build():
 stamp=datetime.now(timezone.utc).isoformat();enroll=fetch('enrollments');owners=fetch('owners');by_id={};providers=[]
 for r in enroll:
  ccn=r['CCN'].strip().zfill(6)
  if not ccn.isdigit() or len(ccn)!=6:continue
  p={'enrollmentId':r['ENROLLMENT ID'],'ccn':ccn,'npi':r['NPI'].strip(),'associateId':r['ASSOCIATE ID'],'legalName':r['ORGANIZATION NAME'],'dba':r['DOING BUSINESS AS NAME'],'city':r['CITY'],'state':r['STATE'],'zip':r['ZIP CODE'],'providerType':r['PROVIDER TYPE TEXT'],'source':'enrollments','observedAt':stamp}
  providers.append(p);by_id.setdefault(p['enrollmentId'],[]).append(p)
 edges=[];excluded=0;seen=set()
 for r in owners:
  # No individual owners or addresses are copied into the public draft.
  name=r['ORGANIZATION NAME - OWNER'].strip();ownerid=r['ASSOCIATE ID - OWNER'].strip()
  if not name or not ownerid:excluded+=1;continue
  for p in by_id.get(r['ENROLLMENT ID'],[]):
   identity=(p['ccn'],p['enrollmentId'],ownerid,r['ROLE CODE - OWNER'],r['ASSOCIATION DATE - OWNER'],r['PERCENTAGE OWNERSHIP'])
   if identity in seen:continue
   seen.add(identity);role=r['ROLE TEXT - OWNER'];is_ownership='ownership' in role.lower() or 'owner' in role.lower()
   edges.append({'ccn':p['ccn'],'enrollmentId':p['enrollmentId'],'providerAssociateId':p['associateId'],'ownerAssociateId':ownerid,'ownerName':name,'ownerDba':r['DOING BUSINESS AS NAME - OWNER'],'role':role,'roleCode':r['ROLE CODE - OWNER'],'relationship':'REPORTED_OWNERSHIP_INTEREST' if is_ownership else 'REPORTED_CONTROL_ROLE','associationDate':r['ASSOCIATION DATE - OWNER'],'percentage':r['PERCENTAGE OWNERSHIP'],'city':r['CITY - OWNER'],'state':r['STATE - OWNER'],'privateEquityFlag':r['PRIVATE EQUITY COMPANY - OWNER'],'reitFlag':r['REIT - OWNER'],'chainHomeOfficeFlag':r['CHAIN HOME OFFICE - OWNER'],'evidenceStatus':'source_reported','confidence':1.0,'confidenceMeaning':'Exact enrollment-ID join to a CMS-reported organizational relationship, not audited ultimate ownership.','source':'owners','sourceVintage':SOURCES['owners']['vintage'],'observedAt':stamp})
 result={'sources':SOURCES,'queriedAt':stamp,'providers':providers,'relationships':edges,'coverage':{'enrollmentRowsQueried':len(enroll),'ownerRowsQueried':len(owners),'providerRowsRetained':len(providers),'hospitalCcns':len({p['ccn'] for p in providers}),'organizationalRelationships':len(edges),'nonOrganizationalOrUnidentifiedOwnerRowsOmitted':excluded},'limitations':['CMS enrollment disclosures are not a complete ultimate-parent registry.','Association dates do not establish termination dates. Do not apply current disclosures to all 2017–2024 financial years.','Managerial/control roles are distinct from ownership interests.','No individual owner data is published. Missing disclosure does not establish independence.','Name similarities may support review candidates, never verified ownership.']}
 result['snapshotSha256']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest();(BASE/'providers.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps(result['coverage'],indent=2))
if __name__=='__main__':build()
