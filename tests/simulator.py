# simulator.py
# Giả lập stream nến từ queue, phân tích trend, và mô phỏng 1 tài khoản giả $1000
# Chạy file này sau khi m đã load rates từ MT5 (hoặc script này tự fetch lại).
# Lưu ý: P/L tính đơn giản theo phần trăm biến động giá so với giá vào.
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))

import time
from datetime import datetime, timezone
import pytz
import MetaTrader5 as mt5
import pandas as pd
from collections import deque

# --- Copy các lớp/hàm từ code chính (RateQueue, analyze_trend, get_timeframe_auto) ---
class RateQueue:
    def __init__(self, max_size=2000):
        self.queue = deque(maxlen=max_size)
    def add(self, rate):
        if not isinstance(rate, dict):
            raise TypeError("Rate must be a dictionary")
        self.queue.append(rate)
    def clear(self):
        self.queue.clear()
    def pop(self):
        if not self.queue:
            return None
        return self.queue.popleft()
    def size(self):
        return len(self.queue)
    def to_list(self):
        return list(self.queue)

# Nếu m đã có analyze_trend trong module khác, import thay vì copy
import pandas_ta as ta
import pandas as pd

def analyze_trend(df: pd.DataFrame):
    """Như đã định nghĩa: EMA + MACD => trả về trend string"""
    # guard: nếu df quá ngắn thì trả UNKNOWN
    if len(df) < 60:
        return "⚪ TOO_SHORT"

    df = df.copy()
    df["EMA_20"] = ta.ema(df["close"], length=20)
    df["EMA_50"] = ta.ema(df["close"], length=50)
    macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df = pd.concat([df, macd_df], axis=1)

    latest = df.iloc[-1]
    # bảo đảm các cột MACD tồn tại
    macd_key = "MACD_12_26_9"
    macds_key = "MACDs_12_26_9"
    if macd_key not in df.columns or macds_key not in df.columns:
        return "⚪ INDICATOR_MISSING"

    ema_up = latest["EMA_20"] > latest["EMA_50"]
    macd_up = latest[macd_key] > latest[macds_key]

    if ema_up and macd_up:
        return "UPTREND"
    elif not ema_up and not macd_up:
        return "DOWNTREND"
    elif ema_up and not macd_up:
        return "WEAK_UP"
    elif not ema_up and macd_up:
        return "WEAK_DOWN"
    else:
        return "SIDEWAY"

# ================== Simulator config ==================
SIM_START_DATE = datetime(2025, 10, 1, tzinfo=pytz.timezone("Etc/UTC"))
SIM_END_DATE = datetime(2025, 10, 27, tzinfo=pytz.timezone("Etc/UTC"))
SIMULATE_SPEED = 0  # seconds per candle (0.05 => fast). Set 0 for no sleep (batch mode)
INVEST_PER_TRADE = 100.0  # $100 mỗi trade (mô phỏng)
INITIAL_BALANCE = 1000.0
LOT = 1
SYMBOL = "USDJPY"
TF = mt5.TIMEFRAME_M15    # giả sử data là H1; nếu khác, code vẫn chạy với rates tương ứng
MAX_QUEUE_SIZE = 2000
# =====================================================

def simulate_from_rates(rates, start_dt=SIM_START_DATE, speed=SIMULATE_SPEED):
    data_list = []
    for r in rates:
        if isinstance(r, dict):
            data_list.append(r)
        else:
            data_list.append({
                'time': int(r[0]),
                'open': float(r[1]),
                'high': float(r[2]),
                'low': float(r[3]),
                'close': float(r[4]),
                'tick_volume': int(r[5]),
                'spread': int(r[6]) if len(r) > 6 else 0,
                'real_volume': int(r[7]) if len(r) > 7 else 0
            })

    start_ts = int(start_dt.timestamp())
    idx = 0
    while idx < len(data_list) and data_list[idx]['time'] < start_ts:
        idx += 1

    queue = RateQueue(max_size=MAX_QUEUE_SIZE)
    balance = INITIAL_BALANCE
    position = None
    trades = []

    print(f"🔁 Sim start from idx={idx}, time={start_dt.isoformat()}, total candles={len(data_list)-idx}")

    for i in range(idx, len(data_list)):
        candle = data_list[i]

        # skip nến ngoài khoảng sim
        candle_time = pd.to_datetime(candle['time'], unit='s').tz_localize('UTC')
        if candle_time > SIM_END_DATE:
            break

        queue.add(candle)
        df = pd.DataFrame(queue.to_list())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        # indicators
        if len(df) < 60:
            trend = "⚪ TOO_SHORT"
        else:
            df["EMA_20"] = ta.ema(df["close"], length=20)
            df["EMA_50"] = ta.ema(df["close"], length=50)
            macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
            df = pd.concat([df, macd_df], axis=1)
            df["RSI_14"] = ta.rsi(df["close"], length=14)
            df["ATR_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)

            latest = df.iloc[-1]
            ema_up = latest["EMA_20"] > latest["EMA_50"]
            macd_up = latest["MACD_12_26_9"] > latest["MACDs_12_26_9"]
            rsi_ok = latest["RSI_14"] < 70  # tránh quá mua

            trend = "UPTREND" if ema_up and macd_up and rsi_ok else \
                    "DOWNTREND" if not ema_up and not macd_up and latest["RSI_14"] > 30 else \
                    "SIDEWAY"

        close_price = candle['close']

        # convert candle time sang VN time
        candle_vn_time = pd.to_datetime(candle['time'], unit='s').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh')
        hour_min = candle_vn_time.hour * 60 + candle_vn_time.minute  # phút trong ngày
        trade_allowed = not (1140 <= hour_min < 1185)  # 19:00→19:45 = 1140→1185 phút


        # OPEN LONG với trend filter mạnh
        if trend == "UPTREND" and position is None and balance >= INVEST_PER_TRADE and trade_allowed:
            atr = latest["ATR_14"]

            # --- xác định strength của Uptrend ---
            candle_range = candle['high'] - candle['low']
            if candle_range > 2 * atr:
                strength = "STRONG_UP"
                lot = LOT * 2       # tăng lot
                tp_mult = 2.5       # TP xa hơn
                sl_mult = 1.5       # SL rộng hơn
            elif candle_range > atr:
                strength = "MEDIUM_UP"
                lot = LOT
                tp_mult = 2.0
                sl_mult = 1.0
            else:
                strength = "WEAK_UP"
                lot = LOT * 0.5
                tp_mult = 1.5
                sl_mult = 0.7

            position = {
                'side': 'LONG',
                'entry_price': close_price,
                'invest': INVEST_PER_TRADE,
                'entry_time': candle_vn_time,
                'SL': close_price - atr * sl_mult,
                'TP': close_price + atr * tp_mult,
                'lot': lot,
                'strength': strength
            }
            balance -= INVEST_PER_TRADE
            print(f"[{candle_vn_time}] ➕ OPEN LONG @ {close_price:.5f} invest=${INVEST_PER_TRADE:.2f} LOT={lot} SL={position['SL']:.5f} TP={position['TP']:.5f} strength={strength} balance=${balance:.2f}")

        # trong phần CHECK LONG exit
        elif position is not None and position['side'] == 'LONG':
            if trend == "DOWNTREND" or close_price <= position['SL'] or close_price >= position['TP']:
                # tính P/L theo LOT
                pip = 0.01 if SYMBOL.endswith("JPY") else 0.0001  # EURUSD H4
                ret = (close_price - position['entry_price']) 
                pnl = ret * position['lot'] * 10  # mỗi LOT 0.1 → 1 pip ~ $10
                balance += position['invest'] + pnl
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': pd.to_datetime(candle['time'], unit='s'),
                    'entry_price': position['entry_price'],
                    'exit_price': close_price,
                    'invest': position['invest'],
                    'pnl': pnl,
                    'lot': position['lot']
                })
                print(f"[{pd.to_datetime(candle['time'], unit='s')}] ➖ CLOSE LONG @ {close_price:.5f} P/L=${pnl:.2f} balance=${balance:.2f}")
                position = None

        # OPEN SHORT
        if trend == "DOWNTREND" and position is None and balance >= INVEST_PER_TRADE and trade_allowed:
            atr = latest["ATR_14"]

            candle_range = candle['high'] - candle['low']
            if candle_range > 2 * atr:
                strength = "STRONG_DOWN"
                lot = LOT * 2
                tp_mult = 2.5
                sl_mult = 1.5
            elif candle_range > atr:
                strength = "MEDIUM_DOWN"
                lot = LOT
                tp_mult = 2.0
                sl_mult = 1.0
            else:
                strength = "WEAK_DOWN"
                lot = LOT * 0.5
                tp_mult = 1.5
                sl_mult = 0.7

            position = {
                'side': 'SHORT',
                'entry_price': close_price,
                'invest': INVEST_PER_TRADE,
                'entry_time': candle_vn_time,
                'SL': close_price + atr * sl_mult,
                'TP': close_price - atr * tp_mult,
                'lot': lot,
                'strength': strength
            }
            balance -= INVEST_PER_TRADE
            print(f"[{candle_vn_time}] ➖ OPEN SHORT @ {close_price:.5f} invest=${INVEST_PER_TRADE:.2f} LOT={lot} SL={position['SL']:.5f} TP={position['TP']:.5f} strength={strength} balance=${balance:.2f}")

        # CHECK SHORT exit
        elif position is not None and position['side'] == 'SHORT':
            if trend == "UPTREND" or close_price >= position['SL'] or close_price <= position['TP']:
                pip = 0.01 if SYMBOL.endswith("JPY") else 0.0001
                ret = (position['entry_price'] - close_price)
                pnl = ret * position['lot'] * 10
                balance += position['invest'] + pnl
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': candle_vn_time,
                    'entry_price': position['entry_price'],
                    'exit_price': close_price,
                    'invest': position['invest'],
                    'pnl': pnl,
                    'lot': position['lot']
                })
                print(f"[{candle_vn_time}] ➕ CLOSE SHORT @ {close_price:.5f} P/L=${pnl:.2f} balance=${balance:.2f}")
                position = None

    # auto-close cuối cùng
    if position is not None:
        last_price = data_list[-1]['close']
        ret = (last_price - position['entry_price']) if position['side'] == "LONG" else (position['entry_price'] - last_price)
        pnl = ret * position['lot'] * 10  # KHÔNG chia /0.0001 nữa
        balance += position['invest'] + pnl
        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': pd.to_datetime(data_list[-1]['time'], unit='s'),
            'entry_price': position['entry_price'],
            'exit_price': last_price,
            'invest': position['invest'],
            'pnl': pnl,
            'lot': position['lot']
        })
        print(f"[END] Auto-close position @ {last_price:.5f} P/L=${pnl:.2f} balance=${balance:.2f}")

# ---------------------------
# Example usage:
# ---------------------------
if __name__ == "__main__":
    # --- connect MT5 and fetch a wide range of data if not already available ---
    if not mt5.initialize(path='C:\\Program Files\\MetaTrader 5\\terminal64.exe'):
        raise RuntimeError("MT5 init failed")
    symbol = SYMBOL
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError("Symbol select failed")
    # fetch enough candles covering the simulation window (here fetch 10000 H1 candles as example)
    rates = mt5.copy_rates_from_pos(symbol, TF, 0, 10000)  # thay số lượng theo nhu cầu
    mt5.shutdown()

    # run simulation
    simulate_from_rates(rates, start_dt=SIM_START_DATE, speed=SIMULATE_SPEED)
