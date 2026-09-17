# -*- coding: utf-8 -*-
"""
PDF 安全模块：打开加密文档、加密输出、解除密码。

全部基于 PyMuPDF 离线完成，不依赖外挂工具。
"""
from __future__ import annotations

import os
import tempfile
from typing import Callable, Optional, Tuple

import fitz

from app.i18n import t


def probe_encryption(pdf_path: str) -> Tuple[bool, bool]:
    """
    探测 PDF 是否可当作有效 PDF 打开，以及是否需要密码。

    判定收紧：必须是 PDF；未加密时至少有一页。
    加密文件在未输入密码前仍返回 can=True（避免误杀）。

    :return: (文件可打开为 PDF, 是否需要密码)
    """
    try:
        document = fitz.open(pdf_path)
    except Exception:
        return False, False
    try:
        # 图片等非 PDF 被 MuPDF 打开时 is_pdf 为 False
        if not bool(getattr(document, "is_pdf", False)):
            return False, False
        needs_password = bool(document.needs_pass)
        if needs_password:
            return True, True
        # 未加密：0 页视为无效（截断/空壳常见表现）
        if int(document.page_count) <= 0:
            return False, False
        return True, False
    finally:
        document.close()


def open_pdf(pdf_path: str, password: str = ""):
    """
    打开 PDF；若加密则用密码认证。

    认证成功后校验 is_pdf 与页数，拒绝损坏/伪 PDF。

    :raises ValueError: 密码错误或无法打开
    :return: fitz.Document（调用方负责 close）
    """
    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise ValueError(t("msg.cannot_open_detail", error=exc)) from exc

    if document.needs_pass:
        auth_ok = document.authenticate(password or "")
        if not auth_ok:
            document.close()
            raise ValueError(t("msg.bad_pdf_pwd"))

    # 密码通过后再验结构，避免加密文档未认证时的页数误判
    if not bool(getattr(document, "is_pdf", False)):
        document.close()
        raise ValueError(t("msg.bad_pdf"))
    if int(document.page_count) <= 0:
        document.close()
        raise ValueError(t("msg.bad_pdf"))
    return document


def encrypt_pdf(
    pdf_path: str,
    output_path: str,
    user_password: str,
    owner_password: str = "",
    password: str = "",
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    allow_print: bool = True,
    allow_copy: bool = True,
) -> bool:
    """
    将 PDF 另存为加密文件（AES-256）。

    :param password: 打开源文件所需密码（源已加密时）
    :param user_password: 打开输出文件的用户密码
    :param owner_password: 所有者密码；空则与用户密码相同
    """
    if not user_password:
        raise ValueError(t("encrypt.empty_pwd"))
    owner = owner_password or user_password

    # 权限位：按需限制打印/复制（与常见阅读器行为一致）
    permissions = int(fitz.PDF_PERM_ACCESSIBILITY)
    if allow_print:
        permissions |= int(fitz.PDF_PERM_PRINT | fitz.PDF_PERM_PRINT_HQ)
    if allow_copy:
        permissions |= int(fitz.PDF_PERM_COPY)

    document = open_pdf(pdf_path, password)
    try:
        if cancel_check and cancel_check():
            return False
        if progress_callback:
            progress_callback(30)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        if cancel_check and cancel_check():
            return False
        document.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=user_password,
            owner_pw=owner,
            permissions=permissions,
            garbage=4,
            deflate=True,
        )
        if progress_callback:
            progress_callback(100)
        return True
    finally:
        document.close()


def decrypt_pdf(
    pdf_path: str,
    output_path: str,
    password: str,
    progress_callback: Optional[Callable[[int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> bool:
    """校验密码后另存为无加密 PDF。"""
    document = open_pdf(pdf_path, password)
    try:
        if cancel_check and cancel_check():
            return False
        if progress_callback:
            progress_callback(40)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        # 明确以无加密方式写出
        document.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_NONE,
            garbage=4,
            deflate=True,
        )
        if progress_callback:
            progress_callback(100)
        return True
    finally:
        document.close()


def materialize_unlocked_copy(pdf_path: str, password: str = "") -> str:
    """
    若文件加密，解密到临时文件并返回临时路径；否则返回原路径。

    供尚未透传 password 参数的旧接口临时桥接使用。
    """
    document = open_pdf(pdf_path, password)
    try:
        if not document.needs_pass and not password:
            # 未加密：直接用原路径（needs_pass 在认证后为 False）
            # 注意：未加密打开时 needs_pass 本就为 False
            is_encrypted = document.is_encrypted
            if not is_encrypted:
                return pdf_path
        handle, temp_path = tempfile.mkstemp(suffix=".pdf", prefix="pdf_unlocked_")
        os.close(handle)
        document.save(temp_path, encryption=fitz.PDF_ENCRYPT_NONE, garbage=4, deflate=True)
        return temp_path
    finally:
        document.close()
