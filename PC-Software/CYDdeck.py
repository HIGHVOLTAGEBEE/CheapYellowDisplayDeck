import sys
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QTextEdit, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QPalette, QColor, QFont
import keyboard
import time


class SerialThread(QThread):
    message_received = pyqtSignal(str)
    key_pressed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    ready_received = pyqtSignal()
    
    def __init__(self, port, baudrate, keyboard_layout):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.keyboard_layout = keyboard_layout
        self.running = False
        self.serial_connection = None
        self.is_ready = False
        
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            
            while self.running:
                if self.serial_connection.in_waiting > 0:
                    try:
                        message = self.serial_connection.readline().decode('utf-8').strip()
                        if message:
                            self.message_received.emit(message)
                            
                            # Prüfe auf Ready-Signal
                            if message == "CYD Deck Ready!" and not self.is_ready:
                                self.is_ready = True
                                self.ready_received.emit()
                            elif self.is_ready:
                                # Führe Kommandos nur aus wenn Ready-Signal empfangen wurde
                                self.process_keystroke(message)
                    except UnicodeDecodeError:
                        self.error_occurred.emit("Dekodierungsfehler")
                time.sleep(0.01)
                
        except serial.SerialException as e:
            self.error_occurred.emit(f"Serieller Fehler: {str(e)}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
    
    def process_keystroke(self, message):
        if message == "CYD Deck Ready!": return  # Ignoriere Ready-Signal
        """Verarbeitet die empfangene Nachricht und drückt die entsprechenden Tasten"""
        try:
            # Entferne Leerzeichen
            message = message.strip()
            
            # Debug-Ausgabe
            self.message_received.emit(f"DEBUG: Verarbeite '{message}'")
            
            # Teile die Nachricht bei '+'
            keys = message.split('+')
            
            # Konvertiere spezielle Tastenbezeichnungen
            key_mapping = {
                'CTRL': 'ctrl',
                'CONTROL': 'ctrl',
                'ALT': 'alt',
                'SHIFT': 'shift',
                'WIN': 'win',
                'WINDOWS': 'win',
                'CMD': 'win',  # Auf Windows wird CMD zu WIN
                'ENTER': 'enter',
                'RETURN': 'enter',
                'SPACE': 'space',
                'TAB': 'tab',
                'ESC': 'esc',
                'ESCAPE': 'esc',
                'BACKSPACE': 'backspace',
                'DELETE': 'delete',
                'DEL': 'delete',
                'UP': 'up',
                'DOWN': 'down',
                'LEFT': 'left',
                'RIGHT': 'right',
                'HOME': 'home',
                'END': 'end',
                'PAGEUP': 'page up',
                'PAGEDOWN': 'page down',
                'INSERT': 'insert',
                'F1': 'f1', 'F2': 'f2', 'F3': 'f3', 'F4': 'f4',
                'F5': 'f5', 'F6': 'f6', 'F7': 'f7', 'F8': 'f8',
                'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12'
            }
            
            # Konvertiere die Tasten
            processed_keys = []
            for key in keys:
                key = key.strip()
                # Prüfe ob es eine spezielle Taste ist (case-insensitive)
                key_upper = key.upper()
                if key_upper in key_mapping:
                    processed_keys.append(key_mapping[key_upper])
                else:
                    # Konvertiere zu Kleinbuchstaben für normale Tasten
                    processed_keys.append(key.lower())
            
            # Debug-Ausgabe
            self.message_received.emit(f"DEBUG: Konvertiert zu {processed_keys}")
            
            # Kleine Verzögerung vor dem Tastendruck
            time.sleep(0.05)
            
            # Drücke die Tastenkombination
            if len(processed_keys) == 1:
                keyboard.press_and_release(processed_keys[0])
                self.key_pressed.emit(f"Gedrückt: {processed_keys[0]}")
            else:
                # Kombiniere mehrere Tasten mit '+'
                combo = '+'.join(processed_keys)
                keyboard.press_and_release(combo)
                self.key_pressed.emit(f"Gedrückt: {combo}")
                
        except Exception as e:
            self.error_occurred.emit(f"Tastenfehler: {str(e)}")
    
    def stop(self):
        self.running = False


class SerialKeyboardUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("ESP32 Serial to Keyboard")
        self.setGeometry(100, 100, 500, 400)
        
        # Dark Mode Palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        self.setPalette(palette)
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Port Auswahl
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        port_label.setFont(QFont("Segoe UI", 10))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(30)
        self.update_ports()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        
        # Baud Rate Auswahl
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud:")
        baud_label.setFont(QFont("Segoe UI", 10))
        self.baud_combo = QComboBox()
        self.baud_combo.setMinimumHeight(30)
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud_combo.setCurrentText("115200")
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_combo)
        
        # Tastatur-Layout Auswahl
        layout_layout = QHBoxLayout()
        layout_label = QLabel("Layout:")
        layout_label.setFont(QFont("Segoe UI", 10))
        self.layout_combo = QComboBox()
        self.layout_combo.setMinimumHeight(30)
        self.layout_combo.addItems(["Auto", "DE (Deutsch)", "US (English)", "FR (Français)", 
                                    "ES (Español)", "IT (Italiano)", "UK (English)"])
        self.layout_combo.setCurrentText("DE (Deutsch)")
        layout_layout.addWidget(layout_label)
        layout_layout.addWidget(self.layout_combo)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.setMinimumHeight(35)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.start_button.clicked.connect(self.start_serial)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.stop_button.clicked.connect(self.stop_serial)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        
        # Terminal
        terminal_label = QLabel("Terminal:")
        terminal_label.setFont(QFont("Segoe UI", 10))
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 9))
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        # Layout zusammensetzen
        main_layout.addLayout(port_layout)
        main_layout.addLayout(baud_layout)
        main_layout.addLayout(layout_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(terminal_label)
        main_layout.addWidget(self.terminal)
        
    def update_ports(self):
        """Aktualisiert die Liste der verfügbaren COM-Ports"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")
            
    def start_serial(self):
        """Startet die serielle Verbindung"""
        port = self.port_combo.currentText().split(' - ')[0]
        baudrate = int(self.baud_combo.currentText())
        
        # Extrahiere Tastatur-Layout Code
        layout_text = self.layout_combo.currentText()
        layout_mapping = {
            "Auto": "auto",
            "DE (Deutsch)": "de",
            "US (English)": "us",
            "FR (Français)": "fr",
            "ES (Español)": "es",
            "IT (Italiano)": "it",
            "UK (English)": "uk"
        }
        keyboard_layout = layout_mapping.get(layout_text, "auto")
        
        if not port:
            self.append_terminal("Fehler: Kein Port ausgewählt", "error")
            return
        
        self.serial_thread = SerialThread(port, baudrate, keyboard_layout)
        self.serial_thread.message_received.connect(self.on_message_received)
        self.serial_thread.key_pressed.connect(self.on_key_pressed)
        self.serial_thread.error_occurred.connect(self.on_error)
        self.serial_thread.ready_received.connect(self.on_ready)
        self.serial_thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.layout_combo.setEnabled(False)
        
        self.append_terminal(f"Verbunden mit {port} @ {baudrate} baud", "success")
        self.append_terminal("Warte auf 'CYD Deck Ready!' Signal...", "info")
        
    def stop_serial(self):
        """Stoppt die serielle Verbindung"""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait()
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.layout_combo.setEnabled(True)
        
        self.append_terminal("Verbindung getrennt", "info")
        
    def on_message_received(self, message):
        """Zeigt empfangene Nachricht im Terminal"""
        self.append_terminal(f"Empfangen: {message}", "message")
        
    def on_key_pressed(self, key_info):
        """Zeigt gedrückte Taste im Terminal"""
        self.append_terminal(key_info, "key")
    
    def on_ready(self):
        """Wird aufgerufen wenn 'CYD Deck Ready!' empfangen wurde"""
        self.append_terminal("✓ CYD Deck ist bereit! Kommandos werden jetzt ausgeführt.", "success")
        
    def on_error(self, error):
        """Zeigt Fehler im Terminal"""
        self.append_terminal(error, "error")
        
    def append_terminal(self, text, msg_type="info"):
        """Fügt Text zum Terminal hinzu mit Farbcodierung"""
        colors = {
            "message": "#61afef",  # Blau
            "key": "#98c379",      # Grün
            "error": "#e06c75",    # Rot
            "success": "#98c379",  # Grün
            "info": "#abb2bf"      # Grau
        }
        color = colors.get(msg_type, "#abb2bf")
        self.terminal.append(f'<span style="color: {color};">{text}</span>')
        
    def closeEvent(self, event):
        """Schließt die serielle Verbindung beim Beenden"""
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialKeyboardUI()
    window.show()
    sys.exit(app.exec())