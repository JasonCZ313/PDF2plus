# -*- coding: utf-8 -*-
"""
大文件分片 / 拼接工具

用途：
1. 将超过阈值的文件切成多个 .partNNN，便于推送 Git（单文件 < 平台上限）
2. 根据旁边的 .parts.json 清单，把分片静默拼回原始文件（字节级一致）
3. 供打包脚本（run_build.py）与薄启动器（launcher.py）共同调用

分片命名约定（与原文件同目录）：
  原文件:   torch_cpu.dll
  清单:     torch_cpu.dll.parts.json
  分片:     torch_cpu.dll.part001、torch_cpu.dll.part002、...
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Callable, Iterable, List, Optional


# 默认分片大小：90MiB，低于 GitHub 100MB 硬限制，也低于常见私服约 200MB 限制
DEFAULT_PART_SIZE_BYTES = 90 * 1024 * 1024

# 达到或超过该大小的文件才会被分片（略高于分片大小，避免边界抖动）
DEFAULT_SPLIT_THRESHOLD_BYTES = 90 * 1024 * 1024

# 清单文件后缀：原文件名 + 本后缀
MANIFEST_SUFFIX = ".parts.json"

# 二次启动加速：校验通过后写入的标记后缀（与清单同目录）
ASSEMBLED_OK_SUFFIX = ".assembled_ok"

# 清单格式版本号，便于以后兼容升级
MANIFEST_VERSION = 1


def part_path_for(original_path: str, part_index: int) -> str:
    """根据原文件路径与从 1 开始的分片序号，生成分片完整路径。"""
    return f"{original_path}.part{part_index:03d}"


def manifest_path_for(original_path: str) -> str:
    """返回与原文件对应的清单文件路径。"""
    return original_path + MANIFEST_SUFFIX


def sha256_file(file_path: str, chunk_size: int = 8 * 1024 * 1024) -> str:
    """计算文件 SHA-256，分块读取以避免一次载入超大文件到内存。"""
    digest = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        while True:
            block = file_handle.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _write_manifest(manifest_path: str, payload: dict) -> None:
    """将清单字典以 UTF-8 JSON 写入磁盘（带缩进，便于人工查看）。"""
    with open(manifest_path, "w", encoding="utf-8") as manifest_file:
        json.dump(payload, manifest_file, ensure_ascii=False, indent=2)


def load_manifest(manifest_path: str) -> dict:
    """读取并返回分片清单内容；文件不存在或损坏时抛出异常。"""
    with open(manifest_path, "r", encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def split_file(
    original_path: str,
    part_size_bytes: int = DEFAULT_PART_SIZE_BYTES,
    remove_original: bool = True,
) -> str:
    """
    将单个大文件切成多个分片，并写入 .parts.json 清单。

    :param original_path: 待分片的完整文件路径
    :param part_size_bytes: 每个分片的最大字节数
    :param remove_original: 分片成功后是否删除原文件（便于 Git 只跟踪分片）
    :return: 清单文件路径
    """
    if not os.path.isfile(original_path):
        raise FileNotFoundError(original_path)
    if part_size_bytes <= 0:
        raise ValueError("part_size_bytes 必须为正整数")

    file_size = os.path.getsize(original_path)
    file_digest = sha256_file(original_path)
    original_name = os.path.basename(original_path)
    parent_dir = os.path.dirname(original_path) or "."

    part_names: List[str] = []
    part_index = 1
    with open(original_path, "rb") as source_file:
        while True:
            chunk_data = source_file.read(part_size_bytes)
            if not chunk_data:
                break
            part_name = f"{original_name}.part{part_index:03d}"
            part_full_path = os.path.join(parent_dir, part_name)
            with open(part_full_path, "wb") as part_file:
                part_file.write(chunk_data)
            part_names.append(part_name)
            part_index += 1

    if not part_names:
        raise RuntimeError(f"文件为空，无法分片: {original_path}")

    manifest_payload = {
        "version": MANIFEST_VERSION,
        "original_name": original_name,
        "size": file_size,
        "sha256": file_digest,
        "part_size": part_size_bytes,
        "part_count": len(part_names),
        "parts": part_names,
    }
    manifest_path = manifest_path_for(original_path)
    _write_manifest(manifest_path, manifest_payload)

    if remove_original:
        os.remove(original_path)
        _clear_assembled_ok(manifest_path)

    return manifest_path


def iter_oversized_files(
    root_dir: str,
    threshold_bytes: int = DEFAULT_SPLIT_THRESHOLD_BYTES,
) -> Iterable[str]:
    """
    递归遍历目录，产出体积达到阈值、且尚不是分片/清单本身的文件路径。

    会跳过：
    - *.partNNN 分片文件
    - *.parts.json 清单文件
    """
    for current_dir, _dir_names, file_names in os.walk(root_dir):
        for file_name in file_names:
            # 跳过已有分片与清单，避免重复处理
            if file_name.endswith(MANIFEST_SUFFIX):
                continue
            if file_name.endswith(ASSEMBLED_OK_SUFFIX):
                continue
            if ".part" in file_name and _looks_like_part_name(file_name):
                continue
            full_path = os.path.join(current_dir, file_name)
            try:
                if os.path.getsize(full_path) >= threshold_bytes:
                    yield full_path
            except OSError:
                continue


def _looks_like_part_name(file_name: str) -> bool:
    """判断文件名是否形如 xxx.part001（用于遍历时跳过分片）。"""
    marker = ".part"
    if marker not in file_name:
        return False
    suffix = file_name.rsplit(marker, 1)[-1]
    return suffix.isdigit() and len(suffix) == 3


def split_tree(
    root_dir: str,
    threshold_bytes: int = DEFAULT_SPLIT_THRESHOLD_BYTES,
    part_size_bytes: int = DEFAULT_PART_SIZE_BYTES,
    remove_original: bool = True,
) -> List[str]:
    """
    扫描目录树，对所有超限文件执行分片。

    :return: 新生成的清单路径列表
    """
    if not os.path.isdir(root_dir):
        raise NotADirectoryError(root_dir)

    manifest_paths: List[str] = []
    # 先收集列表再处理，避免 walk 过程中目录内容变化
    oversized_paths = list(iter_oversized_files(root_dir, threshold_bytes))
    for file_path in oversized_paths:
        # 若已有完整清单且分片齐全，则跳过（幂等）
        existing_manifest = manifest_path_for(file_path)
        if os.path.isfile(existing_manifest) and not os.path.isfile(file_path):
            continue
        if os.path.isfile(existing_manifest) and os.path.isfile(file_path):
            # 原文件与清单同时存在：先删旧分片再重新切，保证与当前原文件一致
            _remove_parts_described_by(existing_manifest)
            _clear_assembled_ok(existing_manifest)

        manifest_path = split_file(
            file_path,
            part_size_bytes=part_size_bytes,
            remove_original=remove_original,
        )
        manifest_paths.append(manifest_path)
    return manifest_paths


def _remove_parts_described_by(manifest_path: str) -> None:
    """根据清单删除已存在的分片文件（重新分片前清理）。"""
    try:
        payload = load_manifest(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return
    base_dir = os.path.dirname(manifest_path) or "."
    for part_name in payload.get("parts", []):
        part_full = os.path.join(base_dir, part_name)
        if os.path.isfile(part_full):
            try:
                os.remove(part_full)
            except OSError:
                pass


def find_manifests(root_dir: str) -> List[str]:
    """递归查找目录下所有 .parts.json 清单路径。"""
    manifest_paths: List[str] = []
    if not os.path.isdir(root_dir):
        return manifest_paths
    for current_dir, _dir_names, file_names in os.walk(root_dir):
        for file_name in file_names:
            if file_name.endswith(MANIFEST_SUFFIX):
                manifest_paths.append(os.path.join(current_dir, file_name))
    return manifest_paths


def target_path_from_manifest(manifest_path: str) -> str:
    """由清单路径推导应还原出的原文件完整路径。"""
    if not manifest_path.endswith(MANIFEST_SUFFIX):
        raise ValueError(f"不是有效清单路径: {manifest_path}")
    return manifest_path[: -len(MANIFEST_SUFFIX)]


def assembled_ok_path_for(manifest_path: str) -> str:
    """返回与清单对应的「已校验通过」标记文件路径。"""
    return manifest_path + ASSEMBLED_OK_SUFFIX


def _write_assembled_ok(manifest_path: str, sha256_hex: str) -> None:
    """写入校验通过标记，内容为清单中的 sha256，供二次启动跳过全量哈希。"""
    ok_path = assembled_ok_path_for(manifest_path)
    try:
        with open(ok_path, "w", encoding="utf-8") as ok_file:
            ok_file.write(sha256_hex.strip())
    except OSError:
        pass


def _clear_assembled_ok(manifest_path: str) -> None:
    """删除校验标记（重新分片或准备重拼前调用）。"""
    ok_path = assembled_ok_path_for(manifest_path)
    if os.path.isfile(ok_path):
        try:
            os.remove(ok_path)
        except OSError:
            pass


def is_assembled_ok(manifest_path: str) -> bool:
    """
    判断原文件是否已存在且与清单一致。

    策略（保证正确性、加速二次启动）：
    1. 文件不存在或大小不符 → 否
    2. 存在 .assembled_ok 且内容等于清单 sha256 → 是（跳过全量哈希）
    3. 否则全量 SHA-256；通过则写标记并返回是
    """
    target_path = target_path_from_manifest(manifest_path)
    if not os.path.isfile(target_path):
        return False
    try:
        payload = load_manifest(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError):
        return False

    expected_size = int(payload.get("size", -1))
    expected_hash = str(payload.get("sha256", ""))
    if expected_size < 0 or not expected_hash:
        return False
    if os.path.getsize(target_path) != expected_size:
        return False

    ok_path = assembled_ok_path_for(manifest_path)
    if os.path.isfile(ok_path):
        try:
            with open(ok_path, "r", encoding="utf-8") as ok_file:
                stored_hash = ok_file.read().strip()
            if stored_hash == expected_hash:
                return True
        except OSError:
            pass

    if sha256_file(target_path) == expected_hash:
        _write_assembled_ok(manifest_path, expected_hash)
        return True
    return False


def assemble_from_manifest(
    manifest_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> str:
    """
    按清单将分片拼回原文件；写入临时文件后再原子替换，避免半截损坏文件。

    :param manifest_path: .parts.json 路径
    :param progress_callback: 可选回调 (已完成字节数, 总字节数)
    :return: 还原后的原文件路径
    """
    payload = load_manifest(manifest_path)
    target_path = target_path_from_manifest(manifest_path)
    base_dir = os.path.dirname(manifest_path) or "."
    part_names = payload.get("parts") or []
    expected_size = int(payload["size"])
    expected_hash = str(payload["sha256"])

    if not part_names:
        raise RuntimeError(f"清单未列出分片: {manifest_path}")

    # 启动前校验全部分片存在，避免拼到一半才失败
    part_full_paths: List[str] = []
    for part_name in part_names:
        part_full = os.path.join(base_dir, part_name)
        if not os.path.isfile(part_full):
            raise FileNotFoundError(f"缺少分片文件: {part_full}")
        part_full_paths.append(part_full)

    target_dir = os.path.dirname(target_path) or "."
    os.makedirs(target_dir, exist_ok=True)

    # 在同目录写临时文件，保证 os.replace 同卷原子替换
    temp_file_handle = tempfile.NamedTemporaryFile(
        mode="wb",
        dir=target_dir,
        prefix=os.path.basename(target_path) + ".",
        suffix=".assembling",
        delete=False,
    )
    temp_path = temp_file_handle.name
    bytes_written = 0
    try:
        with temp_file_handle:
            for part_full in part_full_paths:
                with open(part_full, "rb") as part_file:
                    while True:
                        block = part_file.read(8 * 1024 * 1024)
                        if not block:
                            break
                        temp_file_handle.write(block)
                        bytes_written += len(block)
                        if progress_callback is not None:
                            progress_callback(bytes_written, expected_size)

        if bytes_written != expected_size:
            raise RuntimeError(
                f"拼接后大小不符: 期望 {expected_size}，实际 {bytes_written}，清单 {manifest_path}"
            )

        actual_hash = sha256_file(temp_path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"拼接后校验失败（SHA-256 不一致）: {manifest_path}"
            )

        # 若已有旧原文件，先替换为新拼好的完整文件
        os.replace(temp_path, target_path)
        temp_path = ""  # 标记已成功接管，避免 finally 误删
        _write_assembled_ok(manifest_path, expected_hash)
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

    return target_path


def assemble_all_under(
    root_dir: str,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> List[str]:
    """
    扫描目录下全部清单：缺文件或校验失败则拼接，已完好则跳过。

    :param progress_callback: 可选 (当前原文件名, 已写字节, 总字节)
    :return: 本次实际执行了拼接的原文件路径列表
    """
    restored_paths: List[str] = []
    for manifest_path in find_manifests(root_dir):
        if is_assembled_ok(manifest_path):
            continue
        target_name = os.path.basename(target_path_from_manifest(manifest_path))

        def _on_progress(done: int, total: int, name: str = target_name) -> None:
            if progress_callback is not None:
                progress_callback(name, done, total)

        restored = assemble_from_manifest(manifest_path, progress_callback=_on_progress)
        restored_paths.append(restored)
    return restored_paths
