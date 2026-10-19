"""Add/update a versioned graph snapshot in the existing server without replacing it.

Preserves graph nodes and prior catalog lineage. If initially stopped, starts only
for the import and restores stopped state. Credentials never leave the server.
"""
import hashlib,json,time
from pathlib import Path
import boto3
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'graph/build'
d=json.loads((OUT/'deployment.json').read_text());session=boto3.Session(region_name=d['region'])
s3=session.client('s3');ssm=session.client('ssm');ec2=session.client('ec2');cf=session.client('cloudformation');iam=session.client('iam')
archive=OUT/'neo4j-import.zip';sha=hashlib.sha256(archive.read_bytes()).hexdigest();key='graph/'+sha+'.zip'
s3.upload_file(str(archive),d['artifactBucket'],key)
role=cf.describe_stack_resource(StackName=d['stack'],LogicalResourceId='Role')['StackResourceDetail']['PhysicalResourceId']
state=ec2.describe_instances(InstanceIds=[d['InstanceId']])['Reservations'][0]['Instances'][0]['State']['Name']
if state not in ['running','stopped']:raise RuntimeError('Wait for the instance state to settle before updating.')
policy='ReadWorkforceSnapshot'+sha[:12]
iam.put_role_policy(RoleName=role,PolicyName=policy,PolicyDocument=json.dumps({'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'s3:GetObject','Resource':'arn:aws:s3:::'+d['artifactBucket']+'/'+key}]}))
try:
 if state=='stopped':
  ec2.start_instances(InstanceIds=[d['InstanceId']]);print('Starting existing graph server for import; it will be stopped again.',flush=True)
 for _ in range(100):
  info=ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[d['InstanceId']]}])['InstanceInformationList']
  if info and info[0]['PingStatus']=='Online':break
  time.sleep(5)
 else:raise RuntimeError('Existing server did not become available to SSM.')
 commands=['set -e','for i in $(seq 1 12); do aws s3 cp s3://'+d['artifactBucket']+'/'+key+' /var/lib/hcris-neo4j/workforce-import.zip --region '+d['region']+' && break; sleep 5; done',
  'python3 -c "import hashlib; assert hashlib.sha256(open(\'/var/lib/hcris-neo4j/workforce-import.zip\',\'rb\').read()).hexdigest()==\''+sha+'\'"',
  'python3 -c "import zipfile; zipfile.ZipFile(\'/var/lib/hcris-neo4j/workforce-import.zip\').extractall(\'/var/lib/hcris-neo4j/import\')"',
  'chown -R 7474:7474 /var/lib/hcris-neo4j/import',
  'systemctl start docker',
  "for i in $(seq 1 90); do if docker exec hcris-neo4j bash -c 'export NEO4J_PASSWORD=$(printf \"%s\" \"$NEO4J_AUTH\" | cut -d/ -f2-); cypher-shell -u neo4j \"RETURN 1;\"' >/dev/null 2>&1; then break; fi; sleep 3; done",
  "if ! docker exec hcris-neo4j bash -c 'export NEO4J_PASSWORD=$(printf \"%s\" \"$NEO4J_AUTH\" | cut -d/ -f2-); cypher-shell -u neo4j -f /import/load.cypher' > /var/lib/hcris-neo4j/workforce-import.log 2>&1; then tail -c 2000 /var/lib/hcris-neo4j/workforce-import.log; exit 1; fi",
  "docker exec hcris-neo4j bash -c 'export NEO4J_PASSWORD=$(printf \"%s\" \"$NEO4J_AUTH\" | cut -d/ -f2-); cypher-shell -u neo4j --format plain \"MATCH (r:CostReport) RETURN count(r) AS reports, count(r.payrollFte) AS payrollFteReports, count(r.residentFte) AS residentFteReports, count(r.salaries) AS salaryReports; MATCH (r:CostReport {ccn: \\\"460010\\\",datasetYear:2024}) RETURN r.payrollFte,r.metric_ftePer100Beds,r.metric_patientDaysPerFte,r.metric_salaryPerFte; MATCH (n) RETURN count(n) AS nodes; MATCH ()-[r]->() RETURN count(r) AS relationships;\"'"
 ]
 command=ssm.send_command(InstanceIds=[d['InstanceId']],DocumentName='AWS-RunShellScript',Parameters={'commands':commands,'executionTimeout':['1200']})['Command']['CommandId']
 print('Applying workforce properties and source lineage to existing graph.',flush=True)
 for _ in range(240):
  try:r=ssm.get_command_invocation(CommandId=command,InstanceId=d['InstanceId'])
  except ssm.exceptions.InvocationDoesNotExist:time.sleep(5);continue
  if r['Status'] in ['Success','Failed','Cancelled','TimedOut']:
   if r['Status']!='Success':raise RuntimeError('Import failed; inspect the server workforce-import.log. '+r.get('StandardOutputContent','')[-2200:]+r.get('StandardErrorContent','')[-1000:])
   (OUT/'workforce-verification.txt').write_text(r['StandardOutputContent']);print(r['StandardOutputContent'],flush=True);break
  time.sleep(5)
 else:raise RuntimeError('Import is still running; inspect its SSM command before retrying.')
 d.update(artifactKey=key,artifactSha256=sha,previousPowerState=state,workforceCatalogSha256=json.loads((OUT/'graph-manifest.json').read_text())['catalogSha256'])
 (OUT/'deployment.json').write_text(json.dumps(d,indent=2)+'\n')
finally:
 iam.delete_role_policy(RoleName=role,PolicyName=policy)
 if state=='stopped':
  ec2.stop_instances(InstanceIds=[d['InstanceId']]);print('Restored the graph server to stopped state.',flush=True)
