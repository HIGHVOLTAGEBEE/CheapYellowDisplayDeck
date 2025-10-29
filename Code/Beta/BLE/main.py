import sys
import traceback
from PyQt6.QtWidgets import QApplication

try:
    from ui_handler import BluetoothKeyboardUI
    print("UI import successful")
except Exception as e:
    print(f"Failed to import UI: {e}")
    traceback.print_exc()
    sys.exit(1)

def main():
    try:
        print("Starting application...")
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        print("Creating window...")
        window = BluetoothKeyboardUI()
        print("Showing window...")
        window.show()
        print("UI visible, entering event loop")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error in main: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()