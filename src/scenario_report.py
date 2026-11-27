"""Write the main scenario tables and publication figure."""
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
from matplotlib.lines import Line2D
from figure_style import configure_figures
import numpy as np
from scenarios import SCENARIOS

STYLES = {'BAU': ('#505050', '--'), 'Accelerated': ('#007b78', '-.'),
          'High Ambition': ('#8d3455', '-')}


def write_scenarios(root, history, paths, detail, references):
    tables, figures = root / 'outputs/tables', root / 'outputs/figures'
    paths.to_csv(tables / 'annual_scenarios.csv', index=False)
    paths.loc[paths.year.isin([2030, 2040, 2050])].to_csv(
        tables / 'summary_2030_2040_2050.csv', index=False)
    final = paths.loc[paths.year.eq(paths.year.max())]
    final.to_csv(tables / 'FINAL_2050_TWh_by_scenario.csv', index=False)
    detail.to_csv(tables / 'scenario_contributions.csv', index=False)
    plot_scenarios(history, paths, references, figures)


def plot_scenarios(history, paths, references, figures):
    paths = paths.loc[~paths.country.eq("Turkmenistan")]
    configure_figures()
    fig, axes = plt.subplots(2, 2, figsize=(22, 15), sharex=True, sharey=True)
    fig.subplots_adjust(left=.12, right=.97, bottom=.21, top=.95, wspace=.31, hspace=.34)
    ceiling = np.ceil(paths.generation_GWh.max() / 20000) * 20000
    for ax, (country, group) in zip(axes.flat, paths.groupby('country', sort=False)):
        observed = history.loc[history.country.eq(country)].dropna()
        ax.plot(observed.year, observed.generation_GWh, color='#253b58', lw=2)
        ax.axvline(2025.5, color='#929292', ls=':', lw=1)
        ref = references.loc[references.country.eq(country)].iloc[0]
        if ref.reference_year == 2025:
            ax.scatter(2025, ref.reference_GWh, color='#253b58', facecolors='white', s=38)
        if country == 'Uzbekistan':
            estimate = group.loc[group.year.eq(2026) & group.scenario.eq('BAU'), 'generation_GWh'].item()
            ax.scatter(2026, estimate, color='#253b58', marker='D', s=38, zorder=5)
            group = group[group.year.gt(2026)]
        # Draw the baseline last so it remains visible where paths coincide.
        for case in reversed(SCENARIOS):
            d = group.loc[group.scenario.eq(case)]
            color, style = STYLES[case]
            ax.plot(d.year, d.generation_GWh, color=color, ls=style, lw=2.1)
        ax.set(title=country, xlim=(2000, 2051), ylim=(0, ceiling))
        ax.set_xticks([2000, 2010, 2020, 2030, 2040, 2050])
        ax.tick_params(labelbottom=True, labelleft=True)
        ax.tick_params(axis='x', pad=8)
        ax.tick_params(axis='y', pad=8)
        ax.set_yticks(np.arange(0, ceiling + 1, 20000))
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        ax.grid(axis='y', alpha=.2)
    handles = [Line2D([], [], color='#253b58', lw=2, label='IRENA history through 2024'),
               Line2D([], [], color='#253b58', ls='', marker='o', mfc='white', label='2025 national reference'),
               Line2D([], [], color='#253b58', ls='', marker='D', label='Uzbekistan 2026 estimate')]
    handles.extend(Line2D([], [], color=STYLES[case][0], ls=STYLES[case][1],
                          lw=2.1, label=case) for case in SCENARIOS)
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.53, .018), ncol=3, frameon=False)
    fig.supylabel('Renewable electricity generation (GWh/year)', x=.022)
    fig.supxlabel('Year', x=.55, y=.135)
    fig.savefig(figures / 'Figure_1_RE_2050_three_scenarios.png', dpi=300)
    fig.savefig(figures / 'Figure_1_RE_2050_three_scenarios.pdf', metadata={'CreationDate': None})
    plt.close(fig)
