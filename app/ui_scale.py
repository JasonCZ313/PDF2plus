# -*- coding: utf-8 -*-
"""
界面响应式缩放（方案 C）

以设计稿尺寸为基准，按当前窗口宽高计算统一缩放因子，
供 QSS、控件几何、列表自绘、说明面板 HTML 共同使用。
"""
from __future__ import annotations

from typing import Dict

from app.config import (
    UI_DESIGN_WIDTH,
    UI_DESIGN_HEIGHT,
    UI_SCALE_MIN,
    UI_SCALE_MAX,
    UI_SCALE_EPSILON,
    DIALOG_SCALE_MIN,
    DIALOG_SCALE_MAX,
    DIALOG_SCALE_EPSILON,
    UI_FONT_SIZE_DEFAULT,
    UI_FONT_SIZE_MULTIPLIERS,
)

# 进程内当前缩放因子（主窗口 resize 时更新）
_current_scale: float = 1.0
# 用户字号档位倍率（默认/大/特大），与窗口缩放相乘
_font_multiplier: float = 1.0
_font_size_preset: str = UI_FONT_SIZE_DEFAULT
# 最近一次窗口客户区高度，供底部说明区独立放大字号
_window_height: int = UI_DESIGN_HEIGHT


def get_scale() -> float:
    """返回当前全局 UI 缩放因子（不含字号倍率）。"""
    return _current_scale


def set_scale(scale: float) -> None:
    """写入当前全局缩放因子（由主窗口在确认需要刷新后调用）。"""
    global _current_scale
    _current_scale = float(scale)


def get_font_size_preset() -> str:
    """返回当前字号档位键名。"""
    return _font_size_preset


def get_font_multiplier() -> float:
    """返回当前字号倍率。"""
    return _font_multiplier


def set_font_size_preset(preset: str) -> None:
    """设置字号档位；非法值回落默认。"""
    global _font_multiplier, _font_size_preset
    key = str(preset or UI_FONT_SIZE_DEFAULT).strip().lower()
    if key not in UI_FONT_SIZE_MULTIPLIERS:
        key = UI_FONT_SIZE_DEFAULT
    _font_size_preset = key
    _font_multiplier = float(UI_FONT_SIZE_MULTIPLIERS[key])


def _combined_factor(scale: float = None) -> float:
    """窗口缩放 × 字号倍率，供像素与字号换算。"""
    base = _current_scale if scale is None else float(scale)
    return base * _font_multiplier


def set_window_height(window_height: int) -> None:
    """记录主窗口高度，底部说明面板按此单独放大字号与高度。"""
    global _window_height
    _window_height = max(1, int(window_height))


def help_font_px(base_pixels: float) -> int:
    """
    底部功能介绍/使用方法专用字号。

    随窗口高度放大，上限高于全局 UI_SCALE_MAX，避免最大化后说明区字仍过小；
    再乘用户字号倍率。
    """
    height_ratio = _window_height / float(UI_DESIGN_HEIGHT)
    factor = max(_current_scale, height_ratio)
    if factor < UI_SCALE_MIN:
        factor = UI_SCALE_MIN
    # 说明区允许比按钮区更大，方便一次读完步骤
    if factor > 1.70:
        factor = 1.70
    value = int(round(base_pixels * factor * _font_multiplier))
    return max(12, value)


def help_min_height() -> int:
    """底部说明区保底高度：随窗口变高与字号档位加高。"""
    height_ratio = _window_height / float(UI_DESIGN_HEIGHT)
    factor = max(_current_scale, min(height_ratio, 1.70)) * _font_multiplier
    return max(px(168), int(round(180 * factor)))


def compute_scale(window_width: int, window_height: int) -> float:
    """
    根据窗口客户区尺寸相对设计稿计算缩放。

    取宽高比例的较小值，避免超宽屏把字放得过大导致纵向溢出；
    再用上下限夹住，防止极端分辨率失控。
    """
    if window_width <= 0 or window_height <= 0:
        return 1.0
    width_ratio = window_width / float(UI_DESIGN_WIDTH)
    height_ratio = window_height / float(UI_DESIGN_HEIGHT)
    raw_scale = min(width_ratio, height_ratio)
    if raw_scale < UI_SCALE_MIN:
        return UI_SCALE_MIN
    if raw_scale > UI_SCALE_MAX:
        return UI_SCALE_MAX
    return raw_scale


def scale_changed_significantly(new_scale: float, old_scale: float = None) -> bool:
    """变化小于阈值则视为无需刷新，减轻拖拽窗口时的闪烁。"""
    baseline = _current_scale if old_scale is None else old_scale
    return abs(new_scale - baseline) >= UI_SCALE_EPSILON


def compute_dialog_scale(
    dialog_width: int,
    dialog_height: int,
    design_width: int,
    design_height: int,
) -> float:
    """
    按弹窗当前客户区相对该弹窗设计稿计算本地缩放。

    与主窗口全局 scale 独立：用户拉大弹窗时字号/控件随弹窗变大。
    """
    if dialog_width <= 0 or dialog_height <= 0 or design_width <= 0 or design_height <= 0:
        return 1.0
    width_ratio = dialog_width / float(design_width)
    height_ratio = dialog_height / float(design_height)
    raw_scale = min(width_ratio, height_ratio)
    if raw_scale < DIALOG_SCALE_MIN:
        return DIALOG_SCALE_MIN
    if raw_scale > DIALOG_SCALE_MAX:
        return DIALOG_SCALE_MAX
    return raw_scale


def dialog_scale_changed(new_scale: float, old_scale: float) -> bool:
    """弹窗缩放变化是否达到刷新阈值。"""
    return abs(new_scale - old_scale) >= DIALOG_SCALE_EPSILON


def px(base_pixels: float, scale: float = None) -> int:
    """将设计稿像素按（窗口缩放×字号倍率）取整，至少为 1。"""
    value = int(round(base_pixels * _combined_factor(scale)))
    return max(1, value)


def font_px(base_pixels: float, scale: float = None) -> int:
    """字号缩放（含用户档位倍率），下限 10px。"""
    value = int(round(base_pixels * _combined_factor(scale)))
    return max(10, value)


def qss_tokens(scale: float = None) -> Dict[str, int]:
    """
    生成填入浅色/深色 QSS 模板的全部尺寸令牌。

    键名与模板中的 {占位符} 一一对应；已含字号倍率。
    """
    # 传入 combined 因子，避免 px/font_px 再乘一次倍率
    window_part = _current_scale if scale is None else float(scale)
    factor = window_part  # px/font_px 内部会再乘 _font_multiplier

    def size(base: float) -> int:
        return px(base, factor)

    def font(base: float) -> int:
        return font_px(base, factor)

    return {
        "fs": font(13),
        "fs_sm": font(12),
        "fs_xs": font(11),
        "radius_lg": size(10),
        "radius_md": size(8),
        "radius_sm": size(6),
        "radius_xs": size(5),
        "radius_xxs": size(4),
        "group_margin_top": size(14),
        "group_pad_t": size(16),
        "group_pad_h": size(14),
        "group_pad_b": size(12),
        "title_pad_v": size(2),
        "title_pad_h": size(12),
        "btn_pad_v": size(6),
        "btn_pad_h": size(16),
        "list_pad": size(4),
        "check_space": size(6),
        "check_size": size(18),
        "check_border": max(1, size(2)),
        "progress_h": size(22),
        "progress_radius": size(6),
        "progress_chunk_radius": size(5),
        "edit_pad_v": size(4),
        "edit_pad_h": size(8),
        "combo_pad_v": size(4),
        "combo_pad_h": size(10),
        "combo_min_w": size(80),
        "combo_drop_pad": size(8),
        "header_pad_v": size(6),
        "header_pad_h": size(8),
        "header_border": max(1, size(2)),
        "splitter": max(2, size(3)),
        "spin_pad_v": size(3),
        "spin_pad_h": size(8),
        "scroll_w": size(10),
        "scroll_radius": size(5),
        "scroll_min_h": size(30),
        "msg_btn_pad_v": size(5),
        "msg_btn_pad_h": size(20),
        "msg_btn_min_w": size(70),
        "msg_btn_radius": size(4),
    }
