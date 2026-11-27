"""Publisher restrictions apply to every active source and parameter reference."""
from urllib.parse import urlparse
from pathlib import Path
import json
import pandas as pd

def approved_family(url):
 u=urlparse(str(url));h=(u.hostname or '').lower();path=u.path
 if u.scheme!='https':return None
 if h=='www.unfccc.int' and path=='/sites/default/files/2025-10/NDC3.0_Kyrgyzstan_English_30-09-2025%20%282%29.pdf':return 'Government of the Kyrgyz Republic (NDC depositary)'
 if h=='irena.org' or h.endswith('.irena.org'):return 'IRENA'
 if h=='worldbank.org' or h.endswith('.worldbank.org'):return 'World Bank'
 if h=='iea.org' or h.endswith('.iea.org'):return 'IEA'
 if h=='www.gov.kz' and path=='/org/kaenk/press/news/details/1322353':return 'Ministry Kazakhstan committee'
 if h in ['gov.kz','www.gov.kz'] and (path.startswith('/org/energo/') or path.startswith('/memleket/entities/energo/')):return 'Ministry Kazakhstan'
 if h in ['gov.uz','digital.gov.uz'] and any(path.startswith('/'+lang+'/minenergy/') for lang in ['ru','en','uz','oz']):return 'Ministry Uzbekistan'
 if h in ['minenergy.uz','www.minenergy.uz']:return 'Ministry Uzbekistan'
 if h in ['minenergo.gov.kg','www.minenergo.gov.kg']:return 'Ministry Kyrgyzstan'
 if h in ['mewr.tj','www.mewr.tj']:return 'Ministry Tajikistan'
 if h in ['minenergo.gov.tm','www.minenergo.gov.tm']:return 'Ministry Turkmenistan'
 return None

def validate_source_table(sources):
 if sources.id.duplicated().any():raise ValueError('Duplicate source IDs')
 family=sources.url.map(approved_family)
 if family.isna().any():raise ValueError('Publisher outside user-approved list: '+','.join(sources.loc[family.isna(),'id']))
 return family

def validate(root):
 root=Path(root);s=pd.read_csv(root/'data/evidence/sources.csv');families=validate_source_table(s);ids=set(s.id)
 checked=[]
 for file in ['baselines.csv','uzbekistan_reference_inputs.csv','project_inputs.csv','projects.csv','design_yield_inputs.csv','yields.csv']:
  d=pd.read_csv(root/'data'/file)
  for value in d.source_ids.dropna():
   missing=set(str(value).split(';'))-ids
   if missing:raise ValueError('Unknown source IDs in '+file+':'+','.join(missing))
  checked.append(file)
 assumptions=json.loads((root/'data/scenario_assumptions.json').read_text())
 if any(set(item['sources'])-ids for item in assumptions.values()):raise ValueError('Unknown scenario source ID')
 checked.append('scenario_assumptions.json')
 return {'approved_sources_only':True,'source_count':len(s),'source_families':families.value_counts().to_dict(),'checked_parameter_files':checked}
