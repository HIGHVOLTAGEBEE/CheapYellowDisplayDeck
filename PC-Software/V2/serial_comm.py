"""
serial_comm.py - Serial communication thread

API:
    SerialThread(port, baudrate, layout_code)
    Signals:
        - message_received(str)
        - command_executed(str, bool, str)
        - error_occurred(str)
        - ready_received()
    Methods:
        - start() / stop()
"""

import serial
import time
from PyQt6.QtCore import QThread, pyqtSignal
from kb_handler import KeyboardLayoutManager, CommandParser, KeyExecutor, CommandType

class SerialThread(QThread):
    message_received = pyqtSignal(str)
    command_executed = pyqtSignal(str, bool, str)
    error_occurred = pyqtSignal(str)
    ready_received = pyqtSignal()
    
    def __init__(self, port: str, baudrate: int, layout_code: str):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.serial_connection = None
        self.is_ready = False
        self.layout_manager = KeyboardLayoutManager(layout_code)
        self.parser = CommandParser(self.layout_manager)
        self.executor = KeyExecutor()
    
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            
            while self.running:
                if self.serial_connection.in_waiting > 0:
                    try:
                        raw_message = self.serial_connection.readline()
                        message = raw_message.decode('utf-8', errors='ignore').strip()
                        
                        if not message:
                            continue
                        
                        self.message_received.emit(message)
                        
                        if message in CommandParser.READY_SIGNALS and not self.is_ready:
                            self.is_ready = True
                            self.ready_received.emit()
                        elif self.is_ready:
                            self._process_command(message)
                    except UnicodeDecodeError as e:
                        self.error_occurred.emit(f"Decode error: {str(e)}")
                
                time.sleep(0.01)
        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial error: {str(e)}")
        finally:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
    
    def _process_command(self, message: str):
        try:
            command = self.parser.parse(message)
            if command.command_type == CommandType.READY_SIGNAL:
                return
            success, result_message = self.executor.execute(command)
            self.command_executed.emit(command.raw_input, success, result_message)
        except Exception as e:
            self.error_occurred.emit(f"Command error: {str(e)}")
    
    def stop(self):
        self.running = False