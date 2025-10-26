# window.py
from PyQt6.QtWidgets import QMainWindow, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from .navbar import NavBar
from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "UNKNOWN_APP")
VERSION = os.getenv("VERSION", "0.0.0")



class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {VERSION}")
        self.setWindowIcon(QIcon("public/imgs/logo.svg"))

        self.init_ui()

    def init_ui(self):
        self.resize(1280, 720)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
                color: #000000;
            }
        """)

        QTimer.singleShot(100, self.showMaximized)

        central = QWidget()
        layout = QHBoxLayout(central)

        # Add navbar trái
        self.navbar = NavBar()
        layout.addWidget(self.navbar, 1)

        # chỗ main content (chart, dashboard,...)
        # layout.addWidget(self.main_content, 4)

        self.setCentralWidget(central)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

