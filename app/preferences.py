"""用户偏好设置模块（完全离线，无需联网）"""
import os
import json
import sys


def _get_data_dir():
    """获取 data/ 目录（开发 / onedir+启动器 分发通用）。

    正式布局：
      安装根/PDF2plus.exe
      安装根/runtime/PDF主程序.exe
      安装根/data/
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        parent_dir = os.path.dirname(exe_dir)
        parent_data = os.path.join(parent_dir, "data")

        # 主程序在 runtime/ 时，data 与启动器同级
        if os.path.basename(exe_dir).lower() == "runtime":
            return parent_data

        if os.path.basename(exe_dir).lower() == "dist" and os.path.isdir(parent_data):
            return parent_data

        return os.path.join(exe_dir, "data")
    else:
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data"
        )


def _ensure_data_dir():
    """确保 data/ 目录及其子目录存在"""
    d = _get_data_dir()
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(d, "workspace"), exist_ok=True)
    os.makedirs(os.path.join(d, "history"), exist_ok=True)
    return d


DATA_DIR = _ensure_data_dir()
PREFS_FILE = os.path.join(DATA_DIR, "preferences.json")

# 默认值
_DEFAULTS = {
    "copy_original_pdf_on_convert": False,  # 转换时保留原始PDF（总开关）
    "default_save_path": "",                # 默认保存路径（空=桌面）
    "remember_save_path": True,             # 是否记住默认保存路径
    "last_working_folder": "",
    "last_output_dir": "",
    "image_format": "png",
    "image_dpi": "300 (高清)",
    "theme": "light",                       # 主题: "light" 或 "dark"
    # 界面语言: zh=中文（默认）/ en=英文
    "ui_language": "zh",
    # 界面字号档位: default / large / xlarge
    "ui_font_size": "default",
    # 水印对话框：记住上次文字颜色(RGB0~1列表)与透明度
    "stamp_text_color": [0.85, 0.12, 0.12],
    "stamp_text_opacity": 0.45,
    # 页码距页边（毫米）
    "stamp_page_margin_mm": 10.0,
    "stamp_page_unit": "mm",
    "stamp_page_left_pt": 262.5,
    "stamp_page_edge_pt": 28.35,
    "stamp_page_box_width_pt": 70.0,
    "stamp_page_box_height_pt": 20.0,
    "stamp_page_font_size": 11.0,
}


def _load():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 合并默认值，确保新增的 key 有默认值
            merged = dict(_DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(data):
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# 全局缓存
_cache = _load()


def get(key, default=None):
    val = _cache.get(key, _DEFAULTS.get(key, default))
    return val if val is not None else default


def set(key, value):
    _cache[key] = value
    _save(_cache)


def get_all():
    return dict(_cache)


def get_data_dir():
    """返回 data/ 目录路径"""
    return DATA_DIR


def get_workspace():
    """返回工作空间目录（data/workspace/）"""
    return os.path.join(DATA_DIR, "workspace")
