import pandas as pd
import time

DATA_PATH = "./data/EURUSD_M5_48-1_reversed.csv"
df = pd.read_csv(DATA_PATH, sep=';', engine='python')
df['time'] = pd.to_datetime(df['time'])

# Thời gian delay giữa các tick (simulated)
DELAY = 0.1  # 0.1s ~ tốc độ nhanh, test nhanh
