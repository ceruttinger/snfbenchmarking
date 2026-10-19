"""Append exact-ID facility, ownership assertion and dated event imports."""
import hashlib,json
def extend(root,write,load,statements):
 d=json.loads((root/'docs/hospitals/lab/network.json').read_text());sources=[];sourceids={}
 for key,s in d['sources'].items():
  sid='network:'+key+':'+s['sha256'];sourceids[key]=sid
  sources.append({'id':sid,'name':s['title'],'url':s['url'],'vintage':s['vintage'],'queriedAt':s['queriedAt'],'sha256':s['sha256']})
 orgs={};facilities={};enroll=[];assertions=[];events=[]
 for p in d['facilities']:
  facilities[p['id']]={**p,'sourceSnapshotId':sourceids[p['sourceId']]}
  oid='cms:associate:'+p['associateId']
  if p['associateId']:orgs[oid]={'id':oid,'associateId':p['associateId'],'name':p['legalName']}
  enroll.append({**p,'id':hashlib.sha256(json.dumps([p['id'],p['enrollmentId'],p['npi']]).encode()).hexdigest(),'facilityId':p['id'],'organizationId':oid,'sourceSnapshotId':sourceids[p['sourceId']]})
 for a in d['assertions']:
  oid='cms:associate:'+a['ownerAssociateId'];orgs.setdefault(oid,{'id':oid,'associateId':a['ownerAssociateId'],'name':a['ownerName']})
  if a['category']=='Hospital':continue # baseline hospital assertions already retain original identities.
  row={**a,'organizationId':oid,'sourceSnapshotId':sourceids[a['sourceId']]}
  row['id']=hashlib.sha256(json.dumps([a,sourceids[a['sourceId']]],sort_keys=True).encode()).hexdigest();assertions.append(row)
 for e in d['events']:
  row={**e,'sourceSnapshotId':sourceids[e['sourceId']]}
  for side in ['buyer','seller']:
   aid=e[side+'AssociateId'];oid='cms:associate:'+aid;row[side+'OrganizationId']=oid if aid else ''
   if aid:orgs.setdefault(oid,{'id':oid,'associateId':aid,'name':e[side+'Name']})
  events.append(row)
 write('network_sources',sources);write('network_organizations',orgs.values());write('network_facilities',facilities.values());write('network_enrollments',{r['id']:r for r in enroll}.values());write('network_assertions',assertions);write('ownership_events',events)
 statements += ['CREATE CONSTRAINT facility_id IF NOT EXISTS FOR (n:Facility) REQUIRE n.id IS UNIQUE;','CREATE CONSTRAINT ownershipevent_id IF NOT EXISTS FOR (n:OwnershipEvent) REQUIRE n.id IS UNIQUE;','MATCH (h:Hospital) SET h:Facility,h.category="Hospital",h.ccn=h.id;']
 load('network_sources',"MERGE (s:SourceSnapshot {id:row.id}) SET s.name=row.name,s.url=row.url,s.vintage=row.vintage,s.queriedAt=row.queriedAt,s.sha256=row.sha256")
 load('network_organizations',"MERGE (o:Organization {id:row.id}) ON CREATE SET o.name=row.name,o.associateId=row.associateId,o.ultimateParentResolved=false")
 load('network_facilities',"MATCH (s:SourceSnapshot {id:row.sourceSnapshotId}) MERGE (f:Facility {id:row.id}) ON CREATE SET f.name=row.name,f.state=row.state,f.city=row.city SET f.category=row.category,f.ccn=row.ccn MERGE (f)-[:FROM_SOURCE]->(s)")
 load('network_enrollments',"MATCH (f:Facility {id:row.facilityId}),(s:SourceSnapshot {id:row.sourceSnapshotId}) MERGE (e:ProviderEnrollment {id:row.enrollmentId}) ON CREATE SET e.legalName=row.legalName,e.providerType=row.category,e.state=row.state,e.ccn=row.ccn,e.npi=row.npi MERGE (f)-[:ENROLLED_AS]->(e) MERGE (e)-[:FROM_SOURCE]->(s) WITH e,row OPTIONAL MATCH (o:Organization {id:row.organizationId}) FOREACH (_ IN CASE WHEN o IS NULL THEN [] ELSE [1] END | MERGE (o)-[:HAS_REPORTED_ENROLLMENT]->(e)) FOREACH (_ IN CASE WHEN size(row.npi)=10 THEN [1] ELSE [] END | MERGE (n:NPI {id:row.npi}) ON CREATE SET n.enumerationType='not_enriched',n.status='not_enriched' MERGE (e)-[:HAS_REPORTED_NPI]->(n))")
 load('network_assertions',"MATCH (f:Facility {id:row.facilityId}),(o:Organization {id:row.organizationId}),(s:SourceSnapshot {id:row.sourceSnapshotId}) MERGE (a:OwnershipAssertion {id:row.id}) SET a.role=row.role,a.roleCode=row.roleCode,a.percentage=toFloat(row.percentage),a.associationDate=row.associationDate,a.sourceVintage=row.sourceVintage,a.evidenceStatus='source_reported',a.category=row.category,a.enrollmentId=row.enrollmentId,a.relationshipKind=row.relationship MERGE (f)-[:HAS_OWNERSHIP_ASSERTION]->(a) MERGE (a)-[:ASSOCIATE]->(o) MERGE (a)-[:FROM_SOURCE]->(s) FOREACH (_ IN CASE WHEN row.relationship='REPORTED_OWNERSHIP_INTEREST' THEN [1] ELSE [] END | MERGE (f)-[r:REPORTED_OWNERSHIP_INTEREST {assertionId:row.id}]->(o) SET r.role=row.role,r.percentage=toFloat(row.percentage),r.evidenceStatus='source_reported',r.sourceVintage=row.sourceVintage) FOREACH (_ IN CASE WHEN row.relationship='REPORTED_CONTROL_ROLE' THEN [1] ELSE [] END | MERGE (f)-[r:REPORTED_CONTROL_ROLE {assertionId:row.id}]->(o) SET r.role=row.role,r.evidenceStatus='source_reported',r.sourceVintage=row.sourceVintage)")
 load('network_assertions',"MATCH (f:Facility {id:row.facilityId}),(o:Organization {id:row.organizationId}) FOREACH (_ IN CASE WHEN row.relationship='REPORTED_ASSOCIATION_ROLE' THEN [1] ELSE [] END | MERGE (f)-[r:REPORTED_ASSOCIATION_ROLE {assertionId:row.id}]->(o) SET r.role=row.role,r.evidenceStatus='source_reported',r.sourceVintage=row.sourceVintage)")
 load('ownership_events',"MATCH (s:SourceSnapshot {id:row.sourceSnapshotId}) MERGE (e:OwnershipEvent {id:row.id}) SET e.effectiveDate=date(row.effectiveDate),e.eventType=row.eventType,e.buyerCcn=row.buyerCcn,e.sellerCcn=row.sellerCcn,e.buyerName=row.buyerName,e.sellerName=row.sellerName,e.evidenceStatus='source_reported' MERGE (e)-[:FROM_SOURCE]->(s) WITH e,row OPTIONAL MATCH (b:Organization {id:row.buyerOrganizationId}) OPTIONAL MATCH (v:Organization {id:row.sellerOrganizationId}) OPTIONAL MATCH (h:Hospital {id:row.buyerCcn}) OPTIONAL MATCH (j:Hospital {id:row.sellerCcn}) FOREACH (_ IN CASE WHEN b IS NULL THEN [] ELSE [1] END | MERGE (e)-[:REPORTED_BUYER]->(b)) FOREACH (_ IN CASE WHEN v IS NULL THEN [] ELSE [1] END | MERGE (e)-[:REPORTED_SELLER]->(v)) FOREACH (_ IN CASE WHEN h IS NULL THEN [] ELSE [1] END | MERGE (h)-[:HAS_OWNERSHIP_EVENT {role:'buyer_ccn'}]->(e)) FOREACH (_ IN CASE WHEN j IS NULL THEN [] ELSE [1] END | MERGE (j)-[:HAS_OWNERSHIP_EVENT {role:'seller_ccn'}]->(e))")
 return {'snapshotSha256':d['snapshotSha256'],'coverage':d['coverage'],'hospitalEvents':len(events),'limitations':d['limitations']}
