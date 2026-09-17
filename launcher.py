# -*- coding: utf-8 -*-
"""
薄启动器（方案 A+B）

职责：
1. 在常见布局中定位 PDF主程序.exe
2. 若目录里仍有历史「Git 分片」残留，启动前静默拼回完整文件（兼容旧包）
3. 启动真正的功能程序后立即退出
4. 找不到时给出可操作的中文说明（不依赖 Qt）

说明：现行打包默认产出完整文件；安装包请走网盘分发，勿提交 dist/ 到 Git。
"""
import ctypes
import os
import subprocess
import sys

import large_file_parts


RUNTIME_DIR_NAME = "runtime"
MAIN_EXE_NAME = "PDF主程序.exe"

MB_ICONERROR = 0x00000010
MB_ICONINFORMATION = 0x00000040
MB_OK = 0x00000000

# Win32 常量：用于首次还原时的简易等待窗口
WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_VISIBLE = 0x10000000
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
SS_CENTER = 0x00000001
SW_SHOW = 5
PM_REMOVE = 0x0001
WM_QUIT = 0x0012
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
IDC_ARROW = 32512
COLOR_WINDOW = 5


class _POINT(ctypes.Structure):
    """Win32 POINT，供 GetCursorPos 等使用（本文件主要用于消息结构对齐）。"""

    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _MSG(ctypes.Structure):
    """Win32 MSG 结构，用于 PeekMessage 泵送等待窗口消息。"""

    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_uint),
        ("pt", _POINT),
    ]


def _show_message(title: str, message: str, icon: int = MB_ICONERROR) -> None:
    """弹出 Windows 原生消息框，向用户展示错误或提示。"""
    ctypes.windll.user32.MessageBoxW(None, message, title, icon | MB_OK)


def _launcher_base_dir() -> str:
    """返回启动器所在目录（打包后为 exe 旁，开发时为源码旁）。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _candidate_main_exe_paths(base_dir: str) -> list:
    """按优先级列出可能的主程序路径（正式安装 + 开发/半成品布局）。"""
    parent_dir = os.path.dirname(base_dir)
    grand_dir = os.path.dirname(parent_dir)
    return [
        # 正式发布布局：启动器旁 runtime/
        os.path.join(base_dir, RUNTIME_DIR_NAME, MAIN_EXE_NAME),
        # 开发：启动器与 onedir 输出并列
        os.path.join(base_dir, "PDF主程序", MAIN_EXE_NAME),
        # 启动器在 dist_launcher，主程序在 dist/package 或 dist/PDF主程序
        os.path.join(parent_dir, "dist", "package", RUNTIME_DIR_NAME, MAIN_EXE_NAME),
        os.path.join(parent_dir, "dist", "PDF主程序", MAIN_EXE_NAME),
        os.path.join(parent_dir, "package", RUNTIME_DIR_NAME, MAIN_EXE_NAME),
        os.path.join(parent_dir, "PDF主程序", MAIN_EXE_NAME),
        # 再上一层（例如从子目录误点）
        os.path.join(grand_dir, "dist", "package", RUNTIME_DIR_NAME, MAIN_EXE_NAME),
        os.path.join(grand_dir, "dist", "PDF主程序", MAIN_EXE_NAME),
    ]


def _resolve_main_exe(base_dir: str) -> str:
    """返回第一个存在的主程序路径；找不到返回空字符串。"""
    seen = set()
    for path in _candidate_main_exe_paths(base_dir):
        normalized = os.path.normpath(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if os.path.isfile(normalized):
            return normalized
    return ""


def _missing_main_message(base_dir: str) -> str:
    """生成找不到主程序时的详细说明。"""
    expected = os.path.normpath(os.path.join(base_dir, RUNTIME_DIR_NAME, MAIN_EXE_NAME))
    return (
        "未找到主程序文件。\n\n"
        f"启动器位置：\n{base_dir}\n\n"
        f"期望路径：\n{expected}\n\n"
        "正确用法：\n"
        "请运行「dist\\package\\PDF2plus.exe」\n"
        "（不要单独运行 dist_launcher 或 dist 根目录下的测试启动器）\n\n"
        "若尚无 package 目录，请在项目根执行：\n"
        "  python run_build.py\n\n"
        "其他可能原因：\n"
        "1. 安装不完整或 runtime 被删除\n"
        "2. 杀毒软件隔离了 runtime 目录\n"
    )


def _restore_search_roots(base_dir: str, main_exe_path: str) -> list:
    """
    确定需要扫描分片清单的目录列表。

    优先扫描主程序所在 runtime，其次启动器目录，覆盖正式包与开发布局。
    """
    roots = []
    runtime_dir = os.path.dirname(main_exe_path)
    for candidate in (runtime_dir, base_dir, os.path.join(base_dir, RUNTIME_DIR_NAME)):
        normalized = os.path.normpath(candidate)
        if normalized not in roots and os.path.isdir(normalized):
            roots.append(normalized)
    return roots


def _collect_pending_manifests(search_roots: list) -> list:
    """收集所有尚未完好还原的分片清单路径（去重）。"""
    pending = []
    seen = set()
    for root_dir in search_roots:
        for manifest_path in large_file_parts.find_manifests(root_dir):
            normalized = os.path.normpath(manifest_path)
            if normalized in seen:
                continue
            seen.add(normalized)
            if not large_file_parts.is_assembled_ok(normalized):
                pending.append(normalized)
    return pending


# 64 位 Windows 下 WPARAM/LPARAM/LRESULT 必须用指针宽度整数，否则回调会 OverflowError
_WPARAM = ctypes.c_size_t
_LPARAM = ctypes.c_ssize_t
_LRESULT = ctypes.c_ssize_t
_WNDPROC = ctypes.WINFUNCTYPE(_LRESULT, ctypes.c_void_p, ctypes.c_uint, _WPARAM, _LPARAM)


class _WaitBanner:
    """
    极简置顶提示窗口：首次拼接大文件时告诉用户「正在还原」，避免误以为卡死。

    不依赖 Qt；使用 user32 创建静态文本窗口，并在拼接循环中泵送消息。
    """

    def __init__(self, title: str, message: str) -> None:
        """创建并显示等待窗口。"""
        self._user32 = ctypes.windll.user32
        # 明确声明原型，避免 64 位参数被截断或溢出
        self._user32.DefWindowProcW.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, _WPARAM, _LPARAM
        ]
        self._user32.DefWindowProcW.restype = _LRESULT
        self._hwnd = None
        self._class_name = "PdfToolRestoreBanner"
        self._title = title
        self._message = message
        self._create()

    def _create(self) -> None:
        """注册窗口类并创建可见的提示窗。"""

        def _procedure(hwnd, message, wparam, lparam):
            if message in (WM_DESTROY, WM_CLOSE):
                self._user32.PostQuitMessage(0)
                return 0
            return self._user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._wnd_proc_ref = _WNDPROC(_procedure)

        class _WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", ctypes.c_uint),
                ("lpfnWndProc", _WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.c_void_p),
                ("hIcon", ctypes.c_void_p),
                ("hCursor", ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", ctypes.c_wchar_p),
                ("lpszClassName", ctypes.c_wchar_p),
            ]

        hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        window_class = _WNDCLASS()
        window_class.style = 0
        window_class.lpfnWndProc = self._wnd_proc_ref
        window_class.cbClsExtra = 0
        window_class.cbWndExtra = 0
        window_class.hInstance = hinstance
        window_class.hIcon = None
        window_class.hCursor = self._user32.LoadCursorW(None, ctypes.c_void_p(IDC_ARROW))
        window_class.hbrBackground = ctypes.c_void_p(COLOR_WINDOW + 1)
        window_class.lpszMenuName = None
        window_class.lpszClassName = self._class_name
        # 重复运行时类可能已注册，忽略已存在错误
        self._user32.RegisterClassW(ctypes.byref(window_class))

        width, height = 420, 120
        screen_w = self._user32.GetSystemMetrics(0)
        screen_h = self._user32.GetSystemMetrics(1)
        pos_x = max(0, (screen_w - width) // 2)
        pos_y = max(0, (screen_h - height) // 2)

        style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_VISIBLE
        ex_style = WS_EX_TOPMOST | WS_EX_TOOLWINDOW
        self._hwnd = self._user32.CreateWindowExW(
            ex_style,
            self._class_name,
            self._title,
            style,
            pos_x,
            pos_y,
            width,
            height,
            None,
            None,
            hinstance,
            None,
        )
        # 子静态文本：居中显示提示文案
        self._user32.CreateWindowExW(
            0,
            "STATIC",
            self._message,
            WS_CHILD | WS_VISIBLE | SS_CENTER,
            10,
            30,
            width - 30,
            40,
            self._hwnd,
            None,
            hinstance,
            None,
        )
        self._user32.ShowWindow(self._hwnd, SW_SHOW)
        self._user32.UpdateWindow(self._hwnd)
        self.pump()

    def pump(self) -> None:
        """处理已排队的窗口消息，保持提示窗可响应绘制。"""
        message = _MSG()
        while self._user32.PeekMessageW(ctypes.byref(message), None, 0, 0, PM_REMOVE):
            if message.message == WM_QUIT:
                break
            self._user32.TranslateMessage(ctypes.byref(message))
            self._user32.DispatchMessageW(ctypes.byref(message))

    def close(self) -> None:
        """关闭并销毁等待窗口。"""
        if self._hwnd:
            self._user32.DestroyWindow(self._hwnd)
            self._hwnd = None


def _ensure_large_files_restored(base_dir: str, main_exe_path: str) -> None:
    """
    启动主程序前：若存在分片清单且原文件缺失/损坏，则自动拼接还原。

    还原后的文件与打包时字节级一致，因此功能与性能不受影响。
    首次还原会显示简短等待窗；已还原则立即返回。
    """
    search_roots = _restore_search_roots(base_dir, main_exe_path)
    pending_manifests = _collect_pending_manifests(search_roots)
    if not pending_manifests:
        return

    banner = _WaitBanner(
        "正在准备运行环境",
        "首次启动：正在还原运行库文件，请稍候…\n（仅需一次，完成后即可正常使用）",
    )
    last_pump_bytes = {"value": 0}
    try:
        for manifest_path in pending_manifests:
            def _on_progress(done: int, total: int) -> None:
                # 每写入约 8MB 泵送一次消息，避免窗口假死
                if done - last_pump_bytes["value"] >= 8 * 1024 * 1024 or done >= total:
                    last_pump_bytes["value"] = done
                    banner.pump()

            large_file_parts.assemble_from_manifest(
                manifest_path,
                progress_callback=_on_progress,
            )
            banner.pump()
    finally:
        banner.close()


def main() -> int:
    """还原分片（如需要）后查找并启动主程序。"""
    base_dir = _launcher_base_dir()
    main_exe_path = _resolve_main_exe(base_dir)

    if not main_exe_path:
        _show_message("启动失败", _missing_main_message(base_dir), MB_ICONERROR)
        return 1

    try:
        _ensure_large_files_restored(base_dir, main_exe_path)
    except Exception as restore_error:
        _show_message(
            "启动失败",
            "还原运行库分片失败，无法启动。\n\n"
            f"详细信息：{restore_error}\n\n"
            "请确认：\n"
            "1. Git 克隆完整（含全部 .part 分片与 .parts.json）\n"
            "2. 未手动删除 runtime 下的分片文件\n"
            "3. 磁盘空间足够完成拼接\n",
            MB_ICONERROR,
        )
        return 3

    # 还原后主程序路径不变；再次确认文件仍在
    if not os.path.isfile(main_exe_path):
        _show_message("启动失败", _missing_main_message(base_dir), MB_ICONERROR)
        return 1

    runtime_dir = os.path.dirname(main_exe_path)
    try:
        subprocess.Popen(
            [main_exe_path],
            cwd=runtime_dir,
            close_fds=True,
        )
    except OSError as exc:
        _show_message(
            "启动失败",
            f"无法启动主程序：\n{main_exe_path}\n\n详细信息：{exc}",
            MB_ICONERROR,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
