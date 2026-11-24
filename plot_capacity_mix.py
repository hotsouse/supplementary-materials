"""Reproduce Figure 1: the 2025 renewable capacity mix in four Central Asian countries."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

OUTPUT_DIR = BASE_DIR / "figures"

COUNTRIES = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Uzbekistan"]

TECH_MAP = {
    "Renewable hydropower": "Hydropower",
    "Solar photovoltaic": "Solar PV",
    "Onshore wind energy": "Wind",
}

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 25,
    "font.weight": "bold",
    "axes.titlesize": 25,
    "axes.labelsize": 25,
    "xtick.labelsize": 25,
    "ytick.labelsize": 25,
    "legend.fontsize": 25,
    "figure.dpi": 120,
    "savefig.dpi": 300,
})


def load_capacity_data() -> pd.DataFrame:
    """Read the supplied IRENASTAT subset; capacity values are in MW."""
    return pd.read_csv(DATA_DIR / "irena_capacity_2025.csv")


def numeric(df, col):
    """Preserve the original handling of nonnumeric entries as missing values."""
    out = df.copy()
    out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def save(fig, filename, pdf=False):
    """Save publication outputs, creating the output folder when needed."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    fig.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches="tight", facecolor="white")
    if pdf:
        fig.savefig(OUTPUT_DIR / Path(filename).with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_capacity_structure(
    capacity,
    font_size=25,
    label_pad=165,
    filename="figure_01_capacity_mix_2025.png",
    legend_y=1.16,
):
    """Calculate technology shares and render a 100% stacked capacity chart."""
    value_col = "Electricity capacity statistics"
    data = numeric(capacity, value_col)
    data = data[(data["Year"] == 2025) & data["Country/area"].isin(COUNTRIES)]

    data = data[data["Technology"].isin(TECH_MAP)].copy()
    # Match the original figure: missing components contribute zero.
    structure = data.pivot_table(index="Country/area", columns="Technology", values=value_col, aggfunc="sum").fillna(0)
    structure = structure.reindex(COUNTRIES).fillna(0)
    structure = structure.rename(columns=TECH_MAP)
    for col in ("Hydropower", "Solar PV", "Wind"):
        if col not in structure.columns:
            structure[col] = 0.0
    structure = structure[["Hydropower", "Solar PV", "Wind"]]
    # The denominator includes only hydropower, solar PV and onshore wind.
    totals = structure.sum(axis=1)
    shares = structure.div(totals.replace(0, np.nan), axis=0) * 100

    fig, ax = plt.subplots(figsize=(12, 6.8))
    left = np.zeros(len(COUNTRIES))
    labels = ["Hydropower", "Solar PV", "Wind"]

    for label in labels:
        vals = shares[label].fillna(0).to_numpy()
        ax.barh(COUNTRIES, vals, left=left, label=label, edgecolor="white", linewidth=0.8)
        left += vals

    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    ax.set_xlabel("Share of renewable capacity (%)", fontweight="bold", fontsize=font_size)
    ax.set_ylabel("")
    ax.tick_params(axis="y", pad=label_pad, labelsize=font_size)
    ax.tick_params(axis="x", labelsize=font_size)
    for tick in ax.get_yticklabels():
        tick.set_horizontalalignment("left")
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontweight("bold")
    ax.set_title("")
    ax.grid(axis="x", alpha=0.22)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, legend_y), fontsize=font_size)

    ax.set_xlim(0, 100)

    fig.tight_layout(rect=[0, 0.04, 1, 0.95])
    save(fig, filename, pdf=filename == "figure_01_capacity_mix_2025.png")


def main():
    capacity = load_capacity_data()
    plot_capacity_structure(capacity)
    plot_capacity_structure(
        capacity,
        font_size=30,
        label_pad=165,
        filename="figure_01_capacity_mix_2025_large_font.png",
        legend_y=1.32,
    )
    print(f"Saved figures to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
