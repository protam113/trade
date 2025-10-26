import sys
import os
import numpy as np
import json

ROOT = "/home/hoang-pham/Documents/bot_v2/src"  
sys.path.append(ROOT)

print("ROOT:", ROOT)
print("Folders:", os.listdir(ROOT))  

import pandas as pd
import pandas_ta as ta
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from datetime import datetime

# Load trade config
with open("trade_config.json", "r") as f:
    config = json.load(f)
BUY_THRESHOLD = config["BUY_THRESHOLD"]
SCALP_TARGET = config["SCALP_TARGET"]  # 1.02 = 2% profit
STOP_LOSS = config["STOP_LOSS"]  # 0.98 = 2% loss
ENABLE_TRAILING_PROFIT = config["ENABLE_TRAILING_PROFIT"]
ENABLE_DCA = config["ENABLE_DCA"]
MAX_TRADES_PER_DAY = config["MAX_TRADES_PER_DAY"]

# === Load data ===
df = pd.read_csv("./data/EURUSD_M5_48-1_reversed.csv", sep=';')
df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M")
df["EMA5"] = ta.ema(close=df["close"], length=5)
df["EMA20"] = ta.ema(close=df["close"], length=20)
df["RSI"] = ta.rsi(close=df["close"], length=14)
df["RSI_MA"] = ta.sma(close=df["RSI"], length=9)
macd_df = ta.macd(close=df["close"], fast=6, slow=13, signal=5)
df["MACD"] = macd_df["MACD_6_13_5"]
df["MACD_Signal"] = macd_df["MACDs_6_13_5"]
df["VWAP"] = ta.vwap(high=df["high"], low=df["low"], close=df["close"], volume=df["tick_volume"], anchor="D")
df["BBU"] = ta.bbands(close=df["close"], length=5, upper_std=2.0, lower_std=2.0)["BBU_5_2.0_2.0"]
df["BBL"] = ta.bbands(close=df["close"], length=5, upper_std=2.0, lower_std=2.0)["BBL_5_2.0_2.0"]
df["BBM"] = ta.bbands(close=df["close"], length=5, upper_std=2.0, lower_std=2.0)["BBM_5_2.0_2.0"]
df["ATR"] = ta.atr(high=df["high"], low=df["low"], close=df["close"], length=14)
df["STOCHF_k"] = ta.stochf(high=df["high"], low=df["low"], close=df["close"], k=14, d=3)["STOCHFk_14_3"]
df["STOCHF_d"] = ta.stochf(high=df["high"], low=df["low"], close=df["close"], k=14, d=3)["STOCHFd_14_3"]

print("\n=== All Indicator Columns ===")
print(df.columns.tolist())
print("\n=== First 20 rows of Indicators ===")
print(df[["close", "EMA5", "EMA20", "RSI", "RSI_MA", "MACD", "MACD_Signal", "VWAP", "BBU", "BBL", "BBM", "ATR", "STOCHF_k", "STOCHF_d"]].head(20))

# === Qt App & Layout ===
app = QtWidgets.QApplication([])
main_widget = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout()
main_widget.setLayout(layout)

# === PyQtGraph Charts ===
win = pg.GraphicsLayoutWidget()
layout.addWidget(win)

# === Plot 1: Price + EMAs + BBands + VWAP ===
plot_price = win.addPlot(title="EURUSD M5 Price + EMAs + BBands + VWAP")
price_curve = plot_price.plot(pen='y', name="Price")
ema5_curve = plot_price.plot(pen='c', name="EMA5")
ema20_curve = plot_price.plot(pen='m', name="EMA20")
vwap_curve = plot_price.plot(pen='g', name="VWAP")
bbu_curve = plot_price.plot(pen='r', name="BBU")
bbl_curve = plot_price.plot(pen='r', name="BBL")
bbm_curve = plot_price.plot(pen='w', name="BBM")

# Entry signals (dots)
buy_entry_scatter = pg.ScatterPlotItem(size=12, brush='g', symbol='o')
sell_entry_scatter = pg.ScatterPlotItem(size=12, brush='r', symbol='o')

# Exit signals (arrows)
buy_exit_scatter = pg.ScatterPlotItem(size=15, brush='b', symbol='t1')  # triangle down
sell_exit_scatter = pg.ScatterPlotItem(size=15, brush='m', symbol='t')  # triangle up

plot_price.addItem(buy_entry_scatter)
plot_price.addItem(sell_entry_scatter)
plot_price.addItem(buy_exit_scatter)
plot_price.addItem(sell_exit_scatter)
plot_price.addLegend()

# === Plot 2: RSI + RSI_MA ===
win.nextRow()
plot_rsi = win.addPlot(title="RSI (14) + MA (9)")
rsi_curve = plot_rsi.plot(pen='y', name="RSI")
rsi_ma_curve = plot_rsi.plot(pen='c', name="RSI_MA")
plot_rsi.addLine(y=70, pen='r')
plot_rsi.addLine(y=30, pen='g')

# === Plot 3: MACD ===
win.nextRow()
plot_macd = win.addPlot(title="MACD (6,13,5)")
macd_curve = plot_macd.plot(pen='y', name="MACD")
macd_signal_curve = plot_macd.plot(pen='c', name="Signal")
plot_macd.addLine(y=0, pen='w')

# === Plot 4: Stochastic Fast ===
win.nextRow()
plot_stochf = win.addPlot(title="StochF (14,3)")
stochf_k_curve = plot_stochf.plot(pen='y', name="StochF_k")
stochf_d_curve = plot_stochf.plot(pen='c', name="StochF_d")
plot_stochf.addLine(y=80, pen='r')
plot_stochf.addLine(y=20, pen='g')

# === Plot 5: Volume ===
win.nextRow()
plot_vol = win.addPlot(title="Volume")
vol_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='g')
plot_vol.addItem(vol_bars)

# Link x-axes
plot_rsi.setXLink(plot_price)
plot_macd.setXLink(plot_price)
plot_stochf.setXLink(plot_price)
plot_vol.setXLink(plot_price)

# === Balance & Price Labels ===
balance_label = QtWidgets.QLabel("💵 Balance: $1000.00")
balance_label.setStyleSheet("color: black; font-size: 16px;")
layout.addWidget(balance_label)
price_label = QtWidgets.QLabel("💲 Price: 0.00000")
price_label.setStyleSheet("color: blue; font-size: 14px;")
layout.addWidget(price_label)

# === Stats Labels ===
stats_label = QtWidgets.QLabel("📊 Trades: 0 | Win: 0 | Loss: 0 | WR: 0%")
stats_label.setStyleSheet("color: green; font-size: 14px;")
layout.addWidget(stats_label)

# === Profit/Loss Labels ===
pnl_label = QtWidgets.QLabel("💰 Total P/L: $0.00 | Avg: $0.00")
pnl_label.setStyleSheet("color: cyan; font-size: 14px;")
layout.addWidget(pnl_label)

# === Indicator Debug Label ===
ind_label = QtWidgets.QLabel("📈 EMA5: -- | EMA20: -- | RSI: -- | RSI_MA: -- | MACD: -- | STOCHF_k: --")
ind_label.setStyleSheet("color: orange; font-size: 12px;")
layout.addWidget(ind_label)

# === Log Window ===
log_text = QtWidgets.QTextEdit()
log_text.setReadOnly(True)
log_text.setMaximumHeight(150)
log_text.setStyleSheet("background-color:black; color:white; font:12pt 'Courier New';")
layout.addWidget(log_text)

main_widget.show()
pg.setConfigOption('background', 'k')
pg.setConfigOption('foreground', 'w')

# === Trading Simulator State ===
balance = 1000
position = None 
risk_percent = 0.01  # Rủi ro 1% mỗi lệnh
ptr = 20  # Start later to allow indicator initialization
buy_entries, sell_entries = [], []  # Entry points
buy_exits, sell_exits = [], []      # Exit points
logs = []
total_trades = 0
wins = 0
losses = 0
total_profit = 0
debug_mode = True 
daily_trades = {}  # Theo dõi số lệnh mỗi ngày

def log_event(text):
    logs.append(text)
    log_text.setPlainText("\n".join(logs[-15:]))

# === Speed control buttons ===
speed_layout = QtWidgets.QHBoxLayout()
layout.addLayout(speed_layout)
speed_buttons = []
for label, factor in [("1x",1),("2x",2),("5x",5),("10x",10)]:
    btn = QtWidgets.QPushButton(label)
    speed_layout.addWidget(btn)
    speed_buttons.append((btn, factor))

speed = 1
def set_speed(f):
    global speed
    speed = f
    log_event(f"⚡ Speed set to {f}x")
for btn, f in speed_buttons:
    btn.clicked.connect(lambda _, f=f: set_speed(f))

# === Trading Parameters ===
SPREAD = 0.00015

# === Update function ===
def update():
    global ptr, balance, position, risk_percent, speed, total_trades, wins, losses, total_profit, daily_trades

    for _ in range(speed):
        if ptr >= len(df):
            timer.stop()
            log_event("✅ Backtest hoàn tất!")
            log_event(f"📊 Final Balance: ${balance:.2f}")
            log_event(f"📈 Total Trades: {total_trades} | Win: {wins} | Loss: {losses}")
            if total_trades > 0:
                log_event(f"🎯 Win Rate: {wins/total_trades*100:.1f}%")
            return

        # Current candle data
        price_now = df['close'].iloc[ptr]
        high_now = df['high'].iloc[ptr]
        low_now = df['low'].iloc[ptr]
        current_date = df['time'].iloc[ptr].date()
        
        sliced = df.iloc[:ptr+1]
        
        # Update Price + EMAs + BBands + VWAP chart
        price_curve.setData(sliced['close'])
        ema5_curve.setData(sliced['EMA5'])
        ema20_curve.setData(sliced['EMA20'])
        vwap_curve.setData(sliced['VWAP'].dropna())  # Lọc NaN trước khi vẽ
        bbu_curve.setData(sliced['BBU'])
        bbl_curve.setData(sliced['BBL'])
        bbm_curve.setData(sliced['BBM'])
        
        # Update RSI chart
        rsi_curve.setData(sliced['RSI'])
        rsi_ma_curve.setData(sliced['RSI_MA'])
        
        # Update MACD chart
        macd_curve.setData(sliced['MACD'])
        macd_signal_curve.setData(sliced['MACD_Signal'])
        
        # Update Stochastic Fast chart
        stochf_k_curve.setData(sliced['STOCHF_k'])
        stochf_d_curve.setData(sliced['STOCHF_d'])
        
        # Update Volume chart
        if 'tick_volume' in df.columns:
            vol_bars.setOpts(x=sliced.index, height=sliced['tick_volume'])
        
        balance_label.setText(f"💵 Balance: ${balance:.2f}")
        price_label.setText(f"💲 Price: {price_now:.5f}")
        
        win_rate = (wins/total_trades*100) if total_trades > 0 else 0
        stats_label.setText(f"📊 Trades: {total_trades} | Win: {wins} | Loss: {losses} | WR: {win_rate:.1f}%")
        
        avg_profit = (total_profit/total_trades) if total_trades > 0 else 0
        pnl_label.setText(f"💰 Total P/L: ${total_profit:.2f} | Avg: ${avg_profit:.2f}")

        if ptr < 20:  # Wait for indicators to stabilize
            ptr += 1
            continue

        ema5_now = df["EMA5"].iloc[ptr]
        ema20_now = df["EMA20"].iloc[ptr]
        ema5_prev = df["EMA5"].iloc[ptr-1]
        ema20_prev = df["EMA20"].iloc[ptr-1]
        rsi_now = df["RSI"].iloc[ptr]
        rsi_ma_now = df["RSI_MA"].iloc[ptr]
        macd_now = df["MACD"].iloc[ptr]
        macd_signal_now = df["MACD_Signal"].iloc[ptr]
        macd_prev = df["MACD"].iloc[ptr-1]
        macd_signal_prev = df["MACD_Signal"].iloc[ptr-1]
        stochf_k_now = df["STOCHF_k"].iloc[ptr]
        stochf_d_now = df["STOCHF_d"].iloc[ptr]
        stochf_k_prev = df["STOCHF_k"].iloc[ptr-1]
        stochf_d_prev = df["STOCHF_d"].iloc[ptr-1]
        atr_now = df["ATR"].iloc[ptr]
        vwap_now = df["VWAP"].iloc[ptr]
        bbu_now = df["BBU"].iloc[ptr]
        bbl_now = df["BBL"].iloc[ptr]

        # Update Indicator display
        ind_label.setText(f"📈 EMA5: {ema5_now:.5f} | EMA20: {ema20_now:.5f} | RSI: {rsi_now:.2f} | RSI_MA: {rsi_ma_now:.2f} | MACD: {macd_now:.4f} | STOCHF_k: {stochf_k_now:.2f}")

        # === ĐÓNG LỆNH TRƯỚC ===
        if position is not None:
            exit_price = None
            hit = None
            profit = 0
            risk_amount = balance * risk_percent
            
            if position["type"] == "buy":
                # Trailing profit if enabled
                if ENABLE_TRAILING_PROFIT and high_now > position["tp"]:
                    position["tp"] = max(position["tp"], high_now - (atr_now * 1.5))  # Trail by 1.5 ATR
                # Check TP
                if high_now >= position["tp"]:
                    exit_price = position["tp"]
                    hit = "TP✅"
                    profit = (exit_price - position["entry"] - SPREAD) * position["lot"] * 100000
                # Check SL
                elif low_now <= position["sl"]:
                    exit_price = position["sl"]
                    hit = "SL❌"
                    profit = (exit_price - position["entry"] - SPREAD) * position["lot"] * 100000
                    
            elif position["type"] == "sell":
                # Trailing profit if enabled
                if ENABLE_TRAILING_PROFIT and low_now < position["tp"]:
                    position["tp"] = min(position["tp"], low_now + (atr_now * 1.5))  # Trail by 1.5 ATR
                # Check TP
                if low_now <= position["tp"]:
                    exit_price = position["tp"]
                    hit = "TP✅"
                    profit = (position["entry"] - exit_price - SPREAD) * position["lot"] * 100000
                # Check SL
                elif high_now >= position["sl"]:
                    exit_price = position["sl"]
                    hit = "SL❌"
                    profit = (position["entry"] - exit_price - SPREAD) * position["lot"] * 100000

            if hit is not None:
                balance += profit
                total_profit += profit
                total_trades += 1
                if profit > 0:
                    wins += 1
                else:
                    losses += 1
                
                # Add EXIT marker (arrow)
                if position["type"] == "buy":
                    buy_exits.append({"x": ptr, "y": exit_price})  # triangle down
                else:
                    sell_exits.append({"x": ptr, "y": exit_price})  # triangle up
                
                # Detail log with pips
                pips = (exit_price - position["entry"]) / 0.0001 if position["type"] == "buy" else (position["entry"] - exit_price) / 0.0001
                log_event(f"{'✅' if profit > 0 else '❌'} Close {position['type'].upper()} {hit} @ {exit_price:.5f} | {pips:+.1f} pips | ${profit:+.2f}")
                position = None

        # === MỞ LỆNH MỚI ===
        if position is None:
            # Count trades for the day
            if current_date not in daily_trades:
                daily_trades[current_date] = 0
            if daily_trades[current_date] >= MAX_TRADES_PER_DAY:
                ptr += 1
                continue

            # Calculate signal strength (0-1)
            signal_score = 0
            total_indicators = 3  # EMA, RSI, MACD
            if ema5_prev <= ema20_prev and ema5_now > ema20_now:
                signal_score += 1  # EMA Buy
            if rsi_now > 20 and rsi_now < 80:
                signal_score += 1  # RSI not extreme
            if macd_prev <= macd_signal_prev and macd_now > macd_signal_now:
                signal_score += 1  # MACD Buy
            buy_strength = signal_score / total_indicators

            # Sell signal
            signal_score = 0
            if ema5_prev >= ema20_prev and ema5_now < ema20_now:
                signal_score += 1  # EMA Sell
            if rsi_now < 80 and rsi_now > 20:
                signal_score += 1  # RSI not extreme
            if macd_prev >= macd_signal_prev and macd_now < macd_signal_now:
                signal_score += 1  # MACD Sell
            sell_strength = signal_score / total_indicators

            # DEBUG: Log signals
            if debug_mode and (buy_strength >= BUY_THRESHOLD or sell_strength >= BUY_THRESHOLD):
                if buy_strength >= BUY_THRESHOLD:
                    log_event(f"🟡 BUY Signal @ {ptr} | Strength: {buy_strength:.2f} | EMA5: {ema5_now:.5f} | RSI: {rsi_now:.2f} | MACD: {macd_now:.4f}")
                if sell_strength >= BUY_THRESHOLD:
                    log_event(f"🔴 SELL Signal @ {ptr} | Strength: {sell_strength:.2f} | EMA5: {ema5_now:.5f} | RSI: {rsi_now:.2f} | MACD: {macd_now:.4f}")
            
            # Calculate dynamic lot size based on risk
            risk_amount = balance * risk_percent
            pip_value = 10  # $10 per lot per pip for EURUSD
            atr_now = df["ATR"].iloc[ptr]
            stop_loss_pips = (price_now * (1 - STOP_LOSS)) / 0.0001 if buy_strength >= BUY_THRESHOLD else (STOP_LOSS - 1 + price_now) / 0.0001
            lot = min(0.1, risk_amount / (stop_loss_pips * pip_value * 0.0001))  # Cap at 0.1

            # BUY Signal
            if buy_strength >= BUY_THRESHOLD:
                entry_price = price_now
                dynamic_sl = entry_price * STOP_LOSS
                dynamic_tp = entry_price * SCALP_TARGET
                position = {
                    "type": "buy",
                    "entry": entry_price,
                    "tp": dynamic_tp,
                    "sl": dynamic_sl,
                    "lot": lot,
                    "dca_count": 0,
                    "dca_entries": [entry_price]
                }
                buy_entries.append({"x": ptr, "y": entry_price})  # Green dot
                daily_trades[current_date] += 1
                log_event(f"🟢 BUY @ {entry_price:.5f} | TP: {dynamic_tp:.5f} | SL: {dynamic_sl:.5f} | Lot: {lot:.2f}")

            # SELL Signal
            elif sell_strength >= BUY_THRESHOLD:
                entry_price = price_now
                dynamic_sl = entry_price * (2 - STOP_LOSS)  # 1 - (1 - STOP_LOSS)
                dynamic_tp = entry_price * (2 - SCALP_TARGET)  # 1 - (1 - SCALP_TARGET)
                position = {
                    "type": "sell",
                    "entry": entry_price,
                    "tp": dynamic_tp,
                    "sl": dynamic_sl,
                    "lot": lot,
                    "dca_count": 0,
                    "dca_entries": [entry_price]
                }
                sell_entries.append({"x": ptr, "y": entry_price})  # Red dot
                daily_trades[current_date] += 1
                log_event(f"🔴 SELL @ {entry_price:.5f} | TP: {dynamic_tp:.5f} | SL: {dynamic_sl:.5f} | Lot: {lot:.2f}")

            # DCA Logic
            elif ENABLE_DCA and position is not None and position["dca_count"] < 2:  # Limit to 2 DCA
                if position["type"] == "buy" and low_now < position["sl"] and price_now < position["entry"]:
                    new_lot = position["lot"] * 0.5  # Half lot for DCA
                    new_entry = price_now
                    position["entry"] = (position["entry"] * position["lot"] + new_entry * new_lot) / (position["lot"] + new_lot)
                    position["lot"] += new_lot
                    position["dca_count"] += 1
                    position["dca_entries"].append(new_entry)
                    position["sl"] = min(position["sl"], new_entry * STOP_LOSS)
                    position["tp"] = max(position["tp"], new_entry * SCALP_TARGET)
                    log_event(f"🔄 DCA BUY @ {new_entry:.5f} | New Entry: {position['entry']:.5f} | SL: {position['sl']:.5f} | TP: {position['tp']:.5f} | Lot: {position['lot']:.2f}")
                elif position["type"] == "sell" and high_now > position["sl"] and price_now > position["entry"]:
                    new_lot = position["lot"] * 0.5  # Half lot for DCA
                    new_entry = price_now
                    position["entry"] = (position["entry"] * position["lot"] + new_entry * new_lot) / (position["lot"] + new_lot)
                    position["lot"] += new_lot
                    position["dca_count"] += 1
                    position["dca_entries"].append(new_entry)
                    position["sl"] = max(position["sl"], new_entry * (2 - STOP_LOSS))
                    position["tp"] = min(position["tp"], new_entry * (2 - SCALP_TARGET))
                    log_event(f"🔄 DCA SELL @ {new_entry:.5f} | New Entry: {position['entry']:.5f} | SL: {position['sl']:.5f} | TP: {position['tp']:.5f} | Lot: {position['lot']:.2f}")

        # Update all markers
        buy_entry_scatter.setData([b["x"] for b in buy_entries], [b["y"] for b in buy_entries])
        sell_entry_scatter.setData([s["x"] for s in sell_entries], [s["y"] for s in sell_entries])
        buy_exit_scatter.setData([b["x"] for b in buy_exits], [b["y"] for b in buy_exits])
        sell_exit_scatter.setData([s["x"] for s in sell_exits], [s["y"] for s in sell_exits])
        
        ptr += 1

# === Start/Stop buttons ===
button_layout = QtWidgets.QHBoxLayout()
layout.addLayout(button_layout)
start_button = QtWidgets.QPushButton("▶ Start")
stop_button = QtWidgets.QPushButton("⏹ Stop")
reset_button = QtWidgets.QPushButton("🔄 Reset")
debug_toggle = QtWidgets.QPushButton("🐛 Debug: ON")
button_layout.addWidget(start_button)
button_layout.addWidget(stop_button)
button_layout.addWidget(reset_button)
button_layout.addWidget(debug_toggle)

def toggle_debug():
    global debug_mode
    debug_mode = not debug_mode
    debug_toggle.setText(f"🐛 Debug: {'ON' if debug_mode else 'OFF'}")
    log_event(f"Debug mode: {'ON' if debug_mode else 'OFF'}")

def reset_sim():
    global ptr, balance, position, buy_entries, sell_entries, buy_exits, sell_exits, logs, total_trades, wins, losses, total_profit, daily_trades
    ptr = 20
    balance = 1000
    position = None
    buy_entries, sell_entries = [], []
    buy_exits, sell_exits = [], []
    logs = []
    total_trades = 0
    wins = 0
    losses = 0
    total_profit = 0
    daily_trades = {}
    buy_entry_scatter.setData([], [])
    sell_entry_scatter.setData([], [])
    buy_exit_scatter.setData([], [])
    sell_exit_scatter.setData([], [])
    log_event("🔄 Simulation reset")
    balance_label.setText(f"💵 Balance: ${balance:.2f}")
    stats_label.setText(f"📊 Trades: {total_trades} | Win: {wins} | Loss: {losses} | WR: 0%")
    pnl_label.setText(f"💰 Total P/L: $0.00 | Avg: $0.00")

start_button.clicked.connect(lambda: [timer.start(50), log_event("▶ Simulation started")])
stop_button.clicked.connect(lambda: [timer.stop(), log_event("⏹ Simulation stopped")])
reset_button.clicked.connect(reset_sim)
debug_toggle.clicked.connect(toggle_debug)

# === Timer ===
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)

sys.exit(app.exec())