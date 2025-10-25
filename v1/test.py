import sys
from PyQt6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)

    # import window class sau khi QApplication tồn tại
    from ui.layout.window import Window
    window = Window()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
