"""Deploy an isolated AWS draft. Does not change production DNS or GitHub Pages."""
import hashlib,json,mimetypes,time,sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
ROOT=Path(__file__).resolve().parents[1];REGION='us-east-2';STACK='hcris-evidence-draft'
session=boto3.Session(region_name=REGION);account=session.client('sts').get_caller_identity()['Account'];s3=session.client('s3');cf=session.client('cloudformation')
bucket=f'hcris-ai-artifacts-{account}-{REGION}';archive=ROOT/'infra/build/hcris-query.zip';digest=hashlib.sha256(archive.read_bytes()).hexdigest();key='query/'+digest+'.zip'
try:s3.head_bucket(Bucket=bucket)
except ClientError as e:
 if e.response['Error']['Code'] not in ['404','NoSuchBucket','NotFound']:raise
 s3.create_bucket(Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':REGION})
 s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={k:True for k in ['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets']})
s3.upload_file(str(archive),bucket,key);print('Uploaded tested query package.',flush=True)
params=[{'ParameterKey':'ArtifactBucket','ParameterValue':bucket},{'ParameterKey':'ArtifactKey','ParameterValue':key},{'ParameterKey':'ModelId','ParameterValue':'mistral.mistral-large-3-675b-instruct'},{'ParameterKey':'DailyAiLimit','ParameterValue':'50'}]
kwargs={'StackName':STACK,'TemplateBody':(ROOT/'infra/hcris-draft.json').read_text(),'Parameters':params,'Capabilities':['CAPABILITY_IAM'],'Tags':[{'Key':'Project','Value':'HCRIS Dashboard'},{'Key':'Environment','Value':'draft'}]}
try:existing=cf.describe_stacks(StackName=STACK)['Stacks'][0]
except ClientError as e:
 if 'does not exist' not in str(e):raise
 existing=None
if existing:
 try:cf.update_stack(**kwargs)
 except ClientError as e:
  if 'No updates are to be performed' not in str(e):raise
else:cf.create_stack(**kwargs)
previous=''
for _ in range(120):
 stack=cf.describe_stacks(StackName=STACK)['Stacks'][0];status=stack['StackStatus']
 if status!=previous:print('Draft infrastructure:',status,flush=True);previous=status
 if status in ['CREATE_COMPLETE','UPDATE_COMPLETE']:break
 if any(x in status for x in ['FAILED','ROLLBACK']):
  events=cf.describe_stack_events(StackName=STACK)['StackEvents'];print(json.dumps([{'resource':e['LogicalResourceId'],'status':e['ResourceStatus'],'reason':e.get('ResourceStatusReason')} for e in events[:12]],indent=2));raise RuntimeError('Draft infrastructure did not complete')
 time.sleep(5)
else:raise RuntimeError('Draft deployment is still running; inspect the existing stack before retrying.')
outputs={o['OutputKey']:o['OutputValue'] for o in stack['Outputs']}
# All uploaded files come from the existing public docs tree. Ownership snapshots stay server-side.
count=0
for p in ([] if '--runtime-only' in sys.argv else (ROOT/'docs').rglob('*')):
 if not p.is_file() or p.name in ['CNAME','.DS_Store','providers.json']:continue
 rel=p.relative_to(ROOT/'docs').as_posix();content=mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
 if p.suffix=='.gz':content='application/gzip'
 cache='no-cache' if p.suffix in ['.html','.json'] else 'max-age=300'
 s3.upload_file(str(p),outputs['SiteBucket'],rel,ExtraArgs={'ContentType':content,'CacheControl':cache});count+=1
print('Uploaded site assets:',count,flush=True)
session.client('cloudfront').create_invalidation(DistributionId=outputs['DistributionId'],InvalidationBatch={'Paths':{'Quantity':1,'Items':['/hospitals/*']},'CallerReference':str(time.time_ns())})
outputs.update(stack=STACK,region=REGION,artifactBucket=bucket,artifactKey=key,packageSha256=digest)
(ROOT/'infra/build/deployment.json').write_text(json.dumps(outputs,indent=2)+'\n');print(json.dumps(outputs,indent=2),flush=True)
