"""
Statistical forecast of renewable electricity generation to 2050, Central Asia.

Structure (all statistical, no scenarios):
  Total renewable = (A) hydro + other   [stationary / trend models, horizon-matched CV]
                  + (B) solar + wind    [installed capacity x capacity factor,
                                         capacity: damped-drift model, Monte-Carlo intervals]

Why: the old chart extrapolated one noisy total series with a model chosen on 1-year
errors. Hydro (weather driven, mean-reverting) and solar/wind (capacity build-out) have
different dynamics, and the file contains 2025 installed capacity that the old chart ignored.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from statsmodels.tsa.arima.model import ARIMA

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "data" / "raw" / "ELEC-C_20261019-070746.csv"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

COUNTRIES = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkmenistan", "Uzbekistan"]
LAST_OBS, LAST_CAP, END = 2024, 2025, 2050
NSIM = 20000
PHI = 0.98                      # damping of capacity additions (upper bound used in ETS practice)
CF_RANGE = {"solar": (0.10, 0.35), "wind": (0.15, 0.55)}   # physically plausible annual CF
HYDRO_H_SELECT = (3, 5, 10)     # horizons used for model choice (long, because target is 2050)
MIN_TRAIN = 10
TOL = 0.03                      # within 3% of best MAE -> prefer simpler model
RNG = np.random.default_rng(20261024)


def load_panel() -> dict[str, pd.DataFrame]:
    g = pd.read_csv(RAW, skiprows=[0, 1]).rename(columns={"Electricity statistics": "v"})
    g["v"] = pd.to_numeric(g["v"], errors="coerce")
    years = range(2000, LAST_CAP + 1)
    panels = {}
    for c in COUNTRIES:
        d = g[g["Country/area"] == c]

        def s(tech: str, kind: str) -> pd.Series:
            m = d[(d.Technology == tech) & d["Data Type"].str.contains(kind)]
            return m.set_index("Year").v.reindex(years)

        p = pd.DataFrame(index=pd.Index(years, name="year"))
        p["ren"] = s("Total Renewable", "Generation")
        p["nonren"] = s("Total Non-Renewable", "Generation")
        p["gen_solar"] = s("Solar photovoltaic", "Generation")
        p["gen_wind"] = s("Onshore wind energy", "Generation")
        p["cap_solar"] = s("Solar photovoltaic", "Capacity").fillna(0.0)
        p["cap_wind"] = s("Onshore wind energy", "Capacity").fillna(0.0)
        p["hydro_other"] = p["ren"] - p["gen_solar"].fillna(0) - p["gen_wind"].fillna(0)
        h = p["hydro_other"].copy()
        rep = (h.diff().abs() < 0.02)
        run_flag = rep & (rep.shift(1, fill_value=False) | rep.shift(-1, fill_value=False))
        p["hydro_masked"] = h.where(~run_flag)
        p["placeholder_flag"] = run_flag
        panels[c] = p
    return panels

def _valid_diffs(y):
    v = y[~np.isnan(y)]
    return np.diff(v)


def hydro_forecast(y: np.ndarray, model: str, H: int):
    """Return (mean[H], se[H]) for a candidate model fitted on y (NaN allowed)."""
    t = np.arange(len(y), dtype=float)
    ok = ~np.isnan(y)
    v = y[ok]
    h = np.arange(1, H + 1, dtype=float)
    if model == "naive":
        sd = np.std(_valid_diffs(y), ddof=1)
        return np.repeat(v[-1], H), sd * np.sqrt(h)
    if model == "mean":
        sd = np.std(v, ddof=1)
        return np.repeat(v.mean(), H), np.repeat(sd * np.sqrt(1 + 1 / len(v)), H)
    if model == "mean10":
        w = y[-10:]
        w = w[~np.isnan(w)]
        sd = np.std(w, ddof=1)
        return np.repeat(w.mean(), H), np.repeat(sd * np.sqrt(1 + 1 / len(w)), H)
    if model == "ols_trend":
        r = OLS(v, add_constant(t[ok])).fit()
        xf = add_constant(np.arange(len(y), len(y) + H, dtype=float), has_constant="add")
        pr = r.get_prediction(xf)
        return np.asarray(pr.predicted_mean), np.sqrt(pr.var_pred_mean + r.scale)
    if model in ("ar1c", "ar1ct"):
        f = ARIMA(y, order=(1, 0, 0), trend="c" if model == "ar1c" else "ct").fit()
        fc = f.get_forecast(H)
        return np.asarray(fc.predicted_mean), np.asarray(fc.se_mean)
    raise ValueError(model)


HYDRO_MODELS = ["mean", "naive", "mean10", "ols_trend", "ar1c", "ar1ct"]   
Z80 = 1.2816


def hydro_cv(c: str, y: np.ndarray) -> pd.DataFrame:
    rows = []
    n = len(y)
    for m in HYDRO_MODELS:
        for hz in (1, 3, 5, 10):
            errs, cov = [], []
            for p in range(MIN_TRAIN, n - hz + 1):
                if np.isnan(y[p + hz - 1]) or np.isnan(y[:p]).all():
                    continue
                try:
                    mu, se = hydro_forecast(y[:p], m, hz)
                except Exception:
                    continue
                e = mu[hz - 1] - y[p + hz - 1]
                errs.append(abs(e))
                cov.append(abs(e) <= Z80 * se[hz - 1])
            rows.append(dict(country=c, model=m, horizon=hz, n_origins=len(errs),
                             MAE_GWh=np.mean(errs) if errs else np.nan,
                             coverage80_pct=100 * np.mean(cov) if cov else np.nan))
    return pd.DataFrame(rows)


def hydro_interval_inflation(y: np.ndarray, model: str) -> float:
    """Empirical calibration: factor (>=1) that makes the 80% interval cover 80% of
    long-horizon (h=3,5,10) rolling-origin errors."""
    z = []
    n = len(y)
    for hz in HYDRO_H_SELECT:
        for p in range(MIN_TRAIN, n - hz + 1):
            if np.isnan(y[p + hz - 1]):
                continue
            try:
                mu, se = hydro_forecast(y[:p], model, hz)
            except Exception:
                continue
            z.append(abs(mu[hz - 1] - y[p + hz - 1]) / se[hz - 1])
    if not z:
        return 1.0
    return float(max(1.0, np.quantile(z, 0.80) / Z80))


def choose_hydro_model(cv: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    sub = cv[cv.horizon.isin(HYDRO_H_SELECT)]
    score = sub.groupby("model").MAE_GWh.mean().reindex(HYDRO_MODELS)
    best = score.min()
    for m in HYDRO_MODELS:                       
        if score[m] <= best * (1 + TOL):
            return m, score
    return score.idxmin(), score

def cf_estimate(p: pd.DataFrame, tech: str, upto: int):
    """capacity-weighted CF over last 3 plausible years (avg capacity >= 20 MW)."""
    cap = p[f"cap_{tech}"]
    avg = (cap + cap.shift(1)) / 2
    gen = p[f"gen_{tech}"]
    cf = gen / (avg * 8.76)
    lo, hi = CF_RANGE[tech]
    q = (avg >= 20) & cf.between(lo, hi) & (cf.index <= upto)
    yrs = cf.index[q][-3:]
    if len(yrs) == 0:
        return None
    return gen[yrs].sum() / (avg[yrs].sum() * 8.76), cf[q].iloc[-6:], len(yrs)


def pooled_cf(panels, tech):
    num = den = 0.0
    sds = []
    for p in panels.values():
        r = cf_estimate(p, tech, LAST_OBS)
        if r:
            cap = p[f"cap_{tech}"]
            avg = (cap + cap.shift(1)) / 2
            q = avg.index[(avg >= 20) & (p[f"gen_{tech}"] / (avg * 8.76)).between(*CF_RANGE[tech])][-3:]
            num += p.loc[q, f"gen_{tech}"].sum()
            den += avg[q].sum() * 8.76
            sds.append(r[1].std(ddof=1) if len(r[1]) > 1 else np.nan)
    return num / den, float(np.nanmean(sds))


def vre_module(p: pd.DataFrame, panels, years_f: np.ndarray):
    """Return dict with central path and simulated draws of solar+wind generation (GWh) for years_f (2025..2050)."""
    H = len(years_f)
    central = np.zeros(H)
    draws = np.zeros((NSIM, H))
    info = {}
    for tech in ("solar", "wind"):
        cap = p[f"cap_{tech}"]
        if cap.loc[LAST_CAP] < 0.5:
            continue
        r = cf_estimate(p, tech, LAST_OBS)
        if r is None:
            cf_hat, sd_cf = pooled_cf(panels, tech)
            src = "pooled"
        else:
            cf_hat = r[0]
            sd_cf = r[1].std(ddof=1) if len(r[1]) > 1 else np.nan
            src = "own"
        if not np.isfinite(sd_cf):
            sd_cf = pooled_cf(panels, tech)[1]
        sd_cf = max(sd_cf, 0.01)
        d = cap.diff()
        inc3, inc5 = d.loc[LAST_CAP - 2: LAST_CAP].values, d.loc[LAST_CAP - 4: LAST_CAP].values
        k = 3
        b_hat = float(0.5 * (inc3.mean() + inc5.mean()))
        sd_inc = float(max(0.5 * (inc3.std(ddof=1) + inc5.std(ddof=1)), 1e-6))
        # central path
        hh = np.arange(1, H, dtype=float)                       # 2026.. -> h=1..H-1
        add = b_hat * PHI ** hh
        c_path = np.concatenate([[cap.loc[LAST_CAP]], cap.loc[LAST_CAP] + np.cumsum(add)])
        c_prev = np.concatenate([[cap.loc[LAST_OBS]], c_path[:-1]])
        central += cf_hat * (c_prev + c_path) / 2 * 8.76
        b = np.maximum(RNG.normal(b_hat, sd_inc / np.sqrt(k), NSIM), 0)
        e = RNG.normal(0, sd_inc, (NSIM, H - 1))
        incs = np.maximum(b[:, None] * PHI ** hh[None, :] + e, 0)
        C = np.concatenate([np.full((NSIM, 1), cap.loc[LAST_CAP]), cap.loc[LAST_CAP] + np.cumsum(incs, axis=1)], axis=1)
        Cprev = np.concatenate([np.full((NSIM, 1), cap.loc[LAST_OBS]), C[:, :-1]], axis=1)
        cf_path = cf_hat + RNG.normal(0, sd_cf / np.sqrt(3), (NSIM, 1))
        cf_year = np.clip(cf_path + RNG.normal(0, sd_cf, (NSIM, H)), *CF_RANGE[tech])
        draws += cf_year * (Cprev + C) / 2 * 8.76
        info[tech] = dict(cf=cf_hat, cf_source=src, sd_cf=sd_cf, cap2025_MW=cap.loc[LAST_CAP],
                          mean_add_MW_per_year=b_hat, k=k, cap2050_central_MW=c_path[-1])
    return central, draws, info
def vre_backtests(panels):
    rows_cap, rows_now = [], []
    p = panels["Kazakhstan"]
    C = (p.cap_solar + p.cap_wind)
    for T in range(2016, 2021):
        for hz in (1, 3, 5):
            if T + hz > LAST_CAP:
                continue
            inc = C.diff().loc[:T]
            truth = C.loc[T + hz]
            hh = np.arange(1, hz + 1)
            f = {
                "hold_last (flat)": C.loc[T],
                "drift_last3": C.loc[T] + inc.iloc[-3:].mean() * hz,
                "drift_last5": C.loc[T] + inc.iloc[-5:].mean() * hz,
                "damped_last5": C.loc[T] + inc.iloc[-5:].mean() * np.sum(PHI ** hh),
                "combo_3_5_damped (used)": C.loc[T] + 0.5 * (inc.iloc[-3:].mean() + inc.iloc[-5:].mean()) * np.sum(PHI ** hh),
            }
            for m, v in f.items():
                rows_cap.append(dict(origin=T, horizon=hz, method=m, forecast_MW=v, actual_MW=truth,
                                     abs_err_MW=abs(v - truth)))

    for c, yrs in (("Kazakhstan", range(2018, 2025)), ("Uzbekistan", [2024])):
        p = panels[c]
        for t in yrs:
            act = p.gen_solar.fillna(0)[t] + p.gen_wind.fillna(0)[t]
            tot = 0.0
            ok = True
            for tech in ("solar", "wind"):
                r = cf_estimate(p, tech, t - 1)
                if r is None:
                    r = (pooled_cf(panels, tech)[0],)
                cap = p[f"cap_{tech}"]
                tot += r[0] * (cap[t] + cap[t - 1]) / 2 * 8.76
            naive = p.gen_solar.fillna(0)[t - 1] + p.gen_wind.fillna(0)[t - 1]
            rows_now.append(dict(country=c, year=t, actual_GWh=act, capacity_x_CF_GWh=tot, naive_last_year_GWh=naive,
                                 abs_err_capCF=abs(tot - act), abs_err_naive=abs(naive - act)))
    return pd.DataFrame(rows_cap), pd.DataFrame(rows_now)

def main():
    panels = load_panel()
    years_f = np.arange(LAST_OBS + 1, END + 1)          # 2025..2050
    H = len(years_f)
    out_rows, sel_rows, cv_all, comp_rows, vre_info = [], [], [], [], {}

    for c in COUNTRIES:
        p = panels[c]
        obs = p.loc[:LAST_OBS]
        if p["placeholder_flag"].loc[:LAST_OBS].mean() > 0.8:
            last = float(obs.ren.iloc[-1])
            for y, v in obs.ren.items():
                out_rows.append(dict(country=c, year=y, status="observed", observed_GWh=v))
            for y in years_f:
                out_rows.append(dict(country=c, year=y, status="forecast (no reliable signal: placeholder data)",
                                     central_GWh=last))
            sel_rows.append(dict(country=c, hydro_other_model="none (series is a constant placeholder)"))
            continue

        y = obs.hydro_masked.values.astype(float)
        cv = hydro_cv(c, y)
        cv_all.append(cv)
        model, score = choose_hydro_model(cv)
        mu, se = hydro_forecast(y, model, H)
        infl = hydro_interval_inflation(y, model)
        se = se * infl
        vc, vd, info = vre_module(p, panels, years_f)
        vre_info[c] = info
        hyd_draw = np.maximum(mu + se * RNG.standard_normal((NSIM, H)), 0)
        tot = hyd_draw + vd
        central = np.maximum(mu, 0) + vc
        q = lambda a: np.percentile(tot, a, axis=0)
        T = (obs.ren + obs.nonren).loc[2010:]
        b1, b0 = np.polyfit(T.index.values, np.log(T.values), 1)
        Tf = np.exp(b0 + b1 * years_f)

        for yy, v in obs.ren.items():
            out_rows.append(dict(country=c, year=yy, status="observed", observed_GWh=v))
        for i, yy in enumerate(years_f):
            out_rows.append(dict(
                country=c, year=yy,
                status="nowcast (2025 capacity observed)" if yy == LAST_CAP else "forecast",
                central_GWh=central[i], hydro_other_GWh=max(mu[i], 0), solar_wind_GWh=vc[i],
                lo80_GWh=q(10)[i], hi80_GWh=q(90)[i], lo95_GWh=q(2.5)[i], hi95_GWh=q(97.5)[i],
                implied_share_of_total_generation_pct=100 * central[i] / Tf[i]))
        sel_rows.append(dict(country=c, hydro_other_model=model, interval_inflation=round(infl, 2),
                             **{f"CV_MAE_{m}_GWh": round(score[m], 1) for m in HYDRO_MODELS},
                             placeholder_years_masked=";".join(map(str, p.index[p.placeholder_flag & (p.index <= LAST_OBS)]))))

    fc = pd.DataFrame(out_rows)
    fc.to_csv(OUT / "forecast_2025_2050.csv", index=False)
    pd.DataFrame(sel_rows).to_csv(OUT / "model_selection_hydro.csv", index=False)
    pd.concat(cv_all).to_csv(OUT / "cv_hydro_rolling_origin.csv", index=False)
    bc, bn = vre_backtests(panels)
    bc.to_csv(OUT / "backtest_vre_capacity_kazakhstan.csv", index=False)
    bn.to_csv(OUT / "backtest_vre_nowcast.csv", index=False)
    pd.DataFrame([dict(country=c, tech=t, **v) for c, d in vre_info.items() for t, v in d.items()]) \
        .to_csv(OUT / "vre_parameters.csv", index=False)
    print(pd.DataFrame(sel_rows).to_string())
    print(pd.DataFrame([dict(country=c, tech=t, **v) for c, d in vre_info.items() for t, v in d.items()]).round(3).to_string())
    s = bc.groupby("method").abs_err_MW.mean().round(0)
    print("\nKZ VRE capacity backtest, MAE MW:\n", s.to_string())
    print(bn.round(0).to_string())
    print(bn[["abs_err_capCF", "abs_err_naive"]].groupby(bn.country).mean().round(0))
    for c in COUNTRIES:
        d = fc[(fc.country == c) & fc.year.isin([2024, 2025, 2030, 2040, 2050])]
        print(c); print(d[["year", "status", "observed_GWh", "central_GWh", "hydro_other_GWh", "solar_wind_GWh",
                           "lo80_GWh", "hi80_GWh", "lo95_GWh", "hi95_GWh",
                           "implied_share_of_total_generation_pct"]].round(0).to_string(index=False)
              if "lo80_GWh" in d else d.round(0).to_string(index=False))
    make_figures(panels, fc)


def make_figures(panels, fc):
    col = "#1f5f99"
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.6))
    for ax, c in zip(axes.flat, COUNTRIES):
        d = fc[fc.country == c]
        o = d[d.status == "observed"]
        f = d[d.status != "observed"]
        unit, div = ("GWh", 1.0) if c == "Turkmenistan" else ("TWh", 1000.0)
        ax.plot(o.year, o.observed_GWh / div, "k-o", ms=3, lw=1.6)
        if "lo95_GWh" in f and f.lo95_GWh.notna().any():
            ax.fill_between(f.year, f.lo95_GWh / div, f.hi95_GWh / div, color=col, alpha=0.13, lw=0)
            ax.fill_between(f.year, f.lo80_GWh / div, f.hi80_GWh / div, color=col, alpha=0.28, lw=0)
        ax.plot([o.year.iloc[-1], f.year.iloc[0]], [o.observed_GWh.iloc[-1] / div, f.central_GWh.iloc[0] / div],
                color=col, ls=":", lw=1.2)
        ax.plot(f.year, f.central_GWh / div, color=col, ls="--", lw=2)
        ax.axvline(LAST_OBS + 0.5, color="gray", ls=":", lw=1.4)
        ax.set_title(c)
        ax.set_xlabel("Year")
        ax.set_ylabel(f"Renewable electricity generation ({unit}/year)")
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.2)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        if c == "Turkmenistan":
            ax.text(0.03, 0.55, "Source series is a constant\nplaceholder (3.15 GWh):\nno statistical signal", transform=ax.transAxes,
                    fontsize=9, color="#a33")
    ax = axes.flat[-1]
    ax.axis("off")
    ax.plot([], [], "k-o", ms=3, label="Observed (IRENA file, 2000-2024)")
    ax.plot([], [], color=col, ls="--", lw=2, label="Central forecast (hydro model + capacity x CF)")
    ax.fill_between([], [], [], color=col, alpha=0.28, label="80% model-based interval")
    ax.fill_between([], [], [], color=col, alpha=0.13, label="95% model-based interval")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    ax.text(0.0, 0.42, "2025 = nowcast from observed 2025 capacity.\nIntervals are conditional on the model;\n"
            "backtests cover at most 10 years,\nso they do not validate 2050.\nNo policy scenarios are used.",
            fontsize=9.5, va="top", transform=ax.transAxes)
    fig.suptitle("Statistical forecasts of renewable electricity generation to 2050", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / "forecast_to_2050.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    for ax, c in zip(axes, ["Kazakhstan", "Uzbekistan", "Tajikistan"]):
        d = fc[(fc.country == c) & (fc.status != "observed")]
        p = panels[c].loc[:LAST_OBS]
        ax.stackplot(list(p.index) + list(d.year),
                     list(p.hydro_other.fillna(0) / 1000) + list(d.hydro_other_GWh / 1000),
                     list((p.gen_solar.fillna(0) + p.gen_wind.fillna(0)) / 1000) + list(d.solar_wind_GWh / 1000),
                     labels=["Hydro & other", "Solar + wind"], colors=["#7fb0d8", "#f2a900"], alpha=0.9)
        ax.axvline(LAST_OBS + 0.5, color="gray", ls=":")
        ax.set_title(c); ax.set_ylabel("TWh/year"); ax.grid(alpha=0.2)
        ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "decomposition_hydro_vs_solar_wind.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
