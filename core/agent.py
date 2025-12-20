"""
HF-Agent-Infinite: PROMETHEUS
=============================

The Phantom Engineer's Hugging Face Resource Overseer
"One agent to rule them all. Absolute dedication. Infinite intricacy."

PROMETHEUS - The All-Seeing HF Intelligence
- Monitors all HF resources (models, datasets, papers, spaces)
- Self-improving through continuous learning
- Zero manual intervention required
"""

import os
import json
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | PROMETHEUS | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class ResourceMetadata:
    """Metadata for a Hugging Face resource."""
    id: str
    type: str  # model, dataset, paper, space
    name: str
    description: str = ""
    author: str = ""
    downloads: int = 0
    likes: int = 0
    tags: List[str] = field(default_factory=list)
    last_modified: str = ""
    url: str = ""
    raw_data: Dict = field(default_factory=dict)


class HFAgent:
    """
    PROMETHEUS - The Hugging Face Intelligence Agent
    
    Core capabilities:
    1. Resource Discovery - Crawl and index all HF resources
    2. Knowledge Management - Store and retrieve with semantic search
    3. Task Orchestration - Manage workflows and automation
    4. Self-Improvement - Continuous learning and optimization
    5. Monitoring - Track updates and changes across HF ecosystem
    """
    
    CODENAME = "PROMETHEUS"
    VERSION = "1.0.0"
    
    def __init__(
        self,
        db_path: str = "data/hf_infinite.db",
        config_path: str = "configs/agent_config.json"
    ):
        """Initialize the HF Agent."""
        self.db_path = Path(db_path)
        self.config_path = Path(config_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._init_database()
        self._load_config()
        
        # State management
        self.is_running = False
        self.threads: List[threading.Thread] = []
        
        logger.info(f"🔥 {self.CODENAME} initialized | Version {self.VERSION}")
        logger.info("Phantom Engineer's HF Intelligence System Online")
    
    def _init_database(self):
        """Initialize SQLite database with all required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT,
                author TEXT,
                description TEXT,
                downloads INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                tags TEXT,
                pipeline_tag TEXT,
                library_name TEXT,
                last_modified TEXT,
                created_at TEXT,
                raw_data TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Datasets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                name TEXT,
                author TEXT,
                description TEXT,
                downloads INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                tags TEXT,
                size_category TEXT,
                task_categories TEXT,
                last_modified TEXT,
                raw_data TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Papers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                arxiv_id TEXT,
                published_at TEXT,
                upvotes INTEGER DEFAULT 0,
                raw_data TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Spaces table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spaces (
                id TEXT PRIMARY KEY,
                name TEXT,
                author TEXT,
                description TEXT,
                sdk TEXT,
                likes INTEGER DEFAULT 0,
                runtime_stage TEXT,
                last_modified TEXT,
                raw_data TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crawl history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawl_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT,
                items_crawled INTEGER,
                items_new INTEGER,
                items_updated INTEGER,
                duration_seconds REAL,
                status TEXT,
                error_message TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Embeddings table (for vector search)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                resource_type TEXT,
                resource_id TEXT,
                embedding BLOB,
                model_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def _load_config(self):
        """Load agent configuration."""
        default_config = {
            "crawl_interval_hours": 1,
            "max_items_per_crawl": 10000,
            "embedding_model": "all-MiniLM-L6-v2",
            "llm_model": "Qwen/Qwen1.5-0.5B-Chat",
            "enable_auto_fine_tune": False,
            "enable_monitoring": True,
            "alert_channels": ["telegram", "email"],
            "priority_authors": ["DavidAU", "Nymbo"],
            "priority_tags": ["llm", "gguf", "quantized"],
            "hf_token": os.getenv("HF_TOKEN", "")
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = {**default_config, **json.load(f)}
        else:
            self.config = default_config
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
        
        logger.info("Configuration loaded")
    
    def crawl_models(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Crawl all models from Hugging Face Hub.
        
        Returns:
            Dict with crawl statistics
        """
        try:
            from huggingface_hub import HfApi, list_models
            
            api = HfApi()
            limit = limit or self.config.get("max_items_per_crawl", 10000)
            
            logger.info(f"Starting model crawl (limit: {limit})")
            start_time = datetime.now()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_count = 0
            updated_count = 0
            
            models = list_models(limit=limit, sort="downloads", direction=-1)
            
            for model in models:
                model_id = model.id
                
                # Check if exists
                cursor.execute("SELECT id FROM models WHERE id = ?", (model_id,))
                exists = cursor.fetchone()
                
                # Prepare data
                tags = json.dumps(model.tags) if model.tags else "[]"
                raw_data = json.dumps({
                    "id": model.id,
                    "author": model.author,
                    "sha": model.sha,
                    "private": model.private,
                    "gated": model.gated if hasattr(model, 'gated') else None,
                })
                
                if exists:
                    cursor.execute("""
                        UPDATE models SET
                            name = ?, author = ?, downloads = ?, likes = ?,
                            tags = ?, pipeline_tag = ?, library_name = ?,
                            last_modified = ?, raw_data = ?, indexed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        model.id.split("/")[-1],
                        model.author,
                        model.downloads,
                        model.likes,
                        tags,
                        model.pipeline_tag,
                        model.library_name,
                        str(model.last_modified) if model.last_modified else None,
                        raw_data,
                        model_id
                    ))
                    updated_count += 1
                else:
                    cursor.execute("""
                        INSERT INTO models (id, name, author, downloads, likes, tags,
                            pipeline_tag, library_name, last_modified, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        model_id,
                        model.id.split("/")[-1],
                        model.author,
                        model.downloads,
                        model.likes,
                        tags,
                        model.pipeline_tag,
                        model.library_name,
                        str(model.last_modified) if model.last_modified else None,
                        raw_data
                    ))
                    new_count += 1
            
            conn.commit()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Log crawl history
            cursor.execute("""
                INSERT INTO crawl_history (resource_type, items_crawled, items_new,
                    items_updated, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("models", new_count + updated_count, new_count, updated_count, duration, "success"))
            conn.commit()
            conn.close()
            
            stats = {
                "total": new_count + updated_count,
                "new": new_count,
                "updated": updated_count,
                "duration_seconds": duration
            }
            
            logger.info(f"Model crawl complete: {stats}")
            return stats
            
        except ImportError:
            logger.error("huggingface_hub not installed. Run: pip install huggingface_hub")
            return {"error": "huggingface_hub not installed"}
        except Exception as e:
            logger.error(f"Model crawl failed: {str(e)}")
            return {"error": str(e)}
    
    def crawl_datasets(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Crawl all datasets from Hugging Face Hub."""
        try:
            from huggingface_hub import HfApi, list_datasets
            
            api = HfApi()
            limit = limit or self.config.get("max_items_per_crawl", 10000)
            
            logger.info(f"Starting dataset crawl (limit: {limit})")
            start_time = datetime.now()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_count = 0
            updated_count = 0
            
            datasets = list_datasets(limit=limit, sort="downloads", direction=-1)
            
            for dataset in datasets:
                dataset_id = dataset.id
                
                cursor.execute("SELECT id FROM datasets WHERE id = ?", (dataset_id,))
                exists = cursor.fetchone()
                
                tags = json.dumps(dataset.tags) if dataset.tags else "[]"
                raw_data = json.dumps({
                    "id": dataset.id,
                    "author": dataset.author,
                    "sha": dataset.sha,
                    "private": dataset.private,
                })
                
                if exists:
                    cursor.execute("""
                        UPDATE datasets SET
                            name = ?, author = ?, downloads = ?, likes = ?,
                            tags = ?, last_modified = ?, raw_data = ?,
                            indexed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        dataset.id.split("/")[-1],
                        dataset.author,
                        dataset.downloads,
                        dataset.likes,
                        tags,
                        str(dataset.last_modified) if dataset.last_modified else None,
                        raw_data,
                        dataset_id
                    ))
                    updated_count += 1
                else:
                    cursor.execute("""
                        INSERT INTO datasets (id, name, author, downloads, likes,
                            tags, last_modified, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dataset_id,
                        dataset.id.split("/")[-1],
                        dataset.author,
                        dataset.downloads,
                        dataset.likes,
                        tags,
                        str(dataset.last_modified) if dataset.last_modified else None,
                        raw_data
                    ))
                    new_count += 1
            
            conn.commit()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            cursor.execute("""
                INSERT INTO crawl_history (resource_type, items_crawled, items_new,
                    items_updated, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("datasets", new_count + updated_count, new_count, updated_count, duration, "success"))
            conn.commit()
            conn.close()
            
            stats = {
                "total": new_count + updated_count,
                "new": new_count,
                "updated": updated_count,
                "duration_seconds": duration
            }
            
            logger.info(f"Dataset crawl complete: {stats}")
            return stats
            
        except ImportError:
            logger.error("huggingface_hub not installed")
            return {"error": "huggingface_hub not installed"}
        except Exception as e:
            logger.error(f"Dataset crawl failed: {str(e)}")
            return {"error": str(e)}
    
    def crawl_spaces(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Crawl all spaces from Hugging Face Hub."""
        try:
            from huggingface_hub import HfApi, list_spaces
            
            api = HfApi()
            limit = limit or self.config.get("max_items_per_crawl", 10000)
            
            logger.info(f"Starting spaces crawl (limit: {limit})")
            start_time = datetime.now()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_count = 0
            updated_count = 0
            
            spaces = list_spaces(limit=limit, sort="likes", direction=-1)
            
            for space in spaces:
                space_id = space.id
                
                cursor.execute("SELECT id FROM spaces WHERE id = ?", (space_id,))
                exists = cursor.fetchone()
                
                raw_data = json.dumps({
                    "id": space.id,
                    "author": space.author,
                    "sha": space.sha,
                    "private": space.private,
                })
                
                if exists:
                    cursor.execute("""
                        UPDATE spaces SET
                            name = ?, author = ?, sdk = ?, likes = ?,
                            last_modified = ?, raw_data = ?,
                            indexed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        space.id.split("/")[-1],
                        space.author,
                        space.sdk,
                        space.likes,
                        str(space.last_modified) if space.last_modified else None,
                        raw_data,
                        space_id
                    ))
                    updated_count += 1
                else:
                    cursor.execute("""
                        INSERT INTO spaces (id, name, author, sdk, likes,
                            last_modified, raw_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        space_id,
                        space.id.split("/")[-1],
                        space.author,
                        space.sdk,
                        space.likes,
                        str(space.last_modified) if space.last_modified else None,
                        raw_data
                    ))
                    new_count += 1
            
            conn.commit()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            cursor.execute("""
                INSERT INTO crawl_history (resource_type, items_crawled, items_new,
                    items_updated, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("spaces", new_count + updated_count, new_count, updated_count, duration, "success"))
            conn.commit()
            conn.close()
            
            stats = {
                "total": new_count + updated_count,
                "new": new_count,
                "updated": updated_count,
                "duration_seconds": duration
            }
            
            logger.info(f"Spaces crawl complete: {stats}")
            return stats
            
        except ImportError:
            logger.error("huggingface_hub not installed")
            return {"error": "huggingface_hub not installed"}
        except Exception as e:
            logger.error(f"Spaces crawl failed: {str(e)}")
            return {"error": str(e)}
    
    def crawl_all(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Crawl all resource types."""
        logger.info("🚀 Starting full HF crawl...")
        
        results = {
            "models": self.crawl_models(limit),
            "datasets": self.crawl_datasets(limit),
            "spaces": self.crawl_spaces(limit),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Full crawl complete: {results}")
        return results
    
    def search(
        self,
        query: str,
        resource_type: str = "all",
        limit: int = 20
    ) -> List[Dict]:
        """
        Search indexed resources.
        
        Args:
            query: Search query
            resource_type: models, datasets, spaces, or all
            limit: Maximum results to return
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = []
        
        tables = {
            "models": "SELECT id, name, author, description, downloads, likes FROM models",
            "datasets": "SELECT id, name, author, description, downloads, likes FROM datasets",
            "spaces": "SELECT id, name, author, description, likes, sdk FROM spaces"
        }
        
        if resource_type == "all":
            search_tables = tables.keys()
        else:
            search_tables = [resource_type] if resource_type in tables else []
        
        for table in search_tables:
            base_query = tables[table]
            search_query = f"""
                {base_query}
                WHERE name LIKE ? OR author LIKE ? OR description LIKE ? OR id LIKE ?
                ORDER BY downloads DESC
                LIMIT ?
            """
            
            pattern = f"%{query}%"
            cursor.execute(search_query, (pattern, pattern, pattern, pattern, limit))
            
            for row in cursor.fetchall():
                results.append({
                    "type": table.rstrip("s"),
                    "id": row[0],
                    "name": row[1],
                    "author": row[2],
                    "description": row[3],
                    "downloads": row[4] if table != "spaces" else None,
                    "likes": row[5] if table != "spaces" else row[4]
                })
        
        conn.close()
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Count resources
        for table in ["models", "datasets", "spaces", "papers"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Get last crawl times
        cursor.execute("""
            SELECT resource_type, MAX(crawled_at) as last_crawl
            FROM crawl_history
            GROUP BY resource_type
        """)
        stats["last_crawls"] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get total crawl history
        cursor.execute("SELECT COUNT(*) FROM crawl_history")
        stats["total_crawls"] = cursor.fetchone()[0]
        
        conn.close()
        
        stats["agent_codename"] = self.CODENAME
        stats["agent_version"] = self.VERSION
        stats["timestamp"] = datetime.now().isoformat()
        
        return stats
    
    def get_priority_resources(self) -> Dict[str, List[Dict]]:
        """Get resources from priority authors and with priority tags."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        results = {"by_author": [], "by_tag": []}
        
        # Priority authors
        for author in self.config.get("priority_authors", []):
            cursor.execute("""
                SELECT id, name, downloads, likes, tags
                FROM models WHERE author = ?
                ORDER BY downloads DESC LIMIT 10
            """, (author,))
            
            for row in cursor.fetchall():
                results["by_author"].append({
                    "id": row[0],
                    "name": row[1],
                    "author": author,
                    "downloads": row[2],
                    "likes": row[3]
                })
        
        # Priority tags
        for tag in self.config.get("priority_tags", []):
            cursor.execute("""
                SELECT id, name, author, downloads, likes
                FROM models WHERE tags LIKE ?
                ORDER BY downloads DESC LIMIT 10
            """, (f'%"{tag}"%',))
            
            for row in cursor.fetchall():
                results["by_tag"].append({
                    "id": row[0],
                    "name": row[1],
                    "author": row[2],
                    "downloads": row[3],
                    "likes": row[4],
                    "matched_tag": tag
                })
        
        conn.close()
        return results
    
    def export_knowledge(self, output_path: str = "data/knowledge_export.json") -> str:
        """Export all indexed knowledge to JSON."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "agent": self.CODENAME,
            "version": self.VERSION,
            "resources": {}
        }
        
        for table in ["models", "datasets", "spaces"]:
            cursor.execute(f"SELECT * FROM {table}")
            columns = [desc[0] for desc in cursor.description]
            export_data["resources"][table] = [
                dict(zip(columns, row)) for row in cursor.fetchall()
            ]
        
        conn.close()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Knowledge exported to {output_path}")
        return str(output_path)


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PROMETHEUS - HF Agent CLI")
    parser.add_argument("command", choices=["crawl", "search", "stats", "export"])
    parser.add_argument("--type", default="all", help="Resource type (models/datasets/spaces/all)")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--limit", type=int, default=100, help="Limit for crawl/search")
    
    args = parser.parse_args()
    
    agent = HFAgent()
    
    if args.command == "crawl":
        if args.type == "all":
            results = agent.crawl_all(args.limit)
        elif args.type == "models":
            results = agent.crawl_models(args.limit)
        elif args.type == "datasets":
            results = agent.crawl_datasets(args.limit)
        elif args.type == "spaces":
            results = agent.crawl_spaces(args.limit)
        print(json.dumps(results, indent=2))
    
    elif args.command == "search":
        if not args.query:
            print("Error: --query required for search")
        else:
            results = agent.search(args.query, args.type, args.limit)
            print(json.dumps(results, indent=2))
    
    elif args.command == "stats":
        stats = agent.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "export":
        path = agent.export_knowledge()
        print(f"Exported to: {path}")
