import os
import sys
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# --- Setup path ---
ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)
print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))

# --- Import ---
from aiomql.contrib.strategies import Signals_V2
from aiomql.contrib.symbols import ForexSymbol

# --- Hàm chính ---
async def run_nyc_session():
    print(f"\nNYC SESSION BACKTEST (Signals_V2)\n")

    if not mt5.initialize():
        print(f"MT5 initialize failed: {mt5.last_error()}")
        return
    print("MT5 initialized")

    if not mt5.symbol_select("EURUSD", True):
        print(f"Failed to select EURUSD: {mt5.last_error()}")
        mt5.shutdown()
        return
    print("EURUSD selected")

    try:
        symbol = ForexSymbol(name="EURUSD")
        strategy = Signals_V2(
            symbol=symbol,
            params={
                "telegram_enabled": False,  # khỏi spam Telegram
                "min_candles": 30,
                "session": "NYC"
            }
        )

        # 🧠 Chạy test cho ngày hôm qua
        yesterday = datetime.now() - timedelta(days=1)
        await strategy.trade_backtest_v2(yesterday)

    finally:
        mt5.shutdown()
        print("MT5 shutdown")

if __name__ == "__main__":
    asyncio.run(run_nyc_session())
