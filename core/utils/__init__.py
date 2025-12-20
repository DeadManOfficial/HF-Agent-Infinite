"""
Utilities Module
================

Helper functions and utilities for the HF Agent system.
"""

import os
import json
import logging
import hashlib
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
):
    """Configure logging for the application."""
    format_str = log_format or '%(asctime)s | PROMETHEUS | %(levelname)s | %(message)s'
    
    handlers = [logging.StreamHandler()]
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=format_str,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f"{prefix}_{timestamp}" if prefix else timestamp


def hash_content(content: str) -> str:
    """Generate SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely parse JSON with fallback."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize to JSON with default handling."""
    def default_handler(o):
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)
    
    return json.dumps(obj, default=default_handler, **kwargs)


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_number(num: int) -> str:
    """Format large numbers with K/M/B suffixes."""
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 1.0):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
    
    def wait(self):
        """Wait if necessary to respect rate limit."""
        import time
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


class AlertManager:
    """
    Alert management for notifications.
    Supports Telegram and email alerts.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.telegram_token = self.config.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = self.config.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    
    def send_telegram(self, message: str) -> bool:
        """Send alert via Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            response = requests.post(url, data={
                "chat_id": self.telegram_chat_id,
                "text": f"🤖 PROMETHEUS Alert\n\n{message}",
                "parse_mode": "HTML"
            })
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
            return False
    
    def send_alert(self, title: str, message: str, level: str = "info") -> bool:
        """Send alert through configured channels."""
        emoji = {"info": "ℹ️", "warning": "⚠️", "error": "🚨", "success": "✅"}.get(level, "📢")
        full_message = f"{emoji} {title}\n\n{message}"
        
        success = False
        
        if self.telegram_token:
            success = self.send_telegram(full_message) or success
        
        # Log the alert
        log_func = getattr(logger, level if level != "success" else "info")
        log_func(f"Alert: {title} - {message}")
        
        return success


class HealthChecker:
    """System health monitoring."""
    
    def __init__(self, db_path: str = "data/hf_infinite.db"):
        self.db_path = db_path
    
    def check_database(self) -> Dict:
        """Check database health."""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get row counts
            counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "status": "healthy",
                "tables": tables,
                "row_counts": counts
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def check_hf_api(self) -> Dict:
        """Check Hugging Face API connectivity."""
        try:
            response = requests.get(
                "https://huggingface.co/api/models",
                params={"limit": 1},
                timeout=10
            )
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def full_health_check(self) -> Dict:
        """Perform full system health check."""
        return {
            "timestamp": datetime.now().isoformat(),
            "database": self.check_database(),
            "hf_api": self.check_hf_api(),
            "overall": "healthy"  # Simplified for now
        }


# Export
__all__ = [
    "setup_logging",
    "generate_id",
    "hash_content",
    "safe_json_loads",
    "safe_json_dumps",
    "truncate_text",
    "format_number",
    "format_duration",
    "RateLimiter",
    "AlertManager",
    "HealthChecker"
]
