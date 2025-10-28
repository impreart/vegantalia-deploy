#!/usr/bin/env python3
"""
Sitemap Generator für vegantalia.de
Generiert sitemap.xml aus recipes.json
"""

import json
import os
from datetime import datetime
from pathlib import Path

def generate_slug(title: str) -> str:
    """Erstellt URL-freundlichen Slug aus Titel"""
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
    }
    
    slug = title.lower()
    for old, new in replacements.items():
        slug = slug.replace(old, new)
    
    # Nur a-z, 0-9 und Bindestriche
    slug = ''.join(c if c.isalnum() else '-' for c in slug)
    slug = '-'.join(filter(None, slug.split('-')))  # Doppelte Bindestriche entfernen
    
    return slug

def generate_sitemap(base_url: str = "https://vegantalia.de"):
    """Generiert sitemap.xml"""
    
    # Lade Rezepte
    recipes_path = Path(__file__).parent / "recipes.json"
    
    if not recipes_path.exists():
        print(f"❌ recipes.json nicht gefunden: {recipes_path}")
        return False
    
    with open(recipes_path, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    # Statische Seiten
    static_pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/rezepte", "priority": "0.9", "changefreq": "daily"},
        {"loc": "/ueber-mich", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/kontakt", "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/impressum", "priority": "0.5", "changefreq": "yearly"},
    ]
    
    # XML Header
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    
    # Statische Seiten hinzufügen
    for page in static_pages:
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{base_url}{page["loc"]}</loc>')
        xml_lines.append(f'    <changefreq>{page["changefreq"]}</changefreq>')
        xml_lines.append(f'    <priority>{page["priority"]}</priority>')
        xml_lines.append('  </url>')
    
    # Rezept-Seiten hinzufügen
    for recipe in recipes:
        title = recipe.get('title', '')
        if not title:
            continue
        
        slug = generate_slug(title)
        updated_at = recipe.get('updated_at', recipe.get('created_at', datetime.now().isoformat()))
        
        # ISO-Datum zu YYYY-MM-DD konvertieren
        try:
            date_obj = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            lastmod = date_obj.strftime('%Y-%m-%d')
        except:
            lastmod = datetime.now().strftime('%Y-%m-%d')
        
        xml_lines.append('  <url>')
        xml_lines.append(f'    <loc>{base_url}/rezept/{slug}</loc>')
        xml_lines.append(f'    <lastmod>{lastmod}</lastmod>')
        xml_lines.append(f'    <changefreq>weekly</changefreq>')
        xml_lines.append(f'    <priority>0.8</priority>')
        xml_lines.append('  </url>')
    
    xml_lines.append('</urlset>')
    
    # Sitemap schreiben
    sitemap_path = Path(__file__).parent.parent / "public" / "sitemap.xml"
    sitemap_path.parent.mkdir(exist_ok=True)
    
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_lines))
    
    print(f"✅ Sitemap generiert: {sitemap_path}")
    print(f"📊 {len(static_pages)} statische Seiten + {len(recipes)} Rezepte = {len(static_pages) + len(recipes)} URLs")
    
    return True

if __name__ == "__main__":
    generate_sitemap()
