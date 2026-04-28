# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


mediapipe_datas = collect_data_files('mediapipe')
mediapipe_binaries = collect_dynamic_libs('mediapipe')
mediapipe_hiddenimports = collect_submodules('mediapipe.tasks')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=mediapipe_binaries,
    datas=[
        ('eye_drive_tracker\\ui\\assets', 'eye_drive_tracker\\ui\\assets'),
        ('models', 'models'),
        *mediapipe_datas,
    ],
    hiddenimports=mediapipe_hiddenimports,
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
    name='EyeDriveTracker-OneFile',
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
