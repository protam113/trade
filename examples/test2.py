import os
import sys

# --- Setup path ---
ROOT = os.path.join(os.path.dirname(__file__), "..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)


import inspect
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from aiomql.contrib.strategies import MACD_Strategy

START_DATE = '05/11/2025'
END_DATE = '07/11/2025'


# ============================================================
# =============== EXPORT DỮ LIỆU TỪ MT5 =======================
# ============================================================
def export_mt5_data(symbols, timeframe, days_back=365, filename='mt5_data.csv'):
    """Export dữ liệu OHLCV từ MT5 cho nhiều symbols"""
    if not mt5.initialize():
        print("❌ Lỗi khởi tạo MT5")
        return None
    
    all_data = []
    utc_to = datetime.now()
    utc_from = utc_to - timedelta(days=days_back)
    
    for symbol in symbols:
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['symbol'] = symbol
            all_data.append(df)
            print(f"✅ Exported {symbol}: {len(df)} bars")
        else:
            print(f"⚠️ Không lấy được data cho {symbol}")
    
    mt5.shutdown()
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df.to_csv(filename, index=False)
        print(f"\n✅ Đã lưu {len(combined_df)} bars vào {filename}")
        return combined_df
    return None


# ============================================================
# =============== EXPORT LỊCH SỬ GIAO DỊCH ===================
# ============================================================
def export_trade_history(start_date, end_date, filename='trade_history.csv'):
    """Export lịch sử giao dịch từ MT5 trong khoảng thời gian cụ thể"""
    if not mt5.initialize():
        print("❌ Lỗi khởi tạo MT5")
        return None

    # parse date theo định dạng dd/mm/yyyy
    from_date = datetime.strptime(start_date, "%d/%m/%Y")
    to_date = datetime.strptime(end_date, "%d/%m/%Y")

    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None or len(deals) == 0:
        print("⚠️ Không có lịch sử giao dịch trong khoảng thời gian này")
        mt5.shutdown()
        return None
    
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.to_csv(filename, index=False)
    
    mt5.shutdown()
    print(f"✅ Đã export {len(df)} deals vào {filename}")
    return df

# ============================================================
# =============== SUMMARY CHIẾN LƯỢC ==========================
# ============================================================
    
def create_strategy_summary(strategy_source, save_to_file=True):
    """
    Có thể đọc từ class (như MACD_Strategy) hoặc từ file .py
    """
    summary = {}

    if inspect.isclass(strategy_source):
        code = inspect.getsource(strategy_source)
        summary = {
            'type': 'class',
            'name': strategy_source.__name__,
            'code_length': len(code),
            'code_preview': code[:1000],
            'full_code': code
        }

    elif isinstance(strategy_source, str):
        if not os.path.exists(strategy_source):
            print(f"⚠️ File không tồn tại: {strategy_source}")
            return None
        with open(strategy_source, 'r', encoding='utf-8') as f:
            code = f.read()
        summary = {
            'type': 'file',
            'path': strategy_source,
            'code_length': len(code),
            'code_preview': code[:1000],
            'full_code': code
        }

    else:
        print("❌ Input không hợp lệ (phải là class hoặc file path)")
        return None

    # ✅ Ghi file summary
    if save_to_file:
        os.makedirs("summaries", exist_ok=True)
        name = summary.get('name') or os.path.basename(summary.get('path', 'unknown')).replace('.py', '')
        file_path = os.path.join("summaries", f"{name}_summary.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Chiến lược: {name}\n")
            f.write(f"Loại: {summary['type']}\n")
            f.write(f"Độ dài code: {summary['code_length']} ký tự\n")
            f.write("\n--- Preview ---\n")
            f.write(summary['code_preview'])
        print(f"✅ Đã lưu summary vào {file_path}")

    return summary



# ============================================================
# =================== MAIN EXECUTION =========================
# ============================================================
if __name__ == "__main__":
    # ✅ Lưu ý: MT5 không nhận symbol có dấu "/"
    symbols = [
        "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
        "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY",
        "EURNZD", "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF",
        "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF",
        "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"
    ]
    
    # Export dữ liệu giá
    mt5_data = export_mt5_data(
        symbols=symbols, 
        timeframe=mt5.TIMEFRAME_H1,
        days_back=365,
        filename='mt5_all_symbols.csv'
    )
    
    # Export lịch sử giao dịch
    trade_history = export_trade_history(START_DATE, END_DATE, filename='my_trades.csv')
    
    # Tạo summary chiến lược (nhận class)
    strategy_info = create_strategy_summary(MACD_Strategy)
    
    print("\n=== ✅ Hoàn tất! Các file bạn có thể upload: ===")
    print("1️⃣ mt5_all_symbols.csv - Dữ liệu giá")
    print("2️⃣ my_trades.csv - Lịch sử giao dịch")
    print("3️⃣ MACD_Strategy (summary tạo từ class)")
