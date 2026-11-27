from __future__ import annotations
import logging
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from .data import hours_k, truncate

HYDRO = ['mean','naive','mean5','mean10','drift','linear','ar1','ar1trend','ets_damped']
CAPACITY = ['naive','drift3','drift5','damped5_0.8','damped5_0.9','damped5_0.98','combo_0.98','ets_damped']
VRE = ['naive','mean'] + ['capacity_'+m for m in CAPACITY]
HORIZONS=(1,3,5,10)

def valid_diffs(s):
    """Annual increments only: gaps must not turn multi-year changes into annual ones."""
    s=s.sort_index()
    return s.diff().where(s.index.to_series().diff().eq(1)).dropna()

def forecast_series(series, model, years):
    s=series.sort_index().astype(float)
    if not s.notna().any(): raise ValueError('No observations')
    v=s.dropna(); t=v.index.to_numpy(float); y=v.to_numpy(float)
    years=np.asarray(years,int); h=years-t[-1]
    if (h<=0).any(): raise ValueError('Forecast targets must follow last observation')
    if model=='naive': out=np.repeat(y[-1],len(h))
    elif model.startswith('mean'):
        n=int(model[4:]) if model[4:] else len(s)
        out=np.repeat(s.loc[s.index.max()-n+1:].mean(),len(h))
    elif model=='drift': out=y[-1]+(y[-1]-y[0])/(t[-1]-t[0])*h if len(y)>1 else y[-1]+0*h
    elif model=='linear':
        if len(y)<3: raise ValueError('Linear trend requires 3 observations')
        b=np.polyfit(t-t[-1],y,1);out=b[1]+b[0]*h
    elif model.startswith(('drift','damped','combo')):
        d=valid_diffs(s)
        if d.empty: out=np.repeat(y[-1],len(h))
        else:
            if model.startswith('drift'): b=d.loc[d.index>=s.index.max()-int(model[5:])+1].mean();phi=1.
            elif model.startswith('damped'): b=d.loc[d.index>=s.index.max()-4].mean();phi=float(model.split('_')[1])
            else: b=.5*(d.loc[d.index>=s.index.max()-2].mean()+d.loc[d.index>=s.index.max()-4].mean());phi=float(model.split('_')[1])
            if not np.isfinite(b): raise ValueError('No recent consecutive differences')
            out=y[-1]+b*(h if phi==1 else phi*(1-phi**h)/(1-phi))
    elif model in ['ar1','ar1trend','ets_damped']:
        if len(y)<8: raise ValueError('Complex model requires 8 observations')
        # Constant series need no ill-conditioned numerical optimization.
        if np.ptp(y)<1e-10: return np.repeat(y[-1],len(h))
        full=s.reindex(range(int(t[0]),int(t[-1])+1))
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            if model=='ets_damped':
                if full.isna().any(): raise ValueError('ETS disabled with gaps; no interpolation')
                fit=ExponentialSmoothing(full.values,trend='add',damped_trend=True,initialization_method='estimated').fit()
            else:
                fit=ARIMA(full.values,order=(1,0,0),trend='ct' if model=='ar1trend' else 'c').fit()
            for w in ws: logging.warning('%s: %s',model,str(w.message))
            if hasattr(fit,'mle_retvals') and not fit.mle_retvals.get('converged',fit.mle_retvals.get('success',True)):
                raise ValueError('Optimizer did not converge')
        out=np.asarray(fit.forecast(int(h.max())))[h.astype(int)-1]
    else: raise ValueError(model)
    out=np.asarray(out,float)
    if not np.isfinite(out).all(): raise ValueError('Nonfinite forecast')
    # Physical support of a level, not rectification of random annual increments.
    return np.maximum(out,0)

def cf_records(p,tech,origin,window=5,bounds=(0,1),min_capacity=0):
    q=p.loc[:origin]
    cap=q[f'cap_{tech}'];avg=(cap+cap.shift(1))/2
    gen=q[f'gen_{tech}'];energy=avg*np.array([hours_k(y) for y in q.index])
    cf=gen/energy
    good=(avg>0)&(avg>=min_capacity)&cf.between(*bounds)&gen.notna()
    z=pd.DataFrame({'gen':gen,'energy':energy,'cf':cf})[good].tail(window)
    return z

def cf_estimate(panels,country,tech,origin,window=5,bounds=(0,1),min_capacity=0):
    own=cf_records(panels[country],tech,origin,window,bounds,min_capacity)
    if len(own)>=2 and own.gen.sum()>0:
        neff=float(own.energy.sum()**2/(own.energy**2).sum())
        return float(own.gen.sum()/own.energy.sum()), own.cf.values, 'own', neff
    # All pooled observations satisfy the SAME historical cutoff.
    pool=[cf_records(p,tech,origin,window,bounds,min_capacity) for p in panels.values()]
    pool=[p for p in pool if len(p) and p.gen.sum()>0]
    if not pool: return np.nan,np.array([]),'unavailable',0
    num=sum(p.gen.sum() for p in pool);den=sum(p.energy.sum() for p in pool)
    neff=float(den**2/sum((p.energy**2).sum() for p in pool))
    return float(num/den),np.concatenate([p.cf.values for p in pool]),'pooled',neff

def vre_forecast(panels,country,tech,origin,years,model,cap_origin=None,cf_window=5,commission=.5):
    cap_origin=origin if cap_origin is None else cap_origin
    pp=truncate(panels,origin,cap_origin);p=pp[country];years=np.asarray(years)
    if not model.startswith('capacity_'):
        return forecast_series(p[f'gen_{tech}'].loc[:origin],model,years),{}
    cap=p[f'cap_{tech}'].loc[:cap_origin]
    if pd.isna(cap.iloc[-1]): raise ValueError('Missing capacity at origin; not replaced with zero')
    all_years=np.arange(origin,max(years)+1)
    future=all_years[all_years>cap_origin]
    c=cap.reindex(all_years)
    if len(future): c.loc[future]=forecast_series(cap,model[9:],future)
    cf,sample,source,n=cf_estimate(pp,country,tech,origin,cf_window)
    avg=(1-commission)*c.shift(1)+commission*c
    # When every future operating capacity is zero the product is known, even with unknown CF.
    if not np.isfinite(cf):
        if avg.loc[years].eq(0).all(): return np.zeros(len(years)),{'cf':np.nan,'cf_source':source,'cf_n':n,'capacity':c}
        raise ValueError('No historical capacity factor available')
    result=avg.loc[years].values*cf*np.array([hours_k(y) for y in years])
    if not np.isfinite(result).all(): raise ValueError('Missing operating capacity')
    return result,{'cf':cf,'cf_sample':sample,'cf_source':source,'cf_n':n,'capacity':c}
