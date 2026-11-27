"""Prepare the management view and explicit acceptance ledger from executed data."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from renewable.models import HYDRO
from renewable.data import source_hash

ROOT=Path(__file__).resolve().parents[1]
CASES=['base','commission_at_start','commission_at_end','cf_last3','cf_last10',
    'independent','strong_common_shock','retirement_2pct_net_sensitivity','degradation_0.5pct',
    'capacity_naive','capacity_drift3','capacity_drift5','capacity_damped5_0.8',
    'capacity_damped5_0.9','capacity_damped5_0.98']+['hydro_'+m for m in HYDRO]

def build_management(forecast,sensitivity):
    s=sensitivity[sensitivity.case.isin(CASES)]
    if s.duplicated(['country','year','case']).any():raise ValueError('Duplicate sensitivity')
    envelope=s.groupby(['country','year']).central_GWh.agg(['min','max','count']).reset_index()
    result=forecast[['country','year','status','central_GWh','hydro_other_GWh','solar_GWh','wind_GWh']].merge(
        envelope,on=['country','year'],validate='one_to_one')
    if len(result)!=len(forecast) or not result['count'].eq(len(CASES)).all():
        raise ValueError('Incomplete annual sensitivity envelope')
    result['assumption_low_GWh']=np.minimum(result['min'],result.central_GWh)
    result['assumption_high_GWh']=np.maximum(result['max'],result.central_GWh)
    result['n_assumption_cases']=result['count']
    result['range_interpretation']='range_of_assumption_means_not_probability_interval_not_exhaustive'
    result['use_status']='conditional_research_scenario_not_validated_energy_system_plan'
    return result.drop(columns=['min','max','count'])

def main():
    tab=ROOT/'outputs/tables'
    f=pd.read_csv(tab/'FORECAST_2025_2050_CORRECTED.csv')
    assert len(f)==130 and not f.duplicated(['country','year']).any()
    assert np.isfinite(f.central_GWh).all() and (f.central_GWh>=0).all()
    np.testing.assert_allclose(f.central_GWh,f.hydro_other_GWh+f.solar_GWh+f.wind_GWh,rtol=1e-12)
    manifest=json.loads((ROOT/'outputs/RUN_MANIFEST.json').read_text())
    assert source_hash(ROOT/'data/raw/ELEC-C_20261019-070746.csv')==manifest['source_sha256']
    s=pd.read_csv(tab/'SENSITIVITY_ANALYSIS.csv')
    m=build_management(f,s);m.to_csv(tab/'MANAGEMENT_FORECAST.csv',index=False)
    rows=[
      ('raw_integrity','PASS','Source SHA256 unchanged; legacy preserved','outputs/PACKAGE_INTEGRITY.json'),
      ('forecast_arithmetic','PASS','130 rows; nonnegative; component means reconcile','tests/test_forecast.py'),
      ('calibration_chronology','PASS','Each stored forecast selected at own origin; only target<=T errors','tests/test_release.py'),
      ('AR_parameter_variance','IMPLEMENTED_APPROXIMATION','First-order delta approximation; finite-sample accuracy not guaranteed','src/renewable/uncertainty.py'),
      ('selection_objective','PASS','Generation GWh loss for capacity x CF candidates; target cutoffs enforced','outputs/tables/MODEL_SELECTION.csv'),
      ('universal_accuracy_improvement','NOT_ESTABLISHED','See paired country/horizon comparisons, including losses','outputs/tables/PAIRED_IMPROVEMENTS.csv'),
      ('95pct_empirical_coverage','NOT_VALIDATED','Too few calibration errors; conditional MC quantiles are not validated risk limits','outputs/tables/CALIBRATION_VALIDATION.csv'),
      ('2050_coverage','NOT_IDENTIFIABLE_FROM_HISTORY','No 26-year independent test; scenarios have no probability weights','outputs/tables/MANAGEMENT_FORECAST.csv'),
      ('source_conflicts','OPEN_SOURCE_VERIFICATION','UZ capacity/generation inconsistencies and TM missing solar capacity retained','outputs/tables/DATA_QUALITY_AUDIT.csv'),
      ('real_time_vintages','UNAVAILABLE','Historical publication vintages and lags absent from supplied export','Supplementary_Color_Figure_Methods.docx'),
      ('structural_constraints','OPEN_DATA_DEPENDENCY','Plant pipeline, ages, grid, demand and curtailment needed for a planning model','Supplementary_Color_Figure_Methods.docx'),
    ]
    pd.DataFrame(rows,columns=['criterion','status','evidence','reference']).to_csv(tab/'RELEASE_CHECKLIST.csv',index=False)
    print(m[m.year.isin([2030,2050])][['country','year','central_GWh','assumption_low_GWh','assumption_high_GWh']].to_string(index=False))

if __name__=='__main__':main()
