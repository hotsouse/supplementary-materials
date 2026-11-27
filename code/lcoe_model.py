from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


BASE = Path(__file__).resolve().parents[1]
INPUTS = BASE / "data" / "inputs" / "lcoe_model_inputs.csv"
PROCESSED = BASE / "data" / "processed"
FIGURES = BASE / "outputs" / "figures"
N_DRAWS = 10_000
TECHNOLOGY_ORDER = ["Solar_PV", "Onshore_Wind"]
COLORS = {"Solar_PV": "#0072B2", "Onshore_Wind": "#D55E00"}


def calculate_lcoe(capex, opex, capacity_factor, discount, lifetime, degradation):
    discounted_cost = capex
    discounted_generation = 0.0
    for year in range(1, lifetime + 1):
        generation = 8760 * capacity_factor * ((1 - degradation) ** (year - 1))
        discounted_cost += opex / ((1 + discount) ** year)
        discounted_generation += generation / ((1 + discount) ** year)
    return discounted_cost / discounted_generation * 1000


def simulate_lcoe(inputs, n=N_DRAWS):
    rng = np.random.default_rng(int(inputs["MC_Seed"]))
    cap_p5 = inputs["CAPEX_P05_USD_kW"]
    cap_p95 = inputs["CAPEX_P95_USD_kW"]
    cf_p5 = inputs["Capacity_Factor_P05"]
    cf_p95 = inputs["Capacity_Factor_P95"]
    z05, z95 = -1.6448536269514722, 1.6448536269514722

    mu_cap = (np.log(cap_p5) * z95 - np.log(cap_p95) * z05) / (z95 - z05)
    sigma_cap = (np.log(cap_p95) - np.log(cap_p5)) / (z95 - z05)
    capex = rng.lognormal(mu_cap, sigma_cap, n)
    mean_cf = (cf_p5 + cf_p95) / 2
    sigma_cf = (cf_p95 - cf_p5) / (z95 - z05)
    capacity_factor = np.clip(rng.normal(mean_cf, sigma_cf, n), 0.05, 0.70)
    opex = rng.uniform(
        0.75 * inputs["OPEX_USD_kW_yr"],
        1.25 * inputs["OPEX_USD_kW_yr"],
        n,
    )
    wacc = rng.uniform(0.04, 0.12, n)
    values = np.fromiter(
        (
            calculate_lcoe(cap, op, cf, rate, int(inputs["Lifetime_yr"]), inputs["Degradation"])
            for cap, op, cf, rate in zip(capex, opex, capacity_factor, wacc)
        ),
        dtype=float,
        count=n,
    )
    return pd.DataFrame(
        {"LCOE_USD_MWh": values, "Technology": inputs["Technology"]}
    )


def create_figure(
    inputs,
    summaries,
    font_size=25,
    png_filenames=("Figure_5_modelled_LCOE.png",),
    save_pdf=True,
):
    distributions = [
        summaries.loc[
            summaries["Technology"].eq(technology), "LCOE_USD_MWh"
        ].to_numpy()
        for technology in TECHNOLOGY_ORDER
    ]
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = [COLORS[technology] for technology in TECHNOLOGY_ORDER]
    positions = np.arange(len(TECHNOLOGY_ORDER))

    boxes = ax.boxplot(
        distributions,
        vert=False,
        positions=positions,
        widths=0.38,
        whis=(5, 95),
        showfliers=False,
        patch_artist=True,
        medianprops={"color": "black", "linewidth": 1.6},
        whiskerprops={"color": "0.2", "linewidth": 2.0},
        capprops={"color": "0.2", "linewidth": 2.0},
    )
    for index, (box, color) in enumerate(zip(boxes["boxes"], colors)):
        box.set_facecolor(color)
        box.set_alpha(0.32)
        box.set_edgecolor(color)
        box.set_linewidth(1.5)
        for whisker in boxes["whiskers"][2 * index:2 * index + 2]:
            whisker.set_color(color)
            whisker.set_linewidth(2.0)
        for cap in boxes["caps"][2 * index:2 * index + 2]:
            cap.set_color(color)
            cap.set_linewidth(2.0)

    input_by_technology = inputs.set_index("Technology")
    summary_by_technology = summaries.groupby("Technology")["LCOE_USD_MWh"].mean()
    for position, technology, color in zip(positions, TECHNOLOGY_ORDER, colors):
        ax.plot(
            summary_by_technology[technology],
            position,
            "D",
            color="white",
            markersize=7,
            markeredgecolor=color,
            markeredgewidth=1.6,
            zorder=3,
        )
        benchmark = input_by_technology.loc[
            technology, "IRENA_2024_Global_LCOE_USD_MWh"
        ]
        ax.vlines(
            benchmark,
            position - 0.25,
            position + 0.25,
            color=color,
            linestyle=(0, (3, 2)),
            linewidth=1.8,
            zorder=2,
        )

    ax.set_yticks(positions)
    ax.set_yticklabels(["Solar PV", "Onshore wind"])
    ax.set_xlabel(
        "LCOE (USD/MWh)",
        labelpad=12,
        fontsize=font_size,
        fontfamily="Times New Roman",
        fontweight="bold",
    )
    low = min(np.percentile(values, 5) for values in distributions)
    high = max(np.percentile(values, 95) for values in distributions)
    ax.set_xlim(max(0, np.floor((low - 10) / 10) * 10), high + 15)
    ax.tick_params(axis="both", labelsize=font_size, width=0.5, length=3)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontfamily("Times New Roman")
        label.set_fontweight("bold")
    ax.xaxis.label.set_fontfamily("Times New Roman")
    ax.xaxis.label.set_fontweight("bold")
    for spine in ax.spines.values():
        spine.set_linewidth(0.6)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.grid(False, axis="y")
    ax.grid(True, axis="x", linestyle=":", linewidth=0.5, alpha=0.25)
    fig.legend(
        handles=[
            Patch(
                facecolor="0.65",
                edgecolor="0.45",
                alpha=0.28,
                label="Box: P25–P75; whiskers: P05–P95",
            ),
            Line2D(
                [0],
                [0],
                marker="D",
                markerfacecolor="white",
                markeredgecolor="0.35",
                linestyle="None",
                markersize=6 if font_size > 25 else 5,
                label="Mean",
            ),
            Line2D(
                [0],
                [0],
                color="0.35",
                linestyle=(0, (3, 2)),
                linewidth=1.0,
                label="IRENA global average LCOE (2024)",
            ),
        ],
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.99),
        ncol=3,
        columnspacing=1.3,
        handlelength=1.5,
        labelspacing=0.5,
        prop={
            "family": "Times New Roman",
            "size": 18 if font_size > 25 else 15,
            "weight": "bold",
        },
    )
    top = 0.95 if font_size <= 25 else 0.93
    fig.tight_layout(pad=0.7, rect=(0, 0, 1, top))
    FIGURES.mkdir(parents=True, exist_ok=True)
    for filename in png_filenames:
        fig.savefig(FIGURES / filename, facecolor="white", dpi=300)
    if save_pdf:
        fig.savefig(FIGURES / "Figure_5_modelled_LCOE.pdf")
    plt.close(fig)


def main():
    inputs = pd.read_csv(INPUTS).set_index("Technology").loc[TECHNOLOGY_ORDER].reset_index()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    reference_rows = []
    simulations = []

    for row in inputs.to_dict(orient="records"):
        technology = row["Technology"]
        calculated = calculate_lcoe(
            row["CAPEX_USD_kW"],
            row["OPEX_USD_kW_yr"],
            row["Capacity_Factor"],
            row["WACC"],
            int(row["Lifetime_yr"]),
            row["Degradation"],
        )
        reference_rows.append(
            {
                "Technology": technology,
                "CAPEX_USD_kW": row["CAPEX_USD_kW"],
                "OPEX_USD_kW_yr": row["OPEX_USD_kW_yr"],
                "Capacity_Factor": row["Capacity_Factor"],
                "WACC": row["WACC"],
                "Lifetime_yr": int(row["Lifetime_yr"]),
                "Degradation": row["Degradation"],
                "Calculated_LCOE_USD_MWh": calculated,
                "IRENA_2024_Global_LCOE_USD_MWh": row[
                    "IRENA_2024_Global_LCOE_USD_MWh"
                ],
                "Difference_vs_IRENA": calculated
                - row["IRENA_2024_Global_LCOE_USD_MWh"],
            }
        )
        simulations.append(simulate_lcoe(row))

    reference = pd.DataFrame(reference_rows)
    samples = pd.concat(simulations, ignore_index=True)
    summary = (
        samples.groupby("Technology")["LCOE_USD_MWh"]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
    )
    quantiles = (
        samples.groupby("Technology")["LCOE_USD_MWh"]
        .quantile([0.05, 0.50, 0.95])
        .unstack()
        .reset_index()
        .rename(columns={0.05: "P05", 0.50: "Median", 0.95: "P95"})
    )
    summary = summary.merge(quantiles, on="Technology")
    reference.to_csv(PROCESSED / "lcoe_reference_calculation.csv", index=False)
    samples.to_csv(PROCESSED / "lcoe_monte_carlo_samples.csv", index=False)
    summary.to_csv(PROCESSED / "lcoe_monte_carlo_summary.csv", index=False)
    create_figure(inputs, samples)
    create_figure(
        inputs,
        samples,
        font_size=30,
        png_filenames=(
            "Figure_5_modelled_LCOE_v2_font30.png",
            "Figure_5_modelled_LCOE_v2_font30_copy.png",
        ),
        save_pdf=False,
    )
    print("LCOE package outputs rebuilt.")


if __name__ == "__main__":
    main()
