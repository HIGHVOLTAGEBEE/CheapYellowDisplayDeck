"""
ui.py - PyQt6 GUI

API:
    SerialKeyboardUI() - Main window
"""

import serial.tools.list_ports
import time
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QComboBox, QPushButton, QTextEdit, QLabel, 
                             QGroupBox, QLineEdit, QCheckBox)
from PyQt6.QtGui import QPalette, QColor, QFont
from serial_comm import SerialThread
from kb_handler import CommandParser

class SerialKeyboardUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.last_key_pressed = "None"
        self.commands_executed = 0
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("ESP32 Keyboard Bridge v2.1")
        self.setGeometry(100, 100, 750, 700)
        self._apply_palette()
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        layout.addWidget(self._create_header())
        layout.addWidget(self._create_connection_group())
        layout.addWidget(self._create_status_group())
        layout.addWidget(self._create_test_group())
        layout.addWidget(self._create_terminal_group())
    
    def _apply_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(15, 23, 42))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(241, 245, 249))
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 41, 59))
        palette.setColor(QPalette.ColorRole.Text, QColor(241, 245, 249))
        palette.setColor(QPalette.ColorRole.Button, QColor(51, 65, 85))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(241, 245, 249))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(139, 92, 246))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600; font-size: 13px; color: #e2e8f0;
                border: 2px solid #334155; border-radius: 12px;
                margin-top: 12px; padding-top: 16px; background-color: #1e293b;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 4px 12px; background-color: #8b5cf6;
                border-radius: 6px; color: white; left: 16px;
            }
            QComboBox, QLineEdit {
                border: 2px solid #475569; border-radius: 8px;
                padding: 6px 12px; background-color: #334155;
                color: #f1f5f9; font-size: 12px;
            }
            QComboBox:hover, QLineEdit:focus { border-color: #8b5cf6; }
            QCheckBox { color: #cbd5e1; spacing: 8px; }
            QCheckBox::indicator {
                width: 18px; height: 18px; border: 2px solid #475569;
                border-radius: 4px; background-color: #334155;
            }
            QCheckBox::indicator:checked { background-color: #8b5cf6; border-color: #8b5cf6; }
        """)
    
    def _create_header(self):
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        
        title_layout = QHBoxLayout()
        title = QLabel("⌨️  ESP32 Keyboard Bridge")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #8b5cf6; padding: 8px 0;")
        
        version = QLabel("v2.1")
        version.setFont(QFont("Segoe UI", 10))
        version.setStyleSheet("color: #64748b; padding: 12px 8px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(version)
        title_layout.addStretch()
        
        author = QLabel("by HIGHVOLTAGEBEE")
        author.setFont(QFont("Segoe UI", 9))
        author.setStyleSheet("color: #64748b; font-style: italic;")
        
        layout.addLayout(title_layout)
        layout.addWidget(author)
        return header
    
    def _create_connection_group(self):
        group = QGroupBox("Connection Settings")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        port_label.setMinimumWidth(120)
        port_label.setStyleSheet("color: #cbd5e1; font-weight: 500;")
        
        self.port_combo = QComboBox()
        self.port_combo.setMinimumHeight(36)
        self._update_ports()
        
        refresh_btn = QPushButton("🔄 ")
        refresh_btn.setMaximumWidth(50)
        refresh_btn.setMinimumHeight(36)
        refresh_btn.clicked.connect(self._update_ports)
        
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(refresh_btn)
        
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud Rate:")
        baud_label.setMinimumWidth(120)
        baud_label.setStyleSheet("color: #cbd5e1; font-weight: 500;")
        
        self.baud_combo = QComboBox()
        self.baud_combo.setMinimumHeight(36)
        self.baud_combo.addItems(["9600", "115200", "2000000"])
        self.baud_combo.setCurrentText("2000000")
        
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_combo)
        
        layout_layout = QHBoxLayout()
        layout_label = QLabel("Keyboard Layout:")
        layout_label.setMinimumWidth(120)
        layout_label.setStyleSheet("color: #cbd5e1; font-weight: 500;")
        
        self.layout_combo = QComboBox()
        self.layout_combo.setMinimumHeight(36)
        self.layout_combo.addItems(["Deutsch (DE)", "English (US)", "Français (FR)"])
        
        layout_layout.addWidget(layout_label)
        layout_layout.addWidget(self.layout_combo)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.start_button = QPushButton("▶  Start Connection")
        self.start_button.setMinimumHeight(44)
        self.start_button.clicked.connect(self._start_serial)
        
        self.stop_button = QPushButton("⏹  Stop Connection")
        self.stop_button.setMinimumHeight(44)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop_serial)
        
        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.stop_button)
        
        layout.addLayout(port_layout)
        layout.addLayout(baud_layout)
        layout.addLayout(layout_layout)
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_status_group(self):
        group = QGroupBox("Status")
        layout = QHBoxLayout()
        
        self.status_label = QLabel("⚫  Disconnected")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #64748b;")
        
        self.last_key_label = QLabel("Last: None")
        self.last_key_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        
        self.commands_label = QLabel("Commands: 0")
        self.commands_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.last_key_label)
        layout.addWidget(QLabel("  •  "))
        layout.addWidget(self.commands_label)
        
        group.setLayout(layout)
        return group
    
    def _create_test_group(self):
        group = QGroupBox("Test Commands")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        input_layout = QHBoxLayout()
        
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Enter command: CTRL+C, WIN+D, \"Hello\"")
        self.test_input.setMinimumHeight(40)
        self.test_input.returnPressed.connect(self._send_test)
        
        test_btn = QPushButton("Send")
        test_btn.setMinimumHeight(40)
        test_btn.setMinimumWidth(90)
        test_btn.clicked.connect(self._send_test)
        
        input_layout.addWidget(self.test_input)
        input_layout.addWidget(test_btn)
        
        quick_layout = QHBoxLayout()
        for label, cmd in [("CTRL+C", "CTRL+C"), ("CTRL+V", "CTRL+V"), ("WIN+D", "WIN+D")]:
            btn = QPushButton(label)
            btn.setMinimumHeight(34)
            btn.clicked.connect(lambda _, c=cmd: self._quick_test(c))
            quick_layout.addWidget(btn)
        
        layout.addLayout(input_layout)
        layout.addLayout(quick_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_terminal_group(self):
        group = QGroupBox("Terminal")
        layout = QVBoxLayout()
        
        toolbar = QHBoxLayout()
        self.show_debug = QCheckBox("Show Debug")
        self.show_debug.setStyleSheet("color: #94a3b8; font-size: 11px;")
        
        clear_btn = QPushButton("Clear")
        clear_btn.setMaximumWidth(80)
        clear_btn.clicked.connect(lambda: self.terminal.clear())
        
        toolbar.addWidget(self.show_debug)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 9))
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a; color: #cbd5e1;
                border: 2px solid #334155; border-radius: 8px; padding: 12px;
            }
        """)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.terminal)
        group.setLayout(layout)
        return group
    
    def _update_ports(self):
        self.port_combo.clear()
        for port in serial.tools.list_ports.comports():
            self.port_combo.addItem(f"{port.device} - {port.description}")
    
    def _start_serial(self):
        port_text = self.port_combo.currentText()
        if not port_text:
            self._log("❌ No port selected", "error")
            return
        
        port = port_text.split(' - ')[0]
        baudrate = int(self.baud_combo.currentText())
        layout_map = {"Deutsch (DE)": "de", "English (US)": "us", "Français (FR)": "fr"}
        layout_code = layout_map.get(self.layout_combo.currentText(), "us")
        
        self.serial_thread = SerialThread(port, baudrate, layout_code)
        self.serial_thread.message_received.connect(self._on_message)
        self.serial_thread.command_executed.connect(self._on_command)
        self.serial_thread.error_occurred.connect(self._on_error)
        self.serial_thread.ready_received.connect(self._on_ready)
        self.serial_thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.layout_combo.setEnabled(False)
        
        self.status_label.setText("🟡  Connecting...")
        self.status_label.setStyleSheet("color: #fbbf24;")
        self._log(f"📡  Connecting to {port} @ {baudrate}", "info")
    
    def _stop_serial(self):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.layout_combo.setEnabled(True)
        
        self.status_label.setText("⚫  Disconnected")
        self.status_label.setStyleSheet("color: #64748b;")
        self._log("📴  Connection closed", "info")
    
    def _send_test(self):
        if not self.serial_thread or not self.serial_thread.is_ready:
            self._log("⚠  Not ready", "warning")
            return
        cmd = self.test_input.text().strip()
        if cmd:
            self.serial_thread._process_command(cmd)
            self.test_input.clear()
    
    def _quick_test(self, cmd: str):
        if self.serial_thread and self.serial_thread.is_ready:
            self.serial_thread._process_command(cmd)
    
    def _on_message(self, msg: str):
        if self.show_debug.isChecked() and msg not in CommandParser.READY_SIGNALS:
            self._log(f"📥  {msg}", "debug")
    
    def _on_command(self, cmd: str, success: bool, msg: str):
        self.commands_executed += 1
        self.commands_label.setText(f"Commands: {self.commands_executed}")
        
        if "Pressed:" in msg:
            self.last_key_pressed = msg.split("Pressed: ")[1]
        elif "Typed:" in msg:
            self.last_key_pressed = msg.split("Typed: ")[1]
        
        self.last_key_label.setText(f"Last: {self.last_key_pressed}")
        self._log(f"{'✅' if success else '❌'}  {msg}", "success" if success else "error")
    
    def _on_ready(self):
        self.status_label.setText("🟢  Connected & Ready")
        self.status_label.setStyleSheet("color: #22c55e;")
        self._log("✅  Device ready", "success")
    
    def _on_error(self, err: str):
        self._log(f"❌  {err}", "error")
    
    def _log(self, text: str, msg_type: str = "info"):
        colors = {"success": "#22c55e", "error": "#ef4444", "warning": "#f59e0b", 
                  "info": "#94a3b8", "debug": "#a78bfa"}
        color = colors.get(msg_type, colors["info"])
        ts = time.strftime("%H:%M:%S")
        self.terminal.append(f'<span style="color:#64748b;">[{ts}]</span> '
                           f'<span style="color:{color};">{text}</span>')
    
    def closeEvent(self, event):
        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait()
        event.accept()