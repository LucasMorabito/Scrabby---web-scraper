"""
llm_parser.py
-------------
Fallback de parseo usando Google Gemini Flash.

Se activa cuando el parser convencional (BeautifulSoup) devuelve lista vacía,
lo que indica un probable cambio en la estructura HTML del sitio.

Diseño:
    - Un único parser genérico para los 6 scrapers HTML del proyecto.
    - Recibe html + store, devuelve el mismo schema que todos los parsers normales.
    - La Sentry integration con google_genai está incluida automáticamente
      si sentry_sdk está configurado en el proyecto.

Uso:
    from scrappers.llm_parser import llm_parse_products

    productos = llm_parse_products(
        html=raw_html,
        store="mexx",
        base_url="https://www.mexx.com.ar"
    )
"""

import json
import logging
import os
from urllib.parse import urljoin

from google import genai
from google.genai import types

from utils.html_cleaner import clean_html_for_llm, estimate_token_count

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

_MODEL = "gemini-2.5-flash"

# Schema JSON que Gemini garantiza respetar en la respuesta.
# Usamos los mismos campos que el schema estándar de Scrabby,
# excepto "store" y "currency" que los agregamos nosotros después.
_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "name":  {"type": "STRING"},
            "price": {"type": "NUMBER"},
            "url":   {"type": "STRING"},
        },
        "required": ["name", "price", "url"],
    },
}

_SYSTEM_PROMPT = """
Sos un extractor de datos de e-commerce especializado en hardware de computadoras.

Tu tarea es analizar el HTML de una página de resultados de búsqueda y extraer
todos los productos listados.

Para cada producto extraé exactamente estos tres campos:
- name:  nombre completo del producto (string)
- price: precio como número sin símbolo de moneda ni separadores de miles (number)
         Ejemplos: "$ 1.299.999" → 1299999  |  "$299,99" → 299.99
- url:   href del link al producto tal como aparece en el HTML (string)

Reglas:
- Solo incluí productos reales con los tres campos presentes y válidos.
- No incluyas publicidades, banners, ni elementos de navegación.
- Si el precio no es un número claro, omití ese producto.
- Si no hay link al producto, omití ese producto.
""".strip()


# ---------------------------------------------------------------------------
# Funciones internas
# ---------------------------------------------------------------------------

def _build_prompt(html_cleaned: str, store: str) -> str:
    return f"Extraé los productos de esta página de la tienda '{store}':\n\n{html_cleaned}"


def _validate_product(raw: dict) -> bool:
    """
    Valida que un producto extraído por el LLM sea utilizable.
    Doble chequeo de seguridad aunque Gemini ya garantiza el schema.
    """
    name  = raw.get("name", "")
    price = raw.get("price")
    url   = raw.get("url", "")

    if not isinstance(name, str) or not name.strip():
        return False

    if not isinstance(price, (int, float)) or price <= 0:
        return False

    if not isinstance(url, str) or not url.strip():
        return False

    return True


# ---------------------------------------------------------------------------
# Función pública
# ---------------------------------------------------------------------------

def llm_parse_products(
    html: str,
    store: str,
    base_url: str = "",
) -> list[dict]:
    """
    Parsea productos desde HTML crudo usando Gemini como fallback.

    Args:
        html:     HTML crudo de la página scrapeada.
        store:    Nombre de la tienda. Ej: "mexx", "armytech", "rockethard".
        base_url: URL base de la tienda para convertir paths relativos en URLs
                  absolutas. Ej: "https://www.mexx.com.ar".
                  Si el HTML ya tiene URLs absolutas, dejarlo vacío.

    Returns:
        Lista de dicts con el schema estándar de Scrabby:
            [{"store": str, "name": str, "price": float, "currency": "ARS", "url": str}]
        Lista vacía si el LLM tampoco puede extraer productos o si ocurre un error.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("[LLM Fallback] GEMINI_API_KEY no configurada. Saltando fallback.")
        return []

    # --- Paso 1: Limpiar HTML ---
    html_cleaned = clean_html_for_llm(html)
    tokens_est   = estimate_token_count(html_cleaned)
    logger.info(
        f"[LLM Fallback] {store} | HTML limpio: {len(html_cleaned):,} chars "
        f"(~{tokens_est:,} tokens estimados)"
    )

    # --- Paso 2: Llamada a Gemini ---
    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=_MODEL,
            contents=_build_prompt(html_cleaned, store),
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_RESPONSE_SCHEMA,
                temperature=0,  # Máximo determinismo para extracción de datos
            ),
        )

        raw_text = response.text

    except Exception as e:
        logger.error(f"[LLM Fallback] Error en llamada a Gemini para '{store}': {e}")
        return []

    # --- Paso 3: Parsear JSON ---
    # Con response_mime_type="application/json" Gemini garantiza JSON válido,
    # pero mantenemos el try/except como defensa ante comportamientos inesperados.
    try:
        raw_products = json.loads(raw_text)
    except json.JSONDecodeError as e:
        logger.error(
            f"[LLM Fallback] JSON inválido para '{store}': {e}\n"
            f"Respuesta recibida: {raw_text[:300]}"
        )
        return []

    if not isinstance(raw_products, list):
        logger.error(
            f"[LLM Fallback] Se esperaba lista para '{store}', "
            f"se recibió {type(raw_products).__name__}"
        )
        return []

    # --- Paso 4: Validar y normalizar al schema estándar de Scrabby ---
    products = []
    skipped  = 0

    for raw in raw_products:
        if not _validate_product(raw):
            skipped += 1
            continue

        url = raw["url"].strip()
        # Convertir paths relativos a URLs absolutas si se provee base_url
        if base_url and not url.startswith("http"):
            url = urljoin(base_url, url)

        products.append({
            "store":    store,
            "name":     raw["name"].strip(),
            "price":    float(raw["price"]),
            "currency": "ARS",
            "url":      url,
        })

    if skipped:
        logger.warning(
            f"[LLM Fallback] {store} | {skipped} producto(s) descartados por validación"
        )

    logger.info(f"[LLM Fallback] {store} | {len(products)} productos extraídos por LLM")
    return products