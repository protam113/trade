from PyQt6 import QtWidgets, QtCore

class MainTable(QtWidgets.QTableWidget):
    """Custom table widget for trading symbols"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()
    
    def setup_table(self):
        """Setup table headers and configuration"""
        headers = ["SYMBOL", "BID", "ASK", "DAILY CHANGE"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Optional: Configure table appearance
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Auto resize columns
        header = self.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
    
    def update_data(self, symbols_data):
        """Update table with symbol data
        
        Args:
            symbols_data: List of dicts with keys: symbol, bid, ask, change
            Example: [{"symbol": "EURUSD", "bid": 1.0850, "ask": 1.0852, "change": "+0.15%"}]
        """
        self.setRowCount(len(symbols_data))
        
        for row, data in enumerate(symbols_data):
            self.setItem(row, 0, QtWidgets.QTableWidgetItem(data["symbol"]))
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{data['bid']:.5f}"))
            self.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{data['ask']:.5f}"))
            
            # Color code the change
            change_item = QtWidgets.QTableWidgetItem(data["change"])
            if "+" in data["change"]:
                change_item.setForeground(QtCore.Qt.GlobalColor.green)
            elif "-" in data["change"]:
                change_item.setForeground(QtCore.Qt.GlobalColor.red)
            self.setItem(row, 3, change_item)
    
    def add_row(self, symbol, bid, ask, change):
        """Add a single row to table"""
        row = self.rowCount()
        self.insertRow(row)
        
        self.setItem(row, 0, QtWidgets.QTableWidgetItem(symbol))
        self.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{bid:.5f}"))
        self.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{ask:.5f}"))
        self.setItem(row, 3, QtWidgets.QTableWidgetItem(change))
    
    def clear_data(self):
        """Clear all rows but keep headers"""
        self.setRowCount(0)