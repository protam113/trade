import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))

import MetaTrader5 as mt5
import time

# --- Initialize MT5 ---
if not mt5.initialize(
    path='C:\\Program Files\\MetaTrader 5\\terminal64.exe',
    login=52575885,
    password='@q30SMKYhawwOa',
    server='ICMarketsSC-Demo'
):
    print("MT5 initialization failed")
    mt5.shutdown()
    exit()

# --- Check account info ---
info = mt5.account_info()
if info is None:
    print("Account not logged in")
    mt5.shutdown()
    exit()
else:
    print(f"Logged in: {info.login}, trade_mode: {info.trade_mode}")

# --- Select symbol ---
symbol = "EURUSD"
if not mt5.symbol_select(symbol, True):
    print(f"Cannot select {symbol}")
    mt5.shutdown()
    exit()

# Wait a bit for data
time.sleep(1)

# --- Get symbol info ---
symbol_info = mt5.symbol_info(symbol)
if symbol_info is None:
    print(f"Cannot get symbol info for {symbol}")
    mt5.shutdown()
    exit()

print(f"Symbol: {symbol_info.name}")
print(f"Filling modes: {symbol_info.filling_mode}")

# --- Determine filling type ---
filling_type = None
if symbol_info.filling_mode & 1:  # FOK
    filling_type = mt5.ORDER_FILLING_FOK
    print("Using FOK filling")
elif symbol_info.filling_mode & 2:  # IOC
    filling_type = mt5.ORDER_FILLING_IOC
    print("Using IOC filling")
elif symbol_info.filling_mode & 4:  # RETURN
    filling_type = mt5.ORDER_FILLING_RETURN
    print("Using RETURN filling")
else:
    print("No valid filling mode found")
    mt5.shutdown()
    exit()

# --- Realtime tick for 10 seconds ---
print(f"\n--- Realtime price feed for {symbol} (10s) ---")
start_time = time.time()

while time.time() - start_time < 10:
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        print(f"[{time.strftime('%H:%M:%S')}] Ask: {tick.ask:.5f} | Bid: {tick.bid:.5f}")
    else:
        print("No tick data...")
    time.sleep(0.1)

# --- Shutdown ---
mt5.shutdown()
print("MT5 connection closed.")
