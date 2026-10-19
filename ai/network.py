"""Read-only exact-ID organizational footprint and dated event inspection."""
import json,re
from collections import defaultdict,Counter
from functools import lru_cache
from analytics import BASE,QueryError
@lru_cache(maxsize=1)
def layer():return json.loads((BASE/'lab/network.json').read_text())
def overview():
 d=layer();byowner=defaultdict(set);orgs={};facilities={p['id']:p for p in d['facilities']}
 for a in d['assertions']:
  if a['relationship']!='REPORTED_OWNERSHIP_INTEREST':continue
  byowner[a['ownerAssociateId']].add(a['facilityId']);orgs[a['ownerAssociateId']]=a['ownerName']
 rows=[]
 for oid,ids in byowner.items():
  counts=Counter(facilities[f]['category'] for f in ids)
  if len(counts)>1:rows.append({'associateId':oid,'organization':orgs[oid],'facilityCount':len(ids),'categoryCount':len(counts),'categories':dict(counts)})
 rows.sort(key=lambda r:(-r['categoryCount'],-r['facilityCount'],r['associateId']))
 return {'coverage':d['coverage'],'crossCategoryOrganizations':len(rows),'largestCrossCategoryFootprints':rows[:30],'hospitalEvents':len(d['events']),'eventsByYear':dict(sorted(Counter(e['effectiveDate'][:4] for e in d['events']).items())),
  'sources':d['sources'],'snapshotSha256':d['snapshotSha256'],'queriedAt':d['queriedAt'],'limitations':d['limitations']}
def inspect(ccn):
 if not isinstance(ccn,str) or not re.fullmatch(r'\d{6}',ccn):raise QueryError('Use a six-digit hospital CCN.')
 d=layer();target=[a for a in d['assertions'] if a['facilityId']==ccn and a['category']=='Hospital'];owners={a['ownerAssociateId'] for a in target if a['relationship']=='REPORTED_OWNERSHIP_INTEREST'}
 facilities={p['id']:p for p in d['facilities']};ids={a['facilityId'] for a in d['assertions'] if a['ownerAssociateId'] in owners and a['relationship']=='REPORTED_OWNERSHIP_INTEREST'}
 related=[facilities[i] for i in ids if i!=ccn];related.sort(key=lambda p:(p['category'],p['state'],p['name']))
 owner_rows=[{'associateId':a['ownerAssociateId'],'organization':a['ownerName'],'role':a['role'],'percentage':a['percentage'],'sourceVintage':a['sourceVintage']} for a in target if a['relationship']=='REPORTED_OWNERSHIP_INTEREST']
 events=[e for e in d['events'] if ccn in [e['buyerCcn'],e['sellerCcn']]];events.sort(key=lambda e:e['effectiveDate'],reverse=True)
 return {'ccn':ccn,'disclosedOwnershipOrganizations':len(owners),'sourceReportedOwners':owner_rows[:100],'ownerAssertionCount':len(owner_rows),'ownerAssertionLimit':100,'relatedFacilityCount':len(related),'relatedCategoryCounts':dict(Counter(p['category'] for p in related)),
  'relatedFacilities':[{k:p[k] for k in ['id','category','ccn','name','state','npi']} for p in related[:100]],'facilityLimit':100,'possiblyTruncated':len(related)>100,
  'hospitalEvents':events[:50],'eventCount':len(events),'eventLimit':50,'sourceSnapshotSha256':d['snapshotSha256'],'sources':d['sources'],'limitations':d['limitations']}
if __name__=='__main__':
 d=overview();(BASE/'lab/network-summary.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k in ['coverage','crossCategoryOrganizations','hospitalEvents']},indent=2))
