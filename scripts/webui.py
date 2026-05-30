#!/usr/bin/env python3
"""
个人管家 Agent · Streamlit 网页界面
用法: streamlit run webui.py
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

import streamlit as st

scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

from shared import config
from query import retrieve
from search import should_search, search, format_search_results
from openai import OpenAI

# ── 页面配置 ──────────────────────────────────────────────

st.set_page_config(
    page_title="个人管家",
    page_icon="🫱",
    layout="centered",
    initial_sidebar_state="auto",
)

# ── 初始化会话状态 ────────────────────────────────────────

DEFAULTS = {
    "history": [],
    "last_reply": "",
    "last_search_data": None,
    "last_search_query": "",
    "feedback_pending": False,
    "feedback_text": "",
    "insights_saved": False,
}


def init_state():
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_state()

# ── 客户端初始化（延迟）───────────────────────────────────


@st.cache_resource
def get_client():
    key = config["api"]["deepseek_key"]
    if not key:
        st.error("DEEPSEEK_API_KEY 环境变量未设置。请在终端执行 setx 后重启。")
        st.stop()
    return OpenAI(api_key=key, base_url=config["api"]["deepseek_base_url"])


client = get_client()

# ── 人格加载 ──────────────────────────────────────────────


@st.cache_data
def load_persona() -> str:
    persona_file = Path.home() / ".butler" / "core" / "persona-prompt.md"
    if persona_file.exists():
        return persona_file.read_text(encoding="utf-8").strip()
    return "你是这个人的专属个人管家，回答要精准、克制、有用，符合他的表达习惯。"


# ── 核心函数（从 butler.py 复用逻辑）─────────────────────

INTENT_PROMPT = """你非常了解这个人。他刚刚发来一条消息。

他的消息："{user_input}"

请用一句话推断：他表面在问/要X，但结合他的背景，他真正想得到的是什么？

只输出你的推断，格式：
真实意图：[一句话]

如果表面意图和真实意图完全一致，输出：
真实意图：与字面一致"""


def infer_intent(user_input: str, context: str) -> str:
    try:
        response = client.chat.completions.create(
            model=config["models"]["chat"],
            max_tokens=150,
            messages=[
                {"role": "system", "content": f"你了解这个人的背景：\n{context}"},
                {"role": "user", "content": INTENT_PROMPT.format(user_input=user_input)},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"真实意图：与字面一致（推断失败: {e}）"


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


def generate_reply(messages: list) -> str:
    response = client.chat.completions.create(
        model=config["models"]["chat"],
        max_tokens=2000,
        messages=messages,
    )
    return response.choices[0].message.content


# ── 侧边栏：操作面板 ──────────────────────────────────────

with st.sidebar:
    st.title("个人管家")

    # 状态指示
    col1, col2 = st.columns(2)
    with col1:
        st.metric("对话轮次", len(st.session_state.history) // 2)
    with col2:
        st.metric("知识库", "就绪" if Path(config["paths"]["vectordb"]).expanduser().exists() else "空")

    st.divider()

    # 搜索状态
    if st.session_state.last_search_data:
        st.success(f"搜索结果可保存 · {st.session_state.last_search_query[:15]}...")
    else:
        st.caption("暂无搜索结果")

    # 操作按钮
    st.subheader("操作")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存搜索", use_container_width=True, disabled=not st.session_state.last_search_data):
            data = st.session_state.last_search_data
            q = st.session_state.last_search_query
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"search-{timestamp}.md"
            other_dir = Path(config["paths"]["knowledge"]).expanduser() / "other"
            other_dir.mkdir(parents=True, exist_ok=True)
            safe_q = q.replace("#", "＃").replace("\n", " ")
            content = f"# 搜索结果 · {safe_q}\n\n" + format_search_results(data)
            (other_dir / filename).write_text(content, encoding="utf-8")
            st.session_state.last_search_data = None
            st.toast(f"已保存: {filename}", icon="✅")
            st.rerun()

    with c2:
        if st.button("🔄 更新知识库", use_container_width=True):
            with st.spinner("正在更新知识库..."):
                result = subprocess.run(
                    [sys.executable, str(scripts_dir / "ingest.py")],
                    capture_output=True, text=True,
                )
                if result.returncode == 0:
                    st.toast("知识库已更新", icon="✅")
                else:
                    st.toast("更新失败", icon="❌")

    st.divider()

    # 不满意反馈
    st.subheader("反馈")
    if not st.session_state.last_reply:
        st.caption("对话后可使用")
    else:
        if st.button("👎 上次回答不满意", use_container_width=True):
            st.session_state.feedback_pending = True
            st.rerun()

        if st.session_state.feedback_pending:
            feedback = st.text_area("哪里不对？", key="fb_input", placeholder="简单说即可...")
            if st.button("提交反馈", use_container_width=True) and feedback.strip():
                with st.spinner("正在分析反馈..."):
                    fb_prompt = f"""这个人对你刚才的回答不满意。

你的回答是：
{st.session_state.last_reply}

他说哪里不对：{feedback}

请：
1. 用一句话总结这次不满意揭示了什么偏好或规律
2. 给出修正后的回答

输出格式：
[学到] 一句话总结

[修正回答]
修正后的内容"""
                    try:
                        resp = client.chat.completions.create(
                            model=config["models"]["chat"],
                            max_tokens=600,
                            messages=[{"role": "user", "content": fb_prompt}],
                        )
                        result = resp.choices[0].message.content
                        corrected = result
                        if "[修正回答]" in result:
                            corrected = result.split("[修正回答]", 1)[1].strip()
                        # 添加到历史
                        st.session_state.history.append(
                            {"role": "assistant", "content": f"[修正] {corrected}"}
                        )
                        st.session_state.last_reply = corrected
                        st.session_state.feedback_pending = False
                        st.toast("已修正", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"处理失败: {e}")

    st.divider()

    # 清空对话
    if st.button("🗑 清空对话", use_container_width=True):
        st.session_state.history = []
        st.session_state.last_reply = ""
        st.session_state.last_search_data = None
        st.session_state.feedback_pending = False
        st.rerun()

    st.divider()
    st.caption(f"模型: {config['models']['chat']}")
    st.caption(f"检索: {config['retrieval']['n_results']} 条 · 搜索: {'开' if config.get('search', {}).get('api_key', '') else '关'}")

# ── 主聊天区 ──────────────────────────────────────────────

# 欢迎语
if not st.session_state.history:
    st.markdown("""
    ### 管家已就位

    我是你的个人管家。我读过你的资料，了解你的偏好和思维方式。

    直接说你想说的——问问题、讨论想法、需要建议，都可以。
    """)

# 渲染历史消息
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("输入你的消息..."):
    # 添加用户消息
    st.session_state.history.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 1. 检索
        with st.spinner(""):
            context = retrieve(prompt)

        # 2. 联网搜索
        if should_search(prompt):
            with st.status("🔍 联网搜索中...") as status:
                search_data = search(prompt)
                if search_data:
                    sc = format_search_results(search_data)
                    context = context + "\n\n" + sc if context else sc
                    st.session_state.last_search_data = search_data
                    st.session_state.last_search_query = prompt
                    status.update(label="✓ 已获取搜索结果", state="complete")
                else:
                    status.update(label="搜索不可用，仅用本地知识", state="complete")

        # 3. 意图推断
        inferred = infer_intent(prompt, context)

        # 4. 系统提示
        system = build_system_prompt(context, inferred)

        # 5. LLM
        messages = [{"role": "system", "content": system}] + st.session_state.history
        reply = generate_reply(messages)

        st.markdown(reply)
        st.session_state.history.append({"role": "assistant", "content": reply})
        st.session_state.last_reply = reply

    st.rerun()

# ── 页脚 ──────────────────────────────────────────────────

st.divider()
st.caption("个人管家 Agent v2.1 · DeepSeek + 本地 ChromaDB · 所有数据存储在本地")
