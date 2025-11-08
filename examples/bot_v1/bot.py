import os
import sys
import logging
from logging.handlers import RotatingFileHandler
import asyncio
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import json
import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import queue

# --- Setup path ---
ROOT = os.path.join(os.path.dirname(__file__), "../..", "src")
ROOT = os.path.abspath(ROOT)
sys.path.append(ROOT)

# --- Load environment variables ---
load_dotenv()

# --- Imports ---
import MetaTrader5 as mt5
from aiomql.lib.bot import Bot
from aiomql.contrib.symbols import ForexSymbol
from aiomql.contrib.strategies import MACD_Strategy


# ============================================
# [GUI] Custom Log Handler
# ============================================
class QueueHandler(logging.Handler):
    """Handler để gửi logs vào queue cho GUI"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


# ============================================
# [GUI] Main Window - Chạy trong thread riêng
# ============================================
class BotGUI:
    def __init__(self, log_queue, control_queue):
        self.log_queue = log_queue
        self.control_queue = control_queue
        self.root = None
        self.is_bot_running = False
        
    def run(self):
        """Chạy GUI trong thread riêng"""
        self.root = tk.Tk()
        self.root.title("🤖 MT5 MACD Trading Bot - Real-time Logs")
        self.root.geometry("1200x700")
        self.root.configure(bg='#1e1e1e')
        
        self.setup_ui()
        self.update_logs()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Header Frame
        header_frame = tk.Frame(self.root, bg='#2d2d2d', height=60)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(
            header_frame, 
            text="📊 MT5 Multi-Symbol MACD Trading Bot",
            font=('Arial', 16, 'bold'),
            bg='#2d2d2d',
            fg='#00ff00'
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Status indicator
        self.status_label = tk.Label(
            header_frame,
            text="🟢 RUNNING",
            font=('Arial', 12, 'bold'),
            bg='#2d2d2d',
            fg='#00ff00'
        )
        self.status_label.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # Control Frame
        control_frame = tk.Frame(self.root, bg='#2d2d2d', height=50)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        control_frame.pack_propagate(False)
        
        # Stop Button
        self.stop_btn = tk.Button(
            control_frame,
            text="⏹️ STOP BOT",
            command=self.stop_bot,
            bg='#f44336',
            fg='white',
            font=('Arial', 11, 'bold'),
            width=15,
            height=1,
            relief=tk.RAISED,
            cursor='hand2'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10, pady=8)
        
        # Clear Button
        clear_btn = tk.Button(
            control_frame,
            text="🗑️ CLEAR LOGS",
            command=self.clear_logs,
            bg='#607D8B',
            fg='white',
            font=('Arial', 11, 'bold'),
            width=15,
            height=1,
            relief=tk.RAISED,
            cursor='hand2'
        )
        clear_btn.pack(side=tk.LEFT, padx=10, pady=8)
        
        # Info labels
        self.info_frame = tk.Frame(control_frame, bg='#2d2d2d')
        self.info_frame.pack(side=tk.RIGHT, padx=20)
        
        self.balance_label = tk.Label(
            self.info_frame,
            text="Balance: --",
            font=('Arial', 10),
            bg='#2d2d2d',
            fg='#ffeb3b'
        )
        self.balance_label.pack(side=tk.LEFT, padx=10)
        
        self.equity_label = tk.Label(
            self.info_frame,
            text="Equity: --",
            font=('Arial', 10),
            bg='#2d2d2d',
            fg='#03a9f4'
        )
        self.equity_label.pack(side=tk.LEFT, padx=10)
        
        self.profit_label = tk.Label(
            self.info_frame,
            text="Profit: --",
            font=('Arial', 10),
            bg='#2d2d2d',
            fg='#4caf50'
        )
        self.profit_label.pack(side=tk.LEFT, padx=10)
        
        # Log Frame
        log_frame = tk.Frame(self.root, bg='#1e1e1e')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ScrolledText for logs
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg='#0d1117',
            fg='#c9d1d9',
            insertbackground='white',
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for colored logs
        self.log_text.tag_config('INFO', foreground='#58a6ff')
        self.log_text.tag_config('WARNING', foreground='#f0883e')
        self.log_text.tag_config('ERROR', foreground='#f85149')
        self.log_text.tag_config('DEBUG', foreground='#8b949e')
        self.log_text.tag_config('SUCCESS', foreground='#3fb950')
        
    def add_log(self, message):
        """Thêm log vào text widget với màu sắc"""
        self.log_text.config(state=tk.NORMAL)
        
        # Determine log level and color
        if 'ERROR' in message or '❌' in message:
            tag = 'ERROR'
        elif 'WARNING' in message or '⚠️' in message:
            tag = 'WARNING'
        elif 'DEBUG' in message:
            tag = 'DEBUG'
        elif '✅' in message or 'SUCCESS' in message:
            tag = 'SUCCESS'
        else:
            tag = 'INFO'
        
        self.log_text.insert(tk.END, message + '\n', tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def update_logs(self):
        """Update logs từ queue"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                
                # Check for special messages
                if isinstance(message, dict):
                    if 'balance' in message:
                        self.balance_label.config(text=f"Balance: ${message['balance']:.2f}")
                    if 'equity' in message:
                        self.equity_label.config(text=f"Equity: ${message['equity']:.2f}")
                    if 'profit' in message:
                        profit = message['profit']
                        color = '#4caf50' if profit >= 0 else '#f44336'
                        self.profit_label.config(
                            text=f"Profit: ${profit:.2f}",
                            fg=color
                        )
                else:
                    self.add_log(message)
        except queue.Empty:
            pass
        finally:
            if self.root:
                self.root.after(100, self.update_logs)
    
    def clear_logs(self):
        """Xóa tất cả logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def stop_bot(self):
        """Gửi lệnh stop bot"""
        self.control_queue.put("STOP")
        self.status_label.config(text="🟡 STOPPING...", fg='#ffeb3b')
        self.stop_btn.config(state=tk.DISABLED)
        self.add_log("=" * 80)
        self.add_log("⏹️ Sending stop signal to bot...")
        self.add_log("=" * 80)
    
    def on_closing(self):
        """Xử lý khi đóng window"""
        self.control_queue.put("STOP")
        if self.root:
            self.root.destroy()


# ============================================
# [1] Load Configuration
# ============================================
def load_config(config_path="config.json", log_queue=None) -> dict:
    """Load configuration from JSON file"""
    if not os.path.exists(config_path):
        msg = f"❌ Không tìm thấy file config: {config_path}"
        if log_queue:
            log_queue.put(msg)
        raise FileNotFoundError(msg)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    msg = f"✅ Loaded configuration from {config_path}"
    if log_queue:
        log_queue.put(msg)
    return config


# ============================================
# [2] Setup Logging
# ============================================
def setup_logging(config: dict, log_queue):
    """Setup logging với GUI queue handler"""
    log_config = config.get("logging", {})
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_config.get("level", "INFO")))
    
    # Clear existing handlers
    logger.handlers.clear()

    # GUI Queue handler
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(getattr(logging, log_config.get("level", "INFO")))
    
    # File handler
    file_handler = RotatingFileHandler(
        log_config.get("file", "bot_logs.log"),
        maxBytes=log_config.get("max_bytes", 10*1024*1024),
        backupCount=log_config.get("backup_count", 5),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    queue_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(queue_handler)
    logger.addHandler(file_handler)


# ============================================
# [3] Load Symbols from JSON
# ============================================
def load_symbols_from_json(file_path="symbols.json", log_queue=None) -> list:
    """Đọc danh sách symbols từ file JSON"""
    if not os.path.exists(file_path):
        msg = f"❌ Không tìm thấy file {file_path}"
        if log_queue:
            log_queue.put(msg)
        raise FileNotFoundError(msg)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    valid_data = [item for item in data if "symbol" in item and "spread" in item]
    sorted_data = sorted(valid_data, key=lambda x: x.get("spread", float("inf")))
    symbols = [item["symbol"] for item in sorted_data]

    if log_queue:
        log_queue.put(f"✅ Loaded {len(symbols)} symbols from {file_path}")
        for s in sorted_data[:5]:
            log_queue.put(f"  • {s['symbol']} (spread={s['spread']})")

    return symbols


# ============================================
# [4] MT5 Environment Test
# ============================================
def check_mt5_env(config: dict, log_queue=None):
    """Check MT5 connection"""
    mt5_config = config.get("mt5", {})
    
    if log_queue:
        log_queue.put("🔍 Checking MetaTrader 5 environment...")

    login = int(os.getenv("MT5_ACCOUNT", mt5_config.get("login")))
    password = os.getenv("MT5_PASSWORD", mt5_config.get("password"))
    server = os.getenv("MT5_SERVER", mt5_config.get("server"))
    path = os.getenv("MT5_PATH", mt5_config.get("path"))

    if not os.path.exists(path):
        msg = f"❌ Không tìm thấy terminal: {path}"
        if log_queue:
            log_queue.put(msg)
        raise FileNotFoundError(msg)

    if not mt5.initialize(path=path, login=login, password=password, server=server):
        msg = f"❌ MT5 initialize() failed: {mt5.last_error()}"
        if log_queue:
            log_queue.put(msg)
        raise RuntimeError(msg)
    else:
        if log_queue:
            log_queue.put("✅ Connected to MetaTrader5 Terminal")

    account_info = mt5.account_info()
    if account_info is None:
        msg = "❌ Không thể lấy thông tin tài khoản"
        if log_queue:
            log_queue.put(msg)
        raise RuntimeError(msg)
    
    if log_queue:
        log_queue.put(f"✅ Logged in as: {account_info.login}, balance={account_info.balance}")

    terminal_info = mt5.terminal_info()
    if not terminal_info.trade_allowed:
        msg = "⚠️ AutoTrading đang bị tắt trong MT5!"
        if log_queue:
            log_queue.put(msg)
        raise PermissionError(msg)

    if log_queue:
        log_queue.put("✅ AutoTrading ENABLED")
        log_queue.put("✅ Environment OK!")
    
    return {"login": login, "password": password, "server": server, "path": path}


# ============================================
# [5] Load and check symbols
# ============================================
def load_symbols(symbols: list, log_queue=None) -> list:
    """Load và kiểm tra các symbols"""
    loaded_symbols = []
    failed_symbols = []

    if log_queue:
        log_queue.put(f"📦 Loading {len(symbols)} symbols...")

    for symbol in symbols:
        if mt5.symbol_select(symbol, True):
            info = mt5.symbol_info(symbol)
            if (info is not None and 
                info.visible and 
                info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED):
                loaded_symbols.append(symbol)
                if log_queue:
                    log_queue.put(f"  ✅ {symbol} - Ready (spread={info.spread})")
            else:
                failed_symbols.append(symbol)
                if log_queue:
                    log_queue.put(f"  ⚠️ {symbol} - Not tradeable")
        else:
            failed_symbols.append(symbol)
            if log_queue:
                log_queue.put(f"  ❌ {symbol} - Failed to select")

    if log_queue:
        log_queue.put(f"✅ Loaded: {len(loaded_symbols)}/{len(symbols)} symbols")

    return loaded_symbols


# ============================================
# [6] Check market open
# ============================================
def is_market_open() -> bool:
    """Kiểm tra thị trường có mở không"""
    now = datetime.now()
    if now.weekday() == 5:
        return False
    if now.weekday() == 6 and now.hour < 22:
        return False
    return True


# ============================================
# [7] Background monitoring
# ============================================
async def monitor_bot(config: dict, log_queue, control_queue):
    """Background monitoring với stop signal"""
    interval = config.get("monitoring", {}).get("interval_seconds", 300)
    
    while True:
        # Check for stop signal
        try:
            cmd = control_queue.get_nowait()
            if cmd == "STOP":
                logging.info("🛑 Received stop signal")
                log_queue.put("🛑 Bot stopping...")
                break
        except queue.Empty:
            pass
        
        await asyncio.sleep(min(interval, 5))
        
        if is_market_open():
            account = mt5.account_info()
            if account:
                msg = f"🔄 Bot running | Balance: {account.balance} | Equity: {account.equity} | Profit: {account.profit}"
                logging.info(msg)
                
                # Update GUI account info
                log_queue.put({
                    'balance': account.balance,
                    'equity': account.equity,
                    'profit': account.profit
                })
            else:
                logging.warning("⚠️ Cannot get account info")
        else:
            logging.info("⏸️ Market closed - bot paused")


# ============================================
# [8] Bot runs in MAIN thread
# ============================================
def run_realtime_bot(log_queue, control_queue):
    """Main bot execution - chạy trong MAIN thread"""
    try:
        log_queue.put("=" * 80)
        log_queue.put("🚀 BOT STARTING...")
        log_queue.put("=" * 80)
        
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        config = load_config(config_path, log_queue)
        
        setup_logging(config, log_queue)
        mt5_credentials = check_mt5_env(config, log_queue)
        
        symbols_path = os.path.join(os.path.dirname(__file__), "symbols.json")
        symbols_list = load_symbols_from_json(symbols_path, log_queue)
        loaded_symbols = load_symbols(symbols_list, log_queue)

        if not loaded_symbols:
            raise RuntimeError("❌ Không có symbol nào được load!")

        strategies = []
        for symbol in loaded_symbols:
            try:
                symbol_obj = ForexSymbol(name=symbol)
                strategy = MACD_Strategy(symbol=symbol_obj, config=config)
                strategies.append(strategy)
                logging.info(f"[ADD] Added MACD strategy for {symbol}")
            except Exception as e:
                logging.error(f"⚠️ Failed to create strategy for {symbol}: {e}")

        if not strategies:
            raise RuntimeError("❌ Không có strategy nào!")

        log_queue.put(f"✅ Total MACD strategies: {len(strategies)}")

        bot = Bot()
        bot.config.login = mt5_credentials["login"]
        bot.config.password = mt5_credentials["password"]
        bot.config.server = mt5_credentials["server"]

        executor_timeout = config.get("strategy", {}).get("execution", {}).get("timeout", 60)
        bot.executor.timeout = executor_timeout

        # Add monitor với control queue
        bot.add_coroutine(coroutine=lambda: monitor_bot(config, log_queue, control_queue))
        bot.add_strategies(strategies=strategies)

        log_queue.put("🚀 Bot executing with MACD multi-symbol trading...")
        logging.info(f"MACD Bot started with {len(strategies)} strategies")
        
        # Execute bot
        bot.execute()
        
    except KeyboardInterrupt:
        log_queue.put("⚠️ Bot stopped by user (Ctrl+C)")
        logging.info("Bot stopped by user")
    except Exception as e:
        log_queue.put(f"❌ Bot crashed: {e}")
        logging.error(f"Bot error: {e}", exc_info=True)
    finally:
        mt5.shutdown()
        log_queue.put("🛑 MetaTrader5 connection closed")
        log_queue.put("=" * 80)
        log_queue.put("✅ BOT SHUTDOWN COMPLETED")
        log_queue.put("=" * 80)
        logging.info("Bot shutdown completed")


# ============================================
# [9] MAIN ENTRY
# ============================================
if __name__ == "__main__":
    # Create queues
    log_queue = queue.Queue()
    control_queue = queue.Queue()
    
    # Create GUI instance
    gui = BotGUI(log_queue, control_queue)
    
    # Start GUI in separate thread
    gui_thread = threading.Thread(target=gui.run, daemon=True)
    gui_thread.start()
    
    # Wait a bit for GUI to initialize
    import time
    time.sleep(1)
    
    # Run bot in MAIN thread
    run_realtime_bot(log_queue, control_queue)