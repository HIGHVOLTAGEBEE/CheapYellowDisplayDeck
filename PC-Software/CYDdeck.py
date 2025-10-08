import sys
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QComboBox, QPushButton, QTextEdit, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QPalette, QColor, QFont
import keyboard
import time
import os
import subprocess
import shutil


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
                            
                            # Check for ready signal
                            if message == "CYD Deck Ready!" and not self.is_ready:
                                self.is_ready = True
                                self.ready_received.emit()
                            elif self.is_ready:
                                # Führe Kommandos nur aus wenn Ready-Signal empfangen wurde
                                self.process_keystroke(message)
                    except UnicodeDecodeError:
                        self.error_occurred.emit("Decoding error")
                time.sleep(0.01)
                
        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial error: {str(e)}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
    
    def process_keystroke(self, message):
        if message == "CYD Deck Ready!": return  # Ignoriere Ready-Signal
        """Process the received message and press the corresponding keys"""
        try:
            # Entferne Leerzeichen
            message = message.strip()
            # Check for EXECUTE command, format: EXECUTE+program_or_path
            parts = message.split('+')
            if parts and parts[0].upper() == 'EXECUTE' and len(parts) >= 2:
                prog = '+'.join(parts[1:]).strip()
                # Debug info
                self.message_received.emit(f"DEBUG: Execute command received: {prog}")
                try:
                    # Windows: try os.startfile first (works for file associations)
                    if os.name == 'nt':
                        try:
                            os.startfile(prog)
                        except Exception:
                            # Try to find in PATH
                            prog_path = shutil.which(prog)
                            if prog_path:
                                subprocess.Popen([prog_path], shell=False)
                            else:
                                # fallback to shell execution
                                subprocess.Popen(prog, shell=True)
                    else:
                        # POSIX: try to find executable in PATH
                        prog_path = shutil.which(prog)
                        if prog_path:
                            subprocess.Popen([prog_path])
                        else:
                            # fallback to shell execution (may require full path)
                            subprocess.Popen(prog, shell=True)

                    self.message_received.emit(f"Executing: {prog}")
                except Exception as e:
                    self.error_occurred.emit(f"Execute error: {str(e)}")
                return
            
            # Debug-Ausgabe
            self.message_received.emit(f"DEBUG: Processing '{message}'")
            
            # Teile die Nachricht bei '+'
            keys = message.split('+')
            
            # Convert special key names
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
            
            # Convert the keys
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
            
            # Debug output
            self.message_received.emit(f"DEBUG: Converted to {processed_keys}")
            
            # Small delay before key press
            time.sleep(0.05)
            
            # Drücke die Tastenkombination
            if len(processed_keys) == 1:
                keyboard.press_and_release(processed_keys[0])
                self.key_pressed.emit(f"Pressed: {processed_keys[0]}")
            else:
                # Kombiniere mehrere Tasten mit '+'
                combo = '+'.join(processed_keys)
                keyboard.press_and_release(combo)
                self.key_pressed.emit(f"Pressed: {combo}")
                
        except Exception as e:
            self.error_occurred.emit(f"Keystroke error: {str(e)}")
    
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

        # Port selection
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        port_label.setFont(QFont("Segoe UI", 10))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(30)
        self.update_ports()
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)

        # Baud rate selection
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud:")
        baud_label.setFont(QFont("Segoe UI", 10))
        self.baud_combo = QComboBox()
        self.baud_combo.setMinimumHeight(30)
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "1000000", "2000000"])
        self.baud_combo.setCurrentText("2000000")
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_combo)

        # Keyboard layout selection
        layout_layout = QHBoxLayout()
        layout_label = QLabel("Layout:")
        layout_label.setFont(QFont("Segoe UI", 10))
        self.layout_combo = QComboBox()
        self.layout_combo.setMinimumHeight(30)
        self.layout_combo.addItems(["Auto", "DE (German)", "US (English)", "FR (French)", 
                                    "ES (Spanish)", "IT (Italian)", "UK (English)"])
        self.layout_combo.setCurrentText("DE (German)")
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

        # Assemble layout
        main_layout.addLayout(port_layout)
        main_layout.addLayout(baud_layout)
        main_layout.addLayout(layout_layout)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(terminal_label)
        main_layout.addWidget(self.terminal)
        
    def update_ports(self):
        """Update the list of available COM ports"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(f"{port.device} - {port.description}")
            
    def start_serial(self):
        """Start the serial connection"""
        port = self.port_combo.currentText().split(' - ')[0]
        baudrate = int(self.baud_combo.currentText())
        
        # Extract keyboard layout code
        layout_text = self.layout_combo.currentText()
        layout_mapping = {
            "Auto": "auto",
            "DE (German)": "de",
            "US (English)": "us",
            "FR (French)": "fr",
            "ES (Spanish)": "es",
            "IT (Italian)": "it",
            "UK (English)": "uk"
        }
        keyboard_layout = layout_mapping.get(layout_text, "auto")
        
        if not port:
            self.append_terminal("Error: No port selected", "error")
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
        
        self.append_terminal(f"Connected to {port} @ {baudrate} baud", "success")
        self.append_terminal("Waiting for 'CYD Deck Ready!' signal...", "info")
        
    def stop_serial(self):
        """Stop the serial connection"""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait()
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.layout_combo.setEnabled(True)
        
        self.append_terminal("Connection closed", "info")
        
    def on_message_received(self, message):
        """Show received message in the terminal"""
        self.append_terminal(f"Received: {message}", "message")
        
    def on_key_pressed(self, key_info):
        """Show pressed key in the terminal"""
        self.append_terminal(key_info, "key")
    
    def on_ready(self):
        """Called when 'CYD Deck Ready!' is received"""
        self.append_terminal("✓ CYD Deck is ready! Commands will now be executed.", "success")
        
    def on_error(self, error):
        """Show errors in the terminal"""
        self.append_terminal(error, "error")
        
    def append_terminal(self, text, msg_type="info"):
        """Append text to the terminal with color coding"""
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
        """Close the serial connection on exit"""
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialKeyboardUI()
    window.show()
    sys.exit(app.exec())