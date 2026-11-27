from __future__ import annotations
import argparse, json, logging, platform, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd
from renewable.data import load_data,source_hash
from renewable.models import forecast_series,vre_forecast,HORIZONS
from renewable.validation import candidate_backtests,summarize,metrics,interval_metrics,paired_rank_uncertainty
from renewable.uncertainty import make_plan,simulate
from renewable.diagnostics import diagnostics

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'outputs')
    parser.add_argument('--nsim',type=int,default=10000);parser.add_argument('--backtest-nsim',type=int,default=2000)
    parser.add_argument('--skip-legacy',action='store_true');args=parser.parse_args()
    out=args.output;tables=out/'tables';tables.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=out/'fit_log.txt',filemode='w',level=logging.INFO,force=True)
    rawpath=ROOT/'data/raw/ELEC-C_20261019-070746.csv';before=source_hash(rawpath)
    raw,panels,audit=load_data(rawpath);audit.to_csv(tables/'DATA_QUALITY_AUDIT.csv',index=False)
    pd.concat(panels,names=['country']).reset_index().to_csv(tables/'PREPARED_DATA.csv',index=False)
    print('Data checked; fitting all historical candidates',flush=True)
    records=candidate_backtests(panels)
    records.to_csv(tables/'CANDIDATE_PREDICTIONS.csv',index=False)
    summarize(records).to_csv(tables/'MODEL_COMPARISON.csv',index=False)
    paired_rank_uncertainty(records).to_csv(tables/'RANKING_UNCERTAINTY.csv',index=False)
    diagnostics(panels,records).to_csv(tables/'DIAGNOSTICS.csv',index=False)
    print('Candidate comparisons complete; outer rolling evaluation',flush=True)
    outer=[];ivals=[];selection=[];nowcasts=[]
    for T in range(2011,2024):
        years=np.arange(T+1,min(2024,T+10)+1)
        plan,sel=make_plan(panels,records,T);selection.append(sel.assign(stage='outer'))
        sims,_,_=simulate(panels,records,T,years,plan,nsim=args.backtest_nsim,seed=20261024+T)
        for c,p in panels.items():
            for k in ['hydro_other','solar','wind','total']:
                col={'solar':'gen_solar','wind':'gen_wind','total':'ren'}.get(k,k)
                scale=p[col].loc[:T].diff().abs().mean()
                for j,year in enumerate(years):
                    actual=p.loc[year,col]
                    if not np.isfinite(actual):continue
                    ds=sims[c][k][:,j];f=ds.mean()
                    row=dict(country=c,component=k,model='corrected_selected',origin=T,target_year=year,horizon=year-T,
                        actual=actual,forecast=f,error=f-actual,abs_error=abs(f-actual),squared_error=(f-actual)**2,
                        mase_scale=scale,unit='GWh',period='recent_2020_2025' if year>=2020 else 'earlier_2008_2019',
                        evaluation_role='outer_prequential_test')
                    outer.append(row);ivals.append({**row,**interval_metrics(actual,ds)})
        # Nowcast: known end-of-year capacity is allowed ONLY in this separate experiment.
        for c,p in panels.items():
            total=0.;valid=True
            for tech in ['solar','wind']:
                try:f,_=vre_forecast(panels,c,tech,T,[T+1],'capacity_naive',cap_origin=T+1);total+=f[0]
                except ValueError:valid=False
            actual=p.gen_solar.get(T+1,np.nan)+p.gen_wind.get(T+1,np.nan)
            if valid and np.isfinite(actual):
                naive=p.gen_solar.loc[T]+p.gen_wind.loc[T]
                nowcasts.append(dict(country=c,origin=T,target_year=T+1,actual_GWh=actual,forecast_GWh=total,
                    naive_GWh=naive,abs_error=abs(total-actual),naive_abs_error=abs(naive-actual),
                    information_set='generation<=T; capacity<=T+1; source release vintages unavailable'))
        print(f'Outer origin {T} complete',flush=True)
    outer=pd.DataFrame(outer)
    baseline=records[records.model.isin(['naive','mean'])].merge(
        outer[['country','component','origin','target_year']],on=['country','component','origin','target_year'])
    baseline['evaluation_role']='outer_prequential_test'
    outer=pd.concat([outer,baseline],ignore_index=True)
    if not args.skip_legacy:
        legacyfile=tables/'LEGACY_BACKTEST_PREDICTIONS.csv'
        subprocess.run([sys.executable,str(ROOT/'src/legacy_backtest.py'),str(legacyfile)],check=True,stdout=subprocess.DEVNULL)
        outer=pd.concat([outer,pd.read_csv(legacyfile)],ignore_index=True)
    outer.to_csv(tables/'BACKTEST_PREDICTIONS.csv',index=False)
    summarize(outer).to_csv(tables/'BACKTEST_RESULTS.csv',index=False)
    paired_rank_uncertainty(outer).to_csv(tables/'OUTER_RANKING_UNCERTAINTY.csv',index=False)
    pd.DataFrame(nowcasts).to_csv(tables/'NOWCAST_BACKTEST.csv',index=False)
    ivals=pd.DataFrame(ivals);ivals.to_csv(tables/'UNCERTAINTY_PREDICTIONS.csv',index=False)
    urows=[]
    for (c,k,h),d in ivals[ivals.horizon.isin(HORIZONS)].groupby(['country','component','horizon']):
        for period,g in [('all',d)]+list(d.groupby('period')):
            r=dict(country=c,component=k,horizon=h,period=period,n=len(g),WIS=g.WIS.mean(),interval_type='conditional_model_based_unrecalibrated')
            for level in [80,95]:
                coverage=g[f'coverage{level}'].mean();n=len(g);z=1.96
                center=(coverage+z*z/(2*n))/(1+z*z/n);half=z*np.sqrt(coverage*(1-coverage)/n+z*z/(4*n*n))/(1+z*z/n)
                r.update({f'coverage{level}_pct':100*coverage,f'mean_width{level}':g[f'width{level}'].mean(),
                          f'interval_score{level}':g[f'IS{level}'].mean(),f'coverage{level}_Wilson_lo':center-half,f'coverage{level}_Wilson_hi':center+half})
            r['coverage_ci_note']='Descriptive binomial interval; overlapping folds violate independence'
            urows.append(r)
    pd.DataFrame(urows).to_csv(tables/'UNCERTAINTY_VALIDATION.csv',index=False)
    print('Outer evaluation complete; final forecast and sensitivities',flush=True)
    years=np.arange(2025,2051);plan,sel=make_plan(panels,records,2024,2025);selection.append(sel.assign(stage='final'))
    sims,params,corr=simulate(panels,records,2024,years,plan,cap_origin=2025,nsim=args.nsim)
    params.to_csv(tables/'MODEL_PARAMETERS.csv',index=False);corr.to_csv(tables/'INNOVATION_CORRELATION.csv')
    pd.concat(selection).to_csv(tables/'MODEL_SELECTION.csv',index=False)
    forecasts=[]
    for c,d in sims.items():
        for j,year in enumerate(years):
            row=dict(country=c,year=year,status='nowcast_capacity_known' if year==2025 else 'forecast',
                central_estimand='Monte_Carlo_predictive_mean',interval_type='conditional_model_based_not_calibrated_to_2050',
                origin_generation=2024,capacity_information_end=2025,horizon_from_generation_origin=year-2024,
                empirical_95_validated=False,long_term_probability_claim=False,
                central_GWh=d['total'][:,j].mean(),median_GWh=np.median(d['total'][:,j]),
                mc_standard_error_GWh=d['total'][:,j].std(ddof=1)/np.sqrt(args.nsim))
            for k in ['hydro_other','solar','wind']:row[k+'_GWh']=d[k][:,j].mean()
            for tech in ['solar','wind']:
                row['capacity_'+tech+'_MW']=d['capacity_'+tech][:,j].mean()
                row['cf_'+tech]=d['cf_'+tech][:,j].mean()
            for level in [80,95]:
                a=(1-level/100)/2;row[f'lo{level}_GWh'],row[f'hi{level}_GWh']=np.quantile(d['total'][:,j],[a,1-a])
            forecasts.append(row)
    fc=pd.DataFrame(forecasts);fc.to_csv(tables/'FORECAST_2025_2050_CORRECTED.csv',index=False)
    old=pd.read_csv(ROOT/'legacy/outputs/tables/forecast_2025_2050.csv')
    compare=fc[fc.year.isin([2030,2040,2050])].merge(old[['country','year','central_GWh']],on=['country','year'],suffixes=('_corrected','_old'))
    compare['change_GWh']=compare.central_GWh_corrected-compare.central_GWh_old
    compare['change_pct']=100*compare.change_GWh/compare.central_GWh_old
    compare.to_csv(tables/'OLD_VS_CORRECTED.csv',index=False)
    sens=[]
    cases=[('base',{}),('commission_at_start',{'commission':1.}),('commission_at_end',{'commission':0.}),
        ('cf_last3',{'cf_window':3}),('cf_last10',{'cf_window':10}),('independent',{'dependence':'independent'}),
        ('strong_common_shock',{'dependence':'common'}),('retirement_2pct_net_sensitivity',{'retirement':.02}),
        ('degradation_0.5pct',{'degradation':.005})]
    for case,kw in cases+[(f'capacity_{m}',{'capacity_model':m}) for m in ['naive','drift3','drift5','damped5_0.8','damped5_0.9','damped5_0.98']]:
        mp={c:dict(v) for c,v in plan.items()};kw=dict(kw)
        if 'capacity_model' in kw:
            m=kw.pop('capacity_model')
            for c in mp:mp[c].update(solar=m,wind=m)
        dd,_,_=simulate(panels,records,2024,years,mp,cap_origin=2025,nsim=min(4000,args.nsim),**kw)
        for c,d in dd.items():
            for y in years:
                values=d['total'][:,y-2025]
                sens.append(dict(case=case,country=c,year=y,central_GWh=values.mean(),lo80_GWh=np.quantile(values,.1),hi80_GWh=np.quantile(values,.9),
                                 status='unweighted_assumption_sensitivity_not_probability_scenario'))
    pd.DataFrame(sens).to_csv(tables/'SENSITIVITY_ANALYSIS.csv',index=False)
    manifest=dict(source_sha256=before,python=platform.python_version(),nsim=args.nsim,backtest_nsim=args.backtest_nsim,
        random_seed=20261024,raw_rows=len(raw),candidate_rows=len(records),outer_rows=len(outer),
        source_vintage='single supplied export; historical release dates unavailable',
        calibration='Conditional simulation quantiles only. Prequential calibration uses each historical prediction at its own origin; no 95% coverage claim.',
        release_version='2.0',selection_objective='generation_GWh_for_all_components',
        packages={m:__import__(m).__version__ for m in ['numpy','pandas','scipy','statsmodels','matplotlib']})
    assert before==source_hash(rawpath)
    (out/'RUN_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    print(fc[fc.year==2050][['country','central_GWh','lo80_GWh','hi80_GWh']].to_string(index=False),flush=True)
    if out.resolve() == (ROOT/'outputs').resolve():
        subprocess.run([sys.executable, str(ROOT/'src'/'release_summary.py')], cwd=ROOT, check=True)

if __name__=='__main__':main()
