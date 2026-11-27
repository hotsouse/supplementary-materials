"""Comparison tables and a common-scale portfolio figure."""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
from matplotlib.lines import Line2D
from figure_style import configure_figures
from matplotlib.patches import Patch
from model import calculate

PORTFOLIO = 'P_documented_portfolio'
COLORS = dict(zip(['Kazakhstan', 'Kyrgyzstan', 'Tajikistan', 'Turkmenistan', 'Uzbekistan'],
                  ['#2171A6', '#238357', '#99551D', '#8A477F', '#B54742']))
KEY = ['country', 'year']


def write_share_check(root, tables):
    raw = pd.read_csv(root / 'data/raw/ELEC-C_20261019-070746.csv', skiprows=2, na_values='..')
    shares = pd.read_csv(root / 'data/raw/IRENA_RE_share_2000_2025_2026upload.csv', skiprows=2,
                         na_values='..')
    shares.columns = ['country', 'indicator', 'year', 'reported_percent']
    totals = raw[raw.Technology.isin(['Total Renewable', 'Total Non-Renewable'])].pivot(
        index=['Country/area', 'Year', 'Data Type'], columns='Technology',
        values='Electricity statistics').reset_index()
    totals = totals.rename(columns={'Country/area': 'country', 'Year': 'year'})
    totals['indicator'] = totals['Data Type'].map({
        'Electricity Generation (GWh)': 'RE share of electricity generation (%)',
        'Electrical Installed Capacity (MW)': 'RE share of electricity capacity (%)'})
    totals['reconstructed_percent'] = 100 * totals['Total Renewable'] / (
        totals['Total Renewable'] + totals['Total Non-Renewable'])
    check = shares.merge(totals[KEY + ['indicator', 'reconstructed_percent']],
                         on=KEY + ['indicator'], how='left', validate='one_to_one')
    check['delta_percentage_points'] = check.reported_percent - check.reconstructed_percent
    check.to_csv(tables / 'share_crosscheck.csv', index=False)


def write_report_outputs(root, history, main, config, references, projects, rates, yields):
    tables, figures = root / 'outputs/tables', root / 'outputs/figures'
    write_share_check(root, tables)
    old = pd.read_csv(root / 'data/evidence/previous_annual_scenarios.csv')
    old = old.loc[old.scenario.eq(PORTFOLIO), KEY + ['generation_GWh']]
    cases = {'delayed_lower_GWh': dict(delay=3, hydro_factor=.8, yield_factor=.8),
             'higher_output_GWh': dict(hydro_factor=1.2, yield_factor=1.2)}
    report = main.loc[main.scenario.eq(PORTFOLIO), KEY + ['generation_GWh']].copy()
    report = report.merge(old.rename(columns={'generation_GWh': 'previous_GWh'}),
                          on=KEY, validate='one_to_one')
    for column, changes in cases.items():
        alternative, _ = calculate(config, references, projects, rates, yields, **changes)
        report = report.merge(alternative[KEY + ['generation_GWh']].rename(
            columns={'generation_GWh': column}), on=KEY, validate='one_to_one')
    uz_nowcast = report.country.eq('Uzbekistan') & report.year.eq(2026)
    report.loc[uz_nowcast, list(cases)] = np.nan
    report['change_GWh'] = report.generation_GWh - report.previous_GWh
    report['result_type'] = np.where(uz_nowcast, 'partial-year nowcast', 'conditional portfolio')
    for column in list(cases) + ['generation_GWh', 'previous_GWh', 'change_GWh']:
        report[column.replace('_GWh', '_TWh')] = report[column] / 1000
    report.to_csv(tables / 'portfolio_annual_comparison.csv', index=False)
    report[report.year.isin([2030, 2040, 2050])].to_csv(
        tables / 'portfolio_2030_2040_2050.csv', index=False)
    final = main.loc[main.year.eq(2050), ['country', 'scenario', 'generation_GWh']].copy()
    final['generation_TWh'] = final.generation_GWh / 1000
    final['interpretation'] = np.where(final.scenario.eq(PORTFOLIO), 'conditional portfolio',
                                      'historical capacity-build benchmark')
    final.loc[final.generation_GWh.isna(), 'interpretation'] = 'insufficient capacity history'
    final.to_csv(tables / 'diagnostic_2050_historical_build_rates.csv', index=False)
    plot_portfolio(history, report, references, figures)


def plot_portfolio(history, report, references, figures):
    report = report.loc[~report.country.eq("Turkmenistan")]
    configure_figures()
    fig, axes = plt.subplots(2, 2, figsize=(22, 15), sharex=True, sharey=True)
    fig.subplots_adjust(left=.12, right=.97, bottom=.21, top=.95, wspace=.31, hspace=.34)
    ceiling = np.ceil(report.higher_output_GWh.max() / 10000) * 10000
    for ax, country in zip(axes.flat, report.country.unique()):
        color = COLORS[country]
        observed = history.loc[history.country.eq(country)].dropna()
        model = report.loc[report.country.eq(country)]
        ref = references.loc[references.country.eq(country)].iloc[0]
        ax.set(title=country, xlim=(2000, 2051), ylim=(0, ceiling))
        ax.set_xticks([2000, 2010, 2020, 2030, 2040, 2050])
        ax.tick_params(labelbottom=True, labelleft=True)
        ax.tick_params(axis='x', pad=8)
        ax.tick_params(axis='y', pad=8)
        ax.set_yticks(np.arange(0, ceiling + 1, 10000))
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        ax.grid(axis='y', alpha=.2)
        ax.plot(observed.year, observed.generation_GWh, color='#343434', lw=1.8)
        ax.axvline(2025.5, color='#929292', ls=':', lw=1)
        scenario = model.loc[model.result_type.eq('conditional portfolio')]
        ax.fill_between(scenario.year, scenario.delayed_lower_GWh, scenario.higher_output_GWh,
                        color=color, alpha=.17, linewidth=0)
        ax.plot(scenario.year, scenario.generation_GWh, color=color, lw=2.5)
        if country == 'Uzbekistan':
            point = model.loc[model.year.eq(2026)].iloc[0]
            ax.scatter(point.year, point.generation_GWh, color=color, marker='D', s=42, zorder=5)
        elif ref.reference_year == 2025:
            ax.scatter(ref.reference_year, ref.reference_GWh, facecolor='white',
                       edgecolor='#343434', s=45, zorder=5)
    fig.supylabel('Renewable electricity generation (GWh/year)', x=.022)
    fig.supxlabel('Year', x=.55, y=.135)
    fig.legend(handles=[
        Line2D([], [], color='#343434', label='IRENA history through 2024'),
        Line2D([], [], marker='o', mfc='white', mec='#343434', ls='', label='2025 national reference'),
        Line2D([], [], marker='D', color='#B54742', ls='', label='Uzbekistan 2026 estimate'),
        Line2D([], [], color='#2171A6', lw=2.5, label='BAU project portfolio'),
        Patch(facecolor='#2171A6', alpha=.17, label='Timing and output sensitivity')],
        loc='lower center', bbox_to_anchor=(.53, .018), ncol=3, frameon=False)
    fig.savefig(figures / 'Figure_S1_RE_2050_portfolio.png', dpi=300)
    fig.savefig(figures / 'Figure_S1_RE_2050_portfolio.pdf', metadata={'CreationDate': None})
    plt.close(fig)
