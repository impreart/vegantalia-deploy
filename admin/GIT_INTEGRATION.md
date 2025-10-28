# 🔄 Git Auto-Commit Integration

## Was ist das?

Jede Änderung an Rezepten, Vorlagen oder Kategorien wird **automatisch als Git-Commit** gespeichert.

## Vorteile

✅ **Vollständige Versionierung** - Jede Änderung ist nachvollziehbar  
✅ **Einfaches Rollback** - Mit Git kannst du zu jeder Version zurück  
✅ **Keine Datenbank nötig** - Bleibt bei einfachen JSON-Dateien  
✅ **Backup durch Git-History** - Zusätzlich zu `recipes_history/`  

## Wie es funktioniert

### Automatische Commits

Wenn du im Admin-Tool etwas speicherst:
```
Admin: Rezepte aktualisiert (47 Rezepte)
Admin: Vorlagen aktualisiert (8 Vorlagen)
Admin: Kategorien aktualisiert (12 Kategorien)
```

### Git-Status in Sidebar

Die Sidebar zeigt dir:
- ✅ **"Git: Alles synchronisiert"** - Keine ungespeicherten Änderungen
- ⚠️ **"Ungespeicherte Git-Änderungen"** - Dateien geändert aber nicht committed
- 📤 **"X Commit(s) bereit zum Push"** - Lokale Commits noch nicht auf GitHub

## Rollback zu vorheriger Version

### Letzte Änderung rückgängig machen:
```bash
cd d:\vegantalia
git checkout HEAD~1 admin/recipes.json
```

### Zu bestimmter Version zurück:
```bash
# Liste alle Commits
git log --oneline admin/recipes.json

# Gehe zu Version zurück (ersetze HASH)
git checkout <HASH> admin/recipes.json
```

### Änderungen anschauen:
```bash
# Was wurde zuletzt geändert?
git diff HEAD~1 admin/recipes.json

# Commit-History anzeigen
git log --oneline --graph admin/recipes.json
```

## Auto-Save Toggle

In der **Sidebar** findest du:

**⚙️ Speicher-Einstellungen**
- 🔄 Auto-Save aktivieren (Checkbox)

### Auto-Save AUS (Standard)
- Du musst **explizit auf "Speichern" klicken**
- Keine nervigen automatischen Speicherungen
- Volle Kontrolle über deine Änderungen

### Auto-Save AN
- Alte Funktion: Änderungen werden sofort gespeichert
- Praktisch wenn du viele kleine Änderungen machst

## Technische Details

### Betroffene Dateien
- `admin/recipes.json` - Alle Rezepte
- `admin/templates.json` - Rezept-Vorlagen
- `admin/categories.json` - Kategorien

### Git-Integration Code
```python
def git_commit_changes(commit_message: str) -> bool:
    # Automatischer Git-Commit nach Speicherung
    # Fügt Dateien hinzu und committed mit Message
```

### Fehlerbehandlung
- Git-Fehler sind **nicht kritisch** - Speichern funktioniert trotzdem
- Falls Git nicht verfügbar: Speichern läuft normal (nur ohne Commit)
- Timeout nach 5 Sekunden verhindert Hänger

## Workflow

1. **Bearbeite** Rezept im Admin-Tool
2. **Klick** auf "Speichern"-Button (wenn Auto-Save AUS)
3. **Git-Commit** erfolgt automatisch
4. **Prüfe** Git-Status in Sidebar
5. **Push** zu GitHub wenn bereit:
   ```bash
   git push
   ```

## Kombiniert mit recipes_history/

Du hast jetzt **ZWEI Backup-Systeme**:

1. **`admin/recipes_history/`**
   - Letzte 10 Versionen als JSON-Dateien
   - Schnelles Restore im Admin-Tool
   - Timestamp-basiert

2. **Git-History**
   - Unbegrenzte Versionen
   - Vollständige Diff-Ansicht
   - Branching möglich

## Nächste Schritte

- [ ] Bei Bedarf: Git-Push Button direkt im Admin-Tool
- [ ] Bei Bedarf: Visualisierung der letzten Commits
- [ ] Bei Bedarf: Branch-Management für Experimente

---

**🎉 Viel Spaß mit der automatischen Versionierung!**
