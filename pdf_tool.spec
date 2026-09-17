# -*- mode: python ; coding: utf-8 -*-
"""
主程序 onedir（V15：RapidOCR，无 torch）

产物：
  dist/PDF主程序/PDF主程序.exe
  dist/PDF主程序/_internal/...
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None
PROJ_DIR = os.path.abspath(os.getcwd())

QT_DLLS_TO_EXCLUDE = {
    'Qt5Designer',
    'Qt5Quick', 'Qt5Qml', 'Qt5Quick3D', 'Qt5QuickControls2',
    'Qt5QuickTemplates2', 'Qt5QuickShapes', 'Qt5QuickParticles',
    'Qt5QuickWidgets', 'Qt5QuickTest',
    'Qt5QmlModels', 'Qt5QmlWorkerScript',
    'Qt5Bluetooth', 'Qt5Nfc', 'Qt5Sensors', 'Qt5SerialPort',
    'Qt5WebSockets', 'Qt5WebChannel', 'Qt5WebView',
    'Qt5Multimedia', 'Qt5MultimediaWidgets',
    'Qt5Sql',
    'Qt5Help', 'Qt5Test', 'Qt5XmlPatterns', 'Qt5TextToSpeech',
    'Qt5Location', 'Qt5Positioning', 'Qt5RemoteObjects',
    'Qt5DBus',
    'libcrypto', 'libssl', 'libeay32', 'ssleay32',
}

UPX_EXCLUDE_PATTERNS = [
    'opengl32sw.dll',
    'python314.dll',
    'onnxruntime.dll',
    'onnxruntime_providers_shared.dll',
]

extra_datas = []
extra_binaries = []
extra_hidden = []
try:
    extra_datas += collect_data_files('rapidocr')
except Exception:
    pass
try:
    collected_datas, collected_bins, collected_hidden = collect_all('onnxruntime')
    extra_datas += collected_datas
    extra_binaries += collected_bins
    extra_hidden += list(collected_hidden or [])
except Exception:
    pass

ocr_models_dir = os.path.join(PROJ_DIR, 'assets', 'ocr_models')
datas = [
    (os.path.join(PROJ_DIR, 'assets', 'icon.png'), 'assets'),
]
if os.path.isdir(ocr_models_dir):
    datas.append((ocr_models_dir, 'assets/ocr_models'))
datas += extra_datas

a = Analysis(
    [os.path.join(PROJ_DIR, 'main.py')],
    pathex=[PROJ_DIR],
    binaries=extra_binaries,
    datas=datas,
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'fitz',
        'app',
        'app.config',
        'app.file_manager',
        'app.gui',
        'app.history_manager',
        'app.pdf_converter',
        'app.pdf_merger',
        'app.pdf_splitter',
        'app.preferences',
        'docx',
        'docx.opc',
        'docx.oxml',
        'pdf2docx',
        'PIL',
        'rapidocr',
        'onnxruntime',
        'cv2',
        'numpy',
        'omegaconf',
        'pyclipper',
        'shapely',
    ] + extra_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 明确剔除旧 OCR / 深度学习栈
        'easyocr',
        'torch',
        'torchvision',
        'torchaudio',
        'tensorflow',
        'tensorboard',
        'paddle',
        'paddlepaddle',
        'tkinter',
        'matplotlib',
        'pandas',
        'scipy',
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        'sympy',
        'PIL.ImageQt',
        'PIL.ImageTk',
    ],
    cipher=block_cipher,
    noarchive=False,
)

filtered_binaries = []
removed = []
for dest_name, src_path, typecode in a.binaries:
    base = os.path.basename(dest_name)
    name_no_ext = os.path.splitext(base)[0]
    lower_dest = dest_name.replace('\\', '/').lower()
    drop = any(
        name_no_ext.startswith(pattern) or base.startswith(pattern)
        for pattern in QT_DLLS_TO_EXCLUDE
    )
    # 双保险：路径里带 torch 的一律剔除
    if 'torch' in lower_dest or 'easyocr' in lower_dest:
        drop = True
    if drop:
        removed.append(base)
    else:
        filtered_binaries.append((dest_name, src_path, typecode))
if removed:
    print(f"[spec] 剔除 {len(removed)} 个未使用/禁用二进制")
a.binaries = filtered_binaries

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDF主程序',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE_PATTERNS,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJ_DIR, 'assets', 'icon.ico')
    if os.path.isfile(os.path.join(PROJ_DIR, 'assets', 'icon.ico'))
    else os.path.join(PROJ_DIR, 'assets', 'icon.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=UPX_EXCLUDE_PATTERNS,
    name='PDF主程序',
)
