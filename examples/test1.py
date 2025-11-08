# Thêm vào đầu test1.py
import os
print("Current dir:", os.getcwd())
print("CSV exists:", os.path.exists("symbols_list.csv"))

import MetaTrader5 as mt5
print("MT5 init:", mt5.initialize())
print("Account:", mt5.account_info().login if mt5.account_info() else None)

# Kiểm tra 1 symbol
sym = "EURUSD"
print(f"{sym} info:", mt5.symbol_info(sym))
print(f"{sym} selected:", mt5.symbol_select(sym, True))

# load_forex_from_csv.py
import pandas as pd
import logging

def load_forex_pairs_from_csv(csv_path: str = "symbols_list.csv") -> list:
    """
    Đọc file CSV → Lấy TẤT CẢ forex pair có thể trade
    Điều kiện:
        - is_visible = True
        - trade_mode = 4 (full trade)
        - symbol có 6 ký tự: XXXYYY (ví dụ: EURUSD)
    """
    if not mt5.initialize():
        raise RuntimeError("MT5 not initialized")

    try:
        df = pd.read_csv(csv_path)
        logging.info(f"Loaded {len(df)} symbols from CSV")
    except Exception as e:
        raise FileNotFoundError(f"Cannot read CSV: {e}")

    forex_pairs = []
    for _, row in df.iterrows():
        symbol = row['symbol'].strip()
        visible = str(row['is_visible']).lower() == 'true'
        trade_mode = int(row['trade_mode'])

        # Chỉ lấy forex: 6 ký tự, không chứa XAU/XAG/US30...
        if (len(symbol) == 6 and 
            visible and 
            trade_mode == 4 and
            not any(x in symbol for x in ["XAU", "XAG", "US30", "US500", "USTEC", "DE40", "JP225", "UK100", "AUS200", "BTC", "ETH", "DXY"])):
            
            # Kiểm tra trong MT5
            if mt5.symbol_select(symbol, True):
                info = mt5.symbol_info(symbol)
                if info and info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                    forex_pairs.append(symbol)
                    print(f"Loaded: {symbol}")
                else:
                    print(f"Skipped (disabled): {symbol}")
            else:
                print(f"Skipped (not in MT5): {symbol}")

    logging.info(f"Total forex pairs loaded: {len(forex_pairs)}")
    return forex_pairs