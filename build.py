#!/usr/bin/env python3
"""
build.py — Genera artículos HTML desde archivos de contenido + plantilla.

Cada archivo en content/ tiene este formato:

    <!--
    title: Título del artículo
    description: Meta description
    category: Perros
    date: 2026-03-15
    image: https://images.unsplash.com/...
    -->

    <figure>...</figure>
    <p>Contenido HTML...</p>

Uso: python build.py
"""
import os
import re
import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(BASE, 'content', 'articulos')
TEMPLATE_FILE = os.path.join(BASE, 'templates', 'article.html')
OUTPUT_DIR = os.path.join(BASE, 'articulos')

MONTHS_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}


def parse_content_file(filepath):
    """Lee un archivo de contenido y devuelve (metadata_dict, html_content)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Extraer frontmatter del comentario HTML
    fm_match = re.match(r'\s*<!--\s*\n(.*?)\n\s*-->', text, re.DOTALL)
    if not fm_match:
        raise ValueError(f"No se encontró frontmatter en {filepath}")

    meta = {}
    for line in fm_match.group(1).strip().split('\n'):
        line = line.strip()
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip()] = val.strip()

    content = text[fm_match.end():].strip()
    return meta, content


def format_date(date_str):
    """Convierte '2026-03-15' a '15 de marzo, 2026'."""
    try:
        d = datetime.date.fromisoformat(date_str)
        return f"{d.day} de {MONTHS_ES[d.month]}, {d.year}"
    except (ValueError, KeyError):
        return date_str


def estimate_read_time(html_content):
    """Estima minutos de lectura (200 palabras/min)."""
    text = re.sub(r'<[^>]+>', ' ', html_content)
    words = len(text.split())
    return max(1, round(words / 200))


def build_article(template, meta, content, slug):
    """Aplica la plantilla con los datos del artículo."""
    read_time = estimate_read_time(content)
    date_display = format_date(meta.get('date', ''))

    html = template
    replacements = {
        '{{TITLE}}': meta.get('title', ''),
        '{{DESCRIPTION}}': meta.get('description', ''),
        '{{SLUG}}': slug,
        '{{CATEGORY}}': meta.get('category', ''),
        '{{IMAGE}}': meta.get('image', ''),
        '{{DATE_ISO}}': meta.get('date', ''),
        '{{DATE_DISPLAY}}': date_display,
        '{{READ_TIME}}': str(read_time),
        '{{CONTENT}}': content,
    }
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    return html


def main():
    # Leer plantilla
    with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()

    if not os.path.isdir(CONTENT_DIR):
        print(f"Error: No existe {CONTENT_DIR}")
        return

    count = 0
    for filename in sorted(os.listdir(CONTENT_DIR)):
        if not filename.endswith('.html'):
            continue

        slug = filename[:-5]  # quitar .html
        filepath = os.path.join(CONTENT_DIR, filename)

        try:
            meta, content = parse_content_file(filepath)
        except ValueError as e:
            print(f"  ERROR: {e}")
            continue

        html = build_article(template, meta, content, slug)

        # Crear directorio de salida
        out_dir = os.path.join(OUTPUT_DIR, slug)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, 'index.html')

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)

        words = len(re.sub(r'<[^>]+>', ' ', content).split())
        print(f"  ✓ {slug} ({words} palabras, {estimate_read_time(content)} min)")
        count += 1

    print(f"\n{count} artículos generados en {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
