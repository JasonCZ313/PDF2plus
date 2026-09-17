# -*- mode: python ; coding: utf-8 -*-
"""
薄启动器打包配置（强制轻量，但必须打入 large_file_parts）

正常体积应约 5~15 MB。
"""

import os

block_cipher = None
PROJ_DIR = os.path.abspath(os.getcwd())

HEAVY_KEYWORDS = (
    'torch', 'nvidia', 'cuda', 'cudnn',
    'pyqt', 'qt5', 'qt6', 'pyside',
    'opencv', 'cv2', 'numpy', 'scipy', 'pandas', 'sklearn',
    'easyocr', 'rapidocr', 'onnx', 'paddle',
    'fitz', 'pymupdf', 'pillow', 'pil',
    'tensorflow', 'keras', 'sympy', 'matplotlib',
    'docx', 'pdf2docx', 'lxml',
    'opengl', 'skia', 'mkl', 'openblas',
)


def _is_heavy(name: str) -> bool:
    lower = name.replace('\\', '/').lower()
    return any(keyword in lower for keyword in HEAVY_KEYWORDS)


a = Analysis(
    [
        os.path.join(PROJ_DIR, 'launcher.py'),
        os.path.join(PROJ_DIR, 'large_file_parts.py'),
    ],
    pathex=[PROJ_DIR],  # 仅用于解析 large_file_parts
    binaries=[],
    datas=[],
    hiddenimports=['large_file_parts'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'PySide2', 'PySide6',
        'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas',
        'PIL', 'Pillow', 'cv2', 'torch', 'torchvision', 'torchaudio',
        'easyocr', 'rapidocr', 'onnxruntime', 'fitz', 'frontend',
        'docx', 'pdf2docx', 'lxml', 'shapely', 'skimage',
        'app', 'gui', 'pdf_converter', 'pdf_merger', 'pdf_splitter',
    ],
    cipher=block_cipher,
    noarchive=False,
)

before_bins = len(a.binaries)
before_datas = len(a.datas)
a.binaries = [item for item in a.binaries if not _is_heavy(item[0]) and not _is_heavy(item[1])]
a.datas = [item for item in a.datas if not _is_heavy(str(item[0])) and not _is_heavy(str(item[1]))]
print(
    f"[launcher.spec] 精简 binaries {before_bins}->{len(a.binaries)}, "
    f"datas {before_datas}->{len(a.datas)}"
)

# 确认 large_file_parts 进入纯 Python 模块表
pure_names = [entry[0] for entry in a.pure]
if not any(name == 'large_file_parts' or name.endswith('large_file_parts') for name in pure_names):
    raise SystemExit("[launcher.spec] 错误：large_file_parts 未打入启动器，请检查 Analysis")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='启动器',
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
    if os.path.isfile(os.path.join(PROJ_DIR, 'assets', 'icon.ico'))
    else (
        os.path.join(PROJ_DIR, 'assets', 'icon.png')
        if os.path.isfile(os.path.join(PROJ_DIR, 'assets', 'icon.png'))
        else None
    ),
)
