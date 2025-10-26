# navbar.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

class NavBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pinned_pairs = ["EURUSD", "USDJPY", "GBPUSD"]  # ví dụ pinned sẵn
        self.all_pairs = [
            "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD",
            "NZDUSD", "XAUUSD", "BTCUSD", "ETHUSD"
        ]
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Ô input search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm cặp tiền...")
        self.search_input.textChanged.connect(self.filter_pairs)
        layout.addWidget(self.search_input)

        # Danh sách cặp pinned
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # Dropdown "Xem thêm"
        self.more_button = QPushButton("▼ Xem thêm")
        self.more_button.clicked.connect(self.toggle_more)
        layout.addWidget(self.more_button)

        # Danh sách cặp tiền mở rộng (ẩn mặc định)
        self.extra_list_widget = QListWidget()
        self.extra_list_widget.setVisible(False)
        layout.addWidget(self.extra_list_widget)

        # Hiển thị danh sách ban đầu
        self.render_pairs()

        # Style
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QListWidget {
                background-color: #ffffff;
                border: none;
            }
            QPushButton {
                background-color: #eeeeee;
                border: none;
                padding: 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ddd;
            }
        """)

    def render_pairs(self):
        self.list_widget.clear()
        self.extra_list_widget.clear()

        # Pinned pairs (tối đa 5)
        for pair in self.pinned_pairs[:5]:
            self.add_pair_item(self.list_widget, pair, pinned=True)

        # Các cặp khác
        for pair in self.all_pairs:
            if pair not in self.pinned_pairs:
                self.add_pair_item(self.extra_list_widget, pair, pinned=False)

    def add_pair_item(self, list_widget, pair, pinned):
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 2, 6, 2)

        label = QLabel(pair)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        star_btn = QPushButton("⭐" if pinned else "☆")
        star_btn.setFixedWidth(30)
        star_btn.setStyleSheet("border: none; background: transparent; font-size: 16px;")
        star_btn.clicked.connect(lambda: self.toggle_pin(pair))

        layout.addWidget(label)
        layout.addWidget(star_btn, alignment=Qt.AlignmentFlag.AlignRight)
        widget.setLayout(layout)
        item.setSizeHint(widget.sizeHint())
        list_widget.addItem(item)
        list_widget.setItemWidget(item, widget)

    def toggle_pin(self, pair):
        if pair in self.pinned_pairs:
            self.pinned_pairs.remove(pair)
        else:
            if len(self.pinned_pairs) < 5:
                self.pinned_pairs.append(pair)
        self.render_pairs()

    def toggle_more(self):
        self.extra_list_widget.setVisible(not self.extra_list_widget.isVisible())
        self.more_button.setText("▲ Ẩn bớt" if self.extra_list_widget.isVisible() else "▼ Xem thêm")

    def filter_pairs(self, text):
        text = text.upper().strip()
        self.all_pairs = [
            pair for pair in [
                "EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD",
                "NZDUSD", "XAUUSD", "BTCUSD", "ETHUSD"
            ] if text in pair
        ]
        self.render_pairs()
