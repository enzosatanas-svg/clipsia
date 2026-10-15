"""
Paso 4: Agente Especializado de SEO y Marketing Viral (SeoMarketingAgent)
Responsabilidad:
- Genera la estrategia completa de publicación para TikTok, Shorts e Instagram Reels.
- 3 opciones de hooks de pantalla para los primeros 3 segundos (alta curiosidad y retención).
- Descripción optimizada para retención, intriga y apertura de debate en comentarios.
- Llamada a la acción (CTA) directa y contundente.
- 5 a 8 hashtags virales seleccionados y optimizados.
- REGLA ABSOLUTA: Toda la salida DEBE estar 100% en ESPAÑOL.
"""
import re
import logging
from typing import Dict, Any, List
from backend.agents.translator import translate_to_spanish, is_text_spanish

logger = logging.getLogger("clipai.agents.seo")

EMOJIS_LIST = ["🔥", "👀", "🧠", "⚡", "🚀", "💰", "😱", "👇", "💥"]


class SeoMarketingAgent:
    def __init__(self):
        pass

    def process(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce el paquete completo de SEO y Copywriting en español.
        Retorna JSON estructurado.
        """
        text_es = clip_data.get("text_spanish", "")
        if not is_text_spanish(text_es):
            text_es = translate_to_spanish(text_es)

        # Generar 3 opciones de hooks para pantalla en ESPAÑOL
        t_clean = re.sub(r'[^\w\s]', '', text_es).strip()
        words = t_clean.split()
        short_snippet = " ".join(words[:8]) if words else "este momento"

        hooks_options = [
            f"🔥 ¿El secreto que nadie te cuenta sobre {short_snippet.lower()}?",
            f"👀 Mira lo que pasa cuando descubres esto...",
            f"🚨 El error número 1 que estás cometiendo ahora mismo",
        ]

        # Asegurar que los hooks estén en español
        hooks_options = [h if is_text_spanish(h) else translate_to_spanish(h) for h in hooks_options]

        # Descripción optimizada para retención y debate en comentarios
        description = (
            f"Lo que revela este video cambia por completo la perspectiva sobre este tema. "
            f"Muchos ignoran el impacto real que tiene hasta que es demasiado tarde.\n\n"
            f"👇 ¿Estás de acuerdo con esto o piensas diferente? Déjalo abajo en los comentarios."
        )

        # Llamada a la acción (CTA) directa
        cta = "¡Comenta tu opinión abajo y sígueme para no perderte el próximo análisis!"

        # 5 a 8 Hashtags virales en español
        hashtags = [
            "#shorts",
            "#viral",
            "#parati",
            "#reels",
            "#tiktok",
            "#crecimientopersonal",
            "#aprendeentiktok",
            "#tendencia"
        ]

        # Copy completo consolidado listo para publicar
        full_copy = (
            f"{hooks_options[0]}\n\n"
            f"{description}\n\n"
            f"{cta}\n\n"
            f"{' '.join(hashtags)}"
        )

        return {
            "status": "success",
            "agent": "SeoMarketingAgent",
            "language": "es",
            "hook_screen_options": hooks_options,
            "selected_hook": hooks_options[0],
            "description": description,
            "call_to_action": cta,
            "hashtags": hashtags,
            "hashtags_count": len(hashtags),
            "ready_to_publish_copy": full_copy,
        }
