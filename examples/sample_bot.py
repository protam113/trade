import os
import sys
import logging
import asyncio
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
# 💤 Background coroutine (demo task)
# ============================================
async def sleep_run():
    while True:
        print("Sleeping for 5 seconds...")
        await asyncio.sleep(5)
        print("Hello World!")


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
# 🤖 Bot demo
# ============================================
def sample_bot():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # --- Login info ---
    login = 52575885
    password = "@q30SMKYhawwOa"
    server = "ICMarketsSC-Demo"
    path = r"C:\Program Files\MetaTrader 5\terminal64.exe"

    # --- Check environment ---
    check_mt5_env(login, password, server, path)

    # --- Ensure symbol availability ---
    symbols_to_load = ["EURUSD"]
    for sym in symbols_to_load:
        if not mt5.symbol_select(sym, True):
            print(f"⚠️ Failed to select symbol: {sym}")
        else:
            print(f"✅ Symbol {sym} loaded successfully!")

        info = mt5.symbol_info(sym)
        if info:
            print(f"👉 Symbol filling_mode for {sym}: {info.filling_mode}")
        else:
            print(f"⚠️ Could not retrieve symbol info for {sym}")

    # --- Define strategies ---
    symbols = [ForexSymbol(name=sym) for sym in symbols_to_load]
    # strategies = [FingerTrap(symbol=symbol) for symbol in symbols]

    # --- Create bot ---
    bot = Bot()
    bot.config.login = login
    bot.config.password = password
    bot.config.server = server

    # --- Add coroutine & strategies ---
    bot.executor.timeout = 10
    bot.add_coroutine(coroutine=sleep_run)
    # bot.add_strategies(strategies=strategies)

    # --- Run bot ---
    try:
        bot.execute()
    finally:
        mt5.shutdown()
        print("\n🛑 MetaTrader5 connection closed.")


# ============================================
# 🚀 Run main
# ============================================
if __name__ == "__main__":
    sample_bot()
