#!/usr/bin/env python3
"""
Übersetzt flache UI-Struktur mit DeepL
"""

import json
import os
import time
from pathlib import Path

try:
    import deepl
except ImportError:
    print("❌ Fehler: deepl nicht installiert")
    print("Führe aus: pip install deepl")
    exit(1)

# DeepL API
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY', '48bab1ac-46c3-411b-85f6-1d40aac7a2e9:fx')
translator = deepl.Translator(DEEPL_API_KEY)

# Sprachen
LANGUAGES = {
    "en": "EN",
    "es": "ES",
    "fr": "FR",
    "zh": "ZH",
    "uk": "UK",
    "ar": "AR"
}

def show_progress(current, total, prefix=""):
    """Zeigt Fortschrittsbalken"""
    percent = (current / total) * 100
    filled = int(30 * current / total)
    bar = '█' * filled + '░' * (30 - filled)
    print(f"\r  [{bar}] {percent:.0f}% | {current}/{total} {prefix}", end='', flush=True)

def main():
    print("🌍 Flache UI-Übersetzung")
    print("=" * 50)
    
    # Quota check
    try:
        usage = translator.get_usage()
        print(f"\n📊 DeepL Quota:")
        print(f"   Verbraucht: {usage.character.count:,} / 500,000 ({usage.character.count/5000:.1f}%)")
        print(f"   Verfügbar: {500000 - usage.character.count:,}\n")
    except Exception as e:
        print(f"⚠️  Konnte Quota nicht prüfen: {e}\n")
    
    # Lade deutsche Strings
    ui_file = Path(__file__).parent.parent / "src" / "lib" / "ui-translations.json"
    with open(ui_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    german_strings = data['de']
    total_keys = len(german_strings)
    print(f"📚 {total_keys} deutsche Strings geladen\n")
    
    # Übersetze für jede Sprache
    for lang_code, deepl_code in LANGUAGES.items():
        print(f"🌐 Übersetze nach {lang_code.upper()} ({deepl_code})...")
        
        translations = {}
        current = 0
        
        for key, german_text in german_strings.items():
            current += 1
            show_progress(current, total_keys, f"| {key[:20]}...")
            
            try:
                result = translator.translate_text(german_text, target_lang=deepl_code)
                translations[key] = result.text
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"\n  ❌ Fehler bei {key}: {e}")
                translations[key] = german_text  # Fallback
        
        print()  # Neue Zeile nach Progress
        
        # Speichere
        output_file = Path(__file__).parent.parent / "src" / "lib" / f"ui-translations-{lang_code}.json"
        output_data = {lang_code: translations}
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ Gespeichert: {output_file.name}\n")
    
    # Final quota
    try:
        usage = translator.get_usage()
        print(f"📊 Finales DeepL Quota:")
        print(f"   Verbraucht: {usage.character.count:,} / 500,000 ({usage.character.count/5000:.1f}%)")
    except:
        pass
    
    print("\n✅ Übersetzung abgeschlossen!")

if __name__ == "__main__":
    main()
