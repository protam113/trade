# -*- coding: utf-8 -*-
import time
import pandas as pd
from pandas import Series


def forex(
    data_path: str,
    start_date: str = None,
    end_date: str = None,
    speed: float = 0.3,
    **kwargs
) -> Series:
    """
    Forex Market Simulator
    ----------------------
    Simulate a Forex market playback using MT5-style CSV data.

    Parameters:
        data_path (str): Path to the CSV file (e.g. '../../data/EURUSD_M5_48-1_reversed.csv').
        start_date (str): Start date of simulation, format 'YYYY-MM-DD'.
        end_date (str): End date of simulation, format 'YYYY-MM-DD'.
        speed (float): Delay time between each candle in seconds.
        **kwargs: Reserved for future extensions.

    Returns:
        pandas.Series: A series of 'close' prices from the simulated range.

    Notes:
        - The CSV file must include columns: time, open, high, low, close, tick_volume.
        - This function prints each candle line by line to simulate real-time playback.
    """

    # Load CSV data
    df = pd.read_csv(data_path, sep=';')

    # Convert the 'time' column to datetime
    df['time'] = pd.to_datetime(df['time'], format='%Y.%m.%d %H:%M')

    # Filter by date range if provided
    if start_date:
        df = df[df['time'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['time'] <= pd.to_datetime(end_date)]

    df = df.reset_index(drop=True)

    if df.empty:
        print(f"❌ No data found between {start_date} → {end_date}")
        return Series(dtype=float)

    print(f"✅ Loaded {len(df)} candles from {data_path}")
    print(f"🗓 Date range: {df['time'].iloc[0]} → {df['time'].iloc[-1]}")
    print("📈 Starting market simulation...\n")

    # Iterate over each candle and simulate real-time feed
    for _, row in df.iterrows():
        time_str = row['time'].strftime('%Y-%m-%d %H:%M')
        open_ = row['open']
        high = row['high']
        low = row['low']
        close = row['close']
        volume = row['tick_volume']

        print(f"[{time_str}] O:{open_} H:{high} L:{low} C:{close} V:{volume}")
        time.sleep(speed)

    print("\n🏁 Simulation finished.")

    # Return 'close' series for further analysis or indicator chaining
    return Series(df['close'].values, index=df['time'], name='close')
