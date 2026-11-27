"""Regression checks for scenario anchors and complete annual coverage."""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from scenarios import SCENARIOS, validate_paths


class ScenarioChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tables = ROOT / 'outputs/tables'
        cls.paths = pd.read_csv(tables / 'annual_scenarios.csv')
        cls.detail = pd.read_csv(tables / 'scenario_contributions.csv')
        cls.portfolio = pd.read_csv(tables / 'portfolio_annual_comparison.csv')

    def test_five_countries_three_scenarios_and_bau_reconciliation(self):
        self.assertEqual(len(self.paths), 5 * 3 * 25)
        self.assertEqual(set(self.paths.scenario), set(SCENARIOS))
        self.assertEqual(set(self.paths.year), set(range(2026, 2051)))
        validate_paths(self.paths, self.portfolio)

    def test_uzbekistan_high_2030_matches_policy_anchor(self):
        r = self.paths.query('country == "Uzbekistan" and scenario == "High Ambition" and year == 2030')
        self.assertAlmostEqual(r.generation_GWh.item(), 129000 * .54)

    def test_kambarata_is_shifted_without_adding_full_output_twice(self):
        r = self.detail[self.detail.component.eq('earlier_kambarata_delta')]
        self.assertAlmostEqual(r.loc[r.year.eq(2037), 'increment_GWh'].item(), 6000)
        self.assertAlmostEqual(r.loc[r.year.eq(2050), 'increment_GWh'].item(), 0)

    def test_exported_increments_reconcile(self):
        key = ['country', 'scenario', 'year']
        detail = self.detail.groupby(key).increment_GWh.sum()
        result = self.paths.set_index(key).scenario_increment_GWh
        np.testing.assert_allclose(detail.reindex(result.index, fill_value=0), result)

    def test_uzbek_capacity_bridge_closes_energy_balance(self):
        bridge = pd.read_csv(ROOT / 'outputs/tables/uzbekistan_2030_capacity_bridge.csv')
        np.testing.assert_allclose(bridge.solar_MW * bridge.solar_GWh_per_MW +
                                   bridge.wind_MW * bridge.wind_GWh_per_MW, bridge.gap_GWh)
        mix = bridge.set_index('case').additional_MW
        self.assertAlmostEqual(mix.historical_mix_lower_yield, mix.historical_mix / .8)

    def test_sensitivity_keeps_full_coverage_and_does_not_retarget(self):
        stress = pd.read_csv(ROOT / 'outputs/tables/sensitivity.csv')
        key = ['country', 'year', 'scenario']
        counts = stress.groupby('sensitivity_case').size()
        self.assertEqual(len(counts), 8)
        self.assertTrue(counts.eq(375).all())
        self.assertFalse(stress.duplicated(key + ['sensitivity_case']).any())
        delayed = stress.query('country=="Uzbekistan" and year==2030 and scenario=="High Ambition"')
        self.assertLess(delayed.set_index('sensitivity_case').loc['delivery_delay_3y','generation_GWh'],69660)
        anchored = stress.query('country=="Uzbekistan" and year==2026')
        self.assertTrue(np.allclose(anchored.delta_GWh, 0))

    def test_uzbek_half_delivery_applies_to_capacity_gap_only(self):
        stress = pd.read_csv(ROOT / 'outputs/tables/sensitivity.csv')
        case = stress.query('country=="Uzbekistan" and year==2030 and sensitivity_case=="uz_policy_gap_delivery_50pct"')
        output = case.set_index('scenario').generation_GWh
        self.assertAlmostEqual(output['High Ambition'], (69660 + output.Accelerated)/2)
