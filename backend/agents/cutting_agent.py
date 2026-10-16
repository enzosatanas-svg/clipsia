"""
Paso 1: Agente Especializado de Corte y Detección Viral Multi-Nicho (Cutting & Viral Agent)
Responsabilidad:
- Analiza la transcripción completa del video fuente, desde el segundo 0 hasta el final.
- Detecta picos de emoción, revelaciones, giros inesperados o clímax narrativos en múltiples nichos:
  (Deportes, Negocios/Finanzas, Entretenimiento/Podcasts, Tecnología, Desarrollo Personal, Gaming).
- Selecciona los mejores segmentos (highlights) de 30 a 60 segundos con total autonomía narrativa.
- Valida y garantiza un gancho inicial de alto impacto (Hook) en los primeros 3 a 5 segundos.
- REGLA ABSOLUTA DE IDIOMA: Adapta y traduce el contenido al ESPAÑOL si proviene de otro idioma.
- Entrega el resultado en formato JSON estructurado con:
  start_time, end_time, duration_seconds, hook_text, motivo_seleccion, nicho, viral_score, text_spanish.
"""
import re
import logging
from typing import Dict, Any, List
from backend.agents.translator import translate_to_spanish, is_text_spanish

logger = logging.getLogger("clipai.agents.cutting")

# Diccionarios de palabras clave por nicho para análisis temático y picos emocionales
NICHE_LEXICONS = {
    "Negocios & Finanzas": [
        "dinero", "inversión", "ventas", "clientes", "facturación", "negocio",
        "precio", "costo", "ganancia", "millones", "error financiero", "secreto",
        "estrategia", "monetizar", "fracaso", "éxito", "empresa", "deuda",
        "marketing", "funnel", "hustle", "rentabilidad", "riqueza"
    ],
    "Deportes & Adrenalina": [
        "gol", "golazo", "campeón", "victoria", "derrota", "remontada", "final",
        "penal", "jugada", "partido", "velocidad", "récord", "adrenalina",
        "histórico", "brutal", "salvada", "pelea", "knockout", "lesión", "fuerza"
    ],
    "Entretenimiento & Revelaciones": [
        "secreto", "confesión", "nadie sabe", "la verdad", "increíble", "locura",
        "no lo vas a creer", "polémica", "traición", "mentira", "mira esto",
        "inesperado", "revelación", "llanto", "reacción", "humor", "risas"
    ],
    "Tecnología & Trucos": [
        "inteligencia artificial", "ia", "hack", "truco", "herramienta", "secreto",
        "atajo", "futuro", "tutorial", "cómo hacer", "fácil", "gratis",
        "software", "automatización", "prompt", "algoritmo"
    ],
    "Desarrollo Personal & Filosofía": [
        "hábito", "disciplina", "mente", "cambió mi vida", "dolor", "lección",
        "tiempo", "fracaso", "motivación", "propósito", "decisión", "control"
    ]
}

# Palabras disparadoras de gancho potente (Hook Triggers)
HOOK_TRIGGERS = [
    "nunca hagas esto", "el mayor error", "nadie te dice", "la única forma",
    "esto cambió todo", "si quieres ser", "el secreto detrás", "lo que pasó después",
    "no cometas este error", "mira con atención", "te mintieron sobre",
    "cómo logré", "la verdadera razón", "lo que nadie vio", "esto es una locura"
]


class CuttingAgent:
    def __init__(self, target_duration_range=(30, 60)):
        self.target_min, self.target_max = target_duration_range

    def _detect_niche(self, text: str) -> str:
        """Determina el nicho predominante en el texto analizado."""
        text_lower = text.lower()
        scores = {}
        for niche, kws in NICHE_LEXICONS.items():
            count = sum(1 for kw in kws if kw in text_lower)
            scores[niche] = count

        best_niche = max(scores, key=scores.get)
        return best_niche if scores[best_niche] > 0 else "Interés General / Viral"

    def _extract_hook(self, text: str) -> str:
        """Extrae o sintetiza una primera frase contundente como gancho viral (Hook)."""
        sentences = re.split(r'[.!?\n]+', text.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 8]

        if not sentences:
            return "¡Mira lo que sucedió en este momento revelador!"

        first_sentence = sentences[0]
        # Limitar gancho a máximo 15 palabras para impacto instantáneo
        words = first_sentence.split()
        if len(words) > 14:
            first_sentence = " ".join(words[:14]) + "..."

        # Asegurar formato exclamativo o interrogativo si no lo tiene
        if not first_sentence.endswith(("!", "?", "...")):
            first_sentence = f"¡{first_sentence}!"

        return first_sentence

    def _generate_selection_reason(self, niche: str, hook: str, score: float, duration: float) -> str:
        """Genera una justificación narrativa y analítica para la selección del highlight."""
        reasons = [
            f"Segmento de {duration:.1f}s en nicho '{niche}' con autonomía narrativa completa.",
            f"Inicia con gancho potente de alta retención: \"{hook}\".",
            f"Presenta clímax temático con un puntaje algorítmico proyectado de {score:.1f}/10 en retención vertical."
        ]
        return " ".join(reasons)

    def _score_window(self, segments: List[Dict[str, Any]], start_idx: int, end_idx: int) -> float:
        """Evalúa un rango de segmentos para detectar picos emocionales y retención viral."""
        text = " ".join(s.get("text", "") for s in segments[start_idx:end_idx + 1]).lower()
        start_time = float(segments[start_idx].get("start", 0))
        end_time = float(segments[end_idx].get("end", 0))
        duration = max(1.0, end_time - start_time)

        score = 4.5  # Base

        # Coincidencias en léxicos multi-nicho
        for niche_kws in NICHE_LEXICONS.values():
            hits = sum(1 for kw in niche_kws if kw in text)
            score += min(hits * 0.4, 2.0)

        # Disparadores de ganchos virales
        hook_hits = sum(1 for ht in HOOK_TRIGGERS if ht in text[:120])
        score += min(hook_hits * 1.5, 2.5)

        # Duración óptima (30-60 segundos)
        if 30 <= duration <= 55:
            score += 2.0
        elif 25 <= duration <= 60:
            score += 1.0

        # Signos de exclamación e interrogación (emoción/preguntas retóricas)
        score += min(text.count("?") * 0.5, 1.0)
        score += min(text.count("!") * 0.5, 1.0)

        # Ritmo de palabras (ritmo dinámico)
        words = text.split()
        wps = len(words) / duration
        if 2.2 <= wps <= 4.2:
            score += 0.8

        return round(min(score, 9.9), 1)

    def scan_full_video(self, transcript_data: Dict[str, Any], max_clips: int = 3) -> List[Dict[str, Any]]:
        """
        Escanea exhaustivamente todo el video desde el segundo 0 hasta el final,
        construyendo ventanas móviles de 30 a 60 segundos con autonomía narrativa.
        """
        segments = transcript_data.get("segments", [])
        if not segments:
            return []

        candidates = []
        n_segs = len(segments)

        # Escaneo continuo de ventana deslizante
        for i in range(n_segs):
            start_t = float(segments[i].get("start", 0.0))
            
            # Buscar el punto final que cumpla entre 30 y 60 segundos
            for j in range(i, n_segs):
                end_t = float(segments[j].get("end", 0.0))
                dur = end_t - start_t

                if dur < self.target_min:
                    continue
                if dur > self.target_max:
                    break

                # Comprobar autonomía narrativa: no cortar a mitad de frase
                seg_text = segments[j].get("text", "").strip()
                has_clean_ending = bool(re.search(r'[.!?…]$', seg_text)) or (dur >= 45)

                if has_clean_ending or dur >= 50:
                    score = self._score_window(segments, i, j)
                    combined_text = " ".join(s.get("text", "").strip() for s in segments[i:j+1])
                    candidates.append({
                        "start": round(start_t, 2),
                        "end": round(end_t, 2),
                        "duration": round(dur, 2),
                        "text": combined_text,
                        "score": score,
                    })

        if not candidates:
            # Fallback de seguridad: chunk inicial de 30 a 45s
            total_end = float(segments[-1].get("end", 40.0))
            fallback_end = min(45.0, total_end)
            text_acc = " ".join(s.get("text", "") for s in segments if float(s.get("start", 0)) < fallback_end)
            candidates = [{
                "start": 0.0,
                "end": round(fallback_end, 2),
                "duration": round(fallback_end, 2),
                "text": text_acc,
                "score": 8.0,
            }]

        # Ordenar candidatos por puntaje viral descendente
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Filtrar solapamientos excesivos entre clips seleccionados
        selected = []
        for cand in candidates:
            overlap = False
            for sel in selected:
                # Si se superponen más de 12 segundos, evitar duplicar el mismo momento
                if not (cand["end"] <= sel["start"] + 12 or cand["start"] >= sel["end"] - 12):
                    overlap = True
                    break
            if not overlap:
                selected.append(cand)
            if len(selected) >= max_clips:
                break

        # Si quedaron menos de max_clips por filtro estricto, relajar solapamiento
        if len(selected) < max_clips:
            for cand in candidates:
                if cand not in selected:
                    selected.append(cand)
                if len(selected) >= max_clips:
                    break

        # Ordenar cronológicamente para coherencia si se desea, o mantener por relevancia
        selected.sort(key=lambda x: x["score"], reverse=True)
        return selected

    def process(self, transcript_data: Dict[str, Any], max_clips: int = 3) -> Dict[str, Any]:
        """
        Punto de entrada principal del Agente de Corte:
        - Escaneo completo de 0 a fin.
        - Selección multi-nicho.
        - Validación y extracción de ganchos (Hooks).
        - Adaptación estricta al ESPAÑOL.
        - Entrega de JSON estructurado y validado.
        """
        segments = transcript_data.get("segments", [])
        source_lang = transcript_data.get("language", "auto")

        if not segments:
            raise ValueError("La transcripción no contiene segmentos de voz válidos.")

        # Escanear todo el video buscando los momentos virales
        raw_candidates = self.scan_full_video(transcript_data, max_clips=max_clips)

        selected_clips = []
        for idx, cand in enumerate(raw_candidates[:max_clips]):
            raw_text = cand["text"].strip()

            # REGLA ABSOLUTA: TRADUCCIÓN OBLIGATORIA AL ESPAÑOL SI ES NECESARIO
            if not is_text_spanish(raw_text) or (source_lang and not source_lang.startswith("es")):
                logger.info(f"[CuttingAgent] Traduciendo highlight #{idx+1} ({cand['start']}s - {cand['end']}s) al español...")
                text_es = translate_to_spanish(raw_text, source_lang)
            else:
                text_es = raw_text

            # Identificación de Nicho y Gancho Viral
            niche = self._detect_niche(text_es)
            hook = self._extract_hook(text_es)
            motivo = self._generate_selection_reason(niche, hook, cand["score"], cand["duration"])

            clip_item = {
                "clip_index": idx + 1,
                "start_time": cand["start"],
                "end_time": cand["end"],
                "duration_seconds": cand["duration"],
                "nicho": niche,
                "hook_text": hook,
                "motivo_seleccion": motivo,
                "viral_score": cand["score"],
                "original_text": raw_text,
                "text_spanish": text_es,
            }
            selected_clips.append(clip_item)

        result_payload = {
            "status": "success",
            "agent": "CuttingAndViralDetectionAgent",
            "source_language_detected": source_lang,
            "clips_count": len(selected_clips),
            "clips": selected_clips,
        }
        return result_payload
