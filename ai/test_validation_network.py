import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analytics import BASE,dataset,execute
from quality import workforce_flags
from ownership_roles import classify
import network
class ValidationNetworkTests(unittest.TestCase):
 def test_source_audit_is_bounded_and_exact(self):
  d=json.loads((BASE/'lab/validation.json').read_text());self.assertEqual(d['recordsChecked'],30)
  self.assertEqual(d['matchingSourceRecords'],30)
  self.assertTrue(all(all(c['match'] for c in r['checks']) for r in d['results']))
 def test_endpoint_review_preserves_records(self):
  p=json.loads((BASE/'lab/policy.json').read_text())['workforce']
  self.assertEqual(p['candidateHospitals'],p['matchedHospitals']+p['reviewExcludedHospitals'])
  self.assertEqual(p['reviewExcludedHospitals'],len(p['reviewRecords']))
  self.assertTrue(any(r['ccn']=='210044' for r in p['reviewRecords']))
  self.assertNotIn('210044',[r['ccn'] for r in p['largestWorkloadIncreases']])
 def test_target_values_are_preserved_and_warned(self):
  q={'analysis':'trend','targetCcn':'210044','metrics':['payrollFte'],'startYear':2019}
  r=execute(q);self.assertEqual(r['rows'][-1]['target'],54.97)
  self.assertTrue(r['qualityReview']['targetEndpointFlags'])
 def test_endpoint_rank_uses_visible_review_screen(self):
  r=execute({'analysis':'rank','metrics':['patientDaysPerFte'],'sortBy':'change','startYear':2019,'limit':25})
  self.assertTrue(r['qualityReview']['excludedEndpointCount'])
  self.assertNotIn('210044',[v['ccn'] for v in r['rows']])
 def test_role_classification_never_promotes_security_or_adp(self):
  for v in ['5% OR GREATER SECURITY INTEREST','5% OR GREATER MORTGAGE INTEREST','ADP OF THE SNF','TRUSTEE OF THE SNF','OTHER']:
   self.assertEqual(classify(v),'REPORTED_ASSOCIATION_ROLE')
  self.assertEqual(classify('LIMITED PARTNERSHIP INTEREST'),'REPORTED_OWNERSHIP_INTEREST')
  self.assertEqual(classify('OPERATIONAL/MANAGERIAL CONTROL'),'REPORTED_CONTROL_ROLE')
 def test_exact_identity_and_source_references(self):
  d=network.layer();providers={(p['id'],p['enrollmentId']) for p in d['facilities']}
  for a in d['assertions']:
   self.assertIn((a['facilityId'],a['enrollmentId']),providers);self.assertIn(a['sourceId'],d['sources'])
   self.assertEqual(a['relationship'],classify(a['role']))
   self.assertTrue(a['ownerAssociateId'] and a['ownerName'])
   self.assertTrue(a['percentage'] is None or 0<=a['percentage']<=100)
 def test_category_and_event_coverage_is_explicit(self):
  d=network.layer();self.assertEqual(len(d['coverage']),8);self.assertEqual(len(d['events']),779)
  self.assertEqual(len({e['id'] for e in d['events']}),len(d['events']))
  for e in d['events']:self.assertRegex(e['effectiveDate'],r'^\d{4}-\d{2}-\d{2}$')
  for c in d['coverage']:
   if c['category'] in ['Renal','CMHC']:self.assertEqual(c['organizationalAssertions'],0)
 def test_footprint_is_ownership_only_and_bounded(self):
  d=network.overview();self.assertGreater(d['crossCategoryOrganizations'],2000)
  self.assertLessEqual(len(d['largestCrossCategoryFootprints']),30)
  target=network.inspect('460010');self.assertLessEqual(len(target['relatedFacilities']),100)
  self.assertLessEqual(len(target['hospitalEvents']),50)
if __name__=='__main__':unittest.main()
