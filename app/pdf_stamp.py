# -*- coding: utf-8 -*-
"""
PDF 水印与页码：在页面上叠加文字/图片水印与页码，不依赖联网。

文字用水印走 insert_text（无裁剪框），避免 insert_textbox 装不下就整段不画。
图片水印用 Pillow 把透明度写入 PNG alpha 后再嵌入，避免 set_alpha(整数) 无效。
"""
from __future__ import annotations

import io
import os
from typing import Callable, List, Optional, Tuple

import fitz
from PIL import Image

from app.pdf_security import open_pdf


# 页码位置：相对页边距
_PAGE_NUMBER_POSITIONS = {
    "bottom_center": (0.5, 1.0),
    "bottom_left": (0.0, 1.0),
    "bottom_right": (1.0, 1.0),
    "top_center": (0.5, 0.0),
    "top_left": (0.0, 0.0),
    "top_right": (1.0, 0.0),
}

# 嵌入 PDF 时使用的内部字体名，避免与内置 china-s 冲突导致写不进去
_WATERMARK_FONTNAME = "wm-cn"


def _resolve_chinese_fontfile() -> Optional[str]:
    """查找系统中文字体，保证水印/页码中文可显示。"""
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttf",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _clamp_opacity(opacity: float) -> float:
    """把透明度限制在 (0, 1]，保证半透明可见且不会变成全透明。"""
    return max(0.05, min(1.0, float(opacity)))


def _measure_text_width(text: str, font_size: float, fontfile: Optional[str]) -> float:
    """测算水印文字宽度，用于把基线点对齐到格子中心。"""
    try:
        if fontfile:
            font = fitz.Font(fontfile=fontfile)
            return float(font.text_length(text, fontsize=font_size))
    except Exception:
        pass
    return float(font_size) * max(1, len(text)) * 0.62


def _tile_centers(rect: fitz.Rect, step_x: float, step_y: float) -> List[Tuple[float, float]]:
    """在页面内生成平铺中心点，保证四边也有水印而不是只挤在正中。"""
    centers = []
    start_x = rect.x0 + step_x / 2
    start_y = rect.y0 + step_y / 2
    y = start_y
    while y < rect.y1:
        x = start_x
        while x < rect.x1:
            centers.append((x, y))
            x += step_x
        y += step_y
    if not centers:
        centers.append((rect.x0 + rect.width / 2, rect.y0 + rect.height / 2))
    return centers


def stamp_pdf(
    pdf_path: str,
    output_path: str,
    password: str = "",
    # 文字水印
    text_watermark: str = "",
    text_font_size: float = 48.0,
    text_rotate: float = 45.0,
    text_opacity: float = 0.45,
    text_color: Tuple[float, float, float] = (0.85, 0.12, 0.12),
    text_tile: bool = True,
    # 图片水印
    image_watermark_path: str = "",
    image_scale: float = 0.22,
    image_opacity: float = 0.35,
    image_tile: bool = False,
    # 图层：True=叠在内容上（默认，才能看见）；False=衬在内容下
    watermark_overlay: bool = True,
    # 页码；模板空则按当前界面语言取 stamp.page_template
    add_page_number: bool = False,
    page_number_template: str = "",
    page_number_position: str = "bottom_center",
    page_number_font_size: float = 11.0,
    page_number_margin_mm: float = 10.0,
    page_number_offset_left_pt: Optional[float] = None,
    page_number_offset_edge_pt: Optional[float] = None,
    page_number_box_width_pt: Optional[float] = None,
    page_number_box_height_pt: Optional[float] = None,
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    **kwargs,
) -> bool:
    """
    叠加水印与/或页码后另存。

    至少启用文字水印、图片水印、页码之一。
    任一步写入失败则返回 False，不再假装成功。
    """
    has_text = bool(text_watermark and text_watermark.strip())
    has_image = bool(image_watermark_path and os.path.isfile(image_watermark_path))
    if not has_text and not has_image and not add_page_number:
        return False

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    image_png_bytes = None
    image_pixel_size = None
    if has_image:
        image_png_bytes, image_pixel_size = _prepare_image_watermark_png(
            image_watermark_path, image_opacity
        )
        if not image_png_bytes or not image_pixel_size:
            return False

    document = open_pdf(pdf_path, password)
    fontfile = _resolve_chinese_fontfile()
    total_pages = len(document)
    try:
        for page_index in range(total_pages):
            if cancel_check and cancel_check():
                return False
            page = document[page_index]
            if has_text:
                wrote_text = _draw_text_watermark(
                    page,
                    text_watermark.strip(),
                    text_font_size,
                    text_rotate,
                    text_opacity,
                    text_color,
                    text_tile,
                    fontfile,
                    watermark_overlay,
                )
                if not wrote_text:
                    return False
            if has_image:
                wrote_image = _draw_image_watermark(
                    page,
                    image_png_bytes,
                    image_pixel_size,
                    image_scale,
                    image_tile,
                    watermark_overlay,
                )
                if not wrote_image:
                    return False
            if add_page_number:
                from app.i18n import t
                # 显式传入的模板优先；否则跟随当前 UI 语言
                resolved_template = (page_number_template or "").strip() or t(
                    "stamp.page_template"
                )
                _draw_page_number(
                    page,
                    page_index + 1,
                    total_pages,
                    resolved_template,
                    page_number_position,
                    page_number_font_size,
                    fontfile,
                    page_number_margin_mm,
                    offset_left_pt=page_number_offset_left_pt,
                    offset_edge_pt=page_number_offset_edge_pt,
                    box_width_pt=page_number_box_width_pt,
                    box_height_pt=page_number_box_height_pt,
                )
            if progress_callback:
                progress_callback(int((page_index + 1) / total_pages * 90))

        if cancel_check and cancel_check():
            return False
        document.save(output_path, garbage=4, deflate=True)
        if progress_callback:
            progress_callback(100)
        return True
    except Exception:
        return False
    finally:
        document.close()


def _draw_text_watermark(
    page,
    text: str,
    font_size: float,
    rotate_deg: float,
    opacity: float,
    color: Tuple[float, float, float],
    tile: bool,
    fontfile: Optional[str],
    overlay: bool,
) -> bool:
    """
    用 insert_text 写文字水印：无裁剪框，半透明由 fill_opacity 生效。

    返回是否至少成功写入一处。
    """
    rect = page.rect
    fill_color = (float(color[0]), float(color[1]), float(color[2]))
    clamped_opacity = _clamp_opacity(opacity)
    text_width = _measure_text_width(text, font_size, fontfile)
    if tile:
        step_x = max(text_width * 1.55, font_size * 4.0)
        step_y = max(font_size * 3.2, 140.0)
        centers = _tile_centers(rect, step_x, step_y)
    else:
        centers = [(rect.x0 + rect.width / 2, rect.y0 + rect.height / 2)]

    wrote_any = False
    for center_x, center_y in centers:
        # 基线起点：文字视觉中心对准格子中心
        origin = fitz.Point(center_x - text_width / 2.0, center_y + font_size * 0.32)
        morph = None
        if abs(rotate_deg) > 0.1:
            # 绕该格子中心旋转，斜向铺满时每条都是独立斜章
            morph = (fitz.Point(center_x, center_y), fitz.Matrix(rotate_deg))
        if _insert_watermark_text(
            page, origin, text, font_size, fill_color, clamped_opacity, fontfile, morph, overlay
        ):
            wrote_any = True
    return wrote_any


def _insert_watermark_text(
    page,
    origin: fitz.Point,
    text: str,
    font_size: float,
    color: Tuple[float, float, float],
    opacity: float,
    fontfile: Optional[str],
    morph,
    overlay: bool,
) -> bool:
    """向页面写入一处文字水印；中文字体失败时再退回无字体参数。"""
    kwargs = {
        "fontsize": font_size,
        "color": color,
        "fill_opacity": opacity,
        "stroke_opacity": opacity,
        "overlay": overlay,
        "render_mode": 0,
    }
    if morph:
        kwargs["morph"] = morph
    if fontfile:
        kwargs["fontfile"] = fontfile
        kwargs["fontname"] = _WATERMARK_FONTNAME
    try:
        page.insert_text(origin, text, **kwargs)
        return True
    except TypeError:
        # 极旧参数集：去掉透明度仍尝试写出，避免整段功能瘫痪
        kwargs.pop("fill_opacity", None)
        kwargs.pop("stroke_opacity", None)
        try:
            page.insert_text(origin, text, **kwargs)
            return True
        except Exception:
            return False
    except Exception:
        if "fontfile" not in kwargs:
            return False
        kwargs.pop("fontfile", None)
        kwargs.pop("fontname", None)
        try:
            page.insert_text(origin, text, **kwargs)
            return True
        except Exception:
            return False


def _prepare_image_watermark_png(
    image_path: str, opacity: float
) -> Tuple[Optional[bytes], Optional[Tuple[int, int]]]:
    """
    用 Pillow 打开图片，把用户透明度乘进 alpha 通道，输出 PNG 字节。

    这样 insert_image 才能真正半透明；PyMuPDF 的 alpha 参数已被忽略。
    """
    clamped_opacity = _clamp_opacity(opacity)
    try:
        with Image.open(image_path) as pil_image:
            rgba = pil_image.convert("RGBA")
            red, green, blue, alpha = rgba.split()
            faded_alpha = alpha.point(
                lambda pixel_value: int(pixel_value * clamped_opacity)
            )
            rgba.putalpha(faded_alpha)
            pixel_size = (rgba.width, rgba.height)
            buffer = io.BytesIO()
            rgba.save(buffer, format="PNG")
            return buffer.getvalue(), pixel_size
    except Exception:
        return None, None


def _draw_image_watermark(
    page,
    image_png_bytes: bytes,
    image_pixel_size: Tuple[int, int],
    scale: float,
    tile: bool,
    overlay: bool,
) -> bool:
    """按比例把半透明 PNG 水印放到页面上（居中或平铺）。"""
    rect = page.rect
    pixel_width, pixel_height = image_pixel_size
    clamped_scale = max(0.05, min(float(scale), 1.0))
    target_width = rect.width * clamped_scale
    ratio = target_width / max(pixel_width, 1)
    target_height = pixel_height * ratio
    if tile:
        step_x = max(target_width * 1.35, 120.0)
        step_y = max(target_height * 1.35, 120.0)
        centers = _tile_centers(rect, step_x, step_y)
    else:
        centers = [(rect.x0 + rect.width / 2, rect.y0 + rect.height / 2)]

    wrote_any = False
    for center_x, center_y in centers:
        left = center_x - target_width / 2.0
        top = center_y - target_height / 2.0
        target = fitz.Rect(left, top, left + target_width, top + target_height)
        try:
            page.insert_image(
                target,
                stream=image_png_bytes,
                overlay=overlay,
                keep_proportion=True,
            )
            wrote_any = True
        except Exception:
            return False
    return wrote_any


# 1 英寸 = 25.4mm = 72pt；像素按 96DPI，与屏幕预览对齐
_PT_PER_INCH = 72.0
_MM_PER_INCH = 25.4
_PX_PER_INCH = 96.0


def mm_to_pt(millimeters: float) -> float:
    """毫米转 PDF 点。"""
    return float(millimeters) * _PT_PER_INCH / _MM_PER_INCH


def px_to_pt(pixels: float) -> float:
    """屏幕像素（96DPI）转 PDF 点。"""
    return float(pixels) * _PT_PER_INCH / _PX_PER_INCH


def pt_to_mm(points: float) -> float:
    """PDF 点转毫米。"""
    return float(points) * _MM_PER_INCH / _PT_PER_INCH


def pt_to_px(points: float) -> float:
    """PDF 点转屏幕像素（96DPI）。"""
    return float(points) * _PX_PER_INCH / _PT_PER_INCH


def _mm_to_pdf_points(margin_mm: float) -> float:
    """毫米转 PDF 点（兼容旧调用名）。"""
    return mm_to_pt(margin_mm)


def get_first_page_size_pt(pdf_path: str, password: str = "") -> Tuple[float, float]:
    """读取首页宽高（PDF 点），失败则按 A4 竖版回落。"""
    try:
        document = open_pdf(pdf_path, password)
        try:
            rect = document[0].rect
            return float(rect.width), float(rect.height)
        finally:
            document.close()
    except Exception:
        return 595.0, 842.0


def render_stamp_preview_png(
    pdf_path: str,
    password: str,
    page_index: int,
    max_edge: int,
    *,
    text_watermark: str = "",
    text_font_size: float = 48.0,
    text_rotate: float = 45.0,
    text_opacity: float = 0.45,
    text_color: Tuple[float, float, float] = (0.85, 0.12, 0.12),
    text_tile: bool = True,
    image_watermark_path: str = "",
    image_scale: float = 0.22,
    image_opacity: float = 0.35,
    image_tile: bool = False,
    watermark_overlay: bool = True,
    add_page_number: bool = False,
    page_number_template: str = "",
    page_number_position: str = "bottom_center",
    page_number_font_size: float = 11.0,
    page_number_margin_mm: float = 10.0,
    page_number_offset_left_pt: Optional[float] = None,
    page_number_offset_edge_pt: Optional[float] = None,
    page_number_box_width_pt: Optional[float] = None,
    page_number_box_height_pt: Optional[float] = None,
) -> Optional[bytes]:
    """
    把指定页按当前水印/页码设置叠加后渲成 PNG，供对话框预览。
    与最终 stamp_pdf 写入同一套绘制函数，所见即所得。
    """
    if not pdf_path or not os.path.isfile(pdf_path) or max_edge < 40:
        return None
    try:
        source = open_pdf(pdf_path, password)
    except Exception:
        return None
    preview_doc = fitz.open()
    try:
        page_count = len(source)
        if page_count <= 0:
            return None
        safe_index = max(0, min(int(page_index), page_count - 1))
        preview_doc.insert_pdf(source, from_page=safe_index, to_page=safe_index)
        preview_page = preview_doc[0]
        fontfile = _resolve_chinese_fontfile()

        has_text = bool(text_watermark and str(text_watermark).strip())
        has_image = bool(image_watermark_path and os.path.isfile(image_watermark_path))
        if has_text:
            _draw_text_watermark(
                preview_page,
                str(text_watermark).strip(),
                text_font_size,
                text_rotate,
                text_opacity,
                text_color,
                text_tile,
                fontfile,
                watermark_overlay,
            )
        if has_image:
            image_png_bytes, image_pixel_size = _prepare_image_watermark_png(
                image_watermark_path, image_opacity
            )
            if image_png_bytes and image_pixel_size:
                _draw_image_watermark(
                    preview_page,
                    image_png_bytes,
                    image_pixel_size,
                    image_scale,
                    image_tile,
                    watermark_overlay,
                )
        if add_page_number:
            from app.i18n import t
            resolved_template = (page_number_template or "").strip() or t(
                "stamp.page_template"
            )
            _draw_page_number(
                preview_page,
                safe_index + 1,
                page_count,
                resolved_template,
                page_number_position,
                page_number_font_size,
                fontfile,
                page_number_margin_mm,
                offset_left_pt=page_number_offset_left_pt,
                offset_edge_pt=page_number_offset_edge_pt,
                box_width_pt=page_number_box_width_pt,
                box_height_pt=page_number_box_height_pt,
            )

        # 高清底图供界面再缩放；上限放宽，避免大窗仍糊
        scale = float(max_edge) / max(preview_page.rect.width, preview_page.rect.height)
        scale = max(0.2, min(4.0, scale))
        pixmap = preview_page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png")
    except Exception:
        return None
    finally:
        preview_doc.close()
        source.close()


def render_page_number_preview_png(
    pdf_path: str,
    password: str,
    page_index: int,
    max_edge: int,
    add_page_number: bool,
    page_number_template: str = "",
    page_number_position: str = "bottom_center",
    page_number_font_size: float = 11.0,
    page_number_margin_mm: float = 10.0,
    page_number_offset_left_pt: Optional[float] = None,
    page_number_offset_edge_pt: Optional[float] = None,
    page_number_box_width_pt: Optional[float] = None,
    page_number_box_height_pt: Optional[float] = None,
) -> Optional[bytes]:
    """仅页码预览（兼容旧调用）；内部转统一预览函数。"""
    return render_stamp_preview_png(
        pdf_path,
        password,
        page_index,
        max_edge,
        add_page_number=add_page_number,
        page_number_template=page_number_template,
        page_number_position=page_number_position,
        page_number_font_size=page_number_font_size,
        page_number_margin_mm=page_number_margin_mm,
        page_number_offset_left_pt=page_number_offset_left_pt,
        page_number_offset_edge_pt=page_number_offset_edge_pt,
        page_number_box_width_pt=page_number_box_width_pt,
        page_number_box_height_pt=page_number_box_height_pt,
    )


def _fit_font_size_to_box(
    text: str,
    font_size: float,
    box_width: float,
    box_height: float,
    fontfile: Optional[str],
) -> float:
    """把字号收进页码框，避免文字被裁切或撑破。"""
    fitted = max(6.0, min(36.0, float(font_size)))
    max_by_height = max(6.0, box_height * 0.72)
    fitted = min(fitted, max_by_height)
    while fitted > 6.0:
        text_width = _measure_text_width(text, fitted, fontfile)
        if text_width <= max(8.0, box_width - 4.0):
            break
        fitted -= 0.4
    return fitted


def page_number_box_mins_pt(
    text: str,
    font_size: float,
    fontfile: Optional[str] = None,
) -> Tuple[float, float]:
    """
    按目标字号与样本文字，计算页码框最小宽高（PDF 点）。

    供对话框：改字号时自动加宽/加高，保证 Spin 字号与预览一致。
    """
    resolved_font = fontfile if fontfile is not None else _resolve_chinese_fontfile()
    requested = max(6.0, min(36.0, float(font_size)))
    sample = (text or "9").strip() or "9"
    text_width = _measure_text_width(sample, requested, resolved_font)
    # 左右各留约 3pt，与绘制层 box_width-4 的装字余量一致
    min_width = max(42.0, text_width + 6.0)
    # 行高约字号×1.5，与界面框高下限一致
    min_height = max(requested * 1.5, 10.0)
    return float(min_width), float(min_height)


def effective_page_number_font_size(
    text: str,
    font_size: float,
    box_width: float,
    box_height: float,
    fontfile: Optional[str] = None,
) -> float:
    """返回「字迁就框」后的实际字号，供界面提示框过窄时的真实效果。"""
    resolved_font = fontfile if fontfile is not None else _resolve_chinese_fontfile()
    return _fit_font_size_to_box(
        (text or "9").strip() or "9",
        float(font_size),
        max(18.0, float(box_width)),
        max(8.0, float(box_height)),
        resolved_font,
    )


def _draw_page_number(
    page,
    page_number: int,
    total_pages: int,
    template: str,
    position_key: str,
    font_size: float,
    fontfile: Optional[str],
    margin_mm: float = 10.0,
    offset_left_pt: Optional[float] = None,
    offset_edge_pt: Optional[float] = None,
    box_width_pt: Optional[float] = None,
    box_height_pt: Optional[float] = None,
) -> None:
    """
    绘制页码（始终叠在内容之上）。

    若传入左边距/边距/框宽高（PDF 点），按用户框定位；
    否则走旧逻辑（单一距页边 + 六向锚点），保证旧调用不受影响。
    """
    text = template.replace("{page}", str(page_number)).replace("{total}", str(total_pages))
    rect = page.rect
    use_explicit = offset_left_pt is not None and offset_edge_pt is not None
    if "left" in position_key:
        align = fitz.TEXT_ALIGN_LEFT
    elif "right" in position_key:
        align = fitz.TEXT_ALIGN_RIGHT
    else:
        align = fitz.TEXT_ALIGN_CENTER

    if use_explicit:
        # 框尺寸听用户的：只做页面边界夹紧，不再按字号静默抬高（避免距下边与 Spin 不一致）
        requested_font = max(6.0, min(36.0, float(font_size)))
        box_height = max(8.0, min(float(box_height_pt or 16.0), rect.height - 8.0))
        box_width = max(18.0, min(float(box_width_pt or 70.0), rect.width - 8.0))
        left = rect.x0 + max(0.0, float(offset_left_pt))
        if left + box_width > rect.x1 - 2.0:
            left = max(rect.x0 + 2.0, rect.x1 - 2.0 - box_width)
        anchor_y_ratio = _PAGE_NUMBER_POSITIONS.get(
            position_key, _PAGE_NUMBER_POSITIONS["bottom_center"]
        )[1]
        edge = max(0.0, float(offset_edge_pt))
        if anchor_y_ratio < 0.5:
            top = rect.y0 + edge
        else:
            top = rect.y1 - edge - box_height
        top = min(max(top, rect.y0 + 2.0), rect.y1 - box_height - 2.0)
        # 字迁就框：框太矮/太窄时缩小字号，必要时再走下方 insert_text 回退
        font_size = _fit_font_size_to_box(
            text, requested_font, box_width, box_height, fontfile
        )
    else:
        margin = max(4.0, min(_mm_to_pdf_points(margin_mm), min(rect.width, rect.height) * 0.35))
        anchor_x_ratio, anchor_y_ratio = _PAGE_NUMBER_POSITIONS.get(
            position_key, _PAGE_NUMBER_POSITIONS["bottom_center"]
        )
        box_height = font_size * 2.2
        box_width = max(120.0, font_size * max(8, len(text)) * 0.6)
        center_x = rect.x0 + margin + (rect.width - 2 * margin) * anchor_x_ratio
        if anchor_y_ratio < 0.5:
            top = rect.y0 + margin
        else:
            top = rect.y1 - margin - box_height
        left = center_x - box_width / 2
        if "left" in position_key:
            left = rect.x0 + margin
        elif "right" in position_key:
            left = rect.x1 - margin - box_width
        left = min(max(left, rect.x0 + 4), rect.x1 - box_width - 4)

    box = fitz.Rect(left, top, left + box_width, top + box_height)
    # 页码用深灰，避免在浅色底上几乎看不见
    page_color = (0.12, 0.12, 0.12)
    kwargs = {
        "fontsize": font_size,
        "color": page_color,
        "align": align,
        "overlay": True,
    }
    if fontfile:
        kwargs["fontfile"] = fontfile
        kwargs["fontname"] = "wm-pn"
    wrote = False
    try:
        result_code = page.insert_textbox(box, text, **kwargs)
        wrote = result_code >= 0
    except Exception:
        wrote = False
    if not wrote:
        # textbox 装不下或字体失败时，改用 insert_text，保证预览与导出都能看见页码
        fallback = {
            "fontsize": font_size,
            "color": page_color,
            "overlay": True,
        }
        if fontfile:
            fallback["fontfile"] = fontfile
            fallback["fontname"] = "wm-pn"
        # 基线落在框内偏下，与 textbox 视觉接近
        if align == fitz.TEXT_ALIGN_RIGHT:
            origin_x = box.x1 - _measure_text_width(text, font_size, fontfile) - 1.0
        elif align == fitz.TEXT_ALIGN_CENTER:
            origin_x = box.x0 + (box.width - _measure_text_width(text, font_size, fontfile)) / 2.0
        else:
            origin_x = box.x0 + 1.0
        origin = fitz.Point(origin_x, box.y0 + font_size * 0.92)
        try:
            page.insert_text(origin, text, **fallback)
        except Exception:
            fallback.pop("fontfile", None)
            fallback.pop("fontname", None)
            try:
                page.insert_text(origin, text, **fallback)
            except Exception:
                pass
