"""
html_cleaner.py
---------------
Pre-procesa HTML crudo antes de enviarlo a un LLM.

Objetivo: reducir tokens eliminando ruido (scripts, estilos, analytics)
sin perder la estructura semántica que le permite al LLM encontrar productos.

Uso:
    from utils.html_cleaner import clean_html_for_llm
    html_limpio = clean_html_for_llm(raw_html)
"""

from bs4 import BeautifulSoup

# Tags que no aportan contenido semántico para extracción de productos
_TAGS_TO_REMOVE = [
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "link",
    "meta",
    "head",
    "footer",
    "nav",
    "header",
    "aside",
    "form",
    "button",
    "input",
]

# Atributos que no aportan estructura semántica (analytics, handlers, CSS inline)
# Conservamos: class, href, src — útiles para que el LLM entienda el layout y las URLs
_ATTRS_TO_STRIP = {
    "style",
    "onclick",
    "onload",
    "onmouseover",
    "onmouseout",
    "onfocus",
    "onblur",
    "tabindex",
    "aria-hidden",
    "aria-label",
    "aria-describedby",
    "role",
}

# Límite de caracteres antes de truncar.
# ~50k chars ≈ 12k tokens — generoso pero controlado para Gemini Flash.
# Una página de Mexx limpia ronda los 15k-30k chars.
_MAX_CHARS = 50_000


def clean_html_for_llm(html: str, max_chars: int = _MAX_CHARS) -> str:
    """
    Limpia HTML crudo para consumo eficiente por un LLM.

    Pasos:
    1. Elimina tags de ruido (scripts, estilos, nav, footer, etc.)
    2. Elimina atributos de analytics y handlers JS
    3. Elimina atributos data-* (tracking, analytics)
    4. Trunca si supera max_chars

    Args:
        html:      HTML crudo de la página scrapeada.
        max_chars: Límite de caracteres del output. Default: 50_000.

    Returns:
        String con el HTML simplificado, listo para incluir en un prompt.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Paso 1: Eliminar tags de ruido completos (con su contenido)
    for tag in soup(name=_TAGS_TO_REMOVE):
        tag.decompose()

    # Paso 2 y 3: Limpiar atributos en los tags restantes
    for tag in soup.find_all(True):  # True = todos los tags
        attrs_to_delete = [
            attr
            for attr in list(tag.attrs)
            if attr in _ATTRS_TO_STRIP or attr.startswith("data-")
        ]
        for attr in attrs_to_delete:
            del tag.attrs[attr]

    # Serializar de vuelta a string
    cleaned = str(soup)

    # Paso 4: Truncar si es necesario
    # Truncamos desde el final porque la zona de productos suele estar
    # en la parte superior/central de la página.
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars]

    return cleaned


def estimate_token_count(text: str) -> int:
    """
    Estimación rápida de tokens (1 token ≈ 4 caracteres).
    Útil para logging antes de cada llamada al LLM.
    """
    return len(text) // 4


if __name__ == "__main__":
    # Test rápido con HTML de ejemplo para verificar reducción de ruido
    sample_html = """
    <html>
    <head>
        <meta charset="UTF-8">
        <style>body { color: red; } .card { margin: 10px; }</style>
        <script>console.log('tracking'); gtag('event', 'page_view');</script>
    </head>
    <body>
        <nav><a href="/">Inicio</a></nav>
        <header><h1>Mexx Tienda</h1></header>
        <main>
            <div class="card-body" data-product-id="123" data-analytics="view">
                <h4 class="card-title">
                    <a href="/producto/rtx-4060" onclick="trackClick()">RTX 4060 8GB GDDR6</a>
                </h4>
                <div class="price" style="color: green;">
                    <h4><b>$ 1.299.999</b></h4>
                </div>
            </div>
        </main>
        <footer><p>Copyright 2024</p></footer>
        <script>analytics.send();</script>
    </body>
    </html>
    """

    resultado = clean_html_for_llm(sample_html)
    tokens_estimados = estimate_token_count(resultado)

    print("=== HTML ORIGINAL ===")
    print(f"Longitud: {len(sample_html)} chars")
    print()
    print("=== HTML LIMPIO ===")
    print(resultado)
    print()
    print(f"Longitud: {len(resultado)} chars")
    print(f"Tokens estimados: {tokens_estimados}")
    print(f"Reducción: {100 - (len(resultado) * 100 // len(sample_html))}%")