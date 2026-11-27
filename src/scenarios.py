"""Three nested, conditional renewable-electricity paths built on one project ledger."""
import json
import numpy as np
import pandas as pd
from model import calculate

SCENARIOS = ('BAU', 'Accelerated', 'High Ambition')


def ramp(years, start, full_year):
    """First-year tranche credited in start; full tranche from full_year."""
    return np.clip((years - start + 1) / (full_year - start + 1), 0, 1)


def commissioning(years, first, full):
    return np.where(years < first, 0., np.where(years >= full, 1., .5))


def uzbek_capacity_bridge(inputs, accelerated_gwh, long_rates, local_yields):
    country = 'Uzbekistan'
    gap = max(0., inputs['high_target_total_GWh'] * inputs['high_target_share'] - accelerated_gwh)
    solar = local_yields[country, 'solar']
    wind = local_yields[country, 'wind']
    solar_rate = long_rates[country, 'solar']
    wind_rate = long_rates[country, 'wind']
    solar_share = solar_rate / (solar_rate + wind_rate)
    years = inputs['high_target_year'] - inputs['start_year'] + 1
    rows = []
    for case, share, factor in [('solar_only', 1., 1.), ('wind_only', 0., 1.),
                                ('historical_mix', solar_share, 1.),
                                ('historical_mix_lower_yield', solar_share, .8)]:
        average_yield = factor * (share * solar + (1 - share) * wind)
        mw = gap / average_yield
        tender = inputs['tender_benchmark_MW']
        rows.append(dict(case=case, accelerated_2030_GWh=accelerated_gwh,
                         target_2030_GWh=inputs['high_target_total_GWh'] * inputs['high_target_share'],
                         gap_GWh=gap, solar_capacity_share=share, solar_GWh_per_MW=solar*factor,
                         wind_GWh_per_MW=wind*factor, solar_MW=mw*share, wind_MW=mw*(1-share),
                         additional_MW=mw, average_annual_addition_MW=mw/years,
                         tender_benchmark_MW=tender, tender_upper_fraction_of_gap=tender/mw if mw else np.nan))
    return pd.DataFrame(rows)


def compute_paths(root, config, base, projects, rates, yields, portfolio, profiles, raw):
    assumptions = json.loads((root / 'data/scenario_assumptions.json').read_text())
    local_yields = yields.set_index(['country', 'technology']).yield_GWh_MW
    long_rates = rates.loc[rates.window.eq('long')].set_index(['country', 'technology']).rate_MW_year
    frames, contributions = [], []
    for country, ledger in portfolio.groupby('country', sort=False):
        inputs = assumptions[country]
        ledger = ledger.sort_values('year').reset_index(drop=True)
        years = ledger.year.to_numpy()
        components = {scenario: {} for scenario in SCENARIOS[1:]}
        end_year = config['projection_end']

        def add(scenario, name, output):
            components[scenario][name] = np.broadcast_to(output, years.shape).copy()

        def portfolio_mw(tech, ids=None):
            rows = projects[projects.included & projects.country.eq(country) &
                            projects.technology.eq(tech)]
            if ids is not None:
                rows = rows[rows.project_id.isin(ids)]
            return (rows.capacity_MW - rows.embedded_MW).sum()

        if country == 'Kazakhstan':
            for tech, target in [('solar', inputs['policy_solar_MW']),
                                 ('wind', inputs['policy_MW'] - inputs['policy_solar_MW'])]:
                y = local_yields[country, tech]
                gap = max(0., target - portfolio_mw(tech))
                for case, year_key in [('Accelerated', 'accelerated_policy_year'),
                                       ('High Ambition', 'high_policy_year')]:
                    add(case, 'programme_gap_' + tech, y * gap *
                        ramp(years, inputs['start_year'], inputs[year_key]))
                start = inputs['high_continuation_start_year']
                n = np.maximum(years - start + 1, 0)
                pace = target / (inputs['accelerated_policy_year'] - inputs['policy_pace_base_year'])
                add('Accelerated', 'continuation_' + tech, y * long_rates[country, tech] * n)
                add('High Ambition', 'continuation_' + tech, y * pace * n)

        elif country == 'Kyrgyzstan':
            kazarman = inputs['kazarman_GWh'] * commissioning(
                years, inputs['kazarman_first_year'], inputs['kazarman_full_year'])
            add('Accelerated', 'kazarman', kazarman)
            add('High Ambition', 'kazarman', kazarman)
            for i, stage in enumerate(inputs['kokomeren_stages'], start=1):
                add('High Ambition', f'kokomeren_stage_{i}', stage['GWh'] *
                    commissioning(years, stage['first_year'], stage['first_year'] + 1))
            kambarata = projects.copy()
            cols = ['first_year', 'full_year']
            kambarata.loc[kambarata.project_id.eq('KG_KAMBARATA'), cols] = [
                inputs['high_kambarata_first_year'], inputs['high_kambarata_full_year']]
            changed, _ = calculate(config, base.loc[base.country.eq(country)],
                                   kambarata.loc[kambarata.country.eq(country)], rates, yields)
            add('High Ambition', 'earlier_kambarata_delta',
                changed.generation_GWh.to_numpy() - ledger.generation_GWh.to_numpy())

        elif country == 'Tajikistan':
            gap = max(0., inputs['solar_plan_MW'] - portfolio_mw('solar', ['TJ_SOLAR_500']))
            solar = gap * local_yields[country, 'solar'] * commissioning(
                years, inputs['solar_plan_first_year'], inputs['solar_plan_full_year'])
            add('Accelerated', 'solar_programme_gap', solar)
            add('High Ambition', 'solar_programme_gap', solar)
            ref = base.loc[base.country.eq(country)].iloc[0]
            fossil = raw.loc[raw['Country/area'].eq(country) &
                             raw.Technology.eq('Total Non-Renewable') &
                             raw['Data Type'].eq('Electricity Generation (GWh)') &
                             raw.Year.eq(inputs['nonrenewable_reference_year']),
                             'Electricity statistics'].item()
            hydro = profiles.loc[profiles.country.eq(country) & profiles.technology.eq('hydro')
                                 & profiles.year.eq(end_year), 'generation_GWh'].sum()
            hydro += ref.hydro_reference_GWh
            existing_vre = ledger.generation_GWh.iloc[-1] - hydro + solar[-1]
            share = inputs['high_solar_wind_share']
            target = (hydro + fossil) * share / (1 - share)
            add('High Ambition', 'diversification_gap', max(0., target - existing_vre) *
                ramp(years, inputs['high_start_year'], end_year))

        elif country == 'Turkmenistan':
            unit = inputs['replica_MW'] * local_yields[country, 'solar']
            for case, year_key in [('Accelerated', 'accelerated_full_years'),
                                   ('High Ambition', 'high_full_years')]:
                for full in inputs[year_key]:
                    add(case, f'solar_replica_{full}', unit * commissioning(years, full - 1, full))

        elif country == 'Uzbekistan':
            start = inputs['start_year']
            n = np.maximum(years - start + 1, 0)
            for tech in ('solar', 'wind'):
                # Credit the named additions against the programme once, over its full horizon.
                pace = max(0., long_rates[country, tech] - portfolio_mw(tech) / (end_year - start + 1))
                generation = local_yields[country, tech] * pace * n
                add('Accelerated', 'historical_build_gap_' + tech, generation)
                add('High Ambition', 'historical_build_gap_' + tech, generation)
            target_year = inputs['high_target_year']
            idx = np.flatnonzero(years == target_year).item()
            accelerated_at_target = ledger.generation_GWh.iloc[idx] + sum(
                v[idx] for v in components['Accelerated'].values())
            bridge = uzbek_capacity_bridge(inputs, accelerated_at_target, long_rates, local_yields)
            mix = bridge.set_index('case').loc['historical_mix']
            for tech in ('solar', 'wind'):
                add('High Ambition', 'policy_gap_' + tech,
                    mix[tech + '_MW'] * local_yields[country, tech] * ramp(years, start, target_year))

        for case in SCENARIOS:
            detail = components.get(case, {})
            extra = sum(detail.values(), np.zeros(len(years)))
            result = ledger[['country', 'year', 'reference_GWh', 'named_project_GWh']].copy()
            result['scenario'] = case
            result['scenario_increment_GWh'] = extra
            result['generation_GWh'] = ledger.generation_GWh + extra
            result['generation_TWh'] = result.generation_GWh / 1000
            frames.append(result)
            for name, values in detail.items():
                contributions.append(pd.DataFrame({'country': country, 'year': years,
                    'scenario': case, 'component': name, 'increment_GWh': values}))

    result = pd.concat(frames, ignore_index=True)
    detail = pd.concat(contributions, ignore_index=True)
    validate_paths(result, portfolio)
    return result, detail, bridge


def validate_paths(result, portfolio):
    key = ['country', 'year']
    paths = result.pivot(index=key, columns='scenario', values='generation_GWh')
    reference = portfolio.set_index(key).generation_GWh.reindex(paths.index)
    if not np.isfinite(paths.to_numpy()).all() or not np.allclose(paths.BAU, reference):
        raise ValueError('Missing scenario output or BAU differs from the portfolio')
    if (paths['Accelerated'] < paths.BAU - 1e-8).any() or (
            paths['High Ambition'] < paths['Accelerated'] - 1e-8).any():
        raise ValueError('Scenario ordering is violated')
    parts = result[['reference_GWh', 'named_project_GWh', 'scenario_increment_GWh']].sum(axis=1)
    if not np.allclose(parts, result.generation_GWh):
        raise ValueError('Scenario components do not reconcile')
