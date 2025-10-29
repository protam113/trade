# mt5_realtime_logger.py
# Yêu cầu: pip install MetaTrader5
# Chú ý: MetaTrader 5 terminal phải chạy và (nếu cần) đã login.

import time
import logging
import sys
from datetime import datetime
import MetaTrader5 as mt5

# -------- CONFIG --------
SYMBOL = "EURUSD"            # đổi thành cặp bạn muốn
POLL_INTERVAL = 0.1          # giây giữa các poll (0.05-0.2 phổ biến)
LOG_FILE = "mt5_ticks.log"
MT5_PATH = None              # nếu cần, để đường dẫn terminal64.exe, ví dụ r"C:\Program Files\MetaTrader 5\terminal64.exe"
LOGIN = None                 # nếu muốn login tự động: số tài khoản (int) hoặc None để dùng session hiện có
PASSWORD = None              # mật khẩu (string) nếu đặt LOGIN
SERVER = None                # server name nếu cần
# -------------------------

def setup_logging():
    logger = logging.getLogger("mt5logger")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    # console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    # file handler (append)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger

def mt5_init(logger):
    # Init MT5, trả về True nếu ok
    init_kwargs = {}
    if MT5_PATH:
        init_kwargs["path"] = MT5_PATH
    if LOGIN:
        init_kwargs["login"] = LOGIN
    if PASSWORD:
        init_kwargs["password"] = PASSWORD
    if SERVER:
        init_kwargs["server"] = SERVER

    ok = mt5.initialize(**init_kwargs) if init_kwargs else mt5.initialize()
    if not ok:
        logger.error(f"MT5 initialize() failed, error={mt5.last_error()}")
        return False
    logger.info("MT5 initialized.")
    return True

def ensure_symbol(symbol, logger):
    info = mt5.symbol_info(symbol)
    if info is None:
        logger.error(f"Symbol {symbol} not found in MT5.")
        return False
    # add to Market Watch if not already
    if not info.visible:
        added = mt5.symbol_select(symbol, True)
        if not added:
            logger.warning(f"Không thể thêm {symbol} vào Market Watch.")
        else:
            logger.info(f"Đã thêm {symbol} vào Market Watch.")
    return True

def format_tick(tick):
    # tick: object returned từ mt5.symbol_info_tick
    # convert time (int) -> ISO
    t = datetime.fromtimestamp(tick.time) if hasattr(tick, "time") else None
    return {
        "time": t.isoformat(sep=" ") if t else None,
        "bid": getattr(tick, "bid", None),
        "ask": getattr(tick, "ask", None),
        "last": getattr(tick, "last", None),
        "volume": getattr(tick, "volume", None),
        "flags": getattr(tick, "flags", None),
        "time_msc": getattr(tick, "time_msc", None),
    }

def realtime_logger(symbol, poll_interval, logger):
    logger.info(f"Start logging ticks for {symbol} (interval {poll_interval}s). Ctrl-C to stop.")
    last_seen = None
    while True:
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                # nếu có lỗi thì log và cố reconnect nếu cần
                err = mt5.last_error()
                logger.debug(f"symbol_info_tick returned None. last_error: {err}")
                # cố reconnect đơn giản
                time.sleep(0.5)
            else:
                # detect new tick by time_msc or time
                time_id = getattr(tick, "time_msc", getattr(tick, "time", None))
                if time_id != last_seen:
                    last_seen = time_id
                    d = format_tick(tick)
                    # custom message
                    msg = f"{symbol} | time={d['time']} | bid={d['bid']} | ask={d['ask']} | last={d['last']} | vol={d['volume']}"
                    logger.info(msg)
                # else: same tick, skip printing (reduces spam)
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received — stopping realtime logger.")
            break
        except Exception as e:
            logger.exception("Unexpected error in realtime loop:")
            # cố chờ rồi tiếp tục
            time.sleep(1)

def main():
    logger = setup_logging()
    if not mt5_init(logger):
        logger.error("Không thể khởi tạo MT5. Kiểm tra terminal đang chạy và kết nối.")
        return
    if not ensure_symbol(SYMBOL, logger):
        logger.error("Symbol chưa sẵn sàng. Thoát.")
        mt5.shutdown()
        return
    try:
        realtime_logger(SYMBOL, POLL_INTERVAL, logger)
    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown complete.")

if __name__ == "__main__":
    main()
