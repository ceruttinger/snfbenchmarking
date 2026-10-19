"""CMS exact enrollment/CCN/NPI crosswalk and organization-only NPPES enrichment."""
import json,re
from datetime import datetime,timezone
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from analytics import BASE,QueryError
from ownership_roles import classify
@lru_cache(maxsize=1)
def layer():return json.loads((BASE/'lab/providers.json').read_text())
@lru_cache(maxsize=256)
def nppes(npi):
 if not re.fullmatch(r'\d{10}',npi):return {'npi':npi,'status':'invalid_npi'}
 url='https://npiregistry.cms.hhs.gov/api/?version=2.1&number='+npi
 try:
  with urlopen(Request(url,headers={'Accept':'application/json'}),timeout=10) as r:d=json.load(r)
  results=d.get('results',[])
  if not results:return {'npi':npi,'status':'not_found','source':url}
  r=results[0]
  if r.get('enumeration_type')!='NPI-2':return {'npi':npi,'status':'individual_record_not_published','source':url}
  basic=r['basic'];addresses=[{'purpose':a.get('address_purpose'),'city':a.get('city'),'state':a.get('state'),'postalCode':a.get('postal_code')} for a in r.get('addresses',[])]
  return {'npi':npi,'entityType':'NPI-2','legalName':basic.get('organization_name'),'status':basic.get('status'),'enumerationDate':basic.get('enumeration_date'),'lastUpdated':basic.get('last_updated'),'taxonomies':[{'code':t.get('code'),'description':t.get('desc'),'primary':t.get('primary')} for t in r.get('taxonomies',[])],'locations':addresses,'source':url,'queriedAt':datetime.now(timezone.utc).isoformat(),'linkEvidence':'Exact NPI reported by CMS hospital enrollment. NPI identity is not ownership evidence.'}
 except Exception:return {'npi':npi,'status':'lookup_unavailable','source':url}

@lru_cache(maxsize=128)
def related_enrollments(associate):
 source='https://data.cms.gov/data-api/v1/dataset/2457ea29-fc82-48b0-86ec-3b0755de7515/data'
 if not re.fullmatch(r'\d{1,15}',associate):return {'associateId':associate,'rows':[],'status':'invalid_associate'}
 url=source+'?'+urlencode({'size':200,'filter[PECOS_ASCT_CNTL_ID]':associate,'column':'NPI,PECOS_ASCT_CNTL_ID,ENRLMT_ID,PROVIDER_TYPE_CD,PROVIDER_TYPE_DESC,STATE_CD,ORG_NAME','sort':'ENRLMT_ID'})
 try:
  with urlopen(Request(url,headers={'Accept':'application/json'}),timeout=10) as response:rows=json.load(response)
  if not isinstance(rows,list) or any(str(r.get('PECOS_ASCT_CNTL_ID'))!=associate for r in rows):raise ValueError('Provider API filter mismatch')
  orgs=[r for r in rows if r.get('ORG_NAME','').strip()]
  return {'associateId':associate,'rows':[{'npi':r['NPI'],'enrollmentId':r['ENRLMT_ID'],'associateId':r['PECOS_ASCT_CNTL_ID'],'providerType':r['PROVIDER_TYPE_DESC'],'providerTypeCode':r['PROVIDER_TYPE_CD'],'state':r['STATE_CD'],'legalName':r['ORG_NAME']} for r in orgs],'source':url,'sourceVintage':'2026-07-01','queriedAt':datetime.now(timezone.utc).isoformat(),'limit':200,'possiblyTruncated':len(rows)==200,'status':'source_reported','meaning':'Exact CMS associate-ID enrollment link. Provider category does not imply ownership, clinical employment or loaded financial data.'}
 except Exception:return {'associateId':associate,'rows':[],'source':url,'status':'lookup_unavailable'}

def inspect(ccn):
 if not isinstance(ccn,str) or not re.fullmatch(r'\d{6}',ccn):raise QueryError('Use a six-digit CCN.')
 d=layer();providers=[p for p in d['providers'] if p['ccn']==ccn];relationships=[{**r,'relationship':classify(r['role'])} for r in d['relationships'] if r['ccn']==ccn];npis=sorted({p['npi'] for p in providers if re.fullmatch(r'\d{10}',p['npi'])})
 with ThreadPoolExecutor(max_workers=5) as pool:organizations=list(pool.map(nppes,npis[:5]))
 owners={r['ownerAssociateId'] for r in relationships}
 with ThreadPoolExecutor(max_workers=5) as pool:cross_category=list(pool.map(related_enrollments,sorted(owners)[:5]))
 related=[r for r in d['relationships'] if r['ownerAssociateId'] in owners and r['ccn']!=ccn];relatedids=sorted({r['ccn'] for r in related})
 # The national cross-category evidence is a separate, exact-ID layer. Enrollments
 # returned above remain distinct from its reported ownership interests.
 from network import inspect as inspect_network
 network=inspect_network(ccn)
 return {'ccn':ccn,'enrollments':providers,'organizationalRelationships':relationships,'nppes':organizations,'crossCategoryEnrollments':cross_category,'network':network,'associateLookupLimit':5,'nppesLookupLimit':5,'npiCount':len(npis),'relatedHospitalCcns':relatedids[:50],'relatedHospitalCount':len(relatedids),'relationshipMeaning':'Other hospitals reporting at least one of the same organizational associates; shared disclosure is not proof of ultimate common control.','sources':d['sources'],'snapshotSha256':d['snapshotSha256'],'queriedAt':d['queriedAt'],'limitations':d['limitations']}
