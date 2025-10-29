#!/usr/bin/env python3
"""
CYD Deck BLE Communication Module (bluetooth_comm.py)
Compatible with existing UI and command handler
Install: pip install bleak psutil GPUtil PyQt6
"""

import asyncio
import time
import psutil
import subprocess
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from bleak import BleakClient, BleakScanner

SERVICE_UUID="4fafc201-1fb5-459e-8fcc-c5c9c331914b"
RX_CHAR_UUID="beb5483e-36e1-4688-b7f5-ea07361b26a8"
TX_CHAR_UUID="6e400003-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_NAME="CYD_Deck"

class TelemetryBuffer:
    def __init__(self,alpha=0.3,max_change_per_sec=10.0):
        self.alpha=alpha
        self.max_change_per_sec=max_change_per_sec
        self.cpu=None
        self.gpu=None
        self.ram=None
        self.last_update=time.time()
    
    def _limit_change(self,new_val,old_val,dt):
        max_change=self.max_change_per_sec*dt
        diff=new_val-old_val
        if abs(diff)>max_change:
            return old_val+(max_change if diff>0 else -max_change)
        return new_val
    
    def update(self,cpu,gpu,ram):
        now=time.time()
        dt=now-self.last_update
        self.last_update=now
        
        if self.cpu is None:
            self.cpu,self.gpu,self.ram=cpu,gpu,ram
        else:
            smooth_cpu=self.alpha*cpu+(1-self.alpha)*self.cpu
            smooth_gpu=self.alpha*gpu+(1-self.alpha)*self.gpu
            smooth_ram=self.alpha*ram+(1-self.alpha)*self.ram
            
            self.cpu=self._limit_change(smooth_cpu,self.cpu,dt)
            self.gpu=self._limit_change(smooth_gpu,self.gpu,dt)
            self.ram=self._limit_change(smooth_ram,self.ram,dt)
        
        return self.cpu,self.gpu,self.ram

class BluetoothThread(QThread):
    message_received=pyqtSignal(str)
    command_executed=pyqtSignal(str,bool,str)
    error_occurred=pyqtSignal(str)
    ready_received=pyqtSignal()
    telemetry_sent=pyqtSignal(str)
    device_found=pyqtSignal(str,str)
    connected=pyqtSignal()
    disconnected=pyqtSignal()
    
    def __init__(self,layout_code:str='us'):
        super().__init__()
        self.layout_code=layout_code
        self.running=False
        self.is_ready=False
        self.client=None
        self.device_address=None
        self.loop=None
        self.last_telemetry=0
        self.telemetry_buffer=TelemetryBuffer(alpha=0.3,max_change_per_sec=10.0)
        self.message_buffer=""
        
        # Import command handlers only when needed
        try:
            from command_handler import KeyboardLayoutManager,CommandParser,KeyExecutor,CommandType
            self.layout_manager=KeyboardLayoutManager(layout_code)
            self.parser=CommandParser(self.layout_manager)
            self.executor=KeyExecutor()
            self.CommandType=CommandType
            self.has_command_handler=True
        except ImportError:
            self.has_command_handler=False
            self.error_occurred.emit("Warning: command_handler not available, commands disabled")
    
    def run(self):
        self.loop=asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.running=True
        
        try:
            self.loop.run_until_complete(self._async_run())
        except Exception as e:
            self.error_occurred.emit(f"Bluetooth error: {str(e)}")
        finally:
            self.loop.close()
    
    async def _async_run(self):
        while self.running:
            try:
                if not await self._scan_and_connect():
                    await asyncio.sleep(2)
                    continue
                
                await self._communication_loop()
                
            except Exception as e:
                self.error_occurred.emit(f"Connection error: {str(e)}")
                await asyncio.sleep(2)
    
    async def _scan_and_connect(self):
        try:
            devices=await BleakScanner.discover(timeout=10.0,return_adv=True)
            
            for addr,data in devices.items():
                device=data[0]
                if device.name and DEVICE_NAME.lower() in device.name.lower():
                    self.device_address=device.address
                    self.device_found.emit(device.name,device.address)
                    break
            
            if not self.device_address:
                self.error_occurred.emit(f"{DEVICE_NAME} not found")
                return False
            
            self.client=BleakClient(self.device_address,timeout=15.0)
            await self.client.connect()
            
            if not self.client.is_connected:
                self.error_occurred.emit("Connection failed")
                return False
            
            await asyncio.sleep(0.5)
            await self.client.start_notify(TX_CHAR_UUID,self._notification_handler)
            self.connected.emit()
            await asyncio.sleep(0.3)
            return True
                
        except Exception as e:
            self.error_occurred.emit(f"Scan/Connect failed: {str(e)}")
            return False
    
    def _notification_handler(self,sender,data):
        try:
            message=data.decode('utf-8')
            self.message_buffer+=message
            
            while '\n' in self.message_buffer:
                line,self.message_buffer=self.message_buffer.split('\n',1)
                line=line.strip()
                
                if not line:
                    continue
                
                self.message_received.emit(line)
                
                # Check for ready signals
                if self.has_command_handler:
                    if line in self.parser.READY_SIGNALS and not self.is_ready:
                        self.is_ready=True
                        self.ready_received.emit()
                    elif self.is_ready:
                        self._process_command(line)
                else:
                    if "Ready" in line and not self.is_ready:
                        self.is_ready=True
                        self.ready_received.emit()
                    
        except Exception as e:
            self.error_occurred.emit(f"Decode error: {str(e)}")
    
    async def _communication_loop(self):
        while self.running and self.client and self.client.is_connected:
            if time.time()-self.last_telemetry>=0.2 and self.is_ready:
                await self._send_telemetry()
                self.last_telemetry=time.time()
            
            await asyncio.sleep(0.01)
        
        if self.client and self.client.is_connected:
            await self.client.stop_notify(TX_CHAR_UUID)
            await self.client.disconnect()
        
        self.is_ready=False
        self.disconnected.emit()
    
    async def _send_telemetry(self):
        if not (self.client and self.client.is_connected):
            return
        
        try:
            now=datetime.now()
            cpu_raw=psutil.cpu_percent(interval=None)
            ram_raw=psutil.virtual_memory().percent
            gpu_raw=self._get_gpu()
            
            cpu,gpu,ram=self.telemetry_buffer.update(cpu_raw,gpu_raw,ram_raw)
            
            time_str=now.strftime("%H:%M:%S")
            date_str=now.strftime("%Y-%m-%d")
            
            # Send packed telemetry format
            packet=f"<T|{time_str}|{date_str}|{cpu:.1f}|{gpu:.1f}|{ram:.1f}>"
            await self._send_data(packet)
            
            self.telemetry_sent.emit(packet)
        except Exception:
            pass
        except Exception:
            pass
    
    async def _send_data(self,msg):
        if self.client and self.client.is_connected:
            data=(msg+"\n").encode('utf-8')
            await self.client.write_gatt_char(RX_CHAR_UUID,data,response=False)
    
    def _get_gpu(self):
        try:
            import GPUtil
            gpus=GPUtil.getGPUs()
            if gpus:
                return gpus[0].load*100
        except:
            pass
        
        try:
            result=subprocess.run(
                ['nvidia-smi','--query-gpu=utilization.gpu','--format=csv,noheader,nounits'],
                capture_output=True,text=True,timeout=0.5
            )
            if result.returncode==0:
                return float(result.stdout.strip().split('\n')[0])
        except:
            pass
        
        return 0.0
    
    def _process_command(self,message:str):
        if not self.has_command_handler:
            return
            
        try:
            command=self.parser.parse(message)
            if command.command_type==self.CommandType.READY_SIGNAL:
                return
            success,result=self.executor.execute(command)
            self.command_executed.emit(command.raw_input,success,result)
        except Exception as e:
            self.error_occurred.emit(f"Command error: {str(e)}")
    
    def send_command(self,cmd:str):
        if self.loop and self.client and self.client.is_connected and self.is_ready:
            asyncio.run_coroutine_threadsafe(self._send_data(cmd),self.loop)
    
    def stop(self):
        self.running=False
        self.wait()
"""
CYD Deck BLE Communication Tool
Install: pip install bleak psutil GPUtil pyqt6
Usage: python ble_test.py
"""

import asyncio
import sys
import time
import psutil
import subprocess
from datetime import datetime
from bleak import BleakClient, BleakScanner

SERVICE_UUID="4fafc201-1fb5-459e-8fcc-c5c9c331914b"
RX_CHAR_UUID="beb5483e-36e1-4688-b7f5-ea07361b26a8"
TX_CHAR_UUID="6e400003-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_NAME="CYD_Deck"

class TelemetryBuffer:
    def __init__(self,alpha=0.3,max_change_per_sec=10.0):
        self.alpha=alpha
        self.max_change_per_sec=max_change_per_sec
        self.cpu=None
        self.gpu=None
        self.ram=None
        self.last_update=time.time()
    
    def _limit_change(self,new_val,old_val,dt):
        max_change=self.max_change_per_sec*dt
        diff=new_val-old_val
        if abs(diff)>max_change:
            return old_val+(max_change if diff>0 else -max_change)
        return new_val
    
    def update(self,cpu,gpu,ram):
        now=time.time()
        dt=now-self.last_update
        self.last_update=now
        
        if self.cpu is None:
            self.cpu,self.gpu,self.ram=cpu,gpu,ram
        else:
            smooth_cpu=self.alpha*cpu+(1-self.alpha)*self.cpu
            smooth_gpu=self.alpha*gpu+(1-self.alpha)*self.gpu
            smooth_ram=self.alpha*ram+(1-self.alpha)*self.ram
            
            self.cpu=self._limit_change(smooth_cpu,self.cpu,dt)
            self.gpu=self._limit_change(smooth_gpu,self.gpu,dt)
            self.ram=self._limit_change(smooth_ram,self.ram,dt)
        
        return self.cpu,self.gpu,self.ram

class CYDDeckClient:
    def __init__(self):
        self.client=None
        self.connected=False
        self.loop=None
        self.telemetry_buffer=TelemetryBuffer(alpha=0.3,max_change_per_sec=10.0)
        self.message_buffer=""
        self.is_ready=False
        
    async def scan_devices(self,timeout=10.0):
        print(f"🔍 Scanning for '{DEVICE_NAME}' ({timeout}s)...")
        devices=await BleakScanner.discover(timeout=timeout,return_adv=True)
        cyd_devices=[]
        
        for addr,data in devices.items():
            device=data[0]
            adv_data=data[1]
            if device.name and DEVICE_NAME.lower() in device.name.lower():
                cyd_devices.append((device,adv_data))
        
        if not cyd_devices:
            print(f"❌ No '{DEVICE_NAME}' devices found")
            print("\n📱 Available BLE devices:")
            count=0
            for addr,data in devices.items():
                device=data[0]
                adv_data=data[1]
                name=device.name or "Unknown"
                rssi=adv_data.rssi if hasattr(adv_data,'rssi') else 'N/A'
                print(f"  - {name} ({device.address}) RSSI:{rssi}dB")
                count+=1
                if count>=10:
                    break
            return None
            
        print(f"✅ Found {len(cyd_devices)} CYD Deck device(s):")
        for i,(device,adv_data) in enumerate(cyd_devices):
            rssi=adv_data.rssi if hasattr(adv_data,'rssi') else 'N/A'
            print(f"  [{i}] {device.name} - {device.address} (RSSI: {rssi}dB)")
        
        if len(cyd_devices)>1:
            try:
                choice=int(input(f"\nSelect device [0-{len(cyd_devices)-1}]: "))
                if 0<=choice<len(cyd_devices):
                    return cyd_devices[choice][0]
            except:
                pass
        return cyd_devices[0][0]
    
    def notification_handler(self,sender,data):
        try:
            message=data.decode('utf-8')
            self.message_buffer+=message
            
            while '\n' in self.message_buffer:
                line,self.message_buffer=self.message_buffer.split('\n',1)
                line=line.strip()
                
                if not line:
                    continue
                
                print(f"📥 ESP32: {line}")
                
                if "Ready" in line and not self.is_ready:
                    self.is_ready=True
                    print("✅ Device ready for commands")
                    
        except Exception as e:
            print(f"⚠️  RX decode error: {e}")
    
    async def connect(self,device):
        print(f"\n🔗 Connecting to {device.name} ({device.address})...")
        try:
            self.client=BleakClient(device.address,timeout=15.0)
            await self.client.connect()
            
            if not self.client.is_connected:
                print("❌ Connection failed")
                return False
                
            self.connected=True
            print(f"✅ Connected to {device.name}")
            
            await asyncio.sleep(0.5)
            
            # Check if services are available
            try:
                services=self.client.services
                if not services:
                    print("⚠️  No services found, waiting...")
                    await asyncio.sleep(1.0)
                    services=self.client.services
                
                service_found=False
                for service in services:
                    if service.uuid.lower()==SERVICE_UUID.lower():
                        service_found=True
                        print(f"✅ Found CYD Deck service")
                        break
                
                if not service_found:
                    print(f"⚠️  Service {SERVICE_UUID} not found (continuing anyway)")
                    
            except Exception as e:
                print(f"⚠️  Service check failed: {e} (continuing anyway)")
            
            # Enable notifications on TX characteristic
            try:
                await self.client.start_notify(TX_CHAR_UUID,self.notification_handler)
                print(f"🔔 Notifications enabled")
            except Exception as e:
                print(f"⚠️  Could not enable notifications: {e}")
                return False
            
            await asyncio.sleep(0.3)
            return True
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.connected=False
            return False
    
    async def send(self,msg):
        if not self.connected or not self.client or not self.client.is_connected:
            print("❌ Not connected")
            return False
        try:
            data=(msg+"\n").encode('utf-8')
            await self.client.write_gatt_char(RX_CHAR_UUID,data,response=False)
            return True
        except Exception as e:
            print(f"❌ Send failed: {e}")
            self.connected=False
            return False
    
    def get_gpu_usage(self):
        try:
            import GPUtil
            gpus=GPUtil.getGPUs()
            if gpus:
                return gpus[0].load*100
        except:
            pass
        
        try:
            result=subprocess.run(
                ['nvidia-smi','--query-gpu=utilization.gpu','--format=csv,noheader,nounits'],
                capture_output=True,text=True,timeout=0.5
            )
            if result.returncode==0:
                return float(result.stdout.strip().split('\n')[0])
        except:
            pass
        
        return 0.0
    
    async def send_telemetry_loop(self):
        print("\n📊 Starting telemetry stream (Ctrl+C to stop)...")
        print("Sending smoothed CPU/GPU/RAM data every 1 second\n")
        
        counter=0
        last_send=0
        
        try:
            while self.connected:
                now=time.time()
                
                if now-last_send>=1.0:
                    cpu_raw=psutil.cpu_percent(interval=None)
                    ram_raw=psutil.virtual_memory().percent
                    gpu_raw=self.get_gpu_usage()
                    
                    cpu,gpu,ram=self.telemetry_buffer.update(cpu_raw,gpu_raw,ram_raw)
                    
                    time_str=datetime.now().strftime("%H:%M:%S")
                    date_str=datetime.now().strftime("%Y-%m-%d")
                    
                    await self.send(f"CPU:{cpu:.1f}")
                    await asyncio.sleep(0.05)
                    await self.send(f"GPU:{gpu:.1f}")
                    await asyncio.sleep(0.05)
                    await self.send(f"RAM:{ram:.1f}")
                    await asyncio.sleep(0.05)
                    await self.send(f"TIME:{time_str}")
                    await asyncio.sleep(0.05)
                    await self.send(f"DATE:{date_str}")
                    
                    counter+=1
                    if counter%5==0:
                        print(f"📈 [{counter}] CPU:{cpu:.1f}% GPU:{gpu:.1f}% RAM:{ram:.1f}%")
                    
                    last_send=now
                
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n⏹️  Telemetry stopped")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    async def disconnect(self):
        if self.client:
            try:
                if self.client.is_connected:
                    await self.client.stop_notify(TX_CHAR_UUID)
                    await self.client.disconnect()
                print("🔌 Disconnected")
            except:
                pass
            finally:
                self.connected=False

async def interactive_mode(client):
    print("\n💬 Interactive mode")
    print("Commands:")
    print("  CPU:50      - Send CPU value")
    print("  GPU:75      - Send GPU value") 
    print("  RAM:60      - Send RAM value")
    print("  TIME:12:34  - Send time")
    print("  DATE:2024   - Send date")
    print("  <any text>  - Send custom command")
    print("  telem       - Start telemetry loop")
    print("  quit        - Exit")
    print()
    
    try:
        while client.connected:
            cmd=await asyncio.get_event_loop().run_in_executor(
                None,lambda: input("> ").strip()
            )
            
            if not cmd:
                continue
            elif cmd.lower()=='quit':
                break
            elif cmd.lower()=='telem':
                await client.send_telemetry_loop()
            elif cmd.lower()=='help':
                print("\nSend telemetry (CPU:50) or commands")
                print("'telem' for auto mode, 'quit' to exit")
            else:
                await client.send(cmd)
                print(f"📤 Sent: {cmd}")
                
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted")
    except EOFError:
        print("\n⏹️  EOF")

async def main():
    print("═"*60)
    print("           CYD Deck BLE Communication Tool")
    print("           With Smoothed Telemetry Support")
    print("═"*60)
    
    client=CYDDeckClient()
    
    device=await client.scan_devices(timeout=10.0)
    if not device:
        print("\n💡 Tips:")
        print("  - Make sure ESP32 is powered on")
        print("  - Check if BLE is enabled on your PC")
        print("  - ESP32 should show 'BLE initialized' in serial monitor")
        return
    
    if not await client.connect(device):
        return
    
    try:
        await asyncio.sleep(1.0)
        
        print("\n" + "─"*60)
        choice=input("Mode? [1] Telemetry [2] Interactive [Enter=1]: ").strip()
        print("─"*60)
        
        if choice=='2':
            await interactive_mode(client)
        else:
            await client.send_telemetry_loop()
            
    except KeyboardInterrupt:
        print("\n⏹️  Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.disconnect()
        print("\n👋 Goodbye!")
        await asyncio.sleep(0.5)

if __name__=="__main__":
    try:
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")