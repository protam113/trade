from PyQt6.QtWidgets import QApplication
import sys
from ui.layout.window import Window  

def main():
    app = QApplication(sys.argv) 
    window = Window()             
    window.show()                 
    sys.exit(app.exec())          

if __name__ == "__main__":
    main()
