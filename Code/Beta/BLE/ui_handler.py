import time, json, os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QComboBox, QPushButton, QTextEdit, QLabel, 
                             QGroupBox, QLineEdit, QCheckBox)
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt
from bluetooth_comm import BluetoothThread

class BluetoothKeyboardUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bt_thread = None
        self.last_key_pressed = "None"
        self.commands_executed = 0
        self.config_file = "config.json"
        self.config = self._load_config()
        
        self.init_ui()
        self._restore_settings()
        self._start_bluetooth()
    
    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except: pass
        return {"layout": "Deutsch (DE)"}
    
    def _save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except: pass
    
    def init_ui(self):
        self.setWindowTitle("CYD DECK")
        self.setGeometry(100, 100, 700, 650)
        self._apply_palette()
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(self._create_header())
        layout.addWidget(self._create_settings_group())
        layout.addWidget(self._create_status_group())
        layout.addWidget(self._create_test_group())
        layout.addWidget(self._create_terminal_group())
    
    def _apply_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(28, 28, 28))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(38, 38, 38))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(200, 160, 0))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QGroupBox {
                font-weight: 600; font-size: 11px; color: #888;
                border: 1px solid #333; border-radius: 8px;
                margin-top: 10px; padding-top: 14px; background-color: #1c1c1c;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 3px 10px; background-color: #c8a000;
                border-radius: 4px; color: #000; left: 12px;
            }
            QComboBox, QLineEdit {
                border: 1px solid #444; border-radius: 6px;
                padding: 6px 10px; background-color: #262626;
                color: #ddd; font-size: 11px;
            }
            QComboBox:hover, QLineEdit:focus { border-color: #c8a000; }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; border: none; }
            QCheckBox { color: #aaa; spacing: 6px; }
            QCheckBox::indicator {
                width: 16px; height: 16px; border: 1px solid #444;
                border-radius: 3px; background-color: #262626;
            }
            QCheckBox::indicator:checked { background-color: #c8a000; border-color: #c8a000; }
        """)
    
    def _create_header(self):
        header = QWidget()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(2)
        
        title_layout = QHBoxLayout()
        title = QLabel("ESP32 Keyboard Bridge")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #c8a000;")
        
        version = QLabel("by HIGHVOLTAGEBEE")
        version.setFont(QFont("Segoe UI", 9))
        version.setStyleSheet("color: #666; padding: 8px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(version)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        return header
    
    def _create_settings_group(self):
        group = QGroupBox("Settings")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        layout_layout = QHBoxLayout()
        layout_label = QLabel("Layout:")
        layout_label.setMinimumWidth(80)
        layout_label.setStyleSheet("color: #aaa; font-weight: 500;")
        self.layout_combo = QComboBox()
        self.layout_combo.setMinimumHeight(32)
        self.layout_combo.addItems(["Deutsch (DE)", "English (US)", "Français (FR)"])
        self.layout_combo.currentTextChanged.connect(self._on_layout_changed)
        layout_layout.addWidget(layout_label)
        layout_layout.addWidget(self.layout_combo)
        
        layout.addLayout(layout_layout)
        group.setLayout(layout)
        return group
    
    def _create_status_group(self):
        group = QGroupBox("Status")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        conn_layout = QHBoxLayout()
        self.device_label = QLabel("Device: Searching...")
        self.device_label.setStyleSheet("color: #888; font-size: 10px;")
        conn_layout.addWidget(self.device_label)
        
        self.status_label = QLabel("Disconnected")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #666;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        conn_layout.addWidget(self.status_label)
        
        stats_layout = QHBoxLayout()
        self.last_key_label = QLabel("Last: None")
        self.last_key_label.setStyleSheet("color: #777; font-size: 10px;")
        self.commands_label = QLabel("Commands: 0")
        self.commands_label.setStyleSheet("color: #777; font-size: 10px;")
        stats_layout.addWidget(self.last_key_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.commands_label)
        
        layout.addLayout(conn_layout)
        layout.addLayout(stats_layout)
        group.setLayout(layout)
        return group
    
    def _create_test_group(self):
        group = QGroupBox("Test Commands")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        input_layout = QHBoxLayout()
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Enter command: CTRL+C, WIN+D, \"Hello\"")
        self.test_input.setMinimumHeight(36)
        self.test_input.returnPressed.connect(self._send_test)
        
        test_btn = QPushButton("Send")
        test_btn.setMinimumHeight(36)
        test_btn.setMinimumWidth(80)
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #c8a000; color: #000; border-radius: 6px; 
                font-weight: 600; font-size: 11px;
            }
            QPushButton:hover { background-color: #e0b800; }
        """)
        test_btn.clicked.connect(self._send_test)
        
        input_layout.addWidget(self.test_input)
        input_layout.addWidget(test_btn)
        
        quick_layout = QHBoxLayout()
        for label, cmd in [("CTRL+C", "CTRL+C"), ("CTRL+V", "CTRL+V"), ("WIN+D", "WIN+D")]:
            btn = QPushButton(label)
            btn.setMinimumHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #333; color: #ddd; border-radius: 5px; 
                    font-weight: 600; font-size: 10px;
                }
                QPushButton:hover { background-color: #444; }
            """)
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
        self.show_debug = QCheckBox("Debug")
        self.show_debug.setStyleSheet("color: #888; font-size: 10px;")
        
        clear_btn = QPushButton("Clear")
        clear_btn.setMinimumWidth(100)
        clear_btn.setMinimumHeight(32)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #333; color: #ddd; border-radius: 6px;
                font-weight: 600; font-size: 10px;
            }
            QPushButton:hover { background-color: #444; }
        """)
        clear_btn.clicked.connect(lambda: self.terminal.clear())
        
        toolbar.addWidget(self.show_debug)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 9))
        self.terminal.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a; color: #aaa;
                border: 1px solid #333; border-radius: 6px; padding: 10px;
            }
        """)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.terminal)
        group.setLayout(layout)
        return group
    
    def _restore_settings(self):
        self.layout_combo.setCurrentText(self.config.get("layout", "Deutsch (DE)"))
    
    def _start_bluetooth(self):
        layout_map = {"Deutsch (DE)": "de", "English (US)": "us", "Français (FR)": "fr"}
        layout_code = layout_map.get(self.layout_combo.currentText(), "us")
        
        self.bt_thread = BluetoothThread(layout_code)
        self.bt_thread.message_received.connect(self._on_message)
        self.bt_thread.command_executed.connect(self._on_command)
        self.bt_thread.error_occurred.connect(self._on_error)
        self.bt_thread.ready_received.connect(self._on_ready)
        self.bt_thread.telemetry_sent.connect(self._on_telemetry_sent)
        self.bt_thread.device_found.connect(self._on_device_found)
        self.bt_thread.connected.connect(self._on_connected)
        self.bt_thread.disconnected.connect(self._on_disconnected)
        self.bt_thread.start()
        
        self._log("Bluetooth thread started", "info")
    
    def _on_layout_changed(self):
        self.config["layout"] = self.layout_combo.currentText()
        self._save_config()
    
    def _send_test(self):
        if not self.bt_thread or not self.bt_thread.is_ready:
            self._log("Not ready", "warning")
            return
        cmd = self.test_input.text().strip()
        if cmd:
            self.bt_thread.send_command(cmd)
            self.test_input.clear()
    
    def _quick_test(self, cmd: str):
        if self.bt_thread and self.bt_thread.is_ready:
            self.bt_thread.send_command(cmd)
    
    def _on_message(self, msg: str):
        if self.show_debug.isChecked():
            self._log(f"RX: {msg}", "debug")
    
    def _on_command(self, cmd: str, success: bool, msg: str):
        self.commands_executed += 1
        self.commands_label.setText(f"Commands: {self.commands_executed}")
        
        if "Pressed:" in msg:
            self.last_key_pressed = msg.split("Pressed: ")[1]
        elif "Typed:" in msg:
            self.last_key_pressed = msg.split("Typed: ")[1]
        
        self.last_key_label.setText(f"Last: {self.last_key_pressed}")
        self._log(msg, "success" if success else "error")
    
    def _on_device_found(self, name: str, address: str):
        self.device_label.setText(f"Device: {name}")
        self._log(f"Found: {name} ({address})", "info")
    
    def _on_connected(self):
        self.status_label.setText("Connected")
        self.status_label.setStyleSheet("color: #c8a000;")
        self._log("Connected to device", "success")
    
    def _on_ready(self):
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #c8a000;")
        self._log("Device ready", "success")
    
    def _on_disconnected(self):
        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: #666;")
        self.device_label.setText("Device: Searching...")
        self._log("Disconnected, searching...", "info")
    
    def _on_error(self, err: str):
        self._log(err, "error")
    
    def _on_telemetry_sent(self, packet: str):
        if self.show_debug.isChecked():
            safe_packet = packet.replace('<', '&lt;').replace('>', '&gt;')
            self._log(f"TX: {safe_packet}", "telemetry")
    
    def _log(self, text: str, msg_type: str = "info"):
        colors = {
            "success": "#c8a000", 
            "error": "#cc4444", 
            "warning": "#c8a000", 
            "info": "#888", 
            "debug": "#666", 
            "telemetry": "#555"
        }
        color = colors.get(msg_type, colors["info"])
        ts = time.strftime("%H:%M:%S")
        self.terminal.append(f'<span style="color:#555;">[{ts}]</span> '
                           f'<span style="color:{color};">{text}</span>')
    
    def closeEvent(self, event):
        if self.bt_thread and self.bt_thread.isRunning():
            self.bt_thread.stop()
            self.bt_thread.wait()
        event.accept()