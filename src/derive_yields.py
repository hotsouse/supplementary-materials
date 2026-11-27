"""Derive normal-year yields from supplied raw observations and source design inputs."""
from pathlib import Path
import calendar,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def derive():
 c=json.loads((ROOT/'data/config.json').read_text());raw=pd.read_csv(ROOT/'data/raw/ELEC-C_20261019-070746.csv',skiprows=2,na_values='..');raw['Electricity statistics']=pd.to_numeric(raw['Electricity statistics'])
 obs=[];result={}
 for tech,label in [('solar','Solar photovoltaic'),('wind','Onshore wind energy')]:
  a=raw[raw['Country/area'].eq('Kazakhstan')&raw.Technology.eq(label)]
  def value(kind,year):
   z=a[a['Data Type'].eq(kind)&a.Year.eq(year)]['Electricity statistics'];return float(z.iloc[0]) if len(z)==1 else float('nan')
  numer=denom=0.;n=0
  for y in range(c['CF_year_start'],c['CF_year_end']+1):
   g=value('Electricity Generation (GWh)',y);p=value('Electrical Installed Capacity (MW)',y-1);q=value('Electrical Installed Capacity (MW)',y);h=8784 if calendar.isleap(y) else 8760;exposure=(p+q)/2*h/1000;cf=g/exposure if exposure>0 else float('nan');ok=pd.notna(cf) and 0<=cf<=1
   obs.append(['Kazakhstan',tech,y,g,p,q,h,exposure,cf,ok])
   if ok:numer+=g;denom+=exposure;n+=1
  if n<c['minimum_local_CF_observations']:raise ValueError('Insufficient utilization observations')
  result[tech]=numer/denom*c['normalized_hours']/1000
 pd.DataFrame(obs,columns=['country','technology','year','generation_GWh','previous_MW','end_MW','hours','exposure_GWh_at_CF1','effective_CF','accepted']).to_csv(ROOT/'outputs/tables/yield_observations.csv',index=False)
 design=pd.read_csv(ROOT/'data/design_yield_inputs.csv');out=[]
 countries=pd.read_csv(ROOT/'data/baselines.csv').country
 for country in countries:
  for tech in ['solar','wind']:
   z=design[design.country.eq(country)&design.technology.eq(tech)]
   if len(z):value=z.annual_GWh.sum()/z.capacity_MW.sum();method='capacity-weighted source design output';ids=';'.join(z.source_ids.unique())
   else:value=result[tech];method='national observed IRENA2020-24' if country=='Kazakhstan' else 'explicit Kazakhstan transfer; not a regional estimate';ids='S1'
   out.append([country,tech,value,method,ids])
 kz=raw[raw['Country/area'].eq('Kazakhstan')&raw.Technology.eq('Renewable hydropower')&raw.Year.eq(2024)].set_index('Data Type')['Electricity statistics']
 out.append(['Kazakhstan','hydro',float(kz.loc['Electricity Generation (GWh)'])/float(kz.loc['Electrical Installed Capacity (MW)']),'2024 national hydro yield proxy for2025 capacity maturation; not project design','S1'])
 pd.DataFrame(out,columns=['country','technology','yield_GWh_MW','method','source_ids']).to_csv(ROOT/'data/yields.csv',index=False)
if __name__=='__main__':derive()
