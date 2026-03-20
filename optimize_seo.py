#!/usr/bin/env python3
"""
optimize_seo.py
---------------
Optimiza títulos y excerpts SEO de todos los artículos existentes.
Actualiza el index.html y regenera cada archivo HTML individual.

Uso: python optimize_seo.py

Variables de entorno necesarias:
    ANTHROPIC_API_KEY
"""

import os
import re
import json
import time
import unicodedata
import anthropic

API_KEY      = os.environ.get("ANTHROPIC_API_KEY")
HTML_FILE    = "index.html"
ARTICLES_DIR = "articulos"
SITE_URL     = "https://diegonatylab-alt.github.io"
SITE_NAME    = "PetsGuía"


def slugify(text):
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80]


def optimize_seo(article):
    """Llama a la API para obtener título y excerpt optimizados."""
    client = anthropic.Anthropic(api_key=API_KEY)

    # Extraer texto plano del contenido para contexto
    content_plain = re.sub(r"<[^>]+>", " ", article["content"])
    content_plain = re.sub(r"\s+", " ", content_plain).strip()[:600]

    prompt = (
        f'Eres un experto en SEO para blogs de mascotas en español.\n\n'
        f'Tengo este artículo:\n'
        f'Categoría: {article["category"]}\n'
        f'Título actual: {article["title"]}\n'
        f'Contenido (resumen): {content_plain}\n\n'
        f'Necesito que me generes un título y meta description optimizados para Google.\n\n'
        f'REGLAS OBLIGATORIAS:\n'
        f'- El título debe empezar con la keyword principal\n'
        f'- El título debe tener entre 50 y 60 caracteres exactos\n'
        f'- El excerpt es la meta description: incluir keyword, ser persuasivo, entre 120 y 155 caracteres\n'
        f'- Usar lenguaje natural que la gente realmente busca en Google\n'
        f'- No usar signos de exclamación ni lenguaje de clickbait\n\n'
        f'RESPONDE ÚNICAMENTE con JSON puro sin texto antes ni después:\n'
        f'{{"title":"nuevo título optimizado","excerpt":"nueva meta description optimizada"}}'
    )

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No se encontró JSON: {raw[:200]}")

    return json.loads(raw[start:end])


def generate_article_html(article):
    """Genera el HTML completo del artículo individual."""
    slug      = article.get("slug", slugify(article["title"]))
    title     = article["title"]
    excerpt   = article["excerpt"]
    category  = article["category"]
    emoji     = article.get("emoji", "🐾")
    date      = article["date"]
    read_time = article["readTime"]
    content   = article["content"]
    image_url = article.get("image", "")
    canonical = f"{SITE_URL}/{ARTICLES_DIR}/{slug}.html"
    og_image  = image_url if image_url else f"{SITE_URL}/og-default.jpg"

    if image_url and "<figure" not in content:
        content = (
            f'<figure style="margin:0 0 28px 0;">'
            f'<img src="{image_url}" alt="{title}" '
            f'style="width:100%;border-radius:10px;max-height:420px;object-fit:cover;" loading="lazy"/>'
            f'</figure>'
        ) + content

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} – {SITE_NAME}</title>
  <meta name="description" content="{excerpt}"/>
  <link rel="canonical" href="{canonical}"/>
  <meta property="og:type" content="article"/>
  <meta property="og:title" content="{title}"/>
  <meta property="og:description" content="{excerpt}"/>
  <meta property="og:url" content="{canonical}"/>
  <meta property="og:image" content="{og_image}"/>
  <meta property="og:site_name" content="{SITE_NAME}"/>
  <meta name="twitter:card" content="summary_large_image"/>
  <meta name="twitter:title" content="{title}"/>
  <meta name="twitter:description" content="{excerpt}"/>
  <meta name="twitter:image" content="{og_image}"/>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "description": "{excerpt}",
    "image": "{og_image}",
    "datePublished": "{date}",
    "author": {{"@type": "Organization", "name": "{SITE_NAME}"}},
    "publisher": {{"@type": "Organization", "name": "{SITE_NAME}"}},
    "mainEntityOfPage": "{canonical}"
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
  <!-- <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script> -->
  <style>
    :root {{--bg:#faf7f2;--surface:#ffffff;--surface2:#f2ede4;--ink:#1a1510;--ink2:#5a5040;--accent:#c8541a;--accent2:#e8a44a;--green:#3a7d44;--border:#e0d8cc;--radius:12px;--font-display:'Fraunces',Georgia,serif;--font-body:'DM Sans',sans-serif;}}
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:var(--bg);color:var(--ink);font-family:var(--font-body);font-size:16px;line-height:1.6;}}
    a{{color:inherit;text-decoration:none;}}
    header{{background:var(--ink);color:var(--bg);padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:64px;position:sticky;top:0;z-index:100;}}
    .logo{{font-family:var(--font-display);font-size:1.6rem;font-weight:700;color:var(--accent2);letter-spacing:-0.5px;}}
    .logo span{{color:var(--bg);}}
    nav{{display:flex;gap:24px;}}
    nav a{{font-size:0.875rem;font-weight:500;color:rgba(255,255,255,0.75);transition:color 0.2s;}}
    nav a:hover{{color:var(--accent2);}}
    .article-wrap{{max-width:780px;margin:0 auto;padding:48px 24px 80px;}}
    .back-link{{display:inline-flex;align-items:center;gap:6px;font-size:0.875rem;color:var(--ink2);margin-bottom:24px;transition:color 0.2s;}}
    .back-link:hover{{color:var(--accent);}}
    .tag{{display:inline-block;background:var(--accent);color:white;font-size:0.7rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-bottom:12px;}}
    h1{{font-family:var(--font-display);font-size:clamp(1.8rem,4vw,2.6rem);font-weight:700;line-height:1.2;margin-bottom:16px;}}
    .article-meta{{display:flex;gap:16px;color:var(--ink2);font-size:0.85rem;margin-bottom:32px;padding-bottom:24px;border-bottom:2px solid var(--border);flex-wrap:wrap;}}
    .ad-block{{background:var(--surface2);border:2px dashed var(--border);text-align:center;padding:28px;margin:32px 0;font-size:0.8rem;color:var(--ink2);border-radius:var(--radius);}}
    .article-content h2{{font-family:var(--font-display);font-size:1.5rem;margin:32px 0 12px;}}
    .article-content p{{margin-bottom:16px;line-height:1.75;color:#2a2218;}}
    .article-content ul{{padding-left:24px;margin-bottom:16px;}}
    .article-content ul li{{margin-bottom:8px;line-height:1.6;}}
    .article-content figure{{margin:0 0 28px 0;}}
    .article-content figcaption{{font-size:0.75rem;color:#888;margin-top:6px;}}
    footer{{background:var(--ink);color:rgba(255,255,255,0.6);padding:40px 24px;margin-top:32px;}}
    .footer-inner{{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}}
    .footer-logo{{font-family:var(--font-display);font-size:1.3rem;font-weight:700;color:var(--accent2);}}
    .footer-links{{display:flex;gap:20px;font-size:0.85rem;}}
    .footer-links a:hover{{color:white;}}
    @media(max-width:600px){{nav{{display:none;}}}}
  </style>
</head>
<body>
<header>
  <a href="{SITE_URL}" class="logo">Pets<span>Guía</span></a>
  <nav>
    <a href="{SITE_URL}">Inicio</a>
    <a href="{SITE_URL}">Perros</a>
    <a href="{SITE_URL}">Gatos</a>
    <a href="{SITE_URL}">Salud</a>
  </nav>
</header>
<div class="article-wrap">
  <a href="{SITE_URL}" class="back-link">← Volver al inicio</a>
  <span class="tag">{category}</span>
  <h1>{title}</h1>
  <div class="article-meta">
    <span>📅 {date}</span>
    <span>⏱ {read_time} min de lectura</span>
    <span>{emoji} {category}</span>
  </div>
  <div class="ad-block">📢 Google AdSense — 728×90</div>
  <div class="article-content">{content}</div>
  <div class="ad-block" style="margin-top:32px;">📢 Google AdSense — 300×250</div>
</div>
<footer>
  <div class="footer-inner">
    <span class="footer-logo">PetsGuía</span>
    <div class="footer-links">
      <a href="{SITE_URL}">Inicio</a>
      <a href="#">Privacidad</a>
      <a href="#">Contacto</a>
    </div>
    <span class="footer-copy">© 2026 {SITE_NAME}. Todos los derechos reservados.</span>
  </div>
</footer>
</body>
</html>"""


def _find_array_bounds(html):
    match = re.search(r"const articles\s*=\s*\[", html)
    if not match:
        raise ValueError("No se encontró 'const articles = [' en el HTML")
    bracket_start = match.end() - 1
    depth = 0; in_string = False; escape = False
    for i in range(bracket_start, len(html)):
        ch = html[i]
        if escape: escape = False; continue
        if ch == '\\' and in_string: escape = True; continue
        if ch == '"': in_string = not in_string; continue
        if not in_string:
            if ch == '[': depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    return match.start(), bracket_start, i + 1
    raise ValueError("No se encontró el cierre del array articles")


def load_existing_articles(html):
    _, bracket_start, bracket_end = _find_array_bounds(html)
    raw = html[bracket_start:bracket_end]
    raw = re.sub(r',\s*([\]}])', r'\1', raw)
    return json.loads(raw)


def save_articles(html, articles):
    decl_start, _, bracket_end = _find_array_bounds(html)
    semi_pos = html.index(';', bracket_end - 1) + 1
    new_json = json.dumps(articles, ensure_ascii=False, indent=6)
    return html[:decl_start] + "const articles = " + new_json + ";" + html[semi_pos:]


def main():
    if not API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY no está definida")

    os.makedirs(ARTICLES_DIR, exist_ok=True)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    articles = load_existing_articles(html)
    print(f"Artículos a optimizar: {len(articles)}\n")

    for i, article in enumerate(articles):
        print(f"[{i+1}/{len(articles)}] Optimizando: {article['title'][:50]}...")

        try:
            seo = optimize_seo(article)

            old_title = article["title"]
            article["title"]   = seo["title"]
            article["excerpt"] = seo["excerpt"]

            # Actualizar slug si el título cambió significativamente
            new_slug = slugify(seo["title"])
            old_slug = article.get("slug", "")

            # Mantener slug viejo para no romper URLs ya indexadas,
            # solo asignar si no tenía slug
            if not old_slug:
                article["slug"] = new_slug

            print(f"  ✅ Título: {seo['title']}")
            print(f"  📝 Excerpt: {seo['excerpt'][:80]}...")

            # Regenerar HTML individual
            filepath = os.path.join(ARTICLES_DIR, f"{article['slug']}.html")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(generate_article_html(article))
            print(f"  💾 HTML actualizado: {filepath}\n")

        except Exception as e:
            print(f"  ❌ Error: {e}\n")

        # Pausa para no saturar la API
        time.sleep(1)

    # Guardar index.html actualizado
    html_updated = save_articles(html, articles)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_updated)

    print("✅ index.html actualizado con todos los títulos y excerpts optimizados.")


if __name__ == "__main__":
    main()
