"""Old equations at historical origins. Run separately: legacy suppresses warnings globally.
The reference is an adaptation to pure forecasting (no future capacity), not the
leaky published nowcast. All old selection/masking/CF thresholds are preserved.
"""
from pathlib import Path
import sys, importlib.util, functools
import numpy as np
import pandas as pd

def run(output):
    root=Path(__file__).resolve().parents[1]
    sys.argv=[str(root/'legacy/src/forecast_v2.py')]
    spec=importlib.util.spec_from_file_location('legacy_model',root/'legacy/src/forecast_v2.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    original=old.hydro_forecast
    @functools.lru_cache(None)
    def cached(data,model):return original(np.frombuffer(data,dtype=float).copy(),model,26)
    old.hydro_forecast=lambda y,model,H:tuple(x[:H] for x in cached(np.asarray(y,float).tobytes(),model))
    truth=old.load_panel();rows=[];failures=[]
    for T in range(2011,2024):
        old.LAST_OBS=T;old.LAST_CAP=T
        panels=old.load_panel()
        years=np.arange(T+1,min(2024,T+10)+1);H=len(years)
        for c,p in panels.items():
            if p.placeholder_flag.mean()>.8:
                total=np.full(H,p.ren.iloc[-1])
            else:
                y=p.hydro_masked.values
                cv=old.hydro_cv(c,y);model,_=old.choose_hydro_model(cv)
                if not isinstance(model,str):model='naive' # no eligible 3/5/10-year folds at early origins
                mu,_=old.hydro_forecast(y,model,H);total=np.maximum(mu,0)
                for tech in ['solar','wind']:
                    C=p['cap_'+tech]
                    if C.iloc[-1]<.5:continue
                    r=old.cf_estimate(p,tech,T)
                    try:cf=r[0] if r is not None else old.pooled_cf(panels,tech)[0]
                    except ZeroDivisionError:
                        failures.append(dict(country=c,origin=T,technology=tech,reason='Legacy CF pool empty; no future-data fallback allowed'))
                        total[:]=np.nan;break
                    d=C.diff();b=.5*(d.iloc[-3:].mean()+d.iloc[-5:].mean())
                    caps=C.iloc[-1]+np.cumsum(b*.98**np.arange(1,H+1))
                    prev=np.r_[C.iloc[-1],caps[:-1]]
                    total+=cf*(prev+caps)/2*8.76
            for year,value in zip(years,total):
                if not np.isfinite(value):continue
                actual=truth[c].ren.loc[year]
                rows.append(dict(country=c,component='total',model='legacy_chronological',origin=T,target_year=year,horizon=year-T,
                    forecast=value,actual=actual,error=value-actual,abs_error=abs(value-actual),squared_error=(value-actual)**2,
                    mase_scale=truth[c].ren.loc[:T].diff().abs().mean(),unit='GWh',
                    period='recent_2020_2025' if year>=2020 else 'earlier_2008_2019',evaluation_role='outer_prequential_test'))
    pd.DataFrame(rows).to_csv(output,index=False)
    pd.DataFrame(failures).to_csv(Path(output).with_name('LEGACY_UNAVAILABLE.csv'),index=False)

if __name__=='__main__':run(sys.argv[1])
