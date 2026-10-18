"""Build a versioned semantic catalog from published API snapshots and CMS metadata."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'hospitals'))
from build_data import COLUMNS,FIELDS,IDENTITY_FIELDS
out=ROOT/'docs/hospitals/lab'
f=lambda k:{'field':k}
ratio=lambda a,b:{'op':'ratio','args':[f(a),f(b)]}
items=[
 ('occupancy','Occupancy',['occupancy','bed utilization'],'percent',ratio('days','availableDays'),'Patient days / available bed-days. Values outside 0–100% are unavailable.',['days','availableDays']),
 ('lengthOfStay','Average length of stay',['length of stay','ALOS'],'days',ratio('days','discharges'),'Aggregate reported days / discharges; not adjusted for case mix.',['days','discharges']),
 ('patientMargin','Patient-service margin',['patient service margin'],'percent',ratio('patientIncome','netPatientRevenue'),'Not RAND operating margin.',['patientIncome','netPatientRevenue']),
 ('totalMargin','Total margin',['total margin','net margin'],'percent',{'op':'ratio','args':[f('netIncome'),{'op':'add','args':[f('netPatientRevenue'),f('otherIncome')]}]},'RAND total-margin formula using CMS inputs; not operating margin.',['netIncome','netPatientRevenue','otherIncome']),
 ('currentRatio','Current ratio',['liquidity','current ratio'],'ratio',ratio('currentAssets','currentLiabilities'),'Current assets / current liabilities. Not days cash on hand.',['currentAssets','currentLiabilities']),
 ('leverage','Liabilities / assets',['liabilities to assets'],'percent',ratio('liabilities','assets'),'All liabilities, not debt-only leverage.',['liabilities','assets']),
 ('medicareShare','Medicare day share',['Medicare share'],'percent',ratio('medicareDays','days'),'Title XVIII days / total days. Not a validated Medicare Advantage-inclusive share.',['medicareDays','days']),
 ('medicaidShare','Medicaid day share',['Medicaid share'],'percent',ratio('medicaidDays','days'),'Title XIX days / total days. Managed-care scope is not separately validated.',['medicaidDays','days']),
 ('uncompShare','Uncompensated care / expense',['uncompensated care share'],'percent',ratio('uncompensated','operatingExpense'),'Not all unreimbursed Medicaid/CHIP costs.',['uncompensated','operatingExpense']),
 ('beds','Reported beds',['beds','size'],'number',f('beds'),'Reported balance; not annualized.',['beds']),
 ('discharges','Discharges · annualized',['discharges','admissions'],'number',{'op':'annualize','field':'discharges'},'Reported discharges normalized to 365.25 days; admissions are not a separately measured field.',['discharges','reportDays']),
 ('patientDays','Patient days · annualized',['patient days'],'number',{'op':'annualize','field':'days'},'Reported patient days normalized to 365.25 days.',['days','reportDays']),
 ('revenue','Net patient revenue · annualized',['net patient revenue','revenue'],'money',{'op':'annualize','field':'netPatientRevenue'},'Nominal dollars normalized to 365.25 days; not inflation adjusted.',['netPatientRevenue','reportDays']),
 ('expense','Operating expense · annualized',['operating expense','expense'],'money',{'op':'annualize','field':'operatingExpense'},'Nominal dollars normalized to 365.25 days; not inflation adjusted.',['operatingExpense','reportDays'])]
source_fields=dict(zip(COLUMNS[:12],IDENTITY_FIELDS[:11]))
# Explicit mapping preserves field order from the API ingestion contract.
source_fields=dict(zip(COLUMNS[:8],IDENTITY_FIELDS[:8]))
source_fields.update(dict(zip(['begin','end','reportId'],IDENTITY_FIELDS[8:11])))
source_fields.update(dict(zip(COLUMNS[12:28],FIELDS)))
source_fields.update(county='County',reportDays='Derived: inclusive fiscal-end minus fiscal-begin dates')
manifest=json.loads((ROOT/'docs/hospitals/manifest.json').read_text())
metrics={k:{'id':k,'label':label,'synonyms':syn,'unit':unit,'expression':expr,'description':description,'inputs':inputs,'sourceFields':[source_fields[x] for x in inputs],'aggregation':'Unweighted median of valid facility ratios; never ratio of cohort totals.','missingPolicy':'Null on missing/nonfinite inputs or nonpositive denominator; zero is retained.','eligibility':'300–430 inclusive report days for benchmarking and history.','minimumValidPeers':5,'scope':'CMS hospital cost-report complex; not necessarily a single physical campus.'} for k,label,syn,unit,expr,description,inputs in items}
metrics['occupancy']['validRange']=[0,1]
catalog={'version':'1.0.0','entity':'hospital_cost_report','grain':['CCN','CMS source dataset year'],'identity':{'key':'CCN','reportKey':'reportId','physicalCampusEquivalent':False,'ownershipHistoryLoaded':False},'years':sorted(map(int,manifest)), 'metrics':metrics,'dimensions':{k:{'sourceField':source_fields[k]} for k in ['ccn','name','state','city','county','kind','providerType','control','rural','beds','begin','end']},'policies':{'peerMinimum':5,'periodDays':[300,430],'reportSelection':manifest['2024']['selection'],'time':'Dataset year is a grouping, not a calendar-year standardization. Many reports end the following year.','changes':'Adjacent datasets; eligible, nonoverlapping target periods with gap <=60 days. Percent differences are percentage points.','money':'Nominal USD. Flow annualization uses 365.25 / report days.','ranking':'Eligible matching hospitals; target is included in a market ranking but excluded from its own peer benchmark.','cohortModes':['fixed','dynamic','balanced'],'balanced':'Metric-specific fixed CCNs with valid values in every selected dataset.','scope':'Descriptive; no case-mix, wage, teaching or clinical-quality adjustment.'},'relationships':[{'from':'hospital','predicate':'HAS_COST_REPORT','to':'cost_report','status':'loaded','join':'CCN'},{'from':'hospital','predicate':'LOCATED_IN','to':'geography','status':'loaded','join':'state + county/city, as reported'},{'from':'hospital','predicate':'OPERATED_BY','to':'health_system','status':'not_loaded','reason':'Requires dated and verified system/operator observations; name similarity is not ownership evidence.'}], 'unavailable':['RAND observation files and commercial prices','RAND operating margin','Dated system ownership and acquisitions','Other HCRIS provider financial families','Clinical quality and causality','Inflation-adjusted dollars','Days cash on hand'],'sources':manifest}
provider_path=out/'providers.json'
if provider_path.exists():
 providers=json.loads(provider_path.read_text())
 catalog['providerLayer']={'coverage':providers['coverage'],'sources':providers['sources'],'observedAt':providers['queriedAt'],'nppesApi':'https://npiregistry.cms.hhs.gov/api/?version=2.1','nppesMode':'Exact CMS-reported NPI, organization-only lookup on demand; national NPPES is not bulk ingested.','ownershipRule':'Source-reported enrollment disclosures, not an audited ultimate-parent registry. Association dates have no inferred termination dates.'}
 catalog['relationships'] += [{'from':'hospital','predicate':'ENROLLED_AS','to':'cms_enrollment','status':'loaded','join':'Exact CCN'},{'from':'cms_enrollment','predicate':'HAS_NPI','to':'organization_npi','status':'loaded','join':'Exact CMS-reported NPI; NPPES organization enrichment on demand'},{'from':'hospital','predicate':'REPORTED_OWNERSHIP_INTEREST_OR_CONTROL','to':'cms_organizational_associate','status':'loaded','join':'Exact CMS enrollment ID; role and association date preserved'}]
serialized=json.dumps(catalog,sort_keys=True,separators=(',',':')).encode();catalog['catalogSha256']=hashlib.sha256(serialized).hexdigest()
out.mkdir(parents=True,exist_ok=True);(out/'semantic.json').write_text(json.dumps(catalog,indent=2)+'\n')
metadata={'title':'CMS Hospital Provider Cost Report','description':'Selected measures from hospital annual cost reports, organized by CMS Certification Number.','publisher':'Centers for Medicare & Medicaid Services / OEDA','landingPage':'https://data.cms.gov/provider-compliance/cost-reports/hospital-provider-cost-report','dictionary':'https://data.cms.gov/sites/default/files/2024-03/9756088d-5280-4090-80b9-449d31ef25a3/Cost%20Report%20Data%20Dictionary%20Update.pdf','accessMethod':'Paginated official CMS JSON APIs; no raw CSV/ZIP downloads.','sourceSnapshotNotice':'Historical API refresh timestamps are preserved; this is not live CMS data.','fields':[{'name':k,'sourceField':v,'role':'measure' if k in COLUMNS[12:28] else 'identity_or_dimension'} for k,v in source_fields.items()],'years':manifest,'selectedFacilityYears':sum(x['selectedReports'] for x in manifest.values()),'catalogSha256':catalog['catalogSha256']}
if 'providerLayer' in catalog:metadata['providerLayer']=catalog['providerLayer']
(out/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n');print('Built',len(metrics),'semantic metrics and',len(source_fields),'source-field mappings.')
