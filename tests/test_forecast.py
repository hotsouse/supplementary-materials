import hashlib
import numpy as np
import pandas as pd
import pytest
from renewable.data import hours_k,load_data,truncate
from renewable.models import valid_diffs,forecast_series,cf_estimate,vre_forecast
from renewable.uncertainty import make_plan,simulate,hydro_variances
from renewable.validation import interval_score,interval_metrics,metrics,select_model

def test_units_and_leap_year():
    assert hours_k(2025)*100*.25==219
    assert hours_k(2024)==8.784
    assert hours_k(2100)==8.76

def test_consecutive_differences():
    s=pd.Series([5,20,22,np.nan,30,31],index=[2000,2002,2003,2004,2005,2006])
    assert valid_diffs(s).to_dict()=={2003:2,2006:1}

def test_time_index_and_zero_support():
    s=pd.Series([1,2,3],index=[2000,2001,2002])
    assert forecast_series(s,'drift',[2003,2005]).tolist()==[4,6]
    assert forecast_series(s*0,'damped5_0.98',[2003,2004]).tolist()==[0,0]
    with pytest.raises(ValueError):forecast_series(s,'naive',[2001])

def test_declining_capacity():
    s=pd.Series([100,90,80],index=[2020,2021,2022])
    z=forecast_series(s,'drift3',[2023,2040]);assert z[0]<80 and z[1]==0

def test_drift_and_mean_parameter_variance():
    s=pd.Series([1.,2.,4.,7.],index=[2000,2001,2002,2003])
    process,parameter=hydro_variances(s,'drift',[2004,2005],999.)
    np.testing.assert_allclose(process,[1.,2.])
    np.testing.assert_allclose(parameter,[1/3,4/3])
    process,parameter=hydro_variances(s,'mean',[2004,2005],999.)
    np.testing.assert_allclose(process,np.repeat(s.var(),2))
    np.testing.assert_allclose(parameter,np.repeat(s.var()/len(s),2))

def test_source_preserved_and_reconciled(root,panels):
    a = root / 'data/raw/ELEC-C_20261019-070746.csv'
    assert hashlib.sha256(a.read_bytes()).hexdigest() == '2bdad46f9a6b7eb07a5b409c1f8e432ecfebcbc35305f9381c1f7995d120174c'
    for p in panels.values():
        good=p.ren.notna();np.testing.assert_allclose((p.hydro_other+p.gen_solar+p.gen_wind)[good],p.ren[good])
    assert panels['Turkmenistan'].loc[2024,'ren']==3.35
    assert panels['Turkmenistan'].loc[2022,'ren']==3.15

def test_missing_capacity_is_not_zero(panels):
    assert np.isnan(panels['Turkmenistan'].loc[2023,'cap_solar'])
    assert panels['Uzbekistan'].loc[2021,'cf_solar']>1
    mu,_,_,_=cf_estimate(panels,'Uzbekistan','solar',2021)
    assert 0<=mu<=1

def test_cf_formula():
    p=pd.DataFrame({'cap_solar':[100.,100.,100.],'gen_solar':[219.,219.6,219.]},index=[2023,2024,2025])
    m,_,_,_=cf_estimate({'A':p},'A','solar',2025)
    assert m==pytest.approx(.25)

def test_pooled_cf_future_invariance(panels):
    changed={c:p.copy() for c,p in panels.items()}
    for p in changed.values():p.loc[p.index>2018,:]*=1000
    for t in ['solar','wind']:
        a=cf_estimate(panels,'Kyrgyzstan',t,2018)
        b=cf_estimate(changed,'Kyrgyzstan',t,2018)
        assert a[0]==b[0];np.testing.assert_array_equal(a[1],b[1])

def test_selection_future_invariance(records):
    changed=records.copy();changed.loc[changed.target_year>2018,['actual','forecast','error','abs_error']]=1e12
    for c in records.country.unique():
        for component in ['hydro_other','capacity_solar','capacity_wind']:
            assert select_model(records,c,component,2018,gap=0)==select_model(changed,c,component,2018,gap=0)

def test_complete_simulation_future_invariance(panels,records):
    changed={c:p.copy() for c,p in panels.items()}
    for p in changed.values():p.loc[p.index>2018,:]=1e9
    changed_records=records.copy();changed_records.loc[changed_records.target_year>2018,['actual','forecast','error','abs_error']]=1e12
    a,_,_=simulate(panels,records,2018,np.arange(2019,2023),nsim=160,seed=7)
    b,_,_=simulate(changed,changed_records,2018,np.arange(2019,2023),nsim=160,seed=7)
    for c in a:
        for k in a[c]:np.testing.assert_array_equal(a[c][k],b[c][k])

def test_mc_reproducibility_and_reconciliation(panels,records):
    kwargs=dict(origin=2024,years=np.arange(2025,2028),cap_origin=2025,nsim=160,seed=12)
    a,_,_=simulate(panels,records,**kwargs);b,_,_=simulate(panels,records,**kwargs)
    for c in a:
        np.testing.assert_array_equal(a[c]['total'],b[c]['total'])
        np.testing.assert_allclose(a[c]['total'],a[c]['hydro_other']+a[c]['solar']+a[c]['wind'])
        assert np.isfinite(a[c]['total']).all() and (a[c]['total']>=0).all()
        for t in ['solar','wind']:
            assert (a[c]['capacity_'+t]>=0).all()
            assert ((a[c]['cf_'+t]>=0)&(a[c]['cf_'+t]<=1)).all()

def test_no_rectified_noise_growth(panels,records):
    sims,_,_=simulate(panels,records,2018,np.arange(2019,2023),nsim=160,seed=1)
    assert (sims['Kyrgyzstan']['capacity_solar']==0).all()
    assert (sims['Tajikistan']['capacity_solar']==0).all()

def test_coverage_and_score():
    assert interval_score(15,0,10,.2)==60
    x=interval_metrics(5,np.arange(11))
    assert x['coverage80']==1 and x['lo95']<=x['lo80']<=x['hi80']<=x['hi95']
    with pytest.raises(ValueError):interval_score(1,3,2,.2)
    assert interval_metrics(3.15,np.full(10,3.1500000000000004))['coverage95']==1

def test_raw_preparation_is_causal(root,tmp_path,panels):
    source=root/'data/raw/ELEC-C_20261019-070746.csv'
    d=pd.read_csv(source,skiprows=2)
    val=pd.to_numeric(d['Electricity statistics'],errors='coerce');q=(d.Year>2018)&val.notna()
    d.loc[q,'Electricity statistics']=(val[q]*123).astype(str)
    path=tmp_path/'altered.csv'
    path.write_text(source.read_text().splitlines()[0]+'\n\n'+d.to_csv(index=False))
    pp=load_data(path)[1]
    for c in pp:pd.testing.assert_frame_equal(pp[c].loc[:2018],panels[c].loc[:2018])

def test_capacity_nowcast_boundary(panels):
    changed={c:p.copy() for c,p in panels.items()}
    changed['Kazakhstan'].loc[2025,'cap_solar']*=2
    a,_=vre_forecast(panels,'Kazakhstan','solar',2024,[2025],'capacity_naive')
    b,_=vre_forecast(changed,'Kazakhstan','solar',2024,[2025],'capacity_naive')
    np.testing.assert_array_equal(a,b)
    a,_=vre_forecast(panels,'Kazakhstan','solar',2024,[2025],'capacity_naive',cap_origin=2025)
    b,_=vre_forecast(changed,'Kazakhstan','solar',2024,[2025],'capacity_naive',cap_origin=2025)
    assert b[0]>a[0]

def test_output_consistency(root):
    f=pd.read_csv(root/'outputs/tables/FORECAST_2025_2050_CORRECTED.csv')
    assert len(f)==130 and not f.duplicated(['country','year']).any()
    np.testing.assert_allclose(f.central_GWh,f.hydro_other_GWh+f.solar_GWh+f.wind_GWh,rtol=1e-12)
    assert (f.lo95_GWh<=f.lo80_GWh).all() and (f.lo80_GWh<=f.hi80_GWh).all() and (f.hi80_GWh<=f.hi95_GWh).all()
    assert (f[f.year==2025].status=='nowcast_capacity_known').all()

def test_all_selected_models_have_validation(root):
    s=pd.read_csv(root/'outputs/tables/MODEL_SELECTION.csv');m=pd.read_csv(root/'outputs/tables/MODEL_COMPARISON.csv')
    for r in s[s.stage=='final'].itertuples():
        assert ((m.country==r.country)&(m.component==r.component)&(m.model==r.model)).any()
