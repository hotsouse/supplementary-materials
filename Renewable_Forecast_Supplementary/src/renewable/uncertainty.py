from __future__ import annotations
import numpy as np
import pandas as pd
import logging
from scipy.special import expit,logit
from scipy.stats import beta,norm,gamma
from .data import hours_k,truncate
from .models import forecast_series,cf_estimate,cf_records,vre_forecast,valid_diffs,CAPACITY
from .validation import select_model

def make_plan(panels,records,origin,cap_origin=None,gap=0):
    cap_origin=origin if cap_origin is None else cap_origin
    plan={};info=[]
    for country in panels:
        h,meta=select_model(records,country,'hydro_other',origin,gap)
        plan[country]={'hydro_other':h}
        info.append(dict(country=country,component='hydro_other',model=h,origin=origin,**meta))
        for tech in ['solar','wind']:
            # The deliverable predicts GWh, so select the conversion pipeline on
            # its generation errors. Known current capacity may inform the final
            # fit, but cannot supply unknown generation targets for selection.
            m,meta=select_model(records,country,tech,origin,gap,
                candidates=['capacity_'+m for m in CAPACITY],default='capacity_naive')
            plan[country][tech]=m.removeprefix('capacity_')
            info.append(dict(country=country,component='capacity_'+tech,model=plan[country][tech],
                origin=origin,capacity_fit_cutoff=cap_origin,selection_component=tech,
                selection_model=m,selection_unit='GWh',**meta))
    return plan,pd.DataFrame(info)

def innovation_bank(panels,records,plan,origin,cap_origin):
    columns={};ns={}
    for c,p in panels.items():
        for component,model in [('hydro_other',plan[c]['hydro_other']),('capacity_solar',plan[c]['solar']),('capacity_wind',plan[c]['wind'])]:
            cutoff=origin if component=='hydro_other' else cap_origin
            q=records[(records.country==c)&(records.component==component)&(records.model==model)&(records.horizon==1)&(records.target_year<=cutoff)]
            if component=='hydro_other': z=-q.set_index('target_year').error
            else:
                # Capacity trends are ADDITIVE in MW. Relative errors near commissioning
                # from almost zero capacity are unstable and not an appropriate noise scale.
                q=q.sort_values('target_year').tail(5)
                z=pd.Series(q.actual.values-q.forecast.values,index=q.target_year)
            columns[(c,component)]=z
            ns[(c,component)]=len(z)
        for tech in ['solar','wind']:
            cf=cf_records(p,tech,origin,window=100).cf
            # CF levels give weather/measurement scatter; serial/cross dependence estimated below.
            columns[(c,'cf_'+tech)]=cf
            ns[(c,'cf_'+tech)]=len(cf)
    bank=pd.DataFrame(columns).sort_index()
    corr=bank.corr(min_periods=4).fillna(0).values
    np.fill_diagonal(corr,1)
    corr=.5*corr+.5*np.eye(len(corr)) # shrink noisy pairwise estimates toward independence
    vals,vec=np.linalg.eigh(corr);corr=(vec*np.maximum(vals,1e-8))@vec.T
    corr=corr/np.sqrt(np.outer(np.diag(corr),np.diag(corr)))
    return bank,corr,ns

def hydro_variances(series,model,years,error_sd):
    """Conditional process and estimated-parameter variances, in GWh squared.
    Standard mean/RW/drift/OLS formulas; low-order AR uses fitted AR propagation.
    ETS gets an explicitly approximate local-trend variance, tested in outer folds.
    """
    from statsmodels.tsa.arima.model import ARIMA
    import warnings
    s=series.astype(float);v=s.dropna();h=np.asarray(years)-v.index[-1]
    if model.startswith('mean'):
        if model[4:]:v=s.loc[s.index.max()-int(model[4:])+1:].dropna()
        variance=float(v.var(ddof=1)) if len(v)>1 else 0.
        return np.full(len(h),variance),np.full(len(h),variance/max(len(v),1))
    if model in ['naive','drift']:
        d=valid_diffs(s);variance=float(d.var(ddof=1)) if len(d)>1 else 0.
        return variance*h,variance*h*h/max(len(d),1) if model=='drift' else np.zeros(len(h))
    if model=='linear':
        t=v.index.values-v.index[-1];X=np.column_stack([np.ones(len(v)),t])
        b=np.linalg.lstsq(X,v.values,rcond=None)[0];variance=float(np.sum((v.values-X@b)**2)/max(len(v)-2,1))
        xf=np.column_stack([np.ones(len(h)),h]);par=variance*np.sum((xf@np.linalg.pinv(X.T@X))*xf,axis=1)
        return np.full(len(h),variance),par
    if model in ['ar1','ar1trend'] and np.ptp(v.values)>1e-10:
        full=s.reindex(range(int(v.index[0]),int(v.index[-1])+1))
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            fit=ARIMA(full.values,order=(1,0,0),trend='ct' if model=='ar1trend' else 'c').fit()
            for w in ws:logging.warning('AR variance: %s',w.message)
        variance=np.asarray(fit.get_forecast(int(h.max())).var_pred_mean)[h.astype(int)-1]
        if hasattr(fit,'mle_retvals') and not fit.mle_retvals.get('converged',True):
            raise ValueError('AR variance fit did not converge')
        parameter=ar_parameter_variance(fit,h)
        return variance,parameter
    return error_sd**2*h,error_sd**2*h*h/max(len(v),1)

def ar_parameter_variance(fit,horizons):
    """First-order delta approximation J Cov(theta) J', not exact coverage.

    Refilter at perturbed parameters so the fitted state and trend both change.
    Covariance is symmetrized and projected onto the PSD cone for roundoff.
    """
    theta=np.asarray(fit.params,float);cov=np.asarray(fit.cov_params(),float)
    if not np.isfinite(cov).all():raise ValueError('AR parameter covariance is not finite')
    values,vectors=np.linalg.eigh((cov+cov.T)/2)
    if values.min() < -1e-7*max(1.,abs(values).max()):
        logging.warning('AR covariance required PSD projection; min eigenvalue=%g',values.min())
    cov=(vectors*np.maximum(values,0))@vectors.T
    h=np.asarray(horizons,int);jac=np.zeros((len(h),len(theta)))
    for j,value in enumerate(theta):
        step=1e-5*max(1.,abs(value))
        # A variance must stay positive and an AR coefficient stationary.
        name=fit.param_names[j]
        if name=='sigma2':step=min(step,value*.1)
        if name.startswith('ar.'):step=min(step,max(1e-10,(1-abs(value))*.1))
        if step<=0:continue
        plus=theta.copy();minus=theta.copy();plus[j]+=step;minus[j]-=step
        a=np.asarray(fit.model.filter(plus).forecast(int(h.max())))[h-1]
        b=np.asarray(fit.model.filter(minus).forecast(int(h.max())))[h-1]
        jac[:,j]=(a-b)/(2*step)
    variance=np.einsum('ij,jk,ik->i',jac,cov,jac)
    if not np.isfinite(variance).all():raise ValueError('AR delta variance is not finite')
    return np.maximum(variance,0)

def simulate(panels,records,origin,years,plan=None,cap_origin=None,nsim=4000,seed=20261024,
             commission=None,cf_window=5,dependence='estimated',retirement=0.,degradation=0.,
             probability_epsilon=1e-10,cf_filter='physical'):
    """Conditional joint gamma-capacity/lognormal-hydro/physical-beta CF simulation.
    Capacity levels can fall. Zero deterministic capacity remains zero: no rectified noise births.
    Report the mean of THESE paths, never an unrelated deterministic trajectory.
    """
    cap_origin=origin if cap_origin is None else cap_origin
    pp=truncate(panels,origin,cap_origin);years=np.asarray(years,int);H=len(years)
    if not np.array_equal(years,np.arange(origin+1,origin+H+1)): raise ValueError('Consecutive future years required')
    if plan is None:plan,_=make_plan(pp,records,origin,cap_origin)
    bank,corr,ns=innovation_bank(pp,records,plan,origin,cap_origin)
    if dependence=='independent':corr=np.eye(len(corr))
    if dependence=='common':corr=np.ones_like(corr)*.95+np.eye(len(corr))*.05
    rng=np.random.default_rng(seed);D=len(bank.columns)
    root=np.linalg.cholesky(corr)
    z=rng.standard_normal((nsim,H,D))@root.T
    zp=rng.standard_normal((nsim,1,D))@root.T
    rho=[]
    for col in bank:
        x=bank[col];a=pd.concat([x,x.shift(1)],axis=1).dropna()
        r=a.iloc[:,0].corr(a.iloc[:,1]) if len(a)>=5 and (a.std()>1e-12).all() else 0.
        rho.append(float(np.clip(.5*r,-.8,.8)) if np.isfinite(r) else 0.)
    rho=np.asarray(rho) if dependence!='independent' else np.zeros(D)
    for h in range(1,H):z[:,h,:]=rho*z[:,h-1,:]+np.sqrt(1-rho**2)*z[:,h,:]
    draws={};details=[]
    def latent(c,k):
        j=bank.columns.get_loc((c,k));return z[:,:,j],zp[:,:,j],ns[(c,k)]
    for c,p in pp.items():
        country_draw={};model=plan[c]['hydro_other']
        mu=forecast_series(p.hydro_other.loc[:origin],model,years)
        zz,par,n=latent(c,'hydro_other')
        residual=bank[(c,'hydro_other')].dropna()
        sd=float(residual.std(ddof=1)) if len(residual)>1 else 0.
        pv,qv=hydro_variances(p.hydro_other.loc[:origin],model,years,sd)
        total_var=np.maximum(pv+qv,0)
        lv=np.log1p(total_var/np.maximum(mu,1e-12)**2)
        sig=np.sqrt(lv*np.divide(pv,total_var,out=np.zeros_like(lv),where=total_var>0))
        param=np.sqrt(lv*np.divide(qv,total_var,out=np.zeros_like(lv),where=total_var>0))
        country_draw['hydro_other']=mu*np.exp(sig*zz+param*par-.5*(sig**2+param**2))
        details.append(dict(country=c,component='hydro_other',model=model,n_errors=n,sd=sd,cf=np.nan,cf_source='',cf_n=0))
        for tech in ['solar','wind']:
            cap=p[f'cap_{tech}'].loc[:cap_origin]
            if pd.isna(cap.iloc[-1]):
                # Explicit degraded-information fallback, never a fabricated capacity zero.
                g=p[f'gen_{tech}'].loc[:origin].dropna()
                if g.empty: raise ValueError(f'{c}/{tech}: neither generation nor capacity available')
                country_draw[tech]=np.full((nsim,H),g.iloc[-1])
                country_draw['capacity_'+tech]=np.full((nsim,H),np.nan)
                country_draw['cf_'+tech]=np.full((nsim,H),np.nan)
                logging.warning('%s/%s origin %s: missing capacity, generation-naive fallback; uncertainty unidentified',c,tech,origin)
                details.append(dict(country=c,component=tech,model='generation_naive_missing_capacity',n_errors=0,sd=np.nan,cf=np.nan,cf_source='unavailable',cf_n=0))
                continue
            capmodel=plan[c][tech]
            cyears=np.arange(origin,years[-1]+1)
            means=cap.reindex(cyears)
            future=cyears[cyears>cap_origin]
            if len(future):means.loc[future]=forecast_series(cap,capmodel,future)
            # Net historical trends do not identify retirements; nonzero rate is a sensitivity only.
            means.loc[future]*=(1-retirement)**(future-cap_origin)
            zz,par,n=latent(c,'capacity_'+tech)
            vals=bank[(c,'capacity_'+tech)].dropna()
            sd=float(vals.std(ddof=1)) if len(vals)>1 else 0.
            hs=np.maximum(years-cap_origin,0)
            sig=sd*np.sqrt(hs)
            # Uncertain additive trend, only where a trend was estimated.
            ntrend=3 if capmodel=='drift3' else min(max(n,1),5)
            param=sd*hs/np.sqrt(ntrend) if capmodel!='naive' else np.zeros(H)
            variance=sig**2+param**2
            C=np.broadcast_to(means.loc[years].values,(nsim,H)).copy()
            for j,m in enumerate(means.loc[years].values):
                if m>0 and variance[j]>0:
                    u=norm.cdf((sig[j]*zz[:,j]+param[j]*par[:,0])/np.sqrt(variance[j]))
                    C[:,j]=gamma.ppf(np.clip(u,probability_epsilon,1-probability_epsilon),a=m*m/variance[j],scale=variance[j]/m)
            Cprev=np.concatenate([np.full((nsim,1),means.loc[origin]),C[:,:-1]],axis=1)
            bounds={'solar':(.1,.35),'wind':(.15,.55)}[tech] if cf_filter=='legacy' else (0,1)
            cf,sample,source,ncf=cf_estimate(pp,c,tech,origin,cf_window,bounds,20 if cf_filter=='legacy' else 0)
            if not np.isfinite(cf):
                if np.any(C>0): raise ValueError(f'{c}/{tech}: unavailable CF for positive capacity')
                CF=np.zeros_like(C)
            elif cf<=0 or cf>=1:CF=np.full_like(C,cf)
            else:
                var=float(np.var(sample,ddof=1)) if len(sample)>1 else 0.
                zcf,pcf,_=latent(c,'cf_'+tech)
                if var>0:
                    # Physical beta moments; parameter uncertainty added to variance explicitly.
                    var=min(var*(1+1/max(ncf,1)),cf*(1-cf)*.99)
                    k=cf*(1-cf)/var-1
                    CF=beta.ppf(np.clip(norm.cdf((zcf+pcf/np.sqrt(max(ncf,1)))/np.sqrt(1+1/max(ncf,1))),probability_epsilon,1-probability_epsilon),cf*k,(1-cf)*k)
                else: CF=np.full_like(C,cf)
            alpha=rng.uniform(0,1,(nsim,H)) if commission is None else np.full_like(C,commission)
            operating=(1-alpha)*Cprev+alpha*C
            CF*= (1-degradation)**np.maximum(years-cap_origin,0)
            country_draw[tech]=CF*operating*np.array([hours_k(y) for y in years])
            country_draw['capacity_'+tech]=C
            country_draw['cf_'+tech]=CF
            details.append(dict(country=c,component=tech,model=capmodel,n_errors=n,sd=sd,cf=cf,cf_source=source,cf_n=ncf))
        country_draw['total']=sum(country_draw[k] for k in ['hydro_other','solar','wind'])
        for k,v in country_draw.items():
            if k.startswith(('capacity_','cf_')) and np.isnan(v).all():continue
            if not np.isfinite(v).all() or (v<0).any():raise ValueError(f'Nonfinite/negative simulation {c}/{k}')
        draws[c]=country_draw
    return draws,pd.DataFrame(details),pd.DataFrame(corr,index=bank.columns,columns=bank.columns)
