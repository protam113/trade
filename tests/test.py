import MetaTrader5 as mt5
from datetime import datetime
import pytz

# --- Kết nối tới MT5 ---
if not mt5.initialize(path='C:\\Program Files\\MetaTrader 5\\terminal64.exe',
                      login=52575885,
                      password='@q30SMKYhawwOa',
                      server='ICMarketsSC-Demo'):
    print("MT5 initialization failed")
    mt5.shutdown()
    exit()

account_info = mt5.account_info()
if account_info is None:
    print("Login failed")
    mt5.shutdown()
    exit()
print(f"✅ Logged in: {account_info.login}, balance: {account_info.balance}")

# --- Cấu hình timezone và symbol ---
timezone = pytz.timezone("Etc/UTC")
symbol = "EURUSD"

if not mt5.symbol_select(symbol, True):
    print(f"Cannot select {symbol}")
    mt5.shutdown()
    exit()

# --- Thời gian lấy dữ liệu ---
start = datetime(2025, 10, 20, tzinfo=timezone)
end = datetime(2025, 10, 22, tzinfo=timezone)

# h4 d1

# --- Lấy dữ liệu nến H1 ---
rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, start, end)

if rates is None or len(rates) == 0:
    print("❌ Không có dữ liệu trong khoảng thời gian này")
    mt5.shutdown()
    exit()

# --- In log dữ liệu ---
print(f"📊 Lấy được {len(rates)} cây nến H1 cho {symbol} từ {start} đến {end}:\n")
for r in rates:
    time_str = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{time_str} | O:{r['open']:.5f} H:{r['high']:.5f} L:{r['low']:.5f} C:{r['close']:.5f} V:{r['tick_volume']}")

mt5.shutdown()
