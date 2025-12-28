#!/usr/bin/env python3
"""
Greg CLI

Commands:
    dev       Start infrastructure, run migrations, and start server
    server    Start the API server (port 8080)
    worker    Start the ARQ background worker
    console   Interactive database console
    infra     Start PostgreSQL and Redis
    migrate   Run database migrations
    test      Run tests
    models    List available LLM models
    clean     Clean temporary files
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


def run(cmd: list[str], check: bool = False) -> int:
    """Run a command and return exit code."""
    result = subprocess.call(cmd, cwd=ROOT)
    if check and result != 0:
        sys.exit(result)
    return result


def capture(cmd: list[str]) -> tuple[int, str]:
    """Run a command and capture output."""
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout


def wait_for_service(host: str, port: int, name: str, timeout: int = 30) -> bool:
    """Wait for a TCP service to be ready."""
    print(f"  Waiting for {name} at {host}:{port}...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                print(" ready")
                return True
        except OSError:
            time.sleep(0.5)
            print(".", end="", flush=True)
    print(" timeout!")
    return False


def docker_available() -> bool:
    """Check if Docker is running."""
    code, _ = capture(["docker", "info"])
    return code == 0


# Commands


def cmd_dev():
    """Start full development environment."""
    print("Starting Greg Development Environment\n")

    if docker_available():
        print("[1/3] Starting infrastructure...")
        run(["docker", "compose", "up", "-d"])

        print("[2/3] Waiting for services...")
        if not wait_for_service("localhost", 5433, "PostgreSQL"):
            sys.exit(1)
        if not wait_for_service("localhost", 6379, "Redis"):
            sys.exit(1)
    else:
        print("[1/3] Docker not available - ensure services are running manually")
        print("[2/3] Skipping service wait")

    print("[3/3] Running migrations...")
    run(["uv", "run", "alembic", "upgrade", "head"], check=True)

    print("\nGreg is ready!")
    print("  API:  http://localhost:8080")
    print("  Docs: http://localhost:8080/docs\n")
    cmd_server()


def cmd_server():
    """Start the API server."""
    print("Starting API server on http://localhost:8080")
    run(["uv", "run", "python", "main.py"])


def cmd_worker():
    """Start the ARQ background worker."""
    print("Starting ARQ worker...")
    run(["uv", "run", "arq", "api.jobs.worker.WorkerSettings"])


def cmd_console():
    """Start interactive database console."""
    run(["uv", "run", "python", str(ROOT / "scripts" / "console.py")])


def cmd_infra(stop: bool = False):
    """Start or stop infrastructure."""
    if stop:
        print("Stopping infrastructure...")
        run(["docker", "compose", "down"])
    else:
        if not docker_available():
            print("Error: Docker is not running")
            sys.exit(1)
        print("Starting infrastructure...")
        run(["docker", "compose", "up", "-d"])
        print("  PostgreSQL: localhost:5433")
        print("  Redis: localhost:6379")


def cmd_migrate():
    """Run database migrations."""
    print("Running migrations...")
    run(["uv", "run", "alembic", "upgrade", "head"], check=True)


def cmd_test(args: list[str]):
    """Run tests."""
    run(["uv", "run", "pytest", "-v"] + args)


def cmd_models():
    """List available LLM models."""
    print("Checking models...\n")

    # Ollama
    code, stdout = capture(["ollama", "list"])
    if code == 0:
        print("Ollama:")
        for line in stdout.strip().split("\n"):
            print(f"  {line}")
    else:
        print("Ollama: Not running or not installed")

    # API providers
    print("\nAPI Providers:")
    for name, key in [("Anthropic", "ANTHROPIC_API_KEY"),
                      ("OpenAI", "OPENAI_API_KEY"),
                      ("Google", "GOOGLE_API_KEY")]:
        status = "configured" if os.getenv(key) else f"not set ({key})"
        print(f"  {name}: {status}")


def cmd_clean():
    """Clean temporary files."""
    import shutil

    print("Cleaning...")
    for pattern in ["**/__pycache__", ".pytest_cache", "uploads/*", "vector_stores/*"]:
        for path in ROOT.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
    print("Done.")


def cmd_help():
    """Show help."""
    print(__doc__)


def main():
    args = sys.argv[1:]

    if not args:
        cmd_help()
        return

    cmd = args[0]
    rest = args[1:]

    commands = {
        "dev": cmd_dev,
        "server": cmd_server,
        "worker": cmd_worker,
        "console": cmd_console,
        "db": cmd_console,  # alias
        "infra": lambda: cmd_infra(stop=False),
        "infra-stop": lambda: cmd_infra(stop=True),
        "migrate": cmd_migrate,
        "test": lambda: cmd_test(rest),
        "models": cmd_models,
        "clean": cmd_clean,
        "help": cmd_help,
        "-h": cmd_help,
        "--help": cmd_help,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'greg help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
