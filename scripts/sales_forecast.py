from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, roc_auc_score

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_DATA_PATH = Path("data/raw/brasaland_sales.csv")
DEFAULT_OUTPUT_DIR = Path("reports/sales_forecast")
EXPECTED_COLUMNS = {
    "month",
    "revenue_usd",
    "covers_served",
    "avg_ticket_usd",
    "market",
}
EXPECTED_MONTHS = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
TEST_START = pd.Timestamp("2024-01-01")
LAG_MONTHS = 12
RANDOM_STATE = 42


def load_sales(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Load and validate the monthly consolidated Brasaland sales series."""
    raw = pd.read_csv(path)
    missing_columns = EXPECTED_COLUMNS.difference(raw.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing_columns))}")

    market = raw["market"].astype("string").str.strip().str.lower().fillna("")
    sales = raw.loc[market == "consolidated"].copy()
    if sales.empty:
        raise ValueError("The CSV must contain rows with market='consolidated'.")

    sales["month"] = pd.to_datetime(sales["month"], errors="coerce")
    sales["revenue_usd"] = pd.to_numeric(sales["revenue_usd"], errors="coerce")
    for column in ("covers_served", "avg_ticket_usd"):
        sales[column] = pd.to_numeric(sales[column], errors="coerce")
    required_values = ["month", "revenue_usd", "covers_served", "avg_ticket_usd"]
    if sales[required_values].isna().any().any():
        raise ValueError("Consolidated rows cannot have missing or invalid required values.")
    if not np.equal(sales["covers_served"], np.floor(sales["covers_served"])).all():
        raise ValueError("covers_served must contain whole-number counts.")
    if not sales["month"].dt.day.eq(1).all():
        raise ValueError("Every month must use its first day (YYYY-MM-01).")
    if not sales["revenue_usd"].gt(0).all():
        raise ValueError("Every consolidated revenue_usd value must be positive.")

    sales = sales.sort_values("month").reset_index(drop=True)
    if sales["month"].duplicated().any():
        raise ValueError("The consolidated series contains duplicate months.")
    if not sales["month"].equals(pd.Series(EXPECTED_MONTHS, name="month")):
        raise ValueError("Expected one consolidated row for every month from 2016-01 through 2025-12.")
    return sales


def split_sales(sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split chronologically at 2024-01, keeping the final two years unseen."""
    ordered = sales.sort_values("month").reset_index(drop=True)
    train = ordered.loc[ordered["month"] < TEST_START].copy().reset_index(drop=True)
    test = ordered.loc[ordered["month"] >= TEST_START].copy().reset_index(drop=True)
    if len(train) != 96 or len(test) != 24:
        raise ValueError(f"Expected an 8/2-year split of 96/24 rows; got {len(train)}/{len(test)}.")
    if train["month"].max() >= test["month"].min():
        raise ValueError("Training and test periods overlap.")
    return train, test


def _feature_row(history: list[float], month: pd.Timestamp) -> dict[str, float]:
    if len(history) < LAG_MONTHS:
        raise ValueError("At least 12 prior revenue observations are required to build features.")
    previous = np.asarray(history, dtype=float)
    month_number = month.month - 1
    return {
        "lag_1": float(previous[-1]),
        "lag_2": float(previous[-2]),
        "lag_3": float(previous[-3]),
        "lag_12": float(previous[-12]),
        "rolling_mean_3": float(previous[-3:].mean()),
        "rolling_mean_12": float(previous[-12:].mean()),
        "rolling_std_12": float(previous[-12:].std(ddof=0)),
        "month_sin": float(np.sin(2 * np.pi * month_number / 12)),
        "month_cos": float(np.cos(2 * np.pi * month_number / 12)),
        "is_january": float(month.month == 1),
        "is_december": float(month.month == 12),
        "month_index": float(len(history)),
    }


def make_training_matrix(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    rows = [
        _feature_row(train["revenue_usd"].iloc[:index].tolist(), train["month"].iloc[index])
        for index in range(LAG_MONTHS, len(train))
    ]
    features = pd.DataFrame(rows)
    target = train["revenue_usd"].iloc[LAG_MONTHS:].reset_index(drop=True)
    return features, target


def make_model(n_estimators: int = 500) -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=5,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def recursive_forecast(
    model: RandomForestRegressor,
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    history = train["revenue_usd"].astype(float).tolist()
    point_forecasts: list[float] = []
    lower_bounds: list[float] = []
    upper_bounds: list[float] = []

    for month in test["month"]:
        features = pd.DataFrame([_feature_row(history, month)])
        tree_predictions = np.asarray(
            [tree.predict(features.to_numpy())[0] for tree in model.estimators_], dtype=float
        )
        point_forecast = float(tree_predictions.mean())
        point_forecasts.append(point_forecast)
        lower_bounds.append(float(np.percentile(tree_predictions, 10)))
        upper_bounds.append(float(np.percentile(tree_predictions, 90)))
        history.append(point_forecast)

    return np.asarray(point_forecasts), np.asarray(lower_bounds), np.asarray(upper_bounds)


def population_stability_index(reference: np.ndarray, current: np.ndarray) -> float:
    quantiles = np.quantile(reference, np.linspace(0, 1, 11))
    edges = np.unique(quantiles[1:-1])
    edges = np.concatenate(([-np.inf], edges, [np.inf]))
    reference_counts = np.histogram(reference, bins=edges)[0].astype(float)
    current_counts = np.histogram(current, bins=edges)[0].astype(float)
    epsilon = 1e-6
    bin_count = len(edges[:-1])
    reference_share = (reference_counts + epsilon) / (reference_counts.sum() + epsilon * bin_count)
    current_share = (current_counts + epsilon) / (current_counts.sum() + epsilon * bin_count)
    return float(np.sum((current_share - reference_share) * np.log(current_share / reference_share)))


def evaluate_forecast(
    train: pd.DataFrame,
    test: pd.DataFrame,
    predictions: np.ndarray,
) -> dict[str, float | str | None]:
    actual = test["revenue_usd"].to_numpy(dtype=float)
    train_revenue = train["revenue_usd"].to_numpy(dtype=float)
    mse = float(mean_squared_error(actual, predictions))
    psi = population_stability_index(train_revenue, actual)
    low_month_cutoff = float(np.median(actual))
    low_month = actual < low_month_cutoff
    gini = None
    if np.unique(low_month).size == 2:
        gini = float(2 * roc_auc_score(low_month, -predictions) - 1)

    seasonal_naive = np.resize(train_revenue[-12:], len(actual))
    baseline_mse = float(mean_squared_error(actual, seasonal_naive))
    k2_score = 1 - mse / baseline_mse if baseline_mse > 0 else None
    if psi < 0.1:
        psi_status = "stable"
    elif psi < 0.25:
        psi_status = "moderate_shift"
    else:
        psi_status = "high_shift_review_retraining"

    return {
        "mse_usd_squared": mse,
        "rmse_usd": float(np.sqrt(mse)),
        "mape_percent": float(np.mean(np.abs((actual - predictions) / actual)) * 100),
        "psi_train_vs_test_revenue": psi,
        "psi_status": psi_status,
        "gini_low_month_detection": gini,
        "k2_score": float(k2_score) if k2_score is not None else None,
        "k2_baseline": "seasonal naive: repeat the last 12 training revenues",
    }


def plot_forecast(
    train: pd.DataFrame,
    test: pd.DataFrame,
    predictions: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    destination: Path,
) -> None:
    figure, axis = plt.subplots(figsize=(12, 6))
    axis.plot(train["month"], train["revenue_usd"], color="#365f91", label="Entrenamiento (real)")
    axis.plot(test["month"], test["revenue_usd"], color="#252525", marker="o", label="Prueba (real)")
    axis.plot(test["month"], predictions, color="#d2663b", marker="o", label="Pronóstico")
    axis.fill_between(test["month"], lower, upper, color="#d2663b", alpha=0.2, label="P10-P90 entre árboles")
    axis.axvline(TEST_START, color="#777777", linestyle="--", linewidth=1, label="Inicio prueba")
    axis.set(title="Pronóstico mensual de ventas consolidadas Brasaland", ylabel="Ventas (USD)")
    axis.set_xlabel("Mes")
    axis.grid(axis="y", alpha=0.2)
    axis.legend(loc="best")
    figure.tight_layout()
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def run_forecast(data_path: Path, output_dir: Path) -> dict[str, float | str | None]:
    sales = load_sales(data_path)
    train, test = split_sales(sales)
    features, target = make_training_matrix(train)
    model = make_model()
    model.fit(features, target)
    predictions, lower, upper = recursive_forecast(model, train, test)
    metrics = evaluate_forecast(train, test, predictions)
    metrics.update(
        {
            "train_rows": len(train),
            "test_rows": len(test),
            "train_start": train["month"].min().strftime("%Y-%m"),
            "train_end": train["month"].max().strftime("%Y-%m"),
            "test_start": test["month"].min().strftime("%Y-%m"),
            "test_end": test["month"].max().strftime("%Y-%m"),
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_frame = pd.DataFrame(
        {
            "month": test["month"],
            "actual_revenue_usd": test["revenue_usd"],
            "forecast_revenue_usd": predictions,
            "variability_p10_usd": lower,
            "variability_p90_usd": upper,
        }
    )
    predictions_frame.to_csv(output_dir / "predictions.csv", index=False)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    joblib.dump(
        {"model": model, "feature_columns": list(features.columns), "random_state": RANDOM_STATE},
        output_dir / "random_forest.joblib",
    )
    plot_forecast(train, test, predictions, lower, upper, output_dir / "forecast.png")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the Brasaland sales forecast.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        metrics = run_forecast(args.data, args.output_dir)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print(f"MSE: {metrics['mse_usd_squared']:.2f} USD^2")
    print(f"RMSE: {metrics['rmse_usd']:.2f} USD; MAPE: {metrics['mape_percent']:.2f}%")
    print(f"PSI (train/test revenue): {metrics['psi_train_vs_test_revenue']:.4f} ({metrics['psi_status']})")
    print(f"Gini (deteccion de meses bajos): {metrics['gini_low_month_detection']}")
    print(f"K2 Score (skill vs. seasonal naive): {metrics['k2_score']}")
    if metrics["psi_status"] == "high_shift_review_retraining":
        print("ALERTA: PSI alto; revisa un posible cambio estructural y la necesidad de reentrenar.")
        print("El PSI de ingresos brutos tambien recoge crecimiento y estacionalidad; no prueba por si solo un cambio estructural.")
    print(f"Artefactos guardados en: {args.output_dir}")


if __name__ == "__main__":
    main()