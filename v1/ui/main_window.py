# main_window.py
from PyQt6.QtWidgets import QApplication
import sys
from layout.window import Window 

def main():
    app = QApplication(sys.argv)  
    window = Window()             
    window.show()                
    sys.exit(app.exec())         

if __name__ == "__main__":
    main()
