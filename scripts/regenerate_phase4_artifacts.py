"""
Regenerate Phase 4 forecasting artifacts with a consistent 16-feature schema.
"""

from __future__ import annotations

import json
import os

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler


ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW_PATH = os.path.join(ROOT, "data", "raw", "household_power_consumption.csv")
MODELS_DIR = os.path.join(ROOT, "artifacts", "models")
SCALERS_DIR = os.path.join(ROOT, "artifacts", "scalers")
METADATA_PATH = os.path.join(ROOT, "artifacts", "metadata.json")

TARGET = "consumption"
FEATURE_COLS = [
    "hour",
    "dayofweek",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
    "lag_1",
    "lag_2",
    "lag_24",
    "lag_48",
    "lag_168",
    "rolling_mean_24h",
    "rolling_std_24h",
    "rolling_mean_168h",
]


def load_hourly_series() -> pd.DataFrame:
    df = pd.read_csv(
        RAW_PATH,
        sep=";",
        na_values=["?"],
        dtype={"Global_active_power": "float64"},
        low_memory=False,
    )
    df["Datetime"] = pd.to_datetime(
        df["Date"] + " " + df["Time"], format="%d/%m/%Y %H:%M:%S"
    )
    df = df.set_index("Datetime").sort_index()
    df = df[["Global_active_power"]].rename(columns={"Global_active_power": TARGET})
    df = df.resample("1h").mean()
    df[TARGET] = df[TARGET].ffill(limit=3)
    df[TARGET] = df[TARGET].interpolate(method="linear", limit=24)
    df = df.dropna()
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["hour"] = out.index.hour
    out["dayofweek"] = out.index.dayofweek
    out["month"] = out.index.month
    out["is_weekend"] = (out["dayofweek"] >= 5).astype(int)
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24.0)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12.0)
    out["lag_1"] = out[TARGET].shift(1)
    out["lag_2"] = out[TARGET].shift(2)
    out["lag_24"] = out[TARGET].shift(24)
    out["lag_48"] = out[TARGET].shift(48)
    out["lag_168"] = out[TARGET].shift(168)
    out["rolling_mean_24h"] = out[TARGET].shift(1).rolling(24).mean()
    out["rolling_std_24h"] = out[TARGET].shift(1).rolling(24).std()
    out["rolling_mean_168h"] = out[TARGET].shift(1).rolling(168).mean()
    out = out.dropna()
    return out


def temporal_split(df: pd.DataFrame):
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]


def main() -> None:
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(SCALERS_DIR, exist_ok=True)

    series = load_hourly_series()
    full_df = add_features(series)
    train_df, val_df, test_df = temporal_split(full_df)

    X_train = train_df[FEATURE_COLS]
    y_train = train_df[TARGET]
    X_val = val_df[FEATURE_COLS]
    y_val = val_df[TARGET]
    X_test = test_df[FEATURE_COLS]
    y_test = test_df[TARGET]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    assert scaler.n_features_in_ == len(
        FEATURE_COLS
    ), f"Scaler features {scaler.n_features_in_} != columns {len(FEATURE_COLS)}"

    final_model = lgb.LGBMRegressor(
        n_estimators=300, learning_rate=0.05, max_depth=6, random_state=42, verbose=-1
    )
    final_model.fit(X_train_scaled, y_train)

    xgb_q05 = xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=0.05,
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        tree_method="hist",
        random_state=42,
    )
    xgb_q05.fit(X_train_scaled, y_train)

    xgb_q95 = xgb.XGBRegressor(
        objective="reg:quantileerror",
        quantile_alpha=0.95,
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        tree_method="hist",
        random_state=42,
    )
    xgb_q95.fit(X_train_scaled, y_train)

    # Rebuild Phase 5 Isolation Forest using corresponding training dataframe
    from sklearn.ensemble import IsolationForest
    X_iso = pd.DataFrame()
    X_iso['consumption'] = train_df[TARGET]
    X_iso['rolling_mean_24h'] = train_df['rolling_mean_24h']
    X_iso['rolling_std_24h'] = train_df['rolling_std_24h']
    X_iso['hour_of_day'] = train_df.index.hour
    X_iso['day_of_week'] = train_df.index.dayofweek
    X_iso['residual'] = train_df[TARGET] - train_df['rolling_mean_24h']
    
    iso_forest = IsolationForest(contamination=0.01, random_state=42)
    iso_forest.fit(X_iso)

    test_preds = final_model.predict(X_test_scaled)
    test_rmse = float(np.sqrt(mean_squared_error(y_test, test_preds)))
    test_mae = float(mean_absolute_error(y_test, test_preds))

    joblib.dump(final_model, os.path.join(MODELS_DIR, "forecast_winner.pkl"))
    joblib.dump(xgb_q05, os.path.join(MODELS_DIR, "xgb_q05.pkl"))
    joblib.dump(xgb_q95, os.path.join(MODELS_DIR, "xgb_q95.pkl"))
    joblib.dump(iso_forest, os.path.join(MODELS_DIR, "isolation_forest.pkl"))
    joblib.dump(scaler, os.path.join(SCALERS_DIR, "main_scaler.pkl"))
    with open(os.path.join(SCALERS_DIR, "feature_columns.json"), "w", encoding="utf-8") as f:
        json.dump(FEATURE_COLS, f)

    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    metadata.update(
        {
            "algorithm": "LightGBM",
            "model_filename": "forecast_winner.pkl",
            "q05_filename": "xgb_q05.pkl",
            "q95_filename": "xgb_q95.pkl",
            "scaler_filename": "main_scaler.pkl",
            "feature_columns": "feature_columns.json",
            "metrics": {"test_rmse": round(test_rmse, 4), "test_mae": round(test_mae, 4)},
        }
    )

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    print(f"[OK] feature_columns count: {len(FEATURE_COLS)}")
    print(f"[OK] scaler.n_features_in_: {scaler.n_features_in_}")
    print(f"[OK] Assertion passed: {scaler.n_features_in_ == len(FEATURE_COLS)}")
    print(f"[OK] Test RMSE: {test_rmse:.4f}, Test MAE: {test_mae:.4f}")
    print("[OK] Artifacts regenerated and metadata updated.")


if __name__ == "__main__":
    main()

