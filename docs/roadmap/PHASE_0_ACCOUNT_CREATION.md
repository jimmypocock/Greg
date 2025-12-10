# Phase 0: Setup

> **Goal**: Set up all accounts, tools, and environments needed for the project.
> 
> **Time**: 2-3 hours
> 
> **Outcome**: Ready to start coding with Colab Pro, local environment, and Git repo initialized.

---

## Checklist

```
[ ] Accounts created (GitHub, Google/Colab Pro, Hugging Face)
[ ] Local Python environment working
[ ] Project structure created
[ ] Git repository initialized
[ ] Colab Pro subscription active
[ ] VS Code configured (optional but recommended)
```

---

## 1. Create Required Accounts

### Accounts Overview

| Account | Purpose | Cost | Link |
|---------|---------|------|------|
| **GitHub** | Code repository, version control | Free | You likely have this |
| **Google Account** | Colab Pro | $9.99/month | [colab.research.google.com](https://colab.research.google.com) |
| **Hugging Face** | Model hub + free deployment | Free | [huggingface.co/join](https://huggingface.co/join) |
| **Weights & Biases** | Experiment tracking (optional) | Free | [wandb.ai](https://wandb.ai) |

### Google Colab Pro Subscription

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. Click the gear icon (⚙️) in the top right
3. Select "Colab Pro" → Subscribe ($9.99/month)

**Benefits for this project:**
- Faster CPUs (embedding generation is CPU-bound for small models)
- More RAM (important for large document sets)
- Background execution (notebooks keep running when you close the tab)
- GPU access when needed (for larger embedding models)
- Longer runtime limits (up to 24 hours vs 12 hours)

**Note**: For Phases 1-6, you'll mostly use CPU. GPU helps if you choose larger embedding models or have 100k+ documents.

### Hugging Face Account Setup

1. Create account at [huggingface.co](https://huggingface.co)
2. Verify your email
3. Create an access token:
   - Click your profile → Settings → Access Tokens
   - Click "New Token"
   - Name: `semantic-search-project`
   - Role: **Write** (needed for Spaces deployment)
   - Click "Generate"
   - **Copy and save securely** (you won't see it again)

Store this token somewhere safe—you'll need it for Phase 5 (Deployment).

---

## 2. Local Development Environment

Even though heavy compute runs in Colab, you need a local setup for:
- Writing and organizing code
- Git version control  
- Testing small changes quickly
- Running the deployed app locally before pushing

### Check Python Version

```bash
python --version
# or
python3 --version
```

You need **Python 3.9 or higher**. Recommended: Python 3.11.

**If you need to install/upgrade Python:**

```bash
# macOS with Homebrew
brew install python@3.11

# Or use pyenv (recommended for managing multiple versions)
brew install pyenv
pyenv install 3.11.7
pyenv global 3.11.7
```

### Create Project Directory and Virtual Environment

```bash
# Create project directory
mkdir semantic-search-docs
cd semantic-search-docs

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Verify activation (should show venv path)
which python
```

### Create requirements.txt

```bash
cat > requirements.txt << 'EOF'
# Core ML
sentence-transformers>=2.2.0
faiss-cpu>=1.7.4
torch>=2.0.0

# Data handling
pandas>=2.0.0
numpy>=1.24.0
datasets>=2.14.0
beautifulsoup4>=4.12.0
requests>=2.31.0

# UI and deployment
gradio>=4.0.0

# Development
jupyter>=1.0.0
ipykernel>=6.25.0
python-dotenv>=1.0.0
scikit-learn>=1.3.0
tqdm>=4.66.0

# Optional: experiment tracking
# wandb>=0.15.0

# Phase 7 (RAG) - uncomment when needed
# anthropic>=0.18.0
# pymupdf>=1.24.0
# nbformat>=5.9.0
EOF
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

This will take a few minutes. The largest downloads are:
- `torch` (~2GB)
- `sentence-transformers` (includes model downloads)

### Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Virtual environment
venv/
.venv/
env/

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
*.egg-info/

# Jupyter
.ipynb_checkpoints/

# Data and models (too large for git)
data/raw/*
data/processed/*
indexes/*.index
indexes/*.faiss
*.faiss

# Keep directory structure
!data/raw/.gitkeep
!data/processed/.gitkeep
!indexes/.gitkeep

# Environment variables (NEVER commit these)
.env
*.env
.env.local

# OS files
.DS_Store
Thumbs.db
Desktop.ini

# IDE
.vscode/settings.json
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# Model downloads (will be re-downloaded)
models/
EOF
```

### Create .env.example

```bash
cat > .env.example << 'EOF'
# Copy this file to .env and fill in your values
# NEVER commit .env to git!

# Hugging Face (for deployment)
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx

# Phase 7: LLM API (uncomment one)
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# Optional: Weights & Biases
# WANDB_API_KEY=xxxxxxxxxxxxxxxxxxxxx
EOF
```

### Create Project Structure

```bash
# Create directories
mkdir -p notebooks src data/raw data/processed indexes tests docs

# Create placeholder files to preserve directory structure in git
touch data/raw/.gitkeep
touch data/processed/.gitkeep  
touch indexes/.gitkeep
touch src/__init__.py
touch tests/__init__.py

# Create empty app file
touch app.py
```

Your structure should now look like:

```
semantic-search-docs/
├── .gitignore
├── .env.example
├── requirements.txt
├── app.py
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   └── processed/
│       └── .gitkeep
├── indexes/
│   └── .gitkeep
├── notebooks/
├── src/
│   └── __init__.py
├── tests/
│   └── __init__.py
├── docs/
└── venv/
```

### Initialize Git Repository

```bash
# Initialize git
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial project structure"
```

### Create GitHub Repository

1. Go to [github.com/new](https://github.com/new)
2. Name: `semantic-search-docs` (or your preference)
3. Description: "Semantic search engine for documentation using embeddings and FAISS"
4. Visibility: Public (recommended for portfolio)
5. **Don't** initialize with README (we already have files)
6. Click "Create repository"

```bash
# Connect local repo to GitHub (use your username)
git remote add origin https://github.com/YOUR_USERNAME/semantic-search-docs.git
git branch -M main
git push -u origin main
```

---

## 3. Google Colab Pro Setup

### Connecting Colab to Your GitHub Repo

1. Open [colab.research.google.com](https://colab.research.google.com)
2. File → Open notebook → **GitHub** tab
3. Authorize GitHub access when prompted
4. You can now open notebooks directly from your repo

### Mount Google Drive (Persistent Storage)

Colab VMs reset after:
- ~90 minutes of idle time
- 12-24 hours maximum runtime (depending on subscription)

**Google Drive provides persistence** between sessions:

```python
# Run this at the start of every Colab session
from google.colab import drive
drive.mount('/content/drive')

# Create project folder in Drive
import os
PROJECT_DIR = '/content/drive/MyDrive/semantic-search-docs'
os.makedirs(PROJECT_DIR, exist_ok=True)
os.makedirs(f'{PROJECT_DIR}/data', exist_ok=True)
os.makedirs(f'{PROJECT_DIR}/indexes', exist_ok=True)

print(f"Project directory: {PROJECT_DIR}")
```

### Colab Notebook Template

Create this as your starting template. Save it as `notebooks/00_template.ipynb`:

```python
# Cell 1: Setup (run first every session)
# =========================================

import sys
IN_COLAB = 'google.colab' in sys.modules

if IN_COLAB:
    # Mount Google Drive for persistent storage
    from google.colab import drive
    drive.mount('/content/drive')
    
    # Install required packages (Colab resets between sessions)
    !pip install -q sentence-transformers faiss-cpu gradio datasets tqdm
    
    # Set up project directory in Drive
    import os
    PROJECT_DIR = '/content/drive/MyDrive/semantic-search-docs'
    os.makedirs(PROJECT_DIR, exist_ok=True)
    os.makedirs(f'{PROJECT_DIR}/data/raw', exist_ok=True)
    os.makedirs(f'{PROJECT_DIR}/data/processed', exist_ok=True)
    os.makedirs(f'{PROJECT_DIR}/indexes', exist_ok=True)
    
    print(f"Working directory: {PROJECT_DIR}")
else:
    # Local development
    PROJECT_DIR = '.'
    print("Running locally")

# Cell 2: Imports
# ===============

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
from typing import List, Dict, Tuple
import json
import time
from tqdm import tqdm

print("All imports successful!")

# Cell 3: Verify GPU (optional)
# =============================

import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    print("Using CPU (fine for this project)")
```

### Colab Runtime Settings

To use GPU (optional for this project):

1. Runtime → Change runtime type
2. Hardware accelerator: **T4 GPU** (or leave as None/CPU)
3. Click Save

**For Phases 1-6**: CPU is usually sufficient and preserves your GPU quota.

### Saving Work to Drive

Always save important outputs to Drive, not the Colab VM:

```python
# Save FAISS index to Drive
DRIVE_PROJECT = '/content/drive/MyDrive/semantic-search-docs'
faiss.write_index(index, f'{DRIVE_PROJECT}/indexes/docs.index')

# Save metadata
with open(f'{DRIVE_PROJECT}/data/processed/metadata.json', 'w') as f:
    json.dump(metadata, f)

# Load in next session
index = faiss.read_index(f'{DRIVE_PROJECT}/indexes/docs.index')
```

---

## 4. VS Code Configuration (Recommended)

### Essential Extensions

Install these VS Code extensions:

```json
// Recommended extensions (search in VS Code Extensions panel)
- ms-python.python           // Python language support
- ms-python.vscode-pylance   // Python IntelliSense
- ms-toolsai.jupyter         // Jupyter notebook support
- github.copilot             // AI assistance (you have this)
```

### Workspace Settings

Create `.vscode/settings.json`:

```bash
mkdir -p .vscode
cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "none",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.python"
    },
    "jupyter.widgetScriptSources": ["jsdelivr.com", "unpkg.com"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/.ipynb_checkpoints": true,
        "**/venv": true
    }
}
EOF
```

### Remote Development (For Cloud GPUs)

If you later use cloud GPU instances (RunPod, Vast.ai, etc.), the **Remote-SSH** extension lets you:
- Connect VS Code to remote machines
- Edit files directly on the remote
- Run/debug Python on the remote GPU

Install: `ms-vscode-remote.remote-ssh`

---

## 5. Verify Everything Works

### Test Local Environment

```bash
# Make sure venv is activated
source venv/bin/activate

# Test Python
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import sentence_transformers; print('Sentence Transformers: OK')"
python -c "import faiss; print('FAISS: OK')"
python -c "import gradio; print('Gradio: OK')"
```

All should print without errors.

### Test Colab Connection

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. Create a new notebook
3. Run:

```python
# Test installs
!pip install -q sentence-transformers faiss-cpu

from sentence_transformers import SentenceTransformer
import faiss

# Quick embedding test
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(["Hello world", "Hi there"])
print(f"Embedding shape: {embeddings.shape}")  # Should be (2, 384)

# Quick FAISS test
index = faiss.IndexFlatIP(384)
faiss.normalize_L2(embeddings)
index.add(embeddings)
print(f"Index size: {index.ntotal}")  # Should be 2

print("\n✅ All tests passed!")
```

If this runs without errors, you're ready to proceed.

---

## 6. Phase 7 Setup (Do Later)

When you reach Phase 7 (RAG), you'll need additional setup:

### Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create account and add payment method
3. Generate API key
4. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
   ```

### Additional Dependencies

```bash
# Add to requirements.txt when ready
pip install anthropic pymupdf nbformat
```

**Don't worry about this now**—complete Phases 1-6 first.

---

## Troubleshooting Common Setup Issues

### "pip install fails with permission error"

Make sure your virtual environment is activated:
```bash
source venv/bin/activate
which pip  # Should show path inside venv/
```

### "torch installation is huge/slow"

This is normal. PyTorch is ~2GB. Use a stable internet connection and be patient.

### "FAISS import fails on Mac M1/M2"

Install the correct version:
```bash
pip uninstall faiss-cpu
pip install faiss-cpu --no-cache-dir
```

### "Colab keeps disconnecting"

- Keep the browser tab active (don't minimize)
- Click somewhere in the notebook periodically
- Use Colab Pro for longer sessions
- Save to Drive frequently

### "Can't push to GitHub"

Make sure you've authenticated:
```bash
# If using HTTPS
git config --global credential.helper store
# Then push and enter username/token when prompted

# Or use SSH (recommended)
# Set up SSH key at github.com/settings/keys
```

---

## Summary

At the end of Phase 0, you should have:

| Item | Status |
|------|--------|
| GitHub account | ✓ Exists |
| Hugging Face account + token | ✓ Created and saved |
| Google Colab Pro | ✓ Subscribed |
| Local Python 3.9+ | ✓ Installed |
| Virtual environment | ✓ Created and activated |
| Dependencies | ✓ Installed |
| Project structure | ✓ Created |
| Git repo | ✓ Initialized and pushed |
| Colab test | ✓ Working |

---

## Next Step

→ Proceed to **PHASE_1.md** to learn about embeddings and build intuition for how they work.
