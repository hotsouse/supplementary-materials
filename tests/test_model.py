"""Input perturbations and accounting regressions, independent of figure styling."""
from pathlib import Path
import sys,unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from model import load,calculate
from source_policy import validate,validate_source_table
class Accounting(unittest.TestCase):
 def setUp(self):self.c,self.b,self.p,self.r,self.y=load(ROOT)
 def calc(self,**kw):return calculate(self.c,self.b,self.p,self.r,self.y,**kw)
 def test_coverage_and_identity(self):
  raw=pd.read_csv(ROOT/'data/raw/ELEC-C_20261019-070746.csv',skiprows=2,na_values='..');hist=raw[raw.Technology.eq('Total Renewable')&raw['Data Type'].eq('Electricity Generation (GWh)')];self.assertEqual(hist[hist.Year.le(2024)]['Electricity statistics'].notna().sum(),125);self.assertTrue(hist[hist.Year.eq(2025)]['Electricity statistics'].isna().all());
  d,_=self.calc();self.assertEqual(len(d),125);self.assertFalse(d.duplicated(['country','year']).any());np.testing.assert_allclose(d.generation_GWh,d.reference_GWh+d.named_project_GWh+d.unnamed_programme_GWh)
 def test_unestimable_rates_are_missing_not_zero(self):
  a,_=self.calc(window='long');b,_=self.calc(window='recent')
  for country in ['Kyrgyzstan','Tajikistan','Turkmenistan']:
   self.assertTrue(a[a.country.eq(country)].generation_GWh.isna().all())
   self.assertTrue(b[b.country.eq(country)].generation_GWh.isna().all())
  portfolio,_=self.calc()
  self.assertTrue(portfolio.generation_GWh.notna().all())
 def test_kambarata_input_changes_output(self):
  a,_=self.calc();self.p.loc[self.p.project_id.eq('KG_KAMBARATA'),'annual_GWh']=5600;b,_=self.calc();ix=a.country.eq('Kyrgyzstan')&a.year.eq(2050);self.assertAlmostEqual(float((a.generation_GWh-b.generation_GWh)[ix].iloc[0]),400)
 def test_capacity_estimate_uses_edited_capacity(self):
  a,_=self.calc();self.p.loc[self.p.project_id.eq('KZ_JAMBYL'),'capacity_MW']+=100;b,_=self.calc();ix=a.country.eq('Kazakhstan')&a.year.eq(2050);yield_=self.y.loc[self.y.country.eq('Kazakhstan')&self.y.technology.eq('wind'),'yield_GWh_MW'].iloc[0];self.assertAlmostEqual(float((b.generation_GWh-a.generation_GWh)[ix].iloc[0]),100*yield_)
 def test_named_projects_count_toward_build_benchmark(self):
  d,prof=self.calc(window='recent');rr=self.r[self.r.country.eq('Kazakhstan')&self.r.window.eq('recent')].set_index('technology').rate_MW_year;previous={'solar':0,'wind':0}
  for row in d[d.country.eq('Kazakhstan')].itertuples():
   pp=prof[prof.country.eq(row.country)&prof.year.eq(row.year)];expected=0
   for tech in previous:
    named=pp[pp.technology.eq(tech)].end_capacity_MW.sum();expected+=max(0,rr[tech]-max(0,named-previous[tech]));previous[tech]=named
   self.assertAlmostEqual(expected,row.new_unnamed_capacity_MW)
 def test_existing_kemin_not_new_capacity(self):
  _,p=self.calc();z=p[p.project_id.eq('KG_KEMIN_MATURATION')];self.assertTrue(z.end_capacity_MW.eq(0).all());self.assertTrue(z.generation_GWh.eq(190.8).all())
 def test_partial_energy_does_not_halve_year_end_capacity(self):
  _,p=self.calc();z=p[p.project_id.eq('KZ_MIRNY')&p.year.eq(2029)].iloc[0];self.assertAlmostEqual(z.end_capacity_MW,1000);self.assertAlmostEqual(z.generation_GWh,2000)
 def test_non_delivery_retains_already_commissioned_assets(self):
  d,prof=self.calc(delivery=0);self.assertTrue(prof[~prof.project_id.isin(self.p[self.p.delivery_locked].project_id)].generation_GWh.eq(0).all());self.assertGreater(d[d.country.eq('Kyrgyzstan')&d.year.eq(2050)].named_project_GWh.iloc[0],0)
 def test_delay_changes_early_output_and_conserves_full_design(self):
  a,_=self.calc();b,_=self.calc(delay=5);self.assertLess(b[b.country.eq('Kyrgyzstan')&b.year.eq(2030)].generation_GWh.iloc[0],a[a.country.eq('Kyrgyzstan')&a.year.eq(2030)].generation_GWh.iloc[0]);np.testing.assert_allclose(a[a.year.eq(2050)].generation_GWh,b[b.year.eq(2050)].generation_GWh)
 def test_renewable_hybrid_excludes_diesel_and_stage_totals(self):
  self.assertAlmostEqual(self.p[self.p.project_id.str.startswith('TM_HYBRID')].capacity_MW.sum(),10);self.assertAlmostEqual(self.p[self.p.project_id.str.startswith('KG_ROX')].capacity_MW.sum(),1900);self.assertAlmostEqual(self.p[self.p.project_id.str.startswith('KG_ROX')].annual_GWh.sum(),3300)
 def test_invalid_design_fails(self):
  self.p.loc[self.p.project_id.eq('KG_KAMBARATA'),'annual_GWh']=-1
  with self.assertRaises(ValueError):self.calc()
 def test_projection_end_is_input(self):
  self.c['projection_end']=2030;d,_=self.calc();self.assertEqual(len(d),25);self.assertEqual(d.year.max(),2030)
 def test_approved_publishers_and_parameter_references(self):
  result=validate(ROOT);self.assertTrue(result['approved_sources_only']);self.assertGreaterEqual(result['source_count'],30)
 def test_source_gate_rejects_unapproved_publisher(self):
  sources=pd.read_csv(ROOT/'data/evidence/sources.csv');sources.loc[0,'url']='https://unapproved.invalid/input'
  with self.assertRaises(ValueError):validate_source_table(sources)
 def test_2025_maturation_is_not_future_commissioning(self):
  _,p=self.calc();z=p[p.project_id.str.startswith('KZ_2025_MATURATION')];self.assertTrue(z.end_capacity_MW.eq(0).all());self.assertGreater(z.generation_GWh.sum(),0)
 def test_removed_component_cannot_silently_remain(self):
  self.assertFalse(self.p.project_id.isin(['KZ_ZHANAOZEN_WIND','UZ_PSKEM','UZ_ARTEMISYA']).any());self.assertEqual(self.p[self.p.project_id.eq('UZ_UPPER_PSKEM')].capacity_MW.iloc[0],160)
 def test_new_reference_and_2026_double_count(self):
  d,p=self.calc()
  uz=d[d.country.eq('Uzbekistan')].set_index('year')
  self.assertAlmostEqual(uz.loc[2026,'generation_GWh'],25143.6)
  self.assertAlmostEqual(uz.loc[2050,'reference_GWh'],23568.5)
  self.assertFalse(p.project_id.eq('UZ_CHARVAK').any())
 def test_kg_toru_stages_are_one_300_mw_project(self):
  self.assertEqual(self.p[self.p.project_id.str.startswith('KG_TORU')].capacity_MW.sum(),300)
if __name__=='__main__':unittest.main(verbosity=2)
