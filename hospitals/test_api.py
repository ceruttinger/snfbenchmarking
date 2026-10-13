import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import build_data as api

class ApiTests(unittest.TestCase):
    def row(self, key):
        return {**dict.fromkeys(api.IDENTITY_FIELDS+api.FIELDS,''),'rpt_rec_num':key}

    def test_pagination_is_stable_and_complete(self):
        urls=[]
        pages=[[self.row('1'),self.row('2')],[self.row('3')]]
        def response(request, timeout):
            urls.append(request.full_url)
            return io.StringIO(json.dumps(pages.pop(0)))
        with patch.object(api,'urlopen',side_effect=response):
            result=api.query_api('https://data.cms.gov/example',page_size=2)
        self.assertEqual([r['rpt_rec_num'] for r in result],['1','2','3'])
        self.assertEqual([parse_qs(urlparse(u).query)['offset'] for u in urls],[['0'],['2']])
        self.assertEqual(parse_qs(urlparse(urls[0]).query)['sort'],['rpt_rec_num'])

    def test_repeated_page_is_not_published(self):
        with patch.object(api,'urlopen',side_effect=[io.StringIO(json.dumps([self.row('1')])),io.StringIO(json.dumps([self.row('1')]))]):
            with self.assertRaisesRegex(ValueError,'Repeated report'):
                api.query_api('https://data.cms.gov/example',page_size=1)

    def test_missing_schema_and_non_array_fail(self):
        for payload in [[{'rpt_rec_num':'1'}],{'error':'bad response'}]:
            with patch.object(api,'urlopen',return_value=io.StringIO(json.dumps(payload))):
                with self.assertRaises(ValueError):
                    api.query_api('https://data.cms.gov/example')

    def test_null_zero_dates(self):
        self.assertIsNone(api.number(None))
        self.assertIsNone(api.number(''))
        self.assertEqual(api.number('0'),0)
        self.assertEqual(api.parse_date('2023-01-01'),api.parse_date('01/01/2023'))

if __name__=='__main__':
    unittest.main()
