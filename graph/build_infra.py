"""Private Neo4j inspection VM: no inbound rules; access through SSM tunnels."""
import json
from pathlib import Path
ref=lambda k:{'Ref':k}
get=lambda r,k:{'Fn::GetAtt':[r,k]}
sub=lambda s:{'Fn::Sub':s}
bootstrap='''#!/bin/bash
set -euo pipefail
mkdir -p /var/lib/hcris-neo4j/{data,logs,import}
dnf install -y docker unzip
systemctl enable --now docker
aws s3 cp s3://${ArtifactBucket}/${ArtifactKey} /var/lib/hcris-neo4j/import.zip --region ${AWS::Region}
python3 -c "import zipfile;zipfile.ZipFile('/var/lib/hcris-neo4j/import.zip').extractall('/var/lib/hcris-neo4j/import')"
neo4j_password=$(aws secretsmanager get-secret-value --secret-id '${Password}' --region '${AWS::Region}' --query SecretString --output text | python3 -c 'import sys,json;print(json.load(sys.stdin)["password"])')
umask 077
printf '%s\\n' "NEO4J_AUTH=neo4j/$neo4j_password" 'NEO4J_server_memory_heap_initial__size=512m' 'NEO4J_server_memory_heap_max__size=1g' 'NEO4J_server_memory_pagecache_size=1g' 'NEO4J_server_directories_import=/import' 'NEO4J_server_bolt_advertised__address=localhost:7687' 'NEO4J_server_http_advertised__address=localhost:7474' > /var/lib/hcris-neo4j/neo4j.env
unset neo4j_password
chown -R 7474:7474 /var/lib/hcris-neo4j/data /var/lib/hcris-neo4j/logs /var/lib/hcris-neo4j/import
docker run -d --name hcris-neo4j --restart unless-stopped --env-file /var/lib/hcris-neo4j/neo4j.env -p 127.0.0.1:7474:7474 -p 127.0.0.1:7687:7687 -v /var/lib/hcris-neo4j/data:/data -v /var/lib/hcris-neo4j/logs:/logs -v /var/lib/hcris-neo4j/import:/import neo4j:5.26
for attempt in $(seq 1 90); do
 if docker exec hcris-neo4j bash -c 'export NEO4J_PASSWORD=$(printf "%s" "$NEO4J_AUTH" | cut -d/ -f2-); cypher-shell -u neo4j --format plain "RETURN 1;"' >/dev/null 2>&1; then break; fi
 sleep 3
done
docker exec hcris-neo4j bash -c 'export NEO4J_PASSWORD=$(printf "%s" "$NEO4J_AUTH" | cut -d/ -f2-); cypher-shell -u neo4j -f /import/load.cypher' > /var/lib/hcris-neo4j/import.log 2>&1
docker exec hcris-neo4j bash -c 'export NEO4J_PASSWORD=$(printf "%s" "$NEO4J_AUTH" | cut -d/ -f2-); cypher-shell -u neo4j --format plain "MATCH (r:CostReport) RETURN count(r) AS costReports; MATCH (a:OwnershipAssertion) RETURN count(a) AS ownershipAssertions; MATCH (n) RETURN count(n) AS nodes; MATCH ()-[r]->() RETURN count(r) AS relationships;"' > /var/lib/hcris-neo4j/verification.txt
printf 'complete\\n' > /var/lib/hcris-neo4j/import.complete
'''
r={}
r['Password']={'Type':'AWS::SecretsManager::Secret','Properties':{'Description':'HCRIS Neo4j inspection login; never published in source or outputs.','GenerateSecretString':{'SecretStringTemplate':'{"username":"neo4j"}','GenerateStringKey':'password','PasswordLength':32,'ExcludePunctuation':True}}}
r['SecurityGroup']={'Type':'AWS::EC2::SecurityGroup','Properties':{'GroupDescription':'No inbound access; Neo4j inspection through authenticated SSM port forwarding','VpcId':ref('VpcId'),'SecurityGroupIngress':[],'SecurityGroupEgress':[{'IpProtocol':'-1','CidrIp':'0.0.0.0/0'}],'Tags':[{'Key':'Name','Value':'hcris-neo4j-private'}]}}
r['Role']={'Type':'AWS::IAM::Role','Properties':{'AssumeRolePolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'ec2.amazonaws.com'},'Action':'sts:AssumeRole'}]},'ManagedPolicyArns':[sub('arn:${AWS::Partition}:iam::aws:policy/AmazonSSMManagedInstanceCore')],'Policies':[{'PolicyName':'ReadOwnGraphArtifactsAndPassword','PolicyDocument':{'Version':'2012-10-17','Statement':[{'Effect':'Allow','Action':'s3:GetObject','Resource':sub('arn:${AWS::Partition}:s3:::${ArtifactBucket}/${ArtifactKey}')},{'Effect':'Allow','Action':'secretsmanager:GetSecretValue','Resource':ref('Password')}]}}]}}
r['InstanceProfile']={'Type':'AWS::IAM::InstanceProfile','Properties':{'Roles':[ref('Role')]}}
r['Instance']={'Type':'AWS::EC2::Instance','Properties':{'ImageId':ref('AmiId'),'InstanceType':'t3.medium','IamInstanceProfile':ref('InstanceProfile'),'MetadataOptions':{'HttpEndpoint':'enabled','HttpTokens':'required','HttpPutResponseHopLimit':1},'NetworkInterfaces':[{'DeviceIndex':'0','AssociatePublicIpAddress':True,'SubnetId':ref('SubnetId'),'GroupSet':[ref('SecurityGroup')]}],'BlockDeviceMappings':[{'DeviceName':'/dev/xvda','Ebs':{'VolumeType':'gp3','VolumeSize':20,'Encrypted':True,'DeleteOnTermination':True}}],'UserData':{'Fn::Base64':sub(bootstrap)},'Tags':[{'Key':'Name','Value':'hcris-neo4j-inspection'},{'Key':'Project','Value':'HCRIS Dashboard'},{'Key':'Environment','Value':'draft'}]}}
t={'AWSTemplateFormatVersion':'2010-09-09','Description':'HCRIS Neo4j Community inspection server with no inbound ports and Secrets Manager authentication.','Parameters':{'VpcId':{'Type':'AWS::EC2::VPC::Id'},'SubnetId':{'Type':'AWS::EC2::Subnet::Id'},'AmiId':{'Type':'AWS::EC2::Image::Id'},'ArtifactBucket':{'Type':'String'},'ArtifactKey':{'Type':'String'}},'Resources':r,'Outputs':{'InstanceId':{'Value':ref('Instance')},'PasswordSecretArn':{'Value':ref('Password')},'BrowserPort':{'Value':'7474'},'BoltPort':{'Value':'7687'},'SecurityGroup':{'Value':ref('SecurityGroup')}}}
(Path(__file__).parent/'neo4j-aws.json').write_text(json.dumps(t,indent=2)+'\n')
