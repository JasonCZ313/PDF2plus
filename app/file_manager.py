"""文件管理模块（v2.1 — 隐藏工作空间）"""
import os
import shutil
import json
from typing import List, Set


def get_workspace() -> str:
    """获取隐藏工作空间目录（data/workspace/），自动创建"""
    from app.preferences import get_workspace as _gw
    ws = _gw()
    os.makedirs(ws, exist_ok=True)
    return ws


def select_folder(parent=None) -> str:
    """弹出文件夹选择对话框，返回所选路径（标题随当前界面语言）"""
    from PyQt5.QtWidgets import QFileDialog
    from app.i18n import t
    folder = QFileDialog.getExistingDirectory(parent, t("file.select_folder"))
    return folder if folder else ""


def _unique_dest_path(dest_folder: str, file_name: str) -> str:
    """
    在目标目录内生成不冲突的文件路径。

    命名规则与界面转 Word 的重名处理一致：
    原名.pdf → 原名_1.pdf → 原名_2.pdf …
    Windows 下 exists 本身大小写不敏感，可避免 MixCase.PDF / mixcase.pdf 互相覆盖。
    """
    stem_name, extension = os.path.splitext(file_name)
    candidate_path = os.path.join(dest_folder, file_name)
    if not os.path.exists(candidate_path):
        return candidate_path
    suffix_index = 1
    while True:
        candidate_name = f"{stem_name}_{suffix_index}{extension}"
        candidate_path = os.path.join(dest_folder, candidate_name)
        if not os.path.exists(candidate_path):
            return candidate_path
        suffix_index += 1


def import_pdfs_to_folder(files: List[str], dest_folder: str = None) -> List[str]:
    """
    将选中的 PDF 复制到工作空间，返回新路径列表。

    - 同一次导入中相同源路径只拷贝一次（按 normpath 去重，保持首次出现顺序）
    - 目标目录已有同名文件时自动改名，绝不覆盖已有工作区文件
    """
    if dest_folder is None:
        dest_folder = get_workspace()
    os.makedirs(dest_folder, exist_ok=True)

    imported: List[str] = []
    seen_source_paths: Set[str] = set()

    for source_path in files:
        if not source_path:
            continue
        normalized_source = os.path.normpath(source_path)
        # 同一源路径重复出现时跳过，避免无意义的双份拷贝
        if normalized_source in seen_source_paths:
            continue
        seen_source_paths.add(normalized_source)
        if not os.path.isfile(normalized_source):
            continue

        destination_path = _unique_dest_path(
            dest_folder, os.path.basename(normalized_source)
        )
        # 源已在工作区内且路径就是唯一名时，不必再拷（极少见，防御性处理）
        if os.path.normpath(normalized_source) != os.path.normpath(destination_path):
            shutil.copy2(normalized_source, destination_path)
        imported.append(destination_path)

    # 新文件追加到顺序末尾
    order = load_order(dest_folder)
    existing = {os.path.normpath(p) for p in order}
    for imported_path in imported:
        normalized_imported = os.path.normpath(imported_path)
        if normalized_imported not in existing:
            order.append(normalized_imported)
            existing.add(normalized_imported)
    save_order(dest_folder, order)
    return imported


def list_pdfs(folder: str = None) -> List[str]:
    """列出文件夹内所有 PDF 文件，优先按保存的顺序排列"""
    if folder is None:
        folder = get_workspace()
    if not folder or not os.path.isdir(folder):
        return []

    pdf_map = {}
    for f in os.listdir(folder):
        if f.lower().endswith(".pdf"):
            full = os.path.normpath(os.path.join(folder, f))
            pdf_map[full] = os.path.getctime(full)

    # 加载保存的顺序
    order = load_order(folder)
    ordered = []
    seen = set()
    for p in order:
        norm = os.path.normpath(p)
        if norm in pdf_map and norm not in seen:
            ordered.append(norm)
            seen.add(norm)

    # 新文件（不在已保存顺序中）按创建时间追加
    remaining = sorted(
        [p for p in pdf_map if p not in seen],
        key=lambda x: pdf_map[x]
    )
    ordered.extend(remaining)

    return ordered


def save_order(folder: str = None, order: List[str] = None):
    """将文件列表顺序持久化到 .pdf_order.json"""
    from app.config import ORDER_FILE_NAME
    if folder is None:
        folder = get_workspace()
    order_path = os.path.join(folder, ORDER_FILE_NAME)
    try:
        with open(order_path, "w", encoding="utf-8") as f:
            json.dump(order, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_order(folder: str = None) -> List[str]:
    """从 .pdf_order.json 加载已保存的文件顺序"""
    from app.config import ORDER_FILE_NAME
    if folder is None:
        folder = get_workspace()
    order_path = os.path.join(folder, ORDER_FILE_NAME)
    if os.path.exists(order_path):
        try:
            with open(order_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def delete_file(file_path: str) -> bool:
    """删除工作空间中的文件（绝不删除用户原始文件）"""
    try:
        os.remove(file_path)
        return True
    except Exception:
        return False


def get_pdf_page_count(pdf_path: str) -> int:
    """获取 PDF 文件的总页数"""
    import fitz
    try:
        with fitz.open(pdf_path) as pdf:
            return len(pdf)
    except Exception:
        return 0


def choose_save_path(parent=None, default_name: str = None,
                     default_dir: str = "") -> str:
    """
    弹出保存文件对话框，优先使用默认保存路径。

    default_name 为空时按当前语言使用「合并后的文件.pdf」/ merged.pdf。
    """
    from PyQt5.QtWidgets import QFileDialog
    from app.i18n import t
    resolved_name = default_name if default_name else t("file.merge_default")
    path, _ = QFileDialog.getSaveFileName(
        parent,
        t("file.save_title"),
        os.path.join(default_dir, resolved_name) if default_dir else resolved_name,
        t("file.filter_pdf_save"),
    )
    return path if path else ""


def get_default_save_path() -> str:
    """获取有效的默认保存路径（优先用户设置，否则桌面）"""
    from app.preferences import get as pref_get
    saved = pref_get("default_save_path", "")
    if saved and os.path.isdir(saved):
        return saved
    # 回退到桌面
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desktop):
        return desktop
    return os.path.expanduser("~")


def is_valid_path(path: str) -> bool:
    """检查路径是否有效（存在且是目录）"""
    return bool(path) and os.path.isdir(path)
