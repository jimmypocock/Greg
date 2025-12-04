#!/usr/bin/env python3
"""
Main API server for Greg - AI Playground.

This is the entry point for the FastAPI server.
The actual application is created in src/api/app.py.
"""

import os
import signal
import sys
import logging

# Set offline mode for HuggingFace to prevent HTTP 429 errors
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

import uvicorn

from src.api import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create the FastAPI application
app = create_app()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def start_server():
    """Start the FastAPI server."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get port from environment variable or default to 8080
    port = int(os.environ.get("GREG_API_PORT", 8080))
    logger.info(f"Starting server on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        # Disable multiprocessing reload to avoid semaphore leaks
        reload=False,
        workers=1,
        # Let uvicorn handle signals properly
        loop="asyncio",
        access_log=False,  # Reduce log noise
    )


if __name__ == "__main__":
    # Set multiprocessing start method to avoid semaphore leaks on macOS
    import multiprocessing

    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        pass  # Already set

    start_server()
