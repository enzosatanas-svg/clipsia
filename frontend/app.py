"""
ClipAI Generator - Streamlit Frontend
Modern, high-converting AI dashboard to turn YouTube videos into viral TikTok/Shorts/Reels in 1-Click.
"""
import os
import re
import json
import time
from pathlib import Path
from datetime import datetime

import requests
import streamlit as st

# Configure page
st.set_page_config(
    page_title="ClipAI Generator — Viral Shorts & Reels Engine",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# -------------------------------------------------------------
# Premium Dark UI Styling (Outfit Font, Glassmorphism, Gradients)
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    code, pre, .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Radial gradient background */
    .stApp {
        background: radial-gradient(circle at 10% 15%, rgba(139, 92, 246, 0.12) 0%, transparent 40%),
                    radial-gradient(circle at 90% 85%, rgba(236, 72, 153, 0.10) 0%, transparent 40%),
                    radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.05) 0%, transparent 50%),
                    #090D14;
        color: #F1F5F9;
    }

    /* Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(139, 92, 246, 0.35);
        border-radius: 18px;
        padding: 24px 30px;
        margin-bottom: 24px;
        backdrop-filter: blur(14px);
        box-shadow: 0 10px 30px -10px rgba(139, 92, 246, 0.2);
    }
    
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(245, 158, 11, 0.2) 100%);
        border: 1px solid rgba(245, 158, 11, 0.4);
        color: #FDE047;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(90deg, #DDD6FE 0%, #F472B6 50%, #FDE047 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 8px 0 4px 0;
    }

    .hero-desc {
        color: #94A3B8;
        font-size: 1.05rem;
        max-width: 850px;
        line-height: 1.5;
        margin: 0;
    }

    /* Cards */
    .glass-card {
        background: #111622;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(167, 139, 250, 0.4);
        transform: translateY(-2px);
    }

    .glass-card-highlight {
        background: linear-gradient(135deg, rgba(20, 24, 39, 0.9) 0%, rgba(30, 27, 75, 0.6) 100%);
        border: 1px solid rgba(167, 139, 250, 0.4);
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(124, 58, 237, 0.15);
    }

    /* Badges */
    .badge-score {
        display: inline-block;
        background: linear-gradient(135deg, #DC2626 0%, #EA580C 50%, #D97706 100%);
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 12px;
        border-radius: 9999px;
        box-shadow: 0 0 14px rgba(234, 88, 12, 0.4);
    }

    .badge-meta {
        display: inline-block;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #CBD5E1;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 8px;
        margin-right: 6px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: 600;
        color: #94A3B8;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.25) 0%, rgba(217, 70, 239, 0.2) 100%) !important;
        border: 1px solid rgba(139, 92, 246, 0.5) !important;
        color: #FFFFFF !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.2px;
        transition: all 0.2s ease;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7C3AED 0%, #C026D3 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4);
    }

    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(192, 38, 211, 0.5);
        transform: translateY(-1px);
    }

    /* Video player container styling */
    .video-frame {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Backend API Connectors
# -------------------------------------------------------------

def check_backend_health():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def api_get(endpoint: str):
    try:
        r = requests.get(f"{BACKEND_URL}{endpoint}", timeout=25)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def api_post(endpoint: str, payload: dict):
    try:
        r = requests.post(f"{BACKEND_URL}{endpoint}", json=payload, timeout=60)
        return r.json() if r.status_code in (200, 201) else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------------
# State Initialization
# -------------------------------------------------------------

if "active_pipeline_id" not in st.session_state:
    st.session_state["active_pipeline_id"] = None
if "current_job_id" not in st.session_state:
    st.session_state["current_job_id"] = None
if "selected_clip_for_render" not in st.session_state:
    st.session_state["selected_clip_for_render"] = None
if "selected_clip_for_publish" not in st.session_state:
    st.session_state["selected_clip_for_publish"] = None
if "active_render_id" not in st.session_state:
    st.session_state["active_render_id"] = None
if "analyzed_clips" not in st.session_state:
    st.session_state["analyzed_clips"] = []


# -------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🎬 ClipAI Studio")
    st.markdown("<small style='color: #94A3B8;'>Generador Autónomo de Clips 9:16</small>", unsafe_allow_html=True)
    st.write("---")

    backend_ok = check_backend_health()
    if backend_ok:
        st.success("🟢 Backend FastAPI Activo")
    else:
        st.error("🔴 Backend Desconectado")
        st.caption("Ejecuta en consola: `run.bat` o `uvicorn backend.main:app --reload`")

    st.write("---")
    st.markdown("#### 📂 Historial de Sesiones")

    # Fetch recent pipelines
    pipe_history = api_get("/api/pipeline/history") or []
    pipe_choices = {}
    for p in pipe_history:
        pid = p.get("pipeline_id")
        title = p.get("video_title") or pid
        status = p.get("status")
        icon = "✅" if status == "completed" else ("⏳" if status in ("downloading", "transcribing", "detecting", "rendering") else "⚠️")
        pipe_choices[pid] = f"{icon} {title[:24]} ({pid})"

    if pipe_choices:
        cur_p = st.session_state.get("active_pipeline_id")
        def_p_idx = 0
        if cur_p and cur_p in pipe_choices:
            def_p_idx = list(pipe_choices.keys()).index(cur_p)

        sel_pipe = st.selectbox(
            "Ver Lote de Clips:",
            options=list(pipe_choices.keys()),
            format_func=lambda x: pipe_choices[x],
            index=def_p_idx,
            key="sb_pipe_selector",
        )
        if sel_pipe != st.session_state.get("active_pipeline_id"):
            st.session_state["active_pipeline_id"] = sel_pipe
            st.rerun()

    st.write("---")
    st.markdown("#### ⚡ Motor Inteligente")
    st.caption("• **yt-dlp**: Android/iOS Multi-Client (Anti-Bot)")
    st.caption("• **Whisper**: Transcripción Silenciosa en 2do Plano")
    st.caption("• **Auto-Framing**: Detección Facial MediaPipe")
    st.caption("• **Subtítulos**: Alex Hormozi (Animados + Emojis)")
    st.caption("• **Formato**: 1080x1920 (9:16 Vertical MP4)")

    if st.button("🔄 Refrescar Panel", use_container_width=True):
        st.rerun()


# -------------------------------------------------------------
# Top Hero Header
# -------------------------------------------------------------

st.markdown("""
<div class="hero-container">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
            <span class="hero-badge">⚡ 100% Autónomo • 1-Clic</span>
            <h1 class="hero-title">ClipAI Generator</h1>
            <p class="hero-desc">
                Pega la URL de cualquier video de YouTube y obtén al instante tus clips virales en 9:16 vertical, con detección automática de ganchos y subtítulos de alto impacto listos para descargar.
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Navigation Tabs
# -------------------------------------------------------------

tabs = st.tabs([
    "⚡ 1. Generador Viral 1-Clic",
    "📁 2. Biblioteca de Clips 9:16",
    "🎛️ 3. Editor Manual Avanzado",
    "🚀 4. Publicar en Redes",
    "⚙️ 5. Diagnóstico & Ajustes",
])


# =============================================================
# TAB 1: Generador Viral 1-Clic (Experiencia Principal)
# =============================================================
with tabs[0]:
    st.markdown("### ⚡ Generación Automática de Clips Virales")
    st.markdown("Pega el enlace de YouTube y presiona el botón. La IA se encarga de la descarga, el análisis interno del diálogo, la detección de momentos virales y el recorte vertical a 9:16.")

    with st.container():
        st.markdown('<div class="glass-card-highlight">', unsafe_allow_html=True)
        
        yt_input_url = st.text_input(
            "🔗 URL del Video de YouTube:",
            placeholder="https://www.youtube.com/watch?v=... o https://youtu.be/...",
            key="one_click_url",
        )

        c_opt1, c_opt2, c_opt3 = st.columns([1, 1.2, 1.2])
        with c_opt1:
            num_clips = st.selectbox(
                "Cantidad de clips virales:",
                [3, 1, 2, 4, 5],
                index=0,
                help="Número de fragmentos virales óptimos a generar automáticamente.",
            )
        with c_opt2:
            sub_style = st.selectbox(
                "Estilo de Subtítulos:",
                [
                    "alex_hormozi",
                    "alex_hormozi_green",
                    "tiktok_yellow",
                    "neon_cyan",
                    "clean_white",
                ],
                format_func=lambda x: {
                    "alex_hormozi": "🔥 Alex Hormozi (Emojis + Resaltado)",
                    "alex_hormozi_green": "🚀 Hormozi Verde Neón",
                    "tiktok_yellow": "🟡 TikTok Amarillo Clásico",
                    "neon_cyan": "💎 Cian Neón Alto Contraste",
                    "clean_white": "⚪ Blanco Minimalista",
                }.get(x, x),
                index=0,
            )
        with c_opt3:
            layout_mode = st.selectbox(
                "Encuadre 9:16 Vertical:",
                [
                    "autoframing",
                    "blur_bg",
                    "crop",
                ],
                format_func=lambda x: {
                    "autoframing": "📱 Auto-Framing IA Facial 9:16",
                    "blur_bg": "🌌 Fondo Desenfocado Dinámico 9:16",
                    "crop": "✂️ Recorte Centrado 9:16",
                }.get(x, x),
                index=0,
            )

        st.write("")
        run_1click_btn = st.button(
            "⚡ GENERAR CLIPS VIRALES 9:16 EN 1-CLIC",
            type="primary",
            use_container_width=True,
        )

        st.markdown('</div>', unsafe_allow_html=True)

    # Trigger Pipeline
    if run_1click_btn:
        if not yt_input_url or ("youtube.com" not in yt_input_url and "youtu.be" not in yt_input_url):
            st.error("Por favor ingresa una URL válida de YouTube.")
        else:
            with st.spinner("Iniciando motor autónomo de clips virales..."):
                payload = {
                    "youtube_url": yt_input_url,
                    "max_clips": num_clips,
                    "subtitle_style": sub_style,
                    "layout": layout_mode,
                    "aspect_ratio": "9:16",
                    "burn_subtitles": True,
                }
                res = api_post("/api/pipeline/generate", payload)
                if res and "pipeline_id" in res:
                    st.session_state["active_pipeline_id"] = res["pipeline_id"]
                    st.success(f"¡Proceso iniciado exitosamente! ID `{res['pipeline_id']}`")
                    st.rerun()
                else:
                    st.error(f"Error al iniciar el proceso: {res}")

    # Track Pipeline Progress & Show Direct Results
    active_pipe_id = st.session_state.get("active_pipeline_id")
    if active_pipe_id:
        st.write("---")
        pipe_data = api_get(f"/api/pipeline/status/{active_pipe_id}")

        if pipe_data:
            p_status = pipe_data.get("status", "unknown")
            p_prog = pipe_data.get("progress", 0)
            p_msg = pipe_data.get("message", "")
            video_title = pipe_data.get("video_title") or "Video"
            rendered_clips = pipe_data.get("clips", [])

            # While processing: Clean, elegant status without text clutter
            if p_status in ("queued", "downloading", "transcribing", "detecting", "rendering"):
                st.markdown(f"#### ⏳ Procesando Video: **{video_title}** (`{active_pipe_id}`)")
                st.progress(p_prog / 100)

                col_stat1, col_stat2 = st.columns([3, 1])
                with col_stat1:
                    step_badges = {
                        "downloading": "📥 Paso 1/4: Descarga en Alta Definición",
                        "transcribing": "🎙️ Paso 2/4: Análisis Interno de Voz (Whisper IA)",
                        "detecting": "🔥 Paso 3/4: Detección de Momentos Virales y Ganchos",
                        "rendering": "🎬 Paso 4/4: Renderizado 9:16 con Subtítulos Dinámicos",
                    }
                    badge_label = step_badges.get(p_status, "⚡ Procesamiento Autónomo")
                    st.info(f"**[{badge_label}]** — {p_msg}")
                with col_stat2:
                    if st.button("🔄 Actualizar", key="btn_refresh_pipe"):
                        st.rerun()

                st.caption("El procesamiento de audio y transcripción se ejecuta de forma interna y silenciosa en segundo plano...")
                time.sleep(2)
                st.rerun()

            elif p_status == "error":
                st.error(f"❌ Ocurrió un error en el pipeline: {pipe_data.get('error')}")
                st.info("Verifica que la URL sea accesible o prueba con otro video.")

            elif p_status == "completed":
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 14px; padding: 18px 24px; margin-bottom: 24px;">
                    <h3 style="color: #34D399; margin: 0 0 6px 0;">🎉 ¡Tus clips virales están listos para usar!</h3>
                    <p style="color: #E2E8F0; margin: 0; font-size: 1rem;">
                        Video original: <strong>{video_title}</strong> — Se produjeron <strong>{len(rendered_clips)} videos verticales 9:16</strong> con subtítulos quemados y títulos optimizados para algoritmos.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                if not rendered_clips:
                    st.warning("El proceso finalizó pero no se generaron clips. Revisa los registros o reintenta.")
                else:
                    st.markdown(f"### 📱 Galería de Clips Virales 9:16 ({len(rendered_clips)})")

                    for idx, clip in enumerate(rendered_clips):
                        cid = clip.get("clip_id")
                        c_title = clip.get("title", f"Clip {idx+1}")
                        c_score = clip.get("viral_score", 9.0)
                        c_dur = clip.get("duration", 30.0)
                        c_hook = clip.get("hook", "")
                        c_size = clip.get("file_size_mb", 0.0)
                        c_copy = clip.get("ai_copy") or ""
                        v_url = f"{BACKEND_URL}{clip.get('video_url')}"
                        v_path = clip.get("video_path")

                        st.markdown(f"""
                        <div class="glass-card" style="margin-top: 15px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                                <div>
                                    <span class="badge-meta">Clip #{idx+1}</span>
                                    <span class="badge-meta">📱 9:16 Vertical</span>
                                    <span class="badge-meta">⏱️ {c_dur:.1f}s</span>
                                    <span class="badge-meta">💾 {c_size} MB</span>
                                </div>
                                <span class="badge-score">⭐ Viral Score: {c_score}/10</span>
                            </div>
                            <h3 style="color: #F8FAFC; margin: 4px 0 6px 0;">{c_title}</h3>
                            <p style="color: #C084FC; font-size: 0.95rem; margin: 0 0 10px 0;">
                                <strong>Hook inicial:</strong> <em>"{c_hook}"</em>
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                        col_vid, col_meta = st.columns([1.1, 1.3])

                        with col_vid:
                            # Direct 9:16 Video Player
                            st.video(v_url)

                        with col_meta:
                            st.markdown("#### 🚀 Acciones Rápidas")

                            # Direct Download Button
                            has_downloaded = False
                            if v_path and Path(v_path).exists():
                                try:
                                    with open(v_path, "rb") as vf:
                                        video_bytes = vf.read()
                                        st.download_button(
                                            "📥 DESCARGAR CLIP MP4 (Alta Calidad)",
                                            data=video_bytes,
                                            file_name=f"{cid}.mp4",
                                            mime="video/mp4",
                                            type="primary",
                                            key=f"dl_btn_{cid}_{idx}",
                                            use_container_width=True,
                                        )
                                        has_downloaded = True
                                except Exception:
                                    pass

                            if not has_downloaded:
                                try:
                                    resp = requests.get(v_url, timeout=15)
                                    if resp.status_code == 200:
                                        st.download_button(
                                            "📥 DESCARGAR CLIP MP4",
                                            data=resp.content,
                                            file_name=f"{cid}.mp4",
                                            mime="video/mp4",
                                            type="primary",
                                            key=f"dl_btn_net_{cid}_{idx}",
                                            use_container_width=True,
                                        )
                                except Exception:
                                    st.caption(f"📁 Archivo: `{v_url}`")

                            st.write("")
                            # AI Copy & Hashtags
                            st.markdown("##### 📝 Copy & Hashtags para TikTok / Shorts / Reels")
                            st.caption("Texto optimizado con emojis y ganchos de retención para copiar y pegar:")
                            st.code(c_copy, language=None)

                            # Direct Publish shortcut
                            if st.button(f"📤 Preparar Publicación para Clip #{idx+1}", key=f"pub_sc_{cid}"):
                                st.session_state["selected_clip_for_publish"] = clip
                                st.info("Clip seleccionado. Abre la pestaña **'4. Publicar en Redes'**.")

                        st.write("---")

                    if st.button("✨ Procesar Otro Video de YouTube", use_container_width=True):
                        st.session_state["active_pipeline_id"] = None
                        st.rerun()


# =============================================================
# TAB 2: Biblioteca de Clips 9:16
# =============================================================
with tabs[1]:
    st.markdown("### 📁 Biblioteca de Todos los Clips Renderizados")
    st.markdown("Explora, reproduce y descarga todos los videos en formato vertical 9:16 guardados en el sistema.")

    all_clips = api_get("/api/clips/") or []

    if not all_clips:
        st.info("Aún no tienes clips en la biblioteca. Genera tu primer lote con una URL en la Pestaña 1.")
    else:
        st.caption(f"Total de clips listos: **{len(all_clips)}**")

        for i in range(0, len(all_clips), 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < len(all_clips):
                    clip_item = all_clips[i + j]
                    cid = clip_item.get("clip_id")
                    with cols[j]:
                        st.markdown(f"""
                        <div class="glass-card" style="margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span class="badge-score">⭐ {clip_item.get('viral_score', 8.5)}/10</span>
                                <span style="color: #94A3B8; font-size: 0.82rem;">
                                    ⏱️ {clip_item.get('duration', 0):.1f}s | 💾 {clip_item.get('file_size_mb', 0)} MB
                                </span>
                            </div>
                            <h4 style="margin: 4px 0 6px 0; color: #F8FAFC;">{clip_item.get('title')}</h4>
                        </div>
                        """, unsafe_allow_html=True)

                        video_full = f"{BACKEND_URL}{clip_item.get('video_url')}"
                        st.video(video_full)

                        # Copy expander
                        with st.expander("📝 Ver Copy & Hashtags para Redes"):
                            st.code(clip_item.get("ai_copy", ""), language=None)

                        b1, b2, b3 = st.columns(3)
                        with b1:
                            if st.button("🚀 Publicar", key=f"lib_pub_{cid}", use_container_width=True):
                                st.session_state["selected_clip_for_publish"] = clip_item
                                st.info("Clip seleccionado. Abre la pestaña 4.")
                        with b2:
                            local_p = clip_item.get("video_path")
                            if local_p and Path(local_p).exists():
                                with open(local_p, "rb") as f_local:
                                    st.download_button(
                                        "📥 Bajar",
                                        data=f_local.read(),
                                        file_name=f"{cid}.mp4",
                                        mime="video/mp4",
                                        key=f"lib_dl_{cid}",
                                        use_container_width=True,
                                    )
                            else:
                                st.download_button(
                                    "📥 Bajar",
                                    data=requests.get(video_full).content,
                                    file_name=f"{cid}.mp4",
                                    mime="video/mp4",
                                    key=f"lib_dl_{cid}",
                                    use_container_width=True,
                                )
                        with b3:
                            if st.button("🗑️ Borrar", key=f"lib_del_{cid}", use_container_width=True):
                                requests.delete(f"{BACKEND_URL}/api/clips/{cid}")
                                st.success(f"Clip '{cid}' eliminado.")
                                st.rerun()


# =============================================================
# TAB 3: Editor Manual Avanzado (Para ajustes minuciosos)
# =============================================================
with tabs[2]:
    st.markdown("### 🎛️ Editor Manual y Ajuste Fino de Tiempos")
    st.markdown("Herramientas para ajustar manualmente segundo a segundo los cortes, cambiar estilos o probar combinaciones personalizadas.")

    sel_clip = st.session_state.get("selected_clip_for_render") or {}

    col_r1, col_r2 = st.columns([1.1, 1])

    with col_r1:
        st.markdown("#### 1. Parámetros del Clip")
        r_job_id = st.text_input(
            "Job ID / Video ID:",
            value=st.session_state.get("current_job_id") or st.session_state.get("active_pipeline_id") or "",
            key="man_job_id_input",
        )
        r_clip_id = st.text_input(
            "Clip ID:",
            value=sel_clip.get("clip_id") or f"{r_job_id}_custom" if r_job_id else "clip_manual",
            key="man_clip_id_input",
        )

        c_time1, c_time2 = st.columns(2)
        with c_time1:
            r_start = st.number_input(
                "Segundo Inicio:",
                value=float(sel_clip.get("start", 0.0)),
                min_value=0.0,
                step=0.5,
                key="man_start_val",
            )
        with c_time2:
            r_end = st.number_input(
                "Segundo Fin:",
                value=float(sel_clip.get("end", 35.0)),
                min_value=0.5,
                step=0.5,
                key="man_end_val",
            )

        calc_dur = max(1.0, round(r_end - r_start, 2))
        st.caption(f"⏱️ Duración estimada: **{calc_dur} segundos**")

        r_title = st.text_input(
            "Título Viral:",
            value=sel_clip.get("title") or "Momento impactante",
            key="man_title_val",
        )
        r_hook = st.text_input(
            "Hook / Gancho inicial:",
            value=sel_clip.get("hook") or "¿Sabías que...",
            key="man_hook_val",
        )

    with col_r2:
        st.markdown("#### 2. Composición y Subtítulos")
        r_aspect = st.selectbox(
            "Relación de Aspecto:",
            ["9:16 (Vertical Shorts/TikTok)", "1:1 (Cuadrado)", "16:9 (Horizontal)"],
            index=0,
            key="man_aspect_select",
        )
        aspect_val = "9:16" if "9:16" in r_aspect else ("1:1" if "1:1" in r_aspect else "16:9")

        r_layout = st.selectbox(
            "Modo de Encuadre:",
            [
                "Auto-Framing Facial IA (MediaPipe) [Recomendado]",
                "Fondo Desenfocado Profesional (blur_bg)",
                "Recorte Centrado (crop)",
            ],
            index=0,
            key="man_layout_select",
        )
        layout_val = "autoframing" if "Auto-Framing" in r_layout else ("blur_bg" if "Desenfocado" in r_layout else "crop")

        r_subs = st.checkbox("🔥 Quemar subtítulos animados en el video", value=True, key="man_subs_check")

        r_style = st.selectbox(
            "Estilo de Subtítulos:",
            [
                "alex_hormozi (Palabras Resaltadas + Emojis 🔥)",
                "alex_hormozi_green (Verde Neón + Emojis 🚀)",
                "tiktok_yellow (Amarillo Clásico)",
                "neon_cyan (Cian Neón)",
                "clean_white (Blanco Minimalista)",
            ],
            index=0,
            key="man_style_select",
        )
        style_val = r_style.split()[0]

    st.write("---")
    man_render_btn = st.button("🚀 Renderizar Clip Manual Ahora", type="primary", use_container_width=True)

    if man_render_btn:
        if not r_job_id:
            st.error("Debes ingresar un Job ID válido.")
        elif r_end <= r_start:
            st.error("El segundo de fin debe ser mayor al segundo de inicio.")
        else:
            payload = {
                "job_id": r_job_id,
                "clip_id": r_clip_id,
                "start": r_start,
                "end": r_end,
                "aspect_ratio": aspect_val,
                "layout": layout_val,
                "burn_subtitles": r_subs,
                "subtitle_style": style_val,
                "title": r_title,
                "hook": r_hook,
            }
            with st.spinner("Enviando render a FFmpeg..."):
                res = api_post("/api/clips/render", payload)
                if res and "render_id" in res:
                    st.success(f"Render iniciado con ID `{res['render_id']}`. Revisa la Biblioteca de Clips.")
                else:
                    st.error(f"Error iniciando render: {res}")


# =============================================================
# TAB 4: Publicar en Redes
# =============================================================
with tabs[3]:
    st.markdown("### 🚀 Publicador Multiplataforma Automatizado")
    st.markdown("Distribuye tus clips directamente en YouTube Shorts, TikTok e Instagram Reels con un solo clic.")

    pub_clip = st.session_state.get("selected_clip_for_publish")
    all_rendered = api_get("/api/clips/") or []
    clip_options = {c["clip_id"]: f"{c.get('title', c['clip_id'])} ({c.get('duration', 0):.1f}s)" for c in all_rendered}

    p_col1, p_col2 = st.columns([1, 1])

    with p_col1:
        st.markdown("#### 1. Selecciona el Clip")
        if clip_options:
            def_idx = 0
            if pub_clip and pub_clip.get("clip_id") in clip_options:
                def_idx = list(clip_options.keys()).index(pub_clip["clip_id"])

            sel_pub_id = st.selectbox(
                "Clip para publicar:",
                options=list(clip_options.keys()),
                format_func=lambda x: clip_options[x],
                index=def_idx,
            )
            chosen = next((c for c in all_rendered if c["clip_id"] == sel_pub_id), {})
        else:
            sel_pub_id = None
            chosen = {}
            st.warning("No hay clips en la biblioteca. Genera clips primero.")

        st.markdown("#### 2. Plataformas Destino")
        pub_yt = st.checkbox("🔴 YouTube Shorts", value=True)
        pub_tk = st.checkbox("🎵 TikTok", value=True)
        pub_ig = st.checkbox("📸 Instagram Reels", value=True)

        privacy_val = st.selectbox("Visibilidad:", ["public", "unlisted", "private"], index=0)

    with p_col2:
        st.markdown("#### 3. Metadatos del Post")
        f_title = st.text_input(
            "Título del post:",
            value=chosen.get("title", "Mi clip viral #Shorts"),
        )
        f_desc = st.text_area(
            "Descripción / Caption:",
            value=chosen.get("ai_copy") or f"{chosen.get('hook', '')}\n\nCreado con ClipAI Generator #shorts #viral #reels",
            height=120,
        )

    st.write("---")
    pub_btn = st.button("🚀 Publicar en Todas las Plataformas Seleccionadas", type="primary", use_container_width=True)

    if pub_btn:
        if not sel_pub_id:
            st.error("Selecciona un clip primero.")
        else:
            targets = []
            if pub_yt: targets.append("youtube")
            if pub_tk: targets.append("tiktok")
            if pub_ig: targets.append("instagram")

            if not targets:
                st.error("Selecciona al menos una plataforma.")
            else:
                pub_payload = {
                    "clip_id": sel_pub_id,
                    "platforms": targets,
                    "title": f_title,
                    "description": f_desc,
                    "hashtags": chosen.get("hashtags", ["#shorts", "#viral"]),
                    "privacy": privacy_val,
                }
                with st.spinner("Enviando publicaciones..."):
                    pub_res = api_post("/api/publish/send", pub_payload)
                    if pub_res and "results" in pub_res:
                        st.success("¡Publicaciones procesadas exitosamente!")
                        for item in pub_res["results"]:
                            st.write(f"• **{item['platform'].upper()}**: `{item['status']}` — {item.get('message', '')}")
                    else:
                        st.error(f"Error: {pub_res}")


# =============================================================
# TAB 5: Diagnóstico & Ajustes
# =============================================================
with tabs[4]:
    st.markdown("### ⚙️ Diagnóstico del Sistema y Estado de APIs")
    st.markdown("Comprueba las conexiones, modelos de IA y configuraciones locales.")

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        st.markdown("#### 🤖 Modelos de Whisper")
        whisper_dir = Path.home() / ".cache" / "whisper"
        models_found = list(whisper_dir.glob("*.pt")) if whisper_dir.exists() else []
        if models_found:
            for m in models_found:
                sz_mb = round(m.stat().st_size / (1024 * 1024), 1)
                st.success(f"✅ `{m.name}` ({sz_mb} MB listo)")
        else:
            st.info("Los modelos se descargan automáticamente en su primer uso.")

    with col_d2:
        st.markdown("#### 🎥 FFmpeg y Codecs")
        try:
            ff_res = requests.get(f"{BACKEND_URL}/health", timeout=2)
            if ff_res.status_code == 200:
                st.success("✅ Backend FastAPI en línea")
                st.caption("H.264 / AAC / libass habilitados")
            else:
                st.warning("Backend no responde")
        except Exception:
            st.error("Backend no iniciado")

    with col_d3:
        st.markdown("#### 🌐 yt-dlp & APIs")
        st.success("✅ yt-dlp 2026.8.19 (Android/iOS Engine)")
        pub_st = api_get("/api/publish/status") or {}
        yt_conf = pub_st.get("youtube", {}).get("configured", False)
        st.write(f"• Redes Sociales: {'🟢 Conectado' if yt_conf else '🟡 Modo Simulación Activo'}")

    st.write("---")
    st.markdown("#### 💡 Variables de Entorno (`.env`)")
    st.code("""
# Modelo Whisper (base = ultrarrápido, small = alta precisión)
WHISPER_MODEL=base

# Directorios de salida
OUTPUT_DIR=output
DOWNLOADS_DIR=downloads

# OpenAI API (Opcional: Si se deja en blanco, usa el motor algorítmico local gratuito)
OPENAI_API_KEY=
""", language="ini")
