#!/usr/bin/env python3
"""
Watchdog - PROMETHEUS
=====================

Self-healing system monitor.
Monitors all PROMETHEUS components and auto-restarts on failure.

"The guardian that never rests."
"""

import os
import sys
import time
import signal
import subprocess
import logging
import requests
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import setup_logging, AlertManager

# Configuration
CHECK_INTERVAL_SECONDS = int(os.getenv("WATCHDOG_INTERVAL", "60"))
API_URL = os.getenv("API_URL", "http://localhost:8000")
MAX_RESTART_ATTEMPTS = int(os.getenv("MAX_RESTART_ATTEMPTS", "3"))
ENABLE_ALERTS = os.getenv("ENABLE_ALERTS", "false").lower() == "true"

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="data/logs/watchdog.log"
)
logger = logging.getLogger(__name__)

# Global state
running = True
restart_counts = {}


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    logger.info(f"Received signal {signum}, shutting down watchdog...")
    running = False


class ServiceMonitor:
    """Monitor and manage a service."""
    
    def __init__(self, name: str, health_check: callable, restart_cmd: list):
        self.name = name
        self.health_check = health_check
        self.restart_cmd = restart_cmd
        self.restart_count = 0
        self.last_healthy = datetime.now()
        self.process = None
    
    def check_health(self) -> bool:
        """Check if service is healthy."""
        try:
            return self.health_check()
        except Exception as e:
            logger.error(f"{self.name} health check failed: {e}")
            return False
    
    def restart(self) -> bool:
        """Restart the service."""
        logger.warning(f"Restarting {self.name}...")
        
        try:
            # Kill existing process if any
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
        except:
            pass
        
        try:
            self.process = subprocess.Popen(
                self.restart_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.restart_count += 1
            logger.info(f"{self.name} restarted (attempt {self.restart_count})")
            return True
        except Exception as e:
            logger.error(f"Failed to restart {self.name}: {e}")
            return False


def check_api_health() -> bool:
    """Check API server health."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        return response.status_code == 200
    except:
        return False


def check_crawler_health() -> bool:
    """Check crawler process health."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "infinite_crawler.py"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False


def check_database_health() -> bool:
    """Check database health."""
    try:
        import sqlite3
        db_path = Path("data/hf_infinite.db")
        if not db_path.exists():
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return True
    except:
        return False


def run_watchdog():
    """Main watchdog loop."""
    global running
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("🛡️ PROMETHEUS Watchdog Starting")
    logger.info(f"   Check interval: {CHECK_INTERVAL_SECONDS}s")
    logger.info(f"   API URL: {API_URL}")
    logger.info(f"   Max restart attempts: {MAX_RESTART_ATTEMPTS}")
    logger.info("=" * 60)
    
    alerts = AlertManager() if ENABLE_ALERTS else None
    
    # Define services to monitor
    services = {
        "api": {
            "check": check_api_health,
            "restart_cmd": ["python", "-m", "uvicorn", "core.api:app", "--host", "0.0.0.0", "--port", "8000"],
            "restart_count": 0,
            "last_healthy": datetime.now()
        },
        "database": {
            "check": check_database_health,
            "restart_cmd": None,  # Can't restart database
            "restart_count": 0,
            "last_healthy": datetime.now()
        }
    }
    
    while running:
        try:
            check_time = datetime.now()
            
            for service_name, service in services.items():
                is_healthy = service["check"]()
                
                if is_healthy:
                    if service["restart_count"] > 0:
                        logger.info(f"✅ {service_name} recovered after {service['restart_count']} restarts")
                        if alerts:
                            alerts.send_alert(
                                f"{service_name} Recovered",
                                f"Service is healthy again after {service['restart_count']} restart attempts",
                                level="success"
                            )
                    service["restart_count"] = 0
                    service["last_healthy"] = check_time
                else:
                    logger.warning(f"❌ {service_name} is unhealthy")
                    
                    if service["restart_cmd"] and service["restart_count"] < MAX_RESTART_ATTEMPTS:
                        logger.info(f"Attempting to restart {service_name}...")
                        
                        try:
                            subprocess.Popen(
                                service["restart_cmd"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                start_new_session=True
                            )
                            service["restart_count"] += 1
                            
                            if alerts:
                                alerts.send_alert(
                                    f"{service_name} Restarted",
                                    f"Attempt {service['restart_count']}/{MAX_RESTART_ATTEMPTS}",
                                    level="warning"
                                )
                        except Exception as e:
                            logger.error(f"Failed to restart {service_name}: {e}")
                    
                    elif service["restart_count"] >= MAX_RESTART_ATTEMPTS:
                        logger.critical(f"🚨 {service_name} failed after {MAX_RESTART_ATTEMPTS} restart attempts")
                        if alerts:
                            alerts.send_alert(
                                f"{service_name} CRITICAL",
                                f"Service failed after {MAX_RESTART_ATTEMPTS} restart attempts. Manual intervention required.",
                                level="error"
                            )
            
            # Log status summary
            healthy_count = sum(1 for s in services.values() if s["check"]())
            logger.debug(f"Health check: {healthy_count}/{len(services)} services healthy")
            
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
        
        # Sleep until next check
        time.sleep(CHECK_INTERVAL_SECONDS)
    
    logger.info("🛑 PROMETHEUS Watchdog stopped")


if __name__ == "__main__":
    run_watchdog()
