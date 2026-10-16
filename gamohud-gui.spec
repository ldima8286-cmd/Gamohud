# -*- mode: python ; coding: utf-8 -*-

import os
import sys

PROJECT = os.path.abspath(os.getcwd())

# Optional venv site-packages (used when building from the project venv).
_venv_candidates = []
for pyver in ('python3.13', 'python3.12', 'python3.11', 'python3.10'):
    _venv_candidates.append(os.path.join(PROJECT, '.venv', 'lib', pyver, 'site-packages'))
    _venv_candidates.append(os.path.join(PROJECT, '.venv', 'Lib', 'site-packages'))
_venv = [p for p in _venv_candidates if os.path.isdir(p)]

# Bundle a locally provided PresentMon binary if the user fetched one.
_presentmon_dir = os.path.join(PROJECT, 'tools', 'presentmon')
_extra_datas = []
if os.path.isdir(_presentmon_dir):
    _extra_datas.append((_presentmon_dir, 'tools/presentmon'))

a = Analysis(
    ['src/app.py'],
    pathex=_venv + [PROJECT],
    binaries=[],
    datas=[('src', 'src'), ('assets', 'assets')] + _extra_datas,
    hiddenimports=[
        'src.platform_utils',
        'src.gui',
        'src.overlay',
        'src.launcher',
        'src.run_wrapper',
        'src.metrics',
        'src.metrics.system',
        'src.metrics.gpu',
        'src.fps',
        'src.fps.manager',
        'src.fps.presentmon_common',
        'src.fps.presentmon_helper',
        'src.fps.backends',
        'src.fps.backends.null',
        'src.fps.backends.mesa_gallium',
        'src.fps.backends.gamescope',
        'src.fps.backends.presentmon',
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

# On Linux, do not bundle host system libraries: they carry newer glibc deps
# and are provided by the running system.
if sys.platform.startswith('linux'):
    _HOST_PREFIXES = ('/run/host/',)
    a.binaries = [b for b in a.binaries if not str(b[1]).startswith(_HOST_PREFIXES)]

_icon = 'assets/gamohud.ico' if os.path.exists('assets/gamohud.ico') else None

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
    icon=_icon,
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
