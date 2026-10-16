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

# /clips → alias directo para servir videos generados (usado por el frontend estático)
app.mount("/clips", StaticFiles(directory=str(OUTPUT_DIR)), name="clips")

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


import json as _json
from datetime import datetime as _dt


def _enrich_clip_metadata(filename: str, file_path: Path) -> dict:
    """Extrae metadatos enriquecidos del clip: tamaño, URL, título, hashtags, gancho y nicho."""
    # Intentar leer JSON de metadatos del orquestador si existe
    stem = file_path.stem  # ej: clip_1_9x16
    metadata_candidates = [
        OUTPUT_DIR / "metadata" / f"{stem}.json",
        OUTPUT_DIR / f"{stem}_meta.json",
    ]
    meta = {}
    for mc in metadata_candidates:
        if mc.exists():
            try:
                with open(mc, "r", encoding="utf-8") as f:
                    meta = _json.load(f)
                break
            except Exception:
                pass

    # Inferir número de clip desde nombre de archivo
    parts = stem.split("_")
    clip_num = next((p for p in parts if p.isdigit()), "1")

    file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
    created_ts = file_path.stat().st_mtime
    created_str = _dt.fromtimestamp(created_ts).strftime("%d/%m/%Y %H:%M")

    title = meta.get("title") or filename.replace(".mp4", "").replace("_", " ").title()
    hook = meta.get("hook_text") or meta.get("hook") or f"🔥 Clip {clip_num} - Momento Viral"
    niche = meta.get("nicho") or meta.get("niche") or "Interés General"
    viral_score = meta.get("viral_score") or 8.5
    hashtags = meta.get("hashtags") or "#viral #shorts #clipsia #fyp #contenido"
    description = meta.get("description") or meta.get("texto_descripcion") or ""
    ai_copy = meta.get("ai_copy") or ""
    platforms = meta.get("platforms") or {}
    best_posting_times = meta.get("best_posting_times") or ["12:00 - 14:00", "19:00 - 21:00"]
    duration = meta.get("duration") or 0

    return {
        "filename": filename,
        "url": f"/clips/{filename}",
        "thumbnail_url": f"/clips/thumbnails/{stem}.jpg" if (OUTPUT_DIR / "thumbnails" / f"{stem}.jpg").exists() else None,
        "title": title,
        "hook_text": hook,
        "niche": niche,
        "viral_score": viral_score,
        "description": description,
        "hashtags": hashtags,
        "size_mb": file_size_mb,
        "created_at": created_str,
        "clip_index": int(clip_num) if clip_num.isdigit() else 1,
        "ai_copy": ai_copy,
        "platforms": platforms,
        "best_posting_times": best_posting_times,
        "duration": duration,
    }


@app.get("/api/library", tags=["Biblioteca de Clips"])
def get_clip_library():
    """
    Devuelve la biblioteca completa de clips generados en formato 9:16.
    Lista todos los archivos .mp4 del directorio de salida con metadatos enriquecidos.
    """
    clips = []
    if OUTPUT_DIR.exists():
        mp4_files = sorted(
            [f for f in OUTPUT_DIR.iterdir() if f.is_file() and f.suffix == ".mp4"],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        for fp in mp4_files:
            try:
                clips.append(_enrich_clip_metadata(fp.name, fp))
            except Exception as e:
                logger.warning(f"[Library] Error leyendo {fp.name}: {e}")

    return {
        "clips": clips,
        "total": len(clips),
        "output_dir": str(OUTPUT_DIR),
    }


@app.delete("/api/library/{filename}", tags=["Biblioteca de Clips"])
def delete_clip(filename: str):
    """Elimina un clip del disco y su archivo de metadatos si existe."""
    import re
    if not re.match(r'^[\w\-. ]+\.mp4$', filename):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")

    fp = OUTPUT_DIR / filename
    if not fp.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Clip '{filename}' no encontrado.")

    fp.unlink()
    # Limpiar metadata y thumbnail asociados si existen
    stem = fp.stem
    for extra in [
        OUTPUT_DIR / "metadata" / f"{stem}.json",
        OUTPUT_DIR / f"{stem}_meta.json",
        OUTPUT_DIR / "thumbnails" / f"{stem}.jpg",
    ]:
        if extra.exists():
            extra.unlink()

    return {"deleted": filename, "status": "ok"}


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

