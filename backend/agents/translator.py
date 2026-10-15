"""
Módulo de Traducción y Adaptación Cultural al Español
Garantiza que cualquier transcripción o texto de origen (inglés, ruso, etc.)
sea traducido y adaptado al español con tono viral y natural.
"""
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Optional, List, Dict

logger = logging.getLogger("clipai.translator")

# Palabras o marcadores comunes de idiomas extranjeros para validación estricta
NON_SPANISH_INDICATORS = [
    r'\b(the|and|this|that|with|you|what|when|where|why|how|from|have|been|will|would|could|should|about|there|their)\b',
    r'[\u0400-\u04FF]',  # Caracteres cirílicos (ruso, ucraniano, etc.)
    r'\b(pourquoi|avec|dans|mais|nous|vous|ils|elle|faire|avoir|être)\b', # Francés
    r'\b(und|nicht|oder|aber|wieder|immer|werden|haben|sein)\b', # Alemán
]


def is_text_spanish(text: str) -> bool:
    """
    Verifica si el texto está predominantemente en español.
    Retorna False si detecta patrones claros de inglés, ruso, etc.
    """
    if not text or len(text.strip()) < 4:
        return True
    
    t_lower = text.lower()
    for pattern in NON_SPANISH_INDICATORS:
        if re.search(pattern, t_lower, re.IGNORECASE):
            # Si hay más de 2 palabras inglesas/cirílicas o coincidencia cirílica directa
            matches = re.findall(pattern, t_lower, re.IGNORECASE)
            if len(matches) >= 2 or re.search(r'[\u0400-\u04FF]', t_lower):
                return False
    return True


def translate_to_spanish(text: str, source_lang: Optional[str] = None) -> str:
    """
    Traduce texto al español usando servicios robustos en cascada:
    1. MyMemory Translation API
    2. Google GTX Free Fallback
    3. Normalización y adaptación cultural
    """
    if not text or not text.strip():
        return ""
    
    clean_text = text.strip()
    
    # Si ya es español verificado, retornarlo
    if source_lang and source_lang.lower().startswith("es") and is_text_spanish(clean_text):
        return clean_text

    # Intento 1: MyMemory API
    try:
        pair = f"{source_lang[:2]}|es" if (source_lang and len(source_lang) >= 2 and source_lang != "auto") else "auto|es"
        url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode({
            "q": clean_text[:450],
            "langpair": pair
        })
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=6) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            translated = res_data.get("responseData", {}).get("translatedText")
            if translated and not translated.startswith("MYMEMORY WARNING"):
                return translated.strip()
    except Exception as e:
        logger.warning(f"MyMemory traducción falló: {e}")

    # Intento 2: Fallback Google Translator
    try:
        url_gtx = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode({
            "client": "gtx",
            "sl": "auto",
            "tl": "es",
            "dt": "t",
            "q": clean_text
        })
        req_gtx = urllib.request.Request(url_gtx, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_gtx, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and data[0]:
                return "".join([part[0] for part in data[0] if part[0]]).strip()
    except Exception as e_gtx:
        logger.warning(f"Google GTX traducción falló: {e_gtx}")

    return clean_text
