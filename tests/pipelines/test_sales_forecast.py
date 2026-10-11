import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from scripts.evaluate_sales_forecast import evaluate_fold, evaluate_temporal_cv, temporal_splits
from scripts.sales_forecast import _feature_row, evaluate_forecast, make_model, make_training_matrix, split_sales


def monthly_series() -> pd.DataFrame:
    months = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
    return pd.DataFrame(
        {
            "month": months,
            "revenue_usd": np.arange(1, len(months) + 1, dtype=float) * 100,
        }
    )


def test_split_uses_first_eight_years_and_last_two_without_leakage() -> None:
    sales = monthly_series()
    train, test = split_sales(sales)

    assert len(train) == 96
    assert len(test) == 24
    assert train["month"].min() == pd.Timestamp("2016-01-01")
    assert train["month"].max() == pd.Timestamp("2023-12-01")
    assert test["month"].min() == pd.Timestamp("2024-01-01")
    assert test["month"].max() == pd.Timestamp("2025-12-01")
    assert set(train["month"]).isdisjoint(set(test["month"]))

    changed_test = sales.copy()
    changed_test.loc[changed_test["month"] >= "2024-01-01", "revenue_usd"] = 9_999_999
    train_after_test_change, _ = split_sales(changed_test)
    original_features, original_target = make_training_matrix(train)
    changed_features, changed_target = make_training_matrix(train_after_test_change)
    assert_frame_equal(original_features, changed_features)
    assert_series_equal(original_target, changed_target)


def test_features_use_only_prior_revenue_and_encode_january() -> None:
    feature = _feature_row(list(range(1, 13)), pd.Timestamp("2024-01-01"))
    december_feature = _feature_row(list(range(1, 13)), pd.Timestamp("2024-12-01"))

    assert feature["lag_1"] == 12
    assert feature["lag_12"] == 1
    assert feature["rolling_mean_3"] == 11
    assert feature["rolling_mean_12"] == 6.5
    assert feature["is_january"] == 1
    assert feature["is_december"] == 0
    assert december_feature["is_january"] == 0
    assert december_feature["is_december"] == 1


def test_gini_still_measures_low_month_ranking_after_long_term_growth() -> None:
    train = pd.DataFrame({"revenue_usd": np.arange(100, 196, dtype=float)})
    actual = np.arange(200, 224, dtype=float)
    test = pd.DataFrame({"revenue_usd": actual})

    metrics = evaluate_forecast(train, test, actual)

    assert metrics["gini_low_month_detection"] == 1


def test_temporal_folds_preserve_order_and_do_not_overlap() -> None:
    training_period, _ = split_sales(monthly_series())
    folds = temporal_splits(training_period)

    assert len(folds) == 5
    previous_validation_end = -1
    for train_indices, validation_indices in folds:
        assert np.all(np.diff(train_indices) > 0)
        assert np.all(np.diff(validation_indices) > 0)
        assert train_indices[-1] < validation_indices[0]
        assert validation_indices[0] > previous_validation_end
        assert set(train_indices).isdisjoint(set(validation_indices))
        previous_validation_end = validation_indices[-1]


def test_validation_values_cannot_change_fold_training_or_predictions() -> None:
    training_period, _ = split_sales(monthly_series())
    train_indices, validation_indices = temporal_splits(training_period)[0]
    original_metrics, original_predictions = evaluate_fold(
        training_period,
        train_indices,
        validation_indices,
        model_factory=lambda: make_model(10),
    )

    altered_sales = training_period.copy()
    altered_sales.loc[validation_indices, "revenue_usd"] = 9_999_999
    altered_metrics, altered_predictions = evaluate_fold(
        altered_sales,
        train_indices,
        validation_indices,
        model_factory=lambda: make_model(10),
    )

    assert np.isclose(original_metrics["train_rmse_usd"], altered_metrics["train_rmse_usd"])
    np.testing.assert_array_equal(original_predictions, altered_predictions)


def test_temporal_cv_reports_five_expanding_folds_and_error_metrics() -> None:
    training_period, _ = split_sales(monthly_series())
    results = evaluate_temporal_cv(training_period, model_factory=lambda: make_model(10))

    assert len(results) == 5
    assert results["training_months"].tolist() == [36, 48, 60, 72, 84]
    assert results["validation_months"].tolist() == [12] * 5
    assert results["validation_start"].is_monotonic_increasing
    assert results[["train_mae_usd", "validation_mae_usd", "train_rmse_usd", "validation_rmse_usd"]].notna().all().all()