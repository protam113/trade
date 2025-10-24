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
print(f"📊 Data length: {len(df)} rows")

df = df.set_index("time")

# === Calculate Indicators ===
df["EMA8"] = ta.ema(close=df["close"], length=8)
df["EMA21"] = ta.ema(close=df["close"], length=21)
df["EMA50"] = ta.ema(close=df["close"], length=50)
df["VWAP"] = ta.vwap(high=df["high"], low=df["low"], close=df["close"], volume=df["tick_volume"], anchor="D")
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

# ADX
adx = ta.adx(high=df["high"], low=df["low"], close=df["close"], length=14)
if adx is not None and len(adx.columns) >= 1:
    df["ADX"] = adx.iloc[:, 0]
else:
    df["ADX"] = df["close"].rolling(window=14).std() * 100

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

# Stochastic
stoch = ta.stoch(high=df["high"], low=df["low"], close=df["close"], k=14, d=3)
if stoch is not None and len(stoch.columns) >= 2:
    df["STOCH_K"] = stoch.iloc[:, 0]
    df["STOCH_D"] = stoch.iloc[:, 1]
else:
    low14 = df["low"].rolling(window=14).min()
    high14 = df["high"].rolling(window=14).max()
    df["STOCH_K"] = 100 * (df["close"] - low14) / (high14 - low14 + 0.00001)
    df["STOCH_D"] = df["STOCH_K"].rolling(window=3).mean()

df["VOL_AVG"] = df["tick_volume"].rolling(window=20).mean()

# === NEW: Trend-following indicators ===
# Price below EMA8 = bearish
df["Price_Below_EMA8"] = df["close"] < df["EMA8"]
# EMA8 below EMA21 = downtrend
df["EMA8_Below_EMA21"] = df["EMA8"] < df["EMA21"]
# Price momentum (3-bar change)
df["Momentum_3"] = df["close"].diff(3)
# Price below VWAP = selling pressure
df["Price_Below_VWAP"] = df["close"] < df["VWAP"]

df = df.reset_index(drop=False)

print("\n=== Strategy: TREND-FOLLOWING SELL (Follow the Downtrend) ===")

# === Qt App ===
app = QtWidgets.QApplication([])
main_widget = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout()
main_widget.setLayout(layout)

win = pg.GraphicsLayoutWidget()
layout.addWidget(win)

# === Plot 1: Price + EMAs + BBands ===
plot_price = win.addPlot(title="EURUSD M5: TREND-FOLLOWING SELL Strategy")
price_curve = plot_price.plot(pen='y', name="Price")
ema8_curve = plot_price.plot(pen=pg.mkPen('c', width=2), name="EMA8")
ema21_curve = plot_price.plot(pen=pg.mkPen('m', width=2), name="EMA21")
ema50_curve = plot_price.plot(pen=pg.mkPen('orange', width=2), name="EMA50")
vwap_curve = plot_price.plot(pen=pg.mkPen('g', width=2, style=QtCore.Qt.DashLine), name="VWAP")
bbu_curve = plot_price.plot(pen=pg.mkPen('r', width=1, style=QtCore.Qt.DotLine), name="BBU")
bbl_curve = plot_price.plot(pen=pg.mkPen('g', width=1, style=QtCore.Qt.DotLine), name="BBL")

sell_entry_scatter = pg.ScatterPlotItem(size=15, brush='r', symbol='o', pen=pg.mkPen('w', width=2))
sell_exit_scatter = pg.ScatterPlotItem(size=18, brush='lime', symbol='t', pen=pg.mkPen('w', width=2))
plot_price.addItem(sell_entry_scatter)
plot_price.addItem(sell_exit_scatter)
plot_price.addLegend()

# === Plot 2: RSI ===
win.nextRow()
plot_rsi = win.addPlot(title="RSI (14)")
rsi_curve = plot_rsi.plot(pen='y', name="RSI")
plot_rsi.addLine(y=70, pen='r')
plot_rsi.addLine(y=50, pen='w')
plot_rsi.addLine(y=30, pen='g')
plot_rsi.addLegend()

# === Plot 3: MACD ===
win.nextRow()
plot_macd = win.addPlot(title="MACD")
macd_curve = plot_macd.plot(pen='y', name="MACD")
macd_signal_curve = plot_macd.plot(pen='c', name="Signal")
macd_hist_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='b')
plot_macd.addItem(macd_hist_bars)
plot_macd.addLine(y=0, pen='w')
plot_macd.addLegend()

# === Plot 4: Volume ===
win.nextRow()
plot_vol = win.addPlot(title="Volume")
vol_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='g')
vol_avg_curve = plot_vol.plot(pen=pg.mkPen('r', width=2), name="Avg")
plot_vol.addItem(vol_bars)

plot_rsi.setXLink(plot_price)
plot_macd.setXLink(plot_price)
plot_vol.setXLink(plot_price)

# === Labels ===
balance_label = QtWidgets.QLabel("💵 Balance: $10000.00")
balance_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
layout.addWidget(balance_label)

strategy_label = QtWidgets.QLabel("📊 Strategy: TREND-FOLLOWING SELL")
strategy_label.setStyleSheet("color: cyan; font-size: 16px; font-weight: bold;")
layout.addWidget(strategy_label)

price_label = QtWidgets.QLabel("💲 Price: 0.00000")
price_label.setStyleSheet("color: red; font-size: 14px;")
layout.addWidget(price_label)

stats_label = QtWidgets.QLabel("📊 Trades: 0 | Win: 0 | Loss: 0 | WR: 0%")
stats_label.setStyleSheet("color: lime; font-size: 14px;")
layout.addWidget(stats_label)

pnl_label = QtWidgets.QLabel("💰 Total P/L: $0.00 | Avg: $0.00 | Max DD: $0.00")
pnl_label.setStyleSheet("color: orange; font-size: 14px;")
layout.addWidget(pnl_label)

log_text = QtWidgets.QTextEdit()
log_text.setReadOnly(True)
log_text.setMaximumHeight(200)
log_text.setStyleSheet("background-color:black; color:lime; font:11pt 'Courier New';")
layout.addWidget(log_text)

main_widget.show()
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')

# === Trading State ===
INITIAL_BALANCE = 10000
balance = INITIAL_BALANCE
max_balance = INITIAL_BALANCE
max_drawdown = 0
position = None 
lot = 0.1
ptr = 50  # Wait longer for EMA50
sell_entries = []
sell_exits = []
logs = []
total_trades = 0
wins = 0
losses = 0
total_profit = 0
last_entry_bars = 0

# === TREND-FOLLOWING Parameters ===
SPREAD = 0.00015
ATR_SL_MULTIPLIER = 1.5  # Tighter SL
ATR_TP_MULTIPLIER = 2.5  # Bigger TP for trend
ANTI_WHIPSAW_BARS = 2

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

# === Main Update ===
def update():
    global ptr, balance, position, speed, total_trades, wins, losses, total_profit
    global last_entry_bars, max_balance, max_drawdown

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

        price_now = df['close'].iloc[ptr]
        high_now = df['high'].iloc[ptr]
        low_now = df['low'].iloc[ptr]
        
        sliced = df.iloc[:ptr+1]
        
        # Update charts
        price_curve.setData(sliced['close'])
        ema8_curve.setData(sliced['EMA8'])
        ema21_curve.setData(sliced['EMA21'])
        ema50_curve.setData(sliced['EMA50'])
        vwap_curve.setData(sliced['VWAP'].dropna())
        bbu_curve.setData(sliced['BBU'])
        bbl_curve.setData(sliced['BBL'])
        rsi_curve.setData(sliced['RSI'])
        macd_curve.setData(sliced['MACD'])
        macd_signal_curve.setData(sliced['MACD_Signal'])
        macd_hist_bars.setOpts(x=sliced.index, height=sliced['MACD_Hist'])
        vol_bars.setOpts(x=sliced.index, height=sliced['tick_volume'])
        vol_avg_curve.setData(sliced['VOL_AVG'])
        
        balance_label.setText(f"💵 Balance: ${balance:.2f}")
        price_label.setText(f"💲 Price: {price_now:.5f}")
        
        if balance > max_balance:
            max_balance = balance
        drawdown = max_balance - balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        
        win_rate = (wins/total_trades*100) if total_trades > 0 else 0
        stats_label.setText(f"📊 Trades: {total_trades} | Win: {wins} | Loss: {losses} | WR: {win_rate:.1f}%")
        
        avg_profit = (total_profit/total_trades) if total_trades > 0 else 0
        pnl_label.setText(f"💰 Total P/L: ${total_profit:.2f} | Avg: ${avg_profit:.2f} | Max DD: ${max_drawdown:.2f}")

        if ptr < 50:
            ptr += 1
            continue

        # Get indicators
        ema8_now = df["EMA8"].iloc[ptr]
        ema21_now = df["EMA21"].iloc[ptr]
        ema50_now = df["EMA50"].iloc[ptr]
        ema8_prev = df["EMA8"].iloc[ptr-1]
        ema21_prev = df["EMA21"].iloc[ptr-1]
        
        vwap_now = df["VWAP"].iloc[ptr]
        atr_now = df["ATR"].iloc[ptr]
        rsi_now = df["RSI"].iloc[ptr]
        macd_now = df["MACD"].iloc[ptr]
        macd_signal_now = df["MACD_Signal"].iloc[ptr]
        macd_hist_now = df["MACD_Hist"].iloc[ptr]
        momentum_3 = df["Momentum_3"].iloc[ptr]
        
        # === CLOSE POSITION ===
        if position is not None:
            exit_price = None
            hit = None
            profit = 0
            
            if position["type"] == "sell":
                # TP hit
                if low_now <= position["tp"]:
                    exit_price = position["tp"]
                    hit = "TP✅"
                    profit = (position["entry"] - exit_price - SPREAD) * lot * 100000
                # SL hit
                elif high_now >= position["sl"]:
                    exit_price = position["sl"]
                    hit = "SL❌"
                    profit = (position["entry"] - exit_price - SPREAD) * lot * 100000
                # Trend reversal exit: if EMA8 crosses back above EMA21
                elif ema8_prev <= ema21_prev and ema8_now > ema21_now:
                    exit_price = price_now
                    hit = "REVERSAL🔄"
                    profit = (position["entry"] - exit_price - SPREAD) * lot * 100000

            if hit is not None:
                balance += profit
                total_profit += profit
                total_trades += 1
                
                if profit > 0:
                    wins += 1
                else:
                    losses += 1
                
                sell_exits.append({"x": ptr, "y": exit_price})
                pips = (position["entry"] - exit_price) / 0.0001
                log_event(f"{'✅' if profit > 0 else '❌'} Close SELL {hit} @ {exit_price:.5f} | {pips:+.1f} pips | ${profit:+.2f}")
                position = None
                last_entry_bars = 0

        # === OPEN NEW POSITION (TREND-FOLLOWING) ===
        last_entry_bars += 1
        
        if position is None and last_entry_bars >= ANTI_WHIPSAW_BARS:
            sell_signal = False
            
            # === SELL when DOWNTREND is confirmed ===
            # 1. EMA8 < EMA21 (short-term downtrend)
            # 2. Price < EMA8 (price below fast MA)
            # 3. Price < VWAP (selling pressure)
            # 4. RSI < 50 (bearish momentum)
            # 5. MACD histogram < 0 (bearish)
            
            cond1 = ema8_now < ema21_now  # Downtrend
            cond2 = price_now < ema8_now  # Price below fast MA
            cond3 = price_now < vwap_now if not pd.isna(vwap_now) else True  # Below VWAP
            cond4 = rsi_now < 50  # Bearish momentum
            cond5 = macd_hist_now < 0  # MACD bearish
            cond6 = price_now < ema50_now  # Below long-term MA (stronger confirmation)
            
            sell_signal = cond1 and cond2 and cond3 and cond4 and cond5
            
            # Debug display
            conditions_met = sum([cond1, cond2, cond3, cond4, cond5, cond6])
            status = f"📊 Conditions: {conditions_met}/6 | "
            status += f"EMA8<21: {'✅' if cond1 else '❌'} | "
            status += f"P<EMA8: {'✅' if cond2 else '❌'} | "
            status += f"P<VWAP: {'✅' if cond3 else '❌'} | "
            status += f"RSI<50: {'✅' if cond4 else '❌'} | "
            status += f"MACD<0: {'✅' if cond5 else '❌'}"
            
            if sell_signal:
                status = "🎯 SELLING NOW! All conditions met!"
                strategy_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
            elif conditions_met >= 4:
                strategy_label.setStyleSheet("color: orange; font-size: 14px; font-weight: bold;")
            else:
                strategy_label.setStyleSheet("color: cyan; font-size: 14px; font-weight: bold;")
            
            strategy_label.setText(status)
            
            if sell_signal:
                entry_price = price_now
                sl_distance = ATR_SL_MULTIPLIER * atr_now
                tp_distance = ATR_TP_MULTIPLIER * atr_now
                
                position = {
                    "type": "sell",
                    "entry": entry_price,
                    "sl": entry_price + sl_distance,
                    "tp": entry_price - tp_distance
                }
                sell_entries.append({"x": ptr, "y": entry_price})
                log_event(f"🔴 SELL @ {entry_price:.5f} | SL: {position['sl']:.5f} | TP: {position['tp']:.5f}")
                last_entry_bars = 0

        # Update markers
        sell_entry_scatter.setData([s["x"] for s in sell_entries], [s["y"] for s in sell_entries])
        sell_exit_scatter.setData([s["x"] for s in sell_exits], [s["y"] for s in sell_exits])
        
        ptr += 1

# === Buttons ===
button_layout = QtWidgets.QHBoxLayout()
layout.addLayout(button_layout)

start_button = QtWidgets.QPushButton("▶ Start")
stop_button = QtWidgets.QPushButton("⏹ Stop")
reset_button = QtWidgets.QPushButton("🔄 Reset")
button_layout.addWidget(start_button)
button_layout.addWidget(stop_button)
button_layout.addWidget(reset_button)

def reset_sim():
    global ptr, balance, position, sell_entries, sell_exits
    global logs, total_trades, wins, losses, total_profit
    global max_balance, max_drawdown, last_entry_bars
    
    ptr = 50
    balance = INITIAL_BALANCE
    max_balance = INITIAL_BALANCE
    max_drawdown = 0
    position = None
    sell_entries = []
    sell_exits = []
    logs = []
    total_trades = 0
    wins = 0
    losses = 0
    total_profit = 0
    last_entry_bars = 0
    
    sell_entry_scatter.setData([], [])
    sell_exit_scatter.setData([], [])
    log_event("🔄 RESET - Ready!")
    balance_label.setText(f"💵 Balance: ${balance:.2f}")
    stats_label.setText(f"📊 Trades: 0 | Win: 0 | Loss: 0 | WR: 0%")
    pnl_label.setText(f"💰 Total P/L: $0.00 | Avg: $0.00 | Max DD: $0.00")

start_button.clicked.connect(lambda: [timer.start(50), log_event("▶ START")])
stop_button.clicked.connect(lambda: [timer.stop(), log_event("⏹ STOP")])
reset_button.clicked.connect(reset_sim)

timer = QtCore.QTimer()
timer.timeout.connect(update)

log_event("✅ TREND-FOLLOWING SELL Strategy")
log_event("📋 Sell when: EMA8<21 + Price<EMA8 + Price<VWAP + RSI<50 + MACD<0")
log_event("🎯 Follow the downtrend - don't fight it!")
log_event("▶ Press Start to begin")

sys.exit(app.exec())