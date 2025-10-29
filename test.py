import MetaTrader5 as mt5
import time

# Initialize và login
if not mt5.initialize(path='C:\\Program Files\\MetaTrader 5\\terminal64.exe',
                      login=98171894,
                      password='3kP!YmVv',
                      server='MetaQuotes-Demo'):
    print("MT5 initialization failed")
    mt5.shutdown()
    exit()

account_info = mt5.account_info()
if account_info is None:
    print("Login failed")
    mt5.shutdown()
    exit()
print(f"Logged in: {account_info.login}, balance: {account_info.balance}")

symbol = "EURUSD"
if not mt5.symbol_select(symbol, True):
    print(f"Cannot select {symbol}")
    mt5.shutdown()
    exit()

# Đợi 1 giây để MT5 load symbol
time.sleep(1)

tick = mt5.symbol_info_tick(symbol)
if tick is None or tick.ask == 0:
    print("Invalid tick")
    mt5.shutdown()
    exit()

# --- Mở lệnh Buy 0.01 lot ---
lot = 0.01
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot,
    "type": mt5.ORDER_TYPE_BUY,
    "price": tick.ask,
    "deviation": 10,
    "magic": 123456,
    "comment": "Test Buy",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

result = mt5.order_send(request)
if result.retcode != mt5.TRADE_RETCODE_DONE:
    print(f"Order failed, retcode={result.retcode}")
    mt5.shutdown()
    exit()
print(f"Order executed, ticket: {result.order}")

# --- Đóng lệnh sau 3 giây ---
time.sleep(3)
ticket = result.order
close_request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot,
    "type": mt5.ORDER_TYPE_SELL,
    "position": ticket,
    "price": mt5.symbol_info_tick(symbol).bid,
    "deviation": 10,
    "magic": 123456,
    "comment": "Close Buy",
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}

close_result = mt5.order_send(close_request)
if close_result.retcode != mt5.TRADE_RETCODE_DONE:
    print(f"Close order failed, retcode={close_result.retcode}")
else:
    print(f"Order closed, ticket: {ticket}")

mt5.shutdown()
