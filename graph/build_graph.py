"""Build an inspectable Neo4j graph from derived, versioned API evidence."""
import csv,hashlib,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ai'))
from analytics import CAT,YEARS,dataset,metric,eligible
from providers import layer
OUT=Path(__file__).parent/'build';OUT.mkdir(exist_ok=True)
providers=layer();enrichment=json.loads((OUT/'provider-enrichment.json').read_text()) if (OUT/'provider-enrichment.json').exists() else {}
counts={};files={}
def write(name,rows,fields=None):
 rows=list(rows);fields=fields or list(rows[0]) if rows else fields or ['id'];p=OUT/(name+'.csv')
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else '' if v is None else v for k,v in r.items()} for r in rows)
 counts[name]=len(rows);files[name]=p
 return rows
sources=[];hospitals={};reports=[];locations={};orgs={};enrollments={};npi={};assertions=[];catalog_id=CAT['catalogSha256']
for year,s in CAT.get('workforceSources',{}).items():
 sources.append({'id':'workforce:'+year+':'+s['apiRecordsSha256'],'name':'CMS Hospital workforce API fields','datasetYear':year,'vintage':year,'url':s['source'],'queriedAt':s['queriedAt'],'sha256':s['apiRecordsSha256']})
for year in YEARS:
 s=CAT['sources'][str(year)];sid='hcris:'+str(year)+':'+s['apiRecordsSha256'];sources.append({'id':sid,'name':'CMS Hospital Provider Cost Report','datasetYear':year,'vintage':year,'url':s['source'],'queriedAt':s['queriedAt'],'sha256':s['apiRecordsSha256']})
 for r in dataset(year).values():
  hospitals[r['ccn']]={'id':r['ccn'],'name':r['name'],'state':r['state'],'city':r['city'],'county':r['county'],'latestDatasetYear':year}
  row={'id':str(year)+':'+str(r['reportId'])+':'+s['apiRecordsSha256'][:12],'ccn':r['ccn'],'datasetYear':year,'reportId':r['reportId'],'begin':r['begin'],'end':r['end'],'reportDays':r['reportDays'],'eligible':str(eligible(r)).lower(),'snapshotId':sid,'catalogId':catalog_id,**{k:r[k] for k in ['kind','providerType','control','rural','beds','days','availableDays','discharges','medicareDays','medicaidDays','netPatientRevenue','operatingExpense','patientIncome','otherIncome','netIncome','currentAssets','currentLiabilities','assets','liabilities','uncompensated']},**{'metric_'+k:metric(k,r) for k in CAT['metrics']}}
  row['stateId']='state:'+r['state'];locations[row['stateId']]={'id':row['stateId'],'kind':'state','name':r['state'],'state':r['state']}
  row.update({k:r.get(k) for k in ['payrollFte','residentFte','salaries']})
  ws=CAT.get('workforceSources',{}).get(str(year));row['workforceSnapshotId']='workforce:'+str(year)+':'+ws['apiRecordsSha256'] if ws else ''
  row['cityId']='city:'+r['state']+':'+r['city'].strip().upper() if r['city'] else '';row['countyId']='county:'+r['state']+':'+r['county'].strip().upper() if r['county'] else ''
  for key,kind,field in [('cityId','city','city'),('countyId','county','county')]:
   if row[key]:locations[row[key]]={'id':row[key],'kind':kind,'name':r[field],'state':r['state']}
  reports.append(row)
for key,s in providers['sources'].items():sources.append({'id':'cms:'+key+':'+providers['snapshotSha256'],'name':'CMS '+key,'datasetYear':'','vintage':s['vintage'],'url':s['url'],'queriedAt':providers['queriedAt'],'sha256':providers['snapshotSha256']})
for p in providers['providers']:
 hospitals.setdefault(p['ccn'],{'id':p['ccn'],'name':p['dba'] or p['legalName'],'state':p['state'],'city':p['city'],'county':'','latestDatasetYear':''})
 oid='cms:associate:'+p['associateId'];orgs[oid]={'id':oid,'associateId':p['associateId'],'name':p['legalName'],'ultimateParentResolved':'false'}
 enrollments[p['enrollmentId']]={'id':p['enrollmentId'],'ccn':p['ccn'],'associateId':p['associateId'],'organizationId':oid,'npi':p['npi'],'providerType':p['providerType'],'state':p['state'],'legalName':p['legalName'],'snapshotId':'cms:enrollments:'+providers['snapshotSha256']}
 if p['npi'].isdigit() and len(p['npi'])==10:npi[p['npi']]={'id':p['npi'],'legalName':'','enumerationType':'not_enriched','status':'not_enriched','queriedAt':'','source':''}
for r in providers['relationships']:
 oid='cms:associate:'+r['ownerAssociateId'];orgs.setdefault(oid,{'id':oid,'associateId':r['ownerAssociateId'],'name':r['ownerName'],'ultimateParentResolved':'false'})
 aid=hashlib.sha256(json.dumps([r['ccn'],r['enrollmentId'],oid,r['roleCode'],r['associationDate'],r['percentage'],providers['snapshotSha256']],sort_keys=True).encode()).hexdigest()
 assertions.append({'id':aid,'ccn':r['ccn'],'organizationId':oid,'enrollmentId':r['enrollmentId'],'relationship':r['relationship'],'role':r['role'],'roleCode':r['roleCode'],'percentage':r['percentage'],'associationDate':r['associationDate'],'evidenceStatus':r['evidenceStatus'],'observedAt':r['observedAt'],'sourceVintage':r['sourceVintage'],'snapshotId':'cms:owners:'+providers['snapshotSha256']})
for g in enrichment.get('crossCategoryEnrollments',[]):
 if g.get('status')!='source_reported':continue
 sid='cms:cross-category:'+g['associateId'];sources.append({'id':sid,'name':'CMS Medicare FFS Public Provider Enrollment','datasetYear':'','vintage':g['sourceVintage'],'url':g['source'],'queriedAt':g['queriedAt'],'sha256':hashlib.sha256(json.dumps(g,sort_keys=True).encode()).hexdigest()})
 for p in g['rows']:
  oid='cms:associate:'+p['associateId'];orgs.setdefault(oid,{'id':oid,'associateId':p['associateId'],'name':p['legalName'],'ultimateParentResolved':'false'})
  if p['enrollmentId'] not in enrollments:enrollments[p['enrollmentId']]={'id':p['enrollmentId'],'ccn':'','associateId':p['associateId'],'organizationId':oid,'npi':p['npi'],'providerType':p['providerType'],'state':p['state'],'legalName':p['legalName'],'snapshotId':sid}
  if p['npi'].isdigit() and len(p['npi'])==10:npi.setdefault(p['npi'],{'id':p['npi'],'legalName':'','enumerationType':'not_enriched','status':'not_enriched','queriedAt':'','source':''})
taxonomies={};taxonomy_edges=[]
for p in enrichment.get('nppes',[])+enrichment.get('additionalNppesSample',[]):
 if p.get('entityType')!='NPI-2':continue
 npi[p['npi']]={'id':p['npi'],'legalName':p['legalName'],'enumerationType':'NPI-2','status':p['status'],'queriedAt':p['queriedAt'],'source':p['source']}
 for t in p['taxonomies']:
  taxonomies[t['code']]={'id':t['code'],'description':t['description']};taxonomy_edges.append({'npi':p['npi'],'taxonomy':t['code'],'primary':str(t['primary']).lower(),'source':p['source'],'queriedAt':p['queriedAt']})
write('hospitals',hospitals.values());write('reports',reports);write('geographies',locations.values());write('sources',sources);write('organizations',orgs.values());write('enrollments',enrollments.values());write('npis',npi.values());write('ownership_assertions',assertions);write('taxonomies',taxonomies.values(),['id','description']);write('npi_taxonomies',taxonomy_edges,['npi','taxonomy','primary','source','queriedAt'])
write('catalogs',[{'id':catalog_id,'version':CAT['version'],'definition':CAT['policies'],'source':'semantic.json'}]);write('metrics',[{'id':catalog_id+':'+k,'key':k,'label':m['label'],'unit':m['unit'],'formula':m['expression'],'description':m['description'],'catalogId':catalog_id} for k,m in CAT['metrics'].items()])
field_meta=json.loads((Path(__file__).resolve().parents[1]/'docs/hospitals/lab/metadata.json').read_text())
fields={f['name']:{'id':f['name'],'physicalName':f['sourceField']} for f in field_meta['fields']};dependencies=[]
for k,m in CAT['metrics'].items():
 for name,physical in zip(m['inputs'],m['sourceFields']):fields[name]={'id':name,'physicalName':physical};dependencies.append({'metricId':catalog_id+':'+k,'fieldId':name})
write('fields',fields.values());write('metric_fields',dependencies)
statements=[]
for label in ['Hospital','CostReport','Geography','SourceSnapshot','Organization','ProviderEnrollment','NPI','Taxonomy','OwnershipAssertion','SemanticCatalog','MetricDefinition','DataField']:statements.append(f'CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE;')
def load(file,body):statements.append("LOAD CSV WITH HEADERS FROM 'file:///"+file+".csv' AS row CALL { WITH row "+body+" } IN TRANSACTIONS OF 1000 ROWS;")
load('hospitals',"MERGE (n:Hospital {id:row.id}) SET n.name=row.name,n.state=row.state,n.city=row.city,n.county=row.county,n.latestDatasetYear=toInteger(row.latestDatasetYear)")
load('geographies',"MERGE (n:Geography {id:row.id}) SET n.kind=row.kind,n.name=row.name,n.state=row.state")
load('sources',"MERGE (n:SourceSnapshot {id:row.id}) SET n.name=row.name,n.datasetYear=toInteger(row.datasetYear),n.vintage=row.vintage,n.url=row.url,n.queriedAt=row.queriedAt,n.sha256=row.sha256")
load('catalogs',"MERGE (n:SemanticCatalog {id:row.id}) SET n.version=row.version,n.definition=row.definition,n.source=row.source")
load('metrics',"MATCH (c:SemanticCatalog {id:row.catalogId}) MERGE (n:MetricDefinition {id:row.id}) SET n.key=row.key,n.label=row.label,n.unit=row.unit,n.formula=row.formula,n.description=row.description MERGE (c)-[:DEFINES]->(n)")
load('fields',"MERGE (n:DataField {id:row.id}) SET n.physicalName=row.physicalName")
load('metric_fields',"MATCH (m:MetricDefinition {id:row.metricId}),(f:DataField {id:row.fieldId}) MERGE (m)-[:USES_FIELD]->(f)")
load('organizations',"MERGE (n:Organization {id:row.id}) SET n.associateId=row.associateId,n.name=row.name,n.ultimateParentResolved=false")
load('npis',"MERGE (n:NPI {id:row.id}) SET n.legalName=row.legalName,n.enumerationType=row.enumerationType,n.status=row.status,n.queriedAt=row.queriedAt,n.source=row.source")
load('taxonomies',"MERGE (n:Taxonomy {id:row.id}) SET n.description=row.description")
load('npi_taxonomies',"MATCH (n:NPI {id:row.npi}),(t:Taxonomy {id:row.taxonomy}) MERGE (n)-[r:HAS_TAXONOMY]->(t) SET r.primary=toBoolean(row.primary),r.source=row.source,r.queriedAt=row.queriedAt")
load('enrollments',"MATCH (o:Organization {id:row.organizationId}),(s:SourceSnapshot {id:row.snapshotId}) MERGE (n:ProviderEnrollment {id:row.id}) SET n.providerType=row.providerType,n.legalName=row.legalName,n.state=row.state,n.ccn=row.ccn,n.npi=row.npi MERGE (o)-[:HAS_REPORTED_ENROLLMENT]->(n) MERGE (n)-[:FROM_SOURCE]->(s) WITH n,row OPTIONAL MATCH (h:Hospital {id:row.ccn}) FOREACH (_ IN CASE WHEN h IS NULL THEN [] ELSE [1] END | MERGE (h)-[:ENROLLED_AS]->(n)) WITH n,row OPTIONAL MATCH (i:NPI {id:row.npi}) FOREACH (_ IN CASE WHEN i IS NULL THEN [] ELSE [1] END | MERGE (n)-[:HAS_REPORTED_NPI]->(i))")
numeric=['beds','days','availableDays','discharges','medicareDays','medicaidDays','netPatientRevenue','operatingExpense','patientIncome','otherIncome','netIncome','currentAssets','currentLiabilities','assets','liabilities','uncompensated']+['metric_'+k for k in CAT['metrics']]
numeric+=['payrollFte','residentFte','salaries']
sets=','.join('n.'+k+'=toFloat(row.'+k+')' for k in numeric)
load('reports',"MATCH (h:Hospital {id:row.ccn}),(s:SourceSnapshot {id:row.snapshotId}),(c:SemanticCatalog {id:row.catalogId}),(g:Geography {id:row.stateId}) MERGE (n:CostReport {id:row.id}) SET n.datasetYear=toInteger(row.datasetYear),n.reportId=row.reportId,n.ccn=row.ccn,n.fiscalBegin=date(row.begin),n.fiscalEnd=date(row.end),n.reportDays=toInteger(row.reportDays),n.eligible=toBoolean(row.eligible),n.kind=row.kind,n.providerType=row.providerType,n.control=row.control,n.rural=row.rural,"+sets+" MERGE (h)-[:HAS_COST_REPORT]->(n) MERGE (n)-[:FROM_SOURCE]->(s) MERGE (n)-[:INTERPRETED_WITH]->(c) MERGE (n)-[:REPORTED_IN]->(g) WITH n,row OPTIONAL MATCH (city:Geography {id:row.cityId}) FOREACH (_ IN CASE WHEN city IS NULL THEN [] ELSE [1] END | MERGE (n)-[:REPORTED_IN]->(city)) WITH n,row OPTIONAL MATCH (county:Geography {id:row.countyId}) FOREACH (_ IN CASE WHEN county IS NULL THEN [] ELSE [1] END | MERGE (n)-[:REPORTED_IN]->(county))")
load('ownership_assertions',"MATCH (h:Hospital {id:row.ccn}),(o:Organization {id:row.organizationId}),(s:SourceSnapshot {id:row.snapshotId}) MERGE (a:OwnershipAssertion {id:row.id}) SET a.role=row.role,a.roleCode=row.roleCode,a.percentage=toFloat(row.percentage),a.associationDate=row.associationDate,a.evidenceStatus=row.evidenceStatus,a.sourceVintage=row.sourceVintage,a.observedAt=row.observedAt,a.enrollmentId=row.enrollmentId MERGE (h)-[:HAS_OWNERSHIP_ASSERTION]->(a) MERGE (a)-[:ASSOCIATE]->(o) MERGE (a)-[:FROM_SOURCE]->(s) FOREACH (_ IN CASE WHEN row.relationship='REPORTED_OWNERSHIP_INTEREST' THEN [1] ELSE [] END | MERGE (h)-[r:REPORTED_OWNERSHIP_INTEREST {assertionId:row.id}]->(o) SET r.role=row.role,r.percentage=toFloat(row.percentage),r.evidenceStatus=row.evidenceStatus,r.sourceVintage=row.sourceVintage) FOREACH (_ IN CASE WHEN row.relationship='REPORTED_CONTROL_ROLE' THEN [1] ELSE [] END | MERGE (h)-[r:REPORTED_CONTROL_ROLE {assertionId:row.id}]->(o) SET r.role=row.role,r.evidenceStatus=row.evidenceStatus,r.sourceVintage=row.sourceVintage)")
(OUT/'load.cypher').write_text('\n\n'.join(statements)+'\n')
load('reports',"MATCH (r:CostReport {id:row.id}),(s:SourceSnapshot {id:row.workforceSnapshotId}) MERGE (r)-[:WORKFORCE_FROM_SOURCE]->(s)")
(OUT/'load.cypher').write_text('\n\n'.join(statements)+'\n')
summary={'counts':counts,'catalogSha256':catalog_id,'financialFacilityYears':len(reports),'nppesEnrichedOrganizations':sum(x['enumerationType']=='NPI-2' for x in npi.values()),'nppesCoverage':'Identifiers are national hospital enrollment references; NPPES attributes are a bounded exact-NPI sample, not the full national NPPES database.','ownershipPolicy':'Only source-reported organizational interests/control roles. No inferred ultimate-parent edges. Current disclosures are not financial-year ownership histories.'}
(OUT/'graph-manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
with zipfile.ZipFile(OUT/'neo4j-import.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in list(files.values())+[OUT/'load.cypher',OUT/'graph-manifest.json']:z.write(p,p.name)
print(json.dumps(summary,indent=2))
