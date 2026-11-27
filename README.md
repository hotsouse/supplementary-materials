# Statistical Forecast of Renewable Electricity Generation in Central Asia to 2050

## 1. Research Overview

This repository contains the historical datasets, statistical models, Python implementation, uncertainty simulations, validation procedures, and visualization scripts supporting the study **“Renewable Energy Prospects and Challenges in Central Asia.”**

The objective is to estimate annual renewable electricity generation through 2050 using historical electricity generation and installed capacity statistics.

The computational framework covers five Central Asian countries:

- Kazakhstan
- Kyrgyzstan
- Tajikistan
- Turkmenistan
- Uzbekistan

The principal visualization presents Kazakhstan, Kyrgyzstan, Tajikistan, and Uzbekistan. Turkmenistan remains included in the underlying data preparation, statistical calculations, and pooled capacity factor estimation.

The forecasting framework combines:

- Historical renewable electricity generation analysis.
- Component-specific statistical forecasting.
- Installed capacity projections.
- Capacity factor estimation.
- Rolling-origin historical validation.
- Bootstrap-based model selection.
- Joint Monte Carlo uncertainty simulation.
- Sensitivity analysis.
- Reproducible scientific visualization.

The resulting trajectories represent conditional statistical extrapolations rather than deterministic predictions of future national electricity generation.

This package is distinct from the project-based BAU, Accelerated, and High Ambition scenario framework contained in `CA_RE_2050`. National policy targets and individual future infrastructure projects are not numerical inputs to the statistical forecasts presented here.

---

## 2. Historical Data

### 2.1. Primary Data Source

The sole primary numerical input is the electricity statistics dataset published by the International Renewable Energy Agency (IRENA).

**Source:** [IRENASTAT](https://pxweb.irena.org/)

**Database table:** Electricity statistics by Country/area, Technology, Data Type, Grid connection and Year.

**Table identifier:** ELEC-C.

**Original input file:**

`data/raw/ELEC-C_20261019-070746.csv`

The original export is preserved without modification.

| Parameter | Specification |
|---|---|
| Countries | Five Central Asian countries |
| Historical data period | 2000–2025 |
| Electricity generation | GWh |
| Installed capacity | MW |
| Grid connection | All |
| Technology categories | 26 |
| Latest generation observation | 2024 |
| Latest capacity observation | 2025 |
| Forecast period | 2025–2050 |
| Total source records | 6,760 |

The dataset contains 1,299 numerical observations, including explicit zeros, and 5,461 missing entries.

The full dataset structure corresponds to:

**5 countries × 26 years × 26 technologies × 2 data types = 6,760 records.**

The filename identifies the retained data export dated 19 October 2026. The filename alone does not independently establish the publication date or revision history of every observation.

### 2.2. Data Integrity

The SHA-256 checksum of the retained source file is:

```text
2bdad46f9a6b7eb07a5b409c1f8e432ecfebcbc35305f9381c1f7995d120174c
```

The checksum identifies the exact byte-level version of the input dataset used in the retained calculation.

It verifies file integrity rather than the substantive accuracy of individual statistical observations.

### 2.3. Historical Reference Values

The latest available annual renewable electricity generation observations are reported for 2024.

| Country | Renewable generation, GWh |
|---|---:|
| Kazakhstan | 17,657.99 |
| Kyrgyzstan | 12,935.80 |
| Tajikistan | 20,878.88 |
| Turkmenistan | 3.35 |
| Uzbekistan | 12,914.80 |

Generation observations for 2025 are unavailable in the retained export.

However, installed capacity information extends through 2025, allowing a capacity-informed estimate of electricity generation for that year.

### 2.4. Definition of Electricity Generation and Capacity

IRENA electricity generation represents annual gross electricity production, whereas installed capacity generally represents maximum net generating capacity available at the end of the calendar year.

The calculation of historical capacity factors therefore combines gross electricity generation with reported net installed capacity.

The resulting capacity factors are interpreted as operational approximations rather than independently measured plant-level utilization rates.

---

## 3. Data Preparation and Quality Control

The historical preprocessing workflow is implemented in:

`src/renewable/data.py`

### 3.1. Structural Validation

The source dataset is checked for:

- Unique combinations of country, technology, data type, grid connection, and year.
- Valid country identifiers.
- Consistent grid connection coverage.
- Valid generation and installed capacity data types.
- Non-negative numerical observations.
- Correct numerical parsing.

The first two metadata rows of the original CSV are skipped during loading.

Missing entries represented by `..` are converted to `NaN`.

Invalid numerical strings trigger parsing errors rather than being silently converted into missing values.

### 3.2. Renewable Energy Balance

The reported `Total Renewable` category is compared with the sum of available renewable technology components.

Let:

- T be the reported renewable energy total.
- K be the set of renewable technology categories with available numerical observations.
- xₖ be the corresponding generation or capacity value.

The balance residual is calculated as:

**D = T − Σxₖ**

A balance tolerance of 0.021 in the corresponding measurement unit is applied.

The tolerance is an implementation assumption intended to accommodate source precision and rounding differences.

It is not an independently estimated measurement-error distribution.

Unresolved balances are recorded in:

`outputs/tables/DATA_QUALITY_AUDIT.csv`

### 3.3. Treatment of Missing Values

Missing observations are not automatically interpreted as zero.

A working zero may be assigned to a missing renewable technology component when the available components already reconcile with the reported renewable total within the specified tolerance.

For installed capacity, an additional consistency condition is applied: a missing capacity observation is not assigned zero if the corresponding generation observation indicates positive electricity production above the tolerance.

The retained audit records:

| Audit category | Recorded entries |
|---|---:|
| Zeros inferred from closed balances | 2,649 |
| Missing component values retained | 70 |
| Repeated observations retained | 84 |

These counts refer to the relevant preprocessing operations and do not represent all missing observations in the original dataset.

The inferred zeros are conditional on the completeness and consistency of the source technology classification.

They are distinguished from explicit numerical zeros originally reported by IRENA.

### 3.4. Repeated Observations

Repeated historical observations are retained and flagged for inspection.

A repeated value may represent unchanged installed capacity, stable generation, or source rounding.

Repeated values are therefore not removed solely because they remain unchanged across consecutive years.

### 3.5. Hydropower Classification

The renewable technology balance includes renewable hydropower and mixed hydropower as represented in the original dataset.

For Kazakhstan in 2022, the source contains:

- Renewable hydropower: 900.90 GWh.
- Mixed hydropower: 8,241.24 GWh.

Their combined generation is 9,142.14 GWh.

The source classification is retained rather than applying an unsupported numerical correction to individual observations.

---

## 4. Renewable Generation Decomposition

The historical renewable electricity generation series is decomposed into three components:

**G_RE(t) = G_H(t) + G_S(t) + G_W(t)**

where:

- G_RE(t) is total renewable electricity generation.
- G_H(t) is residual hydropower and other renewable electricity generation.
- G_S(t) is solar electricity generation.
- G_W(t) is wind electricity generation.

All generation components are expressed in GWh/year.

### 4.1. Solar Component

Solar generation is calculated from:

**G_S(t) = G_PV(t) + G_solar_thermal(t)**

The corresponding installed capacity is calculated using the same technology grouping.

### 4.2. Wind Component

Wind generation is calculated from:

**G_W(t) = G_onshore(t) + G_offshore(t)**

The corresponding installed capacity combines onshore and offshore wind capacity.

### 4.3. Residual Hydropower and Other Renewables

The residual component is calculated as:

**G_H(t) = G_RE(t) − G_S(t) − G_W(t)**

This component is identified as `hydro_other` in the computational implementation.

It should not be interpreted as exclusively hydropower generation because it also contains other renewable technologies not assigned to the solar and wind components.

The residual formulation preserves consistency with the reported total renewable generation.

### 4.4. Forecasting Architecture

The three components are modelled using different statistical mechanisms.

| Component | Forecasting approach |
|---|---|
| Hydropower and other renewables | Direct generation forecasting |
| Solar | Installed capacity forecasting combined with capacity factor estimation |
| Wind | Installed capacity forecasting combined with capacity factor estimation |

This architecture reflects differences in historical data availability and technology development.

Hydropower has a comparatively long generation history, whereas solar and wind generation can change rapidly as new capacity enters operation.

The architecture is a research decision. Its superiority over direct generation forecasting is not assumed and must be assessed using historical validation.

---

## 5. Capacity Factor Estimation

### 5.1. Effective Annual Installed Capacity

The historical operating capacity is approximated by the arithmetic mean of the previous and current year-end installed capacities.

**C_avg(t) = [C(t−1) + C(t)] / 2**

where C is measured in MW.

This approximation represents an assumed gradual change in installed capacity within the calendar year.

### 5.2. Potential Electricity Generation

The theoretical annual generation at full capacity utilization is:

**E_max(t) = C_avg(t) × L(t) / 1000**

where:

- E_max(t) is potential electricity generation in GWh.
- L(t) is the number of hours in the calendar year.
- L(t) = 8,760 for a standard year.
- L(t) = 8,784 for a leap year.

The division by 1,000 converts MWh into GWh.

### 5.3. Historical Capacity Factor

The historical capacity factor is calculated as:

**CF(t) = G(t) / E_max(t)**

An observation is eligible for future capacity factor estimation when:

- Electricity generation is available.
- Effective installed capacity is positive.
- The calculated capacity factor is between zero and one.

The principal model does not impose an additional minimum installed capacity threshold of 20 MW.

### 5.4. Inconsistent Historical Capacity Factors

Four inconsistent solar and wind capacity factor observations are identified for Uzbekistan.

| Technology | Year | Calculated CF |
|---|---:|---:|
| Solar | 2021 | 1.59817 |
| Wind | 2019 | 2.35921 |
| Wind | 2020 | 2.35276 |
| Wind | 2023 | 1.09589 |

These values exceed the admissible range of the capacity factor used in the model.

The original generation and capacity observations remain preserved.

Only the inconsistent ratios are excluded from the estimation of future capacity factors.

This procedure prevents physically inadmissible utilization coefficients from entering the simulation but does not resolve the underlying source inconsistencies.

### 5.5. Exposure-Weighted Capacity Factor

The model selects up to five of the most recent eligible historical capacity factor observations.

These observations may cover more than five calendar years when missing values are present.

The central capacity factor estimate is calculated as:

**CF_est = ΣG(t) / ΣE_max(t)**

Equivalently:

**CF_est = Σw(t) × CF(t)**

where:

**w(t) = E_max(t) / ΣE_max(t)**

This approach assigns greater weight to observations associated with larger effective generation capacity.

### 5.6. Effective Sample Size

The concentration of observation weights is evaluated using the Kish effective sample size:

**n_eff = [ΣE_max(t)]² / Σ[E_max(t)²]**

An effective sample size close to one indicates that the weighted estimate is dominated by a single observation, even if several historical years are available.

This diagnostic is particularly important for countries experiencing rapid recent capacity expansion.

### 5.7. Country-Specific and Pooled Estimates

A country-specific capacity factor estimate is used when at least two eligible local observations are available and their combined generation is positive.

Otherwise, the model uses an exposure-weighted pooled estimate based on eligible observations from the five Central Asian countries.

The same information cut-off is applied to all observations entering the pooled estimate.

Pooling improves computational coverage for countries with limited solar and wind generation history.

However, pooled capacity factors do not necessarily represent the specific resource conditions, technology characteristics, or operating performance of an individual country.

### 5.8. Retained Capacity Factor Estimates

| Country | Solar CF | Wind CF | Source |
|---|---:|---:|---|
| Kazakhstan | 0.18712 | 0.33607 | Own observations |
| Kyrgyzstan | 0.19629 | 0.33708 | Pooled |
| Tajikistan | 0.19629 | 0.33708 | Pooled |
| Uzbekistan | 0.21408 | 0.35532 | Own observations |

Uzbekistan's effective sample sizes are approximately 1.620 for solar and 1.021 for wind.

These values indicate substantial concentration of the capacity factor estimation weights.

---

## 6. Candidate Forecasting Models

The statistical forecasting functions are implemented in:

`src/renewable/models.py`

Let:

- T be the final available observation year.
- h be the forecast horizon.
- y(T) be the latest available observation.
- ŷ(T+h) be the forecast value.

All forecast levels are constrained to be non-negative.

Negative historical net capacity changes are not automatically removed.

### 6.1. Naive Model

The naive forecast maintains the latest available observation:

**ŷ(T+h) = y(T)**

The model provides a transparent benchmark requiring minimal parameter estimation.

### 6.2. Historical Mean

The mean forecast maintains the average of available historical observations:

**ŷ(T+h) = Σy(t) / n**

Additional mean models use observations from the latest five or ten calendar years.

These models are suitable candidates for series without a persistent growth trend.

### 6.3. Drift Model

The drift forecast extends the average change between the first and last available observations.

**b = [y(T) − y(t₀)] / (T − t₀)**

**ŷ(T+h) = y(T) + bh**

The drift model represents continuation of the long-term historical change.

It does not incorporate a separate future saturation constraint.

### 6.4. Linear Regression

The linear trend model is estimated using ordinary least squares:

**y(t) = a + b(t−T) + ε(t)**

The forecast is:

**ŷ(T+h) = a + bh**

At least three non-missing observations are required.

### 6.5. Recent Capacity Drift

For installed capacity, the model evaluates average annual net additions over recent three-year and five-year windows.

**bₖ = mean[C(t) − C(t−1)]**

Only differences between consecutive calendar years are accepted.

Differences across missing intermediate years are not interpreted as single-year capacity additions.

The corresponding forecast is:

**Ĉ(T+h) = C(T) + hbₖ**

The candidate models are identified as `drift3` and `drift5`.

### 6.6. Damped Capacity Trends

The damped trend model progressively reduces the contribution of recent capacity growth:

**Ĉ(T+h) = C(T) + b₅ × Σφⁱ**

where the summation extends from i = 1 to h.

The candidate damping parameters are:

- φ = 0.8.
- φ = 0.9.
- φ = 0.98.

Damping reduces the unrestricted continuation of recent growth rates over long forecast horizons.

The specified damping values are research-defined candidate settings rather than externally measured national parameters.

### 6.7. Combined Recent Trend

The combined model uses the average of three-year and five-year capacity addition estimates:

**b_combo = (b₃ + b₅) / 2**

The combined trend is damped using φ = 0.98.

This candidate is identified as `combo_0.98`.

### 6.8. First-Order Autoregression

The AR(1) model represents dependence on the preceding observation.

For the constant-mean specification:

**y(t) − μ = φ[y(t−1) − μ] + ε(t)**

The corresponding conditional forecast is:

**ŷ(T+h) = μ + φʰ[y(T) − μ]**

A second specification includes a deterministic linear trend.

The models are implemented using `statsmodels` ARIMA with order `(1, 0, 0)`.

The constant and trend specifications use the corresponding library parameterizations.

### 6.9. Damped Exponential Smoothing

The exponential smoothing candidate uses an additive damped trend.

Its standard forecasting form is:

**ŷ(T+h) = ℓ(T) + b(T) × Σφⁱ**

where:

- ℓ(T) is the estimated level.
- b(T) is the estimated trend.
- φ is the damping coefficient.

The level, trend, smoothing parameters, and damping coefficient are estimated from the training series.

The implementation uses `ExponentialSmoothing` with an additive trend, damped trend, and estimated initialization.

Seasonality is not included because the observations are annual.

AR and ETS models require at least eight available observations and successful numerical estimation.

ETS additionally requires a continuous historical series.

### 6.10. Complete Candidate Sets

| Residual generation models | Installed capacity models |
|---|---|
| mean | naive |
| naive | drift3 |
| mean5 | drift5 |
| mean10 | damped5_0.8 |
| drift | damped5_0.9 |
| linear | damped5_0.98 |
| ar1 | combo_0.98 |
| ar1trend | ets_damped |
| ets_damped | |

Direct naive and mean forecasts of solar and wind generation are also calculated for comparison.

However, the principal forecasting architecture selects solar and wind models from the capacity-based candidates.

A direct generation baseline with lower historical error does not automatically replace the predefined capacity-based architecture.

---

## 7. Historical Validation and Model Selection

The validation and model selection procedures are implemented in:

`src/renewable/validation.py`

### 7.1. Rolling-Origin Evaluation

Candidate forecasting models are evaluated using sequential historical information cut-offs.

At each origin, the model is fitted using observations available up to that year.

Forecasts are then compared with subsequent historical observations.

The evaluated forecast horizons are:

**h = 1, 3, 5, and 10 years.**

Candidate training origins begin in 2007.

The model selection procedure uses eligible validation target years within the latest ten-year calendar window available at the corresponding information cut-off.

This structure reduces the influence of future observations on historical model selection.

However, the historical experiment uses the retained revised statistical export rather than archived data vintages available at each historical date.

It is therefore a retrospective rolling-origin evaluation rather than a complete real-time forecasting experiment.

### 7.2. Error Definition

For a forecast ŷ and corresponding observation y:

**e = ŷ − y**

Positive errors indicate overprediction, while negative errors indicate underprediction.

### 7.3. Mean Absolute Error

**MAE = Σ|eᵢ| / n**

MAE is the principal component-level model selection criterion.

It is expressed in GWh for generation comparisons.

For solar and wind capacity candidates, forecast errors are evaluated after converting the predicted capacity into electricity generation.

This allows candidate performance to be compared in the units of the final research outcome.

### 7.4. Root Mean Squared Error

**RMSE = √[Σeᵢ² / n]**

RMSE assigns greater importance to large forecast errors.

It is reported as an additional historical performance metric.

### 7.5. Forecast Bias

**Bias = Σeᵢ / n**

Bias identifies systematic overprediction or underprediction across historical validation observations.

### 7.6. Mean Absolute Scaled Error

MASE compares absolute forecast errors with the scale of historical naive forecast errors.

Its general form is:

**MASE = MAE_forecast / MAE_naive,training**

MASE is reported as a diagnostic measure.

It is not the principal model selection criterion.

### 7.7. Comparable Validation Pairs

Candidate models are compared using common eligible historical forecast pairs.

A candidate must cover at least 90% of the eligible validation pairs available for the corresponding baseline.

At least five common forecast pairs are required for comparison.

Each included forecast horizon must contain at least three comparable pairs.

These requirements reduce the risk of selecting a model that appears accurate only because difficult validation observations are missing from its evaluation.

### 7.8. Horizon-Weighted Selection

The principal selection score is calculated as the average MAE across eligible forecast horizons, assigning equal weight to each included horizon.

**Score = (1 / |H|) × ΣMAE(h)**

This prevents the more numerous short-horizon forecasts from automatically dominating the selection criterion.

### 7.9. One-Standard-Error Rule

The final model is selected using a one-standard-error rule.

The candidate with the lowest historical error is first identified.

The variability of paired error differences is estimated using a block bootstrap over forecast origins.

The bootstrap configuration uses:

- 500 repetitions.
- Block length of three origins.

The final selection favours the first candidate in the predefined simplicity ordering whose performance lies within one estimated standard error of the leading candidate.

This procedure reduces unnecessary model complexity when the historical difference in accuracy is small relative to its estimated variability.

The bootstrap standard error is a descriptive estimate based on a limited historical sample.

### 7.10. Fallback Models

Where the available validation evidence is insufficient for reliable candidate comparison, the model uses predefined fallback methods:

- Historical mean for residual generation.
- Naive forecasting for installed capacity.

These fallback decisions are part of the computational methodology and are not evidence of superior empirical performance.

---

## 8. Final Selected Models

The retained final model configuration is summarized below.

| Country | Residual generation | Solar capacity | Wind capacity |
|---|---|---|---|
| Kazakhstan | Drift | Naive | Drift3 |
| Kyrgyzstan | Mean | Damped ETS | Naive |
| Tajikistan | Drift | Naive | Naive |
| Turkmenistan | Mean | Naive | Naive |
| Uzbekistan | AR(1) | Damped ETS | Drift3 |

The selected models are documented in:

`outputs/tables/MODEL_SELECTION.csv`

The estimated parameters, capacity factors, effective sample sizes, and uncertainty inputs are documented in:

`outputs/tables/MODEL_PARAMETERS.csv`

The selected models reflect the implemented validation and simplicity criteria.

They should not be interpreted as universally optimal forecasting models for the corresponding countries.

---

## 9. Forecast Information Boundaries

The final calculation distinguishes electricity generation and installed capacity information cut-offs.

| Parameter | Value |
|---|---:|
| Generation origin | 2024 |
| Capacity information end | 2025 |
| First estimated generation year | 2025 |
| Final forecast year | 2050 |

The 2025 generation estimate is classified as:

`nowcast_capacity_known`

This classification indicates that installed capacity information for 2025 is available even though electricity generation for that year is missing.

The subsequent years 2026–2050 are classified as:

`forecast`

During ordinary historical forecast evaluation, generation and capacity information are restricted to the corresponding historical origin.

Consequently, historical validation of ordinary forecasts is not fully equivalent to validation of the capacity-informed 2025 estimate.

---

## 10. Joint Monte Carlo Uncertainty Framework

The uncertainty simulation is implemented in:

`src/renewable/uncertainty.py`

The final forecast uses:

| Parameter | Value |
|---|---:|
| Joint simulation trajectories | 10,000 |
| Random seed | 20261024 |
| Historical validation trajectories per origin | 2,000 |
| Displayed conditional interval | Q10–Q90 |
| Additional stored interval | Q2.5–Q97.5 |

The simulation represents uncertainty in:

- Residual renewable electricity generation.
- Future solar installed capacity.
- Future wind installed capacity.
- Solar capacity factors.
- Wind capacity factors.
- Within-year capacity exposure.
- Dependence between model components.
- Temporal dependence.

The distribution families and variance approximations are explicit modelling assumptions.

They are not independently established probability laws governing future national electricity systems.

### 10.1. Historical Innovation Bank

Historical one-step forecast errors are used to estimate uncertainty scales and dependence structures.

For installed capacity, up to five of the latest eligible one-year forecast errors are retained.

For capacity factors, eligible historical capacity factor sequences are used.

The innovation bank is restricted to observations available at the corresponding information cut-off.

---

## 11. Installed Capacity Uncertainty

### 11.1. Forecast Mean

The selected capacity forecasting model determines the expected future installed capacity:

**m(h) = Ĉ(T+h)**

### 11.2. Forecast Variance

For trend-based capacity models, the uncertainty approximation is:

**v(h) = σ²h + σ²h² / n_trend**

where:

- σ² is the variance estimated from recent one-year capacity forecast errors.
- h is the forecast horizon measured from the capacity information cut-off.
- n_trend represents the effective number of observations supporting the trend estimate.

The first term represents accumulated process uncertainty.

The second term approximates uncertainty associated with continuation of the estimated trend.

For the naive capacity model:

**v(h) = σ²h**

For `drift3`:

**n_trend = 3**

For other trend-based capacity models:

**n_trend = min[max(n_errors, 1), 5]**

These variance expressions are approximations defined by the research implementation.

### 11.3. Gamma Distribution

Future installed capacity is simulated using a gamma distribution when the forecast mean and variance are positive.

**C(h) ~ Gamma(k, θ)**

The shape parameter is:

**k = m(h)² / v(h)**

The scale parameter is:

**θ = v(h) / m(h)**

These parameters follow from the gamma distribution moments:

**E(C) = kθ**

**Var(C) = kθ²**

The gamma distribution maintains non-negative simulated capacity values.

Where the forecast variance equals zero, the corresponding capacity remains deterministic.

Where the forecast mean equals zero, the simulation does not introduce new positive capacity solely through random variation.

### 11.4. Known Installed Capacity

The 2025 installed capacity is treated as known where available.

Its capacity forecast horizon is zero relative to the final capacity information boundary.

Uncertainty in 2025 electricity generation may still arise from capacity factors, within-year exposure, and residual generation.

### 11.5. Interpretation

The gamma distribution is applied to installed capacity levels rather than individual construction projects.

Simulated capacity may therefore decline between consecutive years.

The simulation does not enforce a project-by-project commissioning schedule or a monotonically increasing installed capacity trajectory.

---

## 12. Residual Generation Uncertainty

The residual generation component is simulated using a non-negative lognormal representation.

### 12.1. Variance Components

The model separates forecast uncertainty into:

- Process variance, p(h).
- Parameter variance, q(h).

The total variance is:

**v(h) = p(h) + q(h)**

The variance calculation depends on the selected residual generation model.

### 12.2. Mean Model

For a historical mean model:

**p(h) = s²**

**q(h) = s² / n**

where s² is the historical sample variance and n is the number of available observations.

### 12.3. Naive Model

For a naive model, the process variance is approximated using the variance of eligible one-year changes:

**p(h) = s²h**

### 12.4. Drift Model

For a drift model:

**p(h) = s²h**

**q(h) = s²h² / n_d**

where n_d is the number of eligible historical changes used in the drift uncertainty calculation.

### 12.5. Linear Trend

The linear trend model uses the residual variance and the standard ordinary least squares approximation of uncertainty in the estimated forecast mean.

### 12.6. Autoregressive Models

For autoregressive models, process uncertainty is obtained from the conditional forecast variance calculated by the statistical library.

Parameter uncertainty is approximated using:

**q(h) ≈ J Cov(θ) Jᵀ**

where:

- θ is the estimated parameter vector.
- Cov(θ) is its estimated covariance matrix.
- J is the numerical Jacobian of the forecast with respect to the estimated parameters.

The Jacobian is evaluated through numerical parameter perturbations and state filtering.

### 12.7. Exponential Smoothing

For ETS models, the uncertainty implementation uses an approximate local trend variance structure:

**p(h) ≈ s²h**

**q(h) ≈ s²h² / n**

This is an implementation approximation rather than an exact theoretical ETS prediction interval.

### 12.8. Lognormal Transformation

Let μ(h) be the non-negative forecast mean and v(h) the corresponding total variance.

The moment-matched lognormal variance is:

**σ_log² = ln[1 + v(h) / μ(h)²]**

The corresponding log-scale mean is:

**μ_log = ln[μ(h)] − σ_log² / 2**

The simulated generation can be represented as:

**G_H(h) = exp[μ_log + σ_log Z]**

where Z is a standard normal latent variable.

The implementation incorporates the process and parameter uncertainty components into the joint simulation, including shared parameter effects across forecast years.

The moment adjustment preserves the intended arithmetic mean under the assumed lognormal representation.

A deterministic zero forecast remains zero.

Lognormality is used to maintain non-negative generation and approximate forecast uncertainty. It is not an empirically established model of future hydrological conditions.

---

## 13. Capacity Factor Uncertainty

### 13.1. Capacity Factor Variance

The variance of eligible historical capacity factor observations is adjusted for estimation uncertainty:

**v_CF = s_CF² × [1 + 1 / max(n_eff, 1)]**

where:

- s_CF² is the historical sample variance.
- n_eff is the effective sample size.

The variance is restricted to:

**v_CF ≤ 0.99μ(1−μ)**

where μ is the estimated capacity factor.

This restriction ensures that the corresponding beta distribution parameters remain admissible.

### 13.2. Beta Distribution

Capacity factors are simulated using a beta distribution:

**CF ~ Beta(a, b)**

The parameters are obtained from the specified mean and variance.

Define:

**κ = μ(1−μ) / v_CF − 1**

Then:

**a = μκ**

**b = (1−μ)κ**

The beta distribution constrains simulated capacity factors to the interval from zero to one.

When the variance is zero, the capacity factor remains deterministic.

Boundary means of zero or one are also retained as deterministic values.

### 13.3. Interpretation

The beta distribution imposes a general admissible range for capacity utilization.

It does not impose technology-specific engineering limits or country-specific resource constraints.

Consequently, physically admissible individual capacity factor draws do not establish the feasibility of the complete future electricity system.

---

## 14. Dependence Between Forecast Components

Independent simulations could misrepresent uncertainty where generation, installed capacity, and utilization are historically related.

The framework therefore incorporates an approximate dependence structure using correlated latent normal variables.

### 14.1. Historical Correlation Estimation

Pairwise correlations are estimated from historical innovation sequences when at least four common observations are available.

Unavailable pairwise correlations are assigned zero.

The diagonal elements of the correlation matrix are set to one.

### 14.2. Correlation Shrinkage

The estimated correlation matrix is shrunk toward independence:

**R = 0.5R_raw + 0.5I**

where:

- R_raw is the historical correlation estimate.
- I is the identity matrix.

Shrinkage reduces the influence of unstable correlation estimates derived from short historical series.

### 14.3. Positive-Definite Adjustment

Eigenvalues below 10⁻⁸ are replaced by 10⁻⁸.

The resulting matrix is normalized to restore a valid correlation structure.

This adjustment permits numerical Cholesky decomposition.

### 14.4. Correlated Latent Variables

Joint latent normal variables are generated using:

**Z = Lε**

where:

- ε is a vector of independent standard normal variables.
- L is the Cholesky factor of the adjusted correlation matrix.

The latent normal variables are transformed into the required marginal distributions.

### 14.5. Distribution Transformation

The normal cumulative distribution function converts latent normal values into probabilities.

The corresponding gamma and beta quantile functions transform these probabilities into installed capacity and capacity factor draws.

Probabilities are restricted to:

**[10⁻¹⁰, 1−10⁻¹⁰]**

This numerical restriction avoids infinite or unstable inverse-distribution evaluations at the boundaries.

### 14.6. Temporal Dependence

Where at least five eligible adjacent-year pairs are available, temporal dependence is approximated using half of the estimated lag-one correlation.

The resulting coefficient is restricted to the interval:

**[−0.8, 0.8]**

Shared parameter uncertainty is also propagated across forecast years.

The dependence parameters are estimated on the latent normal scale.

Correlations between the transformed physical quantities may differ from the latent correlations.

---

## 15. Conversion of Installed Capacity into Electricity Generation

Future solar and wind electricity generation is calculated using simulated installed capacity, simulated capacity factors, and calendar-year operating hours.

### 15.1. Within-Year Capacity Exposure

The effective operating capacity is represented as:

**C_op(t) = C(t−1) + α(t)[C(t) − C(t−1)]**

where:

**α(t) ~ Uniform(0,1)**

The parameter α approximates the unknown fraction of the year during which the net capacity change contributes to electricity generation.

The uniform distribution is adopted because detailed project commissioning dates are unavailable in the primary statistical dataset.

It is not estimated from an observed construction or commissioning schedule.

### 15.2. Solar Electricity Generation

**G_S(t) = CF_S(t) × C_op,S(t) × L(t) / 1000**

### 15.3. Wind Electricity Generation

**G_W(t) = CF_W(t) × C_op,W(t) × L(t) / 1000**

### 15.4. Retirement and Degradation

The principal forecast assumes:

- Additional explicit retirement rate = 0.
- Additional explicit degradation rate = 0.

Sensitivity calculations introduce alternative retirement and degradation assumptions.

The retirement adjustment modifies future expected capacity using:

**C_adjusted(t) = C(t) × (1−r)^(t−T_C)**

where T_C is the capacity information cut-off.

Additional degradation is represented through a corresponding multiplicative adjustment to future capacity factors.

These adjustments represent supplementary stress assumptions applied to the statistical capacity trajectory rather than identified plant-level retirement schedules.

---

## 16. Aggregation of Simulation Results

For each simulation trajectory i and forecast year t:

**G_RE,i(t) = G_H,i(t) + G_S,i(t) + G_W,i(t)**

The total generation distribution is calculated by summing the components within each joint simulation trajectory.

### 16.1. Central Forecast

The central forecast is the arithmetic mean of total simulated electricity generation:

**G_central(t) = ΣG_RE,i(t) / N**

where N = 10,000.

The central forecast is not the median of the simulated distribution.

### 16.2. Median

The median is calculated as the 50th percentile:

**G_median(t) = Q0.50[G_RE(t)]**

The median may differ substantially from the arithmetic mean when the simulated distribution is asymmetric.

### 16.3. Conditional 80% Interval

The displayed uncertainty interval is defined by:

**Lower bound = Q0.10[G_RE(t)]**

**Upper bound = Q0.90[G_RE(t)]**

The interval contains the central 80% of simulated annual outcomes under the specified model assumptions.

It is not a confidence interval for the estimated mean.

It is also not a simultaneous 80% probability region for the complete 2025–2050 trajectory.

### 16.4. Additional 95% Interval

The output table additionally stores:

- Q0.025.
- Q0.975.

These quantiles are not displayed in the principal four-panel visualization.

Their empirical long-term coverage has not been established.

### 16.5. Monte Carlo Standard Error

The numerical standard error of the simulated mean is calculated as:

**MCSE(t) = SD[G_RE(t)] / √N**

MCSE measures the computational precision of the estimated simulation mean conditional on the specified model.

It does not measure total forecast error or structural model uncertainty.

Increasing the number of simulations reduces Monte Carlo sampling error but does not correct inaccurate input data or unsupported modelling assumptions.

### 16.6. Aggregation Consistency

The mean of total generation equals the sum of the component means.

However, the total generation quantiles are not calculated by summing the individual component quantiles.

Similarly, multiplying mean installed capacity by mean capacity factor does not necessarily reproduce mean simulated generation because the simulation includes dependence and within-year capacity exposure.

---

## 17. Outer Historical Forecast Evaluation

The complete forecasting procedure is evaluated using outer historical origins from 2011 to 2023.

At each origin, the candidate selection procedure is repeated using only eligible historical information.

The selected models are then evaluated against subsequent observed renewable electricity generation.

The available validation sample sizes are:

| Forecast horizon | Observations per country |
|---|---:|
| 1 year | 13 |
| 3 years | 11 |
| 5 years | 9 |
| 10 years | 4 |

The outer evaluation assesses the historical performance of the complete model selection and forecasting procedure rather than only the performance of a single final fitted model.

### 17.1. Comparison with Baseline Forecasts

The following table reports retained outer-validation MAE values for the selected procedure and simple total-generation baselines.

All values are expressed in GWh.

| Country | Horizon | Selected procedure | Naive | Mean |
|---|---:|---:|---:|---:|
| Kazakhstan | 1 | 1,056.61 | 951.03 | 3,086.57 |
| Kazakhstan | 3 | 2,029.93 | 2,145.45 | 3,864.94 |
| Kazakhstan | 5 | 3,608.89 | 3,235.15 | 4,736.07 |
| Kazakhstan | 10 | 6,584.11 | 6,620.52 | 6,608.54 |
| Kyrgyzstan | 1 | 1,024.89 | 806.20 | 962.01 |
| Kyrgyzstan | 3 | 1,094.22 | 1,606.87 | 999.69 |
| Kyrgyzstan | 5 | 927.62 | 1,605.64 | 925.61 |
| Kyrgyzstan | 10 | 524.08 | 1,257.57 | 504.29 |
| Tajikistan | 1 | 455.92 | 491.62 | 2,015.32 |
| Tajikistan | 3 | 1,182.96 | 1,065.99 | 2,383.12 |
| Tajikistan | 5 | 2,040.09 | 1,852.62 | 2,938.16 |
| Tajikistan | 10 | 3,936.53 | 3,556.41 | 4,140.27 |
| Uzbekistan | 1 | 1,256.20 | 932.52 | 1,212.58 |
| Uzbekistan | 3 | 1,720.92 | 1,687.93 | 1,494.67 |
| Uzbekistan | 5 | 1,837.17 | 2,128.58 | 1,826.69 |
| Uzbekistan | 10 | 2,363.39 | 2,417.29 | 2,356.79 |

The selected component-based procedure does not consistently outperform simple naive or historical mean forecasts.

This result is retained explicitly because the physical interpretability of the forecasting architecture does not establish superior statistical accuracy.

The historical validation results should be considered when interpreting the long-term central forecasts.

---

## 18. Uncertainty Interval Validation

Historical uncertainty interval performance is evaluated using empirical coverage and interval width.

### 18.1. Empirical Coverage

For a historical interval with lower bound Lᵢ and upper bound Uᵢ:

**Coverage = ΣI(Lᵢ ≤ yᵢ ≤ Uᵢ) / n**

where I is an indicator function.

### 18.2. Mean Interval Width

**Mean width = Σ(Uᵢ − Lᵢ) / n**

Coverage and width are evaluated jointly because arbitrarily wide intervals can achieve high coverage without providing informative forecasts.

### 18.3. Interval Score

For a nominal interval level of 1−α:

**IS = (U−L) + (2/α)(L−y)I(y<L) + (2/α)(y−U)I(y>U)**

The score penalizes both interval width and observations falling outside the interval.

Lower values indicate better historical interval performance.

### 18.4. Weighted Interval Score

The implementation also evaluates the weighted interval score using the median and the stored 80% and 95% intervals.

The metric combines absolute median error with weighted interval scores.

### 18.5. Retained Historical Coverage

| Country | 1 year | 3 years | 5 years | 10 years |
|---|---:|---:|---:|---:|
| Kazakhstan | 69.23% | 54.55% | 11.11% | 0.00% |
| Kyrgyzstan | 76.92% | 90.91% | 100.00% | 100.00% |
| Tajikistan | 84.62% | 54.55% | 33.33% | 0.00% |
| Uzbekistan | 69.23% | 63.64% | 55.56% | 50.00% |

These results demonstrate that the nominal 80% intervals are not consistently calibrated across countries and forecast horizons.

In particular, none of the four available ten-year validation observations for Kazakhstan and Tajikistan fell within the corresponding nominal 80% intervals.

The limited sample sizes and dependence between overlapping forecast errors further restrict the interpretation of empirical coverage.

The 2050 forecast intervals must therefore be interpreted as conditional model-based simulation ranges rather than empirically validated probability intervals.

### 18.6. Additional Calibration Diagnostics

The script:

`src/calibration.py`

evaluates an additional historical error-based calibration procedure.

For n eligible historical absolute errors and nominal coverage level p, the selected order statistic has rank:

**k = ceil[(n+1)p]**

A finite calibration radius is available only when k does not exceed n.

At least four eligible errors are required for the 80% level and at least 19 for the 95% level.

The calibration procedure uses historical errors from the same forecast horizon whose target observations are already available.

Because the historical errors are limited and dependent, the procedure is treated as a diagnostic rather than a guarantee of future coverage.

The calibrated diagnostic intervals do not automatically replace the Monte Carlo quantiles displayed in the principal figure.

---

## 19. Statistical Diagnostics

Additional diagnostics are implemented in:

`src/renewable/diagnostics.py`

The retained diagnostic procedures include:

| Diagnostic | Purpose |
|---|---|
| Augmented Dickey–Fuller | Examination of unit-root behaviour |
| KPSS | Examination of level stationarity |
| CUSUM | Examination of linear-model residual stability |
| Ljung–Box | Examination of historical forecast-error autocorrelation |

Where a continuous series is required, the latest eligible continuous segment is used.

Short or constant series may be classified as unsuitable for a particular diagnostic.

These tests are interpreted cautiously because the available annual historical series contain at most 25 generation observations.

Diagnostic results are not used as automatic justification for removing individual observations.

The results are stored in:

`outputs/tables/DIAGNOSTICS.csv`

---

## 20. Principal Forecast Results

### 20.1. Central Forecasts

The retained central estimates are summarized below.

Values are expressed in TWh/year and rounded to two decimal places.

| Country | 2024 observed | 2025 estimated | 2030 | 2040 | 2050 |
|---|---:|---:|---:|---:|---:|
| Kazakhstan | 17.66 | 18.58 | 23.50 | 32.91 | 42.26 |
| Kyrgyzstan | 12.94 | 12.93 | 13.39 | 14.36 | 15.21 |
| Tajikistan | 20.88 | 21.16 | 22.60 | 25.41 | 28.31 |
| Uzbekistan | 12.91 | 19.75 | 53.95 | 121.68 | 183.22 |

The numerical precision shown in the table supports reproducibility and does not imply equivalent predictive precision.

### 20.2. Forecast Distribution in 2050

| Country | Mean, TWh | Median, TWh | Q10, TWh | Q90, TWh |
|---|---:|---:|---:|---:|
| Kazakhstan | 42.26 | 41.57 | 33.06 | 52.35 |
| Kyrgyzstan | 15.21 | 14.83 | 12.51 | 18.36 |
| Tajikistan | 28.31 | 27.98 | 22.98 | 34.03 |
| Uzbekistan | 183.22 | 128.54 | 39.51 | 422.71 |

### 20.3. Generation Components in 2050

| Country | Hydro and other, TWh | Solar, TWh | Wind, TWh |
|---|---:|---:|---:|
| Kazakhstan | 15.352 | 2.174 | 24.734 |
| Kyrgyzstan | 12.861 | 2.345 | 0.000 |
| Tajikistan | 28.305 | 0.00038 | 0.000 |
| Uzbekistan | 7.506 | 128.929 | 46.784 |

Minor differences between displayed component sums and total generation may arise from rounding.

---

## 21. Country-Specific Interpretation

### 21.1. Kazakhstan

The statistical forecast for Kazakhstan reaches approximately 42.26 TWh in 2050.

The principal growth components are:

- Continuation of residual generation through the drift model.
- Expansion of wind capacity through the recent three-year drift model.

Solar capacity is maintained at the latest available level under the selected naive model.

The absence of substantial projected solar capacity growth is a consequence of the statistical model selection procedure.

It does not imply that future solar projects are absent or unlikely.

The mean simulated installed capacities in 2050 are approximately:

- Solar: 1,325.30 MW.
- Wind: 8,583.41 MW.

The relatively weak historical interval coverage at longer horizons limits confidence in the displayed uncertainty range.

### 21.2. Kyrgyzstan

The central forecast reaches approximately 15.21 TWh in 2050.

Residual generation is modelled using the historical mean, while solar capacity is projected using damped exponential smoothing.

Most systematic growth in the statistical trajectory therefore originates from the solar component.

The mean simulated solar capacity in 2050 is approximately 1,383.54 MW.

Wind generation remains zero under the retained capacity model.

The statistical forecast does not explicitly incorporate future major hydropower projects.

Such projects are addressed separately in the project-based scenario framework.

### 21.3. Tajikistan

The central forecast reaches approximately 28.31 TWh in 2050.

The trajectory is dominated by the residual generation component, modelled using the drift method.

Solar and wind capacity models remain at their latest available levels.

The resulting solar contribution is small, and wind generation remains zero.

These outcomes reflect the historical capacity observations and selected statistical models rather than a comprehensive assessment of future renewable energy potential.

### 21.4. Turkmenistan

Turkmenistan remains part of the underlying statistical framework.

The retained models are the historical mean for residual generation and naive models for solar and wind capacity.

Its observations also contribute to the data preparation and pooled capacity factor framework where eligible.

Turkmenistan is excluded from the principal four-panel visualization, not from the computational dataset.

### 21.5. Uzbekistan

Uzbekistan has the highest central statistical forecast among the four displayed countries.

The mean generation estimate reaches approximately 183.22 TWh in 2050.

The result is driven primarily by:

- Damped exponential smoothing of solar installed capacity.
- Continuation of recent wind capacity additions through the `drift3` model.
- An AR(1) model for residual generation.

The mean simulated installed capacities in 2050 are:

| Technology | Mean capacity |
|---|---:|
| Solar | 70,186.29 MW |
| Wind | 15,444.63 MW |
| Combined | 85,630.92 MW |

These capacity estimates are statistical extrapolations rather than confirmed construction commitments.

The simulated generation distribution is strongly asymmetric.

The mean of 183.22 TWh exceeds the median of 128.54 TWh because of the long upper tail of the simulated distribution.

The conditional Q10–Q90 range extends from approximately 39.51 to 422.71 TWh.

The high forecast and wide range should be interpreted in the context of:

- Rapid recent changes in installed capacity.
- Short technology-specific historical series.
- Inconsistent historical generation-to-capacity ratios.
- Low effective sample sizes for capacity factor estimation.
- Uncertainty in the continuation of recent capacity growth.
- Absence of explicit long-term grid, demand, investment, and technology saturation constraints.

The statistical model does not establish that the projected capacity or generation levels are economically or technically achievable.

---

## 22. Sensitivity Analysis

Sensitivity analysis evaluates the dependence of forecast results on alternative modelling assumptions.

The main sensitivity outputs are stored in:

`outputs/tables/SENSITIVITY_ANALYSIS.csv`

### 22.1. Evaluated Assumptions

The sensitivity framework includes variations in:

- Capacity commissioning exposure.
- Capacity factor estimation windows.
- Dependence between model components.
- Additional installed capacity retirement.
- Additional capacity factor degradation.
- Alternative installed capacity forecasting models.
- Alternative residual generation models.

The main sensitivity calculations use up to 4,000 simulation trajectories.

Differences between sensitivity results may therefore include Monte Carlo sampling variability.

### 22.2. Boundary Sensitivity

Additional numerical boundary tests are implemented in:

`src/boundary_sensitivity.py`

These tests include:

- Alternative probability truncation thresholds of 10⁻⁶ and 10⁻¹².
- Fixed within-year capacity exposure of α = 0.5.
- Alternative capacity factor restrictions.
- A minimum installed capacity threshold of 20 MW.

The results are stored in:

`outputs/tables/BOUNDARY_SENSITIVITY.csv`

### 22.3. Model Sensitivity

The script:

`src/model_sensitivity.py`

evaluates the dependence of the forecast on alternative model specifications.

This analysis is important for long-term projections because several candidate models may have similar historical validation errors but substantially different extrapolated trajectories.

### 22.4. Management Sensitivity Range

The file:

`outputs/tables/MANAGEMENT_FORECAST.csv`

contains the range of minimum and maximum mean generation estimates across 24 specified alternative assumptions.

No probability weights are assigned to these alternatives.

The management sensitivity range is distinct from the Q10–Q90 Monte Carlo interval.

It is not used as the shaded region in the principal figure.

---

## 23. Principal Visualization

The current four-panel figure is generated using:

`src/figure_color_shared_scale.py`

The visualization reads two retained numerical tables:

`outputs/tables/PREPARED_DATA.csv`

`outputs/tables/FORECAST_2025_2050_CORRECTED.csv`

The plotting script does not independently re-estimate the forecasting models.

### 23.1. Figure Components

| Visual element | Meaning |
|---|---|
| Solid line with markers | Historical IRENA generation observations |
| Dashed line | Mean simulated annual generation |
| Shaded region | Conditional Q10–Q90 simulation range |
| Vertical dotted line | Historical and forecast boundary at 2024.5 |

The historical period extends from 2000 through 2024.

The estimated and forecast period extends from 2025 through 2050.

### 23.2. Axis Configuration

Kazakhstan, Kyrgyzstan, and Tajikistan use a common linear vertical scale:

**0–60,000 GWh/year.**

Uzbekistan uses a separate linear vertical scale:

**0–450,000 GWh/year.**

All panels start at zero.

Because Uzbekistan uses a different vertical scale, visual comparisons of line height across panels require reference to the corresponding numerical axis.

Year labels are rotated by 45 degrees.

### 23.3. Country Colours

| Country | Colour |
|---|---|
| Kazakhstan | `#176b87` |
| Kyrgyzstan | `#f28e2b` |
| Tajikistan | `#5b8e7d` |
| Uzbekistan | `#c94c4c` |

### 23.4. Figure Outputs

The retained principal figure files are:

`outputs/figures/Figure_S1_Color_SharedScale_TNR25_Bold.png`

`outputs/figures/Figure_S1_Color_SharedScale_TNR25_Bold.pdf`

The default publication formatting uses Times New Roman Bold, 25 pt.

Alternative 30 pt and 36 pt versions can be exported without replacing the default figure.

The internal figure identifier is retained for reproducibility and may differ from the final figure numbering in the associated manuscript.

---

## 24. Repository Structure

```text
Renewable_Forecast_Supplementary/
│
├── data/
│   └── raw/
│       └── ELEC-C_20261019-070746.csv
│
├── src/
│   ├── renewable/
│   │   ├── data.py
│   │   ├── models.py
│   │   ├── validation.py
│   │   ├── uncertainty.py
│   │   └── diagnostics.py
│   │
│   ├── run_pipeline.py
│   ├── run_all.py
│   ├── calibration.py
│   ├── boundary_sensitivity.py
│   ├── model_sensitivity.py
│   ├── check_output_tables.py
│   ├── release_summary.py
│   ├── legacy_backtest.py
│   ├── verify_outputs.py
│   ├── figure3_area_redesign.py
│   └── figure_color_shared_scale.py
│
├── outputs/
│   ├── tables/
│   ├── figures/
│   ├── RUN_MANIFEST.json
│   ├── PACKAGE_INTEGRITY.json
│   └── test_results.txt
│
├── tests/
├── legacy/
├── methodology_audit/
├── Supplementary_Color_Figure_Methods.docx
├── requirements.txt
├── requirements-lock.txt
└── README.md
```

### 24.1. Core Statistical Modules

| Module | Function |
|---|---|
| `data.py` | Historical preprocessing and data quality checks |
| `models.py` | Forecasting models and capacity factor estimation |
| `validation.py` | Historical validation and model selection |
| `uncertainty.py` | Joint uncertainty simulation |
| `diagnostics.py` | Statistical diagnostics |

### 24.2. Workflow Scripts

| Script | Function |
|---|---|
| `run_pipeline.py` | Main forecasting calculation |
| `run_all.py` | Complete statistical workflow |
| `calibration.py` | Historical interval calibration diagnostics |
| `boundary_sensitivity.py` | Numerical boundary sensitivity |
| `model_sensitivity.py` | Alternative model sensitivity |
| `check_output_tables.py` | Output consistency and comparison checks |
| `release_summary.py` | Final result reporting |
| `legacy_backtest.py` | Historical comparison with the legacy model |
| `verify_outputs.py` | Output verification |
| `figure_color_shared_scale.py` | Principal four-panel visualization |

---

## 25. Output Data Documentation

The retained package contains 27 CSV tables covering prepared historical data, model selection, forecasting, validation, and sensitivity analysis.

### 25.1. Principal Output Tables

| File | Description |
|---|---|
| `PREPARED_DATA.csv` | Prepared historical country-year dataset |
| `DATA_QUALITY_AUDIT.csv` | Data preparation decisions and inconsistencies |
| `MODEL_SELECTION.csv` | Historical and final model selections |
| `MODEL_PARAMETERS.csv` | Estimated model and uncertainty parameters |
| `BACKTEST_RESULTS.csv` | Historical forecast evaluation |
| `UNCERTAINTY_VALIDATION.csv` | Historical interval performance |
| `FORECAST_2025_2050_CORRECTED.csv` | Principal annual forecast results |
| `DIAGNOSTICS.csv` | Statistical diagnostics |
| `SENSITIVITY_ANALYSIS.csv` | Main sensitivity calculations |
| `BOUNDARY_SENSITIVITY.csv` | Numerical boundary sensitivity |
| `MANAGEMENT_FORECAST.csv` | Alternative-assumption range |
| `OLD_VS_CORRECTED.csv` | Comparison with the legacy forecast |

### 25.2. Prepared Historical Data

`PREPARED_DATA.csv` contains 130 country-year records:

**5 countries × 26 years.**

The main variables include:

| Column | Description |
|---|---|
| `country` | Country |
| `year` | Calendar year |
| `ren` | Reported total renewable generation |
| `nonren` | Reported total non-renewable generation |
| `cap_ren` | Reported total renewable capacity |
| `gen_solar` | Prepared solar generation |
| `gen_wind` | Prepared wind generation |
| `cap_solar` | Prepared solar capacity |
| `cap_wind` | Prepared wind capacity |
| `hydro_other` | Residual renewable generation |
| `cap_hydro_other` | Remaining renewable capacity |
| `cf_solar` | Historical solar capacity factor |
| `cf_wind` | Historical wind capacity factor |
| `cf_hydro_other` | Descriptive residual capacity factor |

Generation values are expressed in GWh and capacity values in MW.

### 25.3. Principal Forecast Dataset

`FORECAST_2025_2050_CORRECTED.csv` contains annual forecasts for the five countries over 2025–2050.

| Column | Description |
|---|---|
| `country` | Country |
| `year` | Forecast year |
| `origin_generation` | Generation information cut-off |
| `capacity_information_end` | Capacity information cut-off |
| `horizon_from_generation_origin` | Forecast horizon relative to 2024 |
| `central_GWh` | Mean total simulated generation |
| `median_GWh` | Median total simulated generation |
| `mc_standard_error_GWh` | Monte Carlo standard error |
| `hydro_other_GWh` | Mean residual generation |
| `solar_GWh` | Mean solar generation |
| `wind_GWh` | Mean wind generation |
| `capacity_solar_MW` | Mean simulated solar capacity |
| `capacity_wind_MW` | Mean simulated wind capacity |
| `cf_solar` | Mean simulated solar capacity factor |
| `cf_wind` | Mean simulated wind capacity factor |
| `lo80_GWh` | 10th percentile |
| `hi80_GWh` | 90th percentile |
| `lo95_GWh` | 2.5th percentile |
| `hi95_GWh` | 97.5th percentile |
| `empirical_95_validated` | Empirical validation status |
| `long_term_probability_claim` | Long-term probability claim status |

The retained validation flags do not establish empirical 95% coverage or a validated long-term probability claim.

---

## 26. Computational Environment

The retained calculation environment is documented in:

`outputs/RUN_MANIFEST.json`

The recorded software versions include:

| Software | Version |
|---|---|
| Python | 3.12.14 |
| NumPy | 2.3.5 |
| pandas | 2.2.3 |
| SciPy | 1.17.0 |
| statsmodels | 0.14.6 |
| Matplotlib | 3.10.8 |

Dependency information is provided in:

- `requirements.txt`
- `requirements-lock.txt`

For numerical reproducibility, the recorded software versions should be preferred over unverified newer versions.

Differences in statistical library implementations and numerical optimization may affect reproduced results.

---

## 27. Reproduction Instructions

### 27.1. Create a Python Environment

Navigate to the repository root.

Create a dedicated Python virtual environment:

```bash
python -m venv .venv
```

Activate the environment on Windows:

```cmd
.venv\Scripts\activate
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

### 27.2. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

The retained dependency lock file can be consulted when reproducing the original calculation environment.

### 27.3. Run the Complete Forecasting Workflow

```bash
python src/run_all.py
```

The script executes the following sequence:

1. `run_pipeline.py`
2. `calibration.py`
3. `boundary_sensitivity.py`
4. `model_sensitivity.py`
5. `check_output_tables.py`
6. `release_summary.py`

The workflow regenerates the forecasting and diagnostic output tables.

The principal figure is exported separately.

### 27.4. Run the Statistical Pipeline Separately

```bash
python src/run_pipeline.py
```

To write the main pipeline outputs to a separate directory:

```bash
python src/run_pipeline.py --output /absolute/path
```

Additional reporting scripts may continue to use the standard output directory unless separately configured.

### 27.5. Generate the Principal Figure

```bash
python src/figure_color_shared_scale.py
```

If Times New Roman is not available through the operating system, specify a directory containing locally licensed font files:

```bash
python src/figure_color_shared_scale.py --font-dir PATH
```

To export a separate 30 pt version:

```bash
python src/figure_color_shared_scale.py --font-dir PATH --font-size 30
```

To export a separate 36 pt version:

```bash
python src/figure_color_shared_scale.py --font-dir PATH --font-size 36
```

The repository does not redistribute proprietary font files.

The figure can be regenerated directly from the retained historical and forecast tables without repeating the complete statistical estimation.

### 27.6. Preserve the Original Results

The complete forecasting workflow may overwrite generated output files.

For comparison with the retained research release, reproduction should preferably be performed in a separate copy of the repository.

The `legacy/` directory should not be removed without reviewing the existing pipeline dependencies.

The main workflow uses retained legacy forecast outputs for historical comparison, even when execution of the legacy calculation itself is skipped.

---

## 28. Automated Tests and Package Integrity

The automated tests are located in:

`tests/`

Run the test suite using:

```bash
python -m pytest -q
```

The retained test report records:

```text
26 passed in 4.08s
```

The report is stored in:

`outputs/test_results.txt`

The test result documents the successful execution of the retained statistical implementation test suite.

It does not establish that the complete long-running forecasting pipeline was independently re-estimated during every packaging or documentation update.

Package integrity information is stored in:

`outputs/PACKAGE_INTEGRITY.json`

The integrity record documents byte-level agreement of the original calculation core and key retained numerical outputs.

The current package excludes unrelated national target-share scenarios, external project comparisons, and previous editorial reports.

The statistical preparation, forecasting, selection, and simulation functions are retained from the original research release.

---

## 29. Principal Modelling Assumptions

| Assumption | Methodological purpose | Limitation |
|---|---|---|
| Historical patterns remain informative | Enables statistical extrapolation | Structural changes may invalidate historical relationships |
| Residual generation is forecast directly | Uses the longer available generation history | Does not explicitly model future hydropower projects |
| Solar and wind are forecast through capacity | Represents the relationship between infrastructure and generation | Depends on the reliability of capacity forecasts |
| Average adjacent-year capacity approximates historical exposure | Accounts for annual capacity changes | Actual commissioning dates are unavailable |
| Uniform within-year exposure | Represents unknown commissioning timing | Distribution is not empirically estimated |
| Recent capacity factors remain informative | Converts future capacity into generation | Future operating conditions may differ |
| Pooled capacity factors | Supports countries with insufficient local observations | May not represent national resource conditions |
| Gamma capacity distribution | Maintains non-negative capacity | Does not impose construction or saturation constraints |
| Lognormal residual generation | Maintains non-negative generation | Distribution is a modelling assumption |
| Beta capacity factor distribution | Restricts capacity factors to admissible values | Does not impose technology-specific operating limits |
| Correlation shrinkage | Stabilizes dependence estimation | Historical dependence estimates remain uncertain |
| Zero additional retirement and degradation | Defines the central statistical case | May overstate future effective capacity or output |
| Non-negative forecast levels | Maintains physical admissibility | Does not establish system-level feasibility |

---

## 30. Research Limitations

### 30.1. Historical Data Availability

The historical generation series contains at most 25 annual observations.

Solar and wind technologies have substantially shorter effective historical series in several countries.

This limits the reliability of long-term trend estimation and uncertainty calibration.

### 30.2. Source Data Inconsistencies

The retained dataset contains missing values, classification anomalies, and inconsistent generation-to-capacity ratios.

Preprocessing and capacity factor eligibility rules reduce their direct influence on the simulation.

They do not independently resolve the underlying statistical reporting issues.

### 30.3. Historical Data Revisions

The retained export does not provide a complete history of data revisions or publication dates for individual observations.

Historical validation therefore does not reproduce all information conditions that would have existed at each past forecast origin.

### 30.4. Long-Term Capacity Growth

The statistical capacity models do not explicitly incorporate national investment constraints, project financing, land availability, grid connection limits, or technology saturation.

Recent capacity expansion may therefore generate substantial long-term extrapolations.

### 30.5. Hydrological and Climate Factors

The residual generation model does not contain a dedicated representation of:

- Future river discharge.
- Reservoir operation.
- Glacier retreat.
- Climate change.
- Seasonal water availability.
- Regional water allocation.

These factors are reflected only indirectly through historical generation patterns.

### 30.6. Electricity System Constraints

The framework does not model:

- Electricity demand.
- Hourly dispatch.
- Transmission network capacity.
- Storage requirements.
- Curtailment.
- Electricity imports and exports.
- Investment optimization.
- National electricity market equilibrium.

Consequently, the forecast does not establish whether the simulated generation can be fully integrated into future electricity systems.

### 30.7. Historical Forecast Performance

The selected statistical procedure does not consistently outperform simple naive and historical mean benchmarks.

The nominal uncertainty intervals also exhibit substantial historical undercoverage for several countries and forecast horizons.

These findings limit the strength of empirical accuracy claims.

### 30.8. Forecast Horizon

Historical validation extends to a maximum horizon of ten years.

The final forecast extends 26 years beyond the latest available generation observation.

The reliability of the conditional uncertainty intervals at the 2050 horizon has not been empirically established.

### 30.9. Interpretation of Results

The reported values should be interpreted as conditional statistical forecasts under the specified historical data, model architecture, parameter estimates, and simulation assumptions.

They should not be interpreted as:

- Official national electricity generation targets.
- Confirmed future infrastructure deployment.
- Guaranteed electricity generation outcomes.
- Optimized energy transition pathways.
- Empirically calibrated long-term probability forecasts.

---

## 31. References

### Primary Numerical Data

1. International Renewable Energy Agency (IRENA). IRENASTAT. *Electricity statistics by Country/area, Technology, Data Type, Grid connection and Year*. Table ELEC-C. Retained data export: `ELEC-C_20261019-070746.csv`.

   https://pxweb.irena.org/

### Methodological References

2. McKenzie, E., & Gardner, E. S., Jr. (2010). Damped trend exponential smoothing: A modelling viewpoint. *International Journal of Forecasting, 26*(4), 661–665.

   https://doi.org/10.1016/j.ijforecast.2009.07.001

3. Hyndman, R. J., & Koehler, A. B. (2006). Another look at measures of forecast accuracy. *International Journal of Forecasting, 22*(4), 679–688.

   https://doi.org/10.1016/j.ijforecast.2006.03.001

4. Van Poecke, A., Tabari, H., & Hellinckx, P. (2024). Unveiling the backbone of the renewable energy forecasting process: Exploring direct and indirect methods and their applications. *Energy Reports, 11*, 544–557.

   https://doi.org/10.1016/j.egyr.2023.12.031

These publications provide methodological support for damped trend forecasting, forecast accuracy assessment, and direct versus indirect renewable energy forecasting architectures.

Their national datasets and numerical findings are not used as inputs to the statistical forecasts in this repository.

The specific combination of forecasting models, selection rules, capacity factor estimation, variance approximations, dependence structures, and Monte Carlo simulations constitutes the implementation developed for the associated research.

---

## 32. Associated Research

**Renewable Energy Prospects and Challenges in Central Asia**

Aigerim Tolegenkyzy, Sungat Rysbek, Nurlan Idrissov, Zhengisbek Kuspanov, Aigerim Serik, and Chingis Daulbayev.

Electrochemical Conversion and Energy Storage Laboratory, Institute of Nuclear Physics, Almaty, Kazakhstan.

Satbayev University, Almaty, Kazakhstan.

Additional methodological documentation is provided in:

`Supplementary_Color_Figure_Methods.docx`

This repository provides the reproducible statistical forecasting materials supporting the historical and projected renewable electricity generation analysis through 2050.
