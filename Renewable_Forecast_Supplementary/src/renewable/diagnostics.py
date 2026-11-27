import warnings
import logging
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller,kpss
from statsmodels.stats.diagnostic import acorr_ljungbox,breaks_cusumolsresid
from .models import valid_diffs

def diagnostics(panels,records):
    rows=[]
    for c,p in panels.items():
        for col in ['hydro_other','cap_solar','cap_wind']:
            s=p[col].loc[:2024];v=s.dropna().values
            if len(v)<10 or np.ptp(v)<1e-10:
                rows.append(dict(country=c,component=col,test='not_testable',n=len(v),reason='short or constant series'));continue
            # Tests requiring consecutive values use only the final complete segment.
            if s.isna().any():s=s.loc[s.index[s.isna()].max()+1:]
            v=s.values
            if len(v)<10: continue
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter('always')
                a=adfuller(v,maxlag=1,regression='c',autolag=None)
                k=kpss(v,regression='c',nlags=1)
                t=np.arange(len(v));res=v-np.polyval(np.polyfit(t,v,1),t)
                b=breaks_cusumolsresid(res,ddof=2)
                for w in ws:logging.warning('diagnostics %s %s: %s',c,col,w.message)
            for name,stat,pv in [('ADF_fixed_lag1',a[0],a[1]),('KPSS_fixed_lag1',k[0],k[1]),('CUSUM_linear_residual',b[0],b[1])]:
                rows.append(dict(country=c,component=col,test=name,statistic=stat,p_value=pv,n=len(v),reason='Exploratory, low power, no automatic break-driven deletion'))
        q=records[(records.country==c)&(records.component=='hydro_other')&(records.horizon==1)]
        for m,g in q.groupby('model'):
            e=g.sort_values('origin').error.values
            if len(e)>=8 and np.std(e)>1e-10:
                z=acorr_ljungbox(e,lags=[min(3,len(e)//4)],return_df=True).iloc[0]
                rows.append(dict(country=c,component='hydro_other',model=m,test='Ljung_Box_rolling_errors',statistic=z.lb_stat,p_value=z.lb_pvalue,n=len(e),reason='Forecast errors, not fitted residuals; descriptive'))
    return pd.DataFrame(rows)
