import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from scripts.sales_forecast import _feature_row, evaluate_forecast, make_training_matrix, split_sales


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