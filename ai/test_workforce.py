import gzip,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import analytics as a
from build_workforce import clean,join_report
class WorkforceTests(unittest.TestCase):
 def test_exact_join_rejects_changed_period_or_ccn(self):
  r={'reportId':'1','ccn':'460010','begin':'2024-01-01','end':'2024-12-31'}
  raw={'rpt_rec_num':'1','Provider CCN':'460010','Fiscal Year Begin Date':'2024-01-01','Fiscal Year End Date':'2024-12-31'}
  self.assertTrue(join_report(r,raw))
  for key,v in [('rpt_rec_num','2'),('Provider CCN','460001'),('Fiscal Year End Date','2024-11-30')]:self.assertFalse(join_report(r,{**raw,key:v}))
 def test_unknown_zero_and_negative(self):
  self.assertEqual(clean('0'),0)
  for v in ['',None,'NaN','-1']:self.assertIsNone(clean(v))
  r={'payrollFte':0,'beds':100,'days':365,'reportDays':365,'salaries':1000}
  self.assertEqual(a.metric('ftePer100Beds',r),0)
  self.assertIsNone(a.metric('patientDaysPerFte',r));self.assertIsNone(a.metric('salaryPerFte',r))
 def test_period_average_fte_is_not_annualized(self):
  r={'payrollFte':100,'beds':50,'days':3000,'reportDays':300,'salaries':300000}
  self.assertEqual(a.metric('payrollFte',r),100)
  self.assertEqual(a.metric('ftePer100Beds',r),200)
  self.assertAlmostEqual(a.metric('patientDaysPerFte',r),36.525)
  self.assertAlmostEqual(a.metric('salaryPerFte',r),3652.5)
 def test_snapshot_coverage_and_missing_residents(self):
  for y in a.YEARS:
   s=a.CAT['workforceSources'][str(y)];self.assertEqual(s['coverage'].get('unmatchedReports',0),0)
   self.assertGreater(s['coverage']['payrollFteValid'],5800)
   self.assertLess(s['coverage']['residentFteValid'],s['coverage']['payrollFteValid'])
 def test_workforce_trend_lineage_and_balanced_denominators(self):
  r=a.execute({'analysis':'trend','metrics':['patientDaysPerFte'],'startYear':2019,'mode':'balanced'})
  self.assertEqual(len(r['rows']),6);self.assertEqual(len(r['sources']),12)
  self.assertEqual(len({x['validPeers'] for x in r['rows']}),1)
  self.assertTrue(all(x['target'] is None or x['target']>=0 for x in r['rows']))
 def test_unsupported_workforce_does_not_reach_model(self):
  from planner import plan
  for q in ['Show nurse-to-patient ratios','Rank hospitals by turnover','Which hospitals have staffing shortages?']:
   self.assertIn('clarification',plan(q,{}))
if __name__=='__main__':unittest.main()
