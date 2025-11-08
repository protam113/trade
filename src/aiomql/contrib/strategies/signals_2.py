# src/aiomql/contrib/strategies/signals_v2.py
import asyncio
import pandas as pd
import MetaTrader5 as mt5
from logging import getLogger
from datetime import date, datetime
from zoneinfo import ZoneInfo

from ...lib.strategy import Strategy
from ..symbols import ForexSymbol
from ..utils import Tracker
from ..utils.timezones import get_session_range
from ...core.constants import TimeFrame
from ...lib.noti import TelegramNotifier

logger = getLogger(__name__)

"""
Signals_V2: Real-time NYC Session High/Low Monitor

- 9:30 ET: Start tracking session High/Low
- Before 12:00 ET: Update High/Low if price breaks
- After 12:00 ET: Lock High/Low, alert on retest
- Send Telegram alerts on:
    • New High/Low (before noon)
    • Retest of High/Low (after noon)
- No trading — alert only
"""

NYC_TZ = ZoneInfo("America/New_York")
SESSION_START = 9 * 3600 + 30 * 60  # 9:30 ET in seconds
NOON_ET = 12 * 3600  # 12:00 ET in seconds


class Signals_V2(Strategy):
    tracker: Tracker
    notifier: TelegramNotifier
    last_sent_date: date = None

    # Session state
    session_high: float = None
    session_low: float = None
    session_date: date = None
    locked: bool = False  # Lock after 12:00 ET
    alerted_high: bool = False
    alerted_low: bool = False

    parameters = {
        "telegram_enabled": True,
        "min_candles": 30,
        "session": "NYC"
    }

    def __init__(self, *, symbol: ForexSymbol, params: dict = None, sessions=None, name="Signals_V2"):
        super().__init__(symbol=symbol, params=params, sessions=sessions, name=name)
        self.tracker = Tracker(snooze=60)  # Check every minute
        self.min_candles = params.get("min_candles", 30) if params else 30

        telegram_enabled = params.get("telegram_enabled", True) if params else True
        if telegram_enabled:
            try:
                self.notifier = TelegramNotifier(silent=False)
                logger.info(f"Signals_V2: Telegram ready for {symbol.name}")
            except Exception as e:
                logger.warning(f"Telegram failed: {e}")
                self.notifier = None
        else:
            self.notifier = None

    async def get_current_price(self) -> float:
        tick = mt5.symbol_info_tick(self.symbol.name)
        return tick.bid if tick else None

    async def start_new_session(self, now_nyc: datetime):
        self.session_date = now_nyc.date()
        self.session_high = None
        self.session_low = None
        self.locked = False
        self.alerted_high = False
        self.alerted_low = False
        logger.info(f"NYC Session started: {self.session_date}")

    async def update_session_range(self, df: pd.DataFrame):
        session_data = get_session_range(df, "NYC")
        if not session_data:
            return

        high = session_data["high"]
        low = session_data["low"]
        candles = session_data["candles"]

        now_nyc = datetime.now(NYC_TZ)
        seconds_since_open = (now_nyc.hour * 3600 + now_nyc.minute * 60 + now_nyc.second)

        # First candle of session
        if self.session_high is None:
            self.session_high = high
            self.session_low = low
            await self.send_alert(f"NYC SESSION OPEN\nHigh: {high:.5f}\nLow: {low:.5f}")
            return

        # Before noon: update High/Low
        if seconds_since_open < NOON_ET and candles >= 1:
            updated = False
            if high > self.session_high:
                self.session_high = high
                updated = True
                await self.send_alert(f"NEW SESSION HIGH\n{high:.5f} @ {now_nyc.strftime('%H:%M ET')}")
            if low < self.session_low:
                self.session_low = low
                updated = True
                await self.send_alert(f"NEW SESSION LOW\n{low:.5f} @ {now_nyc.strftime('%H:%M ET')}")
            if updated:
                logger.info(f"Updated: H={self.session_high}, L={self.session_low}")

        # At noon: lock High/Low
        if not self.locked and seconds_since_open >= NOON_ET:
            self.locked = True
            await self.send_alert(
                f"NYC HIGH/LOW LOCKED @ 12:00 ET\n"
                f"High: {self.session_high:.5f}\n"
                f"Low: {self.session_low:.5f}\n"
                f"Range: {(self.session_high - self.session_low)*10000:.1f} pips"
            )

    async def check_retest(self, price: float):
        if not self.locked or price is None:
            return

        tolerance = 0.00005  # 0.5 pip
        if abs(price - self.session_high) <= tolerance and not self.alerted_high:
            self.alerted_high = True
            await self.send_alert(f"RETEST SESSION HIGH\n{price:.5f}")
        elif abs(price - self.session_low) <= tolerance and not self.alerted_low:
            self.alerted_low = True
            await self.send_alert(f"RETEST SESSION LOW\n{price:.5f}")

    async def send_alert(self, message: str):
        full_msg = f"{message}\nSymbol: {self.symbol.name}\nSession: {self.session_date}"

        # ✅ In ra console luôn cho dễ debug
        print(f"🔔 {message.replace(chr(10), ' | ')}")

        if not self.notifier:
            return
        self.notifier.send_plain(full_msg)
        logger.info(f"Alert sent: {message.split()[0]}")


    async def trade(self):
        try:
            # Get latest M5 data
            rates = mt5.copy_rates_from_pos(self.symbol.name, TimeFrame.M5.value, 0, 1000)
            if rates is None or len(rates) == 0:
                await asyncio.sleep(60)
                return

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)

            now_nyc = datetime.now(NYC_TZ)
            today_nyc = now_nyc.date()

            # New session?
            if self.session_date != today_nyc and now_nyc.hour >= 9 and now_nyc.minute >= 30:
                await self.start_new_session(now_nyc)

            # Update session range
            await self.update_session_range(df)

            # Check retest
            current_price = await self.get_current_price()
            await self.check_retest(current_price)

            await asyncio.sleep(60)  # Check every minute

        except Exception as e:
            logger.error(f"Signals_V2 Error: {e}")
            await asyncio.sleep(60)

    async def trade_backtest(self, target_date: datetime):
        from datetime import timedelta
        rates = mt5.copy_rates_range(
            self.symbol.name,
            TimeFrame.M5.value,
            target_date.replace(hour=0, minute=0, second=0),
            target_date.replace(hour=23, minute=59, second=59),
        )

        # ✅ Fix lỗi check array
        if rates is None or len(rates) == 0:
            print("❌ No data found for that date.")
            return

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        await self.start_new_session(target_date)
        await self.update_session_range(df)

        print(f"✅ Backtest done for {target_date.date()} | High={self.session_high} | Low={self.session_low}")

    async def trade_backtest_v2(self, target_date: datetime):
        from datetime import timedelta

        rates = mt5.copy_rates_range(
            self.symbol.name,
            TimeFrame.M5.value,
            target_date.replace(hour=0, minute=0, second=0),
            target_date.replace(hour=23, minute=59, second=59),
        )

        if rates is None or len(rates) == 0:
            print("❌ No data found for that date.")
            return
        
        # ✅ Tạo DataFrame trước khi xử lý
        df = pd.DataFrame(rates)

        # --- convert time từ giờ server (GMT+2) về giờ New York ---
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df["time"] = df["time"].dt.tz_convert("America/New_York")
        df.set_index("time", inplace=True)

        # Bắt đầu session
        await self.start_new_session(target_date)
        print(f"▶️ Simulating {target_date.date()} ({len(df)} candles)")

        # Giả lập từng candle
        for idx, (t, row) in enumerate(df.iterrows()):
            now_nyc = t  # đã có timezone chuẩn
            df_slice = df.loc[:t]

            # Cập nhật high/low theo thời điểm hiện tại
            await self.update_session_range(df_slice)

            # Giả lập giá hiện tại = close
            price = float(row["close"])
            await self.check_retest(price)

            # Log progress mỗi 30 cây
            if idx % 30 == 0:
                h = f"{self.session_high:.5f}" if self.session_high is not None else "N/A"
                l = f"{self.session_low:.5f}" if self.session_low is not None else "N/A"
                print(f"[{t.strftime('%H:%M')}] price={price:.5f}  H={h}  L={l}")

            # Giả lập nhanh: 0.05s = 1 candle
            await asyncio.sleep(0.05)

        print(f"✅ Simulation completed for {target_date.date()} | Final H={self.session_high} L={self.session_low}")
