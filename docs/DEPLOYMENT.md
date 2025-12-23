# PROMETHEUS Deployment Guide

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/DeadManOfficial/HF-Agent-Infinite.git
cd HF-Agent-Infinite

# Install dependencies
pip install -r requirements.txt

# Test the agent
python main.py stats

# Run a crawl
python main.py crawl --limit 100

# Start API server
python main.py serve
```

### Interactive Mode

```bash
python main.py

# Commands:
# - crawl      : Run full crawl
# - search <q> : Keyword search
# - semantic <q> : Semantic search (requires FAISS)
# - stats      : Show statistics
# - priority   : Show priority resources
# - export     : Export knowledge base
# - quit       : Exit
```

## Free Deployment Options

### Option 1: GitHub Actions (Recommended)

**Cost:** $0/month  
**Effort:** Minimal  
**Uptime:** Daily scheduled runs

1. Fork the repository
2. Enable GitHub Actions
3. (Optional) Add `HF_TOKEN` secret for private models
4. Workflow runs automatically at midnight UTC

The workflow is in `.github/workflows/daily_crawl.yml`

### Option 2: Oracle Cloud Free Tier

**Cost:** $0/month forever  
**Resources:** 4 ARM cores, 24GB RAM  
**Uptime:** 24/7

```bash
# Sign up at oracle.com/cloud/free
# Create ARM-based VM (Ampere A1)

# On the VM:
git clone https://github.com/DeadManOfficial/HF-Agent-Infinite.git
cd HF-Agent-Infinite
pip install -r requirements.txt

# Start all services
python main.py daemon

# Or use systemd for auto-restart
sudo cp deployment/prometheus.service /etc/systemd/system/
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

### Option 3: Hugging Face Spaces

**Cost:** $0/month  
**Uptime:** 24/7 (with activity)

Create `app.py`:

```python
import gradio as gr
from core.agent import HFAgent

agent = HFAgent()

def search_hf(query, limit=10):
    results = agent.search(query, "all", limit)
    return results

def crawl_hf(resource_type="models", limit=100):
    if resource_type == "models":
        return agent.crawl_models(limit)
    elif resource_type == "datasets":
        return agent.crawl_datasets(limit)
    return {}

def get_stats():
    return agent.get_stats()

with gr.Blocks(title="PROMETHEUS - HF Intelligence") as demo:
    gr.Markdown("# 🔥 PROMETHEUS - HF Intelligence System")
    
    with gr.Tab("Search"):
        query_input = gr.Textbox(label="Search Query")
        search_btn = gr.Button("Search")
        search_output = gr.JSON()
        search_btn.click(search_hf, inputs=query_input, outputs=search_output)
    
    with gr.Tab("Stats"):
        stats_btn = gr.Button("Get Statistics")
        stats_output = gr.JSON()
        stats_btn.click(get_stats, outputs=stats_output)

demo.launch()
```

### Option 4: Replit

**Cost:** $0/month  
**Uptime:** Keep-alive with UptimeRobot

1. Import repository to Replit
2. Run `python main.py serve`
3. Use UptimeRobot (free) to ping every 5 minutes

### Option 5: Google Colab

**Cost:** $0/month  
**Uptime:** Session-based

```python
# In Colab notebook:
!git clone https://github.com/DeadManOfficial/HF-Agent-Infinite.git
%cd HF-Agent-Infinite
!pip install -r requirements.txt

from core.agent import HFAgent
agent = HFAgent()

# Keep running with:
!nohup python main.py daemon &
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["python", "main.py", "daemon"]
```

Build and run:

```bash
docker build -t prometheus-hf .
docker run -d -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --name prometheus \
  prometheus-hf
```

### Docker Compose

```yaml
version: '3.8'

services:
  prometheus:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - CRAWL_INTERVAL_HOURS=1
      - ENABLE_ALERTS=true
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
    restart: unless-stopped
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus-hf
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prometheus-hf:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: prometheus-data
```

## Environment Variables

```bash
# Crawling
CRAWL_INTERVAL_HOURS=1
MAX_ITEMS_PER_CRAWL=10000

# Hugging Face
HF_TOKEN=your_hf_token_here

# Alerts
ENABLE_ALERTS=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Logging
LOG_LEVEL=INFO

# Watchdog
WATCHDOG_INTERVAL=60
MAX_RESTART_ATTEMPTS=3
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Statistics

```bash
curl http://localhost:8000/stats
```

### Logs

```bash
# View logs
tail -f data/logs/prometheus.log

# View crawler logs
tail -f data/logs/crawler.log

# View watchdog logs
tail -f data/logs/watchdog.log
```

## Alerts Setup

### Telegram Bot

1. Create bot with @BotFather
2. Get bot token
3. Get your chat ID (message @userinfobot)
4. Set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export ENABLE_ALERTS=true
```

## Backup & Recovery

### Backup Database

```bash
# Manual backup
cp data/hf_infinite.db data/backups/hf_infinite_$(date +%Y%m%d).db

# Automated daily backup
0 0 * * * cp /path/to/data/hf_infinite.db /path/to/backups/hf_infinite_$(date +\%Y\%m\%d).db
```

### Export Knowledge

```bash
python main.py
> export

# Or via API
curl http://localhost:8000/export
```

## Troubleshooting

### Issue: Crawl fails with rate limit

**Solution:** Reduce `CRAWL_INTERVAL_HOURS` or add `HF_TOKEN`

### Issue: Database locked

**Solution:** Check for multiple instances, restart services

### Issue: Out of memory

**Solution:** Reduce `MAX_ITEMS_PER_CRAWL` or increase system memory

### Issue: API not accessible

**Solution:** Check firewall, ensure port 8000 is open

## Performance Tuning

### For Large Crawls

```json
{
  "max_items_per_crawl": 50000,
  "rate_limits": {
    "hf_api_calls_per_second": 2.0
  }
}
```

### For Fast Search

Install FAISS for semantic search:

```bash
pip install faiss-cpu sentence-transformers
```

Build index:

```bash
python -c "from core.knowledge_base import KnowledgeBase; kb = KnowledgeBase(); kb.build_index_from_db()"
```

## Security

### API Authentication

Add authentication to `core/api.py`:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != "your_secret_token":
        raise HTTPException(status_code=401)
    return {"status": "authorized"}
```

### HTTPS

Use nginx or Caddy as reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name prometheus.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

---

**For more help, see:** [GitHub Issues](https://github.com/DeadManOfficial/HF-Agent-Infinite/issues)
