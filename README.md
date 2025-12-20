# HF-Agent-Infinite: PROMETHEUS

```
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗   ║
║   ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║   ║
║   ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║   ║
║   ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║   ║
║   ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║   ║
║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ║
║                                                                   ║
║   The All-Seeing HF Intelligence | By Phantom Engineer            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

> **"One agent to rule them all. Absolute dedication. Infinite intricacy."**

PROMETHEUS is a fully autonomous, self-healing intelligence system for the Hugging Face ecosystem. It crawls, indexes, and monitors all HF resources—models, datasets, spaces, and papers—with zero manual intervention.

**By DeadManOfficial | Phantom Engineer**

---

## Features

- **Infinite Crawling** - Perpetual monitoring of all HF resources
- **Semantic Search** - Vector-based similarity search using FAISS
- **Priority Monitoring** - Track specific authors and tags
- **Self-Healing** - Auto-restart on failures with exponential backoff
- **REST API** - FastAPI-powered interface for all operations
- **Zero Cost** - Runs entirely on free-tier infrastructure

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/DeadManOfficial/HF-Agent-Infinite.git
cd HF-Agent-Infinite

# Install dependencies
pip install -r requirements.txt

# Run interactive mode
python main.py
```

### Basic Usage

```bash
# Start interactive mode
python main.py

# Run a full crawl
python main.py crawl

# Search for models
python main.py search "llama gguf quantized"

# Semantic search
python main.py search "code generation" --semantic

# Start API server
python main.py serve

# Start all services (daemon mode)
python main.py daemon

# View statistics
python main.py stats
```

### API Usage

```bash
# Start the server
python main.py serve

# Health check
curl http://localhost:8000/health

# Search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "llama", "limit": 10}'

# Trigger crawl
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"resource_type": "models", "limit": 1000}'

# Get statistics
curl http://localhost:8000/stats
```

## Architecture

```
HF-Agent-Infinite/
├── core/                    # Core agent modules
│   ├── agent.py            # Main HFAgent class
│   ├── api.py              # FastAPI REST interface
│   ├── knowledge_base/     # Vector search & storage
│   ├── tasks/              # Task orchestration
│   └── utils/              # Utilities & helpers
├── scripts/                 # Automation scripts
│   ├── infinite_crawler.py # Perpetual crawler
│   └── watchdog.py         # Self-healing monitor
├── agents/                  # Agent profiles
│   └── PROMETHEUS.md       # Agent documentation
├── configs/                 # Configuration files
├── data/                    # Data storage
│   ├── raw/                # Raw crawl data
│   ├── processed/          # Processed data
│   └── embeddings/         # FAISS indices
├── .github/workflows/       # GitHub Actions
└── main.py                  # Entry point
```

## Configuration

Edit `configs/agent_config.json`:

```json
{
  "crawl_interval_hours": 1,
  "max_items_per_crawl": 10000,
  "priority_authors": ["DavidAU", "Nymbo", "TheBloke"],
  "priority_tags": ["llm", "gguf", "quantized"],
  "enable_alerts": true
}
```

## Free Deployment Options

### Option 1: GitHub Actions (Recommended)

The repository includes a GitHub Actions workflow that runs daily crawls for free:

1. Fork this repository
2. Add `HF_TOKEN` secret (optional, for private models)
3. Enable Actions in your fork
4. Crawls run automatically at midnight UTC

### Option 2: Hugging Face Spaces

Deploy as a Gradio app on HF Spaces (free):

```python
# app.py for HF Spaces
import gradio as gr
from core.agent import HFAgent

agent = HFAgent()

def search(query):
    results = agent.search(query, "all", 10)
    return results

gr.Interface(fn=search, inputs="text", outputs="json").launch()
```

### Option 3: Oracle Cloud Free Tier

1. Sign up for Oracle Cloud Free Tier (4 ARM cores, 24GB RAM forever)
2. Clone repository and install dependencies
3. Run `python main.py daemon`

### Option 4: Replit + UptimeRobot

1. Import repository to Replit
2. Run `python main.py serve`
3. Use UptimeRobot (free) to ping every 5 minutes

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | System info |
| `/health` | GET | Health check |
| `/stats` | GET | Statistics |
| `/search` | POST | Search resources |
| `/crawl` | POST | Trigger crawl |
| `/models` | GET | List models |
| `/datasets` | GET | List datasets |
| `/spaces` | GET | List spaces |
| `/priority` | GET | Priority resources |
| `/tasks` | GET | Task status |
| `/export` | GET | Export knowledge |

## Integration with AI Council

PROMETHEUS is part of the Phantom Engineer's AI Council:

- **HYDRA** - Content multiplication
- **PROMETHEUS** - HF intelligence (this agent)
- **SARAH_CLIPPING** - Video clipping
- **MARCUS_VISUALS** - Visual design
- **SEXYO** - SEO optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) for details.

---

**Created by Phantom Engineer | DeadManOfficial**

*"The eye that never sleeps. The mind that never forgets."*
