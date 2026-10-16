"""
Paso 2: Agente Experto en Sincronización y Retención Visual (Subtitle Agent)
Responsabilidad:
- Recibe el clip cortado y la transcripción adaptada/traducida al español.
- Segmentación estricta: Bloques micro-chunk de 1 a 3 palabras por pantalla.
- Precisión milimétrica: Timestamps sincronizados en milisegundos (start_time y end_time).
- Énfasis de Retención: Todo en MAYÚSCULAS con resaltado dinámico de palabras clave usando etiquetas de color.
- Exportación dual:
  1. Lista JSON pura con objetos {start_time, end_time, text}.
  2. Archivo ASS (Advanced SubStation Alpha) de alta resolución con safe zones para TikTok/Shorts.
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.subtitles import (
    generate_ass_subtitles_file,
    detect_contextual_emoji,
    format_ass_time,
    clean_subtitle_text,
    EMOJI_PATTERNS
)
from backend.agents.translator import translate_to_spanish, is_text_spanish

logger = logging.getLogger("clipai.agents.subtitles")

# Paleta cromática de alta retención visual (Estilo Hormozi & MrBeast)
COLOR_PALETTE = {
    "yellow": "#FFE600",    # Oro / Amarillo Eléctrico: Éxito, Valor, Clave
    "green": "#00FF66",     # Verde Neón: Dinero, Ganancias, Rápido, Fácil
    "red": "#FF2E54",       # Rojo Fuego: Errores, Peligro, Jamás, Nunca, Prohibido
    "cyan": "#00E5FF",      # Cyan Neón: Secretos, Hacks, Futuro, Tecnología
    "white": "#FFFFFF",     # Blanco puro: Texto base
}

# Diccionario temático para asignación de color por palabra clave
KEYWORD_COLOR_MAP = {
    # Verde (Finanzas, Dinero, Ganancia)
    "DINERO": COLOR_PALETTE["green"],
    "DÓLARES": COLOR_PALETTE["green"],
    "DOLARES": COLOR_PALETTE["green"],
    "MILLONES": COLOR_PALETTE["green"],
    "FACTURACIÓN": COLOR_PALETTE["green"],
    "FACTURACION": COLOR_PALETTE["green"],
    "GANANCIAS": COLOR_PALETTE["green"],
    "INGRESOS": COLOR_PALETTE["green"],
    "GRATIS": COLOR_PALETTE["green"],
    "RIQUEZA": COLOR_PALETTE["green"],

    # Rojo (Urgencia, Advertencia, Shock)
    "ERROR": COLOR_PALETTE["red"],
    "ERRORES": COLOR_PALETTE["red"],
    "NUNCA": COLOR_PALETTE["red"],
    "JAMÁS": COLOR_PALETTE["red"],
    "JAMAS": COLOR_PALETTE["red"],
    "PELIGRO": COLOR_PALETTE["red"],
    "CUIDADO": COLOR_PALETTE["red"],
    "FRACASO": COLOR_PALETTE["red"],
    "TRAMPA": COLOR_PALETTE["red"],
    "URGENTE": COLOR_PALETTE["red"],

    # Cyan (Hacks, Secretos, Métodos)
    "SECRETO": COLOR_PALETTE["cyan"],
    "TRUCO": COLOR_PALETTE["cyan"],
    "HACK": COLOR_PALETTE["cyan"],
    "MÉTODO": COLOR_PALETTE["cyan"],
    "ESTRATEGIA": COLOR_PALETTE["cyan"],
    "FUTURO": COLOR_PALETTE["cyan"],
    "CLAVE": COLOR_PALETTE["cyan"],
    "FÓRMULA": COLOR_PALETTE["cyan"],

    # Amarillo (Poder, Impacto, Foco)
    "INCREÍBLE": COLOR_PALETTE["yellow"],
    "INCREIBLE": COLOR_PALETTE["yellow"],
    "IMPRESIONANTE": COLOR_PALETTE["yellow"],
    "BRUTAL": COLOR_PALETTE["yellow"],
    "ÉXITO": COLOR_PALETTE["yellow"],
    "EXITO": COLOR_PALETTE["yellow"],
    "MIRA": COLOR_PALETTE["yellow"],
    "ATENCIÓN": COLOR_PALETTE["yellow"],
    "ATENCION": COLOR_PALETTE["yellow"],
    "CAMBIÓ": COLOR_PALETTE["yellow"],
    "CAMBIO": COLOR_PALETTE["yellow"],
    "PODER": COLOR_PALETTE["yellow"],
    "GOL": COLOR_PALETTE["yellow"],
    "CAMPEÓN": COLOR_PALETTE["yellow"],
}


class SubtitleAgent:
    def __init__(self, style_name: str = "alex_hormozi"):
        self.style_name = style_name

    def highlight_word_in_text(self, word: str) -> tuple[str, bool, Optional[str]]:
        """Aplica etiqueta de color HTML al término si coincide con una palabra clave."""
        clean_w = re.sub(r'[^\wÁÉÍÓÚÜÑáéíóúüñ]', '', word).upper()
        if clean_w in KEYWORD_COLOR_MAP:
            color = KEYWORD_COLOR_MAP[clean_w]
            # Conservar puntuación inicial y final (ej: ¿ ¡ . , ! ?)
            m = re.match(r'^([^\wÁÉÍÓÚÜÑáéíóúüñ]*)([\wÁÉÍÓÚÜÑáéíóúüñ]+)([^\wÁÉÍÓÚÜÑáéíóúüñ]*)$', word)
            if m:
                prefix, core, suffix = m.groups()
                tagged = f'{prefix}<font color="{color}">{core.upper()}</font>{suffix}'
            else:
                tagged = f'<font color="{color}">{clean_w}</font>'
            return tagged, True, color
        return word.upper(), False, None

    def segment_transcript_to_micro_chunks(
        self,
        text_spanish: str,
        start_time: float,
        end_time: float,
        whisper_words: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Segmenta el texto en micro-bloques de 1 a 3 palabras con sincronización exacta en milisegundos.
        Aplica formato MAYÚSCULAS y resaltado de palabras clave con etiquetas de color.
        """
        # Normalizar texto en español
        text_clean = text_spanish.strip()
        words = text_clean.split()
        if not words:
            return []

        total_duration = max(0.8, end_time - start_time)
        
        chunks = []
        i = 0
        n_words = len(words)

        # Si tenemos palabras con timestamps reales de Whisper
        if whisper_words and len(whisper_words) >= n_words * 0.7:
            while i < len(whisper_words):
                # Tomar de 1 a 3 palabras según el ritmo y puntuación
                take = 2
                w_current = whisper_words[i].get("word", "").strip()
                if any(w_current.endswith(p) for p in [".", "!", "?", ","]):
                    take = 1
                elif i + 2 < len(whisper_words):
                    take = 2

                chunk_slice = whisper_words[i:i + take]
                c_start = float(chunk_slice[0].get("start", start_time))
                c_end = float(chunk_slice[-1].get("end", c_start + 0.6))
                
                # Formatear palabras del chunk
                rendered_words = []
                has_highlight = False
                color_used = None

                for w_obj in chunk_slice:
                    raw_w = w_obj.get("word", "").strip()
                    tagged_w, hl, col = self.highlight_word_in_text(raw_w)
                    rendered_words.append(tagged_w)
                    if hl:
                        has_highlight = True
                        color_used = col

                chunk_text = " ".join(rendered_words)
                chunks.append({
                    "start_time": round(c_start, 3),
                    "end_time": round(c_end, 3),
                    "text": chunk_text,
                    "plain_text": " ".join(w.get("word", "").strip().upper() for w in chunk_slice),
                    "highlight": has_highlight,
                    "color": color_used or COLOR_PALETTE["white"]
                })
                i += take
        else:
            # Algoritmo de cadencia por micro-bloques (1 a 3 palabras)
            avg_word_dur = total_duration / float(n_words)
            while i < n_words:
                take = 2
                current_word = words[i]
                if any(current_word.endswith(p) for p in [".", "!", "?", ","]):
                    take = 1
                elif i + 2 < n_words and len(words[i + 1]) <= 3:
                    take = 3

                chunk_words = words[i:i + take]
                c_start = start_time + (i * avg_word_dur)
                c_end = min(end_time, c_start + (len(chunk_words) * avg_word_dur))

                # Resaltado en mayúsculas con color
                rendered_words = []
                has_highlight = False
                color_used = None

                for w in chunk_words:
                    tagged_w, hl, col = self.highlight_word_in_text(w)
                    rendered_words.append(tagged_w)
                    if hl:
                        has_highlight = True
                        color_used = col

                chunk_text = " ".join(rendered_words)
                chunks.append({
                    "start_time": round(c_start, 3),
                    "end_time": round(c_end, 3),
                    "text": chunk_text,
                    "plain_text": " ".join(w.upper() for w in chunk_words),
                    "highlight": has_highlight,
                    "color": color_used or COLOR_PALETTE["white"]
                })
                i += take

        return chunks

    def process(
        self,
        clip_data: Dict[str, Any],
        transcript_segments: List[Dict[str, Any]],
        out_dir: Path
    ) -> Dict[str, Any]:
        """
        Punto de entrada principal del Agente de Subtitulación:
        - Segmentación de 1 a 3 palabras.
        - MAYÚSCULAS absolutas con sincronización exacta en milisegundos.
        - Etiquetas de color para retención visual.
        - Estructura JSON y archivo ASS generado.
        """
        clip_index = clip_data.get("clip_index", 1)
        start_time = float(clip_data["start_time"])
        end_time = float(clip_data["end_time"])
        text_spanish = clip_data.get("text_spanish", "").strip()

        # Validación estricta de idioma
        if not is_text_spanish(text_spanish):
            logger.info("[SubtitleAgent] Texto no español detectado. Traduciendo al español...")
            text_spanish = translate_to_spanish(text_spanish)

        # Extraer palabras individuales de los segmentos si existen
        whisper_words = []
        for s in transcript_segments:
            s_start = float(s.get("start", 0))
            s_end = float(s.get("end", 0))
            if s_end >= start_time and s_start <= end_time:
                for w in s.get("words", []):
                    w_start = float(w.get("start", s_start))
                    if start_time <= w_start <= end_time:
                        whisper_words.append(w)

        # Generar micro-segmentos con precisión en milisegundos y etiquetas de color
        json_subtitles = self.segment_transcript_to_micro_chunks(
            text_spanish=text_spanish,
            start_time=start_time,
            end_time=end_time,
            whisper_words=whisper_words if whisper_words else None
        )

        # Generar tokens compatibles con ASS y FFmpeg
        subtitle_tokens = []
        for idx, sub in enumerate(json_subtitles):
            clean_token_text = sub["plain_text"]
            emoji = detect_contextual_emoji(clean_token_text)
            subtitle_tokens.append({
                "index": idx + 1,
                "text_uppercase": clean_token_text,
                "text_tagged": sub["text"],
                "start_ms": int(round((sub["start_time"] - start_time) * 1000)),
                "end_ms": int(round((sub["end_time"] - start_time) * 1000)),
                "start_formatted": format_ass_time(max(0.0, sub["start_time"] - start_time)),
                "end_formatted": format_ass_time(max(0.0, sub["end_time"] - start_time)),
                "is_keyword_highlight": sub["highlight"],
                "color_tag": sub["color"],
                "emoji": emoji,
            })

        # Generar archivo ASS para quemado con FFmpeg
        ass_path = out_dir / f"clip_{clip_index}_subtitles.ass"
        adapted_transcript = {
            "segments": [{
                "start": start_time,
                "end": end_time,
                "text": text_spanish,
                "words": [
                    {
                        "word": t["text_uppercase"],
                        "start": start_time + (t["start_ms"] / 1000.0),
                        "end": start_time + (t["end_ms"] / 1000.0),
                    }
                    for t in subtitle_tokens
                ]
            }]
        }

        generate_ass_subtitles_file(
            transcript=adapted_transcript,
            start_sec=start_time,
            end_sec=end_time,
            out_path=ass_path,
            style_name=self.style_name
        )

        # Formato JSON puro solicitado
        pure_subtitles_json = [
            {
                "start_time": sub["start_time"],
                "end_time": sub["end_time"],
                "text": sub["text"]
            }
            for sub in json_subtitles
        ]

        return {
            "status": "success",
            "agent": "SubtitleAndVisualRetentionAgent",
            "clip_index": clip_index,
            "style": self.style_name,
            "language": "es",
            "subtitles_count": len(json_subtitles),
            "subtitles": pure_subtitles_json,
            "ass_file_path": str(ass_path),
            "all_tokens": subtitle_tokens,
        }
