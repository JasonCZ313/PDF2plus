"""PDF 无损合并模块

使用 PyMuPDF 直接复制 PDF 页面树，不经过渲染->编码流程，
因此矢量元素、嵌入字体、高分辨率图片均完全保留。
"""
import os
import fitz
from typing import Dict, List, Optional, Callable

from app.pdf_security import open_pdf


def merge_pdfs(
    pdf_paths: List[str],
    output_path: str,
    progress_callback: Optional[Callable[[int], None]] = None,
    **kwargs
) -> bool:
    """
    将多个 PDF 按顺序无损合并为一个新的 PDF

    :param pdf_paths: 按合并顺序排列的 PDF 文件路径列表
    :param output_path: 输出文件路径（含 .pdf 后缀）
    :param progress_callback: 进度回调 (0 ~ 100)
    :param kwargs: 可含 cancel_check；可含 passwords: {路径: 打开密码}
    :return: 是否成功（空列表或取消均为 False）
    """
    cancel_check = kwargs.get("cancel_check")
    # 各源文件打开密码；未出现在字典中的视为空密码（未加密）
    passwords: Dict[str, str] = kwargs.get("passwords") or {}
    try:
        if not pdf_paths:
            return False

        result = fitz.open()
        total = len(pdf_paths)

        for file_index, pdf_path in enumerate(pdf_paths):
            if cancel_check and cancel_check():
                result.close()
                return False
            password = passwords.get(pdf_path, "")
            source = open_pdf(pdf_path, password)
            try:
                result.insert_pdf(source)
            finally:
                source.close()
            if progress_callback:
                progress_callback(int((file_index + 1) / total * 100))

        if cancel_check and cancel_check():
            result.close()
            return False

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        result.save(output_path, garbage=4, deflate=True)
        result.close()
        return True
    except Exception:
        return False
