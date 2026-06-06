"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from .config import get_settings
from .db.database import init_db
from .api.routes import router

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="LumenRoute AI",
    description="AI 视频/图片生成统一网关 — Seedance 2.0 + OpenAI Image",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Serve video files (generated videos, uploaded videos)
storage_path = Path(settings.storage_path)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(storage_path)), name="videos")

# Serve image files (generated images, uploaded images)
images_path = Path("./storage/images")
images_path.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(images_path)), name="images")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("Database initialized")
    print(f"Server running on http://{settings.host}:{settings.port}")


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "LumenRoute AI API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
