# -*- coding: utf-8 -*-
"""
浅色 / 深色 QSS 模板：尺寸全部用占位符，由 ui_scale.qss_tokens 填充。
颜色与选择器结构保持不变，仅数值随窗口缩放。
"""
from __future__ import annotations

from typing import Dict

from app import ui_scale


_LIGHT_QSS_TEMPLATE = """
QMainWindow {{
    background: #F5F6FA;
}}
QWidget {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: {fs}px;
    color: #333;
}}
QScrollArea {{
    background: #F5F6FA;
    border: none;
}}
QScrollArea > QWidget {{
    background: #F5F6FA;
}}
QSplitter {{
    background: #F5F6FA;
}}
QGroupBox {{
    border: 1px solid #DDE;
    border-radius: {radius_lg}px;
    margin-top: {group_margin_top}px;
    padding: {group_pad_t}px {group_pad_h}px {group_pad_b}px {group_pad_h}px;
    background: #FFFFFF;
    font-weight: bold;
    font-size: {fs}px;
    color: #444;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: {title_pad_v}px {title_pad_h}px;
    background: #F5F6FA;
    border-radius: {radius_sm}px;
    color: #555;
}}
QPushButton {{
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
    border-radius: {radius_md}px;
    padding: {btn_pad_v}px {btn_pad_h}px;
    color: #333;
    font-size: {fs}px;
}}
QPushButton:hover {{
    background: #F0F3FF;
    border-color: #2C6FBB;
    color: #333;
}}
QPushButton:pressed {{
    background: #DFE6F0;
    color: #333;
}}
QListWidget {{
    background: #FFFFFF;
    border: 1px solid #DDE;
    border-radius: {radius_md}px;
    padding: {list_pad}px;
    outline: none;
    color: #333;
}}
QListWidget::item {{
    border: none;
    padding: 0px;
    color: #333;
}}
QListWidget::item:selected {{
    background: #E8F0FE;
    color: #1A1A1A;
}}
QListWidget::item:hover {{
    background: #F0F3FF;
    color: #1A1A1A;
}}
QListWidget::item:selected:hover {{
    background: #D6E4FF;
    color: #1A1A1A;
}}
QCheckBox {{
    spacing: {check_space}px;
    color: #444;
}}
QCheckBox::indicator {{
    width: {check_size}px;
    height: {check_size}px;
    border: {check_border}px solid #B0B8C8;
    border-radius: {radius_xxs}px;
    background: #FFF;
}}
QCheckBox::indicator:checked {{
    background: #2C6FBB;
    border-color: #2C6FBB;
}}
QCheckBox::indicator:hover {{
    border-color: #2C6FBB;
}}
QProgressBar {{
    border: 1px solid #DDE;
    border-radius: {progress_radius}px;
    text-align: center;
    background: #EAECF0;
    height: {progress_h}px;
    color: #333;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2C6FBB, stop:1 #4A90D9);
    border-radius: {progress_chunk_radius}px;
}}
QLineEdit {{
    padding: {edit_pad_v}px {edit_pad_h}px;
    font-size: {fs}px;
    border: 1px solid #D0D5DD;
    border-radius: {radius_md}px;
    background: #FFF;
    color: #333;
}}
QLineEdit:focus {{
    border-color: #2C6FBB;
}}
QComboBox {{
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
    border-radius: {radius_md}px;
    padding: {combo_pad_v}px {combo_pad_h}px;
    min-width: {combo_min_w}px;
    color: #333333;
}}
QComboBox:hover, QComboBox:focus, QComboBox:on {{
    border-color: #2C6FBB;
    color: #333333;
    background: #FFFFFF;
}}
QComboBox::drop-down {{
    border: none;
    background: transparent;
    padding-right: {combo_drop_pad}px;
}}
QComboBox QAbstractItemView {{
    background: #FFFFFF;
    border: 1px solid #DDE;
    border-radius: {radius_sm}px;
    color: #333333;
    outline: none;
    selection-background-color: #E8F0FE;
    selection-color: #1A1A1A;
}}
QComboBox QAbstractItemView::item {{
    color: #333333;
    background: #FFFFFF;
    min-height: {edit_pad_v}px;
    padding: {combo_pad_v}px {combo_pad_h}px;
}}
QComboBox QAbstractItemView::item:selected {{
    color: #1A1A1A;
    background: #E8F0FE;
}}
QComboBox QAbstractItemView::item:hover {{
    color: #1A1A1A;
    background: #F0F3FF;
}}
QMenu {{
    background: #FFF;
    color: #333;
    border: 1px solid #DDE;
}}
QMenu::item {{
    color: #333;
    background: transparent;
    padding: {combo_pad_v}px {combo_pad_h}px;
}}
QMenu::item:selected {{
    color: #1A1A1A;
    background: #E8F0FE;
}}
QStatusBar {{
    background: #EAECF0;
    border-top: 1px solid #DDE;
    color: #666;
}}
QTableWidget {{
    background: #FFF;
    border: 1px solid #DDE;
    border-radius: {radius_md}px;
    gridline-color: #EEE;
    color: #333;
}}
QTableWidget::item {{
    color: #333;
}}
QTableWidget::item:selected {{
    background: #E8F0FE;
    color: #1A1A1A;
}}
QTableWidget::item:hover {{
    background: #F0F3FF;
    color: #1A1A1A;
}}
QHeaderView::section {{
    background: #F0F2F5;
    padding: {header_pad_v}px {header_pad_h}px;
    border: none;
    border-bottom: {header_border}px solid #DDE;
    font-weight: bold;
    color: #555;
}}
QFrame[frameShape="5"] {{
    background: #FFFFFF;
    border: 1px solid #DDE;
    border-radius: {radius_md}px;
}}
QSplitter::handle {{
    background: #E0E4EA;
}}
QSplitter::handle:horizontal {{
    width: {splitter}px;
}}
QSplitter::handle:vertical {{
    height: {splitter}px;
}}
QSpinBox, QDoubleSpinBox {{
    border: 1px solid #D0D5DD;
    border-radius: {radius_sm}px;
    padding: {spin_pad_v}px {spin_pad_h}px;
    background: #FFF;
    color: #333;
}}
QRadioButton {{
    color: #333;
}}
QScrollBar:vertical {{
    background: #F5F6FA;
    width: {scroll_w}px;
    border-radius: {scroll_radius}px;
}}
QScrollBar::handle:vertical {{
    background: #C0C8D4;
    border-radius: {scroll_radius}px;
    min-height: {scroll_min_h}px;
}}
QScrollBar::handle:vertical:hover {{
    background: #A0A8B4;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QMessageBox {{
    background: #FFFFFF;
}}
QMessageBox QLabel {{
    color: #333333;
    font-size: {fs}px;
}}
QMessageBox QPushButton {{
    color: #333333;
    background: #F0F0F0;
    border: 1px solid #C0C0C0;
    border-radius: {msg_btn_radius}px;
    padding: {msg_btn_pad_v}px {msg_btn_pad_h}px;
    min-width: {msg_btn_min_w}px;
}}
QMessageBox QPushButton:hover {{
    background: #E0E0E0;
    color: #333333;
}}
QDialog {{
    background: #FFFFFF;
    color: #333333;
}}
QDialog QLabel {{
    color: #333333;
    font-size: {fs}px;
}}
QDialog QRadioButton {{
    color: #333333;
}}
QDialog QCheckBox {{
    color: #333333;
}}
QDialog QGroupBox {{
    color: #444444;
    background: #FFFFFF;
    border: 1px solid #DDE;
}}
QDialog QGroupBox::title {{
    color: #555555;
    background: #FFFFFF;
}}
QDialog QTableWidget {{
    color: #333333;
    background: #FFFFFF;
}}
QDialog QTableWidget::item:selected {{
    color: #1A1A1A;
    background: #E8F0FE;
}}
QDialog QHeaderView::section {{
    color: #555555;
    background: #F0F2F5;
}}
QDialog QComboBox {{
    color: #333333;
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
}}
QDialog QComboBox QAbstractItemView {{
    color: #333333;
    background: #FFFFFF;
    selection-background-color: #E8F0FE;
    selection-color: #1A1A1A;
}}
QDialog QComboBox QAbstractItemView::item:selected {{
    color: #1A1A1A;
    background: #E8F0FE;
}}
QDialog QComboBox QAbstractItemView::item:hover {{
    color: #1A1A1A;
    background: #F0F3FF;
}}
QDialog QPushButton {{
    color: #333333;
}}
QDialog QPushButton:hover {{
    color: #333333;
    background: #F0F3FF;
}}
QDialog QSpinBox, QDialog QDoubleSpinBox {{
    color: #333333;
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
}}
QDialog QLineEdit {{
    color: #333333;
    background: #FFFFFF;
    border: 1px solid #D0D5DD;
}}
QDialog QListWidget {{
    color: #333333;
    background: #FFFFFF;
}}
QDialog QListWidget::item {{
    color: #333333;
}}
QDialog QListWidget::item:selected {{
    color: #1A1A1A;
    background: #E8F0FE;
}}
QDialog QListWidget::item:hover {{
    color: #1A1A1A;
    background: #F0F3FF;
}}
"""

_DARK_QSS_TEMPLATE = """
QMainWindow {{
    background: #1E1E2E;
}}
QWidget {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: {fs}px;
    color: #CDD6F4;
}}
QScrollArea {{
    background: #1E1E2E;
    border: none;
}}
QScrollArea > QWidget {{
    background: #1E1E2E;
}}
QSplitter {{
    background: #1E1E2E;
}}
QGroupBox {{
    border: 1px solid #3A3A50;
    border-radius: {radius_lg}px;
    margin-top: {group_margin_top}px;
    padding: {group_pad_t}px {group_pad_h}px {group_pad_b}px {group_pad_h}px;
    background: #252536;
    font-weight: bold;
    font-size: {fs}px;
    color: #BAC2DE;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: {title_pad_v}px {title_pad_h}px;
    background: #1E1E2E;
    border-radius: {radius_sm}px;
    color: #A6ADC8;
}}
QPushButton {{
    background: #2E2E40;
    border: 1px solid #454560;
    border-radius: {radius_md}px;
    padding: {btn_pad_v}px {btn_pad_h}px;
    color: #CDD6F4;
    font-size: {fs}px;
}}
QPushButton:hover {{
    background: #3A3A55;
    border-color: #89B4FA;
    color: #CDD6F4;
}}
QPushButton:pressed {{
    background: #2A2A3C;
    color: #CDD6F4;
}}
QListWidget {{
    background: #252536;
    border: 1px solid #3A3A50;
    border-radius: {radius_md}px;
    padding: {list_pad}px;
    outline: none;
    color: #CDD6F4;
}}
QListWidget::item {{
    border: none;
    padding: 0px;
    color: #CDD6F4;
}}
QListWidget::item:selected {{
    background: #454560;
    color: #CDD6F4;
}}
QListWidget::item:hover {{
    background: #3A3A55;
    color: #CDD6F4;
}}
QListWidget::item:selected:hover {{
    background: #585B70;
    color: #CDD6F4;
}}
QCheckBox {{
    spacing: {check_space}px;
    color: #BAC2DE;
}}
QCheckBox::indicator {{
    width: {check_size}px;
    height: {check_size}px;
    border: {check_border}px solid #585B70;
    border-radius: {radius_xxs}px;
    background: #313244;
}}
QCheckBox::indicator:checked {{
    background: #89B4FA;
    border-color: #89B4FA;
}}
QCheckBox::indicator:hover {{
    border-color: #89B4FA;
}}
QProgressBar {{
    border: 1px solid #454560;
    border-radius: {progress_radius}px;
    text-align: center;
    background: #313244;
    height: {progress_h}px;
    color: #CDD6F4;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #89B4FA, stop:1 #74C7EC);
    border-radius: {progress_chunk_radius}px;
}}
QLineEdit {{
    padding: {edit_pad_v}px {edit_pad_h}px;
    font-size: {fs}px;
    border: 1px solid #454560;
    border-radius: {radius_md}px;
    background: #313244;
    color: #CDD6F4;
}}
QLineEdit:focus {{
    border-color: #89B4FA;
}}
QComboBox {{
    background: #313244;
    border: 1px solid #454560;
    border-radius: {radius_md}px;
    padding: {combo_pad_v}px {combo_pad_h}px;
    min-width: {combo_min_w}px;
    color: #CDD6F4;
}}
QComboBox:hover, QComboBox:focus, QComboBox:on {{
    border-color: #89B4FA;
    color: #CDD6F4;
    background: #313244;
}}
QComboBox::drop-down {{
    border: none;
    background: transparent;
    padding-right: {combo_drop_pad}px;
}}
QComboBox QAbstractItemView {{
    background: #313244;
    border: 1px solid #454560;
    border-radius: {radius_sm}px;
    color: #CDD6F4;
    outline: none;
    selection-background-color: #454560;
    selection-color: #CDD6F4;
}}
QComboBox QAbstractItemView::item {{
    color: #CDD6F4;
    background: #313244;
    padding: {combo_pad_v}px {combo_pad_h}px;
}}
QComboBox QAbstractItemView::item:selected {{
    color: #CDD6F4;
    background: #454560;
}}
QComboBox QAbstractItemView::item:hover {{
    color: #CDD6F4;
    background: #3A3A55;
}}
QMenu {{
    background: #313244;
    color: #CDD6F4;
    border: 1px solid #454560;
}}
QMenu::item {{
    color: #CDD6F4;
    background: transparent;
    padding: {combo_pad_v}px {combo_pad_h}px;
}}
QMenu::item:selected {{
    color: #CDD6F4;
    background: #454560;
}}
QStatusBar {{
    background: #181825;
    border-top: 1px solid #3A3A50;
    color: #A6ADC8;
}}
QTableWidget {{
    background: #252536;
    border: 1px solid #3A3A50;
    border-radius: {radius_md}px;
    gridline-color: #3A3A50;
    color: #CDD6F4;
}}
QTableWidget::item {{
    color: #CDD6F4;
}}
QTableWidget::item:selected {{
    background: #454560;
    color: #CDD6F4;
}}
QTableWidget::item:hover {{
    background: #3A3A55;
    color: #CDD6F4;
}}
QHeaderView::section {{
    background: #313244;
    padding: {header_pad_v}px {header_pad_h}px;
    border: none;
    border-bottom: {header_border}px solid #454560;
    font-weight: bold;
    color: #BAC2DE;
}}
QFrame[frameShape="5"] {{
    background: #252536;
    border: 1px solid #3A3A50;
    border-radius: {radius_md}px;
}}
QSplitter::handle {{
    background: #3A3A50;
}}
QSplitter::handle:horizontal {{
    width: {splitter}px;
}}
QSplitter::handle:vertical {{
    height: {splitter}px;
}}
QSpinBox, QDoubleSpinBox {{
    border: 1px solid #454560;
    border-radius: {radius_sm}px;
    padding: {spin_pad_v}px {spin_pad_h}px;
    background: #313244;
    color: #CDD6F4;
}}
QScrollBar:vertical {{
    background: #1E1E2E;
    width: {scroll_w}px;
    border-radius: {scroll_radius}px;
}}
QScrollBar::handle:vertical {{
    background: #585B70;
    border-radius: {scroll_radius}px;
    min-height: {scroll_min_h}px;
}}
QScrollBar::handle:vertical:hover {{
    background: #6C7086;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QMessageBox {{
    background: #1E1E2E;
    color: #CDD6F4;
}}
QMessageBox QLabel {{
    color: #CDD6F4;
    font-size: {fs}px;
}}
QMessageBox QPushButton {{
    color: #CDD6F4;
    background: #2E2E40;
    border: 1px solid #454560;
    border-radius: {msg_btn_radius}px;
    padding: {msg_btn_pad_v}px {msg_btn_pad_h}px;
    min-width: {msg_btn_min_w}px;
}}
QMessageBox QPushButton:hover {{
    background: #3A3A55;
    border-color: #89B4FA;
    color: #CDD6F4;
}}
QDialog {{
    background: #1E1E2E;
    color: #CDD6F4;
}}
QDialog QLabel {{
    color: #CDD6F4;
    font-size: {fs}px;
}}
QDialog QRadioButton {{
    color: #CDD6F4;
}}
QDialog QCheckBox {{
    color: #CDD6F4;
}}
QDialog QGroupBox {{
    color: #BAC2DE;
    background: #252536;
    border: 1px solid #3A3A50;
}}
QDialog QGroupBox::title {{
    color: #BAC2DE;
    background: #1E1E2E;
}}
QDialog QTableWidget {{
    color: #CDD6F4;
    background: #252536;
    gridline-color: #3A3A50;
    border: 1px solid #3A3A50;
}}
QDialog QTableWidget::item {{
    color: #CDD6F4;
}}
QDialog QTableWidget::item:selected {{
    color: #CDD6F4;
    background: #454560;
}}
QDialog QTableWidget::item:hover {{
    color: #CDD6F4;
    background: #3A3A55;
}}
QDialog QHeaderView::section {{
    color: #BAC2DE;
    background: #313244;
    border: none;
    border-bottom: {header_border}px solid #454560;
}}
QDialog QComboBox {{
    color: #CDD6F4;
    background: #313244;
    border: 1px solid #454560;
}}
QDialog QComboBox:hover {{
    border-color: #89B4FA;
    color: #CDD6F4;
}}
QDialog QComboBox QAbstractItemView {{
    color: #CDD6F4;
    background: #313244;
    selection-background-color: #454560;
    selection-color: #CDD6F4;
    outline: none;
}}
QDialog QComboBox QAbstractItemView::item {{
    color: #CDD6F4;
    background: #313244;
}}
QDialog QComboBox QAbstractItemView::item:selected {{
    color: #CDD6F4;
    background: #454560;
}}
QDialog QComboBox QAbstractItemView::item:hover {{
    color: #CDD6F4;
    background: #3A3A55;
}}
QDialog QPushButton {{
    color: #CDD6F4;
    background: #2E2E40;
    border: 1px solid #454560;
}}
QDialog QPushButton:hover {{
    color: #CDD6F4;
    background: #3A3A55;
    border-color: #89B4FA;
}}
QDialog QPushButton:pressed {{
    color: #CDD6F4;
    background: #2A2A3C;
}}
QDialog QSpinBox, QDialog QDoubleSpinBox {{
    color: #CDD6F4;
    background: #313244;
    border: 1px solid #454560;
}}
QDialog QLineEdit {{
    color: #CDD6F4;
    background: #313244;
    border: 1px solid #454560;
}}
QDialog QListWidget {{
    color: #CDD6F4;
    background: #252536;
    border: 1px solid #3A3A50;
}}
QDialog QListWidget::item {{
    color: #CDD6F4;
}}
QDialog QListWidget::item:selected {{
    color: #CDD6F4;
    background: #454560;
}}
QDialog QListWidget::item:hover {{
    color: #CDD6F4;
    background: #3A3A55;
}}
QDialog QTextEdit {{
    color: #CDD6F4;
    background: #252536;
    border: 1px solid #3A3A50;
}}
QDialog QPlainTextEdit {{
    color: #CDD6F4;
    background: #252536;
    border: 1px solid #3A3A50;
}}
"""


def build_light_qss(scale: float = None) -> str:
    """按缩放因子生成浅色全局样式表。"""
    tokens: Dict[str, int] = ui_scale.qss_tokens(scale)
    return _LIGHT_QSS_TEMPLATE.format(**tokens)


def build_dark_qss(scale: float = None) -> str:
    """按缩放因子生成深色全局样式表。"""
    tokens: Dict[str, int] = ui_scale.qss_tokens(scale)
    return _DARK_QSS_TEMPLATE.format(**tokens)


def build_app_palette(is_dark: bool):
    """
    构建应用级 QPalette，避免 Windows 系统深色模式把未完全 QSS 覆盖的控件画成黑底。
    与浅/深 QSS 色板一致：Window / Base / Button / Text 成套设置。
    """
    from PyQt5.QtGui import QPalette, QColor

    palette = QPalette()
    if is_dark:
        window = QColor("#1E1E2E")
        base = QColor("#252536")
        alt_base = QColor("#313244")
        text = QColor("#CDD6F4")
        button = QColor("#2E2E40")
        highlight = QColor("#454560")
        highlighted_text = QColor("#CDD6F4")
        mid = QColor("#3A3A50")
    else:
        window = QColor("#F5F6FA")
        base = QColor("#FFFFFF")
        alt_base = QColor("#F0F2F5")
        text = QColor("#333333")
        button = QColor("#FFFFFF")
        highlight = QColor("#E8F0FE")
        highlighted_text = QColor("#1A1A1A")
        mid = QColor("#D0D5DD")

    palette.setColor(QPalette.Window, window)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, alt_base)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, button)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.ToolTipBase, base)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, highlighted_text)
    palette.setColor(QPalette.PlaceholderText, mid)
    palette.setColor(QPalette.Light, alt_base)
    palette.setColor(QPalette.Mid, mid)
    palette.setColor(QPalette.Dark, mid)
    return palette
