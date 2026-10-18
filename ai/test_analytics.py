import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import analytics as a
class EngineTests(unittest.TestCase):
 def test_catalog_missing_zero(self):
  self.assertEqual(a.metric('patientMargin',{'patientIncome':0,'netPatientRevenue':100}),0)
  self.assertIsNone(a.metric('patientMargin',{'patientIncome':None,'netPatientRevenue':100}))
  self.assertIsNone(a.metric('currentRatio',{'currentAssets':10,'currentLiabilities':0}))
  self.assertIsNone(a.metric('occupancy',{'days':101,'availableDays':100}))
 def test_unsafe_queries_fail(self):
  for q in [{'analysis':'sql','metrics':['occupancy']},{'analysis':'rank','metrics':['occupancy'],'sql':'DROP TABLE reports'},{'analysis':'trend','metrics':['operatingMargin']},{'analysis':'rank','metrics':['totalMargin'],'filters':{'scope':'city','city':'Springfield'}},{'analysis':'rank','metrics':['totalMargin'],'conditions':[{'metric':'totalMargin','basis':'value','op':'lt','value':'NaN'}]}]:
   with self.assertRaises(a.QueryError):a.execute(q)
 def test_trend_modes(self):
  q={'analysis':'trend','metrics':['occupancy'],'filters':{'bedBand':'same'}}
  fixed=a.execute(q)['rows'];balanced=a.execute({**q,'mode':'balanced'})['rows']
  self.assertEqual(len(fixed),8);self.assertEqual(fixed[0]['change'],None);self.assertTrue(all(r['validPeers']==balanced[0]['validPeers'] for r in balanced));self.assertGreater(fixed[-1]['target'],0)
 def test_rank_compound(self):
  q={'analysis':'rank','metrics':['totalMargin'],'startYear':2019,'sortBy':'change','filters':{'scope':'state','geoState':'UT','ownership':'nonprofit','minBeds':100,'category':'any','providerType':'any'},'conditions':[{'metric':'totalMargin','basis':'value','op':'gt','value':0.05},{'metric':'totalMargin','basis':'change','op':'gt','value':0}]}
  r=a.execute(q)
  self.assertGreater(len(r['rows']),0)
  self.assertEqual(r['rows'],sorted(r['rows'],key=lambda r:(-r['value'],r['ccn'])))
  for row in r['rows']:self.assertGreater(a.metric('totalMargin',a.dataset(2024)[row['ccn']]),0.05);self.assertGreater(row['value'],0)
 def test_zero_small_group_missing_target(self):
  r=a.execute({'analysis':'trend','metrics':['occupancy'],'filters':{'scope':'state','geoState':'UT','bedBand':'same'}})
  self.assertIsNone(r['rows'][-1]['peerMedian'])
  r=a.execute({'analysis':'trend','metrics':['occupancy'],'targetCcn':'460061'})
  self.assertIsNone(r['rows'][0]['target'])
 def test_case_plans(self):
  for c in json.loads((a.BASE/'lab/use-cases.json').read_text()):
   if 'query' in c:
    r=a.execute(c['query']);self.assertIn('catalogSha256',r);self.assertTrue(r['sources'])
 def test_ownership_crosswalk(self):
  from providers import layer
  d=layer();self.assertGreater(len(d['providers']),5000);self.assertGreater(len(d['relationships']),10000)
  enrollment={(p['ccn'],p['enrollmentId']) for p in d['providers']}
  self.assertTrue(all((r['ccn'],r['enrollmentId']) in enrollment for r in d['relationships']))
  self.assertTrue(all(r['ownerName'] and r['ownerAssociateId'] and r['evidenceStatus']=='source_reported' for r in d['relationships']))
if __name__=='__main__':unittest.main()
