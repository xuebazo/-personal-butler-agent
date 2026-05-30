#!/usr/bin/env python3
"""
学习材料检索模块（本地 embedding 版）
支持按 subject/difficulty/status 过滤，命令行和模块调用均可用。
"""

import argparse

from shared import config, get_embedding, get_learning_collection


def query_learning(
    query: str,
    subject: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
    n_results: int | None = None,
) -> str:
    """检索学习材料，支持 metadata 过滤。"""
    collection = get_learning_collection()

    if collection.count() == 0:
        return "（学习材料库为空，请先运行 ingest_learning.py 导入材料）"

    n = n_results or config.get("learning", {}).get("n_results", 5)

    # 构建 where 条件
    where: dict = {}
    if subject:
        where["subject"] = subject
    if difficulty:
        where["difficulty"] = difficulty
    if status:
        where["status"] = status

    try:
        query_embedding = get_embedding(query)
        query_args: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_args["where"] = where

        results = collection.query(**query_args)
    except Exception as e:
        return f"（学习材料检索失败: {e}）"

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return "（未找到相关内容）"

    parts = []
    for doc, meta, dist in zip(docs, metas, distances):
        label = f"[{meta.get('subject', '?')} · {meta.get('difficulty', '?')} · {meta.get('status', '?')}]"
        content = doc.strip()
        source = meta.get("source", "")
        tags = meta.get("tags", "")
        confidence = f" (相似度: {1 - dist:.2f})" if dist is not None else ""

        line = f"{label}{confidence}\n{content}"
        if source:
            line += f"\n来源: {source}"
        if tags:
            line += f" | 标签: {tags}"
        parts.append(line)

    return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="学习材料检索")
    parser.add_argument("query", help="检索关键词")
    parser.add_argument("--subject", default=None, help="按学科过滤")
    parser.add_argument("--difficulty", default=None, help="按难度过滤")
    parser.add_argument("--status", default=None, help="按状态过滤")
    parser.add_argument("-n", type=int, default=None, help="返回条数")
    args = parser.parse_args()

    print(f"查询: {args.query}\n")
    if args.subject:
        print(f"过滤: subject={args.subject}")
    if args.difficulty:
        print(f"过滤: difficulty={args.difficulty}")
    if args.status:
        print(f"过滤: status={args.status}")
    if args.subject or args.difficulty or args.status:
        print()

    result = query_learning(
        args.query,
        subject=args.subject,
        difficulty=args.difficulty,
        status=args.status,
        n_results=args.n,
    )
    print(result)
