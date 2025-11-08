# Bot M5

import os 
import sys 
from datetime import datetime
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import time

# --- Setup path --- 
ROOT = os.path.join(os.path.dirname(__file__), "..", "src") 
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT) 

import pandas_ta as ta

# ==================== CONFIGURATION ====================
SYMBOLS = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "EURAUD", "EURCAD", 
           "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD", "GBPAUD", "GBPCAD", 
           "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", 
           "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
ACCOUNT = {
    "login": 52575885, 
    "password": '@q30SMKYhawwOa', 
    "server": 'ICMarketsSC-Demo'
}

# Strategy Parameters
TIMEFRAME = mt5.TIMEFRAME_M5
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
TP_PIPS = 30
SL_PIPS = 15
LOT_SIZE = 0.1

# Number of bars to analyze for indicators (need history for MACD calculation)
INDICATOR_BARS = 100

# Check interval (seconds)
CHECK_INTERVAL = 60  # Check every 60 seconds (1 minute) for new candles


# ==================== MT5 CONNECTION ====================
def initialize_mt5():
    """Initialize MetaTrader 5 connection"""
    if not mt5.initialize():
        print("MT5 initialization failed")
        return False
    
    # Login to account
    authorized = mt5.login(
        login=ACCOUNT["login"],
        password=ACCOUNT["password"],
        server=ACCOUNT["server"]
    )
    
    if authorized:
        account_info = mt5.account_info()
        print(f"✅ Connected to MT5 Account: {account_info.login}")
        print(f"   Balance: ${account_info.balance:.2f}")
        print(f"   Equity: ${account_info.equity:.2f}")
        print(f"   Server: {account_info.server}")
        return True
    else:
        print(f"❌ Login failed. Error: {mt5.last_error()}")
        return False


def get_latest_data(symbol, timeframe, bars):
    """Fetch latest market data from MT5"""
    # Try to get symbol info first to check if it exists
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        # Try alternative formats
        alt_formats = [
            symbol,
            symbol + ".a",  # Some brokers use .a suffix
            symbol + "m",   # Some brokers use m suffix
            symbol.replace("/", ""),  # Remove slashes if any
        ]
        
        for alt_symbol in alt_formats:
            symbol_info = mt5.symbol_info(alt_symbol)
            if symbol_info is not None:
                symbol = alt_symbol
                break
        
        if symbol_info is None:
            return None
    
    # Make sure symbol is visible in Market Watch
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            return None
    
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    
    if rates is None or len(rates) == 0:
        return None
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    return df


# ==================== INDICATOR CALCULATION ====================
def calculate_indicators(df):
    """Calculate MACD and Volume indicators"""
    # Calculate MACD using pandas_ta
    macd_df = ta.macd(
        df['close'], 
        fast=MACD_FAST, 
        slow=MACD_SLOW, 
        signal=MACD_SIGNAL,
        signal_indicators=False
    )
    
    # Merge MACD with main dataframe
    df = pd.concat([df, macd_df], axis=1)
    
    # Calculate Fast and Slow EMA separately for crossover detection
    df['ema_fast'] = ta.ema(df['close'], length=MACD_FAST)
    df['ema_slow'] = ta.ema(df['close'], length=MACD_SLOW)
    
    # Volume color (green if close > open, red otherwise)
    df['volume_green'] = df['close'] > df['open']
    df['volume_red'] = df['close'] < df['open']
    
    # Detect EMA crossovers
    df['ema_cross_up'] = (df['ema_fast'] > df['ema_slow']) & \
                          (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
    df['ema_cross_down'] = (df['ema_fast'] < df['ema_slow']) & \
                            (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1))
    
    return df


def check_signal(df):
    """Check for buy/sell signals on the latest completed candle"""
    if len(df) < 2:
        return None
    
    # Check the second-to-last bar (last completed candle)
    signal_bar = df.iloc[-2]
    
    macd_col = f'MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    signal_col = f'MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
    
    # Buy Signal Conditions
    if (signal_bar['volume_green'] and 
        signal_bar['ema_cross_up'] and 
        signal_bar[macd_col] > 0 and 
        signal_bar[signal_col] > 0):
        return 'BUY'
    
    # Sell Signal Conditions
    elif (signal_bar['volume_red'] and 
          signal_bar['ema_cross_down'] and 
          signal_bar[macd_col] < 0 and 
          signal_bar[signal_col] < 0):
        return 'SELL'
    
    return None


# ==================== POSITION MANAGEMENT ====================
def get_open_positions(symbol):
    """Get all open positions for a symbol"""
    positions = mt5.positions_get(symbol=symbol)
    return positions if positions is not None else []


def close_position(position):
    """Close an open position"""
    tick = mt5.symbol_info_tick(position.symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_BUY if position.type == 1 else mt5.ORDER_TYPE_SELL,
        "position": position.ticket,
        "price": tick.ask if position.type == 1 else tick.bid,
        "deviation": 20,
        "magic": 234000,
        "comment": "Close by strategy",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    return result


def place_order(symbol, order_type, lot_size, tp_pips, sl_pips):
    """Place a new market order with TP and SL"""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found")
        return None
    
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select {symbol}")
            return None
    
    point = symbol_info.point
    pip_value = point * 10 if 'JPY' in symbol else point
    
    price = mt5.symbol_info_tick(symbol).ask if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
    
    if order_type == mt5.ORDER_TYPE_BUY:
        tp = price + (tp_pips * pip_value)
        sl = price - (sl_pips * pip_value)
    else:
        tp = price - (tp_pips * pip_value)
        sl = price + (sl_pips * pip_value)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "MACD+Volume Strategy",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.retcode} - {result.comment}")
        return None
    
    return result


# ==================== TRADING LOGIC ====================
def process_symbol(symbol, last_candle_time, show_logs=False):
    """Process trading logic for a symbol"""
    # Get latest data
    df = get_latest_data(symbol, TIMEFRAME, INDICATOR_BARS)
    if df is None:
        if show_logs:
            print(f"[{symbol}] ⚠️  Failed to get data")
        return last_candle_time
    
    # Check if we have a new candle
    current_candle_time = df.index[-1]
    if current_candle_time == last_candle_time:
        return last_candle_time  # No new candle yet
    
    # New candle detected
    if show_logs:
        print(f"\n[{symbol}] 🕐 New candle at {current_candle_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Calculate indicators
    df = calculate_indicators(df)
    
    # Check for signals
    signal = check_signal(df)
    
    # Get current positions
    positions = get_open_positions(symbol)
    
    # Check if we have open positions - monitor TP/SL hits
    if len(positions) > 0:
        for pos in positions:
            current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 0 else mt5.symbol_info_tick(symbol).ask
            pnl = pos.profit
            
            # Check if close to TP or SL
            if pos.type == 0:  # BUY position
                distance_to_tp = (pos.tp - current_price) / mt5.symbol_info(symbol).point
                distance_to_sl = (current_price - pos.sl) / mt5.symbol_info(symbol).point
            else:  # SELL position
                distance_to_tp = (current_price - pos.tp) / mt5.symbol_info(symbol).point
                distance_to_sl = (pos.sl - current_price) / mt5.symbol_info(symbol).point
            
            if show_logs:
                status = "🟢 WINNING" if pnl > 0 else "🔴 LOSING" if pnl < 0 else "⚪ BREAKEVEN"
                print(f"[{symbol}] 📊 Position #{pos.ticket} | {'BUY' if pos.type == 0 else 'SELL'} | "
                      f"P&L: ${pnl:.2f} | {status}")
    
    if signal and len(positions) == 0:
        # No open position, place new order
        order_type = mt5.ORDER_TYPE_BUY if signal == 'BUY' else mt5.ORDER_TYPE_SELL
        
        print(f"\n[{symbol}] 🎯 {signal} SIGNAL DETECTED!")
        print(f"[{symbol}] 📅 Time: {current_candle_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[{symbol}] 💹 Placing order...")
        
        result = place_order(symbol, order_type, LOT_SIZE, TP_PIPS, SL_PIPS)
        
        if result:
            print(f"[{symbol}] ✅ ENTRY SUCCESSFUL!")
            print(f"[{symbol}]    Ticket: #{result.order}")
            print(f"[{symbol}]    Type: {signal}")
            print(f"[{symbol}]    Entry Price: {result.price}")
            print(f"[{symbol}]    TP: {result.price + (TP_PIPS * (mt5.symbol_info(symbol).point * 10)) if signal == 'BUY' else result.price - (TP_PIPS * (mt5.symbol_info(symbol).point * 10))}")
            print(f"[{symbol}]    SL: {result.price - (SL_PIPS * (mt5.symbol_info(symbol).point * 10)) if signal == 'BUY' else result.price + (SL_PIPS * (mt5.symbol_info(symbol).point * 10))}")
            print(f"[{symbol}]    Volume: {result.volume} lot")
        else:
            print(f"[{symbol}] ❌ ORDER FAILED!")
    
    elif not signal and len(positions) == 0:
        # No signal and no position
        if show_logs:
            macd_col = f'MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
            signal_col = f'MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'
            last_bar = df.iloc[-2]
            
            macd_val = last_bar[macd_col]
            signal_val = last_bar[signal_col]
            ema_status = "Fast > Slow" if last_bar['ema_fast'] > last_bar['ema_slow'] else "Fast < Slow"
            volume_color = "🟢 Green" if last_bar['volume_green'] else "🔴 Red"
            
            print(f"[{symbol}] ⏸️  No signal - Calculating...")
            print(f"[{symbol}]    MACD: {macd_val:.5f} | Signal: {signal_val:.5f}")
            print(f"[{symbol}]    EMA: {ema_status} | Volume: {volume_color}")
    
    return current_candle_time


# ==================== MAIN TRADING LOOP ====================
def main():
    """Main trading loop"""
    print("="*60)
    print("🚀 MACD + VOLUME LIVE TRADING STRATEGY (M5)")
    print("="*60)
    print(f"MACD Settings: Fast={MACD_FAST}, Slow={MACD_SLOW}, Signal={MACD_SIGNAL}")
    print(f"TP: {TP_PIPS} pips | SL: {SL_PIPS} pips | RR: 1:{TP_PIPS/SL_PIPS}")
    print(f"Lot Size: {LOT_SIZE}")
    print("="*60)
    
    # Initialize MT5
    if not initialize_mt5():
        return
    
    # Validate and filter available symbols
    print("\n🔍 Validating symbols on broker...")
    available_symbols = []
    unavailable_symbols = []
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\r   Checking {i}/{len(SYMBOLS)}: {symbol}...", end='', flush=True)
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            # Try alternative formats
            found = False
            for suffix in [".a", "m", ".raw"]:
                alt_symbol = symbol + suffix
                if mt5.symbol_info(alt_symbol) is not None:
                    available_symbols.append(alt_symbol)
                    found = True
                    break
            
            if not found:
                unavailable_symbols.append(symbol)
        else:
            available_symbols.append(symbol)
            # Make sure it's visible
            if not symbol_info.visible:
                mt5.symbol_select(symbol, True)
    
    print("\r" + " " * 80)  # Clear the line
    print(f"\n✅ Available symbols: {len(available_symbols)}/{len(SYMBOLS)}")
    if len(available_symbols) > 0:
        print(f"   Trading: {', '.join(available_symbols[:8])}")
        if len(available_symbols) > 8:
            print(f"            {', '.join(available_symbols[8:16])}")
        if len(available_symbols) > 16:
            print(f"            {', '.join(available_symbols[16:])}")
    
    if unavailable_symbols:
        print(f"\n⚠️  Unavailable: {len(unavailable_symbols)} symbols")
        if len(unavailable_symbols) <= 10:
            print(f"   {', '.join(unavailable_symbols)}")
    
    if not available_symbols:
        print("\n❌ No valid symbols found. Please check your broker's symbol list.")
        print("   Tip: Check Market Watch in MT5 to see available symbol names.")
        mt5.shutdown()
        return
    
    # Use only available symbols
    SYMBOLS_TO_TRADE = available_symbols
    
    # Track last candle time for each symbol
    last_candle_times = {symbol: None for symbol in SYMBOLS_TO_TRADE}
    
    print("\n✅ Strategy is now LIVE! Monitoring market...")
    print("Press Ctrl+C to stop\n")
    
    try:
        iteration = 0
        while True:
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show detailed logs every iteration, summary every 5 iterations
            show_detailed_logs = True
            show_summary = (iteration % 5 == 1)
            
            if show_summary:
                account_info = mt5.account_info()
                if account_info:
                    print(f"\n{'='*70}")
                    print(f"💰 [{current_time}] ACCOUNT STATUS")
                    print(f"{'='*70}")
                    print(f"   Balance: ${account_info.balance:.2f}")
                    print(f"   Equity: ${account_info.equity:.2f}")
                    print(f"   Profit: ${account_info.profit:+.2f}")
                    print(f"   Margin: ${account_info.margin:.2f}")
                    print(f"   Free Margin: ${account_info.margin_free:.2f}")
                    
                    # Show open positions count
                    total_positions = 0
                    for symbol in SYMBOLS_TO_TRADE:
                        positions = get_open_positions(symbol)
                        total_positions += len(positions)
                    
                    print(f"   Open Positions: {total_positions}")
                    print(f"{'='*70}\n")
            
            # Process each symbol
            print(f"\n🔄 Scanning Market - {current_time}")
            print(f"{'─'*70}")
            
            for symbol in SYMBOLS_TO_TRADE:
                last_candle_times[symbol] = process_symbol(
                    symbol, 
                    last_candle_times[symbol],
                    show_logs=show_detailed_logs
                )
            
            print(f"{'─'*70}")
            print(f"✅ Scan complete. Next check in {CHECK_INTERVAL} seconds...\n")
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Strategy stopped by user")
        
        # Show final positions
        print("\n" + "="*70)
        print("📊 FINAL OPEN POSITIONS")
        print("="*70)
        
        total_positions = 0
        total_pnl = 0
        
        for symbol in SYMBOLS_TO_TRADE:
            positions = get_open_positions(symbol)
            if len(positions) > 0:
                for pos in positions:
                    total_positions += 1
                    total_pnl += pos.profit
                    print(f"[{symbol}] Ticket: #{pos.ticket} | "
                          f"{'BUY' if pos.type == 0 else 'SELL'} | "
                          f"Entry: {pos.price_open} | "
                          f"Current: {pos.price_current} | "
                          f"P&L: ${pos.profit:+.2f}")
        
        if total_positions == 0:
            print("   No open positions")
        else:
            print(f"{'─'*70}")
            print(f"Total: {total_positions} positions | Combined P&L: ${total_pnl:+.2f}")
        
        print("="*70)
        
        # Shutdown MT5
        mt5.shutdown()
        print("\n✅ MT5 Connection Closed. Goodbye!")


if __name__ == "__main__":
    main()