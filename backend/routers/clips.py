"""
Módulo de Edición, Renderizado y Biblioteca de Clips
- Recorta fragmentos virales con timestamps precisos
- Reencuadra a formato vertical 9:16 (Shorts/TikTok/Reels) con fondo desenfocado inteligente o recorte
- Genera y quema subtítulos animados estilo TikTok con timestamps ASS
- Genera miniaturas optimizadas
- Persistencia de trabajos de renderizado y administración completa de la biblioteca de clips
"""
import os
import re
import json
import logging
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend.routers.ingest import get_job, DOWNLOADS_DIR
from backend.autoframing import analyze_speaker_framing
from backend.subtitles import generate_ass_subtitles_file

logger = logging.getLogger("clipai.clips")

router = APIRouter()

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
THUMBNAILS_DIR = OUTPUT_DIR / "thumbnails"
METADATA_DIR = OUTPUT_DIR / "metadata"
RENDERS_DIR = OUTPUT_DIR / "renders"

for p in [OUTPUT_DIR, DOWNLOADS_DIR, THUMBNAILS_DIR, METADATA_DIR, RENDERS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# In-memory render job status
render_jobs: dict[str, dict] = {}


def generate_ai_copy(title: Optional[str], hook: Optional[str] = "", hashtags: Optional[list[str]] = None, text: str = "") -> str:
    """Genera un Copy de alto impacto listo para TikTok, Instagram Reels y YouTube Shorts."""
    tags = hashtags or ["#shorts", "#viral", "#reels", "#tiktok", "#clipai"]
    clean_tags = " ".join(t if t.startswith("#") else f"#{t}" for t in tags)
    clean_title = (title or "Momento viral revelado").strip()
    clean_hook = (hook or "").strip()

    body = clean_hook if clean_hook else (text[:120].strip() if text else "El secreto que nadie te cuenta sobre este tema.")

    copy = (
        f"🔥 {clean_title}\n\n"
        f"👀 {body}...\n\n"
        f"👇 ¿Tú qué opinas al respecto? ¡Déjalo abajo en los comentarios y sígueme para más contenido diario!\n\n"
        f"{clean_tags}"
    )
    return copy


# -------------------------
# Models
# -------------------------

class RenderClipRequest(BaseModel):
    job_id: str
    clip_id: str
    start: Optional[float] = None
    end: Optional[float] = None
    aspect_ratio: str = "9:16"             # "9:16", "1:1", "16:9"
    layout: str = "autoframing"            # "autoframing", "blur_bg", "crop", "fit"
    burn_subtitles: bool = True
    subtitle_style: str = "alex_hormozi"   # "alex_hormozi", "alex_hormozi_green", "tiktok_yellow", "clean_white", "neon_cyan", "karaoke_box"
    title: Optional[str] = None
    hook: Optional[str] = None
    hashtags: Optional[list[str]] = None
    viral_score: Optional[float] = None


class RenderStatus(BaseModel):
    render_id: str
    clip_id: str
    status: str
    progress: int
    message: str
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


# -------------------------
# Helper Functions
# -------------------------

def save_render_status(render_id: str):
    """Save render job state to disk in output/renders/{render_id}.json."""
    if render_id not in render_jobs:
        return
    r_file = RENDERS_DIR / f"{render_id}.json"
    try:
        with open(r_file, "w", encoding="utf-8") as f:
            json.dump(render_jobs[render_id], f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error guardando estado de render {render_id}: {e}")


def get_render_job(render_id: str) -> Optional[dict]:
    """Retrieve render job from memory or disk."""
    if render_id in render_jobs:
        return render_jobs[render_id]
    r_file = RENDERS_DIR / f"{render_id}.json"
    if r_file.exists():
        try:
            with open(r_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                render_jobs[render_id] = data
                return data
        except Exception:
            pass
    return None


def probe_has_audio(video_path: str) -> bool:
    """Check if the video has an audio stream."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(video_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return "audio" in res.stdout.lower()
    except Exception:
        return True  # Assume true if check fails


def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cs ensuring non-negative values."""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def clean_subtitle_text(text: str) -> str:
    """Clean text for ASS subtitles avoiding syntax breaks."""
    text = re.sub(r'[\{\}\\]', '', text)
    text = text.replace('"', "''").strip()
    return text.upper()


def generate_ass_subtitles(
    transcript: dict,
    start_sec: float,
    end_sec: float,
    out_path: Path,
    style_name: str = "tiktok_yellow",
):
    """
    Generate an ASS subtitle file formatted for vertical 9:16 viral videos.
    Uses standard Windows fonts (Arial, Impact, Segoe UI) with strong outline and drop shadow.
    """
    style_defs = {
        "tiktok_yellow": (
            "Style: TikTok,Arial,66,&H0000FFFF,&H000000FF,&H00000000,&H80000000,"
            "-1,0,0,0,100,100,2,0,1,5,3,2,60,60,380,1"
        ),
        "clean_white": (
            "Style: TikTok,Segoe UI,62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            "-1,0,0,0,100,100,2,0,1,4,2,2,60,60,380,1"
        ),
        "neon_cyan": (
            "Style: TikTok,Impact,70,&H00FFFF00,&H000000FF,&H00000000,&H80000000,"
            "-1,0,0,0,100,100,3,0,1,5,3,2,60,60,380,1"
        ),
        "karaoke_box": (
            "Style: TikTok,Arial,64,&H0000FFFF,&H00FFFFFF,&H00000000,&HCC000000,"
            "-1,0,0,0,100,100,1,0,3,4,0,2,60,60,380,1"
        ),
    }

    style_line = style_defs.get(style_name, style_defs["tiktok_yellow"])

    header = f"""[Script Info]
Title: Viral Clip Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    segments = transcript.get("segments", [])

    for seg in segments:
        s_start = float(seg.get("start", 0))
        s_end = float(seg.get("end", 0))

        if s_end <= start_sec or s_start >= end_sec:
            continue

        words = seg.get("words", [])
        if words and len(words) > 0:
            chunk_size = 4
            word_list = [w for w in words if float(w.get("end", 0)) > start_sec and float(w.get("start", 0)) < end_sec]
            for i in range(0, len(word_list), chunk_size):
                chunk = word_list[i:i + chunk_size]
                if not chunk:
                    continue
                w_start = max(0.0, float(chunk[0].get("start", 0)) - start_sec)
                w_end = min(end_sec - start_sec, float(chunk[-1].get("end", 0)) - start_sec)
                if w_end <= w_start:
                    w_end = w_start + 0.8
                chunk_text = clean_subtitle_text(" ".join(w.get("word", "") for w in chunk))
                if chunk_text and (w_end - w_start) >= 0.1:
                    events.append(
                        f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},TikTok,,0,0,0,,{chunk_text}"
                    )
        else:
            rel_start = max(0.0, s_start - start_sec)
            rel_end = min(end_sec - start_sec, s_end - start_sec)
            seg_text = clean_subtitle_text(seg.get("text", ""))
            if (rel_end - rel_start) > 0.2 and seg_text:
                events.append(
                    f"Dialogue: 0,{format_ass_time(rel_start)},{format_ass_time(rel_end)},TikTok,,0,0,0,,{seg_text}"
                )

    ass_content = header + "\n".join(events) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(ass_content)


# -------------------------
# Video Rendering Worker
# -------------------------

def execute_render(render_id: str, req: RenderClipRequest):
    """Render the video clip with vertical reframing, subtitles, and audio."""
    render_job = render_jobs[render_id]
    # Clean clip_id
    raw_clip_id = req.clip_id or f"{req.job_id}_clip"
    clip_id = re.sub(r'[^\w\-]', '_', raw_clip_id)

    try:
        render_job["status"] = "processing"
        render_job["progress"] = 10
        render_job["message"] = "Localizando video original..."
        save_render_status(render_id)

        # 1. Locate source video
        job_data = get_job(req.job_id) or {}
        video_path = job_data.get("video_path")

        if not video_path or not Path(video_path).exists():
            job_dir = DOWNLOADS_DIR / req.job_id
            mp4s = list(job_dir.glob("*.mp4")) if job_dir.exists() else []
            if mp4s:
                video_path = str(mp4s[0])
            else:
                # Search all downloads for any mp4 with job_id in name
                candidates = list(DOWNLOADS_DIR.glob(f"**/*{req.job_id}*/*.mp4")) + list(DOWNLOADS_DIR.glob("*.mp4"))
                if candidates:
                    video_path = str(candidates[0])
                else:
                    raise FileNotFoundError(f"No se encontró el archivo de video para el job '{req.job_id}'.")

        # 2. Load transcript
        transcript = job_data.get("transcript")
        if not transcript:
            t_path = DOWNLOADS_DIR / req.job_id / "transcript.json"
            if t_path.exists():
                with open(t_path, "r", encoding="utf-8") as f:
                    transcript = json.load(f)
            else:
                transcript = {"segments": []}

        # 3. Determine start and end times
        start_time = req.start
        end_time = req.end
        if start_time is None or end_time is None:
            v_clips = job_data.get("viral_clips", [])
            for c in v_clips:
                if c.get("clip_id") == clip_id or c.get("clip_id") == req.clip_id:
                    start_time = float(c.get("start", 0.0))
                    end_time = float(c.get("end", start_time + 40.0))
                    if not req.title:
                        req.title = c.get("title")
                    if not req.hook:
                        req.hook = c.get("hook")
                    if not req.hashtags:
                        req.hashtags = c.get("hashtags")
                    if req.viral_score is None:
                        req.viral_score = c.get("viral_score", 8.0)
                    break

        if start_time is None:
            start_time = 0.0
        if end_time is None or end_time <= start_time:
            end_time = start_time + 40.0

        duration = max(1.0, round(end_time - start_time, 2))

        # Check audio stream presence
        has_audio = probe_has_audio(video_path)

        # 4. Generate subtitles if requested
        subtitles_file = None
        if req.burn_subtitles and transcript.get("segments"):
            render_job["progress"] = 25
            render_job["message"] = f"Generando subtítulos estilo {req.subtitle_style}..."
            save_render_status(render_id)
            subtitles_file = OUTPUT_DIR / f"{clip_id}_temp.ass"
            try:
                generate_ass_subtitles_file(
                    transcript=transcript,
                    start_sec=start_time,
                    end_sec=end_time,
                    out_path=subtitles_file,
                    style_name=req.subtitle_style,
                )
                logger.info(f"Subtítulos generados exitosamente: {subtitles_file}")
            except Exception as e:
                logger.warning(f"Error generando subtítulos ASS: {e}. Continuando sin subtítulos.")
                subtitles_file = None

        # 5. Build FFmpeg command with MediaPipe Auto-Framing
        render_job["progress"] = 40
        render_job["message"] = "Renderizando video vertical 9:16..."
        save_render_status(render_id)
        output_video_path = OUTPUT_DIR / f"{clip_id}.mp4"

        # Aspect ratio & layout filter setup
        if req.aspect_ratio == "9:16":
            if req.layout == "autoframing":
                render_job["message"] = "MediaPipe: Seguimiento facial (Auto-Framing 9:16)..."
                save_render_status(render_id)
                try:
                    framing_info = analyze_speaker_framing(
                        video_path=video_path,
                        start_sec=start_time,
                        end_sec=end_time,
                        target_w=1080,
                        target_h=1920,
                    )
                    video_filter = framing_info.get("video_filter") or "scale=-2:1920,crop=1080:1920[composed]"
                    logger.info(f"Auto-Framing MediaPipe aplicado ({framing_info.get('faces_detected', 0)} caras detectadas)")
                except Exception as ef:
                    logger.warning(f"Error en Auto-Framing MediaPipe: {ef}. Fallback a recorte centrado.")
                    video_filter = "scale=-2:1920,crop=1080:1920[composed]"
            elif req.layout == "crop":
                video_filter = "scale=-2:1920,crop=1080:1920[composed]"
            elif req.layout == "fit":
                video_filter = "scale=1080:-2,pad=1080:1920:(1080-iw)/2:(1920-ih)/2:black[composed]"
            else:
                # Default / blur_bg: Professional Blurred Background
                video_filter = (
                    "[0:v]split=2[in_bg][in_fg];"
                    "[in_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
                    "[in_fg]scale=1080:-2[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2[composed]"
                )
        elif req.aspect_ratio == "1:1":
            video_filter = "[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080[composed]"
        else:  # 16:9
            video_filter = "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(1920-iw)/2:(1080-ih)/2:black[composed]"

        # Add subtitle filter if available
        has_subtitles = False
        if subtitles_file and subtitles_file.exists():
            ass_escaped = str(subtitles_file.resolve()).replace("\\", "/").replace(":", "\\:")
            video_filter += f";[composed]subtitles='{ass_escaped}'[v]"
            output_map = "[v]"
            has_subtitles = True
        else:
            output_map = "[composed]"

        render_job["progress"] = 55
        render_job["message"] = "Codificando MP4 de alta fidelidad con FFmpeg..."
        save_render_status(render_id)

        # Accurate seek + exact duration
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", str(video_path),
            "-t", str(duration),
            "-filter_complex", video_filter,
            "-map", output_map,
        ]

        if has_audio:
            cmd.extend(["-map", "0:a?", "-c:a", "aac", "-b:a", "192k"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-movflags", "+faststart",
            str(output_video_path),
        ])

        logger.info(f"Ejecutando FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning(f"FFmpeg con filtros falló: {result.stderr}. Reintentando sin subtítulos...")
            # Fallback attempt without subtitles filter
            vf_fallback = (
                "[0:v]split=2[in_bg][in_fg];"
                "[in_bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
                "[in_fg]scale=1080:-2[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[composed]"
            ) if req.aspect_ratio == "9:16" else "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[composed]"

            cmd_fallback = [
                "ffmpeg", "-y",
                "-ss", str(start_time),
                "-i", str(video_path),
                "-t", str(duration),
                "-filter_complex", vf_fallback,
                "-map", "[composed]",
            ]
            if has_audio:
                cmd_fallback.extend(["-map", "0:a?", "-c:a", "aac", "-b:a", "128k"])
            cmd_fallback.extend([
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "24",
                "-movflags", "+faststart",
                str(output_video_path),
            ])

            fb_res = subprocess.run(cmd_fallback, capture_output=True, text=True)
            if fb_res.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {fb_res.stderr[-300:]}")

        # Clean up temporary ASS file
        if subtitles_file and subtitles_file.exists():
            try:
                subtitles_file.unlink()
            except Exception:
                pass

        # 6. Generate thumbnail
        render_job["progress"] = 85
        render_job["message"] = "Generando miniatura..."
        save_render_status(render_id)
        thumb_path = THUMBNAILS_DIR / f"{clip_id}.jpg"
        thumb_seek = str(min(1.0, duration / 2.0))
        thumb_cmd = [
            "ffmpeg", "-y",
            "-ss", thumb_seek,
            "-i", str(output_video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(thumb_path),
        ]
        subprocess.run(thumb_cmd, capture_output=True)

        # 7. Calculate file size & generate AI Copy & save metadata
        file_size_mb = 0.0
        if output_video_path.exists():
            file_size_mb = round(output_video_path.stat().st_size / (1024 * 1024), 2)

        clip_text = ""
        for seg in transcript.get("segments", []):
            if float(seg.get("end", 0)) > start_time and float(seg.get("start", 0)) < end_time:
                clip_text += " " + seg.get("text", "")

        ai_copy_text = generate_ai_copy(
            title=req.title,
            hook=req.hook,
            hashtags=req.hashtags,
            text=clip_text.strip(),
        )

        meta = {
            "clip_id": clip_id,
            "job_id": req.job_id,
            "title": req.title or f"Clip {clip_id}",
            "hook": req.hook or "",
            "hashtags": req.hashtags or ["#shorts", "#viral", "#reels", "#tiktok"],
            "viral_score": req.viral_score or 8.0,
            "start": start_time,
            "end": end_time,
            "duration": duration,
            "aspect_ratio": req.aspect_ratio,
            "layout": req.layout,
            "burn_subtitles": req.burn_subtitles,
            "subtitle_style": req.subtitle_style,
            "video_path": str(output_video_path),
            "video_url": f"/output/{clip_id}.mp4",
            "thumbnail_path": str(thumb_path) if thumb_path.exists() else "",
            "thumbnail_url": f"/output/thumbnails/{clip_id}.jpg" if thumb_path.exists() else "",
            "created_at": datetime.now().isoformat(),
            "file_size_mb": file_size_mb,
            "ai_copy": ai_copy_text,
        }

        meta_path = METADATA_DIR / f"{clip_id}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        render_job["status"] = "done"
        render_job["progress"] = 100
        render_job["message"] = "✅ Clip renderizado exitosamente."
        render_job["video_url"] = meta["video_url"]
        render_job["thumbnail_url"] = meta["thumbnail_url"]
        render_job["metadata"] = meta
        save_render_status(render_id)
        logger.info(f"Render completado para {clip_id} ({file_size_mb} MB)")

    except Exception as e:
        logger.error(f"Error renderizando {clip_id}: {e}", exc_info=True)
        render_job["status"] = "error"
        render_job["error"] = str(e)
        render_job["message"] = f"Error en renderizado: {str(e)}"
        save_render_status(render_id)


# -------------------------
# Routes
# -------------------------

@router.post("/render", response_model=RenderStatus)
async def render_clip(req: RenderClipRequest, background_tasks: BackgroundTasks):
    """Trigger background rendering of a viral clip."""
    import uuid
    render_id = str(uuid.uuid4())[:8]
    clean_clip_id = re.sub(r'[^\w\-]', '_', req.clip_id)

    render_jobs[render_id] = {
        "render_id": render_id,
        "clip_id": clean_clip_id,
        "status": "queued",
        "progress": 5,
        "message": "En cola de renderizado...",
        "video_url": None,
        "thumbnail_url": None,
        "metadata": None,
        "error": None,
    }
    save_render_status(render_id)

    background_tasks.add_task(execute_render, render_id, req)

    return RenderStatus(**render_jobs[render_id])


@router.post("/render-all/{job_id}")
async def render_all_clips(job_id: str, background_tasks: BackgroundTasks):
    """Render all viral clips discovered for a job sequentially."""
    job_data = get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    viral_clips = job_data.get("viral_clips", [])
    if not viral_clips:
        raise HTTPException(status_code=400, detail="No hay clips virales analizados para este job. Analiza el video primero.")

    results = []
    import uuid
    for clip in viral_clips:
        clip_id = clip.get("clip_id")
        render_id = str(uuid.uuid4())[:8]
        req = RenderClipRequest(
            job_id=job_id,
            clip_id=clip_id,
            start=clip.get("start"),
            end=clip.get("end"),
            title=clip.get("title"),
            hook=clip.get("hook"),
            hashtags=clip.get("hashtags"),
            viral_score=clip.get("viral_score"),
        )
        render_jobs[render_id] = {
            "render_id": render_id,
            "clip_id": clip_id,
            "status": "queued",
            "progress": 5,
            "message": "En cola de renderizado en lote...",
            "video_url": None,
            "thumbnail_url": None,
            "metadata": None,
            "error": None,
        }
        save_render_status(render_id)
        background_tasks.add_task(execute_render, render_id, req)
        results.append({"clip_id": clip_id, "render_id": render_id})

    return {"message": f"Iniciando render de {len(results)} clips en lote", "clips": results}


@router.get("/status/{render_id}", response_model=RenderStatus)
async def get_status_endpoint(render_id: str):
    """Get status of a rendering job."""
    job = get_render_job(render_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render ID no encontrado")
    return RenderStatus(**job)


@router.get("/")
async def list_clips():
    """List all rendered clips in the library."""
    clips_list = []
    seen_ids = set()

    # Read from metadata directory
    for meta_file in sorted(METADATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                cid = data.get("clip_id")
                v_path = Path(data.get("video_path", ""))
                if v_path.exists() and cid not in seen_ids:
                    # Garantizar que siempre tenga copy generado por IA
                    if not data.get("ai_copy"):
                        data["ai_copy"] = generate_ai_copy(data.get("title"), data.get("hook"), data.get("hashtags"))
                        try:
                            with open(meta_file, "w", encoding="utf-8") as mf:
                                json.dump(data, mf, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                    clips_list.append(data)
                    seen_ids.add(cid)
        except Exception as e:
            logger.warning(f"Error leyendo {meta_file}: {e}")

    # Also detect any orphaned MP4 files in OUTPUT_DIR
    for mp4 in sorted(OUTPUT_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True):
        cid = mp4.stem
        if cid not in seen_ids and not cid.endswith("_temp"):
            size_mb = round(mp4.stat().st_size / (1024 * 1024), 2)
            auto_meta = {
                "clip_id": cid,
                "job_id": "manual",
                "title": f"Clip {cid}",
                "hook": "",
                "hashtags": ["#shorts", "#viral", "#clipai"],
                "viral_score": 8.0,
                "duration": 0.0,
                "aspect_ratio": "9:16",
                "layout": "autoframing",
                "video_path": str(mp4),
                "video_url": f"/output/{mp4.name}",
                "thumbnail_path": "",
                "thumbnail_url": "",
                "created_at": datetime.now().isoformat(),
                "file_size_mb": size_mb,
                "ai_copy": generate_ai_copy(f"Clip {cid}", "", ["#shorts", "#viral", "#clipai"]),
            }
            clips_list.append(auto_meta)
            seen_ids.add(cid)

    return clips_list


@router.get("/copy/{clip_id}")
async def get_clip_copy(clip_id: str):
    """Retrieve or generate high-converting AI Copy & Hashtags for a clip."""
    meta_path = METADATA_DIR / f"{clip_id}.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                copy = data.get("ai_copy") or generate_ai_copy(data.get("title"), data.get("hook"), data.get("hashtags"))
                return {
                    "clip_id": clip_id,
                    "title": data.get("title"),
                    "copy": copy,
                    "hashtags": data.get("hashtags", []),
                }
        except Exception as e:
            logger.warning(f"Error leyendo copy de {clip_id}: {e}")

    fallback_copy = generate_ai_copy(f"Clip {clip_id}", "", ["#shorts", "#viral", "#clipai"])
    return {
        "clip_id": clip_id,
        "title": clip_id,
        "copy": fallback_copy,
        "hashtags": ["#shorts", "#viral", "#clipai"],
    }


@router.get("/{clip_id}")
async def get_clip(clip_id: str):
    """Get metadata for a specific clip."""
    meta_path = METADATA_DIR / f"{clip_id}.json"
    if not meta_path.exists():
        video_path = OUTPUT_DIR / f"{clip_id}.mp4"
        if video_path.exists():
            return {
                "clip_id": clip_id,
                "video_path": str(video_path),
                "video_url": f"/output/{clip_id}.mp4",
                "title": clip_id,
            }
        raise HTTPException(status_code=404, detail="Clip no encontrado")

    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.delete("/{clip_id}")
async def delete_clip(clip_id: str):
    """Delete a clip, its thumbnail, and metadata."""
    meta_path = METADATA_DIR / f"{clip_id}.json"
    video_path = OUTPUT_DIR / f"{clip_id}.mp4"
    thumb_path = THUMBNAILS_DIR / f"{clip_id}.jpg"

    deleted = []
    for p in [meta_path, video_path, thumb_path]:
        if p.exists():
            try:
                p.unlink()
                deleted.append(p.name)
            except Exception as e:
                logger.warning(f"No se pudo borrar {p}: {e}")

    if not deleted:
        raise HTTPException(status_code=404, detail="Clip no encontrado o ya eliminado")

    return {"message": f"Clip {clip_id} eliminado exitosamente", "deleted_files": deleted}


@router.get("/download/{clip_id}")
async def download_clip_file(clip_id: str):
    """Download the rendered MP4 file directly."""
    video_path = OUTPUT_DIR / f"{clip_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Archivo de video no encontrado")

    return FileResponse(
        path=str(video_path),
        filename=f"{clip_id}.mp4",
        media_type="video/mp4",
    )
