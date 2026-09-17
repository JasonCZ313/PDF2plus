"""历史记录管理模块（完全离线，无需联网）

存储结构：
    history/
        history_index.json          # 索引文件（最多10条）
        20260722_143052_合并/
            info.json               # 元数据
            output_xxx.pdf          # 输出文件副本
        20260722_150000_转Word/
            info.json
            output_xxx.docx
"""
import os
import json
import shutil
from datetime import datetime
from app.preferences import get_data_dir

HISTORY_DIR = os.path.join(get_data_dir(), "history")
INDEX_FILE = os.path.join(HISTORY_DIR, "history_index.json")
MAX_RECORDS = 10


def _load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_index(index):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_record(op_type, source_paths, output_path):
    """
    添加一条历史记录

    :param op_type: 操作类型（合并/拆分/转图片/转Word）
    :param source_paths: 源文件路径列表
    :param output_path: 输出文件路径（单个文件或目录）
    :return: 记录 ID
    """
    now = datetime.now()
    record_id = now.strftime("%Y%m%d_%H%M%S") + f"_{op_type}"
    record_dir = os.path.join(HISTORY_DIR, record_id)
    os.makedirs(record_dir, exist_ok=True)

    # 保存输出文件
    stored_output = None
    if os.path.isfile(output_path):
        stored_output = os.path.join(record_dir, os.path.basename(output_path))
        shutil.copy2(output_path, stored_output)
    elif os.path.isdir(output_path):
        # 如果是目录，复制目录内所有文件
        stored_output = os.path.join(record_dir, "output")
        os.makedirs(stored_output, exist_ok=True)
        for f in os.listdir(output_path):
            src = os.path.join(output_path, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(stored_output, f))

    # 写入 info.json
    info = {
        "id": record_id,
        "type": op_type,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": source_paths,  # 只记录路径，不复制源文件
        "output_path": output_path,
        "stored_output": stored_output,
    }
    with open(os.path.join(record_dir, "info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    # 更新索引
    index = _load_index()
    index.insert(0, info)

    # FIFO：超过最大记录数则删除最旧的
    while len(index) > MAX_RECORDS:
        oldest = index.pop()
        oldest_dir = os.path.join(HISTORY_DIR, oldest["id"])
        if os.path.exists(oldest_dir):
            shutil.rmtree(oldest_dir, ignore_errors=True)

    _save_index(index)
    return record_id


def get_all_records():
    """获取所有历史记录（最新在前）"""
    return _load_index()


def get_record(record_id):
    """获取单条记录详情"""
    for r in _load_index():
        if r["id"] == record_id:
            return r
    return None


def delete_record(record_id):
    """删除一条历史记录及其文件"""
    record_dir = os.path.join(HISTORY_DIR, record_id)
    if os.path.exists(record_dir):
        shutil.rmtree(record_dir, ignore_errors=True)
    index = _load_index()
    index = [r for r in index if r["id"] != record_id]
    _save_index(index)


def download_output(record_id, dest_path):
    """将历史记录中的输出文件复制到用户选择的位置"""
    record = get_record(record_id)
    if not record or not record.get("stored_output"):
        return False
    src = record["stored_output"]
    if os.path.isfile(src):
        shutil.copy2(src, dest_path)
        return True
    elif os.path.isdir(src):
        os.makedirs(dest_path, exist_ok=True)
        for f in os.listdir(src):
            s = os.path.join(src, f)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(dest_path, f))
        return True
    return False
