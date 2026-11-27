"""Perturb schedules and yields without recalibrating the policy capacity gaps."""
import numpy as np
import pandas as pd
from model import calculate
from scenarios import validate_paths

KEY = ['country', 'year', 'scenario']
HYDRO_EXTRAS = r'^(kazarman|kokomeren_stage_\d+|earlier_kambarata_delta)$'


def run_sensitivity(root, config, base, projects, rates, yields, paths, detail, assumptions):
    limits = config['scenario_sensitivity']
    cases = {'delivery_delay_3y': {'delay': limits['delay_years']},
             'post_milestone_build_50pct': {'continuation': limits['continuation_factor']},
             'uz_policy_gap_delivery_50pct': {'uz_delivery': limits['uzbek_policy_gap_delivery_factor']},
             'combined_delivery_and_output': {'delay': limits['delay_years'],
                 'yield_factor': min(limits['estimated_yield_factors']),
                 'hydro_factor': min(limits['hydro_factors'])}}
    for factor in limits['estimated_yield_factors']:
        cases[f'wind_solar_yield_{factor:g}'] = {'yield_factor': factor}
    for factor in limits['hydro_factors']:
        cases[f'hydro_output_{factor:g}'] = {'hydro_factor': factor}

    reference = paths.set_index(KEY).generation_GWh
    hydro = detail.component.str.match(HYDRO_EXTRAS)
    tables = []
    for label, case in cases.items():
        factor = case.get('yield_factor', 1.)
        hydro_factor = case.get('hydro_factor', 1.)
        delay = case.get('delay', 0)
        yields_case = yields.copy()
        yields_case.loc[yields_case.technology.isin(['solar', 'wind']), 'yield_GWh_MW'] *= factor
        baseline, _ = calculate(config, base, projects, rates, yields_case,
                                delay=delay, hydro_factor=hydro_factor)
        # Preserve the already reported 2026 Uzbekistan nowcast in all counterfactuals.
        fixed = baseline.country.eq('Uzbekistan') & baseline.year.eq(2026)
        fixed_gwh = reference.loc[('Uzbekistan', 2026, 'BAU')]
        baseline.loc[fixed, ['reference_GWh', 'generation_GWh']] = fixed_gwh

        changed = detail.copy()
        changed.loc[hydro, 'increment_GWh'] *= hydro_factor
        changed.loc[~hydro, 'increment_GWh'] *= factor
        if delay:
            changed['year'] += delay
        if 'continuation' in case:
            kz = changed.country.eq('Kazakhstan') & changed.component.str.startswith('continuation_')
            changed.loc[kz, 'increment_GWh'] *= case['continuation']
            uz = changed.country.eq('Uzbekistan') & changed.component.str.startswith('historical_build_gap_')
            cutoff = assumptions['Uzbekistan']['high_target_year']
            idx = ['scenario', 'component']
            at_cutoff = changed.loc[uz & changed.year.eq(cutoff)].set_index(idx).increment_GWh
            post = uz & changed.year.gt(cutoff)
            values = changed.loc[post].set_index(idx).increment_GWh
            anchor = at_cutoff.reindex(values.index).to_numpy()
            changed.loc[post, 'increment_GWh'] = anchor + case['continuation'] * (values.to_numpy() - anchor)
        if 'uz_delivery' in case:
            policy = changed.country.eq('Uzbekistan') & changed.component.str.startswith('policy_gap_')
            changed.loc[policy, 'increment_GWh'] *= case['uz_delivery']

        increments = changed.groupby(KEY).increment_GWh.sum()
        out = paths[KEY].merge(baseline[['country', 'year', 'reference_GWh', 'named_project_GWh']],
                               on=['country', 'year'], validate='many_to_one').set_index(KEY)
        out['scenario_increment_GWh'] = increments.reindex(out.index, fill_value=0.)
        out['generation_GWh'] = out[['reference_GWh', 'named_project_GWh',
                                     'scenario_increment_GWh']].sum(axis=1)
        out['delta_GWh'] = out.generation_GWh - reference
        out['generation_TWh'] = out.generation_GWh / 1000
        out['delta_TWh'] = out.delta_GWh / 1000
        out['sensitivity_case'] = label
        out = out.reset_index()
        validate_paths(out, baseline)
        tables.append(out)

    table = pd.concat(tables, ignore_index=True)
    if len(table) != len(paths) * len(cases) or not np.isfinite(table.generation_GWh).all():
        raise ValueError('Incomplete scenario sensitivity')
    output = root / 'outputs/tables'
    table.to_csv(output / 'sensitivity.csv', index=False)
    table[table.year.isin([2030, 2040, 2050])].to_csv(
        output / 'sensitivity_2030_2040_2050.csv', index=False)
    summary = table.groupby(KEY).generation_TWh.agg(stress_min_TWh='min', stress_max_TWh='max')
    summary = paths[KEY + ['generation_TWh']].merge(summary.reset_index(), on=KEY, validate='one_to_one')
    summary.to_csv(output / 'scenario_sensitivity_envelope.csv', index=False)
    return len(table)
