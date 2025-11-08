import os
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

ACCOUNT = {
    "login": 52575885,
    "password": "@q30SMKYhawwOa",
    "server": "ICMarketsSC-Demo"
}

START_DATE = '05/11/2025'
END_DATE = '07/11/2025'

def main():
    if not mt5.initialize():
        print("❌ MT5 initialize failed.")
        return
    if not mt5.login(**ACCOUNT):
        print("❌ Login failed.")
        mt5.shutdown()
        return
    print(f"✅ Connected: {mt5.account_info().login}")

    # Convert string dates to datetime objects
    start = datetime.strptime(START_DATE, "%d/%m/%Y")
    end = datetime.strptime(END_DATE, "%d/%m/%Y")

    # Lấy lịch sử trade
    history = mt5.history_deals_get(start, end)
    if history is None:
        print("⚠ No trade history found in this period.")
        mt5.shutdown()
        return

    # Chuyển sang DataFrame
    deals = []
    for deal in history:
        deals.append({
            "ticket": deal.ticket,
            "order": deal.order,
            "symbol": deal.symbol,
            "type": deal.type,
            "volume": deal.volume,
            "price": deal.price,
            "profit": deal.profit,
            "swap": deal.swap,
            "commission": deal.commission,
            "time": datetime.fromtimestamp(deal.time)
        })

    df = pd.DataFrame(deals)
    file_path = os.path.join(os.path.dirname(__file__), "trade_history.csv")
    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {len(df)} trades to {file_path}")

    mt5.shutdown()

if __name__ == "__main__":
    main()
