"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import settings
from app.routes import chat, documents

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chat Application",
    description="Retrieval-Augmented Generation Chat Application",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (before SPA routing)
@app.get("/api/health")
async def health():
    """Health check endpoint."""
    is_valid, error = settings.validate()
    return {
        "status": "healthy" if is_valid else "unhealthy",
        "error": error,
        "settings": {
            "llm_model": settings.LLM_MODEL_NAME,
            "pinecone_index": settings.PINECONE_INDEX_NAME,
        }
    }

# Include API routes
app.include_router(chat.router)
app.include_router(documents.router)

# Serve static files (React build)
static_dir = Path(__file__).parent.parent / "static"
static_assets_dir = static_dir / "static"  # React build puts assets in static/static/

if static_dir.exists():
    # Mount the static assets directory (static/static/) to /static
    if static_assets_dir.exists():
        app.mount("/static", StaticFiles(directory=static_assets_dir), name="static")
    else:
        # Fallback: mount the main static directory
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "RAG Chat API", "status": "running"}
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React app for all non-API routes."""
        if not full_path.startswith("api") and not full_path.startswith("static"):
            index_file = static_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
        return {"error": "Not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )

