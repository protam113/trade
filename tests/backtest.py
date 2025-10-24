"""
main.py - Main Trading Bot Application
Kết nối monitor và strategy, chạy backtest

Sử dụng:
    python main.py
"""
import sys
import os

ROOT = "/home/hoang-pham/Documents/bot_v2/src"  
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))  

import pandas as pd
from bot.signals.signal_generator import MockSignalGenerator as SignalGenerator

# ===== CONFIG =====
AGENT_VERSION = "lenf_001"
DATA_PATH = "./data/EURUSD_M5_48-1_reversed.csv"

# ===== INIT =====
sg = SignalGenerator(AGENT_VERSION)

# Load CSV
df = pd.read_csv(DATA_PATH, sep=';', engine='python')
df['time'] = pd.to_datetime(df['time'])

# Init feature data
sg.initialise_data(str(df.iloc[0]['time']))

# ===== LOOP TRADE GIẢ LẬP =====
for i, row in df.iterrows():
    now = str(row['time'])

    try:
        # Update tick data + feature
        sg.update_data(now)

        # Predict action
        signal = sg.predict()

        # Print kết quả ra terminal
        print(f"[{now}] Action: {signal['action_pos']}, Dist: {signal['action_dist_pos'][:3]}...")

    except Exception as e:
        print(f"⚠️ Lỗi tại {now}: {e}")
        continue

print("✅ Backtest done!")
