import os 
import sys 
import asyncio

# --- Setup path --- 
ROOT = os.path.join(os.path.dirname(__file__), "..", "src") 
ROOT = os.path.abspath(ROOT)

sys.path.append(ROOT) 
print("ROOT:", ROOT) 
print("Folders:", os.listdir(ROOT))

from aiomql.contrib.strategies import Signals_V1
from aiomql.contrib.symbols import ForexSymbol
from aiomql.lib.signal_bot import SignalBot
from aiomql.core.constants import TimeFrame

# --- Config ---
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY"]
START_DATE = "2025-01-01"
END_DATE = "2025-06-01"

# --- Parameters cho strategy ---
STRATEGY_PARAMS = {
    "fast_ema": 8,
    "slow_ema": 20,
    "ltf": TimeFrame.M1,
    "htf": TimeFrame.M5,  # Dùng M5 cho dễ test
    "lcc": 100,
    "hcc": 100,
    "interval": 60,  # Check mỗi 60 giây
    "telegram_enabled": True  # Bật Telegram
}


def main():
    """Chạy Signal Bot với Signals_V1 strategy"""
    
    print("\n🤖 Starting Signal Detection Bot...")
    
    # Tạo bot
    bot = SignalBot()
    
    # Thêm strategy cho từng symbol
    for symbol_name in SYMBOLS:
        try:
            # Tạo symbol
            symbol = ForexSymbol(name=symbol_name)
            
            # Tạo strategy instance
            strategy = Signals_V1(
                symbol=symbol,
                params=STRATEGY_PARAMS,
                name=f"Signals_V1_{symbol_name}"
            )
            
            # Thêm vào bot
            bot.add_strategy(strategy=strategy)
            print(f"✅ Added strategy for {symbol_name}")
            
        except Exception as e:
            print(f"❌ Failed to add {symbol_name}: {e}")
    
    # Chạy bot
    print("\n🚀 Starting signal monitoring...")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Chạy bot (blocking)
        bot.execute()
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping bot...")
        bot.shutdown_sync()
        print("✅ Bot stopped successfully")


async def main_async():
    """Phiên bản async của main (nếu cần)"""
    
    print("\n🤖 Starting Signal Detection Bot (Async)...")
    
    bot = SignalBot()
    
    for symbol_name in SYMBOLS:
        try:
            symbol = ForexSymbol(name=symbol_name)
            strategy = Signals_V1(
                symbol=symbol,
                params=STRATEGY_PARAMS,
                name=f"Signals_V1_{symbol_name}"
            )
            bot.add_strategy(strategy=strategy)
            print(f"✅ Added strategy for {symbol_name}")
        except Exception as e:
            print(f"❌ Failed to add {symbol_name}: {e}")
    
    print("\n🚀 Starting signal monitoring...")
    print("Press Ctrl+C to stop\n")
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping bot...")
        await bot.shutdown()
        print("✅ Bot stopped successfully")


if __name__ == "__main__":
    # Chọn 1 trong 2 cách chạy:
    
    # Cách 1: Sync (đơn giản)
    main()
    
    # Cách 2: Async (nếu cần tích hợp async code khác)
    # asyncio.run(main_async())