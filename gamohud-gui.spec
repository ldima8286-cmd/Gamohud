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
        'src.launcher',
        'src.run_wrapper',
        'src.metrics',
        'src.metrics.system',
        'src.metrics.gpu',
        'src.fps',
        'src.fps.manager',
        'src.fps.backends',
        'src.fps.backends.null',
        'src.fps.backends.mesa_gallium',
        'src.fps.backends.gamescope',
        'src.fps.backends.vulkan_layer',
        'src.profiles',
        'src.profiles.model',
        'src.profiles.store',
        'src.profiles.matcher',
        'src.games',
        'src.gamemode',
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
