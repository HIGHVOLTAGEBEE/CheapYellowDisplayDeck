import keyboard as kb
import time
import os
import subprocess
import shutil
import ctypes
import webbrowser
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

VK_CODES = {
    'VOLUME_MUTE': 0xAD, 'VOLUME_DOWN': 0xAE, 'VOLUME_UP': 0xAF,
    'MEDIA_NEXT': 0xB0, 'MEDIA_PREV': 0xB1, 'MEDIA_STOP': 0xB2,
    'MEDIA_PLAY_PAUSE': 0xB3, 'BROWSER_BACK': 0xA6, 'BROWSER_FORWARD': 0xA7,
    'BRIGHTNESS_DOWN': 0x8C, 'BRIGHTNESS_UP': 0x8D,
}

FN_VK_MAPPING = {
    'f5': VK_CODES['MEDIA_STOP'], 'f6': VK_CODES['MEDIA_PREV'],
    'f7': VK_CODES['MEDIA_PLAY_PAUSE'], 'f8': VK_CODES['MEDIA_NEXT'],
    'f10': VK_CODES['VOLUME_DOWN'], 'f11': VK_CODES['VOLUME_UP'],
    'f12': VK_CODES['VOLUME_MUTE'],
}

KEYEVENTF_KEYUP = 0x0002

class CommandType(Enum):
    KEYSTROKE = "keystroke"
    EXECUTE = "execute"
    TEXT = "text"
    URL = "url"
    FILE_PATH = "file_path"
    CMD = "cmd"
    DELAY = "delay"
    READY_SIGNAL = "ready_signal"

@dataclass
class KeyCommand:
    command_type: CommandType
    raw_input: str
    modifiers: List[str]
    keys: List[str]
    text_content: Optional[str] = None
    execute_path: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    cmd_command: Optional[str] = None
    delay_ms: Optional[int] = None

class KeyboardLayoutManager:
    LAYOUTS = {
        'de': {'transformations': {'y': 'z', 'z': 'y', '-': 'ß', '[': 'ü', ']': '+', ';': 'ö', "'": 'ä'}},
        'us': {'transformations': {}},
        'fr': {'transformations': {'a': 'q', 'q': 'a', 'w': 'z', 'z': 'w', 'm': ',', ',': 'm'}}
    }
    
    def __init__(self, layout_code: str = 'us'):
        self.transformations = self.LAYOUTS.get(layout_code.lower(), {'transformations': {}})['transformations']
    
    def transform_key(self, key: str) -> str:
        return self.transformations.get(key.lower(), key) if len(key) == 1 else key
    
    def transform_keys(self, keys: List[str]) -> List[str]:
        return [self.transform_key(k) for k in keys]

class KeyMapper:
    KEY_MAPPINGS = {
        'CTRL': 'ctrl', 'CONTROL': 'ctrl', 'ALT': 'alt', 'SHIFT': 'shift',
        'WIN': 'win', 'WINDOWS': 'win', 'CMD': 'win', 'SUPER': 'win',
        'FN': 'fn', 'FUNCTION': 'fn', 'ENTER': 'enter', 'RETURN': 'enter',
        'SPACE': 'space', 'TAB': 'tab', 'ESC': 'esc', 'ESCAPE': 'esc',
        'BACKSPACE': 'backspace', 'DELETE': 'delete', 'DEL': 'delete',
        'UP': 'up', 'DOWN': 'down', 'LEFT': 'left', 'RIGHT': 'right',
        'HOME': 'home', 'END': 'end', 'PAGEUP': 'page up', 'PAGEDOWN': 'page down',
        **{f'F{i}': f'f{i}' for i in range(1, 25)},
    }
    
    MODIFIER_KEYS = {'ctrl', 'alt', 'shift', 'win', 'fn'}
    
    @classmethod
    def map_key(cls, key: str) -> str:
        return cls.KEY_MAPPINGS.get(key.upper(), key.lower())
    
    @classmethod
    def is_modifier(cls, key: str) -> bool:
        return key.lower() in cls.MODIFIER_KEYS

class CommandParser:
    READY_SIGNALS = ["CYD Deck Ready!", "cyd deck ready!", "CYD DECK READY!", "Ready!", "ready!"]
    
    def __init__(self, layout_manager: KeyboardLayoutManager):
        self.layout_manager = layout_manager
    
    def parse(self, raw_command: str) -> KeyCommand:
        raw_command = raw_command.strip()
        
        if raw_command in self.READY_SIGNALS:
            return KeyCommand(CommandType.READY_SIGNAL, raw_command, [], [])
        
        if raw_command.upper().startswith('D') and len(raw_command) > 1:
            delay_str = raw_command[1:]
            if delay_str.isdigit():
                delay_ms = int(delay_str)
                return KeyCommand(CommandType.DELAY, raw_command, [], [], delay_ms=delay_ms)
        
        if raw_command.startswith('<') and raw_command.endswith('>'):
            cmd_text = raw_command[1:-1].strip()
            return KeyCommand(CommandType.CMD, raw_command, [], [], cmd_command=cmd_text)
        
        if raw_command.upper().startswith('EXECUTE+'):
            return KeyCommand(CommandType.EXECUTE, raw_command, [], [], execute_path=raw_command[8:].strip())
        
        if raw_command.startswith("|") and raw_command.endswith("|") and len(raw_command) > 2:
            content = raw_command[1:-1]
            if self._is_url(content):
                return KeyCommand(CommandType.URL, raw_command, [], [], url=content)
            else:
                return KeyCommand(CommandType.FILE_PATH, raw_command, [], [], file_path=content)
        
        if '"' in raw_command:
            first_quote = raw_command.index('"')
            last_quote = raw_command.rindex('"')
            
            if first_quote != last_quote:
                prefix = raw_command[:first_quote].rstrip('+').strip()
                text_content = raw_command[first_quote+1:last_quote]
                
                if not prefix and self._is_url(text_content):
                    return KeyCommand(CommandType.URL, raw_command, [], [], url=text_content)
                
                prefix_keys = [KeyMapper.map_key(k.strip()) for k in prefix.split('+') if k.strip()] if prefix else []
                modifiers = [k for k in prefix_keys if KeyMapper.is_modifier(k)]
                keys = [k for k in prefix_keys if not KeyMapper.is_modifier(k)]
                return KeyCommand(CommandType.TEXT, raw_command, modifiers, keys, text_content=text_content)
        
        parts = raw_command.split('+')
        processed_keys = self.layout_manager.transform_keys([KeyMapper.map_key(p.strip()) for p in parts if p.strip()])
        modifiers = [k for k in processed_keys if KeyMapper.is_modifier(k)]
        keys = [k for k in processed_keys if not KeyMapper.is_modifier(k)]
        return KeyCommand(CommandType.KEYSTROKE, raw_command, modifiers, keys)
    
    def _is_url(self, text: str) -> bool:
        url_lower = text.lower()
        return (url_lower.startswith('http://') or 
                url_lower.startswith('https://') or 
                url_lower.startswith('www.') or
                url_lower.startswith('ftp://'))

class KeyExecutor:
    def execute(self, command: KeyCommand) -> tuple[bool, str]:
        try:
            if command.command_type == CommandType.READY_SIGNAL:
                return True, "Ready signal"
            elif command.command_type == CommandType.DELAY:
                return self._execute_delay(command.delay_ms)
            elif command.command_type == CommandType.EXECUTE:
                return self._execute_program(command.execute_path)
            elif command.command_type == CommandType.URL:
                return self._execute_url(command.url)
            elif command.command_type == CommandType.FILE_PATH:
                return self._execute_file_path(command.file_path)
            elif command.command_type == CommandType.CMD:
                return self._execute_cmd(command.cmd_command)
            elif command.command_type == CommandType.TEXT:
                return self._execute_text(command)
            elif command.command_type == CommandType.KEYSTROKE:
                return self._execute_keystroke(command)
            return False, "Unknown type"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def _execute_delay(self, delay_ms: int) -> tuple[bool, str]:
        try:
            time.sleep(delay_ms / 1000.0)
            return True, f"Delayed: {delay_ms}ms"
        except Exception as e:
            return False, f"Delay failed: {str(e)}"
    
    def _execute_program(self, path: str) -> tuple[bool, str]:
        try:
            if os.name == 'nt':
                try:
                    os.startfile(path)
                except:
                    prog_path = shutil.which(path)
                    subprocess.Popen([prog_path] if prog_path else path, shell=not prog_path)
            else:
                prog_path = shutil.which(path)
                subprocess.Popen([prog_path] if prog_path else path, shell=not prog_path)
            return True, f"Executed: {path}"
        except Exception as e:
            return False, f"Execute failed: {str(e)}"
    
    def _execute_url(self, url: str) -> tuple[bool, str]:
        try:
            if not url.lower().startswith(('http://', 'https://', 'ftp://')):
                url = 'https://' + url
            
            webbrowser.open(url)
            display_url = url[:50] + '...' if len(url) > 50 else url
            return True, f"Opened URL: {display_url}"
        except Exception as e:
            return False, f"URL open failed: {str(e)}"
    
    def _execute_file_path(self, path: str) -> tuple[bool, str]:
        try:
            if not os.path.exists(path):
                return False, f"Path not found: {path}"
            
            if os.name == 'nt':
                os.startfile(path)
            elif os.name == 'posix':
                if os.uname().sysname == 'Darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
            
            display_path = path[:50] + '...' if len(path) > 50 else path
            return True, f"Opened: {display_path}"
        except Exception as e:
            return False, f"Path open failed: {str(e)}"
    
    def _execute_cmd(self, command: str) -> tuple[bool, str]:
        try:
            if os.name == 'nt':
                subprocess.Popen(['cmd', '/c', command], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                if os.uname().sysname == 'Darwin':
                    subprocess.Popen(['osascript', '-e', 
                                    f'tell application "Terminal" to do script "{command}"'])
                else:
                    terminals = ['gnome-terminal', 'konsole', 'xterm']
                    for term in terminals:
                        if shutil.which(term):
                            subprocess.Popen([term, '-e', command])
                            break
            
            display_cmd = command[:50] + '...' if len(command) > 50 else command
            return True, f"CMD executed: {display_cmd}"
        except Exception as e:
            return False, f"CMD failed: {str(e)}"
    
    def _execute_text(self, command: KeyCommand) -> tuple[bool, str]:
        if command.modifiers or command.keys:
            kb.press_and_release('+'.join(command.modifiers + command.keys))
            time.sleep(0.001)
        if command.text_content:
            kb.write(command.text_content, delay=0.001)
        preview = command.text_content[:55] + '...' if len(command.text_content) > 55 else command.text_content
        return True, f"Typed: {preview}"
    
    def _execute_keystroke(self, command: KeyCommand) -> tuple[bool, str]:
        all_keys = command.modifiers + command.keys
        if not all_keys:
            return False, "No keys"
        if 'fn' in all_keys:
            return self._execute_fn_combination(all_keys)
        combo = '+'.join(all_keys)
        kb.press_and_release(combo)
        return True, f"Pressed: {combo}"
    
    def _execute_fn_combination(self, keys: List[str]) -> tuple[bool, str]:
        fn_keys = [k for k in keys if k != 'fn']
        try:
            kb.press('fn')
            for key in fn_keys:
                kb.press_and_release(key)
            kb.release('fn')
            return True, f"Pressed: fn+{'+'.join(fn_keys)}"
        except:
            if len(fn_keys) == 1 and fn_keys[0] in FN_VK_MAPPING:
                vk_code = FN_VK_MAPPING[fn_keys[0]]
                if vk_code:
                    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
                    return True, f"Pressed (VK): fn+{fn_keys[0]}"
            for key in fn_keys:
                kb.press_and_release(key)
            return True, f"Pressed (fallback): {'+'.join(fn_keys)}"