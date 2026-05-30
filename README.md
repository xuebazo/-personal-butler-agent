# Personal Butler Agent | 个人管家

> **English** | [中文](#中文)

A personal digital twin that learns who you are — and becomes you.

Unlike generic chatbots that treat every user the same, this agent builds a structured understanding of **you specifically**: your thinking style, communication preferences, emotional patterns, and behavioral rhythms. The more you use it, the more it resembles you.

> **Status:** V2.5 active — RAG + Web Search + Learning Database + Claude Code Skill
> **Roadmap:** V3.0 adds personality profiling, layered memory, and dual-mode (companion / proxy)

## What Makes This Different

| | Generic Chatbot | RAG Chatbot | **Personal Butler** |
|---|---|---|---|
| Knows your background | No | Minimal | Deep (about-me + conversation insights) |
| Mimics your tone | No | No | Yes (persona prompt + style fingerprint) |
| Learns your preferences | No | No | Yes (auto-extracted from every conversation) |
| Isolates personal vs learning data | N/A | N/A | Yes (separate vector collections) |
| Evolves over time | No | No | Yes (insight accumulation + temporal tracking) |
| Can work as you | No | No | Planned (V3.3 proxy mode) |

## Features

**Personal Knowledge Base**
RAG retrieval against your personal documents, weighted by importance. Core files (about-me, persona prompt) get highest priority.

**Web Search (Manual)**
Toggle on/off manually. Uses Tavily API. Search results can be saved to your knowledge base with one command — not auto-saved, you decide what stays.

**Learning Materials Database**
Independent vector collection for study notes, tutorials, paper summaries. Supports YAML frontmatter metadata (subject, difficulty, status, tags) for filtered retrieval.

**Claude Code Integration**
`/learning` skill lets you search your learning materials directly inside Claude Code conversations. Lightweight — no persona data exposed.

**Insight Accumulation**
Every conversation automatically generates insights about your patterns, preferences, and reaction signals. Stored in daily logs, ingested into the knowledge base.

**Feedback Loop**
Unsatisfactory response? Type `bad`, explain what's wrong. The system learns the correction and records the pattern for future use.

**Dual Interface**
- CLI: `python scripts/butler.py` — full-featured, scriptable
- WebUI: `streamlit run scripts/webui.py` — chat interface with sidebar controls

## Architecture

```
User Input
  │
  ├── Personal Knowledge Retrieval     (personal_context collection)
  ├── Learning Materials Retrieval     (learning_materials collection)
  ├── Web Search                       (Tavily API, manual toggle only)
  │
  ├── Intent Inference                 (real needs behind surface questions)
  ├── Context Assembly                 (persona + retrieved + searched + intent)
  │
  └── LLM Response                     (DeepSeek V4-Pro)
        │
        ├── Session Insights           (auto-extracted, logged)
        └── Feedback Learning          (on 'bad' command)
```

## Quick Start

```powershell
# 1. Install
pip install -r requirements.txt

# 2. API Keys (one-time, persistent)
setx DEEPSEEK_API_KEY "sk-your-key"
setx TAVILY_API_KEY "tvly-your-key"        # optional: web search

# 3. Create your personal files
copy core\about-me.example.md core\about-me.md
copy core\persona-prompt.example.md core\persona-prompt.md

# 4. Fill in about-me.md (most important step)

# 5. Ingest
python scripts\ingest.py

# 6. Start
python scripts\butler.py                    # CLI mode
streamlit run scripts\webui.py              # Web UI
```

## Data Architecture

### Vector Collections

| Collection | Source | Purpose | Isolated |
|---|---|---|---|
| `personal_context` | core/, knowledge/, logs/ | Who you are | — |
| `learning_materials` | knowledge/learning/ | What you've learned | Yes |

### File Layout

```
~/.butler/
├── config.yaml
├── scripts/
│   ├── butler.py              # Main agent (CLI + conversation loop)
│   ├── webui.py               # Streamlit web interface
│   ├── shared.py              # Config, ChromaDB, embedding model
│   ├── ingest.py              # Personal knowledge ingestion
│   ├── query.py               # Personal knowledge retrieval
│   ├── ingest_learning.py     # Learning materials ingestion
│   ├── query_learning.py      # Learning materials retrieval
│   ├── search.py              # Tavily web search
│   ├── distill.py             # Chat log -> personality insights
│   └── skill_helper.py        # Claude Code skill adapter
│
├── core/
│   ├── about-me.example.md
│   └── persona-prompt.example.md
│
├── knowledge/
│   ├── notes/                 # Personal notes
│   ├── chats/                 # Chat logs (for distillation)
│   ├── other/                 # Saved web search results + misc
│   └── learning/              # Study materials (with YAML frontmatter)
│       ├── ml/
│       ├── systems/
│       └── ...
│
├── vectordb/                  # ChromaDB storage (gitignored)
├── logs/                      # Insights + feedback (gitignored)
└── .claude/skills/
    └── learning.md            # Claude Code skill definition
```

## CLI Commands

| Command | Action |
|---|---|
| `bad` | Flag unsatisfactory response, trigger correction learning |
| `search` | Toggle web search on/off (default: off) |
| `save` | Save last search results to knowledge base |
| `reload` | Hot-reload knowledge base (re-run ingest) |
| `clear` | Clear conversation history (insights saved) |
| `exit` | Quit (insights saved) |

## Learning Materials Format

Files in `knowledge/learning/` require YAML frontmatter:

```yaml
---
subject: ml                          # ml, systems, math, ...
difficulty: intermediate             # beginner, intermediate, advanced
status: in-progress                  # to-read, in-progress, completed, archived
tags: [transformer, attention, nlp]
source: "Attention Is All You Need"
created: 2026-05-28
---

# Content starts here
```

Without frontmatter, the file is skipped during ingestion.

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | DeepSeek V4-Pro (via OpenAI SDK) |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 (local, 384-dim) |
| Vector DB | ChromaDB (cosine distance, HNSW index) |
| Web Search | Tavily Search API |
| Web UI | Streamlit |
| CC Integration | Claude Code Skill |

## Privacy

- All data stored locally in `~/.butler/`
- API keys passed via environment variables, never stored in code or config files
- Personal files (about-me, persona-prompt, knowledge/, logs/) are gitignored
- Template files (.example.md) are safe to share publicly
- Web search is manual-only — no auto-trigger, no accidental data leakage

## Roadmap

| Version | Focus | Status |
|---|---|---|
| V2.1 | RAG + Web Search + Web UI | Done |
| V2.5 | Learning Database + CC Skill | In Progress |
| V3.0 | Personality Profiler + Layered Memory + Dual Mode | Planned |
| V3.1 | State Tracking + Emotion Sensing | Planned |
| V3.2 | Evolution Engine + Cyclical Reflection | Planned |
| V3.3 | Prediction + Proxy Mode | Planned |

See [docs/expansion-design-review.md](docs/expansion-design-review.md) for detailed design.

## License

MIT

---

<a name="中文"></a>

# 个人管家 | Personal Butler Agent

一个个人数字孪生，学习你是谁——然后成为你。

和那些对所有用户一视同仁的通用聊天机器人不同，这个 Agent 会构建对**你个人**的结构化理解：你的思维方式、沟通偏好、情绪模式、行为节奏。用得越久，越像你。

> **当前版本:** V2.5 — RAG 检索 + 联网搜索 + 学习材料库 + Claude Code 技能
> **路线图:** V3.0 加入人格侧写、分层记忆、双模式（陪伴 / 代理）

## 和其他方案有什么不同

| | 通用聊天机器人 | RAG 聊天机器人 | **个人管家** |
|---|---|---|---|
| 了解你的背景 | 否 | 极少 | 深度（about-me + 对话洞察） |
| 模仿你的语气 | 否 | 否 | 是（人格提示 + 风格指纹） |
| 学习你的偏好 | 否 | 否 | 是（每轮对话自动提取） |
| 个人数据与学习数据隔离 | 无 | 无 | 是（独立向量集合） |
| 随时间进化 | 否 | 否 | 是（洞察积累 + 时间追踪） |
| 能替你工作 | 否 | 否 | 计划中（V3.3 代理模式） |

## 功能

**个人知识库**
基于个人文档的 RAG 检索，按重要性加权。核心文件（about-me、人格提示）优先级最高。

**联网搜索（手动触发）**
手动开关控制，使用 Tavily API。搜索结果可一键保存到知识库——不自动保存，由你决定留下什么。

**学习材料库**
独立向量集合，存放学习笔记、教程、论文摘要。支持 YAML 前置元数据（学科、难度、状态、标签），可按条件过滤检索。

**Claude Code 集成**
`/learning` 技能让你在 Claude Code 对话中直接搜索学习材料。轻量级——不暴露人格数据。

**洞察积累**
每轮对话自动生成洞察：你的模式、偏好、反应信号。存入每日日志，导入知识库。

**反馈学习**
回答不满意？输入 `bad`，说明哪里不好。系统学习修正并记录模式，下次改进。

**双界面**
- CLI: `python scripts/butler.py` — 全功能，可脚本化
- WebUI: `streamlit run scripts/webui.py` — 带侧栏控制的聊天界面

## 架构

```
用户输入
  │
  ├── 个人知识检索               (personal_context 集合)
  ├── 学习材料检索               (learning_materials 集合)
  ├── 联网搜索                   (Tavily API，仅手动触发)
  │
  ├── 意图推断                   (表面问题背后的真实需求)
  ├── 上下文组装                 (人格 + 检索结果 + 搜索结果 + 意图)
  │
  └── LLM 回复                   (DeepSeek V4-Pro)
        │
        ├── 会话洞察             (自动提取，记录日志)
        └── 反馈学习             (输入 'bad' 时触发)
```

## 快速开始

```powershell
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（一次性，持久化）
setx DEEPSEEK_API_KEY "sk-your-key"
setx TAVILY_API_KEY "tvly-your-key"        # 可选：联网搜索

# 3. 创建个人文件
copy core\about-me.example.md core\about-me.md
copy core\persona-prompt.example.md core\persona-prompt.md

# 4. 填写 about-me.md（最关键的一步）

# 5. 导入知识库
python scripts\ingest.py

# 6. 启动
python scripts\butler.py                    # CLI 模式
streamlit run scripts\webui.py              # Web 界面
```

## 数据架构

### 向量集合

| 集合 | 数据来源 | 用途 | 隔离 |
|---|---|---|---|
| `personal_context` | core/, knowledge/, logs/ | 你是谁 | — |
| `learning_materials` | knowledge/learning/ | 你学了什么 | 是 |

### 目录结构

```
~/.butler/
├── config.yaml
├── scripts/
│   ├── butler.py              # 主 Agent（CLI + 对话循环）
│   ├── webui.py               # Streamlit Web 界面
│   ├── shared.py              # 配置、ChromaDB、Embedding 模型
│   ├── ingest.py              # 个人知识入库
│   ├── query.py               # 个人知识检索
│   ├── ingest_learning.py     # 学习材料入库
│   ├── query_learning.py      # 学习材料检索
│   ├── search.py              # Tavily 联网搜索
│   ├── distill.py             # 聊天日志 → 人格洞察
│   └── skill_helper.py        # Claude Code 技能适配
│
├── core/
│   ├── about-me.example.md
│   └── persona-prompt.example.md
│
├── knowledge/
│   ├── notes/                 # 个人笔记
│   ├── chats/                 # 聊天记录（用于蒸馏）
│   ├── other/                 # 保存的搜索结果 + 杂项
│   └── learning/              # 学习材料（需 YAML 前置元数据）
│       ├── ml/
│       ├── systems/
│       └── ...
│
├── vectordb/                  # ChromaDB 存储（已 gitignore）
├── logs/                      # 洞察 + 反馈日志（已 gitignore）
└── .claude/skills/
    └── learning.md            # Claude Code 技能定义
```

## CLI 命令

| 命令 | 作用 |
|---|---|
| `bad` | 标记不满意回答，触发修正学习 |
| `search` | 切换联网搜索开关（默认关闭） |
| `save` | 将上次搜索结果保存到知识库 |
| `reload` | 热重载知识库（重新运行 ingest） |
| `clear` | 清空对话历史（洞察已保存） |
| `exit` | 退出（洞察已保存） |

## 学习材料格式

`knowledge/learning/` 下的文件需要 YAML 前置元数据：

```yaml
---
subject: ml                          # 学科：ml, systems, math, ...
difficulty: intermediate             # 难度：beginner, intermediate, advanced
status: in-progress                  # 状态：to-read, in-progress, completed, archived
tags: [transformer, attention, nlp]
source: "Attention Is All You Need"
created: 2026-05-28
---

# 正文从这里开始
```

没有 frontmatter 的文件在入库时会被跳过。

## 技术栈

| 层级 | 技术 |
|---|---|
| LLM | DeepSeek V4-Pro（OpenAI SDK） |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2（本地，384 维） |
| 向量数据库 | ChromaDB（余弦距离，HNSW 索引） |
| 联网搜索 | Tavily Search API |
| Web 界面 | Streamlit |
| CC 集成 | Claude Code Skill |

## 隐私

- 所有数据本地存储在 `~/.butler/`
- API Key 通过环境变量传递，不在代码或配置文件中存储
- 个人文件（about-me、persona-prompt、knowledge/、logs/）已 gitignore
- 模板文件（.example.md）可安全公开分享
- 联网搜索仅手动触发——不会自动触发，不会意外泄露数据

## 路线图

| 版本 | 重点 | 状态 |
|---|---|---|
| V2.1 | RAG + 联网搜索 + Web 界面 | 已完成 |
| V2.5 | 学习材料库 + Claude Code 技能 | 进行中 |
| V3.0 | 人格侧写器 + 分层记忆 + 双模式 | 计划中 |
| V3.1 | 状态追踪 + 情绪感知 | 计划中 |
| V3.2 | 进化引擎 + 循环反思 | 计划中 |
| V3.3 | 预测 + 代理模式 | 计划中 |

详细设计见 [docs/expansion-design-review.md](docs/expansion-design-review.md)。

## 许可证

MIT
