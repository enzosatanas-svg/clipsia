# 🎬 ClipAI Generator

> Generador automatizado de clips virales para **YouTube Shorts, TikTok e Instagram Reels** a partir de videos largos de YouTube, impulsado por IA, Whisper y FFmpeg.

---

## ⚡ Características Principales

1. **⚡ Generador Viral en 1-Clic**:
   - Pega cualquier enlace de YouTube y presiona un solo botón.
   - El sistema descarga, transcribe internamente en segundo plano, detecta los momentos virales con IA y renderiza los videos a 9:16 vertical listos para usar y descargar.
   - Sin pantallas intermedias ni bloques molestos de texto crudo.

2. **Ingesta Robusta con yt-dlp**:
   - Descarga a prueba de bloqueos con emulación multi-cliente (Android/iOS) y evasión de advertencias de bot.
   - Limpieza automática de URLs (YouTube Shorts, youtu.be, parámetros de tracking y marcas de tiempo).
   - Extracción de audio optimizada (16 kHz WAV mono).

3. **Transcripción Silenciosa y Detección Algorítmica de Momentos Virales**:
   - Transcripción interna y silenciosa con **OpenAI Whisper** (local y 100% gratuita).
   - Detección automática de curvas de retención, ganchos de curiosidad (*hooks*), preguntas clave y palabras de alto engagement.
   - Generación automática de títulos llamativos con emojis, hooks para los primeros 3 segundos y copy con hashtags virales.

4. **Renderizado Vertical 9:16 Profesional**:
   - Conversión inteligente de horizontal a vertical 9:16 (1080x1920).
   - Auto-Framing inteligente con seguimiento facial (MediaPipe) o fondo desenfocado dinámico (*Blurred Ambient Background*).
   - Subtítulos animados quemados estilo **Alex Hormozi** (palabras resaltadas dinámicas + emojis contextuales) y estilo TikTok.
   - Generación de miniaturas optimizadas para cada clip.

5. **Galería y Biblioteca de Clips**:
   - Previsualización directa en reproductor de video nativo 9:16.
   - Botón directo para descarga inmediata en archivo MP4.
   - Copiado en un clic de Copywriting y hashtags optimizados para TikTok, Shorts y Reels.

---

## 🚀 Inicio Rápido (Windows)

### Opción A: Instalación y Arranque Automático en 1 Clic
Simplemente haz doble clic en el archivo:
```text
setup.bat
```
El instalador verificará e instalará automáticamente:
- Python 3.11 (vía winget si no está presente)
- FFmpeg (vía winget si no está presente)
- Dependencias de `backend/requirements.txt`
- Creará el archivo `.env`
- Iniciará el backend FastAPI y el frontend Streamlit

### Opción B: Ejecución Manual
1. Clona o abre la carpeta del proyecto.
2. Instala las dependencias:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Inicia el backend de FastAPI:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. En otra terminal, inicia el frontend Streamlit:
   ```bash
   streamlit run frontend/app.py --server.port 8501
   ```
5. Abre en tu navegador:
   - **Frontend App**: [http://localhost:8501](http://localhost:8501)
   - **Backend Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Estructura del Proyecto

```text
CafeCamilo/
├── backend/
│   ├── main.py                  # Servidor FastAPI principal y middleware
│   ├── routers/
│   │   ├── ingest.py            # Descarga con yt-dlp y transcripción Whisper
│   │   ├── process.py           # Detección de clips virales y generación de hooks
│   │   ├── clips.py             # Renderizado 9:16, subtítulos ASS y biblioteca
│   │   └── publish.py           # Publicación en YouTube Shorts, TikTok y Reels
│   ├── requirements.txt         # Dependencias Python del proyecto
│   └── __init__.py
├── frontend/
│   ├── app.py                   # Dashboard visual Streamlit con 6 pestañas
│   └── __init__.py
├── downloads/                   # Almacén temporal de videos y audios descargados
├── output/                      # Almacén de clips renderizados y miniaturas
├── .env.example                 # Variables de entorno y claves API
├── setup.bat                    # Script de instalación y arranque para Windows
└── run.bat                      # Lanzador rápido
```

---

## ⚙️ Configuración (`.env`)

Copia `.env.example` a `.env` y configura tus credenciales si deseas usar APIs externas:

```ini
# Modelo de Whisper (tiny, base, small, medium, large)
WHISPER_MODEL=small

# OpenAI (Opcional: Si se deja vacío, el sistema usa análisis local gratuito)
OPENAI_API_KEY=

# YouTube Shorts (Google Cloud Console OAuth)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=

# TikTok Content Posting API
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# Instagram Graph API
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_USER_ID=
```
