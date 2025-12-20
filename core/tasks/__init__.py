"""
Task Orchestrator Module
========================

Manages workflows, scheduling, and task automation.
Supports both synchronous and asynchronous task execution.
"""

import os
import json
import time
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Queue, PriorityQueue

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass
class Task:
    """A task to be executed."""
    id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        """For priority queue comparison."""
        return self.priority.value < other.priority.value


@dataclass
class ScheduledTask:
    """A task scheduled to run at specific times."""
    id: str
    name: str
    func: Callable
    cron_expression: Optional[str] = None  # For cron-like scheduling
    interval_seconds: Optional[int] = None  # For interval-based scheduling
    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0


class TaskOrchestrator:
    """
    Task orchestration and workflow management.
    
    Features:
    - Priority-based task queue
    - Scheduled task execution
    - Retry logic with exponential backoff
    - Task history and logging
    - Worker thread pool
    """
    
    def __init__(
        self,
        db_path: str = "data/hf_infinite.db",
        num_workers: int = 4,
        max_queue_size: int = 1000
    ):
        self.db_path = Path(db_path)
        self.num_workers = num_workers
        
        # Task queues
        self.task_queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        
        # Worker management
        self.workers: List[threading.Thread] = []
        self.is_running = False
        self.shutdown_event = threading.Event()
        
        # Task registry
        self.tasks: Dict[str, Task] = {}
        
        self._init_database()
        logger.info(f"TaskOrchestrator initialized with {num_workers} workers")
    
    def _init_database(self):
        """Initialize task-related database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT,
                priority TEXT,
                result TEXT,
                error TEXT,
                created_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                retry_count INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                cron_expression TEXT,
                interval_seconds INTEGER,
                enabled INTEGER DEFAULT 1,
                last_run TIMESTAMP,
                next_run TIMESTAMP,
                run_count INTEGER DEFAULT 0,
                config TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def submit(
        self,
        func: Callable,
        *args,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Submit a task for execution.
        
        Returns:
            Task ID
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        task = Task(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            max_retries=max_retries
        )
        
        self.tasks[task_id] = task
        self.task_queue.put((priority.value, task))
        
        logger.info(f"Task submitted: {task_id} ({task.name})")
        return task_id
    
    def schedule(
        self,
        func: Callable,
        *args,
        name: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Schedule a recurring task.
        
        Args:
            func: Function to execute
            interval_seconds: Run every N seconds
            cron_expression: Cron-style schedule (not implemented yet)
        
        Returns:
            Scheduled task ID
        """
        task_id = f"scheduled_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        scheduled = ScheduledTask(
            id=task_id,
            name=name or func.__name__,
            func=func,
            args=args,
            kwargs=kwargs,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression
        )
        
        if interval_seconds:
            scheduled.next_run = datetime.now() + timedelta(seconds=interval_seconds)
        
        self.scheduled_tasks[task_id] = scheduled
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO scheduled_tasks
            (id, name, cron_expression, interval_seconds, enabled, next_run)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            scheduled.name,
            cron_expression,
            interval_seconds,
            1,
            scheduled.next_run.isoformat() if scheduled.next_run else None
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Task scheduled: {task_id} ({scheduled.name})")
        return task_id
    
    def _execute_task(self, task: Task) -> Task:
        """Execute a single task with retry logic."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        while task.retry_count <= task.max_retries:
            try:
                task.result = task.func(*task.args, **task.kwargs)
                task.status = TaskStatus.COMPLETED
                break
            except Exception as e:
                task.retry_count += 1
                task.error = str(e)
                
                if task.retry_count > task.max_retries:
                    task.status = TaskStatus.FAILED
                    logger.error(f"Task {task.id} failed after {task.max_retries} retries: {e}")
                else:
                    # Exponential backoff
                    wait_time = 2 ** task.retry_count
                    logger.warning(f"Task {task.id} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
        
        task.completed_at = datetime.now()
        
        # Save to history
        self._save_task_history(task)
        
        return task
    
    def _save_task_history(self, task: Task):
        """Save task execution to history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        duration = None
        if task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
        
        cursor.execute("""
            INSERT OR REPLACE INTO task_history
            (id, name, status, priority, result, error, created_at,
             started_at, completed_at, duration_seconds, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id,
            task.name,
            task.status.value,
            task.priority.name,
            json.dumps(task.result) if task.result else None,
            task.error,
            task.created_at.isoformat(),
            task.started_at.isoformat() if task.started_at else None,
            task.completed_at.isoformat() if task.completed_at else None,
            duration,
            task.retry_count
        ))
        
        conn.commit()
        conn.close()
    
    def _worker_loop(self, worker_id: int):
        """Worker thread main loop."""
        logger.info(f"Worker {worker_id} started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get task with timeout to allow checking shutdown
                try:
                    _, task = self.task_queue.get(timeout=1.0)
                except:
                    continue
                
                logger.info(f"Worker {worker_id} executing: {task.name}")
                self._execute_task(task)
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _scheduler_loop(self):
        """Scheduler thread for recurring tasks."""
        logger.info("Scheduler started")
        
        while not self.shutdown_event.is_set():
            now = datetime.now()
            
            for task_id, scheduled in list(self.scheduled_tasks.items()):
                if not scheduled.enabled:
                    continue
                
                if scheduled.next_run and now >= scheduled.next_run:
                    # Submit task for execution
                    self.submit(
                        scheduled.func,
                        *scheduled.args,
                        name=f"{scheduled.name}_run_{scheduled.run_count + 1}",
                        **scheduled.kwargs
                    )
                    
                    scheduled.last_run = now
                    scheduled.run_count += 1
                    
                    # Calculate next run
                    if scheduled.interval_seconds:
                        scheduled.next_run = now + timedelta(seconds=scheduled.interval_seconds)
                    
                    logger.info(f"Scheduled task triggered: {scheduled.name}")
            
            # Sleep for a bit
            time.sleep(1)
        
        logger.info("Scheduler stopped")
    
    def start(self):
        """Start the task orchestrator."""
        if self.is_running:
            logger.warning("Orchestrator already running")
            return
        
        self.is_running = True
        self.shutdown_event.clear()
        
        # Start worker threads
        for i in range(self.num_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        # Start scheduler thread
        scheduler = threading.Thread(target=self._scheduler_loop, daemon=True)
        scheduler.start()
        self.workers.append(scheduler)
        
        logger.info(f"TaskOrchestrator started with {self.num_workers} workers")
    
    def stop(self, wait: bool = True, timeout: float = 30.0):
        """Stop the task orchestrator."""
        if not self.is_running:
            return
        
        logger.info("Stopping TaskOrchestrator...")
        self.shutdown_event.set()
        
        if wait:
            for worker in self.workers:
                worker.join(timeout=timeout)
        
        self.workers.clear()
        self.is_running = False
        logger.info("TaskOrchestrator stopped")
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "priority": task.priority.name,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "retry_count": task.retry_count,
            "error": task.error
        }
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        return {
            "queue_size": self.task_queue.qsize(),
            "total_tasks": len(self.tasks),
            "scheduled_tasks": len(self.scheduled_tasks),
            "workers": len(self.workers),
            "is_running": self.is_running
        }
    
    def get_task_history(self, limit: int = 100) -> List[Dict]:
        """Get recent task history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, status, priority, duration_seconds, error, completed_at
            FROM task_history
            ORDER BY completed_at DESC
            LIMIT ?
        """, (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],
                "name": row[1],
                "status": row[2],
                "priority": row[3],
                "duration_seconds": row[4],
                "error": row[5],
                "completed_at": row[6]
            })
        
        conn.close()
        return history


# Workflow definitions for common HF operations
class HFWorkflows:
    """Pre-defined workflows for HF operations."""
    
    @staticmethod
    def full_crawl_workflow(agent) -> Dict:
        """Complete crawl of all HF resources."""
        return agent.crawl_all()
    
    @staticmethod
    def priority_monitor_workflow(agent) -> Dict:
        """Monitor priority authors and tags."""
        return agent.get_priority_resources()
    
    @staticmethod
    def build_index_workflow(kb) -> int:
        """Rebuild the knowledge base index."""
        return kb.build_index_from_db()


# Export
__all__ = ["TaskOrchestrator", "Task", "TaskStatus", "TaskPriority", "HFWorkflows"]
