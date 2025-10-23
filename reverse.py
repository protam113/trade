import pandas as pd
from pathlib import Path

DATA_PATH = Path('../../data/EURUSD_M5_48-1.csv')
OUTPUT_PATH = DATA_PATH.with_name(DATA_PATH.stem + '_reversed.csv')

# Đọc file CSV
df = pd.read_csv(DATA_PATH, sep=';')

# Đảo ngược thứ tự dòng
df = df.iloc[::-1].reset_index(drop=True)

# Ghi ra file mới
df.to_csv(OUTPUT_PATH, sep=';', index=False)

print(f"✅ Đã lưu file đảo ngược tại: {OUTPUT_PATH}")
