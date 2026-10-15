"""
Paso 1: Agente Especializado de Corte (Cutting Agent)
Responsabilidad:
- Analiza la transcripción completa del video fuente.
- Identifica los momentos más virales y de mayor retención (highlights de 30-60 segundos).
- Establece marcas de tiempo exactas (start_time / end_time).
- REGLA ABSOLUTA DE IDIOMA: Adapta y traduce el contenido al ESPAÑOL si proviene de otro idioma.
- Devuelve la respuesta en formato JSON estructurado y validado.
"""
import logging
from typing import Dict, Any, List
from backend.routers import process
from backend.agents.translator import translate_to_spanish, is_text_spanish

logger = logging.getLogger("clipai.agents.cutting")


class CuttingAgent:
    def __init__(self, target_duration_range=(25, 60)):
        self.target_min, self.target_max = target_duration_range

    def process(self, transcript_data: Dict[str, Any], max_clips: int = 3) -> Dict[str, Any]:
        """
        Analiza la transcripción y extrae los mejores fragmentos virales en español.
        Retorna JSON estructurado.
        """
        segments = transcript_data.get("segments", [])
        source_lang = transcript_data.get("language", "auto")

        if not segments:
            raise ValueError("La transcripción no contiene segmentos de voz válidos.")

        # Obtener candidatos mediante motor heurístico de retención
        raw_candidates = process.find_viral_segments_local(transcript_data, n=max_clips * 2)
        if not raw_candidates:
            # Fallback a chunks directos de 30-45s
            start_t = 0.0
            end_t = min(40.0, float(segments[-1].get("end", 40.0)))
            text_acc = " ".join([s.get("text", "") for s in segments if float(s.get("start", 0)) < 40.0])
            raw_candidates = [{
                "start": start_t,
                "end": end_t,
                "duration": round(end_t - start_t, 2),
                "text": text_acc,
                "score": 8.0,
            }]

        selected_clips = []
        for idx, cand in enumerate(raw_candidates[:max_clips]):
            raw_text = cand["text"].strip()
            
            # TRADUCCIÓN OBLIGATORIA AL ESPAÑOL SI NO ES ESPAÑOL
            if not is_text_spanish(raw_text) or (source_lang and not source_lang.startswith("es")):
                logger.info(f"[CuttingAgent] Traduciendo fragmento #{idx+1} al español...")
                text_es = translate_to_spanish(raw_text, source_lang)
            else:
                text_es = raw_text

            # Asegurar duración estricta 30-60s
            duration = cand["duration"]
            if duration < self.target_min:
                duration = self.target_min
            elif duration > self.target_max:
                duration = self.target_max

            clip_item = {
                "clip_index": idx + 1,
                "start_time": round(float(cand["start"]), 2),
                "end_time": round(float(cand["start"]) + duration, 2),
                "duration_seconds": round(duration, 2),
                "original_text": raw_text,
                "text_spanish": text_es,
                "viral_score": round(float(cand.get("score", 8.0)), 1),
            }
            selected_clips.append(clip_item)

        result_payload = {
            "status": "success",
            "agent": "CuttingAgent",
            "source_language_detected": source_lang,
            "clips_count": len(selected_clips),
            "clips": selected_clips,
        }
        return result_payload
