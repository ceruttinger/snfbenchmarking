"""Query CMS APIs in memory and build derived hospital dashboard caches.

Never downloads or saves raw CMS CSV/ZIP distributions.
"""
import argparse
import gzip
import hashlib
import json
import math
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from collections import Counter
from datetime import datetime
from pathlib import Path

COLUMNS = ['ccn','name','city','state','kind','providerType','control','rural',
           'begin','end','reportDays','reportId','beds','days','availableDays',
           'discharges','medicareDays','medicaidDays','netPatientRevenue',
           'operatingExpense','patientIncome','otherIncome','netIncome',
           'currentAssets','currentLiabilities','assets','liabilities','uncompensated','county']
FIELDS = ['Number of Beds','Total Days (V + XVIII + XIX + Unknown)',
          'Total Bed Days Available','Total Discharges (V + XVIII + XIX + Unknown)',
          'Total Days Title XVIII','Total Days Title XIX','Net Patient Revenue',
          'Less Total Operating Expense','Net Income from Service to Patients',
          'Total Other Income','Net Income','Total Current Assets',
          'Total Current Liabilities','Total Assets','Total Liabilities',
          'Cost of Uncompensated Care']
URLS = {int(year):url for year,url in json.loads((Path(__file__).parent/'api_sources.json').read_text()).items()}
IDENTITY_FIELDS = ['Provider CCN','Hospital Name','City','State Code','CCN Facility Type',
                   'Provider Type','Type of Control','Rural Versus Urban',
                   'Fiscal Year Begin Date','Fiscal Year End Date','rpt_rec_num','County']

def query_api(url, page_size=1000):
    """Stable ordering, bounded pages, no persisted raw response or fallback files."""
    offset, result, report_ids = 0, [], set()
    while True:
        query = urlencode({'size':page_size,'offset':offset,'sort':'rpt_rec_num',
                           'column':','.join(IDENTITY_FIELDS + FIELDS)})
        for attempt in range(3):
            try:
                with urlopen(Request(url+'?'+query, headers={'Accept':'application/json'}), timeout=45) as response:
                    page = json.load(response)
                break
            except HTTPError as error:
                if error.code not in (429,500,502,503,504) or attempt == 2:
                    raise
                time.sleep(2 ** attempt)
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        if not isinstance(page, list):
            raise ValueError('CMS API did not return a record array')
        for row in page:
            if not all(key in row for key in IDENTITY_FIELDS + FIELDS):
                raise ValueError('CMS API schema changed: required fields are missing')
            report_id = str(row['rpt_rec_num'])
            if report_id in report_ids:
                raise ValueError('Repeated report across API pages; refusing partial/duplicated cache')
            report_ids.add(report_id)
        result.extend(page)
        print(f'CMS API: {len(result)} reports queried', flush=True)
        if len(page) < page_size:
            return result
        offset += len(page)
        if offset > 100000:
            raise ValueError('Unexpected API pagination size')

def parse_date(value):
    for fmt in ('%Y-%m-%d','%m/%d/%Y'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError('Invalid CMS reporting date: '+str(value))

def number(value):
    try:
        n = float(str(value).replace(',', ''))
        return n if math.isfinite(n) else None
    except (ValueError, AttributeError):
        return None

def build(output_dir, years=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = json.loads((output_dir/'manifest.json').read_text()) if (output_dir/'manifest.json').exists() else {}
    for year, url in URLS.items():
        if years is not None and year not in years:
            continue
        chosen = {}
        rows = query_api(url)
        for row in rows:
            ccn = row['Provider CCN'].strip().zfill(6)
            if not ccn.isdigit() or len(ccn) != 6:
                continue
            begin = parse_date(row['Fiscal Year Begin Date'])
            end = parse_date(row['Fiscal Year End Date'])
            duration = (end - begin).days + 1
            # One representative report per CCN/source year, not a summed calendar year.
            rank = (300 <= duration <= 430, duration, end, int(row['rpt_rec_num']))
            entry = [ccn,row['Hospital Name'],row['City'],row['State Code'],
                     row['CCN Facility Type'],row['Provider Type'],row['Type of Control'],
                     row['Rural Versus Urban'],begin.date().isoformat(),end.date().isoformat(),
                     duration,row['rpt_rec_num']] + [number(row[f]) for f in FIELDS] + [row['County']]
            if ccn not in chosen or rank > chosen[ccn][0]:
                chosen[ccn] = (rank, entry)
        result = [chosen[k][1] for k in sorted(chosen)]
        payload = {'year':year,'columns':COLUMNS,'rows':result,'source':url,
                   'sourceType':'CMS paginated JSON API',
                   'queriedAt':datetime.now().astimezone().isoformat(timespec='seconds'),
                   'apiRecordsSha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                   'inputReports':len(rows),'selectedReports':len(result),
                   'selection':'Prefer a 300–430-day report, then longest duration, latest end date, highest report ID. One report per CCN/source year; not a calendar-year aggregation.'}
        assert all(len(x) == len(COLUMNS) for x in result)
        raw = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
        (output_dir / f'data-{year}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
        audit[str(year)] = {k:payload[k] for k in ['source','sourceType','queriedAt','apiRecordsSha256','inputReports','selectedReports','selection']}
        audit[str(year)]['standardPeriodReports'] = sum(300 <= x[10] <= 430 for x in result)
        audit[str(year)]['types'] = dict(Counter(x[4] for x in result))
    (output_dir / 'manifest.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1]/'docs/hospitals')
    parser.add_argument('--years', type=int, nargs='+', choices=sorted(URLS))
    args = parser.parse_args()
    build(args.output_dir,args.years)
