# -*- mode: python ; coding: utf-8 -*-

import os

PROJECT = os.path.abspath(os.getcwd())
VENV_SP = os.path.join(PROJECT, '.venv', 'lib', 'python3.13', 'site-packages')

a = Analysis(
    ['src/app.py'],
    pathex=[VENV_SP, PROJECT],
    binaries=[],
    datas=[('src', 'src')],
    hiddenimports=[
        'src.gui',
        'src.overlay',
        'src.monitor',
        'src.fps',
        'src.settings',
        'src.games',
        'src.gamemode',
        'src.restore',
        'src.game_bindings',
        'src.dashboard',
        'src.config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Do not bundle host system libraries (they carry newer glibc deps).
# These are provided by the running system.
_HOST_PREFIXES = ('/run/host/',)
a.binaries = [b for b in a.binaries if not str(b[1]).startswith(_HOST_PREFIXES)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='gamohud-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='gamohud-gui',
)
