#!/usr/bin/env python3
"""
学习材料入库脚本
扫描 knowledge/learning/ 下的 .md 文件，解析 YAML frontmatter，向量化后存入 learning_materials collection。
支持增量（MD5 缓存，内容未变化则跳过）。
"""

import hashlib
import json
import re
from pathlib import Path

import yaml

from shared import config, get_embedding, get_learning_collection

LEARNING_DIR = Path.home() / ".butler" / "knowledge" / "learning"
CACHE_PATH = Path.home() / ".butler" / "vectordb" / "_learning_cache.json"


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """解析文件头部的 YAML frontmatter。没有则返回 ({}, 全文) 并打印警告。"""
    text = filepath.read_text(encoding="utf-8")
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
    match = pattern.match(text)
    if not match:
        print(f"  WARNING: {filepath.name} 缺少 frontmatter，跳过")
        return {}, ""
    try:
        metadata = yaml.safe_load(match.group(1))
        body = match.group(2).strip()
        if not isinstance(metadata, dict):
            print(f"  WARNING: {filepath.name} frontmatter 格式错误，跳过")
            return {}, ""
        return metadata, body
    except Exception as e:
        print(f"  WARNING: {filepath.name} frontmatter 解析失败: {e}，跳过")
        return {}, ""


def validate_metadata(metadata: dict, filepath: Path) -> bool:
    """验证必填字段：subject, difficulty, status, created。"""
    required = ["subject", "difficulty", "status", "created"]
    missing = [k for k in required if k not in metadata]
    if missing:
        print(f"  WARNING: {filepath.name} 缺少必填字段 {missing}，跳过")
        return False
    return True


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 60) -> list:
    """按中文句子分隔符切块。"""
    sentences = re.split(r"(?<=[。！？\n])\s*", text)
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


def remove_old_chunks(filepath: Path, collection):
    """删除某个文件之前入库的所有块。"""
    try:
        existing = collection.get(
            where={"source": str(filepath)},
            include=["metadatas"]
        )
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def ingest_file(filepath: Path, collection):
    """处理单个学习材料文件：frontmatter → 分块 → 向量化 → 入库。"""
    metadata, body = parse_frontmatter(filepath)
    if not metadata or not body:
        return 0

    if not validate_metadata(metadata, filepath):
        return 0

    remove_old_chunks(filepath, collection)

    chunks = chunk_text(body)
    ingested = 0

    tags = metadata.get("tags", [])
    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)

    for i, chunk in enumerate(chunks):
        if len(chunk.strip()) < 20:
            continue
        doc_id = hashlib.md5(
            f"learning:{filepath}:{i}".encode()
        ).hexdigest()
        try:
            embedding = get_embedding(chunk)
            chunk_meta = {
                "source": str(filepath),
                "filename": filepath.name,
                "subject": str(metadata.get("subject", "")),
                "difficulty": str(metadata.get("difficulty", "")),
                "status": str(metadata.get("status", "")),
                "tags": tags_str,
                "created": str(metadata.get("created", "")),
                "chunk_index": i,
            }
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[chunk_meta],
            )
            ingested += 1
        except Exception as e:
            print(f"  WARNING: chunk {i} 向量化失败: {e}")

    return ingested


def ingest_all():
    collection = get_learning_collection()
    cache = load_cache()
    total_files = 0
    total_chunks = 0
    total_skipped = 0

    if not LEARNING_DIR.exists():
        print(f"ERROR: learning dir not found: {LEARNING_DIR}")
        return

    subject_dirs = [d for d in LEARNING_DIR.iterdir() if d.is_dir()]
    if not subject_dirs:
        print(f"ERROR: no subject dirs under {LEARNING_DIR}")
        return

    for subject_dir in sorted(subject_dirs):
        files = list(subject_dir.glob("**/*.md"))
        if not files:
            continue
        print(f"[{subject_dir.name}] 检查 {len(files)} 个文件...")

        for f in sorted(files):
            try:
                fh = hashlib.md5(f.read_bytes()).hexdigest()
            except Exception:
                print(f"  WARNING: 无法读取 {f.name}，跳过")
                continue

            cached = cache.get(str(f))
            if cached == fh:
                print(f"  - {f.name} (unchanged, skipped)")
                total_skipped += 1
                continue

            count = ingest_file(f, collection)
            cache[str(f)] = fh
            if count > 0:
                print(f"  OK {f.name} -> {count} blocks ingested")
                total_chunks += count
                total_files += 1
            else:
                total_skipped += 1

    save_cache(cache)
    print(f"\nDone: {total_files} files processed")
    print(f"   {total_chunks} chunks ingested, {total_skipped} skipped (unchanged)")
    print(f"   learning_materials collection has {collection.count()} records")


if __name__ == "__main__":
    print("[INGEST] 开始处理学习材料...")
    ingest_all()
