"""
Rol: Agente experto en SEO, Copywriting de Alta Retención y Estrategia de Publicación Multi-Plataforma.

Objetivo:
Transformar cada clip detectado en un paquete de publicación viral de alto impacto,
con ganchos psicológicos de pantalla para los primeros 3 segundos, descripciones
diseñadas para retención y debate en comentarios, llamadas a la acción (CTA) y
hashtags algorítmicos balanceados, 100% adaptado al ESPAÑOL.

Instrucciones:
1. Ganchos de Pantalla Psicológicos (Hooks):
   - Mínimo 3 opciones diferenciadas por disparador psicológico:
     a) Pattern Interrupt (Ruptura de patrón / Shock)
     b) Curiosity Gap / Bucle Abierto (Intriga irresistible)
     c) Sesgo Negativo / Prevención de Error Fatal (FOMO / Alerta)
2. Copywriting de Alta Conversión y Retención:
   - Primeras dos líneas ultra-magnéticas antes del botón 'ver más'.
   - Narrativa concisa que abre debate en comentarios para forzar interacciones.
3. Adaptación Multi-Plataforma:
   - TikTok: Ritmo ágil, llamada a comentar, emojis y tags de tendencia.
   - Instagram Reels: Micro-historia persuasiva, llamada a guardar (Save) o compartir.
   - YouTube Shorts: Título con palabras clave SEO de búsqueda y alto CTR.
4. Estrategia Algorítmica de Hashtags:
   - Entre 5 y 8 hashtags distribuidos entre tendencia, nicho específico y keywords SEO.
5. Regla Absoluta de Idioma:
   - Toda la salida DEBE estar 100% en ESPAÑOL neutro y fluido.
6. Formato JSON Estructurado para el Director de Orquesta.
"""
import re
import random
import logging
from typing import Dict, Any, List, Optional
from backend.agents.translator import translate_to_spanish, is_text_spanish

logger = logging.getLogger("clipai.agents.seo")

# Hashtags curados y balanceados por nicho temático (100% en español)
NICHE_HASHTAGS = {
    "Negocios & Finanzas": [
        "#negocios", "#finanzaspersonales", "#inversiones", "#emprendimiento",
        "#mentalidadmillonaria", "#crecimientofinanciero", "#estrategias"
    ],
    "Deportes & Adrenalina": [
        "#deportes", "#futbol", "#motivaciondeportiva", "#entrenamiento",
        "#jugadasincreibles", "#adrenalina", "#pasiondeportiva"
    ],
    "Entretenimiento & Revelaciones": [
        "#revelaciones", "#historiasreales", "#podcastclips", "#curiosidades",
        "#momentoincreible", "#polemica", "#entretenimiento"
    ],
    "Tecnología & Trucos": [
        "#inteligenciaartificial", "#tecnologia", "#trucostecnologicos",
        "#herramientasdigitales", "#productividad", "#futurodigital"
    ],
    "Desarrollo Personal & Filosofía": [
        "#desarrollopersonal", "#disciplina", "#habitospositivos",
        "#mentalidadganadora", "#estoicismo", "#motivacion"
    ],
    "General": [
        "#aprendeentiktok", "#contenidoeducativo", "#viralclips",
        "#tendencias", "#inspiracion"
    ]
}

# Hashtags universales de alto alcance (Broad Reach)
BROAD_HASHTAGS = ["#shorts", "#viral", "#parati", "#reels", "#fyp"]

# Plantillas de ganchos psicológicos por categoría
HOOK_FRAMEWORKS = {
    "pattern_interrupt": [
        "🚨 Detén el scroll: nadie te va a decir esto sobre {topic}.",
        "💥 La verdad incómoda que nadie quiere admitir sobre {topic}.",
        "⚠️ Lo que estás haciendo con {topic} está arruinando tus resultados.",
        "🛑 Si piensas que {topic} funciona así, estás viviendo un engaño.",
    ],
    "curiosity_gap": [
        "👀 Mira con atención lo que pasa cuando entiendes {topic}...",
        "🧠 El 99% de las personas ignora este detalle clave sobre {topic}.",
        "🔒 Este es el secreto mejor guardado detrás de {topic}.",
        "⚡ Lo que descubrí sobre {topic} cambió mi perspectiva para siempre.",
    ],
    "negative_bias": [
        "❌ El error número uno que cometes todos los días con {topic}.",
        "😱 Lo que nunca te enseñaron sobre {topic} te está costando caro.",
        "🔥 ¿Por qué casi todos fracasan al intentar dominar {topic}?",
        "👇 El peligro invisible que pasas por alto cuando hablas de {topic}.",
    ]
}

# Llamadas a la acción (CTAs) de alta conversión
CTAS = [
    "👇 ¿Estás de acuerdo o piensas diferente? Déjame tu punto de vista en los comentarios.",
    "💾 Guarda este clip para no olvidarlo y compártelo con alguien que necesite escucharlo hoy.",
    "🚀 Sígueme si quieres dominar este tema y no perderte los próximos análisis.",
    "🔥 Comenta abajo tu experiencia con esto. ¡Leo y respondo a todos!",
]


class SeoMarketingAgent:
    """
    Agente Especializado en SEO, Copywriting y Estrategia Multi-Plataforma.
    Gobernado por la Regla Absoluta de Idioma en Español.
    """
    def __init__(self):
        pass

    def _extract_core_topic(self, text_es: str, fallback_niche: str) -> str:
        """
        Extrae un concepto clave del texto en español para insertar en los hooks.
        Prioriza sustantivos temáticos y verbos clave para frases con gancho natural.
        """
        clean = re.sub(r'[^\w\s]', '', text_es.lower())
        words = [w for w in clean.split() if len(w) > 3]

        stopwords = {
            "porque", "cuando", "donde", "quien", "desde", "hasta", "entonces",
            "primero", "segundo", "despues", "durante", "siempre", "nunca",
            "tambien", "ademas", "muchos", "pocos", "algunos", "realmente",
            "mayor", "menor", "cometes", "haces", "tienes", "puedes", "sabes",
            "quieres", "decir", "hacer", "tener", "estar", "parte", "cosas",
            "gente", "forma", "manera", "sobre", "entre", "mismo", "todos"
        }
        candidates = [w for w in words if w not in stopwords]

        # Palabras clave temáticas prioritarias
        thematic_keywords = {
            "dinero", "inversion", "inversiones", "invertir", "negocios", "negocio",
            "ventas", "finanzas", "activos", "pasivos", "deuda", "ganancias",
            "exito", "fracaso", "disciplina", "habitos", "estrategia", "mentalidad",
            "tecnologia", "algoritmo", "herramientas", "tiempo", "crecimiento"
        }
        matched = [w for w in candidates if w in thematic_keywords]

        if len(matched) >= 2:
            return f"{matched[0]} y {matched[1]}"
        elif len(matched) == 1:
            return matched[0]
        elif len(candidates) >= 2:
            return f"{candidates[0]} y {candidates[1]}"
        elif candidates:
            return candidates[0]
        else:
            return fallback_niche.lower()

    def _detect_niche(self, text_es: str, given_niche: Optional[str] = None) -> str:
        """Determina el nicho temático prioritario para hashtags y tono."""
        if given_niche and given_niche in NICHE_HASHTAGS:
            return given_niche

        text_lower = text_es.lower()
        if any(k in text_lower for k in ["dinero", "inversion", "empresa", "ventas", "negocio", "precio", "ganancia"]):
            return "Negocios & Finanzas"
        elif any(k in text_lower for k in ["gol", "partido", "jugador", "campeon", "victoria", "deporte", "pelea"]):
            return "Deportes & Adrenalina"
        elif any(k in text_lower for k in ["ia", "inteligencia artificial", "software", "tecnologia", "truco", "hack"]):
            return "Tecnología & Trucos"
        elif any(k in text_lower for k in ["mente", "habito", "disciplina", "vida", "exito", "fracaso", "dolor"]):
            return "Desarrollo Personal & Filosofía"
        elif any(k in text_lower for k in ["secreto", "confesion", "nadie sabe", "verdad", "locura", "polemica"]):
            return "Entretenimiento & Revelaciones"
        return "General"

    def _select_balanced_hashtags(self, niche: str) -> List[str]:
        """
        Garantiza entre 5 y 8 hashtags balanceados:
        - 2 hashtags universales de alto volumen (#shorts, #parati, #reels)
        - 3 a 4 hashtags especializados del nicho
        - 1 hashtag de keyword/educativo
        """
        broad = random.sample(BROAD_HASHTAGS, 2)
        niche_pool = NICHE_HASHTAGS.get(niche, NICHE_HASHTAGS["General"])
        niche_selected = random.sample(niche_pool, min(4, len(niche_pool)))

        combined = list(dict.fromkeys(broad + niche_selected))
        if len(combined) < 5:
            combined.append("#aprendeentiktok")
        return combined[:7]

    def process(self, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de SEO, Copywriting y Estrategia Viral.
        Retorna contrato JSON rigurosamente validado en ESPAÑOL.
        """
        # 1. Normalización y validación de texto en español
        text_es = clip_data.get("text_spanish") or clip_data.get("text") or ""
        if not is_text_spanish(text_es):
            text_es = translate_to_spanish(text_es)

        niche = self._detect_niche(text_es, clip_data.get("nicho") or clip_data.get("niche"))
        topic = self._extract_core_topic(text_es, niche)

        # 2. Generación de 3 ganchos psicológicos diferenciados
        h_pattern = random.choice(HOOK_FRAMEWORKS["pattern_interrupt"]).format(topic=topic)
        h_curiosity = random.choice(HOOK_FRAMEWORKS["curiosity_gap"]).format(topic=topic)
        h_negative = random.choice(HOOK_FRAMEWORKS["negative_bias"]).format(topic=topic)

        hooks_options = [h_pattern, h_curiosity, h_negative]
        # Asegurar español estricto
        hooks_options = [
            h if is_text_spanish(h) else translate_to_spanish(h)
            for h in hooks_options
        ]
        selected_hook = hooks_options[0]

        # 3. Llamada a la acción (CTA) y hashtags
        cta = random.choice(CTAS)
        hashtags = self._select_balanced_hashtags(niche)

        # 4. Descripción optimizada para retención
        description = (
            f"Lo que revela este fragmento expone una realidad fundamental sobre {topic}. "
            f"Muy pocas personas están prestando atención a cómo esto impacta los resultados a largo plazo."
        )

        # 5. Copys especializados por plataforma
        ready_to_publish_copy = (
            f"{selected_hook}\n\n"
            f"{description}\n\n"
            f"{cta}\n\n"
            f"{' '.join(hashtags)}"
        )

        tiktok_copy = (
            f"{selected_hook}\n\n"
            f"¿Tú qué opinas de esto? 👇 Te leo en los comentarios.\n\n"
            f"{' '.join(hashtags)}"
        )

        reels_copy = (
            f"{selected_hook}\n\n"
            f"{description}\n\n"
            f"💡 Guarda este reel para repasarlo más tarde y compártelo con alguien a quien le sirva.\n\n"
            f"{' '.join(hashtags)}"
        )

        shorts_title = f"{selected_hook[:65].strip()} | #Shorts"
        shorts_description = (
            f"{selected_hook}\n\n"
            f"{description}\n\n"
            f"Suscríbete al canal para más análisis diarios en formato corto.\n\n"
            f"{' '.join(hashtags)}"
        )

        return {
            "status": "success",
            "agent": "SeoMarketingAgent",
            "role": "Agente experto en SEO, Copywriting de Alta Retención y Estrategia Multi-Plataforma",
            "language": "es",
            "niche_detected": niche,
            "core_topic": topic,
            "hook_screen_options": hooks_options,
            "selected_hook": selected_hook,
            "description": description,
            "call_to_action": cta,
            "hashtags": hashtags,
            "hashtags_count": len(hashtags),
            "ready_to_publish_copy": ready_to_publish_copy,
            "platforms": {
                "tiktok": {
                    "caption": tiktok_copy,
                    "target_cta": "Comentarios & Debate",
                    "hashtags": hashtags[:5],
                },
                "instagram_reels": {
                    "caption": reels_copy,
                    "target_cta": "Guardar & Compartir",
                    "hashtags": hashtags,
                },
                "youtube_shorts": {
                    "title": shorts_title,
                    "description": shorts_description,
                    "target_cta": "Suscripción & Búsqueda SEO",
                    "tags": [t.replace("#", "") for t in hashtags],
                }
            },
            "best_posting_times": ["12:00 - 14:00", "18:30 - 21:00"],
            "reading_time_seconds": 12,
        }

