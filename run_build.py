# -*- coding: utf-8 -*-
"""
一键打包：onedir 主程序 + 薄启动器 + package 组装

产出：
- dist/package/PDF2plus.exe（用户双击入口；V4 起可随仓库分发）
- 可选 dist/app_payload.zip / 安装器（便于网盘分发，默认不进 Git）

流程：
1. 打包主程序 onedir
2. 打包薄启动器
3. 组装为 dist/package（完整文件，可直接双击运行）
4. 可选：生成 app_payload.zip / 安装器

用法：
    python run_build.py
    python run_build.py --installer
    build.bat
"""
import argparse
import os
import shutil
import sys
import zipfile
import subprocess


PROJ_DIR = os.path.dirname(os.path.abspath(__file__))  # 项目根目录绝对路径
DIST_DIR = os.path.join(PROJ_DIR, "dist")  # PyInstaller / 组装输出目录
BUILD_DIR = os.path.join(PROJ_DIR, "build")  # PyInstaller 中间文件目录

MAIN_ONEDIR_NAME = "PDF主程序"  # 主程序 onedir 文件夹名
LAUNCHER_BUILD_NAME = "启动器.exe"  # PyInstaller 打出的启动器文件名
LAUNCHER_EXE_NAME = "PDF2plus.exe"  # 最终给用户双击的入口名
PACKAGE_DIR_NAME = "package"  # 完整可分发目录名（放在 dist 下）
PAYLOAD_ZIP_NAME = "app_payload.zip"  # 可选：整包 zip，方便网盘上传
INSTALLER_EXE_NAME = "PDF2plus下载器.exe"  # 可选安装器文件名
LAUNCHER_MAX_MB = 30.0  # 启动器体积上限，超过说明误打入了主程序依赖


def _run_pyinstaller(spec_name: str, use_ml_skip_wrapper: bool = False) -> None:
    """在项目根目录执行指定 spec。

    :param use_ml_skip_wrapper: 主程序打包时跳过 torch 等 DLL 扫描，防止卡死
    """
    spec_path = os.path.join(PROJ_DIR, spec_name)
    if not os.path.isfile(spec_path):
        raise FileNotFoundError(spec_path)

    if use_ml_skip_wrapper:
        # 辅助脚本放临时目录，避免被 --clean 清掉
        import tempfile
        helper_path = os.path.join(tempfile.gettempdir(), "pdf_tool_pyi_skip_build.py")
        helper_code = f'''# -*- coding: utf-8 -*-
import os, sys
os.chdir(r"{PROJ_DIR}")
import PyInstaller.building.build_main as bm
_orig = bm.find_binary_dependencies
def _patched(binaries, import_packages, symlink_suppression_patterns):
    filtered = [p for p in import_packages if not p.startswith(
        ("torch", "easyocr", "cv2", "torchvision", "skimage")
    )]
    skipped = len(import_packages) - len(filtered)
    if skipped:
        print(f"[build] 跳过 {{skipped}} 个 ML 包 DLL 扫描")
    return _orig(binaries, filtered, symlink_suppression_patterns)
bm.find_binary_dependencies = _patched
import PyInstaller.__main__
sys.argv = ["pyinstaller", "--noconfirm", "--clean",
            "--workpath", r"{BUILD_DIR}",
            "--distpath", r"{DIST_DIR}",
            r"{spec_path}"]
PyInstaller.__main__.run()
'''
        with open(helper_path, "w", encoding="utf-8") as helper_file:
            helper_file.write(helper_code)
        cmd = [sys.executable, helper_path]
    else:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--clean",
            "--workpath", BUILD_DIR,
            "--distpath", DIST_DIR,
            spec_path,
        ]

    print(f"[INFO] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJ_DIR)
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller 失败: {spec_name} 返回码 {result.returncode}")


def _assert_thin_launcher(launcher_path: str) -> None:
    size_mb = os.path.getsize(launcher_path) / (1024 * 1024)
    print(f"[INFO] 启动器体积: {size_mb:.2f} MB")
    if size_mb > LAUNCHER_MAX_MB:
        raise RuntimeError(
            f"启动器异常偏大（{size_mb:.1f} MB > {LAUNCHER_MAX_MB} MB），"
            "疑似误打入主程序依赖。"
        )


def _assemble_package() -> str:
    onedir_path = os.path.join(DIST_DIR, MAIN_ONEDIR_NAME)
    main_exe = os.path.join(onedir_path, f"{MAIN_ONEDIR_NAME}.exe")
    launcher_src = os.path.join(DIST_DIR, LAUNCHER_BUILD_NAME)

    if not os.path.isfile(main_exe):
        raise FileNotFoundError(f"主程序缺失: {main_exe}")
    if not os.path.isfile(launcher_src):
        raise FileNotFoundError(f"启动器缺失: {launcher_src}")

    _assert_thin_launcher(launcher_src)

    package_dir = os.path.join(DIST_DIR, PACKAGE_DIR_NAME)
    if os.path.isdir(package_dir):
        shutil.rmtree(package_dir, ignore_errors=True)
    os.makedirs(package_dir, exist_ok=True)

    shutil.copy2(launcher_src, os.path.join(package_dir, LAUNCHER_EXE_NAME))
    shutil.copytree(onedir_path, os.path.join(package_dir, "runtime"))

    print(f"[INFO] 已组装: {package_dir}")
    print(f"[INFO] 请运行: {os.path.join(package_dir, LAUNCHER_EXE_NAME)}")
    return package_dir


def _zip_package(package_dir: str) -> str:
    """把完整 package 打成 zip，便于上传网盘或给安装器使用。"""
    zip_path = os.path.join(DIST_DIR, PAYLOAD_ZIP_NAME)
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for root, _dirs, files in os.walk(package_dir):
            for file_name in files:
                full_path = os.path.join(root, file_name)
                arc_name = os.path.relpath(full_path, package_dir)
                zip_file.write(full_path, arc_name)
    print(f"[INFO] 网盘/安装载荷: {zip_path} ({os.path.getsize(zip_path)/1024/1024:.1f} MB)")
    return zip_path


def _post_build_checks(package_dir: str) -> None:
    """打包后自检：启动器体积、OCR 模型是否打进 runtime。"""
    launcher_path = os.path.join(package_dir, LAUNCHER_EXE_NAME)
    _assert_thin_launcher(launcher_path)

    # OCR 模型应在 runtime 内，否则扫描件转 Word 可能无识别
    model_candidates = [
        os.path.join(package_dir, "runtime", "_internal", "assets", "ocr_models"),
        os.path.join(package_dir, "runtime", "assets", "ocr_models"),
    ]
    model_ok = False
    for model_dir in model_candidates:
        if os.path.isdir(model_dir) and any(
            name.endswith(".onnx") for name in os.listdir(model_dir)
        ):
            model_ok = True
            print(f"[INFO] OCR 模型目录: {model_dir}")
            break
    if not model_ok:
        print("[WARNING] 未在 package 中找到 OCR ONNX 模型目录，转 Word 扫描件可能无识别")


def main():
    """执行完整打包：主程序 → 启动器 → 组装 →（可选）zip / 安装器。"""
    parser = argparse.ArgumentParser(description="一键打包 PDF2plus（产出 dist/package）")
    parser.add_argument("--installer", action="store_true", help="继续打包安装器")
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="不生成 app_payload.zip（只要可运行目录时使用）",
    )
    args = parser.parse_args()

    # 打包前重新生成 PDF2+ 封面图标，保证 exe / 窗口图标一致
    print("\n[0/4] 生成 PDF2+ 图标...")
    generate_icon_script = os.path.join(PROJ_DIR, "generate_icon.py")
    icon_result = subprocess.run(
        [sys.executable, generate_icon_script],
        cwd=PROJ_DIR,
    )
    if icon_result.returncode != 0:
        print("[ERROR] 生成图标失败")
        sys.exit(1)

    # 打包前检查关键源码与资源是否齐全
    for relative, label in [
        ("main.py", "main.py"),
        ("launcher.py", "launcher.py"),
        ("pdf_tool.spec", "pdf_tool.spec"),
        ("launcher.spec", "launcher.spec"),
        (os.path.join("assets", "icon.png"), "icon.png"),
        (os.path.join("assets", "icon.ico"), "icon.ico"),
        (os.path.join("assets", "ocr_models", "PP-OCRv6_det_small.onnx"), "OCR det 模型"),
        (os.path.join("assets", "ocr_models", "PP-OCRv6_rec_small.onnx"), "OCR rec 模型"),
        (os.path.join("assets", "ocr_models", "ch_ppocr_mobile_v2.0_cls_mobile.onnx"), "OCR cls 模型"),
    ]:
        path = os.path.join(PROJ_DIR, relative)
        if not os.path.exists(path):
            print(f"[ERROR] 缺少 {label}: {path}")
            sys.exit(1)

    # 清空旧构建，避免混入过期文件
    for dir_path in (BUILD_DIR, DIST_DIR):
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)
            print(f"[INFO] 已清理: {dir_path}")

    print("\n[1/4] 打包主程序 onedir（RapidOCR）...")
    _run_pyinstaller("pdf_tool.spec", use_ml_skip_wrapper=True)

    print("\n[2/4] 打包薄启动器...")
    _run_pyinstaller("launcher.spec", use_ml_skip_wrapper=False)

    print("\n[3/4] 组装 package（完整可运行目录）...")
    package_dir = _assemble_package()

    zip_path = None
    if args.no_zip:
        print("\n[4/4] 跳过 zip（--no-zip）")
    else:
        print("\n[4/4] 生成网盘分发用 zip...")
        zip_path = _zip_package(package_dir)

    _post_build_checks(package_dir)

    if args.installer:
        installer_spec = os.path.join(PROJ_DIR, "installer.spec")
        if not os.path.isfile(installer_spec):
            print("[WARNING] 无 installer.spec，跳过安装器")
        else:
            print("\n[附加] 打包安装器...")
            _run_pyinstaller("installer.spec")
    else:
        print("\n[附加] 跳过安装器（需要时加 --installer）")

    launcher = os.path.join(package_dir, LAUNCHER_EXE_NAME)
    print("\n" + "=" * 56)
    print("  打包成功")
    print(f"  用户启动入口: {launcher}")
    print(f"  启动器体积: {os.path.getsize(launcher)/1024/1024:.2f} MB")
    if zip_path:
        print(f"  可选网盘包: {zip_path}")
    print("  说明: dist/package 可随仓库分发；app_payload.zip 默认不进 Git")
    print("=" * 56)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)
