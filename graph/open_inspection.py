"""Open authenticated local tunnels. Never retrieve or print the database password."""
import json,subprocess,time,sys
from pathlib import Path
from urllib.parse import quote
out=Path(__file__).parent/'build';d=json.loads((out/'deployment.json').read_text());processes=[]
try:
 for port in [7474,7687]:
  args=['aws','ssm','start-session','--region',d['region'],'--target',d['InstanceId'],'--document-name','AWS-StartPortForwardingSession','--parameters',json.dumps({'portNumber':[str(port)],'localPortNumber':[str(port)]})]
  log=(out/('tunnel-'+str(port)+'.log')).open('a');processes.append(subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT))
 print('Neo4j Browser: http://127.0.0.1:7474/\nConnect: bolt://localhost:7687\nUsername: neo4j',flush=True)
 print('Retrieve the password through your AWS account: https://'+d['region']+'.console.aws.amazon.com/secretsmanager/secret?name='+quote(d['PasswordSecretArn'],safe='')+'&region='+d['region'],flush=True)
 print('Keep this command running. Press Ctrl+C to close the tunnels.',flush=True)
 while all(p.poll() is None for p in processes):time.sleep(2)
 if any(p.poll() not in [None,0] for p in processes):raise RuntimeError('A port-forward session ended. Inspect graph/build/tunnel-*.log and refresh AWS SSO if needed.')
except KeyboardInterrupt:pass
finally:
 for p in processes:
  if p.poll() is None:p.terminate()
