#!/usr/bin/env python3
"""Verify test setup and imports"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Verifying Test Setup")
print("=" * 60)

# Check imports
tests_to_verify = [
    ("Unit test imports", "from src.documents.processor import DocumentProcessor"),
    ("Web search imports", "from src.rag.web_search import WebSearcher"),
    ("UI test imports", "from tests.ui.base_test import StreamlitTest"),
    ("Config imports", "from src.config.settings import Config"),
]

for test_name, import_stmt in tests_to_verify:
    try:
        exec(import_stmt)
        print(f"✅ {test_name}: OK")
    except ImportError as e:
        print(f"❌ {test_name}: FAILED - {e}")

# Check required packages
print("\n📦 Checking Required Packages")
print("-" * 60)

required_packages = [
    "pytest",
    "playwright", 
    "beautifulsoup4",
    "requests",
    "psutil",
    "streamlit",
    "fastapi",
    "langchain",
    "faiss",
]

import importlib
for package in required_packages:
    try:
        importlib.import_module(package.replace("-", "_"))
        print(f"✅ {package}: Installed")
    except ImportError:
        print(f"❌ {package}: NOT INSTALLED")

# Check services
print("\n🔧 Checking Services")
print("-" * 60)

import subprocess

# Check Ollama
try:
    result = subprocess.run(["ollama", "list"], capture_output=True)
    if result.returncode == 0:
        print("✅ Ollama: Available")
    else:
        print("❌ Ollama: Not running")
except FileNotFoundError:
    print("❌ Ollama: Not installed")

# Check if API can start
print("\n✅ Test setup verification complete!")
print("\nTo run all tests: make test")