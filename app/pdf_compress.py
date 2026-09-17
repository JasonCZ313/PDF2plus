# -*- coding: utf-8 -*-
"""
PDF 压缩：固定档位，或按用户填写的目标体积离线逼近。
全程使用本机 PyMuPDF + Pillow，不访问网络。
"""
from __future__ import annotations

import io
import os
import shutil
import tempfile
from typing import Callable, Dict, List, Optional, Set, Tuple

import fitz
from PIL import Image

from app.i18n import t
from app.pdf_security import open_pdf


# 固定档位：轻度只做无损清理；标准/强力重编码位图
_LEVEL_PRESETS = {
    "light": {"dpi": None, "jpeg_quality": None},
    "standard": {"dpi": 150, "jpeg_quality": 75},
    "strong": {"dpi": 110, "jpeg_quality": 58},
}

# 按目标体积搜索时的画质上下限（再低文字会明显糊，体积也几乎不再降）
_TARGET_DPI_MAX = 200
_TARGET_DPI_MIN = 72
_TARGET_JPEG_MAX = 85
_TARGET_JPEG_MIN = 30
# 二分次数上限，避免 1GB 级文件反复全量重编码拖太久
_TARGET_MAX_ATTEMPTS = 6


def format_file_size(num_bytes: int) -> str:
    """把字节数转成界面可读的体积文案（B / KB / MB / GB）。"""
    value = float(max(0, int(num_bytes)))
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024.0 or unit == "GB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024.0
    return f"{num_bytes}B"


def compress_pdf(
    pdf_path: str,
    output_path: str,
    level: str = "standard",
    password: str = "",
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    target_bytes: Optional[int] = None,
    allow_rasterize: bool = False,
    **kwargs,
) -> Dict:
    """
    离线压缩 PDF 并另存。

    固定档位（light/standard/strong）按预设处理；
    level 为 target 且传入 target_bytes 时，先无损清理，再按 DPI/JPEG 二分逼近目标体积。
    最终写出文件不得大于原文件：若无法缩小则按原文件复制并说明原因。
    """
    result = {
        "success": False,
        "original_size": 0,
        "output_size": 0,
        "ratio": 0.0,
        "message": "",
    }
    wanted_target = int(target_bytes) if target_bytes else 0
    use_target = (level == "target") or (wanted_target > 0)
    if (not use_target) and level not in _LEVEL_PRESETS:
        level = "standard"

    if not os.path.isfile(pdf_path):
        result["message"] = t("compress.msg.missing")
        return result

    original_size = os.path.getsize(pdf_path)
    result["original_size"] = original_size
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 先确认能打开 PDF，再校验目标体积，避免损坏小文件被误报「目标不合法」
    try:
        document = open_pdf(pdf_path, password)
        document.close()
    except ValueError as exc:
        result["message"] = str(exc)
        return result

    if use_target:
        if wanted_target <= 0 or wanted_target >= original_size:
            result["message"] = t("compress.msg.target_invalid")
            return result

    if _is_cancelled(cancel_check):
        result["message"] = t("compress.msg.cancelled")
        return result

    temp_dir = tempfile.mkdtemp(prefix="pdf2plus_compress_")
    try:
        if use_target:
            chosen_path, note_key, extra = _compress_toward_target(
                pdf_path=pdf_path,
                password=password,
                original_size=original_size,
                target_bytes=wanted_target,
                allow_rasterize=bool(allow_rasterize),
                work_dir=temp_dir,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )
        else:
            chosen_path, note_key, extra = _compress_fixed_level(
                pdf_path=pdf_path,
                password=password,
                original_size=original_size,
                level=level,
                work_dir=temp_dir,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

        if note_key == "cancelled":
            result["message"] = t("compress.msg.cancelled")
            return result
        if not chosen_path:
            result["message"] = extra or t("compress.msg.failed", error="")
            return result

        shutil.copy2(chosen_path, output_path)
        output_size = os.path.getsize(output_path) if os.path.isfile(output_path) else 0
        # 硬规则：写出体积不得大于原件
        if output_size > original_size:
            shutil.copy2(pdf_path, output_path)
            output_size = original_size
            note_key = "cannot_shrink"

        result["output_size"] = output_size
        if original_size > 0:
            result["ratio"] = 1.0 - (output_size / original_size)
        saved_percent = max(0.0, result["ratio"] * 100.0)
        result["success"] = True
        result["message"] = _build_result_message(
            note_key=note_key,
            original_size=original_size,
            output_size=output_size,
            target_bytes=wanted_target if use_target else 0,
            saved_percent=saved_percent,
        )
        if progress_callback:
            progress_callback(100)
        return result
    except Exception as exc:
        result["message"] = t("compress.msg.failed", error=str(exc))
        return result
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _compress_fixed_level(
    pdf_path: str,
    password: str,
    original_size: int,
    level: str,
    work_dir: str,
    progress_callback: Optional[Callable[[int], None]],
    cancel_check: Optional[Callable[[], bool]],
) -> Tuple[Optional[str], str, str]:
    """
    固定三档压缩：轻度只清理；标准/强力按预设重编码图片。
    返回 (候选文件路径, 结果文案键, 附加错误信息)。
    """
    lossless_path = os.path.join(work_dir, "lossless.pdf")
    if not _save_lossless_copy(
        pdf_path, password, lossless_path, progress_callback, 8, cancel_check
    ):
        return None, "cancelled", ""
    lossless_size = os.path.getsize(lossless_path)

    if level == "light":
        if progress_callback:
            progress_callback(90)
        if lossless_size < original_size:
            return lossless_path, "ok", ""
        return _copy_original_as_candidate(pdf_path, work_dir), "cannot_shrink", ""

    preset = _LEVEL_PRESETS[level]
    encoded_path = os.path.join(work_dir, "preset.pdf")
    if not _reencode_images_to_file(
        pdf_path,
        password,
        encoded_path,
        int(preset["dpi"]),
        int(preset["jpeg_quality"]),
        progress_callback,
        10,
        90,
        cancel_check,
    ):
        return None, "cancelled", ""
    encoded_size = os.path.getsize(encoded_path)
    best_path, best_size = _pick_smaller(
        (lossless_path, lossless_size),
        (encoded_path, encoded_size),
    )
    if best_size >= original_size:
        return _copy_original_as_candidate(pdf_path, work_dir), "cannot_shrink", ""
    return best_path, "ok", ""


def _compress_toward_target(
    pdf_path: str,
    password: str,
    original_size: int,
    target_bytes: int,
    allow_rasterize: bool,
    work_dir: str,
    progress_callback: Optional[Callable[[int], None]],
    cancel_check: Optional[Callable[[], bool]],
) -> Tuple[Optional[str], str, str]:
    """
    按目标体积压缩：无损清理 → 估算一刀 → 最多若干次二分 DPI/JPEG。
    优先选出「不超过目标」里最接近目标的结果（画质更好）；否则取已得到的最小体积。
    """
    candidates: List[Tuple[str, int]] = []
    lossless_path = os.path.join(work_dir, "lossless.pdf")
    if not _save_lossless_copy(
        pdf_path, password, lossless_path, progress_callback, 8, cancel_check
    ):
        return None, "cancelled", ""
    lossless_size = os.path.getsize(lossless_path)
    if lossless_size < original_size:
        candidates.append((lossless_path, lossless_size))
    if lossless_size <= target_bytes and lossless_size < original_size:
        if progress_callback:
            progress_callback(90)
        return lossless_path, "ok_target", ""

    strength_guess = _estimate_strength(lossless_size, target_bytes)
    low_strength = 0.0
    high_strength = 1.0
    hit_floor = False
    for attempt_index in range(_TARGET_MAX_ATTEMPTS):
        if _is_cancelled(cancel_check):
            return None, "cancelled", ""
        if attempt_index == 0:
            strength = strength_guess
        else:
            strength = (low_strength + high_strength) / 2.0
        dpi, jpeg_quality = _strength_to_params(strength)
        if dpi <= _TARGET_DPI_MIN and jpeg_quality <= _TARGET_JPEG_MIN:
            hit_floor = True
        attempt_path = os.path.join(work_dir, f"try_{attempt_index}.pdf")
        progress_start = 10 + attempt_index * 12
        progress_end = min(82, progress_start + 12)
        if not _reencode_images_to_file(
            pdf_path,
            password,
            attempt_path,
            dpi,
            jpeg_quality,
            progress_callback,
            progress_start,
            progress_end,
            cancel_check,
        ):
            return None, "cancelled", ""
        attempt_size = os.path.getsize(attempt_path)
        if attempt_size < original_size:
            candidates.append((attempt_path, attempt_size))
        if attempt_size > target_bytes:
            low_strength = min(1.0, strength + 0.04)
        else:
            high_strength = max(0.0, strength - 0.04)
        # 已经贴得足够近就提前结束
        if 0 < attempt_size <= target_bytes and (target_bytes - attempt_size) <= max(
            32 * 1024, int(target_bytes * 0.06)
        ):
            break

    if allow_rasterize:
        smallest_now = min((item[1] for item in candidates), default=original_size)
        if smallest_now > target_bytes:
            raster_path = os.path.join(work_dir, "raster.pdf")
            if not _rasterize_to_file(
                pdf_path,
                password,
                raster_path,
                progress_callback,
                84,
                94,
                cancel_check,
            ):
                return None, "cancelled", ""
            raster_size = os.path.getsize(raster_path)
            if raster_size < original_size:
                candidates.append((raster_path, raster_size))
                hit_floor = True

    chosen = _choose_candidate(candidates, target_bytes, original_size)
    if chosen is None:
        return _copy_original_as_candidate(pdf_path, work_dir), "cannot_shrink", ""
    chosen_path, chosen_size = chosen
    if chosen_size > target_bytes:
        return chosen_path, "ok_target_floor" if hit_floor else "ok_target_floor", ""
    return chosen_path, "ok_target", ""


def _choose_candidate(
    candidates: List[Tuple[str, int]],
    target_bytes: int,
    original_size: int,
) -> Optional[Tuple[str, int]]:
    """在小于原体积的候选里：能进目标则取最接近目标（通常更大、更清晰），否则取最小。"""
    valid = [(path, size) for path, size in candidates if 0 < size < original_size]
    if not valid:
        return None
    under_target = [(path, size) for path, size in valid if size <= target_bytes]
    if under_target:
        return max(under_target, key=lambda item: item[1])
    return min(valid, key=lambda item: item[1])


def _estimate_strength(current_size: int, target_bytes: int) -> float:
    """
    根据当前体积与目标体积估算压缩强度 0～1。
    强度越大 DPI/JPEG 越低。扫描件体积大致随面积×质量下降，用平方根作粗略映射。
    """
    if current_size <= 0 or target_bytes <= 0:
        return 0.55
    ratio = max(0.02, min(0.98, target_bytes / float(current_size)))
    # ratio 越小需要越狠；sqrt 避免一上来就打到画质地板
    estimated = 1.0 - (ratio ** 0.5)
    return max(0.12, min(0.92, estimated))


def _strength_to_params(strength: float) -> Tuple[int, int]:
    """把 0～1 强度映射成 DPI 与 JPEG 质量。"""
    clamped = max(0.0, min(1.0, float(strength)))
    dpi = int(round(_TARGET_DPI_MAX - clamped * (_TARGET_DPI_MAX - _TARGET_DPI_MIN)))
    jpeg_quality = int(
        round(_TARGET_JPEG_MAX - clamped * (_TARGET_JPEG_MAX - _TARGET_JPEG_MIN))
    )
    dpi = max(_TARGET_DPI_MIN, min(_TARGET_DPI_MAX, dpi))
    jpeg_quality = max(_TARGET_JPEG_MIN, min(_TARGET_JPEG_MAX, jpeg_quality))
    return dpi, jpeg_quality


def _save_lossless_copy(
    pdf_path: str,
    password: str,
    output_path: str,
    progress_callback: Optional[Callable[[int], None]],
    progress_value: int,
    cancel_check: Optional[Callable[[], bool]],
) -> bool:
    """打开源 PDF 做垃圾回收与 deflate，不重编码图片。取消时返回 False。"""
    if _is_cancelled(cancel_check):
        return False
    document = open_pdf(pdf_path, password)
    try:
        if _is_cancelled(cancel_check):
            return False
        _save_compressed(document, output_path)
        if progress_callback:
            progress_callback(progress_value)
        return True
    finally:
        document.close()


def _reencode_images_to_file(
    pdf_path: str,
    password: str,
    output_path: str,
    target_dpi: int,
    jpeg_quality: int,
    progress_callback: Optional[Callable[[int], None]],
    progress_start: int,
    progress_end: int,
    cancel_check: Optional[Callable[[], bool]],
) -> bool:
    """从源文件重新打开，按给定 DPI/JPEG 重编码全部位图后保存。始终从原图出发，避免代际损失。"""
    if _is_cancelled(cancel_check):
        return False
    document = open_pdf(pdf_path, password)
    try:
        page_count = len(document)
        seen_xrefs: Set[int] = set()
        for page_index in range(page_count):
            if _is_cancelled(cancel_check):
                return False
            page = document[page_index]
            for image_info in page.get_images(full=True):
                xref = int(image_info[0])
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    _recompress_image_on_page(
                        document, page, xref, target_dpi, jpeg_quality
                    )
                except Exception:
                    continue
            if progress_callback and page_count:
                span = max(1, progress_end - progress_start)
                progress_callback(
                    progress_start + int((page_index + 1) / page_count * span)
                )
        if _is_cancelled(cancel_check):
            return False
        _save_compressed(document, output_path)
        return True
    finally:
        document.close()


def _rasterize_to_file(
    pdf_path: str,
    password: str,
    output_path: str,
    progress_callback: Optional[Callable[[int], None]],
    progress_start: int,
    progress_end: int,
    cancel_check: Optional[Callable[[], bool]],
) -> bool:
    """
    可选最后一招：整页栅格化为 JPEG 再写入新 PDF。
    文字将不可选，仅在用户勾选且图片重编码仍远超目标时使用。
    """
    if _is_cancelled(cancel_check):
        return False
    source = open_pdf(pdf_path, password)
    output_doc = fitz.open()
    try:
        page_count = len(source)
        matrix = fitz.Matrix(
            _TARGET_DPI_MIN / 72.0,
            _TARGET_DPI_MIN / 72.0,
        )
        for page_index in range(page_count):
            if _is_cancelled(cancel_check):
                return False
            page = source[page_index]
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            try:
                jpeg_bytes = pixmap.tobytes("jpeg")
            except Exception:
                image = Image.frombytes(
                    "RGB", (pixmap.width, pixmap.height), pixmap.samples
                )
                buffer = io.BytesIO()
                image.save(
                    buffer,
                    format="JPEG",
                    quality=_TARGET_JPEG_MIN,
                    optimize=True,
                )
                jpeg_bytes = buffer.getvalue()
            new_page = output_doc.new_page(
                width=page.rect.width, height=page.rect.height
            )
            new_page.insert_image(page.rect, stream=jpeg_bytes)
            if progress_callback and page_count:
                span = max(1, progress_end - progress_start)
                progress_callback(
                    progress_start + int((page_index + 1) / page_count * span)
                )
        if _is_cancelled(cancel_check):
            return False
        _save_compressed(output_doc, output_path)
        return True
    finally:
        output_doc.close()
        source.close()


def _save_compressed(document: fitz.Document, output_path: str) -> None:
    """统一压缩保存参数：垃圾回收、deflate 图片与字体。"""
    document.save(
        output_path,
        garbage=4,
        deflate=True,
        clean=True,
        deflate_images=True,
        deflate_fonts=True,
    )


def _recompress_image_on_page(
    document: fitz.Document,
    page: fitz.Page,
    xref: int,
    target_dpi: int,
    jpeg_quality: int,
) -> None:
    """将页面中的位图按目标 DPI 缩小并替换为 JPEG。"""
    pixmap = fitz.Pixmap(document, xref)
    try:
        if pixmap.n > 4:
            pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
        if pixmap.alpha:
            pixmap = fitz.Pixmap(pixmap, 0)
        if pixmap.n != 3:
            pixmap = fitz.Pixmap(fitz.csRGB, pixmap)

        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        width, height = image.size
        scale = min(1.0, float(target_dpi) / 200.0)
        if max(width, height) > 400 and scale < 0.999:
            image = image.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        jpeg_bytes = buffer.getvalue()

        replaced = False
        if hasattr(page, "replace_image"):
            try:
                page.replace_image(xref, stream=jpeg_bytes)
                replaced = True
            except Exception:
                replaced = False
        if not replaced:
            document.update_stream(xref, jpeg_bytes)
    finally:
        pixmap = None


def _copy_original_as_candidate(pdf_path: str, work_dir: str) -> str:
    """无法缩小时把原文件拷到工作目录，供后续统一写出（体积与原件相同）。"""
    copied_path = os.path.join(work_dir, "original_copy.pdf")
    shutil.copy2(pdf_path, copied_path)
    return copied_path


def _pick_smaller(
    first: Tuple[str, int],
    second: Tuple[str, int],
) -> Tuple[str, int]:
    """两个候选里取体积更小的一个。"""
    if first[1] <= 0:
        return second
    if second[1] <= 0:
        return first
    return first if first[1] <= second[1] else second


def _build_result_message(
    note_key: str,
    original_size: int,
    output_size: int,
    target_bytes: int,
    saved_percent: float,
) -> str:
    """按压缩结局生成给用户看的体积对比说明。"""
    original_text = format_file_size(original_size)
    output_text = format_file_size(output_size)
    target_text = format_file_size(target_bytes) if target_bytes else ""
    if note_key == "cannot_shrink":
        return t("compress.msg.cannot_shrink", original=original_text)
    if note_key == "ok_target_floor":
        return t(
            "compress.msg.ok_target_floor",
            original=original_text,
            output=output_text,
            target=target_text,
        )
    if note_key == "ok_target":
        return t(
            "compress.msg.ok_target",
            original=original_text,
            output=output_text,
            target=target_text,
            percent=f"{saved_percent:.1f}",
        )
    return t(
        "compress.msg.ok",
        original=original_text,
        output=output_text,
        percent=f"{saved_percent:.1f}",
    )


def _is_cancelled(cancel_check: Optional[Callable[[], bool]]) -> bool:
    """统一判断用户是否点了取消。"""
    return bool(cancel_check and cancel_check())
