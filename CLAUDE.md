# CLAUDE.md - HF-Agent-Infinite

## Project Overview

**PROMETHEUS** - The All-Seeing HF Intelligence

A fully autonomous, self-healing intelligence system for the Hugging Face ecosystem. Crawls, indexes, and monitors all HF resources with zero manual intervention.

## Architecture

```
HF-Agent-Infinite/
├── core/                    # Core modules
│   ├── agent.py            # HFAgent - main intelligence
│   ├── api.py              # FastAPI REST interface
│   ├── knowledge_base/     # Vector search (FAISS)
│   ├── tasks/              # Task orchestration
│   └── utils/              # Utilities
├── scripts/                 # Automation
│   ├── infinite_crawler.py # Perpetual crawler
│   └── watchdog.py         # Self-healing monitor
├── agents/                  # Agent profiles
├── configs/                 # Configuration
├── data/                    # Storage
└── main.py                  # Entry point
```

## Key Commands

```bash
# Interactive mode
python main.py

# Crawl HF resources
python main.py crawl
python main.py crawl --type models --limit 1000

# Search
python main.py search "llama gguf"
python main.py search "code generation" --semantic

# Start API server
python main.py serve

# Start all services
python main.py daemon

# View stats
python main.py stats
```

## API Endpoints

- `GET /` - System info
- `GET /health` - Health check
- `GET /stats` - Statistics
- `POST /search` - Search resources
- `POST /crawl` - Trigger crawl
- `GET /models` - List models
- `GET /datasets` - List datasets
- `GET /spaces` - List spaces

## Configuration

Edit `configs/agent_config.json` for:
- Crawl intervals
- Priority authors/tags
- Alert settings
- API configuration

## Dependencies

Core: `huggingface_hub`, `fastapi`, `uvicorn`
Search: `faiss-cpu`, `sentence-transformers`

## Development Notes

- Agent codename: PROMETHEUS
- Part of AI Council (alongside HYDRA, etc.)
- Designed for zero-cost deployment
- Self-healing with watchdog
- GitHub Actions for automated crawls
