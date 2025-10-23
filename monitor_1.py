import sys
import os

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
bbands_df = ta.bbands(close=df["close"], length=30, lower_std=2.0, upper_std=2.0, mamode="sma")
df = pd.concat([df, bbands_df], axis=1)

print("\n=== BBands Columns ===")
print(df.columns.tolist())
print("\n=== First 20 rows BBands ===")
print(df[["close", "BBL_30_2.0_2.0", "BBM_30_2.0_2.0", "BBU_30_2.0_2.0"]].head(20))

# === Qt App & Layout ===
app = QtWidgets.QApplication([])
main_widget = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout()
main_widget.setLayout(layout)

# === PyQtGraph Charts ===
win = pg.GraphicsLayoutWidget()
layout.addWidget(win)

# === Plot 1: Price + BBands ===
plot_price = win.addPlot(title="EURUSD M5 Price + BBands")
price_curve = plot_price.plot(pen='y', name="Price")
bbm_curve = plot_price.plot(pen='w', name="BBM")
bbl_curve = plot_price.plot(pen='g', name="BBL")
bbu_curve = plot_price.plot(pen='r', name="BBU")

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

# === Plot 2: Volume ===
win.nextRow()
plot_vol = win.addPlot(title="Volume")
vol_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='g')
plot_vol.addItem(vol_bars)

# Link x-axes
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

# === BBands Debug Label ===
bbands_label = QtWidgets.QLabel("📈 BBL: -- | BBM: -- | BBU: --")
bbands_label.setStyleSheet("color: orange; font-size: 12px;")
layout.addWidget(bbands_label)

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
lot = 0.1
ptr = 100  # Start later to avoid initial noise
buy_entries, sell_entries = [], []  # Entry points
buy_exits, sell_exits = [], []      # Exit points
logs = []
total_trades = 0
wins = 0
losses = 0
total_profit = 0
debug_mode = True 

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
STOP_LOSS_PIPS = 10
SPREAD = 0.00015

# === Update function ===
def update():
    global ptr, balance, position, lot, speed, total_trades, wins, losses, total_profit

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
        
        sliced = df.iloc[:ptr+1]
        
        # Update Price + BBands chart
        price_curve.setData(sliced['close'])
        bbm_curve.setData(sliced['BBM_30_2.0_2.0'])
        bbl_curve.setData(sliced['BBL_30_2.0_2.0'])
        bbu_curve.setData(sliced['BBU_30_2.0_2.0'])
        
        # Update Volume chart
        if 'tick_volume' in df.columns:
            vol_bars.setOpts(x=sliced.index, height=sliced['tick_volume'])
        
        balance_label.setText(f"💵 Balance: ${balance:.2f}")
        price_label.setText(f"💲 Price: {price_now:.5f}")
        
        win_rate = (wins/total_trades*100) if total_trades > 0 else 0
        stats_label.setText(f"📊 Trades: {total_trades} | Win: {wins} | Loss: {losses} | WR: {win_rate:.1f}%")
        
        avg_profit = (total_profit/total_trades) if total_trades > 0 else 0
        pnl_label.setText(f"💰 Total P/L: ${total_profit:.2f} | Avg: ${avg_profit:.2f}")

        if ptr < 30:  # Wait for BBands to stabilize
            ptr += 1
            continue

        bbl_now = df["BBL_30_2.0_2.0"].iloc[ptr]
        bbu_now = df["BBU_30_2.0_2.0"].iloc[ptr]
        price_prev = df["close"].iloc[ptr-1]
        
        # Update BBands display
        bbands_label.setText(f"📈 BBL: {bbl_now:.5f} | BBM: {df['BBM_30_2.0_2.0'].iloc[ptr]:.5f} | BBU: {bbu_now:.5f}")

        # === ĐÓNG LỆNH TRƯỚC ===
        if position is not None:
            exit_price = None
            hit = None
            profit = 0
            
            if position["type"] == "buy":
                # Chốt lời khi chạm BBU
                if high_now >= bbu_now:
                    exit_price = bbu_now
                    hit = "TP✅ (BBU)"
                    profit = (exit_price - position["entry"] - SPREAD) * lot * 100000
                # Stop loss khi vượt 10 pips
                elif low_now <= position["sl"]:
                    exit_price = position["sl"]
                    hit = "SL❌"
                    profit = (exit_price - position["entry"] - SPREAD) * lot * 100000
                    
            elif position["type"] == "sell":
                # Chốt lời khi chạm BBL
                if low_now <= bbl_now:
                    exit_price = bbl_now
                    hit = "TP✅ (BBL)"
                    profit = (position["entry"] - exit_price - SPREAD) * lot * 100000
                # Stop loss khi vượt 10 pips
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
            # Check BUY condition - Price touches or goes below BBL
            buy_signal = price_prev > bbl_now and price_now <= bbl_now
            
            # Check SELL condition - Price touches or goes above BBU
            sell_signal = price_prev < bbu_now and price_now >= bbu_now
            
            # DEBUG: Log signals
            if debug_mode and (buy_signal or sell_signal):
                if buy_signal:
                    log_event(f"🟡 BUY Signal @ {ptr} | Price: {price_now:.5f}")
                if sell_signal:
                    log_event(f"🟡 SELL Signal @ {ptr} | Price: {price_now:.5f}")
            
            # BUY Signal
            if buy_signal:
                entry_price = price_now
                # Dynamic SL based on BBands width
                bb_width = (bbu_now - bbl_now) * 10000  # Convert to pips
                dynamic_sl = max(10, int(bb_width * 0.5))  # Minimum 10 pips, adjust based on width
                position = {
                    "type": "buy",
                    "entry": entry_price,
                    "sl": entry_price - dynamic_sl * 0.0001
                }
                buy_entries.append({"x": ptr, "y": entry_price})  # Green dot
                log_event(f"🟢 BUY @ {entry_price:.5f} | SL: {position['sl']:.5f} (Dynamic: {dynamic_sl} pips)")

            # SELL Signal
            elif sell_signal:
                entry_price = price_now
                # Dynamic SL based on BBands width
                bb_width = (bbu_now - bbl_now) * 10000  # Convert to pips
                dynamic_sl = max(10, int(bb_width * 0.5))  # Minimum 10 pips, adjust based on width
                position = {
                    "type": "sell",
                    "entry": entry_price,
                    "sl": entry_price + dynamic_sl * 0.0001
                }
                sell_entries.append({"x": ptr, "y": entry_price})  # Red dot
                log_event(f"🔴 SELL @ {entry_price:.5f} | SL: {position['sl']:.5f} (Dynamic: {dynamic_sl} pips)")

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
    global ptr, balance, position, buy_entries, sell_entries, buy_exits, sell_exits, logs, total_trades, wins, losses, total_profit
    ptr = 100
    balance = 1000
    position = None
    buy_entries, sell_entries = [], []
    buy_exits, sell_exits = [], []
    logs = []
    total_trades = 0
    wins = 0
    losses = 0
    total_profit = 0
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