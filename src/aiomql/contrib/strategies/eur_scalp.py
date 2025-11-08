import asyncio
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

# === CONFIG ===
MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 5
TP_PIPS = 30
SL_PIPS = 15
LOT_SIZE = 0.02
ATR_LENGTH = 14

# Max number of simultaneous commands
CANDLE_M1 = 100
CANDLE_M5 = 100

# === VOLATILITY FILTER CONFIG ===
VOL_MULTIPLIER = 1.5      # ATR multiplier for volatility filter
VOL_TP_FACTOR = 2.5       # TP factor based on volatility
VOL_SL_FACTOR = 1.5       # SL factor based on volatility
ADX_THRESHOLD = 20        # Minimum ADX for trend confirmation
USE_VOLATILITY_FILTER = True  # Enable/disable volatility filter


class EUR_SCALP(Strategy):
    """MACD Strategy with volatility filter, continuous loop, and position limit."""

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

    parameters = {  
        "fast_macd": MACD_FAST,
        "slow_macd": MACD_SLOW,
        "signal_macd": MACD_SIGNAL,
        "ltf": TimeFrame.M1,
        "htf": TimeFrame.M15,
        "lcc": CANDLE_M1,
        "hcc": CANDLE_M5,
        "interval": 30, 
        "tp_pips": TP_PIPS,
        "sl_pips": SL_PIPS,
        "lot_size": LOT_SIZE,
        "atr_length": ATR_LENGTH,
        "vol_multiplier": VOL_MULTIPLIER,
        "vol_tp_factor": VOL_TP_FACTOR,
        "vol_sl_factor": VOL_SL_FACTOR,
        "adx_threshold": ADX_THRESHOLD,
        "use_volatility_filter": USE_VOLATILITY_FILTER
    }

    def __init__(self, *, symbol: ForexSymbol, params: dict = None, sessions=None, name="MACD_Volatility_Strategy"):
        super().__init__(symbol=symbol, params=params, sessions=sessions, name=name)
        self.tracker = Tracker(snooze=self.interval or self.ltf.seconds)
        self.trader = ScalpTrader(symbol=self.symbol)


    async def has_open_position_for_symbol(self) -> bool:
        """Kiểm tra xem symbol hiện tại có position đang mở trên MT5 không"""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get(symbol=self.symbol.name)
            
            if positions is None:
                return False
            
            # Kiểm tra có position nào của symbol này không
            has_position = len(positions) > 0
            
            if has_position:
                logger.debug(f"{self.symbol.name} has {len(positions)} open position(s) on MT5")
            
            return has_position
            
        except Exception as e:
            logger.error(f"Error checking position for {self.symbol.name}: {e}")
            return False

    async def check_trend(self):
        """Phân tích trend với volatility filter và tính toán signal"""
        try:
            # ✅ Lấy nến HTF & LTF
            htf_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=self.htf, count=self.hcc)
            ltf_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=self.ltf, count=self.lcc)

            if htf_candles_obj is None or len(htf_candles_obj) < 50:
                logger.warning(f"{self.symbol.name} Insufficient HTF data")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            if ltf_candles_obj is None or len(ltf_candles_obj) < self.slow_macd + self.signal_macd:
                logger.warning(f"{self.symbol.name} Insufficient LTF data")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return

            # ✅ Convert to DataFrame
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

            # ✅ Kiểm tra cần update
            current = htf_candles.iloc[-1]
            if (current is not None and 
                current["time"] <= self.tracker.trend_time and 
                current["close"] == self.tracker.last_trend_price):
                self.tracker.update(new=False, order_type=None, snooze=5)
                return

            self.tracker.update(new=True, trend_time=current["time"], last_trend_price=current["close"])

            # ✅ Tính EMA50 HTF
            ema_50 = ta.ema(htf_candles["close"], length=50)
            htf_candles["EMA_50"] = ema_50
            current_close = htf_candles["close"].iloc[-1]
            current_ema = htf_candles["EMA_50"].iloc[-1]
            
            if pd.isna(current_ema):
                logger.warning(f"{self.symbol.name} EMA not ready")
                self.tracker.update(order_type=None, tp=0, sl=0)
                return
            
            htf_trend = "bullish" if current_close > current_ema else "bearish"

            # ✅ Tính MACD LTF
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

            # ✅ Lấy giá trị MACD
            macd_col = f"MACD_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"
            signal_col = f"MACDs_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"
            hist_col = f"MACDh_{self.fast_macd}_{self.slow_macd}_{self.signal_macd}"

            current_macd = macd_df[macd_col].iloc[-1]
            current_signal = macd_df[signal_col].iloc[-1]
            current_hist = macd_df[hist_col].iloc[-1]

            prev_macd = macd_df[macd_col].iloc[-2]
            prev_signal = macd_df[signal_col].iloc[-2]
            prev_hist = macd_df[hist_col].iloc[-2]

            # ✅ VOLATILITY FILTER
            vol_entry = True  # Default: allow entry
            vol_tp_value = None
            vol_sl_value = None
            
            if self.use_volatility_filter:
                # Tính volatility filter trên M5 để giảm noise
                atr_tf = TimeFrame.M5
                atr_candles_obj = await self.symbol.copy_rates_from_pos(timeframe=atr_tf, count=50)
                
                if atr_candles_obj is None or len(atr_candles_obj) < self.atr_length:
                    logger.warning(f"{self.symbol.name} Insufficient data for volatility filter")
                    self.tracker.update(order_type=None, tp=0, sl=0)
                    return

                atr_candles = pd.DataFrame({
                    'high': [c.high for c in atr_candles_obj],
                    'low': [c.low for c in atr_candles_obj],
                    'close': [c.close for c in atr_candles_obj],
                })
                
                # Gọi volatility_filter từ pandas_ta
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
                        adx_threshold=self.adx_threshold
                    )
                except Exception as vol_err:
                    logger.warning(f"{self.symbol.name} Volatility filter error: {vol_err}")
                    # Fallback: disable volatility filter for this iteration
                    vol_entry = True
                    vol_filter_df = None

                if vol_filter_df is None or vol_filter_df.empty:
                    logger.debug(f"{self.symbol.name} Volatility filter returned None/empty - using fallback")
                    # Tính ATR thủ công để có TP/SL
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
                    
                    vol_entry = True  # Allow entry
                    vol_tp_value = atr_value.iloc[-1] * self.vol_tp_factor
                    vol_sl_value = atr_value.iloc[-1] * self.vol_sl_factor
                else:
                    # Lấy giá trị cuối
                    vol_entry = bool(vol_filter_df["VOLF_ENTRY"].iloc[-1])
                    vol_filter_value = vol_filter_df["VOLF"].iloc[-1]
                    
                    if "VOLF_TP" in vol_filter_df.columns:
                        vol_tp_value = vol_filter_df["VOLF_TP"].iloc[-1]
                    if "VOLF_SL" in vol_filter_df.columns:
                        vol_sl_value = vol_filter_df["VOLF_SL"].iloc[-1]

                    # Kiểm tra nếu không đủ volatility hoặc trend yếu
                    if not vol_entry:
                        logger.debug(f"⏸️ {self.symbol.name} Volatility filter blocked entry (low vol or weak trend)")
                        self.tracker.update(
                            trend="ranging",
                            snooze=self.interval,
                            order_type=None,
                            tp=0,
                            sl=0
                        )
                        return

                    logger.debug(f"✅ {self.symbol.name} Volatility filter passed | vol_filter: {vol_filter_value:.5f}")

            # ✅ Tính TP/SL
            current_price = ltf_candles["close"].iloc[-1]
            
            # Sử dụng TP/SL từ volatility filter nếu có, không thì dùng ATR
            if vol_tp_value is not None and vol_sl_value is not None:
                # Dynamic TP/SL từ volatility filter
                tp_distance = vol_tp_value
                sl_distance = vol_sl_value
            else:
                # Fallback về ATR cũ
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

            # ✅ BUY Signal
            if (htf_trend == "bullish" and 
                prev_macd <= prev_signal and 
                current_macd > current_signal and 
                current_hist > 0 and
                vol_entry):  # Thêm volatility filter check
                
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

                logger.info(f"✅ {self.symbol.name} BUY Signal | Price: {current_price:.5f} | TP: {tp:.5f} | SL: {sl:.5f}")

            # ✅ SELL Signal
            elif (htf_trend == "bearish" and 
                  prev_macd >= prev_signal and 
                  current_macd < current_signal and 
                  current_hist < 0 and
                  vol_entry):  # Thêm volatility filter check
                
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

                logger.info(f"❌ {self.symbol.name} SELL Signal | Price: {current_price:.5f} | TP: {tp:.5f} | SL: {sl:.5f}")

            else:
                self.tracker.update(
                    trend="ranging",
                    snooze=self.interval,
                    order_type=None,
                    tp=0,
                    sl=0
                )
                logger.debug(f"⏸️ {self.symbol.name} No signal - HTF: {htf_trend}, MACD hist: {current_hist:.5f}")

        except Exception as err:
            logger.error(f"❌ {self.symbol.name} Error in check_trend: {err}", exc_info=True)
            self.tracker.update(trend="ranging", snooze=self.interval, order_type=None, tp=0, sl=0)

    async def trade(self):
        """Main trading loop - chạy liên tục mỗi 30s"""
        waiting_for_slots = False
        
        while True:
            try:
                # ✅ 1. Check trend & signal với volatility filter
                await self.check_trend()

                # ✅ 2. Nếu có signal
                if self.tracker.order_type is not None:
                    # ✅ Kiểm tra symbol này đã có position trên MT5 chưa
                    if await self.has_open_position_for_symbol():
                        logger.debug(f"⏸️ {self.symbol.name} already has open position on MT5 - skipping new entry")
                        self.tracker.update(order_type=None, tp=0, sl=0)
                        await asyncio.sleep(self.interval)
                        continue

                    # ✅ Double-check với trader's internal check (fallback)
                    if await self.trader.has_open_position():
                        logger.debug(f"{self.symbol.name} already has open trade (trader check) — skip entry")
                        await asyncio.sleep(self.interval)
                        continue

                    # ✅ Place trade
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

                    # Reset tracker
                    self.tracker.update(order_type=None, tp=0, sl=0)

                # ✅ 3. Sleep 30s
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                logger.info(f"🛑 {self.symbol.name} Strategy cancelled")
                break
            except Exception as err:
                logger.error(f"❌ {self.symbol.name} Trade execution failed: {err}", exc_info=True)
                await asyncio.sleep(self.interval)