"""
Configuration for the OmniPro 220 Expert Agent backend.

All configuration in one place:
- API keys (from .env)
- File paths
- Model settings
- Directory initialization
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# ===== API KEYS =====
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY not set. Chat will not work until it is configured.")

# ===== PATHS =====
BASE_DIR = Path(__file__).parent
PROJECT_DIR = BASE_DIR.parent
FILES_DIR = PROJECT_DIR / "files"  # The 3 PDF manuals
KNOWLEDGE_DIR = BASE_DIR / "knowledge" / "data"
IMAGES_DIR = KNOWLEDGE_DIR / "images"

# ===== MODEL CONFIGURATION =====
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8096

# ===== TOOL CONFIGURATION =====
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI embeddings
USE_OPENAI_EMBEDDINGS = False  # Set to False to skip OpenAI embeddings

# ===== ENSURE DIRECTORIES EXIST =====
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

print(f"✓ Config loaded: BASE_DIR={BASE_DIR}, KNOWLEDGE_DIR={KNOWLEDGE_DIR}")
