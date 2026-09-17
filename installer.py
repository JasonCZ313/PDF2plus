"""
PDF2plus 下载器 — 安装向导
自包含安装器：内嵌主程序，用户选择路径后释放并创建快捷方式
"""
import sys
import os
import shutil
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QCheckBox, QProgressBar, QFileDialog,
    QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

# ------------------------------------------------------------
# 资源路径（兼容 PyInstaller 打包后 _MEIPASS 临时目录）
# ------------------------------------------------------------
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

MAIN_EXE_SOURCE = resource_path("PDF2plus.exe")
MAIN_EXE_NAME = "PDF2plus.exe"
DEFAULT_DIR_NAME = "PDF2plus"
DEFAULT_INSTALL_DIR = os.path.join("C:\\", "Program Files", DEFAULT_DIR_NAME)

# ------------------------------------------------------------
# 安装线程（后台复制 + 创建快捷方式）
# ------------------------------------------------------------
class InstallThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, target_dir, create_shortcut):
        super().__init__()
        self.target_dir = target_dir
        self.create_shortcut = create_shortcut

    def run(self):
        try:
            self.progress.emit(5)
            # 递归创建目标目录
            os.makedirs(self.target_dir, exist_ok=True)
            self.progress.emit(20)

            # 复制主程序
            target_path = os.path.join(self.target_dir, MAIN_EXE_NAME)
            self._copy_with_progress(target_path)
            self.progress.emit(85)

            # 快捷方式
            if self.create_shortcut:
                self._create_desktop_shortcut(target_path)
            self.progress.emit(100)

            self.finished.emit(True, f"安装完成！\n\n程序位置：\n{target_path}")
        except PermissionError:
            self.finished.emit(
                False,
                "权限不足！\n\n请以【管理员身份】运行此安装程序，\n"
                "或选择其他安装路径（例如 D 盘、桌面等）。"
            )
        except Exception as e:
            self.finished.emit(False, f"安装失败：{str(e)}")

    def _copy_with_progress(self, target_path):
        """分块复制并在 20%~85% 之间推进进度"""
        total = os.path.getsize(MAIN_EXE_SOURCE)
        copied = 0
        chunk = 16 * 1024 * 1024  # 16 MB
        with open(MAIN_EXE_SOURCE, 'rb') as src, open(target_path, 'wb') as dst:
            while True:
                data = src.read(chunk)
                if not data:
                    break
                dst.write(data)
                copied += len(data)
                pct = 20 + int((copied / total) * 65)
                self.progress.emit(pct)

    def _create_desktop_shortcut(self, target_path):
        """通过 PowerShell 创建桌面快捷方式"""
        ps_script = (
            f'$desktop = [Environment]::GetFolderPath("Desktop");'
            f'$lnk = Join-Path $desktop "PDF2plus.lnk";'
            f'$WshShell = New-Object -ComObject WScript.Shell;'
            f'$Shortcut = $WshShell.CreateShortcut($lnk);'
            f'$Shortcut.TargetPath = "{target_path}";'
            f'$Shortcut.IconLocation = "{target_path},0";'
            f'$Shortcut.Description = "PDF2plus";'
            f'$Shortcut.WorkingDirectory = "{os.path.dirname(target_path)}";'
            f'$Shortcut.Save()'
        )
        subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            capture_output=True, timeout=15
        )


# ------------------------------------------------------------
# 安装向导主窗口
# ------------------------------------------------------------
class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF2plus — 安装向导")
        self.setFixedSize(540, 350)
        self._init_ui()
        self._apply_style()

    # ----- UI 布局 -----
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(28, 22, 28, 22)

        # 标题
        title = QLabel("PDF2plus")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # 副标题
        subtitle = QLabel("安装向导  ·  版本 V10.0.1")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        # 安装路径
        path_group = QGroupBox("安装路径")
        path_group_layout = QVBoxLayout()
        path_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(DEFAULT_INSTALL_DIR)
        path_row.addWidget(self.path_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(72)
        browse_btn.setObjectName("browseBtn")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        path_group_layout.addLayout(path_row)

        # 路径下方提示
        hint = QLabel("提示：如安装到 C:\\Program Files 需要管理员权限")
        hint.setObjectName("hintLabel")
        path_group_layout.addWidget(hint)

        path_group.setLayout(path_group_layout)
        layout.addWidget(path_group)

        # 桌面快捷方式复选框
        self.shortcut_cb = QCheckBox("创建桌面快捷方式")
        self.shortcut_cb.setChecked(True)
        layout.addWidget(self.shortcut_cb)

        layout.addStretch()

        # 安装按钮
        self.install_btn = QPushButton("开始安装")
        self.install_btn.setFixedHeight(42)
        self.install_btn.setObjectName("installBtn")
        self.install_btn.clicked.connect(self._install)
        layout.addWidget(self.install_btn)

        # 进度条（默认隐藏）
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.setLayout(layout)

    # ----- 选择目录 -----
    def _browse(self):
        current = self.path_input.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "选择安装目录", current)
        if path:
            self.path_input.setText(os.path.join(path, DEFAULT_DIR_NAME))

    # ----- 开始安装 -----
    def _install(self):
        target = self.path_input.text().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入安装路径。")
            return

        # 权限预检：如果是 C:\Program Files 且当前不是管理员，弹提示
        if target.lower().startswith("c:\\program files") and not self._is_admin():
            reply = QMessageBox.question(
                self, "管理员权限提示",
                "你选择的路径需要管理员权限。\n\n"
                "是否继续尝试安装？\n"
                "（如果失败，请以管理员身份重新运行安装程序）",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                return

        self.install_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        self.thread = InstallThread(target, self.shortcut_cb.isChecked())
        self.thread.progress.connect(self.progress.setValue)
        self.thread.finished.connect(self._on_finished)
        self.thread.start()

    def _on_finished(self, success, msg):
        self.progress.setVisible(False)
        self.install_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "安装完成", msg)
            self.close()
        else:
            QMessageBox.critical(self, "安装失败", msg)

    @staticmethod
    def _is_admin():
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False

    # ----- 样式 -----
    def _apply_style(self):
        self.setStyleSheet("""
            QWidget {
                background: #ffffff;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 10pt;
            }
            QLabel#titleLabel {
                font-size: 16pt;
                font-weight: bold;
                color: #1a73e8;
                padding: 0;
            }
            QLabel#subtitleLabel {
                font-size: 10pt;
                color: #888888;
                padding: 0;
            }
            QLabel#hintLabel {
                font-size: 9pt;
                color: #999999;
                padding: 2px 0 0 0;
            }
            QGroupBox {
                font-weight: bold;
                color: #333333;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 18px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #1a73e8;
            }
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 7px 10px;
                background: #fafafa;
                color: #333333;
                selection-background-color: #1a73e8;
            }
            QLineEdit:focus {
                border-color: #1a73e8;
                background: #ffffff;
            }
            QPushButton#installBtn {
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton#installBtn:hover {
                background: #1557b0;
            }
            QPushButton#installBtn:disabled {
                background: #a0c4f0;
            }
            QPushButton#browseBtn {
                background: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 7px 12px;
            }
            QPushButton#browseBtn:hover {
                background: #e0e0e0;
            }
            QCheckBox {
                spacing: 8px;
                color: #333333;
            }
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background: #f0f0f0;
            }
            QProgressBar::chunk {
                background: #1a73e8;
                border-radius: 3px;
            }
        """)


# ------------------------------------------------------------
# 入口
# ------------------------------------------------------------
def main():
    # 防止高 DPI 缩放模糊
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    # 安装向导窗口使用与产品一致的 PDF2+ 图标
    icon_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png"),
        resource_path("icon.png"),
        resource_path("icon.ico"),
    ]
    for icon_path in icon_candidates:
        if os.path.isfile(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break
    else:
        app.setWindowIcon(app.style().standardIcon(app.style().SP_ComputerIcon))

    win = InstallerWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
