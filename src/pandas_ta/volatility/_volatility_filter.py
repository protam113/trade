# -*- coding: utf-8 -*-
"""
_volatility_filter.py
Scalper's Volatility Filter [QuantraSystems] - pandas_ta style
Dùng ATR để lọc biến động, hỗ trợ entry + TP/SL động cho scalping.
"""

from pandas import DataFrame, Series
import pandas as pd
from pandas_ta._typing import DictLike, Int, IntFloat
from pandas_ta.utils._validate import (
    v_series, v_pos_default, v_float, v_offset
)

from ..utils._math import zero
from ..utils._signals import above_value
from .atr import atr
from ..trend.adx import adx


def volatility_filter(
    high: Series, low: Series, close: Series,
    length: Int = 14,
    multiplier: IntFloat = 1.5,
    min_volatility: IntFloat = None, 
    tp_factor: IntFloat = 1.5,
    sl_factor: IntFloat = 1.0,
    adx_filter: bool = True,          
    adx_threshold: IntFloat = 20,
    offset: Int = None,
    **kwargs: DictLike
    
) -> DataFrame:
    """
    Tính Scalper's Volatility Filter:
        - vol_filter = ATR * multiplier
        - vol_entry = vol_filter > min_volatility
        - TP/SL = vol_filter * factor
        - Tùy chọn ADX filter để lọc trend yếu
    """
    # Validate series
    high = v_series(high)
    low = v_series(low)
    close = v_series(close)
    if high is None or low is None or close is None:
        return None

    # Validate data length
    if len(high) < length or len(low) < length or len(close) < length:
        return None

    length = v_pos_default(length, 14)
    multiplier = v_float(multiplier, 1.5)
    tp_factor = v_float(tp_factor, 1.5)
    sl_factor = v_float(sl_factor, 1.0)
    offset = v_offset(offset)

    # Tính ATR
    try:
        atr_series = atr(high=high, low=low, close=close, length=length)
        if atr_series is None or atr_series.empty:
            return None
    except Exception as e:
        print(f"[!] ATR calculation failed: {e}")
        return None

    # Tính vol_filter
    vol_filter = atr_series * multiplier

    # Tính min_volatility tự động nếu không truyền
    if min_volatility is None:
        min_volatility_series = 0.5 * atr_series.rolling(length, min_periods=1).mean()
    else:
        min_volatility_series = pd.Series([v_float(min_volatility, 0.0)] * len(vol_filter), index=vol_filter.index)

    # Entry flag - Sử dụng comparison trực tiếp thay vì above_value
    try:
        # Đảm bảo cả hai đều là Series và có cùng index
        vol_filter_clean = vol_filter.fillna(0)
        min_vol_clean = min_volatility_series.fillna(0)
        
        # So sánh trực tiếp
        vol_entry = (vol_filter_clean > min_vol_clean).astype(bool)
        
    except Exception as e:
        print(f"[!] Volatility comparison failed: {e}")
        # Fallback: tạo Series False
        vol_entry = pd.Series([False] * len(vol_filter), index=vol_filter.index)

    # ADX trend filter
    if adx_filter:
        try:
            adx_df = adx(high, low, close, length=length)
            if adx_df is not None and not adx_df.empty and f'ADX_{length}' in adx_df.columns:
                adx_col = f'ADX_{length}'
                trend_flag = adx_df[adx_col].fillna(0) > adx_threshold
                vol_entry = vol_entry & trend_flag
            else:
                # Nếu ADX fail, bỏ qua filter này
                print(f"[!] ADX calculation failed or empty, skipping ADX filter")
        except Exception as e:
            print(f"[!] ADX filter error: {e}, skipping ADX filter")

    # TP/SL
    vol_tp = vol_filter * tp_factor if tp_factor is not None else None
    vol_sl = vol_filter * sl_factor if sl_factor is not None else None

    # Build DataFrame
    data = {"VOLF": vol_filter, "VOLF_ENTRY": vol_entry}
    if vol_tp is not None:
        data["VOLF_TP"] = vol_tp
    if vol_sl is not None:
        data["VOLF_SL"] = vol_sl

    df = DataFrame(data, index=high.index)

    if offset != 0:
        df = df.shift(offset)

    if "fillna" in kwargs:
        df.fillna(kwargs["fillna"], inplace=True)
    else:
        # Default fillna để tránh NaN issues - using modern pandas syntax
        df.ffill(inplace=True)  # Forward fill
        df.fillna(0, inplace=True)  # Fill remaining NaN with 0

    df.name = f"VOLF_{length}_{multiplier}"
    df.category = "volatility"

    return df