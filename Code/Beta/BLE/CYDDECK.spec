# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/Manue/Documents/GitHub/CheapYellowDisplayDeck/PC-Software/Beta/BLE/bluetooth_comm.py', '.'), ('C:/Users/Manue/Documents/GitHub/CheapYellowDisplayDeck/PC-Software/Beta/BLE/command_handler.py', '.'), ('C:/Users/Manue/Documents/GitHub/CheapYellowDisplayDeck/PC-Software/Beta/BLE/ui_handler.py', '.')],
    hiddenimports=['PyQt6', 'pyserial', 'Keyboard', 'psutil', 'gputil', 'bleak', 'asyncio'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CYDDECK',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Manue\\Downloads\\favicon (1).ico'],
)
