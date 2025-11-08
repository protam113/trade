import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# --- Setup path ---
ROOT = os.path.join(os.path.dirname(__file__), "../..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)

# --- Load environment variables ---
load_dotenv()

# --- Imports ---
import MetaTrader5 as mt5
from aiomql.lib.bot import Bot
from aiomql.contrib.symbols import ForexSymbol
from aiomql.contrib.strategies import EUR_SCALP
import json


# --- Config ---
MODE = "realtime"
TIMEFRAME = mt5.TIMEFRAME_M5

def load_symbols_from_json(file_path="symbols.json") -> list:
    """Đọc danh sách symbols từ file JSON và sắp xếp theo spread tăng dần"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Lọc ra các entry có 'symbol' và 'spread' hợp lệ
    valid_data = [item for item in data if "symbol" in item and "spread" in item]

    # Sắp xếp theo spread tăng dần (nhỏ → lớn)
    sorted_data = sorted(valid_data, key=lambda x: x.get("spread", float("inf")))

    # Lấy danh sách symbol sau khi sắp xếp
    symbols = [item["symbol"] for item in sorted_data]

    print(f"✅ Loaded {len(symbols)} symbols from {file_path} (sorted by spread ↑)")
    # Hiển thị top 5 để debug
    for s in sorted_data[:5]:
        print(f"  • {s['symbol']} (spread={s['spread']})")

    return symbols


SYMBOLS = load_symbols_from_json(os.path.join(os.path.dirname(__file__), "symbols.json"))

# ============================================
# [1] Setup Logging
# ============================================
def setup_logging():
    """Setup logging với file rotation"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # File handler (max 10MB, 5 backups)
    file_handler = RotatingFileHandler(
        'bot_logs.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


# ============================================
# [2] MT5 Environment Test
# ============================================
def check_mt5_env(login: int, password: str, server: str, path: str):
    print("\n🔍 Checking MetaTrader 5 environment...")

    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Không tìm thấy terminal: {path}")

    if not mt5.initialize(path=path, login=login, password=password, server=server):
        raise RuntimeError(f"❌ MT5 initialize() failed: {mt5.last_error()}")
    else:
        print("✅ Connected to MetaTrader5 Terminal")

    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError("❌ Không thể lấy thông tin tài khoản")
    print(f"✅ Logged in as: {account_info.login}, balance={account_info.balance}")

    terminal_info = mt5.terminal_info()
    if not terminal_info.trade_allowed:
        raise PermissionError("⚠️ AutoTrading đang bị tắt trong MT5!")

    print("✅ AutoTrading ENABLED")
    print("✅ Environment OK!\n")


# ============================================
# [3] Load and check symbols
# ============================================
def load_symbols(symbols: list) -> list:
    """Load và kiểm tra các symbols có sẵn trong MT5"""
    loaded_symbols = []
    failed_symbols = []

    print(f"\n📦 Loading {len(symbols)} symbols...")

    for symbol in symbols:
        if mt5.symbol_select(symbol, True):
            info = mt5.symbol_info(symbol)
            # Kiểm tra visible + trade_mode
            if (info is not None and 
                info.visible and 
                info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED):
                loaded_symbols.append(symbol)
                print(f"  ✅ {symbol} - Ready (spread={info.spread})")
            else:
                failed_symbols.append(symbol)
                print(f"  ⚠️ {symbol} - Not tradeable or not visible")
        else:
            failed_symbols.append(symbol)
            print(f"  ❌ {symbol} - Failed to select")

    print(f"\n✅ Loaded: {len(loaded_symbols)}/{len(symbols)} symbols")
    if failed_symbols:
        print(f"⚠️ Failed symbols: {', '.join(failed_symbols)}")

    return loaded_symbols


# ============================================
# [4] Check the open market
# ============================================
def is_market_open() -> bool:
    """Kiểm tra xem thị trường Forex có đang mở không"""
    now = datetime.now()
    # Forex đóng cửa thứ 7 và chủ nhật sáng
    if now.weekday() == 5:  # Saturday
        return False
    if now.weekday() == 6 and now.hour < 22:  # Sunday before 22:00
        return False
    return True


# ============================================
# [5] Background monitoring
# ============================================
async def monitor_bot():
    """Background task để monitor trạng thái bot"""
    while True:
        await asyncio.sleep(300)  # 5 phút
        if is_market_open():
            account = mt5.account_info()
            if account:
                logging.info(
                    f"🔄 Bot running | Balance: {account.balance} | "
                    f"Equity: {account.equity} | Profit: {account.profit}"
                )
            else:
                logging.warning("⚠️ Cannot get account info")
        else:
            logging.info("⏸️ Market closed - bot paused")


# ============================================
# [6] Bot runs in real time
# ============================================
def run_realtime_bot():
    setup_logging()

    login = int(os.getenv("MT5_ACCOUNT", "52575885"))
    password = os.getenv("MT5_PASSWORD", "@q30SMKYhawwOa")
    server = os.getenv("MT5_SERVER", "ICMarketsSC-Demo")
    path = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")

    check_mt5_env(login, password, server, path)

    loaded_symbols = load_symbols(SYMBOLS)

    if not loaded_symbols:
        raise RuntimeError("❌ Không có symbol nào được load thành công!")

    strategies = []
    for symbol in loaded_symbols:
        try:
            symbol_obj = ForexSymbol(name=symbol)
            strategy = EUR_SCALP(symbol=symbol_obj)
            strategies.append(strategy)
            logging.info(f"[ADD] Added strategy for {symbol}")
        except Exception as e:
            logging.error(f"⚠️ Failed to create strategy for {symbol}: {e}")

    if not strategies:
        raise RuntimeError("❌ Không có strategy nào được tạo thành công!")

    print(f"\n✅ Total strategies: {len(strategies)}")

    # Create bot
    bot = Bot()
    bot.config.login = login
    bot.config.password = password
    bot.config.server = server

    # Tăng timeout cho nhiều symbol
    bot.executor.timeout = 60  # 60 giây

    # Add monitoring coroutine
    bot.add_coroutine(coroutine=monitor_bot)
    bot.add_strategies(strategies=strategies)

    # Run bot
    try:
        print("\n🚀 Starting bot with multi-symbol trading...\n")
        logging.info(f"Bot started with {len(strategies)} strategies")
        bot.execute()
    except KeyboardInterrupt:
        print("\n⚠️ Bot stopped by user (Ctrl+C)")
        logging.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        logging.error(f"Bot error: {e}", exc_info=True)
    finally:
        mt5.shutdown()
        print("\n🛑 MetaTrader5 connection closed.")
        logging.info("Bot shutdown completed")


# ============================================
# [7] MAIN ENTRY
# ============================================
if __name__ == "__main__":
    run_realtime_bot()