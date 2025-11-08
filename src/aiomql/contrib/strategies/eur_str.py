import asyncio
from logging import getLogger
import pandas_ta as ta
import pandas as pd
import numpy as np

from ...lib.strategy import Strategy
from ..symbols import ForexSymbol
from ..utils import Tracker
from ...core.constants import TimeFrame, OrderType
from ..traders.scalp_trader import ScalpTrader
from noti_bot.tele.tele_bot import bot_tele

# Import logging helpers
try:
    from ..utils.logging_config import log_signal, log_trade_execution
    LOGGING_HELPERS_AVAILABLE = True
except ImportError:
    LOGGING_HELPERS_AVAILABLE = False

logger = getLogger(__name__)


class EUR_Strategy(Strategy):
    """EUR Scalping Strategy - Optimized for M1 entries with improved edge case handling."""

    etf: TimeFrame
    ltf: TimeFrame
    htf: TimeFrame
    ctf: TimeFrame
    
    ecc: int
    lcc: int
    hcc: int
    ccc: int
    
    fast_macd: int
    slow_macd: int
    signal_macd: int
    lot_size: float
    tracker: Tracker
    interval: int
    vol_multiplier: float
    vol_tp_factor: float
    vol_sl_factor: float
    adx_threshold: float
    use_volatility_filter: bool
    use_trailing: bool
    max_open_signals: int
    atr_length: int
    
    # New: Emergency exit parameters
    max_drawdown_pct: float
    emergency_exit_enabled: bool

    parameters = {}

    def __init__(self, *, symbol: ForexSymbol, config: dict, params: dict = None, sessions=None, name="EUR_Scalping_Strategy"):
        """Initialize optimized scalping strategy"""
        strategy_config = config.get("strategy", {})
        macd_config = strategy_config.get("macd", {})
        timeframes = strategy_config.get("timeframes", {})
        candles = strategy_config.get("candles", {})
        risk = strategy_config.get("risk_management", {})
        vol_filter = strategy_config.get("volatility_filter", {})
        execution = strategy_config.get("execution", {})
        trailing_config = strategy_config.get("trailing", {})
        
        self.parameters = {
            "fast_macd": macd_config.get("fast", 6),
            "slow_macd": macd_config.get("slow", 13),
            "signal_macd": macd_config.get("signal", 5),
            
            "etf": self._parse_timeframe(timeframes.get("etf", "M1")),
            "ltf": self._parse_timeframe(timeframes.get("ltf", "M5")),
            "htf": self._parse_timeframe(timeframes.get("htf", "M15")),
            "ctf": self._parse_timeframe(timeframes.get("ctf", "H1")),
            
            "ecc": candles.get("m1", 100),
            "lcc": candles.get("m5", 100),
            "hcc": candles.get("m15", 100),
            "ccc": candles.get("h1", 72),
            
            "lot_size": risk.get("lot_size", 0.02),
            
            "atr_length": vol_filter.get("atr_length", 14),
            "vol_multiplier": vol_filter.get("multiplier", 1.5),
            "vol_tp_factor": vol_filter.get("tp_factor", 2.5),
            "vol_sl_factor": vol_filter.get("sl_factor", 1.5),
            "adx_threshold": vol_filter.get("adx_threshold", 20),
            "use_volatility_filter": vol_filter.get("enabled", True),
            
            "interval": execution.get("interval_seconds", 30),
            
            "use_trailing": trailing_config.get("enabled", True),
            "etf_trail": self._parse_timeframe(trailing_config.get("etf", "M1")),
            "ltf_trail": self._parse_timeframe(trailing_config.get("ltf", "M5")),
            "htf_trail": self._parse_timeframe(trailing_config.get("htf", "M15")),
            "atr_multiplier": vol_filter.get("multiplier", 2.0),
            "trail_activation": trailing_config.get("trail_activation", 0.15),
            "ema_length": 20,
            "adx_length": 14,
            "min_volatility": None,
            
            # NEW: Emergency exit protection
            "max_drawdown_pct": risk.get("max_drawdown_pct", 3.0),
            "emergency_exit_enabled": risk.get("emergency_exit_enabled", True),
            "max_spread_pips": risk.get("max_spread_pips", 2.0),

            "bypass_spread_check": strategy_config.get("bypass_spread_check", False),
        }
        
        self.max_open_signals = execution.get("max_open_signals", 1)
        
        if params:
            self.parameters.update(params)
        
        super().__init__(symbol=symbol, params=self.parameters, sessions=sessions, name=name)
        self.tracker = Tracker(snooze=self.interval or self.etf.seconds)
        self.trader = ScalpTrader(symbol=self.symbol)
        
        logger.info(f"✅ Initialized {name} for {symbol.name}")
        logger.info(f"   📊 Timeframes: ETF={self.etf.name}, LTF={self.ltf.name}, HTF={self.htf.name}, CTF={self.ctf.name}")
        logger.info(f"   🛡️ Emergency Exit: {'Enabled' if self.parameters.get('emergency_exit_enabled') else 'Disabled'}")

    @staticmethod
    def _parse_timeframe(tf_str: str) -> TimeFrame:
        """Parse timeframe string to TimeFrame enum"""
        timeframe_map = {
            "M1": TimeFrame.M1,
            "M5": TimeFrame.M5,
            "M15": TimeFrame.M15,
            "M30": TimeFrame.M30,
            "H1": TimeFrame.H1,
            "H4": TimeFrame.H4,
            "D1": TimeFrame.D1,
        }
        return timeframe_map.get(tf_str, TimeFrame.M1)

    async def get_total_open_positions(self) -> int:
        """Get total open positions count for SPECIFIC SYMBOLS ONLY"""
        try:
            import MetaTrader5 as mt5
            
            # Danh sách symbols bạn đang trade
            my_symbols = ["EURUSD", "GBPUSD"]  # Thêm symbol nào đang chạy vào đây
            
            total_count = 0
            
            for symbol in my_symbols:
                positions = mt5.positions_get(symbol=symbol)
                if positions:
                    count = len(positions)
                    total_count += count
                    logger.debug(f"   {symbol}: {count} position(s)")
            
            logger.debug(f"📊 Total positions for tracked symbols: {total_count}/{len(my_symbols)}")
            return total_count
            
        except Exception as e:
            logger.error(f"Error getting total positions: {e}")
            return 0


    async def has_open_position_for_symbol(self) -> bool:
        """Chỉ kiểm tra lệnh mở của CHÍNH symbol đang chạy"""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=self.symbol.name)
            
            if not positions:
                return False

            count = len(positions)
            logger.debug(f"{self.symbol.name} Đang có {count} lệnh mở")
            return count > 0

        except Exception as e:
            logger.error(f"Lỗi kiểm tra lệnh {self.symbol.name}: {e}")
            return False

    def validate_numeric_values(self, *values) -> bool:
        """Validate all numeric values are valid (not NaN, not None, finite)"""
        for i, val in enumerate(values):
            if val is None:
                logger.debug(f"❌ Value at index {i} is None")
                return False
            if pd.isna(val):
                logger.debug(f"❌ Value at index {i} is NaN")
                return False
            if not np.isfinite(val):
                logger.debug(f"❌ Value at index {i} is not finite: {val}")
                return False
        return True

    async def check_spread(self) -> bool:
        """Check spread with bypass option"""
        bypass = self.parameters.get("bypass_spread_check", False)
        
        if bypass:
            logger.info(f"{self.symbol.name} SPREAD CHECK BYPASSED (bypass_spread_check = true)")
            return True

        # --- KIỂM TRA BÌNH THƯỜNG ---
        try:
            import MetaTrader5 as mt5
            tick = mt5.symbol_info_tick(self.symbol.name)
            if not tick:
                logger.warning(f"{self.symbol.name} No tick data")
                return False

            spread = (tick.ask - tick.bid) / self.symbol.point
            max_spread = self.parameters.get("max_spread_pips", 2.0)

            logger.debug(f"{self.symbol.name} Spread: {spread:.1f}p (max: {max_spread}p)")

            if spread > max_spread:
                logger.info(f"{self.symbol.name} SPREAD TOO HIGH: {spread:.1f} > {max_spread} → BLOCKED")
                return False

            return True
        except Exception as e:
            logger.error(f"Spread check error: {e}")
            return False

    async def check_emergency_exit(self):
        """Emergency exit protection for gap/sudden moves"""
        try:
            import MetaTrader5 as mt5
            
            if not self.parameters.get("emergency_exit_enabled", True):
                return
            
            positions = mt5.positions_get(symbol=self.symbol.name)
            
            if positions is None or len(positions) == 0:
                return
            
            max_drawdown = self.parameters.get("max_drawdown_pct", 3.0)
            
            logger.debug(f"🔍 {self.symbol.name} Checking emergency exit for {len(positions)} position(s)")
            
            for position in positions:
                entry_price = position.price_open
                current_price = position.price_current
                position_type = position.type
                
                # Calculate current drawdown %
                if position_type == 0:  # BUY
                    drawdown_pct = ((entry_price - current_price) / entry_price) * 100
                else:  # SELL
                    drawdown_pct = ((current_price - entry_price) / entry_price) * 100
                
                logger.debug(f"📉 {self.symbol.name} Ticket {position.ticket} drawdown: {drawdown_pct:.2f}% (max: {max_drawdown}%)")
                
                if drawdown_pct > max_drawdown:
                    logger.warning(
                        f"🚨 {self.symbol.name} EMERGENCY EXIT triggered! "
                        f"Drawdown: {drawdown_pct:.2f}% > {max_drawdown}%"
                    )
                    
                    # Close position immediately
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "position": position.ticket,
                        "symbol": self.symbol.name,
                        "volume": position.volume,
                        "type": mt5.ORDER_TYPE_SELL if position_type == 0 else mt5.ORDER_TYPE_BUY,
                        "price": mt5.symbol_info_tick(self.symbol.name).bid if position_type == 0 else mt5.symbol_info_tick(self.symbol.name).ask,
                        "deviation": 20,
                        "magic": 234000,
                        "comment": "emergency_exit",
                    }
                    
                    result = mt5.order_send(request)
                    
                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"✅ Emergency exit executed for ticket {position.ticket}")
                        bot_tele(
                            f"🚨 EMERGENCY EXIT\n"
                            f"{self.symbol.name}\n"
                            f"Ticket: {position.ticket}\n"
                            f"Drawdown: {drawdown_pct:.2f}%\n"
                            f"Closed at: {current_price:.5f}"
                        )
                    else:
                        logger.error(f"❌ Emergency exit failed: {result.retcode}")
                        
        except Exception as e:
            logger.error(f"Error in emergency exit: {e}", exc_info=True)

    async def check_trend(self):
        """Multi-timeframe trend analysis with detailed logging"""
        try:
            logger.info(f"🔍 {self.symbol.name} ========== STARTING TREND CHECK ==========")
            
            # STEP 1: Check spread
            logger.info(f"📏 {self.symbol.name} [STEP 1/8] Checking spread...")
            if not await self.check_spread():
                logger.info(f"❌ {self.symbol.name} [STEP 1/8] FAILED - Spread too high, aborting")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            logger.info(f"✅ {self.symbol.name} [STEP 1/8] PASSED - Spread acceptable")

            # STEP 2: Get candles
            logger.info(f"📊 {self.symbol.name} [STEP 2/8] Fetching candle data...")
            ctf_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=self.ctf, count=self.ccc)
            htf_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=self.htf, count=self.hcc)
            ltf_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=self.ltf, count=self.lcc)
            etf_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=self.etf, count=self.ecc)

            # Validate data
            data_status = {
                'CTF': len(ctf_candles_obj) if ctf_candles_obj else 0,
                'HTF': len(htf_candles_obj) if htf_candles_obj else 0,
                'LTF': len(ltf_candles_obj) if ltf_candles_obj else 0,
                'ETF': len(etf_candles_obj) if etf_candles_obj else 0,
            }
            
            logger.info(f"📊 {self.symbol.name} Data received: {data_status}")
            
            if any(c is None or len(c) < 50 for c in [ctf_candles_obj, htf_candles_obj, ltf_candles_obj, etf_candles_obj]):
                logger.warning(f"❌ {self.symbol.name} [STEP 2/8] FAILED - Insufficient data (need 50+ candles)")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            
            logger.info(f"✅ {self.symbol.name} [STEP 2/8] PASSED - All timeframes have sufficient data")

            # Convert to DataFrames
            def to_df(candles):
                return pd.DataFrame({
                    'time': [c.time for c in candles],
                    'open': [c.open for c in candles],
                    'high': [c.high for c in candles],
                    'low': [c.low for c in candles],
                    'close': [c.close for c in candles],
                    'tick_volume': [c.tick_volume for c in candles],
                })

            ctf_candles = to_df(ctf_candles_obj)
            htf_candles = to_df(htf_candles_obj)
            ltf_candles = to_df(ltf_candles_obj)
            etf_candles = to_df(etf_candles_obj)

            # STEP 3: Check for duplicate entry
            logger.info(f"🔄 {self.symbol.name} [STEP 3/8] Checking for duplicate signals...")
            current_etf = etf_candles.iloc[-1]
            if (current_etf["time"] <= self.tracker.trend_time and 
                current_etf["close"] == self.tracker.last_trend_price):
                logger.info(f"⏭️ {self.symbol.name} [STEP 3/8] Same candle as previous check - skipping")
                self.tracker.update(new=False, order_type=None, snooze=5)
                return

            self.tracker.update(new=True, trend_time=current_etf["time"], last_trend_price=current_etf["close"])
            logger.info(f"✅ {self.symbol.name} [STEP 3/8] PASSED - New candle detected")

            # STEP 4: LTF Trend Analysis
            logger.info(f"📈 {self.symbol.name} [STEP 4/8] Analyzing LTF (M5) trend...")
            ema_20_ltf = ta.ema(ltf_candles["close"], length=20)
            ema_50_ltf = ta.ema(ltf_candles["close"], length=50)
            current_close_ltf = ltf_candles["close"].iloc[-1]
            current_ema20_ltf = ema_20_ltf.iloc[-1]
            current_ema50_ltf = ema_50_ltf.iloc[-1]
            
            logger.info(
                f"   LTF values: Price={current_close_ltf:.5f}, "
                f"EMA20={current_ema20_ltf:.5f}, EMA50={current_ema50_ltf:.5f}"
            )
            
            if not self.validate_numeric_values(current_ema20_ltf, current_ema50_ltf, current_close_ltf):
                logger.warning(f"❌ {self.symbol.name} [STEP 4/8] FAILED - LTF EMA values invalid (NaN/None)")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            
            # Determine LTF trend
            ltf_trend = "bullish" if (current_ema20_ltf > current_ema50_ltf and current_close_ltf > current_ema20_ltf) else \
                       ("bearish" if (current_ema20_ltf < current_ema50_ltf and current_close_ltf < current_ema20_ltf) else "ranging")
            
            logger.info(f"   LTF Trend: {ltf_trend.upper()}")
            
            if ltf_trend == "ranging":
                logger.info(f"❌ {self.symbol.name} [STEP 4/8] FAILED - LTF in ranging mode (no clear trend)")
                self.tracker.update(trend="ranging", order_type=None, tp=0, sl=0)
                return
            
            logger.info(f"✅ {self.symbol.name} [STEP 4/8] PASSED - LTF shows clear {ltf_trend} trend")

            # STEP 5: HTF Confirmation
            logger.info(f"📈 {self.symbol.name} [STEP 5/8] Checking HTF (M15) confirmation...")
            ema_50_htf = ta.ema(htf_candles["close"], length=50)
            current_close_htf = htf_candles["close"].iloc[-1]
            current_ema_htf = ema_50_htf.iloc[-1]
            
            logger.info(
                f"   HTF values: Price={current_close_htf:.5f}, EMA50={current_ema_htf:.5f}"
            )
            
            if not self.validate_numeric_values(current_ema_htf, current_close_htf):
                logger.warning(f"❌ {self.symbol.name} [STEP 5/8] FAILED - HTF EMA not ready (NaN/None)")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            
            htf_trend = "bullish" if current_close_htf > current_ema_htf else "bearish"
            logger.info(f"   HTF Trend: {htf_trend.upper()}")
            
            # Check alignment
            if ltf_trend != htf_trend:
                logger.info(
                    f"❌ {self.symbol.name} [STEP 5/8] FAILED - Trend mismatch "
                    f"(LTF: {ltf_trend} vs HTF: {htf_trend})"
                )
                self.tracker.update(trend="ranging", order_type=None, tp=0, sl=0)
                return
            
            logger.info(f"✅ {self.symbol.name} [STEP 5/8] PASSED - HTF confirms {htf_trend} trend")

            # # STEP 6: MACD Signal
            # logger.info(f"📊 {self.symbol.name} [STEP 6/8] Calculating MACD signal...")
            # macd_df = ta.macd(
            #     etf_candles["close"],
            #     fast=self.fast_macd,
            #     slow=self.slow_macd,
            #     signal=self.signal_macd
            # )

            # if macd_df is None or macd_df.empty:
            #     logger.warning(f"❌ {self.symbol.name} [STEP 6/8] FAILED - MACD calculation returned None/empty")
            #     self.tracker.update(order_type=None, tp=0, sl=0)
            #     return

            # macd_col = f"MACD_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"
            # signal_col = f"MACDs_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"
            # hist_col = f"MACDh_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"

            # current_macd = macd_df[macd_col].iloc[-1]
            # current_signal = macd_df[signal_col].iloc[-1]
            # current_hist = macd_df[hist_col].iloc[-1]
            # prev_macd = macd_df[macd_col].iloc[-2]
            # prev_signal = macd_df[signal_col].iloc[-2]

            # logger.info(
            #     f"   MACD: current={current_macd:.6f}, signal={current_signal:.6f}, "
            #     f"hist={current_hist:.6f}"
            # )
            # logger.info(
            #     f"   MACD prev: macd={prev_macd:.6f}, signal={prev_signal:.6f}"
            # )

            # if not self.validate_numeric_values(current_macd, current_signal, current_hist, prev_macd, prev_signal):
            #     logger.warning(f"❌ {self.symbol.name} [STEP 6/8] FAILED - MACD values invalid")
            #     self.tracker.update(order_type=None, tp=0, sl=0)
            #     return
            
            # # Check for crossover
            # has_bullish_cross = (prev_macd <= prev_signal and current_macd > current_signal and current_hist > 0)
            # has_bearish_cross = (prev_macd >= prev_signal and current_macd < current_signal and current_hist < 0)
            
            # logger.info(
            #     f"   Crossover: Bullish={has_bullish_cross}, Bearish={has_bearish_cross}"
            # )
            
            # if not has_bullish_cross and not has_bearish_cross:
            #     logger.info(f"❌ {self.symbol.name} [STEP 6/8] NO CROSSOVER - Waiting for MACD signal")
            #     self.tracker.update(trend="ranging", order_type=None, tp=0, sl=0)
            #     return
            
            # logger.info(f"✅ {self.symbol.name} [STEP 6/8] PASSED - MACD crossover detected")
            # Thay thế đoạn STEP 6 trong hàm check_trend()

            # STEP 6: MACD Signal (RELAXED VERSION)
            logger.info(f"📊 {self.symbol.name} [STEP 6/8] Calculating MACD signal...")
            macd_df = ta.macd(
                etf_candles["close"],
                fast=self.fast_macd,
                slow=self.slow_macd,
                signal=self.signal_macd
            )

            if macd_df is None or macd_df.empty:
                logger.warning(f"❌ {self.symbol.name} [STEP 6/8] FAILED - MACD calculation returned None/empty")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            macd_col = f"MACD_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"
            signal_col = f"MACDs_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"
            hist_col = f"MACDh_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"

            current_macd = macd_df[macd_col].iloc[-1]
            current_signal = macd_df[signal_col].iloc[-1]
            current_hist = macd_df[hist_col].iloc[-1]
            prev_macd = macd_df[macd_col].iloc[-2]
            prev_signal = macd_df[signal_col].iloc[-2]

            # Check 2 cây trước nữa để nới lỏng
            prev2_macd = macd_df[macd_col].iloc[-3] if len(macd_df) >= 3 else None
            prev2_signal = macd_df[signal_col].iloc[-3] if len(macd_df) >= 3 else None

            logger.info(
                f"   MACD: current={current_macd:.6f}, signal={current_signal:.6f}, "
                f"hist={current_hist:.6f}"
            )
            logger.info(
                f"   MACD prev: macd={prev_macd:.6f}, signal={prev_signal:.6f}"
            )

            if not self.validate_numeric_values(current_macd, current_signal, current_hist, prev_macd, prev_signal):
                logger.warning(f"❌ {self.symbol.name} [STEP 6/8] FAILED - MACD values invalid")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            # ===== NỚI LỎNG: Check crossover trong 2 cây gần nhất =====
            has_bullish_cross = False
            has_bearish_cross = False

            # Check cây hiện tại
            if (prev_macd <= prev_signal and current_macd > current_signal and current_hist > 0):
                has_bullish_cross = True
                logger.info("   🎯 Bullish crossover: CURRENT candle")
            elif (prev_macd >= prev_signal and current_macd < current_signal and current_hist < 0):
                has_bearish_cross = True
                logger.info("   🎯 Bearish crossover: CURRENT candle")

            # Check cây trước nếu chưa có signal
            if not has_bullish_cross and not has_bearish_cross and prev2_macd is not None:
                if (prev2_macd <= prev2_signal and prev_macd > prev_signal and current_hist > 0):
                    has_bullish_cross = True
                    logger.info("   🎯 Bullish crossover: PREVIOUS candle (still valid)")
                elif (prev2_macd >= prev2_signal and prev_macd < prev_signal and current_hist < 0):
                    has_bearish_cross = True
                    logger.info("   🎯 Bearish crossover: PREVIOUS candle (still valid)")

            # Hoặc: MACD đang ở vùng mạnh
            if not has_bullish_cross and not has_bearish_cross:
                # Bullish: MACD > Signal + histogram tăng
                if current_macd > current_signal and current_hist > 0 and current_hist > prev_macd - prev_signal:
                    has_bullish_cross = True
                    logger.info("   🎯 Strong bullish momentum (MACD > Signal + rising)")
                # Bearish: MACD < Signal + histogram giảm
                elif current_macd < current_signal and current_hist < 0 and current_hist < prev_macd - prev_signal:
                    has_bearish_cross = True
                    logger.info("   🎯 Strong bearish momentum (MACD < Signal + falling)")

            logger.info(
                f"   Crossover: Bullish={has_bullish_cross}, Bearish={has_bearish_cross}"
            )

            if not has_bullish_cross and not has_bearish_cross:
                logger.info(f"❌ {self.symbol.name} [STEP 6/8] NO MACD SIGNAL - Waiting for crossover or momentum")
                self.tracker.update(trend="ranging", order_type=None, tp=0, sl=0)
                return

            logger.info(f"✅ {self.symbol.name} [STEP 6/8] PASSED - MACD signal detected")

            # STEP 7: Volatility Filter
            logger.info(f"📉 {self.symbol.name} [STEP 7/8] Applying volatility filter...")
            vol_entry = True
            vol_tp_value = None
            vol_sl_value = None
            
            if self.use_volatility_filter:
                try:
                    # Calculate ATR
                    atr_series = ta.atr(
                        high=ltf_candles["high"],
                        low=ltf_candles["low"],
                        close=ltf_candles["close"],
                        length=self.atr_length
                    )
                    
                    if atr_series is None or atr_series.empty:
                        logger.warning(f"❌ {self.symbol.name} [STEP 7/8] FAILED - ATR calculation returned None")
                        self.tracker.update(order_type=None, tp=0, sl=0)
                        return
                    
                    atr_value = atr_series.iloc[-1]
                    logger.info(f"   ATR value: {atr_value:.5f}")
                    
                    if not self.validate_numeric_values(atr_value):
                        logger.warning(f"❌ {self.symbol.name} [STEP 7/8] FAILED - ATR value invalid (NaN/infinite)")
                        self.tracker.update(order_type=None, tp=0, sl=0)
                        return
                    
                    # Calculate ADX
                    adx_df = ta.adx(
                        high=ltf_candles["high"],
                        low=ltf_candles["low"],
                        close=ltf_candles["close"],
                        length=self.adx_length
                    )
                    
                    if adx_df is not None and not adx_df.empty:
                        adx_value = adx_df[f"ADX_{self.adx_length}"].iloc[-1]
                        logger.info(f"   ADX value: {adx_value:.2f} (threshold: {self.adx_threshold})")
                        
                        if self.validate_numeric_values(adx_value):
                            if adx_value < self.adx_threshold:
                                logger.info(
                                    f"❌ {self.symbol.name} [STEP 7/8] FAILED - ADX too weak "
                                    f"({adx_value:.1f} < {self.adx_threshold})"
                                )
                                self.tracker.update(trend="ranging", order_type=None, tp=0, sl=0)
                                return
                        else:
                            logger.warning(f"⚠️ {self.symbol.name} ADX value invalid - skipping ADX filter")
                    
                    # Calculate TP/SL from ATR
                    vol_tp_value = atr_value * self.vol_tp_factor
                    vol_sl_value = atr_value * self.vol_sl_factor
                    
                    logger.info(
                        f"   TP distance: {vol_tp_value:.5f} (ATR * {self.vol_tp_factor})"
                    )
                    logger.info(
                        f"   SL distance: {vol_sl_value:.5f} (ATR * {self.vol_sl_factor})"
                    )
                    logger.info(f"✅ {self.symbol.name} [STEP 7/8] PASSED - Volatility filter OK")
                    
                except Exception as vol_err:
                    logger.error(f"❌ {self.symbol.name} [STEP 7/8] FAILED - Volatility filter error: {vol_err}")
                    self.tracker.update(order_type=None, tp=0, sl=0)
                    return
            else:
                logger.info(f"⏭️ {self.symbol.name} [STEP 7/8] SKIPPED - Volatility filter disabled")

            # STEP 8: Calculate TP/SL and Generate Signal
            logger.info(f"🎯 {self.symbol.name} [STEP 8/8] Calculating TP/SL and generating signal...")
            current_price = etf_candles["close"].iloc[-1]
            
            logger.info(f"   Current price: {current_price:.5f}")
            
            if not self.validate_numeric_values(current_price):
                logger.warning(f"❌ {self.symbol.name} [STEP 8/8] FAILED - Current price invalid")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            
            if not self.validate_numeric_values(vol_tp_value, vol_sl_value):
                logger.warning(f"❌ {self.symbol.name} [STEP 8/8] FAILED - TP/SL values invalid")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            tp_distance = vol_tp_value
            sl_distance = vol_sl_value

            order_type = None

            # Check for BUY signal
            if (ltf_trend == "bullish" and 
                htf_trend == "bullish" and
                has_bullish_cross and
                vol_entry):
                
                order_type = OrderType.BUY
                tp = current_price + tp_distance
                sl = current_price - sl_distance

                self.tracker.update(
                    trend="bullish",
                    snooze=self.interval,
                    order_type=OrderType.BUY,
                    tp=tp,
                    sl=sl
                )

                logger.info(f"🟢 {self.symbol.name} [STEP 8/8] ✅ BUY SIGNAL GENERATED!")
                logger.info(
                    f"   Entry: {current_price:.5f} | TP: {tp:.5f} (+{tp_distance:.5f}) | "
                    f"SL: {sl:.5f} (-{sl_distance:.5f})"
                )
                logger.info(
                    f"   Risk/Reward: 1:{(tp_distance/sl_distance):.2f}"
                )
                
                # Log to signal file using helper function
                if LOGGING_HELPERS_AVAILABLE:
                    log_signal(
                        symbol=self.symbol.name,
                        signal_type="BUY",
                        details={
                            "price": f"{current_price:.5f}",
                            "tp": f"{tp:.5f}",
                            "sl": f"{sl:.5f}",
                            "rr": f"{tp_distance/sl_distance:.2f}",
                            "ltf": ltf_trend,
                            "htf": htf_trend
                        }
                    )

            # Check for SELL signal
            elif (ltf_trend == "bearish" and 
                  htf_trend == "bearish" and
                  has_bearish_cross and
                  vol_entry):
                
                order_type = OrderType.SELL
                tp = current_price - tp_distance
                sl = current_price + sl_distance

                self.tracker.update(
                    trend="bearish",
                    snooze=self.interval,
                    order_type=OrderType.SELL,
                    tp=tp,
                    sl=sl
                )

                logger.info(f"🔴 {self.symbol.name} [STEP 8/8] ✅ SELL SIGNAL GENERATED!")
                logger.info(
                    f"   Entry: {current_price:.5f} | TP: {tp:.5f} (-{tp_distance:.5f}) | "
                    f"SL: {sl:.5f} (+{sl_distance:.5f})"
                )
                logger.info(
                    f"   Risk/Reward: 1:{(tp_distance/sl_distance):.2f}"
                )
                
                # Log to signal file using helper function
                if LOGGING_HELPERS_AVAILABLE:
                    log_signal(
                        symbol=self.symbol.name,
                        signal_type="SELL",
                        details={
                            "price": f"{current_price:.5f}",
                            "tp": f"{tp:.5f}",
                            "sl": f"{sl:.5f}",
                            "rr": f"{tp_distance/sl_distance:.2f}",
                            "ltf": ltf_trend,
                            "htf": htf_trend
                        }
                    )

            else:
                # No signal - log why
                reasons = []
                if ltf_trend == "ranging":
                    reasons.append("LTF ranging")
                if ltf_trend != htf_trend:
                    reasons.append(f"Trend mismatch (LTF:{ltf_trend} vs HTF:{htf_trend})")
                if not has_bullish_cross and not has_bearish_cross:
                    reasons.append("No MACD crossover")
                if not vol_entry:
                    reasons.append("Volatility filter blocked")
                
                logger.info(f"⏸️ {self.symbol.name} [STEP 8/8] NO SIGNAL - Reasons: {', '.join(reasons)}")
                
                self.tracker.update(
                    trend="ranging",
                    snooze=self.interval,
                    order_type=None,
                    tp=0,
                    sl=0
                )
            
            logger.info(f"🏁 {self.symbol.name} ========== TREND CHECK COMPLETED ==========\n")

        except Exception as err:
            logger.error(f"❌ {self.symbol.name} Error in check_trend: {err}", exc_info=True)
            self.tracker.update(trend="ranging", snooze=self.interval, order_type=None, tp=0, sl=0)

    async def update_trailing_stop(self):
        """Aggressive trailing stop for scalping - FIXED & OPTIMIZED"""
        try:
            import MetaTrader5 as mt5
            
            if not getattr(self, 'use_trailing', False):
                return
            
            positions = mt5.positions_get(symbol=self.symbol.name)
            if not positions:
                return

            logger.debug(f"{self.symbol.name} Checking trailing stop for {len(positions)} position(s)")

            for pos in positions:
                ticket = pos.ticket
                pos_type = pos.type  # 0=BUY, 1=SELL
                entry = pos.price_open
                current_price = pos.price_current
                current_sl = pos.sl or 0
                current_tp = pos.tp

                # Tính khoảng cách TP
                tp_distance = (current_tp - entry) if pos_type == 0 else (entry - current_tp)
                if tp_distance <= 0:
                    logger.warning(f"Invalid TP distance for ticket {ticket}: {tp_distance}")
                    continue

                # Tính % đạt được so với TP
                profit_distance = (current_price - entry) if pos_type == 0 else (entry - current_price)
                profit_pct = (profit_distance / tp_distance) * 100

                if profit_pct < 0:
                    logger.debug(f"Ticket {ticket} in loss ({profit_pct:.1f}%) - skip trailing")
                    continue

                # === TRAILING LOGIC (chuẩn scalping) ===
                new_sl = None
                status = "none"

                if profit_pct >= 50:  # 50% TP → Lock 30% profit
                    lock_price = entry + (tp_distance * 0.30) if pos_type == 0 else entry - (tp_distance * 0.30)
                    new_sl = lock_price
                    status = "lock_30pct"
                    logger.info(f"Ticket {ticket} | 50% TP → Lock +30% profit @ {new_sl:.5f}")

                elif profit_pct >= 30:  # 30% TP → Breakeven
                    new_sl = entry
                    status = "breakeven"
                    logger.info(f"Ticket {ticket} | 30% TP → Breakeven SL @ {entry:.5f}")

                elif profit_pct >= 15:  # 15% TP → Pull SL gần entry (chỉ -5% rủi ro)
                    offset = tp_distance * 0.05
                    new_sl = entry - offset if pos_type == 0 else entry + offset
                    status = "near_entry"
                    logger.info(f"Ticket {ticket} | 15% TP → SL near entry @ {new_sl:.5f}")

                # === CHỈ CẬP NHẬT NẾU CẢI THIỆN ===
                if new_sl is not None:
                    should_update = (pos_type == 0 and new_sl > current_sl) or (pos_type == 1 and new_sl < current_sl)
                    
                    if should_update and abs(new_sl - current_sl) > 1e-5:  # tránh float error
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": ticket,
                            "sl": new_sl,
                            "tp": current_tp,
                        }
                        result = mt5.order_send(request)

                        if result.retcode == mt5.TRADE_RETCODE_DONE:
                            logger.info(f"TRAILED | {self.symbol.name} | #{ticket} | "
                                      f"{profit_pct:.1f}% → {status.upper()} | "
                                      f"SL: {current_sl:.5f} → {new_sl:.5f}")
                            
                            # Gửi Telegram
                            bot_tele(
                                f"{self.symbol.name} Trailing\n"
                                f"#{ticket} | {profit_pct:.1f}% TP\n"
                                f"New SL: {new_sl:.5f}\n"
                                f"Status: {status.replace('_', ' ').title()}"
                            )
                        else:
                            logger.warning(f"Trail failed #{ticket} | Code: {result.retcode}")
                    else:
                        logger.debug(f"SL not improved #{ticket} | {current_sl:.5f} → {new_sl:.5f}")

        except Exception as e:
            logger.error(f"Trailing stop error: {e}", exc_info=True)

            
    async def trade(self):
        """Main trading loop with comprehensive logging"""
        waiting_for_slots = False
        loop_count = 0
        
        logger.info(f"🚀 {self.symbol.name} Starting trading loop (interval: {self.interval}s)")
        
        while True:
            try:
                loop_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 {self.symbol.name} Loop #{loop_count} - {pd.Timestamp.now()}")
                logger.info(f"{'='*60}")
                
                # STEP 1: Emergency exit check
                if self.parameters.get("emergency_exit_enabled", True):
                    logger.debug(f"🚨 {self.symbol.name} [1/3] Checking emergency exit...")
                    await self.check_emergency_exit()
                
                # STEP 2: Trailing stop
                if self.use_trailing:
                    logger.debug(f"🔒 {self.symbol.name} [2/3] Checking trailing stops...")
                    await self.update_trailing_stop()
                
                # STEP 3: Check trend & signal
                logger.info(f"📊 {self.symbol.name} [3/3] Analyzing market for signals...")
                await self.check_trend()

                # STEP 4: Execute trade if signal exists
                if self.tracker.order_type is not None:
                    logger.info(f"🎯 {self.symbol.name} Signal detected: {self.tracker.order_type}")
                    
                    # Check if already has position for this symbol
                    if await self.has_open_position_for_symbol():
                        logger.info(f"⏸️ {self.symbol.name} Already has open position - SKIPPING new entry")
                        self.tracker.update(order_type=None, tp=0, sl=0)
                        await asyncio.sleep(self.interval)
                        continue

                    # Check max positions limit
                    total_positions = await self.get_total_open_positions()
                    
                    if total_positions >= self.max_open_signals:
                        if not waiting_for_slots:
                            logger.info(
                                f"⏸️ {self.symbol.name} Max positions reached "
                                f"({total_positions}/{self.max_open_signals}) - WAITING for free slots"
                            )
                            waiting_for_slots = True
                        else:
                            logger.debug(f"⏸️ {self.symbol.name} Still waiting for slots...")
                        
                        await asyncio.sleep(self.interval)
                        continue
                    else:
                        if waiting_for_slots:
                            logger.info(
                                f"✅ {self.symbol.name} Slots now available "
                                f"({total_positions}/{self.max_open_signals}) - RESUMING trading"
                            )
                            waiting_for_slots = False

                    # Double check trader position
                    if await self.trader.has_open_position():
                        logger.debug(f"⏸️ {self.symbol.name} Trader has open position - skipping")
                        await asyncio.sleep(self.interval)
                        continue

                    # Place the trade
                    logger.info(
                        f"📤 {self.symbol.name} Executing {self.tracker.order_type} order:\n"
                        f"   Entry: {self.tracker.last_trend_price:.5f}\n"
                        f"   TP: {self.tracker.tp:.5f}\n"
                        f"   SL: {self.tracker.sl:.5f}\n"
                        f"   Lot Size: {self.lot_size}"
                    )

                    if not hasattr(self, 'trader') or self.trader is None:
                        logger.error(f"❌ {self.symbol.name} Trader object is None - CRITICAL ERROR!")
                        await asyncio.sleep(self.interval)
                        continue

                    params = {**self.parameters, "use_fixed_lot": True}
                    result = await self.trader.place_trade_with_sl_tp(
                        order_type=self.tracker.order_type,
                        volume=self.lot_size,
                        sl=self.tracker.sl,
                        tp=self.tracker.tp,
                        parameters=params
                    )

                    if result:
                        logger.info(f"✅ {self.symbol.name} Trade EXECUTED successfully!")
                        
                        # Log execution using helper function
                        if LOGGING_HELPERS_AVAILABLE:
                            log_trade_execution(
                                symbol=self.symbol.name,
                                success=True,
                                details={
                                    "type": str(self.tracker.order_type),
                                    "entry": f"{self.tracker.last_trend_price:.5f}",
                                    "tp": f"{self.tracker.tp:.5f}",
                                    "sl": f"{self.tracker.sl:.5f}",
                                    "lot": self.lot_size
                                }
                            )
                        
                        bot_tele(
                            f"✅ {self.symbol.name} Order Executed\n"
                            f"Direction: {self.tracker.order_type}\n"
                            f"Entry: {self.tracker.last_trend_price:.5f}\n"
                            f"TP: {self.tracker.tp:.5f}\n"
                            f"SL: {self.tracker.sl:.5f}\n"
                            f"Lot: {self.lot_size}"
                        )
                    else:
                        logger.warning(f"⚠️ {self.symbol.name} Trade FAILED - Check MT5 connection/settings")
                        
                        # Log failed execution
                        if LOGGING_HELPERS_AVAILABLE:
                            log_trade_execution(
                                symbol=self.symbol.name,
                                success=False,
                                details={
                                    "type": str(self.tracker.order_type),
                                    "entry": f"{self.tracker.last_trend_price:.5f}"
                                }
                            )

                    self.tracker.update(order_type=None, tp=0, sl=0)
                else:
                    logger.debug(f"⏸️ {self.symbol.name} No signal generated - continuing monitoring")

                logger.info(f"⏰ {self.symbol.name} Sleeping for {self.interval}s until next check...\n")
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info(f"🛑 {self.symbol.name} Strategy CANCELLED - Shutting down gracefully")
                break
            except Exception as err:
                logger.error(
                    f"❌ {self.symbol.name} CRITICAL ERROR in trading loop:\n"
                    f"   Error: {err}\n"
                    f"   Loop: #{loop_count}",
                    exc_info=True
                )
                logger.info(f"⏰ Waiting {self.interval}s before retry...")
                await asyncio.sleep(self.interval)