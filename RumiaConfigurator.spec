# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\RumiaConfigurator.py'],
    pathex=[],
    binaries=[],
    datas=[('src/assets', 'assets')],
    hiddenimports=['customtkinter', 'PIL', 'numpy', 'scipy', 'matplotlib', 'python-can', 'tkinter'],
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
    name='RumiaConfigurator',
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
    icon=['src\\assets\\Rumia_logo.ico'],
)
