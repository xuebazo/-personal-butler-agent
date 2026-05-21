#!/usr/bin/env python3
"""
个人管家 Agent · DeepSeek + 本地 embedding 版

用法:
  python butler.py              # 交互对话模式
  python butler.py "问一个问题"  # 单次查询

对话中的特殊命令:
  bad      对上一条回答不满意，触发反馈学习
  reload   重新加载知识库
  clear    清空当前对话历史
  exit     退出
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

from shared import config
from query import retrieve

from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        key = config["api"]["deepseek_key"]
        if not key:
            print("ERROR: DEEPSEEK_API_KEY env var is not set.")
            print("Set it via: set DEEPSEEK_API_KEY=sk-... (Windows) or export DEEPSEEK_API_KEY=... (Unix)")
            sys.exit(1)
        _client = OpenAI(
            api_key=key,
            base_url=config["api"]["deepseek_base_url"]
        )
    return _client


scripts_dir = Path(__file__).parent

logs_dir = Path(config["paths"]["logs"]).expanduser()
logs_dir.mkdir(parents=True, exist_ok=True)


# ─── 人格加载 ────────────────────────────────────────────

def load_persona() -> str:
    persona_file = Path.home() / ".butler" / "core" / "persona-prompt.md"
    if persona_file.exists():
        return persona_file.read_text(encoding="utf-8").strip()
    return "你是这个人的专属个人管家，回答要精准、克制、有用，符合他的表达习惯。"


# ─── 隐含需求推理 ────────────────────────────────────────

INTENT_PROMPT = """你非常了解这个人。他刚刚发来一条消息。

他的消息："{user_input}"

请用一句话推断：他表面在问/要X，但结合他的背景，他真正想得到的是什么？

只输出你的推断，格式：
真实意图：[一句话]

如果表面意图和真实意图完全一致，输出：
真实意图：与字面一致"""


def infer_intent(user_input: str, context: str) -> str:
    """推断用户的隐含意图"""
    try:
        response = _get_client().chat.completions.create(
            model=config["models"]["chat"],
            max_tokens=150,
            messages=[
                {"role": "system", "content": f"你了解这个人的背景：\n{context}"},
                {"role": "user", "content": INTENT_PROMPT.format(user_input=user_input)}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [WARN] intent inference failed (fallback to literal): {e}")
        return "真实意图：与字面一致"


# ─── 系统提示构建 ─────────────────────────────────────────

def build_system_prompt(context: str, inferred_intent: str) -> str:
    persona = load_persona()

    return f"""{persona}

---

## 当前召回的相关个人背景

{context}

---

## 对他这次提问的意图分析

{inferred_intent}

如果推断的真实意图与字面不同，优先基于真实意图来回答。
回答结束后，如果你基于了不同于字面的理解，用一句话说明："我理解你真正想要的是……，对吗？"

---

## 行为准则

- 不要询问他已在资料中说明过的背景
- 自然融入对他的了解，不要说"根据你的资料"
- 保持管家风格：精准、克制、不废话
- 如对他某个偏好不确定，给出判断而不是反问
""".strip()


# ─── 学习闭环：对话洞察记录 ─────────────────────────────

SESSION_SUMMARY_PROMPT = """以下是刚刚结束的一段对话记录。

{conversation}

请从这段对话中提炼出对这个人的新洞察（如果有的话）。
关注：他的反应模式、隐含偏好、满意/不满意的信号、新出现的关注点。

输出格式（每条一行）：
[洞察] 内容（不超过30字）

如果这段对话没有新的洞察价值，输出：无新洞察"""


def save_session_insights(history: list):
    """对话结束后，提炼洞察并写入日志"""
    if len(history) < 2:
        return

    conversation = "\n".join([
        f"{'用户' if m['role'] == 'user' else '管家'}: {m['content']}"
        for m in history
    ])

    try:
        response = _get_client().chat.completions.create(
            model=config["models"]["chat"],
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": SESSION_SUMMARY_PROMPT.format(conversation=conversation)
            }]
        )
        result = response.choices[0].message.content.strip()

        if "无新洞察" in result:
            return

        insights = [l for l in result.split("\n") if l.strip().startswith("[洞察]")]
        if not insights:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = logs_dir / f"insights-{today}.md"
        is_new = not log_file.exists() or log_file.stat().st_size == 0

        timestamp = datetime.now().strftime("%H:%M")
        entry = f"\n## {timestamp}\n" + "\n".join(insights) + "\n"

        with open(log_file, "a", encoding="utf-8") as f:
            if is_new:
                f.write(f"# 对话洞察日志 · {today}\n")
            f.write(entry)

        print(f"\n（已记录 {len(insights)} 条新洞察到日志）")

    except Exception:
        pass  # 洞察记录失败不影响主流程


# ─── 负反馈机制 ──────────────────────────────────────────

FEEDBACK_PROMPT = """这个人对你刚才的回答不满意。

你的回答是：
{last_reply}

他说哪里不对：{feedback}

请：
1. 用一句话总结这次不满意揭示了什么偏好或规律
2. 给出修正后的回答

输出格式：
[学到] 一句话总结（将被记录到知识库）

[修正回答]
修正后的内容"""


def handle_bad_feedback(last_reply: str) -> str:
    """处理用户的不满意反馈"""
    try:
        feedback = input("  哪里不对？（简单说即可）: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""

    if not feedback:
        return ""

    try:
        response = _get_client().chat.completions.create(
            model=config["models"]["chat"],
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": FEEDBACK_PROMPT.format(
                    last_reply=last_reply,
                    feedback=feedback
                )
            }]
        )
        result = response.choices[0].message.content.strip()

        lines = result.split("\n")
        learned = next((l for l in lines if l.startswith("[学到]")), None)
        if learned:
            today = datetime.now().strftime("%Y-%m-%d")
            feedback_file = logs_dir / f"feedback-{today}.md"
            is_new = not feedback_file.exists() or feedback_file.stat().st_size == 0

            timestamp = datetime.now().strftime("%H:%M")
            entry = f"\n[{timestamp}] {learned}\n原始回答片段：{last_reply[:100]}...\n"
            with open(feedback_file, "a", encoding="utf-8") as f:
                if is_new:
                    f.write(f"# 负反馈记录 · {today}\n")
                f.write(entry)

        corrected_start = result.find("[修正回答]")
        if corrected_start != -1:
            return result[corrected_start + len("[修正回答]"):].strip()
        return result

    except Exception as e:
        return f"（处理反馈失败: {e}）"


# ─── 主对话循环 ───────────────────────────────────────────

def chat():
    print("╭─────────────────────────────────────╮")
    print("│  个人管家已就位（DeepSeek + 本地向量）│")
    print("│  bad · reload · clear · exit        │")
    print("╰─────────────────────────────────────╯\n")

    history = []
    last_reply = ""

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n正在保存本次对话洞察...")
            save_session_insights(history)
            print("再见。")
            break

        if not user_input:
            continue

        # ── 特殊命令 ──
        if user_input.lower() == "exit":
            print("正在保存本次对话洞察...")
            save_session_insights(history)
            print("再见。")
            break

        if user_input.lower() == "clear":
            save_session_insights(history)
            history.clear()
            last_reply = ""
            print("（对话历史已清空，洞察已保存）\n")
            continue

        if user_input.lower() == "reload":
            print("正在更新知识库...")
            result = subprocess.run(
                [sys.executable, str(scripts_dir / "ingest.py")],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(result.stdout)
                print("✓ 知识库已更新\n")
            else:
                print(f"✗ 更新失败:\n{result.stderr}\n")
            continue

        if user_input.lower() == "bad":
            if not last_reply:
                print("（还没有可以反馈的回答）\n")
                continue
            print("收到，告诉我哪里不对：")
            corrected = handle_bad_feedback(last_reply)
            if corrected:
                print(f"\n管家（修正）: {corrected}\n")
                last_reply = corrected
                history.append({"role": "assistant", "content": f"[修正] {corrected}"})
            continue

        # ── 正常对话流程（只检索一次）──
        context = retrieve(user_input)
        inferred_intent = infer_intent(user_input, context)
        system = build_system_prompt(context, inferred_intent)

        history.append({"role": "user", "content": user_input})

        try:
            messages = [{"role": "system", "content": system}] + history
            response = _get_client().chat.completions.create(
                model=config["models"]["chat"],
                max_tokens=2000,
                messages=messages
            )
            reply = response.choices[0].message.content
            history.append({"role": "assistant", "content": reply})
            last_reply = reply
            print(f"\n管家: {reply}\n")

        except Exception as e:
            print(f"\n✗ 调用失败: {e}\n")
            history.pop()


def single_query(question: str):
    context = retrieve(question)
    inferred_intent = infer_intent(question, context)
    system = build_system_prompt(context, inferred_intent)
    try:
        response = _get_client().chat.completions.create(
            model=config["models"]["chat"],
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question}
            ]
        )
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"✗ 调用失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        single_query(" ".join(sys.argv[1:]))
    else:
        chat()
