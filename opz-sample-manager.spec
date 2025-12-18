# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Flask and Jinja2 data files
datas = [
    ('static', 'static'),
    ('templates', 'templates'),
]

# Collect hidden imports for Flask and related packages
hiddenimports = [
    'flask',
    'flask_cors',
    'jinja2',
    'werkzeug',
    'requests',
    'engineio.async_drivers.threading',
]

# Add blueprint modules
hiddenimports += [
    'blueprints.config',
    'blueprints.sample_converter',
    'blueprints.sample_manager',
    'blueprints.tape_export',
    'blueprints.dialogs',
    'blueprints.backup',
]

# Exclude unused PyQt5 modules to reduce size
excludes = [
    'PyQt5.QtBluetooth',
    'PyQt5.QtDBus',
    'PyQt5.QtDesigner',
    'PyQt5.QtHelp',
    'PyQt5.QtLocation',
    'PyQt5.QtMultimedia',
    'PyQt5.QtMultimediaWidgets',
    'PyQt5.QtNfc',
    'PyQt5.QtOpenGL',
    'PyQt5.QtPositioning',
    'PyQt5.QtQml',
    'PyQt5.QtQuick',
    'PyQt5.QtQuickWidgets',
    'PyQt5.QtRemoteObjects',
    'PyQt5.QtSensors',
    'PyQt5.QtSerialPort',
    'PyQt5.QtSql',
    'PyQt5.QtSvg',
    'PyQt5.QtTest',
    'PyQt5.QtXml',
    'PyQt5.QtXmlPatterns',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OP-Z Sample Manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Strip debug symbols
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=sys.platform == 'darwin',  # macOS only
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico' if sys.platform == 'win32' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,  # Strip debug symbols
    upx=True,
    upx_exclude=[],
    name='OP-Z Sample Manager',
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='OP-Z Sample Manager.app',
        icon='static/favicon.png',
        bundle_identifier='com.opz.samplemanager',
        info_plist={
            'CFBundleName': 'OP-Z Sample Manager',
            'CFBundleDisplayName': 'OP-Z Sample Manager',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
