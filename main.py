#!/usr/bin/env python3
"""
HF-Agent-Infinite: PROMETHEUS
=============================

The Phantom Engineer's Hugging Face Intelligence System

"One agent to rule them all. Absolute dedication. Infinite intricacy."

Usage:
    python main.py                  # Start interactive mode
    python main.py crawl            # Run a full crawl
    python main.py search <query>   # Search indexed resources
    python main.py serve            # Start API server
    python main.py daemon           # Start all services (crawler + API + watchdog)
    python main.py stats            # Show statistics
"""

import os
import sys
import json
import argparse
import threading
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

from core.agent import HFAgent
from core.knowledge_base import KnowledgeBase
from core.tasks import TaskOrchestrator
from core.utils import setup_logging, format_number, format_duration

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ██████╗ ██████╗  ██████╗ ███╗   ███╗███████╗████████╗██╗  ██╗   ║
║   ██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝██║  ██║   ║
║   ██████╔╝██████╔╝██║   ██║██╔████╔██║█████╗     ██║   ███████║   ║
║   ██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔══╝     ██║   ██╔══██║   ║
║   ██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║███████╗   ██║   ██║  ██║   ║
║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝   ╚═╝  ╚═╝   ║
║                                                                   ║
║   HF-Agent-Infinite | The All-Seeing HF Intelligence              ║
║   By Phantom Engineer | DeadManOfficial                           ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""


def print_banner():
    """Print the PROMETHEUS banner."""
    print(BANNER)


def cmd_crawl(args):
    """Execute crawl command."""
    print("🔥 Starting crawl...")
    agent = HFAgent()
    
    if args.type == "all":
        results = agent.crawl_all(args.limit)
    elif args.type == "models":
        results = agent.crawl_models(args.limit)
    elif args.type == "datasets":
        results = agent.crawl_datasets(args.limit)
    elif args.type == "spaces":
        results = agent.crawl_spaces(args.limit)
    else:
        print(f"Unknown type: {args.type}")
        return
    
    print("\n📊 Crawl Results:")
    print(json.dumps(results, indent=2, default=str))


def cmd_search(args):
    """Execute search command."""
    agent = HFAgent()
    
    if args.semantic:
        kb = KnowledgeBase()
        results = kb.semantic_search(args.query, args.limit)
        
        print(f"\n🔍 Semantic Search Results for: '{args.query}'")
        print("-" * 60)
        
        for r in results:
            print(f"\n[{r.resource_type.upper()}] {r.id}")
            print(f"  Name: {r.name}")
            print(f"  Score: {r.score:.4f}")
            if r.description:
                desc = r.description[:100] + "..." if len(r.description) > 100 else r.description
                print(f"  Description: {desc}")
    else:
        results = agent.search(args.query, args.type, args.limit)
        
        print(f"\n🔍 Search Results for: '{args.query}'")
        print("-" * 60)
        
        for r in results:
            print(f"\n[{r.get('type', 'unknown').upper()}] {r.get('id')}")
            print(f"  Name: {r.get('name')}")
            print(f"  Author: {r.get('author')}")
            if r.get('downloads'):
                print(f"  Downloads: {format_number(r['downloads'])}")
            if r.get('likes'):
                print(f"  Likes: {format_number(r['likes'])}")


def cmd_serve(args):
    """Start the API server."""
    print("🚀 Starting PROMETHEUS API Server...")
    
    import uvicorn
    uvicorn.run(
        "core.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


def cmd_daemon(args):
    """Start all services in daemon mode."""
    print_banner()
    print("🔥 Starting PROMETHEUS in daemon mode...")
    print("   This will start: API Server + Infinite Crawler + Watchdog")
    print("-" * 60)
    
    import subprocess
    import time
    
    processes = []
    
    # Start API server
    print("Starting API server...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "core.api:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(("API Server", api_proc))
    time.sleep(2)
    
    # Start crawler
    print("Starting infinite crawler...")
    crawler_proc = subprocess.Popen(
        [sys.executable, "scripts/infinite_crawler.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(("Crawler", crawler_proc))
    
    # Start watchdog
    print("Starting watchdog...")
    watchdog_proc = subprocess.Popen(
        [sys.executable, "scripts/watchdog.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(("Watchdog", watchdog_proc))
    
    print("\n✅ All services started!")
    print("   API: http://localhost:8000")
    print("   Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop all services...")
    
    try:
        while True:
            time.sleep(1)
            # Check if any process died
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"⚠️ {name} exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping all services...")
        for name, proc in processes:
            proc.terminate()
            proc.wait(timeout=10)
            print(f"   {name} stopped")
        print("👋 PROMETHEUS shutdown complete")


def cmd_stats(args):
    """Show agent statistics."""
    agent = HFAgent()
    stats = agent.get_stats()
    
    print_banner()
    print("📊 PROMETHEUS Statistics")
    print("=" * 60)
    
    print(f"\n🤖 Agent: {stats.get('agent_codename')} v{stats.get('agent_version')}")
    print(f"📅 Timestamp: {stats.get('timestamp')}")
    
    print("\n📦 Indexed Resources:")
    print(f"   Models:   {format_number(stats.get('models_count', 0))}")
    print(f"   Datasets: {format_number(stats.get('datasets_count', 0))}")
    print(f"   Spaces:   {format_number(stats.get('spaces_count', 0))}")
    print(f"   Papers:   {format_number(stats.get('papers_count', 0))}")
    
    print(f"\n🔄 Total Crawls: {stats.get('total_crawls', 0)}")
    
    if stats.get('last_crawls'):
        print("\n⏰ Last Crawl Times:")
        for resource_type, timestamp in stats['last_crawls'].items():
            print(f"   {resource_type}: {timestamp}")


def cmd_interactive(args):
    """Start interactive mode."""
    print_banner()
    
    agent = HFAgent()
    kb = KnowledgeBase()
    
    print("🎮 Interactive Mode")
    print("   Commands: crawl, search <query>, stats, priority, export, quit")
    print("-" * 60)
    
    while True:
        try:
            cmd = input("\n🔥 PROMETHEUS> ").strip()
            
            if not cmd:
                continue
            
            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()
            
            if action == "quit" or action == "exit":
                print("👋 Goodbye!")
                break
            
            elif action == "crawl":
                print("Starting crawl...")
                results = agent.crawl_all(100)
                print(json.dumps(results, indent=2, default=str))
            
            elif action == "search":
                if len(parts) < 2:
                    print("Usage: search <query>")
                    continue
                query = parts[1]
                results = agent.search(query, "all", 10)
                for r in results:
                    print(f"[{r.get('type')}] {r.get('id')} - {r.get('name')}")
            
            elif action == "semantic":
                if len(parts) < 2:
                    print("Usage: semantic <query>")
                    continue
                query = parts[1]
                results = kb.semantic_search(query, 10)
                for r in results:
                    print(f"[{r.resource_type}] {r.id} (score: {r.score:.4f})")
            
            elif action == "stats":
                stats = agent.get_stats()
                print(json.dumps(stats, indent=2, default=str))
            
            elif action == "priority":
                results = agent.get_priority_resources()
                print(json.dumps(results, indent=2, default=str))
            
            elif action == "export":
                path = agent.export_knowledge()
                print(f"Exported to: {path}")
            
            elif action == "help":
                print("Commands:")
                print("  crawl      - Run a full crawl")
                print("  search <q> - Keyword search")
                print("  semantic <q> - Semantic search")
                print("  stats      - Show statistics")
                print("  priority   - Show priority resources")
                print("  export     - Export knowledge base")
                print("  quit       - Exit")
            
            else:
                print(f"Unknown command: {action}. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PROMETHEUS - HF-Agent-Infinite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Interactive mode
  python main.py crawl              # Full crawl
  python main.py crawl --type models --limit 1000
  python main.py search "llama gguf"
  python main.py serve              # Start API server
  python main.py daemon             # Start all services
  python main.py stats              # Show statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Crawl HF resources")
    crawl_parser.add_argument("--type", default="all", choices=["all", "models", "datasets", "spaces"])
    crawl_parser.add_argument("--limit", type=int, default=1000)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search indexed resources")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--type", default="all", choices=["all", "models", "datasets", "spaces"])
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--semantic", action="store_true", help="Use semantic search")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true")
    
    # Daemon command
    daemon_parser = subparsers.add_parser("daemon", help="Start all services")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Route to appropriate command
    if args.command == "crawl":
        cmd_crawl(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    elif args.command == "stats":
        cmd_stats(args)
    else:
        # Default to interactive mode
        cmd_interactive(args)


if __name__ == "__main__":
    main()
