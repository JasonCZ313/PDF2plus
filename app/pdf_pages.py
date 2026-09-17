# -*- coding: utf-8 -*-
"""
PDF 页面管理核心：删除、旋转、提取、重排。
"""
from __future__ import annotations

import os
from typing import Callable, List, Optional, Sequence

import fitz

from app.pdf_security import open_pdf


def get_page_count(pdf_path: str, password: str = "") -> int:
    """读取页数（支持密码）。"""
    document = open_pdf(pdf_path, password)
    try:
        return len(document)
    finally:
        document.close()


def render_page_thumbnail(
    pdf_path: str,
    page_index: int,
    password: str = "",
    max_edge: int = 160,
    rotation: int = 0,
) -> bytes:
    """
    渲染单页缩略图/预览图，返回 PNG 字节。

    :param page_index: 0-based
    :param rotation: 额外旋转角度（0/90/180/270），与页面管理预览一致
    """
    document = open_pdf(pdf_path, password)
    try:
        page = document[page_index]
        scale = max_edge / max(page.rect.width, page.rect.height)
        matrix = fitz.Matrix(scale, scale)
        rotate_delta = int(rotation) % 360
        if rotate_delta:
            matrix = matrix * fitz.Matrix(rotate_delta)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("png")
    finally:
        document.close()


def render_page_preview(
    pdf_path: str,
    page_index: int,
    password: str = "",
    max_edge: int = 900,
    rotation: int = 0,
) -> bytes:
    """离线大图预览：更高清晰度，仍完全本地渲染。"""
    return render_page_thumbnail(
        pdf_path,
        page_index,
        password=password,
        max_edge=max_edge,
        rotation=rotation,
    )

def apply_page_edits(
    pdf_path: str,
    output_path: str,
    keep_order: Sequence[int],
    rotations: Optional[dict] = None,
    password: str = "",
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    **kwargs,
) -> bool:
    """
    按新的页面顺序生成 PDF；可附带每页旋转增量。

    :param keep_order: 源页 0-based 序号列表（可含重复表示复制页）
    :param rotations: {源页index: 旋转角度增量}，角度为 0/90/180/270
    """
    if not keep_order:
        return False
    rotations = rotations or {}
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    source = open_pdf(pdf_path, password)
    result = fitz.open()
    try:
        total = len(keep_order)
        for out_index, source_index in enumerate(keep_order):
            if cancel_check and cancel_check():
                result.close()
                return False
            if source_index < 0 or source_index >= len(source):
                continue
            result.insert_pdf(source, from_page=source_index, to_page=source_index)
            rotate_delta = int(rotations.get(source_index, 0)) % 360
            if rotate_delta:
                page = result[-1]
                page.set_rotation((page.rotation + rotate_delta) % 360)
            if progress_callback:
                progress_callback(int((out_index + 1) / total * 100))
        if len(result) == 0:
            result.close()
            return False
        if cancel_check and cancel_check():
            result.close()
            return False
        result.save(output_path, garbage=4, deflate=True)
        result.close()
        return True
    except Exception:
        try:
            result.close()
        except Exception:
            pass
        return False
    finally:
        source.close()


def extract_pages(
    pdf_path: str,
    output_path: str,
    page_indices: Sequence[int],
    password: str = "",
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    **kwargs,
) -> bool:
    """提取指定页面为新 PDF（保持给定顺序）。"""
    return apply_page_edits(
        pdf_path,
        output_path,
        keep_order=list(page_indices),
        password=password,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
