"""Live semantic-interpretation gate. Does not judge prose fluency."""
import json,sys,time
from pathlib import Path
from planner import plan,MODEL
context={'targetCcn':'460010','anchorYear':2024,'startYear':2017,'endYear':2024,'mode':'fixed','filters':{'scope':'national','category':'same','providerType':'same','bedBand':'same'}}
cases=json.loads((Path(__file__).resolve().parents[1]/'docs/hospitals/lab/use-cases.json').read_text())
checks={'trend':{'analysis':'trend','startYear':2019,'mode':'fixed','metrics':['occupancy']},'financial':{'analysis':'compare','metrics':['totalMargin','currentRatio','leverage']},'rank':{'analysis':'rank','sortBy':'value','direction':'asc','endYear':2024,'filters':{'scope':'state','geoState':'UT','ownership':'nonprofit','minBeds':100,'category':'any','providerType':'any','bedBand':'any'}},'compound':{'analysis':'rank','startYear':2019,'endYear':2024,'sortBy':'change','direction':'desc','filters':{'scope':'state','geoState':'UT','ownership':'nonprofit','minBeds':100},'conditions':[{'metric':'totalMargin','basis':'value','op':'gt','value':0.05},{'metric':'totalMargin','basis':'change','op':'gt','value':0}]},'balanced':{'analysis':'trend','mode':'balanced','metrics':['revenue','expense']},'dynamic':{'analysis':'trend','mode':'dynamic'},'definition':{'analysis':'definition','metrics':['totalMargin']},'coverage':{'analysis':'coverage','metrics':['uncompShare']},'ownership':{'analysis':'ownership'},'ambiguous':None,'quality':None}
def matches(actual,expected):
 if isinstance(expected,dict):return isinstance(actual,dict) and all(k in actual and matches(actual[k],v) for k,v in expected.items())
 if isinstance(expected,list):return sorted(json.dumps(x,sort_keys=True) for x in actual)==sorted(json.dumps(x,sort_keys=True) for x in expected)
 return actual==expected
out=[]
for c in cases:
 start=time.monotonic()
 try:
  r=plan(c['question'],context);expected=checks[c['id']];passed=bool(r.get('clarification')) if expected is None else matches(r.get('query'),expected)
  out.append({'id':c['id'],'passed':passed,'seconds':round(time.monotonic()-start,2),'response':r})
 except Exception as e:out.append({'id':c['id'],'passed':False,'error':type(e).__name__+': '+str(e)})
 print(c['id'],out[-1]['passed'],flush=True)
path=Path(__file__).resolve().parents[1]/'infra/build/planner-evaluation.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps({'model':MODEL,'passed':sum(x['passed'] for x in out),'total':len(out),'cases':out},indent=2)+'\n')
if not all(x['passed'] for x in out):sys.exit(1)
