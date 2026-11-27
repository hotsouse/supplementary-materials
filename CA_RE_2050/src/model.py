"""Pure scenario accounting. Input tables and config are the sole parameter authority."""
from pathlib import Path
import json
import numpy as np
import pandas as pd


def load(root):
 root=Path(root)
 config=json.loads((root/'data/config.json').read_text())
 base=pd.read_csv(root/'data/baselines.csv')
 bridge=pd.read_csv(root/'data/uzbekistan_reference_inputs.csv').set_index('technology')
 bridge['Q4_estimate_GWh']=bridge.oct_2026_GWh.mul(3).fillna(bridge.full_2025_GWh/4)
 bridge['estimate_2026_GWh']=bridge.jan_sep_2026_GWh+bridge.Q4_estimate_GWh
 bridge['reference_GWh']=bridge.estimate_2026_GWh
 bridge.loc['hydro','reference_GWh']=bridge.loc['hydro','full_2025_GWh']
 uz=base.country.eq('Uzbekistan')
 base.loc[uz,'reference_GWh']=bridge.reference_GWh.sum()
 base.loc[uz,'hydro_reference_GWh']=bridge.loc['hydro','reference_GWh']
 base.loc[uz,'first_year_hydro_GWh']=bridge.loc['hydro','estimate_2026_GWh']
 base.loc[uz,'reference_year']=2026
 base.loc[uz,'classification']='partial_year_nowcast_with_normalized_hydro_for_future'
 base.loc[uz,'source_ids']='N03;UZ_OCT'
 base.loc[uz,'scope_note']='2026 VRE nowcast maintained; 2025 hydro reference resumes from 2027; 2026 hydro nowcast is year-specific'

 projects=pd.read_csv(root/'data/projects.csv')
 rates=pd.read_csv(root/'data/deployment_rates.csv')
 yields=pd.read_csv(root/'data/yields.csv')
 if config['projection_end']<config['projection_start'] or not 0<=config['new_capacity_first_year_fraction']<=1:raise ValueError('Invalid calendar or exposure')
 if yields.duplicated(['country','technology']).any() or not np.isfinite(yields.yield_GWh_MW).all() or (yields.yield_GWh_MW<=0).any():raise ValueError('Invalid yields')
 if not np.isfinite(base[['reference_GWh','hydro_reference_GWh']]).all().all() or (base.hydro_reference_GWh>base.reference_GWh).any():raise ValueError('Invalid reference components')
 if (projects.embedded_MW>projects.capacity_MW).any() or not projects.first_year_fraction.between(0,1).all():raise ValueError('Invalid project exposure')
 if not projects.profile.isin(['step','linear']).all():raise ValueError('Unknown project profile')
 if base.country.duplicated().any() or projects.project_id.duplicated().any():raise ValueError('Duplicate input identifiers')
 if not set(projects.country).issubset(set(base.country)):raise ValueError('Unknown country')
 if not projects.included.isin([True,False]).all():raise ValueError('Boolean included field required')
 for col in ['annual_GWh','embedded_GWh','capacity_MW','embedded_MW']:
  if (projects[col].dropna()<0).any():raise ValueError('Negative project parameter '+col)
 if (projects.embedded_GWh>projects.annual_GWh).any():raise ValueError('Output overlap exceeds design output')
 return config,base,projects,rates,yields


def project_profiles(projects,years,yields,delay=0,delivery=1.,yield_factor=1.):
 lookup=yields.set_index(['country','technology']).yield_GWh_MW
 rows=[]
 for p in projects[projects.included].itertuples():
  project_delay=0 if p.delivery_locked else delay
  project_delivery=1. if p.delivery_locked else delivery
  first,full=int(p.first_year)+project_delay,int(p.full_year)+project_delay
  if full<first:raise ValueError('Invalid dates '+p.project_id)
  for year in years:
   if year<first:f=0.
   elif year>=full:f=1.
   elif p.profile=='linear':f=(year-first+1)/(full-first+1)
   else:f=float(p.first_year_fraction)
   annual=p.capacity_MW*lookup.loc[(p.country,p.technology)]*yield_factor if p.energy_method=='estimated_from_capacity' else p.annual_GWh
   net=(annual-p.embedded_GWh)*f*project_delivery
   if not np.isfinite(net) or net<0:raise ValueError('Invalid project yield '+p.project_id)
   capacity_fraction=f if p.profile=='linear' else float(year>=first)
   cap=max(0,p.capacity_MW-p.embedded_MW)*capacity_fraction*project_delivery
   rows.append(dict(country=p.country,technology=p.technology,project_id=p.project_id,year=year,generation_GWh=net,end_capacity_MW=cap,energy_method=p.energy_method))
 return pd.DataFrame(rows)


def calculate(config,base,projects,rates,yields,scenario='portfolio',window=None,delay=0,delivery=1.,yield_factor=1.,hydro_factor=1.,baseline_factor=1.,programme_factor=1.,erosion=0.):
 years=list(range(config['projection_start'],config['projection_end']+1))
 prof=project_profiles(projects,years,yields,delay,delivery,yield_factor)
 lookup=yields.set_index(['country','technology']).yield_GWh_MW
 rows=[]
 for b in base.itertuples():
  # A missing rate cannot be interpreted as 0 MW/year. Exclude the entire
  # historical-benchmark series for that country until BOTH technology rates
  # are observed/estimable. Portfolio is independent of these rates.
  if window:
   required=rates[(rates.country==b.country)&(rates.window==window)&rates.technology.isin(config['programme_technologies'])]
   if len(required)!=len(config['programme_technologies']) or not np.isfinite(required.rate_MW_year).all():
    for year in years:
     rows.append(dict(country=b.country,year=year,scenario=scenario,generation_GWh=np.nan,reference_GWh=np.nan,named_project_GWh=np.nan,unnamed_programme_GWh=np.nan,unnamed_capacity_MW=np.nan,new_unnamed_capacity_MW=np.nan))
    continue
  extra_capacity={t:0. for t in config['programme_technologies']}
  previous_named={t:0. for t in config['programme_technologies']}
  for year in years:
   sub=prof[(prof.country==b.country)&(prof.year==year)]
   named_energy=sub.generation_GWh.sum()
   named_hydro=sub[sub.technology.eq('hydro')].generation_GWh.sum()
   named_energy+=(hydro_factor-1)*named_hydro
   extra_energy=0.;new_build=0.
   for tech in config['programme_technologies']:
    named_cap=sub[sub.technology.eq(tech)].end_capacity_MW.sum()
    new_named=max(0.,named_cap-previous_named[tech]);previous_named[tech]=named_cap
    rate=0.
    if window:
     rr=rates[(rates.country==b.country)&(rates.technology==tech)&(rates.window==window)]
     if len(rr)!=1:raise ValueError('Missing or repeated rate')
     rate=float(rr.rate_MW_year.iloc[0])*programme_factor if year>b.reference_year else 0.
    # The named build is credited to the total annual build benchmark. No full
    # historical programme is blindly stacked on top of those same-year projects.
    unnamed=max(0.,rate-new_named)
    prev=extra_capacity[tech];extra_capacity[tech]+=unnamed
    extra_energy+=(prev+config['new_capacity_first_year_fraction']*unnamed)*lookup.loc[(b.country,tech)]*yield_factor
    new_build+=unnamed
   hydro_reference=b.hydro_reference_GWh
   first_year_hydro=getattr(b,'first_year_hydro_GWh',np.nan)
   if year==b.reference_year and np.isfinite(first_year_hydro):
    hydro_reference=first_year_hydro
   baseline=(b.reference_GWh-b.hydro_reference_GWh+hydro_factor*hydro_reference)*baseline_factor*(1-erosion)**(year-config['projection_start'])
   total=baseline+named_energy+extra_energy
   if not np.isfinite(total) or total<0:raise ValueError('Invalid output')
   rows.append(dict(country=b.country,year=year,scenario=scenario,generation_GWh=total,reference_GWh=baseline,named_project_GWh=named_energy,unnamed_programme_GWh=extra_energy,unnamed_capacity_MW=sum(extra_capacity.values()),new_unnamed_capacity_MW=new_build))
 return pd.DataFrame(rows),prof
