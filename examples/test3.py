from datetime import datetime
import MetaTrader5 as mt5

SYMBOL = "USDJPY"

if not mt5.initialize():
    print("LỖI: Không kết nối MT5!")
    exit()

if not mt5.symbol_select(SYMBOL, True):
    print(f"LỖI: Không chọn được {SYMBOL}")
    mt5.shutdown()
    exit()

# === LẤY GIỜ SERVER ===
tick = mt5.symbol_info_tick(SYMBOL)
if not tick:
    print("LỖI: Không lấy được tick!")
    mt5.shutdown()
    exit()

# DÙNG utcfromtimestamp() để KHÔNG chuyển múi giờ
server_time = datetime.utcfromtimestamp(tick.time)

print("="*60)
print("        GIỜ SERVER (GIỐNG NHƯ TRÊN MT5)")
print("="*60)
print(f"Giờ hiển thị trên MT5: {server_time.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

mt5.shutdown()
