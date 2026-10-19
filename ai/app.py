"""Lambda + local HTTP adapter for validated, read-only hospital questions."""
import base64,json,os,time
from datetime import datetime,timezone
from analytics import CAT,QueryError,execute,validate
from planner import plan

def reserve_call(kind,limit):
 table=os.environ.get('QUOTA_TABLE')
 if not table:return
 import boto3
 from botocore.exceptions import ClientError
 today=datetime.now(timezone.utc).date().isoformat();client=boto3.client('dynamodb')
 try:client.update_item(TableName=table,Key={'id':{'S':kind+':'+today}},UpdateExpression='SET expiresAt = :ttl ADD calls :one',ConditionExpression='attribute_not_exists(calls) OR calls < :limit',ExpressionAttributeValues={':one':{'N':'1'},':limit':{'N':str(limit)},':ttl':{'N':str(int(time.time())+172800)}})
 except ClientError as e:
  if e.response['Error']['Code']=='ConditionalCheckFailedException':raise QueryError('The draft’s daily '+kind+' allowance is used. Please try again tomorrow.')
  raise

def route(path,body):
 if path=='/api/health':return {'status':'ok','catalogVersion':CAT['version'],'catalogSha256':CAT['catalogSha256'],'modelConfigured':bool(os.environ.get('BEDROCK_MODEL_ID')),'years':CAT['years']}
 if not isinstance(body,dict):raise QueryError('Send a JSON object.')
 reserve_call('request',2000)
 if path=='/api/network':
  from network import inspect
  return {'execution':'Exact CMS organizational IDs and dated event evidence','network':inspect(body.get('ccn'))}
 if path=='/api/provider':
  from providers import inspect
  return {'execution':'CMS enrollment evidence + exact-NPI NPPES lookup','provider':inspect(body.get('ccn'))}
 if path=='/api/query':return {'execution':'semantic_engine','result':execute(body.get('query'))}
 if path=='/api/chat':
  context=body.get('context',{})
  if not isinstance(context,dict) or set(context)-{'targetCcn','anchorYear','startYear','endYear','mode','filters'}:raise QueryError('Invalid context.')
  validate({'analysis':'compare','metrics':['occupancy'],**context})
  question=body.get('question')
  if not isinstance(question,str) or not 1<=len(question.strip())<=2000:raise QueryError('Please ask a question of 1–2,000 characters.')
  reserve_call('AI',int(os.environ.get('DAILY_AI_LIMIT','50')));p=plan(question,context)
  if 'clarification' in p:return {'execution':'clarification',**p}
  result=execute(p['query']);result['interpretationNotes']=p.get('interpretationNotes',[])
  return {'execution':p['model']+' → validated semantic engine','model':p['model'],'result':result}
 raise QueryError('Unknown endpoint.')

def handler(event,context):
 path=event.get('rawPath',event.get('path',''));method=event.get('requestContext',{}).get('http',{}).get('method','GET');headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
 if method=='OPTIONS':return {'statusCode':204,'headers':headers,'body':''}
 if method not in (['GET'] if path=='/api/health' else ['POST']):return {'statusCode':405,'headers':headers,'body':json.dumps({'error':'Method not allowed'})}
 try:
  raw=event.get('body') or '{}'
  if event.get('isBase64Encoded'):raw=base64.b64decode(raw).decode()
  if len(raw)>12000:raise QueryError('Request is too large.')
  response=route(path,json.loads(raw));code=200
 except (QueryError,json.JSONDecodeError) as e:response={'error':str(e)};code=400
 except Exception as e:
  print(json.dumps({'event':'request_failed','type':type(e).__name__}))
  response={'error':'The query service could not complete this request. No answer was generated.'};code=503
 return {'statusCode':code,'headers':headers,'body':json.dumps(response,allow_nan=False,separators=(',',':'))}

if __name__=='__main__':
 from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
 from pathlib import Path
 root=Path(__file__).resolve().parents[1]/'docs'
 class Local(SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw):super().__init__(*a,directory=str(root),**kw)
  def do_GET(self):
   if self.path.startswith('/api/'):self.answer('GET')
   else:super().do_GET()
  def do_POST(self):self.answer('POST')
  def answer(self,method):
   length=int(self.headers.get('Content-Length','0'))
   if length>12000:self.send_error(413);return
   r=handler({'rawPath':self.path.split('?')[0],'requestContext':{'http':{'method':method}},'body':self.rfile.read(length).decode() if length else '{}'},None)
   self.send_response(r['statusCode'])
   for k,v in r['headers'].items():self.send_header(k,v)
   self.end_headers();self.wfile.write(r['body'].encode())
 ThreadingHTTPServer(('127.0.0.1',8765),Local).serve_forever()
