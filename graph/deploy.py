"""Provision the final private Neo4j inspection environment in AWS."""
import hashlib,json,time
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'graph/build';session=boto3.Session(region_name='us-east-2');cf=session.client('cloudformation');ec2=session.client('ec2');ssm=session.client('ssm');s3=session.client('s3')
account=session.client('sts').get_caller_identity()['Account'];bucket=f'hcris-ai-artifacts-{account}-us-east-2';archive=OUT/'neo4j-import.zip';digest=hashlib.sha256(archive.read_bytes()).hexdigest();key='graph/'+digest+'.zip';s3.upload_file(str(archive),bucket,key)
vpcs=ec2.describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs']
if not vpcs:raise RuntimeError('No default VPC; specify a reviewed VPC/subnet before deployment.')
vpc=vpcs[0]['VpcId'];subnets=ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpc]},{'Name':'default-for-az','Values':['true']}])['Subnets']
if not subnets:raise RuntimeError('No default subnet.')
subnet=sorted(subnets,key=lambda x:x['AvailabilityZone'])[0]['SubnetId'];ami=ssm.get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')['Parameter']['Value']
stack_name='hcris-neo4j-inspection';params=[{'ParameterKey':k,'ParameterValue':v} for k,v in {'VpcId':vpc,'SubnetId':subnet,'AmiId':ami,'ArtifactBucket':bucket,'ArtifactKey':key}.items()]
kwargs={'StackName':stack_name,'TemplateBody':(ROOT/'graph/neo4j-aws.json').read_text(),'Parameters':params,'Capabilities':['CAPABILITY_IAM'],'Tags':[{'Key':'Project','Value':'HCRIS Dashboard'},{'Key':'Environment','Value':'draft'}]}
try:existing=cf.describe_stacks(StackName=stack_name)['Stacks'][0]
except ClientError as e:
 if 'does not exist' not in str(e):raise
 existing=None
if existing:raise RuntimeError('The Neo4j stack already exists. Inspect it before changing its data or resources.')
cf.create_stack(**kwargs);previous=''
for _ in range(100):
 stack=cf.describe_stacks(StackName=stack_name)['Stacks'][0];status=stack['StackStatus']
 if status!=previous:print('Neo4j infrastructure:',status,flush=True);previous=status
 if status=='CREATE_COMPLETE':break
 if any(x in status for x in ['FAILED','ROLLBACK']):
  print(json.dumps([{'resource':e['LogicalResourceId'],'status':e['ResourceStatus'],'reason':e.get('ResourceStatusReason')} for e in cf.describe_stack_events(StackName=stack_name)['StackEvents'][:12]],indent=2));raise RuntimeError('Neo4j infrastructure did not complete.')
 time.sleep(5)
else:raise RuntimeError('Stack is still running. Inspect the existing deployment before retrying.')
outputs={o['OutputKey']:o['OutputValue'] for o in stack['Outputs']};outputs.update(stack=stack_name,region='us-east-2',artifactBucket=bucket,artifactKey=key,artifactSha256=digest)
(OUT/'deployment.json').write_text(json.dumps(outputs,indent=2)+'\n');print(json.dumps(outputs,indent=2),flush=True)
