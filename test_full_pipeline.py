"""
Full End-to-End Pipeline Test Script
Tests the full ClipAI pipeline with a real YouTube URL:
 1. Download video
 2. Extract audio and transcribe
 3. Detect multiple viral clips (5)
 4. Render all clips to 9:16 with Alex Hormozi subtitles
 5. Verify library
"""
import sys
import os
import json
import time
from pathlib import Path

# Force UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, r"c:\Users\WINDOWS\.gemini\antigravity\scratch\CafeCamilo")
os.chdir(r"c:\Users\WINDOWS\.gemini\antigravity\scratch\CafeCamilo")

import importlib
ingest_mod = importlib.import_module("backend.routers.ingest")
process_mod = importlib.import_module("backend.routers.process")
clips_mod = importlib.import_module("backend.routers.clips")

YOUTUBE_URL = "https://www.youtube.com/watch?v=clG3LV28bC0"
MAX_CLIPS = 5
WHISPER_MODEL = "base"

print("=" * 60)
print("  ClipAI Generator - Full Pipeline Test")
print(f"  URL: {YOUTUBE_URL}")
print(f"  Max clips: {MAX_CLIPS}")
print("=" * 60)

# ------------------------------------------------------------------
# STEP 1: Download + Transcribe
# ------------------------------------------------------------------
print("\n[1/5] Starting download & transcription...")
import uuid
job_id = str(uuid.uuid4())[:8]

ingest_mod.jobs[job_id] = {
    "job_id": job_id,
    "url": YOUTUBE_URL,
    "language": None,  # auto-detect
    "whisper_model": WHISPER_MODEL,
    "status": "queued",
    "progress": 5,
    "message": "Starting...",
    "video_path": None,
    "video_title": None,
    "duration": None,
    "thumbnail": None,
    "audio_path": None,
    "transcript": None,
    "error": None,
}
ingest_mod.save_job(job_id)

# Run download + transcription synchronously
ingest_mod.download_video(job_id, YOUTUBE_URL, WHISPER_MODEL)

job_data = ingest_mod.jobs[job_id]
if job_data.get("status") == "error":
    print(f"  ERROR in download/transcription: {job_data.get('error')}")
    sys.exit(1)

video_title = job_data.get("video_title", "unknown")
duration = job_data.get("duration", 0)
transcript = job_data.get("transcript", {})
n_segs = len(transcript.get("segments", []))
print(f"  Job ID    : {job_id}")
print(f"  Title     : {video_title}")
print(f"  Duration  : {duration:.1f}s ({duration/60:.1f} min)")
print(f"  Language  : {transcript.get('language')}")
print(f"  Segments  : {n_segs}")
print(f"  Status    : {job_data.get('status')}")


# ------------------------------------------------------------------
# STEP 2: Detect viral clips
# ------------------------------------------------------------------
print(f"\n[2/5] Detecting top {MAX_CLIPS} viral clips with AI scoring...")
raw_clips = process_mod.find_viral_segments_local(transcript, n=MAX_CLIPS)

if not raw_clips:
    print("  ERROR: No viral segments found")
    sys.exit(1)

viral_clips = []
for idx, clip in enumerate(raw_clips):
    clip_id = f"{job_id}_clip{idx+1}"
    title, hook, hashtags = process_mod.generate_title_and_hook(clip["text"], idx)
    reason = process_mod.generate_viral_reason(clip["score"], clip["text"])

    vc = process_mod.ViralClip(
        clip_id=clip_id,
        start=clip["start"],
        end=clip["end"],
        duration=clip["duration"],
        text=clip["text"],
        title=title,
        hook=hook,
        hashtags=hashtags,
        viral_score=clip["score"],
        reason=reason,
    )
    viral_clips.append(vc)
    print(f"  Clip {idx+1}: [{clip['start']:.1f}s - {clip['end']:.1f}s] score={clip['score']}  \"{clip['text'][:60]}...\"")

# Save viral clips to job
job_data["viral_clips"] = [c.dict() for c in viral_clips]
ingest_mod.save_job(job_id)


# ------------------------------------------------------------------
# STEP 3: Render all clips
# ------------------------------------------------------------------
print(f"\n[3/5] Rendering {len(viral_clips)} clips to 9:16 with Alex Hormozi subtitles...")

render_ids = []
for vc in viral_clips:
    render_req = clips_mod.RenderClipRequest(
        job_id=job_id,
        clip_id=vc.clip_id,
        start=vc.start,
        end=vc.end,
        aspect_ratio="9:16",
        layout="autoframing",
        burn_subtitles=True,
        subtitle_style="alex_hormozi",
        title=vc.title,
        hook=vc.hook,
        hashtags=vc.hashtags,
        viral_score=vc.viral_score,
    )
    import uuid as _uuid
    render_id = str(_uuid.uuid4())[:8]
    clips_mod.render_jobs[render_id] = {
        "render_id": render_id,
        "clip_id": vc.clip_id,
        "status": "queued",
        "progress": 5,
        "message": "Queued...",
        "video_url": None,
        "thumbnail_url": None,
        "metadata": None,
        "error": None,
    }
    clips_mod.save_render_status(render_id)
    render_ids.append((render_id, vc.clip_id))
    print(f"  Rendering {vc.clip_id} (render_id={render_id})...", flush=True)
    clips_mod.execute_render(render_id, render_req)
    rj = clips_mod.render_jobs[render_id]
    status = rj.get("status")
    if status == "done":
        meta = rj.get("metadata", {})
        size = meta.get("file_size_mb", 0)
        print(f"    OK: {meta.get('video_path')} ({size} MB)")
    else:
        print(f"    FAILED: {rj.get('error')}")


# ------------------------------------------------------------------
# STEP 4: Verify library
# ------------------------------------------------------------------
print(f"\n[4/5] Verifying Clips Library...")
all_clips = []
from pathlib import Path
import json as _json

meta_dir = Path("output/metadata")
for meta_file in sorted(meta_dir.glob(f"{job_id}_*.json")):
    with open(meta_file, "r", encoding="utf-8") as f:
        data = _json.load(f)
        all_clips.append(data)

print(f"  {len(all_clips)} clips found in library:")
for clip in all_clips:
    print(f"    [{clip['clip_id']}] {clip.get('duration',0):.1f}s | {clip.get('file_size_mb',0)} MB | Score: {clip.get('viral_score',0)}")
    print(f"     Title: {clip.get('title','')[:70]}")
    print(f"     Video: {clip.get('video_path','')}")
    ai_copy = clip.get("ai_copy", "")
    print(f"     Copy: {ai_copy[:80]}...")
    print()

print("\n[5/5] Final Summary")
ok_clips = [c for c in all_clips if Path(c.get("video_path","")).exists()]
print(f"  Total clips rendered successfully: {len(ok_clips)}/{MAX_CLIPS}")
print(f"  Job ID: {job_id}")
print(f"  Library path: output/")
print("\n=== PIPELINE TEST COMPLETE ===")
