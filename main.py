"""PDF 合并与转换工具 — 程序入口"""
import sys
import os

# 确保 app 包可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 转 Word 隔离子进程：尽早分支，避免拉起 Qt / 工作区哨兵（崩溃也不影响主界面）
if len(sys.argv) >= 3 and sys.argv[1] == "--task-pdf-to-word":
    from app.pdf_converter import run_pdf_to_word_worker

    raise SystemExit(run_pdf_to_word_worker(sys.argv[2]))

# 确保 data/ 目录在启动时即创建完成
from app.preferences import get_data_dir, get_workspace

_data_dir = get_data_dir()
os.makedirs(os.path.join(_data_dir, "workspace"), exist_ok=True)
os.makedirs(os.path.join(_data_dir, "history"), exist_ok=True)

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QFont
from app.config import APP_NAME, APP_VERSION
from app.preferences import get as pref_get
from app.i18n import t, set_language
from app import ui_scale
from app.gui import MainWindow

SENTINEL_FILE = os.path.join(get_workspace(), ".session_active")


def _clear_workspace():
    """清空工作空间中的所有 PDF 文件和顺序文件"""
    ws = get_workspace()
    if not os.path.isdir(ws):
        return
    for f in os.listdir(ws):
        fp = os.path.join(ws, f)
        try:
            if os.path.isfile(fp):
                os.remove(fp)
        except Exception:
            pass


def _handle_workspace_on_startup():
    """启动时处理工作空间：检测崩溃 / 清理"""
    if os.path.exists(SENTINEL_FILE):
        # 上次异常退出 → 询问用户（文案随当前界面语言）
        reply = QMessageBox.question(
            None,
            t("startup.recover_title"),
            t("startup.recover_body"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.No:
            _clear_workspace()
        # 删除旧的哨兵（下面会重建）
        try:
            os.remove(SENTINEL_FILE)
        except Exception:
            pass
    else:
        # 正常启动 → 清空工作空间
        _clear_workspace()

    # 创建哨兵文件
    try:
        with open(SENTINEL_FILE, "w") as f:
            f.write("active")
    except Exception:
        pass


def _cleanup_on_exit():
    """正常退出时清理"""
    _clear_workspace()
    try:
        if os.path.exists(SENTINEL_FILE):
            os.remove(SENTINEL_FILE)
    except Exception:
        pass


def main():
    app = QApplication(sys.argv)
    # 与窗口标题、品牌名保持一致，避免任务管理器显示旧名
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # 启动前恢复字号档位与界面语言，保证首帧与启动弹窗即按记忆渲染
    ui_scale.set_font_size_preset(pref_get("ui_font_size", "default"))
    set_language(pref_get("ui_language", "zh"))

    # 设置全局默认字体（支持中文）
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 启动时处理工作空间
    _handle_workspace_on_startup()

    window = MainWindow()
    window.show()

    # 注册退出清理
    app.aboutToQuit.connect(_cleanup_on_exit)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
