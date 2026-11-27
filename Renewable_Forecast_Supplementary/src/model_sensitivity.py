"""Expose hydro-model structural sensitivity without selecting on future outcomes."""
from pathlib import Path
import numpy as np
import pandas as pd
from renewable.data import load_data
from renewable.models import HYDRO
from renewable.uncertainty import make_plan,simulate

ROOT=Path(__file__).resolve().parents[1]

def main():
    tab=ROOT/'outputs/tables';_,panels,_=load_data(ROOT/'data/raw/ELEC-C_20261019-070746.csv')
    records=pd.read_csv(tab/'CANDIDATE_PREDICTIONS.csv');plan,_=make_plan(panels,records,2024,2025)
    years=np.arange(2025,2051);rows=[]
    for model in HYDRO:
        mp={c:{**p,'hydro_other':model} for c,p in plan.items()}
        sims,_,_=simulate(panels,records,2024,years,mp,cap_origin=2025,nsim=4000)
        for c,d in sims.items():
            for j,y in enumerate(years):
                x=d['total'][:,j]
                rows.append(dict(case='hydro_'+model,country=c,year=y,central_GWh=x.mean(),
                    lo80_GWh=np.quantile(x,.1),hi80_GWh=np.quantile(x,.9),
                    status='unweighted_model_assumption_sensitivity_not_probability_scenario'))
    old=pd.read_csv(tab/'SENSITIVITY_ANALYSIS.csv');old=old[~old.case.str.startswith('hydro_')]
    pd.concat([old,pd.DataFrame(rows)],ignore_index=True).to_csv(tab/'SENSITIVITY_ANALYSIS.csv',index=False)

if __name__=='__main__':main()
