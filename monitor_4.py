import sys
import os
import numpy as np

ROOT = "/home/hoang-pham/Documents/bot_v2/src"  
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))  

import pandas as pd
import pandas_ta as ta
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

# === Load data ===
df = pd.read_csv("./data/EURUSD_M5_48-1_reversed.csv", sep=';')
df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")

# Set DatetimeIndex for VWAP
df = df.set_index("time")

# === Calculate ALL Indicators ===
# EMA 8, 21 for trend + momentum
df["EMA8"] = ta.ema(close=df["close"], length=8)
df["EMA21"] = ta.ema(close=df["close"], length=21)

# VWAP (session) - now works with DatetimeIndex
df["VWAP"] = ta.vwap(high=df["high"], low=df["low"], close=df["close"], volume=df["tick_volume"], anchor="D")

# ATR(14) for dynamic SL/TP
df["ATR"] = ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)

# Bollinger Bands (20,2) for mean reversion
bbands = ta.bbands(close=df["close"], length=20, std=2.0)
# Check actual column names returned
print("BBands columns:", bbands.columns.tolist() if bbands is not None else "None")
if bbands is not None and len(bbands.columns) >= 3:
    df["BBU"] = bbands.iloc[:, 0]  # Upper band
    df["BBM"] = bbands.iloc[:, 1]  # Middle band
    df["BBL"] = bbands.iloc[:, 2]  # Lower band
else:
    # Fallback manual calculation
    df["BBM"] = df["close"].rolling(window=20).mean()
    std = df["close"].rolling(window=20).std()
    df["BBU"] = df["BBM"] + (2.0 * std)
    df["BBL"] = df["BBM"] - (2.0 * std)

# ADX(14) for regime filter
adx = ta.adx(high=df["high"], low=df["low"], close=df["close"], length=14)
print("ADX columns:", adx.columns.tolist() if adx is not None else "None")
if adx is not None and len(adx.columns) >= 3:
    df["ADX"] = adx.iloc[:, 0]  # ADX
    df["DMP"] = adx.iloc[:, 1]  # DI+
    df["DMN"] = adx.iloc[:, 2]  # DI-
else:
    # Fallback - simple trend strength
    df["ADX"] = df["close"].rolling(window=14).std() * 100

# MACD for momentum confirmation
macd_df = ta.macd(close=df["close"], fast=12, slow=26, signal=9)
print("MACD columns:", macd_df.columns.tolist() if macd_df is not None else "None")
if macd_df is not None and len(macd_df.columns) >= 3:
    df["MACD"] = macd_df.iloc[:, 0]
    df["MACD_Hist"] = macd_df.iloc[:, 1]
    df["MACD_Signal"] = macd_df.iloc[:, 2]
else:
    # Fallback
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

# RSI(14) for overbought/oversold
df["RSI"] = ta.rsi(close=df["close"], length=14)

# Stochastic for range mode
stoch = ta.stoch(high=df["high"], low=df["low"], close=df["close"], k=14, d=3)
print("Stochastic columns:", stoch.columns.tolist() if stoch is not None else "None")
if stoch is not None and len(stoch.columns) >= 2:
    df["STOCH_K"] = stoch.iloc[:, 0]
    df["STOCH_D"] = stoch.iloc[:, 1]
else:
    # Fallback
    low14 = df["low"].rolling(window=14).min()
    high14 = df["high"].rolling(window=14).max()
    df["STOCH_K"] = 100 * (df["close"] - low14) / (high14 - low14 + 0.00001)
    df["STOCH_D"] = df["STOCH_K"].rolling(window=3).mean()

# Volume average (20-period)
df["VOL_AVG"] = df["tick_volume"].rolling(window=20).mean()

# Reset index to integer for plotting
df = df.reset_index(drop=False)

print("\n=== Indicator Columns ===")
print(df.columns.tolist())
print("\n=== First 25 rows ===")
print(df[["close", "EMA8", "EMA21", "VWAP", "ATR", "ADX", "RSI", "MACD", "BBU", "BBL"]].head(25))

# === Qt App & Layout ===
app = QtWidgets.QApplication([])
main_widget = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout()
main_widget.setLayout(layout)

# === PyQtGraph Charts ===
win = pg.GraphicsLayoutWidget()
layout.addWidget(win)

# === Plot 1: Price + EMA8/21 + BBands + VWAP ===
plot_price = win.addPlot(title="EURUSD M5: Price + EMA8/21 + BBands + VWAP")
price_curve = plot_price.plot(pen='y', name="Price")
ema8_curve = plot_price.plot(pen=pg.mkPen('c', width=2), name="EMA8")
ema21_curve = plot_price.plot(pen=pg.mkPen('m', width=2), name="EMA21")
vwap_curve = plot_price.plot(pen=pg.mkPen('g', width=2, style=QtCore.Qt.DashLine), name="VWAP")
bbu_curve = plot_price.plot(pen=pg.mkPen('r', style=QtCore.Qt.DotLine), name="BBU")
bbl_curve = plot_price.plot(pen=pg.mkPen('r', style=QtCore.Qt.DotLine), name="BBL")
bbm_curve = plot_price.plot(pen=pg.mkPen('w', style=QtCore.Qt.DotLine), name="BBM")

# Entry/Exit markers
buy_entry_scatter = pg.ScatterPlotItem(size=15, brush='g', symbol='o', pen=pg.mkPen('w', width=2))
sell_entry_scatter = pg.ScatterPlotItem(size=15, brush='r', symbol='o', pen=pg.mkPen('w', width=2))
buy_exit_scatter = pg.ScatterPlotItem(size=18, brush='b', symbol='t1', pen=pg.mkPen('w', width=2))
sell_exit_scatter = pg.ScatterPlotItem(size=18, brush='m', symbol='t', pen=pg.mkPen('w', width=2))

plot_price.addItem(buy_entry_scatter)
plot_price.addItem(sell_entry_scatter)
plot_price.addItem(buy_exit_scatter)
plot_price.addItem(sell_exit_scatter)
plot_price.addLegend()

# === Plot 2: ADX (Regime Filter) ===
win.nextRow()
plot_adx = win.addPlot(title="ADX (14) - Regime Filter")
adx_curve = plot_adx.plot(pen=pg.mkPen('y', width=2), name="ADX")
plot_adx.addLine(y=25, pen=pg.mkPen('g', width=2, style=QtCore.Qt.DashLine))  # Trending threshold
plot_adx.addLine(y=20, pen=pg.mkPen('r', width=2, style=QtCore.Qt.DashLine))  # Sideways threshold
plot_adx.addLegend()

# === Plot 3: RSI + Stochastic ===
win.nextRow()
plot_rsi = win.addPlot(title="RSI (14) + Stochastic")
rsi_curve = plot_rsi.plot(pen='y', name="RSI")
stoch_k_curve = plot_rsi.plot(pen='c', name="STOCH_K")
stoch_d_curve = plot_rsi.plot(pen='m', name="STOCH_D")
plot_rsi.addLine(y=70, pen='r')
plot_rsi.addLine(y=30, pen='g')
plot_rsi.addLine(y=80, pen=pg.mkPen('r', style=QtCore.Qt.DashLine))
plot_rsi.addLine(y=20, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
plot_rsi.addLegend()

# === Plot 4: MACD ===
win.nextRow()
plot_macd = win.addPlot(title="MACD (12,26,9)")
macd_curve = plot_macd.plot(pen='y', name="MACD")
macd_signal_curve = plot_macd.plot(pen='c', name="Signal")
macd_hist_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='b')
plot_macd.addItem(macd_hist_bars)
plot_macd.addLine(y=0, pen='w')
plot_macd.addLegend()

# === Plot 5: Volume ===
win.nextRow()
plot_vol = win.addPlot(title="Volume (with 20-period avg)")
vol_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='g')
vol_avg_curve = plot_vol.plot(pen=pg.mkPen('r', width=2), name="Vol Avg")
plot_vol.addItem(vol_bars)
plot_vol.addLegend()

# Link x-axes
plot_adx.setXLink(plot_price)
plot_rsi.setXLink(plot_price)
plot_macd.setXLink(plot_price)
plot_vol.setXLink(plot_price)

# === Balance & Mode Labels ===
balance_label = QtWidgets.QLabel("💵 Balance: $10000.00")
balance_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
layout.addWidget(balance_label)

mode_label = QtWidgets.QLabel("📊 Mode: -- | ADX: --")
mode_label.setStyleSheet("color: cyan; font-size: 16px; font-weight: bold;")
layout.addWidget(mode_label)

price_label = QtWidgets.QLabel("💲 Price: 0.00000")
price_label.setStyleSheet("color: red; font-size: 14px;")
layout.addWidget(price_label)

# === Stats Labels ===
stats_label = QtWidgets.QLabel("📊 Trades: 0 | Win: 0 | Loss: 0 | WR: 0%")
stats_label.setStyleSheet("color: lime; font-size: 14px;")
layout.addWidget(stats_label)

pnl_label = QtWidgets.QLabel("💰 Total P/L: $0.00 | Avg: $0.00 | Max DD: $0.00")
pnl_label.setStyleSheet("color: orange; font-size: 14px;")
layout.addWidget(pnl_label)

# === Log Window ===
log_text = QtWidgets.QTextEdit()
log_text.setReadOnly(True)
log_text.setMaximumHeight(200)
log_text.setStyleSheet("background-color:black; color:lime; font:11pt 'Courier New';")
layout.addWidget(log_text)

main_widget.show()
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')

# === Trading Simulator State ===
INITIAL_BALANCE = 10000
balance = INITIAL_BALANCE
max_balance = INITIAL_BALANCE
max_drawdown = 0
position = None 
lot = 0.1  # Fixed lot for simplicity
ptr = 25  # Start after indicators stabilize
buy_entries, sell_entries = [], []
buy_exits, sell_exits = [], []
logs = []
total_trades = 0
wins = 0
losses = 0
total_profit = 0
daily_loss = 0
trades_today = 0
last_entry_bars = 0  # Anti-whipsaw: count bars since last entry

# === Trading Parameters ===
SPREAD = 0.00015
ATR_SL_MULTIPLIER = 1.2  # SL = 1.2 * ATR
ATR_TP_MULTIPLIER_TREND = 2.0  # TP for trend mode
ATR_TP_MULTIPLIER_RANGE = 1.0  # TP for range mode
RISK_PER_TRADE = 0.003  # 0.3% risk per trade
DAILY_MAX_LOSS_PCT = 0.02  # 2% daily max loss
MAX_CONCURRENT_TRADES = 1
VOLUME_MULTIPLIER = 1.2  # Volume must be >= 1.2 * avg
ANTI_WHIPSAW_BARS = 3  # Minimum bars between entries

def log_event(text):
    logs.append(text)
    log_text.setPlainText("\n".join(logs[-20:]))

# === Speed Control ===
speed_layout = QtWidgets.QHBoxLayout()
layout.addLayout(speed_layout)
speed = 1
for label, factor in [("1x",1),("2x",2),("5x",5),("10x",10),("20x",20)]:
    btn = QtWidgets.QPushButton(label)
    speed_layout.addWidget(btn)
    btn.clicked.connect(lambda _, f=factor: set_speed(f))

def set_speed(f):
    global speed
    speed = f
    log_event(f"⚡ Speed: {f}x")

# === Main Update Function ===
def update():
    global ptr, balance, position, speed, total_trades, wins, losses, total_profit
    global daily_loss, trades_today, last_entry_bars, max_balance, max_drawdown

    for _ in range(speed):
        if ptr >= len(df):
            timer.stop()
            log_event("=" * 50)
            log_event("✅ BACKTEST COMPLETE!")
            log_event(f"💵 Final Balance: ${balance:.2f}")
            log_event(f"📈 Total Trades: {total_trades} | Win: {wins} | Loss: {losses}")
            if total_trades > 0:
                wr = wins/total_trades*100
                log_event(f"🎯 Win Rate: {wr:.1f}%")
                log_event(f"💰 Total Profit: ${total_profit:.2f}")
                log_event(f"📉 Max Drawdown: ${max_drawdown:.2f}")
                log_event(f"📊 Avg Profit/Trade: ${total_profit/total_trades:.2f}")
            log_event("=" * 50)
            return

        # Current bar data
        price_now = df['close'].iloc[ptr]
        high_now = df['high'].iloc[ptr]
        low_now = df['low'].iloc[ptr]
        
        sliced = df.iloc[:ptr+1]
        
        # Update all charts
        price_curve.setData(sliced['close'])
        ema8_curve.setData(sliced['EMA8'])
        ema21_curve.setData(sliced['EMA21'])
        vwap_curve.setData(sliced['VWAP'].dropna())
        bbu_curve.setData(sliced['BBU'])
        bbl_curve.setData(sliced['BBL'])
        bbm_curve.setData(sliced['BBM'])
        
        adx_curve.setData(sliced['ADX'])
        rsi_curve.setData(sliced['RSI'])
        stoch_k_curve.setData(sliced['STOCH_K'])
        stoch_d_curve.setData(sliced['STOCH_D'])
        macd_curve.setData(sliced['MACD'])
        macd_signal_curve.setData(sliced['MACD_Signal'])
        macd_hist_bars.setOpts(x=sliced.index, height=sliced['MACD_Hist'])
        vol_bars.setOpts(x=sliced.index, height=sliced['tick_volume'])
        vol_avg_curve.setData(sliced['VOL_AVG'])
        
        # Update labels
        balance_label.setText(f"💵 Balance: ${balance:.2f}")
        price_label.setText(f"💲 Price: {price_now:.5f}")
        
        # Track max drawdown
        if balance > max_balance:
            max_balance = balance
        drawdown = max_balance - balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        
        win_rate = (wins/total_trades*100) if total_trades > 0 else 0
        stats_label.setText(f"📊 Trades: {total_trades} | Win: {wins} | Loss: {losses} | WR: {win_rate:.1f}%")
        
        avg_profit = (total_profit/total_trades) if total_trades > 0 else 0
        pnl_label.setText(f"💰 Total P/L: ${total_profit:.2f} | Avg: ${avg_profit:.2f} | Max DD: ${max_drawdown:.2f}")

        if ptr < 25:  # Wait for indicators
            ptr += 1
            continue

        # Get indicators
        ema8_now = df["EMA8"].iloc[ptr]
        ema21_now = df["EMA21"].iloc[ptr]
        ema8_prev = df["EMA8"].iloc[ptr-1]
        ema21_prev = df["EMA21"].iloc[ptr-1]
        
        vwap_now = df["VWAP"].iloc[ptr]
        atr_now = df["ATR"].iloc[ptr]
        adx_now = df["ADX"].iloc[ptr]
        rsi_now = df["RSI"].iloc[ptr]
        macd_now = df["MACD"].iloc[ptr]
        macd_hist_now = df["MACD_Hist"].iloc[ptr]
        stoch_k_now = df["STOCH_K"].iloc[ptr]
        bbu_now = df["BBU"].iloc[ptr]
        bbl_now = df["BBL"].iloc[ptr]
        vol_now = df["tick_volume"].iloc[ptr]
        vol_avg_now = df["VOL_AVG"].iloc[ptr]
        
        # Determine market regime
        if adx_now > 25:
            mode = "TREND"
            mode_color = "lime"
        elif adx_now < 20:
            mode = "RANGE"
            mode_color = "orange"
        else:
            mode = "NEUTRAL"
            mode_color = "red"
        
        mode_label.setText(f"📊 Mode: {mode} | ADX: {adx_now:.2f}")
        mode_label.setStyleSheet(f"color: {mode_color}; font-size: 16px; font-weight: bold;")
        
        # Daily loss limit check
        if daily_loss >= INITIAL_BALANCE * DAILY_MAX_LOSS_PCT:
            if position is None:
                ptr += 1
                continue  # Stop trading for the day
        
        # === CLOSE EXISTING POSITION ===
        if position is not None:
            exit_price = None
            hit = None
            profit = 0
            
            if position["type"] == "buy":
                if high_now >= position["tp"]:
                    exit_price = position["tp"]
                    hit = "TP✅"
                    profit = (exit_price - position["entry"] - SPREAD) * lot * 100000
                elif low_now <= position["sl"]:
                    exit_price = position["sl"]
                    hit = "SL❌"
                    profit = (exit_price - position["entry"] - SPREAD) * lot * 100000
                    
            elif position["type"] == "sell":
                if low_now <= position["tp"]:
                    exit_price = position["tp"]
                    hit = "TP✅"
                    profit = (position["entry"] - exit_price - SPREAD) * lot * 100000
                elif high_now >= position["sl"]:
                    exit_price = position["sl"]
                    hit = "SL❌"
                    profit = (position["entry"] - exit_price - SPREAD) * lot * 100000

            if hit is not None:
                balance += profit
                total_profit += profit
                total_trades += 1
                
                if profit > 0:
                    wins += 1
                else:
                    losses += 1
                    daily_loss += abs(profit)
                
                # Add exit marker
                if position["type"] == "buy":
                    buy_exits.append({"x": ptr, "y": exit_price})
                else:
                    sell_exits.append({"x": ptr, "y": exit_price})
                
                pips = (exit_price - position["entry"]) / 0.0001 if position["type"] == "buy" else (position["entry"] - exit_price) / 0.0001
                log_event(f"{'✅' if profit > 0 else '❌'} Close {position['type'].upper()} {hit} @ {exit_price:.5f} | {pips:+.1f} pips | ${profit:+.2f} | Mode: {position['mode']}")
                position = None
                last_entry_bars = 0

        # === OPEN NEW POSITION ===
        last_entry_bars += 1
        
        if position is None and last_entry_bars >= ANTI_WHIPSAW_BARS:
            buy_signal = False
            sell_signal = False
            
            # Volume confirmation
            vol_confirm = vol_now >= VOLUME_MULTIPLIER * vol_avg_now if not pd.isna(vol_avg_now) else True
            
            # === TREND MODE (ADX > 25) ===
            if mode == "TREND":
                # BUY conditions
                buy_signal = (
                    ema8_prev <= ema21_prev and ema8_now > ema21_now and  # EMA8 crosses above EMA21
                    price_now > vwap_now and  # Price above VWAP
                    (macd_hist_now > 0 or rsi_now > 50) and  # Momentum confirmation
                    vol_confirm  # Volume confirmation
                )
                
                # SELL conditions
                sell_signal = (
                    ema8_prev >= ema21_prev and ema8_now < ema21_now and  # EMA8 crosses below EMA21
                    price_now < vwap_now and  # Price below VWAP
                    (macd_hist_now < 0 or rsi_now < 50) and  # Momentum confirmation
                    vol_confirm
                )
            
            # === RANGE/MEAN-REVERSION MODE (ADX < 20) ===
            elif mode == "RANGE":
                # BUY conditions (oversold bounce)
                buy_signal = (
                    (price_now <= bbl_now or price_now < bbl_now * 1.001) and  # Touch or slightly below lower BB
                    (stoch_k_now < 20 or rsi_now < 35) and  # Oversold
                    not pd.isna(vwap_now) and abs(price_now - vwap_now) < 0.005  # VWAP relatively flat
                )
                
                # SELL conditions (overbought fade)
                sell_signal = (
                    (price_now >= bbu_now or price_now > bbu_now * 0.999) and  # Touch or slightly above upper BB
                    (stoch_k_now > 80 or rsi_now > 65) and  # Overbought
                    not pd.isna(vwap_now) and abs(price_now - vwap_now) < 0.005
                )
            
            # Execute trades
            if buy_signal:
                entry_price = price_now
                sl_distance = ATR_SL_MULTIPLIER * atr_now
                tp_multiplier = ATR_TP_MULTIPLIER_TREND if mode == "TREND" else ATR_TP_MULTIPLIER_RANGE
                tp_distance = tp_multiplier * atr_now
                
                position = {
                    "type": "buy",
                    "entry": entry_price,
                    "sl": entry_price - sl_distance,
                    "tp": entry_price + tp_distance,
                    "mode": mode
                }
                buy_entries.append({"x": ptr, "y": entry_price})
                log_event(f"🟢 BUY @ {entry_price:.5f} | SL: {position['sl']:.5f} | TP: {position['tp']:.5f} | Mode: {mode}")
                last_entry_bars = 0

            elif sell_signal:
                entry_price = price_now
                sl_distance = ATR_SL_MULTIPLIER * atr_now
                tp_multiplier = ATR_TP_MULTIPLIER_TREND if mode == "TREND" else ATR_TP_MULTIPLIER_RANGE
                tp_distance = tp_multiplier * atr_now
                
                position = {
                    "type": "sell",
                    "entry": entry_price,
                    "sl": entry_price + sl_distance,
                    "tp": entry_price - tp_distance,
                    "mode": mode
                }
                sell_entries.append({"x": ptr, "y": entry_price})
                log_event(f"🔴 SELL @ {entry_price:.5f} | SL: {position['sl']:.5f} | TP: {position['tp']:.5f} | Mode: {mode}")
                last_entry_bars = 0

        # Update markers
        buy_entry_scatter.setData([b["x"] for b in buy_entries], [b["y"] for b in buy_entries])
        sell_entry_scatter.setData([s["x"] for s in sell_entries], [s["y"] for s in sell_entries])
        buy_exit_scatter.setData([b["x"] for b in buy_exits], [b["y"] for b in buy_exits])
        sell_exit_scatter.setData([s["x"] for s in sell_exits], [s["y"] for s in sell_exits])
        
        ptr += 1

# === Control Buttons ===
button_layout = QtWidgets.QHBoxLayout()
layout.addLayout(button_layout)

start_button = QtWidgets.QPushButton("▶ Start")
stop_button = QtWidgets.QPushButton("⏹ Stop")
reset_button = QtWidgets.QPushButton("🔄 Reset")
button_layout.addWidget(start_button)
button_layout.addWidget(stop_button)
button_layout.addWidget(reset_button)

def reset_sim():
    global ptr, balance, position, buy_entries, sell_entries, buy_exits, sell_exits
    global logs, total_trades, wins, losses, total_profit, daily_loss, trades_today
    global max_balance, max_drawdown, last_entry_bars
    
    ptr = 25
    balance = INITIAL_BALANCE
    max_balance = INITIAL_BALANCE
    max_drawdown = 0
    position = None
    buy_entries, sell_entries = [], []
    buy_exits, sell_exits = [], []
    logs = []
    total_trades = 0
    wins = 0
    losses = 0
    total_profit = 0
    daily_loss = 0
    trades_today = 0
    last_entry_bars = 0
    
    buy_entry_scatter.setData([], [])
    sell_entry_scatter.setData([], [])
    buy_exit_scatter.setData([], [])
    sell_exit_scatter.setData([], [])
    log_event("🔄 Simulation RESET - Ready to start!")
    balance_label.setText(f"💵 Balance: ${balance:.2f}")
    stats_label.setText(f"📊 Trades: 0 | Win: 0 | Loss: 0 | WR: 0%")
    pnl_label.setText(f"💰 Total P/L: $0.00 | Avg: $0.00 | Max DD: $0.00")

start_button.clicked.connect(lambda: [timer.start(50), log_event("▶ Simulation STARTED")])
stop_button.clicked.connect(lambda: [timer.stop(), log_event("⏹ Simulation STOPPED")])
reset_button.clicked.connect(reset_sim)

# === Timer ===
timer = QtCore.QTimer()
timer.timeout.connect(update)

log_event("✅ Strategy loaded: TREND + RANGE Mode with ADX filter")
log_event("📋 Indicators: EMA8/21, VWAP, ATR, BBands, ADX, MACD, RSI, Stochastic")
log_event("🎯 Press ▶ Start to begin backtest")

sys.exit(app.exec())