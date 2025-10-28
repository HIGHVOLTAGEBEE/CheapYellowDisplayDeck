# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/Users/Manue/Documents/GitHub/CheapYellowDisplayDeck/PC-Software/V2/serial_comm.py', '.'), ('C:/Users/Manue/Documents/GitHub/CheapYellowDisplayDeck/PC-Software/V2/kb_handler.py', '.'), ('C:/Users/Manue/Documents/GitHub/CheapYellowDisplayDeck/PC-Software/V2/ui.py', '.')],
    hiddenimports=['PyQt6', 'pyserial', 'keyboard', 'psutil', 'gputil'],
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
    name='GOGOGO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
