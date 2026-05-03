"""
Bootstrap Buffer Script
=======================
Reads the raw household_power_consumption.csv, resamples to hourly,
and extracts the last 200 hours as recent_history.csv.

This CSV is the cold-start seed for the FastAPI in-memory buffer.
Run this ONCE before starting the API for the first time.

Usage:
    python scripts/bootstrap_buffer.py
"""
import pandas as pd
import os

RAW_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'household_power_consumption.csv')
OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'recent_history.csv')

def main():
    print("Loading raw dataset...")
    df = pd.read_csv(RAW_PATH, sep=';', na_values=['?'], dtype={'Global_active_power': 'float64'})
    df['Datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%d/%m/%Y %H:%M:%S')
    df.set_index('Datetime', inplace=True)
    df.drop(columns=['Date', 'Time'], inplace=True)

    df_hourly = df[['Global_active_power']].resample('1h').mean()
    df_hourly.rename(columns={'Global_active_power': 'consumption'}, inplace=True)
    df_hourly['consumption'] = df_hourly['consumption'].ffill(limit=3)
    df_hourly['consumption'] = df_hourly['consumption'].interpolate(method='linear', limit=24)
    df_hourly.dropna(inplace=True)

    # Take the last 200 hours (need 168 for weekly lag + 32 warm-up rows)
    buffer = df_hourly.tail(200).copy()
    buffer.index.name = 'Datetime'

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    buffer.to_csv(OUT_PATH)
    print(f"[OK] Saved {len(buffer)} rows to {os.path.abspath(OUT_PATH)}")
    print(f"     Date range: {buffer.index[0]} to {buffer.index[-1]}")

if __name__ == '__main__':
    main()
