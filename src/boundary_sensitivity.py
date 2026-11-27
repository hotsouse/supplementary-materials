"""Explicit checks of numerical clipping and legacy CF acceptance thresholds."""
from pathlib import Path
import numpy as np
import pandas as pd
from renewable.data import load_data
from renewable.uncertainty import make_plan,simulate

ROOT=Path(__file__).resolve().parents[1]

def main():
    _,panels,_=load_data(ROOT/'data/raw/ELEC-C_20261019-070746.csv')
    tables=ROOT/'outputs/tables';records=pd.read_csv(tables/'CANDIDATE_PREDICTIONS.csv')
    plan,_=make_plan(panels,records,2024,2025);years=np.arange(2025,2051)
    rows=[];reference=None
    for case,kw in [('base',{}),('numerical_clip_1e-6',{'probability_epsilon':1e-6}),
                    ('numerical_clip_1e-12',{'probability_epsilon':1e-12}),
                    ('legacy_CF_range_and_20MW',{'cf_filter':'legacy'}),('fixed_midyear_commission',{'commission':.5})]:
        draws,_,_=simulate(panels,records,2024,years,plan,cap_origin=2025,nsim=4000,**kw)
        if reference is None:reference=draws
        for c,d in draws.items():
            for j,y in enumerate(years):
                x=d['total'][:,j];ref=reference[c]['total'][:,j]
                rows.append(dict(case=case,country=c,year=y,central_GWh=x.mean(),
                    lo80_GWh=np.quantile(x,.1),hi80_GWh=np.quantile(x,.9),
                    delta_mean_vs_same_seed_base_GWh=x.mean()-ref.mean(),
                    max_draw_difference_GWh=np.max(np.abs(x-ref)),status='unweighted_assumption_sensitivity'))
    d=pd.DataFrame(rows);d.to_csv(tables/'BOUNDARY_SENSITIVITY.csv',index=False)
    old=pd.read_csv(tables/'SENSITIVITY_ANALYSIS.csv')
    names=set(d.case)-{'base'};old=old[~old.case.isin(names)]
    cols=['case','country','year','central_GWh','lo80_GWh','hi80_GWh','status']
    pd.concat([old,d[(d.case!='base')&d.year.isin([2030,2040,2050])][cols]],ignore_index=True).to_csv(tables/'SENSITIVITY_ANALYSIS.csv',index=False)

if __name__=='__main__':main()
