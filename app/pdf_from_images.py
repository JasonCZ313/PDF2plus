# -*- coding: utf-8 -*-
"""
图片转 PDF：多图按顺序生成离线 PDF。

统一经 Pillow 解码并写入内存流，再交给 PyMuPDF 嵌入，
以兼容 WebP 等 MuPDF 无法直接打开的格式。
"""
from __future__ import annotations

import io
import os
from typing import Callable, List, Optional, Tuple

import fitz
from PIL import Image


# A4 点阵尺寸（72 DPI 下的 PDF 点）
A4_WIDTH_PT = 595.0
A4_HEIGHT_PT = 842.0


def _pil_to_embed_stream(pil_image: Image.Image) -> Tuple[bytes, int, int]:
    """
    将 Pillow 图像转为可嵌入 PDF 的字节流。

    带透明通道用 PNG；其余转 RGB 后用高质量 JPEG，兼顾清晰度与体积。
    :return: (stream_bytes, pixel_width, pixel_height)
    """
    has_alpha = pil_image.mode in ("RGBA", "LA") or (
        pil_image.mode == "P" and "transparency" in pil_image.info
    )
    pixel_width, pixel_height = pil_image.size
    buffer = io.BytesIO()
    if has_alpha:
        # 保留透明：铺白底再存 PNG，避免部分阅读器对 alpha 异常
        rgba = pil_image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        background.save(buffer, format="PNG", optimize=True)
        pixel_width, pixel_height = background.size
    else:
        rgb = pil_image.convert("RGB") if pil_image.mode != "RGB" else pil_image
        rgb.save(buffer, format="JPEG", quality=92, optimize=True)
        pixel_width, pixel_height = rgb.size
    return buffer.getvalue(), pixel_width, pixel_height


def images_to_pdf(
    image_paths: List[str],
    output_path: str,
    page_mode: str = "a4_fit",
    margin_pt: float = 24.0,
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    **kwargs,
) -> bool:
    """
    将多张图片按顺序写入一个 PDF。

    :param page_mode: a4_fit=放入 A4；original=按像素以 72dpi 映射页面
    :param margin_pt: a4_fit 时页边距（点）
    :return: 至少成功写入一页则为 True；取消或全部失败为 False
    """
    if not image_paths:
        return False

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    result_doc = fitz.open()
    total = len(image_paths)
    try:
        for index, image_path in enumerate(image_paths):
            if cancel_check and cancel_check():
                result_doc.close()
                if os.path.isfile(output_path):
                    try:
                        os.remove(output_path)
                    except OSError:
                        pass
                return False
            if not os.path.isfile(image_path):
                continue

            try:
                with Image.open(image_path) as pil_image:
                    # 处理多帧（如 GIF）时只取首帧，避免意外拉长文档
                    pil_image.load()
                    stream_bytes, pixel_width, pixel_height = _pil_to_embed_stream(pil_image)
            except Exception:
                # 单张坏图跳过，不拖垮整批
                continue

            use_landscape = page_mode == "a4_fit" and pixel_width > pixel_height

            if page_mode == "original":
                page_width = float(pixel_width)
                page_height = float(pixel_height)
                page = result_doc.new_page(width=page_width, height=page_height)
                page.insert_image(page.rect, stream=stream_bytes)
            else:
                if use_landscape:
                    page_width, page_height = A4_HEIGHT_PT, A4_WIDTH_PT
                else:
                    page_width, page_height = A4_WIDTH_PT, A4_HEIGHT_PT
                page = result_doc.new_page(width=page_width, height=page_height)
                content_width = max(1.0, page_width - 2 * margin_pt)
                content_height = max(1.0, page_height - 2 * margin_pt)
                scale = min(content_width / pixel_width, content_height / pixel_height)
                draw_width = pixel_width * scale
                draw_height = pixel_height * scale
                left = (page_width - draw_width) / 2.0
                top = (page_height - draw_height) / 2.0
                rect = fitz.Rect(left, top, left + draw_width, top + draw_height)
                page.insert_image(rect, stream=stream_bytes)

            if progress_callback:
                progress_callback(int((index + 1) / total * 100))

        if cancel_check and cancel_check():
            result_doc.close()
            return False
        if len(result_doc) == 0:
            result_doc.close()
            return False
        result_doc.save(output_path, garbage=4, deflate=True)
        result_doc.close()
        return True
    except Exception:
        try:
            result_doc.close()
        except Exception:
            pass
        return False
