#!/usr/bin/env python3
"""
原材料入库脚本（本地 embedding + 中文分块 + 增量入库）
用法: python ingest.py
功能: 扫描所有文档目录，按中文句子切块，用本地 embedding 模型向量化后存入 ChromaDB。
      文件哈希缓存——内容未变化则跳过，避免重复处理。
"""

import json
import hashlib
import re
from pathlib import Path

from shared import config, collection, get_embedding

# 文件哈希缓存路径
CACHE_PATH = Path(config["paths"]["vectordb"]).expanduser() / "_file_cache.json"


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 60) -> list:
    """
    按中文句子分隔符切块。
    在 。！？\\n 处断句，累积到 chunk_size 字符附近输出一个块。
    overlap 控制相邻块之间保留多少字符的重叠。
    """
    sentences = re.split(r'(?<=[。！？\n])\s*', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) > chunk_size and current:
            chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = tail + sent
        else:
            current += sent

    if current:
        chunks.append(current)

    return chunks


def load_cache() -> dict:
    """加载文件哈希缓存 {filepath: md5_hex}"""
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    """保存文件哈希缓存"""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def file_hash(filepath: Path) -> str:
    """计算文件内容的 MD5 哈希"""
    return hashlib.md5(filepath.read_bytes()).hexdigest()


def remove_old_chunks(filepath: Path):
    """删除某个文件之前入库的所有块（通过 metadata source 匹配）"""
    try:
        existing = collection.get(
            where={"source": str(filepath)},
            include=["metadatas"]
        )
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass  # ChromaDB 在某些版本对 where 过滤支持有限，忽略即可


def ingest_file(filepath: Path, doc_type: str, file_hash_value: str):
    """处理单个文件：分块 → 向量化 → 入库"""
    try:
        text = filepath.read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"  ✗ 读取失败: {filepath} ({e})")
        return

    if not text:
        print(f"  - 跳过空文件: {filepath.name}")
        return

    remove_old_chunks(filepath)

    chunks = chunk_text(text)
    ingested = 0

    for i, chunk in enumerate(chunks):
        if len(chunk.strip()) < 20:
            continue
        doc_id = hashlib.md5(f"{filepath}-{i}-{file_hash_value}".encode()).hexdigest()
        try:
            embedding = get_embedding(chunk)
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "source": str(filepath),
                    "filename": filepath.name,
                    "type": doc_type,
                    "chunk_index": i
                }]
            )
            ingested += 1
        except Exception as e:
            print(f"  ✗ 向量化失败 chunk {i}: {e}")

    tag = "  ✓" if ingested > 0 else "  -"
    print(f"{tag} {filepath.name} → {ingested} 个块已入库")


def ingest_all():
    base = Path.home() / ".butler"
    targets = [
        (base / "core", "core"),
        (base / "knowledge" / "notes", "notes"),
        (base / "knowledge" / "chats", "chats"),
        (base / "knowledge" / "other", "saved_search"),
        (base / "logs", "logs"),
    ]

    cache = load_cache()
    total_processed = 0
    total_skipped = 0

    for directory, doc_type in targets:
        if not directory.exists():
            continue
        files = list(directory.glob("**/*.md")) + list(directory.glob("**/*.txt"))
        if not files:
            continue
        print(f"\n[{doc_type}] 检查 {len(files)} 个文件...")
        for f in files:
            try:
                fh = file_hash(f)
            except Exception:
                print(f"  ✗ 无法读取: {f.name}")
                continue

            cached = cache.get(str(f))
            if cached == fh:
                print(f"  - {f.name}（内容未变化，跳过）")
                total_skipped += 1
                continue

            ingest_file(f, doc_type, fh)
            cache[str(f)] = fh
            total_processed += 1

    save_cache(cache)

    print(f"\n✅ 入库完成")
    print(f"   处理 {total_processed} 个文件，跳过 {total_skipped} 个（未变化）")
    print(f"   数据库现有 {collection.count()} 条记录")


if __name__ == "__main__":
    print("🔄 开始处理原材料（本地 embedding · 中文分块 · 增量）...")
    ingest_all()
