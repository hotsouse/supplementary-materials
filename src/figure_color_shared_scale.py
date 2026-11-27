"""Plot saved forecast values with common limits for three countries.

No models are fitted. Requires licensed Times New Roman Bold.
Run from the project root with --font-dir if the font is not installed.
"""
from pathlib import Path
import argparse
import hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Uzbekistan"]
COLORS = ["#176b87", "#f28e2b", "#5b8e7d", "#c94c4c"]
FONT_SIZE = 25


def build_figure(history, forecast, font_size=FONT_SIZE):
    plt.rcParams.update({
        "font.family": "Times New Roman",
        "font.size": font_size,
        "font.weight": "bold",
        "axes.labelsize": font_size,
        "axes.labelweight": "bold",
        "axes.titlesize": font_size,
        "axes.titleweight": "bold",
        "xtick.labelsize": font_size,
        "ytick.labelsize": font_size,
        "legend.fontsize": font_size,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
    })
    fig, axes = plt.subplots(2, 2, figsize=(24, 16))
    formatter = FuncFormatter(lambda value, position: f"{value:,.0f}")
    for ax, country, color in zip(axes.flat, COUNTRIES, COLORS):
        h = history[
            (history.country == country)
            & (history.year <= 2024)
            & history.ren.notna()
        ].sort_values("year")
        q = forecast[forecast.country == country].sort_values("year")
        assert list(q.year) == list(range(2025, 2051))
        assert (q.lo80_GWh <= q.hi80_GWh).all()
        ax.fill_between(
            q.year, q.lo80_GWh, q.hi80_GWh,
            color=color, alpha=0.18, linewidth=0,
        )
        observed, = ax.plot(
            h.year, h.ren, color=color,
            linewidth=2.2, marker="o", markersize=4,
        )
        central, = ax.plot(
            q.year, q.central_GWh, color=color,
            linewidth=3, linestyle="--",
        )
        np.testing.assert_array_equal(observed.get_ydata(), h.ren.to_numpy())
        np.testing.assert_array_equal(central.get_ydata(), q.central_GWh.to_numpy())
        ax.axvline(2024.5, color="#75808C", linestyle=":", linewidth=1.5)
        title = country
        ax.set_title(title, pad=16)
        ax.set_xlabel("Year")
        ax.set_ylabel("Renewable generation (GWh/year)", labelpad=14)
        ax.set_xlim(1999, 2051)
        ax.set_xticks([2000, 2010, 2020, 2030, 2040, 2050])
        ax.tick_params(axis="x", labelrotation=45, pad=7)
        ax.tick_params(axis="y", pad=7)
        if country == "Uzbekistan":
            ax.set_ylim(0, 450000)
            ax.set_yticks([0, 100000, 200000, 300000, 400000])
        else:
            ax.set_ylim(0, 60000)
            ax.set_yticks(np.arange(0, 60001, 10000))
        assert max(q.hi80_GWh.max(), h.ren.max()) < ax.get_ylim()[1]
        ax.yaxis.set_major_formatter(formatter)
        ax.grid(axis="y", color="#CBD0D6", alpha=0.35, linewidth=0.8)
        ax.set_axisbelow(True)
        for label in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
            label.set_fontweight("bold")
            label.set_fontsize(font_size)
    fig.legend(
        handles=[
            Line2D([], [], color="#343A40", marker="o", markersize=6,
                   linewidth=2.2, label="Historical observations"),
            Line2D([], [], color="#343A40", linestyle="--",
                   linewidth=3, label="Central forecast (mean)"),
            Patch(facecolor="#778A96", alpha=0.18,
                  label="Conditional model-based 80% interval"),
        ],
        loc="lower center", bbox_to_anchor=(0.51, 0.022),
        ncol=3, frameon=False, handlelength=2.4, columnspacing=1.6,
        prop={"family": "Times New Roman", "size": font_size, "weight": "bold"},
    )
    fig.subplots_adjust(
        left=0.105, right=0.98, bottom=0.16,
        top=0.94, wspace=0.33, hspace=0.43,
    )
    fig.canvas.draw()
    texts = [t for t in fig.findobj(Text) if t.get_visible() and t.get_text()]
    assert {t.get_fontproperties().get_name() for t in texts} == {"Times New Roman"}
    assert {t.get_fontsize() for t in texts} == {float(font_size)}
    assert all(t.get_fontweight() in ("bold", 700) for t in texts)
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--font-dir", type=Path)
    parser.add_argument("--font-size", type=int, choices=(25, 30, 36), default=FONT_SIZE)
    args = parser.parse_args()
    if args.font_dir:
        for path in args.font_dir.iterdir():
            if path.suffix.lower() in (".ttf", ".otf"):
                font_manager.fontManager.addfont(str(path))
    prop = font_manager.FontProperties(family="Times New Roman", weight="bold")
    actual_font = font_manager.findfont(prop, fallback_to_default=False)
    if font_manager.FontProperties(fname=actual_font).get_name() != "Times New Roman":
        raise RuntimeError("Times New Roman Bold is required")
    paths = [
        ROOT / "outputs/tables/PREPARED_DATA.csv",
        ROOT / "outputs/tables/FORECAST_2025_2050_CORRECTED.csv",
    ]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    history, forecast = [pd.read_csv(p) for p in paths]
    fig = build_figure(history, forecast, font_size=args.font_size)
    out = ROOT / "outputs/figures"
    out.mkdir(parents=True, exist_ok=True)
    stem = f"Figure_S1_Color_SharedScale_TNR{args.font_size}_Bold"
    for extension in ("png", "pdf"):
        fig.savefig(out / f"{stem}.{extension}", dpi=300)
    plt.close(fig)
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    print("Saved PNG and PDF. Forecast and history CSVs are unchanged.")


if __name__ == "__main__":
    main()
