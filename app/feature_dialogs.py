# -*- coding: utf-8 -*-
"""
V3 新功能相关对话框：密码、压缩、水印页码、图片转PDF、页面管理。
"""
from __future__ import annotations

import os
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QIcon, QPixmap, QImage, QColor, QPainter, QBrush,
)
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QRadioButton, QButtonGroup, QCheckBox, QComboBox,
    QSpinBox, QDoubleSpinBox, QFileDialog, QListWidget, QListWidgetItem,
    QAbstractItemView, QMessageBox, QProgressDialog, QApplication,
    QColorDialog, QFrame, QScrollArea, QWidget, QGroupBox, QFormLayout,
    QSizePolicy,
)

from app import ui_scale
from app.i18n import t, apply_dialog_button_box
from app import layout_fit
from app.responsive_dialog import ResponsiveDialog
from app.preferences import get as pref_get, set as pref_set
from app.pdf_pages import get_page_count, render_page_thumbnail, render_page_preview
from app.pdf_compress import format_file_size
from app.pdf_stamp import (
    mm_to_pt, px_to_pt, pt_to_mm, pt_to_px,
    get_first_page_size_pt, render_page_number_preview_png,
    render_stamp_preview_png,
    page_number_box_mins_pt, effective_page_number_font_size,
)

# 文字水印快捷色：名称 → RGB(0~1)，覆盖合同/标书常见需求
_WATERMARK_PRESET_COLORS = [
    ("stamp.color_red", (0.85, 0.12, 0.12)),
    ("stamp.color_blue", (0.15, 0.35, 0.85)),
    ("stamp.color_black", (0.08, 0.08, 0.08)),
    ("stamp.color_gray", (0.35, 0.35, 0.35)),
    ("stamp.color_orange", (0.90, 0.45, 0.05)),
]
# 默认水印色：醒目红，避免旧版浅灰几乎看不见
_DEFAULT_WATERMARK_COLOR = (0.85, 0.12, 0.12)
_DEFAULT_WATERMARK_OPACITY = 0.45
# 页码默认距页边 10 毫米（约等于旧版写死的 28pt）
_DEFAULT_PAGE_MARGIN_MM = 10.0
# 页码框宽绝对下限（毫米）：禁止再设到 8mm 那种几乎装不下中文的宽度
_PAGE_BOX_WIDTH_ABS_MIN_MM = 15.0


def _load_saved_page_margin_mm() -> float:
    """从偏好读取上次页码边距（毫米），夹在 2～40。"""
    saved = pref_get("stamp_page_margin_mm", _DEFAULT_PAGE_MARGIN_MM)
    try:
        value = float(saved)
    except (TypeError, ValueError):
        return _DEFAULT_PAGE_MARGIN_MM
    return max(2.0, min(40.0, value))


def _rgb_tuple_to_qcolor(rgb_tuple) -> QColor:
    """把 (r,g,b) 0~1 转为 QColor，供色块与取色器使用。"""
    red = int(max(0.0, min(1.0, float(rgb_tuple[0]))) * 255)
    green = int(max(0.0, min(1.0, float(rgb_tuple[1]))) * 255)
    blue = int(max(0.0, min(1.0, float(rgb_tuple[2]))) * 255)
    return QColor(red, green, blue)


def _qcolor_to_rgb_tuple(color: QColor):
    """把 QColor 转为 PyMuPDF 用的 (r,g,b) 0~1。"""
    return (color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0)


def _load_saved_watermark_color():
    """从偏好读取上次水印色；无效则回落默认红。"""
    saved = pref_get("stamp_text_color", None)
    if isinstance(saved, (list, tuple)) and len(saved) == 3:
        try:
            return (
                float(saved[0]),
                float(saved[1]),
                float(saved[2]),
            )
        except (TypeError, ValueError):
            pass
    if isinstance(saved, str) and saved.startswith("#") and len(saved) == 7:
        color = QColor(saved)
        if color.isValid():
            return _qcolor_to_rgb_tuple(color)
    return _DEFAULT_WATERMARK_COLOR


def _load_saved_watermark_opacity() -> float:
    """从偏好读取上次透明度，夹在合法范围内。"""
    saved = pref_get("stamp_text_opacity", _DEFAULT_WATERMARK_OPACITY)
    try:
        value = float(saved)
    except (TypeError, ValueError):
        return _DEFAULT_WATERMARK_OPACITY
    return max(0.05, min(1.0, value))


class PasswordDialog(ResponsiveDialog):
    """输入 PDF 打开密码；紧凑窗，全文可见。"""

    DESIGN_WIDTH = 380
    DESIGN_HEIGHT = 160
    DIALOG_KIND = "compact"

    def __init__(self, parent=None, title: str = None):
        super().__init__(parent)
        self.setWindowTitle(title if title else t("pwd.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(ui_scale.px(360))
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=True, margin=True)
        layout.addWidget(QLabel(t("pwd.prompt")))
        self.edit = QLineEdit()
        self.edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.edit)
        layout.addSpacing(layout_fit.gap_section())
        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)
        apply_dialog_button_box(self._button_box)
        self.edit.setFocus()

    def password(self) -> str:
        return self.edit.text()


class EncryptOptionsDialog(ResponsiveDialog):
    """设置加密输出选项；紧凑分组。"""

    DESIGN_WIDTH = 420
    DESIGN_HEIGHT = 280
    DIALOG_KIND = "compact"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("encrypt.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(ui_scale.px(400))
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        grp_pwd = QGroupBox(t("encrypt.pwd_group"))
        pwd_form = QFormLayout(grp_pwd)
        layout_fit.apply_layout_gaps(pwd_form, related=True)
        self.edit_user = QLineEdit()
        self.edit_user.setEchoMode(QLineEdit.Password)
        self.edit_confirm = QLineEdit()
        self.edit_confirm.setEchoMode(QLineEdit.Password)
        pwd_form.addRow(t("encrypt.user_pwd"), self.edit_user)
        pwd_form.addRow(t("encrypt.confirm_pwd"), self.edit_confirm)
        layout.addWidget(grp_pwd)

        grp_perm = QGroupBox(t("encrypt.perm_group"))
        perm_layout = QVBoxLayout(grp_perm)
        layout_fit.apply_layout_gaps(perm_layout, related=True)
        self.chk_print = QCheckBox(t("encrypt.allow_print"))
        self.chk_print.setChecked(True)
        self.chk_copy = QCheckBox(t("encrypt.allow_copy"))
        self.chk_copy.setChecked(True)
        perm_layout.addWidget(self.chk_print)
        perm_layout.addWidget(self.chk_copy)
        layout.addWidget(grp_perm)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)
        apply_dialog_button_box(self._button_box)

    def _on_ok(self):
        if not self.edit_user.text():
            QMessageBox.warning(self, t("dialog.tip"), t("encrypt.empty_pwd"))
            return
        if self.edit_user.text() != self.edit_confirm.text():
            QMessageBox.warning(self, t("dialog.tip"), t("encrypt.pwd_mismatch"))
            return
        self.accept()

    def get_result(self):
        return {
            "user_password": self.edit_user.text(),
            "allow_print": self.chk_print.isChecked(),
            "allow_copy": self.chk_copy.isChecked(),
        }


class CompressDialog(ResponsiveDialog):
    """
    压缩设置：固定三档，或填写目标体积（MB）。
    顶部固定展示原 PDF 体积；目标必须小于原件。
    """

    DESIGN_WIDTH = 500
    DESIGN_HEIGHT = 430
    DIALOG_KIND = "compact"

    def __init__(self, parent=None, original_bytes: int = 0):
        super().__init__(parent)
        # 源文件字节数，用于展示原体积并校验目标不能更大
        self._original_bytes = max(0, int(original_bytes or 0))
        self.setWindowTitle(t("compress.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(ui_scale.px(460), ui_scale.px(320))
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        original_label = QLabel(
            t(
                "compress.original",
                size=format_file_size(self._original_bytes),
                bytes=f"{self._original_bytes:,}",
            )
        )
        original_label.setWordWrap(True)
        self._original_label = original_label
        layout.addWidget(original_label)

        grp = QGroupBox(t("compress.level"))
        grp_layout = QVBoxLayout(grp)
        layout_fit.apply_layout_gaps(grp_layout, related=True)
        tip = QLabel(t("compress.choose"))
        tip.setWordWrap(True)
        grp_layout.addWidget(tip)
        self.radio_light = QRadioButton(t("compress.light"))
        self.radio_standard = QRadioButton(t("compress.standard"))
        self.radio_strong = QRadioButton(t("compress.strong"))
        self.radio_target = QRadioButton(t("compress.target_mode"))
        self.radio_standard.setChecked(True)
        self._mode_group = QButtonGroup(self)
        for radio in (
            self.radio_light, self.radio_standard, self.radio_strong, self.radio_target
        ):
            # PyQt5 的 QRadioButton 无 setWordWrap，靠对话框宽度保证全文可见
            radio.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self._mode_group.addButton(radio)
            grp_layout.addWidget(radio)

        target_row = QHBoxLayout()
        self._target_caption = QLabel(t("compress.target_label"))
        self.spin_target_mb = QDoubleSpinBox()
        self.spin_target_mb.setDecimals(2)
        self.spin_target_mb.setSingleStep(0.5)
        self.spin_target_mb.setSuffix(" " + t("compress.target_unit"))
        original_mb = self._original_bytes / (1024.0 * 1024.0)
        # 下限 0.01MB；上限略小于原体积，避免填成「比原来还大」
        max_mb = max(0.01, original_mb * 0.99) if original_mb > 0.02 else max(0.001, original_mb * 0.5)
        self.spin_target_mb.setRange(0.01 if original_mb >= 0.02 else 0.001, max(0.01, max_mb))
        default_mb = 10.0
        if original_mb > 0:
            default_mb = min(10.0, max(0.01, original_mb * 0.5))
            default_mb = min(default_mb, max_mb)
        self.spin_target_mb.setValue(default_mb)
        target_row.addWidget(self._target_caption)
        target_row.addWidget(self.spin_target_mb, 1)
        grp_layout.addLayout(target_row)

        self._target_hint = QLabel(t("compress.target_hint"))
        self._target_hint.setWordWrap(True)
        grp_layout.addWidget(self._target_hint)

        self.chk_rasterize = QCheckBox(t("compress.rasterize"))
        self.chk_rasterize.setToolTip(t("compress.rasterize_tip"))
        self.chk_rasterize.setChecked(False)
        grp_layout.addWidget(self.chk_rasterize)
        layout.addWidget(grp)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self._on_accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)
        apply_dialog_button_box(self._button_box)

        self.radio_target.toggled.connect(self._sync_target_enabled)
        self._sync_target_enabled()
        # 原体积无效时禁用目标模式，避免 0B 文件填出怪异目标
        if self._original_bytes <= 0:
            self.radio_target.setEnabled(False)
            self.radio_target.setToolTip(t("compress.target_disabled_tip"))
            if self.radio_target.isChecked():
                self.radio_standard.setChecked(True)
            self._sync_target_enabled()

    def _sync_target_enabled(self):
        """仅在「按目标体积」且原体积有效时启用 MB 输入与栅格化。"""
        can_target = self._original_bytes > 0
        enabled = can_target and self.radio_target.isChecked()
        self._target_caption.setEnabled(enabled)
        self.spin_target_mb.setEnabled(enabled)
        self._target_hint.setEnabled(enabled)
        self.chk_rasterize.setEnabled(enabled)

    def apply_dialog_scale(self):
        """压缩窗：字号 + 单选最小高度，保证长文案完整。"""
        super().apply_dialog_scale()
        for radio in (
            self.radio_light, self.radio_standard, self.radio_strong, self.radio_target
        ):
            radio.setMinimumHeight(self.dpx(28))
        self.chk_rasterize.setMinimumHeight(self.dpx(28))

    def _on_accept(self):
        """确定前校验：目标模式必须小于原体积；原体积无效不可走目标。"""
        if self.radio_target.isChecked():
            if self._original_bytes <= 0:
                QMessageBox.warning(
                    self, t("dialog.tip"), t("compress.target_disabled_tip")
                )
                return
            target_bytes = self._target_bytes()
            if target_bytes <= 0 or target_bytes >= self._original_bytes:
                QMessageBox.warning(
                    self, t("dialog.tip"), t("compress.target_invalid_dialog")
                )
                return
        self.accept()

    def _target_bytes(self) -> int:
        """把用户填写的 MB 转成字节（1MB = 1024×1024）。"""
        return int(self.spin_target_mb.value() * 1024.0 * 1024.0)

    def get_level(self) -> str:
        """供旧调用兼容：返回档位名或 target。"""
        return self.get_options()["level"]

    def get_options(self) -> dict:
        """
        返回压缩参数。
        level: light/standard/strong/target
        target_bytes: 目标模式才有正数
        allow_rasterize: 仅目标模式且用户勾选时为 True
        """
        if self.radio_light.isChecked():
            level = "light"
        elif self.radio_strong.isChecked():
            level = "strong"
        elif self.radio_target.isChecked():
            level = "target"
        else:
            level = "standard"
        return {
            "level": level,
            "target_bytes": self._target_bytes() if level == "target" else None,
            "allow_rasterize": bool(
                level == "target" and self.chk_rasterize.isChecked()
            ),
        }


class ClickablePreviewLabel(QLabel):
    """可点击的缩略图标签，点击后发出信号以便打开放大预览。"""

    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        """左键点击缩略图时通知外层打开大图。"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class StampPreviewDialog(ResponsiveDialog):
    """
    水印/页码预览大窗：高清底图 + 界面放大缩小，可换页。
    include_watermarks=False 时只看页码；True 时叠加当前全部水印与页码。
    """

    DESIGN_WIDTH = 780
    DESIGN_HEIGHT = 900
    DIALOG_KIND = "workspace"

    def __init__(
        self,
        parent,
        pdf_path: str,
        password: str,
        page_count: int,
        page_index: int,
        include_watermarks: bool = False,
    ):
        super().__init__(parent)
        self._pdf_path = pdf_path
        self._password = password
        self._stamp_dialog = parent
        self._include_watermarks = bool(include_watermarks)
        self._base_pixmap = QPixmap()
        self._zoom = 1.0
        title_key = (
            "stamp.preview_full_title"
            if self._include_watermarks
            else "stamp.preview_large_title"
        )
        self.setWindowTitle(t(title_key))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(ui_scale.px(560), ui_scale.px(640))
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        head = QHBoxLayout()
        layout_fit.apply_layout_gaps(head, related=True)
        head.addWidget(QLabel(t("stamp.preview_page")))
        self.spin_page = QSpinBox()
        self.spin_page.setRange(1, max(1, int(page_count)))
        self.spin_page.setValue(max(1, int(page_index)))
        self.spin_page.valueChanged.connect(self._redraw_base)
        head.addWidget(self.spin_page)
        head.addSpacing(ui_scale.px(12))
        head.addWidget(QLabel(t("stamp.preview_zoom")))
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_out.setFixedWidth(ui_scale.px(36))
        self.btn_zoom_out.clicked.connect(lambda: self._change_zoom(0.8))
        head.addWidget(self.btn_zoom_out)
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setMinimumWidth(ui_scale.px(48))
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        head.addWidget(self.lbl_zoom)
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_in.setFixedWidth(ui_scale.px(36))
        self.btn_zoom_in.clicked.connect(lambda: self._change_zoom(1.25))
        head.addWidget(self.btn_zoom_in)
        self.btn_zoom_reset = QPushButton(t("stamp.preview_zoom_reset"))
        self.btn_zoom_reset.clicked.connect(self._reset_zoom)
        head.addWidget(self.btn_zoom_reset)
        head.addStretch()
        layout.addLayout(head)

        tip = QLabel(t("stamp.preview_zoom_tip"))
        tip.setWordWrap(True)
        layout.addWidget(tip)

        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setMinimumSize(ui_scale.px(400), ui_scale.px(520))
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignCenter)
        self._scroll.setWidget(self.lbl_image)
        layout.addWidget(self._scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        apply_dialog_button_box(buttons)
        layout.addWidget(buttons)
        QTimer.singleShot(0, self._redraw_base)

    def _preview_kwargs(self) -> dict:
        """从水印对话框取预览参数。"""
        if self._include_watermarks:
            return self._stamp_dialog._full_stamp_preview_kwargs()
        return {
            "text_watermark": "",
            "image_watermark_path": "",
            **self._stamp_dialog._page_number_draw_kwargs(),
        }

    def _redraw_base(self, *_args):
        """按当前页重新渲染高清底图，再套用缩放。"""
        max_edge = 1600
        png_bytes = render_stamp_preview_png(
            self._pdf_path,
            self._password,
            max(0, self.spin_page.value() - 1),
            max_edge,
            **self._preview_kwargs(),
        )
        if not png_bytes:
            self._base_pixmap = QPixmap()
            self.lbl_image.setPixmap(QPixmap())
            self.lbl_image.setText(t("stamp.preview_empty"))
            self.lbl_image.adjustSize()
            return
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes)
        if pixmap.isNull():
            self._base_pixmap = QPixmap()
            self.lbl_image.setText(t("stamp.preview_empty"))
            return
        self._base_pixmap = pixmap
        self._apply_zoom_display()

    def _change_zoom(self, factor: float):
        """相对当前比例放大或缩小。"""
        self._zoom = max(0.25, min(4.0, self._zoom * float(factor)))
        self._apply_zoom_display()

    def _reset_zoom(self):
        """恢复 100% 显示。"""
        self._zoom = 1.0
        self._apply_zoom_display()

    def _apply_zoom_display(self):
        """把底图按缩放比例显示到可滚动区域。"""
        self.lbl_zoom.setText(f"{int(round(self._zoom * 100))}%")
        if self._base_pixmap.isNull():
            return
        target_width = max(40, int(self._base_pixmap.width() * self._zoom))
        target_height = max(40, int(self._base_pixmap.height() * self._zoom))
        scaled = self._base_pixmap.scaled(
            target_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.lbl_image.setText("")
        self.lbl_image.setPixmap(scaled)
        self.lbl_image.resize(scaled.size())
        self.lbl_image.adjustSize()

    def wheelEvent(self, event):
        """Ctrl+滚轮缩放预览图。"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._change_zoom(1.1)
            elif delta < 0:
                self._change_zoom(1.0 / 1.1)
            event.accept()
            return
        super().wheelEvent(event)

    def apply_dialog_scale(self):
        """预览窗控件随弹窗比例微调。"""
        super().apply_dialog_scale()
        if hasattr(self, "btn_zoom_out"):
            self.btn_zoom_out.setFixedWidth(self.dpx(36))
            self.btn_zoom_in.setFixedWidth(self.dpx(36))
            layout_fit.fit_button(self.btn_zoom_reset, self._dialog_scale)


# 兼容旧类名：页码大预览仍可引用
PageNumberPreviewDialog = StampPreviewDialog


class StampDialog(ResponsiveDialog):
    """
    水印与页码：文字 / 图片 / 页码分三组；组内紧凑，组间拉开。
    """

    DESIGN_WIDTH = 780
    DESIGN_HEIGHT = 720
    DIALOG_KIND = "workspace"

    def __init__(self, parent=None, pdf_path: str = "", password: str = ""):
        super().__init__(parent)
        self._stamp_pdf_path = pdf_path or ""
        self._stamp_password = password or ""
        page_width_pt, page_height_pt = get_first_page_size_pt(
            self._stamp_pdf_path, self._stamp_password
        )
        self._page_width_pt = page_width_pt
        self._page_height_pt = page_height_pt
        try:
            self._preview_page_count = (
                get_page_count(self._stamp_pdf_path, self._stamp_password)
                if self._stamp_pdf_path else 1
            )
        except Exception:
            self._preview_page_count = 1
        self._page_unit = str(pref_get("stamp_page_unit", "mm") or "mm")
        if self._page_unit not in ("mm", "px"):
            self._page_unit = "mm"
        self._applying_page_geometry = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._refresh_page_preview)
        super().__init__(parent)
        self.setWindowTitle(t("stamp.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumWidth(ui_scale.px(640))
        self._text_color_rgb = _load_saved_watermark_color()
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        # ----- 文字水印 -----
        grp_text = QGroupBox(t("stamp.text_group"))
        text_layout = QVBoxLayout(grp_text)
        layout_fit.apply_layout_gaps(text_layout, related=True)
        self.chk_text = QCheckBox(t("stamp.add_text"))
        self.chk_text.setChecked(True)
        text_layout.addWidget(self.chk_text)
        self.edit_text = QLineEdit(t("stamp.default_text"))
        text_layout.addWidget(self.edit_text)

        row1 = QHBoxLayout()
        layout_fit.apply_layout_gaps(row1, related=True)
        row1.addWidget(QLabel(t("stamp.font_size")))
        self.spin_font = QSpinBox()
        self.spin_font.setRange(12, 120)
        self.spin_font.setValue(48)
        row1.addWidget(self.spin_font)
        row1.addWidget(QLabel(t("stamp.rotate")))
        self.spin_rotate = QSpinBox()
        self.spin_rotate.setRange(-90, 90)
        self.spin_rotate.setValue(45)
        row1.addWidget(self.spin_rotate)
        row1.addWidget(QLabel(t("stamp.opacity")))
        self.spin_opacity = QDoubleSpinBox()
        self.spin_opacity.setRange(0.05, 1.0)
        self.spin_opacity.setSingleStep(0.05)
        self.spin_opacity.setDecimals(2)
        self.spin_opacity.setValue(_load_saved_watermark_opacity())
        row1.addWidget(self.spin_opacity)
        row1.addStretch()
        text_layout.addLayout(row1)

        color_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(color_row, related=True)
        color_row.addWidget(QLabel(t("stamp.color")))
        self._preset_buttons = []
        for preset_name, preset_rgb in _WATERMARK_PRESET_COLORS:
            preset_button = QPushButton(t(preset_name))
            preset_button.setMinimumWidth(ui_scale.px(44))
            preset_button.setMinimumHeight(ui_scale.px(28))
            preset_button.setCursor(Qt.PointingHandCursor)
            preset_button.clicked.connect(
                lambda _checked=False, rgb=preset_rgb: self._set_text_color(rgb)
            )
            color_row.addWidget(preset_button)
            self._preset_buttons.append((preset_button, preset_rgb))
        self.btn_custom_color = QPushButton(t("stamp.custom_color"))
        self.btn_custom_color.setMinimumHeight(ui_scale.px(28))
        self.btn_custom_color.setCursor(Qt.PointingHandCursor)
        self.btn_custom_color.setToolTip(t("stamp.custom_color_tip"))
        self.btn_custom_color.clicked.connect(self._pick_custom_color)
        color_row.addWidget(self.btn_custom_color)
        self.lbl_color_swatch = QFrame()
        self.lbl_color_swatch.setFixedSize(ui_scale.px(36), ui_scale.px(28))
        self.lbl_color_swatch.setFrameShape(QFrame.StyledPanel)
        self.lbl_color_swatch.setToolTip(t("stamp.swatch_tip"))
        self.lbl_color_swatch.setCursor(Qt.PointingHandCursor)
        self.lbl_color_swatch.mousePressEvent = (
            lambda event: self._pick_custom_color()
        )
        color_row.addWidget(self.lbl_color_swatch)
        color_row.addStretch()
        text_layout.addLayout(color_row)
        self._refresh_color_swatch()
        self.chk_tile = QCheckBox(t("stamp.tile_text"))
        self.chk_tile.setChecked(True)
        text_layout.addWidget(self.chk_tile)
        layout.addWidget(grp_text)

        # ----- 图片水印 -----
        grp_image = QGroupBox(t("stamp.image_group"))
        image_layout = QVBoxLayout(grp_image)
        layout_fit.apply_layout_gaps(image_layout, related=True)
        self.chk_image = QCheckBox(t("stamp.add_image"))
        image_layout.addWidget(self.chk_image)
        img_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(img_row, related=True)
        self.edit_image = QLineEdit()
        self.edit_image.setPlaceholderText(t("stamp.image_placeholder"))
        self.btn_browse_image = QPushButton(t("stamp.browse"))
        self.btn_browse_image.clicked.connect(self._browse_image)
        img_row.addWidget(self.edit_image, 1)
        img_row.addWidget(self.btn_browse_image)
        image_layout.addLayout(img_row)
        img_opt_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(img_opt_row, related=True)
        img_opt_row.addWidget(QLabel(t("stamp.image_scale")))
        self.spin_image_scale = QDoubleSpinBox()
        self.spin_image_scale.setRange(0.05, 1.00)
        self.spin_image_scale.setSingleStep(0.05)
        self.spin_image_scale.setDecimals(2)
        self.spin_image_scale.setValue(0.22)
        self.spin_image_scale.setToolTip(t("stamp.image_scale_tip"))
        img_opt_row.addWidget(self.spin_image_scale)
        img_opt_row.addWidget(QLabel(t("stamp.image_opacity")))
        self.spin_image_opacity = QDoubleSpinBox()
        self.spin_image_opacity.setRange(0.05, 1.0)
        self.spin_image_opacity.setSingleStep(0.05)
        self.spin_image_opacity.setDecimals(2)
        self.spin_image_opacity.setValue(0.35)
        self.spin_image_opacity.setToolTip(t("stamp.image_opacity_tip"))
        img_opt_row.addWidget(self.spin_image_opacity)
        img_opt_row.addStretch()
        image_layout.addLayout(img_opt_row)
        self.chk_image_tile = QCheckBox(t("stamp.tile_image"))
        image_layout.addWidget(self.chk_image_tile)
        self.chk_underlay = QCheckBox(t("stamp.underlay"))
        self.chk_underlay.setChecked(False)
        image_layout.addWidget(self.chk_underlay)
        layout.addWidget(grp_image)

        # ----- 页码：格式 / 边距 / 框尺寸 / 真页预览（不影响文字与图片水印） -----
        grp_page = QGroupBox(t("stamp.page_group"))
        page_outer = QHBoxLayout(grp_page)
        layout_fit.apply_layout_gaps(page_outer, related=True)
        page_layout = QVBoxLayout()
        layout_fit.apply_layout_gaps(page_layout, related=True)
        self.chk_page_no = QCheckBox(t("stamp.add_page_no"))
        self.chk_page_no.setChecked(True)
        page_layout.addWidget(self.chk_page_no)

        format_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(format_row, related=True)
        format_row.addWidget(QLabel(t("stamp.page_format")))
        self.cmb_page_format = QComboBox()
        # 显示名用 X 占位，数据才是真正写入 PDF 的 {page}/{total} 模板
        self._page_template_pairs = (
            ("stamp.tpln_full", "stamp.tpl_full"),
            ("stamp.tpln_compact_cn", "stamp.tpl_compact_cn"),
            ("stamp.tpln_slash_page", "stamp.tpl_slash_page"),
            ("stamp.tpln_slash", "stamp.tpl_slash"),
            ("stamp.tpln_spaced", "stamp.tpl_spaced"),
            ("stamp.tpln_page_only", "stamp.tpl_page_only"),
        )
        for name_key, template_key in self._page_template_pairs:
            self.cmb_page_format.addItem(t(name_key), t(template_key))
        self.cmb_page_format.addItem(t("stamp.tpl_custom"), "")
        format_row.addWidget(self.cmb_page_format, 1)
        page_layout.addLayout(format_row)
        custom_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(custom_row, related=True)
        custom_row.addWidget(QLabel(t("stamp.page_custom")))
        self.edit_template = QLineEdit(t("stamp.page_template"))
        self.edit_template.setPlaceholderText(t("stamp.page_custom_tip"))
        custom_row.addWidget(self.edit_template, 1)
        page_layout.addLayout(custom_row)

        pos_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(pos_row, related=True)
        pos_row.addWidget(QLabel(t("stamp.position")))
        self.cmb_pos = QComboBox()
        self.cmb_pos.addItem(t("stamp.pos_bc"), "bottom_center")
        self.cmb_pos.addItem(t("stamp.pos_bl"), "bottom_left")
        self.cmb_pos.addItem(t("stamp.pos_br"), "bottom_right")
        self.cmb_pos.addItem(t("stamp.pos_tc"), "top_center")
        self.cmb_pos.addItem(t("stamp.pos_tl"), "top_left")
        self.cmb_pos.addItem(t("stamp.pos_tr"), "top_right")
        pos_row.addWidget(self.cmb_pos)
        pos_row.addWidget(QLabel(t("stamp.unit")))
        self.cmb_page_unit = QComboBox()
        self.cmb_page_unit.addItem(t("stamp.unit_mm"), "mm")
        self.cmb_page_unit.addItem(t("stamp.unit_px"), "px")
        unit_index = 0 if self._page_unit == "mm" else 1
        self.cmb_page_unit.setCurrentIndex(unit_index)
        pos_row.addWidget(self.cmb_page_unit)
        pos_row.addStretch()
        page_layout.addLayout(pos_row)

        offset_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(offset_row, related=True)
        self._lbl_offset_left = QLabel(t("stamp.offset_left"))
        offset_row.addWidget(self._lbl_offset_left)
        self.spin_offset_left = QDoubleSpinBox()
        self.spin_offset_left.setDecimals(1)
        offset_row.addWidget(self.spin_offset_left)
        self._lbl_offset_edge = QLabel(t("stamp.offset_bottom"))
        offset_row.addWidget(self._lbl_offset_edge)
        self.spin_offset_edge = QDoubleSpinBox()
        self.spin_offset_edge.setDecimals(1)
        offset_row.addWidget(self.spin_offset_edge)
        offset_row.addStretch()
        page_layout.addLayout(offset_row)

        box_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(box_row, related=True)
        box_row.addWidget(QLabel(t("stamp.box_width")))
        self.spin_box_width = QDoubleSpinBox()
        self.spin_box_width.setDecimals(1)
        box_row.addWidget(self.spin_box_width)
        box_row.addWidget(QLabel(t("stamp.box_height")))
        self.spin_box_height = QDoubleSpinBox()
        self.spin_box_height.setDecimals(1)
        box_row.addWidget(self.spin_box_height)
        box_row.addWidget(QLabel(t("stamp.page_font")))
        self.spin_page_font = QDoubleSpinBox()
        self.spin_page_font.setRange(7.0, 28.0)
        self.spin_page_font.setDecimals(1)
        self.spin_page_font.setSingleStep(0.5)
        saved_font = pref_get("stamp_page_font_size", 11.0)
        try:
            self.spin_page_font.setValue(max(7.0, min(28.0, float(saved_font))))
        except (TypeError, ValueError):
            self.spin_page_font.setValue(11.0)
        box_row.addWidget(self.spin_page_font)
        box_row.addStretch()
        page_layout.addLayout(box_row)
        # 框过窄时字号会被压小：用一行提示说明「设定 vs 实际」
        self.lbl_page_font_effective = QLabel("")
        self.lbl_page_font_effective.setWordWrap(True)
        self.lbl_page_font_effective.setStyleSheet(
            f"color:#8a5a00; font-size:{ui_scale.font_px(11)}px;"
        )
        page_layout.addWidget(self.lbl_page_font_effective)

        # 兼容旧控件名：偏好仍写毫米边距
        self.spin_page_margin = self.spin_offset_edge

        page_outer.addLayout(page_layout, 3)
        preview_box = QVBoxLayout()
        layout_fit.apply_layout_gaps(preview_box, related=True)
        preview_head = QHBoxLayout()
        layout_fit.apply_layout_gaps(preview_head, related=True)
        preview_head.addWidget(QLabel(t("stamp.preview")))
        preview_head.addWidget(QLabel(t("stamp.preview_page")))
        self.spin_preview_page = QSpinBox()
        self.spin_preview_page.setRange(1, max(1, int(self._preview_page_count)))
        self.spin_preview_page.setValue(1)
        preview_head.addWidget(self.spin_preview_page)
        self.btn_enlarge_preview = QPushButton(t("stamp.preview_enlarge"))
        self.btn_enlarge_preview.setCursor(Qt.PointingHandCursor)
        self.btn_enlarge_preview.clicked.connect(self._open_large_preview)
        preview_head.addWidget(self.btn_enlarge_preview)
        preview_head.addStretch()
        preview_box.addLayout(preview_head)
        self.lbl_page_preview = ClickablePreviewLabel(t("stamp.preview_hint"))
        self.lbl_page_preview.setAlignment(Qt.AlignCenter)
        self.lbl_page_preview.setMinimumSize(ui_scale.px(200), ui_scale.px(260))
        self.lbl_page_preview.setWordWrap(True)
        self.lbl_page_preview.setCursor(Qt.PointingHandCursor)
        self.lbl_page_preview.setToolTip(t("stamp.preview_click_tip"))
        self.lbl_page_preview.clicked.connect(self._open_large_preview)
        preview_box.addWidget(self.lbl_page_preview, 1)
        page_outer.addLayout(preview_box, 2)
        layout.addWidget(grp_page)

        preview_action_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(preview_action_row, related=True)
        self.btn_preview_watermark = QPushButton(t("stamp.preview_watermark"))
        self.btn_preview_watermark.setCursor(Qt.PointingHandCursor)
        self.btn_preview_watermark.setToolTip(t("stamp.preview_watermark_tip"))
        self.btn_preview_watermark.clicked.connect(self._open_watermark_preview)
        preview_action_row.addWidget(self.btn_preview_watermark)
        preview_action_row.addStretch()
        layout.addLayout(preview_action_row)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self._on_ok)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)
        apply_dialog_button_box(self._button_box)

        self._restore_page_geometry_from_prefs()
        self._bind_page_preview_signals()
        self._sync_offset_edge_label()
        QTimer.singleShot(0, self._refresh_page_preview)

    def apply_dialog_scale(self):
        """水印对话框：字号 + 色块/按钮/毫米 Spin 防裁切。"""
        super().apply_dialog_scale()
        for preset_button, preset_rgb in self._preset_buttons:
            preset_button.setMinimumHeight(self.dpx(28))
            layout_fit.fit_button(preset_button, self._dialog_scale, extra_pad=self.dpx(16))
            # 色名按钮用本色铺底，深色底配浅字、浅色底配深字，避免被主题盖成一团黑
            fill = _rgb_tuple_to_qcolor(preset_rgb)
            luminance = (
                0.299 * fill.red() + 0.587 * fill.green() + 0.114 * fill.blue()
            )
            label_color = "#FFFFFF" if luminance < 140 else "#1A1A1A"
            radius = self.dpx(4)
            preset_button.setStyleSheet(
                f"QPushButton{{background:{fill.name()}; color:{label_color};"
                f"border:1px solid #888; border-radius:{radius}px;"
                f"font-size:{self.dfs(12)}px;"
                f"padding:{self.dpx(2)}px {self.dpx(8)}px;}}"
                f"QPushButton:hover{{border:2px solid #89B4FA;}}"
            )
        self.btn_custom_color.setMinimumHeight(self.dpx(28))
        layout_fit.fit_button(self.btn_custom_color, self._dialog_scale)
        layout_fit.fit_button(self.btn_browse_image, self._dialog_scale)
        if hasattr(self, "btn_enlarge_preview"):
            layout_fit.fit_button(self.btn_enlarge_preview, self._dialog_scale)
        if hasattr(self, "btn_preview_watermark"):
            layout_fit.fit_button(self.btn_preview_watermark, self._dialog_scale)
        self.lbl_color_swatch.setFixedSize(self.dpx(36), self.dpx(28))
        self._refresh_color_swatch()
        if hasattr(self, "lbl_page_preview"):
            self.lbl_page_preview.setMinimumSize(self.dpx(200), self.dpx(260))
            sample = "888.8 毫米" if self._page_unit == "mm" else "888.8 像素"
            for page_spin in (
                self.spin_offset_left, self.spin_offset_edge,
                self.spin_box_width, self.spin_box_height,
            ):
                layout_fit.fit_spin_with_suffix(
                    page_spin, sample_text=sample, scale=self._dialog_scale
                )
            layout_fit.fit_spin_with_suffix(
                self.spin_page_font, sample_text="28.0", scale=self._dialog_scale
            )
            if hasattr(self, "lbl_page_font_effective"):
                self.lbl_page_font_effective.setStyleSheet(
                    f"color:#8a5a00; font-size:{self.dfs(11)}px;"
                )
        layout_fit.fit_spin_with_suffix(
            self.spin_opacity, sample_text="0.00", scale=self._dialog_scale
        )
        layout_fit.fit_spin_with_suffix(
            self.spin_image_opacity, sample_text="0.00", scale=self._dialog_scale
        )

    def _page_unit_suffix(self) -> str:
        """当前页码单位的 Spin 后缀。"""
        return " " + (t("stamp.unit_mm") if self._page_unit == "mm" else t("stamp.unit_px"))

    def _to_pt(self, value: float) -> float:
        """把界面上的毫米或像素转成 PDF 点。"""
        if self._page_unit == "px":
            return px_to_pt(value)
        return mm_to_pt(value)

    def _from_pt(self, points: float) -> float:
        """把 PDF 点转成当前界面单位。"""
        if self._page_unit == "px":
            return pt_to_px(points)
        return pt_to_mm(points)

    def _page_number_sample_text(self) -> str:
        """用总页数估最宽页码样本文字，供测宽与实际字号提示。"""
        template = self.edit_template.text().strip() or t("stamp.page_template")
        total_pages = max(1, int(getattr(self, "_preview_page_count", 1) or 1))
        page_token = str(total_pages)
        return template.replace("{page}", page_token).replace("{total}", str(total_pages))

    def _min_box_pts_for_current_font(self) -> Tuple[float, float]:
        """当前字号+模板下，框宽高至少需要多少 PDF 点。"""
        font_pt = float(self.spin_page_font.value()) if hasattr(self, "spin_page_font") else 11.0
        return page_number_box_mins_pt(self._page_number_sample_text(), font_pt)

    def _expand_box_to_fit_font(self):
        """
        字号/模板变大时只加宽加高框，不缩小用户已拉大的框。
        保证设定字号能真正画出来，预览与 Spin 一致。
        """
        min_width_pt, min_height_pt = self._min_box_pts_for_current_font()
        page_width = max(80.0, float(getattr(self, "_page_width_pt", 595.0) or 595.0))
        min_width_pt = min(min_width_pt, max(42.0, page_width - 8.0))
        current_width_pt = self._to_pt(self.spin_box_width.value())
        current_height_pt = self._to_pt(self.spin_box_height.value())
        if current_width_pt + 0.05 < min_width_pt:
            self._set_spin_pt(self.spin_box_width, min_width_pt)
        if current_height_pt + 0.05 < min_height_pt:
            self._set_spin_pt(self.spin_box_height, min_height_pt)

    def _update_effective_font_tip(self):
        """框装不下时提示实际字号，避免用户以为预览没刷新。"""
        if not hasattr(self, "lbl_page_font_effective"):
            return
        requested = float(self.spin_page_font.value())
        box_width_pt = self._to_pt(self.spin_box_width.value())
        box_height_pt = self._to_pt(self.spin_box_height.value())
        actual = effective_page_number_font_size(
            self._page_number_sample_text(),
            requested,
            box_width_pt,
            box_height_pt,
        )
        if actual + 0.35 < requested:
            self.lbl_page_font_effective.setText(
                t(
                    "stamp.page_font_effective",
                    actual=f"{actual:.1f}",
                    requested=f"{requested:.1f}",
                )
            )
        else:
            self.lbl_page_font_effective.setText("")

    def _apply_page_spin_ranges(self):
        """按单位设置偏移和框尺寸范围；框高下限随当前字号，框宽禁止过窄。"""
        suffix = self._page_unit_suffix()
        font_pt = float(self.spin_page_font.value()) if hasattr(self, "spin_page_font") else 11.0
        # 约字号×1.5，保证中文行高装得下；界面不允许再设更矮
        min_height_pt = max(font_pt * 1.5, 10.0)
        min_height_ui = self._from_pt(min_height_pt)
        # 绝对下限约 15mm，不再允许 8mm 那种几乎装不下「第 X 页」的宽度
        abs_min_width_pt = mm_to_pt(_PAGE_BOX_WIDTH_ABS_MIN_MM)
        min_width_ui = self._from_pt(abs_min_width_pt)
        if self._page_unit == "mm":
            ranges = {
                "left": (0.0, 200.0, 1.0),
                "edge": (0.0, 80.0, 0.5),
                "width": (max(15.0, min_width_ui), 120.0, 1.0),
                "height": (max(3.0, min_height_ui), 40.0, 0.5),
            }
        else:
            ranges = {
                "left": (0.0, 800.0, 4.0),
                "edge": (0.0, 300.0, 2.0),
                "width": (max(42.0, min_width_ui), 450.0, 4.0),
                "height": (max(10.0, min_height_ui), 150.0, 2.0),
            }
        mapping = (
            (self.spin_offset_left, ranges["left"]),
            (self.spin_offset_edge, ranges["edge"]),
            (self.spin_box_width, ranges["width"]),
            (self.spin_box_height, ranges["height"]),
        )
        for spin, (minimum, maximum, step) in mapping:
            spin.blockSignals(True)
            spin.setRange(minimum, maximum)
            spin.setSingleStep(step)
            spin.setSuffix(suffix)
            if spin.value() < minimum:
                spin.setValue(minimum)
            spin.blockSignals(False)

    def _on_page_font_changed(self, *_args):
        """字号变大时抬高框并自动加宽，保证预览里字真变大。"""
        if self._applying_page_geometry:
            return
        self._applying_page_geometry = True
        self._apply_page_spin_ranges()
        self._expand_box_to_fit_font()
        self._applying_page_geometry = False
        self._update_effective_font_tip()
        self._schedule_page_preview()

    def _set_spin_pt(self, spin: QDoubleSpinBox, points: float):
        """把 PDF 点写入 Spin（已按当前单位换算）。"""
        spin.blockSignals(True)
        spin.setValue(self._from_pt(points))
        spin.blockSignals(False)

    def _restore_page_geometry_from_prefs(self):
        """恢复上次页码框与边距；过窄/过矮的框按当前字号抬到可装字。"""
        self._apply_page_spin_ranges()
        default_left = max(20.0, (self._page_width_pt - 70.0) / 2.0)
        left_pt = float(pref_get("stamp_page_left_pt", default_left) or default_left)
        edge_pt = float(pref_get("stamp_page_edge_pt", mm_to_pt(10.0)) or mm_to_pt(10.0))
        width_pt = float(pref_get("stamp_page_box_width_pt", 70.0) or 70.0)
        height_pt = float(pref_get("stamp_page_box_height_pt", 20.0) or 20.0)
        font_pt = float(self.spin_page_font.value())
        min_width_pt, min_height_pt = page_number_box_mins_pt(
            self._page_number_sample_text(), font_pt
        )
        abs_min_width_pt = mm_to_pt(_PAGE_BOX_WIDTH_ABS_MIN_MM)
        width_pt = max(width_pt, min_width_pt, abs_min_width_pt)
        height_pt = max(height_pt, min_height_pt, 10.0)
        page_width = max(80.0, float(self._page_width_pt or 595.0))
        width_pt = min(width_pt, max(42.0, page_width - 8.0))
        self._set_spin_pt(self.spin_offset_left, left_pt)
        self._set_spin_pt(self.spin_offset_edge, edge_pt)
        self._set_spin_pt(self.spin_box_width, width_pt)
        self._set_spin_pt(self.spin_box_height, height_pt)
        self._sync_format_combo_from_template()
        self._update_effective_font_tip()

    def _bind_page_preview_signals(self):
        """页码相关控件变化时防抖刷新预览。"""
        self.chk_page_no.toggled.connect(self._schedule_page_preview)
        self.cmb_page_format.currentIndexChanged.connect(self._on_page_format_changed)
        self.edit_template.textChanged.connect(self._on_template_edited)
        self.cmb_pos.currentIndexChanged.connect(self._on_position_shortcut)
        self.cmb_page_unit.currentIndexChanged.connect(self._on_page_unit_changed)
        self.spin_offset_left.valueChanged.connect(self._schedule_page_preview)
        self.spin_offset_edge.valueChanged.connect(self._schedule_page_preview)
        self.spin_box_width.valueChanged.connect(self._on_page_box_geometry_changed)
        self.spin_box_height.valueChanged.connect(self._on_page_box_geometry_changed)
        self.spin_page_font.valueChanged.connect(self._on_page_font_changed)
        self.spin_preview_page.valueChanged.connect(self._schedule_page_preview)

    def _on_page_box_geometry_changed(self, *_args):
        """手改框宽高：刷新实际字号提示并重渲预览。"""
        if self._applying_page_geometry:
            return
        self._update_effective_font_tip()
        self._schedule_page_preview()

    def _schedule_page_preview(self, *_args):
        """短延迟后刷新，避免拖 Spin 时每一步都渲 PDF。"""
        if self._applying_page_geometry:
            return
        self._preview_timer.start(120)

    def _on_page_format_changed(self, _index: int):
        """选预设则填入模板；自定义不改当前输入。"""
        template = self.cmb_page_format.currentData()
        if template:
            self.edit_template.blockSignals(True)
            self.edit_template.setText(template)
            self.edit_template.blockSignals(False)
        self._on_page_template_geometry_changed()

    def _on_template_edited(self, _text: str):
        """手改模板时，对得上预设就同步下拉，否则显示自定义。"""
        self._sync_format_combo_from_template()
        self._on_page_template_geometry_changed()

    def _on_page_template_geometry_changed(self):
        """模板变长时加宽框，避免字号被压小。"""
        if self._applying_page_geometry:
            return
        self._applying_page_geometry = True
        self._expand_box_to_fit_font()
        self._applying_page_geometry = False
        self._update_effective_font_tip()
        self._schedule_page_preview()

    def _sync_format_combo_from_template(self):
        """按输入框内容选中对应格式项。"""
        current = self.edit_template.text().strip()
        self.cmb_page_format.blockSignals(True)
        matched = False
        for index in range(self.cmb_page_format.count()):
            data = self.cmb_page_format.itemData(index)
            if data and data == current:
                self.cmb_page_format.setCurrentIndex(index)
                matched = True
                break
        if not matched:
            self.cmb_page_format.setCurrentIndex(self.cmb_page_format.count() - 1)
        self.cmb_page_format.blockSignals(False)

    def _sync_offset_edge_label(self):
        """上沿锚点显示距顶边，下沿显示距下边。"""
        position_key = self.cmb_pos.currentData() or "bottom_center"
        if str(position_key).startswith("top"):
            self._lbl_offset_edge.setText(t("stamp.offset_top"))
        else:
            self._lbl_offset_edge.setText(t("stamp.offset_bottom"))

    def _on_position_shortcut(self, _index: int):
        """快捷位置只改左边距初值（居中/靠右），垂直仍由距下/顶边决定。"""
        self._sync_offset_edge_label()
        position_key = self.cmb_pos.currentData() or "bottom_center"
        box_width_pt = self._to_pt(self.spin_box_width.value())
        edge_pt = self._to_pt(self.spin_offset_edge.value())
        if "left" in position_key:
            left_pt = edge_pt
        elif "right" in position_key:
            left_pt = max(0.0, self._page_width_pt - box_width_pt - edge_pt)
        else:
            left_pt = max(0.0, (self._page_width_pt - box_width_pt) / 2.0)
        self._applying_page_geometry = True
        self._set_spin_pt(self.spin_offset_left, left_pt)
        self._applying_page_geometry = False
        self._schedule_page_preview()

    def _on_page_unit_changed(self, _index: int):
        """毫米/像素切换时换算四个数值，预览几何保持不变。"""
        left_pt = self._to_pt(self.spin_offset_left.value())
        edge_pt = self._to_pt(self.spin_offset_edge.value())
        width_pt = self._to_pt(self.spin_box_width.value())
        height_pt = self._to_pt(self.spin_box_height.value())
        new_unit = self.cmb_page_unit.currentData() or "mm"
        if new_unit == self._page_unit:
            return
        self._page_unit = new_unit
        self._applying_page_geometry = True
        self._apply_page_spin_ranges()
        self._set_spin_pt(self.spin_offset_left, left_pt)
        self._set_spin_pt(self.spin_offset_edge, edge_pt)
        self._set_spin_pt(self.spin_box_width, width_pt)
        self._set_spin_pt(self.spin_box_height, height_pt)
        self._applying_page_geometry = False
        self._schedule_page_preview()
        self._update_effective_font_tip()

    def _page_number_draw_kwargs(self) -> dict:
        """预览与导出共用的页码几何参数（内部已是 PDF 点）。"""
        edge_pt = self._to_pt(self.spin_offset_edge.value())
        return {
            "add_page_number": self.chk_page_no.isChecked(),
            "page_number_template": self.edit_template.text().strip() or t("stamp.page_template"),
            "page_number_position": self.cmb_pos.currentData() or "bottom_center",
            "page_number_font_size": float(self.spin_page_font.value()),
            "page_number_margin_mm": pt_to_mm(edge_pt),
            "page_number_offset_left_pt": self._to_pt(self.spin_offset_left.value()),
            "page_number_offset_edge_pt": edge_pt,
            "page_number_box_width_pt": self._to_pt(self.spin_box_width.value()),
            "page_number_box_height_pt": self._to_pt(self.spin_box_height.value()),
        }

    def _full_stamp_preview_kwargs(self) -> dict:
        """水印+页码完整预览参数，与确定后写入一致。"""
        return {
            "text_watermark": self.edit_text.text().strip() if self.chk_text.isChecked() else "",
            "text_font_size": float(self.spin_font.value()),
            "text_rotate": float(self.spin_rotate.value()),
            "text_opacity": float(self.spin_opacity.value()),
            "text_color": tuple(self._text_color_rgb),
            "text_tile": self.chk_tile.isChecked(),
            "image_watermark_path": (
                self.edit_image.text().strip() if self.chk_image.isChecked() else ""
            ),
            "image_scale": float(self.spin_image_scale.value()),
            "image_opacity": float(self.spin_image_opacity.value()),
            "image_tile": self.chk_image_tile.isChecked(),
            "watermark_overlay": not self.chk_underlay.isChecked(),
            **self._page_number_draw_kwargs(),
        }

    def _refresh_page_preview(self):
        """用真实 PDF 页渲染页码效果（缩略图不含文字/图片水印）。"""
        png_bytes = render_page_number_preview_png(
            self._stamp_pdf_path,
            self._stamp_password,
            max(0, self.spin_preview_page.value() - 1),
            max(180, self.lbl_page_preview.width() - 8),
            **self._page_number_draw_kwargs(),
        )
        if not png_bytes:
            self.lbl_page_preview.setPixmap(QPixmap())
            self.lbl_page_preview.setText(t("stamp.preview_empty"))
            return
        pixmap = QPixmap()
        pixmap.loadFromData(png_bytes)
        if pixmap.isNull():
            self.lbl_page_preview.setText(t("stamp.preview_empty"))
            return
        self.lbl_page_preview.setText("")
        self.lbl_page_preview.setPixmap(
            pixmap.scaled(
                self.lbl_page_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self._sync_open_preview_dialogs()

    def _sync_open_preview_dialogs(self):
        """若放大预览窗仍开着，按最新参数重绘。"""
        for attr_name in ("_large_preview_dialog", "_watermark_preview_dialog"):
            dialog = getattr(self, attr_name, None)
            if dialog is not None and dialog.isVisible():
                dialog._redraw_base()

    def _open_large_preview(self):
        """打开可缩放的页码高清预览。"""
        self._show_stamp_preview(
            attr_name="_large_preview_dialog",
            include_watermarks=False,
        )

    def _open_watermark_preview(self):
        """打开可缩放的水印+页码效果预览。"""
        if (
            not self.chk_text.isChecked()
            and not self.chk_image.isChecked()
            and not self.chk_page_no.isChecked()
        ):
            QMessageBox.information(self, t("dialog.tip"), t("stamp.need_one"))
            return
        self._show_stamp_preview(
            attr_name="_watermark_preview_dialog",
            include_watermarks=True,
        )

    def _show_stamp_preview(self, attr_name: str, include_watermarks: bool):
        """复用统一预览窗：页码专用或含水印。"""
        if not self._stamp_pdf_path:
            QMessageBox.information(self, t("dialog.tip"), t("stamp.preview_empty"))
            return
        existing = getattr(self, attr_name, None)
        if existing is not None and existing.isVisible():
            existing.spin_page.setValue(self.spin_preview_page.value())
            existing.raise_()
            existing.activateWindow()
            existing._redraw_base()
            return
        dialog = StampPreviewDialog(
            self,
            self._stamp_pdf_path,
            self._stamp_password,
            self._preview_page_count,
            self.spin_preview_page.value(),
            include_watermarks=include_watermarks,
        )
        setattr(self, attr_name, dialog)
        dialog.show()

    def _set_text_color(self, rgb_tuple):
        """切换当前水印色并刷新色块样式。"""
        self._text_color_rgb = (
            float(rgb_tuple[0]),
            float(rgb_tuple[1]),
            float(rgb_tuple[2]),
        )
        self._refresh_color_swatch()

    def _refresh_color_swatch(self):
        """按当前色更新预览色块背景。"""
        qcolor = _rgb_tuple_to_qcolor(self._text_color_rgb)
        hex_color = qcolor.name()
        radius = self.dpx(4) if hasattr(self, "_dialog_scale") else ui_scale.px(4)
        self.lbl_color_swatch.setStyleSheet(
            f"QFrame{{background:{hex_color};border:1px solid #888;"
            f"border-radius:{radius}px;}}"
        )

    def _pick_custom_color(self):
        """弹出系统取色器，确认后写入当前色。"""
        initial = _rgb_tuple_to_qcolor(self._text_color_rgb)
        chosen = QColorDialog.getColor(initial, self, t("stamp.pick_color"))
        if chosen.isValid():
            self._set_text_color(_qcolor_to_rgb_tuple(chosen))

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, t("stamp.pick_image"), "",
            t("stamp.image_filter"),
        )
        if path:
            self.edit_image.setText(path)
            self.chk_image.setChecked(True)

    def _on_ok(self):
        if not self.chk_text.isChecked() and not self.chk_image.isChecked() and not self.chk_page_no.isChecked():
            QMessageBox.warning(self, t("dialog.tip"), t("stamp.need_one"))
            return
        if self.chk_image.isChecked() and not os.path.isfile(self.edit_image.text().strip()):
            QMessageBox.warning(self, t("dialog.tip"), t("stamp.need_image"))
            return
        if self.chk_text.isChecked():
            pref_set("stamp_text_color", list(self._text_color_rgb))
            pref_set("stamp_text_opacity", float(self.spin_opacity.value()))
        if self.chk_page_no.isChecked():
            draw_kwargs = self._page_number_draw_kwargs()
            pref_set("stamp_page_margin_mm", float(draw_kwargs["page_number_margin_mm"]))
            pref_set("stamp_page_unit", self._page_unit)
            pref_set("stamp_page_left_pt", float(draw_kwargs["page_number_offset_left_pt"]))
            pref_set("stamp_page_edge_pt", float(draw_kwargs["page_number_offset_edge_pt"]))
            pref_set("stamp_page_box_width_pt", float(draw_kwargs["page_number_box_width_pt"]))
            pref_set("stamp_page_box_height_pt", float(draw_kwargs["page_number_box_height_pt"]))
            pref_set("stamp_page_font_size", float(self.spin_page_font.value()))
        self.accept()

    def get_result(self) -> dict:
        """返回 stamp_pdf 所需参数（含 text_color）。"""
        return {
            "text_watermark": self.edit_text.text().strip() if self.chk_text.isChecked() else "",
            "text_font_size": float(self.spin_font.value()),
            "text_rotate": float(self.spin_rotate.value()),
            "text_opacity": float(self.spin_opacity.value()),
            "text_color": tuple(self._text_color_rgb),
            "text_tile": self.chk_tile.isChecked(),
            "image_watermark_path": self.edit_image.text().strip() if self.chk_image.isChecked() else "",
            "image_scale": float(self.spin_image_scale.value()),
            "image_opacity": float(self.spin_image_opacity.value()),
            "image_tile": self.chk_image_tile.isChecked(),
            "watermark_overlay": not self.chk_underlay.isChecked(),
            **self._page_number_draw_kwargs(),
        }


class ImagesToPdfDialog(ResponsiveDialog):
    """多图转 PDF：列表吃空间；排序与页面模式分组。"""

    DESIGN_WIDTH = 520
    DESIGN_HEIGHT = 420
    DIALOG_KIND = "workspace"

    def __init__(self, image_paths: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("img2pdf.title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(ui_scale.px(520), ui_scale.px(420))
        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)

        grp_order = QGroupBox(t("img2pdf.order"))
        order_layout = QVBoxLayout(grp_order)
        layout_fit.apply_layout_gaps(order_layout, related=True)
        order_layout.addWidget(QLabel(t("img2pdf.order_tip")))
        self.list_widget = QListWidget()
        for path in image_paths:
            self.list_widget.addItem(QListWidgetItem(path))
        order_layout.addWidget(self.list_widget, 1)
        btn_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(btn_row, related=True)
        self.btn_up = QPushButton(t("img2pdf.up"))
        self.btn_down = QPushButton(t("img2pdf.down"))
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)
        btn_row.addWidget(self.btn_up)
        btn_row.addWidget(self.btn_down)
        btn_row.addStretch()
        order_layout.addLayout(btn_row)
        layout.addWidget(grp_order, 1)

        grp_mode = QGroupBox(t("img2pdf.mode"))
        mode_layout = QVBoxLayout(grp_mode)
        layout_fit.apply_layout_gaps(mode_layout, related=True)
        self.radio_a4 = QRadioButton(t("img2pdf.a4"))
        self.radio_orig = QRadioButton(t("img2pdf.orig"))
        self.radio_a4.setChecked(True)
        mode_layout.addWidget(self.radio_a4)
        mode_layout.addWidget(self.radio_orig)
        layout.addWidget(grp_mode)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)
        apply_dialog_button_box(self._button_box)

    def apply_dialog_scale(self):
        """图片转 PDF：字号 + 上移/下移按钮全文宽度。"""
        super().apply_dialog_scale()
        layout_fit.fit_buttons((self.btn_up, self.btn_down), self._dialog_scale)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row <= 0:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, item)
        self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= self.list_widget.count() - 1:
            return
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, item)
        self.list_widget.setCurrentRow(row + 1)

    def get_result(self) -> Tuple[List[str], str]:
        paths = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        mode = "a4_fit" if self.radio_a4.isChecked() else "original"
        return paths, mode


class PageThumbListWidget(QListWidget):
    """
    页面缩略图列表：自己处理按住拖松开，按「页与页之间的缝」判定插入。

    不用 Qt 自带 InternalMove / QDrag，避免松手不换位或丢页。
    """

    pages_reordered = pyqtSignal(int, int)  # from_row, insert_before
    preview_requested = pyqtSignal(int)  # row

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # 关闭 Qt 拖放，改由 mousePress/Move/Release 自己完成
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self._dialog_scale = 1.0  # 由页面管理弹窗写入，供缝线/提示缩放
        self._press_pos = QPoint()
        self._press_row = -1
        self._dragging = False
        self._insert_before = -1
        self._gap_line = QRect()
        self._ghost = QLabel(self.viewport())
        self._ghost.hide()
        self._ghost.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._tip = QLabel(t("img2pdf.insert_here"), self.viewport())
        self._tip.hide()
        self._tip.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.apply_tip_scale(1.0)

    def apply_tip_scale(self, dialog_scale: float):
        """按弹窗比例刷新插入提示气泡字号与内边距。"""
        self._dialog_scale = dialog_scale
        self._tip.setStyleSheet(
            f"QLabel{{background:#2979FF;color:#FFF;"
            f"font-size:{ui_scale.font_px(11, dialog_scale)}px;"
            f"padding:{ui_scale.px(2, dialog_scale)}px {ui_scale.px(8, dialog_scale)}px;"
            f"border-radius:{ui_scale.px(6, dialog_scale)}px;}}"
        )

    def mousePressEvent(self, event):
        """记录按下的页，供拖出阈值后进入重排。"""
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            self._press_pos = QPoint(event.pos())
            self._press_row = self.row(item) if item is not None else -1
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """超过拖拽阈值后按缝更新竖线；未达阈值则保持原选择行为。"""
        if not (event.buttons() & Qt.LeftButton) or self._press_row < 0:
            super().mouseMoveEvent(event)
            return
        if not self._dragging:
            distance = (event.pos() - self._press_pos).manhattanLength()
            if distance < QApplication.startDragDistance():
                super().mouseMoveEvent(event)
                return
            self._begin_gap_drag()
        self._refresh_gap_preview(event.pos())
        self._move_ghost(event.pos())
        event.accept()

    def mouseReleaseEvent(self, event):
        """松手：按当前竖线位置重排；未进入拖拽则交给默认单击。"""
        if event.button() == Qt.LeftButton and self._dragging:
            from_row = self._press_row
            insert_before = self._insert_before
            self._end_gap_drag()
            if from_row >= 0 and insert_before >= 0:
                if insert_before != from_row and insert_before != from_row + 1:
                    self.pages_reordered.emit(from_row, insert_before)
            event.accept()
            return
        self._end_gap_drag()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item is not None:
            self.preview_requested.emit(self.row(item))
        super().mouseDoubleClickEvent(event)

    def _begin_gap_drag(self):
        """进入缝插入拖拽：半透明跟手影子。"""
        self._dragging = True
        self.setCursor(Qt.ClosedHandCursor)
        item = self.item(self._press_row)
        if item is not None and not item.icon().isNull():
            pixmap = item.icon().pixmap(self.iconSize())
            faded = QPixmap(pixmap.size())
            faded.fill(Qt.transparent)
            painter = QPainter(faded)
            painter.setOpacity(0.55)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            self._ghost.setPixmap(faded)
            self._ghost.resize(faded.size())
            self._ghost.show()
            self._ghost.raise_()

    def _end_gap_drag(self):
        """结束拖拽视觉状态，不改数据。"""
        self._dragging = False
        self._press_row = -1
        self._insert_before = -1
        self._gap_line = QRect()
        self._ghost.hide()
        self._tip.hide()
        self.unsetCursor()
        self.viewport().update()

    def _move_ghost(self, pos: QPoint):
        """影子跟在光标右下，不挡缝。"""
        if self._ghost.isHidden():
            return
        self._ghost.move(pos + QPoint(12, 12))
        self._ghost.raise_()

    def _item_rect(self, row: int) -> QRect:
        """某一缩略图在视口中的矩形。"""
        return self.visualItemRect(self.item(row))

    def _group_visual_rows(self, indices: List[int]) -> List[List[int]]:
        """把剩余页按屏幕行分组（先上后下，行内从左到右）。"""
        if not indices:
            return []
        ordered = sorted(
            indices,
            key=lambda row: (self._item_rect(row).center().y(), self._item_rect(row).left()),
        )
        visual_rows: List[List[int]] = []
        for row in ordered:
            rect = self._item_rect(row)
            if not visual_rows:
                visual_rows.append([row])
                continue
            prev_center_y = self._item_rect(visual_rows[-1][0]).center().y()
            if abs(rect.center().y() - prev_center_y) < max(rect.height() * 0.45, 24):
                visual_rows[-1].append(row)
            else:
                visual_rows.append([row])
        for visual_row in visual_rows:
            visual_row.sort(key=lambda row: self._item_rect(row).left())
        return visual_rows

    def _refresh_gap_preview(self, pos: QPoint):
        """按光标找最近缝，更新竖线、插入下标与提示。"""
        insert_before, line = self._nearest_gap(pos, self._press_row)
        self._insert_before = insert_before
        self._gap_line = line
        self._update_insert_tip()
        self.viewport().update()

    def _nearest_gap(self, pos: QPoint, drag_row: int) -> Tuple[int, QRect]:
        """
        在「除被拖页外」的页面之间找最近缝。

        返回 (insert_before, 竖线矩形)。insert_before 为当前列表下标，
        表示插到该下标之前；等于 count 表示插到末尾。
        """
        count = self.count()
        thickness = max(3, ui_scale.px(4, self._dialog_scale))
        remaining = [row for row in range(count) if row != drag_row]
        if not remaining:
            return 0, QRect(8, 8, thickness, ui_scale.px(160, self._dialog_scale))

        visual_rows = self._group_visual_rows(remaining)
        reading_order: List[int] = []
        for visual_row in visual_rows:
            reading_order.extend(visual_row)

        # 先按 Y 落到哪一行（行带略放大，空白缝也好命中）
        chosen_row = visual_rows[0]
        best_y_dist = None
        for visual_row in visual_rows:
            tops = [self._item_rect(row).top() for row in visual_row]
            bottoms = [self._item_rect(row).bottom() for row in visual_row]
            top, bottom = min(tops), max(bottoms)
            if top - 16 <= pos.y() <= bottom + 16:
                chosen_row = visual_row
                break
            mid_y = (top + bottom) / 2.0
            dist = abs(pos.y() - mid_y)
            if best_y_dist is None or dist < best_y_dist:
                best_y_dist = dist
                chosen_row = visual_row

        def reading_index(original_row: int) -> int:
            return reading_order.index(original_row)

        first_row = chosen_row[0]
        last_row = chosen_row[-1]
        first_rect = self._item_rect(first_row)
        last_rect = self._item_rect(last_row)
        line_top = min(first_rect.top(), last_rect.top())
        line_height = max(first_rect.height(), last_rect.height())

        # 每条缝：(x, 在剩余阅读顺序中的插入下标 k)
        gaps: List[Tuple[int, int]] = []
        gaps.append((first_rect.left() - 2, reading_index(first_row)))
        for left_row, right_row in zip(chosen_row, chosen_row[1:]):
            left_rect = self._item_rect(left_row)
            right_rect = self._item_rect(right_row)
            mid_x = int((left_rect.right() + right_rect.left()) / 2)
            gaps.append((mid_x, reading_index(right_row)))
        gaps.append((last_rect.right() + 2, reading_index(last_row) + 1))

        nearest_x, remain_k = min(gaps, key=lambda item: abs(pos.x() - item[0]))
        if remain_k >= len(reading_order):
            insert_before = count
        else:
            insert_before = reading_order[remain_k]
        line = QRect(nearest_x - thickness // 2, line_top, thickness, line_height)
        return insert_before, line

    def _update_insert_tip(self):
        """竖线旁显示「将插入此处」。"""
        if not self._dragging or self._gap_line.isNull():
            self._tip.hide()
            return
        self._tip.setText(t("img2pdf.insert_here"))
        self._tip.adjustSize()
        tip_x = self._gap_line.right() + 6
        tip_y = max(0, self._gap_line.top())
        if tip_x + self._tip.width() > self.viewport().width():
            tip_x = max(0, self._gap_line.left() - self._tip.width() - 6)
        self._tip.move(tip_x, tip_y)
        self._tip.show()
        self._tip.raise_()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._dragging or self._gap_line.isNull():
            return
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#2979FF")))
        painter.drawRoundedRect(self._gap_line, 2, 2)
        painter.end()



class PagePreviewDialog(ResponsiveDialog):
    """离线单页大图预览：本地 PyMuPDF 渲染；预览区吃空间，导航贴紧。"""

    DESIGN_WIDTH = 720
    DESIGN_HEIGHT = 560
    DIALOG_KIND = "workspace"

    def __init__(
        self,
        pdf_path: str,
        password: str,
        pages: List[Tuple[int, int]],
        start_index: int,
        parent=None,
    ):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.password = password or ""
        self.pages = list(pages)
        self.current_index = max(0, min(start_index, len(self.pages) - 1))
        self._zoom = 1.0
        self.setWindowTitle(t("preview.offline_title"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(ui_scale.px(720), ui_scale.px(560))
        layout = QVBoxLayout(self)

        self.lbl_info = QLabel()
        layout.addWidget(self.lbl_info)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.scroll.setWidget(self.lbl_image)
        layout.addWidget(self.scroll, 1)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton(t("preview.prev"))
        self.btn_next = QPushButton(t("preview.next"))
        self.btn_zoom_out = QPushButton(t("preview.zoom_out"))
        self.btn_zoom_in = QPushButton(t("preview.zoom_in"))
        self.btn_fit = QPushButton(t("preview.fit"))
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.btn_next)
        nav.addStretch()
        nav.addWidget(self.btn_zoom_out)
        nav.addWidget(self.btn_zoom_in)
        nav.addWidget(self.btn_fit)
        layout.addLayout(nav)

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)
        close_box.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        layout.addWidget(close_box)

        self.btn_prev.clicked.connect(self._go_prev)
        self.btn_next.clicked.connect(self._go_next)
        self.btn_zoom_out.clicked.connect(lambda: self._set_zoom(self._zoom / 1.25))
        self.btn_zoom_in.clicked.connect(lambda: self._set_zoom(self._zoom * 1.25))
        self.btn_fit.clicked.connect(self._fit_window)
        self._reload_image()

    def apply_dialog_scale(self):
        """预览弹窗：字号放大 + 导航按钮全文 + 按新视口重渲。"""
        self.apply_common_chrome()
        self.apply_root_gaps(related=False)
        self.lbl_info.setStyleSheet(
            f"font-size:{self.dfs(13)}px; color:"
            f"{'#CDD6F4' if self.is_dark_theme() else '#333333'};"
        )
        layout_fit.fit_buttons(
            (
                self.btn_prev,
                self.btn_next,
                self.btn_zoom_out,
                self.btn_zoom_in,
                self.btn_fit,
            ),
            self._dialog_scale,
        )
        self.fit_dialog_buttons()
        if self.isVisible():
            self._reload_image()

    def _set_zoom(self, value: float):
        self._zoom = max(0.4, min(3.0, float(value)))
        self._reload_image()

    def _fit_window(self):
        self._zoom = 1.0
        self._reload_image()

    def _go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._reload_image()

    def _go_next(self):
        if self.current_index < len(self.pages) - 1:
            self.current_index += 1
            self._reload_image()

    def _reload_image(self):
        """按当前列表页与缩放重新渲染离线预览图。"""
        if not self.pages:
            self.lbl_image.setText(t("preview.empty"))
            return
        source_index, rotation = self.pages[self.current_index]
        self.lbl_info.setText(
            t(
                "preview.info",
                current=self.current_index + 1,
                total=len(self.pages),
                source=source_index + 1,
                zoom=int(self._zoom * 100),
            )
        )
        self.btn_prev.setEnabled(self.current_index > 0)
        self.btn_next.setEnabled(self.current_index < len(self.pages) - 1)
        # 以视口短边为基准，再乘用户缩放
        viewport = self.scroll.viewport().size()
        base_edge = max(400, min(viewport.width(), viewport.height()) - 40)
        max_edge = int(base_edge * self._zoom)
        try:
            png_bytes = render_page_preview(
                self.pdf_path,
                source_index,
                self.password,
                max_edge=max_edge,
                rotation=rotation,
            )
            image = QImage.fromData(png_bytes, "PNG")
            self.lbl_image.setPixmap(QPixmap.fromImage(image))
        except Exception as exc:
            self.lbl_image.setText(t("preview.fail", error=exc))


class PageManagerDialog(ResponsiveDialog):
    """
    页面管理：缩略图多选，支持删除/旋转/提取/重排/离线预览后另存。
    工具按钮折两行并按全文撑宽，避免「仅提取选中页」被裁切。
    """

    DESIGN_WIDTH = 900
    DESIGN_HEIGHT = 620
    DIALOG_KIND = "workspace"

    def __init__(self, pdf_path: str, password: str = "", parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.password = password or ""
        self.setWindowTitle(t("pages.title", name=os.path.basename(pdf_path)))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(ui_scale.px(780), ui_scale.px(520))

        # 当前顺序：元素为 (source_index, rotation_delta) —— 唯一数据源
        self._pages: List[Tuple[int, int]] = []
        page_count = get_page_count(pdf_path, self.password)
        self._pages = [(index, 0) for index in range(page_count)]

        layout = QVBoxLayout(self)
        layout_fit.apply_layout_gaps(layout, related=False, margin=True)
        self._tip_label = QLabel(t("pages.tip"))
        self._tip_label.setWordWrap(True)
        layout.addWidget(self._tip_label)

        self.list_widget = PageThumbListWidget()
        self.list_widget.setIconSize(QSize(ui_scale.px(120), ui_scale.px(160)))
        self.list_widget.setSpacing(ui_scale.px(10))
        self.list_widget.pages_reordered.connect(self._on_pages_reordered)
        self.list_widget.preview_requested.connect(self._preview_row)
        layout.addWidget(self.list_widget, 1)

        # 工具行拆两行，避免长文案被挤成省略号
        tool_block = QVBoxLayout()
        layout_fit.apply_layout_gaps(tool_block, related=True)
        edit_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(edit_row, related=True)
        self.btn_delete = QPushButton(t("pages.delete"))
        self.btn_rot_left = QPushButton(t("pages.rot_left"))
        self.btn_rot_right = QPushButton(t("pages.rot_right"))
        edit_row.addWidget(self.btn_delete)
        edit_row.addWidget(self.btn_rot_left)
        edit_row.addWidget(self.btn_rot_right)
        edit_row.addStretch()
        tool_block.addLayout(edit_row)

        action_row = QHBoxLayout()
        layout_fit.apply_layout_gaps(action_row, related=True)
        self.btn_preview = QPushButton(t("pages.preview"))
        self.btn_extract = QPushButton(t("pages.extract"))
        action_row.addWidget(self.btn_preview)
        action_row.addWidget(self.btn_extract)
        action_row.addStretch()
        tool_block.addLayout(action_row)
        layout.addLayout(tool_block)

        self._button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)
        apply_dialog_button_box(self._button_box)
        self._button_box.button(QDialogButtonBox.Ok).setText(t("pages.save_all"))

        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_rot_left.clicked.connect(lambda: self._rotate_selected(-90))
        self.btn_rot_right.clicked.connect(lambda: self._rotate_selected(90))
        self.btn_preview.clicked.connect(self._preview_selected)
        self.btn_extract.clicked.connect(self._mark_extract_only)

        self._extract_only = False
        # 缩略图清晰重渲防抖：拖大窗口时先快速拉伸，停手后再按新尺寸渲染
        self._thumb_rerender_timer = QTimer(self)
        self._thumb_rerender_timer.setSingleShot(True)
        self._thumb_rerender_timer.timeout.connect(self._rerender_thumbs_for_scale)
        self._reload_icons()

    def apply_dialog_scale(self):
        """页面管理：字号/按钮全文 + 缩略图格子放大，并延迟清晰重渲。"""
        self.apply_common_chrome()
        self.apply_root_gaps(related=False)
        self._tip_label.setStyleSheet(
            f"font-size:{self.dfs(12)}px; color:"
            f"{'#CDD6F4' if self.is_dark_theme() else '#333333'};"
        )
        layout_fit.fit_buttons(
            (
                self.btn_delete,
                self.btn_rot_left,
                self.btn_rot_right,
                self.btn_preview,
                self.btn_extract,
            ),
            self._dialog_scale,
        )
        self.fit_dialog_buttons(self._button_box)
        icon_width = self.dpx(120)
        icon_height = self.dpx(160)
        self.list_widget.setIconSize(QSize(icon_width, icon_height))
        self.list_widget.setSpacing(self.dpx(10))
        self.list_widget.apply_tip_scale(self._dialog_scale)
        size_hint = QSize(self.dpx(130), self.dpx(190))
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            item.setSizeHint(size_hint)
            icon = item.icon()
            if icon.isNull():
                continue
            available = icon.availableSizes()
            source_size = available[0] if available else QSize(icon_width, icon_height)
            source_pixmap = icon.pixmap(source_size)
            if source_pixmap.isNull():
                continue
            stretched = source_pixmap.scaled(
                icon_width,
                icon_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            item.setIcon(QIcon(stretched))
        self._thumb_rerender_timer.start(220)

    def _rerender_thumbs_for_scale(self):
        """按当前弹窗比例用 PyMuPDF 重新生成清晰缩略图。"""
        size_hint = QSize(self.dpx(130), self.dpx(190))
        for row, (source_index, rotation) in enumerate(self._pages):
            if row >= self.list_widget.count():
                break
            item = self.list_widget.item(row)
            pixmap = self._make_page_pixmap(source_index, rotation)
            item.setIcon(QIcon(pixmap))
            item.setSizeHint(size_hint)

    def _make_page_pixmap(self, source_index: int, rotation: int) -> QPixmap:
        """生成单页缩略图（含旋转预览），边长随弹窗比例变化。"""
        try:
            png_bytes = render_page_thumbnail(
                self.pdf_path,
                source_index,
                self.password,
                max_edge=self.dpx(160),
                rotation=rotation,
            )
            image = QImage.fromData(png_bytes, "PNG")
            return QPixmap.fromImage(image)
        except Exception:
            pixmap = QPixmap(self.dpx(120), self.dpx(160))
            pixmap.fill(Qt.lightGray)
            return pixmap

    def _reload_icons(self):
        """按当前 _pages 全量刷新缩略图列表（删除/提取后使用）。"""
        self.list_widget.clear()
        progress = QProgressDialog(
            t("pages.gen_thumbs"), t("dialog.cancel"), 0, len(self._pages), self
        )
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        for ui_index, (source_index, rotation) in enumerate(self._pages):
            progress.setValue(ui_index)
            QApplication.processEvents()
            if progress.wasCanceled():
                break
            self._append_list_item(source_index, rotation)
        progress.setValue(len(self._pages))
        self._assert_list_matches_pages()

    def _append_list_item(self, source_index: int, rotation: int):
        """追加一项缩略图，写入源页号与旋转。"""
        pixmap = self._make_page_pixmap(source_index, rotation)
        item = QListWidgetItem(QIcon(pixmap), t("pages.page_label", num=source_index + 1))
        item.setData(Qt.UserRole, source_index)
        item.setData(Qt.UserRole + 1, rotation)
        item.setSizeHint(QSize(self.dpx(130), self.dpx(190)))
        self.list_widget.addItem(item)

    def _sync_pages_from_list(self):
        """把列表当前视觉顺序写回 _pages。"""
        synced = []
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            synced.append((int(item.data(Qt.UserRole)), int(item.data(Qt.UserRole + 1) or 0)))
        self._pages = synced

    def _assert_list_matches_pages(self):
        """列表项数必须与 _pages 一致，防止拖拽丢页后静默少页。"""
        if self.list_widget.count() != len(self._pages):
            # 以数据源为准强制重建
            self.list_widget.blockSignals(True)
            self.list_widget.clear()
            for source_index, rotation in self._pages:
                self._append_list_item(source_index, rotation)
            self.list_widget.blockSignals(False)

    def _on_pages_reordered(self, from_row: int, insert_before: int):
        """
        数据驱动重排：只挪动现有 QListWidgetItem，不重渲缩略图。
        """
        if from_row < 0 or from_row >= len(self._pages):
            return
        if insert_before < 0:
            insert_before = 0
        if insert_before > len(self._pages):
            insert_before = len(self._pages)
        # 先改数据
        moving = self._pages.pop(from_row)
        if insert_before > from_row:
            insert_before -= 1
        self._pages.insert(insert_before, moving)
        # 再改界面项（保持图标，避免大 PDF 卡顿）
        item = self.list_widget.takeItem(from_row)
        if item is None:
            self._reload_icons()
            return
        # take 之后下标已变：若原 insert_before 在 from_row 之后，需减一
        target = insert_before
        self.list_widget.insertItem(target, item)
        self.list_widget.setCurrentItem(item)
        self._assert_list_matches_pages()
        self._sync_pages_from_list()

    def _selected_rows(self) -> List[int]:
        return sorted({index.row() for index in self.list_widget.selectedIndexes()}, reverse=True)

    def _delete_selected(self):
        rows = self._selected_rows()
        if not rows:
            return
        if self.list_widget.count() - len(rows) < 1:
            QMessageBox.warning(self, t("dialog.tip"), t("pages.keep_one"))
            return
        for row in rows:
            self.list_widget.takeItem(row)
        self._sync_pages_from_list()
        self._assert_list_matches_pages()

    def _rotate_selected(self, delta: int):
        """只更新选中项的旋转预览，避免整本缩略图重载卡顿。"""
        indexes = self.list_widget.selectedIndexes()
        if not indexes:
            return
        selected_rows = sorted({model_index.row() for model_index in indexes})
        for row in selected_rows:
            item = self.list_widget.item(row)
            source_index = int(item.data(Qt.UserRole))
            rotation = (int(item.data(Qt.UserRole + 1) or 0) + delta) % 360
            item.setData(Qt.UserRole + 1, rotation)
            pixmap = self._make_page_pixmap(source_index, rotation)
            item.setIcon(QIcon(pixmap))
        self._sync_pages_from_list()
        for row in selected_rows:
            item = self.list_widget.item(row)
            if item:
                item.setSelected(True)

    def _preview_selected(self):
        """预览当前选中的第一页；无选中则预览当前项。"""
        indexes = self.list_widget.selectedIndexes()
        if indexes:
            row = min(index.row() for index in indexes)
        else:
            item = self.list_widget.currentItem()
            if item is None:
                QMessageBox.information(self, t("dialog.tip"), t("pages.need_preview"))
                return
            row = self.list_widget.row(item)
        self._preview_row(row)

    def _preview_row(self, row: int):
        """打开离线预览对话框。"""
        self._sync_pages_from_list()
        if row < 0 or row >= len(self._pages):
            return
        dialog = PagePreviewDialog(
            self.pdf_path, self.password, self._pages, row, self
        )
        dialog.exec_()

    def _mark_extract_only(self):
        if not self.list_widget.selectedIndexes():
            QMessageBox.information(self, t("dialog.tip"), t("pages.need_extract"))
            return
        selected_rows = sorted({i.row() for i in self.list_widget.selectedIndexes()})
        keep_items = []
        for row in selected_rows:
            item = self.list_widget.item(row)
            keep_items.append((int(item.data(Qt.UserRole)), int(item.data(Qt.UserRole + 1) or 0)))
        self._pages = keep_items
        self._extract_only = True
        self._reload_icons()

    def get_result(self) -> Tuple[List[int], dict]:
        """返回 keep_order 与 rotations 映射（按源页号）。"""
        self._sync_pages_from_list()
        self._assert_list_matches_pages()
        keep_order = [source_index for source_index, _ in self._pages]
        rotations = {}
        for source_index, rotation in self._pages:
            if rotation:
                rotations[source_index] = rotation
        return keep_order, rotations
