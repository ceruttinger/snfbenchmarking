import csv,json,re,unittest
from pathlib import Path
BASE=Path(__file__).parent/'build'
def rows(name):
 with (BASE/(name+'.csv')).open() as f:return list(csv.DictReader(f))
class GraphTests(unittest.TestCase):
 def test_counts_and_keys(self):
  manifest=json.loads((BASE/'graph-manifest.json').read_text())
  for name,count in manifest['counts'].items():
   r=rows(name);self.assertEqual(len(r),count,name)
   if r and 'id' in r[0]:self.assertEqual(len({v['id'] for v in r}),len(r),name)
  self.assertEqual(manifest['financialFacilityYears'],48193)
 def test_references(self):
  hospitals={r['id'] for r in rows('hospitals')};sources={r['id'] for r in rows('sources')};organizations={r['id'] for r in rows('organizations')};enrollments={r['id'] for r in rows('enrollments')}
  for r in rows('reports'):self.assertIn(r['ccn'],hospitals);self.assertIn(r['snapshotId'],sources)
  for r in rows('ownership_assertions'):self.assertIn(r['ccn'],hospitals);self.assertIn(r['organizationId'],organizations);self.assertIn(r['snapshotId'],sources);self.assertIn(r['enrollmentId'],enrollments);self.assertEqual(r['evidenceStatus'],'source_reported')
 def test_coverage_is_explicit(self):
  r=rows('npis');self.assertEqual(sum(v['enumerationType']=='NPI-2' for v in r),11);self.assertTrue(any(v['enumerationType']=='not_enriched' for v in r))
  self.assertTrue(all(v['ultimateParentResolved']=='false' for v in rows('organizations')))
 def test_no_inferred_ownership(self):
  assertions=rows('ownership_assertions');self.assertTrue(any(r['percentage']=='' for r in assertions));self.assertTrue(any(r['ccn']=='460010' and r['percentage']=='100' for r in assertions))
if __name__=='__main__':unittest.main()
