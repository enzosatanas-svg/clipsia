"""
ClipAI Generator - FastAPI Backend
Main application entry point
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("clipai")

# Create required directories
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "downloads"))
for d in [OUTPUT_DIR, DOWNLOADS_DIR, OUTPUT_DIR / "thumbnails", OUTPUT_DIR / "metadata", OUTPUT_DIR / "renders"]:
    d.mkdir(parents=True, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="ClipAI Generator API",
    description="Backend API for automated viral clip creation in vertical 9:16 format",
    version="1.2.0",
)

# CORS for Streamlit frontend and local browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directories for video & thumbnail serving
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")

PUBLIC_DIR = Path("public")
if PUBLIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static-app")

# Import and register routers
from backend.routers import ingest, process, clips, publish, pipeline

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["One-Click Pipeline"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingestion"])
app.include_router(process.router, prefix="/api/process", tags=["Processing"])
app.include_router(clips.router, prefix="/api/clips", tags=["Clips Library"])
app.include_router(publish.router, prefix="/api/publish", tags=["Publishing"])


from fastapi import BackgroundTasks

@app.post("/api/process-video", tags=["Aliases"])
async def process_video_alias(req: pipeline.OneClickRequest, background_tasks: BackgroundTasks):
    """Alias for /api/pipeline/generate for static frontend clients."""
    return await pipeline.generate_viral_clips(req, background_tasks)


@app.get("/api/status/{job_id}", tags=["Aliases"])
async def status_alias(job_id: str):
    """Alias for /api/pipeline/status/{job_id} for static frontend clients."""
    return await pipeline.get_pipeline_status(job_id)


@app.get("/")
async def root():
    return {
        "app": "ClipAI Generator",
        "version": "1.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "clipai-backend"}

