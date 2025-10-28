# 🥦 VeganTalia Admin

Rezept-Verwaltungs-System für VeganTalia.

## 🚀 Start

### Windows:
```bash
# Im Root-Verzeichnis:
start_admin.bat

# Oder direkt:
cd admin
streamlit run generate_recipe.py
```

### Linux/Mac:
```bash
cd admin
streamlit run generate_recipe.py
```

## 📁 Struktur

```
admin/
├── .streamlit/
│   └── config.toml              ← Streamlit-Konfiguration
├── data/                        ← Zusätzliche Daten (optional)
├── deploy_backup/               ← Deployment-Backups
├── recipes_history/             ← Automatische Versionshistorie
│   ├── recipes_20251028_*.json
│   └── ...
├── generate_recipe.py           ← Haupt-Admin-Script
├── recipes.json                 ← 🔴 Haupt-Datenbank
├── recipes.json.backup          ← Manuelles Backup
├── templates.json               ← Rezept-Vorlagen
├── categories.json              ← Kategorien
├── featured.json                ← Featured Rezepte
└── README.md                    ← Diese Datei
```

## ✨ Features

### Rezept-Management
- ✅ Rezepte erstellen/bearbeiten/löschen
- ✅ Duplikat-Funktion
- ✅ Bulk-Operationen (mehrere Rezepte gleichzeitig bearbeiten)
- ✅ Version History mit Restore-Funktion

### Bild-Verwaltung
- ✅ **4 Bild-Modi:**
  - 📁 Datei hochladen (direkt)
  - 📷 Kamera-Aufnahme (live)
  - 🖼️ Dateiname aus `../src/assets/`
  - 🌐 URL (extern)

### Content-Management
- ✅ Vorlagen-Management (Templates)
- ✅ Kategorien-Verwaltung (add/rename/move/delete)
- ✅ Featured-Rezepte

### KI-Integration
- ✅ Gemini API Assistenten:
  - Zutaten generieren
  - Schritte generieren
  - Nährwerte berechnen
  - Rezept verbessern
  - Beschreibung generieren

### Import/Export
- ✅ JSON Export/Import
- ✅ Backup-System
- ✅ Version History (automatisch bei jedem Speichern)

## 🔧 Konfiguration

### API-Key einrichten
Erstelle/Bearbeite `../config/.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Streamlit-Settings
Die Datei `.streamlit/config.toml` enthält:
```toml
[server]
headless = true
enableCORS = false

[browser]
gatherUsageStats = false

[client]
showErrorDetails = true

[runner]
fastReruns = true
```

## 📊 Tests

```bash
# Backend-Funktions-Tests
python ../tests/test_functions.py

# Health-Check
python ../tests/test_app_health.py
```

**Erwartetes Ergebnis:** 16/16 Tests bestanden

## 🗂️ Daten-Management

### Automatische Backups
Jedes Mal wenn du Rezepte speicherst, wird automatisch ein Backup erstellt in:
```
admin/recipes_history/recipes_YYYYMMDD_HHMMSS.json
```

### Version Restore
1. Öffne Sidebar
2. Klicke auf "⏮️ Version History (Restore)"
3. Wähle eine Version aus
4. Klicke "Restore"

### Manuelles Backup
```bash
# Backup erstellen
cp recipes.json recipes.json.backup

# Backup wiederherstellen
cp recipes.json.backup recipes.json
```

## 🎯 Workflow

### Neues Rezept erstellen:
1. Wähle "Neues Rezept erstellen"
2. Fülle Titel, Kategorie, etc. aus
3. Lade ein Bild hoch (4 Modi verfügbar)
4. Füge Zutaten-Gruppen hinzu
5. Füge Zubereitungsschritte hinzu
6. Optional: KI-Assistenten nutzen
7. Speichern → Automatisches Backup in `recipes_history/`

### Rezept bearbeiten:
1. Wähle "Rezept bearbeiten"
2. Wähle Rezept aus Dropdown
3. Bearbeite Felder
4. Verwende ↑↓ Buttons zum Sortieren
5. Speichern → Neues Backup erstellt

### Bulk-Operationen:
1. Wähle "Rezept löschen"
2. Markiere mehrere Rezepte (Checkboxes)
3. Wähle Aktion (Kategorie ändern, Tag hinzufügen, Exportieren, Löschen)
4. Bestätige

## 🚨 Wichtige Hinweise

- **recipes.json** ist die Haupt-Datenbank - regelmäßig sichern!
- **recipes_history/** wächst mit der Zeit - alte Versionen können gelöscht werden
- **API-Key** niemals in Git committen (`.env` ist in `.gitignore`)
- Bei Problemen: Version History nutzen zum Wiederherstellen

## 🐛 Troubleshooting

### App startet nicht
```bash
# Prüfe ob Streamlit installiert ist
pip list | grep streamlit

# Neu installieren
pip install streamlit

# Port bereits belegt?
streamlit run generate_recipe.py --server.port 8502
```

### Bilder werden nicht angezeigt
- Prüfe ob `../src/assets/` existiert
- Prüfe Dateirechte
- Nutze absolute URLs für externe Bilder

### API-Fehler (Gemini)
- Prüfe ob `../config/.env` existiert
- Prüfe ob API-Key gültig ist
- Prüfe Internet-Verbindung

---

**Erstellt:** Oktober 2025  
**Version:** 2.0  
**Status:** ✅ Produktionsreif
