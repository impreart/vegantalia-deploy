#!/usr/bin/env python3
"""
Pre-Translation Script für vegantalia.de
Übersetzt alle Rezepte in alle unterstützten Sprachen beim Deploy
"""

import json
import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Unterstützte Sprachen (außer DE - das ist das Original)
TARGET_LANGUAGES = {
    'en': 'EN',
    'es': 'ES', 
    'fr': 'FR',
    'zh': 'ZH',
    'uk': 'UK',
    'ar': 'AR'
}

def load_env():
    """Lädt .env Datei"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def check_deepl_quota():
    """
    Prüft DeepL API Quota BEVOR Übersetzung startet
    Gibt verfügbare Zeichen zurück oder beendet bei Fehler
    """
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("❌ DEEPL_API_KEY nicht gefunden!")
        sys.exit(1)
    
    # Free vs Pro API
    if api_key.endswith(':fx'):
        base_url = "https://api-free.deepl.com/v2/usage"
    else:
        base_url = "https://api.deepl.com/v2/usage"
    
    try:
        headers = {
            "Authorization": f"DeepL-Auth-Key {api_key}"
        }
        
        response = requests.get(base_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            used = data.get('character_count', 0)
            limit = data.get('character_limit', 500000)
            available = limit - used
            percentage = (used / limit * 100) if limit > 0 else 0
            
            print(f"📊 DeepL Quota:")
            print(f"   Verbraucht: {used:,} / {limit:,} Zeichen ({percentage:.1f}%)")
            print(f"   Verfügbar: {available:,} Zeichen")
            
            if percentage >= 95:
                print("⚠️ WARNUNG: Quota fast aufgebraucht (>95%)!")
                response = input("Trotzdem fortfahren? (y/n): ")
                if response.lower() != 'y':
                    print("❌ Abgebrochen.")
                    sys.exit(0)
            elif percentage >= 80:
                print("⚠️ Achtung: Quota zu 80% verbraucht")
            
            return available
        else:
            print(f"⚠️ Quota-Check fehlgeschlagen: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"⚠️ Quota-Check Fehler: {e}")
        return None

def translate_with_deepl(text: str, target_lang: str, source_lang: str = "DE") -> str:
    """Übersetzt Text mit DeepL API"""
    api_key = os.environ.get("DEEPL_API_KEY")
    if not api_key:
        print("❌ DEEPL_API_KEY nicht gefunden!")
        sys.exit(1)
    
    # Free vs Pro API
    if api_key.endswith(':fx'):
        base_url = "https://api-free.deepl.com/v2/translate"
    else:
        base_url = "https://api.deepl.com/v2/translate"
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            headers = {
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "text": [text],
                "target_lang": target_lang.upper(),
                "source_lang": source_lang.upper()
            }
            
            response = requests.post(base_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("translations"):
                    return result["translations"][0]["text"]
            elif response.status_code == 456:
                print(f"❌ DeepL Quota überschritten!")
                sys.exit(1)
            elif response.status_code == 429:
                # Rate limit - warte länger
                retry_count += 1
                wait_time = retry_count * 2
                print(f"⚠️ Rate limit erreicht, warte {wait_time}s...")
                time.sleep(wait_time)
                continue
            
            print(f"⚠️ DeepL Fehler: {response.status_code}")
            return text  # Fallback: Original-Text
            
        except requests.exceptions.Timeout:
            retry_count += 1
            print(f"⚠️ Timeout (Versuch {retry_count}/{max_retries}), wiederhole...")
            time.sleep(2)
            continue
            
        except Exception as e:
            retry_count += 1
            print(f"⚠️ Fehler: {e} (Versuch {retry_count}/{max_retries})")
            if retry_count < max_retries:
                time.sleep(2)
                continue
            break
        return text  # Fallback

def translate_recipe(recipe: dict, target_lang: str) -> dict:
    """Übersetzt ein einzelnes Rezept"""
    translated = recipe.copy()
    
    # Speichere Original-Titel für Vergleich
    original_title = recipe.get('title', '')
    
    # Zähle Gesamt-Tasks für Progress
    total_tasks = 1  # Titel
    if recipe.get('subtitle'): total_tasks += 1
    if recipe.get('ingredients'):
        for group in recipe['ingredients']:
            total_tasks += 1 + len(group.get('items', []))
    if recipe.get('steps'):
        for step in recipe['steps']:
            total_tasks += len(step.get('substeps', []))
    if recipe.get('tips'): total_tasks += 1
    
    current_task = 0
    
    def show_progress(label):
        nonlocal current_task
        current_task += 1
        percentage = (current_task / total_tasks * 100) if total_tasks > 0 else 0
        bar_length = 20
        filled = int(bar_length * current_task / total_tasks) if total_tasks > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\r    [{bar}] {percentage:.0f}% | {label:<40}", end='', flush=True)
    
    # Titel
    show_progress("Titel")
    translated['title'] = translate_with_deepl(original_title, target_lang)
    time.sleep(0.5)
    
    # Untertitel
    if recipe.get('subtitle'):
        show_progress("Untertitel")
        translated['subtitle'] = translate_with_deepl(recipe['subtitle'], target_lang)
        time.sleep(0.5)
    
    # Zutaten
    if recipe.get('ingredients'):
        translated['ingredients'] = []
        for idx, group in enumerate(recipe['ingredients'], 1):
            new_group = group.copy()
            show_progress(f"Zutatengruppe {idx}/{len(recipe['ingredients'])}")
            new_group['group'] = translate_with_deepl(group.get('group', ''), target_lang)
            time.sleep(0.4)
            
            new_items = []
            for item_idx, item in enumerate(group.get('items', []), 1):
                new_item = item.copy()
                show_progress(f"Zutat {item_idx} (Gruppe {idx})")
                new_item['name'] = translate_with_deepl(item.get('name', ''), target_lang)
                time.sleep(0.4)
                new_items.append(new_item)
            
            new_group['items'] = new_items
            translated['ingredients'].append(new_group)
    
    # Zubereitungsschritte
    if recipe.get('steps'):
        translated['steps'] = []
        step_count = sum(len(s.get('substeps', [])) for s in recipe['steps'])
        current_substep = 0
        
        for step in recipe['steps']:
            new_step = step.copy()
            new_substeps = []
            
            for substep in step.get('substeps', []):
                current_substep += 1
                show_progress(f"Schritt {current_substep}/{step_count}")
                translated_substep = translate_with_deepl(substep, target_lang)
                time.sleep(0.4)
                new_substeps.append(translated_substep)
            
            new_step['substeps'] = new_substeps
            translated['steps'].append(new_step)
    
    # Tipps
    if recipe.get('tips'):
        translated['tips'] = []
        for tip_idx, tip in enumerate(recipe['tips'], 1):
            show_progress(f"Tipp {tip_idx}/{len(recipe['tips'])}")
            translated_tip = translate_with_deepl(tip, target_lang)
            time.sleep(0.4)
            translated['tips'].append(translated_tip)
    
    print()  # Neue Zeile nach Fortschrittsbalken
    
    # Metadaten (WICHTIG: original_title für Vergleich speichern!)
    translated['language'] = target_lang.lower()
    translated['original_title'] = original_title  # Für Incremental Translation
    translated['translation_source'] = 'deepl'
    translated['translated_at'] = datetime.now().isoformat()
    
    return translated

def load_existing_translations(lang_code):
    """
    Lädt existierende Übersetzungen (falls vorhanden)
    Returniert dict: {original_title: translated_recipe}
    """
    output_file = Path(__file__).parent / f"recipes_{lang_code}.json"
    if not output_file.exists():
        return {}
    
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        
        # Index nach ORIGINAL-Titel (nicht übersetzter Titel!)
        existing_by_original = {}
        for recipe in existing:
            # Nutze original_title falls vorhanden, sonst title
            original = recipe.get('original_title', recipe.get('title', ''))
            existing_by_original[original] = recipe
        
        return existing_by_original
    except Exception as e:
        print(f"⚠️ Fehler beim Laden existierender Übersetzungen: {e}")
        return {}

def main():
    """Hauptfunktion"""
    print("🌍 Incremental Translation Script für vegantalia.de")
    print("=" * 50)
    
    # Lade .env
    load_env()
    
    # Prüfe DeepL Quota VOR der Übersetzung
    print()
    available_chars = check_deepl_quota()
    print()
    
    # Lade deutsche Rezepte
    recipes_file = Path(__file__).parent / "recipes.json"
    if not recipes_file.exists():
        print(f"❌ {recipes_file} nicht gefunden!")
        sys.exit(1)
    
    with open(recipes_file, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    print(f"📚 {len(recipes)} Rezepte geladen")
    print()
    
    # Übersetze in alle Sprachen
    total_languages = len(TARGET_LANGUAGES)
    
    for lang_idx, (lang_code, deepl_code) in enumerate(TARGET_LANGUAGES.items(), 1):
        print(f"🌐 Übersetze nach {lang_code.upper()} ({deepl_code})... [{lang_idx}/{total_languages}]")
        
        # Lade existierende Übersetzungen
        existing_translations = load_existing_translations(lang_code)
        print(f"  📦 {len(existing_translations)} existierende Übersetzungen gefunden")
        
        translated_recipes = []
        new_count = 0
        reused_count = 0
        
        total_recipes = len(recipes)
        
        for idx, recipe in enumerate(recipes, 1):
            title = recipe.get('title', 'Unbekannt')
            
            # Progress Bar
            percentage = (idx / total_recipes) * 100
            bar_length = 30
            filled = int(bar_length * idx / total_recipes)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            # Prüfe ob bereits übersetzt (via Original-Titel)
            if title in existing_translations:
                status_icon = "♻️"
                status_text = "bereits übersetzt"
                translated_recipes.append(existing_translations[title])
                reused_count += 1
            else:
                status_icon = "🆕"
                status_text = "neu übersetzen"
                translated = translate_recipe(recipe, deepl_code)
                translated_recipes.append(translated)
                new_count += 1
            
            # Progress Bar ausgeben (überschreibt vorherige Zeile)
            print(f"\r  [{bar}] {percentage:.0f}% | [{idx}/{total_recipes}] {title[:30]:<30} {status_icon}", end='', flush=True)
        
        # Nach der Schleife: Neue Zeile
        print()
        
        # Speichere übersetztes JSON
        output_file = Path(__file__).parent / f"recipes_{lang_code}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(translated_recipes, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Gespeichert: {output_file.name}")
        print(f"   📊 {new_count} neu übersetzt, {reused_count} wiederverwendet")
        print()
    
    print("=" * 50)
    print("🎉 Alle Übersetzungen abgeschlossen!")
    print()
    print("Generierte Dateien:")
    for lang_code in TARGET_LANGUAGES.keys():
        print(f"  - recipes_{lang_code}.json")

if __name__ == "__main__":
    main()
