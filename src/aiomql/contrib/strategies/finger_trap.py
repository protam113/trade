import logging

from ..symbols import ForexSymbol
from ...lib.trader import Trader
from ...lib.candle import Candles
from ...lib.strategy import Strategy
from ...core.constants import TimeFrame, OrderType
from ...lib.sessions import Sessions
from ..candle_patterns import find_bearish_fractal, find_bullish_fractal
from ..traders import SimpleTrader
from ..utils import Tracker

logger = logging.getLogger(__name__)


class FingerTrap(Strategy):
    ttf: TimeFrame
    etf: TimeFrame
    fast_ema: int
    slow_ema: int
    entry_ema: int
    ecc: int
    tcc: int
    trader: Trader
    tracker: Tracker

    parameters = {"fast_ema": 8, "slow_ema": 20, "etf": TimeFrame.M5, "ttf": TimeFrame.H1,
                  "entry_ema": 5, "tcc": 720, "ecc": 8640}

    def __init__(self, *, symbol: ForexSymbol, params: dict | None = None, trader: Trader = None, sessions: Sessions = None,
                 name: str = "FingerTrap"):
        super().__init__(symbol=symbol, params=params, sessions=sessions, name=name)
        self.trader = trader or SimpleTrader(symbol=self.symbol)
        self.tracker: Tracker = Tracker(snooze=self.ttf.seconds)

    async def check_trend(self):
        try:
            candles: Candles = await self.symbol.copy_rates_from_pos(timeframe=self.ttf, count=self.tcc)
            if (current := candles[-1]) and current.time < self.tracker.trend_time:
                self.tracker.update(new=False, order_type=None)
                return

            self.tracker.update(new=True, trend_time=current.time, last_trend_price=current.close)
            candles.ta.ema(length=self.slow_ema, append=True, fillna=0)
            candles.ta.ema(length=self.fast_ema, append=True, fillna=0)
            candles.rename(inplace=True, **{f"EMA_{self.fast_ema}": "fast", f"EMA_{self.slow_ema}": "slow"})

            fas = candles.ta_lib.above(candles.fast, candles.slow)
            fbs = candles.ta_lib.below(candles.fast, candles.slow)
            caf = candles.ta_lib.above(candles.close, candles.fast)
            cbf = candles.ta_lib.below(candles.close, candles.fast)

            if fas.iloc[-1] and caf.iloc[-1]:
                self.tracker.update(trend="bullish")

            elif fbs.iloc[-1] and cbf.iloc[-1]:
                self.tracker.update(trend="bearish")

            else:
                self.tracker.update(trend="ranging", snooze=self.ttf.seconds, order_type=None)
        except Exception as err:
            logger.error(f"{err} for {self.symbol} in {self.__class__.__name__}.check_trend")
            self.tracker.update(snooze=self.ttf.seconds, order_type=None)

    async def confirm_trend(self):
        try:
            candles = await self.symbol.copy_rates_from_pos(timeframe=self.etf, count=self.ecc)
            if (current := candles[-1]) and current.time < self.tracker.entry_time:
                self.tracker.update(new=False, order_type=None)
                return

            self.tracker.update(new=True, entry_time=current.time, last_entry_price=current.close)
            candles.ta.ema(length=self.entry_ema, append=True)
            candles.rename(**{f"EMA_{self.entry_ema}": "ema"})
            candles["cae"] = candles.ta_lib.cross(candles.close, candles.ema)
            candles["cbe"] = candles.ta_lib.cross(candles.close, candles.ema, above=False)
            current = candles[-1]

            if self.tracker.bullish and current.cae:
                sl = find_bullish_fractal(candles).low
                self.tracker.update(snooze=self.ttf.seconds, order_type=OrderType.BUY, sl=sl)
            elif self.tracker.bearish and current.cbe:
                sl = find_bearish_fractal(candles).high
                self.tracker.update(snooze=self.ttf.seconds, order_type=OrderType.SELL, sl=sl)
            else:
                self.tracker.update(snooze=self.etf.seconds, order_type=None)
        except Exception as err:
            logger.error(f"{err} for {self.symbol} in {self.__class__.__name__}.confirm_trend")
            self.tracker.update(snooze=self.etf.seconds, order_type=None)

    async def watch_market(self):
        await self.check_trend()
        if self.tracker.ranging is False:
            await self.confirm_trend()

    async def trade(self):
        try:
            await self.watch_market()

            # Không có tín hiệu mới - bỏ qua
            if not self.tracker.new:
                return None

            # Nếu có tín hiệu trade
            if self.tracker.order_type:
                entry_price = self.tracker.last_entry_price or 1.0
                sl = self.tracker.sl or 0

                # Log giao dịch
                logger.info(
                    f"📈 [{self.tracker.order_type.name}] {self.symbol.name} | "
                    f"Time: {self.tracker.entry_time} | Price: {entry_price:.5f} | SL: {sl:.5f}"
                )
                
                # Trả về signal cho backtest
                return {
                    "type": self.tracker.order_type.name,
                    "symbol": self.symbol.name,
                    "time": self.tracker.entry_time,
                    "price": entry_price,
                    "sl": sl
                }
            
            return None

        except Exception as err:
            logger.error(f"{err} For {self.symbol} in {self.__class__.__name__}.trade")
            return None

    async def on_tick(self, tick):
        signal = await self.trade()
        return signal

    async def sleep(self, secs: float = None):
        """Custom sleep cho phép truyền thời gian."""
        import asyncio
        if secs is not None:
            await asyncio.sleep(secs)
        else:
            await asyncio.sleep(1)