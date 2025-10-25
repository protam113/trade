import sys
import pandas as pd
import MetaTrader5 as mt5
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
import pyqtgraph as pg
import numpy as np

# Thông tin đăng nhập MT5
creds = {
    'path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
    'login': 98171894,
    'password': '3kP!YmVv',
    'server': 'MetaQuotes-Demo',
    'timeout': 60000,
    'portable': False
}

# Khởi động MT5
if not mt5.initialize(
        path=creds['path'],
        login=creds['login'],
        password=creds['password'],
        server=creds['server'],
        timeout=creds['timeout'],
        portable=creds['portable']
):
    print("MT5 initialization failed")
    mt5.shutdown()
    sys.exit()

account_info = mt5.account_info()
if account_info is None:
    print("Failed to connect")
    mt5.shutdown()
    sys.exit()
account_info = mt5.account_info()
if account_info is None:
    print("Failed to connect")
    mt5.shutdown()
    sys.exit()
else:
    print("Logged in:", account_info.login)
    balance = account_info.balance  # Lấy số dư tài khoản
    print(f"Số tiền hiện tại trong tài khoản: {balance} USD")

# Lấy dữ liệu từ 22/10/2025 đến 23/10/2025, khung H1
from_date = pd.Timestamp('2025-10-1 00:00:00').to_pydatetime()
to_date = pd.Timestamp('2025-10-23 23:59:59').to_pydatetime()
rates = mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_H4, from_date, to_date)

if len(rates) > 0:
    df = pd.DataFrame(rates)
    print(f"Đã lấy {len(df)} cây nến H4 từ 22/10 đến 23/10.")
else:
    print("Không thể lấy dữ liệu. Kiểm tra symbol hoặc ngày tháng.")
    mt5.shutdown()
    sys.exit()

# Tạo ứng dụng PyQt
app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("EURUSD H4 Chart (22/10 - 23/10/2025)")
window.setGeometry(100, 100, 800, 600)

# Tạo widget đồ thị
widget = QWidget()
layout = QVBoxLayout()
window.setCentralWidget(widget)
widget.setLayout(layout)

# Tạo biểu đồ pyqtgraph
graph = pg.PlotWidget()
layout.addWidget(graph)

# Chuẩn bị dữ liệu
x = np.arange(len(df))
open_prices = df['open'].values
high_prices = df['high'].values
low_prices = df['low'].values
close_prices = df['close'].values
dates = pd.to_datetime(df['time'], unit='s')

# Vẽ nến thủ công
for i in range(len(df)):
    # Đường giá cao-thấp
    graph.plot([i, i], [low_prices[i], high_prices[i]], pen=pg.mkPen('w', width=1))
    
    # Thân nến
    if close_prices[i] >= open_prices[i]:  # Nến tăng (xanh)
        color = (0, 255, 0, 100)  # Màu xanh nhạt
    else:  # Nến giảm (đỏ)
        color = (255, 0, 0, 100)  # Màu đỏ nhạt
    body_height = abs(close_prices[i] - open_prices[i])
    if body_height > 0.0001:  # Tránh nến quá mỏng
        bar = pg.BarGraphItem(x0=i-0.2, x1=i+0.2, y0=min(open_prices[i], close_prices[i]), 
                              height=body_height, brush=pg.mkBrush(color))
        graph.addItem(bar)

# Thiết lập trục x (thời gian)
graph.setLabel('bottom', 'Time')
graph.getAxis('bottom').setTicks([[(i, dates[i].strftime('%H:%M\n%d/%m')) for i in range(len(dates))]])

# Thiết lập trục y (giá)
graph.setLabel('left', 'Price')

# Hiển thị cửa sổ
window.show()
sys.exit(app.exec_())

# Đóng MT5 sau khi xong
mt5.shutdown()