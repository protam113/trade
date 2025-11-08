import random
from logging import getLogger

from ...lib.strategy import Strategy
from ..symbols import ForexSymbol
from ..utils import Tracker
from ...core.constants import TimeFrame, OrderType
from ..traders.scalp_trader import ScalpTrader

logger = getLogger(__name__)


class Chaos(Strategy):
    """A chaotic strategy that buys and sells randomly."""

    ltf: TimeFrame
    htf: TimeFrame
    lcc: int
    hcc: int
    fast_ema: int
    slow_ema: int
    tracker: Tracker
    interval: int
    parameters = {"fast_ema": 8, "slow_ema": 20, "ltf": TimeFrame.M1, "htf": TimeFrame.M2, "lcc": 100, "hcc": 100,
                  "interval": 0}

    def __init__(self, *, symbol: ForexSymbol, params: dict = None, sessions=None, name="Chaos"):
        super().__init__(symbol=symbol, params=params, sessions=sessions, name=name)
        self.tracker = Tracker(snooze=self.interval or self.ltf.seconds)
        self.trader = ScalpTrader(symbol=self.symbol)

    async def check_trend(self):
        try:
            # 📊 Lấy cả LTF và HTF
            htf_candles = await self.symbol.copy_rates_from_pos(timeframe=self.htf, count=self.hcc)
            ltf_candles = await self.symbol.copy_rates_from_pos(timeframe=self.ltf, count=self.lcc)
            
            if (
                (current := htf_candles[-1])
                and current.time < self.tracker.trend_time
                and current.close == self.tracker.last_trend_price
            ):
                self.tracker.update(new=False, order_type=None, snooze=5)
                return
            
            self.tracker.update(new=True, trend_time=current.time, last_trend_price=current.close)
            
            # ✅ Tính EMA cho HTF (trend chính)
            htf_candles.ta.ema(length=50, append=True, fillna=0)  # EMA dài cho trend
            htf_trend = "bullish" if htf_candles["close"].iloc[-1] > htf_candles["EMA_50"].iloc[-1] else "bearish"
            
            # ✅ Tính EMA cho LTF (entry signal)
            ltf_candles.ta.ema(length=self.fast_ema, append=True, fillna=0)
            ltf_candles.ta.ema(length=self.slow_ema, append=True, fillna=0)
            ltf_candles.rename(inplace=True, **{f"EMA_{self.fast_ema}": "fast", f"EMA_{self.slow_ema}": "slow"})
            
            fast_ema = ltf_candles["fast"].iloc[-1]
            slow_ema = ltf_candles["slow"].iloc[-1]
            prev_fast = ltf_candles["fast"].iloc[-2]
            prev_slow = ltf_candles["slow"].iloc[-2]
            
            order_type = None
            
            # 🟢 BUY: HTF bullish + LTF golden cross
            if htf_trend == "bullish" and prev_fast <= prev_slow and fast_ema > slow_ema:
                order_type = OrderType.BUY
                self.tracker.update(trend="bullish", snooze=self.interval or self.htf.seconds, order_type=OrderType.BUY)
                logger.info(f"🟢 BUY (HTF Bullish + LTF Cross)")
            
            # 🔴 SELL: HTF bearish + LTF death cross
            elif htf_trend == "bearish" and prev_fast >= prev_slow and fast_ema < slow_ema:
                order_type = OrderType.SELL
                self.tracker.update(trend="bearish", snooze=self.interval or self.htf.seconds, order_type=OrderType.SELL)
                logger.info(f"🔴 SELL (HTF Bearish + LTF Cross)")
            
            else:
                self.tracker.update(trend="ranging", snooze=self.interval or self.ltf.seconds, order_type=None)
                
        except Exception as err:
            logger.error(f"{err}. Failed to check trend")
            self.tracker.update(trend="ranging", snooze=self.interval or self.ltf.seconds, order_type=None)


    async def trade(self):
        try:
            # Debug 1: Trước khi check trend
            logger.info(f"🔄 Starting trade cycle for {self.symbol.name}")
            
            await self.check_trend()
            
            # Debug 2: Sau khi check trend
            logger.info(f"📊 After check_trend: order_type={self.tracker.order_type}, trend={self.tracker.trend}")
            
            if self.tracker.order_type is not None:
                logger.info(f"🎯 Attempting to place {self.tracker.order_type} trade...")
                
                # Debug 3: Kiểm tra trader
                if not hasattr(self, 'trader') or self.trader is None:
                    logger.error("❌ self.trader is None!")
                    return
                
                # Place trade
                result = await self.trader.place_trade(
                    order_type=self.tracker.order_type, 
                    parameters=self.parameters
                )
                
                logger.info(f"✅ Trade result: {result}")
                
                self.tracker.update(order_type=None)
                await self.sleep(secs=self.tracker.snooze)
            else:
                logger.info(f"⏸️ No trade signal, sleeping {self.tracker.snooze}s")
                await self.sleep(secs=self.tracker.snooze)
                
        except Exception as err:
            logger.error(f"❌ {err}. Failed to trade {self.symbol.name}", exc_info=True)  # ← Thêm exc_info