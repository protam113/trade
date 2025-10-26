from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt
from ui.table.main_table import MainTable

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
        # Update data sau khi initUI
        data = [
            {"symbol": "EURUSD", "bid": 1.0850, "ask": 1.0852, "change": "+0.15%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
            {"symbol": "GBPUSD", "bid": 1.2650, "ask": 1.2652, "change": "-0.08%"},
        ]
        self.tableWidget.update_data(data)
    
    def initUI(self):
        main_layout = QVBoxLayout(self)
        
        # Welcome message ở trên
        welcome = QLabel("Trading Dashboard")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(welcome)
    
        # Layout ngang cho table
        h_layout = QHBoxLayout()
    
        self.tableWidget = MainTable(self)
        self.tableWidget.setMaximumHeight(450) 

        h_layout.addWidget(self.tableWidget)
        h_layout.addStretch(2) 
    
        # Set stretch: table=1, spacer=2
        h_layout.setStretch(0, 1)  # table 1/3
        h_layout.setStretch(1, 2)  # spacer 2/3
    
        main_layout.addLayout(h_layout)
        main_layout.addStretch()