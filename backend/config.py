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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY not set. Chat will not work until it is configured.")

# ===== PATHS =====
BASE_DIR = Path(__file__).parent
PROJECT_DIR = BASE_DIR.parent
FILES_DIR = PROJECT_DIR / "files"  # The 3 PDF manuals
KNOWLEDGE_DIR = BASE_DIR / "knowledge" / "data"
IMAGES_DIR = KNOWLEDGE_DIR / "images"

# ===== MODEL CONFIGURATION =====
MODEL = "claude-opus-4-20250514"
MAX_TOKENS = 8096

# ===== EMBEDDING & SEARCH =====
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI embeddings (1536 dims)
USE_OPENAI_EMBEDDINGS = bool(OPENAI_API_KEY)  # Auto-enable if key present

# Hybrid search weights (must sum to 1.0)
SEARCH_WEIGHT_EMBEDDING = 0.5
SEARCH_WEIGHT_KEYWORD = 0.3
SEARCH_WEIGHT_STRUCTURED = 0.2

# ===== CACHING =====
TOOL_CACHE_SIZE = 256  # LRU cache for tool results
MAX_CONVERSATION_MESSAGES = 20  # Trim older messages beyond this

# ===== ENSURE DIRECTORIES EXIST =====
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

print(f"✓ Config loaded: BASE_DIR={BASE_DIR}, KNOWLEDGE_DIR={KNOWLEDGE_DIR}")
