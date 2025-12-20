"""
HF-Agent-Infinite REST API
==========================

FastAPI-based REST interface for the PROMETHEUS agent.
Provides endpoints for crawling, searching, and monitoring.
"""

import os
import json
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import agent components
from .agent import HFAgent
from .knowledge_base import KnowledgeBase
from .tasks import TaskOrchestrator, TaskPriority

# Initialize FastAPI app
app = FastAPI(
    title="PROMETHEUS - HF Agent API",
    description="Phantom Engineer's Hugging Face Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (lazy loading)
_agent: Optional[HFAgent] = None
_kb: Optional[KnowledgeBase] = None
_orchestrator: Optional[TaskOrchestrator] = None


def get_agent() -> HFAgent:
    """Get or create the HF Agent instance."""
    global _agent
    if _agent is None:
        _agent = HFAgent()
    return _agent


def get_kb() -> KnowledgeBase:
    """Get or create the Knowledge Base instance."""
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


def get_orchestrator() -> TaskOrchestrator:
    """Get or create the Task Orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskOrchestrator()
        _orchestrator.start()
    return _orchestrator


# Request/Response models
class SearchRequest(BaseModel):
    query: str
    resource_type: str = "all"
    limit: int = 20
    semantic: bool = False


class CrawlRequest(BaseModel):
    resource_type: str = "all"
    limit: Optional[int] = None


class TaskSubmitRequest(BaseModel):
    task_type: str
    priority: str = "NORMAL"
    params: dict = {}


class SearchResult(BaseModel):
    id: str
    type: str
    name: str
    author: Optional[str]
    description: Optional[str]
    downloads: Optional[int]
    likes: Optional[int]
    score: Optional[float] = None


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "PROMETHEUS",
        "description": "Phantom Engineer's HF Intelligence System",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from .utils import HealthChecker
    checker = HealthChecker()
    return checker.full_health_check()


@app.get("/stats")
async def get_stats():
    """Get agent statistics."""
    agent = get_agent()
    return agent.get_stats()


@app.post("/search")
async def search(request: SearchRequest):
    """
    Search for HF resources.
    
    Supports both keyword and semantic search.
    """
    agent = get_agent()
    
    if request.semantic:
        kb = get_kb()
        results = kb.semantic_search(
            request.query,
            top_k=request.limit,
            resource_type=request.resource_type if request.resource_type != "all" else None
        )
        return {
            "query": request.query,
            "type": "semantic",
            "results": [
                {
                    "id": r.id,
                    "type": r.resource_type,
                    "name": r.name,
                    "description": r.description,
                    "score": r.score
                }
                for r in results
            ]
        }
    else:
        results = agent.search(
            request.query,
            request.resource_type,
            request.limit
        )
        return {
            "query": request.query,
            "type": "keyword",
            "results": results
        }


@app.get("/search/{query}")
async def search_get(
    query: str,
    resource_type: str = Query("all", description="Resource type filter"),
    limit: int = Query(20, description="Maximum results"),
    semantic: bool = Query(False, description="Use semantic search")
):
    """GET endpoint for search."""
    request = SearchRequest(
        query=query,
        resource_type=resource_type,
        limit=limit,
        semantic=semantic
    )
    return await search(request)


@app.post("/crawl")
async def crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Trigger a crawl operation.
    
    Runs in background for large crawls.
    """
    agent = get_agent()
    orchestrator = get_orchestrator()
    
    # Submit as background task
    if request.resource_type == "all":
        task_id = orchestrator.submit(
            agent.crawl_all,
            request.limit,
            name="full_crawl",
            priority=TaskPriority.HIGH
        )
    elif request.resource_type == "models":
        task_id = orchestrator.submit(
            agent.crawl_models,
            request.limit,
            name="models_crawl"
        )
    elif request.resource_type == "datasets":
        task_id = orchestrator.submit(
            agent.crawl_datasets,
            request.limit,
            name="datasets_crawl"
        )
    elif request.resource_type == "spaces":
        task_id = orchestrator.submit(
            agent.crawl_spaces,
            request.limit,
            name="spaces_crawl"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown resource type: {request.resource_type}")
    
    return {
        "status": "submitted",
        "task_id": task_id,
        "resource_type": request.resource_type,
        "message": "Crawl task submitted. Check /tasks/{task_id} for status."
    }


@app.get("/crawl/{resource_type}")
async def crawl_get(
    resource_type: str,
    limit: int = Query(100, description="Maximum items to crawl"),
    background_tasks: BackgroundTasks = None
):
    """GET endpoint for triggering crawl."""
    request = CrawlRequest(resource_type=resource_type, limit=limit)
    return await crawl(request, background_tasks)


@app.get("/models")
async def list_models(
    limit: int = Query(50, description="Maximum results"),
    sort_by: str = Query("downloads", description="Sort field"),
    author: Optional[str] = Query(None, description="Filter by author")
):
    """List indexed models."""
    import sqlite3
    agent = get_agent()
    
    conn = sqlite3.connect(agent.db_path)
    cursor = conn.cursor()
    
    query = f"SELECT id, name, author, downloads, likes, pipeline_tag FROM models"
    params = []
    
    if author:
        query += " WHERE author = ?"
        params.append(author)
    
    query += f" ORDER BY {sort_by} DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    models = []
    for row in cursor.fetchall():
        models.append({
            "id": row[0],
            "name": row[1],
            "author": row[2],
            "downloads": row[3],
            "likes": row[4],
            "pipeline_tag": row[5]
        })
    
    conn.close()
    return {"models": models, "count": len(models)}


@app.get("/models/{model_id:path}")
async def get_model(model_id: str):
    """Get details for a specific model."""
    import sqlite3
    agent = get_agent()
    
    conn = sqlite3.connect(agent.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM models WHERE id = ?", (model_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Model not found: {model_id}")
    
    columns = [desc[0] for desc in cursor.description]
    model = dict(zip(columns, row))
    
    conn.close()
    return model


@app.get("/datasets")
async def list_datasets(
    limit: int = Query(50, description="Maximum results"),
    sort_by: str = Query("downloads", description="Sort field")
):
    """List indexed datasets."""
    import sqlite3
    agent = get_agent()
    
    conn = sqlite3.connect(agent.db_path)
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT id, name, author, downloads, likes
        FROM datasets
        ORDER BY {sort_by} DESC
        LIMIT ?
    """, (limit,))
    
    datasets = []
    for row in cursor.fetchall():
        datasets.append({
            "id": row[0],
            "name": row[1],
            "author": row[2],
            "downloads": row[3],
            "likes": row[4]
        })
    
    conn.close()
    return {"datasets": datasets, "count": len(datasets)}


@app.get("/spaces")
async def list_spaces(
    limit: int = Query(50, description="Maximum results"),
    sort_by: str = Query("likes", description="Sort field"),
    sdk: Optional[str] = Query(None, description="Filter by SDK")
):
    """List indexed spaces."""
    import sqlite3
    agent = get_agent()
    
    conn = sqlite3.connect(agent.db_path)
    cursor = conn.cursor()
    
    query = "SELECT id, name, author, sdk, likes FROM spaces"
    params = []
    
    if sdk:
        query += " WHERE sdk = ?"
        params.append(sdk)
    
    query += f" ORDER BY {sort_by} DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    spaces = []
    for row in cursor.fetchall():
        spaces.append({
            "id": row[0],
            "name": row[1],
            "author": row[2],
            "sdk": row[3],
            "likes": row[4]
        })
    
    conn.close()
    return {"spaces": spaces, "count": len(spaces)}


@app.get("/priority")
async def get_priority_resources():
    """Get resources from priority authors and tags."""
    agent = get_agent()
    return agent.get_priority_resources()


@app.get("/tasks")
async def list_tasks(limit: int = Query(50, description="Maximum results")):
    """List recent tasks."""
    orchestrator = get_orchestrator()
    return {
        "stats": orchestrator.get_queue_stats(),
        "history": orchestrator.get_task_history(limit)
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get status of a specific task."""
    orchestrator = get_orchestrator()
    status = orchestrator.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return status


@app.post("/index/build")
async def build_index(background_tasks: BackgroundTasks):
    """Rebuild the semantic search index."""
    kb = get_kb()
    orchestrator = get_orchestrator()
    
    task_id = orchestrator.submit(
        kb.build_index_from_db,
        name="build_index",
        priority=TaskPriority.HIGH
    )
    
    return {
        "status": "submitted",
        "task_id": task_id,
        "message": "Index build task submitted."
    }


@app.get("/export")
async def export_knowledge():
    """Export all indexed knowledge to JSON."""
    agent = get_agent()
    output_path = agent.export_knowledge()
    
    return {
        "status": "exported",
        "path": output_path,
        "timestamp": datetime.now().isoformat()
    }


# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    print("🔥 PROMETHEUS starting up...")
    get_agent()
    print("✅ Agent initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _orchestrator
    if _orchestrator:
        _orchestrator.stop()
    print("👋 PROMETHEUS shutting down")


# Run with: uvicorn core.api:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
