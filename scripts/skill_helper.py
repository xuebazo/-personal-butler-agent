#!/usr/bin/env python3
"""
CC Skill 适配层
被 Claude Code 的 /learning skill 调用，输出标准化格式供注入对话上下文。
用法: python skill_helper.py "查询内容" [--subject ml] [--status in-progress]
"""

import argparse
import sys

from query_learning import query_learning


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--subject", default=None)
    parser.add_argument("--difficulty", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("-n", type=int, default=None)
    args = parser.parse_args()

    try:
        result = query_learning(
            args.query,
            subject=args.subject,
            difficulty=args.difficulty,
            status=args.status,
            n_results=args.n,
        )
    except Exception as e:
        print(f"学习材料检索出错: {e}", file=sys.stderr)
        sys.exit(1)

    # stdout 输出正常结果（CC 读取）
    print(f"=== 学习材料检索结果 ===")
    print(f"查询: {args.query}")
    if args.subject:
        print(f"学科: {args.subject}")
    if args.status:
        print(f"状态: {args.status}")
    print()
    print(result)


if __name__ == "__main__":
    main()
