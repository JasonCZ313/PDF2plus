# -*- coding: utf-8 -*-
"""PDF 无损拆分模块（支持可选打开密码，默认空则与旧行为一致）"""
import fitz
import os
from typing import List, Optional, Callable, Tuple

from app.pdf_security import open_pdf
from app.i18n import t


def _cleanup_written_files(file_paths: List[str]) -> None:
    """取消任务时删除本轮已写入的半成品，避免输出目录残留。"""
    for file_path in file_paths:
        try:
            if file_path and os.path.isfile(file_path):
                os.remove(file_path)
        except OSError:
            pass


def _normalize_page_range(start, end, total_pages: int) -> Optional[Tuple[int, int]]:
    """
    将自定义页范围规范为合法的 0-based 闭区间。

    非法（越界、颠倒、无法解析、空文档）返回 None，不做静默夹紧，
    避免越界被悄悄改成末页而掩盖错误输入。
    """
    if total_pages <= 0:
        return None
    try:
        start_index = int(start)
        end_index = int(end)
    except (TypeError, ValueError):
        return None
    if start_index < 0 or end_index < 0:
        return None
    if start_index >= total_pages or end_index >= total_pages:
        return None
    if start_index > end_index:
        return None
    return start_index, end_index


def split_pdf_by_pages(
    pdf_path: str,
    output_dir: str,
    pages_per_chunk: int = 1,
    progress_callback: Optional[Callable[[int], None]] = None,
    **kwargs
) -> List[str]:
    """
    将 PDF 按指定页数拆分成多个文件

    :param kwargs: 可含 cancel_check、password（打开源文件密码）
    :return: 生成的文件路径列表；取消时清理半成品并返回空列表
    """
    cancel_check = kwargs.get("cancel_check")
    password = kwargs.get("password", "") or ""
    output_files: List[str] = []
    try:
        os.makedirs(output_dir, exist_ok=True)
        pdf = open_pdf(pdf_path, password)
        try:
            total_pages = len(pdf)
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]

            chunks = []
            for start in range(0, total_pages, pages_per_chunk):
                end = min(start + pages_per_chunk - 1, total_pages - 1)
                chunks.append((start, end))

            for idx, (start, end) in enumerate(chunks):
                if cancel_check and cancel_check():
                    _cleanup_written_files(output_files)
                    return []
                new_pdf = fitz.open()
                new_pdf.insert_pdf(pdf, from_page=start, to_page=end)
                # 文件名随当前界面语言（中文「第N部分」/ 英文 partN）
                output_name = t(
                    "out.split_by_pages",
                    base=base_name,
                    index=idx + 1,
                    start=start + 1,
                    end=end + 1,
                )
                output_path = os.path.join(output_dir, output_name)
                new_pdf.save(output_path, garbage=4, deflate=True)
                new_pdf.close()
                output_files.append(output_path)
                if progress_callback:
                    progress_callback(int((idx + 1) / len(chunks) * 100))
        finally:
            pdf.close()

        return output_files
    except Exception:
        _cleanup_written_files(output_files)
        return []


def split_pdf_by_ranges(
    pdf_path: str,
    output_dir: str,
    page_ranges: list,
    progress_callback=None,
    cancel_check=None,
    password: str = "",
    **kwargs,
) -> list:
    """
    按自定义页范围拆分 PDF（0-based 闭区间）。

    非法范围跳过；全部非法或取消时返回空列表并清理半成品。
    :param password: 打开源文件密码；也可经 kwargs 传入
    """
    if kwargs.get("password"):
        password = kwargs.get("password") or password
    output_files = []
    try:
        os.makedirs(output_dir, exist_ok=True)
        pdf = open_pdf(pdf_path, password or "")
        try:
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            total_pages = len(pdf)
            # 先筛合法段，避免越界仍写出怪异单页文件
            valid_ranges = []
            for raw_start, raw_end in page_ranges or []:
                normalized = _normalize_page_range(raw_start, raw_end, total_pages)
                if normalized is not None:
                    valid_ranges.append(normalized)
            if not valid_ranges:
                return []

            total = len(valid_ranges)
            for idx, (start, end) in enumerate(valid_ranges):
                if cancel_check and cancel_check():
                    _cleanup_written_files(output_files)
                    return []
                new_pdf = fitz.open()
                new_pdf.insert_pdf(pdf, from_page=start, to_page=end)
                output_name = t(
                    "out.split_by_range",
                    base=base_name,
                    index=idx + 1,
                    start=start + 1,
                    end=end + 1,
                )
                output_path = os.path.join(output_dir, output_name)
                new_pdf.save(output_path, garbage=4, deflate=True)
                new_pdf.close()
                output_files.append(output_path)
                if progress_callback:
                    progress_callback(int((idx + 1) / total * 100))
        finally:
            pdf.close()

        return output_files
    except Exception:
        _cleanup_written_files(output_files)
        return []


def split_pdf_by_copies(
    pdf_path: str,
    output_dir: str,
    copies: int,
    progress_callback: Optional[Callable[[int], None]] = None,
    **kwargs
) -> List[str]:
    """
    将 PDF 平均拆分成指定份数

    :param copies: 要拆成的份数
    :param kwargs: 可含 cancel_check、password
    :return: 生成的文件路径列表；取消时清理半成品并返回空列表
    """
    cancel_check = kwargs.get("cancel_check")
    password = kwargs.get("password", "") or ""
    output_files: List[str] = []
    try:
        os.makedirs(output_dir, exist_ok=True)
        pdf = open_pdf(pdf_path, password)
        try:
            total_pages = len(pdf)
            if copies <= 0 or copies > total_pages:
                return []

            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            pages_per_copy = total_pages // copies
            remainder = total_pages % copies

            chunks = []
            current = 0
            for i in range(copies):
                extra = 1 if i < remainder else 0
                end = current + pages_per_copy + extra - 1
                chunks.append((current, end))
                current = end + 1

            for idx, (start, end) in enumerate(chunks):
                if cancel_check and cancel_check():
                    _cleanup_written_files(output_files)
                    return []
                new_pdf = fitz.open()
                new_pdf.insert_pdf(pdf, from_page=start, to_page=end)
                output_name = t(
                    "out.split_by_range",
                    base=base_name,
                    index=idx + 1,
                    start=start + 1,
                    end=end + 1,
                )
                output_path = os.path.join(output_dir, output_name)
                new_pdf.save(output_path, garbage=4, deflate=True)
                new_pdf.close()
                output_files.append(output_path)
                if progress_callback:
                    progress_callback(int((idx + 1) / copies * 100))
        finally:
            pdf.close()

        return output_files
    except Exception:
        _cleanup_written_files(output_files)
        return []
