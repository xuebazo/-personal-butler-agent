#!/usr/bin/env python3
"""
聊天记录蒸馏脚本（DeepSeek 版）
用法: python distill.py
功能: 读取 knowledge/chats 下的原始聊天记录，
     用 DeepSeek 提炼出高质量性格洞察，
     输出到 core/distilled-insights.md，再统一入库。
     每次运行全量重新蒸馏，确保输出完整。
"""

from pathlib import Path
from datetime import datetime

from shared import config

from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        key = config["api"]["deepseek_key"]
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY env var is not set.")
        _client = OpenAI(
            api_key=key,
            base_url=config["api"]["deepseek_base_url"]
        )
    return _client

DISTILL_PROMPT = """你是一个信息提炼专家。我会给你一段 AI 对话记录。

请从中提取真正有洞察价值的信息，忽略对话的任务内容本身，只关注"这个人是怎样的人"。

提取维度：
1. 他明确表达的偏好或立场
2. 他隐含的思维模式（从他的问法、追问、措辞中推断）
3. 他对哪类回答表示满意或不满意（从他的反应推断）
4. 他反复出现的关注点或价值观

输出格式（每条一行，不要编号，不要废话）：
[偏好] 内容
[思维] 内容
[反感] 内容
[价值观] 内容

规则：
- 每条不超过 30 字
- 没有洞察价值的内容直接跳过
- 宁可少，不要凑数
- 如果整段对话没有有价值的信息，输出：无有效洞察

对话记录：
{chat_content}
"""

CHATS_DIR = Path.home() / ".butler" / "knowledge" / "chats"


def distill_file(filepath: Path) -> list[str]:
    """蒸馏单个聊天文件，返回洞察条目列表"""
    text = filepath.read_text(encoding="utf-8").strip()
    if not text or len(text) < 100:
        return []

    max_chars = 6000
    segments = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
    all_insights = []

    for seg in segments:
        try:
            response = _get_client().chat.completions.create(
                model=config["models"]["chat"],
                max_tokens=800,
                messages=[{
                    "role": "user",
                    "content": DISTILL_PROMPT.format(chat_content=seg)
                }]
            )
            result = response.choices[0].message.content.strip()
            if "无有效洞察" not in result:
                lines = [l.strip() for l in result.split("\n") if l.strip() and l.startswith("[")]
                all_insights.extend(lines)
        except Exception as e:
            print(f"  ✗ 蒸馏失败: {filepath.name} ({e})")

    return all_insights


def distill_all():
    output_file = Path.home() / ".butler" / "core" / "distilled-insights.md"

    if not CHATS_DIR.exists():
        print("✗ chats 目录不存在")
        return

    files = list(CHATS_DIR.glob("**/*.txt")) + list(CHATS_DIR.glob("**/*.md"))
    if not files:
        print("✗ 没有找到聊天记录文件")
        return

    print(f"🔍 开始蒸馏 {len(files)} 个聊天文件...\n")

    all_insights = []
    processed = 0

    for f in files:
        print(f"  处理: {f.name}")
        insights = distill_file(f)
        if insights:
            all_insights.extend(insights)
            print(f"  ✓ 提炼出 {len(insights)} 条洞察")
        else:
            print(f"  - 无有效洞察")
        processed += 1

    if not all_insights:
        print("\n没有提炼到任何洞察。")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"# 聊天记录蒸馏洞察\n\n> 最后更新：{timestamp}，共 {len(all_insights)} 条\n\n"
    content = header + "\n".join(all_insights)
    output_file.write_text(content, encoding="utf-8")

    print(f"\n✅ 蒸馏完成")
    print(f"   处理 {processed} 个文件")
    print(f"   共 {len(all_insights)} 条洞察")
    print(f"   已写入: {output_file}")
    print(f"\n提示：运行 ingest.py 将蒸馏结果入库")


if __name__ == "__main__":
    distill_all()
