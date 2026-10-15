"""
Paso 2: Agente Especializado de Subtitulación (Subtitle Agent)
Responsabilidad:
- Recibe el clip cortado y el texto en español adaptado.
- Exige la segmentación palabra por palabra (o micro-frases de 1-3 palabras).
- Genera todo el texto en MAYÚSCULAS con timestamps precisos sincronizados en milisegundos.
- Aplica resaltado dinámico de palabras clave (dinero, viral, secreto, atención, etc.) y emojis de alto impacto.
- Genera el archivo de subtítulos ASS (Advanced SubStation Alpha) optimizado con safe zones verticales.
- Devuelve la estructura en formato JSON.
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List
from backend.subtitles import (
    generate_ass_subtitles_file,
    detect_contextual_emoji,
    format_ass_time,
    clean_subtitle_text,
    EMOJI_PATTERNS
)
from backend.agents.translator import translate_to_spanish, is_text_spanish

logger = logging.getLogger("clipai.agents.subtitles")

KEYWORD_BOOST = [
    "SECRETO", "TRUCO", "HACK", "NUNCA", "JAMÁS", "SIEMPRE", "INCREÍBLE", "IMPOSIBLE",
    "DINERO", "MILLONES", "ERROR", "CUIDADO", "MIRA", "ATENCIÓN", "PODER", "ÉXITO",
    "BRUTAL", "GRATIS", "FÁCIL", "RÁPIDO", "RESULTADO", "URGENTE", "FUEGO", "BOOM"
]


class SubtitleAgent:
    def __init__(self, style_name: str = "alex_hormozi"):
        self.style_name = style_name

    def process(self, clip_data: Dict[str, Any], transcript_segments: List[Dict[str, Any]], out_dir: Path) -> Dict[str, Any]:
        """
        Genera subtítulos dinámicos de 1-3 palabras en MAYÚSCULAS con safe zones.
        Retorna JSON estructurado y el archivo ASS generado.
        """
        clip_index = clip_data.get("clip_index", 1)
        start_time = float(clip_data["start_time"])
        end_time = float(clip_data["end_time"])
        text_spanish = clip_data.get("text_spanish", "").strip()

        # Validación estricta de idioma
        if not is_text_spanish(text_spanish):
            logger.info("[SubtitleAgent] Texto no español detectado. Traduciendo al español...")
            text_spanish = translate_to_spanish(text_spanish)

        # Generar micro-segmentos de 1 a 3 palabras
        words = text_spanish.split()
        total_duration = max(1.0, end_time - start_time)
        word_duration = total_duration / max(len(words), 1)

        subtitle_tokens = []
        i = 0
        chunk_size = 2  # 1-3 palabras por pantalla (estilo Hormozi)

        while i < len(words):
            chunk = words[i:i + chunk_size]
            chunk_text = " ".join(chunk).upper()
            chunk_start = start_time + (i * word_duration)
            chunk_end = min(end_time, chunk_start + (len(chunk) * word_duration))

            is_kw = any(kw in chunk_text for kw in KEYWORD_BOOST)
            emoji = detect_contextual_emoji(chunk_text)

            subtitle_tokens.append({
                "index": len(subtitle_tokens) + 1,
                "text_uppercase": chunk_text,
                "start_ms": int(round((chunk_start - start_time) * 1000)),
                "end_ms": int(round((chunk_end - start_time) * 1000)),
                "start_formatted": format_ass_time(max(0.0, chunk_start - start_time)),
                "end_formatted": format_ass_time(max(0.0, chunk_end - start_time)),
                "is_keyword_highlight": is_kw,
                "emoji": emoji,
            })
            i += len(chunk)

        # Escribir archivo ASS para FFmpeg
        ass_path = out_dir / f"clip_{clip_index}_subtitles.ass"
        
        # Mapeo de transcript adaptado en español
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

        return {
            "status": "success",
            "agent": "SubtitleAgent",
            "clip_index": clip_index,
            "style": self.style_name,
            "language": "es",
            "tokens_count": len(subtitle_tokens),
            "ass_file_path": str(ass_path),
            "sample_tokens": subtitle_tokens[:5],
            "all_tokens": subtitle_tokens,
        }
