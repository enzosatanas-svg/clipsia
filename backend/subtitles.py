"""
Módulo de Generación de Subtítulos Animados Estilo Alex Hormozi y Redes Sociales
- Resaltado palabra por palabra (Word-by-Word Highlight / Karaoke Dinámico)
- Tipografías gruesas de alto impacto (Impact, Montserrat, Arial Black)
- Emojis contextuales automáticos basados en IA semántica
- Compatibilidad nativa con FFmpeg y formato ASS (Advanced SubStation Alpha)
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("clipai.subtitles")

# Mapeo semántico de palabras clave a emojis automáticos de alto impacto
EMOJI_PATTERNS = [
    (r'\b(dinero|dolar|dolares|plata|cash|money|millones|precio|ganar|ganancia|rico|fortuna|financiero)\b', '💰'),
    (r'\b(fuego|viral|increible|brutal|locura|exito|top|crack|rompe|rompiendo|brutalmente|flama)\b', '🔥'),
    (r'\b(secreto|truco|hack|mente|cerebro|idea|pensar|inteligencia|saber|aprender|estrategia)\b', '🧠'),
    (r'\b(mira|ojo|atencion|cuidado|espera|wow|escucha|revelado|descubre)\b', '👀'),
    (r'\b(rapido|tiempo|segundo|segundos|minuto|velocidad|ya|ahora|urgente|inmediato)\b', '⚡'),
    (r'\b(crecer|escalar|subir|duplicar|resultado|meta|objetivo|despegue|futuro)\b', '🚀'),
    (r'\b(fuerza|poder|fuerte|disciplina|habito|entrenamiento|duro|constancia)\b', '💪'),
    (r'\b(error|nunca|jamas|no|peligro|stop|fallo|perder|trampa|cero)\b', '❌'),
    (r'\b(verdad|real|100|clave|perfecto|garantizado|seguro)\b', '💯'),
    (r'\b(habla|dije|dice|voz|comunicar|podcast|entrevista|gritar)\b', '🗣️'),
    (r'\b(meta|ganador|victoria|campeon|triunfo|premio)\b', '🏆'),
    (r'\b(magia|increible|magico|impacto|boom|sorpresa)\b', '💥'),
]


def format_ass_time(seconds: float) -> str:
    """Formatea segundos a formato de timestamp ASS: H:MM:SS.cs con valores no negativos."""
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def clean_subtitle_text(text: str) -> str:
    """Limpia caracteres de escape de ASS y normaliza a mayúsculas para estilo Hormozi."""
    text = re.sub(r'[\{\}\\]', '', text)
    text = text.replace('"', "''").strip()
    return text.upper()


def detect_contextual_emoji(text: str) -> str:
    """Detecta automáticamente el emoji más impactante según el texto."""
    t_lower = text.lower()
    for pattern, emoji in EMOJI_PATTERNS:
        if re.search(pattern, t_lower):
            return emoji
    if "?" in text:
        return "❓"
    if "!" in text:
        return "🔥"
    return ""


def build_hormozi_subtitles(
    transcript: dict,
    start_sec: float,
    end_sec: float,
    font_name: str = "Impact",
    highlight_color: str = "&H0000FFFF&",  # Amarillo brillante en BGR ASS
    normal_color: str = "&H00FFFFFF&",     # Blanco puro
    chunk_size: int = 3,
) -> str:
    """
    Genera diálogos estilo Alex Hormozi con resaltado palabra por palabra y emojis automáticos.
    """
    segments = transcript.get("segments", [])
    events = []

    for seg in segments:
        s_start = float(seg.get("start", 0))
        s_end = float(seg.get("end", 0))

        # Filtrar segmentos fuera del rango del clip
        if s_end <= start_sec or s_start >= end_sec:
            continue

        raw_words = seg.get("words", [])

        # Si el modelo Whisper no incluyó timestamps por palabra, interpolar uniformemente
        if not raw_words:
            seg_text = clean_subtitle_text(seg.get("text", ""))
            tokens = seg_text.split()
            if not tokens:
                continue
            seg_dur = max(0.2, s_end - s_start)
            word_dur = seg_dur / len(tokens)
            raw_words = []
            for idx, token in enumerate(tokens):
                w_s = s_start + (idx * word_dur)
                w_e = w_s + word_dur
                raw_words.append({"word": token, "start": w_s, "end": w_e})

        # Filtrar palabras dentro del rango
        in_range_words = [
            w for w in raw_words
            if float(w.get("end", 0)) > start_sec and float(w.get("start", 0)) < end_sec
        ]

        if not in_range_words:
            continue

        # Agrupar en pequeños fragmentos de 2-4 palabras para máxima retención visual
        for i in range(0, len(in_range_words), chunk_size):
            chunk = in_range_words[i:i + chunk_size]
            if not chunk:
                continue

            chunk_text = " ".join(clean_subtitle_text(w.get("word", "")) for w in chunk)
            emoji = detect_contextual_emoji(chunk_text)
            emoji_suffix = f" {emoji}" if emoji else ""

            # Generar resaltado palabra por palabra para cada palabra del grupo
            for active_idx, target_word in enumerate(chunk):
                w_start_rel = max(0.0, float(target_word.get("start", 0)) - start_sec)
                w_end_rel = min(end_sec - start_sec, float(target_word.get("end", 0)) - start_sec)

                # Si es la última palabra del grupo o duración muy corta, dar tiempo visible mínimo
                if w_end_rel <= w_start_rel:
                    w_end_rel = w_start_rel + 0.35
                elif (w_end_rel - w_start_rel) < 0.2:
                    w_end_rel = w_start_rel + 0.25

                # Armar el texto con la palabra activa resaltada
                word_pieces = []
                for idx, w in enumerate(chunk):
                    w_text = clean_subtitle_text(w.get("word", ""))
                    if not w_text:
                        continue
                    if idx == active_idx:
                        # Color amarillo/neón para la palabra que se está diciendo
                        word_pieces.append(f"{{\\c{highlight_color}}}{w_text}{{\\c{normal_color}}}")
                    else:
                        word_pieces.append(w_text)

                line_content = " ".join(word_pieces) + emoji_suffix
                if line_content.strip():
                    events.append(
                        f"Dialogue: 0,{format_ass_time(w_start_rel)},{format_ass_time(w_end_rel)},Hormozi,,0,0,0,,{line_content}"
                    )

    return "\n".join(events)


def generate_ass_subtitles_file(
    transcript: dict,
    start_sec: float,
    end_sec: float,
    out_path: Path,
    style_name: str = "alex_hormozi",
) -> Path:
    """
    Crea el archivo ASS completo con estilos modernos de alta fidelidad para videos verticales 9:16.
    """
    style_defs = {
        "alex_hormozi": {
            "style_line": (
                "Style: Hormozi,Impact,78,&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,"
                "-1,0,0,0,100,100,2,0,1,6,3,2,60,60,420,1"
            ),
            "is_hormozi": True,
            "highlight": "&H0000FFFF&",  # Amarillo Hormozi
            "normal": "&H00FFFFFF&",     # Blanco puro
        },
        "alex_hormozi_green": {
            "style_line": (
                "Style: Hormozi,Impact,78,&H00FFFFFF,&H0033FF00,&H00000000,&H90000000,"
                "-1,0,0,0,100,100,2,0,1,6,3,2,60,60,420,1"
            ),
            "is_hormozi": True,
            "highlight": "&H0033FF00&",  # Verde Neón Hormozi
            "normal": "&H00FFFFFF&",
        },
        "tiktok_yellow": {
            "style_line": (
                "Style: TikTok,Arial,66,&H0000FFFF,&H000000FF,&H00000000,&H80000000,"
                "-1,0,0,0,100,100,2,0,1,5,3,2,60,60,380,1"
            ),
            "is_hormozi": False,
        },
        "clean_white": {
            "style_line": (
                "Style: TikTok,Segoe UI,62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                "-1,0,0,0,100,100,2,0,1,4,2,2,60,60,380,1"
            ),
            "is_hormozi": False,
        },
        "neon_cyan": {
            "style_line": (
                "Style: TikTok,Impact,70,&H00FFFF00,&H000000FF,&H00000000,&H80000000,"
                "-1,0,0,0,100,100,3,0,1,5,3,2,60,60,380,1"
            ),
            "is_hormozi": False,
        },
        "karaoke_box": {
            "style_line": (
                "Style: TikTok,Arial,64,&H0000FFFF,&H00FFFFFF,&H00000000,&HCC000000,"
                "-1,0,0,0,100,100,1,0,3,4,0,2,60,60,380,1"
            ),
            "is_hormozi": False,
        },
    }

    style_cfg = style_defs.get(style_name, style_defs["alex_hormozi"])

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
{style_cfg["style_line"]}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    if style_cfg.get("is_hormozi", False):
        events_str = build_hormozi_subtitles(
            transcript=transcript,
            start_sec=start_sec,
            end_sec=end_sec,
            highlight_color=style_cfg.get("highlight", "&H0000FFFF&"),
            normal_color=style_cfg.get("normal", "&H00FFFFFF&"),
        )
    else:
        # Estilos tradicionales
        events = []
        segments = transcript.get("segments", [])
        for seg in segments:
            s_start = float(seg.get("start", 0))
            s_end = float(seg.get("end", 0))
            if s_end <= start_sec or s_start >= end_sec:
                continue

            words = seg.get("words", [])
            if words:
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
                    if chunk_text:
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
        events_str = "\n".join(events)

    ass_content = header + events_str + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return out_path
