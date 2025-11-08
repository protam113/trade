import asyncio
from datetime import datetime, timedelta
from logging import getLogger
import pandas_ta as ta
import pandas as pd

from ...lib.strategy import Strategy
from ..symbols import ForexSymbol
from ..utils import Tracker
from ...core.constants import TimeFrame, OrderType
from ..traders.scalp_trader import ScalpTrader
from noti_bot.tele.tele_bot import bot_tele

logger = getLogger(__name__)


class MACD_Strategy1(Strategy):
    """
    MACD Strategy with improved filters for scalping:
    - Signal gap control (prevent spam)
    - Stronger HTF filter (require ALL 3 conditions)
    - Volume confirmation
    - MACD momentum check
    - Stricter volatility/ADX filter
    """

    ltf: TimeFrame
    htf: TimeFrame
    lcc: int
    hcc: int
    fast_macd: int
    slow_macd: int
    signal_macd: int
    tp_pips: float
    sl_pips: float
    lot_size: float
    tracker: Tracker
    interval: int
    vol_multiplier: float
    vol_tp_factor: float
    vol_sl_factor: float
    adx_threshold: float
    use_volatility_filter: bool
    max_open_signals: int
    atr_length: int
    min_signal_gap_minutes: int  # 🆕 NEW

    parameters = {}

    def __init__(self, *, symbol: ForexSymbol, config: dict, params: dict = None, sessions=None, name="MACD_Improved_Strategy"):
        """Initialize strategy with config from JSON"""
        strategy_config = config.get("strategy", {})
        macd_config = strategy_config.get("macd", {})
        timeframes = strategy_config.get("timeframes", {})
        candles = strategy_config.get("candles", {})
        risk = strategy_config.get("risk_management", {})
        vol_filter = strategy_config.get("volatility_filter", {})
        execution = strategy_config.get("execution", {})
        
        self.parameters = {
            "fast_macd": macd_config.get("fast", 12),
            "slow_macd": macd_config.get("slow", 26),
            "signal_macd": macd_config.get("signal", 9),
            "ltf": self._parse_timeframe(timeframes.get("ltf", "M1")),
            "htf": self._parse_timeframe(timeframes.get("htf", "M5")),
            "lcc": candles.get("m1", 200),
            "hcc": candles.get("m5", 100),
            "tp_pips": risk.get("tp_pips", 20),
            "sl_pips": risk.get("sl_pips", 10),
            "lot_size": risk.get("lot_size", 0.01),
            "atr_length": vol_filter.get("atr_length", 14),
            "vol_multiplier": vol_filter.get("multiplier", 2.5),
            "vol_tp_factor": vol_filter.get("tp_factor", 2.0),
            "vol_sl_factor": vol_filter.get("sl_factor", 1.0),
            "adx_threshold": vol_filter.get("adx_threshold", 30),
            "use_volatility_filter": vol_filter.get("enabled", True),
            "interval": execution.get("interval_seconds", 120),
            "min_signal_gap_minutes": execution.get("min_signal_gap_minutes", 15),  # 🆕 NEW
        }
        
        self.max_open_signals = execution.get("max_open_signals", 3)
        
        if params:
            self.parameters.update(params)
        
        super().__init__(symbol=symbol, params=self.parameters, sessions=sessions, name=name)
        self.tracker = Tracker(snooze=self.interval or self.ltf.seconds)
        self.trader = ScalpTrader(symbol=self.symbol)
        
        # 🆕 Track last signal time per symbol (prevent spam)
        self.last_signal_time = {}
        
        logger.info(f"✅ Initialized {name} for {symbol.name} with IMPROVED filters")

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

    def can_generate_signal(self) -> bool:
        """
        🆕 Check if we can generate a new signal
        Prevent spam orders on the same pair
        """
        symbol_name = self.symbol.name
        current_time = datetime.now()
        
        if symbol_name in self.last_signal_time:
            last_time = self.last_signal_time[symbol_name]
            time_diff = (current_time - last_time).total_seconds() / 60
            
            if time_diff < self.min_signal_gap_minutes:
                logger.debug(
                    f"⏸️ {symbol_name} Signal gap too short "
                    f"({time_diff:.1f}min < {self.min_signal_gap_minutes}min)"
                )
                return False
        
        return True
    
    def update_signal_time(self):
        """🆕 Update last signal time"""
        self.last_signal_time[self.symbol.name] = datetime.now()

    async def get_total_open_positions(self) -> int:
        """Đếm tổng số position đang mở (tất cả symbols)"""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get()
            return len(positions) if positions else 0
        except Exception as e:
            logger.error(f"Error getting total positions: {e}")
            return 0

    async def has_open_position_for_symbol(self) -> bool:
        """Kiểm tra xem symbol hiện tại có position đang mở trên MT5 không"""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=self.symbol.name)
            
            if positions is None:
                return False
            
            has_position = len(positions) > 0
            
            if has_position:
                logger.debug(f"{self.symbol.name} has {len(positions)} open position(s) on MT5")
            
            return has_position
            
        except Exception as e:
            logger.error(f"Error checking position for {self.symbol.name}: {e}")
            return False

    async def check_trend(self):
        """
        IMPROVED trend analysis với filters mạnh hơn
        """
        try:
            # ============================================
            # 0️⃣ 🆕 PRE-CHECK: Signal gap control
            # ============================================
            if not self.can_generate_signal():
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            # ============================================
            # 1️⃣ Lấy nến HTF & LTF
            # ============================================
            htf_candles_obj = await self.symbol.copy_rates_from_pos(
                timeframe=self.htf, count=self.hcc
            )
            ltf_candles_obj = await self.symbol.copy_rates_from_pos(
                timeframe=self.ltf, count=self.lcc
            )

            if htf_candles_obj is None or len(htf_candles_obj) < 50:
                logger.warning(f"{self.symbol.name} Insufficient HTF data")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            if ltf_candles_obj is None or len(ltf_candles_obj) < self.slow_macd + self.signal_macd:
                logger.warning(f"{self.symbol.name} Insufficient LTF data")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            # Convert to DataFrame
            htf_candles = pd.DataFrame({
                'time': [c.time for c in htf_candles_obj],
                'open': [c.open for c in htf_candles_obj],
                'high': [c.high for c in htf_candles_obj],
                'low': [c.low for c in htf_candles_obj],
                'close': [c.close for c in htf_candles_obj],
                'tick_volume': [c.tick_volume for c in htf_candles_obj],
            })

            ltf_candles = pd.DataFrame({
                'time': [c.time for c in ltf_candles_obj],
                'open': [c.open for c in ltf_candles_obj],
                'high': [c.high for c in ltf_candles_obj],
                'low': [c.low for c in ltf_candles_obj],
                'close': [c.close for c in ltf_candles_obj],
                'tick_volume': [c.tick_volume for c in ltf_candles_obj],
            })

            # Kiểm tra cần update
            current = htf_candles.iloc[-1]
            if (current is not None and 
                current["time"] <= self.tracker.trend_time and 
                current["close"] == self.tracker.last_trend_price):
                self.tracker.update(new=False, order_type=None, snooze=5)
                return

            self.tracker.update(
                new=True, 
                trend_time=current["time"], 
                last_trend_price=current["close"]
            )

            # ============================================
            # 2️⃣ HTF TREND FILTER - 🔥 STRICTER (ALL 3 conditions)
            # ============================================
            ema_50 = ta.ema(htf_candles["close"], length=50)
            ema_20 = ta.ema(htf_candles["close"], length=20)
            htf_candles["EMA_50"] = ema_50
            htf_candles["EMA_20"] = ema_20
            
            current_close = htf_candles["close"].iloc[-1]
            current_ema50 = htf_candles["EMA_50"].iloc[-1]
            current_ema20 = htf_candles["EMA_20"].iloc[-1]
            prev_ema50 = htf_candles["EMA_50"].iloc[-2]
            
            if pd.isna(current_ema50) or pd.isna(current_ema20):
                logger.warning(f"{self.symbol.name} EMA not ready")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            
            # 🔥 REQUIRE ALL 3 conditions (no more 2/3)
            htf_bullish = (
                current_close > current_ema50 and  # 1. Price above EMA50
                current_ema20 > current_ema50 and  # 2. EMA20 above EMA50
                current_ema50 > prev_ema50         # 3. EMA50 rising
            )
            
            htf_bearish = (
                current_close < current_ema50 and  # 1. Price below EMA50
                current_ema20 < current_ema50 and  # 2. EMA20 below EMA50
                current_ema50 < prev_ema50         # 3. EMA50 falling
            )
            
            if not htf_bullish and not htf_bearish:
                logger.debug(f"⏸️ {self.symbol.name} HTF trend not clear (need ALL 3 conditions)")
                self.tracker.update(
                    trend="ranging",
                    snooze=self.interval,
                    order_type=None,
                    tp=0,
                    sl=0
                )
                return
            
            htf_trend = "bullish" if htf_bullish else "bearish"

            # ============================================
            # 3️⃣ LTF MACD
            # ============================================
            macd_df = ta.macd(
                ltf_candles["close"],
                fast=self.fast_macd,
                slow=self.slow_macd,
                signal=self.signal_macd
            )

            if macd_df is None or macd_df.empty:
                logger.warning(f"{self.symbol.name} MACD calculation failed")
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
            prev_hist = macd_df[hist_col].iloc[-1]

            # ============================================
            # 4️⃣ 🆕 VOLUME CONFIRMATION
            # ============================================
            recent_volume = ltf_candles["tick_volume"].iloc[-3:].mean()
            avg_volume = ltf_candles["tick_volume"].iloc[-50:].mean()
            volume_ok = recent_volume > avg_volume * 1.3  # Must be 30% higher
            
            if not volume_ok:
                logger.debug(
                    f"⏸️ {self.symbol.name} Volume too low "
                    f"({recent_volume/avg_volume:.2f}x < 1.3x)"
                )
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            # ============================================
            # 5️⃣ 🆕 MACD MOMENTUM CHECK
            # ============================================
            hist_accelerating = abs(current_hist) > abs(prev_hist) * 1.2  # Must accelerate 20%
            hist_not_too_weak = abs(current_hist) > abs(prev_hist) * 0.8  # At least 80% of prev
            
            if not hist_not_too_weak:
                logger.debug(f"⏸️ {self.symbol.name} MACD histogram too weak")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            # ============================================
            # 6️⃣ VOLATILITY FILTER (STRICTER with ADX=30)
            # ============================================
            vol_entry = True
            vol_tp_value = None
            vol_sl_value = None
            
            if self.use_volatility_filter:
                atr_tf = TimeFrame.M5
                atr_candles_obj = await self.symbol.copy_rates_from_pos(
                    timeframe=atr_tf, count=50
                )
                
                if atr_candles_obj is None or len(atr_candles_obj) < self.atr_length:
                    logger.warning(f"{self.symbol.name} Insufficient data for volatility filter")
                    self.tracker.update(order_type=None, tp=0, sl=0)
                    return

                atr_candles = pd.DataFrame({
                    'high': [c.high for c in atr_candles_obj],
                    'low': [c.low for c in atr_candles_obj],
                    'close': [c.close for c in atr_candles_obj],
                })
                
                try:
                    vol_filter_df = ta.volatility_filter(
                        high=atr_candles["high"],
                        low=atr_candles["low"],
                        close=atr_candles["close"],
                        length=self.atr_length,
                        multiplier=self.vol_multiplier,
                        tp_factor=self.vol_tp_factor,
                        sl_factor=self.vol_sl_factor,
                        adx_filter=True,
                        adx_threshold=self.adx_threshold  # Now 30 (stricter!)
                    )
                except Exception as vol_err:
                    logger.warning(f"{self.symbol.name} Volatility filter error: {vol_err}")
                    vol_entry = True
                    vol_filter_df = None

                if vol_filter_df is None or vol_filter_df.empty:
                    atr_value = ta.atr(
                        high=atr_candles["high"],
                        low=atr_candles["low"],
                        close=atr_candles["close"],
                        length=self.atr_length
                    )
                    if atr_value is None or atr_value.empty:
                        logger.warning(f"{self.symbol.name} ATR fallback also failed")
                        self.tracker.update(order_type=None, tp=0, sl=0)
                        return
                    
                    vol_entry = True
                    vol_tp_value = atr_value.iloc[-1] * self.vol_tp_factor
                    vol_sl_value = atr_value.iloc[-1] * self.vol_sl_factor
                else:
                    vol_entry = bool(vol_filter_df["VOLF_ENTRY"].iloc[-1])
                    
                    if "VOLF_TP" in vol_filter_df.columns:
                        vol_tp_value = vol_filter_df["VOLF_TP"].iloc[-1]
                    if "VOLF_SL" in vol_filter_df.columns:
                        vol_sl_value = vol_filter_df["VOLF_SL"].iloc[-1]

                    if not vol_entry:
                        logger.debug(
                            f"⏸️ {self.symbol.name} Volatility/ADX filter blocked entry (ADX < {self.adx_threshold})"
                        )
                        self.tracker.update(
                            trend="ranging",
                            snooze=self.interval,
                            order_type=None,
                            tp=0,
                            sl=0
                        )
                        return

            # ============================================
            # 7️⃣ SIGNAL GENERATION - STRICTER CONDITIONS
            # ============================================
            current_price = ltf_candles["close"].iloc[-1]
            
            # Tính TP/SL từ ATR
            if vol_tp_value is not None and vol_sl_value is not None:
                tp_distance = vol_tp_value
                sl_distance = vol_sl_value
            else:
                atr_value = ta.atr(
                    high=atr_candles["high"],
                    low=atr_candles["low"],
                    close=atr_candles["close"],
                    length=self.atr_length
                ).iloc[-1]
                
                if pd.isna(atr_value):
                    logger.warning(f"{self.symbol.name} ATR not ready")
                    self.tracker.update(order_type=None, tp=0, sl=0)
                    return
                
                tp_distance = atr_value * self.vol_tp_factor
                sl_distance = atr_value * self.vol_sl_factor

            order_type = None

            # 🔥 STRICTER BUY: HTF bullish + MACD cross + volume + momentum + volatility
            buy_conditions = (
                htf_trend == "bullish" and
                prev_macd <= prev_signal and
                current_macd > current_signal and
                current_hist > 0 and
                hist_accelerating and  # 🆕 Must accelerate
                volume_ok and          # 🆕 Volume confirmation
                vol_entry
            )
            
            if buy_conditions:
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
                
                # 🆕 Update signal time
                self.update_signal_time()

                logger.info(
                    f"✅ {self.symbol.name} BUY Signal | "
                    f"Price: {current_price:.5f} | TP: {tp:.5f} (+{tp_distance*10000:.1f}p) | "
                    f"SL: {sl:.5f} (-{sl_distance*10000:.1f}p) | "
                    f"Vol: {recent_volume/avg_volume:.2f}x | MACD: {current_hist:.6f}"
                )

            # 🔥 STRICTER SELL
            sell_conditions = (
                htf_trend == "bearish" and
                prev_macd >= prev_signal and
                current_macd < current_signal and
                current_hist < 0 and
                hist_accelerating and
                volume_ok and
                vol_entry
            )
            
            if sell_conditions:
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
                
                # 🆕 Update signal time
                self.update_signal_time()

                logger.info(
                    f"❌ {self.symbol.name} SELL Signal | "
                    f"Price: {current_price:.5f} | TP: {tp:.5f} (-{tp_distance*10000:.1f}p) | "
                    f"SL: {sl:.5f} (+{sl_distance*10000:.1f}p) | "
                    f"Vol: {recent_volume/avg_volume:.2f}x | MACD: {current_hist:.6f}"
                )

            if not buy_conditions and not sell_conditions:
                self.tracker.update(
                    trend="ranging",
                    snooze=self.interval,
                    order_type=None,
                    tp=0,
                    sl=0
                )

        except Exception as err:
            logger.error(
                f"❌ {self.symbol.name} Error in check_trend: {err}", 
                exc_info=True
            )
            self.tracker.update(
                trend="ranging", 
                snooze=self.interval, 
                order_type=None, 
                tp=0, 
                sl=0
            )

    async def trade(self):
        """Main trading loop - chạy liên tục mỗi interval giây"""
        waiting_for_slots = False
        
        while True:
            try:
                await self.check_trend()

                if self.tracker.order_type is not None:
                    if await self.has_open_position_for_symbol():
                        logger.debug(f"⏸️ {self.symbol.name} already has open position on MT5 - skipping new entry")
                        self.tracker.update(order_type=None, tp=0, sl=0)
                        await asyncio.sleep(self.interval)
                        continue

                    total_positions = await self.get_total_open_positions()
                    
                    if total_positions >= self.max_open_signals:
                        if not waiting_for_slots:
                            logger.info(f"⏸️ Max positions reached ({total_positions}/{self.max_open_signals}) - Waiting for free slots...")
                            waiting_for_slots = True
                        
                        logger.debug(f"{self.symbol.name} Still waiting... ({total_positions}/{self.max_open_signals})")
                        await asyncio.sleep(self.interval)
                        continue
                    else:
                        if waiting_for_slots:
                            logger.info(f"✅ Slots available ({total_positions}/{self.max_open_signals}) - Resuming trading")
                            waiting_for_slots = False

                    if await self.trader.has_open_position():
                        logger.debug(f"{self.symbol.name} already has open trade (trader check) — skip entry")
                        await asyncio.sleep(self.interval)
                        continue

                    logger.info(f"🎯 {self.symbol.name} Placing {self.tracker.order_type} | TP: {self.tracker.tp:.5f} | SL: {self.tracker.sl:.5f}")

                    if not hasattr(self, 'trader') or self.trader is None:
                        logger.error(f"❌ {self.symbol.name} Trader is None!")
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
                        logger.info(f"✅ {self.symbol.name} Trade placed successfully!")
                        bot_tele(
                            f"✅ {self.symbol.name} Order Executed\n"
                            f"Direction: {self.tracker.order_type}\n"
                            f"Entry: {self.tracker.tp:.5f}\n"
                            f"TP: {self.tracker.tp:.5f}\n"
                            f"SL: {self.tracker.sl:.5f}\n"
                            f"Lot: {self.lot_size}"
                        )
                    else:
                        logger.warning(f"⚠️ {self.symbol.name} Trade failed!")

                    self.tracker.update(order_type=None, tp=0, sl=0)

                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info(f"🛑 {self.symbol.name} Strategy cancelled")
                break
            except Exception as err:
                logger.error(f"❌ {self.symbol.name} Trade execution failed: {err}", exc_info=True)
                await asyncio.sleep(self.interval)