import os
import sys
import logging
import asyncio
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5

# --- Setup path ---
ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))

# --- Imports ---
from aiomql.lib.bot import Bot
from aiomql.contrib.strategies import Chaos, FingerTrap
from aiomql.contrib.symbols import ForexSymbol


# ============================================
# ⚙️ Cấu hình chế độ chạy
# ============================================
MODE = "backtest"  # "realtime" hoặc "backtest"
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M5
START_DATE = datetime(2025, 6, 1)
END_DATE = datetime(2025, 10, 1)


# ============================================
# 🧠 Kiểm tra môi trường MT5
# ============================================
def check_mt5_env(login: int, password: str, server: str, path: str):
    """Kiểm tra môi trường MT5 trước khi chạy bot"""
    print("\n🔍 Checking MetaTrader 5 environment...")

    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Không tìm thấy terminal: {path}")

    if not mt5.initialize(path=path, login=login, password=password, server=server):
        raise RuntimeError(f"❌ MT5 initialize() failed: {mt5.last_error()}")
    else:
        print("✅ Connected to MetaTrader5 Terminal")

    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError("❌ Không thể lấy thông tin tài khoản (account_info is None)")
    print(f"✅ Logged in as: {account_info.login}, balance={account_info.balance}")

    terminal_info = mt5.terminal_info()
    if not terminal_info.trade_allowed:
        raise PermissionError("⚠️ AutoTrading đang bị tắt trong MT5 — bật lại trước khi chạy bot!")

    print("✅ AutoTrading ENABLED")
    print("✅ Environment OK!\n")


# ============================================
# 💤 Background coroutine (demo task)
# ============================================
async def sleep_run():
    while True:
        print("Sleeping for 5 seconds...")
        await asyncio.sleep(5)
        print("Hello World!")


# ============================================
# 📊 Hàm tải dữ liệu MT5 (cho backtest)
# ============================================
def load_mt5_data(symbol: str, timeframe, start: datetime, end: datetime) -> pd.DataFrame:
    """Lấy dữ liệu lịch sử từ MT5"""
    print(f"\n📥 Đang tải dữ liệu {symbol} từ {start} đến {end}...")
    rates = mt5.copy_rates_range(symbol, timeframe, start, end)

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"❌ Không thể lấy dữ liệu {symbol}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    print(f"✅ Đã tải {len(df)} cây nến {symbol}")
    return df


# ============================================
# 🤖 Bot chạy realtime (online)
# ============================================
def run_realtime_bot():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # --- Login info ---
    login = 52575885
    password = "@q30SMKYhawwOa"
    server = "ICMarketsSC-Demo"
    path = r"C:\Program Files\MetaTrader 5\terminal64.exe"

    # --- Check environment ---
    check_mt5_env(login, password, server, path)

    # --- Ensure symbol availability ---
    if not mt5.symbol_select(SYMBOL, True):
        print(f"⚠️ Failed to select symbol: {SYMBOL}")
    else:
        print(f"✅ Symbol {SYMBOL} loaded successfully!")

    # --- Define strategies ---
    symbol_obj = ForexSymbol(name=SYMBOL)
    strategies = [Chaos(symbol=symbol_obj)]

    # --- Create bot ---
    bot = Bot()
    bot.config.login = login
    bot.config.password = password
    bot.config.server = server

    bot.executor.timeout = 10
    bot.add_coroutine(coroutine=sleep_run)
    bot.add_strategies(strategies=strategies)

    # --- Run bot ---
    try:
        bot.execute()
    finally:
        mt5.shutdown()
        print("\n🛑 MetaTrader5 connection closed.")


# ============================================
# 🧪 Backtest bot (offline)
# ============================================
async def run_backtest():
    # --- Kết nối MT5 ---
    if not mt5.initialize():
        raise RuntimeError("❌ Không thể khởi tạo MT5")

    df = load_mt5_data(SYMBOL, TIMEFRAME, START_DATE, END_DATE)

    # --- Setup chiến lược ---
    symbol_obj = ForexSymbol(name=SYMBOL)
    strategy = FingerTrap(symbol=symbol_obj)

    print("\n🚀 Bắt đầu mô phỏng chiến lược FingerTrap...\n")
    print(f"{'='*80}")
    print(f"{'Time':<20} | {'Signal':<6} | {'Price':<10} | {'SL':<10}")
    print(f"{'='*80}")

    trade_count = 0
    
    # QUAN TRỌNG: Indentation phải đúng!
    for _, row in df.iterrows():
        tick = {"time": row["time"], "bid": row["close"], "ask": row["close"]}
        signal = await strategy.on_tick(tick)

        # In tín hiệu nếu có (phải nằm TRONG vòng lặp for)
        if signal:
            trade_count += 1
            print(f"{signal['time']} | {signal['type']:<6} | {signal['price']:<10.5f} | {signal['sl']:<10.5f}")

        await asyncio.sleep(0.001)  # Cũng phải nằm TRONG vòng lặp

    print(f"{'='*80}")
    print(f"\n✅ Backtest hoàn tất! Tổng số tín hiệu: {trade_count}")
    
    mt5.shutdown()


# ============================================
# 🚀 MAIN ENTRY
# ============================================
if __name__ == "__main__":
    if MODE == "realtime":
        run_realtime_bot()
    else:
        asyncio.run(run_backtest())