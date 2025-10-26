# login_form.py
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
import sys

def authenticate(username: str, password: str) -> bool:
    # Demo: username là "admin", password là "1234" thì login thành công
    return username == "admin" and password == "1234"

class LoginForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login Form")
        self.setFixedSize(300, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        self.label = QLabel("Please login")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if authenticate(username, password):  # check với auth.py
            QMessageBox.information(self, "Success", "Login successful!")
            # Nếu muốn, cậu có thể close form và mở main window:
            # self.close()
            # self.main_window = MainWindow()
            # self.main_window.show()
        else:
            QMessageBox.warning(self, "Error", "Username or password incorrect.")
