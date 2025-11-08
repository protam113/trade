# -*- coding: utf-8 -*-
"""
trailing.py
Multi-Timeframe Trailing Stop for Scalping/Short-term Trading - pandas_ta style
Trailing stop trên ETF với validation từ LTF và HTF để tránh cắt lệnh sớm.
"""

from pandas import DataFrame, Series
import pandas as pd
from typing import Optional, Dict, Any
import logging

# Setup logging
logger = logging.getLogger(__name__)


def trailing_stop(
    high: Series,
    low: Series, 
    close: Series,
    position_type: str,  
    entry_price: float,
    current_sl: float,
    
    # ETF - Main timeframe for trailing
    etf_high: Series = None,
    etf_low: Series = None,
    etf_close: Series = None,
    
    # LTF - Lower timeframe validation
    ltf_high: Series = None,
    ltf_low: Series = None,
    ltf_close: Series = None,
    
    # HTF - Higher timeframe validation
    htf_high: Series = None,
    htf_low: Series = None,
    htf_close: Series = None,
    
    # Trailing parameters
    enabled: bool = True,
    atr_length: int = 14,
    atr_multiplier: float = 2.0,
    trail_activation: float = 0.3,  # % profit to activate trailing (30 pips = 0.3%)
    trail_step: float = 0.1,  # % to trail (10 pips = 0.1%)
    
    # Trend validation
    ema_length: int = 20,
    adx_length: int = 14,
    adx_threshold: float = 20,
    min_volatility: float = None,
    
    # Options
    offset: int = 0,
    debug: bool = False,
    **kwargs: Dict[str, Any]
) -> DataFrame:
    """
    Multi-Timeframe Trailing Stop
    
    Parameters:
    -----------
    high, low, close : Series
        Price data (default timeframe)
    position_type : str
        "BUY" or "SELL"
    entry_price : float
        Entry price of position
    current_sl : float
        Current stop loss
    etf_*, ltf_*, htf_* : Series
        Price data for different timeframes
    enabled : bool
        Enable/disable trailing
    atr_length : int
        ATR period
    atr_multiplier : float
        ATR multiplier for trailing distance
    trail_activation : float
        Profit % to activate trailing (0.3 = 0.3%)
    trail_step : float
        Trailing step % (0.1 = 0.1%)
    ema_length : int
        EMA period for trend validation
    adx_length : int
        ADX period for trend strength
    adx_threshold : float
        Minimum ADX for trailing
    min_volatility : float
        Minimum ATR for trailing
    offset : int
        Offset for result
    debug : bool
        Enable debug logging
        
    Returns:
    --------
    DataFrame with columns:
        - TRAIL_PRICE: Current price
        - TRAIL_SL: New trailing stop
        - TRAIL_ACTIVE: Trailing is active
        - TRAIL_STATUS: Status message
        - TRAIL_PROFIT_PCT: Current profit %
    """
    
    if not enabled:
        logger.debug("Trailing stop disabled")
        return _create_inactive_result(close, current_sl, "Disabled")
    
    # Validate inputs
    if high is None or low is None or close is None:
        logger.warning("Missing price data")
        return _create_inactive_result(close, current_sl, "Missing Data")
    
    if len(high) < max(atr_length, ema_length, adx_length):
        logger.warning("Insufficient data for trailing calculation")
        return _create_inactive_result(close, current_sl, "Insufficient Data")
    
    # Use provided timeframe data or default to main data
    if etf_high is None:
        etf_high, etf_low, etf_close = high, low, close
    if ltf_high is None:
        ltf_high, ltf_low, ltf_close = high, low, close
    if htf_high is None:
        htf_high, htf_low, htf_close = high, low, close
    
    try:
        # Calculate ATR for ETF (main trailing timeframe)
        from ..volatility.atr import atr
        atr_series = atr(high=etf_high, low=etf_low, close=etf_close, length=atr_length)
        
        if atr_series is None or atr_series.empty:
            logger.warning("ATR calculation failed")
            return _create_inactive_result(close, current_sl, "ATR Failed")
        
        current_atr = atr_series.iloc[-1]
        current_price = etf_close.iloc[-1]
        
        if debug:
            logger.info(f"[TRAIL] Price: {current_price:.5f} | ATR: {current_atr:.5f} | Entry: {entry_price:.5f}")
        
        # Check profit activation
        profit_pct = _calculate_profit_pct(entry_price, current_price, position_type)
        
        if profit_pct < trail_activation:
            if debug:
                logger.debug(f"[TRAIL] Profit {profit_pct:.2f}% < activation {trail_activation:.2f}%")
            return _create_inactive_result(
                close, current_sl, 
                f"Wait Profit ({profit_pct:.2f}% < {trail_activation:.2f}%)",
                profit_pct
            )
        
        # Validate volatility
        if min_volatility is not None and current_atr < min_volatility:
            if debug:
                logger.debug(f"[TRAIL] ATR {current_atr:.5f} < min {min_volatility:.5f}")
            return _create_inactive_result(
                close, current_sl,
                f"Low Volatility (ATR={current_atr:.5f})",
                profit_pct
            )
        
        # Check LTF trend
        ltf_trend_ok = _check_trend_alignment(
            ltf_high, ltf_low, ltf_close,
            position_type, ema_length, adx_length, adx_threshold, debug, "LTF"
        )
        
        if not ltf_trend_ok:
            if debug:
                logger.info("[TRAIL] LTF trend weakening - holding SL")
            return _create_inactive_result(
                close, current_sl,
                "LTF Trend Weak",
                profit_pct
            )
        
        # Check HTF trend
        htf_trend_ok = _check_trend_alignment(
            htf_high, htf_low, htf_close,
            position_type, ema_length, adx_length, adx_threshold, debug, "HTF"
        )
        
        if not htf_trend_ok:
            if debug:
                logger.info("[TRAIL] HTF trend weakening - holding SL")
            return _create_inactive_result(
                close, current_sl,
                "HTF Trend Weak",
                profit_pct
            )
        
        # Calculate new trailing stop
        trail_distance = current_atr * atr_multiplier
        
        if position_type.upper() == "BUY":
            # For BUY: trail up with price, stop should be below
            new_sl = current_price - trail_distance
            
            # Only move SL up, never down
            if new_sl > current_sl:
                trailing_active = True
                status = f"Active UP (ATR×{atr_multiplier})"
            else:
                new_sl = current_sl
                trailing_active = False
                status = "Holding (no upside)"
                
        else:  # SELL
            # For SELL: trail down with price, stop should be above
            new_sl = current_price + trail_distance
            
            # Only move SL down, never up
            if new_sl < current_sl:
                trailing_active = True
                status = f"Active DOWN (ATR×{atr_multiplier})"
            else:
                new_sl = current_sl
                trailing_active = False
                status = "Holding (no downside)"
        
        if debug and trailing_active:
            logger.info(
                f"[TRAIL] ✅ {position_type} | "
                f"Price: {current_price:.5f} | "
                f"Old SL: {current_sl:.5f} → New SL: {new_sl:.5f} | "
                f"Distance: {trail_distance:.5f} | "
                f"Profit: {profit_pct:.2f}%"
            )
        
        # Build result DataFrame
        result = DataFrame({
            "TRAIL_PRICE": current_price,
            "TRAIL_SL": new_sl,
            "TRAIL_ACTIVE": trailing_active,
            "TRAIL_STATUS": status,
            "TRAIL_PROFIT_PCT": profit_pct,
            "TRAIL_ATR": current_atr,
            "TRAIL_DISTANCE": trail_distance
        }, index=[close.index[-1]])
        
        # Apply offset
        if offset != 0:
            result = result.shift(offset)
        
        # Apply fillna
        if "fillna" in kwargs:
            result.fillna(kwargs["fillna"], inplace=True)
        
        result.name = f"TRAIL_{position_type}"
        result.category = "trailing"
        
        return result
        
    except Exception as e:
        logger.error(f"[TRAIL] Error: {e}", exc_info=True)
        return _create_inactive_result(close, current_sl, f"Error: {str(e)}")


def _calculate_profit_pct(entry: float, current: float, position_type: str) -> float:
    """Calculate profit percentage"""
    if position_type.upper() == "BUY":
        return ((current - entry) / entry) * 100
    else:  # SELL
        return ((entry - current) / entry) * 100


def _check_trend_alignment(
    high: Series,
    low: Series,
    close: Series,
    position_type: str,
    ema_length: int,
    adx_length: int,
    adx_threshold: float,
    debug: bool,
    tf_label: str
) -> bool:
    """
    Check if trend is still aligned with position
    Returns True if trend supports trailing
    """
    try:
        # Calculate EMA
        from ..overlap.ema import ema
        ema_series = ema(close, length=ema_length)
        
        if ema_series is None or ema_series.empty:
            logger.warning(f"[{tf_label}] EMA calculation failed")
            return True  # Don't block on calc failure
        
        current_close = close.iloc[-1]
        current_ema = ema_series.iloc[-1]
        
        # Check price vs EMA
        if position_type.upper() == "BUY":
            price_aligned = current_close > current_ema
        else:  # SELL
            price_aligned = current_close < current_ema
        
        if not price_aligned:
            if debug:
                logger.debug(
                    f"[{tf_label}] Price not aligned with EMA | "
                    f"Price: {current_close:.5f} | EMA: {current_ema:.5f}"
                )
            return False
        
        # Calculate ADX for trend strength
        from ..trend.adx import adx
        adx_df = adx(high, low, close, length=adx_length)
        
        if adx_df is None or adx_df.empty:
            logger.warning(f"[{tf_label}] ADX calculation failed")
            return True  # Don't block on calc failure
        
        adx_col = f'ADX_{adx_length}'
        if adx_col not in adx_df.columns:
            logger.warning(f"[{tf_label}] ADX column not found")
            return True
        
        current_adx = adx_df[adx_col].iloc[-1]
        
        if pd.isna(current_adx):
            logger.warning(f"[{tf_label}] ADX is NaN")
            return True
        
        adx_ok = current_adx >= adx_threshold
        
        if debug:
            logger.debug(
                f"[{tf_label}] Trend Check | "
                f"Price: {current_close:.5f} | EMA: {current_ema:.5f} | "
                f"ADX: {current_adx:.2f} (threshold: {adx_threshold}) | "
                f"Aligned: {price_aligned} | Strong: {adx_ok}"
            )
        
        return price_aligned and adx_ok
        
    except Exception as e:
        logger.error(f"[{tf_label}] Trend check error: {e}")
        return True  # Don't block on error


def _create_inactive_result(
    close: Series,
    current_sl: float,
    status: str,
    profit_pct: float = 0.0
) -> DataFrame:
    """Create inactive trailing result"""
    current_price = close.iloc[-1] if not close.empty else 0.0
    
    result = DataFrame({
        "TRAIL_PRICE": current_price,
        "TRAIL_SL": current_sl,
        "TRAIL_ACTIVE": False,
        "TRAIL_STATUS": status,
        "TRAIL_PROFIT_PCT": profit_pct,
        "TRAIL_ATR": 0.0,
        "TRAIL_DISTANCE": 0.0
    }, index=[close.index[-1]] if not close.empty else [0])
    
    result.name = "TRAIL_INACTIVE"
    result.category = "trailing"
    
    return result


# ============================================
# Batch Trailing for Multiple Positions
# ============================================

def batch_trailing_stop(
    positions: list,
    market_data: Dict[str, Dict[str, Series]],
    config: Dict[str, Any],
    debug: bool = False
) -> Dict[str, DataFrame]:
    """
    Calculate trailing stops for multiple positions
    
    Parameters:
    -----------
    positions : list
        List of position dicts with keys:
        - symbol: str
        - position_type: "BUY" or "SELL"
        - entry_price: float
        - current_sl: float
        - ticket: int (optional)
    
    market_data : dict
        Nested dict: {symbol: {timeframe: {"high": Series, "low": Series, "close": Series}}}
        Example: {"EURUSD": {"M1": {...}, "M5": {...}, "M15": {...}}}
    
    config : dict
        Trailing config with keys:
        - enabled: bool
        - etf, ltf, htf: str (timeframes)
        - atr_length, atr_multiplier, etc.
    
    Returns:
    --------
    Dict[symbol, DataFrame]: Trailing results per symbol
    """
    results = {}
    
    if not config.get("enabled", False):
        logger.info("Batch trailing disabled")
        return results
    
    etf = config.get("etf", "M1")
    ltf = config.get("ltf", "M5")
    htf = config.get("htf", "M15")
    
    for pos in positions:
        symbol = pos["symbol"]
        
        try:
            if symbol not in market_data:
                logger.warning(f"No market data for {symbol}")
                continue
            
            symbol_data = market_data[symbol]
            
            # Get data for each timeframe
            etf_data = symbol_data.get(etf, {})
            ltf_data = symbol_data.get(ltf, {})
            htf_data = symbol_data.get(htf, {})
            
            if not etf_data:
                logger.warning(f"No {etf} data for {symbol}")
                continue
            
            # Calculate trailing stop
            result = trailing_stop(
                high=etf_data.get("high"),
                low=etf_data.get("low"),
                close=etf_data.get("close"),
                position_type=pos["position_type"],
                entry_price=pos["entry_price"],
                current_sl=pos["current_sl"],
                
                etf_high=etf_data.get("high"),
                etf_low=etf_data.get("low"),
                etf_close=etf_data.get("close"),
                
                ltf_high=ltf_data.get("high"),
                ltf_low=ltf_data.get("low"),
                ltf_close=ltf_data.get("close"),
                
                htf_high=htf_data.get("high"),
                htf_low=htf_data.get("low"),
                htf_close=htf_data.get("close"),
                
                enabled=config.get("enabled", True),
                atr_length=config.get("atr_length", 14),
                atr_multiplier=config.get("atr_multiplier", 2.0),
                trail_activation=config.get("trail_activation", 0.3),
                trail_step=config.get("trail_step", 0.1),
                ema_length=config.get("ema_length", 20),
                adx_length=config.get("adx_length", 14),
                adx_threshold=config.get("adx_threshold", 20),
                min_volatility=config.get("min_volatility"),
                debug=debug
            )
            
            results[symbol] = result
            
            if debug:
                status = result["TRAIL_STATUS"].iloc[0]
                active = result["TRAIL_ACTIVE"].iloc[0]
                new_sl = result["TRAIL_SL"].iloc[0]
                logger.info(
                    f"[BATCH] {symbol} | Active: {active} | "
                    f"SL: {pos['current_sl']:.5f} → {new_sl:.5f} | "
                    f"Status: {status}"
                )
                
        except Exception as e:
            logger.error(f"[BATCH] Error processing {symbol}: {e}", exc_info=True)
    
    return results