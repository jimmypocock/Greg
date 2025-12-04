#!/usr/bin/env python3
"""
Greg Project Runner

Replaces Makefile with a Python-based CLI for project management.
Run with: python run.py <command>

Commands:
    api         Start the API server
    cli         Start interactive CLI
    preprocess  Process documents in /documents folder
    test        Run tests
    clean       Clean temporary files
    help        Show this help message
"""

import subprocess
import sys
import os
from pathlib import Path

# Project root
ROOT = Path(__file__).parent


def run_cmd(cmd: list[str], env: dict | None = None) -> int:
    """Run a command and return exit code."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.call(cmd, cwd=ROOT, env=full_env)


def cmd_api():
    """Start the API server."""
    print("Starting Greg API server...")
    print("API docs at: http://localhost:8080/docs")
    run_cmd(["uv", "run", "python", "main.py"])


def cmd_cli():
    """Start interactive CLI."""
    print("Starting Greg CLI...")
    run_cmd(["uv", "run", "python", "cli.py"])


def cmd_preprocess():
    """Process documents in /documents folder."""
    print("Processing documents...")
    run_cmd(["uv", "run", "python", "scripts/preprocess_documents.py"])


def cmd_start():
    """Start API with document preprocessing."""
    print("=" * 50)
    print("Starting Greg")
    print("=" * 50)

    # Check if Ollama is running (for local LLM support)
    import shutil
    if shutil.which("ollama"):
        print("Checking Ollama...")
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("  Ollama is running")
        else:
            print("  Starting Ollama...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    # Preprocess documents
    cmd_preprocess()

    # Start API
    cmd_api()


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
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
        else:
            print("  Ollama not running")
    else:
        print("Ollama: Not installed")

    print()

    # Check for API keys
    from dotenv import load_dotenv
    load_dotenv()

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


def cmd_help():
    """Show help message."""
    print(__doc__)
    print("\nExamples:")
    print("  python run.py start       # Start with preprocessing")
    print("  python run.py api         # Just start API")
    print("  python run.py cli         # Interactive chat")
    print("  python run.py test        # Run tests")
    print("  python run.py models      # List available models")


def main():
    if len(sys.argv) < 2:
        cmd_help()
        return

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    commands = {
        "api": cmd_api,
        "cli": cmd_cli,
        "preprocess": cmd_preprocess,
        "start": cmd_start,
        "run": cmd_start,  # Alias
        "test": lambda: cmd_test(args),
        "clean": cmd_clean,
        "models": cmd_models,
        "help": cmd_help,
        "-h": cmd_help,
        "--help": cmd_help,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python run.py help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    main()
