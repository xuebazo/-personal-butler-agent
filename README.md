# Personal Butler Agent

A Persona-Grounded RAG Agent that learns who you are and answers in your voice.

Local-first. All offline except LLM API calls.

## Architecture

```
User Input → RAG Retrieval → Intent Inference → Context Assembly → LLM → Response
                                ↑
                        Persona Prompt + Personal Knowledge Base
```

## Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your DeepSeek API key (permanent, one-time)
setx DEEPSEEK_API_KEY "sk-your-key-here"

# 3. Create your personal files from templates
copy core\about-me.example.md core\about-me.md
copy core\persona-prompt.example.md core\persona-prompt.md

# 4. Fill in core/about-me.md with your personal information
#    This is the most important step — see template for structure

# 5. Ingest your data
python scripts\ingest.py

# 6. Start the butler
python scripts\butler.py
```

## Commands (in-chat)

| Command | Action |
|---------|--------|
| `bad` | Flag unsatisfactory response, trigger feedback learning |
| `reload` | Hot-reload knowledge base without restarting |
| `clear` | Clear conversation history (insights auto-saved) |
| `exit` | Quit (insights auto-saved) |

## Project Structure

```
.butler/
├── config.yaml              # Model & retrieval config (API key via env var)
├── requirements.txt
├── scripts/
│   ├── shared.py            # Shared: config loader, ChromaDB, embedding model
│   ├── butler.py            # Main agent entry point
│   ├── ingest.py            # Document ingestion with Chinese chunking
│   ├── query.py             # RAG retrieval with core-weighted ranking
│   └── distill.py           # Chat log distillation → personality insights
├── core/
│   ├── about-me.example.md       # Template — copy and fill in
│   └── persona-prompt.example.md # Template — copy and fill in
├── knowledge/               # Your personal documents (gitignored)
│   ├── notes/
│   ├── chats/
│   └── other/
├── vectordb/                # ChromaDB storage (gitignored, auto-created)
└── logs/                    # Session insights & feedback (gitignored)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | DeepSeek (`deepseek-v4-pro`) via OpenAI SDK |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` (local, ~120MB) |
| Vector DB | ChromaDB (local PersistentClient, cosine distance) |
| Runtime | Python 3.13+ |

## Privacy

- All data stored locally in `~/.butler/`
- API key passed via `DEEPSEEK_API_KEY` environment variable
- Personal files (`about-me.md`, `persona-prompt.md`, `knowledge/`, `logs/`) are gitignored
- Template files (`.example.md`) are safe to share publicly

## License

MIT
