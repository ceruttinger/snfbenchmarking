"""Build compact, source-traceable hospital pilot data from CMS public-use CSVs."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

COLUMNS = ['ccn','name','city','state','kind','providerType','control','rural',
           'begin','end','reportDays','reportId','beds','days','availableDays',
           'discharges','medicareDays','medicaidDays','netPatientRevenue',
           'operatingExpense','patientIncome','otherIncome','netIncome',
           'currentAssets','currentLiabilities','assets','liabilities','uncompensated']
FIELDS = ['Number of Beds','Total Days (V + XVIII + XIX + Unknown)',
          'Total Bed Days Available','Total Discharges (V + XVIII + XIX + Unknown)',
          'Total Days Title XVIII','Total Days Title XIX','Net Patient Revenue',
          'Less Total Operating Expense','Net Income from Service to Patients',
          'Total Other Income','Net Income','Total Current Assets',
          'Total Current Liabilities','Total Assets','Total Liabilities',
          'Cost of Uncompensated Care']
URLS = {
  2022:'https://data.cms.gov/sites/default/files/2026-10/1be4ec08-6d9d-4e05-b871-c4d74fe81089/CostReport_2022_Final.csv',
  2023:'https://data.cms.gov/sites/default/files/2026-10/e48e1326-aeeb-4ad4-acf6-a506871b6d20/CostReport_2023_Final.csv'}

def number(value):
    try:
        n = float(value.replace(',', ''))
        return n if math.isfinite(n) else None
    except (ValueError, AttributeError):
        return None

def build(input_dir, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    audit = {}
    for year, url in URLS.items():
        path = input_dir / f'CostReport_{year}.csv'
        chosen = {}
        rows = list(csv.DictReader(path.open(encoding='utf-8-sig')))
        for row in rows:
            ccn = row['Provider CCN'].strip().zfill(6)
            if not ccn.isdigit() or len(ccn) != 6:
                continue
            begin = datetime.strptime(row['Fiscal Year Begin Date'], '%m/%d/%Y')
            end = datetime.strptime(row['Fiscal Year End Date'], '%m/%d/%Y')
            duration = (end - begin).days + 1
            # One representative report per CCN/source year, not a summed calendar year.
            rank = (300 <= duration <= 430, duration, end, int(row['rpt_rec_num']))
            entry = [ccn,row['Hospital Name'],row['City'],row['State Code'],
                     row['CCN Facility Type'],row['Provider Type'],row['Type of Control'],
                     row['Rural Versus Urban'],begin.date().isoformat(),end.date().isoformat(),
                     duration,row['rpt_rec_num']] + [number(row[f]) for f in FIELDS]
            if ccn not in chosen or rank > chosen[ccn][0]:
                chosen[ccn] = (rank, entry)
        result = [chosen[k][1] for k in sorted(chosen)]
        payload = {'year':year,'columns':COLUMNS,'rows':result,'source':url,
                   'sourceModified':'2026-10-05','retrieved':'2026-10-13',
                   'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'inputReports':len(rows),'selectedReports':len(result),
                   'selection':'Prefer a 300–430-day report, then longest duration, latest end date, highest report ID. One report per CCN/source year; not a calendar-year aggregation.'}
        assert all(len(x) == len(COLUMNS) for x in result)
        raw = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
        (output_dir / f'data-{year}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
        audit[year] = {k:payload[k] for k in ['source','sourceModified','retrieved','sourceSha256','inputReports','selectedReports','selection']}
        audit[year]['standardPeriodReports'] = sum(300 <= x[10] <= 430 for x in result)
        audit[year]['types'] = dict(Counter(x[4] for x in result))
    (output_dir / 'manifest.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parents[1]/'docs/hospitals')
    args = parser.parse_args()
    build(args.input_dir, args.output_dir)
