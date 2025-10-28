#!/usr/bin/env python3
"""
UI Translation Script für vegantalia.de
Übersetzt UI-Elemente (Buttons, Labels, etc.) aus ui-translations.json
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# Zielsprachen (wie bei Rezepten)
TARGET_LANGUAGES = {
    'en': 'EN',
    'es': 'ES',
    'fr': 'FR',
    'zh': 'ZH',
    'uk': 'UK',
    'ar': 'AR'
}

def load_env():
    """Lädt .env File"""
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        print("❌ .env File nicht gefunden!")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

def translate_with_deepl(text, target_lang, source_lang="DE"):
    """Übersetzt Text mit DeepL API"""
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("❌ DEEPL_API_KEY nicht in .env gefunden!")
        return text
    
    # Free API hat :fx suffix
    base_url = 'https://api-free.deepl.com/v2/translate' if api_key.endswith(':fx') else 'https://api.deepl.com/v2/translate'
    
    headers = {
        'Authorization': f'DeepL-Auth-Key {api_key}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'text': [text],
        'target_lang': target_lang,
        'source_lang': source_lang,
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('translations'):
                return result['translations'][0]['text']
        elif response.status_code == 456:
            print(f"❌ DeepL Quota erreicht!")
            sys.exit(1)
        else:
            print(f"⚠️ DeepL Fehler {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️ Übersetzung fehlgeschlagen: {e}")
    
    return text  # Fallback: Original zurückgeben

# Globale Zähler für Progress
_translation_count = 0
_total_translations = 0

def count_strings(obj):
    """Zählt alle zu übersetzenden Strings"""
    count = 0
    if isinstance(obj, dict):
        for value in obj.values():
            count += count_strings(value)
    elif isinstance(obj, str) and obj.strip():
        count += 1
    return count

def translate_dict(obj, target_lang, path=""):
    """
    Rekursiv alle String-Werte in einem dict übersetzen
    """
    global _translation_count, _total_translations
    
    if isinstance(obj, dict):
        translated = {}
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            translated[key] = translate_dict(value, target_lang, new_path)
        return translated
    elif isinstance(obj, str):
        # Übersetze nur wenn Text vorhanden
        if obj.strip():
            _translation_count += 1
            percentage = (_translation_count / _total_translations * 100) if _total_translations > 0 else 0
            bar_length = 30
            filled = int(bar_length * _translation_count / _total_translations) if _total_translations > 0 else 0
            bar = '█' * filled + '░' * (bar_length - filled)
            
            # Progress Bar
            print(f"\r  [{bar}] {percentage:.0f}% | {_translation_count}/{_total_translations} | {path[:40]:<40}", end='', flush=True)
            translated = translate_with_deepl(obj, target_lang)
            time.sleep(0.25)  # Rate limiting
            return translated
        return obj
    else:
        return obj

def check_deepl_quota():
    """
    Prüft DeepL API Quota BEVOR Übersetzung startet
    """
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        return None
    
    # Free vs Pro API
    if api_key.endswith(':fx'):
        base_url = "https://api-free.deepl.com/v2/usage"
    else:
        base_url = "https://api.deepl.com/v2/usage"
    
    try:
        headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
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
            elif percentage >= 80:
                print("⚠️ Achtung: Quota zu 80% verbraucht")
            
            return available
        else:
            return None
    except:
        return None

def load_existing_translations(lang_code):
    """Lädt existierende UI-Übersetzungen"""
    ui_file = Path(__file__).parent.parent / "src" / "lib" / f"ui-translations-{lang_code}.json"
    
    if ui_file.exists():
        try:
            with open(ui_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    return None

def main():
    print("🌍 UI Translation Script für vegantalia.de")
    print("=" * 50)
    
    # Lade .env
    load_env()
    
    # Prüfe DeepL Quota
    print()
    check_deepl_quota()
    print()
    
    # Lade deutsche UI-Texte
    ui_file = Path(__file__).parent.parent / "src" / "lib" / "ui-translations.json"
    if not ui_file.exists():
        print(f"❌ {ui_file} nicht gefunden!")
        sys.exit(1)
    
    with open(ui_file, 'r', encoding='utf-8') as f:
        ui_texts = json.load(f)
    
    # Hole deutsche Texte
    de_texts = ui_texts.get('de', {})
    if not de_texts:
        print("❌ Keine deutschen Texte gefunden!")
        sys.exit(1)
    
    print(f"📚 UI-Texte geladen (Deutsch)")
    print()
    
    # Übersetze in alle Sprachen
    global _translation_count, _total_translations
    
    for lang_code, deepl_code in TARGET_LANGUAGES.items():
        print(f"🌐 Übersetze UI nach {lang_code.upper()} ({deepl_code})...")
        
        # Prüfe ob bereits existiert
        existing = load_existing_translations(lang_code)
        
        if existing and existing.get(lang_code):
            print(f"  ♻️ Übersetzung existiert bereits - überspringe")
            print()
            continue
        
        print(f"  🆕 Neue Übersetzung erstellen...")
        
        # Zähle Strings für Progress
        _total_translations = count_strings(de_texts)
        _translation_count = 0
        print(f"  📝 {_total_translations} Texte zu übersetzen")
        
        # Übersetze rekursiv
        translated_texts = translate_dict(de_texts, deepl_code)
        print()  # Neue Zeile nach Progress Bar
        
        # Erstelle vollständiges JSON
        full_json = ui_texts.copy()
        full_json[lang_code] = translated_texts
        
        # Speichere
        output_file = Path(__file__).parent.parent / "src" / "lib" / f"ui-translations-{lang_code}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(full_json, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Gespeichert: {output_file.name}")
        print()
    
    print("=" * 50)
    print("🎉 Alle UI-Übersetzungen abgeschlossen!")
    print()
    print("Generierte Dateien:")
    for lang_code in TARGET_LANGUAGES.keys():
        print(f"  - ui-translations-{lang_code}.json")

if __name__ == "__main__":
    main()
