import json
from pathlib import Path
base={'targetCcn':'460010','anchorYear':2024,'startYear':2017,'endYear':2024,'mode':'fixed','filters':{'category':'same','providerType':'same','bedBand':'same','scope':'national'}}
cases=[]
def add(id,question,analysis,metrics,**kw):cases.append({'id':id,'question':question,'query':{**base,'analysis':analysis,'metrics':metrics,**kw}})
add('trend','How has Intermountain Medical Center’s occupancy changed since 2019 versus the same peers?','trend',['occupancy'],startYear=2019)
add('financial','Compare this hospital’s total margin, liquidity and liabilities/assets with its defined peers.','compare',['totalMargin','currentRatio','leverage'])
add('rank','Which 10 nonprofit Utah hospitals had the lowest total margin in 2024, with at least 100 beds?','rank',['totalMargin'],direction='asc',filters={'scope':'state','geoState':'UT','ownership':'nonprofit','minBeds':100,'category':'any','providerType':'any','bedBand':'any'})
add('compound','Among nonprofit Utah hospitals with at least 100 beds, which improved total margin most from 2019 to 2024 and ended above 5%?','rank',['totalMargin'],startYear=2019,sortBy='change',direction='desc',filters={'scope':'state','geoState':'UT','ownership':'nonprofit','minBeds':100,'category':'any','providerType':'any','bedBand':'any'},conditions=[{'metric':'totalMargin','basis':'value','op':'gt','value':0.05},{'metric':'totalMargin','basis':'change','op':'gt','value':0}])
add('balanced','Show revenue and expense trends using peers with valid observations throughout 2017–2024.','trend',['revenue','expense'],mode='balanced')
add('dynamic','Compare occupancy trends when similar-size peers are reselected every year.','trend',['occupancy'],mode='dynamic')
add('definition','How is total margin calculated, which CMS fields are used, and is it RAND operating margin?','definition',['totalMargin','patientMargin'])
add('coverage','How many hospital reports have valid uncompensated-care measures in each year?','coverage',['uncompShare'])
cases.extend([{'id':'ambiguous','question':'Which hospitals have the best operating margin?','expected':'clarification','reason':'Operating margin is not patient-service or total margin.'},{'id':'ownership','question':'Which system owns this hospital, and what other provider types does it operate?','expected':'ownership_evidence','reason':'Requires CMS ownership/enrollment and verified affiliation evidence; HCRIS control type alone is not a parent organization.'},{'id':'quality','question':'Did this acquisition improve clinical quality?','expected':'unsupported','reason':'Clinical outcomes and causal acquisition evidence are not in the loaded financial subset.'}])
ownership=next(c for c in cases if c['id']=='ownership');ownership.pop('expected',None);ownership['question']='Who owns Intermountain Medical Center, according to CMS enrollment disclosures?';ownership['query']={'analysis':'ownership','metrics':['totalMargin'],'targetCcn':'460010','anchorYear':2024,'startYear':2024,'endYear':2024}
(Path(__file__).resolve().parents[1]/'docs/hospitals/lab/use-cases.json').write_text(json.dumps(cases,indent=2)+'\n')
