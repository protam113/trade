from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QPushButton, QStackedWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon
import sys
import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "UNKNOWN_APP")
VERSION = os.getenv("VERSION", "0.0.0")

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(48)
        self.setStyleSheet("background-color: #333; color: #fff;")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)

        # Icon
        self.iconLabel = QLabel(self)
        self.iconLabel.setFixedSize(20, 20)
        self.layout.addWidget(self.iconLabel)

        # Title
        self.titleLabel = QLabel(APP_NAME, self)
        self.layout.addWidget(self.titleLabel)

        self.layout.addStretch()

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

        # =========================
        # Optional: fake title bar area for styling
        # =========================
        title_area = CustomTitleBar(self)
        layout.addWidget(title_area)

        # =========================
        # Navigation and content area
        # =========================
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Navigation bar (using buttons for simplicity)
        self.navigationBar = QWidget()
        nav_layout = QVBoxLayout(self.navigationBar)
        nav_layout.setSpacing(5)
        self.navigationBar.setFixedWidth(150)
        self.navigationBar.setStyleSheet("background-color: #444;")

        # Stack widget for content
        self.stackWidget = QStackedWidget()
        content_layout.addWidget(self.navigationBar)
        content_layout.addWidget(self.stackWidget, stretch=1)

        layout.addWidget(content)
        self.initNavigation()

        # Optional: start maximized
        QTimer.singleShot(100, self.showMaximized)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def initNavigation(self):
        # Create widget instances for each sub-interface
        songs_widget = QWidget()
        songs_widget.setObjectName("Songs")
        songs_layout = QVBoxLayout(songs_widget)
        songs_layout.addWidget(QLabel("Songs Page"))

        playlists_widget = QWidget()
        playlists_widget.setObjectName("Playlists")
        playlists_layout = QVBoxLayout(playlists_widget)
        playlists_layout.addWidget(QLabel("Playlists Page"))

        artists_widget = QWidget()
        artists_widget.setObjectName("Artists")
        artists_layout = QVBoxLayout(artists_widget)
        artists_layout.addWidget(QLabel("Artists Page"))

        # Add sub-interfaces to stackWidget and navigationBar
        self.addSubInterface(songs_widget, "Songs")
        self.addSubInterface(playlists_widget, "Playlists")
        self.addSubInterface(artists_widget, "Artists")

        # Add About item to navigation bar
        self.addNavItem(
            routeKey='About',
            text='About',
            onClick=self.showMessageBox,
            selectable=False
        )

        # Connect stackWidget changes to update navigation bar
        self.stackWidget.currentChanged.connect(self.updateNavigationBar)
        self.setCurrentNavItem("Songs")  # Set default to Songs

    def addSubInterface(self, interface, name, selectedIcon=None):
        """Add a sub-interface to the stackWidget and navigationBar"""
        self.stackWidget.addWidget(interface)
        self.addNavItem(
            routeKey=interface.objectName(),
            text=name,
            onClick=lambda: self.switchTo(interface),
            selectedIcon=selectedIcon
        )

    def addNavItem(self, routeKey, text, onClick, selectable=True, selectedIcon=None):
        """Add a navigation item (button) to the navigation bar"""
        button = QPushButton(text)
        button.setObjectName(routeKey)
        button.setFixedHeight(40)
        button.setStyleSheet("QPushButton { background-color: #555; color: white; border: none; }"
                             "QPushButton:hover { background-color: #666; }"
                             "QPushButton:checked { background-color: #777; }")
        if not selectable:
            button.setCheckable(False)
        else:
            button.setCheckable(True)
        button.clicked.connect(onClick)
        self.navigationBar.layout().addWidget(button)

    def switchTo(self, interface):
        """Switch to the specified interface in stackWidget"""
        self.stackWidget.setCurrentWidget(interface)

    def setCurrentNavItem(self, routeKey):
        """Set the current navigation item as selected"""
        for button in self.navigationBar.findChildren(QPushButton):
            if button.isCheckable():
                button.setChecked(button.objectName() == routeKey)

    def updateNavigationBar(self):
        """Update navigation bar to reflect current stackWidget index"""
        current_widget = self.stackWidget.currentWidget()
        if current_widget:
            self.setCurrentNavItem(current_widget.objectName())

    def showMessageBox(self):
        """Placeholder for About message box"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, "About", "This is the About page.")

# main
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())