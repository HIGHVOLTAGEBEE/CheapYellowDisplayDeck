import serial, time, psutil, subprocess
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from kb_handler import KeyboardLayoutManager, CommandParser, KeyExecutor, CommandType

class TelemetryBuffer:
    """Exponential Moving Average filter with rate limiting for smooth telemetry values"""
    def __init__(self, alpha=0.03, max_change_per_sec=5.0):
        self.alpha = alpha  # Smoothing factor (0.0-1.0, higher = more responsive)
        self.max_change_per_sec = max_change_per_sec  # Max % change per second
        self.cpu = None
        self.gpu = None
        self.ram = None
        self.last_update = time.time()
    
    def _limit_change(self, new_val, old_val, dt):
        """Limit the rate of change based on time delta"""
        max_change = self.max_change_per_sec * dt
        diff = new_val - old_val
        if abs(diff) > max_change:
            return old_val + (max_change if diff > 0 else -max_change)
        return new_val
    
    def update(self, cpu, gpu, ram):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now
        
        if self.cpu is None:
            self.cpu, self.gpu, self.ram = cpu, gpu, ram
        else:
            # Apply EMA smoothing
            smooth_cpu = self.alpha * cpu + (1 - self.alpha) * self.cpu
            smooth_gpu = self.alpha * gpu + (1 - self.alpha) * self.gpu
            smooth_ram = self.alpha * ram + (1 - self.alpha) * self.ram
            
            # Apply rate limiting
            self.cpu = self._limit_change(smooth_cpu, self.cpu, dt)
            self.gpu = self._limit_change(smooth_gpu, self.gpu, dt)
            self.ram = self._limit_change(smooth_ram, self.ram, dt)
        
        return self.cpu, self.gpu, self.ram

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
        self.telemetry_buffer = TelemetryBuffer(alpha=0.3, max_change_per_sec=10.0)
    
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            self.running = True
            
            while self.running:
                if time.time() - self.last_telemetry >= 0.01 and self.is_ready:
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
            cpu_raw = psutil.cpu_percent(interval=None)
            ram_raw = psutil.virtual_memory().percent
            gpu_raw = self._get_gpu()
            
            cpu, gpu, ram = self.telemetry_buffer.update(cpu_raw, gpu_raw, ram_raw)
            
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