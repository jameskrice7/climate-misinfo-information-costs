"""Checks for material data/estimand mistakes and numerical identification."""
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from publication_analysis import load_panel, ROOT, X

class PublicationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=load_panel()

    def test_actual_listing_markets(self):
        markets=self.p.groupby('RIC').Market.first()
        for ric,market in {'MTFN.JK':'Indonesia','PETR3.SA':'Brazil',
                '6477.TW':'Taiwan','0883.HK':'Hong Kong','SHEL.AS':'Netherlands'}.items():
            self.assertEqual(markets[ric],market)

    def test_exposure_window_and_unique_keys(self):
        self.assertFalse(self.p.duplicated(['RIC','Date']).any())
        d=self.p.loc[self.p.analysis_eligible]
        self.assertLessEqual(d.Date.max(),pd.Timestamp('2025-10-13'))
        self.assertTrue((d.SpreadPercent>0).all())
        self.assertTrue((d.ASK>=d.BID).all())

    def test_daily_spread_and_vwap_gap_identities(self):
        p=self.p
        ok=p.SpreadPercent.notna()
        np.testing.assert_allclose(p.loc[ok,'SpreadPercent'],
            200*(p.loc[ok,'ASK']-p.loc[ok,'BID'])/(p.loc[ok,'ASK']+p.loc[ok,'BID']),atol=1e-10)
        ok=p.PriceImpact.notna()
        np.testing.assert_allclose(p.loc[ok,'OrderFlow'],p.loc[ok,'VWAP']-p.loc[ok,'MidPrice'],atol=1e-10)
        np.testing.assert_allclose(p.loc[ok,'PriceImpact'],
            100*p.loc[ok,'OrderFlow'].abs()/p.loc[ok,'MidPrice'],atol=1e-10)

    def test_lag_uses_prior_observed_session_including_weekends(self):
        p=self.p
        a=p.loc[(p.Volume>0)&(p['Price Close']>0)].copy()
        expected=a.groupby('RIC')[X].shift(1)
        ok=a.lag_exposure.notna()
        np.testing.assert_allclose(a.loc[ok,'lag_exposure'],expected[ok])
        mondays=a.loc[(a.Date.dt.weekday==0)&a.lag_exposure.notna()]
        self.assertGreater(len(mondays),1000)
        self.assertTrue((mondays.Date>mondays.lag_date).all())

    def test_sector_level_exposure(self):
        d=self.p.loc[self.p.exposure_matched]
        ranges=d.groupby(['Sector','Date'])[X].agg(['min','max'])
        self.assertLess(float((ranges['max']-ranges['min']).max()),1e-10)

    def test_completed_results_and_fwl(self):
        file=ROOT/'results/publication/analysis_results.json'
        if not file.exists(): self.skipTest('Run publication_analysis.py first')
        r=json.loads(file.read_text())
        s=r['specifications']
        if 'primary' not in s: self.skipTest('Analysis is still running')
        self.assertEqual(s['common_date']['N'],s['common_month']['N'])
        for name,model in s.items():
            if 'fwl_coefficient' in model:
                term=next(iter(model['firm_date']))
                self.assertAlmostEqual(model['fwl_coefficient'],model['firm_date'][term]['Estimate'],places=7)
        self.assertAlmostEqual(s['benchmark_month']['firm_date'][X]['Estimate'],0.0038418,places=6)

if __name__=='__main__': unittest.main(verbosity=2)
