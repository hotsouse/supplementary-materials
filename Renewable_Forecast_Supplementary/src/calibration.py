"""Chronological residual calibration of already-issued outer predictions.

Each prediction was selected and fitted at its own origin. At origin T, only
errors with observed targets <= T may calibrate a new prediction. No historical
prediction is refitted using a subsequently selected model. This is an adaptive
time-series diagnostic, not exchangeable split conformal inference.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from renewable.models import HORIZONS
from renewable.validation import interval_score

ROOT=Path(__file__).resolve().parents[1]

def calibrate_prediction(history,country,origin,horizon,point,level,actual=np.nan):
    q=history[(history.country==country)&(history.horizon==horizon)&
              (history.target_year<=origin)&(history.origin<origin)].copy()
    if (q.target_year<=q.origin).any():raise ValueError('Invalid historical forecast chronology')
    if q.duplicated(['country','origin','target_year']).any():raise ValueError('Duplicate calibration forecast')
    residual=np.abs(q.actual-q.forecast).dropna().to_numpy();n=len(residual)
    rank=int(np.ceil((n+1)*level/100-1e-12))
    finite=rank<=n and n>0
    radius=float(np.sort(residual)[rank-1]) if finite else np.inf
    lo=max(0.,point-radius);hi=point+radius
    tol=1e-10*max(1.,abs(actual)) if np.isfinite(actual) else 0.
    return dict(country=country,origin=origin,horizon=horizon,target_year=origin+horizon,
        nominal_level=level,n_calibration=n,quantile_rank=rank,
        calibration_start=q.target_year.min() if n else np.nan,
        calibration_end=q.target_year.max() if n else np.nan,
        latest_calibration_prediction_origin=q.origin.max() if n else np.nan,
        point_GWh=point,lo_GWh=lo,hi_GWh=hi,actual_GWh=actual,
        covered=float(lo-tol<=actual<=hi+tol) if finite and np.isfinite(actual) else np.nan,
        interval_score=interval_score(actual,lo,hi,1-level/100) if finite and np.isfinite(actual) else np.nan,
        status='finite_prequential_rank_interval_no_coverage_guarantee' if finite else 'insufficient_history_for_finite_interval',
        estimand='primary_MC_mean_ordinary_forecast_capacity_at_origin',
        selection_rule='each_historical_prediction_selected_at_its_own_origin')

def run():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'outputs');args=parser.parse_args()
    tab=args.output/'tables'
    history=pd.read_csv(tab/'UNCERTAINTY_PREDICTIONS.csv')
    history=history[(history.component=='total')&history.horizon.isin(HORIZONS)]
    rows=[]
    for r in history.sort_values(['origin','country','horizon']).itertuples():
        for level in [80,95]:
            rows.append(calibrate_prediction(history,r.country,r.origin,r.horizon,r.forecast,level,r.actual))
    d=pd.DataFrame(rows);d.to_csv(tab/'CALIBRATION_DIAGNOSTICS.csv',index=False)
    keys=['country','horizon','nominal_level']
    result=d.groupby(keys,as_index=False).agg(n_issued=('point_GWh','size'),
        n_finite_test=('covered','count'),coverage=('covered','mean'),
        mean_interval_score=('interval_score','mean'),max_n_calibration=('n_calibration','max'))
    result['interpretation']='Finite intervals only; no evidence of 26-year or real-time coverage'
    result.to_csv(tab/'CALIBRATION_VALIDATION.csv',index=False)

if __name__=='__main__':run()
