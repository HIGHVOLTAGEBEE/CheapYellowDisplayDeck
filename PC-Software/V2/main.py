"""
main.py - Application entry point

Usage:
    python main.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from ui import SerialKeyboardUI

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = SerialKeyboardUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()