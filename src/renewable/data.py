from __future__ import annotations
import calendar
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd

COUNTRIES = ['Kazakhstan', 'Kyrgyzstan', 'Tajikistan', 'Turkmenistan', 'Uzbekistan']
TECHS = ['Renewable hydropower', 'Mixed hydropower', 'Solar photovoltaic',
         'Solar thermal energy', 'Onshore wind energy', 'Offshore wind energy',
         'Gas biofuels', 'Solid biofuels', 'Liquid biofuels', 'Renewable waste',
         'Geothermal energy', 'Marine energy']
KINDS = {'gen': 'Electricity Generation (GWh)', 'cap': 'Electrical Installed Capacity (MW)'}
TOL = .021  # source rounding, in GWh or MW; not a statistical outlier threshold

def hours_k(year):
    return (8784 if calendar.isleap(int(year)) else 8760) / 1000

def load_data(path: Path):
    raw = pd.read_csv(path, skiprows=2, dtype={'Electricity statistics': str})
    keys = ['Country/area','Technology','Data Type','Grid connection','Year']
    if raw.duplicated(keys).any():
        raise ValueError('Duplicate country/technology/type/grid/year records')
    if set(raw['Country/area']) != set(COUNTRIES) or set(raw['Grid connection']) != {'All'}:
        raise ValueError('Unexpected country or grid coverage')
    if set(raw['Data Type']) != set(KINDS.values()):
        raise ValueError('Unexpected measurement units')
    values = raw['Electricity statistics'].replace('..', np.nan)
    raw['value'] = pd.to_numeric(values, errors='raise')
    if (raw.value.dropna() < 0).any():
        raise ValueError('Negative source observations')
    audit, panels = [], {}
    def log(country, year, tech, kind, rule, value=np.nan, detail='', severity='info'):
        audit.append(dict(country=country,year=year,technology=tech,kind=kind,
                          rule=rule,value=value,detail=detail,severity=severity))
    for country in COUNTRIES:
        d = raw[raw['Country/area'] == country]
        grids = {}
        for kind, name in KINDS.items():
            w = d[d['Data Type']==name].pivot(index='Year', columns='Technology', values='value').sort_index()
            total = w['Total Renewable']
            known = w[TECHS].sum(axis=1,min_count=1)
            residual = total - known
            close = residual.abs() <= TOL
            for year in w.index:
                log(country, year, 'Total Renewable', kind, 'reconciliation', residual.loc[year],
                    'Total minus sum of reported renewable categories; mixed hydro counted separately in this export',
                    'error' if pd.notna(residual.loc[year]) and not close.loc[year] else 'info')
            for tech in TECHS:
                original=w[tech].copy()
                # Infer zero ONLY from same-year nonnegative additive balance.
                # Do not infer absent capacity when same-year positive generation contradicts it.
                missing = w[tech].isna()
                fill = missing & close
                if kind == 'cap':
                    gg = grids['gen'][tech]
                    fill &= ~(gg > TOL)
                for year in w.index[missing]:
                    log(country, year, tech, kind,
                        'zero_inferred_from_closed_balance' if fill.loc[year] else 'missing_retained',
                        detail='Derived working value only; original .. preserved')
                w.loc[fill,tech] = 0.0
                diff = original.diff().abs()
                # Causal flag: current and preceding values only; never mask automatically.
                repeats = (diff <= .011) & (diff.shift(1) <= .011)
                for year in w.index[repeats & original.notna()]:
                    log(country, year, tech, kind, 'repeated_values_retained', w.loc[year,tech],
                        'A repeat is not proof of a placeholder', 'review')
            grids[kind] = w
        p = pd.DataFrame(index=grids['gen'].index)
        p.index.name='year'
        p['ren']=grids['gen']['Total Renewable']
        p['nonren']=grids['gen']['Total Non-Renewable']
        p['cap_ren']=grids['cap']['Total Renewable']
        for kind in KINDS:
            p[f'{kind}_solar'] = grids[kind][['Solar photovoltaic','Solar thermal energy']].sum(axis=1,min_count=2)
            p[f'{kind}_wind'] = grids[kind][['Onshore wind energy','Offshore wind energy']].sum(axis=1,min_count=2)
        p['hydro_other'] = p.ren-p.gen_solar-p.gen_wind
        other=[t for t in TECHS if t not in ['Solar photovoltaic','Solar thermal energy','Onshore wind energy','Offshore wind energy']]
        p['cap_hydro_other'] = grids['cap'][other].sum(axis=1,min_count=len(other))
        # Capacity may be known while historical generation is unavailable (KG/TJ PV).
        for tech in ['solar','wind','hydro_other']:
            g = p.hydro_other if tech=='hydro_other' else p[f'gen_{tech}']
            c = p[f'cap_{tech}']
            avg=(c+c.shift(1))/2
            fac=pd.Series([hours_k(y) for y in p.index],index=p.index)
            cf=g/(avg*fac)
            p[f'cf_{tech}']=cf.where(avg>0)
            for year in p.index[(g>0)&avg.isna()]:
                log(country,year,tech,'gen/cap','average_capacity_unavailable',
                    detail='Cannot estimate annual CF; prior-year or current capacity missing. First source year has no opening capacity.',severity='review')
            for year in p.index[(g>0)&((avg<=0)|(cf>1))]:
                log(country,year,tech,'gen/cap','capacity_factor_inconsistent',cf.loc[year],
                    'Positive generation with zero average capacity, or implied CF > 1; exclude from CF fitting, preserve source', 'error')
            for year in p.index[avg>0]:
                log(country,year,tech,'gen/cap','implied_capacity_factor',cf.loc[year],
                    'Midyear commissioning approximation; gross generation / net capacity convention')
        panels[country]=p
    log('ALL',None,'ALL','metadata','source_status_unknown',detail='Export has no release vintage, URL, or per-cell official/estimated flags. File date is not proof of provenance.',severity='review')
    log('Kazakhstan',2022,'Mixed hydropower','gen','hydro_classification_anomaly',8241.24,
        'Renewable hydropower 900.90 + mixed 8241.24 = 9142.14. No evidence justifies multiplying 900.90 by ten.', 'review')
    return raw, panels, pd.DataFrame(audit)

def truncate(panels, origin, cap_origin=None):
    """An information boundary, including missing-value inference already done year by year."""
    cap_origin = origin if cap_origin is None else cap_origin
    result={}
    for c,p in panels.items():
        q=p.loc[:max(origin,cap_origin)].copy()
        q.loc[q.index>origin,[x for x in q if not x.startswith('cap_')]]=np.nan
        q.loc[q.index>cap_origin,[x for x in q if x.startswith('cap_')]]=np.nan
        result[c]=q
    return result

def source_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
