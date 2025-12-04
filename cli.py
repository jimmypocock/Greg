#!/usr/bin/env python3
"""
Greg CLI - Command Line Interface for the Greg RAG API

A simple CLI for interacting with documents and LLMs.
Supports streaming responses, document uploads, and web search.
"""

import argparse
import sys
import json
import requests
from pathlib import Path
from typing import Optional

# Default API URL
API_URL = "http://localhost:8080"


def print_error(message: str):
    """Print error message in red"""
    print(f"\033[91m✗ {message}\033[0m", file=sys.stderr)


def print_success(message: str):
    """Print success message in green"""
    print(f"\033[92m✓ {message}\033[0m")


def print_info(message: str):
    """Print info message in blue"""
    print(f"\033[94mℹ {message}\033[0m")


def check_api():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def cmd_health(args):
    """Check API health"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        data = response.json()

        print(f"\nStatus: {data.get('status', 'unknown')}")

        if 'memory' in data:
            mem = data['memory']
            print(f"\nMemory:")
            print(f"  Available: {mem.get('available_gb', '?')} GB")
            print(f"  Used: {mem.get('percent_used', '?')}%")
            print(f"  Total: {mem.get('total_gb', '?')} GB")

        if 'model' in data:
            print(f"\nDefault Model: {data['model']}")

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Is it running?")
        print_info("Start the API with: make api")
        sys.exit(1)


def cmd_models(args):
    """List available models"""
    try:
        response = requests.get(f"{API_URL}/models", timeout=10)
        data = response.json()

        models = data.get('models', [])
        if not models:
            print_info("No models available")
            return

        print(f"\nAvailable Models ({len(models)}):\n")
        print(f"{'Name':<30} {'Provider':<10} {'Size':<10}")
        print("-" * 50)

        for model in models:
            name = model.get('name', 'unknown')
            provider = model.get('provider', 'unknown')
            size = model.get('size', 'N/A')
            default = " (default)" if name == data.get('default') else ""
            print(f"{name:<30} {provider:<10} {size:<10}{default}")

        print(f"\nProviders:")
        for provider, info in data.get('providers', {}).items():
            status = "✓" if info.get('available') else "✗"
            reason = f" - {info.get('reason')}" if info.get('reason') else ""
            print(f"  {status} {provider}{reason}")

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API")
        sys.exit(1)


def cmd_documents(args):
    """List processed documents"""
    try:
        response = requests.get(f"{API_URL}/documents", timeout=10)
        data = response.json()

        docs = data.get('documents', [])
        if not docs:
            print_info("No documents loaded")
            print_info("Upload a document with: greg upload <file>")
            return

        print(f"\nDocuments ({len(docs)}):\n")
        print(f"{'Filename':<40} {'Pages':<8} {'Chunks':<8}")
        print("-" * 60)

        for doc in docs:
            filename = doc.get('filename', 'unknown')
            pages = doc.get('pages', '?')
            chunks = doc.get('chunks', '?')
            print(f"{filename:<40} {pages:<8} {chunks:<8}")

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API")
        sys.exit(1)


def cmd_upload(args):
    """Upload a document"""
    file_path = Path(args.file)

    if not file_path.exists():
        print_error(f"File not found: {file_path}")
        sys.exit(1)

    print_info(f"Uploading {file_path.name}...")

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f)}
            data = {'chunk_size': args.chunk_size}
            response = requests.post(
                f"{API_URL}/upload",
                files=files,
                data=data,
                timeout=300  # 5 minute timeout for large files
            )

        if response.status_code == 200:
            result = response.json()
            print_success(f"Uploaded: {file_path.name}")
            print(f"  Document ID: {result.get('document_id')}")
            print(f"  Pages: {result.get('pages')}")
            print(f"  Chunks: {result.get('chunks')}")
            print(f"  Processing time: {result.get('processing_time', 0):.2f}s")
        else:
            print_error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API")
        sys.exit(1)


def stream_response(response):
    """Stream and print the response"""
    full_response = ""

    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')

            # Handle SSE format
            if line_str.startswith('data: '):
                data = line_str[6:]  # Remove 'data: ' prefix

                # Check for end of stream
                if data == '[DONE]':
                    break

                try:
                    chunk = json.loads(data)
                    if 'content' in chunk:
                        content = chunk['content']
                        print(content, end='', flush=True)
                        full_response += content
                    elif 'error' in chunk:
                        print_error(chunk['error'])
                except json.JSONDecodeError:
                    # Plain text chunk
                    print(data, end='', flush=True)
                    full_response += data
            else:
                # Plain text response
                print(line_str, end='', flush=True)
                full_response += line_str

    print()  # Final newline
    return full_response


def cmd_ask(args):
    """Ask a question about documents"""
    question = ' '.join(args.question)

    if not question:
        print_error("Please provide a question")
        sys.exit(1)

    payload = {
        "question": question,
        "document_id": args.document or "unified",
        "use_web_search": args.web,
        "stream": True
    }

    if args.model:
        payload["model_name"] = args.model

    if args.temperature:
        payload["temperature"] = args.temperature

    try:
        print()  # Empty line before response

        response = requests.post(
            f"{API_URL}/ask",
            json=payload,
            stream=True,
            timeout=120
        )

        if response.status_code != 200:
            error = response.json().get('detail', 'Unknown error')
            print_error(f"Error: {error}")
            sys.exit(1)

        stream_response(response)
        print()  # Extra newline after response

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted")


def cmd_search(args):
    """Search the web"""
    query = ' '.join(args.query)

    if not query:
        print_error("Please provide a search query")
        sys.exit(1)

    payload = {
        "question": query,
        "document_id": "web_only",
        "use_web_search": True
    }

    if args.model:
        payload["model_name"] = args.model

    try:
        print()  # Empty line before response

        response = requests.post(
            f"{API_URL}/web-search",
            json=payload,
            stream=True,
            timeout=120
        )

        if response.status_code != 200:
            error = response.json().get('detail', 'Unknown error')
            print_error(f"Error: {error}")
            sys.exit(1)

        stream_response(response)
        print()  # Extra newline after response

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted")


def cmd_chat(args):
    """Interactive chat mode"""
    print("\n" + "=" * 50)
    print("Greg - Interactive Chat")
    print("=" * 50)
    print("Type your questions. Use 'exit' or Ctrl+C to quit.")
    print("Use '/web' prefix for web search mode.")
    print("Use '/upload <file>' to upload a document.")
    print("=" * 50 + "\n")

    model = args.model
    web_mode = args.web

    while True:
        try:
            # Get user input
            prompt = "\033[92mYou:\033[0m " if not web_mode else "\033[94mYou (web):\033[0m "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print_info("Goodbye!")
                break

            if user_input.startswith('/web'):
                web_mode = not web_mode
                mode = "enabled" if web_mode else "disabled"
                print_info(f"Web search {mode}")
                continue

            if user_input.startswith('/upload '):
                file_path = user_input[8:].strip()
                # Create a mock args object
                class UploadArgs:
                    pass
                upload_args = UploadArgs()
                upload_args.file = file_path
                upload_args.chunk_size = 800
                cmd_upload(upload_args)
                continue

            if user_input.startswith('/model '):
                model = user_input[7:].strip()
                print_info(f"Model set to: {model}")
                continue

            if user_input == '/models':
                class ModelsArgs:
                    pass
                cmd_models(ModelsArgs())
                continue

            if user_input == '/docs':
                class DocsArgs:
                    pass
                cmd_documents(DocsArgs())
                continue

            if user_input == '/help':
                print("\nCommands:")
                print("  /web       - Toggle web search mode")
                print("  /upload <file> - Upload a document")
                print("  /model <name>  - Switch model")
                print("  /models    - List available models")
                print("  /docs      - List loaded documents")
                print("  /help      - Show this help")
                print("  exit       - Quit\n")
                continue

            # Ask the question
            print("\n\033[93mGreg:\033[0m ", end='', flush=True)

            payload = {
                "question": user_input,
                "document_id": "unified",
                "use_web_search": web_mode,
                "stream": True
            }

            if model:
                payload["model_name"] = model

            endpoint = "/web-search" if web_mode else "/ask"

            response = requests.post(
                f"{API_URL}{endpoint}",
                json=payload,
                stream=True,
                timeout=120
            )

            if response.status_code != 200:
                error = response.json().get('detail', 'Unknown error')
                print_error(f"Error: {error}")
                continue

            stream_response(response)
            print()  # Extra newline

        except KeyboardInterrupt:
            print("\n")
            print_info("Goodbye!")
            break
        except EOFError:
            print_info("Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(
        prog='greg',
        description='Greg CLI - Document Q&A with Local LLMs',
        epilog='Example: greg ask "What is this document about?"'
    )

    parser.add_argument(
        '--api-url',
        default=API_URL,
        help=f'API URL (default: {API_URL})'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Health command
    health_parser = subparsers.add_parser('health', help='Check API health')
    health_parser.set_defaults(func=cmd_health)

    # Models command
    models_parser = subparsers.add_parser('models', help='List available models')
    models_parser.set_defaults(func=cmd_models)

    # Documents command
    docs_parser = subparsers.add_parser('docs', help='List processed documents')
    docs_parser.set_defaults(func=cmd_documents)

    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a document')
    upload_parser.add_argument('file', help='File to upload')
    upload_parser.add_argument(
        '--chunk-size', '-c',
        type=int,
        default=800,
        help='Chunk size for processing (default: 800)'
    )
    upload_parser.set_defaults(func=cmd_upload)

    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question about documents')
    ask_parser.add_argument('question', nargs='+', help='Question to ask')
    ask_parser.add_argument('--model', '-m', help='Model to use')
    ask_parser.add_argument('--document', '-d', help='Document ID to query')
    ask_parser.add_argument(
        '--web', '-w',
        action='store_true',
        help='Also search the web'
    )
    ask_parser.add_argument(
        '--temperature', '-t',
        type=float,
        help='Temperature (0.0-1.0)'
    )
    ask_parser.set_defaults(func=cmd_ask)

    # Search command (web search)
    search_parser = subparsers.add_parser('search', help='Search the web')
    search_parser.add_argument('query', nargs='+', help='Search query')
    search_parser.add_argument('--model', '-m', help='Model to use')
    search_parser.set_defaults(func=cmd_search)

    # Chat command (interactive)
    chat_parser = subparsers.add_parser('chat', help='Interactive chat mode')
    chat_parser.add_argument('--model', '-m', help='Model to use')
    chat_parser.add_argument(
        '--web', '-w',
        action='store_true',
        help='Start in web search mode'
    )
    chat_parser.set_defaults(func=cmd_chat)

    args = parser.parse_args()

    # Update API URL if provided
    global API_URL
    API_URL = args.api_url

    # Default to chat if no command
    if args.command is None:
        # Check if API is running first
        if not check_api():
            print_error("Cannot connect to API")
            print_info("Start the API with: make api")
            sys.exit(1)

        # Start interactive chat
        args.model = None
        args.web = False
        cmd_chat(args)
    else:
        args.func(args)


if __name__ == '__main__':
    main()
