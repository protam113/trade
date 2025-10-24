"""
monitor.py - GUI and Chart Display Module
Chứa tất cả code liên quan đến PyQtGraph và UI

Sử dụng:
    from monitor import TradingMonitor
    
    monitor = TradingMonitor()
    monitor.show()
    monitor.exec()
"""

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

class TradingMonitor:
    def __init__(self):
        """Initialize GUI components"""
        self.app = QtWidgets.QApplication([])
        self.main_widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QVBoxLayout()
        self.main_widget.setLayout(self.layout)
        
        # Graphics window
        self.win = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.win)
        
        # Setup charts
        self._setup_charts()
        
        # Setup labels
        self._setup_labels()
        
        # Setup log window
        self._setup_log()
        
        # Setup buttons
        self._setup_buttons()
        
        # Configure PyQtGraph
        pg.setConfigOption('background', 'k')
        pg.setConfigOption('foreground', 'w')
        
        # Data containers
        self.sell_entries = []
        self.sell_exits = []
        self.logs = []
        
    def _setup_charts(self):
        """Setup all charts"""
        # === Plot 1: Price + EMAs ===
        self.plot_price = self.win.addPlot(title="EURUSD M5: TREND-FOLLOWING SELL")
        self.price_curve = self.plot_price.plot(pen='y', name="Price")
        self.ema8_curve = self.plot_price.plot(pen=pg.mkPen('c', width=2), name="EMA8")
        self.ema21_curve = self.plot_price.plot(pen=pg.mkPen('m', width=2), name="EMA21")
        self.ema50_curve = self.plot_price.plot(pen=pg.mkPen('orange', width=2), name="EMA50")
        self.vwap_curve = self.plot_price.plot(pen=pg.mkPen('g', width=2, style=QtCore.Qt.DashLine), name="VWAP")
        self.bbu_curve = self.plot_price.plot(pen=pg.mkPen('r', width=1, style=QtCore.Qt.DotLine), name="BBU")
        self.bbl_curve = self.plot_price.plot(pen=pg.mkPen('g', width=1, style=QtCore.Qt.DotLine), name="BBL")
        
        # Entry/Exit markers
        self.sell_entry_scatter = pg.ScatterPlotItem(size=15, brush='r', symbol='o', pen=pg.mkPen('w', width=2))
        self.sell_exit_scatter = pg.ScatterPlotItem(size=18, brush='lime', symbol='t', pen=pg.mkPen('w', width=2))
        self.plot_price.addItem(self.sell_entry_scatter)
        self.plot_price.addItem(self.sell_exit_scatter)
        self.plot_price.addLegend()
        
        # === Plot 2: RSI ===
        self.win.nextRow()
        self.plot_rsi = self.win.addPlot(title="RSI (14)")
        self.rsi_curve = self.plot_rsi.plot(pen='y', name="RSI")
        self.plot_rsi.addLine(y=70, pen='r')
        self.plot_rsi.addLine(y=50, pen='w')
        self.plot_rsi.addLine(y=30, pen='g')
        
        # === Plot 3: MACD ===
        self.win.nextRow()
        self.plot_macd = self.win.addPlot(title="MACD")
        self.macd_curve = self.plot_macd.plot(pen='y', name="MACD")
        self.macd_signal_curve = self.plot_macd.plot(pen='c', name="Signal")
        self.macd_hist_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='b')
        self.plot_macd.addItem(self.macd_hist_bars)
        self.plot_macd.addLine(y=0, pen='w')
        
        # === Plot 4: Volume ===
        self.win.nextRow()
        self.plot_vol = self.win.addPlot(title="Volume")
        self.vol_bars = pg.BarGraphItem(x=[], height=[], width=0.6, brush='g')
        self.vol_avg_curve = self.plot_vol.plot(pen=pg.mkPen('r', width=2), name="Avg")
        self.plot_vol.addItem(self.vol_bars)
        
        # Link x-axes
        self.plot_rsi.setXLink(self.plot_price)
        self.plot_macd.setXLink(self.plot_price)
        self.plot_vol.setXLink(self.plot_price)
    
    def _setup_labels(self):
        """Setup info labels"""
        self.balance_label = QtWidgets.QLabel("💵 Balance: $10000.00")
        self.balance_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.balance_label)
        
        self.strategy_label = QtWidgets.QLabel("📊 Strategy: TREND-FOLLOWING SELL")
        self.strategy_label.setStyleSheet("color: cyan; font-size: 16px; font-weight: bold;")
        self.layout.addWidget(self.strategy_label)
        
        self.price_label = QtWidgets.QLabel("💲 Price: 0.00000")
        self.price_label.setStyleSheet("color: red; font-size: 14px;")
        self.layout.addWidget(self.price_label)
        
        self.stats_label = QtWidgets.QLabel("📊 Trades: 0 | Win: 0 | Loss: 0 | WR: 0%")
        self.stats_label.setStyleSheet("color: lime; font-size: 14px;")
        self.layout.addWidget(self.stats_label)
        
        self.pnl_label = QtWidgets.QLabel("💰 Total P/L: $0.00 | Avg: $0.00 | Max DD: $0.00")
        self.pnl_label.setStyleSheet("color: orange; font-size: 14px;")
        self.layout.addWidget(self.pnl_label)
    
    def _setup_log(self):
        """Setup log window"""
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("background-color:black; color:lime; font:11pt 'Courier New';")
        self.layout.addWidget(self.log_text)
    
    def _setup_buttons(self):
        """Setup control buttons"""
        # Speed buttons
        speed_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(speed_layout)
        
        self.speed_buttons = []
        for label, factor in [("1x",1),("2x",2),("5x",5),("10x",10),("20x",20)]:
            btn = QtWidgets.QPushButton(label)
            speed_layout.addWidget(btn)
            self.speed_buttons.append((btn, factor))
        
        # Control buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.layout.addLayout(button_layout)
        
        self.start_button = QtWidgets.QPushButton("▶ Start")
        self.stop_button = QtWidgets.QPushButton("⏹ Stop")
        self.reset_button = QtWidgets.QPushButton("🔄 Reset")
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.reset_button)
    
    def update_charts(self, df_slice):
        """Update all charts with new data"""
        self.price_curve.setData(df_slice['close'])
        self.ema8_curve.setData(df_slice['EMA8'])
        self.ema21_curve.setData(df_slice['EMA21'])
        self.ema50_curve.setData(df_slice['EMA50'])
        self.vwap_curve.setData(df_slice['VWAP'].dropna())
        self.bbu_curve.setData(df_slice['BBU'])
        self.bbl_curve.setData(df_slice['BBL'])
        self.rsi_curve.setData(df_slice['RSI'])
        self.macd_curve.setData(df_slice['MACD'])
        self.macd_signal_curve.setData(df_slice['MACD_Signal'])
        self.macd_hist_bars.setOpts(x=df_slice.index, height=df_slice['MACD_Hist'])
        self.vol_bars.setOpts(x=df_slice.index, height=df_slice['tick_volume'])
        self.vol_avg_curve.setData(df_slice['VOL_AVG'])
    
    def update_labels(self, balance, price, stats, pnl, strategy_status):
        """Update all labels"""
        self.balance_label.setText(f"💵 Balance: ${balance:.2f}")
        self.price_label.setText(f"💲 Price: {price:.5f}")
        
        self.stats_label.setText(
            f"📊 Trades: {stats['total']} | "
            f"Win: {stats['wins']} | "
            f"Loss: {stats['losses']} | "
            f"WR: {stats['win_rate']:.1f}%"
        )
        
        self.pnl_label.setText(
            f"💰 Total P/L: ${pnl['total']:.2f} | "
            f"Avg: ${pnl['avg']:.2f} | "
            f"Max DD: ${pnl['max_dd']:.2f}"
        )
        
        self.strategy_label.setText(strategy_status)
        if "🎯" in strategy_status or "IN POSITION" in strategy_status:
            self.strategy_label.setStyleSheet("color: red; font-size: 14px; font-weight: bold;")
        elif "Conditions: 4" in strategy_status or "Conditions: 5" in strategy_status:
            self.strategy_label.setStyleSheet("color: orange; font-size: 14px; font-weight: bold;")
        else:
            self.strategy_label.setStyleSheet("color: cyan; font-size: 14px; font-weight: bold;")
    
    def add_entry_marker(self, bar_index, price):
        """Add entry marker to chart"""
        self.sell_entries.append({"x": bar_index, "y": price})
        self.sell_entry_scatter.setData(
            [s["x"] for s in self.sell_entries],
            [s["y"] for s in self.sell_entries]
        )
    
    def add_exit_marker(self, bar_index, price):
        """Add exit marker to chart"""
        self.sell_exits.append({"x": bar_index, "y": price})
        self.sell_exit_scatter.setData(
            [s["x"] for s in self.sell_exits],
            [s["y"] for s in self.sell_exits]
        )
    
    def log_event(self, text):
        """Add log message"""
        self.logs.append(text)
        self.log_text.setPlainText("\n".join(self.logs[-20:]))
    
    def clear_markers(self):
        """Clear all entry/exit markers"""
        self.sell_entries = []
        self.sell_exits = []
        self.sell_entry_scatter.setData([], [])
        self.sell_exit_scatter.setData([], [])
    
    def show(self):
        """Show the GUI"""
        self.main_widget.show()
    
    def exec(self):
        """Execute the Qt application"""
        return self.app.exec()