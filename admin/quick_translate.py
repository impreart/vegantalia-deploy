#!/usr/bin/env python3
"""Quick translation of missing UI keys"""

import json
import os
import deepl
from pathlib import Path

# DeepL API Setup
DEEPL_API_KEY = os.getenv('DEEPL_API_KEY', '48bab1ac-46c3-411b-85f6-1d40aac7a2e9:fx')
translator = deepl.Translator(DEEPL_API_KEY)

# New keys to translate
new_keys = {
    "about.love": "Ganz viel Liebe ❤️ ❤️ ❤️",
    "about.signature": "Eure Waldelfe Talia ❤️",
    "about.connect": "Let's connect",
    "about.newsletter": "Join the fun!",
    "about.newsletterText": "Bleibt auf dem laufenden und meldet euch für den Newsletter an",
    "contact.formName": "Name",
    "contact.formEmail": "E-Mail",
    "contact.formSubject": "Betreff",
    "contact.formMessage": "Nachricht",
    "contact.formSubmit": "Nachricht senden",
    "contact.formRequired": "Pflichtfeld",
    "contact.formRequiredFields": "Pflichtfelder",
    "contact.formMinChars": "Mindestens 10 Zeichen",
    "contact.formSuccess": "Vielen Dank für deine Nachricht! Ich melde mich bald bei dir.",
    "contact.errorNameRequired": "Bitte gib deinen Namen an",
    "contact.errorEmailRequired": "Bitte gib deine E-Mail-Adresse an",
    "contact.errorEmailInvalid": "Bitte gib eine gültige E-Mail-Adresse an",
    "contact.errorSubjectRequired": "Bitte gib einen Betreff an",
    "contact.errorMessageRequired": "Bitte schreibe eine Nachricht",
    "contact.errorMessageTooShort": "Die Nachricht sollte mindestens 10 Zeichen lang sein",
}

# Languages to translate to
languages = {
    "en": "EN",
    "es": "ES",
    "fr": "FR",
    "zh": "ZH",
    "uk": "UK",
    "ar": "AR"
}

def set_nested_key(d, key_path, value):
    """Set a value in a nested dict using dot notation"""
    keys = key_path.split('.')
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value

def main():
    print("🌍 Quick UI Translation")
    print("=" * 50)
    
    # Check quota
    usage = translator.get_usage()
    print(f"\n📊 DeepL Quota:")
    print(f"   Verbraucht: {usage.character.count:,} / 500,000 Zeichen ({usage.character.count/5000:.1f}%)")
    print(f"   Verfügbar: {500000 - usage.character.count:,} Zeichen\n")
    
    for lang_code, deepl_code in languages.items():
        print(f"\n🌐 Übersetze nach {lang_code.upper()}...")
        
        # Load existing translation file
        file_path = Path(__file__).parent.parent / "src" / "lib" / f"ui-translations-{lang_code}.json"
        
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {lang_code: {}}
        
        # Ensure we have the lang_code key
        if lang_code not in data:
            data[lang_code] = {}
        
        # Translate and add missing keys
        for key, german_text in new_keys.items():
            print(f"  ✅ {key}")
            result = translator.translate_text(german_text, target_lang=deepl_code)
            set_nested_key(data[lang_code], key, result.text)
        
        # Save
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"  💾 Gespeichert: {file_path.name}")
    
    # Final quota check
    usage = translator.get_usage()
    print(f"\n📊 Finales DeepL Quota:")
    print(f"   Verbraucht: {usage.character.count:,} / 500,000 Zeichen ({usage.character.count/5000:.1f}%)")
    print(f"\n✅ Fertig!")

if __name__ == "__main__":
    main()
