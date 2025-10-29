
import os 
import sys 

# --- Setup path --- 
ROOT = os.path.join(os.path.dirname(__file__), "..", "src") 
ROOT = os.path.abspath(ROOT)

sys.path.append(ROOT) 
print("ROOT:", ROOT) 
print("Folders:", os.listdir(ROOT))

import asyncio
import MetaTrader5 as mt5
from datetime import datetime
from aiomql.contrib.strategies import Signals_V1
from aiomql.contrib.symbols import ForexSymbol
from aiomql.lib.signal_bot import SignalBot
from aiomql.core.constants import TimeFrame
from aiomql.lib.noti import TelegramNotifier
import pandas as pd

SYMBOLS = ["EURUSD"]
START_DATE = "2025-10-01"
END_DATE = "2025-10-09"

# Test Mode: "live" hoặc "backtest"
TEST_MODE = "backtest"  # Đổi thành "live" để chạy real-time

# --- Parameters cho strategy ---
STRATEGY_PARAMS = {
    "fast_ema": 8,
    "slow_ema": 20,
    "ltf": TimeFrame.M1,
    "htf": TimeFrame.M5,
    "lcc": 100,
    "hcc": 100,
    "interval": 60,
    "telegram_enabled": True
}


def backtest_signals():
    """Test signals trên dữ liệu lịch sử"""
    
    print(f"\n📊 BACKTEST MODE: {START_DATE} → {END_DATE}\n")
    
    # Khởi tạo MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialize failed: {mt5.last_error()}")
        return
    
    try:
        notifier = TelegramNotifier(silent=False)
        telegram_enabled = True
    except:
        print("⚠️ Telegram not configured, will use console only")
        notifier = None
        telegram_enabled = False
    
    # Convert dates
    start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(END_DATE, "%Y-%m-%d")
    
    total_signals = 0
    
    for symbol_name in SYMBOLS:
        print(f"\n{'='*60}")
        print(f"🔍 Testing {symbol_name}...")
        print(f"{'='*60}")
        
        # Enable symbol
        if not mt5.symbol_select(symbol_name, True):
            print(f"❌ Failed to select {symbol_name}")
            continue
        
        # Lấy dữ liệu lịch sử - dùng HTF từ config
        htf = STRATEGY_PARAMS['htf']
        
        # Convert TimeFrame enum sang MT5 timeframe
        timeframe_map = {
            TimeFrame.M1: mt5.TIMEFRAME_M1,
            TimeFrame.M5: mt5.TIMEFRAME_M5,
            TimeFrame.M15: mt5.TIMEFRAME_M15,
            TimeFrame.M30: mt5.TIMEFRAME_M30,
            TimeFrame.H1: mt5.TIMEFRAME_H1,
            TimeFrame.H4: mt5.TIMEFRAME_H4,
            TimeFrame.D1: mt5.TIMEFRAME_D1,
        }
        
        mt5_timeframe = timeframe_map.get(htf, mt5.TIMEFRAME_H4)
        print(f"📊 Using timeframe: {htf.name} ({mt5_timeframe})")
        
        rates = mt5.copy_rates_range(
            symbol_name,
            mt5_timeframe,  # ✅ Dùng đúng timeframe từ config
            start_dt,
            end_dt
        )
        
        if rates is None or len(rates) == 0:
            print(f"❌ No data for {symbol_name}")
            continue
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        print(f"📈 Loaded {len(df)} candles")
        
        # Tính EMA
        fast_ema = STRATEGY_PARAMS['fast_ema']
        slow_ema = STRATEGY_PARAMS['slow_ema']
        
        df['ema_fast'] = df['close'].ewm(span=fast_ema, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_ema, adjust=False).mean()
        
        # Phát hiện tín hiệu
        signals = []
        
        # Cần ít nhất 50 cây nến để EMA ổn định
        warmup_period = max(50, slow_ema * 2)
        
        for i in range(warmup_period, len(df)):
            prev_fast = df['ema_fast'].iloc[i-1]
            prev_slow = df['ema_slow'].iloc[i-1]
            curr_fast = df['ema_fast'].iloc[i]
            curr_slow = df['ema_slow'].iloc[i]
            
            signal = None
            
            # === CÁCH 1: Crossover với confirmation ===
            # Không cần threshold lớn, nhưng phải confirm trong 2-3 cây nến
            
            # Check crossover đơn giản
            prev_bullish = prev_fast < prev_slow
            curr_bullish = curr_fast > curr_slow
            prev_bearish = prev_fast > prev_slow
            curr_bearish = curr_fast < curr_slow
            
            # Điều kiện bổ sung: Momentum phải mạnh
            fast_momentum = curr_fast - prev_fast  # Fast EMA đang tăng/giảm bao nhiêu
            slow_momentum = curr_slow - prev_slow
            momentum_diff = abs(fast_momentum - slow_momentum)
            
            # Tăng yêu cầu momentum lên 1 pip (từ 0.5 pip)
            min_momentum = 0.00010  # Ít nhất 1 pip momentum
            min_momentum_diff = 0.00010  # Momentum diff cũng phải >1 pip
            
            # Thêm điều kiện: Price phải confirm trend
            price_change = df['close'].iloc[i] - df['close'].iloc[i-1]
            
            # Bullish crossover với momentum mạnh + price confirm
            if (prev_bullish == False and curr_bullish == True and 
                fast_momentum > min_momentum and      # Fast tăng >1 pip
                momentum_diff > min_momentum_diff and # Chênh lệch >1 pip
                price_change > 0):                    # Giá phải đang tăng
                signal = "BUY"
                
            # Bearish crossover với momentum mạnh + price confirm
            elif (prev_bearish == False and curr_bearish == True and
                  fast_momentum < -min_momentum and    # Fast giảm >1 pip
                  momentum_diff > min_momentum_diff and # Chênh lệch >1 pip
                  price_change < 0):                    # Giá phải đang giảm
                signal = "SELL"
            
            if signal:
                signal_time = df['time'].iloc[i]
                
                # ✅ Chỉ lấy signals trong khoảng START_DATE → END_DATE
                if signal_time < start_dt or signal_time > end_dt:
                    continue  # Bỏ qua signal ngoài range
                
                signal_data = {
                    'time': signal_time,
                    'symbol': symbol_name,
                    'type': signal,
                    'price': df['close'].iloc[i],
                    'ema_fast': curr_fast,
                    'ema_slow': curr_slow
                }
                signals.append(signal_data)
                
                # In ra console với thêm thông tin debug
                emoji = "🟢" if signal == "BUY" else "🔴"
                distance = abs(curr_fast - curr_slow)
                prev_distance = abs(prev_fast - prev_slow)
                
                print(f"\n{emoji} SIGNAL #{len(signals)}")
                print(f"   Time: {signal_data['time']}")
                print(f"   Type: {signal}")
                print(f"   Price: {signal_data['price']:.5f}")
                print(f"   Price Change: {price_change:.5f} ({price_change*10000:.1f} pips)")
                print(f"   EMA Fast: {curr_fast:.5f}")
                print(f"   EMA Slow: {curr_slow:.5f}")
                print(f"   Prev Fast: {prev_fast:.5f}")
                print(f"   Prev Slow: {prev_slow:.5f}")
                print(f"   Distance: {distance:.5f} ({distance*10000:.1f} pips)")
                print(f"   Fast Momentum: {fast_momentum:.5f} ({fast_momentum*10000:.1f} pips)")
                print(f"   Momentum Diff: {momentum_diff:.5f} ({momentum_diff*10000:.1f} pips)")
                
                # Gửi Telegram
                if notifier and telegram_enabled:
                    message = f"{emoji} SIGNAL DETECTED (BACKTEST)\n\n"
                    message += f"Symbol: {symbol_name}\n"
                    message += f"Time: {signal_data['time']}\n"
                    message += f"Type: {signal}\n"
                    message += f"Price: {signal_data['price']:.5f}\n"
                    message += f"EMA Fast ({fast_ema}): {curr_fast:.5f}\n"
                    message += f"EMA Slow ({slow_ema}): {curr_slow:.5f}"
                    
                    notifier.send_plain(message)
        
        print(f"\n✅ {symbol_name}: Found {len(signals)} signals")
        total_signals += len(signals)
        
        # Lưu signals vào CSV (optional)
        if signals:
            signals_df = pd.DataFrame(signals)
            filename = f"signals_{symbol_name}_{START_DATE}_{END_DATE}.csv"
            signals_df.to_csv(filename, index=False)
            print(f"💾 Saved to {filename}")
    
    print(f"\n{'='*60}")
    print(f"🎯 TOTAL SIGNALS FOUND: {total_signals}")
    print(f"{'='*60}\n")
    
    mt5.shutdown()


def main_live():
    """Chạy Signal Bot real-time"""
    
    print("\n🤖 LIVE MODE: Real-time Signal Detection\n")
    
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
        bot.execute()
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping bot...")
        bot.shutdown_sync()
        print("✅ Bot stopped successfully")


async def main_live_async():
    """Phiên bản async của live mode"""
    
    print("\n🤖 LIVE MODE (Async): Real-time Signal Detection\n")
    
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
    print(f"\n{'='*60}")
    print(f"📡 SIGNAL DETECTION BOT")
    print(f"{'='*60}")
    print(f"Mode: {TEST_MODE.upper()}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    
    if TEST_MODE == "backtest":
        print(f"Period: {START_DATE} → {END_DATE}")
        print(f"{'='*60}\n")
        backtest_signals()
    else:
        print(f"{'='*60}\n")
        # Chọn live mode
        main_live()
        # Hoặc async: asyncio.run(main_live_async())