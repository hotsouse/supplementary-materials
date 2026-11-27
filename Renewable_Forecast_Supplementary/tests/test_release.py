import numpy as np
import pandas as pd
import pytest
from calibration import calibrate_prediction
from renewable.models import CAPACITY
from renewable.uncertainty import make_plan,hydro_variances
from release_summary import build_management,CASES

def history():
    return pd.DataFrame(dict(country=['A']*9,origin=np.arange(2000,2009),
        target_year=np.arange(2001,2010),horizon=[1]*9,actual=np.arange(11.,20.),forecast=[10.]*9))

def test_calibration_uses_only_observed_targets():
    a=calibrate_prediction(history(),'A',2004,1,20.,80,actual=24.)
    assert a['n_calibration']==4 and a['quantile_rank']==4
    assert a['lo_GWh']==16. and a['hi_GWh']==24. and a['covered']==1
    assert a['calibration_end']<=2004
    q=history();q.loc[q.target_year>2004,['actual','forecast']]=1e20
    assert a==calibrate_prediction(q,'A',2004,1,20.,80,actual=24.)

def test_calibration_never_calls_unbounded_interval_a_success():
    a=calibrate_prediction(history(),'A',2004,1,20.,95,actual=24.)
    assert np.isinf(a['hi_GWh']) and np.isnan(a['covered'])
    assert np.isnan(a['interval_score']) and a['n_calibration']==4

def test_ten_year_calibration_has_no_early_future_errors():
    q=history();q['horizon']=10;q['target_year']=q.origin+10
    a=calibrate_prediction(q,'A',2009,10,20.,80)
    assert a['n_calibration']==0 and np.isinf(a['hi_GWh'])

def test_finite_95_rank_requires_19_observations():
    q=pd.DataFrame(dict(country=['A']*19,origin=np.arange(1980,1999),
        target_year=np.arange(1981,2000),horizon=[1]*19,actual=np.arange(1.,20.),forecast=[0.]*19))
    assert np.isfinite(calibrate_prediction(q,'A',1999,1,20.,95)['hi_GWh'])
    assert np.isinf(calibrate_prediction(q,'A',1998,1,20.,95)['hi_GWh'])

def test_selection_scores_generation_not_capacity_and_respects_cutoffs(panels,records):
    plan,info=make_plan(panels,records,2024,2025)
    q=info[info.component.str.startswith('capacity_')]
    assert (q.selection_unit=='GWh').all() and (q.selection_cutoff==2024).all()
    assert (q.capacity_fit_cutoff==2025).all()
    altered=records.copy()
    altered.loc[(altered.target_year>2024)|altered.component.str.startswith('capacity_'),
        ['actual','forecast','error','abs_error']]=1e20
    changed,meta=make_plan(panels,altered,2024,2025)
    assert plan==changed
    pd.testing.assert_frame_equal(info,meta)

def test_ar_has_positive_finite_parameter_uncertainty():
    rng=np.random.default_rng(33);x=np.zeros(60);x[0]=100
    for j in range(1,len(x)):x[j]=40+.6*x[j-1]+rng.normal(0,4)
    s=pd.Series(x,index=np.arange(1960,2020))
    process,parameter=hydro_variances(s,'ar1',[2020,2021,2029],1.)
    assert np.isfinite(process).all() and np.isfinite(parameter).all()
    assert (process>0).all() and (parameter>0).all()

def test_management_range_rejects_missing_cases():
    f=pd.DataFrame([dict(country='A',year=2030,status='forecast',central_GWh=100.,hydro_other_GWh=80.,solar_GWh=10.,wind_GWh=10.)])
    s=pd.DataFrame([dict(country='A',year=2030,case=c,central_GWh=90.+i) for i,c in enumerate(CASES)])
    r=build_management(f,s)
    assert r.assumption_low_GWh.iloc[0]<=100<=r.assumption_high_GWh.iloc[0]
    with pytest.raises(ValueError):build_management(f,s.iloc[:-1])

def test_published_calibration_metadata_and_management(root):
    c=pd.read_csv(root/'outputs/tables/CALIBRATION_DIAGNOSTICS.csv')
    q=c[c.n_calibration>0]
    assert (q.calibration_end<=q.origin).all()
    assert (q.latest_calibration_prediction_origin<q.origin).all()
    assert c.loc[np.isinf(c.hi_GWh),'covered'].isna().all()
    m=pd.read_csv(root/'outputs/tables/MANAGEMENT_FORECAST.csv')
    assert len(m)==130 and (m.n_assumption_cases==len(CASES)).all()
    assert (m.assumption_low_GWh<=m.central_GWh).all() and (m.central_GWh<=m.assumption_high_GWh).all()
