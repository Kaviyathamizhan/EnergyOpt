"""
Phase 6 validator
=================
Runs LP optimization on 5 real 48-hour windows and stores results.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
HISTORY_PATH = os.path.join(ROOT, "data", "processed", "recent_history.csv")
OUT_JSON = os.path.join(ROOT, "artifacts", "phase6_validation_results.json")

from src.optimization.lp_scheduler import optimize_schedule


def _row_to_dict(row: pd.Series) -> dict[str, Any]:
    return {
        "window_start": str(row["window_start"]),
        "window_end": str(row["window_end"]),
        "solver_ok": bool(row["solver_ok"]),
        "optimized_cost_leq_original": bool(row["optimized_cost_leq_original"]),
        "demand_conserved": bool(row["demand_conserved"]),
        "all_non_negative": bool(row["all_non_negative"]),
        "within_capacity": bool(row["within_capacity"]),
        "original_cost": float(row["original_cost"]),
        "optimized_cost": float(row["optimized_cost"]),
        "savings": float(row["savings"]),
        "savings_pct": float(row["savings_pct"]),
    }


def main() -> None:
    df = pd.read_csv(HISTORY_PATH, parse_dates=["Datetime"])
    if "consumption" not in df.columns:
        raise ValueError("recent_history.csv must include a 'consumption' column.")
    min_rows_for_5_windows = 48 + 4 * 30  # overlapping windows
    if len(df) < min_rows_for_5_windows:
        raise ValueError(f"Need at least {min_rows_for_5_windows} rows for 5 windows.")

    values = df["consumption"].astype(float).to_numpy()
    capacity = float(values.max() * 1.25)

    start_positions = [0, 30, 60, 90, 120]
    results = []
    for pos in start_positions:
        window = df.iloc[pos : pos + 48].copy()
        if len(window) < 48:
            continue
        forecast = window["consumption"].astype(float).tolist()
        res = optimize_schedule(
            forecast=forecast,
            capacity=capacity,
            flexibility_fraction=0.20,
            tariff_profile="residential_tou",
        )
        optimized = pd.Series(res.optimized_schedule, dtype=float)
        total_demand = float(sum(forecast))
        conserved = abs(float(optimized.sum()) - total_demand) <= 1e-6
        non_negative = bool((optimized >= -1e-9).all())
        within_capacity = bool((optimized <= capacity + 1e-9).all())

        results.append(
            {
                "window_start": window["Datetime"].iloc[0],
                "window_end": window["Datetime"].iloc[-1],
                "solver_ok": res.solver_code == 0,
                "optimized_cost_leq_original": res.optimized_cost <= res.original_cost + 1e-9,
                "demand_conserved": conserved,
                "all_non_negative": non_negative,
                "within_capacity": within_capacity,
                "original_cost": res.original_cost,
                "optimized_cost": res.optimized_cost,
                "savings": res.savings,
                "savings_pct": res.savings_pct,
            }
        )

    out = {
        "phase": 6,
        "windows_tested": len(results),
        "capacity_used": capacity,
        "results": [_row_to_dict(pd.Series(r)) for r in results],
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"[OK] Saved validation report: {OUT_JSON}")
    print(f"[INFO] Windows tested: {len(results)}")
    all_pass = all(
        r["solver_ok"]
        and r["optimized_cost_leq_original"]
        and r["demand_conserved"]
        and r["all_non_negative"]
        and r["within_capacity"]
        for r in results
    )
    print(f"[INFO] Phase 6 checks pass: {all_pass}")


if __name__ == "__main__":
    main()
