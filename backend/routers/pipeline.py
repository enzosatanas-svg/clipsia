"""
Módulo de Pipeline Automatizado en 1-Clic (End-to-End)
Permite al usuario ingresar una URL de YouTube y presionar un solo botón para:
 1. Descargar el video de YouTube de forma robusta con yt-dlp (sin bloqueos de bot).
 2. Extraer audio y transcribir silenciosamente en segundo plano con Whisper (sin mostrar bloques gigantes de texto).
 3. Analizar heurísticamente con IA los mejores ganchos y momentos virales (30-50s).
 4. Renderizar automáticamente cada clip a formato vertical 9:16 con subtítulos Alex Hormozi o TikTok.
 5. Devolver directamente la lista y galería de clips virales listos para previsualizar y descargar.
"""
import os
import json
import uuid
import logging
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.routers import ingest, process, clips

logger = logging.getLogger("clipai.pipeline")
router = APIRouter()

PIPELINE_DIR = Path("output/pipeline")
PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

pipeline_jobs: dict[str, dict] = {}


class OneClickRequest(BaseModel):
    youtube_url: str
    max_clips: int = 3
    whisper_model: str = "base"
    aspect_ratio: str = "9:16"
    layout: str = "autoframing"
    subtitle_style: str = "alex_hormozi"
    burn_subtitles: bool = True


class RenderedClipItem(BaseModel):
    clip_id: str
    title: str
    hook: str
    hashtags: list[str]
    viral_score: float
    duration: float
    video_url: str
    video_path: str
    thumbnail_url: Optional[str] = None
    file_size_mb: Optional[float] = 0.0
    ai_copy: Optional[str] = ""


class PipelineStatus(BaseModel):
    pipeline_id: str
    status: str  # "queued", "downloading", "transcribing", "detecting", "rendering", "completed", "error"
    progress: int
    message: str
    video_title: Optional[str] = None
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    clips: List[RenderedClipItem] = []
    error: Optional[str] = None


def save_pipeline_job(pipeline_id: str):
    """Guarda el estado del pipeline en disco para que persista."""
    if pipeline_id not in pipeline_jobs:
        return
    job_file = PIPELINE_DIR / f"{pipeline_id}.json"
    try:
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(pipeline_jobs[pipeline_id], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error guardando pipeline {pipeline_id}: {e}")


def get_pipeline_job(pipeline_id: str) -> Optional[dict]:
    """Recupera el pipeline de memoria o disco."""
    if pipeline_id in pipeline_jobs:
        return pipeline_jobs[pipeline_id]
    job_file = PIPELINE_DIR / f"{pipeline_id}.json"
    if job_file.exists():
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                pipeline_jobs[pipeline_id] = data
                return data
        except Exception:
            pass
    return None


def run_one_click_worker(pipeline_id: str, req: OneClickRequest):
    """Ejecutor integral de todas las fases del pipeline."""
    p_job = pipeline_jobs[pipeline_id]
    url = req.youtube_url.strip()

    try:
        # -------------------------------------------------------------
        # FASE 1: Descarga con yt-dlp
        # -------------------------------------------------------------
        p_job["status"] = "downloading"
        p_job["progress"] = 15
        p_job["message"] = "📥 Conectando con YouTube y descargando video original en alta calidad..."
        save_pipeline_job(pipeline_id)

        # Inicializar el job en el router de ingesta
        ingest.jobs[pipeline_id] = {
            "job_id": pipeline_id,
            "url": url,
            "language": None,
            "whisper_model": req.whisper_model,
            "status": "queued",
            "progress": 10,
            "message": "Iniciando descarga...",
            "video_path": None,
            "video_title": None,
            "duration": None,
            "thumbnail": None,
            "audio_path": None,
            "transcript": None,
            "error": None,
        }
        ingest.save_job(pipeline_id)

        # Ejecutar descarga de YouTube o procesamiento de video local
        if Path(url).exists():
            p_job["message"] = f"📁 Procesando archivo local: {Path(url).name}..."
            save_pipeline_job(pipeline_id)
            clean_title = ingest.sanitize_filename(Path(url).stem)
            ingest.jobs[pipeline_id]["video_path"] = str(Path(url).resolve())
            ingest.jobs[pipeline_id]["video_title"] = clean_title
            ingest.jobs[pipeline_id]["status"] = "downloaded"
            ingest.save_job(pipeline_id)
            ingest.extract_audio_and_transcribe(pipeline_id, str(Path(url).resolve()), req.whisper_model)
        else:
            p_job["message"] = "📥 Descargando video de YouTube..."
            save_pipeline_job(pipeline_id)
            ingest.download_video(pipeline_id, url, req.whisper_model)

        ing_job = ingest.get_job(pipeline_id)
        if not ing_job or ing_job.get("status") == "error":
            err = ing_job.get("error") if ing_job else "Error desconocido durante la descarga."
            p_job["status"] = "error"
            p_job["error"] = err
            p_job["message"] = f"❌ Error: {err}"
            save_pipeline_job(pipeline_id)
            return

        p_job["video_title"] = ing_job.get("video_title", "Video")
        p_job["duration"] = ing_job.get("duration", 0.0)
        p_job["thumbnail"] = ing_job.get("thumbnail", "")

        # -------------------------------------------------------------
        # FASE 2: Transcripción Whisper Interna y Silenciosa
        # (Ya ejecutada de fondo dentro de ingest.download_video)
        # -------------------------------------------------------------
        p_job["status"] = "transcribing"
        p_job["progress"] = 55
        p_job["message"] = "🎙️ Procesamiento de audio y diálogo completado silenciosamente."
        save_pipeline_job(pipeline_id)

        transcript = ing_job.get("transcript")
        if not transcript or not transcript.get("segments"):
            p_job["status"] = "error"
            p_job["error"] = "No se detectaron segmentos de audio inteligibles en el video."
            p_job["message"] = "❌ No se detectó diálogo para generar clips."
            save_pipeline_job(pipeline_id)
            return

        # -------------------------------------------------------------
        # FASE 3, 4 y 5: Orquestación Supervisada por Lead System Agent
        # -------------------------------------------------------------
        p_job["status"] = "detecting"
        p_job["progress"] = 65
        p_job["message"] = "👑 Lead System Agent supervisando agentes: Corte, Subtitulado, 9:16 y SEO..."
        save_pipeline_job(pipeline_id)

        from backend.agents.orchestrator import LeadOrchestratorAgent

        orchestrator = LeadOrchestratorAgent(output_dir=clips.OUTPUT_DIR)
        report = orchestrator.orchestrate_pipeline(
            job_id=pipeline_id,
            source_video_path=ing_job["video_path"],
            transcript_data=transcript,
            max_clips=req.max_clips,
            framing_layout=req.layout,
        )

        rendered_items = []
        for c in report.get("clips", []):
            item = RenderedClipItem(
                clip_id=c["clip_id"],
                title=c["marketing_seo"]["recommended_hook"],
                hook=c["marketing_seo"]["recommended_hook"],
                hashtags=c["marketing_seo"]["hashtags"],
                viral_score=c["viral_score"],
                duration=c["timing"]["duration_seconds"],
                video_url=c["video_technical"]["video_url"],
                video_path=c["video_technical"]["video_path"],
                thumbnail_url=f"/output/thumbnails/{c['clip_id']}.jpg",
                file_size_mb=c["video_technical"]["file_size_mb"],
                ai_copy=c["marketing_seo"]["ready_to_publish_copy"],
            )
            rendered_items.append(item)

        p_job["status"] = "completed"
        p_job["progress"] = 100
        p_job["clips"] = [it.dict() for it in rendered_items]
        p_job["orchestrator_report"] = report
        p_job["message"] = f"🎉 ¡{len(rendered_items)} clips virales generados y aprobados por el Lead System Agent (100% en español)!"
        save_pipeline_job(pipeline_id)

    except Exception as e:
        logger.exception(f"Error en worker del pipeline {pipeline_id}: {e}")
        p_job["status"] = "error"
        p_job["error"] = str(e)
        p_job["message"] = f"❌ Fallo inesperado: {str(e)}"
        save_pipeline_job(pipeline_id)


# -------------------------------------------------------------
# Endpoints de la API
# -------------------------------------------------------------

@router.post("/generate", response_model=PipelineStatus)
async def generate_viral_clips(req: OneClickRequest, background_tasks: BackgroundTasks):
    """Inicia el pipeline completo de generación de clips virales en 1 solo clic."""
    url = req.youtube_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Debes proporcionar una URL de YouTube.")

    pipeline_id = str(uuid.uuid4())[:8]

    p_status = {
        "pipeline_id": pipeline_id,
        "status": "queued",
        "progress": 5,
        "message": "Iniciando proceso autónomo de clips virales...",
        "video_title": None,
        "duration": None,
        "thumbnail": None,
        "clips": [],
        "error": None,
    }
    pipeline_jobs[pipeline_id] = p_status
    save_pipeline_job(pipeline_id)

    background_tasks.add_task(run_one_click_worker, pipeline_id, req)

    return PipelineStatus(**p_status)


@router.get("/status/{pipeline_id}", response_model=PipelineStatus)
async def get_pipeline_status(pipeline_id: str):
    """Consulta el estado en vivo del pipeline y los clips generados."""
    p_job = get_pipeline_job(pipeline_id)
    if not p_job:
        raise HTTPException(status_code=404, detail="Pipeline ID no encontrado")
    return PipelineStatus(**p_job)


@router.get("/history")
async def list_pipeline_history():
    """Lista todos los pipelines generados recientemente."""
    items = []
    for f in sorted(PIPELINE_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as jf:
                items.append(json.load(jf))
        except Exception:
            pass
    return items
