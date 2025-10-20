import serial, time, psutil, subprocess
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from kb_handler import KeyboardLayoutManager, CommandParser, KeyExecutor, CommandType

class SerialThread(QThread):
    message_received = pyqtSignal(str)
    command_executed = pyqtSignal(str, bool, str)
    error_occurred = pyqtSignal(str)
    ready_received = pyqtSignal()
    telemetry_sent = pyqtSignal(str)
    
    def __init__(self, port: str, baudrate: int, layout_code: str):
        super().__init__()
        self.port, self.baudrate = port, baudrate
        self.running, self.is_ready = False, False
        self.serial_connection = None
        self.layout_manager = KeyboardLayoutManager(layout_code)
        self.parser = CommandParser(self.layout_manager)
        self.executor = KeyExecutor()
        self.last_telemetry = 0
    
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            
            while self.running:
                if time.time() - self.last_telemetry >= 1 and self.is_ready:
                    self._send_telemetry()
                    self.last_telemetry = time.time()
                
                if self.serial_connection.in_waiting > 0:
                    try:
                        message = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
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
    
    def _send_telemetry(self):
        if not (self.serial_connection and self.serial_connection.is_open):
            return
        
        try:
            now = datetime.now()
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            gpu = self._get_gpu()
            packet = f"<T|{now:%H:%M:%S}|{now:%d.%m.%Y}|{cpu:.1f}|{gpu:.1f}|{ram:.1f}>"
            self.serial_connection.write((packet + "\n").encode('utf-8'))
            self.telemetry_sent.emit(packet)
        except Exception:
            pass
    
    def _get_gpu(self):
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                return gpus[0].load * 100
        except Exception:
            pass
        
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=0.5
            )
            if result.returncode == 0:
                return float(result.stdout.strip().split('\n')[0])
        except Exception:
            pass
        
        return 0.0
    
    def _process_command(self, message: str):
        try:
            command = self.parser.parse(message)
            if command.command_type == CommandType.READY_SIGNAL:
                return
            success, result = self.executor.execute(command)
            self.command_executed.emit(command.raw_input, success, result)
        except Exception as e:
            self.error_occurred.emit(f"Command error: {str(e)}")
    
    def stop(self):
        self.running = False