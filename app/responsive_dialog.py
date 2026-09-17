# -*- coding: utf-8 -*-
"""
弹窗响应式缩放基类。

主窗口用全局 ui_scale；弹窗用本地 dialog_scale。
COMPACT：紧凑设置窗，按内容定尺寸，避免拉出大片空白。
WORKSPACE：工作区窗，列表/预览吃 stretch，工具栏贴紧。
"""
from __future__ import annotations

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from app import ui_scale
from app import layout_fit


class ResponsiveDialog(QDialog):
    """
    可随自身尺寸放大/缩小的对话框基类。

    子类设置 DESIGN_WIDTH / DESIGN_HEIGHT，并重写 apply_dialog_scale()。
    DIALOG_KIND = \"compact\" | \"workspace\" 决定尺寸策略。
    """

    DESIGN_WIDTH = 480
    DESIGN_HEIGHT = 360
    # compact：内容定高，限制盲目拉空；workspace：可自由拉大
    DIALOG_KIND = "workspace"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dialog_scale = 1.0
        self._dialog_scale_applied = False
        self._dialog_scale_timer = QTimer(self)
        self._dialog_scale_timer.setSingleShot(True)
        self._dialog_scale_timer.timeout.connect(self._refresh_dialog_scale)

    def dpx(self, base_pixels: float) -> int:
        """按当前弹窗比例换算像素。"""
        return ui_scale.px(base_pixels, self._dialog_scale)

    def dfs(self, base_pixels: float) -> int:
        """按当前弹窗比例换算字号。"""
        return ui_scale.font_px(base_pixels, self._dialog_scale)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._dialog_scale_timer.start(80)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._on_first_show)

    def _on_first_show(self):
        """首次显示：刷新缩放；紧凑窗再按内容收一收尺寸。"""
        self._refresh_dialog_scale()
        if self.DIALOG_KIND == "compact":
            self._shrink_to_content()

    def _shrink_to_content(self):
        """
        紧凑窗：按布局推荐尺寸定高，避免打开时上下空洞。
        仍允许用户略放大（字号会跟），但默认不浪费空间。
        """
        layout = self.layout()
        if layout is None:
            return
        layout.activate()
        hint = self.sizeHint()
        # 不低于当前最小尺寸，不强制改宽度若已更宽
        target_width = max(self.minimumWidth(), hint.width())
        target_height = max(self.minimumHeight(), hint.height())
        # 略留一点余量，避免贴边裁切
        target_width += self.dpx(8)
        target_height += self.dpx(8)
        self.resize(target_width, target_height)

    def _refresh_dialog_scale(self):
        """根据弹窗客户区计算本地缩放并应用。"""
        new_scale = ui_scale.compute_dialog_scale(
            self.width(),
            self.height(),
            self.DESIGN_WIDTH,
            self.DESIGN_HEIGHT,
        )
        if self._dialog_scale_applied and not ui_scale.dialog_scale_changed(
            new_scale, self._dialog_scale
        ):
            return
        self._dialog_scale = new_scale
        self._dialog_scale_applied = True
        self.apply_dialog_scale()

    def is_dark_theme(self) -> bool:
        """
        判断当前弹窗应套深色还是浅色。
        优先用自身标记，再沿父控件找主窗 _is_dark，保证与主界面主题一致。
        """
        if hasattr(self, "_is_dark"):
            return bool(getattr(self, "_is_dark"))
        if hasattr(self, "_split_is_dark"):
            return bool(getattr(self, "_split_is_dark"))
        parent_widget = self.parentWidget()
        while parent_widget is not None:
            if hasattr(parent_widget, "_is_dark"):
                return bool(getattr(parent_widget, "_is_dark"))
            parent_widget = parent_widget.parentWidget()
        return False

    def apply_common_chrome(self):
        """
        通用控件字号、最小高度，并按主题成对写入字色与背景色。
        浅色：深字 + 浅底；深色：浅字 + 深底。禁止只改字色不改背景。
        """
        is_dark = self.is_dark_theme()
        fs = self.dfs(13)
        fs_sm = self.dfs(12)
        btn_min_h = self.dpx(30)
        edit_min_h = self.dpx(28)
        pad_v = self.dpx(5)
        pad_h = self.dpx(12)
        item_pad_v = self.dpx(4)
        item_pad_h = self.dpx(8)
        radius = self.dpx(6)

        if is_dark:
            # 深色板：与主窗 / 全局深色 QSS 对齐
            text_color = "#CDD6F4"
            muted_color = "#A6ADC8"
            dialog_bg = "#1E1E2E"
            panel_bg = "#252536"
            edit_bg = "#313244"
            btn_bg = "#2E2E40"
            btn_hover = "#3A3A55"
            border = "#454560"
            border_soft = "#3A3A50"
            sel_bg = "#454560"
            hover_bg = "#3A3A55"
            group_title_bg = "#1E1E2E"
            accent_border = "#89B4FA"
        else:
            # 浅色板：保持原有可读对比度
            text_color = "#333333"
            muted_color = "#555555"
            dialog_bg = "#FFFFFF"
            panel_bg = "#FFFFFF"
            edit_bg = "#FFFFFF"
            btn_bg = "#FFFFFF"
            btn_hover = "#F0F3FF"
            border = "#D0D5DD"
            border_soft = "#DDE"
            sel_bg = "#E8F0FE"
            hover_bg = "#F0F3FF"
            group_title_bg = "#FFFFFF"
            accent_border = "#2C6FBB"

        self.setStyleSheet(
            f"QDialog{{background:{dialog_bg}; color:{text_color};}}"
            f"QLabel{{font-size:{fs}px; color:{text_color};}}"
            f"QRadioButton{{font-size:{fs}px; color:{text_color};}}"
            f"QCheckBox{{font-size:{fs}px; color:{text_color};}}"
            f"QPushButton{{font-size:{fs}px;min-height:{btn_min_h}px;"
            f"padding:{pad_v}px {pad_h}px; color:{text_color};"
            f"background:{btn_bg}; border:1px solid {border};"
            f"border-radius:{radius}px;}}"
            f"QPushButton:hover{{color:{text_color}; background:{btn_hover};"
            f"border-color:{accent_border};}}"
            f"QDialogButtonBox QPushButton{{font-size:{fs}px;min-height:{btn_min_h}px;"
            f"padding:{pad_v}px {pad_h}px; color:{text_color};"
            f"background:{btn_bg}; border:1px solid {border};"
            f"border-radius:{radius}px;}}"
            f"QDialogButtonBox QPushButton:hover{{color:{text_color};"
            f"background:{btn_hover}; border-color:{accent_border};}}"
            f"QLineEdit{{font-size:{fs}px;min-height:{edit_min_h}px;"
            f"color:{text_color}; background:{edit_bg}; border:1px solid {border};}}"
            f"QSpinBox{{font-size:{fs}px;min-height:{edit_min_h}px;"
            f"color:{text_color}; background:{edit_bg}; border:1px solid {border};}}"
            f"QDoubleSpinBox{{font-size:{fs}px;min-height:{edit_min_h}px;"
            f"color:{text_color}; background:{edit_bg}; border:1px solid {border};}}"
            f"QComboBox{{font-size:{fs}px;min-height:{edit_min_h}px;"
            f"color:{text_color}; background:{edit_bg}; border:1px solid {border};}}"
            f"QComboBox:hover{{color:{text_color}; border-color:{accent_border};}}"
            f"QComboBox QAbstractItemView{{color:{text_color}; background:{edit_bg};"
            f"selection-background-color:{sel_bg}; selection-color:{text_color}; outline:none;}}"
            f"QComboBox QAbstractItemView::item{{color:{text_color}; background:{edit_bg};"
            f"padding:{item_pad_v}px {item_pad_h}px;}}"
            f"QComboBox QAbstractItemView::item:selected{{color:{text_color}; background:{sel_bg};}}"
            f"QComboBox QAbstractItemView::item:hover{{color:{text_color}; background:{hover_bg};}}"
            f"QListWidget{{font-size:{fs}px; color:{text_color}; background:{panel_bg};"
            f"border:1px solid {border_soft};}}"
            f"QListWidget::item{{color:{text_color};}}"
            f"QListWidget::item:selected{{color:{text_color}; background:{sel_bg};}}"
            f"QListWidget::item:hover{{color:{text_color}; background:{hover_bg};}}"
            f"QTableWidget{{font-size:{fs}px; color:{text_color}; background:{panel_bg};"
            f"border:1px solid {border_soft}; gridline-color:{border_soft};}}"
            f"QTableWidget::item{{color:{text_color};}}"
            f"QTableWidget::item:selected{{color:{text_color}; background:{sel_bg};}}"
            f"QTableWidget::item:hover{{color:{text_color}; background:{hover_bg};}}"
            f"QHeaderView::section{{font-size:{fs_sm}px;padding:{self.dpx(4)}px;"
            f"color:{muted_color}; background:{edit_bg}; border:none;}}"
            f"QGroupBox{{font-size:{fs}px; color:{muted_color}; background:{panel_bg};"
            f"border:1px solid {border_soft};}}"
            f"QGroupBox::title{{font-size:{fs}px; color:{muted_color};"
            f"background:{group_title_bg};}}"
            f"QTextEdit{{color:{text_color}; background:{panel_bg}; border:1px solid {border_soft};}}"
            f"QPlainTextEdit{{color:{text_color}; background:{panel_bg}; border:1px solid {border_soft};}}"
            f"QMenu::item{{color:{text_color};}}"
            f"QMenu::item:selected{{color:{text_color}; background:{sel_bg};}}"
        )

    def apply_root_gaps(self, related: bool = False):
        """根布局套边距与区块间距。"""
        root = self.layout()
        if root is None:
            return
        layout_fit.apply_layout_gaps(
            root, related=related, scale=self._dialog_scale, margin=True
        )

    def fit_dialog_buttons(self, button_box: QDialogButtonBox = None):
        """把对话框底部 OK/Cancel 等按钮按全文撑宽。"""
        boxes = []
        if button_box is not None:
            boxes.append(button_box)
        else:
            boxes = self.findChildren(QDialogButtonBox)
        for box in boxes:
            for button in box.buttons():
                layout_fit.fit_button(button, self._dialog_scale)

    def apply_dialog_scale(self):
        """子类可重写；默认通用字号 + 根间距 + 底栏按钮 fit。"""
        self.apply_common_chrome()
        self.apply_root_gaps(related=(self.DIALOG_KIND == "compact"))
        self.fit_dialog_buttons()
