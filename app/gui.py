"""主界面 - PyQt5 实现（V3.0：合并/转换 + 整理/安全/图片转PDF）"""
import os, sys, shutil, tempfile, subprocess

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QSplitter, QProgressBar, QMessageBox,
    QFileDialog, QDialog, QRadioButton, QSpinBox,
    QComboBox, QDialogButtonBox, QFrame, QMenu, QMenuBar,
    QAction, QApplication, QAbstractItemView, QGroupBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QLineEdit, QStyledItemDelegate, QStyleOptionViewItem, QStyle,
    QScrollArea, QSizePolicy, QFormLayout,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QPoint, QRect, QTimer
from PyQt5.QtGui import (
    QIcon, QFont, QColor, QDragEnterEvent, QDropEvent,
    QPainter, QPen, QBrush, QLinearGradient, QPalette
)

from app.config import (
    APP_NAME, APP_VERSION, APP_WIDTH, APP_HEIGHT, APP_AUTHOR,
    UI_MIN_WIDTH, UI_MIN_HEIGHT,
    UI_FONT_SIZE_DEFAULT, UI_FONT_SIZE_LARGE, UI_FONT_SIZE_XLARGE,
    UI_FONT_SIZE_LABELS,
)
from app.file_manager import (
    select_folder, import_pdfs_to_folder, list_pdfs,
    delete_file, save_order, load_order,
    get_pdf_page_count, choose_save_path,
    get_default_save_path, is_valid_path
)
from app.pdf_merger import merge_pdfs
from app.pdf_splitter import split_pdf_by_pages, split_pdf_by_copies, split_pdf_by_ranges
from app.pdf_converter import pdf_to_images, pdf_to_word
from app.pdf_compress import compress_pdf
from app.pdf_from_images import images_to_pdf
from app.pdf_stamp import stamp_pdf
from app.pdf_pages import apply_page_edits, get_page_count as get_pdf_page_count_secure
from app.pdf_security import (
    probe_encryption, encrypt_pdf, decrypt_pdf,
)
from app.feature_dialogs import (
    PasswordDialog, EncryptOptionsDialog, CompressDialog,
    StampDialog, ImagesToPdfDialog, PageManagerDialog,
)
from app.preferences import get as pref_get, set as pref_set
from app import history_manager
from app import ui_scale
from app import layout_fit
from app.ui_theme import build_light_qss, build_dark_qss, build_app_palette
from app.i18n import t, set_language, get_language, apply_dialog_button_box, translate_op_type
from app.responsive_dialog import ResponsiveDialog


# ============================================================
# 带取消功能的后台线程
# ============================================================

class WorkerThread(QThread):
    """带取消功能的后台线程：向任务注入 cancel_check，取消时保留 partial_result 供清理。"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self._cancelled = False
        self.task_func = task_func
        self.args = args
        self._kwargs = dict(kwargs)
        # 统一注入取消检查，任务函数可轮询；未实现的旧函数也不报错
        self._kwargs.setdefault("cancel_check", self._is_cancelled)
        # 取消后仍可能已产生部分文件，供界面清理半成品
        self.partial_result = None

    def cancel(self):
        """由「取消」按钮调用，置位后任务应尽快停止。"""
        self._cancelled = True

    def _is_cancelled(self):
        """供业务函数轮询：True 表示用户已请求取消。"""
        return self._cancelled

    def run(self):
        try:
            result = self.task_func(
                *self.args,
                progress_callback=self._on_progress,
                **self._kwargs
            )
            if self._cancelled:
                # 记下返回值（可能是已写出的文件列表），界面据此删除半成品
                self.partial_result = result
                self.finished.emit(None)
            else:
                self.partial_result = None
                self.finished.emit(result)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))

    def _on_progress(self, value: int):
        self.progress.emit(value)


# ============================================================
# 交替行背景色定义
# ============================================================

ROW_COLORS_LIGHT = [
    QColor(255, 249, 196, 65),   # 极淡黄，高透明度
    QColor(200, 230, 255, 65),   # 极淡蓝
    QColor(255, 210, 225, 65),   # 极淡粉
]
ROW_COLORS_DARK = [
    QColor(85, 83, 60, 70),      # 微暗黄调，低透明度
    QColor(55, 70, 90, 70),      # 微暗蓝调
    QColor(80, 55, 68, 70),      # 微暗粉调
]

HANDLE_BG_LIGHT = QColor("#E0E0E0")
HANDLE_BG_DARK = QColor("#3A3A3A")


# ============================================================
# 浅色 / 深色样式：由 ui_theme 按缩放因子动态生成
# ============================================================

# 兼容旧引用名：模块加载时先生成 1.0 倍样式，窗口缩放后再刷新
LIGHT_QSS = build_light_qss(1.0)
DARK_QSS = build_dark_qss(1.0)


# ============================================================
# 自定义 PDF 列表项绘制代理
# ============================================================

class PdfItemDelegate(QStyledItemDelegate):
    """为 PDF 列表项绘制：序号徽章、交替背景色、≡ 拖拽手柄（几何随 UI 缩放）。"""

    handle_pressed = pyqtSignal(int)  # 发送被点击手柄所在的行号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark_mode = False
        self._dragging_row = -1  # 正在被拖拽的行号

    def set_dark_mode(self, dark: bool):
        self._dark_mode = dark

    def set_dragging_row(self, row: int):
        """设置正在被拖拽的行号，-1 表示无拖拽"""
        self._dragging_row = row

    def _handle_width(self) -> int:
        """拖拽手柄宽度（随缩放）。"""
        return ui_scale.px(18)

    def _get_handle_rect(self, option):
        """计算手柄矩形：向右留间距，高度居中。"""
        rect = option.rect
        handle_width = self._handle_width()
        handle_height = ui_scale.px(32)
        margin_right = ui_scale.px(6)
        top = rect.top() + max(2, (rect.height() - handle_height) // 2)
        return QRect(
            rect.right() - handle_width - margin_right,
            top,
            handle_width,
            handle_height,
        )

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        row = index.row()
        total = index.model().rowCount()
        rect = option.rect
        handle_width = self._handle_width()
        check_size = ui_scale.px(20)
        badge_w = ui_scale.px(32)
        badge_h = ui_scale.px(28)
        check_left = ui_scale.px(36)
        badge_left = ui_scale.px(64)
        margin_right = ui_scale.px(6)
        handle_height = ui_scale.px(32)

        # --- 正在被拖拽的条目：半透明绘制 ---
        if row == self._dragging_row:
            painter.setOpacity(0.35)

        # --- 交替行背景色 ---
        if total > 0 and row < total:
            colors = ROW_COLORS_DARK if self._dark_mode else ROW_COLORS_LIGHT
            bg_color = colors[row % 3]
            painter.fillRect(rect, bg_color)
        else:
            bg = QColor("#313244") if self._dark_mode else QColor("#FFFFFF")
            painter.fillRect(rect, bg)

        # --- 选中高亮 ---
        if option.state & QStyle.State_Selected:
            highlight = QColor(60, 100, 200, 60) if not self._dark_mode else QColor(100, 140, 220, 60)
            painter.fillRect(rect, highlight)

        # --- 复选框 ---
        check_rect = QRect(
            rect.left() + check_left,
            rect.top() + (rect.height() - check_size) // 2,
            check_size,
            check_size,
        )
        check_state = index.data(Qt.CheckStateRole)
        is_checked = (check_state == Qt.Checked)
        is_partial = (check_state == Qt.PartiallyChecked)

        check_bg = QColor("#89B4FA") if (is_checked or is_partial) and self._dark_mode else (
            QColor("#2C6FBB") if (is_checked or is_partial) else
            QColor("#313244") if self._dark_mode else QColor("#FFF")
        )
        check_border = QColor("#585B70") if self._dark_mode else QColor("#B0B8C8")
        if is_checked or is_partial:
            check_border = check_bg

        painter.setPen(QPen(check_border, max(1, ui_scale.px(2))))
        painter.setBrush(check_bg)
        painter.drawRoundedRect(check_rect, ui_scale.px(4), ui_scale.px(4))

        if is_checked:
            painter.setPen(QPen(QColor("#FFF"), max(1, ui_scale.px(2))))
            painter.drawLine(
                check_rect.left() + ui_scale.px(4), check_rect.top() + ui_scale.px(10),
                check_rect.left() + ui_scale.px(8), check_rect.top() + ui_scale.px(14),
            )
            painter.drawLine(
                check_rect.left() + ui_scale.px(8), check_rect.top() + ui_scale.px(14),
                check_rect.left() + ui_scale.px(15), check_rect.top() + ui_scale.px(5),
            )
        elif is_partial:
            painter.setPen(QPen(QColor("#FFF"), max(1, ui_scale.px(2))))
            painter.drawLine(
                check_rect.left() + ui_scale.px(4), check_rect.top() + ui_scale.px(10),
                check_rect.left() + ui_scale.px(15), check_rect.top() + ui_scale.px(10),
            )

        # --- 序号徽章 ---
        badge_rect = QRect(
            rect.left() + badge_left,
            rect.top() + (rect.height() - badge_h) // 2,
            badge_w,
            badge_h,
        )
        badge_color = QColor("#2C6FBB") if not self._dark_mode else QColor("#89B4FA")
        painter.setPen(Qt.NoPen)
        painter.setBrush(badge_color)
        painter.drawRoundedRect(badge_rect, ui_scale.px(6), ui_scale.px(6))

        painter.setPen(QColor("#FFFFFF"))
        font_badge = QFont("Microsoft YaHei", ui_scale.font_px(11), QFont.Bold)
        painter.setFont(font_badge)
        painter.drawText(badge_rect, Qt.AlignCenter, str(row + 1))

        # --- 文件名 + 页数（大字号时最多两行换行，避免单行省略过多） ---
        text_left = badge_rect.right() + ui_scale.px(10)
        text_rect = QRect(
            text_left,
            rect.top() + ui_scale.px(2),
            rect.width() - text_left - handle_width - ui_scale.px(8),
            rect.height() - ui_scale.px(4),
        )

        name = index.data(Qt.DisplayRole) or ""
        text_color = QColor("#CDD6F4") if self._dark_mode else QColor("#333")
        painter.setPen(text_color)
        font_text = QFont("Microsoft YaHei", ui_scale.font_px(11))
        painter.setFont(font_text)
        # 两行显示；仍不够则末行省略，完整名靠 tooltip
        flags = Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap
        metrics = painter.fontMetrics()
        bounding = metrics.boundingRect(text_rect, flags, name)
        if bounding.height() > text_rect.height():
            # 手动压成最多两行并省略
            line_height = metrics.lineSpacing()
            max_lines = max(1, text_rect.height() // max(1, line_height))
            elided = metrics.elidedText(name, Qt.ElideRight, text_rect.width() * max_lines)
            painter.drawText(text_rect, flags, elided)
        else:
            painter.drawText(text_rect, flags, name)

        # --- 拖拽手柄区域（视觉左移一个手柄宽度，检测区位置不变）---
        handle_top = rect.top() + max(2, (rect.height() - handle_height) // 2)
        handle_rect = QRect(
            rect.right() - handle_width - margin_right - handle_width,
            handle_top,
            handle_width,
            handle_height,
        )
        handle_bg = HANDLE_BG_DARK if self._dark_mode else HANDLE_BG_LIGHT
        painter.fillRect(handle_rect, handle_bg)

        line_color = QColor("#555570") if self._dark_mode else QColor("#C0C0C0")
        painter.setPen(QPen(line_color, 1))
        painter.drawLine(handle_rect.topLeft(), handle_rect.bottomLeft())

        handle_text_color = QColor("#AAA") if self._dark_mode else QColor("#666")
        painter.setPen(handle_text_color)
        font_handle = QFont("Microsoft YaHei", ui_scale.font_px(9), QFont.Bold)
        painter.setFont(font_handle)
        painter.drawText(handle_rect, Qt.AlignCenter, "≡")

        painter.restore()

    def sizeHint(self, option, index):
        """行高随字号加高，大/特大时允许两行书名。"""
        base = 40
        if ui_scale.get_font_multiplier() >= 1.18:
            base = 52
        if ui_scale.get_font_multiplier() >= 1.36:
            base = 60
        return QSize(200, ui_scale.px(base))

    def editorEvent(self, event, model, option, index):
        """处理复选框点击和手柄点击（自定义绘制位置后必须手动处理）"""
        if event.type() == event.MouseButtonPress:
            handle_rect = self._get_handle_rect(option)
            if handle_rect.contains(event.pos()):
                self.handle_pressed.emit(index.row())
                return True
        if event.type() == event.MouseButtonRelease:
            rect = option.rect
            check_size = ui_scale.px(24)
            check_rect = QRect(
                rect.left() + ui_scale.px(36),
                rect.top() + (rect.height() - check_size) // 2,
                check_size,
                check_size,
            )
            if check_rect.contains(event.pos()):
                current = index.data(Qt.CheckStateRole)
                new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                model.setData(index, new_state, Qt.CheckStateRole)
                return True
        return super().editorEvent(event, model, option, index)


# ============================================================
# 自定义拖拽列表（复选框 + 拖拽手柄）
# ============================================================

class DragListWidget(QListWidget):
    order_changed = pyqtSignal()
    file_double_clicked = pyqtSignal()  # 双击文件名文字区域时触发预览

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self._drag_start_pos = None
        self._drag_initiated = False
        self._handle_width = ui_scale.px(18)
        self._dragging_row = -1  # 当前拖拽行号，-1=无拖拽

        # 安装自定义绘制代理
        self._delegate = PdfItemDelegate(self)
        self.setItemDelegate(self._delegate)
        # 连接 delegate 的手柄点击信号 → 启动拖拽
        self._delegate.handle_pressed.connect(self._on_handle_pressed)

        # 拖拽插入提示浮标
        self._drop_label = QLabel(t("list.drop_here"), self.viewport())
        self._apply_drop_label_style()
        self._drop_label.hide()
        self._drop_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.setStyleSheet(
            "QListWidget{padding:4px;}"
            "QListWidget::item:drop-indicator{background:#2979FF; height:6px;border-radius:2px;}"
        )

    def _apply_drop_label_style(self):
        """拖拽浮标样式随 UI 缩放更新。"""
        self._drop_label.setStyleSheet(
            f"QLabel{{background:#2979FF;color:#FFF;font-size:{ui_scale.font_px(12)}px;font-weight:bold;"
            f"padding:{ui_scale.px(3)}px {ui_scale.px(10)}px;border-radius:{ui_scale.px(10)}px;}}"
        )

    def apply_ui_scale(self):
        """窗口缩放/字号档位后刷新手柄宽度、行高与浮标样式。"""
        self._handle_width = ui_scale.px(18)
        base_height = 40
        if ui_scale.get_font_multiplier() >= 1.18:
            base_height = 52
        if ui_scale.get_font_multiplier() >= 1.36:
            base_height = 60
        row_height = ui_scale.px(base_height)
        for row_index in range(self.count()):
            item = self.item(row_index)
            if item is not None:
                item.setSizeHint(QSize(0, row_height))
        self._apply_drop_label_style()
        self.viewport().update()

    def set_delegate_dark_mode(self, dark: bool):
        """切换 delegate 的深色/浅色模式"""
        self._delegate.set_dark_mode(dark)
        self.viewport().update()

    def add_pdf_item(self, name, full_path, pages):
        # 完整书名交给绘制代理换行；页数附在名称后
        text = f"{name}{t('list.pages_suffix', pages=pages)}"
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, full_path)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        item.setToolTip(f"{name}\n{full_path}")
        base_height = 40
        if ui_scale.get_font_multiplier() >= 1.18:
            base_height = 52
        if ui_scale.get_font_multiplier() >= 1.36:
            base_height = 60
        item.setSizeHint(QSize(0, ui_scale.px(base_height)))
        self.addItem(item)

    def get_checked_count(self):
        c = 0
        for i in range(self.count()):
            if self.item(i).checkState() == Qt.Checked:
                c += 1
        return c

    def get_checked(self):
        return [i for i in range(self.count()) if self.item(i).checkState() == Qt.Checked]

    def get_checked_paths(self):
        return [self.item(i).data(Qt.UserRole) for i in self.get_checked()]

    def set_all_checked(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.count()):
            self.item(i).setCheckState(state)

    def _on_handle_pressed(self, row: int):
        """delegate 的手柄被点击 → 准备启动拖拽"""
        item = self.item(row)
        if item:
            self._dragging_row = row
            self._drag_start_pos = self.mapFromGlobal(self.cursor().pos())
            self._drag_initiated = False
            # 设置拖拽阈值触发
            QTimer.singleShot(0, self._check_drag_threshold)

    def _check_drag_threshold(self):
        """在下一个事件循环检查拖拽阈值"""
        if self._drag_start_pos is not None and not self._drag_initiated:
            # 立即启动拖拽（手柄区域点击直接启动，无需阈值）
            self._drag_initiated = True
            if self._dragging_row >= 0:
                self._delegate.set_dragging_row(self._dragging_row)
                self.viewport().update()
            self.startDrag(Qt.MoveAction)
            # 拖拽结束，恢复
            self._delegate.set_dragging_row(-1)
            self._dragging_row = -1
            self._drop_label.hide()
            self.viewport().update()

    def mousePressEvent(self, event):
        # 手柄点击已在 delegate editorEvent 中处理，这里只处理普通点击
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                # 检查是否在手柄区域（向右留6px间距，32px高居中，作为兜底）
                rect = self.visualItemRect(item)
                handle_zone = QRect(
                    rect.right() - self._handle_width - ui_scale.px(6),
                    rect.top() + ui_scale.px(4),
                    self._handle_width,
                    ui_scale.px(32),
                )
                if handle_zone.contains(event.pos()):
                    # 手柄区域，由 delegate editorEvent 处理，这里忽略
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._drag_initiated = False
        if self._dragging_row >= 0:
            self._delegate.set_dragging_row(-1)
            self._dragging_row = -1
            self.viewport().update()
        super().mouseReleaseEvent(event)

    def dropEvent(self, event):
        super().dropEvent(event)
        self._drag_start_pos = None
        self._drag_initiated = False
        self._dragging_row = -1
        self._delegate.set_dragging_row(-1)
        self._drop_label.hide()
        self.viewport().update()
        self.order_changed.emit()

    def dragMoveEvent(self, event):
        """限制拖拽范围仅在列表内部，同时更新插入提示浮标位置"""
        if self.rect().contains(event.pos()):
            super().dragMoveEvent(event)
            # 更新插入提示浮标位置
            self._update_drop_label(event.pos())
        else:
            self._drop_label.hide()
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开列表时隐藏提示"""
        self._drop_label.hide()
        super().dragLeaveEvent(event)

    def _update_drop_label(self, pos):
        """在拖拽位置显示插入提示浮标"""
        item = self.itemAt(pos)
        if item:
            rect = self.visualItemRect(item)
            # 判断插入位置：在条目上半部分 → 插入到该条目之前，下半部分 → 之后
            mid_y = rect.top() + rect.height() // 2
            if pos.y() < mid_y:
                label_y = rect.top() - 5
            else:
                label_y = rect.bottom() - 5
            # 偏右1/3位置，避开手柄区域
            label_x = rect.right() - 150
            self._drop_label.move(label_x, label_y)
            self._drop_label.show()
            self._drop_label.raise_()

    def mouseDoubleClickEvent(self, event):
        """只有双击文件名文字区域才触发预览，复选框和手柄区域不触发"""
        item = self.itemAt(event.pos())
        if not item:
            return
        rect = self.visualItemRect(item)
        # 文字区域左边界随缩放：复选框区 + 序号徽章 + 间距
        text_left = rect.left() + ui_scale.px(106)
        # 文字区域右边界: 手柄开始位置
        handle_left = rect.right() - self._handle_width - ui_scale.px(6)
        if text_left <= event.pos().x() < handle_left:
            self.file_double_clicked.emit()


# ============================================================
# 功能介绍面板（左下）
# ============================================================

class DescPanel(QTextEdit):
    """底部功能介绍：只读、无滚动条，高度由文档内容撑开。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setPlaceholderText(t("desc.placeholder"))
        self._dark_mode = False
        self._last_payload = None  # 用于缩放后重绘当前内容
        # 用文档边距代替 QSS padding，避免底部文字被内边距裁切
        self.document().setDocumentMargin(ui_scale.px(10))

    def set_dark_mode(self, dark: bool):
        self._dark_mode = dark

    def wheelEvent(self, event):
        """禁止滚轮滚动：悬停说明不能靠滚动阅读。"""
        event.ignore()

    def apply_ui_scale(self):
        """缩放后按上次内容刷新字号。"""
        if self._last_payload is None:
            self.clear_desc()
        else:
            title, desc, offline = self._last_payload
            self.show_desc(title, desc, offline)

    def show_desc(self, title, desc, offline=True):
        self._last_payload = (title, desc, offline)
        offline_text = t("desc.offline") if offline else t("desc.online")
        if self._dark_mode:
            text_color = "#E0E0E0"
            offline_color = "#80C080" if offline else "#FFB366"
        else:
            text_color = "#333"
            offline_color = "#008800" if offline else "#CC6600"
        title_fs = ui_scale.help_font_px(16)
        body_fs = ui_scale.help_font_px(14)
        meta_fs = ui_scale.help_font_px(13)
        self.document().setDocumentMargin(ui_scale.px(10))
        safe_title = (
            str(title).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        safe_desc = (
            str(desc).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        html = (
            f"<b style='font-size:{title_fs}px;'>&#128218; {safe_title}</b><br><br>"
            f"<span style='color:{text_color};font-size:{body_fs}px;line-height:1.45;'>{safe_desc}</span><br>"
            f"<span style='color:{offline_color};font-weight:bold;font-size:{meta_fs}px;'>"
            f"&#128274; {offline_text}</span>"
        )
        self.setHtml(html)

    def clear_desc(self):
        self._last_payload = None
        hint_color = "#B0B0B0" if self._dark_mode else "#999"
        self.setHtml(
            f"<span style='color:{hint_color};font-size:{ui_scale.help_font_px(14)}px;'>"
            f"{t('desc.idle')}</span>"
        )

    def content_height(self) -> int:
        """当前 HTML 完整显示所需高度（含内边距）。"""
        return _help_panel_content_height(self)


# ============================================================
# 使用方法面板（右下）
# ============================================================

class StepsPanel(QTextEdit):
    """底部使用方法：只读、无滚动条，高度由文档内容撑开。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setPlaceholderText(t("steps.placeholder"))
        self._dark_mode = False
        self._last_payload = None
        # 用文档边距代替 QSS padding，避免红字注意事项被框底裁切
        self.document().setDocumentMargin(ui_scale.px(10))

    def set_dark_mode(self, dark: bool):
        self._dark_mode = dark

    def wheelEvent(self, event):
        """禁止滚轮滚动：悬停说明不能靠滚动阅读。"""
        event.ignore()

    def apply_ui_scale(self):
        """缩放后按上次内容刷新字号。"""
        if self._last_payload is None:
            self.clear_steps()
        else:
            title, steps, warning = self._last_payload
            self.show_steps(title, steps, warning)

    def show_steps(self, title, steps, warning=""):
        self._last_payload = (title, steps, warning)
        if self._dark_mode:
            text_color = "#E0E0E0"
            warning_color = "#FF6B6B"
        else:
            text_color = "#333"
            warning_color = "#CC0000"
        title_fs = ui_scale.help_font_px(16)
        body_fs = ui_scale.help_font_px(14)
        warn_fs = ui_scale.help_font_px(13)
        self.document().setDocumentMargin(ui_scale.px(10))
        # 步骤换行转 HTML，避免 pre-wrap 把行高撑乱却仍裁切
        safe_title = (
            str(title).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        steps_html = (
            str(steps)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        warning_html = (
            str(warning)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        html = (
            f"<b style='font-size:{title_fs}px;'>&#128196; {t('steps.title', title=safe_title)}</b><br><br>"
            f"<span style='color:{text_color};font-size:{body_fs}px;line-height:1.5;'>{steps_html}</span>"
        )
        if warning:
            html += (
                f"<br><br><span style='color:{warning_color};font-weight:bold;font-size:{warn_fs}px;'>"
                f"&#9888; {warning_html}</span>"
            )
        self.setHtml(html)

    def clear_steps(self):
        self._last_payload = None
        hint_color = "#B0B0B0" if self._dark_mode else "#999"
        self.setHtml(
            f"<span style='color:{hint_color};font-size:{ui_scale.help_font_px(14)}px;'>"
            f"{t('steps.idle')}</span>"
        )

    def content_height(self) -> int:
        """当前 HTML 完整显示所需高度（含内边距）。"""
        return _help_panel_content_height(self)


def _help_panel_content_height(panel: QTextEdit) -> int:
    """
    按当前可视宽度测量文档高度，保证步骤与警告一次展示完。

    document.size() 不含 QTextEdit 边框；QSS padding 也不在文档尺寸里，
    必须把「控件高度 − 视口高度」加回去，并留一点末行防裁切余量。
    """
    viewport_width = panel.viewport().width()
    if viewport_width < 40:
        viewport_width = max(200, panel.width() - ui_scale.px(24))
    document = panel.document()
    document.setTextWidth(float(viewport_width))
    document_height = int(document.size().height() + 0.999)
    chrome = panel.height() - panel.viewport().height()
    if chrome < ui_scale.px(8):
        chrome = panel.frameWidth() * 2 + ui_scale.px(8)
    needed = document_height + chrome + ui_scale.px(10)
    return max(needed, ui_scale.help_min_height())


# ============================================================
# 拆分设置对话框（v2.1：移除保留原PDF复选框，由主窗口全局控制）
# ============================================================

class SplitDialog(ResponsiveDialog):
    """PDF 拆分设置；工作区窗，模式与范围分组，选项全文可见。"""

    DESIGN_WIDTH = 540
    DESIGN_HEIGHT = 430
    DIALOG_KIND = "workspace"

    def __init__(self, pdf_path, total_pages, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.total_pages = total_pages
        self._parent = parent
        self.setWindowTitle(t("split.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(ui_scale.px(520))
        self.setMinimumHeight(ui_scale.px(360))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        self.pdf_name_label = QLabel(t("split.working_on", name=os.path.basename(self.pdf_path)))
        is_dark = self._parent and getattr(self._parent, '_is_dark', False)
        self._split_is_dark = bool(is_dark)
        fs = ui_scale.font_px(13)
        pad_v, pad_h = ui_scale.px(6), ui_scale.px(10)
        radius = ui_scale.px(6)
        if is_dark:
            self.pdf_name_label.setStyleSheet(
                f"font-size:{fs}px; font-weight:bold; color:#89B4FA;"
                f"padding:{pad_v}px {pad_h}px; background:#1E2A3A; border-radius:{radius}px;"
            )
        else:
            self.pdf_name_label.setStyleSheet(
                f"font-size:{fs}px; font-weight:bold; color:#2C6FBB;"
                f"padding:{pad_v}px {pad_h}px; background:#E8F0FE; border-radius:{radius}px;"
            )
        self.pdf_name_label.setWordWrap(True)
        layout.addWidget(self.pdf_name_label)

        self.info_label = QLabel(t("split.info", pages=self.total_pages))
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        grp_mode = QGroupBox(t("split.mode"))
        mode_layout = QVBoxLayout(grp_mode)
        layout_fit.apply_layout_gaps(mode_layout, related=True)
        self.radio_pages = QRadioButton(t("split.by_pages"))
        self.radio_copies = QRadioButton(t("split.by_copies"))
        self.radio_ranges = QRadioButton(t("split.by_ranges"))
        self.radio_pages.setChecked(True)

        row1 = QHBoxLayout()
        layout_fit.apply_layout_gaps(row1, related=True)
        self.spin_pages = QSpinBox()
        self.spin_pages.setRange(1, self.total_pages)
        self.spin_pages.setValue(1)
        row1.addWidget(self.radio_pages)
        row1.addWidget(self.spin_pages)
        row1.addWidget(QLabel(t("split.pages_unit")))
        row1.addStretch()
        mode_layout.addLayout(row1)

        row2 = QHBoxLayout()
        layout_fit.apply_layout_gaps(row2, related=True)
        self.spin_copies = QSpinBox()
        self.spin_copies.setRange(1, self.total_pages)
        self.spin_copies.setValue(2)
        row2.addWidget(self.radio_copies)
        row2.addWidget(self.spin_copies)
        row2.addWidget(QLabel(t("split.copies_unit")))
        row2.addStretch()
        mode_layout.addLayout(row2)
        mode_layout.addWidget(self.radio_ranges)
        layout.addWidget(grp_mode)

        grp_range = QGroupBox(t("split.ranges_group"))
        range_layout = QVBoxLayout(grp_range)
        layout_fit.apply_layout_gaps(range_layout, related=True)
        # 功能简介：说明「一行一份」、页码规则与可滚动多行
        tip_color = "#AAA" if self._split_is_dark else "#666"
        self.ranges_tip_label = QLabel(t("split.ranges_tip"))
        self.ranges_tip_label.setWordWrap(True)
        self.ranges_tip_label.setStyleSheet(
            f"font-size:{ui_scale.font_px(12)}px; color:{tip_color};"
        )
        range_layout.addWidget(self.ranges_tip_label)

        self.range_table = QTableWidget(1, 2)
        self.range_table.setHorizontalHeaderLabels([t("split.col_start"), t("split.col_end")])
        self.range_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # 至少露出约 3 行，行多时用表格自带垂直滚动条（不再卡死在 160px）
        self.range_table.setMinimumHeight(self._range_table_min_height(ui_scale.get_scale()))
        self.range_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.range_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.range_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.range_table.setItem(0, 0, QTableWidgetItem("1"))
        self.range_table.setItem(0, 1, QTableWidgetItem(str(self.total_pages)))
        self.range_table.setEnabled(False)

        range_btns = QHBoxLayout()
        layout_fit.apply_layout_gaps(range_btns, related=True)
        self.btn_add_range = QPushButton(t("split.add_range"))
        self.btn_del_range = QPushButton(t("split.del_range"))
        self.btn_add_range.setEnabled(False)
        self.btn_del_range.setEnabled(False)
        self.btn_add_range.clicked.connect(self._add_range_row)
        self.btn_del_range.clicked.connect(self._del_range_row)
        range_btns.addWidget(self.btn_add_range)
        range_btns.addWidget(self.btn_del_range)
        range_btns.addStretch()
        range_layout.addWidget(self.range_table, 1)
        range_layout.addLayout(range_btns)
        layout.addWidget(grp_range, 1)

        self.radio_pages.toggled.connect(self._on_mode_changed)
        self.radio_ranges.toggled.connect(self._on_mode_changed)
        self._on_mode_changed()

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def apply_dialog_scale(self):
        """拆分弹窗：通用字号 + 标题条/表格 + 按钮全文。"""
        self.apply_common_chrome()
        self.apply_root_gaps(related=False)
        fs = self.dfs(13)
        pad_v, pad_h = self.dpx(6), self.dpx(10)
        radius = self.dpx(6)
        if self._split_is_dark:
            self.pdf_name_label.setStyleSheet(
                f"font-size:{fs}px; font-weight:bold; color:#89B4FA;"
                f"padding:{pad_v}px {pad_h}px; background:#1E2A3A; border-radius:{radius}px;"
            )
        else:
            self.pdf_name_label.setStyleSheet(
                f"font-size:{fs}px; font-weight:bold; color:#2C6FBB;"
                f"padding:{pad_v}px {pad_h}px; background:#E8F0FE; border-radius:{radius}px;"
            )
        tip_color = "#AAA" if self._split_is_dark else "#666"
        self.info_label.setStyleSheet(
            f"font-size:{fs}px; color:"
            f"{'#CDD6F4' if self.is_dark_theme() else '#333333'};"
        )
        self.ranges_tip_label.setStyleSheet(
            f"font-size:{self.dfs(12)}px; color:{tip_color};"
        )
        # 按当前弹窗缩放刷新表格最小高度，保证约 3 行可见并可滚动
        self.range_table.setMinimumHeight(self._range_table_min_height(self._dialog_scale))
        layout_fit.fit_buttons((self.btn_add_range, self.btn_del_range), self._dialog_scale)
        layout_fit.fit_spin_with_suffix(
            self.spin_pages, sample_text=str(self.total_pages), scale=self._dialog_scale
        )
        layout_fit.fit_spin_with_suffix(
            self.spin_copies, sample_text=str(self.total_pages), scale=self._dialog_scale
        )
        self.fit_dialog_buttons(self._button_box)

    def _range_table_min_height(self, scale: float = None) -> int:
        """
        计算范围表最小高度：表头 + 约 3 行数据，让用户一眼看出可多行。
        行数更多时由表格垂直滚动条承接，不再用过矮的 maxHeight 卡死。
        """
        use_scale = scale if scale is not None else ui_scale.get_scale()
        header_h = ui_scale.px(32, use_scale)
        row_h = ui_scale.px(28, use_scale)
        return header_h + row_h * 3 + ui_scale.px(8, use_scale)

    def _on_mode_changed(self):
        is_custom = self.radio_ranges.isChecked()
        self.spin_pages.setEnabled(self.radio_pages.isChecked())
        self.spin_copies.setEnabled(self.radio_copies.isChecked())
        self.range_table.setEnabled(is_custom)
        self.btn_add_range.setEnabled(is_custom)
        self.btn_del_range.setEnabled(is_custom)

    def _add_range_row(self):
        row = self.range_table.rowCount()
        self.range_table.insertRow(row)
        self.range_table.setItem(row, 0, QTableWidgetItem("1"))
        self.range_table.setItem(row, 1, QTableWidgetItem("1"))

    def _del_range_row(self):
        rows = set(i.row() for i in self.range_table.selectedItems())
        if not rows:
            return
        if self.range_table.rowCount() <= 1:
            return
        for row in sorted(rows, reverse=True):
            self.range_table.removeRow(row)

    def _get_custom_ranges(self):
        ranges = []
        for row in range(self.range_table.rowCount()):
            try:
                s = int(self.range_table.item(row, 0).text()) - 1
                e = int(self.range_table.item(row, 1).text()) - 1
                if s < 0:
                    s = 0
                if e >= self.total_pages:
                    e = self.total_pages - 1
                if s <= e:
                    ranges.append((s, e))
            except Exception:
                continue
        return ranges

    def _on_accept(self):
        """确定前校验：自定义范围若全部无效则提示，避免空结果。"""
        if self.radio_ranges.isChecked():
            ranges = self._get_custom_ranges()
            if not ranges:
                QMessageBox.warning(
                    self, t("dialog.tip"), t("msg.split_ranges_empty")
                )
                return
        self.accept()

    def get_result(self):
        if self.radio_pages.isChecked():
            return ("pages", self.spin_pages.value())
        elif self.radio_copies.isChecked():
            return ("copies", self.spin_copies.value())
        else:
            return ("ranges", self._get_custom_ranges())


# ============================================================
# 图片导出设置对话框
# ============================================================

class ImageExportDialog(ResponsiveDialog):
    """图片导出设置；紧凑表单，格式与 DPI 成组贴紧。"""

    DESIGN_WIDTH = 400
    DESIGN_HEIGHT = 260
    DIALOG_KIND = "compact"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("export.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(ui_scale.px(380))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        grp = QGroupBox(t("export.params"))
        form = QFormLayout(grp)
        layout_fit.apply_layout_gaps(form, related=True)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems(["png", "jpg", "bmp", "tiff"])
        saved_fmt = pref_get("image_format", "png")
        idx = self.cmb_fmt.findText(saved_fmt)
        if idx >= 0:
            self.cmb_fmt.setCurrentIndex(idx)
        form.addRow(t("export.format"), self.cmb_fmt)

        self.cmb_dpi = QComboBox()
        # 用稳定 key 存偏好，界面显示走翻译
        self._dpi_option_keys = ["dpi_300", "dpi_600", "dpi_custom"]
        for dpi_key, label_key in (
            ("dpi_300", "export.dpi_300"),
            ("dpi_600", "export.dpi_600"),
            ("dpi_custom", "export.dpi_custom"),
        ):
            self.cmb_dpi.addItem(t(label_key), dpi_key)
        saved_dpi = pref_get("image_dpi", "dpi_300")
        # 兼容旧版中文偏好值
        legacy_dpi_map = {
            "300 (高清)": "dpi_300",
            "600 (超高精)": "dpi_600",
            "自定义": "dpi_custom",
        }
        saved_dpi = legacy_dpi_map.get(saved_dpi, saved_dpi)
        idx2 = self.cmb_dpi.findData(saved_dpi)
        if idx2 < 0:
            idx2 = 0
        self.cmb_dpi.setCurrentIndex(idx2)
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 1200)
        # 上下箭头每次 ±50，方便在 72～1200 间快速调节，不必一格一格点
        self.spin_dpi.setSingleStep(50)
        self.spin_dpi.setValue(300)
        self.spin_dpi.setSuffix(" DPI")
        self.spin_dpi.setToolTip(t("export.dpi_spin_tip"))
        self.spin_dpi.setVisible(self.cmb_dpi.currentData() == "dpi_custom")
        self.cmb_dpi.currentIndexChanged.connect(self._on_dpi_index)

        dpi_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(dpi_row, related=True)
        dpi_row.addWidget(self.cmb_dpi, 1)
        dpi_row.addWidget(self.spin_dpi)
        form.addRow(t("export.dpi"), dpi_row)

        # 清晰度范围说明，避免用户不知道自定义上下限
        is_dark = self.parent() and getattr(self.parent(), "_is_dark", False)
        tip_color = "#AAA" if is_dark else "#666"
        self.dpi_hint_label = QLabel(t("export.dpi_hint"))
        self.dpi_hint_label.setWordWrap(True)
        self.dpi_hint_label.setStyleSheet(
            f"font-size:{ui_scale.font_px(12)}px; color:{tip_color};"
        )
        form.addRow("", self.dpi_hint_label)
        layout.addWidget(grp)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def apply_dialog_scale(self):
        """导出设置：字号 + Spin 防裁切 + 范围提示字色。"""
        super().apply_dialog_scale()
        layout_fit.fit_spin_with_suffix(
            self.spin_dpi, sample_text="1200 DPI", scale=self._dialog_scale
        )
        tip_color = "#AAA" if self.is_dark_theme() else "#666"
        self.dpi_hint_label.setStyleSheet(
            f"font-size:{self.dfs(12)}px; color:{tip_color};"
        )

    def _on_dpi_index(self, index):
        """自定义 DPI 时显示数值框。"""
        self.spin_dpi.setVisible(self.cmb_dpi.itemData(index) == "dpi_custom")

    def _on_accept(self):
        pref_set("image_format", self.cmb_fmt.currentText())
        pref_set("image_dpi", self.cmb_dpi.currentData() or "dpi_300")
        self.accept()

    def get_result(self):
        fmt = self.cmb_fmt.currentText()
        dpi_key = self.cmb_dpi.currentData() or "dpi_300"
        if dpi_key == "dpi_300":
            dpi = 300
        elif dpi_key == "dpi_600":
            dpi = 600
        else:
            dpi = self.spin_dpi.value()
        return fmt, dpi


# ============================================================
# 彩色圆形按钮（历史记录用）
# ============================================================

class ColorButton(QPushButton):
    """彩色圆形按钮，悬停时发送信号显示功能说明（尺寸随弹窗本地缩放）。"""
    hovered = pyqtSignal(str)
    unhovered = pyqtSignal()

    def __init__(self, color, desc="", parent=None):
        super().__init__(parent)
        self._desc = desc
        self._color = color
        self._scale_factor = 1.0
        self._apply_scale_style()
        self.setCursor(Qt.PointingHandCursor)

    def apply_dialog_scale(self, scale_factor: float):
        """由历史记录弹窗调用，按弹窗比例刷新圆形尺寸。"""
        self._scale_factor = scale_factor
        self._apply_scale_style()

    def _apply_scale_style(self):
        """按当前缩放设置圆形按钮尺寸与样式。"""
        size = ui_scale.px(22, self._scale_factor)
        radius = size // 2
        self.setFixedSize(size, size)
        self.setStyleSheet(
            f"QPushButton{{background:{self._color}; border:none; border-radius:{radius}px;}}"
            f"QPushButton:hover{{border:2px solid #FFFFFF;}}"
        )

    def enterEvent(self, event):
        self.hovered.emit(self._desc)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.unhovered.emit()
        super().leaveEvent(event)


# ============================================================
# 历史记录对话框
# ============================================================

class HistoryDialog(ResponsiveDialog):
    """历史记录；表格吃空间，图例与说明贴紧底部。"""

    DESIGN_WIDTH = 1050
    DESIGN_HEIGHT = 480
    DIALOG_KIND = "workspace"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark = parent and getattr(parent, '_is_dark', False)
        self.setWindowTitle(t("history.title"))
        self.setMinimumSize(ui_scale.px(1050), ui_scale.px(480))
        # 去掉标题栏 "?" 按钮
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                t("history.col_time"),
                t("history.col_type"),
                t("history.col_sources"),
                t("history.col_output"),
                t("history.col_actions"),
                t("history.col_delete"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnWidth(4, ui_scale.px(120))  # 操作列
        self.table.setColumnWidth(5, ui_scale.px(55))   # 删除列
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table, 1)

        # 颜色图例说明（用彩色圆点+文字）
        c1, c2, c3, c4 = "#2979FF", "#4CAF50", "#FF9800", "#F44336"
        legend_text = t(
            "history.legend", c1=c1, c2=c2, c3=c3, c4=c4
        )
        self._legend = QLabel(legend_text)
        legend_color = "#AAA" if self._is_dark else "#666"
        self._legend_color = legend_color
        self._legend.setStyleSheet(
            f"font-size:{ui_scale.font_px(11)}px; color:{legend_color}; "
            f"padding:{ui_scale.px(4)}px {ui_scale.px(8)}px;"
        )
        self._legend.setWordWrap(True)
        layout.addWidget(self._legend)

        # 按钮功能说明面板（悬停时显示）
        self._desc_bg = "#2A2A3E" if self._is_dark else "#F5F5F5"
        self._desc_text_color = "#CDD6F4" if self._is_dark else "#333"
        self._desc_label = QLabel(t("history.hover_hint"))
        self._desc_label.setStyleSheet(
            f"font-size:{ui_scale.font_px(12)}px; color:{self._desc_text_color};"
            f"background:{self._desc_bg}; border-radius:{ui_scale.px(6)}px; "
            f"padding:{ui_scale.px(6)}px {ui_scale.px(12)}px;"
        )
        self._desc_label.setMinimumHeight(ui_scale.px(30))
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

    def apply_dialog_scale(self):
        """历史记录：表格/图例字号 + 行内彩色圆钮尺寸。"""
        self.apply_common_chrome()
        self.table.setColumnWidth(4, self.dpx(120))
        self.table.setColumnWidth(5, self.dpx(55))
        self._legend.setStyleSheet(
            f"font-size:{self.dfs(11)}px; color:{self._legend_color}; "
            f"padding:{self.dpx(4)}px {self.dpx(8)}px;"
        )
        self._desc_label.setStyleSheet(
            f"font-size:{self.dfs(12)}px; color:{self._desc_text_color};"
            f"background:{self._desc_bg}; border-radius:{self.dpx(6)}px; "
            f"padding:{self.dpx(6)}px {self.dpx(12)}px;"
        )
        self._desc_label.setMinimumHeight(self.dpx(30))
        # 遍历操作列/删除列里的 ColorButton，按弹窗比例放大
        for row in range(self.table.rowCount()):
            for column in (4, 5):
                cell_widget = self.table.cellWidget(row, column)
                if cell_widget is None:
                    continue
                for child in cell_widget.findChildren(ColorButton):
                    child.apply_dialog_scale(self._dialog_scale)

    def refresh(self):
        records = history_manager.get_all_records()
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(r.get("time", "")))
            self.table.setItem(
            row, 1, QTableWidgetItem(translate_op_type(r.get("type", "")))
        )
            n_src = len(r.get("source_paths", []))
            self.table.setItem(row, 2, QTableWidgetItem(str(n_src)))
            out = r.get("output_path", "")
            self.table.setItem(row, 3, QTableWidgetItem(
                os.path.basename(out) if out else ""
            ))

            op_widget = QWidget()
            op_layout = QHBoxLayout(op_widget)
            op_layout.setContentsMargins(4, 6, 4, 6)
            op_layout.setSpacing(6)

            btn_dl = ColorButton("#2979FF", t("history.dl_desc"))
            btn_dl.setToolTip(t("history.dl_tip"))
            btn_dl.apply_dialog_scale(self._dialog_scale)
            btn_dl.hovered.connect(self._desc_label.setText)
            btn_dl.unhovered.connect(lambda: self._desc_label.setText(t("history.hover_hint")))
            btn_dl.clicked.connect(lambda checked, rid=r["id"]: self._download(rid))

            btn_src = ColorButton("#4CAF50", t("history.src_desc"))
            btn_src.setToolTip(t("history.src_tip"))
            btn_src.apply_dialog_scale(self._dialog_scale)
            btn_src.hovered.connect(self._desc_label.setText)
            btn_src.unhovered.connect(lambda: self._desc_label.setText(t("history.hover_hint")))
            btn_src.clicked.connect(lambda checked, rid=r["id"]: self._open_src(rid))

            btn_out = ColorButton("#FF9800", t("history.out_desc"))
            btn_out.setToolTip(t("history.out_tip"))
            btn_out.apply_dialog_scale(self._dialog_scale)
            btn_out.hovered.connect(self._desc_label.setText)
            btn_out.unhovered.connect(lambda: self._desc_label.setText(t("history.hover_hint")))
            btn_out.clicked.connect(lambda checked, rid=r["id"]: self._open_out(rid))

            op_layout.addWidget(btn_dl)
            op_layout.addWidget(btn_src)
            op_layout.addWidget(btn_out)
            self.table.setCellWidget(row, 4, op_widget)

            del_widget = QWidget()
            del_layout = QHBoxLayout(del_widget)
            del_layout.setContentsMargins(4, 6, 4, 6)
            btn_del = ColorButton("#F44336", t("history.del_desc"))
            btn_del.setToolTip(t("history.del_tip"))
            btn_del.apply_dialog_scale(self._dialog_scale)
            btn_del.hovered.connect(self._desc_label.setText)
            btn_del.unhovered.connect(lambda: self._desc_label.setText(t("history.hover_hint")))
            btn_del.clicked.connect(lambda checked, rid=r["id"]: self._del(rid))
            del_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 5, del_widget)

    def _download(self, record_id):
        record = history_manager.get_record(record_id)
        if not record:
            return
        out = record.get("output_path", "")
        ext = os.path.splitext(out)[1] if out else ""
        default_name = t("history.restore_name", id=record_id, ext=ext)
        # 同步默认保存路径
        default_dir = pref_get("default_save_path", "")
        if not default_dir or not is_valid_path(default_dir):
            default_dir = get_default_save_path()
        dest, _ = QFileDialog.getSaveFileName(self, t("history.save_as"), os.path.join(default_dir, default_name))
        if dest:
            if history_manager.download_output(record_id, dest):
                QMessageBox.information(self, t("dialog.done"), t("history.dl_ok"))
            else:
                QMessageBox.warning(self, t("dialog.failed"), t("history.dl_fail"))

    def _open_src(self, record_id):
        record = history_manager.get_record(record_id)
        if record and record.get("source_paths"):
            d = os.path.dirname(record["source_paths"][0])
            if os.path.exists(d):
                os.startfile(d)

    def _open_out(self, record_id):
        record = history_manager.get_record(record_id)
        if record and record.get("output_path"):
            d = os.path.dirname(record["output_path"])
            if os.path.exists(d):
                os.startfile(d)

    def _del(self, record_id):
        r = QMessageBox.question(self, t("dialog.confirm"), t("history.del_confirm"))
        if r == QMessageBox.Yes:
            history_manager.delete_record(record_id)
            self.refresh()


# ============================================================
# 主窗口
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.cancel_requested = False
        # 后台任务队列：多选拆分/转图时串行执行，禁止覆盖正在跑的 Worker
        self._task_queue = []
        self._batch_active = False
        self._batch_total = 0
        self._batch_index = 0
        self._batch_results = []
        self._is_dark = False
        # 窗口缩放防抖定时器：拖拽过程中避免频繁重刷 QSS
        self._scale_timer = QTimer(self)
        self._scale_timer.setSingleShot(True)
        self._scale_timer.timeout.connect(self._on_scale_timer)
        self.init_ui()
        self.connect_signals()
        # 首帧显示后按实际窗口尺寸应用一次缩放
        QTimer.singleShot(0, self._refresh_ui_scale)

    # ---------- 界面搭建 ----------

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(UI_MIN_WIDTH, UI_MIN_HEIGHT)
        self.resize(APP_WIDTH, APP_HEIGHT)

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base, "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 支持外部拖入 PDF
        self.setAcceptDrops(True)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        self._root_layout = root
        root.setContentsMargins(14, 6, 14, 10)
        root.setSpacing(8)

        # ===== 顶部：默认保存路径设置 =====
        self._setup_path_bar(root)

        # ===== 中部：文件列表 + 操作面板 =====
        mid_splitter = QSplitter(Qt.Horizontal)
        mid_splitter.setChildrenCollapsible(False)
        self._mid_splitter = mid_splitter

        # -- 左侧：文件列表 --
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        select_row = QHBoxLayout()
        self.chk_select_all = QCheckBox(t("list.select_all"))
        self.chk_select_all.setTristate(False)
        self.lbl_checked_count = QLabel(t("list.checked", count=0))
        self.lbl_checked_count.setStyleSheet("color:#2C6FBB;font-weight:bold;")
        select_row.addWidget(self.chk_select_all)
        select_row.addStretch()
        select_row.addWidget(self.lbl_checked_count)
        left_layout.addLayout(select_row)

        self.list_widget = DragListWidget()
        left_layout.addWidget(self.list_widget, 1)

        # 第一行：仅文件操作，避免与偏好下拉抢同一行宽度导致特大字号叠钮
        list_btn_row = QHBoxLayout()
        self._list_btn_row = list_btn_row
        layout_fit.apply_layout_gaps(list_btn_row, related=True)
        self.btn_import = QPushButton(t("btn.import"))
        self.btn_import.setMinimumHeight(32)
        self.btn_remove = QPushButton(t("btn.remove"))
        self.btn_remove.setMinimumHeight(32)
        self.btn_preview = QPushButton(t("btn.preview"))
        self.btn_preview.setMinimumHeight(32)
        list_btn_row.addWidget(self.btn_import)
        list_btn_row.addWidget(self.btn_remove)
        list_btn_row.addWidget(self.btn_preview)
        list_btn_row.addStretch()
        left_layout.addLayout(list_btn_row)

        # 第二行：字号 / 主题 / 历史 / 语言，单独占满左栏宽度，特大与英文不再互压
        pref_btn_row = QHBoxLayout()
        self._pref_btn_row = pref_btn_row
        layout_fit.apply_layout_gaps(pref_btn_row, related=True)
        pref_btn_row.setSpacing(ui_scale.px(12))

        self._lbl_font_size = QLabel(t("label.font"))
        self._lbl_font_size.setStyleSheet("font-size:11px; color:#888;")
        self.cmb_font_size = QComboBox()
        self._font_size_keys = [
            UI_FONT_SIZE_DEFAULT,
            UI_FONT_SIZE_LARGE,
            UI_FONT_SIZE_XLARGE,
        ]
        _font_label_keys = {
            UI_FONT_SIZE_DEFAULT: "font.default",
            UI_FONT_SIZE_LARGE: "font.large",
            UI_FONT_SIZE_XLARGE: "font.xlarge",
        }
        for font_key in self._font_size_keys:
            self.cmb_font_size.addItem(t(_font_label_keys[font_key]), font_key)
        pref_btn_row.addWidget(self._lbl_font_size)
        pref_btn_row.addWidget(self.cmb_font_size)

        self._lbl_theme = QLabel(t("label.theme"))
        self._lbl_theme.setStyleSheet("font-size:11px; color:#888;")
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItem(t("theme.light"), "light")
        self.cmb_theme.addItem(t("theme.dark"), "dark")
        pref_btn_row.addWidget(self._lbl_theme)
        pref_btn_row.addWidget(self.cmb_theme)

        self.btn_history = QPushButton(t("btn.history"))
        self.btn_history.setToolTip(t("btn.history.tip"))
        pref_btn_row.addWidget(self.btn_history)

        self._lbl_language = QLabel(t("label.language"))
        self._lbl_language.setStyleSheet("font-size:11px; color:#888;")
        self.cmb_language = QComboBox()
        self.cmb_language.addItem(t("lang.zh"), "zh")
        self.cmb_language.addItem(t("lang.en"), "en")
        pref_btn_row.addWidget(self._lbl_language)
        pref_btn_row.addWidget(self.cmb_language)
        pref_btn_row.addStretch()
        left_layout.addLayout(pref_btn_row)

        mid_splitter.addWidget(left_panel)

        # -- 右侧：功能面板（可滚动，避免小屏裁切 V3 按钮） --
        right_panel = QWidget()
        self._right_panel = right_panel
        # 右侧功能栏加宽：英语长按钮与大字号不易裁切叠字
        right_panel.setMaximumWidth(420)
        right_panel.setMinimumWidth(300)
        right_outer = QVBoxLayout(right_panel)
        self._right_layout = right_outer
        right_outer.setContentsMargins(10, 0, 0, 0)
        right_outer.setSpacing(0)

        right_scroll = QScrollArea()
        self._right_scroll = right_scroll
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        scroll_content = QWidget()
        self._right_scroll_content = scroll_content
        right_layout = QVBoxLayout(scroll_content)
        right_layout.setContentsMargins(0, 0, 4, 0)
        # 不同功能分组之间用较大间距
        right_layout.setSpacing(layout_fit.gap_section())
        self._right_scroll_layout = right_layout

        # 合并分组
        self.grp_merge = QGroupBox(t("group.merge"))
        grp_merge = self.grp_merge
        g1 = QVBoxLayout(grp_merge)
        layout_fit.apply_layout_gaps(g1, related=True)
        self.btn_merge = QPushButton(t("btn.merge"))
        self.btn_merge.setMinimumHeight(38)
        g1.addWidget(self.btn_merge)
        right_layout.addWidget(grp_merge)

        # 转换分组
        self.grp_convert = QGroupBox(t("group.convert"))
        grp_convert = self.grp_convert
        g2 = QVBoxLayout(grp_convert)
        layout_fit.apply_layout_gaps(g2, related=True)

        self.chk_copy_original = QCheckBox(t("btn.copy_original"))
        self.chk_copy_original.setChecked(
            pref_get("copy_original_pdf_on_convert", False)
        )
        self.chk_copy_original.setStyleSheet(
            "QCheckBox{font-weight:bold;color:#2C6FBB;margin-bottom:4px;}"
        )
        g2.addWidget(self.chk_copy_original)

        self.btn_split = QPushButton(t("btn.split"))
        self.btn_to_images = QPushButton(t("btn.to_images"))
        self.btn_to_word = QPushButton(t("btn.to_word"))
        for b in [self.btn_split, self.btn_to_images, self.btn_to_word]:
            b.setMinimumHeight(36)
            g2.addWidget(b)
        right_layout.addWidget(grp_convert)

        # 整理分组：压缩 / 页面 / 水印页码
        self.grp_organize = QGroupBox(t("group.organize"))
        grp_organize = self.grp_organize
        g_organize = QVBoxLayout(grp_organize)
        layout_fit.apply_layout_gaps(g_organize, related=True)
        self.btn_compress = QPushButton(t("btn.compress"))
        self.btn_pages = QPushButton(t("btn.pages"))
        self.btn_stamp = QPushButton(t("btn.stamp"))
        for organize_button in (self.btn_compress, self.btn_pages, self.btn_stamp):
            organize_button.setMinimumHeight(34)
            g_organize.addWidget(organize_button)
        right_layout.addWidget(grp_organize)

        # 安全分组：加密 / 解密
        self.grp_security = QGroupBox(t("group.security"))
        grp_security = self.grp_security
        g_security = QVBoxLayout(grp_security)
        layout_fit.apply_layout_gaps(g_security, related=True)
        self.btn_encrypt = QPushButton(t("btn.encrypt"))
        self.btn_decrypt = QPushButton(t("btn.decrypt"))
        for security_button in (self.btn_encrypt, self.btn_decrypt):
            security_button.setMinimumHeight(34)
            g_security.addWidget(security_button)
        right_layout.addWidget(grp_security)

        # 新建分组：图片转 PDF（不依赖列表选中）
        self.grp_create = QGroupBox(t("group.create"))
        grp_create = self.grp_create
        g_create = QVBoxLayout(grp_create)
        layout_fit.apply_layout_gaps(g_create, related=True)
        self.btn_images_to_pdf = QPushButton(t("btn.images_to_pdf"))
        self.btn_images_to_pdf.setMinimumHeight(34)
        g_create.addWidget(self.btn_images_to_pdf)
        right_layout.addWidget(grp_create)

        right_layout.addStretch()

        right_scroll.setWidget(scroll_content)
        right_outer.addWidget(right_scroll)

        mid_splitter.addWidget(right_panel)
        root.addWidget(mid_splitter, 1)

        # ===== 底部：双面板（功能介绍 | 使用方法） =====
        bottom_splitter = QSplitter(Qt.Horizontal)
        self._bottom_splitter = bottom_splitter
        bottom_splitter.setChildrenCollapsible(False)

        self.desc_panel = DescPanel()
        self.steps_panel = StepsPanel()
        bottom_splitter.addWidget(self.desc_panel)
        bottom_splitter.addWidget(self.steps_panel)
        bottom_splitter.setSizes([500, 500])
        # 不参与 stretch：高度由内容决定，避免被中间列表挤成一条还带滚动条
        root.addWidget(bottom_splitter, 0)

        # ===== 底部：进度条 + 取消按钮 =====
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.btn_cancel = QPushButton(t("main.cancel"))
        self.btn_cancel.setMinimumHeight(28)
        self.btn_cancel.setMaximumWidth(80)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setStyleSheet(
            "QPushButton{color:#CC0000;font-weight:bold;}"
        )
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.btn_cancel)
        root.addLayout(progress_row)

        self.statusBar().showMessage(t("main.ready"))

        # 右下角：版本号（固定可见）+ 制作人署名
        self._lbl_version = QLabel(f"V{APP_VERSION}")
        self._lbl_version.setStyleSheet(
            f"font-size:{ui_scale.font_px(11)}px; color:#2C6FBB; font-weight:bold; padding-right:10px;"
        )
        self._lbl_version.setToolTip(t("main.version_tip", app=APP_NAME, version=APP_VERSION))
        self.statusBar().addPermanentWidget(self._lbl_version)

        credit = QLabel(
            t("main.credit", color="#2C6FBB", author=APP_AUTHOR)
        )
        credit.setStyleSheet("font-size:11px; color:#888; padding-right:8px;")
        self._lbl_credit = credit
        self.statusBar().addPermanentWidget(credit)

        # 先恢复界面语言，再刷文案与悬停
        saved_language = pref_get("ui_language", "zh")
        set_language(saved_language)
        lang_index = 1 if get_language() == "en" else 0
        self.cmb_language.blockSignals(True)
        self.cmb_language.setCurrentIndex(lang_index)
        self.cmb_language.blockSignals(False)
        self.retranslate_ui()

        # 设置悬停信息
        self._setup_hover_info()

        # 加载字号档位（须在主题/缩放刷新前写入 ui_scale）
        saved_font = pref_get("ui_font_size", UI_FONT_SIZE_DEFAULT)
        ui_scale.set_font_size_preset(saved_font)
        font_index = self._font_size_keys.index(saved_font) if saved_font in self._font_size_keys else 0
        self.cmb_font_size.blockSignals(True)
        self.cmb_font_size.setCurrentIndex(font_index)
        self.cmb_font_size.blockSignals(False)
        # 大/特大字号：首屏按倍率加宽加高，避免偏好行与功能钮重叠
        self._ensure_startup_window_room()

        # 加载主题偏好并应用
        saved_theme = pref_get("theme", "light")
        self._apply_theme(saved_theme)
        theme_index = self.cmb_theme.findData(saved_theme)
        self.cmb_theme.blockSignals(True)
        self.cmb_theme.setCurrentIndex(theme_index if theme_index >= 0 else 0)
        self.cmb_theme.blockSignals(False)

        # 启动后自动加载工作空间的 PDF
        self.refresh_file_list()

    def _ensure_startup_window_room(self):
        """
        按当前字号倍率抬高初始窗口尺寸（不超过可用屏幕），
        解决英语界面与「特大」字号下首屏文案裁切、按键重叠。
        """
        font_multiplier = max(1.0, ui_scale.get_font_multiplier())
        target_width = max(self.width(), int(APP_WIDTH * font_multiplier))
        target_height = max(self.height(), int(APP_HEIGHT * font_multiplier))
        primary_screen = QApplication.primaryScreen()
        if primary_screen is not None:
            # 留出任务栏等边距，避免启动时超出可见区域
            available_geometry = primary_screen.availableGeometry()
            target_width = min(target_width, int(available_geometry.width() * 0.96))
            target_height = min(target_height, int(available_geometry.height() * 0.92))
        if target_width > self.width() or target_height > self.height():
            self.resize(target_width, target_height)

    def resizeEvent(self, event):
        """窗口尺寸变化时防抖触发 UI 缩放刷新。"""
        super().resizeEvent(event)
        self._scale_timer.start(90)

    def _on_scale_timer(self):
        """防抖到期后真正计算并应用缩放。"""
        self._refresh_ui_scale()

    def _refresh_ui_scale(self):
        """根据当前窗口客户区计算缩放；变化够大才刷新界面。"""
        ui_scale.set_window_height(self.height())
        new_scale = ui_scale.compute_scale(self.width(), self.height())
        if not ui_scale.scale_changed_significantly(new_scale):
            # 首次也可能正好是 1.0，仍需确保控件几何已按 scale 应用过
            if getattr(self, "_scale_applied_once", False):
                # 全局 scale 已顶满时，窗口再变高仍要放大底部说明字号与高度
                theme = "dark" if self._is_dark else "light"
                self._apply_theme_accents(theme)
                self.desc_panel.apply_ui_scale()
                self.steps_panel.apply_ui_scale()
                QTimer.singleShot(0, self._fit_bottom_help_panels)
                return
        ui_scale.set_scale(new_scale)
        self._scale_applied_once = True
        self.apply_ui_scale()

    def apply_ui_scale(self):
        """
        将当前缩放应用到：全局 QSS、关键控件尺寸、列表与说明面板。
        主题色逻辑仍走 _apply_theme，此处只负责尺寸与字号。
        """
        theme = "dark" if self._is_dark else "light"
        # 先更新全局样式（含字号）与调色板，再套主题强调色内联样式
        app = QApplication.instance()
        app.setPalette(build_app_palette(self._is_dark))
        if self._is_dark:
            app.setStyleSheet(build_dark_qss())
        else:
            app.setStyleSheet(build_light_qss())

        if hasattr(self, "_root_layout"):
            self._root_layout.setContentsMargins(
                ui_scale.px(14), ui_scale.px(6), ui_scale.px(14), ui_scale.px(10)
            )
            self._root_layout.setSpacing(ui_scale.px(8))

        if hasattr(self, "_right_panel"):
            # 随缩放同步右侧栏宽限，英语/特大字时仍可完整显示按钮文案
            self._right_panel.setMinimumWidth(ui_scale.px(300))
            self._right_panel.setMaximumWidth(ui_scale.px(420))
        if hasattr(self, "_right_layout"):
            self._right_layout.setContentsMargins(ui_scale.px(10), 0, 0, 0)
        if hasattr(self, "_right_scroll_layout"):
            self._right_scroll_layout.setSpacing(layout_fit.gap_section())
            self._right_scroll_layout.setContentsMargins(0, 0, ui_scale.px(4), 0)

        self.btn_import.setMinimumHeight(ui_scale.px(32))
        self.btn_remove.setMinimumHeight(ui_scale.px(32))
        self.btn_preview.setMinimumHeight(ui_scale.px(32))
        self.btn_merge.setMinimumHeight(ui_scale.px(38))
        for action_button in (self.btn_split, self.btn_to_images, self.btn_to_word):
            action_button.setMinimumHeight(ui_scale.px(36))
        for organize_button in (
            self.btn_compress, self.btn_pages, self.btn_stamp,
            self.btn_encrypt, self.btn_decrypt, self.btn_images_to_pdf,
        ):
            organize_button.setMinimumHeight(ui_scale.px(34))

        # 主界面按钮按全文撑宽，避免省略号
        layout_fit.fit_buttons(
            (
                self.btn_import, self.btn_remove, self.btn_preview,
                self.btn_merge, self.btn_split, self.btn_to_images, self.btn_to_word,
                self.btn_compress, self.btn_pages, self.btn_stamp,
                self.btn_encrypt, self.btn_decrypt, self.btn_images_to_pdf,
                self.btn_history,
            )
        )

        # 各 GroupBox 组内间距随缩放收紧
        for group_box in self._right_scroll_content.findChildren(QGroupBox):
            group_layout = group_box.layout()
            if group_layout is not None:
                layout_fit.apply_layout_gaps(group_layout, related=True)

        # 导入行右侧偏好控件：字号 + 主题成套下拉样式（切换主题时也必须重套）
        self._apply_preference_chrome(theme)
        self.btn_cancel.setMinimumHeight(ui_scale.px(28))
        self.btn_cancel.setMaximumWidth(ui_scale.px(80))

        # 字号加大时主窗最小尺寸同步抬高，避免控件挤爆
        min_w = int(UI_MIN_WIDTH * max(1.0, ui_scale.get_font_multiplier()))
        min_h = int(UI_MIN_HEIGHT * max(1.0, ui_scale.get_font_multiplier()))
        self.setMinimumSize(min_w, min_h)

        if hasattr(self, "input_save_path"):
            self.input_save_path.setMinimumHeight(ui_scale.px(30))
        if hasattr(self, "btn_browse_path"):
            self.btn_browse_path.setMinimumHeight(ui_scale.px(30))
            self.btn_browse_path.setMinimumWidth(ui_scale.px(70))

        self.list_widget.apply_ui_scale()
        self.desc_panel.apply_ui_scale()
        self.steps_panel.apply_ui_scale()

        # 重新套主题相关内联样式（合并按钮强调色等），避免被全局 QSS 冲掉后尺寸不对
        self._apply_theme_accents(theme)
        self._validate_path_input()
        # HTML 排版后再按文档高度撑开，避免出现滚动条
        QTimer.singleShot(0, self._fit_bottom_help_panels)

    def _apply_preference_chrome(self, theme: str):
        """
        导入行右侧：字号/主题下拉与历史按钮按当前主题成套着色。
        必须在切换主题时调用，否则本地深色 QSS 会残留在浅色界面上。
        """
        is_dark = (theme == "dark")
        meta_fs = ui_scale.font_px(11)
        pad_v = ui_scale.px(2)
        pad_h = ui_scale.px(6)
        label_color = "#A6ADC8" if is_dark else "#888888"
        for label in (self._lbl_font_size, self._lbl_theme, self._lbl_language):
            label.setStyleSheet(f"font-size:{meta_fs}px; color:{label_color};")
            # 同步 QFont，避免量宽用小字、绘制用大字导致溢出叠字
            label_font = QFont(label.font())
            label_font.setPixelSize(meta_fs)
            label.setFont(label_font)
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if is_dark:
            combo_qss = (
                f"QComboBox{{font-size:{meta_fs}px; padding:{pad_v}px {pad_h}px;"
                f"color:#CDD6F4; background:#313244; border:1px solid #454560;}}"
                f"QComboBox:hover, QComboBox:focus, QComboBox:on{{"
                f"border-color:#89B4FA; color:#CDD6F4; background:#313244;}}"
                f"QComboBox::drop-down{{border:none; width:{ui_scale.px(22)}px; background:transparent;}}"
                f"QComboBox QAbstractItemView{{background:#313244; color:#CDD6F4;"
                f"selection-background-color:#454560; selection-color:#CDD6F4; outline:none;}}"
                f"QComboBox QAbstractItemView::item{{color:#CDD6F4; background:#313244;"
                f"padding:{pad_v}px {pad_h}px;}}"
                f"QComboBox QAbstractItemView::item:selected{{color:#CDD6F4; background:#454560;}}"
                f"QComboBox QAbstractItemView::item:hover{{color:#CDD6F4; background:#3A3A55;}}"
            )
            history_qss = (
                f"QPushButton{{font-size:{meta_fs}px; padding:{pad_v}px {ui_scale.px(10)}px;"
                f"color:#CDD6F4; background:#2E2E40; border:1px solid #454560;}}"
                f"QPushButton:hover{{background:#3A3A55; border-color:#89B4FA; color:#CDD6F4;}}"
            )
        else:
            combo_qss = (
                f"QComboBox{{font-size:{meta_fs}px; padding:{pad_v}px {pad_h}px;"
                f"color:#333333; background:#FFFFFF; border:1px solid #D0D5DD;}}"
                f"QComboBox:hover, QComboBox:focus, QComboBox:on{{"
                f"border-color:#2C6FBB; color:#333333; background:#FFFFFF;}}"
                f"QComboBox::drop-down{{border:none; width:{ui_scale.px(22)}px; background:transparent;}}"
                f"QComboBox QAbstractItemView{{background:#FFFFFF; color:#333333;"
                f"selection-background-color:#E8F0FE; selection-color:#1A1A1A; outline:none;}}"
                f"QComboBox QAbstractItemView::item{{color:#333333; background:#FFFFFF;"
                f"padding:{pad_v}px {pad_h}px;}}"
                f"QComboBox QAbstractItemView::item:selected{{color:#1A1A1A; background:#E8F0FE;}}"
                f"QComboBox QAbstractItemView::item:hover{{color:#1A1A1A; background:#F0F3FF;}}"
            )
            history_qss = (
                f"QPushButton{{font-size:{meta_fs}px; padding:{pad_v}px {ui_scale.px(10)}px;"
                f"color:#333333; background:#FFFFFF; border:1px solid #D0D5DD;}}"
                f"QPushButton:hover{{background:#F0F3FF; border-color:#2C6FBB; color:#333333;}}"
            )
        for combo in (self.cmb_font_size, self.cmb_theme, self.cmb_language):
            combo.setMinimumHeight(ui_scale.px(28))
            combo.setStyleSheet(combo_qss)
        # 按「当前界面语言下最宽选项 + 实际像素字号」撑开，特大/英文不再盖住右侧「主题」等标签
        layout_fit.fit_combo_min_width(
            self.cmb_font_size,
            (t("font.default"), t("font.large"), t("font.xlarge")),
            pixel_size=meta_fs,
        )
        layout_fit.fit_combo_min_width(
            self.cmb_theme,
            (t("theme.light"), t("theme.dark")),
            pixel_size=meta_fs,
        )
        layout_fit.fit_combo_min_width(
            self.cmb_language,
            (t("lang.zh"), t("lang.en")),
            pixel_size=meta_fs,
        )
        layout_fit.fit_widget_min_width(self._lbl_font_size, t("label.font"), extra=ui_scale.px(8))
        layout_fit.fit_widget_min_width(self._lbl_theme, t("label.theme"), extra=ui_scale.px(8))
        layout_fit.fit_widget_min_width(self._lbl_language, t("label.language"), extra=ui_scale.px(8))
        self.btn_history.setMinimumHeight(ui_scale.px(28))
        self.btn_history.setStyleSheet(history_qss)
        layout_fit.fit_button(self.btn_history)
        # 偏好行独立布局：加大组内间距，标签与下拉、历史按钮互不贴边
        if hasattr(self, "_pref_btn_row") and self._pref_btn_row is not None:
            self._pref_btn_row.setSpacing(ui_scale.px(12))
        if hasattr(self, "_list_btn_row") and self._list_btn_row is not None:
            self._list_btn_row.setSpacing(ui_scale.px(10))

    def _paint_shell_surfaces(self, is_dark: bool):
        """
        主窗壳体铺底：中央区、左右栏、右侧滚动视口。
        QScrollArea 视口默认跟系统色，不显式铺色深色模式就会露白条。
        样式必须带 objectName 限定，避免无选择器背景色污染子控件。
        """
        shell_bg = "#1E1E2E" if is_dark else "#F5F6FA"
        panel_bg = "#1E1E2E" if is_dark else "#F5F6FA"
        path_bg = "#252536" if is_dark else "#FFFFFF"
        path_border = "#3A3A50" if is_dark else "#DDE"
        handle_bg = "#3A3A50" if is_dark else "#E0E4EA"
        radius = ui_scale.px(8)

        central = self.centralWidget()
        if central is not None:
            central.setObjectName("centralShell")
            central.setAutoFillBackground(True)
            central.setStyleSheet(f"#centralShell{{background:{shell_bg};}}")

        if hasattr(self, "_mid_splitter"):
            self._mid_splitter.setObjectName("midSplitter")
            self._mid_splitter.setStyleSheet(
                f"#midSplitter{{background:{shell_bg};}}"
                f"#midSplitter::handle{{background:{handle_bg};}}"
            )

        if hasattr(self, "_right_panel"):
            self._right_panel.setObjectName("rightPanelShell")
            self._right_panel.setAutoFillBackground(True)
            self._right_panel.setStyleSheet(
                f"#rightPanelShell{{background:{panel_bg};}}"
            )

        if hasattr(self, "_right_scroll"):
            self._right_scroll.setObjectName("rightScrollShell")
            self._right_scroll.setAutoFillBackground(True)
            self._right_scroll.setStyleSheet(
                f"#rightScrollShell{{background:{panel_bg}; border:none;}}"
                f"#rightScrollShell > QWidget{{background:{panel_bg};}}"
            )
            viewport = self._right_scroll.viewport()
            if viewport is not None:
                viewport.setAutoFillBackground(True)
                viewport_palette = viewport.palette()
                viewport_palette.setColor(QPalette.Window, QColor(panel_bg))
                viewport_palette.setColor(QPalette.Base, QColor(panel_bg))
                viewport.setPalette(viewport_palette)

        if hasattr(self, "_right_scroll_content"):
            self._right_scroll_content.setObjectName("rightScrollContent")
            self._right_scroll_content.setAutoFillBackground(True)
            self._right_scroll_content.setStyleSheet(
                f"#rightScrollContent{{background:{panel_bg};}}"
            )

        if hasattr(self, "_path_frame"):
            self._path_frame.setObjectName("pathFrameShell")
            self._path_frame.setStyleSheet(
                f"#pathFrameShell{{background:{path_bg}; border:1px solid {path_border};"
                f"border-radius:{radius}px;}}"
            )

    def _fit_bottom_help_panels(self):
        """
        按全部悬停文案（含空闲提示）取最大所需高度，一次定高且不加滚动条。
        悬停只换文字、不改高度，避免按钮上移导致鼠标进出死循环抖动。
        窗口缩放 / 换语言 / 换字号时再重新测算。
        """
        if not hasattr(self, "desc_panel") or not hasattr(self, "steps_panel"):
            return

        # 测量前冻结重绘，避免逐条写入 HTML 时闪一下
        self.desc_panel.setUpdatesEnabled(False)
        self.steps_panel.setUpdatesEnabled(False)
        try:
            saved_desc = self.desc_panel._last_payload
            saved_steps = self.steps_panel._last_payload
            target_height = ui_scale.help_min_height()

            # 空闲文案也要参与比高
            self.desc_panel.clear_desc()
            self.steps_panel.clear_steps()
            target_height = max(
                target_height,
                self.desc_panel.content_height(),
                self.steps_panel.content_height(),
            )

            # 遍历所有功能悬停文案，取左右面板所需高度的全局最大值
            for payload in getattr(self, "_hover_payloads", []):
                self.desc_panel.show_desc(payload["title"], payload["desc"], True)
                self.steps_panel.show_steps(
                    payload["title"], payload["steps"], payload["warning"]
                )
                target_height = max(
                    target_height,
                    self.desc_panel.content_height(),
                    self.steps_panel.content_height(),
                )

            # 恢复测量前正在显示的内容
            if saved_desc is None:
                self.desc_panel.clear_desc()
            else:
                title_text, desc_text, offline_flag = saved_desc
                self.desc_panel.show_desc(title_text, desc_text, offline_flag)
            if saved_steps is None:
                self.steps_panel.clear_steps()
            else:
                title_text, steps_text, warning_text = saved_steps
                self.steps_panel.show_steps(title_text, steps_text, warning_text)

            self.desc_panel.setFixedHeight(target_height)
            self.steps_panel.setFixedHeight(target_height)
        finally:
            self.desc_panel.setUpdatesEnabled(True)
            self.steps_panel.setUpdatesEnabled(True)

    def _apply_theme_accents(self, theme: str):
        """仅更新主题强调色与面板局部样式（字号已按当前 scale）。"""
        is_dark = (theme == "dark")
        self._paint_shell_surfaces(is_dark)
        fs_merge = ui_scale.font_px(14)
        fs_panel = ui_scale.font_px(12)
        fs_help = ui_scale.help_font_px(14)
        fs_meta = ui_scale.font_px(11)
        pad = ui_scale.px(8)
        radius = ui_scale.px(8)

        if is_dark:
            self.btn_merge.setStyleSheet(
                f"QPushButton{{font-size:{fs_merge}px;font-weight:bold;"
                f"background:#89B4FA;color:#1E1E2E;border-radius:{radius}px;border:none;}}"
                f"QPushButton:hover{{background:#A0C8FF;}}"
            )
            self.btn_cancel.setStyleSheet(
                "QPushButton{color:#F38BA8;font-weight:bold;}"
            )
            self.lbl_checked_count.setStyleSheet(
                "color:#89B4FA;font-weight:bold;"
            )
            self.chk_copy_original.setStyleSheet(
                f"QCheckBox{{font-weight:bold;color:#89B4FA;margin-bottom:{ui_scale.px(4)}px;}}"
            )
            self.desc_panel.setStyleSheet(
                f"QTextEdit{{background:#252536;border:1px solid #3A3A50;"
                f"border-radius:{radius}px;padding:0px;font-size:{fs_help}px;color:#CDD6F4;}}"
            )
            self.steps_panel.setStyleSheet(
                f"QTextEdit{{background:#252536;border:1px solid #3A3A50;"
                f"border-radius:{radius}px;padding:0px;font-size:{fs_help}px;color:#CDD6F4;}}"
            )
            self.lbl_path_status.setStyleSheet(
                f"font-size:{fs_panel}px;color:#A6ADC8;"
            )
            self._lbl_theme.setStyleSheet(
                f"font-size:{fs_meta}px; color:#A6ADC8;"
            )
            if hasattr(self, "_lbl_font_size"):
                self._lbl_font_size.setStyleSheet(
                    f"font-size:{fs_meta}px; color:#A6ADC8;"
                )
            if hasattr(self, "_lbl_version"):
                self._lbl_version.setText(f"V{APP_VERSION}")
                self._lbl_version.setStyleSheet(
                    f"font-size:{fs_meta}px; color:#89B4FA; font-weight:bold; padding-right:10px;"
                )
            self._lbl_credit.setText(
                t("main.credit", color="#89B4FA", author=APP_AUTHOR)
            )
            self._lbl_credit.setStyleSheet(
                f"font-size:{fs_meta}px; color:#A6ADC8; padding-right:{ui_scale.px(8)}px;"
            )
        else:
            self.btn_merge.setStyleSheet(
                f"QPushButton{{font-size:{fs_merge}px;font-weight:bold;"
                f"background:#2C6FBB;color:white;border-radius:{radius}px;border:none;}}"
                f"QPushButton:hover{{background:#3A80D0;}}"
            )
            self.btn_cancel.setStyleSheet(
                "QPushButton{color:#CC0000;font-weight:bold;}"
            )
            self.lbl_checked_count.setStyleSheet(
                "color:#2C6FBB;font-weight:bold;"
            )
            self.chk_copy_original.setStyleSheet(
                f"QCheckBox{{font-weight:bold;color:#2C6FBB;margin-bottom:{ui_scale.px(4)}px;}}"
            )
            self.desc_panel.setStyleSheet(
                f"QTextEdit{{background:#FFF8E1;border:1px solid #E0D5A0;"
                f"border-radius:{radius}px;padding:0px;font-size:{fs_help}px;color:#333;}}"
            )
            self.steps_panel.setStyleSheet(
                f"QTextEdit{{background:#E8F5E9;border:1px solid #A5D6A7;"
                f"border-radius:{radius}px;padding:0px;font-size:{fs_help}px;color:#333;}}"
            )
            self.lbl_path_status.setStyleSheet(f"font-size:{fs_panel}px;")
            self._lbl_theme.setStyleSheet(f"font-size:{fs_meta}px; color:#888;")
            if hasattr(self, "_lbl_font_size"):
                self._lbl_font_size.setStyleSheet(f"font-size:{fs_meta}px; color:#888;")
            if hasattr(self, "_lbl_version"):
                self._lbl_version.setText(f"V{APP_VERSION}")
                self._lbl_version.setStyleSheet(
                    f"font-size:{fs_meta}px; color:#2C6FBB; font-weight:bold; padding-right:10px;"
                )
            self._lbl_credit.setText(
                t("main.credit", color="#2C6FBB", author=APP_AUTHOR)
            )
            self._lbl_credit.setStyleSheet(
                f"font-size:{fs_meta}px; color:#888; padding-right:{ui_scale.px(8)}px;"
            )
    def _setup_path_bar(self, root):
        """顶部默认保存路径栏"""
        path_frame = QFrame()
        self._path_frame = path_frame
        path_frame.setFrameShape(QFrame.StyledPanel)
        path_layout = QVBoxLayout(path_frame)
        path_layout.setContentsMargins(12, 8, 12, 8)
        path_layout.setSpacing(4)
        self._path_layout = path_layout

        # 第一行：输入框 + 浏览按钮
        row1 = QHBoxLayout()
        lbl = QLabel(t("path.label"))
        self._lbl_save_path = lbl
        lbl.setStyleSheet(
            f"font-size:{ui_scale.font_px(13)}px; font-weight:bold;"
        )
        self.input_save_path = QLineEdit()
        self.input_save_path.setMinimumHeight(ui_scale.px(30))
        self.input_save_path.setPlaceholderText(t("path.placeholder"))
        self.btn_browse_path = QPushButton(t("dialog.browse"))
        self.btn_browse_path.setMinimumHeight(ui_scale.px(30))
        self.btn_browse_path.setMinimumWidth(ui_scale.px(70))

        row1.addWidget(lbl)
        row1.addWidget(self.input_save_path, 1)
        row1.addWidget(self.btn_browse_path)
        path_layout.addLayout(row1)

        # 第二行：记住路径 + 状态提示
        row2 = QHBoxLayout()
        self.chk_remember_path = QCheckBox(t("path.remember"))
        self.chk_remember_path.setChecked(pref_get("remember_save_path", True))
        self.lbl_path_status = QLabel("")
        row2.addWidget(self.chk_remember_path)
        row2.addStretch()
        row2.addWidget(self.lbl_path_status)
        path_layout.addLayout(row2)

        root.addWidget(path_frame)

        # 初始化路径显示
        saved_path = pref_get("default_save_path", "")
        if saved_path:
            self.input_save_path.setText(saved_path)
            self._validate_path_input()
        else:
            self.lbl_path_status.setText(t("path.unset"))
            self.lbl_path_status.setStyleSheet(
                f"color:#888;font-size:{ui_scale.font_px(12)}px;"
            )

    def _path_edit_stylesheet(self, border_color: str, background: str = "", text_color: str = "") -> str:
        """按当前缩放生成路径输入框样式。"""
        parts = [
            f"padding:{ui_scale.px(4)}px {ui_scale.px(8)}px",
            f"font-size:{ui_scale.font_px(13)}px",
            f"border:1px solid {border_color}",
            f"border-radius:{ui_scale.px(4)}px",
        ]
        if background:
            # 有效/无效状态用更粗边框
            parts[2] = f"border:2px solid {border_color}"
            parts.append(f"background:{background}")
        if text_color:
            parts.append(f"color:{text_color}")
        return "QLineEdit{" + ";".join(parts) + ";}"

    def _validate_path_input(self):
        """校验输入框中的路径是否有效"""
        path = self.input_save_path.text().strip()
        is_dark = getattr(self, '_is_dark', False)
        fs = ui_scale.font_px(12)
        if hasattr(self, "_lbl_save_path"):
            self._lbl_save_path.setStyleSheet(
                f"font-size:{ui_scale.font_px(13)}px; font-weight:bold;"
            )
        if hasattr(self, "_path_layout"):
            self._path_layout.setContentsMargins(
                ui_scale.px(12), ui_scale.px(8), ui_scale.px(12), ui_scale.px(8)
            )
            self._path_layout.setSpacing(ui_scale.px(4))
        if not path:
            border = "#454560" if is_dark else "#BBB"
            self.input_save_path.setStyleSheet(self._path_edit_stylesheet(border))
            self.lbl_path_status.setText(t("path.unset"))
            self.lbl_path_status.setStyleSheet(
                f"color:#A6ADC8;font-size:{fs}px;" if is_dark
                else f"color:#888;font-size:{fs}px;"
            )
            return True  # 空路径允许（回退桌面）
        if is_valid_path(path):
            if is_dark:
                self.input_save_path.setStyleSheet(
                    self._path_edit_stylesheet("#4CAF50", "#1B3A1B", "#A5D6A7")
                )
            else:
                self.input_save_path.setStyleSheet(
                    self._path_edit_stylesheet("#4CAF50", "#F1F8E9")
                )
            self.lbl_path_status.setText(t("path.valid"))
            self.lbl_path_status.setStyleSheet(
                f"color:#A5D6A7;font-size:{fs}px;font-weight:bold;" if is_dark
                else f"color:#4CAF50;font-size:{fs}px;font-weight:bold;"
            )
            return True
        else:
            if is_dark:
                self.input_save_path.setStyleSheet(
                    self._path_edit_stylesheet("#E53935", "#3A1B1B", "#EF9A9A")
                )
            else:
                self.input_save_path.setStyleSheet(
                    self._path_edit_stylesheet("#E53935", "#FFEBEE")
                )
            self.lbl_path_status.setText(t("path.invalid"))
            self.lbl_path_status.setStyleSheet(
                f"color:#EF9A9A;font-size:{fs}px;font-weight:bold;" if is_dark
                else f"color:#E53935;font-size:{fs}px;font-weight:bold;"
            )
            return False

    def _get_effective_save_dir(self):
        """获取当前有效的保存目录（优先用户设置，否则桌面）"""
        path = self.input_save_path.text().strip()
        if path and is_valid_path(path):
            return path
        return get_default_save_path()

    def _ensure_valid_save_path(self):
        """确保默认保存路径有效，无效则弹窗提示"""
        path = self.input_save_path.text().strip()
        if path and not is_valid_path(path):
            QMessageBox.warning(
                self, t("path.invalid_warn_title"),
                t("path.invalid_warn_detail", path=path),
            )
            self.input_save_path.setFocus()
            return False
        return True

    # ---------- 悬停信息 ----------

    def _setup_hover_info(self):
        """配置按钮悬停时两个面板的内容（文案随当前语言）。"""
        def _hover(prefix, has_warn=False):
            return {
                "title": t(f"{prefix}.title"),
                "desc": t(f"{prefix}.desc"),
                "steps": t(f"{prefix}.steps"),
                "warning": t(f"{prefix}.warn") if has_warn else "",
            }

        hover_data = {
            self.btn_import: _hover("hover.import"),
            self.btn_remove: _hover("hover.remove"),
            self.btn_preview: _hover("hover.preview"),
            self.btn_merge: _hover("hover.merge"),
            self.btn_split: _hover("hover.split"),
            self.btn_to_images: _hover("hover.to_images"),
            self.btn_to_word: _hover("hover.to_word", True),
            self.btn_compress: _hover("hover.compress", True),
            self.btn_pages: _hover("hover.pages", True),
            self.btn_stamp: _hover("hover.stamp", True),
            self.btn_encrypt: _hover("hover.encrypt", True),
            self.btn_decrypt: _hover("hover.decrypt", True),
            self.btn_images_to_pdf: _hover("hover.img2pdf"),
            self.btn_browse_path: _hover("hover.path"),
            self.btn_history: _hover("hover.history"),
            self.cmb_font_size: _hover("hover.font", True),
            self.cmb_language: _hover("hover.language"),
        }
        # 供底部说明区按「全部文案最高篇」一次定高，避免悬停改高导致抖动
        self._hover_payloads = list(hover_data.values())

        for btn, data in hover_data.items():
            btn.setToolTip(data["steps"].replace('\u201c', '').replace('\u201d', ''))
            btn.enterEvent = (
                lambda e, d=data:
                self._on_btn_hover(d["title"], d["desc"], d["steps"], d["warning"])
            )
            btn.leaveEvent = lambda e: self._on_btn_leave()

    def _on_btn_hover(self, title, desc, steps, warning):
        """悬停只刷新说明文字；高度已由 _fit_bottom_help_panels 锁定，禁止再改高。"""
        self.desc_panel.show_desc(title, desc, True)
        self.steps_panel.show_steps(title, steps, warning)

    def _on_btn_leave(self):
        """离开按钮恢复空闲提示；同样不改底部高度，避免布局回弹。"""
        self.desc_panel.clear_desc()
        self.steps_panel.clear_steps()

    # ---------- 外部拖入 PDF ----------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            f = url.toLocalFile()
            if f.lower().endswith('.pdf'):
                files.append(f)
        if files:
            self._import_files(files)

    def _import_files(self, files):
        """将文件列表导入工作空间并刷新列表"""
        imported = import_pdfs_to_folder(files)
        self.refresh_file_list()
        self.statusBar().showMessage(t("msg.imported", count=len(imported)))

    # ---------- 信号连接 ----------

    def connect_signals(self):
        self.btn_import.clicked.connect(self.on_import_pdfs)
        self.btn_remove.clicked.connect(self.on_remove_selected)
        self.btn_preview.clicked.connect(self.on_preview)
        self.btn_merge.clicked.connect(self.on_merge)
        self.btn_split.clicked.connect(self.on_split)
        self.btn_to_images.clicked.connect(self.on_to_images)
        self.btn_to_word.clicked.connect(self.on_to_word)
        self.btn_compress.clicked.connect(self.on_compress)
        self.btn_pages.clicked.connect(self.on_page_manager)
        self.btn_stamp.clicked.connect(self.on_stamp)
        self.btn_encrypt.clicked.connect(self.on_encrypt)
        self.btn_decrypt.clicked.connect(self.on_decrypt)
        self.btn_images_to_pdf.clicked.connect(self.on_images_to_pdf)
        self.btn_cancel.clicked.connect(self.on_cancel)
        self.btn_browse_path.clicked.connect(self.on_browse_path)
        self.btn_history.clicked.connect(self.on_show_history)
        self.cmb_theme.currentIndexChanged.connect(self.on_theme_changed)
        self.cmb_language.currentIndexChanged.connect(self.on_language_changed)
        self.cmb_font_size.currentIndexChanged.connect(self.on_font_size_changed)
        self.input_save_path.textChanged.connect(self._on_path_text_changed)
        self.chk_remember_path.stateChanged.connect(self._on_remember_changed)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)
        self.list_widget.order_changed.connect(self.on_order_changed)
        self.list_widget.file_double_clicked.connect(self.on_preview)
        self.list_widget.itemChanged.connect(self.on_check_changed)
        self.chk_select_all.stateChanged.connect(self.on_select_all)
        self.chk_copy_original.stateChanged.connect(
            lambda s: pref_set("copy_original_pdf_on_convert", s == Qt.Checked)
        )

    # ---------- 默认保存路径操作 ----------

    def on_browse_path(self):
        folder = select_folder(self)
        if folder:
            self.input_save_path.setText(folder)
            # 自动保存到偏好（如有勾选记住）
            if self.chk_remember_path.isChecked():
                pref_set("default_save_path", folder)

    def _on_path_text_changed(self, text):
        self._validate_path_input()
        # 手动输入也自动保存（如有勾选）
        if self.chk_remember_path.isChecked() and text.strip():
            if is_valid_path(text.strip()):
                pref_set("default_save_path", text.strip())

    def _on_remember_changed(self, state):
        pref_set("remember_save_path", state == Qt.Checked)
        if state == Qt.Checked:
            path = self.input_save_path.text().strip()
            if path and is_valid_path(path):
                pref_set("default_save_path", path)
            else:
                pref_set("default_save_path", "")

    # ---------- 文件导入 ----------

    def on_import_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, t("file.import_title"), "", t("file.filter_pdf")
        )
        if files:
            self._import_files(files)

    # ---------- 文件列表刷新 ----------

    def refresh_file_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        try:
            paths = list_pdfs()
            for full_path in paths:
                name = os.path.basename(full_path)
                pages = get_pdf_page_count(full_path)
                self.list_widget.add_pdf_item(name, full_path, pages)
        finally:
            self.list_widget.blockSignals(False)
        self._update_checked_label()
        self.statusBar().showMessage(
            t("status.list_summary", count=self.list_widget.count())
        )

    # ---------- 勾选相关 ----------

    def on_check_changed(self, item):
        self._update_checked_label()
        total = self.list_widget.count()
        checked = self.list_widget.get_checked_count()
        self.chk_select_all.blockSignals(True)
        if checked == total and total > 0:
            self.chk_select_all.setCheckState(Qt.Checked)
        elif checked == 0:
            self.chk_select_all.setCheckState(Qt.Unchecked)
        else:
            self.chk_select_all.setCheckState(Qt.PartiallyChecked)
        self.chk_select_all.blockSignals(False)

    def on_select_all(self, state):
        self.list_widget.blockSignals(True)
        self.list_widget.set_all_checked(state == Qt.Checked)
        self.list_widget.blockSignals(False)
        self._update_checked_label()

    def _update_checked_label(self):
        n = self.list_widget.get_checked_count()
        self.lbl_checked_count.setText(t("list.checked", count=n))
        self.btn_merge.setText(
            t("btn.merge_n", count=n) if n >= 2
            else t("btn.merge")
        )

    # ---------- 顺序变更 ----------

    def on_order_changed(self):
        order = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            path = item.data(Qt.UserRole)
            if path:
                order.append(path)
        save_order(None, order)

    # ---------- 移除选中（不删除原始文件） ----------

    def on_remove_selected(self):
        checked = self.list_widget.get_checked()
        if not checked:
            QMessageBox.information(self, t("dialog.tip"), t("msg.need_check_remove"))
            return
        reply = QMessageBox.question(
            self, t("msg.remove_confirm_title"),
            t("msg.remove_confirm_body", count=len(checked)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for idx in sorted(checked, reverse=True):
                item = self.list_widget.item(idx)
                path = item.data(Qt.UserRole)
                if path:
                    delete_file(path)
            self.refresh_file_list()

    # ---------- 预览 ----------

    def on_preview(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.information(self, t("dialog.tip"), t("msg.need_select_preview"))
            return
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            os.startfile(path)

    # ---------- 右键菜单 ----------

    def on_context_menu(self, pos):
        item = self.list_widget.currentItem()
        if not item:
            return
        menu = QMenu(self)
        act_preview = menu.addAction(t("msg.context_preview"))
        act_preview.triggered.connect(self.on_preview)
        act_split_this = menu.addAction(t("msg.context_split"))
        act_split_this.triggered.connect(
            lambda: self._split_single(item.data(Qt.UserRole))
        )
        menu.exec_(self.list_widget.viewport().mapToGlobal(pos))

    # ---------- 历史记录 ----------

    def on_show_history(self):
        dlg = HistoryDialog(self)
        dlg.exec_()

    # ---------- 主题切换 ----------


    def retranslate_ui(self):
        """
        按当前语言刷新主界面全部可见文案（不重建控件、不改业务状态）。
        弹窗在打开时按当前语言创建，无需此处处理。
        """
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.chk_select_all.setText(t("list.select_all"))
        self.btn_import.setText(t("btn.import"))
        self.btn_remove.setText(t("btn.remove"))
        self.btn_preview.setText(t("btn.preview"))
        self._lbl_font_size.setText(t("label.font"))
        self._lbl_theme.setText(t("label.theme"))
        self._lbl_language.setText(t("label.language"))
        self.btn_history.setText(t("btn.history"))
        self.btn_history.setToolTip(t("btn.history.tip"))

        # 下拉：保留当前 data，只改显示文字
        font_map = {
            UI_FONT_SIZE_DEFAULT: "font.default",
            UI_FONT_SIZE_LARGE: "font.large",
            UI_FONT_SIZE_XLARGE: "font.xlarge",
        }
        for index in range(self.cmb_font_size.count()):
            key = self.cmb_font_size.itemData(index)
            self.cmb_font_size.setItemText(index, t(font_map.get(key, "font.default")))
        for index in range(self.cmb_theme.count()):
            key = self.cmb_theme.itemData(index)
            self.cmb_theme.setItemText(
                index, t("theme.dark" if key == "dark" else "theme.light")
            )
        for index in range(self.cmb_language.count()):
            key = self.cmb_language.itemData(index)
            self.cmb_language.setItemText(
                index, t("lang.en" if key == "en" else "lang.zh")
            )

        self.grp_merge.setTitle(t("group.merge"))
        self.grp_convert.setTitle(t("group.convert"))
        self.grp_organize.setTitle(t("group.organize"))
        self.grp_security.setTitle(t("group.security"))
        self.grp_create.setTitle(t("group.create"))
        self._update_checked_label()
        self.chk_copy_original.setText(t("btn.copy_original"))
        self.btn_split.setText(t("btn.split"))
        self.btn_to_images.setText(t("btn.to_images"))
        self.btn_to_word.setText(t("btn.to_word"))
        self.btn_compress.setText(t("btn.compress"))
        self.btn_pages.setText(t("btn.pages"))
        self.btn_stamp.setText(t("btn.stamp"))
        self.btn_encrypt.setText(t("btn.encrypt"))
        self.btn_decrypt.setText(t("btn.decrypt"))
        self.btn_images_to_pdf.setText(t("btn.images_to_pdf"))
        self.btn_cancel.setText(t("main.cancel"))
        self._lbl_save_path.setText(t("path.label"))
        self.input_save_path.setPlaceholderText(t("path.placeholder"))
        self.btn_browse_path.setText(t("dialog.browse"))
        self.chk_remember_path.setText(t("path.remember"))
        self._lbl_version.setToolTip(
            t("main.version_tip", app=APP_NAME, version=APP_VERSION)
        )
        accent = "#89B4FA" if self._is_dark else "#2C6FBB"
        self._lbl_credit.setText(t("main.credit", color=accent, author=APP_AUTHOR))
        if not self.progress_bar.isVisible():
            self.statusBar().showMessage(t("main.ready"))
        self.desc_panel.clear_desc()
        self.steps_panel.clear_steps()
        self.list_widget._drop_label.setText(t("list.drop_here"))
        # 刷新列表页数后缀
        self.refresh_file_list()

    def on_theme_changed(self, index):
        """主题下拉框切换（按 itemData，避免语言切换后索引语义错乱）。"""
        theme = self.cmb_theme.itemData(index) or "light"
        self._apply_theme(theme)

    def on_language_changed(self, index):
        """界面语言切换：立即重译主窗并写入偏好。"""
        language_code = self.cmb_language.itemData(index) or "zh"
        set_language(language_code)
        pref_set("ui_language", language_code)
        self.retranslate_ui()
        self._setup_hover_info()
        self._on_btn_leave()
        # 偏好行宽度随英文变长，重新 fit
        theme = "dark" if self._is_dark else "light"
        self._apply_preference_chrome(theme)
        self._apply_theme_accents(theme)
        self._validate_path_input()
        QTimer.singleShot(0, self._fit_bottom_help_panels)

    def on_font_size_changed(self, index):
        """字体大小档位切换：写入记忆并立刻刷新全界面。"""
        preset = self.cmb_font_size.itemData(index) or UI_FONT_SIZE_DEFAULT
        ui_scale.set_font_size_preset(preset)
        pref_set("ui_font_size", preset)
        self._scale_applied_once = False
        self.apply_ui_scale()
        self.list_widget.apply_ui_scale()

    def _apply_theme(self, theme: str):
        """应用浅色/深色主题（含当前缩放因子）。"""
        is_dark = (theme == "dark")
        self._is_dark = is_dark

        app = QApplication.instance()
        # 先套应用级调色板，阻断 Windows 系统深色把下拉画成黑底
        app.setPalette(build_app_palette(is_dark))
        if is_dark:
            app.setStyleSheet(build_dark_qss())
        else:
            app.setStyleSheet(build_light_qss())

        # 更新列表 delegate 深色模式
        self.list_widget.set_delegate_dark_mode(is_dark)

        # 更新底部面板暗色模式
        self.desc_panel.set_dark_mode(is_dark)
        self.steps_panel.set_dark_mode(is_dark)

        # 主题强调色、右侧壳体铺底、偏好下拉必须同步重套
        self._apply_theme_accents(theme)
        self._apply_preference_chrome(theme)
        self.desc_panel.apply_ui_scale()
        self.steps_panel.apply_ui_scale()

        # 刷新路径校验样式
        self._validate_path_input()

        # 持久化主题偏好
        pref_set("theme", theme)
        QTimer.singleShot(0, self._fit_bottom_help_panels)

    # ---------- 重名解析 ----------

    def _resolve_unique_output(self, directory, base_name, ext,
                                also_copy_pdf=False):
        """避免重名：返回 (最终基础名, 最终输出路径)"""
        candidate_name = base_name
        candidate_path = os.path.join(directory, f"{candidate_name}{ext}")
        pdf_copy_path = os.path.join(directory, f"{candidate_name}.pdf") if also_copy_pdf else None

        if (not os.path.exists(candidate_path) and
                (pdf_copy_path is None or not os.path.exists(pdf_copy_path))):
            return candidate_name, candidate_path

        i = 1
        while True:
            candidate_name = f"{base_name}_{i}"
            candidate_path = os.path.join(directory, f"{candidate_name}{ext}")
            pdf_copy_path = os.path.join(directory, f"{candidate_name}.pdf") if also_copy_pdf else None
            if (not os.path.exists(candidate_path) and
                    (pdf_copy_path is None or not os.path.exists(pdf_copy_path))):
                return candidate_name, candidate_path
            i += 1

    # ---------- 合并（仅合并勾选的） ----------

    def on_merge(self):
        if not self._ensure_valid_save_path():
            return
        checked = self.list_widget.get_checked_paths()
        if len(checked) < 2:
            QMessageBox.warning(
                self, t("dialog.tip"), t("msg.need_merge")
            )
            return

        save_dir = self._get_effective_save_dir()
        output = choose_save_path(self, t("file.merge_default"), default_dir=save_dir)
        if not output:
            return

        # 按列表顺序收集
        ordered = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                ordered.append(item.data(Qt.UserRole))

        passwords = self._ask_passwords_for_paths(ordered)
        if passwords is None:
            return

        self._run_task(
            merge_pdfs,
            (ordered, output),
            t("task.merge"),
            t("task.merge_done"),
            op_type="合并",
            source_paths=ordered,
            output_path=output,
            extra_kwargs={"passwords": passwords},
        )

    # ---------- 拆分 ----------

    def on_split(self):
        if not self._ensure_valid_save_path():
            return
        items = self.list_widget.selectedItems()
        if not items:
            item = self.list_widget.currentItem()
            if item:
                items = [item]
        if not items:
            QMessageBox.information(self, t("dialog.tip"), t("msg.need_select_pdf"))
            return
        # 先收集全部拆分任务，再串行执行，避免多选时互相覆盖 Worker
        jobs = []
        for item in items:
            job = self._prepare_split_job(item.data(Qt.UserRole))
            if job is not None:
                jobs.append(job)
        if not jobs:
            return
        if len(jobs) == 1:
            self._run_task(**jobs[0])
        else:
            self._run_task_batch(jobs)

    def _prepare_split_job(self, pdf_path):
        """弹出拆分设置并组装一个后台任务描述；用户取消则返回 None。"""
        if not pdf_path:
            return None
        password = self._ask_password_if_needed(pdf_path)
        if password is None:
            return None
        try:
            total = get_pdf_page_count_secure(pdf_path, password)
        except Exception:
            total = 0
        if total == 0:
            QMessageBox.warning(self, t("dialog.error"), t("msg.bad_pdf_pwd"))
            return None

        dlg = SplitDialog(pdf_path, total, self)
        if dlg.exec_() != QDialog.Accepted:
            return None
        mode, val = dlg.get_result()

        save_dir = self._get_effective_save_dir()
        output_dir = QFileDialog.getExistingDirectory(
            self, t("file.split_dir"), save_dir
        )
        if not output_dir:
            return None

        keep_orig = self.chk_copy_original.isChecked()

        if mode == "pages":
            task_fn = split_pdf_by_pages
            args = (pdf_path, output_dir, val)
        elif mode == "copies":
            task_fn = split_pdf_by_copies
            args = (pdf_path, output_dir, val)
        else:
            task_fn = split_pdf_by_ranges
            args = (pdf_path, output_dir, val)

        # 用默认参数绑住当前文件，避免闭包在循环里串味
        def split_with_copy(
            *a,
            _task_fn=task_fn,
            _output_dir=output_dir,
            _pdf_path=pdf_path,
            _keep_orig=keep_orig,
            **kw
        ):
            results = _task_fn(*a, **kw)
            if _keep_orig and results:
                dest = os.path.join(_output_dir, os.path.basename(_pdf_path))
                if os.path.normpath(dest) != os.path.normpath(_pdf_path):
                    shutil.copy2(_pdf_path, dest)
            return results

        return {
            "task_fn": split_with_copy,
            "args": args,
            "in_progress_msg": t("task.split"),
            "success_msg": t("task.split_done"),
            "op_type": "拆分",
            "source_paths": [pdf_path],
            "output_path": output_dir,
            "extra_kwargs": {"password": password},
            "display_name": os.path.basename(pdf_path),
        }

    # ---------- 转图片 ----------

    def on_to_images(self):
        if not self._ensure_valid_save_path():
            return
        items = self.list_widget.selectedItems()
        if not items:
            item = self.list_widget.currentItem()
            if item:
                items = [item]
        if not items:
            QMessageBox.information(self, t("dialog.tip"), t("msg.need_select_pdf"))
            return

        dlg = ImageExportDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return
        fmt, dpi = dlg.get_result()

        copy_orig = self.chk_copy_original.isChecked()
        jobs = []
        for item in items:
            job = self._prepare_images_job(
                item.data(Qt.UserRole), fmt, dpi, copy_orig
            )
            if job is not None:
                jobs.append(job)
        if not jobs:
            return
        if len(jobs) == 1:
            self._run_task(**jobs[0])
        else:
            self._run_task_batch(jobs)

    def _prepare_images_job(self, pdf_path, fmt, dpi, copy_orig):
        """为单个 PDF 收集转图片任务；取消密码或目录选择则返回 None。"""
        if not pdf_path:
            return None
        password = self._ask_password_if_needed(pdf_path)
        if password is None:
            return None
        save_dir = self._get_effective_save_dir()
        output_dir = QFileDialog.getExistingDirectory(
            self, t("file.images_dir"), save_dir
        )
        if not output_dir:
            return None
        return {
            "task_fn": pdf_to_images,
            "args": (pdf_path, output_dir, dpi, fmt),
            "in_progress_msg": t("task.to_images"),
            "success_msg": t("task.to_images_done"),
            "op_type": "转图片",
            "source_paths": [pdf_path],
            "output_path": output_dir,
            "extra_kwargs": {
                "copy_original_pdf": copy_orig,
                "password": password,
            },
            "display_name": os.path.basename(pdf_path),
        }

    # ---------- 转 Word ----------

    def on_to_word(self):
        if not self._ensure_valid_save_path():
            return
        items = self.list_widget.selectedItems()
        if not items:
            item = self.list_widget.currentItem()
            if item:
                items = [item]
        if not items:
            QMessageBox.information(self, t("dialog.tip"), t("msg.need_select_pdf"))
            return

        copy_orig = self.chk_copy_original.isChecked()

        # 一次只处理一个文件（避免多个 worker 互相覆盖）
        item = items[0]
        path = item.data(Qt.UserRole)
        if not path:
            return
        password = self._ask_password_if_needed(path)
        if password is None:
            return
        base_name = os.path.splitext(os.path.basename(path))[0]
        save_dir = self._get_effective_save_dir()

        # 处理重名
        final_base, output = self._resolve_unique_output(
            save_dir, base_name, ".docx", also_copy_pdf=copy_orig
        )

        def convert_word(*a, **kw):
            result = pdf_to_word(*a, copy_original_pdf=copy_orig, **kw)
            return result

        self._run_task(
            convert_word,
            (path, output),
            t("task.to_word"),
            t("task.to_word_done"),
            op_type="转Word",
            source_paths=[path],
            output_path=output,
            extra_kwargs={"password": password},
        )

    # ---------- V3：选中文件 / 密码辅助 ----------

    def _get_one_selected_pdf(self):
        """
        取当前操作目标 PDF：优先列表选中项，否则用当前高亮项。
        未选中时弹提示并返回空字符串。
        """
        items = self.list_widget.selectedItems()
        if not items:
            current_item = self.list_widget.currentItem()
            if current_item:
                items = [current_item]
        if not items:
            QMessageBox.information(self, t("dialog.tip"), t("msg.need_select_pdf"))
            return ""
        pdf_path = items[0].data(Qt.UserRole)
        return pdf_path or ""

    def _ask_password_if_needed(self, pdf_path: str):
        """
        若 PDF 需要密码则弹出输入框。

        :return: 成功返回密码字符串（可为 ""）；用户取消或无法打开返回 None
        """
        can_open, needs_password = probe_encryption(pdf_path)
        if not can_open:
            QMessageBox.warning(self, t("dialog.error"), t("msg.bad_pdf"))
            return None
        if not needs_password:
            return ""
        dialog = PasswordDialog(
            self, title=t("pwd.title_named", name=os.path.basename(pdf_path))
        )
        if dialog.exec_() != QDialog.Accepted:
            return None
        return dialog.password()

    def _ask_passwords_for_paths(self, pdf_paths):
        """
        为多个 PDF 收集打开密码（仅对需要密码的文件弹窗）。

        :return: {路径: 密码}；用户取消或某文件无法打开时返回 None
        """
        passwords = {}
        for pdf_path in pdf_paths:
            can_open, needs_password = probe_encryption(pdf_path)
            if not can_open:
                QMessageBox.warning(
                    self, t("dialog.error"),
                    t("msg.cannot_open_named", name=os.path.basename(pdf_path))
                )
                return None
            if not needs_password:
                passwords[pdf_path] = ""
                continue
            dialog = PasswordDialog(
                self, title=t("pwd.title_named", name=os.path.basename(pdf_path))
            )
            if dialog.exec_() != QDialog.Accepted:
                return None
            passwords[pdf_path] = dialog.password()
        return passwords

    # ---------- V3：压缩 ----------

    def on_compress(self):
        """压缩选中 PDF：选档位 → 密码（如需）→ 另存。"""
        if not self._ensure_valid_save_path():
            return
        pdf_path = self._get_one_selected_pdf()
        if not pdf_path:
            return
        original_bytes = os.path.getsize(pdf_path) if os.path.isfile(pdf_path) else 0
        dialog = CompressDialog(self, original_bytes=original_bytes)
        if dialog.exec_() != QDialog.Accepted:
            return
        compress_options = dialog.get_options()
        password = self._ask_password_if_needed(pdf_path)
        if password is None:
            return
        base_name = os.path.splitext(os.path.basename(pdf_path))[0] + t("file.suffix_compress")
        save_dir = self._get_effective_save_dir()
        chosen = choose_save_path(
            self, f"{base_name}.pdf", default_dir=save_dir
        )
        if not chosen:
            return
        self._run_task(
            compress_pdf,
            (pdf_path, chosen, compress_options["level"]),
            t("task.compress"),
            t("task.compress_done"),
            op_type="压缩",
            source_paths=[pdf_path],
            output_path=chosen,
            extra_kwargs={
                "password": password,
                "target_bytes": compress_options["target_bytes"],
                "allow_rasterize": compress_options["allow_rasterize"],
            },
        )

    # ---------- V3：页面管理 ----------

    def on_page_manager(self):
        """打开缩略图页面管理，确认后另存编辑结果。"""
        if not self._ensure_valid_save_path():
            return
        pdf_path = self._get_one_selected_pdf()
        if not pdf_path:
            return
        password = self._ask_password_if_needed(pdf_path)
        if password is None:
            return
        try:
            dialog = PageManagerDialog(pdf_path, password, self)
        except Exception as exc:
            QMessageBox.warning(
                self, t("dialog.error"), t("msg.pages_open_fail", error=exc)
            )
            return
        if dialog.exec_() != QDialog.Accepted:
            return
        keep_order, rotations = dialog.get_result()
        if not keep_order:
            QMessageBox.warning(self, t("dialog.tip"), t("msg.pages_empty"))
            return
        base_name = os.path.splitext(os.path.basename(pdf_path))[0] + t("file.suffix_pages")
        save_dir = self._get_effective_save_dir()
        chosen = choose_save_path(
            self, f"{base_name}.pdf", default_dir=save_dir
        )
        if not chosen:
            return
        self._run_task(
            apply_page_edits,
            (pdf_path, chosen, keep_order),
            t("task.pages"),
            t("task.pages_done"),
            op_type="页面管理",
            source_paths=[pdf_path],
            output_path=chosen,
            extra_kwargs={"rotations": rotations, "password": password},
        )

    # ---------- V3：水印与页码 ----------

    def on_stamp(self):
        """叠加文字/图片水印与页码后另存。"""
        if not self._ensure_valid_save_path():
            return
        pdf_path = self._get_one_selected_pdf()
        if not pdf_path:
            return
        password = self._ask_password_if_needed(pdf_path)
        if password is None:
            return
        dialog = StampDialog(self, pdf_path=pdf_path, password=password)
        if dialog.exec_() != QDialog.Accepted:
            return
        options = dialog.get_result()
        base_name = os.path.splitext(os.path.basename(pdf_path))[0] + t("file.suffix_stamp_short")
        save_dir = self._get_effective_save_dir()
        chosen = choose_save_path(
            self, f"{base_name}.pdf", default_dir=save_dir
        )
        if not chosen:
            return
        self._run_task(
            stamp_pdf,
            (pdf_path, chosen),
            t("task.stamp"),
            t("task.stamp_done"),
            op_type="水印页码",
            source_paths=[pdf_path],
            output_path=chosen,
            extra_kwargs={"password": password, **options},
        )

    # ---------- V3：加密 / 解密 ----------

    def on_encrypt(self):
        """将选中 PDF 另存为 AES-256 加密文件。"""
        if not self._ensure_valid_save_path():
            return
        pdf_path = self._get_one_selected_pdf()
        if not pdf_path:
            return
        # 先问源文件打开密码，再设置输出新密码，避免白填
        open_password = self._ask_password_if_needed(pdf_path)
        if open_password is None:
            return
        options_dialog = EncryptOptionsDialog(self)
        if options_dialog.exec_() != QDialog.Accepted:
            return
        encrypt_options = options_dialog.get_result()
        base_name = os.path.splitext(os.path.basename(pdf_path))[0] + t("file.suffix_encrypt")
        save_dir = self._get_effective_save_dir()
        chosen = choose_save_path(
            self, f"{base_name}.pdf", default_dir=save_dir
        )
        if not chosen:
            return
        self._run_task(
            encrypt_pdf,
            (pdf_path, chosen, encrypt_options["user_password"]),
            t("task.encrypt"),
            t("task.encrypt_done"),
            op_type="加密",
            source_paths=[pdf_path],
            output_path=chosen,
            extra_kwargs={
                "password": open_password,
                "allow_print": encrypt_options["allow_print"],
                "allow_copy": encrypt_options["allow_copy"],
            },
        )

    def on_decrypt(self):
        """验证密码后另存为无加密 PDF。"""
        if not self._ensure_valid_save_path():
            return
        pdf_path = self._get_one_selected_pdf()
        if not pdf_path:
            return
        can_open, needs_password = probe_encryption(pdf_path)
        if not can_open:
            QMessageBox.warning(self, t("dialog.error"), t("msg.cannot_open"))
            return
        if not needs_password:
            QMessageBox.information(self, t("dialog.tip"), t("msg.not_encrypted"))
            return
        dialog = PasswordDialog(self, title=t("pwd.unlock_title"))
        if dialog.exec_() != QDialog.Accepted:
            return
        password = dialog.password()
        base_name = os.path.splitext(os.path.basename(pdf_path))[0] + t("file.suffix_decrypt")
        save_dir = self._get_effective_save_dir()
        chosen = choose_save_path(
            self, f"{base_name}.pdf", default_dir=save_dir
        )
        if not chosen:
            return
        self._run_task(
            decrypt_pdf,
            (pdf_path, chosen, password),
            t("task.decrypt"),
            t("task.decrypt_done"),
            op_type="解密",
            source_paths=[pdf_path],
            output_path=chosen,
        )

    # ---------- V3：图片转 PDF ----------

    def on_images_to_pdf(self):
        """多选图片 → 排序/纸张模式 → 生成 PDF。"""
        if not self._ensure_valid_save_path():
            return
        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            t("file.pick_images"),
            self._get_effective_save_dir(),
            t("file.filter_images"),
        )
        if not image_paths:
            return
        dialog = ImagesToPdfDialog(image_paths, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        ordered_paths, page_mode = dialog.get_result()
        if not ordered_paths:
            return
        save_dir = self._get_effective_save_dir()
        chosen = choose_save_path(
            self, t("file.images_default"), default_dir=save_dir
        )
        if not chosen:
            return
        self._run_task(
            images_to_pdf,
            (ordered_paths, chosen),
            t("task.img2pdf"),
            t("task.img2pdf_done"),
            op_type="图片转PDF",
            source_paths=ordered_paths,
            output_path=chosen,
            extra_kwargs={"page_mode": page_mode},
        )

    # ---------- 取消 ----------

    def on_cancel(self):
        # 取消当前任务并清空排队中的后续任务
        self.cancel_requested = True
        self._task_queue.clear()
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.btn_cancel.setEnabled(False)
            self.statusBar().showMessage(t("status.cancelling"))

    # ---------- 后台任务封装（支持串行队列） ----------

    def _make_task_job(
        self, task_fn, args, in_progress_msg, success_msg,
        op_type="", source_paths=None, output_path="",
        extra_kwargs=None, display_name="",
    ):
        """组装一份可入队的任务描述。"""
        return {
            "task_fn": task_fn,
            "args": args or (),
            "in_progress_msg": in_progress_msg,
            "success_msg": success_msg,
            "op_type": op_type or "",
            "source_paths": source_paths,
            "output_path": output_path or "",
            "extra_kwargs": extra_kwargs,
            "display_name": display_name or "",
        }

    def _run_task(self, task_fn, args, in_progress_msg, success_msg,
                  op_type="", source_paths=None, output_path="",
                  extra_kwargs=None, display_name=""):
        """
        启动后台任务。若已有任务在跑则入队，绝不覆盖 Worker。
        单任务路径与旧版一致；多选批量请用 _run_task_batch。
        """
        job = self._make_task_job(
            task_fn, args, in_progress_msg, success_msg,
            op_type, source_paths, output_path, extra_kwargs, display_name,
        )
        if self.worker and self.worker.isRunning():
            self._task_queue.append(job)
            if not self._batch_active:
                self._batch_active = True
                self._batch_total = 1 + len(self._task_queue)
                self._batch_index = 1
                self._batch_results = []
            else:
                self._batch_total += 1
            self.statusBar().showMessage(
                t(
                    "task.batch_queued",
                    queued=len(self._task_queue),
                    total=self._batch_total,
                )
            )
            return
        self._batch_active = False
        self._batch_total = 0
        self._batch_index = 0
        self._batch_results = []
        self._start_worker(job)

    def _run_task_batch(self, jobs):
        """多任务串行：先入队再泵出第一个。"""
        if not jobs:
            return
        self._task_queue = list(jobs)
        self._batch_active = True
        self._batch_total = len(jobs)
        self._batch_index = 0
        self._batch_results = []
        self.cancel_requested = False
        self._pump_task_queue()

    def _pump_task_queue(self):
        """取出队列头并启动；空队列则结束批次。"""
        if self.cancel_requested:
            self._task_queue.clear()
            return
        if not self._task_queue:
            return
        if self.worker and self.worker.isRunning():
            return
        job = self._task_queue.pop(0)
        self._batch_index += 1
        self._start_worker(job)

    def _start_worker(self, job):
        """真正创建并启动 WorkerThread。"""
        self._set_ui_enabled(False)
        self.cancel_requested = False
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.btn_cancel.setVisible(True)
        self.btn_cancel.setEnabled(True)

        in_progress_msg = job["in_progress_msg"]
        if self._batch_active and self._batch_total > 1:
            in_progress_msg = t(
                "task.batch_progress",
                current=self._batch_index,
                total=self._batch_total,
                msg=job["in_progress_msg"],
            )
        self.statusBar().showMessage(in_progress_msg)

        kwargs = {}
        if job.get("extra_kwargs"):
            kwargs.update(job["extra_kwargs"])

        success_msg = job["success_msg"]
        op_type = job.get("op_type") or ""
        source_paths = job.get("source_paths")
        output_path = job.get("output_path") or ""
        display_name = job.get("display_name") or ""

        self.worker = WorkerThread(job["task_fn"], *job["args"], **kwargs)
        self.worker.progress.connect(self._on_progress)
        # 默认参数绑定，避免 lambda 晚绑定串到下一任务
        self.worker.finished.connect(
            lambda result, msg=success_msg, ot=op_type, sp=source_paths,
                   op=output_path, dn=display_name: self._on_task_done(
                result, msg, ot, sp, op, dn
            )
        )
        self.worker.error.connect(
            lambda err, msg=success_msg, ot=op_type, sp=source_paths,
                   op=output_path, dn=display_name: self._on_task_error(
                err, msg, ot, sp, op, dn
            )
        )
        self.worker.start()

    def _on_progress(self, value):
        self.progress_bar.setValue(value)

    def _cleanup_cancelled_outputs(self, output_path, partial_result):
        """
        取消后清理半成品：
        1. 若任务返回了文件路径列表，逐个删除（拆分/转图等）
        2. 再尝试删除合并/转 Word 的单一输出文件
        3. 若输出是空目录则移除目录
        """
        if isinstance(partial_result, dict):
            # 转图片等任务改为返回 dict 后，半成品路径在 files 字段
            partial_result = partial_result.get("files") or []
        if isinstance(partial_result, list):
            for file_path in partial_result:
                try:
                    if file_path and os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
        if output_path and os.path.exists(output_path):
            try:
                if os.path.isfile(output_path):
                    os.remove(output_path)
                elif os.path.isdir(output_path) and not os.listdir(output_path):
                    os.rmdir(output_path)
            except Exception:
                pass

    def _result_succeeded(self, result) -> bool:
        """判断任务返回值是否表示成功。"""
        if result is None:
            return False
        if isinstance(result, bool):
            return bool(result)
        if isinstance(result, list):
            return True
        if isinstance(result, dict):
            return bool(result.get("success", False))
        return True

    def _result_detail(self, result) -> str:
        """取出失败/警告说明文字。"""
        if isinstance(result, dict):
            return str(result.get("warning") or result.get("message") or "")
        return ""

    def _record_batch_result(self, display_name, result, error_text=""):
        """把本条任务结果记入批次汇总。"""
        name = display_name or t("task.batch_unnamed")
        if error_text:
            self._batch_results.append(
                {"name": name, "ok": False, "detail": error_text}
            )
            return
        ok = self._result_succeeded(result)
        detail = self._result_detail(result)
        self._batch_results.append({"name": name, "ok": ok, "detail": detail})

    def _show_batch_summary(self):
        """多任务全部结束后弹出汇总。"""
        ok_count = sum(1 for item in self._batch_results if item.get("ok"))
        fail_count = len(self._batch_results) - ok_count
        lines = [
            t(
                "task.batch_summary",
                total=len(self._batch_results),
                ok=ok_count,
                fail=fail_count,
            )
        ]
        for item in self._batch_results:
            mark = t("task.batch_ok") if item.get("ok") else t("task.batch_fail")
            line = f"{mark} {item.get('name') or ''}"
            detail = (item.get("detail") or "").strip()
            if detail and not item.get("ok"):
                line += f" — {detail}"
            elif detail and item.get("ok"):
                line += f" （{detail}）"
            lines.append(line)
        text = "\n".join(lines)
        if fail_count:
            QMessageBox.warning(self, t("msg.convert_warn_title"), text)
        else:
            QMessageBox.information(self, t("dialog.done"), text)

    def _finish_ui_after_task(self):
        """单任务或批次全部结束后恢复界面。"""
        self.progress_bar.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._set_ui_enabled(True)

    def _on_task_done(self, result, msg, op_type, source_paths, output_path,
                      display_name=""):
        if self.cancel_requested or result is None:
            self._task_queue.clear()
            self._batch_active = False
            self._batch_total = 0
            self._finish_ui_after_task()
            self.statusBar().showMessage(t("main.task_cancelled_status"))
            partial_result = getattr(self.worker, "partial_result", None) if self.worker else None
            self._cleanup_cancelled_outputs(output_path, partial_result)
            QMessageBox.information(self, t("dialog.tip"), t("msg.task_cancelled"))
            return

        if op_type and source_paths and output_path and self._result_succeeded(result):
            try:
                history_manager.add_record(op_type, source_paths, output_path)
            except Exception:
                pass

        in_batch = self._batch_active and self._batch_total > 1
        if in_batch:
            self._record_batch_result(display_name, result)
            self.refresh_file_list()
            if self._task_queue and not self.cancel_requested:
                self.progress_bar.setValue(0)
                self._pump_task_queue()
                return
            self._finish_ui_after_task()
            self.statusBar().showMessage(msg)
            self._show_batch_summary()
            self._batch_active = False
            self._batch_total = 0
            self._batch_results = []
            return

        self._finish_ui_after_task()
        self.statusBar().showMessage(msg)
        self.refresh_file_list()

        if isinstance(result, list):
            QMessageBox.information(
                self, t("dialog.done"),
                t("msg.done_files", msg=msg, count=len(result)),
            )
        elif isinstance(result, dict):
            success = result.get("success", False)
            # 兼容转 Word 的 warning 与压缩等模块的 message
            detail = result.get("warning") or result.get("message") or ""
            file_list = result.get("files")
            if success:
                if isinstance(file_list, list) and file_list:
                    text = t("msg.done_files", msg=msg, count=len(file_list))
                    if detail:
                        text = f"{text}\n\n{detail}"
                else:
                    text = f"{msg}\n\n{detail}" if detail else msg
                if result.get("warning"):
                    QMessageBox.warning(self, t("msg.convert_warn_title"), text)
                else:
                    QMessageBox.information(self, t("dialog.done"), text)
            else:
                QMessageBox.warning(
                    self, t("msg.op_failed"), detail or t("msg.op_failed_retry")
                )
        elif isinstance(result, bool):
            QMessageBox.information(
                self, t("dialog.done") if result else t("dialog.failed"),
                msg if result else t("msg.op_failed_console"),
            )

    def _on_task_error(self, err_msg, success_msg="", op_type="", source_paths=None,
                       output_path="", display_name=""):
        in_batch = self._batch_active and self._batch_total > 1
        if in_batch:
            self._record_batch_result(display_name, None, error_text=str(err_msg))
            if self._task_queue and not self.cancel_requested:
                self.progress_bar.setValue(0)
                self._pump_task_queue()
                return
            self._finish_ui_after_task()
            self.statusBar().showMessage(t("status.error"))
            self._show_batch_summary()
            self._batch_active = False
            self._batch_total = 0
            self._batch_results = []
            return

        self._finish_ui_after_task()
        self.statusBar().showMessage(t("status.error"))
        QMessageBox.critical(
            self, t("dialog.error"), t("msg.op_failed_detail", msg=err_msg)
        )

    def _set_ui_enabled(self, enabled):
        for w in [
            self.btn_merge, self.btn_import, self.btn_remove,
            self.btn_preview, self.btn_split, self.btn_to_images,
            self.btn_to_word, self.btn_compress, self.btn_pages,
            self.btn_stamp, self.btn_encrypt, self.btn_decrypt,
            self.btn_images_to_pdf, self.list_widget, self.chk_select_all,
            self.input_save_path, self.btn_browse_path
        ]:
            w.setEnabled(enabled)
