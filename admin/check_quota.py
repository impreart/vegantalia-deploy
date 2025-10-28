#!/usr/bin/env python3
"""
Quota Check Script - Prüft DeepL API Verfügbarkeit
"""

import os
import sys
import requests
from pathlib import Path

def load_env():
    """Lädt .env File"""
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        print("❌ .env nicht gefunden!")
        sys.exit(1)
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

def main():
    print("🔍 DeepL Quota Check")
    print("=" * 50)
    
    load_env()
    
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("❌ DEEPL_API_KEY nicht gefunden!")
        sys.exit(1)
    
    # Free vs Pro API
    if api_key.endswith(':fx'):
        base_url = "https://api-free.deepl.com/v2/usage"
        print("📌 API Typ: Free")
    else:
        base_url = "https://api.deepl.com/v2/usage"
        print("📌 API Typ: Pro")
    
    print()
    
    try:
        headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
        response = requests.get(base_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            used = data.get('character_count', 0)
            limit = data.get('character_limit', 500000)
            available = limit - used
            percentage = (used / limit * 100) if limit > 0 else 0
            
            print(f"✅ API Verbindung erfolgreich!")
            print()
            print(f"📊 Quota Details:")
            print(f"   Verbraucht: {used:,} Zeichen")
            print(f"   Limit:      {limit:,} Zeichen")
            print(f"   Verfügbar:  {available:,} Zeichen")
            print(f"   Nutzung:    {percentage:.1f}%")
            print()
            
            # Visualisierung
            bar_length = 40
            filled = int(bar_length * percentage / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"   [{bar}] {percentage:.1f}%")
            print()
            
            if percentage >= 95:
                print("🚨 WARNUNG: Quota fast aufgebraucht (>95%)!")
            elif percentage >= 80:
                print("⚠️ Achtung: Quota zu 80% verbraucht")
            elif percentage >= 50:
                print("ℹ️ Quota zur Hälfte verbraucht")
            else:
                print("✅ Quota hat ausreichend Kapazität")
            
        elif response.status_code == 403:
            print("❌ Authentifizierung fehlgeschlagen!")
            print("   Prüfe deinen API Key in der .env Datei")
        else:
            print(f"❌ API Fehler: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Timeout: DeepL API antwortet nicht")
    except Exception as e:
        print(f"❌ Fehler: {e}")

if __name__ == "__main__":
    main()
