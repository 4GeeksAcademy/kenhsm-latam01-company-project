from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from scripts.sales_forecast import (
    DEFAULT_DATA_PATH,
    LAG_MONTHS,
    make_model,
    make_training_matrix,
    load_sales,
    recursive_forecast,
    split_sales,
)

DEFAULT_OUTPUT_DIR = Path("data/eval")
FOLDS = 5
HORIZON_MONTHS = 12


def temporal_splits(
    sales: pd.DataFrame,
    n_splits: int = FOLDS,
    test_size: int = HORIZON_MONTHS,
) -> list[tuple[np.ndarray, np.ndarray]]:
    if n_splits < 5:
        raise ValueError("At least five temporal folds are required.")
    if not sales["month"].is_monotonic_increasing or sales["month"].duplicated().any():
        raise ValueError("Time-series folds require unique, chronologically sorted months.")
    if len(sales) <= n_splits * test_size + LAG_MONTHS:
        raise ValueError("Not enough rows for five validation windows and 12 months of feature history.")

    splitter = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
    folds = list(splitter.split(sales))
    previous_validation_end = -1
    for train_indices, validation_indices in folds:
        if train_indices[-1] >= validation_indices[0]:
            raise ValueError("A temporal fold places training data at or after its validation window.")
        if validation_indices[0] <= previous_validation_end:
            raise ValueError("Validation windows overlap or are not chronological.")
        previous_validation_end = int(validation_indices[-1])
    return folds


def evaluate_fold(
    sales: pd.DataFrame,
    train_indices: np.ndarray,
    validation_indices: np.ndarray,
    model_factory: Callable = make_model,
) -> tuple[dict[str, float | int | str], np.ndarray]:
    fold_train = sales.iloc[train_indices].copy().reset_index(drop=True)
    fold_validation = sales.iloc[validation_indices].copy().reset_index(drop=True)

    # Features are rebuilt from this fold's history; validation labels never enter them.
    features, target = make_training_matrix(fold_train)
    model = model_factory()
    model.fit(features, target)
    training_predictions = model.predict(features)
    validation_predictions, _, _ = recursive_forecast(model, fold_train, fold_validation)

    training_actual = target.to_numpy(dtype=float)
    validation_actual = fold_validation["revenue_usd"].to_numpy(dtype=float)
    seasonal_training = fold_train["revenue_usd"].iloc[:-LAG_MONTHS].to_numpy(dtype=float)
    seasonal_validation = np.resize(
        fold_train["revenue_usd"].iloc[-LAG_MONTHS:].to_numpy(dtype=float),
        len(validation_actual),
    )
    record: dict[str, float | int | str] = {
        "training_months": len(fold_train),
        "training_feature_rows": len(features),
        "validation_months": len(fold_validation),
        "validation_start": fold_validation["month"].min().strftime("%Y-%m"),
        "validation_end": fold_validation["month"].max().strftime("%Y-%m"),
        "train_mae_usd": float(mean_absolute_error(training_actual, training_predictions)),
        "train_rmse_usd": float(np.sqrt(mean_squared_error(training_actual, training_predictions))),
        "validation_mae_usd": float(mean_absolute_error(validation_actual, validation_predictions)),
        "validation_rmse_usd": float(np.sqrt(mean_squared_error(validation_actual, validation_predictions))),
        "seasonal_naive_train_rmse_usd": float(np.sqrt(mean_squared_error(training_actual, seasonal_training))),
        "seasonal_naive_validation_rmse_usd": float(np.sqrt(mean_squared_error(validation_actual, seasonal_validation))),
    }
    return record, validation_predictions


def evaluate_temporal_cv(
    sales: pd.DataFrame,
    n_splits: int = FOLDS,
    test_size: int = HORIZON_MONTHS,
    model_factory: Callable = make_model,
) -> pd.DataFrame:
    rows = []
    for fold_number, (train_indices, validation_indices) in enumerate(
        temporal_splits(sales, n_splits=n_splits, test_size=test_size), start=1
    ):
        record, _ = evaluate_fold(sales, train_indices, validation_indices, model_factory)
        record["fold"] = fold_number
        rows.append(record)
    return pd.DataFrame(rows)


def diagnose_fit(results: pd.DataFrame) -> tuple[str, str, dict[str, float]]:
    final_fold = results.iloc[-1]
    train_rmse = float(final_fold["train_rmse_usd"])
    validation_rmse = float(final_fold["validation_rmse_usd"])
    naive_train_rmse = float(final_fold["seasonal_naive_train_rmse_usd"])
    naive_validation_rmse = float(final_fold["seasonal_naive_validation_rmse_usd"])
    gap_ratio = validation_rmse / max(train_rmse, np.finfo(float).eps)
    train_baseline_ratio = train_rmse / max(naive_train_rmse, np.finfo(float).eps)
    validation_baseline_ratio = validation_rmse / max(naive_validation_rmse, np.finfo(float).eps)
    evidence = {
        "final_train_rmse_usd": train_rmse,
        "final_validation_rmse_usd": validation_rmse,
        "validation_to_train_rmse_ratio": gap_ratio,
        "train_to_seasonal_naive_rmse_ratio": train_baseline_ratio,
        "validation_to_seasonal_naive_rmse_ratio": validation_baseline_ratio,
    }

    if gap_ratio >= 1.5:
        diagnosis = "overfitting"
        action = (
            "Reducir max_depth de 5 a 3 y subir min_samples_leaf de 2 a 4; comparar de nuevo "
            "los cinco folds sin tocar el holdout 2024-2025."
        )
    elif train_baseline_ratio >= 0.95 and validation_baseline_ratio >= 0.95:
        diagnosis = "underfitting"
        action = (
            "Agregar una feature causal de crecimiento interanual (lag_1 / lag_12 - 1) y probar "
            "max_depth=7; conservar la validacion temporal para comprobar si baja el error en train y validacion."
        )
    else:
        diagnosis = "bien ajustado"
        action = (
            "No cambiar complejidad: mantener los hiperparametros y comprobar estabilidad en un "
            "siguiente periodo mensual antes de promover a staging."
        )
    return diagnosis, action, evidence


def _mean_std(values: pd.Series) -> tuple[float, float]:
    return float(values.mean()), float(values.std(ddof=1))


def plot_learning_curve(results: pd.DataFrame, destination: Path) -> None:
    figure, axis = plt.subplots(figsize=(9, 5.5))
    sample_sizes = results["training_feature_rows"]
    axis.plot(sample_sizes, results["train_rmse_usd"], marker="o", label="RMSE entrenamiento")
    axis.plot(sample_sizes, results["validation_rmse_usd"], marker="o", label="RMSE validacion (12 meses)")
    axis.set(
        title="Curva de aprendizaje temporal - Brasaland",
        xlabel="Meses de entrenamiento con features disponibles",
        ylabel="RMSE (USD)",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def build_report(results: pd.DataFrame, learning_curve_path: Path) -> str:
    diagnosis, action, evidence = diagnose_fit(results)
    summaries = {
        metric: _mean_std(results[metric])
        for metric in (
            "train_mae_usd",
            "validation_mae_usd",
            "train_rmse_usd",
            "validation_rmse_usd",
        )
    }
    mae_train_mean, mae_train_std = summaries["train_mae_usd"]
    mae_validation_mean, mae_validation_std = summaries["validation_mae_usd"]
    rmse_train_mean, rmse_train_std = summaries["train_rmse_usd"]
    rmse_validation_mean, rmse_validation_std = summaries["validation_rmse_usd"]
    stability = float(results["validation_mae_usd"].std(ddof=1))
    return f"""# Evaluacion tecnica del pronostico de ventas Brasaland

## Alcance y protocolo

- Fuente: `data/raw/brasaland_sales.csv`, filas `market=consolidated`, objetivo `revenue_usd`.
- Holdout final: 2016-2023 para desarrollo; 2024-2025 permanece fuera de esta validacion cruzada.
- Validacion: {len(results)} ventanas expansivas de 12 meses con `TimeSeriesSplit`; sin shuffle. En cada fold las features se reconstruyen solo con la serie de entrenamiento y el horizonte se pronostica recursivamente, sin usar ventas reales de validacion como lags.
- Curva: [learning_curve.png]({learning_curve_path.name}); el eje horizontal cuenta filas de entrenamiento disponibles despues del lag de 12 meses.
- Modelo: Random Forest con `max_depth=5`, `min_samples_leaf=2`, `n_estimators=500` y semilla 42.

## Metricas por fold (media +/- desviacion estandar)

MAE es la metrica principal: representa directamente el error absoluto mensual tipico en USD, util para planificar compras. El contexto no indica un costo asimetrico de sobreestimar frente a subestimar; por eso no se pondera un sentido del error. RMSE se conserva como metrica secundaria porque penaliza mas los errores grandes, que pueden distorsionar pedidos de insumos.

| Metrica | Media +/- desviacion estandar |
|---|---:|
| MAE entrenamiento (USD) | {mae_train_mean:.2f} +/- {mae_train_std:.2f} |
| MAE validacion (USD) | {mae_validation_mean:.2f} +/- {mae_validation_std:.2f} |
| RMSE entrenamiento (USD) | {rmse_train_mean:.2f} +/- {rmse_train_std:.2f} |
| RMSE validacion (USD) | {rmse_validation_mean:.2f} +/- {rmse_validation_std:.2f} |

La desviacion estandar de MAE de validacion entre folds es {stability:.2f} USD y resume la variacion entre origenes temporales.

## Diagnostico

**Clasificacion: {diagnosis}.** Evidencia del fold con mayor historial:

- RMSE train: {evidence['final_train_rmse_usd']:.2f} USD.
- RMSE validacion: {evidence['final_validation_rmse_usd']:.2f} USD.
- Cociente validacion/train: {evidence['validation_to_train_rmse_ratio']:.2f}.
- Cocientes RMSE del modelo vs baseline estacional (train/validacion): {evidence['train_to_seasonal_naive_rmse_ratio']:.2f} / {evidence['validation_to_seasonal_naive_rmse_ratio']:.2f}.

Regla explicita: brecha validacion/train >= 1.5 indica overfitting; si no, ambos errores >= 95% de su baseline estacional indican underfitting; en los demas casos se clasifica como bien ajustado respecto a ese baseline. Es una regla operativa del reporte, no un umbral universal.

## Accion correctiva

{action}

La recomendacion se basa en los patrones de la curva y en la comparacion contra el baseline, no en el holdout final. La clasificacion no prueba que el modelo este listo para produccion; requiere revisar el error absoluto en USD y el siguiente periodo real.
"""


def run_evaluation(
    data_path: Path = DEFAULT_DATA_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    model_factory: Callable = make_model,
) -> pd.DataFrame:
    sales = load_sales(data_path)
    training_period, _ = split_sales(sales)
    results = evaluate_temporal_cv(training_period, model_factory=model_factory)
    output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_dir / "sales_forecast_cv.csv", index=False)
    plot_learning_curve(results, output_dir / "learning_curve.png")
    (output_dir / "evaluation_report.md").write_text(
        build_report(results, output_dir / "learning_curve.png"), encoding="utf-8"
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Brasaland sales model with temporal cross-validation.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        results = run_evaluation(args.data, args.output_dir)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(results[["fold", "train_mae_usd", "validation_mae_usd", "train_rmse_usd", "validation_rmse_usd"]].to_string(index=False))
    print(f"Evaluacion guardada en {args.output_dir}")


if __name__ == "__main__":
    main()