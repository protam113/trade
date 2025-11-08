"""
Cấu hình cho MACD Trading Bot
"""
import os
import sys
from dotenv import load_dotenv

# Thêm path của project root để import exness_connector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Cấu hình Exchange
EXCHANGE_NAME = "exness"  # "exness", "binance", "bybit", "okx", etc.

# Cấu hình cho CCXT exchanges (Binance, Bybit, etc.)
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_API_SECRET = os.getenv("EXCHANGE_API_SECRET", "")

# Cấu hình cho Exness (MetaTrader 5)
MT5_ACCOUNT = int(os.getenv("MT5_ACCOUNT", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "Exness-Demo")

# Cấu hình Trading
SYMBOLS = ["AUD/CAD", "AUD/CHF", "AUD/JPY", "AUD/NZD", "AUD/USD", "EUR/AUD", "EUR/CAD", "EUR/CHF", "EUR/GBP", "EUR/JPY", "EUR/NZD", "EUR/USD", "GBP/AUD", "GBP/CAD", "GBP/CHF", "GBP/JPY", "GBP/NZD", "GBP/USD", "NZD/CAD", "NZD/CHF", "NZD/JPY", "NZD/USD", "USD/CAD", "USD/CHF", "USD/JPY"]  # Các cặp tiền muốn trade

# Cấu hình Multi-Timeframe Analysis cho MACD
TIMEFRAMES = ["1h", "15m", "5m", "1m"]  # Từ lớn đến nhỏ

# Trọng số cho mỗi timeframe (tổng = 100)
TIMEFRAME_WEIGHTS = {
    "1h": 35,   # Timeframe lớn nhất - xác định xu hướng chính
    "15m": 30,  # Xu hướng trung hạn
    "5m": 20,   # Tìm điểm vào
    "1m": 15    # Vào lệnh chính xác
}

# Timeframe chính để vào lệnh
PRIMARY_TIMEFRAME = "1m"

# Cấu hình MACD
# Standard MACD: fast=12, slow=26, signal=9
# Optimized for M5 Scalping: fast=6, slow=13, signal=5
MACD_FAST = 12   # Fast EMA period
MACD_SLOW = 26   # Slow EMA period
MACD_SIGNAL = 9  # Signal line EMA period

# Nếu muốn dùng tham số tối ưu cho M5 scalping, uncomment:
# MACD_FAST = 6
# MACD_SLOW = 13
# MACD_SIGNAL = 5

# Sử dụng TA-Lib nếu có
USE_TALIB = True  # True nếu đã cài TA-Lib, False để dùng tính toán thủ công

# Cấu hình Risk Management
MAX_POSITION_SIZE = 0.1  # Khối lượng tối đa mỗi lệnh (lot cho Forex)

# Cấu hình Stop Loss và Take Profit (cho Forex)
STOP_LOSS_PIPS = 20.0   # Stop loss 20 pip
TAKE_PROFIT_PIPS = 40.0  # Take profit 40 pip

# Cấu hình cho Forex (Exness)
LOT_SIZE = 0.1  # Kích thước lot mặc định

# Cấu hình kết nối
USE_SANDBOX = True  # True nếu dùng testnet, False nếu trade thật

# Cấu hình Signal Threshold
MIN_CONFIDENCE = 0.5  # Độ tin cậy tối thiểu để vào lệnh (0-1)
MIN_BULLISH_SCORE = 4  # Điểm bullish tối thiểu để vào lệnh BUY
MIN_BEARISH_SCORE = 4  # Điểm bearish tối thiểu để vào lệnh SELL

