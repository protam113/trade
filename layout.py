import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox, QPushButton, QFrame)

class TradingBotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Bot - Layout")
        self.setGeometry(100, 100, 400, 500)  # Vị trí và kích thước cửa sổ
        self.setStyleSheet("background-color: #2E2E2E; color: white;")  # Màu nền tối

        # Tạo widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Tiêu đề
        title_label = QLabel("Trading Bot Configuration")
        title_label.setStyleSheet("font: bold 16px Arial;")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)
        layout.addSpacing(10)

        # Frame chứa ô nhập liệu
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #2E2E2E;")
        input_layout = QVBoxLayout(input_frame)

        # Symbol
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol (VD: EURUSD):"))
        self.symbol_entry = QLineEdit()
        self.symbol_entry.setFixedWidth(200)
        symbol_layout.addWidget(self.symbol_entry)
        input_layout.addLayout(symbol_layout)

        # Timeframe
        timeframe_layout = QHBoxLayout()
        timeframe_layout.addWidget(QLabel("Timeframe (VD: M30):"))
        self.timeframe_entry = QComboBox()
        self.timeframe_entry.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        self.timeframe_entry.setCurrentText("M30")
        self.timeframe_entry.setFixedWidth(200)
        timeframe_layout.addWidget(self.timeframe_entry)
        input_layout.addLayout(timeframe_layout)

        # Risk Percent
        risk_layout = QHBoxLayout()
        risk_layout.addWidget(QLabel("Risk % (VD: 1.0):"))
        self.risk_percent_entry = QLineEdit()
        self.risk_percent_entry.setText("1.0")
        self.risk_percent_entry.setFixedWidth(200)
        risk_layout.addWidget(self.risk_percent_entry)
        input_layout.addLayout(risk_layout)

        # SL Multiplier
        sl_layout = QHBoxLayout()
        sl_layout.addWidget(QLabel("SL Multiplier (VD: 2.0):"))
        self.sl_multiplier_entry = QLineEdit()
        self.sl_multiplier_entry.setText("2.0")
        self.sl_multiplier_entry.setFixedWidth(200)
        sl_layout.addWidget(self.sl_multiplier_entry)
        input_layout.addLayout(sl_layout)

        # TP Multiplier
        tp_layout = QHBoxLayout()
        tp_layout.addWidget(QLabel("TP Multiplier (VD: 3.0):"))
        self.tp_multiplier_entry = QLineEdit()
        self.tp_multiplier_entry.setText("3.0")
        self.tp_multiplier_entry.setFixedWidth(200)
        tp_layout.addWidget(self.tp_multiplier_entry)
        input_layout.addLayout(tp_layout)

        layout.addWidget(input_frame)
        layout.addSpacing(20)

        # Frame chứa nút
        button_frame = QFrame()
        button_frame.setStyleSheet("background-color: #2E2E2E;")
        button_layout = QHBoxLayout(button_frame)
        self.run_button = QPushButton("Chạy Bot")
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.run_button.setFixedWidth(150)
        self.run_button.setEnabled(False)
        button_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Dừng Bot")
        self.stop_button.setStyleSheet("background-color: #F44336; color: white;")
        self.stop_button.setFixedWidth(150)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        layout.addWidget(button_frame)
        layout.addSpacing(20)

        # Frame trạng thái
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #2E2E2E;")
        status_layout = QHBoxLayout(status_frame)
        self.status_label = QLabel("Trạng thái: Chưa chạy")
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_frame)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TradingBotWindow()
    window.show()
    sys.exit(app.exec_())