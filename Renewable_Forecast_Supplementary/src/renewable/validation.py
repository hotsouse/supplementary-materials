from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from .models import HYDRO,CAPACITY,VRE,HORIZONS,forecast_series,vre_forecast,valid_diffs

def candidate_backtests(panels):
    rows=[]
    for country,p in panels.items():
        for component in ['hydro_other','solar','wind','capacity_solar','capacity_wind','total']:
            iscap=component.startswith('capacity_')
            column='cap_'+component[9:] if iscap else ('gen_'+component if component in ['solar','wind'] else ('ren' if component=='total' else component))
            s=p[column];last=int(s.last_valid_index())
            models=CAPACITY if iscap else (VRE if component in ['solar','wind'] else (['naive','mean'] if component=='total' else HYDRO))
            for origin in range(2007,last):
                train=s.loc[:origin];scale=valid_diffs(train).abs().mean()
                years=np.arange(origin+1,last+1)
                for model in models:
                    try:
                        if component in ['solar','wind']:
                            pred,_=vre_forecast(panels,country,component,origin,years,model)
                        else: pred=forecast_series(train,model,years)
                    except (ValueError,RuntimeError,np.linalg.LinAlgError) as e:
                        logging.info('Unavailable %s %s %s origin=%s: %s',country,component,model,origin,e)
                        continue
                    for year,f in zip(years,pred):
                        actual=s.get(year,np.nan)
                        if not np.isfinite(actual): continue
                        h=int(year-origin)
                        rows.append(dict(country=country,component=component,model=model,origin=origin,target_year=year,
                            horizon=h,actual=actual,forecast=f,error=f-actual,abs_error=abs(f-actual),
                            squared_error=(f-actual)**2,mase_scale=scale,unit='MW' if iscap else 'GWh',
                            period='recent_2020_2025' if year>=2020 else 'earlier_2008_2019',
                            evaluation_role='candidate_selection_only'))
    return pd.DataFrame(rows)

def select_model(records,country,component,origin,gap=0,candidates=None,default=None):
    """Nested selection with an explicit information cutoff.
    Equal horizon weights, equal errors within each horizon. Common folds only.
    Models within one paired block-bootstrap SE of the winner: simplest wins.
    """
    cutoff=origin-gap
    q=records[(records.country==country)&(records.component==component)&
        (records.target_year<=cutoff)&(records.target_year>cutoff-10)&records.horizon.isin(HORIZONS)]
    priority=candidates if candidates is not None else (HYDRO if component=='hydro_other' else (CAPACITY if component.startswith('capacity_') else VRE))
    default=default or ('mean' if component=='hydro_other' else 'naive')
    if q.empty: return default,dict(selection_cutoff=cutoff,n_selection=0,reason='insufficient_history_simple_default')
    pivot=q.pivot(index=['origin','horizon'],columns='model',values='abs_error')
    # Remove candidates missing >10% of the baseline folds; use shared folds afterwards.
    base= pivot[default].notna() if default in pivot else pivot.notna().any(axis=1)
    eligible=[m for m in priority if m in pivot and pivot.loc[base,m].notna().mean()>=.9]
    common=pivot[eligible].dropna()
    if len(common)<5: return default,dict(selection_cutoff=cutoff,n_selection=len(common),reason='insufficient_common_folds')
    counts=common.groupby(level='horizon').size()
    hs=counts[counts>=3].index
    common=common[common.index.get_level_values('horizon').isin(hs)]
    if not len(common): return default,dict(selection_cutoff=cutoff,n_selection=0,reason='insufficient_horizon_samples')
    scores=common.groupby(level='horizon').mean().mean()
    best=scores.idxmin()
    selected=best;se=0.
    for model in eligible:
        counts=common.groupby(level='horizon').size()
        nh=common.index.get_level_values('horizon').map(counts).to_numpy()
        weights=common.index.get_level_values('origin').nunique()/(len(counts)*nh)
        delta=((common[model]-common[best])*weights).groupby(level='origin').sum().values
        if len(delta)>1:
            rng=np.random.default_rng(217)
            n=len(delta);starts=rng.integers(0,n,size=(500,(n+2)//3))
            idx=((starts[:,:,None]+np.arange(3))%n).reshape(500,-1)[:,:n]
            se=float(np.std(delta[idx].mean(axis=1),ddof=1))
        else:se=0.
        if scores[model]<=scores[best]+se+1e-10:
            selected=model;break
    return selected,dict(selection_cutoff=cutoff,n_selection=len(common),reason='equal_horizon_MAE_one_paired_block_SE',
        raw_winner=best,selected_score=float(scores[selected]),winner_score=float(scores[best]),paired_block_SE=se,
        horizons=';'.join(map(str,hs.tolist())))

def metrics(d):
    e=d.error.to_numpy();den=d.actual.abs().sum();valid=d.mase_scale>1e-12
    return dict(n=len(d),n_origins=d.origin.nunique(),MAE=float(np.mean(abs(e))),RMSE=float(np.sqrt(np.mean(e**2))),
        Bias=float(np.mean(e)),WAPE_pct=float(100*np.sum(abs(e))/den) if den>0 else np.nan,
        MASE=float((d.loc[valid,'abs_error']/d.loc[valid,'mase_scale']).mean()) if valid.any() else np.nan,
        n_MASE=int(valid.sum()),first_target=int(d.target_year.min()),last_target=int(d.target_year.max()))

def summarize(records):
    groups=['country','component','model','horizon','unit','evaluation_role']
    rows=[]
    for key,d in records[records.horizon.isin(HORIZONS)].groupby(groups):
        for period,sub in [('all',d)]+list(d.groupby('period')):
            rows.append(dict(zip(groups,key),period=period,**metrics(sub)))
    return pd.DataFrame(rows)

def interval_score(actual,lo,hi,alpha):
    if lo>hi: raise ValueError('Reversed interval')
    return hi-lo+2/alpha*max(lo-actual,0)+2/alpha*max(actual-hi,0)

def interval_metrics(actual,draws):
    mean=float(np.mean(draws));median=float(np.median(draws));out={}
    wis=.5*abs(actual-median)
    for level in [80,95]:
        alpha=1-level/100;lo,hi=np.quantile(draws,[alpha/2,1-alpha/2])
        score=interval_score(actual,lo,hi,alpha)
        tol=1e-10*max(1,abs(actual)) # floating-point equality for degenerate constant series
        out.update({f'lo{level}':lo,f'hi{level}':hi,f'coverage{level}':float(lo-tol<=actual<=hi+tol),
                    f'width{level}':hi-lo,f'IS{level}':score})
        wis+=alpha/2*score
    out['WIS']=wis/2.5
    return out

def paired_rank_uncertainty(records):
    rows=[]
    for (c,component,h),g in records[records.horizon.isin(HORIZONS)].groupby(['country','component','horizon']):
        p=g.pivot_table(index='origin',columns='model',values='abs_error')
        if 'naive' not in p: continue
        for m in p:
            if m=='naive':continue
            z=p[[m,'naive']].dropna();d=(z[m]-z.naive).values;n=len(d)
            if n<3: continue
            rng=np.random.default_rng(451);block=min(max(h,2),n)
            starts=rng.integers(0,n,(1000,int(np.ceil(n/block))))
            idx=((starts[:,:,None]+np.arange(block))%n).reshape(1000,-1)[:,:n]
            q=np.quantile(d[idx].mean(axis=1),[.025,.975])
            rows.append(dict(country=c,component=component,horizon=h,model=m,n_pairs=n,
                MAE_difference_vs_naive=d.mean(),bootstrap_lo95=q[0],bootstrap_hi95=q[1],block_length=block,
                warning='descriptive; overlapping errors and short history; not a model-selection significance test'))
    return pd.DataFrame(rows)
