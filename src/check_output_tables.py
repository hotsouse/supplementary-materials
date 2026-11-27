"""Generate comparison diagnostics from IRENA-derived forecast outputs."""
from pathlib import Path
import numpy as np
import pandas as pd
from renewable.data import load_data,hours_k

ROOT=Path(__file__).resolve().parents[1]
TAB=ROOT/'outputs/tables'

def main():
    fc=pd.read_csv(TAB/'FORECAST_2025_2050_CORRECTED.csv')
    back=pd.read_csv(TAB/'BACKTEST_PREDICTIONS.csv')
    pairs=[]
    keys=['country','component','origin','target_year','horizon']
    new=back[back.model=='corrected_selected']
    for baseline in ['legacy_chronological','naive','mean']:
        a=new.merge(back[back.model==baseline],on=keys,suffixes=('_new','_baseline'))
        for (c,h),d in a[(a.component=='total')&a.horizon.isin([1,3,5,10])].groupby(['country','horizon']):
            n=d.abs_error_new.mean();b=d.abs_error_baseline.mean()
            pairs.append(dict(country=c,horizon=h,baseline=baseline,n_pairs=len(d),MAE_corrected=n,MAE_baseline=b,
                              improvement_pct=100*(b-n)/b if b>1e-10 else np.nan))
    paired=pd.DataFrame(pairs);paired.to_csv(TAB/'PAIRED_IMPROVEMENTS.csv',index=False)
    _,panels,_=load_data(ROOT/'data/raw/ELEC-C_20261019-070746.csv')
    plaus=[]
    for c,p in panels.items():
        f=fc[fc.country==c]
        for r in f.itertuples():
            hcap=p.cap_hydro_other.loc[2025]
            plaus.append(dict(country=c,year=r.year,renewable_GWh=r.central_GWh,
                ratio_to_reported_2024_total=r.central_GWh/(p.ren.loc[2024]+p.nonren.loc[2024]),
                hydro_CF_if_2025_other_capacity_held=r.hydro_other_GWh/(hcap*hours_k(r.year)),
                solar_MW=r.capacity_solar_MW,wind_MW=r.capacity_wind_MW,
                warning='2024 total and held-2025 hydro capacity are sensitivities, not future ceilings; plant ages/grid limits unavailable'))
    pd.DataFrame(plaus).to_csv(TAB/'PHYSICAL_PLAUSIBILITY.csv',index=False)

if __name__=='__main__':main()
