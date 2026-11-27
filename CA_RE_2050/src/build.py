from pathlib import Path
import sys,json,hashlib,re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from model import load,calculate
T=ROOT/'outputs/tables';F=ROOT/'outputs/figures';T.mkdir(parents=True,exist_ok=True);F.mkdir(parents=True,exist_ok=True)
config=json.loads((ROOT/'data/config.json').read_text())
raw=pd.read_csv(ROOT/'data/raw/ELEC-C_20261019-070746.csv',skiprows=2,na_values='..')
keys=['Country/area','Technology','Data Type','Grid connection','Year']
if raw.duplicated(keys).any():raise ValueError('Duplicate IRENA keys')
if not raw['Grid connection'].eq('All').all():raise ValueError('Grid coverage mismatch')
raw['Electricity statistics']=pd.to_numeric(raw['Electricity statistics'],errors='raise')
cap=raw[raw['Data Type'].eq('Electrical Installed Capacity (MW)')]
hist=raw[raw['Data Type'].eq('Electricity Generation (GWh)')&raw.Technology.eq('Total Renewable')].rename(columns={'Country/area':'country','Year':'year','Electricity statistics':'generation_GWh'})[['country','year','generation_GWh']]
hist.to_csv(T/'history.csv',index=False)
techs={'solar':'Solar photovoltaic','wind':'Onshore wind energy'}
rr=[]
for c in hist.country.unique():
 for tech,label in techs.items():
  s=cap[cap['Country/area'].eq(c)&cap.Technology.eq(label)].set_index('Year')['Electricity statistics'].sort_index()
  if c=='Uzbekistan' and tech=='solar':s.loc[2021]=np.nan
  for start,w in [(config['long_window_start'],'long'),(config['recent_window_start'],'recent')]:
   z=s.loc[start:config['rate_end_year']].dropna()
   span=int(z.index[-1]-z.index[0]) if len(z) else 0
   eligible=len(z)>=config['minimum_rate_observations'] and span>=config['minimum_rate_span_years']
   slope=(z.iloc[-1]-z.iloc[0])/span if eligible else np.nan
   rate=float(slope) if eligible and slope>=0 else np.nan
   rr.append(dict(country=c,technology=tech,window=w,start=int(z.index[0]) if len(z) else np.nan,end=int(z.index[-1]) if len(z) else np.nan,n=len(z),span=span,raw_rate_MW_year=slope,rate_MW_year=rate,status='eligible' if eligible and slope>=0 else 'NOT_ESTIMABLE: insufficient or negative historical slope'))
pd.DataFrame(rr).to_csv(ROOT/'data/deployment_rates.csv',index=False)
from derive_yields import derive
derive()
from derive_projects import derive as derive_projects
derive_projects()
from source_policy import validate as validate_sources
source_check=validate_sources(ROOT)
(ROOT/'outputs/source_policy_check.json').write_text(json.dumps(source_check,indent=2))
config,base,proj,rates,yields=load(ROOT)
# Preserve national reporting scope without importing any excluded publisher.
pd.DataFrame([
 ['Uzbekistan',2025,'large solar and wind',10500,'GWh','N03','included once'],
 ['Uzbekistan',2025,'hydro',6500,'GWh','N03','included once'],
 ['Uzbekistan',2025,'small solar',2000,'GWh','N03','included once'],
 ['Uzbekistan',2025,'earlier green aggregate',16800,'GWh','N04','separate scope stress'],
 ['Kazakhstan',2025,'ministry renewable subset',8621,'GWh','N23','excludes large hydro; not substituted for total renewable'],
 ['Kazakhstan',2025,'ministry wind',5380.02,'GWh','N23','context only; different scope/vintage from IRENA'],
 ['Kazakhstan',2025,'ministry solar',2042.6,'GWh','N23','context only'],
 ['Kazakhstan',2025,'ministry small hydro',1195.9,'GWh','N23','not total national hydro'],
 ['Kyrgyzstan',2025,'large hydro',12900,'GWh','N02','included once'],
 ['Kyrgyzstan',2025,'small hydro',223,'GWh','N02','included once'],
 ['Kyrgyzstan',2025,'mini hydro and other RE',234,'GWh','N02','mixed category retained'],
 ['Tajikistan',2025,'all electricity',23982.6,'GWh','N19','not relabelled renewable'],
],columns=['country','year','reported_category','value','unit','source_ids','treatment']).to_csv(T/'source_harmonization.csv',index=False)
cases=[('P_documented_portfolio',None),('H_long_build_rate','long'),('H_recent_build_rate','recent')]
frames=[]
for name,w in cases:
 d,profile=calculate(config,base,proj,rates,yields,name,w);frames.append(d)
main=pd.concat(frames,ignore_index=True);main.to_csv(T/'diagnostic_historical_build_rates.csv',index=False)
profile.to_csv(T/'project_contributions.csv',index=False)
base.to_csv(T/'model_references.csv',index=False)
# All sensitivity values are read from config. None are probability quantiles.
stress=[]
for name,w in cases:
 tests=[('delay_'+str(v),{'delay':v}) for v in config['stress_delays']]
 tests += [('non_delivery',{'delivery':0.})]
 for v in config['hydro_stress_factors']:tests.append(('hydro_'+str(v),{'hydro_factor':v}))
 for v in config['programme_stress_factors']:tests.append(('programme_'+str(v),{'programme_factor':v}))
 for v in config['baseline_stress_factors']:tests.append(('baseline_'+str(v),{'baseline_factor':v}))
 for v in config['yield_stress_factors']:tests.append(('yield_'+str(v),{'yield_factor':v}))
 tests.append(('reference_service_erosion',{'erosion':config['reference_erosion_stress']}))
 for label,kwargs in tests:
  d,_=calculate(config,base,proj,rates,yields,name,w,**kwargs);d['stress']=label;stress.append(d)
 # An alternative World Bank modelling date, distinct from NDC 2040.
 pp=proj.copy()
 pp.loc[pp.project_id.eq('KG_KAMBARATA'),['first_year','full_year']]=[2035,2037]
 d,_=calculate(config,base,pp,rates,yields,name,w);d['stress']='Kambarata_WB_2035';stress.append(d)
 # Alternative source value; change the actual input table.
 pp=proj.copy();pp.loc[pp.project_id.eq('KG_KAMBARATA'),'annual_GWh']=config['kambarata_alternative_GWh']
 d,_=calculate(config,base,pp,rates,yields,name,w);d['stress']='Kambarata_5600';stress.append(d)
# Local source alternatives are separate one-factor variants, not averaged vintages.
for name,w in cases:
 for value in config['solar_alternative_yields_GWh_MW']:
  yy=yields.copy();yy.loc[yy.country.eq('Uzbekistan')&yy.technology.eq('solar'),'yield_GWh_MW']=value
  d,_=calculate(config,base,proj,rates,yy,name,w);d['stress']='UZ_solar_source_yield_'+str(value);stress.append(d)
# The planned dates for Mirny differ within ministry publications.
for name,w in cases:
 pp=proj.copy();m=pp.project_id.eq('KZ_MIRNY');pp.loc[m,['first_year','full_year','first_year_fraction']]=[2028,2029,.25]
 d,_=calculate(config,base,pp,rates,yields,name,w);d['stress']='Mirny_ministry_2028Q4';stress.append(d)
stress=pd.concat(stress,ignore_index=True);stress.to_csv(T/'diagnostic_portfolio_sensitivity.csv',index=False)
# No claimed 2050 forecast accuracy. Diagnose historical reference rates only.
bt=[]
for c in hist.country.unique():
 for tech,ir in techs.items():
  s=cap[cap['Country/area'].eq(c)&cap.Technology.eq(ir)].set_index('Year')['Electricity statistics'].sort_index()
  if c=='Uzbekistan' and tech=='solar':s.loc[2021]=np.nan
  s=s.dropna()
  for origin in range(2018,2025):
   if origin not in s.index:continue
   for start,w in [(config['long_window_start'],'long'),(config['recent_window_start'],'recent')]:
    tr=s.loc[start:origin]
    if len(tr)<config['minimum_rate_observations'] or tr.index[-1]-tr.index[0]<config['minimum_rate_span_years']:continue
    rate=(tr.iloc[-1]-tr.iloc[0])/(tr.index[-1]-tr.index[0])
    for hor in [1,3,5]:
     target=origin+hor
     if target>2025 or target not in s.index:continue
     for method,pred in [('constant',s.loc[origin]),('net_rate',max(0.,s.loc[origin]+rate*hor))]:
      bt.append([c,tech,w,origin,hor,target,method,s.loc[target],pred,abs(pred-s.loc[target]),(pred-s.loc[target])**2])
bt=pd.DataFrame(bt,columns=['country','technology','window','origin','horizon','target','method','actual_MW','predicted_MW','AE_MW','SE_MW']);bt.to_csv(T/'capacity_hindcasts.csv',index=False)
metrics=bt.groupby(['country','technology','window','method','horizon']).agg(n=('AE_MW','size'),MAE_MW=('AE_MW','mean'),MSE=('SE_MW','mean')).reset_index();metrics['RMSE_MW']=np.sqrt(metrics.pop('MSE'));metrics.to_csv(T/'capacity_diagnostics.csv',index=False)
from report_outputs import write_report_outputs
write_report_outputs(ROOT,hist,main,config,base,proj,rates,yields)
from scenarios import compute_paths
from scenario_report import write_scenarios
portfolio=main.loc[main.scenario.eq('P_documented_portfolio')]
paths,scenario_components,uz_bridge=compute_paths(ROOT,config,base,proj,rates,yields,portfolio,profile,raw)
write_scenarios(ROOT,hist,paths,scenario_components,base)
uz_bridge.to_csv(T/"uzbekistan_2030_capacity_bridge.csv",index=False)
from scenario_sensitivity import run_sensitivity
scenario_stress_rows=run_sensitivity(ROOT,config,base,proj,rates,yields,paths,scenario_components,json.loads((ROOT/"data/scenario_assumptions.json").read_text()))

# Runtime identities use explicit exceptions, not assertions that disappear under -O.
if len(main)!=len(base)*(config['projection_end']-config['projection_start']+1)*3 or main.duplicated(['country','year','scenario']).any():raise ValueError('Coverage failure')
if not np.allclose(main.loc[main.generation_GWh.notna(),'generation_GWh'],main.loc[main.generation_GWh.notna(),['reference_GWh','named_project_GWh','unnamed_programme_GWh']].sum(axis=1)):raise ValueError('Energy identity failure')
(ROOT/'outputs/checks.json').write_text(json.dumps({'version':config['version'],'main_rows':len(paths),'diagnostic_rows':len(main),'stress_rows':scenario_stress_rows,'diagnostic_stress_rows':len(stress),'source_policy':source_check,'project_components':int(proj.included.sum()),'reference_years':base.set_index('country').reference_year.to_dict(),'raw_sha256':hashlib.sha256((ROOT/'data/raw/ELEC-C_20261019-070746.csv').read_bytes()).hexdigest(),'purpose':'conditional documented project scenario; historical benchmarks only where rates estimable, otherwise NA; not probability forecasts'},indent=2))
print(paths[paths.year.eq(2050)][['country','scenario','generation_GWh']].to_string(index=False))
