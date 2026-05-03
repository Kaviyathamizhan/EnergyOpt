"""
StateBuffer: In-Memory Rolling History for Real-Time Feature Generation
=======================================================================
Maintains a fixed-size deque of hourly energy readings.
Generates lag features (t-1, t-2, t-24, t-48, t-168) and rolling
statistics (mean/std over 24h and 168h) without touching pandas at
inference time — pure Python + numpy for speed on low-spec hardware.
"""
import json
import os
import math
from collections import deque
from datetime import datetime
import numpy as np
import pandas as pd


class StateBuffer:
    """
    A rolling window of hourly consumption readings.

    Parameters
    ----------
    max_size : int
        Maximum number of hourly readings to retain. Must be >= 200
        to support the 168-hour weekly lag plus warm-up rows.
    csv_path : str or None
        Path to recent_history.csv for cold-start initialization.
    """

    def __init__(self, max_size: int = 200, csv_path: str = None):
        if max_size < 200:
            raise ValueError("Buffer must hold at least 200 rows to support lag-168 + warm-up.")
        self.max_size = max_size
        # Each element: {'datetime': datetime, 'consumption': float}
        self._buffer: deque = deque(maxlen=max_size)

        if csv_path and os.path.exists(csv_path):
            self._load_csv(csv_path)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def _load_csv(self, path: str):
        """Load the bootstrap CSV into the buffer."""
        df = pd.read_csv(path, parse_dates=['Datetime'], index_col='Datetime')
        for dt, row in df.iterrows():
            self._buffer.append({
                'datetime': dt.to_pydatetime(),
                'consumption': float(row['consumption'])
            })
        print(f"[Buffer] Loaded {len(self._buffer)} rows from {path}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_reading(self, dt: datetime, consumption: float):
        """Append a new hourly reading. Oldest row auto-evicts if full."""
        self._buffer.append({'datetime': dt, 'consumption': consumption})

    def __len__(self):
        return len(self._buffer)

    @property
    def is_ready(self) -> bool:
        """True if the buffer has enough history for all lag features."""
        return len(self._buffer) >= 169  # need at least lag-168 + current

    def get_latest_consumption(self) -> float:
        """Return the most recent consumption value."""
        if not self._buffer:
            return 0.0
        return self._buffer[-1]['consumption']

    # ------------------------------------------------------------------
    # Feature Generation (matches Colab feature_columns.json exactly)
    # ------------------------------------------------------------------
    def get_forecast_features(self) -> dict:
        """
        Generate the exact 16 features expected by the forecasting model.

        Returns a dict keyed by feature name, matching the order in
        artifacts/scalers/feature_columns.json:
        [hour, dayofweek, month, is_weekend, hour_sin, hour_cos,
         month_sin, month_cos, lag_1, lag_2, lag_24, lag_48, lag_168,
         rolling_mean_24h, rolling_std_24h, rolling_mean_168h]
        """
        if not self.is_ready:
            raise RuntimeError(
                f"Buffer has {len(self._buffer)} rows, needs >= 169 for feature generation."
            )

        buf = self._buffer
        current = buf[-1]
        dt = current['datetime']

        # Temporal features
        hour = dt.hour
        dayofweek = dt.weekday()
        month = dt.month
        is_weekend = 1 if dayofweek >= 5 else 0
        hour_sin = math.sin(2 * math.pi * hour / 24)
        hour_cos = math.cos(2 * math.pi * hour / 24)
        month_sin = math.sin(2 * math.pi * month / 12)
        month_cos = math.cos(2 * math.pi * month / 12)

        # Lag features (index from end: -1 is current, -2 is t-1, etc.)
        lag_1 = buf[-2]['consumption']
        lag_2 = buf[-3]['consumption']
        lag_24 = buf[-25]['consumption']
        lag_48 = buf[-49]['consumption']
        lag_168 = buf[-169]['consumption']

        # Rolling features (computed over the previous 24/168 readings, excluding current)
        last_24 = [buf[-(i+2)]['consumption'] for i in range(24)]
        last_168 = [buf[-(i+2)]['consumption'] for i in range(168)]

        rolling_mean_24h = float(np.mean(last_24))
        rolling_std_24h = float(np.std(last_24, ddof=1)) if len(last_24) > 1 else 0.0
        rolling_mean_168h = float(np.mean(last_168))

        return {
            'hour': hour,
            'dayofweek': dayofweek,
            'month': month,
            'is_weekend': is_weekend,
            'hour_sin': hour_sin,
            'hour_cos': hour_cos,
            'month_sin': month_sin,
            'month_cos': month_cos,
            'lag_1': lag_1,
            'lag_2': lag_2,
            'lag_24': lag_24,
            'lag_48': lag_48,
            'lag_168': lag_168,
            'rolling_mean_24h': rolling_mean_24h,
            'rolling_std_24h': rolling_std_24h,
            'rolling_mean_168h': rolling_mean_168h,
        }

    def get_anomaly_features(self, consumption: float) -> dict:
        """
        Generate the 6 features expected by the Isolation Forest.

        Matches artifacts/scalers/anomaly_feature_columns.json:
        [consumption, rolling_mean_24h, rolling_std_24h,
         hour_of_day, day_of_week, residual]
        """
        if len(self._buffer) < 25:
            raise RuntimeError("Buffer needs >= 25 rows for anomaly features.")

        buf = self._buffer
        dt = buf[-1]['datetime']

        last_24 = [buf[-(i+2)]['consumption'] for i in range(24)]
        rolling_mean_24h = float(np.mean(last_24))
        rolling_std_24h = float(np.std(last_24, ddof=1)) if len(last_24) > 1 else 0.0

        return {
            'consumption': consumption,
            'rolling_mean_24h': rolling_mean_24h,
            'rolling_std_24h': rolling_std_24h,
            'hour_of_day': dt.hour,
            'day_of_week': dt.weekday(),
            'residual': consumption - rolling_mean_24h,
        }
