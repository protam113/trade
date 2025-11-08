# -*- coding: utf-8 -*-
"""
MACD Indicator Module
Moving Average Convergence Divergence
Optimized for M5 Scalping
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


def calculate_ema(series: pd.Series, length: int) -> pd.Series:
    """
    Tính Exponential Moving Average (EMA)
    
    Parameters:
    -----------
    series : pd.Series
        Chuỗi giá
    length : int
        Độ dài EMA
    
    Returns:
    --------
    pd.Series
        EMA của series
    """
    return series.ewm(span=length, adjust=False).mean()


def calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    talib: bool = False
) -> pd.DataFrame:
    """
    Tính toán MACD (Moving Average Convergence Divergence)
    
    Parameters:
    -----------
    close : pd.Series
        Chuỗi giá đóng cửa
    fast : int
        Fast EMA period. Default: 12 (standard) hoặc 6 (cho M5 scalping)
    slow : int
        Slow EMA period. Default: 26 (standard) hoặc 13 (cho M5 scalping)
    signal : int
        Signal line EMA period. Default: 9 (standard) hoặc 5 (cho M5 scalping)
    talib : bool
        Sử dụng TA-Lib nếu có. Default: False
    
    Returns:
    --------
    pd.DataFrame
        DataFrame chứa MACD, Signal, Histogram
    """
    if len(close) < slow + signal:
        return pd.DataFrame()
    
    # Thử dùng TA-Lib nếu có
    if talib:
        try:
            import talib
            macd_line, signal_line, histogram = talib.MACD(
                close.values,
                fastperiod=fast,
                slowperiod=slow,
                signalperiod=signal
            )
            result = pd.DataFrame({
                'MACD': macd_line,
                'Signal': signal_line,
                'Histogram': histogram
            }, index=close.index)
            return result
        except ImportError:
            pass  # Fallback về tính toán thủ công
    
    # Tính toán thủ công
    fast_ema = calculate_ema(close, fast)
    slow_ema = calculate_ema(close, slow)
    
    # MACD line = Fast EMA - Slow EMA
    macd_line = fast_ema - slow_ema
    
    # Signal line = EMA của MACD line
    signal_line = calculate_ema(macd_line, signal)
    
    # Histogram = MACD - Signal
    histogram = macd_line - signal_line
    
    result = pd.DataFrame({
        'MACD': macd_line,
        'Signal': signal_line,
        'Histogram': histogram
    }, index=close.index)
    
    return result


def get_macd_signals(df: pd.DataFrame, macd_df: pd.DataFrame) -> Dict:
    """
    Phân tích tín hiệu MACD
    
    Strategy:
    - BUY: MACD line vượt lên Signal line (Histogram > 0) và MACD > 0
    - SELL: MACD line vượt xuống Signal line (Histogram < 0) và MACD < 0
    - Mạnh hơn: Histogram tăng/giảm (động lượng)
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame chứa OHLCV
    macd_df : pd.DataFrame
        DataFrame chứa MACD, Signal, Histogram
    
    Returns:
    --------
    dict
        Dictionary chứa tín hiệu MACD
    """
    if macd_df.empty or len(macd_df) < 2:
        return {
            'signal': 'hold',
            'trend': 'neutral',
            'macd_cross': 'none',
            'histogram_trend': 'none',
            'strength': 0,
            'reason': ['Không đủ dữ liệu MACD']
        }
    
    # Lấy giá trị hiện tại (nến cuối cùng)
    current_macd = macd_df['MACD'].iloc[-1]
    current_signal = macd_df['Signal'].iloc[-1]
    current_histogram = macd_df['Histogram'].iloc[-1]
    
    # Lấy giá trị trước đó
    prev_macd = macd_df['MACD'].iloc[-2] if len(macd_df) > 1 else current_macd
    prev_signal = macd_df['Signal'].iloc[-2] if len(macd_df) > 1 else current_signal
    prev_histogram = macd_df['Histogram'].iloc[-2] if len(macd_df) > 1 else current_histogram
    
    # Phân tích tín hiệu
    signal = 'hold'
    trend = 'neutral'
    macd_cross = 'none'
    histogram_trend = 'none'
    strength = 0
    reasons = []
    
    # 1. Phát hiện MACD cross Signal line
    if prev_macd <= prev_signal and current_macd > current_signal:
        # MACD vượt lên Signal (Bullish crossover)
        macd_cross = 'bullish'
        strength += 3
        reasons.append("MACD vượt lên Signal line (Bullish crossover)")
    elif prev_macd >= prev_signal and current_macd < current_signal:
        # MACD vượt xuống Signal (Bearish crossover)
        macd_cross = 'bearish'
        strength += 3
        reasons.append("MACD vượt xuống Signal line (Bearish crossover)")
    
    # 2. Phân tích Histogram (động lượng)
    if current_histogram > 0:
        histogram_trend = 'bullish'
        if prev_histogram < current_histogram:
            # Histogram tăng (động lượng tăng)
            strength += 2
            reasons.append("Histogram tăng (động lượng bullish mạnh)")
        else:
            strength += 1
            reasons.append("Histogram > 0 (bullish)")
    elif current_histogram < 0:
        histogram_trend = 'bearish'
        if prev_histogram > current_histogram:
            # Histogram giảm (động lượng tăng)
            strength += 2
            reasons.append("Histogram giảm (động lượng bearish mạnh)")
        else:
            strength += 1
            reasons.append("Histogram < 0 (bearish)")
    
    # 3. Phân tích vị trí MACD line so với zero line
    if current_macd > 0:
        trend = 'bullish'
        strength += 1
        reasons.append("MACD > 0 (bullish trend)")
    elif current_macd < 0:
        trend = 'bearish'
        strength += 1
        reasons.append("MACD < 0 (bearish trend)")
    
    # 4. Kết hợp tín hiệu để quyết định
    bullish_score = 0
    bearish_score = 0
    
    if macd_cross == 'bullish':
        bullish_score += 3
    elif macd_cross == 'bearish':
        bearish_score += 3
    
    if histogram_trend == 'bullish':
        bullish_score += 2
    elif histogram_trend == 'bearish':
        bearish_score += 2
    
    if trend == 'bullish':
        bullish_score += 1
    elif trend == 'bearish':
        bearish_score += 1
    
    # Quyết định signal
    if bullish_score >= 4 and bullish_score > bearish_score:
        signal = 'buy'
    elif bearish_score >= 4 and bearish_score > bullish_score:
        signal = 'sell'
    
    if not reasons:
        reasons.append("Không có tín hiệu rõ ràng")
    
    return {
        'signal': signal,
        'trend': trend,
        'macd_cross': macd_cross,
        'histogram_trend': histogram_trend,
        'strength': min(strength / 6.0, 1.0),  # Normalize về 0-1
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'macd_value': current_macd,
        'signal_value': current_signal,
        'histogram_value': current_histogram,
        'reason': reasons
    }

