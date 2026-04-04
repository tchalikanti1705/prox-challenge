#!/usr/bin/env python
"""
OmniPro 220 Expert - Development Server

Quick development launcher that sets everything up and starts the server.
"""
import os
import sys
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

# Check .env
if not Path(".env").exists():
    print("❌ .env file not found. Creating from .env.example...")
    if Path(".env.example").exists():
        import shutil
        shutil.copy(".env.example", ".env")
        print("✓ .env created. Please edit with your ANTHROPIC_API_KEY")
        sys.exit(1)
    else:
        print("❌ .env.example not found either")
        sys.exit(1)

# Check knowledge base
if not Path("backend/knowledge/data/chunks.json").exists():
    print("\n⚠️ Knowledge base not extracted. This is required.")
    print("\nRunning extraction now...")
    import subprocess
    result = subprocess.run([sys.executable, "backend/scripts/extract.py"])
    if result.returncode != 0:
        print("\n❌ Extraction failed")
        sys.exit(1)

# Start server
print("\n" + "="*60)
print("  Starting OmniPro 220 Expert Backend")
print("="*60 + "\n")

# Use uvicorn directly
import uvicorn
uvicorn.run(
    "backend.app:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    log_level="info"
)
