import unittest
from research.resource_report import estimate_cost


class ResourceReportTests(unittest.TestCase):
    def setUp(self):
        self.price={'source':'test','checked_date':'2026-11-06','rates':{'m':{'off_peak':{'input_cached':1,'input_uncached':2,'output':3},'peak':{'input_cached':2,'input_uncached':4,'output':6}}}}

    def test_actual_cached_and_uncached_usage_bounds(self):
        value=estimate_cost([{'id':'a','model':'m','usage':{'input_tokens':1000000,'cache_tokens':250000,'output_tokens':100000}}],self.price)
        self.assertAlmostEqual(value['usd_lower'],2.05)
        self.assertAlmostEqual(value['usd_upper'],4.10)
        self.assertFalse(value['is_invoice'])

    def test_missing_usage_is_not_free(self):
        value=estimate_cost([{'id':'unknown','model':'m','usage':None}],self.price)
        self.assertEqual(value['unpriced_call_ids'],['unknown'])


if __name__=='__main__':unittest.main()
