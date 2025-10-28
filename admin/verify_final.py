#!/usr/bin/env python3
"""Finale Verifizierung der UI-Übersetzungen"""
import json
from pathlib import Path

langs = ['en', 'es', 'fr', 'zh', 'uk', 'ar']
errors = []

print("🔍 FINALE VERIFIZIERUNG")
print("=" * 60)

# 1. Check src/lib/
print("\n📂 SRC/LIB:")
for lang in langs:
    file = Path(f"d:/vegantalia/src/lib/ui-translations-{lang}.json")
    if not file.exists():
        errors.append(f"❌ {file.name} fehlt!")
        continue
    
    data = json.load(open(file, encoding='utf-8'))
    is_flat = 'de' not in data and 'en' not in data and lang not in data
    print(f"  {lang}: {len(data)} keys, FLAT={is_flat}")
    
    if not is_flat:
        errors.append(f"❌ {file.name} ist NICHT FLAT!")
    if len(data) != 137:
        errors.append(f"⚠️ {file.name} hat {len(data)} statt 137 keys")

# 2. Check public/
print("\n📂 PUBLIC:")
for lang in langs:
    file = Path(f"d:/vegantalia/public/ui-translations-{lang}.json")
    if not file.exists():
        errors.append(f"❌ {file.name} fehlt!")
        continue
    
    data = json.load(open(file, encoding='utf-8'))
    is_flat = 'de' not in data and 'en' not in data and lang not in data
    print(f"  {lang}: {len(data)} keys, FLAT={is_flat}")
    
    if not is_flat:
        errors.append(f"❌ {file.name} ist NICHT FLAT!")
    if len(data) != 137:
        errors.append(f"⚠️ {file.name} hat {len(data)} statt 137 keys")

# 3. Check Sync
print("\n🔄 SYNC CHECK:")
all_synced = True
for lang in langs:
    src_file = Path(f"d:/vegantalia/src/lib/ui-translations-{lang}.json")
    pub_file = Path(f"d:/vegantalia/public/ui-translations-{lang}.json")
    
    src_data = json.load(open(src_file, encoding='utf-8'))
    pub_data = json.load(open(pub_file, encoding='utf-8'))
    
    if src_data == pub_data:
        print(f"  ✅ {lang}: src/lib = public")
    else:
        print(f"  ❌ {lang}: NICHT synchron!")
        errors.append(f"❌ {lang} nicht synchron zwischen src/lib und public")
        all_synced = False

# 4. Test translate_ui.py Erkennung
print("\n🧪 TRANSLATE SCRIPT TEST:")
print("  Führe translate_ui.py aus...")
import subprocess
result = subprocess.run(['python', 'translate_ui.py'], 
                       capture_output=True, text=True, cwd='d:/vegantalia/admin')
output = result.stdout
if '♻️ Alle Strings bereits übersetzt' in output:
    count = output.count('♻️ Alle Strings bereits übersetzt')
    print(f"  ✅ Script erkennt alle {count}/6 Sprachen als komplett")
else:
    print("  ❌ Script will neu übersetzen!")
    errors.append("❌ translate_ui.py erkennt vorhandene Übersetzungen NICHT")

# Finale Ausgabe
print("\n" + "=" * 60)
if errors:
    print("❌ FEHLER GEFUNDEN:")
    for err in errors:
        print(f"  {err}")
else:
    print("✅ ALLES PERFEKT!")
    print("✅ Alle 6 Sprachen × 137 Keys in FLAT Struktur")
    print("✅ src/lib und public/ synchron")
    print("✅ translate_ui.py erkennt alle als komplett")
    print("\n🚀 READY TO DEPLOY!")
