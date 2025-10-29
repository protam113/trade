import random
from logging import getLogger

from ...lib.strategy import Strategy
from ..symbols import ForexSymbol
from ..utils import Tracker
from ..utils.timezones import get_session_range
from ...core.constants import TimeFrame, OrderType
from ...lib.noti import TelegramNotifier
from datetime import date

logger = getLogger(__name__)


class Signals_V1(Strategy):
    """A strategy that detects and alerts trading signals without executing trades."""

    ltf: TimeFrame
    htf: TimeFrame
    lcc: int
    hcc: int
    fast_ema: int
    slow_ema: int
    tracker: Tracker
    interval: int
    notifier: TelegramNotifier
    
    parameters = {
        "fast_ema": 8, 
        "slow_ema": 20, 
        "ltf": TimeFrame.M1, 
        "htf": TimeFrame.M5, 
        "lcc": 100, 
        "hcc": 100,
        "interval": 0,
        "telegram_enabled": True  # Bật/tắt Telegram
    }

    def __init__(self, *, symbol: ForexSymbol, params: dict = None, sessions=None, name="Signals_V1"):
        super().__init__(symbol=symbol, params=params, sessions=sessions, name=name)
        self.tracker = Tracker(snooze=self.interval or self.ltf.seconds)
        
        # Khởi tạo Telegram notifier nếu được bật
        telegram_enabled = params.get("telegram_enabled", True) if params else True
        if telegram_enabled:
            try:
                self.notifier = TelegramNotifier(silent=False)
                logger.info(f"Telegram notifier initialized for {symbol.name}")
            except ValueError as e:
                logger.warning(f"Telegram not configured: {e}")
                self.notifier = None
        else:
            self.notifier = None

    async def check_trend(self):
        try:
            candles = await self.symbol.copy_rates_from_pos(timeframe=self.htf, count=self.hcc)
            if (
                (current := candles[-1])
                and current.time < self.tracker.trend_time
                and current.close == self.tracker.last_trend_price
            ):
                self.tracker.update(new=False, order_type=None, snooze=5)
                return
            
            self.tracker.update(new=True, trend_time=current.time, last_trend_price=current.close)
            candles.ta.ema(length=self.slow_ema, append=True, fillna=0)
            candles.ta.ema(length=self.fast_ema, append=True, fillna=0)
            candles.rename(inplace=True, **{f"EMA_{self.fast_ema}": "fast", f"EMA_{self.slow_ema}": "slow"})
            
            # Xác định tín hiệu (giữ nguyên logic cũ)
            order_type = random.choice([OrderType.BUY, OrderType.SELL])
            
            if order_type == OrderType.BUY:
                self.tracker.update(
                    trend="bullish", 
                    snooze=self.interval or self.htf.seconds, 
                    order_type=OrderType.BUY
                )
            else:
                self.tracker.update(
                    trend="bearish", 
                    snooze=self.interval or self.htf.seconds, 
                    order_type=OrderType.SELL
                )
        except Exception as err:
            logger.error(f"{err}. Failed to check trend")
            self.tracker.update(trend="ranging", snooze=self.interval or self.ltf.seconds, order_type=None)

    def send_signal_alert(self, order_type: OrderType, price: float):
        """Gửi thông báo tín hiệu qua Telegram và log"""
        signal_emoji = "🟢" if order_type == OrderType.BUY else "🔴"
        signal_type = "BUY" if order_type == OrderType.BUY else "SELL"
        
        # Log ra console
        logger.info(f"{signal_emoji} SIGNAL DETECTED: {self.symbol.name} - {signal_type} at {price}")
        
        # Gửi Telegram nếu có
        if self.notifier:
            message = f"{signal_emoji} SIGNAL DETECTED\n\n"
            message += f"Symbol: {self.symbol.name}\n"
            message += f"Strategy: {self.name}\n"
            message += f"Type: {signal_type}\n"
            message += f"Price: {price:.5f}\n"
            message += f"Trend: {self.tracker.trend}\n"
            message += f"Timeframe: {self.htf.name}\n"
            
            self.notifier.send_plain(message)

    async def trade(self):
        """Renamed to detect_signals - only detects and alerts, no trading"""
        try:
            await self.check_trend()
            
            if self.tracker.order_type is not None:
                # Lấy giá hiện tại
                current_price = await self.symbol.last_tick_price()
                
                # GỬI THÔNG BÁO thay vì vào lệnh
                self.send_signal_alert(
                    order_type=self.tracker.order_type,
                    price=current_price
                )
                
                # Reset order_type
                self.tracker.update(order_type=None)
                await self.sleep(secs=self.tracker.snooze)
            else:
                await self.sleep(secs=self.tracker.snooze)
                
        except Exception as err:
            logger.error(f"{err}. Failed to detect signal for {self.symbol.name} with {self.__class__.__name__}")

    async def detect_signals(self):
        """Alias method for clarity - this strategy only detects signals"""
        await self.trade()




    """
    Signals_V2: Gửi High & Low của PHIÊN MỸ (NYC) qua Telegram
    - Chỉ 1 lần mỗi phiên
    - Tự động DST
    - Không EMA, không random, không trade
    """

    tracker: Tracker
    notifier: TelegramNotifier
    last_sent_date: date = None  # Theo ngày New York

    parameters = {
        "telegram_enabled": True,
        "min_candles": 30,        # Đảm bảo phiên đã đóng (30 nến M5 = 2.5h)
        "session": "NYC"          # Chỉ NYC
    }

    def __init__(self, *, symbol: ForexSymbol, params: dict = None, sessions=None, name="Signals_V2"):
        super().__init__(symbol=symbol, params=params, sessions=sessions, name=name)
        
        self.tracker = Tracker(snooze=3600)  # Kiểm tra mỗi giờ
        self.min_candles = params.get("min_candles", 30) if params else 30

        # Telegram
        telegram_enabled = params.get("telegram_enabled", True) if params else True
        if telegram_enabled:
            try:
                self.notifier = TelegramNotifier(silent=False)
                logger.info(f"Signals_V2: Telegram ready for {symbol.name} - NYC Session")
            except Exception as e:
                logger.warning(f"Signals_V2: Telegram failed: {e}")
                self.notifier = None
        else:
            self.notifier = None

    async def get_nyc_range(self):
        """Lấy dữ liệu M5 và trả về NYC Session Range"""
        try:
            # Lấy 1000 nến M5 (~3-4 ngày)
            df = await self.symbol.copy_rates_from_pos(
                timeframe=TimeFrame.M5,
                count=1000
            )
            if df.empty:
                return None

            return get_session_range(df, "NYC")
        except Exception as e:
            logger.error(f"Signals_V2: Failed to get data - {e}")
            return None

    def format_telegram_message(self, data: dict):
        return (
            f"NYC SESSION RANGE\n\n"
            f"Symbol: {self.symbol.name}\n"
            f"Date: {data['date_local']}\n"
            f"High: {data['high']:.5f}\n"
            f"Low: {data['low']:.5f}\n"
            f"Range: {data['range']:.5f} ({data['range']/data['high']*10000:.1f} pips)\n"
            f"Candles: {data['candles']}\n"
            f"Timezone: {data['timezone']}"
        )

    async def send_nyc_range(self, data: dict):
        if not self.notifier:
            return

        message = self.format_telegram_message(data)
        self.notifier.send_plain(message)
        logger.info(f"Signals_V2: NYC Range sent for {self.symbol.name} on {data['date_local']}")

    async def trade(self):
        """
        Gọi định kỳ (mỗi giờ) → kiểm tra xem phiên NYC hôm qua đã đóng chưa
        """
        try:
            range_data = await self.get_nyc_range()
            if not range_data:
                await self.sleep(3600)
                return

            ny_date = range_data["date_local"]

            # Chỉ gửi 1 lần mỗi ngày (theo ngày New York)
            if self.last_sent_date == ny_date:
                await self.sleep(self.tracker.snooze_remaining() or 3600)
                return

            # Kiểm tra phiên đã đóng chưa
            if range_data["candles"] < self.min_candles:
                logger.info(f"Signals_V2: NYC session not closed yet ({range_data['candles']} candles)")
                await self.sleep(1800)  # Chờ 30 phút
                return

            # GỬI TELEGRAM
            await self.send_nyc_range(range_data)

            # Cập nhật
            self.last_sent_date = ny_date
            self.tracker.update(snooze=86400)  # Ngủ 24h

        except Exception as e:
            logger.error(f"Signals_V2: Error in trade loop - {e}")
            await self.sleep(3600)

    async def detect_nyc_range(self):
        """Alias để rõ nghĩa"""
        await self.trade()