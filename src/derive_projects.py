"""2025 Kazakhstan capacity maturation is derived from the unchanged IRENA export."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def derive():
 p=pd.read_csv(ROOT/'data/project_inputs.csv');raw=pd.read_csv(ROOT/'data/raw/ELEC-C_20261019-070746.csv',skiprows=2,na_values='..');bridge=[]
 for technology,label in [('solar','Solar photovoltaic'),('wind','Onshore wind energy'),('hydro','Renewable hydropower')]:
  z=raw[raw['Country/area'].eq('Kazakhstan')&raw.Technology.eq(label)&raw['Data Type'].eq('Electrical Installed Capacity (MW)')].set_index('Year')['Electricity statistics']
  before,after=float(z.loc[2024]),float(z.loc[2025]);increment=after-before
  if increment<0:raise ValueError('Negative maturation increment needs explicit retirement treatment')
  bridge.append(dict(country='Kazakhstan',technology=technology,capacity_2024_MW=before,capacity_2025_MW=after,net_increment_MW=increment,source_ids='S1'))
  if increment==0:continue
  row=p.iloc[0].to_dict();row.update(project_id='KZ_2025_MATURATION_'+technology.upper(),country='Kazakhstan',technology=technology,capacity_MW=increment,embedded_MW=increment,annual_GWh=float('nan'),embedded_GWh=0,first_year=2026,full_year=2026,first_year_fraction=1,profile='step',energy_method='estimated_from_capacity',included=True,source_ids='S1',status='capacity increment observed in IRENA2025; energy estimated',timing_basis='full annual service in2026; existing2025 capacity is not counted as new2026 build',aliases='IRENA2025 net increment '+technology,delivery_locked=True)
  p=pd.concat([p,pd.DataFrame([row])],ignore_index=True)
 p.to_csv(ROOT/'data/projects.csv',index=False);pd.DataFrame(bridge).to_csv(ROOT/'outputs/tables/KZ_2025_capacity_bridge.csv',index=False)
if __name__=='__main__':derive()
