"""
kb_handler.py - Keyboard command parsing and execution

API:
    KeyCommand: Command data structure
    CommandParser.parse(raw: str) -> KeyCommand
    KeyExecutor.execute(command: KeyCommand) -> tuple[bool, str]
"""

import keyboard as kb
import time
import os
import subprocess
import shutil
import ctypes
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
    READY_SIGNAL = "ready_signal"

@dataclass
class KeyCommand:
    command_type: CommandType
    raw_input: str
    modifiers: List[str]
    keys: List[str]
    text_content: Optional[str] = None
    execute_path: Optional[str] = None

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
        
        if raw_command.upper().startswith('EXECUTE+'):
            return KeyCommand(CommandType.EXECUTE, raw_command, [], [], execute_path=raw_command[8:].strip())
        
        if '"' in raw_command:
            parts = raw_command.split('"', 2)
            prefix = parts[0].rstrip('+') if parts[0] else ''
            text_content = parts[1] if len(parts) > 1 else ''
            prefix_keys = [KeyMapper.map_key(k.strip()) for k in prefix.split('+') if k.strip()] if prefix else []
            modifiers = [k for k in prefix_keys if KeyMapper.is_modifier(k)]
            keys = [k for k in prefix_keys if not KeyMapper.is_modifier(k)]
            return KeyCommand(CommandType.TEXT, raw_command, modifiers, keys, text_content=text_content)
        
        parts = raw_command.split('+')
        processed_keys = self.layout_manager.transform_keys([KeyMapper.map_key(p.strip()) for p in parts if p.strip()])
        modifiers = [k for k in processed_keys if KeyMapper.is_modifier(k)]
        keys = [k for k in processed_keys if not KeyMapper.is_modifier(k)]
        return KeyCommand(CommandType.KEYSTROKE, raw_command, modifiers, keys)

class KeyExecutor:
    def execute(self, command: KeyCommand) -> tuple[bool, str]:
        try:
            if command.command_type == CommandType.READY_SIGNAL:
                return True, "Ready signal"
            elif command.command_type == CommandType.EXECUTE:
                return self._execute_program(command.execute_path)
            elif command.command_type == CommandType.TEXT:
                return self._execute_text(command)
            elif command.command_type == CommandType.KEYSTROKE:
                return self._execute_keystroke(command)
            return False, "Unknown type"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
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
    
    def _execute_text(self, command: KeyCommand) -> tuple[bool, str]:
        if command.modifiers or command.keys:
            kb.press_and_release('+'.join(command.modifiers + command.keys))
            time.sleep(0.05)
        if command.text_content:
            kb.write(command.text_content, delay=0.01)
        preview = command.text_content[:30] + '...' if len(command.text_content) > 30 else command.text_content
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