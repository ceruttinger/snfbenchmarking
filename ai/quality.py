"""Transparent endpoint review screens; never corrections or shortage findings."""
import math
def positive(v):return isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v) and v>0
def workforce_flags(a,b):
 reasons=[]
 if not a or not b:return ['Missing endpoint report']
 f0=a.get('payrollFte');f1=b.get('payrollFte')
 if not all(positive(v) for v in [f0,f1]):return ['Missing or nonpositive payroll FTE endpoint']
 if max(f1/f0,f0/f1)>4:reasons.append('More than fourfold payroll FTE change')
 d0=a.get('days');d1=b.get('days');p0=a.get('reportDays');p1=b.get('reportDays')
 if all(positive(v) for v in [d0,d1,p0,p1]):
  dayratio=(d1/p1)/(d0/p0);workratio=dayratio/(f1/f0)
  if max(dayratio,1/dayratio)>4:reasons.append('More than fourfold annualized patient-day change')
  if max(workratio,1/workratio)>4:reasons.append('More than fourfold patient-days-per-FTE change')
 if a.get('providerType')!=b.get('providerType'):reasons.append('Reported provider type changed')
 return reasons
