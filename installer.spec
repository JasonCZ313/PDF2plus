# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — PDF2plus 下载器
将主程序 EXE 嵌入安装器中，打包为单文件自包含安装器
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
PROJ_DIR = os.path.abspath(os.getcwd())

a = Analysis(
    ['installer.py'],
    pathex=[PROJ_DIR],
    binaries=[],
    datas=[
        # 将主程序 EXE 嵌入（安装器运行时读取此文件释放到目标目录）
        (os.path.join(PROJ_DIR, 'dist', 'PDF2plus.exe'), '.'),
        # 安装向导窗口图标
        (os.path.join(PROJ_DIR, 'assets', 'icon.png'), '.'),
        (os.path.join(PROJ_DIR, 'assets', 'icon.ico'), '.'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PDF2plus下载器',
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
    icon=os.path.join(PROJ_DIR, 'assets', 'icon.ico')
    if os.path.isfile(os.path.join(PROJ_DIR, 'assets', 'icon.ico')) else None,
)
