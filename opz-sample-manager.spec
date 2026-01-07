# -*- mode: python ; coding: utf-8 -*-

import shutil
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Platform-specific FFMPEG binary
if sys.platform == 'darwin':
    ffmpeg_binary = [('bin/ffmpeg', 'bin')]
elif sys.platform == 'linux':
    # On Linux, rely on system ffmpeg (do not bundle).
    ffmpeg_binary = []
else:
    # Windows
    ffmpeg_binary = [('bin/ffmpeg.exe', 'bin')]

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

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ffmpeg_binary,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    hooksconfig={
        "gi": {
            "icons": ["Adwaita"],       # Only include one basic icon theme
            "themes": ["Adwaita"],      # Only include one basic GTK theme
            "languages": ["en_US"],     # Only include English translations
            "module-versions": {
                "Gtk": "3.0",
                "WebKit2": "4.1"
            },
        },
    },
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'win32':
    # Windows: Single-file executable (everything bundled into one .exe)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='OP-Z Sample Manager',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        icon='static/favicon.ico',
    )
elif sys.platform == 'linux':
    # Linux: Folder mode (no .app bundle)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='opz-sample-manager',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='opz-sample-manager',
    )
else:
    # macOS: Folder mode, then wrap in .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='OP-Z Sample Manager',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='OP-Z Sample Manager',
    )

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
