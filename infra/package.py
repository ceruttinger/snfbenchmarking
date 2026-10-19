"""Package the tested service and existing derived snapshots for Lambda."""
import hashlib,json,zipfile,py_compile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for source in (ROOT/'ai').glob('*.py'):py_compile.compile(str(source),doraise=True)
out=ROOT/'infra/build';out.mkdir(exist_ok=True)
archive=out/'hcris-query.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in (ROOT/'ai').glob('*.py'):
  if not p.name.startswith(('test_','build_')):z.write(p,p.name)
 z.write(ROOT/'ai/query_schema.json','query_schema.json')
 for p in (ROOT/'docs/hospitals').glob('data-*.gz'):z.write(p,'data/'+p.name)
 for p in (ROOT/'docs/hospitals/workforce').glob('data-*.gz'):z.write(p,'data/workforce/'+p.name)
 for name in ['semantic.json','providers.json']:z.write(ROOT/'docs/hospitals/lab'/name,'data/lab/'+name)
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
