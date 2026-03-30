#!/usr/bin/env python3
"""
generate_article.py
-------------------
Genera un artículo diario sobre mascotas usando la API de Anthropic,
busca una imagen en Unsplash, lo inserta en el index.html y genera
un archivo HTML individual con URL propia para SEO.

Variables de entorno necesarias:
    ANTHROPIC_API_KEY   → API key de Anthropic
    UNSPLASH_ACCESS_KEY → Access key de Unsplash (gratuita)
"""

import os
import re
import json
import random
import shutil
import datetime
import unicodedata
import urllib.request
import urllib.parse
import anthropic

# ─── CONFIGURACIÓN ──────────────────────────────────────────────
API_KEY         = os.environ.get("ANTHROPIC_API_KEY")
UNSPLASH_KEY    = os.environ.get("UNSPLASH_ACCESS_KEY")
HTML_FILE       = "index.html"
ARTICLES_DIR    = "articulos"
MAX_ARTICLES    = 60
SITE_URL = "https://petsguia.com"
SITE_NAME       = "PetsGuía"
# ────────────────────────────────────────────────────────────────

CATEGORIES = [
    ("Perros",       "🐶"),
    ("Gatos",        "🐱"),
    ("Aves",         "🦜"),
    ("Reptiles",     "🦎"),
    ("Exóticas",     "🐇"),
    ("Salud",        "💊"),
    ("Alimentación", "🍖"),
]

UNSPLASH_KEYWORDS = {
    "Perros":        "dog pet",
    "Gatos":         "cat pet",
    "Aves":          "pet bird parrot",
    "Reptiles":      "reptile lizard pet",
    "Exóticas":      "exotic pet rabbit hamster",
    "Salud":         "veterinarian pet health",
    "Alimentación":  "pet food dog cat",
}

TOPIC_POOL = {
    "Perros": [
        "razas ideales para casa con patio",
        "cómo entrenar un cachorro en casa",
        "señales de dolor en perros",
        "cómo bañar a un perro correctamente",
        "juegos para estimular mentalmente a tu perro",
        "por qué los perros comen pasto",
        "cuánto ejercicio necesita cada raza",
        "qué significa el lenguaje corporal del perro",
        "cómo cortar las uñas a un perro en casa",
    ],
    "Gatos": [
        "por qué los gatos ronronean",
        "cómo limpiar los ojos de un gato",
        "razas de gatos hipoalergénicas",
        "gatos de interior vs exterior pros y contras",
        "qué vacunas necesita un gato cada año",
        "como cortarle las uñas a un gato en casa",
        "señales de felicidad en gatos",
        "cuántas veces al día debe comer un gato cachorro",
        "por qué mi gato me trae presas",
        "cómo presentar a un gato nuevo en casa",
        "enfermedades más comunes en gatos mayores",
        "tamaño de bandeja sanitaria adecuada para tu gato",
    ],
    "Aves": [
        "cómo saber si un jilguero está sano",
        "qué frutas puede comer una cotorra",
        "canarios cuidados básicos para principiantes",
        "cómo enseñar a hablar a un loro",
        "por que mi canario no canta",
        "guacamayos guía completa de cuidados",
    ],
    "Reptiles": [
        "qué come una tortuga doméstica",
        "temperatura ideal para un terrario de serpientes",
        "tortuga de tierra cuidados en el hogar",
        "gecko leopardo como mascota guía para principiantes",
        "señales de enfermedad en reptiles",
        "dragons barbudos alimentación y hábitat",
    ],
    "Exóticas": [
        "cómo cuidar un hamster",
        "hámster vs cobayo cuál es mejor mascota",
        "erizo africano consejos veterinario",
        "hurón doméstico en que paises esta permitido como mascota",
        "peces betta cuidados en acuario",
        "chinchillas como mascotas ventajas y desafíos",
    ],
    "Salud": [
        "calendario de vacunación para perros y gatos",
        "cómo detectar pulgas y garrapatas",
        "primeros auxilios para mascotas",
        "señales de alerta que requieren veterinario urgente",
        "desparasitación cuándo y con qué frecuencia",
        "enfermedades zoonóticas cuáles pueden contagiarse a humanos",
    ],
    "Alimentación": [
        "alimentos tóxicos para gatos que quizás no conocés",
        "dietas especiales para gatos pros y contras según la ciencia",
        "cómo leer la etiqueta de un alimento balanceado",
        "cuánta agua debe beber una mascota al día",
        "suplementos vitamínicos para mascotas cuándo son necesarios",
        "alimentos caseros seguros para gatos",
    ],
}


# ─── UTILIDADES ─────────────────────────────────────────────────

# Palabras de relleno a eliminar del slug
_STOPWORDS = {
    "a", "al", "con", "de", "del", "el", "en", "es", "la", "las", "lo", "los",
    "para", "por", "que", "se", "si", "su", "sus", "tu", "tus", "un", "una",
    "y", "o", "como", "todo", "toda", "todos", "sobre", "mas", "muy", "sin",
    "cuando", "donde", "este", "esta", "estos", "son", "ser",
}


def slugify(text):
    """Convierte un título en slug URL-amigable y corto."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s-]", "", text)
    words = text.split()
    words = [w for w in words if w not in _STOPWORDS]
    slug = "-".join(words)
    slug = re.sub(r"-+", "-", slug).strip("-")
    # Cortar en límite de palabra (~45 chars)
    if len(slug) > 45:
        slug = slug[:45].rsplit("-", 1)[0]
    return slug


def pick_topic(existing_titles):
    cats = list(CATEGORIES)
    random.shuffle(cats)
    for cat_name, emoji in cats:
        topics = list(TOPIC_POOL.get(cat_name, []))
        random.shuffle(topics)
        for topic in topics:
            if not any(topic.lower() in t.lower() for t in existing_titles[-30:]):
                return cat_name, emoji, topic
    cat_name, emoji = random.choice(CATEGORIES)
    topic = random.choice(TOPIC_POOL[cat_name])
    return cat_name, emoji, topic


# ─── UNSPLASH ────────────────────────────────────────────────────

def fetch_unsplash_image(cat, topic):
    if not UNSPLASH_KEY:
        print("UNSPLASH_ACCESS_KEY no definida, saltando imagen.")
        return None

    base_kw  = UNSPLASH_KEYWORDS.get(cat, "pet animal")
    topic_kw = " ".join(topic.split()[:3])
    query    = f"{base_kw} {topic_kw}"

    params = urllib.parse.urlencode({
        "query":          query,
        "per_page":       10,
        "orientation":    "landscape",
        "content_filter": "high",
    })
    url = f"https://api.unsplash.com/search/photos?{params}"
    req = urllib.request.Request(url, headers={
        "Authorization":  f"Client-ID {UNSPLASH_KEY}",
        "Accept-Version": "v1",
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("results", [])
        if not results:
            print(f"Unsplash no devolvió resultados para: {query}")
            return None
        photo = random.choice(results[:5])
        return {
            "url":        photo["urls"]["regular"] + "&w=800&q=75&fm=webp&fit=crop",
            "thumb":      photo["urls"]["small"] + "&w=400&q=70&fm=webp&fit=crop",
            "alt":        photo.get("alt_description") or query,
            "author":     photo["user"]["name"],
            "author_url": photo["user"]["links"]["html"],
        }
    except Exception as e:
        print(f"Error al buscar imagen en Unsplash: {e}")
        return None


def build_image_html(image):
    if not image:
        return ""
    return (
        f'<figure style="margin:0 0 28px 0;">'
        f'<img src="{image["url"]}" alt="{image["alt"]}" '
        f'width="800" height="420" '
        f'style="width:100%;border-radius:10px;max-height:420px;object-fit:cover;" loading="lazy"/>'
        f'<figcaption style="font-size:0.75rem;color:#888;margin-top:6px;">'
        f'Foto de <a href="{image["author_url"]}?utm_source=petsguia&utm_medium=referral" '
        f'target="_blank" rel="noopener">{image["author"]}</a> en '
        f'<a href="https://unsplash.com/?utm_source=petsguia&utm_medium=referral" '
        f'target="_blank" rel="noopener">Unsplash</a>'
        f'</figcaption></figure>'
    )


# ─── GENERACIÓN DE CONTENIDO ─────────────────────────────────────

def generate_article(cat, topic):
    client = anthropic.Anthropic(api_key=API_KEY)

    prompt = (
        f'Eres un experto en SEO y mascotas. Escribí un artículo optimizado para Google en español '
        f'sobre "{topic}" para la categoría "{cat}".\n\n'
        'REGLAS SEO OBLIGATORIAS:\n'
        '- El título debe comenzar con la keyword principal (ej: "Cómo bañar a un perro: guía paso a paso")\n'
        '- El título debe tener entre 50 y 60 caracteres para no cortarse en Google\n'
        '- El excerpt es la meta description: debe incluir la keyword, ser persuasivo y tener entre 120 y 155 caracteres\n'
        '- Los subtítulos H2 deben ser preguntas o frases que la gente realmente busca en Google\n'
        '- El primer párrafo debe incluir la keyword principal en las primeras 100 palabras\n'
        '- Incluir al menos un H2 con formato "¿Por qué..." o "¿Cuándo..." o "¿Cómo..."\n'
        '- El artículo debe tener mínimo 700 palabras para posicionar bien\n'
        '- Usar listas <ul> con al menos 4 ítems concretos y accionables\n'
        '- Terminar con un H2 de conclusión o llamado a la acción\n\n'
        'RESPONDE ÚNICAMENTE con JSON puro. Sin texto antes ni después. Sin bloques de código. '
        'Sin comillas triples. Solo el objeto JSON.\n\n'
        'Estructura exacta (respeta las comillas dobles en todas las claves y valores):\n'
        '{"title":"Keyword principal al inicio, máx 60 caracteres",'
        '"excerpt":"Meta description con keyword, entre 120 y 155 caracteres, persuasiva",'
        '"readTime":"6",'
        '"content":"HTML del artículo con h2 p ul li. Mínimo 700 palabras. '
        'Sin html body style. Las comillas dentro del HTML deben ser \\u0022 o evitadas."}'
    )

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    print(f"RAW API response (primeros 200 chars): {raw[:200]}")

    raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No se encontró JSON en la respuesta: {raw[:300]}")
    raw = raw[start:end]

    return json.loads(raw)


# ─── GENERACIÓN DE HTML INDIVIDUAL ───────────────────────────────

def generate_article_html(article):
    """Genera el HTML completo de una página de artículo individual."""
    slug      = article.get("slug", slugify(article["title"]))
    title     = article["title"]
    excerpt   = article["excerpt"]
    category  = article["category"]
    emoji     = article.get("emoji", "🐾")
    date      = article["date"]
    read_time = article["readTime"]
    content   = article["content"]
    image_url = article.get("image", "")
    canonical = f"{SITE_URL}/{ARTICLES_DIR}/{slug}/"
    og_image  = image_url if image_url else f"{SITE_URL}/og-default.jpg"

    # Agregar imagen hero si el contenido no la tiene ya
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
  <script>if(location.protocol!=='https:')location.replace('https://'+location.hostname+location.pathname+location.search);</script>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} – {SITE_NAME}</title>
  <meta name="description" content="{excerpt}"/>
  <link rel="canonical" href="{canonical}"/>

  <!-- Open Graph / SEO -->
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

  <!-- Schema.org Article -->
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

  <!-- Google AdSense placeholder -->
  <!-- <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX" crossorigin="anonymous"></script> -->

  <style>
    :root {{
      --bg: #faf7f2; --surface: #ffffff; --surface2: #f2ede4;
      --ink: #1a1510; --ink2: #5a5040; --accent: #c8541a;
      --accent2: #e8a44a; --green: #3a7d44; --border: #e0d8cc;
      --radius: 12px;
      --font-display: 'Fraunces', Georgia, serif;
      --font-body: 'DM Sans', sans-serif;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--ink); font-family: var(--font-body); font-size: 16px; line-height: 1.6; }}
    a {{ color: inherit; text-decoration: none; }}
    header {{ background: var(--ink); color: var(--bg); padding: 0 24px; display: flex; align-items: center; justify-content: space-between; height: 64px; position: sticky; top: 0; z-index: 100; }}
    .logo {{ font-family: var(--font-display); font-size: 1.6rem; font-weight: 700; color: var(--accent2); letter-spacing: -0.5px; }}
    .logo span {{ color: var(--bg); }}
    nav {{ display: flex; gap: 24px; }}
    nav a {{ font-size: 0.875rem; font-weight: 500; color: rgba(255,255,255,0.75); transition: color 0.2s; }}
    nav a:hover {{ color: var(--accent2); }}
    .article-wrap {{ max-width: 780px; margin: 0 auto; padding: 48px 24px 80px; }}
    .back-link {{ display: inline-flex; align-items: center; gap: 6px; font-size: 0.875rem; color: var(--ink2); margin-bottom: 24px; transition: color 0.2s; }}
    .back-link:hover {{ color: var(--accent); }}
    .tag {{ display: inline-block; background: var(--accent); color: white; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; padding: 3px 10px; border-radius: 4px; margin-bottom: 12px; }}
    h1 {{ font-family: var(--font-display); font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 700; line-height: 1.2; margin-bottom: 16px; }}
    .article-meta {{ display: flex; gap: 16px; color: var(--ink2); font-size: 0.85rem; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 2px solid var(--border); flex-wrap: wrap; }}
    .ad-block {{ background: var(--surface2); border: 2px dashed var(--border); text-align: center; padding: 28px; margin: 32px 0; font-size: 0.8rem; color: var(--ink2); border-radius: var(--radius); }}
    .article-content h2 {{ font-family: var(--font-display); font-size: 1.5rem; margin: 32px 0 12px; }}
    .article-content p {{ margin-bottom: 16px; line-height: 1.75; color: #2a2218; }}
    .article-content ul {{ padding-left: 24px; margin-bottom: 16px; }}
    .article-content ul li {{ margin-bottom: 8px; line-height: 1.6; }}
    .article-content figure {{ margin: 0 0 28px 0; }}
    .article-content figcaption {{ font-size: 0.75rem; color: #888; margin-top: 6px; }}
    footer {{ background: var(--ink); color: rgba(255,255,255,0.6); padding: 40px 24px; margin-top: 32px; }}
    .footer-inner {{ max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }}
    .footer-logo {{ font-family: var(--font-display); font-size: 1.3rem; font-weight: 700; color: var(--accent2); }}
    .footer-links {{ display: flex; gap: 20px; font-size: 0.85rem; }}
    .footer-links a:hover {{ color: white; }}
    @media (max-width: 600px) {{ nav {{ display: none; }} }}
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

  <div class="article-content">
    {content}
  </div>

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


# ─── INDEX HTML ──────────────────────────────────────────────────

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
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR al parsear articles. Primeros 500 chars:\n{raw[:500]}")
        raise e


def save_articles(html, articles):
    decl_start, _, bracket_end = _find_array_bounds(html)
    semi_pos = html.index(';', bracket_end - 1) + 1
    new_json = json.dumps(articles, ensure_ascii=False, indent=6)
    return html[:decl_start] + "const articles = " + new_json + ";" + html[semi_pos:]


# ─── MAIN ────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        raise EnvironmentError("ANTHROPIC_API_KEY no está definida")

    # Crear carpeta de artículos si no existe
    os.makedirs(ARTICLES_DIR, exist_ok=True)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    articles = load_existing_articles(html)
    print(f"Artículos existentes: {len(articles)}")

    # ── Migrar slugs viejos a nuevos más cortos y estructura de carpetas ──
    slugs_added = False
    for a in articles:
        old_slug = a.get("slug", "")
        new_slug = slugify(a["title"])
        if old_slug != new_slug:
            a["slug"] = new_slug
            slugs_added = True
            # Migrar archivo viejo .html si existe
            old_file = os.path.join(ARTICLES_DIR, f"{old_slug}.html")
            if os.path.exists(old_file):
                os.remove(old_file)
                print(f"  Eliminado archivo viejo: {old_slug}.html")
            # Eliminar carpeta vieja si existe
            old_folder = os.path.join(ARTICLES_DIR, old_slug)
            if old_slug and os.path.isdir(old_folder):
                shutil.rmtree(old_folder)
                print(f"  Eliminada carpeta vieja: {old_slug}/")
        # Actualizar campo url
        a["url"] = f"/{ARTICLES_DIR}/{a['slug']}/"
        folder = os.path.join(ARTICLES_DIR, a['slug'])
        filepath = os.path.join(folder, "index.html")
        if not os.path.exists(filepath):
            os.makedirs(folder, exist_ok=True)
            article_html = generate_article_html(a)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(article_html)
            print(f"  HTML generado: {a['slug']}/index.html")

    if slugs_added:
        print(f"Slugs agregados a artículos existentes.")

    # ── Generar nuevo artículo ──
    existing_titles = [a.get("title", "") for a in articles]
    cat, emoji, topic = pick_topic(existing_titles)
    print(f"Generando artículo sobre '{topic}' [{cat}]...")

    image = fetch_unsplash_image(cat, topic)
    if image:
        print(f"Imagen obtenida de Unsplash: {image['author']}")
    else:
        print("Sin imagen, se usará solo el emoji.")

    new_data = generate_article(cat, topic)
    image_html = build_image_html(image)
    content_with_image = image_html + new_data["content"]

    today = datetime.date.today()
    months_es = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    date_str = f"{today.day} de {months_es[today.month-1]}, {today.year}"

    max_id = max((a.get("id", 0) for a in articles), default=0)
    slug   = slugify(new_data["title"])

    new_article = {
        "id":       max_id + 1,
        "slug":     slug,
        "title":    new_data["title"],
        "excerpt":  new_data["excerpt"],
        "category": cat,
        "emoji":    emoji,
        "date":     date_str,
        "readTime": str(new_data.get("readTime", "5")),
        "featured": False,
        "image":    image["url"] if image else "",
        "content":  content_with_image,
        "url":      f"/{ARTICLES_DIR}/{slug}/",
    }

    # Guardar HTML individual del nuevo artículo
    folder = os.path.join(ARTICLES_DIR, slug)
    os.makedirs(folder, exist_ok=True)
    article_html = generate_article_html(new_article)
    filepath = os.path.join(folder, "index.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(article_html)
    print(f"HTML individual generado: {filepath}")

    # Actualizar index.html
    articles.insert(0, new_article)
    for i, a in enumerate(articles):
        a["featured"] = (i == 0)
    if len(articles) > MAX_ARTICLES:
        articles = articles[:MAX_ARTICLES]

    html_updated = save_articles(html, articles)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_updated)

    print(f"✅ Artículo publicado: {new_article['title']}")
    print(f"   URL: {SITE_URL}/{ARTICLES_DIR}/{slug}/")


if __name__ == "__main__":
    main()
