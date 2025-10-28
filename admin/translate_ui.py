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
from typing import Dict, Any, Optional

# Zielsprachen (wie bei Rezepten)
TARGET_LANGUAGES = {
    'en': 'EN',
    'es': 'ES',
    'fr': 'FR',
    'zh': 'ZH',
    'uk': 'UK',
    'ar': 'AR'
}

def load_env() -> None:
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

def translate_with_deepl(text: str, target_lang: str, source_lang: str = "DE") -> str:
    """
    Übersetzt Text mit DeepL API
    
    Args:
        text: Zu übersetzender Text
        target_lang: Zielsprache (z.B. "EN", "ES", "FR")
        source_lang: Quellsprache (Standard: "DE")
    
    Returns:
        Übersetzter Text oder Originaltext bei Fehler
    
    Raises:
        ValueError: Wenn text leer oder kein String
        Exception: Wenn DeepL Quota erreicht
    """
    # Input-Validierung
    if not text or not isinstance(text, str) or not text.strip():
        return text
    
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        raise ValueError("DEEPL_API_KEY nicht in .env gefunden!")
    
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
            raise Exception("DeepL Quota erreicht!")
        else:
            print(f"⚠️ DeepL Fehler {response.status_code}: {response.text}")
    except Exception as e:
        if "Quota erreicht" in str(e):
            raise  # Re-raise um Script zu stoppen
        print(f"⚠️ Übersetzung fehlgeschlagen: {e}")
    
    return text  # Fallback: Original zurückgeben

def count_strings(obj: Any) -> int:
    """
    Zählt alle zu übersetzenden Strings
    
    Args:
        obj: Dictionary oder beliebiger Wert
    
    Returns:
        Anzahl der nicht-leeren Strings
    """
    count = 0
    if isinstance(obj, dict):
        for value in obj.values():
            count += count_strings(value)
    elif isinstance(obj, str) and obj.strip():
        count += 1
    return count

class TranslationProgress:
    """Verwaltet den Übersetzungsfortschritt thread-safe"""
    def __init__(self, total: int):
        """
        Initialisiert Progress Tracker
        
        Args:
            total: Gesamtanzahl der zu übersetzenden Strings
        """
        self.count = 0
        self.total = total
    
    def increment(self) -> int:
        """
        Erhöht den Zähler und gibt den aktuellen Wert zurück
        
        Returns:
            Aktueller Zählerstand
        """
        self.count += 1
        return self.count
    
    def get_percentage(self) -> float:
        """Berechnet den Fortschritt in Prozent"""
        if self.total == 0:
            return 0.0
        return (self.count / self.total) * 100
    
    def show_progress(self, label: str = "") -> None:
        """
        Zeigt den Fortschrittsbalken an
        
        Args:
            label: Optionales Label für die aktuelle Übersetzung
        """
        percentage = self.get_percentage()
        bar_length = 30
        filled = int(bar_length * self.count / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Progress Bar
        label_truncated = label[:40] if label else ""
        print(f"\r  [{bar}] {percentage:.0f}% | {self.count}/{self.total} | {label_truncated:<40}", end='', flush=True)

def translate_dict(obj: Any, target_lang: str, progress: TranslationProgress, path: str = "") -> Any:
    """
    Rekursiv alle String-Werte in einem dict übersetzen
    
    Args:
        obj: Dictionary oder String zum Übersetzen
        target_lang: Zielsprache (z.B. "EN-US", "ES", "FR")
        progress: TranslationProgress Instanz für Fortschrittsanzeige
        path: Aktueller Pfad im Dictionary (für Debug-Ausgabe)
    
    Returns:
        Übersetztes Dictionary oder String
    """
    if isinstance(obj, dict):
        translated = {}
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            translated[key] = translate_dict(value, target_lang, progress, new_path)
        return translated
    elif isinstance(obj, str):
        # Übersetze nur wenn Text vorhanden
        if obj.strip():
            progress.increment()
            progress.show_progress(path)
            translated = translate_with_deepl(obj, target_lang)
            time.sleep(0.25)  # Rate limiting
            return translated
        return obj
    else:
        return obj

def check_deepl_quota() -> Optional[int]:
    """
    Prüft DeepL API Quota BEVOR Übersetzung startet
    
    Returns:
        Verfügbare Zeichen oder None bei Fehler
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

def load_existing_translations(lang_code: str) -> Dict[str, Any]:
    """
    Lädt existierende UI-Übersetzungen
    
    Args:
        lang_code: Sprachcode (z.B. "en", "es", "fr")
    
    Returns:
        Dictionary mit Übersetzungen oder leeres Dict
    """
    ui_file = Path(__file__).parent.parent / "src" / "lib" / f"ui-translations-{lang_code}.json"
    
    if ui_file.exists():
        try:
            with open(ui_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(lang_code, {})
        except:
            pass
    
    return {}

def find_missing_keys(source_dict: Dict[str, Any], translated_dict: Dict[str, Any], path: str = "") -> Dict[str, Any]:
    """
    Findet fehlende Keys rekursiv.
    
    Args:
        source_dict: Quell-Dictionary (deutsch)
        translated_dict: Übersetztes Dictionary
        path: Aktueller Pfad im Dictionary (für Debug)
    
    Returns:
        Dictionary mit nur den fehlenden/neuen Einträgen
    """
    missing = {}
    
    for key, value in source_dict.items():
        current_path = f"{path}.{key}" if path else key
        
        if key not in translated_dict:
            # Komplett fehlend
            missing[key] = value
        elif isinstance(value, dict) and isinstance(translated_dict[key], dict):
            # Rekursiv prüfen
            nested_missing = find_missing_keys(value, translated_dict[key], current_path)
            if nested_missing:
                missing[key] = nested_missing
        # WICHTIG: String-Änderungen NICHT als fehlend markieren!
        # Übersetzungen sind IMMER unterschiedlich zum deutschen Original
        # Nur komplett fehlende Keys werden übersetzt
    
    return missing

def merge_dicts(base_dict: Dict[str, Any], new_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merged zwei dicts rekursiv
    
    Args:
        base_dict: Basis-Dictionary
        new_dict: Dictionary mit neuen/überschreibenden Werten
    
    Returns:
        Gemergtes Dictionary
    """
    result = base_dict.copy()
    
    for key, value in new_dict.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def main() -> None:
    """Hauptfunktion - Übersetzt UI-Strings in alle Zielsprachen"""
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
        de_texts = json.load(f)
    
    if not de_texts:
        print("❌ Keine deutschen Texte gefunden!")
        sys.exit(1)
    
    print(f"📚 UI-Texte geladen (Deutsch)")
    print()
    
    # Übersetze in alle Sprachen
    for lang_code, deepl_code in TARGET_LANGUAGES.items():
        print(f"🌐 Übersetze UI nach {lang_code.upper()} ({deepl_code})...")
        
        # Lade existierende Übersetzungen
        existing_translations = load_existing_translations(lang_code)
        
        # Finde fehlende/neue Strings
        missing_strings = find_missing_keys(de_texts, existing_translations)
        
        if not missing_strings:
            print(f"  ♻️ Alle Strings bereits übersetzt - nichts zu tun")
            print()
            continue
        
        # Zähle wie viele Strings fehlen
        missing_count = count_strings(missing_strings)
        existing_count = count_strings(existing_translations)
        total_count = count_strings(de_texts)
        
        print(f"  📊 Status: {existing_count}/{total_count} bereits übersetzt")
        print(f"  🆕 {missing_count} neue/geänderte Strings zu übersetzen")
        
        # Erstelle Progress Tracker
        progress = TranslationProgress(missing_count)
        
        # Übersetze nur die fehlenden Strings
        newly_translated = translate_dict(missing_strings, deepl_code, progress)
        print()  # Neue Zeile nach Progress Bar
        
        # Merge mit existierenden Übersetzungen
        complete_translations = merge_dicts(existing_translations, newly_translated)
        
        # Erstelle JSON mit nur dieser Sprache
        output_json = {lang_code: complete_translations}
        
        # Speichere
        output_file = Path(__file__).parent.parent / "src" / "lib" / f"ui-translations-{lang_code}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_json, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Gespeichert: {output_file.name} ({existing_count} wiederverwendet + {missing_count} neu)")
        print()
    
    print("=" * 50)
    print("🎉 Alle UI-Übersetzungen abgeschlossen!")
    print()
    print("Generierte Dateien:")
    for lang_code in TARGET_LANGUAGES.keys():
        print(f"  - ui-translations-{lang_code}.json")

if __name__ == "__main__":
    main()
