import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "src")
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))



import pandas as pd
import pandas_ta as ta
from pyqtgraph.Qt import QtCore


# Import custom modules
from monitor import TradingMonitor
from strategy import TrendFollowingSellStrategy

class TradingBot:
    def __init__(self, data_path, config):
        """Initialize Trading Bot"""
        # Load and prepare data
        self.df = self._load_data(data_path)
        
        # Initialize modules
        self.monitor = TradingMonitor()
        self.strategy = TrendFollowingSellStrategy(config)
        
        # Trading state
        self.balance = config.get('initial_balance', 10000)
        self.initial_balance = self.balance
        self.max_balance = self.balance
        self.max_drawdown = 0
        
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_profit = 0
        
        self.ptr = 50
        self.speed = 1
        
        # Setup timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        
        # Connect buttons
        self._connect_buttons()
        
        # Initial logs
        self.monitor.log_event("✅ TREND-FOLLOWING SELL Strategy Loaded")
        self.monitor.log_event("📋 Entry: EMA8<21 + Price<EMA8 + Price<VWAP + RSI<50 + MACD<0")
        self.monitor.log_event("🎯 Exit: TP/SL or EMA8 crosses back above EMA21")
        self.monitor.log_event("▶ Press Start to begin backtest")
    
    def _load_data(self, data_path):
        """Load and calculate indicators"""
        df = pd.read_csv(data_path, sep=';')
        df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")
        print(f"📊 Data loaded: {len(df)} rows")
        
        df = df.set_index("time")
        
        # Calculate indicators
        print("🔧 Calculating indicators...")
        df["EMA8"] = ta.ema(close=df["close"], length=8)
        df["EMA21"] = ta.ema(close=df["close"], length=21)
        df["EMA50"] = ta.ema(close=df["close"], length=50)
        df["VWAP"] = ta.vwap(high=df["high"], low=df["low"], close=df["close"], 
                             volume=df["tick_volume"], anchor="D")
        df["ATR"] = ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)
        
        # Bollinger Bands
        bbands = ta.bbands(close=df["close"], length=20, std=2.0)
        if bbands is not None and len(bbands.columns) >= 3:
            df["BBU"] = bbands.iloc[:, 0]
            df["BBM"] = bbands.iloc[:, 1]
            df["BBL"] = bbands.iloc[:, 2]
        else:
            df["BBM"] = df["close"].rolling(window=20).mean()
            std = df["close"].rolling(window=20).std()
            df["BBU"] = df["BBM"] + (2.0 * std)
            df["BBL"] = df["BBM"] - (2.0 * std)
        
        # MACD
        macd_df = ta.macd(close=df["close"], fast=12, slow=26, signal=9)
        if macd_df is not None and len(macd_df.columns) >= 3:
            df["MACD"] = macd_df.iloc[:, 0]
            df["MACD_Hist"] = macd_df.iloc[:, 1]
            df["MACD_Signal"] = macd_df.iloc[:, 2]
        else:
            ema12 = df["close"].ewm(span=12).mean()
            ema26 = df["close"].ewm(span=26).mean()
            df["MACD"] = ema12 - ema26
            df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
            df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
        
        df["RSI"] = ta.rsi(close=df["close"], length=14)
        df["VOL_AVG"] = df["tick_volume"].rolling(window=20).mean()
        
        df = df.reset_index(drop=False)
        print("✅ Indicators calculated")
        
        return df
    
    def _connect_buttons(self):
        """Connect UI buttons"""
        for btn, factor in self.monitor.speed_buttons:
            btn.clicked.connect(lambda _, f=factor: self.set_speed(f))
        
        self.monitor.start_button.clicked.connect(self.start)
        self.monitor.stop_button.clicked.connect(self.stop)
        self.monitor.reset_button.clicked.connect(self.reset)
    
    def set_speed(self, factor):
        """Set simulation speed"""
        self.speed = factor
        self.monitor.log_event(f"⚡ Speed: {factor}x")
    
    def start(self):
        """Start backtest"""
        self.timer.start(50)
        self.monitor.log_event("▶ Backtest STARTED")
    
    def stop(self):
        """Stop backtest"""
        self.timer.stop()
        self.monitor.log_event("⏹ Backtest STOPPED")
    
    def reset(self):
        """Reset simulation"""
        self.ptr = 50
        self.balance = self.initial_balance
        self.max_balance = self.initial_balance
        self.max_drawdown = 0
        
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_profit = 0
        
        self.strategy.reset()
        self.monitor.clear_markers()
        self.monitor.logs = []
        
        self.monitor.log_event("🔄 Simulation RESET")
        self._update_labels()
    
    def update(self):
        """Main update loop"""
        for _ in range(self.speed):
            if self.ptr >= len(self.df):
                self._finish_backtest()
                return
            
            self._process_bar()
            self.ptr += 1
    
    def _process_bar(self):
        """Process one bar"""
        current_bar = self.df.iloc[self.ptr]
        price_now = current_bar['close']
        high_now = current_bar['high']
        low_now = current_bar['low']
        
        # Update charts
        sliced = self.df.iloc[:self.ptr+1]
        self.monitor.update_charts(sliced)
        
        # Update balance tracking
        if self.balance > self.max_balance:
            self.max_balance = self.balance
        drawdown = self.max_balance - self.balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # Get indicators
        indicators = {
            'ema8': current_bar['EMA8'],
            'ema21': current_bar['EMA21'],
            'ema50': current_bar['EMA50'],
            'price': price_now,
            'vwap': current_bar['VWAP'],
            'rsi': current_bar['RSI'],
            'macd_hist': current_bar['MACD_Hist'],
            'atr': current_bar['ATR']
        }
        
        # Check exit
        if self.ptr > 0:
            prev_bar = self.df.iloc[self.ptr-1]
            exit_data = {
                'high': high_now,
                'low': low_now,
                'close': price_now,
                'ema8': current_bar['EMA8'],
                'ema21': current_bar['EMA21'],
                'ema8_prev': prev_bar['EMA8'],
                'ema21_prev': prev_bar['EMA21']
            }
            
            should_exit, reason, exit_price, profit = self.strategy.check_exit_signal(exit_data)
            
            if should_exit:
                self._execute_exit(exit_price, profit, reason)
        
        # Check entry
        has_signal, entry_info = self.strategy.check_entry_signal(indicators)
        
        if has_signal:
            self._execute_entry(entry_info)
        
        # Update labels
        strategy_status = self.strategy.get_debug_status(indicators)
        self._update_labels(strategy_status)
    
    def _execute_entry(self, entry_info):
        """Execute entry"""
        self.monitor.add_entry_marker(self.ptr, entry_info['entry'])
        self.monitor.log_event(
            f"🔴 SELL @ {entry_info['entry']:.5f} | "
            f"SL: {entry_info['sl']:.5f} | "
            f"TP: {entry_info['tp']:.5f}"
        )
    
    def _execute_exit(self, exit_price, profit, reason):
        """Execute exit"""
        self.balance += profit
        self.total_profit += profit
        self.total_trades += 1
        
        if profit > 0:
            self.wins += 1
        else:
            self.losses += 1
        
        self.monitor.add_exit_marker(self.ptr, exit_price)
        
        pips = profit / 100  # Approximate pips
        self.monitor.log_event(
            f"{'✅' if profit > 0 else '❌'} Close SELL {reason} @ {exit_price:.5f} | "
            f"{pips:+.1f} pips | ${profit:+.2f}"
        )
    
    def _update_labels(self, strategy_status=""):
        """Update UI labels"""
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_profit = (self.total_profit / self.total_trades) if self.total_trades > 0 else 0
        
        current_price = self.df.iloc[self.ptr]['close']
        
        stats = {
            'total': self.total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate
        }
        
        pnl = {
            'total': self.total_profit,
            'avg': avg_profit,
            'max_dd': self.max_drawdown
        }
        
        self.monitor.update_labels(self.balance, current_price, stats, pnl, strategy_status)
    
    def _finish_backtest(self):
        """Finish backtest and show results"""
        self.timer.stop()
        self.monitor.log_event("=" * 50)
        self.monitor.log_event("✅ BACKTEST COMPLETE!")
        self.monitor.log_event(f"💵 Final Balance: ${self.balance:.2f}")
        self.monitor.log_event(f"📈 Total Trades: {self.total_trades} | Win: {self.wins} | Loss: {self.losses}")
        
        if self.total_trades > 0:
            wr = self.wins / self.total_trades * 100
            self.monitor.log_event(f"🎯 Win Rate: {wr:.1f}%")
            self.monitor.log_event(f"💰 Total Profit: ${self.total_profit:.2f}")
            self.monitor.log_event(f"📉 Max Drawdown: ${self.max_drawdown:.2f}")
            self.monitor.log_event(f"📊 Avg Profit/Trade: ${self.total_profit/self.total_trades:.2f}")
            
            # Calculate Sharpe-like metric
            profit_pct = (self.balance - self.initial_balance) / self.initial_balance * 100
            self.monitor.log_event(f"📈 Return: {profit_pct:+.2f}%")
        
        self.monitor.log_event("=" * 50)
    
    def run(self):
        """Run the trading bot"""
        self.monitor.show()
        return self.monitor.exec()


# === MAIN EXECUTION ===
if __name__ == "__main__":
    # Configuration
    config = {
        'initial_balance': 10000,
        'spread': 0.00015,
        'atr_sl_multiplier': 1.5,
        'atr_tp_multiplier': 2.5,
        'anti_whipsaw_bars': 2,
        'lot': 0.1
    }
    
    # Data path
    data_path = "./data/EURUSD_M5_48-1_reversed.csv"
    
    # Create and run bot
    print("🚀 Starting Trading Bot...")
    bot = TradingBot(data_path, config)
    sys.exit(bot.run())
