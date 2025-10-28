# 🌍 Übersetzungssystem für vegantalia.de

## Hybrid Translation System

Das vegantalia.de Übersetzungssystem verwendet einen **hybriden Ansatz**:

1. **Pre-Translation** (Build-Time): Alle Rezepte werden beim Deployment automatisch übersetzt
2. **Smart Loading** (Runtime): Frontend lädt vorübersetzte JSON-Dateien
3. **Fallback** (Runtime): Bei fehlenden Übersetzungen wird deutsch angezeigt

---

## 🎯 Unterstützte Sprachen

| Sprache | Code | DeepL Code | Status |
|---------|------|------------|--------|
| Deutsch | `de` | - | Original |
| Englisch | `en` | `EN` | ✅ |
| Spanisch | `es` | `ES` | ✅ |
| Französisch | `fr` | `FR` | ✅ |
| Chinesisch (Mandarin) | `zh` | `ZH` | ✅ |
| Ukrainisch | `uk` | `UK` | ✅ |
| Arabisch | `ar` | `AR` | ✅ |

---

## 📦 Deployment Workflow

### Automatische Übersetzung

Bei jedem Deployment (`deploy.sh`) werden automatisch alle Rezepte übersetzt:

```bash
# Im deploy.sh Script:
python admin/translate_all_recipes.py
```

**Output:**
- `admin/recipes_en.json` (Englische Rezepte)
- `admin/recipes_es.json` (Spanische Rezepte)
- `admin/recipes_fr.json` (Französische Rezepte)
- `admin/recipes_zh.json` (Chinesische Rezepte)
- `admin/recipes_uk.json` (Ukrainische Rezepte)
- `admin/recipes_ar.json` (Arabische Rezepte)

### Manuelle Übersetzung

Falls nötig, kannst du die Übersetzung manuell triggern:

```bash
cd admin
python translate_all_recipes.py
```

---

## 🔧 Technische Details

### Translation Script (`translate_all_recipes.py`)

```python
# Übersetzt ALLE Felder:
- title (Rezeptname)
- subtitle (Untertitel)
- ingredients (alle Zutaten in allen Gruppen)
- steps (alle Kochschritte)
- tips (optionale Koch-Tipps)
```

**Metadaten:**
- `language`: Zielsprache (z.B. "en")
- `translation_source`: Immer "deepl"
- `translated_at`: Timestamp der Übersetzung

**Rate Limiting:**
- 0.2-0.3 Sekunden Pause zwischen API-Calls
- Verhindert DeepL Quota-Überschreitung

### Frontend Smart Loading (`src/lib/translations.ts`)

```typescript
// 1. Versuche pre-translated JSON zu laden
fetch(`/admin/recipes_${language}.json`)

// 2. Fallback: Zeige deutsche Originale
fetch('/admin/recipes.json')
```

**Cache:**
- Übersetzungen werden in `localStorage` gecacht
- Cache-Gültigkeit: 30 Tage
- Cache-Key: `vegantalia_translation_cache`

### Language Switcher (`src/components/LanguageSwitcher.tsx`)

**Auto-Erkennung:**
- Nutzt `navigator.language` zur Browser-Sprachen-Erkennung
- Speichert Auswahl in `localStorage` → `vegantalia_language`

**UI:**
- Dropdown mit Flaggen-Emojis
- Checkmark bei aktiver Sprache

---

## 🔑 DeepL API Configuration

### API Key
Die API-Schlüssel werden in `.env` gespeichert:

```bash
# admin/.env
DEEPL_API_KEY=6691c6eb-4838-4310-8154-b6b41fe3bb3a:fx
```

**Free API Tier:**
- Endpoint: `https://api-free.deepl.com/v2/translate`
- Kennzeichen: API-Key endet mit `:fx`
- Limit: 500.000 Zeichen/Monat

### Quota Management

Bei **3 Rezepten** mit durchschnittlich:
- 10 Zutaten × 6 Gruppen = ~300 Zeichen
- 8 Schritte × 100 Zeichen = ~800 Zeichen
- Titel + Subtitle + Tips = ~200 Zeichen

**Pro Rezept:** ~1.300 Zeichen  
**Pro Sprache:** 3 Rezepte × 1.300 = ~3.900 Zeichen  
**Gesamt (6 Sprachen):** 3.900 × 6 = **~23.400 Zeichen**

→ Weit unter dem Free-Tier Limit! ✅

---

## 🧪 Testing

### 1. Lokale Übersetzung testen

```bash
cd admin
python translate_all_recipes.py
```

**Erwartete Dateien:**
- `recipes_en.json`
- `recipes_es.json`
- `recipes_fr.json`
- `recipes_zh.json`
- `recipes_uk.json`
- `recipes_ar.json`

### 2. Frontend testen

```bash
npm run dev
```

1. Öffne Browser → `http://localhost:5173`
2. Klicke auf Language Switcher (🌐)
3. Wähle Sprache → Rezepte sollten übersetzt sein
4. Falls noch nicht deployed: Zeigt deutsche Originale

### 3. DeepL Quota prüfen

```bash
curl -X POST https://api-free.deepl.com/v2/usage \
  -H "Authorization: DeepL-Auth-Key 6691c6eb-4838-4310-8154-b6b41fe3bb3a:fx"
```

**Response:**
```json
{
  "character_count": 23400,
  "character_limit": 500000
}
```

---

## ⚙️ Troubleshooting

### Problem: Übersetzung schlägt fehl

**Fehler:** `HTTPError: 403 Forbidden`

**Lösung:**
- Prüfe API-Key in `admin/.env`
- Prüfe DeepL Quota: https://www.deepl.com/pro-account/usage

---

### Problem: Frontend zeigt deutsche Rezepte trotz englischer Auswahl

**Ursache:** Pre-translated JSONs noch nicht deployed

**Lösung:**
1. Lokal generieren: `python admin/translate_all_recipes.py`
2. Deployment triggern: `bash deploy.sh`
3. Nach Deploy: Cloudflare Pages neu laden

---

### Problem: Browser erkennt falsche Sprache

**Ursache:** `navigator.language` gibt Browser-Sprache zurück

**Lösung:**
- Manuell über Language Switcher wählen
- Auswahl wird in `localStorage` gespeichert

---

## 📝 Best Practices

### Rezepte hinzufügen

1. Rezept in **Deutsch** im Admin-Tool erstellen
2. `recipes.json` speichern
3. **Nicht** manuell "🌍 Übersetzen" klicken!
4. Deployment triggern → Automatische Übersetzung

### Rezepte bearbeiten

1. Bearbeite **nur** das deutsche Original
2. Deployment triggern → Übersetzungen werden aktualisiert
3. Alte Übersetzungen werden überschrieben

### Performance

- Pre-translated JSONs sind **schnell** (kein API-Call)
- Cache reduziert Ladezeiten auf ~5ms
- Lazy Loading nur bei fehlenden Übersetzungen

---

## 🚀 Future Enhancements

Mögliche Erweiterungen:

1. **Live Translation Fallback:**
   - Falls `recipes_${lang}.json` fehlt → Live DeepL API
   - Erfordert Server-Side Proxy (API-Key nicht im Frontend!)

2. **Incremental Translation:**
   - Nur neue/geänderte Rezepte übersetzen
   - Spart DeepL Quota

3. **Translation Memory:**
   - Wiederverwendung häufiger Phrasen
   - "Vegane Butter" → "Vegan butter" (gecacht)

4. **Custom Glossary:**
   - DeepL Glossary für Fachbegriffe
   - "Spätzle" → "Spaetzle" (nicht "noodles")

---

## 📄 Dateien-Übersicht

```
admin/
├── .env                        # DeepL API Key
├── translate_all_recipes.py    # Pre-Translation Script
├── recipes.json                # Deutsche Originale
├── recipes_en.json             # Englische Übersetzungen
├── recipes_es.json             # Spanische Übersetzungen
├── recipes_fr.json             # Französische Übersetzungen
├── recipes_zh.json             # Chinesische Übersetzungen
├── recipes_uk.json             # Ukrainische Übersetzungen
└── recipes_ar.json             # Arabische Übersetzungen

src/
├── lib/
│   └── translations.ts         # Smart Loading + Cache
├── hooks/
│   └── useLanguage.ts          # Language State Hook
└── components/
    └── LanguageSwitcher.tsx    # UI Dropdown

deploy.sh                        # Auto-Translation beim Deploy
```

---

## ✅ Checklist: Übersetzungssystem aktivieren

- [x] DeepL API Key in `admin/.env`
- [x] Translation Script erstellt (`translate_all_recipes.py`)
- [x] Deploy Script erweitert (`deploy.sh`)
- [x] Frontend Smart Loading (`src/lib/translations.ts`)
- [x] Language Switcher UI (`src/components/LanguageSwitcher.tsx`)
- [x] useLanguage Hook (`src/hooks/useLanguage.ts`)
- [x] Rezepte-Seite angepasst (`src/pages/Rezepte.tsx`)
- [x] Index-Seite angepasst (`src/pages/Index.tsx`)
- [x] Recipe-Detail angepasst (`src/pages/RecipeDetail.tsx`)
- [x] `.gitignore` erweitert (`admin/.env` ausschließen)
- [ ] Erster Deployment-Test durchführen
- [ ] DeepL Quota nach Deployment prüfen

---

**Viel Erfolg! 🌍🚀**
