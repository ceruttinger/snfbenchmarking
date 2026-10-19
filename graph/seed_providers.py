"""Persist a bounded, provenance-preserving enrichment sample for graph inspection."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ai'))
from providers import inspect,nppes
out=Path(__file__).parent/'build';out.mkdir(exist_ok=True)
p=inspect('460010');known={r['npi'] for r in p['enrollments']};other=[r['npi'] for g in p['crossCategoryEnrollments'] for r in g['rows'] if r['npi'] not in known]
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as pool:extra=list(pool.map(nppes,list(dict.fromkeys(other))[:10]))
p['additionalNppesSample']=extra
(out/'provider-enrichment.json').write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'target':p['ccn'],'organizationNppesRecords':sum(r.get('entityType')=='NPI-2' for r in p['nppes']+extra),'crossCategoryEnrollments':sum(len(g['rows']) for g in p['crossCategoryEnrollments']),'lookupLimit':10},indent=2))
