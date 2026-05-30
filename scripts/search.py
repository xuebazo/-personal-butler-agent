#!/usr/bin/env python3
"""
联网搜索模块（Tavily API）
被 butler.py 调用，提供 should_search() / search() / format_search_results()
"""

import time
import requests
from shared import config

TAVILY_URL = "https://api.tavily.com/search"


def should_search(query: str) -> bool:
    """检查用户输入是否命中触发关键词"""
    keywords = config.get("search", {}).get("trigger_keywords", [])
    if not keywords:
        return False
    return any(kw in query for kw in keywords)


def search(query: str) -> dict | None:
    """调用 Tavily API 执行搜索，失败返回 None"""
    api_key = config.get("search", {}).get("api_key", "")
    if not api_key:
        return None

    timeout = config.get("search", {}).get("timeout", 10)
    max_results = config.get("search", {}).get("max_results", 5)

    try:
        response = requests.post(
            TAVILY_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": max_results,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def format_search_results(data: dict, max_results: int = 5) -> str:
    """将 Tavily 返回的 JSON 格式化为 prompt-ready 字符串"""
    if not data:
        return ""

    parts = ["[网络搜索]"]

    answer = data.get("answer", "").strip()
    if answer:
        parts.append(f"摘要：{answer}")

    results = data.get("results", [])[:max_results]
    if results:
        parts.append("\n相关链接：")
        for i, r in enumerate(results, 1):
            title = r.get("title", "").strip()
            url = r.get("url", "").strip()
            content = r.get("content", "").strip()
            if title and url:
                parts.append(f"  {i}. {title}\n     {url}")
            if content:
                parts.append(f"     {content[:300]}")

    return "\n".join(parts)


if __name__ == "__main__":
    q = " ".join(__import__("sys").argv[1:]) or "比特币最新价格"
    print(f"查询: {q}")
    if not should_search(q):
        print("（未触发搜索）")
    else:
        print("触发搜索...")
        start = time.time()
        data = search(q)
        elapsed = (time.time() - start) * 1000
        print(f"耗时: {elapsed:.0f}ms\n")
        if data:
            print(format_search_results(data))
        else:
            print("搜索失败（网络异常或 API Key 未配置）")
