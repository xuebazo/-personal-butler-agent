#!/usr/bin/env python3
"""
RAG 检索模块（本地 embedding 版），被 butler.py 调用
"""

from shared import config, collection, get_embedding


def retrieve(query: str, n_results: int = None) -> str:
    if collection.count() == 0:
        return "（知识库为空，请先运行 ingest.py 导入个人资料）"

    n = n_results or config["retrieval"]["n_results"]
    fetch_n = min(n * 3, collection.count())

    try:
        query_embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_n,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        return f"（检索失败: {e}）"

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    core_weight = config["retrieval"]["core_weight"]

    scored = []
    for doc, meta, dist in zip(docs, metas, distances):
        weight = core_weight if meta["type"] in ("core", "logs") else 1.0
        score = dist * weight
        scored.append((score, doc, meta))

    scored.sort(key=lambda x: x[0])
    top = scored[:n]

    parts = []
    for _, doc, meta in top:
        label = f"[{meta['type']} · {meta['filename']}]"
        parts.append(f"{label}\n{doc.strip()}")

    return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "我的性格特点"
    print(f"查询: {q}\n")
    print(retrieve(q))
