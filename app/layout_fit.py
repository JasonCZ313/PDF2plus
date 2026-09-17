# -*- coding: utf-8 -*-
"""
布局适配：防文字裁切、相关紧/无关远间距令牌。

配合 ui_scale / ResponsiveDialog：缩放后仍保证按钮、Spin 全文可见。
"""
from __future__ import annotations

from typing import Iterable, Optional

from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from app import ui_scale


def gap_related(scale: float = None) -> int:
    """同功能组内间距（标签↔控件、同组按钮）。"""
    return ui_scale.px(6, scale)


def gap_section(scale: float = None) -> int:
    """不同功能块之间的间距，明显大于组内。"""
    return ui_scale.px(16, scale)


def gap_dialog_margin(scale: float = None) -> int:
    """弹窗外边距。"""
    return ui_scale.px(14, scale)


def apply_layout_gaps(
    layout: QLayout,
    *,
    related: bool = True,
    scale: float = None,
    margin: bool = False,
) -> None:
    """
    给布局套间距令牌。

    related=True 用组内紧间距；False 用区块间距。
    margin=True 时同步设置四周边距。
    """
    spacing = gap_related(scale) if related else gap_section(scale)
    layout.setSpacing(spacing)
    if margin:
        edge = gap_dialog_margin(scale)
        layout.setContentsMargins(edge, edge, edge, edge)


def fit_button(button: QPushButton, scale: float = None, extra_pad: int = None) -> None:
    """
    按当前字体把按钮最小宽度撑到能显示全文，避免省略号裁切。

    计入字号与左右内边距，大/特大字号时仍能完整显示。
    """
    if button is None:
        return
    button.ensurePolished()
    metrics = QFontMetrics(button.font())
    text = button.text() or ""
    text_width = metrics.horizontalAdvance(text)
    # 左右 padding + 边框余量
    pad = extra_pad if extra_pad is not None else (
        ui_scale.px(20, scale) + ui_scale.px(16, scale) + ui_scale.px(8, scale)
    )
    button.setMinimumWidth(max(ui_scale.px(72, scale), text_width + pad))
    button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    button.updateGeometry()


def fit_buttons(buttons: Iterable[QPushButton], scale: float = None) -> None:
    """批量 fit_button。"""
    for button in buttons:
        fit_button(button, scale)


def fit_spin_with_suffix(
    spin: QAbstractSpinBox,
    sample_text: Optional[str] = None,
    scale: float = None,
) -> None:
    """
    按「样本文字 + 上下箭头区」设置 Spin 最小宽度，避免 suffix 贴死箭头。

    sample_text 不传时用当前显示文本。
    """
    if spin is None:
        return
    spin.ensurePolished()
    metrics = QFontMetrics(spin.font())
    if sample_text is None:
        if hasattr(spin, "cleanText") and hasattr(spin, "suffix"):
            sample_text = f"{spin.cleanText()}{spin.suffix()}"
        else:
            sample_text = "00.0 毫米"
    text_width = metrics.horizontalAdvance(sample_text or "00.0 毫米")
    arrow_zone = ui_scale.px(36, scale)
    pad = ui_scale.px(16, scale)
    spin.setMinimumWidth(text_width + arrow_zone + pad)


def fit_widget_min_width(widget: QWidget, text: str, scale: float = None, extra: int = None) -> None:
    """按文字给任意控件设最小宽度（下拉、标签等）。"""
    if widget is None:
        return
    metrics = QFontMetrics(widget.font())
    pad = extra if extra is not None else ui_scale.px(24, scale)
    widget.setMinimumWidth(metrics.horizontalAdvance(text) + pad)


def fit_combo_min_width(
    combo: QWidget,
    sample_texts: Iterable[str],
    scale: float = None,
    pixel_size: int = None,
) -> None:
    """
    按下拉框「实际显示字号」计算最小宽度，避免 QSS font-size 与 QFont 不一致时文字溢出盖住右侧标签。

    sample_texts：各选项文案，取最宽一项；额外预留下拉箭头与内边距。
    """
    if combo is None:
        return
    combo.ensurePolished()
    measure_font = QFont(combo.font())
    # 与偏好行 QSS 使用同一像素字号，保证量宽与渲染一致
    if pixel_size is not None and pixel_size > 0:
        measure_font.setPixelSize(int(pixel_size))
        combo.setFont(measure_font)
    metrics = QFontMetrics(measure_font)
    widest = 0
    for sample in sample_texts:
        if not sample:
            continue
        widest = max(widest, metrics.horizontalAdvance(str(sample)))
    # 左右 padding + 下拉箭头区 + 边框余量（特大字号下 QSS 内边距更大，多留余量防视觉溢出）
    arrow_and_pad = ui_scale.px(44, scale) + ui_scale.px(28, scale)
    needed_width = max(ui_scale.px(72, scale), widest + arrow_and_pad)
    # 固定宽高：布局必须按此分配，避免总宽不够时被压扁后互相盖住
    combo.setFixedWidth(needed_width)
    combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    combo.updateGeometry()
