#!/usr/bin/env python3
"""
Infinite Crawler - PROMETHEUS
=============================

Perpetual Hugging Face resource crawler.
Runs forever, polling HF API at configured intervals.

"The eye that never sleeps."
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent import HFAgent
from core.utils import setup_logging, AlertManager

# Configuration
CRAWL_INTERVAL_HOURS = float(os.getenv("CRAWL_INTERVAL_HOURS", "1"))
MAX_ITEMS_PER_CRAWL = int(os.getenv("MAX_ITEMS_PER_CRAWL", "5000"))
ENABLE_ALERTS = os.getenv("ENABLE_ALERTS", "false").lower() == "true"

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="data/logs/crawler.log"
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    running = False


def infinite_crawl():
    """
    Main infinite crawl loop.
    
    Crawls all HF resources at configured intervals.
    Self-healing: continues on errors with exponential backoff.
    """
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("🔥 PROMETHEUS Infinite Crawler Starting")
    logger.info(f"   Crawl interval: {CRAWL_INTERVAL_HOURS} hours")
    logger.info(f"   Max items per crawl: {MAX_ITEMS_PER_CRAWL}")
    logger.info(f"   Alerts enabled: {ENABLE_ALERTS}")
    logger.info("=" * 60)
    
    # Initialize components
    agent = HFAgent()
    alerts = AlertManager() if ENABLE_ALERTS else None
    
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while running:
        try:
            crawl_start = datetime.now()
            logger.info(f"Starting crawl cycle at {crawl_start.isoformat()}")
            
            # Crawl all resource types
            results = agent.crawl_all(limit=MAX_ITEMS_PER_CRAWL)
            
            # Log results
            total_items = sum(
                r.get("total", 0) for r in results.values() 
                if isinstance(r, dict) and "total" in r
            )
            
            crawl_duration = (datetime.now() - crawl_start).total_seconds()
            
            logger.info(f"Crawl cycle complete:")
            logger.info(f"   Models: {results.get('models', {}).get('total', 0)}")
            logger.info(f"   Datasets: {results.get('datasets', {}).get('total', 0)}")
            logger.info(f"   Spaces: {results.get('spaces', {}).get('total', 0)}")
            logger.info(f"   Duration: {crawl_duration:.1f}s")
            
            # Send success alert if enabled
            if alerts and consecutive_errors > 0:
                alerts.send_alert(
                    "Crawler Recovered",
                    f"Crawl successful after {consecutive_errors} errors. "
                    f"Indexed {total_items} items in {crawl_duration:.1f}s",
                    level="success"
                )
            
            consecutive_errors = 0
            
            # Wait for next cycle
            sleep_seconds = CRAWL_INTERVAL_HOURS * 3600
            logger.info(f"Sleeping for {CRAWL_INTERVAL_HOURS} hours until next crawl...")
            
            # Sleep in small increments to allow graceful shutdown
            sleep_end = time.time() + sleep_seconds
            while running and time.time() < sleep_end:
                time.sleep(min(60, sleep_end - time.time()))
            
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Crawl error ({consecutive_errors}/{max_consecutive_errors}): {e}")
            
            # Send error alert
            if alerts:
                alerts.send_alert(
                    "Crawler Error",
                    f"Error: {str(e)}\nConsecutive errors: {consecutive_errors}",
                    level="error"
                )
            
            # Exponential backoff
            if consecutive_errors < max_consecutive_errors:
                backoff = min(300, 30 * (2 ** consecutive_errors))
                logger.info(f"Backing off for {backoff}s before retry...")
                time.sleep(backoff)
            else:
                logger.critical(f"Too many consecutive errors ({max_consecutive_errors}), pausing for 1 hour")
                time.sleep(3600)
                consecutive_errors = 0
    
    logger.info("🛑 PROMETHEUS Infinite Crawler stopped")


if __name__ == "__main__":
    infinite_crawl()
