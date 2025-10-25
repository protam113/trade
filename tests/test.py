import pandas as pd
import MetaTrader5 as mt5

creds = {
    'path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
    'login': 98171894,
    'password': '3kP!YmVv',
    'server': 'MetaQuotes-Demo',
    'timeout': 60000,
    'portable': False
}

if mt5.initialize(
        path=creds['path'],
        login=creds['login'],
        password=creds['password'],
        server=creds['server'],
        timeout=creds['timeout'],
        portable=creds['portable']
):
    print("MT5 initialized successfully")
else:
    print("MT5 initialization failed")
    mt5.shutdown()
    exit()

account_info = mt5.account_info()
if account_info is not None:
    print("Logged in:", account_info.login)
else:
    print("Failed to connect")

# Lấy và in giá hiện tại của BTCUSD
symbol = "EURUSD"
tick = mt5.symbol_info_tick(symbol)
if tick is not None:
    print(f"Giá Bid của EURUSD: {tick.bid}")
    print(f"Giá Ask của EURUSD: {tick.ask}")
else:
    print(f"Không thể lấy giá của {symbol}. Vui lòng kiểm tra xem symbol có sẵn không.")