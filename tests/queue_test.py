import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))

import MetaTrader5 as mt5
from datetime import datetime
import pytz
from collections import deque
import pandas_ta as ta
import pandas as pd
import sys


# ============================================================
# 📦 CLASS: RateQueue - quản lý dữ liệu nến (FIFO)
# ============================================================
class RateQueue:
    def __init__(self, max_size=2000):
        """Khởi tạo queue"""
        self.queue = deque(maxlen=max_size)

    def add(self, rate):
        """Thêm 1 rate (dict) vào queue"""
        if not isinstance(rate, dict):
            raise TypeError("Rate must be a dictionary")
        self.queue.append(rate)

    def clear(self):
        """Xóa toàn bộ queue"""
        self.queue.clear()

    def pop(self):
        """Lấy phần tử đầu tiên"""
        if not self.queue:
            return None
        return self.queue.popleft()

    def size(self):
        """Trả về số lượng phần tử"""
        return len(self.queue)

    def print_all(self):
        """In toàn bộ dữ liệu queue"""
        print(f"\n🧾 Queue hiện có {len(self.queue)} nến:\n")
        for r in self.queue:
            time_str = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{time_str} | O:{r['open']:.5f} H:{r['high']:.5f} L:{r['low']:.5f} C:{r['close']:.5f} V:{r['tick_volume']}")


def get_queue_memory_usage(queue: RateQueue):
    """Tính dung lượng RAM (byte) mà queue đang chiếm"""
    total = sys.getsizeof(queue.queue)
    for item in queue.queue:
        total += sys.getsizeof(item)
        for v in item.values():
            total += sys.getsizeof(v)
    return total

def analyze_trend(df: pd.DataFrame):
    """
    📈 Phân tích xu hướng thị trường bằng EMA + MACD.
    Trả về chuỗi mô tả xu hướng hiện tại.
    """

    # --- Tính toán EMA ---
    df["EMA_20"] = ta.ema(df["close"], length=20)
    df["EMA_50"] = ta.ema(df["close"], length=50)

    # --- Tính toán MACD ---
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd_df], axis=1)

    # --- Lấy dòng dữ liệu mới nhất ---
    latest = df.iloc[-1]
    ema_up = latest["EMA_20"] > latest["EMA_50"]
    macd_up = latest["MACD_12_26_9"] > latest["MACDs_12_26_9"]

    # --- Logic xác định xu hướng ---
    if ema_up and macd_up:
        return "🚀 UPTREND (EMA + MACD đồng thuận)"
    elif not ema_up and not macd_up:
        return "💀 DOWNTREND (EMA + MACD đồng thuận)"
    elif ema_up and not macd_up:
        return "⚠️ EMA tăng nhưng MACD yếu → có thể sắp đảo chiều giảm"
    elif not ema_up and macd_up:
        return "⚠️ EMA giảm nhưng MACD mạnh → có thể sắp đảo chiều tăng"
    else:
        return "⚖️ SIDEWAY / CHƯA RÕ"

# ============================================================
# ⚙️ HÀM QUY ĐỔI TIMEFRAME TỰ ĐỘNG
# ============================================================
def get_timeframe_auto(start: datetime, end: datetime):
    """Chọn timeframe hợp lý dựa theo khoảng thời gian cần phân tích"""
    days = (end - start).days
    if days <= 7:
        return mt5.TIMEFRAME_H1, "H1"
    elif days <= 90:  # khoảng 3 tháng
        return mt5.TIMEFRAME_H4, "H4"
    elif days <= 365:  # dưới 1 năm
        return mt5.TIMEFRAME_H12, "H12"
    else:  # hơn 1 năm
        return mt5.TIMEFRAME_D1, "D1"

# ============================================================
# ⚙️ KẾT NỐI MT5 + LẤY DỮ LIỆU NẾN
# ============================================================
if not mt5.initialize(
    path='C:\\Program Files\\MetaTrader 5\\terminal64.exe',
    login=52575885,
    password='@q30SMKYhawwOa',
    server='ICMarketsSC-Demo'
):
    print("MT5 initialization failed")
    mt5.shutdown()
    exit()

account_info = mt5.account_info()
if account_info is None:
    print("Login failed")
    mt5.shutdown()
    exit()
print(f"✅ Logged in: {account_info.login}, balance: {account_info.balance}")

# --- Symbol & Timezone ---
symbol = "EURUSD"
timezone = pytz.timezone("Etc/UTC")

if not mt5.symbol_select(symbol, True):
    print(f"Cannot select {symbol}")
    mt5.shutdown()
    exit()

# --- Thời gian lấy dữ liệu ---
start = datetime(2025, 10, 14, tzinfo=timezone)
end = datetime(2025, 10, 27, tzinfo=timezone)

# --- Chọn timeframe tự động ---
timeframe, tf_str = get_timeframe_auto(start, end)
print(f"🕒 Timeframe được chọn: {tf_str} (theo {end - start})")

# --- Lấy dữ liệu ---
rates = mt5.copy_rates_range(symbol, timeframe, start, end)

if rates is None or len(rates) == 0:
    print("❌ Không có dữ liệu trong khoảng thời gian này")
    mt5.shutdown()
    exit()

print(f"📊 Lấy được {len(rates)} cây nến {tf_str} cho {symbol} từ {start} đến {end}")

# ============================================================
# 🧠 ĐỔ DỮ LIỆU VÀO QUEUE & IN RA
# ============================================================
queue = RateQueue(max_size=2000)

for r in rates:
    rate_dict = {
        'time': r['time'],
        'open': r['open'],
        'high': r['high'],
        'low': r['low'],
        'close': r['close'],
        'tick_volume': r['tick_volume'],
        'spread': r['spread'],
        'real_volume': r['real_volume']
    }
    queue.add(rate_dict)
queue.print_all()


# --- ví dụ dùng ---
size_bytes = get_queue_memory_usage(queue)
size_mb = size_bytes / (1024 * 1024)
print(f"💾 Queue chiếm khoảng: {size_mb:.3f} MB ({queue.size()} nến)")

# ============================================================
# 🧩 CHUYỂN RATES -> DATAFRAME ĐỂ PHÂN TÍCH
# ============================================================
data = list(queue.queue)
df = pd.DataFrame(data)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

trend = analyze_trend(df)
print("📊 Phân tích xu hướng:", trend)

# --- Kết thúc ---
mt5.shutdown()
