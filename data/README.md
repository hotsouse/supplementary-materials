# Input data

## Provenance

- Source dataset: IRENASTAT, C-ELECCAP (electricity capacity statistics).
- Original supplied export: `C-ELECCAP_20260908-055900.csv`.
- Repository file: `irena_capacity_2025.csv`.
- Selection: year 2025; `OnGrid`; Kazakhstan, Kyrgyzstan, Tajikistan and
  Uzbekistan; Renewable hydropower, Solar photovoltaic and Onshore wind energy.
- Coverage: 12 rows (four countries multiplied by three technologies).
- Unit: megawatts (MW).

This is a selected subset of the export supplied with the original project,
not a new database download. The original numeric text and `-` entries have
been retained. The descriptive first line of the export has been removed so
the CSV begins with a standard column header. No values were estimated.
The complete original export is outside the scope of this repository.

## Fields

| Column | Meaning |
| --- | --- |
| `Country/area` | Country name in the source export |
| `Technology` | IRENASTAT technology category |
| `Grid connection` | `OnGrid` for every included observation |
| `Year` | 2025 for every included observation |
| `Electricity capacity statistics` | Installed electricity capacity in MW; `-` is a nonnumeric source entry |

## Missing values and denominator

The two `-` entries are for onshore wind in Kyrgyzstan and Tajikistan.
The plotting script uses `pandas.to_numeric(..., errors="coerce")` and fills
missing technology components with zero, matching the original figure.
Percentages use the sum of hydropower, solar PV and onshore wind only.
Bioenergy, total renewable energy and other technology rows are not included.
