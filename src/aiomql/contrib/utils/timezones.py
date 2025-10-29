# utils/timezones.py
from datetime import time
from zoneinfo import ZoneInfo
import pandas as pd

# ===================================================================
# CẤU HÌNH PHIÊN GIAO DỊCH - THEO MÙA (DST tự động)
# ===================================================================
TIMEZONES = {
    "SYD": {  # Sydney
        "tz": ZoneInfo("Australia/Sydney"),
        "open": time(22, 0),   # 22:00 GMT (mùa đông)
        "close": time(7, 0),   # 7:00 GMT
        "name": "Sydney Session"
    },
    "TOK": {  # Tokyo
        "tz": ZoneInfo("Asia/Tokyo"),
        "open": time(0, 0),
        "close": time(9, 0),
        "name": "Tokyo Session"
    },
    "LON": {  # London
        "tz": ZoneInfo("Europe/London"),
        "open": time(8, 0),
        "close": time(17, 0),
        "name": "London Session"
    },
    "NYC": {  # New York
        "tz": ZoneInfo("America/New_York"),
        "open": time(9, 30),
        "close": time(16, 0),
        "name": "New York Session"
    }
}

# ===================================================================
# HÀM CHUNG: LẤY HIGH/LOW CỦA 1 PHIÊN
# ===================================================================
def is_in_session(ts: pd.Timestamp, session: dict) -> bool:
    """Kiểm tra 1 timestamp có nằm trong phiên không (DST tự động)"""
    local_time = ts.tz_convert(session["tz"]).time()
    start = session["open"]
    end = session["close"]
    if start <= end:
        return start <= local_time <= end
    else:
        return local_time >= start or local_time <= end

def get_session_range(df: pd.DataFrame, session_name: str) -> dict:
    """
    Trả về High/Low của phiên gần nhất đã đóng cửa
    
    Args:
        df: DataFrame có index là datetime (UTC hoặc có tz)
        session_name: "NYC", "LON", "TOK", "SYD"
    
    Returns:
        dict: high, low, date, range, count hoặc None
    """
    if session_name not in TIMEZONES:
        raise ValueError(f"Session {session_name} not found. Available: {list(TIMEZONES.keys())}")
    
    session = TIMEZONES[session_name]
    df = df.copy()
    
    # Chuẩn hóa về UTC nếu chưa có
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    
    # Lọc nến trong phiên
    in_session = df.index.to_series().apply(lambda x: is_in_session(x, session))
    session_df = df[in_session]
    
    if session_df.empty:
        return None
    
    # Lấy ngày phiên gần nhất (theo giờ local)
    last_local_date = session_df.index[-1].tz_convert(session["tz"]).date()
    day_data = session_df[session_df.index.tz_convert(session["tz"]).date == last_local_date]
    
    # Kiểm tra phiên đã đóng chưa (ít nhất 10 nến M5 → ~50 phút)
    if len(day_data) < 10:
        return None  # Chưa đóng cửa
    
    high = day_data["high"].max()
    low = day_data["low"].min()
    
    return {
        "session": session["name"],
        "date_local": last_local_date,
        "high": float(high),
        "low": float(low),
        "range": float(high - low),
        "candles": len(day_data),
        "timezone": str(session["tz"])
    }