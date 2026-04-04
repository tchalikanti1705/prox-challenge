"""
Entry point for the OmniPro 220 Expert Agent backend.

Run with: python app.py
Server will start on http://0.0.0.0:8000

Before running, make sure to:
1. Set ANTHROPIC_API_KEY in .env
2. Run scripts/extract.py to build the knowledge base first
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn

from api.routes import router
from knowledge.store import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load knowledge base on startup, cleanup on shutdown."""
    print("\n🚀 Starting OmniPro 220 Expert Agent...\n")

    try:
        store.load()

        if store.is_loaded:
            print("✅ Backend ready!")
            print(f"   - {len(store.chunks)} text chunks loaded")
            print(f"   - {len(store.image_catalog)} images cataloged")
            print(f"   - Processes: {list(store.structured_data.get('polarity', {}).keys())}")
            print("\n📍 API running at http://0.0.0.0:8000")
            print("📍 Docs at http://0.0.0.0:8000/docs\n")
        else:
            print("⚠️ Knowledge base failed to load")
            print("💡 Run: python scripts/extract.py")

    except Exception as e:
        print(f"❌ Startup error: {e}")

    yield

    print("\n👋 Shutting down OmniPro 220 Expert Agent")


# Create FastAPI app
app = FastAPI(
    title="OmniPro 220 Expert",
    description="Multimodal AI advisor for the Vulcan OmniPro 220 welder",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (allow frontend to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Serve frontend static files — mount AFTER API routes so /api/* takes priority
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import sys
    import os
    
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Ensure the backend package is importable when run from project root
    backend_dir = Path(__file__).parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    # Start server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
