# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

> _Spanish version: [README.es.md](./README.es.md)._

## Incident analyzer

The Brasaland incident analyzer is implemented in `incident_analysis.py` and exposed through `analyze.py`:

```bash
PYTHONPATH=scripts python3 scripts/analyze.py incidents-brasaland.csv
```

It validates the exact locations, categories, statuses and satisfaction rules from `CONTEXT.md`, prints the breakdown, and optionally writes `results.csv` with `metric`, `value` and `percentage` columns.

## Brasaland sales forecast

Run the 2016-2025 consolidated monthly forecast from the repository root:

```bash
uv run python scripts/sales_forecast.py
uv run pytest tests/pipelines/test_sales_forecast.py
```

The command reads `data/raw/brasaland_sales.csv`, trains on 2016-2023, and recursively forecasts 2024-2025 without feeding actual test revenues back into later predictions. It writes `reports/sales_forecast/metrics.json`, `predictions.csv`, `forecast.png`, and `random_forest.joblib`. Pass `--data` or `--output-dir` to override those paths.

Random Forest is a good first fit for 96 training months (84 remain after the 12-month lag): it models nonlinear lag/calendar interactions with little tuning and can be explained as an average of trees. Tree models do not require feature scaling. The model uses prior-month lags, 3/12-month rolling statistics and calendar features for January's dip and December's peak. Its P10-P90 band is the spread across trees, a variability indicator rather than a calibrated confidence interval.

The report defines MSE in USD^2 and adds RMSE in USD plus MAPE as an understandable percentage error. PSI compares train and test revenue distributions using training-derived decile bins; values above 0.25 trigger a structural-change/retraining review, but raw revenue PSI also reflects expected growth and seasonality. Gini is `2 * AUC - 1` for identifying test months below the test-period median, ranked by predicted low revenue; the cutoff is only used to evaluate held-out labels, never as a model feature. Because the source requirements do not define a standard K2 metric, this implementation explicitly defines K2 as forecast skill `1 - model MSE / seasonal-naive MSE`, where the baseline repeats the final 12 training revenues. A negative K2 means the model underperformed that baseline. These complementary checks matter because a low MSE alone can hide poor identification of weak months or a distribution shift.

The CSV validator requires the documented five columns, valid numeric covers/tickets, positive revenue, and exactly one consolidated observation per month from 2016-01 through 2025-12. It fails on missing/invalid required values or duplicate/missing months instead of imputing fabricated sales.
