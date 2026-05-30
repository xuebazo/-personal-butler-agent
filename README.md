# Personal Butler Agent

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
│   ├── distill.py             # Chat log → personality insights
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
