# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\RumiaConfigurator.py'],
    pathex=[],
    binaries=[],
    datas=[('src\\assets', 'assets')],
    hiddenimports=['gui', 'can_interface', 'plot_manager', 'utils', 'plotting', 'customtkinter', 'darkdetect', 'serial', 'serial.tools.list_ports', 'can', 'can.interfaces', 'can.interfaces.slcan', 'can.interfaces.virtual'],
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
    name='RumiaConfigurator_debug',
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
    icon=['src\\assets\\Rumia_logo.ico'],
)
