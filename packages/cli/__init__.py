#!/usr/bin/env python3
"""
Greg CLI Runner

Commands:
    dev         Start infrastructure, run migrations, and start API server
    server      Start the Writer API server (port 8080)
    songwriter  Start the Songwriter API server (port 8081)
    frontend    Start the Next.js frontend (port 3000)
    worker      Start the ARQ background worker
    infra       Start PostgreSQL and Redis (docker-compose)
    infra-stop  Stop infrastructure containers
    migrate     Run database migrations
    console     Interactive Python console with DB access
    test        Run tests
    models      List available LLM models
    clean       Clean temporary files
    help        Show this help message

Examples:
    greg dev              # Full development environment
    greg server           # Writer app (port 8080)
    greg songwriter       # Songwriter app (port 8081)
    greg frontend         # Next.js frontend (port 3000)
    greg console          # Interactive DB console
    greg worker           # Just the background worker
    greg test             # Run test suite
    greg test -k "test_auth"  # Run specific tests
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Project root (two levels up from packages/cli/)
ROOT = Path(__file__).parent.parent.parent

# Load environment variables from .env
def load_env():
    """Load .env file into environment."""
    env_file = ROOT / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    # Remove quotes if present
                    value = value.strip().strip("'\"")
                    os.environ.setdefault(key.strip(), value)


def run_cmd(cmd: list[str], env: dict | None = None, check: bool = False) -> int:
    """Run a command and return exit code."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.call(cmd, cwd=ROOT, env=full_env)
    if check and result != 0:
        sys.exit(result)
    return result


def run_silent(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command and capture output."""
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def check_docker():
    """Check if Docker is available."""
    code, _, _ = run_silent(["docker", "info"])
    return code == 0


def wait_for_postgres(timeout: int = 30) -> bool:
    """Wait for PostgreSQL to be ready."""
    import socket

    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "5433"))

    print(f"  Waiting for PostgreSQL at {host}:{port}...", end="", flush=True)

    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(" ready")
                return True
        except socket.error:
            pass
        time.sleep(0.5)
        print(".", end="", flush=True)

    print(" timeout!")
    return False


def wait_for_redis(timeout: int = 30) -> bool:
    """Wait for Redis to be ready."""
    import socket

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    # Parse host:port from URL
    if redis_url.startswith("redis://"):
        redis_url = redis_url[8:]
    if "@" in redis_url:
        redis_url = redis_url.split("@", 1)[1]
    if "/" in redis_url:
        redis_url = redis_url.split("/", 1)[0]

    if ":" in redis_url:
        host, port_str = redis_url.rsplit(":", 1)
        port = int(port_str)
    else:
        host = redis_url
        port = 6379

    print(f"  Waiting for Redis at {host}:{port}...", end="", flush=True)

    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(" ready")
                return True
        except socket.error:
            pass
        time.sleep(0.5)
        print(".", end="", flush=True)

    print(" timeout!")
    return False


def cmd_infra():
    """Start PostgreSQL and Redis with docker-compose."""
    if not check_docker():
        print("Error: Docker is not running. Please start Docker first.")
        sys.exit(1)

    print("Starting infrastructure...")
    run_cmd(["docker", "compose", "up", "-d"], check=True)
    print("Infrastructure started.")
    print("  PostgreSQL: localhost:5432")
    print("  Redis: localhost:6379")


def cmd_infra_stop():
    """Stop infrastructure containers."""
    print("Stopping infrastructure...")
    run_cmd(["docker", "compose", "down"])


def cmd_migrate():
    """Run database migrations."""
    print("Running database migrations...")
    run_cmd(["uv", "run", "alembic", "upgrade", "head"], check=True)


def cmd_server():
    """Start the API server (writer app)."""
    print("Starting Greg API server...")
    print("API docs at: http://localhost:8080/docs")
    run_cmd(["uv", "run", "python", "main.py"])


def cmd_songwriter():
    """Start the Songwriter app."""
    print("Starting Songwriter API server...")
    print("API docs at: http://localhost:8081/docs")
    run_cmd(["uv", "run", "uvicorn", "apps.songwriter.app:app", "--port", "8081", "--reload"])


def cmd_worker():
    """Start the ARQ background worker."""
    print("Starting ARQ worker...")
    run_cmd(["uv", "run", "arq", "packages.core.jobs.worker.WorkerSettings"])


def cmd_dev():
    """Start full development environment."""
    print("=" * 50)
    print("Starting Greg Development Environment")
    print("=" * 50)
    print()

    # Start infrastructure
    if check_docker():
        print("[1/4] Starting infrastructure...")
        run_cmd(["docker", "compose", "up", "-d"])

        # Wait for services
        print("[2/4] Waiting for services...")
        if not wait_for_postgres():
            print("Error: PostgreSQL did not start in time")
            sys.exit(1)
        if not wait_for_redis():
            print("Error: Redis did not start in time")
            sys.exit(1)
    else:
        print("[1/4] Skipping infrastructure (Docker not available)")
        print("  Make sure PostgreSQL and Redis are running manually")
        print("[2/4] Skipping service wait")

    # Run migrations
    print("[3/4] Running migrations...")
    run_cmd(["uv", "run", "alembic", "upgrade", "head"], check=True)

    # Check Ollama
    import shutil
    if shutil.which("ollama"):
        code, _, _ = run_silent(["ollama", "list"])
        if code != 0:
            print("  Starting Ollama...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(2)

    # Start API server
    print("[4/4] Starting API server...")
    print()
    print("=" * 50)
    print("Greg is ready!")
    print("  API: http://localhost:8080")
    print("  Docs: http://localhost:8080/docs")
    print("=" * 50)
    print()
    cmd_server()


def cmd_test(args: list[str] = None):
    """Run tests."""
    test_args = ["uv", "run", "pytest"]
    if args:
        test_args.extend(args)
    else:
        test_args.extend(["-v"])
    run_cmd(test_args)


def cmd_clean():
    """Clean temporary files."""
    print("Cleaning temporary files...")

    patterns = [
        "**/__pycache__",
        "**/*.pyc",
        ".pytest_cache",
        "uploads/*",
        "vector_stores/*",
    ]

    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if path.is_dir():
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            elif path.is_file():
                path.unlink(missing_ok=True)

    print("Done.")


def cmd_models():
    """List available LLM models."""
    print("Checking available models...\n")

    # Check Ollama models
    import shutil
    if shutil.which("ollama"):
        print("Ollama Models:")
        code, stdout, _ = run_silent(["ollama", "list"])
        if code == 0:
            for line in stdout.strip().split("\n"):
                print(f"  {line}")
        else:
            print("  Ollama not running")
    else:
        print("Ollama: Not installed")

    print()

    # Check for API keys
    providers = {
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Google": "GOOGLE_API_KEY",
    }

    print("API Providers:")
    for name, key in providers.items():
        if os.getenv(key):
            print(f"  {name}: Configured")
        else:
            print(f"  {name}: Not configured (set {key} in .env)")


def cmd_console():
    """Start an interactive Python console with database access."""
    print("Starting Greg console...")
    print("Loading models and database connection...\n")

    startup_code = '''
import asyncio
from uuid import UUID

# Database
from packages.core.database import init_database, get_session

# Songwriter models
from apps.songwriter.models import (
    AgentReview,
    ChordPlacement,
    Line,
    Section,
    Song,
    SongSection,
)
from apps.songwriter.enums import AgentTaskType, AgentType, SectionType, SongStatus
from apps.songwriter.services.db_store import SongDBStore

# SQLAlchemy
from sqlalchemy import select, delete, update, func
from sqlalchemy.orm import selectinload

# Create event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


def run(coro):
    """Run an async coroutine. Usage: run(store.list_all())"""
    return loop.run_until_complete(coro)


async def _init():
    await init_database()
    print("Database connected")


run(_init())


async def get_store():
    """Get a fresh SongDBStore with a new session."""
    async with get_session() as session:
        return SongDBStore(session)


print()
print("Available:")
print("  run(coro)             - Run async code")
print("  get_store()           - Get a SongDBStore (use with run)")
print("  Song, SongSection     - SQLModel models")
print("  Line, ChordPlacement  - Pydantic models")
print("  select, func          - SQLAlchemy query helpers")
print()
print("Examples:")
print("  async def list_songs():")
print("      async with get_session() as session:")
print("          store = SongDBStore(session)")
print("          return await store.list_all()")
print()
print("  songs = run(list_songs())")
print("  [s.title for s in songs]")
print()
'''

    import shutil
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(startup_code)
        startup_file = f.name

    if shutil.which("ipython"):
        run_cmd(["uv", "run", "ipython", "-i", startup_file])
    else:
        run_cmd(["uv", "run", "python", "-i", startup_file])


def cmd_frontend():
    """Start the Songwriter web frontend."""
    frontend_dir = ROOT / "apps" / "songwriter-web"
    if not frontend_dir.exists():
        print("Error: apps/songwriter-web directory not found")
        sys.exit(1)

    # Check for node_modules
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        result = subprocess.call(["npm", "install"], cwd=frontend_dir)
        if result != 0:
            print("Error: Failed to install dependencies")
            sys.exit(1)

    print("Starting Next.js frontend...")
    print("Frontend: http://localhost:3000")
    subprocess.call(["npm", "run", "dev"], cwd=frontend_dir)


def cmd_help():
    """Show help message."""
    print(__doc__)


def main():
    # Load environment first
    load_env()

    if len(sys.argv) < 2:
        cmd_help()
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    commands = {
        # Development
        "dev": cmd_dev,
        "start": cmd_dev,  # Alias

        # Individual services
        "server": cmd_server,
        "api": cmd_server,  # Alias
        "writer": cmd_server,  # Alias
        "songwriter": cmd_songwriter,
        "frontend": cmd_frontend,
        "web": cmd_frontend,  # Alias
        "worker": cmd_worker,

        # Infrastructure
        "infra": cmd_infra,
        "infra-stop": cmd_infra_stop,
        "up": cmd_infra,  # Alias
        "down": cmd_infra_stop,  # Alias

        # Database
        "migrate": cmd_migrate,
        "db": cmd_migrate,  # Alias
        "console": cmd_console,
        "c": cmd_console,  # Alias

        # Testing
        "test": lambda: cmd_test(args),

        # Utilities
        "models": cmd_models,
        "clean": cmd_clean,

        # Help
        "help": cmd_help,
        "-h": cmd_help,
        "--help": cmd_help,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print("Run 'greg help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
