"""
Módulo de Ingesta y Transcripción
- Descarga video de YouTube con yt-dlp o sube video local
- Extrae audio en formato WAV 16kHz
- Transcribe con Whisper (soporte para tiny, base, small, medium)
- Persistencia robusta en disco (sobrevive a reinicios del servidor)
"""
import os
import re
import json
import logging
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

import yt_dlp
import whisper

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger("clipai.ingest")

router = APIRouter()

DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "downloads"))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# In-memory models cache
_whisper_models: dict[str, whisper.Whisper] = {}


def get_whisper_model(model_name: str = "base"):
    """Load or retrieve cached Whisper model."""
    global _whisper_models
    model_name = model_name.strip().lower()
    if model_name not in _whisper_models:
        logger.info(f"Cargando modelo Whisper '{model_name}'...")
        _whisper_models[model_name] = whisper.load_model(model_name)
        logger.info(f"Modelo Whisper '{model_name}' cargado con éxito.")
    return _whisper_models[model_name]


class IngestRequest(BaseModel):
    youtube_url: str
    language: Optional[str] = None  # None = auto-detect
    whisper_model: Optional[str] = None


class IngestStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    video_path: Optional[str] = None
    video_title: Optional[str] = None
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    audio_path: Optional[str] = None
    transcript: Optional[dict] = None
    error: Optional[str] = None


# In-memory jobs dict
jobs: dict[str, dict] = {}


def sanitize_filename(name: str) -> str:
    """Remove problematic characters from filenames."""
    clean = re.sub(r'[^\w\s\.-]', '_', name, flags=re.UNICODE)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:80] if clean else "video"


def save_job(job_id: str):
    """Persist job state to disk in downloads/{job_id}/job.json."""
    if job_id not in jobs:
        return
    job_dir = DOWNLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    job_file = job_dir / "job.json"
    try:
        # Don't dump huge transcript in job.json if saved separately
        data = dict(jobs[job_id])
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"No se pudo guardar job.json para {job_id}: {e}")


def get_job(job_id: str) -> Optional[dict]:
    """Retrieve job from memory or recover from disk."""
    if not job_id:
        return None

    if job_id in jobs:
        return jobs[job_id]

    job_dir = DOWNLOADS_DIR / job_id
    if not job_dir.exists():
        return None

    job_file = job_dir / "job.json"
    job_data = None
    if job_file.exists():
        try:
            with open(job_file, "r", encoding="utf-8") as f:
                job_data = json.load(f)
        except Exception as e:
            logger.warning(f"Error leyendo {job_file}: {e}")

    if not job_data:
        # Auto-reconstruct from directory contents
        mp4s = list(job_dir.glob("*.mp4"))
        wavs = list(job_dir.glob("*.wav"))
        v_path = str(mp4s[0]) if mp4s else None
        a_path = str(wavs[0]) if wavs else None
        t_path = job_dir / "transcript.json"

        transcript = None
        if t_path.exists():
            try:
                with open(t_path, "r", encoding="utf-8") as f:
                    transcript = json.load(f)
            except Exception:
                pass

        job_data = {
            "job_id": job_id,
            "url": "",
            "language": None,
            "status": "done" if transcript else ("downloaded" if v_path else "unknown"),
            "progress": 100 if transcript else 50,
            "message": "Trabajo recuperado de disco",
            "video_path": v_path,
            "video_title": Path(v_path).stem if v_path else "Video",
            "duration": 0.0,
            "thumbnail": "",
            "audio_path": a_path,
            "transcript": transcript,
            "error": None,
        }

    # If transcript in separate file but not loaded
    if not job_data.get("transcript"):
        t_file = job_dir / "transcript.json"
        if t_file.exists():
            try:
                with open(t_file, "r", encoding="utf-8") as f:
                    job_data["transcript"] = json.load(f)
            except Exception:
                pass

    jobs[job_id] = job_data
    return job_data


def clean_youtube_url(url: str) -> str:
    """Clean and standardize YouTube URLs to ensure yt-dlp compatibility."""
    if not url:
        return ""
    url = url.strip()
    # Handle Shorts: https://www.youtube.com/shorts/ID
    m_shorts = re.search(r'youtube\.com/shorts/([a-zA-Z0-9_-]+)', url)
    if m_shorts:
        return f"https://www.youtube.com/watch?v={m_shorts.group(1)}"
    # Handle youtu.be/ID
    m_short = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
    if m_short:
        return f"https://www.youtube.com/watch?v={m_short.group(1)}"
    # Handle standard watch?v=ID stripping tracking parameters
    m_watch = re.search(r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)', url)
    if m_watch:
        return f"https://www.youtube.com/watch?v={m_watch.group(1)}"
    return url


def download_video(job_id: str, url: str, model_name: str = "base"):
    """Download YouTube video, extract audio, and transcribe."""
    job = jobs[job_id]
    job["status"] = "downloading"
    job["progress"] = 10
    job["message"] = "Conectando con YouTube y descargando video..."
    save_job(job_id)

    out_dir = DOWNLOADS_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    clean_url = clean_youtube_url(url)

    # Use a clean, safe output template
    out_template = str(out_dir / "source.%(ext)s")

    # Check for optional cookies.txt file
    cookie_file = None
    for cf in [Path("cookies.txt"), DOWNLOADS_DIR / "cookies.txt", Path(__file__).resolve().parent.parent.parent / "cookies.txt"]:
        if cf.exists():
            cookie_file = str(cf.resolve())
            break

    ydl_opts = {
        "outtmpl": out_template,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "writeinfojson": True,
        "nocheckcertificate": True,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "web"],
                "player_skip": ["configs", "webpage"],
            }
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 14; US) gzip",
            "Accept-Language": "en-US,en;q=0.9",
        }
    }
    if cookie_file:
        ydl_opts["cookiefile"] = cookie_file

    info = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
    except Exception as e_first:
        logger.warning(f"Primer intento de descarga con yt-dlp falló: {e_first}. Intentando con formato alternativo...")
        fallback_opts = dict(ydl_opts)
        fallback_opts["format"] = "18/22/best[ext=mp4]/best"
        fallback_opts["extractor_args"] = {"youtube": {"player_client": ["android", "ios"]}}
        try:
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
        except Exception as e_second:
            job["status"] = "error"
            job["error"] = f"Error al descargar video de YouTube: {str(e_second)}"
            job["message"] = f"Fallo al descargar video: {str(e_second)}"
            logger.error(f"Download error for job {job_id}: {e_second}")
            save_job(job_id)
            return

    try:
        raw_title = info.get("title", "Video") if info else "Video"
        clean_title = sanitize_filename(raw_title)
        duration = float(info.get("duration", 0)) if info else 0.0

        mp4_files = list(out_dir.glob("*.mp4"))
        if not mp4_files:
            raise FileNotFoundError("No se encontró el archivo MP4 descargado.")

        video_path = str(mp4_files[0])
        job["video_path"] = video_path
        job["video_title"] = clean_title
        job["duration"] = duration
        job["thumbnail"] = info.get("thumbnail", "") if info else ""
        job["progress"] = 35
        job["message"] = f"Video descargado: {clean_title}"
        logger.info(f"Video descargado: {video_path}")
        save_job(job_id)

    except Exception as e:
        job["status"] = "error"
        job["error"] = f"Error al procesar video descargado: {str(e)}"
        job["message"] = f"Fallo al procesar archivo: {str(e)}"
        logger.error(f"Post-download error for job {job_id}: {e}")
        save_job(job_id)
        return

    # Extract audio as WAV for Whisper
    extract_audio_and_transcribe(job_id, video_path, model_name)


def extract_audio_and_transcribe(job_id: str, video_path: str, model_name: str = "base"):
    """Extract audio from video file and run Whisper transcription."""
    job = jobs[job_id]
    job["progress"] = 40
    job["message"] = "Extrayendo audio a 16kHz WAV..."
    save_job(job_id)

    out_dir = Path(video_path).parent
    audio_path = str(out_dir / "audio.wav")

    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ar", "16000", "-ac", "1", "-vn",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction error: {result.stderr}")

        job["audio_path"] = audio_path
        job["progress"] = 50
        job["message"] = "Audio extraído con éxito. Iniciando transcripción Whisper..."
        save_job(job_id)
        logger.info(f"Audio extraído: {audio_path}")
    except Exception as e:
        job["status"] = "error"
        job["error"] = f"Error extrayendo audio: {str(e)}"
        job["message"] = f"Fallo en extracción de audio: {str(e)}"
        logger.error(f"Audio extraction error for job {job_id}: {e}")
        save_job(job_id)
        return

    # Transcribe with Whisper
    transcribe_video(job_id, audio_path, job.get("language"), model_name)


def transcribe_video(job_id: str, audio_path: str, language: Optional[str] = None, model_name: str = "base"):
    """Transcribe audio with Whisper and save results."""
    job = jobs[job_id]
    job["status"] = "transcribing"
    job["progress"] = 55
    job["message"] = f"Transcribiendo con Whisper ({model_name})... Esto puede tardar unos momentos."
    save_job(job_id)

    try:
        model = get_whisper_model(model_name)
        transcribe_opts = {"word_timestamps": True, "verbose": False}
        if language:
            transcribe_opts["language"] = language

        job["progress"] = 70
        job["message"] = "Procesando audio y reconociendo palabras..."
        save_job(job_id)

        result = model.transcribe(audio_path, **transcribe_opts)

        # Build clean transcript with timestamps
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "id": seg.get("id", 0),
                "start": round(float(seg.get("start", 0)), 2),
                "end": round(float(seg.get("end", 0)), 2),
                "text": seg.get("text", "").strip(),
                "words": seg.get("words", []),
            })

        transcript = {
            "language": result.get("language", "unknown"),
            "full_text": result.get("text", "").strip(),
            "segments": segments,
        }

        # Save transcript JSON
        out_dir = Path(audio_path).parent
        transcript_path = str(out_dir / "transcript.json")
        with open(transcript_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

        job["transcript"] = transcript
        job["transcript_path"] = transcript_path
        job["status"] = "done"
        job["progress"] = 100
        job["message"] = f"✅ Transcripción completada exitosamente ({len(segments)} segmentos)."
        save_job(job_id)
        logger.info(f"Transcripción completada para job {job_id}")

    except Exception as e:
        job["status"] = "error"
        job["error"] = f"Error en transcripción: {str(e)}"
        job["message"] = f"Fallo en Whisper: {str(e)}"
        save_job(job_id)
        logger.error(f"Transcription error for job {job_id}: {e}")


# -------------------------
# API Routes
# -------------------------

@router.post("/start", response_model=IngestStatus)
async def start_ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    """Start video download + transcription pipeline."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    chosen_model = req.whisper_model or DEFAULT_WHISPER_MODEL

    jobs[job_id] = {
        "job_id": job_id,
        "url": req.youtube_url,
        "language": req.language,
        "whisper_model": chosen_model,
        "status": "queued",
        "progress": 5,
        "message": "En cola de descarga...",
        "video_path": None,
        "video_title": None,
        "duration": None,
        "thumbnail": None,
        "audio_path": None,
        "transcript": None,
        "error": None,
    }
    save_job(job_id)

    background_tasks.add_task(
        download_video,
        job_id,
        req.youtube_url,
        chosen_model,
    )

    return IngestStatus(**jobs[job_id])


@router.post("/upload")
async def upload_local_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    whisper_model: str = Form("base"),
    language: Optional[str] = Form(None),
):
    """Upload a local video file (MP4/MOV) and transcribe directly."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    job_dir = DOWNLOADS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    dest_path = job_dir / "source.mp4"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    clean_title = sanitize_filename(Path(file.filename).stem)

    jobs[job_id] = {
        "job_id": job_id,
        "url": f"local://{file.filename}",
        "language": language if language != "auto" else None,
        "whisper_model": whisper_model,
        "status": "queued",
        "progress": 35,
        "message": f"Archivo local cargado: {file.filename}",
        "video_path": str(dest_path),
        "video_title": clean_title,
        "duration": 0.0,
        "thumbnail": "",
        "audio_path": None,
        "transcript": None,
        "error": None,
    }
    save_job(job_id)

    background_tasks.add_task(
        extract_audio_and_transcribe,
        job_id,
        str(dest_path),
        whisper_model,
    )

    return IngestStatus(**jobs[job_id])


@router.post("/retranscribe/{job_id}", response_model=IngestStatus)
async def retranscribe(job_id: str, background_tasks: BackgroundTasks, model_name: str = "base"):
    """Retrigger transcription for an existing downloaded job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado en disco ni en memoria")

    video_path = job.get("video_path")
    if not video_path or not Path(video_path).exists():
        job_dir = DOWNLOADS_DIR / job_id
        mp4s = list(job_dir.glob("*.mp4"))
        if mp4s:
            video_path = str(mp4s[0])
            job["video_path"] = video_path
        else:
            raise HTTPException(status_code=400, detail="No se encontró archivo de video para este job")

    job["status"] = "queued"
    job["progress"] = 35
    job["message"] = f"Reiniciando transcripción con Whisper ({model_name})..."
    job["error"] = None
    save_job(job_id)

    background_tasks.add_task(
        extract_audio_and_transcribe,
        job_id,
        video_path,
        model_name,
    )

    return IngestStatus(**job)


@router.get("/status/{job_id}", response_model=IngestStatus)
async def get_status(job_id: str):
    """Get status of an ingest job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return IngestStatus(**job)


@router.get("/jobs")
async def list_jobs():
    """List all available jobs from memory and disk."""
    found_jobs = {}

    # Scan disk
    for job_dir in sorted(DOWNLOADS_DIR.iterdir(), key=os.path.getmtime, reverse=True):
        if job_dir.is_dir():
            jid = job_dir.name
            j_data = get_job(jid)
            if j_data:
                found_jobs[jid] = j_data

    # Merge with memory
    for jid, j_data in jobs.items():
        found_jobs[jid] = j_data

    # Clean output (omit heavy transcript from listing)
    return [
        {k: v for k, v in j.items() if k != "transcript"}
        for j in found_jobs.values()
    ]
