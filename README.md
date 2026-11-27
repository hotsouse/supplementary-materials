# Renewable Electricity Generation Scenarios in Central Asia to 2050

## 1. Research Scope

This repository contains the computational framework, historical datasets, project-level evidence, scenario assumptions, validation procedures, and visualization scripts associated with the study **“Renewable Energy Prospects and Challenges in Central Asia.”**

The analysis examines potential renewable electricity generation pathways in five Central Asian countries:

- Kazakhstan
- Kyrgyzstan
- Tajikistan
- Turkmenistan
- Uzbekistan

Three conditional development scenarios are constructed for 2026–2050: Business as Usual (BAU), Accelerated, and High Ambition.

The framework combines historical electricity statistics with documented renewable energy projects, commissioning schedules, national development programmes, and explicit assumptions concerning future capacity deployment.

Unlike purely statistical extrapolation, this approach accounts for individual infrastructure projects and their expected contributions to annual electricity generation.

The scenarios are not probabilistic forecasts or optimized national energy transition pathways. They describe possible generation outcomes conditional on the implementation of specified projects and development assumptions.

**Model version:** 4.1 submission package.

**Evidence cut-off date:** 9 November 2026.

---

## 2. Historical Data and Primary Sources

### 2.1. IRENASTAT Dataset

The primary historical dataset is obtained from the International Renewable Energy Agency (IRENA).

Source: [IRENASTAT Electricity Statistics](https://pxweb.irena.org/)

Dataset:

`Electricity statistics by Country/area, Technology, Data Type, Grid connection and Year`

The original data export is preserved in:

`data/raw/ELEC-C_20261019-070746.csv`

The dataset contains electricity generation and installed capacity observations for the five Central Asian countries.

| Parameter | Specification |
|---|---|
| Historical period | 2000–2025 |
| Electricity generation | GWh |
| Installed capacity | MW |
| Grid connection | All |
| Latest available generation year | 2024 |
| Latest available capacity year | 2025 |
| Projection period | 2026–2050 |

The historical dataset includes 6,760 records across five countries, 26 years, 26 technology categories, and two data types.

Missing observations, represented by `..` in the original export, are treated as missing values rather than zero.

The distinction between missing observations and actual zero generation is maintained throughout the computational workflow.

### 2.2. Historical Reference Generation

The following renewable electricity generation values are reported by IRENA for 2024.

| Country | Renewable generation, GWh |
|---|---:|
| Kazakhstan | 17,657.99 |
| Kyrgyzstan | 12,935.80 |
| Tajikistan | 20,878.88 |
| Turkmenistan | 3.35 |
| Uzbekistan | 12,914.80 |

These values represent historical observations and should not be confused with the adjusted reference generation values used in the project-based scenario model.

The adjusted reference values are stored in `data/baselines.csv` and incorporate country-specific evidence where applicable.

### 2.3. Additional Evidence

The historical dataset is supplemented by project-level information and national renewable energy development targets.

Additional evidence includes:

- Official national energy development programmes.
- Government and ministry publications.
- Renewable energy project specifications.
- Published installed capacity and annual generation estimates.
- Project commissioning schedules.
- Nationally determined contributions.
- World Bank analytical reports and project documentation.
- Official renewable electricity generation targets.

The complete source register is provided in:

`data/evidence/sources.csv`

Project inputs are linked to their corresponding evidence through source identifiers. These identifiers distinguish externally documented parameters from modelling assumptions.

The evidence directory also contains methodological notes, source reconciliation records, and explanations of project inclusion and exclusion.

---

## 3. Data Processing and Parameter Preparation

### 3.1. Treatment of Historical Observations

Historical generation and capacity observations are processed separately because they represent different physical quantities.

Electricity generation measures annual energy production, whereas installed capacity represents generating capacity available at the end of the reporting year.

The workflow therefore does not directly interpret installed capacity as annual electricity generation.

Missing generation observations for 2025 are not replaced with zero or automatically treated as observed values.

The model uses available historical observations, documented project information, and explicitly identified reference adjustments.

### 3.2. Project Inventory

The editable project inventory is stored in:

`data/project_inputs.csv`

The processed project ledger is stored in:

`data/projects.csv`

Individual projects or project phases are represented by parameters including:

- Country and renewable energy technology.
- Unique project identifier.
- Installed capacity.
- Expected annual electricity generation.
- First modelled commissioning year.
- First year of full annual operation.
- Commissioning profile.
- First-year generation fraction.
- Capacity already included in the existing fleet.
- Generation already included in the reference baseline.
- Inclusion status.
- Delivery-lock status.
- Energy estimation method.

The project inventory includes infrastructure at different development stages. Inclusion in the BAU portfolio does not imply that every project is fully financed, under construction, or guaranteed to be completed.

### 3.3. Data Consistency

The model validates input identifiers, project parameters, reference generation components, and generation yields before calculating scenario pathways.

The validation procedures reject:

- Duplicate country or project identifiers.
- Unknown project countries.
- Unsupported commissioning profiles.
- Negative project capacity or generation parameters.
- Invalid first-year generation fractions.
- Embedded capacity exceeding total project capacity.
- Embedded generation exceeding total project generation.
- Non-positive or non-finite generation yields.

Historical capacity addition rates that cannot be estimated reliably remain missing. They are not interpreted as zero deployment.

---

## 4. Mathematical Framework

### 4.1. General Scenario Accounting

Annual renewable electricity generation for country c, scenario s, and year t is represented as:

**G(c,s,t) = B(c,t) + P(c,t) + A(c,s,t)**

where:

- G(c,s,t) is total annual renewable electricity generation, GWh/year;
- B(c,t) is generation maintained from the reference fleet;
- P(c,t) is the net annual contribution of projects included in the BAU portfolio;
- A(c,s,t) is the additional contribution associated with Accelerated or High Ambition assumptions.

For BAU:

**A(c,BAU,t) = 0**

Consequently:

**G(c,BAU,t) = B(c,t) + P(c,t)**

The three scenarios share a common project ledger and reference generation framework.

The model verifies that:

**G(c,BAU,t) ≤ G(c,Accelerated,t) ≤ G(c,High Ambition,t)**

This ordering is checked for every country and projection year.

### 4.2. Reference Generation

The central BAU calculation maintains the reference generation of the existing renewable electricity fleet.

The general baseline expression implemented in `src/model.py` is:

**B(t) = [(B₀ − H₀) + kH × H(t)] × kB × (1 − e)^(t − t₀)**

where:

- B₀ is total reference renewable generation;
- H₀ is reference hydropower generation;
- H(t) is the applicable hydropower reference for year t;
- kH is the hydropower adjustment factor;
- kB is the baseline adjustment factor;
- e is the annual reference erosion parameter;
- t₀ is the first projection year.

For the central calculation, the adjustment factors equal one and reference erosion equals zero.

Maintaining reference generation provides a transparent starting point where annual retirement, rehabilitation, degradation, and replacement schedules for the existing fleet are unavailable.

This assumption does not imply that the physical generating fleet remains unchanged through 2050.

### 4.3. Project-Level Generation

The annual contribution of a renewable electricity project is determined from published design generation or estimated using installed capacity and a technology-specific generation yield.

Where annual project generation is unavailable:

**Qⱼ = Cⱼ × Y(c,k)**

where:

- Qⱼ is full annual project generation, GWh/year;
- Cⱼ is installed capacity, MW;
- Y(c,k) is annual generation per MW for country c and technology k, GWh/MW/year.

Published project generation is used directly where the project inventory specifies a source-based annual output estimate.

The model therefore distinguishes between documented project design generation and capacity-derived generation.

### 4.4. Net Additional Generation

To prevent double counting, generation already represented in the reference fleet is deducted from the full annual project contribution.

**Qnet,ⱼ = Qⱼ − Qembedded,ⱼ**

Similarly, net additional installed capacity is calculated as:

**Cnet,ⱼ = max(0, Cⱼ − Cembedded,ⱼ)**

These adjustments are particularly important for partially commissioned infrastructure and projects implemented in multiple phases.

Annual generation is calculated from the net project contribution rather than repeatedly adding the complete project capacity or design generation.

### 4.5. Commissioning Profiles

Project generation is introduced using a commissioning fraction fⱼ(t).

The annual contribution is:

**Pⱼ(t) = Qnet,ⱼ × fⱼ(t)**

Two commissioning profiles are implemented.

#### Step profile

- Before the first commissioning year: fⱼ(t) = 0.
- Between the first and full-operation years: fⱼ(t) = αⱼ.
- From the full-operation year onward: fⱼ(t) = 1.

The parameter αⱼ is specified in the project inventory.

A value of 0.5 is commonly used when the commissioning month is unavailable, approximating half a year of electricity generation.

#### Linear profile

For projects requiring gradual commissioning:

**fⱼ(t) = (t − tfirst + 1) / (tfull − tfirst + 1)**

The commissioning fraction is zero before the first modelled year and one from the full-operation year onward.

Linear commissioning is used to approximate the gradual increase in generation where a detailed annual commissioning schedule is unavailable.

The model distinguishes annual generation exposure from year-end installed capacity. A project operating for half a year does not necessarily have only half of its capacity installed at the end of that year.

---

## 5. Generation Yield Estimation

### 5.1. Historical Capacity Factors

Generation yields for solar photovoltaic and onshore wind technologies are derived using historical observations or documented project design information.

For Kazakhstan, historical capacity factors are calculated from IRENA observations for 2020–2024.

The effective annual capacity is approximated by:

**Cavg(t) = [C(t−1) + C(t)] / 2**

Potential annual generation at full utilization is:

**Emax(t) = Cavg(t) × h(t) / 1000**

where h(t) equals 8,760 hours in a standard year and 8,784 hours in a leap year.

The effective annual capacity factor is:

**CF(t) = G(t) / Emax(t)**

Observations are accepted when the capacity exposure is positive and the calculated capacity factor lies between zero and one.

At least three valid observations are required for the historical yield calculation.

### 5.2. Exposure-Weighted Capacity Factor

The aggregate capacity factor is calculated as:

**CFweighted = ΣG(t) / ΣEmax(t)**

This method weights observations according to their effective capacity exposure rather than assigning equal importance to years with substantially different installed capacities.

The normalized annual generation yield is:

**Y = CFweighted × 8760 / 1000**

The resulting yield is expressed in GWh/MW/year.

### 5.3. Source-Based Design Yields

Where documented project design capacity and annual generation are available, the generation yield is calculated as:

**Ydesign = ΣQⱼ / ΣCⱼ**

This is a capacity-weighted design yield.

The calculation preserves the relationship between documented installed capacity and expected annual generation.

The relevant project design inputs are stored in:

`data/design_yield_inputs.csv`

### 5.4. Transfer of Generation Yields

Where country-specific design information is unavailable, the implementation uses the corresponding Kazakhstan solar or wind yield.

This transfer is explicitly identified in `data/yields.csv`.

The transferred value is not presented as an observed national capacity factor or a statistically representative Central Asian average.

It is a modelling proxy used to maintain computational coverage under limited local evidence.

### 5.5. Hydropower Yield Proxy

For Kazakhstan, a separate hydropower yield proxy is calculated using 2024 renewable hydropower generation divided by installed renewable hydropower capacity.

This coefficient is used for the specified capacity maturation calculation and is not interpreted as a universal hydropower project design yield.

### 5.6. Yield Audit Files

The complete yield calculation is implemented in:

`src/derive_yields.py`

The derived coefficients are stored in:

`data/yields.csv`

The historical observations, calculated capacity factors, capacity exposure, and acceptance flags are exported to:

`outputs/tables/yield_observations.csv`

---

## 6. Historical Capacity Deployment Rates

Historical net capacity addition rates are used in selected scenario components and diagnostic comparisons.

The average annual net capacity addition rate is calculated as:

**R = (Cend − Cstart) / (tend − tstart)**

where:

- R is the annual net capacity addition rate, MW/year;
- Cstart and Cend are installed capacities at the first and last eligible observations;
- tstart and tend are the corresponding observation years.

Two historical windows are configured:

| Window | Period |
|---|---|
| Long-term | 2015–2025 |
| Recent | 2020–2025 |

The configuration requires at least four observations spanning at least three years.

The derived rates are stored in:

`data/deployment_rates.csv`

Historical net additions represent observed changes in installed capacity and are not equivalent to gross construction volumes.

Where suitable observations are unavailable, the corresponding deployment rate remains missing.

### 6.1. Historical Deployment Benchmark

For diagnostic historical deployment calculations, named project additions are credited toward the annual capacity deployment benchmark.

**Cextra(t) = max[0, R(t) − Cnamed,new(t)]**

The generation associated with additional unnamed capacity is:

**Gextra(t) = Y × [Cextra,cumulative(t−1) + α × Cextra(t)]**

The first-year generation fraction α is set to 0.5 in the configuration.

This procedure prevents the complete historical deployment benchmark from being added on top of named projects representing the same capacity additions.

The historical deployment benchmark is separate from the central BAU portfolio.

---

## 7. Business as Usual Scenario

The BAU scenario maintains the reference generation of the existing renewable electricity fleet and adds the net annual contribution of included projects.

**GBAU(t) = B(t) + ΣPⱼ(t)**

The portfolio is constructed from documented renewable energy infrastructure and explicitly identified project assumptions.

The BAU scenario does not automatically introduce undocumented capacity additions after the last included project reaches full operation.

Consequently, generation can stabilize during the later projection years.

Such stabilization reflects the boundaries of the documented project inventory rather than a prediction that renewable energy development will cease.

The scenario includes large hydropower and other renewable electricity generation represented in the reference fleet.

### 7.1. Portfolio Accounting

The following accounting principles are applied:

- Existing generation is not added repeatedly as new generation.
- Previously commissioned capacity is deducted from the additional capacity of partially completed projects.
- Multi-stage infrastructure is represented through its individual commissioning phases.
- Renewable components of hybrid projects are distinguished from non-renewable components.
- Project inclusion and exclusion are controlled by the project ledger.
- Already commissioned or delivery-locked assets are distinguished from future projects in sensitivity calculations.

### 7.2. BAU Outputs

The main portfolio results are stored in:

- `outputs/tables/portfolio_annual_comparison.csv`
- `outputs/tables/portfolio_2030_2040_2050.csv`
- `outputs/tables/project_contributions.csv`
- `outputs/tables/model_references.csv`

Supplementary Figure S1 is generated from the project portfolio and its sensitivity cases.

---

## 8. Accelerated and High Ambition Scenarios

The Accelerated and High Ambition scenarios extend the BAU portfolio using country-specific project additions, development programmes, alternative commissioning dates, and national policy targets.

Additional generation is represented as:

**Gs(t) = GBAU(t) + ΔGs(t)**

where ΔGs(t) is the sum of the scenario-specific contributions.

For a programme with a specified capacity target, the additional generation is calculated from the remaining capacity gap and the corresponding generation yield.

**ΔG(t) = Cgap × Y × F(t)**

For gradually implemented programmes:

**F(t) = clip[(t − tstart + 1) / (tfull − tstart + 1), 0, 1]**

The programme reaches its full modelled generation contribution in the specified target year.

The scenario assumptions are stored in:

`data/scenario_assumptions.json`

The implementation is provided in:

`src/scenarios.py`

---

## 9. Country-Specific Scenario Assumptions

### 9.1. Kazakhstan

Kazakhstan's higher-deployment scenarios incorporate an 8,400 MW renewable energy programme.

The programme is represented as:

| Technology | Modelled capacity |
|---|---:|
| Solar PV | 1,800 MW |
| Wind | 6,600 MW |
| Total | 8,400 MW |

The non-solar remainder is represented as wind for the purpose of converting capacity into annual generation.

This technology allocation is a modelling assumption.

Named projects already included in the BAU portfolio are deducted by technology.

**Cgap,k = max(0, Ctarget,k − Cportfolio,k)**

The remaining programme capacity is introduced gradually from 2027.

| Parameter | Accelerated | High Ambition |
|---|---:|---:|
| Programme start | 2027 | 2027 |
| Programme completion | 2035 | 2033 |
| Continuation start | 2036 | 2036 |

Under Accelerated, deployment after 2035 follows the long-window historical net capacity addition rate for each technology.

Under High Ambition, subsequent deployment follows a policy-based annual rate:

**Rpolicy,k = Ctarget,k / (2035 − 2025)**

The resulting annual modelled rates are 180 MW/year for solar and 660 MW/year for wind.

These continuation rates are scenario assumptions rather than independently verified annual construction commitments through 2050.

Relevant source identifiers:

`N23`, `SC_KZ_PLAN`, `S1`.

### 9.2. Kyrgyzstan

Kyrgyzstan's alternative scenarios emphasize additional hydropower development and changes in commissioning schedules.

#### Accelerated

The Kazarman hydropower project is added with:

- Installed capacity: 912 MW.
- Full annual generation: 3,750 GWh.
- First modelled generation year: 2031.
- Full annual generation from 2032.

The model uses the lower published design generation estimate.

A half-year contribution is assigned in the first commissioning year.

#### High Ambition

High Ambition retains the Kazarman contribution and adds three Kokomeren development stages.

| Stage | Capacity, MW | Annual generation, GWh | First modelled year |
|---|---:|---:|---:|
| 1 | 33 | 95 | 2029 |
| 2 | 360 | 848 | 2035 |
| 3 | 912 | 2,374 | 2039 |

Each stage receives half of its full annual generation in the first modelled year and full generation from the following year.

High Ambition also introduces an earlier commissioning schedule for Kambarata-1.

| Parameter | BAU | High Ambition |
|---|---:|---:|
| First modelled year | 2040 | 2035 |
| Full-operation year | 2042 | 2037 |

The earlier commissioning assumption is implemented by recalculating the portfolio with modified commissioning dates.

Only the difference between the revised portfolio and the original BAU portfolio is added to High Ambition.

**ΔGKambarata(t) = Gearlier(t) − GBAU(t)**

This ensures that the full generation of Kambarata-1 is not counted twice.

The alternative start year is associated with World Bank documentation, while the intermediate ramp to full operation is a modelling assumption.

Relevant source identifiers:

`SC_KG_KAZ`, `SC_KG_PLAN`, `KG_CCDR`, `KG_NDC`.

### 9.3. Tajikistan

Tajikistan's higher-deployment scenarios emphasize solar energy development and diversification of a hydropower-dominated electricity system.

#### Accelerated

A 1,500 MW solar development programme is considered.

The 500 MW solar project already included in BAU is deducted:

**Cadditional = 1500 − 500 = 1000 MW**

The additional solar capacity receives half of its annual generation contribution in 2028 and full annual generation from 2029.

#### High Ambition

High Ambition retains the Accelerated solar contribution and introduces a diversification benchmark.

The model targets a 10% non-hydropower renewable share of domestic electricity generation by 2050.

Let:

- H be modelled hydropower generation in 2050;
- F be non-renewable electricity generation maintained at the IRENA 2024 level;
- V be non-hydropower renewable electricity generation;
- p be the target share, equal to 0.10.

The target condition is:

**V / (H + F + V) = p**

Rearranging gives:

**Vtarget = p × (H + F) / (1 − p)**

The remaining generation gap is:

**ΔV = max(0, Vtarget − Vexisting)**

Here, Vexisting includes the non-hydropower renewable contribution already represented in BAU and Accelerated.

The remaining generation gap is introduced gradually between 2031 and 2050.

Incremental non-hydropower generation is represented as solar-equivalent generation.

Holding non-renewable electricity generation constant is an explicit denominator assumption. It does not represent a separate forecast of Tajikistan's fossil-fuel electricity generation.

Relevant source identifiers:

`SC_TJ_SOLAR`, `SC_TJ_MIX`, `N19`, `S1`.

### 9.4. Turkmenistan

Turkmenistan has limited historical renewable electricity deployment and insufficient evidence to support a detailed long-term national project pipeline.

The model therefore uses an illustrative replication approach based on a 300 MW solar project.

BAU retains the original project.

Accelerated adds one equivalent 300 MW solar block reaching full operation in 2040.

High Ambition adds four equivalent blocks reaching full operation in:

- 2035.
- 2040.
- 2045.
- 2050.

Each block contributes half of its annual generation in the year preceding full operation.

The additional generation of each block is:

**Qblock = 300 × Ysolar**

The replication schedule and future commissioning dates are author-defined assumptions.

They should not be interpreted as announced, approved, or financed renewable energy projects.

Turkmenistan is retained in the computational framework and output tables, although it is omitted from the principal scenario visualizations.

Relevant source identifiers:

`A04`, `SC_TM_IR`.

### 9.5. Uzbekistan

Uzbekistan's scenario construction includes an adjusted reference generation estimate, historical deployment rates, and an official 2030 renewable electricity target.

#### Reference generation adjustment

The 2026 reference calculation combines available January–September generation with an estimated fourth-quarter contribution.

Where October 2026 generation is available:

**Q4estimate = 3 × GOctober,2026**

Otherwise:

**Q4estimate = G2025 / 4**

Estimated annual generation is:

**G2026 = GJanuary–September,2026 + Q4estimate**

This calculation is applied to the technology-level reference inputs.

The estimated 2026 variable renewable generation is maintained in the reference fleet.

For hydropower, the model uses the 2026 estimate specifically for 2026 and returns to the 2025 hydropower reference from 2027 onward.

This treatment distinguishes the partial-year generation estimate from the hydropower level maintained in subsequent projection years.

The reference inputs are stored in:

`data/uzbekistan_reference_inputs.csv`

#### Accelerated

Additional solar and wind deployment follows the long-window historical net capacity addition rates.

Named projects are credited against the total deployment programme over the complete 2027–2050 horizon.

For each technology:

**Radjusted,k = max[0, Rhistorical,k − Cportfolio,k / N]**

where N is the number of programme years from 2027 through 2050.

The additional annual generation is:

**ΔGk(t) = Yk × Radjusted,k × max(0, t − 2027 + 1)**

This approach avoids adding the full historical deployment programme independently of the named projects already included in the portfolio.

#### High Ambition

The High Ambition scenario incorporates a renewable electricity generation target of 54% in 2030.

The total electricity generation anchor is 129,000 GWh.

The corresponding renewable electricity generation target is:

**Gtarget,2030 = 129000 × 0.54 = 69660 GWh**

The additional generation required beyond Accelerated is:

**Ggap = max(0, 69660 − GAccelerated,2030)**

The gap is converted into implied additional solar and wind capacity.

The solar capacity allocation weight is:

**wsolar = Rsolar / (Rsolar + Rwind)**

The wind allocation weight is:

**wwind = 1 − wsolar**

The combined generation yield is:

**Ymix = wsolar × Ysolar + wwind × Ywind**

Required additional capacity is:

**Cadditional = Ggap / Ymix**

The technology-specific capacities are:

**Csolar = wsolar × Cadditional**

**Cwind = wwind × Cadditional**

The resulting capacity requirement is introduced gradually from 2027 to 2030.

After 2030, the additional annual generation achieved through the policy gap is maintained, while further growth follows the same historical deployment component as Accelerated.

No external 2050 generation target is imposed.

The capacity allocation is a model-derived technology mix, not a verified inventory of specific future projects.

#### Capacity bridge

The capacity bridge evaluates four alternative configurations:

1. Solar-only capacity.
2. Wind-only capacity.
3. Historical solar–wind capacity mix.
4. Historical mix with generation yields reduced by 20%.

The announced 2,200 MW tender is included as a scale comparator.

It is not automatically added as an independent project because its overlap with other developments and commissioning schedule are not fully verified.

The capacity bridge is exported to:

`outputs/tables/uzbekistan_2030_capacity_bridge.csv`

Relevant source identifiers:

`SC_UZ_2030`, `S1`, `N03`, `UZ_OCT`.

---

## 10. Prevention of Double Counting

The framework applies several complementary accounting mechanisms to avoid overstating renewable electricity generation.

| Potential duplication | Model treatment |
|---|---|
| Existing generation included in a new project estimate | Deduction of embedded generation |
| Previously installed project capacity | Deduction of embedded capacity |
| Named projects overlapping with national programmes | Deduction from programme capacity |
| Named projects overlapping with historical deployment | Adjustment of additional deployment rates |
| Alternative commissioning schedules | Calculation of incremental differences |
| Multi-stage projects | Separate phase accounting |
| Unverified tender overlap | Use as a comparator rather than an automatic additional project |

These procedures are implemented in `src/model.py`, `src/derive_projects.py`, and `src/scenarios.py`.

Project reconciliation decisions and exclusions are documented in the evidence directory.

The accounting framework is designed to maintain consistency between the reference fleet, the named project portfolio, and additional scenario contributions.

---

## 11. Sensitivity Analysis

The model includes deterministic sensitivity calculations to evaluate the effect of alternative project delivery and generation assumptions.

These calculations are not Monte Carlo simulations and do not assign probabilities to individual outcomes.

### 11.1. BAU Portfolio Sensitivity

The lower and upper portfolio cases evaluate changes in hydropower generation and estimated generation yields.

| Parameter | Lower case | Central case | Upper case |
|---|---:|---:|---:|
| Hydropower generation factor | 0.8 | 1.0 | 1.2 |
| Estimated generation yield factor | 0.8 | 1.0 | 1.2 |
| Project commissioning delay | 3 years | 0 years | 0 years |

The lower case combines reduced generation assumptions with delayed commissioning.

The upper case applies increased hydropower generation and estimated yields.

Delivery-locked projects are protected from the corresponding project delay and delivery adjustments.

The resulting range illustrates selected implementation and generation risks.

### 11.2. Additional Scenario Sensitivity

The scenario sensitivity configuration includes:

- A three-year commissioning delay.
- Estimated generation yields reduced or increased by 20%.
- Hydropower generation reduced or increased by 20%.
- A continuation factor of 0.5.
- A Uzbekistan policy-gap delivery factor of 0.5.

The sensitivity analysis evaluates eight alternative cases across the three scenarios.

The annual sensitivity output contains 3,000 records:

**5 countries × 25 years × 3 scenarios × 8 sensitivity cases.**

Additional diagnostic portfolio settings include alternative delays, reference generation factors, deployment factors, and project-specific assumptions.

The sensitivity parameters are stored in:

`data/config.json`

The scenario sensitivity implementation is provided in:

`src/scenario_sensitivity.py`

### 11.3. Interpretation

Sensitivity envelopes represent the minimum and maximum generation outcomes across the tested assumptions.

They are not:

- Statistical confidence intervals.
- Probabilistic prediction intervals.
- Estimates of the probability of achieving national targets.
- Exhaustive representations of future uncertainty.

The sensitivity outputs are available in:

- `outputs/tables/sensitivity.csv`
- `outputs/tables/sensitivity_2030_2040_2050.csv`
- `outputs/tables/scenario_sensitivity_envelope.csv`
- `outputs/tables/diagnostic_portfolio_sensitivity.csv`

---

## 12. Model Validation and Quality Assurance

The repository contains automated regression tests and input validation procedures.

The tests are organized in:

- `tests/test_model.py`
- `tests/test_scenarios.py`

The saved validation report records 25 successfully completed tests.

The tests cover:

- Country and scenario coverage.
- BAU reconciliation with the underlying project portfolio.
- Consistency of exported scenario contributions.
- Correct treatment of commissioning delays.
- Preservation of already commissioned assets.
- Exclusion of duplicated project capacity.
- Correct treatment of partial-year generation.
- Separation of renewable and non-renewable hybrid project components.
- Handling of missing deployment rates.
- Rejection of invalid project design inputs.
- Source-policy checks.
- Kambarata-1 commissioning adjustments.
- Uzbekistan's 2030 target reconciliation.
- Uzbekistan's additional capacity bridge.
- Sensitivity calculation coverage.
- Correct treatment of partial policy-gap delivery.

The model also checks the accounting identity:

**Gtotal = Greference + Gnamed projects + Gscenario increment**

The validation report is stored in:

`outputs/test_results.txt`

Additional validation results are stored in:

- `outputs/checks.json`
- `outputs/source_policy_check.json`

These checks verify computational consistency and implementation behaviour.

They do not constitute independent empirical validation of electricity generation outcomes through 2050.

---

## 13. Repository Structure

```text
CA_RE_2050/
│
├── data/
│   ├── raw/
│   ├── evidence/
│   ├── baselines.csv
│   ├── project_inputs.csv
│   ├── projects.csv
│   ├── design_yield_inputs.csv
│   ├── yields.csv
│   ├── deployment_rates.csv
│   ├── uzbekistan_reference_inputs.csv
│   ├── scenario_assumptions.json
│   └── config.json
│
├── src/
│   ├── build.py
│   ├── model.py
│   ├── scenarios.py
│   ├── derive_projects.py
│   ├── derive_yields.py
│   ├── scenario_sensitivity.py
│   ├── scenario_report.py
│   ├── report_outputs.py
│   ├── source_policy.py
│   ├── figure_style.py
│   ├── write_documents.py
│   └── reproduce.py
│
├── outputs/
│   ├── figures/
│   ├── tables/
│   ├── checks.json
│   ├── source_policy_check.json
│   └── test_results.txt
│
├── manuscript/
├── tests/
│   ├── test_model.py
│   └── test_scenarios.py
│
├── requirements.txt
├── environment.json
├── SHA256.json
└── README.md
```

### 13.1. Input Files

| File | Description |
|---|---|
| `data/raw/` | Original historical data exports |
| `data/evidence/` | Source register and supporting methodological evidence |
| `baselines.csv` | Reference generation inputs |
| `project_inputs.csv` | Editable project-level input inventory |
| `projects.csv` | Processed project ledger |
| `design_yield_inputs.csv` | Documented project capacity and generation inputs |
| `yields.csv` | Derived generation yields |
| `deployment_rates.csv` | Historical capacity deployment rates |
| `uzbekistan_reference_inputs.csv` | Technology-level reference generation inputs |
| `scenario_assumptions.json` | Country-specific scenario parameters |
| `config.json` | Global model configuration and sensitivity settings |

### 13.2. Computational Scripts

| Script | Purpose |
|---|---|
| `model.py` | Reference generation and project portfolio accounting |
| `scenarios.py` | Construction of the three scenario pathways |
| `derive_projects.py` | Preparation of the project ledger |
| `derive_yields.py` | Calculation of generation yields |
| `scenario_sensitivity.py` | Scenario sensitivity calculations |
| `scenario_report.py` | Scenario reporting |
| `report_outputs.py` | Output reporting |
| `source_policy.py` | Source-policy validation |
| `figure_style.py` | Figure formatting |
| `write_documents.py` | Generation of methodological documents |
| `build.py` | Computational build workflow |
| `reproduce.py` | Complete offline reproduction entry point |

---

## 14. Output Files

### 14.1. Annual Scenario Results

`outputs/tables/annual_scenarios.csv`

Contains 375 annual records:

**5 countries × 25 years × 3 scenarios.**

The results include reference generation, named project generation, scenario-specific increments, and total renewable electricity generation.

Generation is reported in both GWh and TWh.

### 14.2. Summary Results

`outputs/tables/summary_2030_2040_2050.csv`

Contains scenario generation results for the selected milestone years 2030, 2040, and 2050.

### 14.3. Project Contributions

`outputs/tables/project_contributions.csv`

Provides the annual contributions of individual projects and commissioning phases.

The table supports tracing aggregate portfolio generation back to the underlying project ledger.

### 14.4. Scenario Contributions

`outputs/tables/scenario_contributions.csv`

Contains the additional generation components associated with Accelerated and High Ambition.

The table distinguishes programme additions, project additions, continuation assumptions, commissioning changes, and policy-target contributions.

### 14.5. Diagnostic Outputs

Additional output tables include:

- `portfolio_annual_comparison.csv`
- `portfolio_2030_2040_2050.csv`
- `model_references.csv`
- `yield_observations.csv`
- `uzbekistan_2030_capacity_bridge.csv`
- `diagnostic_historical_build_rates.csv`
- `diagnostic_2050_historical_build_rates.csv`
- `diagnostic_portfolio_sensitivity.csv`

These files support independent inspection of the model inputs, intermediate calculations, and alternative assumptions.

---

## 15. Figures

The generated figures are stored in:

`outputs/figures/`

### Three-Scenario Figure

`Figure_1_RE_2050_three_scenarios.png`

`Figure_1_RE_2050_three_scenarios.pdf`

The figure presents the BAU, Accelerated, and High Ambition renewable electricity generation pathways.

### Supplementary Figure S1

`Figure_S1_RE_2050_portfolio.png`

Supplementary Figure S1 presents the BAU project portfolio and its sensitivity range.

The principal visualizations display Kazakhstan, Kyrgyzstan, Tajikistan, and Uzbekistan.

Turkmenistan remains included in the numerical output tables.

The internal figure filenames are retained for computational reproducibility and may differ from the final figure numbering in the associated manuscript.

The figures use annual electricity generation in GWh/year.

PNG figures are exported at 300 dpi. PDF output provides a vector representation suitable for scientific publication.

The publication formatting uses Times New Roman. Where the font is not installed, the `TNR_FONT_DIR` environment variable can be configured to point to locally available font files.

---

## 16. Reproducing the Results

### 16.1. Software Requirements

The computational framework is implemented in Python.

The main dependencies include:

- NumPy.
- pandas.
- Matplotlib.
- python-docx.

The required packages are specified in `requirements.txt`.

The recorded Python and package versions are available in `environment.json`.

### 16.2. Installation

Navigate to the root directory of the project.

Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

### 16.3. Complete Reproduction

Execute:

```bash
python src/reproduce.py
```

The reproduction script runs the computational build, generates methodological documents, executes automated tests, and records the software environment and file checksums.

Once the required dependencies are installed, the workflow operates offline using the supplied data files.

### 16.4. Running Tests Separately

```bash
python -m unittest discover -s tests -v
```

The saved test report is available in:

`outputs/test_results.txt`

### 16.5. File Integrity

The file `SHA256.json` contains SHA-256 checksums generated by the reproduction workflow.

The checksums support identification of file modifications and verification of the recorded computational package.

Python cache files and the checksum manifest itself are excluded from the checksum calculation.

Reproduced file hashes may differ when software versions, generated document metadata, or other environment-dependent output properties differ.

---

## 17. Model Assumptions and Limitations

The results should be interpreted within the following methodological boundaries.

### Existing Fleet

The central calculation maintains reference generation where detailed future retirement, degradation, rehabilitation, and replacement schedules are unavailable.

### Project Implementation

Documented projects may be delayed, modified, cancelled, or implemented with different technical specifications.

The inclusion of a project does not guarantee its future commissioning.

### Commissioning Exposure

Half-year generation and linear commissioning profiles approximate annual operation where detailed commissioning dates are unavailable.

### Generation Yields

Historical and design-based yields are used as generation conversion parameters.

They do not capture all future changes in weather, equipment performance, curtailment, resource quality, or operational conditions.

Transferred Kazakhstan yields introduce additional uncertainty in countries with limited local evidence.

### Historical Deployment

Historical net capacity addition rates are used as conditional continuation assumptions.

They do not guarantee that future investment and construction will follow the same rates.

### Policy Targets

National targets are translated into generation or capacity requirements under explicitly specified assumptions.

Achieving a target in the model does not demonstrate that the target is technically, financially, or institutionally achievable.

### Electricity System Boundaries

The framework is an annual generation accounting model.

It does not perform hourly electricity system dispatch, transmission optimization, storage sizing, electricity market simulation, or comprehensive investment optimization.

### Hydropower

Long-term hydrological variability, climate change, water allocation, and reservoir management are not represented through a dedicated hydrological simulation.

### Uncertainty

The sensitivity calculations evaluate selected alternative assumptions.

They do not provide probability distributions or statistical confidence levels for future generation outcomes.

### Long-Term Interpretation

The projection horizon extends to 2050, whereas the project evidence is limited to information available by 9 November 2026.

Uncertainty increases with the projection horizon.

The scenarios should therefore be interpreted as conditional development pathways rather than definitive forecasts.

---

## 18. Source Documentation and References

The complete project-level source register is maintained in:

`data/evidence/sources.csv`

The source register connects historical observations, project parameters, national policy targets, and supporting evidence to their use in the model.

Additional documentation includes:

- `data/evidence/UPDATE_NOTES.md`
- `data/evidence/SCENARIO_METHODS.md`
- `manuscript/Supplementary_Methods_RU.docx`
- `manuscript/Manuscript_Methods_EN.docx`

Primary institutional resources include:

- [International Renewable Energy Agency — IRENASTAT](https://pxweb.irena.org/)
- [International Renewable Energy Agency](https://www.irena.org/)
- [World Bank](https://www.worldbank.org/)
- [UNFCCC Nationally Determined Contributions Registry](https://unfccc.int/NDCREG)

Individual project documents, national publications, and policy references are identified through the source register rather than through institutional homepage links alone.

The repository distinguishes source-derived parameters from author-defined modelling assumptions.

---

## 19. Associated Research

**Renewable Energy Prospects and Challenges in Central Asia**

Aigerim Tolegenkyzy, Sungat Rysbek, Nurlan Idrissov, Zhengisbek Kuspanov, Aigerim Serik, and Chingis Daulbayev.

Electrochemical Conversion and Energy Storage Laboratory, Institute of Nuclear Physics, Almaty, Kazakhstan.

Satbayev University, Almaty, Kazakhstan.

This repository provides the computational materials supporting the project-based renewable electricity generation scenarios and Supplementary Figure S1.

The associated manuscript and Supplementary Materials provide the broader scientific context, interpretation, and discussion of renewable energy development in Central Asia.
