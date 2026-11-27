# Additional LCOE Analysis: Solar PV and Onshore Wind

## Overview

This repository presents an additional analysis of the Levelized Cost of Electricity (LCOE) for solar photovoltaic (PV) and onshore wind technologies using Monte Carlo simulation.

The analysis was developed as an extension of the original research on renewable electricity generation in Central Asia through 2050. It was not included in the original article or its supplementary materials.

## Research Objective

The analysis aims to:

- Assess the uncertainty associated with renewable electricity generation costs.
- Compare the modeled LCOE distributions of solar PV and onshore wind.
- Evaluate the variability of electricity generation costs under alternative techno-economic conditions.
- Compare simulation results with the global weighted-average LCOE reported by IRENA for 2024.

## Data and Methodology

The analysis uses global techno-economic indicators and reference values from the International Renewable Energy Agency (IRENA), including:

- Capital expenditure (CAPEX);
- Operating expenditure (OPEX);
- Capacity factor (CF);
- Global weighted-average LCOE.

Monte Carlo simulation is applied to propagate uncertainty in selected input parameters and obtain probability distributions of LCOE for both technologies.

A common real discount rate of 8% is adopted as a modeling assumption to ensure comparability under consistent financing conditions.

## Figure Interpretation

The horizontal box plots represent the simulated LCOE distributions:

| Graphical element | Description |
|---|---|
| Box (P25–P75) | Central 50% of simulated values |
| Whiskers (P05–P95) | Central 90% of simulated values |
| Black vertical line | Median (P50) |
| Diamond marker | Arithmetic mean |
| Dashed vertical line | IRENA global weighted-average LCOE for 2024 |

All LCOE values are expressed in USD/MWh.

## Results

| Technology | Simulated mean LCOE (USD/MWh) | IRENA 2024 benchmark (USD/MWh) |
|---|---:|---:|
| Onshore wind | 49.30 | 34.00 |
| Solar PV | 74.39 | 43.00 |

Under the adopted modeling assumptions, onshore wind demonstrates a lower mean LCOE and a narrower uncertainty range than solar PV.

The differences between simulated results and IRENA benchmarks reflect the adopted input distributions and modeling assumptions. They should not be interpreted as deviations from observed national electricity generation costs.

## Scope and Limitations

The analysis is based on global techno-economic reference data rather than country-specific project-level observations.

Consequently, the results represent conditional technology-level cost estimates and do not constitute national LCOE estimates for individual Central Asian countries.

## Data Source

International Renewable Energy Agency (IRENA). (2025). *Renewable Power Generation Costs in 2024*. Abu Dhabi: IRENA.

https://www.irena.org/

## Relationship to the Original Research

This analysis constitutes an independent methodological extension of the original study. It provides additional insights into renewable energy cost uncertainty and complements the electricity generation forecast through 2050.

The analysis and associated visualization were not included in the original article or its supplementary materials.
