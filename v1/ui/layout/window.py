from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import sys
import os
from dotenv import load_dotenv
from views.home import HomePage
from ui.components.menu_bar import MenuBar

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "UNKNOWN_APP")
VERSION = os.getenv("VERSION", "0.0.0")


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #333; color: #fff;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(QWidget())  # placeholder, có thể thêm label nếu muốn

    def toggle_max(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon("assets/imgs/logo.png"))
        self.resize(1280, 720)

        # =========================
        # Main layout
        # =========================
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Setup menubar
        self.menu_bar = MenuBar(self)
        self.menu_bar.setup_menubar()

        # =========================
        # Title bar
        # =========================
        title_area = CustomTitleBar(self)
        layout.addWidget(title_area)

        # =========================
        # Main content
        # =========================
        self.content = HomePage()
        layout.addWidget(self.content)

        # Optional: start maximized
        QTimer.singleShot(100, self.showMaximized)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

def setup_connections(self):
        """Connect menu actions to slots"""
        callbacks = {
            "actionExit": self.close,
            "actionRefresh": self.refresh_data,
            "actionClose": self.close_current,
            "actionFullScreen": self.toggle_fullscreen,
            "actionOptions": self.show_options,
        }
        self.menu_bar.connect_actions(callbacks)
        
        # Connect button
        self.pushButton.clicked.connect(self.show_account)
    
    # Slot methods
def refresh_data(self):
        print("Refreshing data...")
        self.statusbar.showMessage("Data refreshed", 2000)
    
def close_current(self):
        print("Closing current window...")
    
def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
def show_options(self):
        print("Opening options...")
    
def show_account(self):
        print("Opening account dialog...")