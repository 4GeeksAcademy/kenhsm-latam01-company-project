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

## Sales forecast evaluation

Once the original CSV is present, run the five-fold expanding-window evaluation from the repository root:

```bash
uv run python -m scripts.evaluate_sales_forecast
uv run pytest tests/pipelines/test_sales_forecast.py
```

The evaluation uses only 2016-2023 for five consecutive 12-month validation windows. Features are rebuilt inside each fold from its training history, and validation is forecast recursively without actual validation revenues entering later lags. It saves `data/eval/sales_forecast_cv.csv`, `data/eval/learning_curve.png`, and `data/eval/evaluation_report.md`. MAE is primary because it reports typical absolute sales error directly in USD for purchasing plans; RMSE is also reported because unusually large misses can distort ingredient orders. The business context does not establish a higher cost for over- versus under-forecasting, so metrics treat them symmetrically.

The report's operational diagnosis compares the final learning-curve train/validation RMSE gap and each against a seasonal-naive baseline. A gap of at least 1.5 is labeled overfitting; absent that gap, both model errors at least 95% of baseline are labeled underfitting; other results are labeled bien ajustado. These are explicit comparison rules, not universal thresholds. For overfitting, the report proposes shallower trees and larger leaves; for underfitting, it proposes an interannual-growth feature and a controlled depth increase. The 2024-2025 holdout is kept out of this evaluation and all proposed tuning.
