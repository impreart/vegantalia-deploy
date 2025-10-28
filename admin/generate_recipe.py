import streamlit as st
import json
import base64
import os
import time
import sys
import subprocess

from typing import Dict, List, Optional, Union
from datetime import datetime

# Git Auto-Commit Helper
def git_commit_changes(commit_message: str) -> bool:
    """Automatischer Git-Commit nach Speicherung.
    
    Args:
        commit_message: Die Commit-Nachricht
        
    Returns:
        bool: True wenn erfolgreich, False bei Fehler
    """
    try:
        # Gehe zum Projekt-Root (eins über admin/)
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Git add (nur admin/recipes.json und templates.json)
        subprocess.run(
            ["git", "add", "admin/recipes.json", "admin/templates.json", "admin/categories.json"],
            cwd=repo_root,
            capture_output=True,
            timeout=5
        )
        
        # Git commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_root,
            capture_output=True,
            timeout=5,
            text=True
        )
        
        # Erfolg wenn Returncode 0 ODER "nothing to commit" (kein Fehler)
        if result.returncode == 0:
            return True
        elif "nothing to commit" in result.stdout.lower():
            return True  # Keine Änderungen, aber kein Fehler
        else:
            return False
            
    except Exception as e:
        # Fehler beim Git-Commit sind nicht kritisch - speichern war ja erfolgreich
        return False

# Small helper to safely request a rerun across Streamlit versions
def safe_rerun():
    try:
        # Preferred API
        if hasattr(st, 'experimental_rerun'):
            st.experimental_rerun()
            return
        # Newer versions may have 'rerun'
        if hasattr(st, 'rerun'):
            st.rerun()
            return
        # Fallback: try to set a query param to nudge a reload
        try:
            st.experimental_set_query_params(_refresh=int(time.time()))
        except Exception:
            # Last resort: stop execution (user can reload manually)
            try:
                st.stop()
            except Exception:
                pass
    except Exception:
        # Swallow any exception to avoid breaking the UI
        try:
            st.write("Bitte die Seite manuell neu laden.")
        except Exception:
            pass

# Initialize session state
if 'edit_index' not in st.session_state:
    st.session_state['edit_index'] = None
if 'preview_recipe' not in st.session_state:
    st.session_state['preview_recipe'] = None
if 'auto_save_enabled' not in st.session_state:
    st.session_state['auto_save_enabled'] = False  # Default: Auto-Save AUS

def process_form_transfer(parsed):
    """Verarbeitet die Übertragung von Rezeptdaten in Formularfelder.
    
    Args:
        parsed: Dictionary mit Rezeptdaten
        
    Returns:
        bool: True wenn erfolgreich übertragen
    """
    try:
        # Mapping von JSON zu Formularfeldern
        field_map = {
            "title": "Titel des Rezepts*",
            "subtitle": "Untertitel", 
            "category": "Kategorie",
            "preparationTime": "Vorbereitungszeit (z. B. 10 Min)",
            "cookTime": "Kochzeit (z. B. 30 Min)",
            "portion": "portion_value",  # GEÄNDERT: Verwende neuen Key
            "difficulty": "Schwierigkeitsgrad",
            "tips": "Tipps oder Varianten"
        }
        
        # Kopiere Hauptfelder
        for json_field, form_field in field_map.items():
            value = parsed.get(json_field)
            if value is not None:
                st.session_state[form_field] = value
        
        # Kopiere Bild (falls vorhanden)
        if parsed.get("image"):
            st.session_state["transferred_image"] = parsed["image"]
        
        # Kopiere Nährwerte
        nutr = parsed.get("nutrition", {})
        for key in ["kcal", "protein", "carbs", "fat", "fiber"]:
            if key in nutr:
                st.session_state[key] = int(nutr[key]) if nutr[key] else 0
                
        # Kopiere Zutaten - stelle Min-Werte sicher
        ingredients = parsed.get("ingredients", [])
        if ingredients and len(ingredients) > 0:
            st.session_state["num_groups"] = max(1, len(ingredients))
            for i, group in enumerate(ingredients):
                st.session_state[f"groupname_{i}"] = group.get("group", "")
                items = group.get("items", [])
                st.session_state[f"items_{i}"] = max(1, len(items))
                for j, item in enumerate(items):
                    st.session_state[f"amount_{i}_{j}"] = str(item.get("amount", ""))
                    st.session_state[f"unit_{i}_{j}"] = str(item.get("unit", ""))
                    st.session_state[f"name_{i}_{j}"] = str(item.get("name", ""))
        else:
            # Setze Minimalwerte wenn keine Zutaten vorhanden
            st.session_state["num_groups"] = 1
            st.session_state["items_0"] = 1
                    
        # Kopiere Schritte - stelle Min-Werte sicher
        steps = parsed.get("steps", [])
        if steps and len(steps) > 0:
            st.session_state["num_steps"] = max(1, len(steps))
            for s, step in enumerate(steps):
                st.session_state[f"time_{s}"] = str(step.get("time", "10 Min"))
                needed = step.get("needed", [])
                st.session_state[f"needed_{s}"] = len(needed)
                for n, need in enumerate(needed):
                    st.session_state[f"n_amount_{s}_{n}"] = str(need.get("amount", ""))
                    st.session_state[f"n_unit_{s}_{n}"] = str(need.get("unit", ""))
                    st.session_state[f"n_name_{s}_{n}"] = str(need.get("name", ""))
                substeps = step.get("substeps", [])
                st.session_state[f"num_substeps_{s}"] = max(1, len(substeps))
                for subi, subv in enumerate(substeps):
                    st.session_state[f"subtext_{s}_{subi}"] = str(subv)
        else:
            # Setze Minimalwerte wenn keine Schritte vorhanden
            st.session_state["num_steps"] = 1
            st.session_state["num_substeps_0"] = 1
        
        # Markiere erfolgreiche Übertragung
        st.session_state["form_transfer_success"] = True
        return True
        
    except Exception as e:
        st.error(f"❌ Fehler beim Übertragen der Daten: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False

# Verarbeite ausstehende Änderungen am Anfang
if "pending_nutrition" in st.session_state:
    nutr = st.session_state.pop("pending_nutrition")
    for key in ["kcal", "protein", "carbs", "fat", "fiber"]:
        st.session_state[key] = nutr.get(key, 0)

if "pending_form_transfer" in st.session_state:
    parsed = st.session_state.pop("pending_form_transfer")
    process_form_transfer(parsed)

# optional imports (we import lazily and offer installation in the UI)
requests = None
BeautifulSoup = None
genai = None

def auto_install_and_update():
    """Automatische Installation und Update-Prüfung für alle Abhängigkeiten."""
    required_packages = {
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'google-generativeai': 'google.generativeai'
    }
    
    missing = []
    outdated = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    # Installiere fehlende Pakete
    if missing:
        st.info(f"📦 Installiere fehlende Pakete: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing, 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            st.success(f"✅ {len(missing)} Paket(e) erfolgreich installiert!")
            st.info("🔄 Bitte die App neu starten (Strg+R oder F5)")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Installation fehlgeschlagen: {e}")
            return False
    
    # UPDATE-CHECK DEAKTIVIERT (verlangsamt Start)
    # Um zu aktivieren: "if False" in "if True" ändern
    if False and 'update_check_done' not in st.session_state:
        st.session_state['update_check_done'] = True
        with st.spinner("� Prüfe Updates..."):
            try:
                # Hole installierte Versionen
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    outdated_json = json.loads(result.stdout)
                    outdated_relevant = [pkg for pkg in outdated_json if pkg['name'] in required_packages.keys()]
                    
                    if outdated_relevant:
                        outdated_names = [pkg['name'] for pkg in outdated_relevant]
                        st.info(f"🆙 Updates verfügbar für: {', '.join(outdated_names)}")
                        
                        if st.button("⬆️ Jetzt aktualisieren"):
                            try:
                                subprocess.check_call(
                                    [sys.executable, "-m", "pip", "install", "--upgrade"] + outdated_names,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                                )
                                st.success("✅ Pakete erfolgreich aktualisiert!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Update fehlgeschlagen: {e}")
            except Exception:
                pass  # Stille Update-Prüfung, kein Fehler bei Timeout
    
    return True

def check_dependencies():
    """Überprüfe alle benötigten Abhängigkeiten und biete Installation an."""
    # Rufe automatische Installation auf
    if not auto_install_and_update():
        st.stop()
        return False
    
    # Importiere nach Installation
    missing = try_import_optional()
    if missing:
        st.warning("⚠️ Einige Pakete konnten nicht importiert werden")
        st.write("Folgende Pakete fehlen noch:", missing)
        if st.button("🔄 Erneut versuchen"):
            st.rerun()
        st.stop()
        return False
    return True

## removed duplicate install_packages (see unified implementation below)

def try_import_optional():
    global requests, BeautifulSoup, genai
    missing = []
    try:
        import requests as _requests
        requests = _requests
    except Exception:
        missing.append("requests")
    try:
        from bs4 import BeautifulSoup as _bs
        BeautifulSoup = _bs
    except Exception:
        missing.append("beautifulsoup4")
    try:
        import google.generativeai as _genai
        genai = _genai
    except Exception:
        missing.append("google-generativeai")
    # openai is imported on demand in call_openai_chat
    return missing

def install_packages(packages):
    """Install packages via pip (may require restart). Returns (ok, output)."""
    python = sys.executable or "python"
    cmd = [python, "-m", "pip", "install"] + packages
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        ok = proc.returncode == 0
        out = proc.stdout + "\n" + proc.stderr
        return ok, out
    except Exception as e:
        return False, str(e)
from datetime import datetime

# ====== Datei-Konstanten ======
RECIPES_FILE = "recipes.json"  # Jetzt im gleichen Ordner (admin/)
CONFIG_FILE = os.path.join("..", "config", ".env")  # Eine Ebene höher
PLACEHOLDER_IMAGE = os.path.join("..", "src", "assets", "foto-folgt.png")  # Fallback-Bild

# ====== Hilfsfunktionen ======
def get_image_display(recipe_dict, width=200):
    """
    Gibt den Pfad für st.image() zurück.
    Falls kein Bild vorhanden, wird Placeholder verwendet.
    """
    image_data = recipe_dict.get("image", "")
    if image_data and image_data.strip():  # Prüfe auf nicht-leeren String
        # Base64-kodiertes Bild
        return "data:image/png;base64," + image_data
    else:
        # Fallback auf foto-folgt.png
        script_dir = os.path.dirname(os.path.abspath(__file__))
        placeholder_path = os.path.join(script_dir, "..", "src", "assets", "foto-folgt.png")
        if os.path.exists(placeholder_path):
            return placeholder_path
        else:
            return None  # Kein Bild verfügbar

def load_api_key():
    """Lädt den API-Key aus der Konfigurationsdatei oder Umgebungsvariable."""
    # Zuerst aus Umgebungsvariable
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        # Configure genai if available
        if genai:
            try:
                genai.configure(api_key=key)
            except Exception:
                pass
        return key
        
    # Dann aus Konfigurationsdatei
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                for line in f:
                    if line.startswith('GOOGLE_API_KEY='):
                        key = line.split('=', 1)[1].strip()
                        os.environ["GOOGLE_API_KEY"] = key  # In Umgebung setzen
                        # Configure genai if available
                        if genai:
                            try:
                                genai.configure(api_key=key)
                            except Exception:
                                pass
                        return key
        except Exception:
            pass
    return None

# ====== Hilfsfunktionen ======
@st.cache_data(ttl=10)  # Cache für 10 Sekunden
def load_recipes():
    if os.path.exists(RECIPES_FILE):
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data(ttl=10)
def load_templates():
    """Lädt benutzerdefinierte Vorlagen aus templates.json."""
    template_file = os.path.join(os.path.dirname(__file__), "admin", "templates.json")
    if os.path.exists(template_file):
        try:
            with open(template_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_templates(templates):
    """Speichert benutzerdefinierte Vorlagen in templates.json mit Git-Integration."""
    # Script liegt bereits in admin/, also direkt templates.json verwenden
    template_file = os.path.join(os.path.dirname(__file__), "templates.json")
    try:
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
        
        # Git Auto-Commit
        git_commit_changes(f"Admin: Vorlagen aktualisiert ({len(templates)} Vorlagen)")
        return True
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern der Vorlagen: {e}")
        return False

@st.cache_data(ttl=10)
def load_categories():
    """Lädt benutzerdefinierte Kategorien aus categories.json."""
    # Script liegt in admin/, categories.json ist im gleichen Ordner
    categories_file = os.path.join(os.path.dirname(__file__), "categories.json")
    if os.path.exists(categories_file):
        try:
            with open(categories_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            # Fallback zu Standard-Kategorien
            return ["Hauptgerichte", "Vorspeisen", "Desserts", "Salate & Vorspeisen", 
                   "Suppen & Eintöpfe", "Snacks & Fingerfood", "Getränke"]
    # Standard-Kategorien wenn Datei nicht existiert
    return ["Hauptgerichte", "Vorspeisen", "Desserts", "Salate & Vorspeisen", 
           "Suppen & Eintöpfe", "Snacks & Fingerfood", "Getränke"]

def save_categories(categories):
    """Speichert benutzerdefinierte Kategorien in categories.json mit Git-Integration."""
    # Script liegt in admin/, categories.json ist im gleichen Ordner
    categories_file = os.path.join(os.path.dirname(__file__), "categories.json")
    try:
        with open(categories_file, "w", encoding="utf-8") as f:
            json.dump(categories, f, ensure_ascii=False, indent=2)
        
        # Git Auto-Commit
        git_commit_changes(f"Admin: Kategorien aktualisiert ({len(categories)} Kategorien)")
        return True
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern der Kategorien: {e}")
        return False

def save_recipes(recipes, force_save=False):
    """Speichert Rezepte in recipes.json mit Fehlerbehandlung und Git-Integration.
    
    Args:
        recipes: Liste der Rezepte
        force_save: Wenn True, speichert ohne Bestätigung (expliziter Save-Button)
    """
    # Nur speichern wenn:
    # 1. force_save=True (expliziter Save-Button) ODER
    # 2. Auto-Save aktiviert ist
    if not force_save and not st.session_state.get('auto_save_enabled', False):
        return False  # Stillschweigend nicht speichern
        
    try:
        # Backup erstellen (für Version History)
        if os.path.exists(RECIPES_FILE):
            # recipes_history ist jetzt im gleichen Ordner (admin/)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backup_dir = os.path.join(script_dir, "recipes_history")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"recipes_{timestamp}.json")
            
            import shutil
            shutil.copy2(RECIPES_FILE, backup_file)
            
            # Halte nur die letzten 10 Backups
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("recipes_")])
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    try:
                        os.remove(os.path.join(backup_dir, old_backup))
                    except:
                        pass
        
        # Speichern
        with open(RECIPES_FILE, "w", encoding="utf-8") as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
        
        # Verifizieren
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            if len(saved_data) == len(recipes):
                # ✨ GIT AUTO-COMMIT ✨
                git_commit_changes(f"Admin: Rezepte aktualisiert ({len(recipes)} Rezepte)")
                
                # 🗺️ SITEMAP REGENERIEREN
                try:
                    import subprocess
                    sitemap_script = os.path.join(os.path.dirname(__file__), "generate_sitemap.py")
                    if os.path.exists(sitemap_script):
                        subprocess.run([sys.executable, sitemap_script], check=True, capture_output=True)
                except Exception as e:
                    # Sitemap-Fehler sollten nicht das Speichern verhindern
                    print(f"⚠️ Sitemap-Generierung fehlgeschlagen: {e}")
                
                return True
            else:
                st.error(f"⚠️ Verifizierung fehlgeschlagen: {len(saved_data)} statt {len(recipes)} Rezepte")
                return False
                
    except PermissionError:
        st.error(f"❌ Keine Schreibberechtigung für {RECIPES_FILE}")
        st.info("💡 Tipp: Starte die App als Administrator oder ändere Dateiberechtigungen")
        return False
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern: {e}")
        import traceback
        with st.expander("🔍 Technische Details"):
            st.code(traceback.format_exc())
        return False

def add_metadata_to_recipe(recipe, is_new=True):
    """Fügt automatisch Metadaten zu einem Rezept hinzu."""
    now = datetime.now().isoformat()
    
    if is_new:
        # Neues Rezept
        recipe["created_at"] = now
        recipe["updated_at"] = now
        recipe["version"] = 1
    else:
        # Bestehendes Rezept
        recipe["updated_at"] = now
        recipe["version"] = recipe.get("version", 1) + 1
    
    return recipe

def validate_recipe(recipe):
    """Validiert ein Rezept und gibt Warnungen/Fehler zurück."""
    errors = []
    warnings = []
    
    # Kritische Fehler (sollten behoben werden)
    if not recipe.get("title") or not recipe.get("title").strip():
        errors.append("❌ Kein Titel angegeben")
    
    if not recipe.get("ingredients") or len(recipe.get("ingredients", [])) == 0:
        errors.append("❌ Keine Zutaten vorhanden")
    else:
        # Prüfe ob mindestens eine Zutat mit Name existiert
        has_ingredient = False
        for group in recipe.get("ingredients", []):
            for item in group.get("items", []):
                if item.get("name", "").strip():
                    has_ingredient = True
                    break
        if not has_ingredient:
            errors.append("❌ Keine benannten Zutaten gefunden")
    
    if not recipe.get("steps") or len(recipe.get("steps", [])) == 0:
        errors.append("❌ Keine Zubereitungsschritte vorhanden")
    
    # Warnungen (optional, aber empfohlen)
    if not recipe.get("image") and not recipe.get("image_filename") and not recipe.get("image_url"):
        warnings.append("⚠️ Kein Bild vorhanden")
    
    if not recipe.get("category") or not recipe.get("category").strip():
        warnings.append("⚠️ Keine Kategorie angegeben")
    
    nutr = recipe.get("nutrition", {})
    if not nutr or all(v == 0 for v in nutr.values()):
        warnings.append("⚠️ Keine Nährwerte angegeben")
    
    if not recipe.get("preparationTime") and not recipe.get("cookTime"):
        warnings.append("⚠️ Keine Zeitangaben")
    
    if not recipe.get("tips") or not recipe.get("tips").strip():
        warnings.append("💡 Keine Tipps/Varianten angegeben")
    
    return {"errors": errors, "warnings": warnings}

def generate_seo_metadata(recipe):
    """Generiert SEO-Metadaten für ein Rezept."""
    # Meta Description (max 160 Zeichen)
    title = recipe.get("title", "Rezept")
    subtitle = recipe.get("subtitle", "")
    category = recipe.get("category", "")
    
    desc_parts = [title]
    if subtitle:
        desc_parts.append(subtitle)
    if category:
        desc_parts.append(f"({category})")
    
    meta_description = " - ".join(desc_parts)
    if len(meta_description) > 160:
        meta_description = meta_description[:157] + "..."
    
    # Keywords (aus Titel, Kategorie, Tags, Zutaten)
    keywords = [title.lower()]
    if category:
        keywords.append(category.lower())
    if recipe.get("tags"):
        keywords.extend(recipe["tags"])
    
    # Top 5 Zutaten als Keywords
    for group in recipe.get("ingredients", [])[:1]:  # Nur erste Gruppe
        for item in group.get("items", [])[:5]:
            ingr_name = item.get("name", "").strip().lower()
            if ingr_name:
                keywords.append(ingr_name)
    
    keywords = list(set(keywords))[:10]  # Max 10 Keywords
    
    # Schema.org JSON-LD (Google Rich Snippets)
    schema_org = {
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": title,
        "description": meta_description,
        "recipeCategory": category,
        "recipeCuisine": "Vegan",
        "recipeYield": f"{recipe.get('portion', 1)} Portionen",
        "prepTime": recipe.get("preparationTime", ""),
        "cookTime": recipe.get("cookTime", ""),
        "recipeIngredient": [],
        "recipeInstructions": []
    }
    
    # Zutaten für Schema
    for group in recipe.get("ingredients", []):
        for item in group.get("items", []):
            amount = item.get("amount", "")
            unit = item.get("unit", "")
            name = item.get("name", "")
            if name:
                schema_org["recipeIngredient"].append(f"{amount} {unit} {name}".strip())
    
    # Schritte für Schema
    for i, step in enumerate(recipe.get("steps", []), 1):
        for substep in step.get("substeps", []):
            schema_org["recipeInstructions"].append({
                "@type": "HowToStep",
                "text": substep
            })
    
    # Nährwerte für Schema
    if recipe.get("nutrition"):
        nutr = recipe["nutrition"]
        schema_org["nutrition"] = {
            "@type": "NutritionInformation",
            "calories": f"{nutr.get('kcal', 0)} kcal",
            "proteinContent": f"{nutr.get('protein', 0)}g",
            "carbohydrateContent": f"{nutr.get('carbs', 0)}g",
            "fatContent": f"{nutr.get('fat', 0)}g",
            "fiberContent": f"{nutr.get('fiber', 0)}g"
        }
    
    return {
        "meta_description": meta_description,
        "keywords": keywords,
        "schema_org": schema_org
    }

def encode_image_to_base64(image_file):
    if image_file is None:
        return ""
    return base64.b64encode(image_file.read()).decode("utf-8")

def decode_image(base64_str):
    if not base64_str:
        return None
    return base64.b64decode(base64_str)

# ----- Bilder-Verwaltung -----
def save_recipe_image(image_file, recipe_slug):
    """Speichert Bild als Datei im public/recipe-images/ Ordner.
    
    Args:
        image_file: Streamlit UploadedFile oder File-Like Object
        recipe_slug: Eindeutiger Slug für das Rezept
        
    Returns:
        str: Dateiname des gespeicherten Bildes (z.B. "kaesespaetzle-vegan-1234.jpg")
    """
    try:
        from PIL import Image
        import io
        from datetime import datetime
        
        # Projekt-Root ermitteln (eins über admin/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        images_dir = os.path.join(project_root, "public", "recipe-images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Bild laden
        image = Image.open(image_file)
        
        # Konvertiere zu RGB (wichtig für WebP)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        
        # Skaliere auf max 1200px Breite (für Performance)
        max_width = 1200
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Generiere Dateinamen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{recipe_slug}_{timestamp}.webp"
        filepath = os.path.join(images_dir, filename)
        
        # Speichere als WebP (bessere Kompression)
        image.save(filepath, 'WEBP', quality=85, optimize=True)
        
        return filename
        
    except Exception as e:
        st.error(f"❌ Fehler beim Speichern des Bildes: {e}")
        return None

def list_recipe_images():
    """Listet alle Rezeptbilder aus public/recipe-images/ UND src/assets/.
    
    Returns:
        list: Liste von Dictionaries mit {filename, path, size, date, source}
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        images = []
        
        # Quelle 1: public/recipe-images/
        public_images_dir = os.path.join(project_root, "public", "recipe-images")
        if os.path.exists(public_images_dir):
            for filename in os.listdir(public_images_dir):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    filepath = os.path.join(public_images_dir, filename)
                    stat = os.stat(filepath)
                    images.append({
                        'filename': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'date': datetime.fromtimestamp(stat.st_mtime),
                        'source': 'public/recipe-images',
                        'url': f"/recipe-images/{filename}"
                    })
        
        # Quelle 2: src/assets/
        assets_dir = os.path.join(project_root, "src", "assets")
        if os.path.exists(assets_dir):
            for filename in os.listdir(assets_dir):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    filepath = os.path.join(assets_dir, filename)
                    stat = os.stat(filepath)
                    images.append({
                        'filename': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'date': datetime.fromtimestamp(stat.st_mtime),
                        'source': 'src/assets',
                        'url': f"/assets/{filename}"  # Vite URL
                    })
        
        # Sortiere nach Datum (neueste zuerst)
        images.sort(key=lambda x: x['date'], reverse=True)
        return images
        
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Bilder: {e}")
        return []

def get_image_url(filename):
    """Gibt die URL für ein Rezeptbild zurück.
    
    Args:
        filename: Dateiname des Bildes (z.B. "kaesespaetzle-vegan-123.webp")
        
    Returns:
        str: Relative URL (z.B. "/recipe-images/kaesespaetzle-vegan-123.webp")
    """
    return f"/recipe-images/{filename}" if filename else ""

def extract_images_from_recipes():
    """Extrahiert alle Bilder aus recipes.json (Base64 oder Dateinamen).
    
    Returns:
        list: Liste von Dictionaries mit {recipe, image_data, image_type, title}
    """
    try:
        recipes = load_recipes()
        images = []
        
        for recipe in recipes:
            image = recipe.get('image', '')
            if not image:
                continue
            
            # Base64-Bild
            if image.startswith('data:image'):
                images.append({
                    'recipe': recipe.get('slug', recipe.get('title', 'unknown')),
                    'title': recipe.get('title', 'Unbekannt'),
                    'image_data': image,
                    'image_type': 'base64',
                    'size': len(image) * 3 / 4,  # Grobe Schätzung
                    'date': recipe.get('updated_at') or recipe.get('created_at') or 'Unbekannt'
                })
            # Dateiname
            elif not image.startswith('http'):
                images.append({
                    'recipe': recipe.get('slug', recipe.get('title', 'unknown')),
                    'title': recipe.get('title', 'Unbekannt'),
                    'filename': image,
                    'image_type': 'file',
                    'size': 0,
                    'date': recipe.get('updated_at') or recipe.get('created_at') or 'Unbekannt'
                })
        
        return images
        
    except Exception as e:
        st.error(f"❌ Fehler beim Extrahieren der Bilder: {e}")
        return []


# ----- Web Scraping -----
def fetch_url_text(url, timeout=6):
    """Fetch and extract recipe-relevant text from a URL."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "vegantalia-bot/1.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find recipe-specific content first
            recipe_content = None
            
            # Common recipe content selectors
            selectors = [
                "article",
                "[itemtype*='Recipe']",
                ".recipe",
                "#recipe",
                ".ingredients",
                ".instructions",
                "main",
                ".content",
                "#content"
            ]
            
            # Try each selector
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    recipe_content = elements[0]
                    break
            
            # If no specific content found, use body
            if not recipe_content:
                recipe_content = soup.body
            
            # Extract text, preserving some structure
            lines = []
            
            # Add title if found
            if soup.title:
                lines.append(soup.title.string)
            
            # Add description if found
            meta_desc = soup.find("meta", attrs={"name": "description"}) or \
                       soup.find("meta", attrs={"property": "og:description"})
            if meta_desc and meta_desc.get("content"):
                lines.append(meta_desc["content"])
            
            # Helper to clean text
            def clean(text):
                return ' '.join(text.split())
            
            # Process the main content
            if recipe_content:
                # First try to find structured parts
                ingredients = recipe_content.find_all(class_=lambda x: x and 'ingredient' in x.lower())
                if ingredients:
                    lines.append("Zutaten:")
                    for ing in ingredients:
                        lines.append(clean(ing.get_text()))
                
                steps = recipe_content.find_all(class_=lambda x: x and any(w in x.lower() for w in ['step', 'instruction', 'preparation', 'method']))
                if steps:
                    lines.append("\nZubereitung:")
                    for step in steps:
                        lines.append(clean(step.get_text()))
                
                # If no structured parts found, add all paragraphs
                if not ingredients and not steps:
                    for p in recipe_content.find_all(['p', 'li']):
                        text = clean(p.get_text())
                        if text and len(text) > 20:  # Skip very short texts
                            lines.append(text)
            
            return '\n\n'.join(line for line in lines if line.strip())
            
    except Exception as e:
        st.error(f"Fehler beim Laden der URL {url}: {str(e)}")
        return ""
    
    return ""

# ----- Recipe Templates -----
RECIPE_TEMPLATES = {
    "Hauptgerichte": {
        "base": {
            "category": "Hauptgerichte",
            "preparationTime": "20 Min",
            "cookTime": "30 Min",
            "portion": 2,
            "difficulty": "Mittel",
            "ingredients": [
                {
                    "group": "Basis",
                    "items": []
                },
                {
                    "group": "Gewürze & Zusätze",
                    "items": []
                }
            ],
            "steps": [
                {"time": "5 Min", "needed": [], "substeps": ["Alle Zutaten vorbereiten"]},
                {"time": "15 Min", "needed": [], "substeps": []},
                {"time": "30 Min", "needed": [], "substeps": ["Fertig anrichten"]}
            ]
        },
        "keywords": ["kochen", "braten", "backen", "dampfgaren", "hauptspeise", "mittag", "abend"]
    },
    "Salate": {
        "base": {
            "category": "Salate",
            "preparationTime": "15 Min",
            "cookTime": "0 Min",
            "portion": 2,
            "difficulty": "Einfach",
            "ingredients": [
                {
                    "group": "Salat",
                    "items": []
                },
                {
                    "group": "Dressing",
                    "items": []
                }
            ],
            "steps": [
                {"time": "10 Min", "needed": [], "substeps": ["Salatzutaten vorbereiten"]},
                {"time": "5 Min", "needed": [], "substeps": ["Dressing zubereiten", "Alles vermengen"]}
            ]
        },
        "keywords": ["salat", "dressing", "rohkost", "frisch"]
    },
    "Dessert": {
        "base": {
            "category": "Dessert",
            "preparationTime": "20 Min",
            "cookTime": "0 Min",
            "portion": 4,
            "difficulty": "Einfach",
            "ingredients": [
                {
                    "group": "Basis",
                    "items": []
                },
                {
                    "group": "Topping",
                    "items": []
                }
            ],
            "steps": [
                {"time": "15 Min", "needed": [], "substeps": ["Zutaten vorbereiten"]},
                {"time": "5 Min", "needed": [], "substeps": ["Dessert anrichten"]}
            ]
        },
        "keywords": ["dessert", "nachspeise", "süß", "süssspeise"]
    }
}

def extract_recipe_info(text):
    """Extract recipe information from text.
    Tries AI extraction first, falls back to regex parsing.
    Returns dict with extracted info or None if nothing found."""
    
    if not text or len(text.strip()) < 20:
        st.warning("Zu wenig Text zum Verarbeiten.")
        return None
    
    # Try AI-based extraction first (more reliable)
    try:
        # Check if we have AI available
        api_key = load_api_key()
        if api_key and genai:
            st.info("🤖 Verwende AI für intelligente Rezept-Extraktion...")
            
            prompt = f"""Extrahiere aus folgendem Text ein vollständiges veganes Rezept im JSON-Format.

Text:
{text[:4000]}  # Limit für Token

Erstelle ein JSON-Objekt mit folgender Struktur:
{{
  "title": "Rezeptname",
  "subtitle": "Kurze Beschreibung",
  "category": "Hauptgerichte|Salate|Dessert",
  "preparationTime": "X Min",
  "cookTime": "Y Min",
  "portion": 2,
  "difficulty": "Einfach|Mittel|Schwer",
  "ingredients": [
    {{
      "group": "Gruppenname",
      "items": [
        {{"amount": "200", "unit": "g", "name": "Kichererbsen"}},
        {{"amount": "2", "unit": "EL", "name": "Olivenöl"}}
      ]
    }}
  ],
  "steps": [
    {{
      "time": "10 Min",
      "needed": [
        {{"amount": "200", "unit": "g", "name": "Kichererbsen"}},
        {{"amount": "2", "unit": "EL", "name": "Olivenöl"}}
      ],
      "substeps": ["Kichererbsen abtropfen lassen", "Mit Olivenöl in Mixer geben und pürieren"]
    }}
  ],
  "tips": "Tipps und Varianten"
}}

KRITISCH WICHTIG:
- JEDER Schritt MUSS ein "needed"-Array mit den verwendeten Zutaten haben!
- Das "needed"-Array enthält Objekte mit amount, unit, name
- Die "substeps" beschreiben die Arbeitsschritte (dürfen auch Mengen enthalten)
- Beispiel RICHTIG needed: [{{"amount": "200", "unit": "g", "name": "Kartoffeln"}}, {{"amount": "1", "unit": "EL", "name": "Öl"}}]
- Beispiel FALSCH needed: [] (leer ist NICHT erlaubt!)
- Trage in "needed" ALLE Zutaten ein, die in diesem Schritt verwendet werden!
- JEDER substep muss mindestens eine Zutat mit Menge erwähnen
- Extrahiere NUR vegane Rezepte
- Wenn kein vollständiges Rezept gefunden wird, gib {{"title": "", "ingredients": [], "steps": []}} zurück
- Gib NUR valides JSON zurück, KEINE Erklärungen
"""
            
            result = call_gemini(prompt)
            parsed = try_parse_json(result)
            
            if parsed and parsed.get("title"):
                st.success("✅ AI-Extraktion erfolgreich!")
                return parsed
            else:
                st.warning("AI konnte kein vollständiges Rezept extrahieren. Versuche Fallback...")
                
    except Exception as e:
        st.warning(f"AI-Extraktion fehlgeschlagen: {e}. Versuche Fallback...")
    
    # Fallback: Regex-based extraction
    st.info("📝 Verwende Regex-basierte Extraktion...")
    return extract_recipe_info_regex(text)

def extract_recipe_info_regex(text):
    """Fallback: Extract recipe using regex patterns.
    Returns dict with extracted info or minimal template."""
    import re
    
    # Basic info patterns
    title_patterns = [
        r"rezept[:\s]+([^\n.]+)",
        r"([^\n.]+)\s*rezept",
        r"^([^\n.]+)\s*(?=zutaten|zubereitung)",
    ]
    time_patterns = {
        "preparationTime": [
            r"vorbereit\w+\s*(?:zeit)?[:;\s]*(\d+[\s-]*(?:min|minute|stunde|std|h))",
            r"prep\s*time\s*[:;\s]*(\d+[\s-]*(?:min|minute|hour|h))",
        ],
        "cookTime": [
            r"(?:koch|back|gar)\w*\s*(?:zeit)?[:;\s]*(\d+[\s-]*(?:min|minute|stunde|std|h))",
            r"cook\s*time\s*[:;\s]*(\d+[\s-]*(?:min|minute|hour|h))",
        ]
    }
    
    # Find ingredients section and steps section
    sections = {
        "ingredients": "",
        "steps": ""
    }
    
    # Try to find ingredient section
    ing_matches = re.split(r"(?i)(?:^|\n)\s*(?:zutaten|ingredients)[:;\s]*\n", text, maxsplit=1)
    if len(ing_matches) > 1:
        sections["ingredients"] = ing_matches[1].split("\n\n")[0]
    
    # Try to find steps section
    step_matches = re.split(r"(?i)(?:^|\n)\s*(?:zubereitung|anleitung|steps|instructions)[:;\s]*\n", text, maxsplit=1)
    if len(step_matches) > 1:
        sections["steps"] = step_matches[1]
    
    # Extract title
    title = ""
    for pattern in title_patterns:
        m = re.search(pattern, text, re.I)
        if m:
            title = m.group(1).strip()
            break
    
    # Detect category based on keywords
    category = "Hauptgerichte"  # default
    for cat, info in RECIPE_TEMPLATES.items():
        if any(kw in text.lower() for kw in info["keywords"]):
            category = cat
            break
    
    # Extract times
    times = {}
    for time_key, patterns in time_patterns.items():
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                times[time_key] = m.group(1).strip()
                break
    
    # Parse ingredients
    ingredient_groups = []
    if sections["ingredients"]:
        current_group = {"group": "Basis", "items": []}
        for line in sections["ingredients"].split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a group header
            if line.endswith(":") or line.isupper() or ":" in line:
                if current_group["items"]:
                    ingredient_groups.append(current_group)
                current_group = {"group": line.rstrip(":"), "items": []}
                continue
            
            # Try to parse ingredient line
            m = re.match(r"^\s*(?:[-•*]\s*)?(?:(\d+[\d.,/\s]*)\s*([a-zA-Z]+))?\s*(.+)$", line)
            if m:
                amount, unit, name = m.groups()
                current_group["items"].append({
                    "amount": amount or "",
                    "unit": unit or "",
                    "name": name.strip()
                })
        
        if current_group["items"]:
            ingredient_groups.append(current_group)
    
    # If no groups found, create default group
    if not ingredient_groups:
        ingredient_groups = [{"group": "Basis", "items": []}]
    
    # Parse steps
    steps = []
    if sections["steps"]:
        current_time = "10 Min"
        step_texts = re.split(r"\d+\.", sections["steps"])
        for i, step in enumerate(step_texts):
            if not step.strip():
                continue
            substeps = [s.strip() for s in step.split("\n") if s.strip()]
            if substeps:
                steps.append({
                    "time": current_time,
                    "needed": [],
                    "substeps": substeps
                })
    
    # If no steps found, use template steps
    if not steps:
        steps = RECIPE_TEMPLATES[category]["base"]["steps"]
    
    return {
        "title": title,
        "subtitle": "",
        "category": category,
        "preparationTime": times.get("preparationTime", RECIPE_TEMPLATES[category]["base"]["preparationTime"]),
        "cookTime": times.get("cookTime", RECIPE_TEMPLATES[category]["base"]["cookTime"]),
        "portion": RECIPE_TEMPLATES[category]["base"]["portion"],
        "difficulty": RECIPE_TEMPLATES[category]["base"]["difficulty"],
        "ingredients": ingredient_groups,
        "steps": steps,
        "tips": "",
        "image": ""
    }

def save_api_key(key):
    """Speichert den API-Key persistent und testet ihn."""
    try:
        # Setze die Umgebungsvariable
        os.environ["GOOGLE_API_KEY"] = key
        
        # Configure genai immediately
        if genai:
            try:
                genai.configure(api_key=key)
                st.success("🔧 Gemini SDK konfiguriert")
            except Exception as e:
                st.warning(f"Genai config Warnung: {e}")
        
        # Persistieren ZUERST (auch wenn Test fehlschlägt)
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(f"GOOGLE_API_KEY={key}\n")
            st.success(f"✅ Key gespeichert in: {CONFIG_FILE}")
        except PermissionError:
            st.error(f"❌ Keine Berechtigung zum Schreiben in {CONFIG_FILE}")
            st.info("💡 Versuche die App als Administrator auszuführen")
            return False
        except Exception as e:
            st.error(f"⚠️ Konnte Key nicht in Datei speichern: {e}")
            import traceback
            with st.expander("🔍 Fehlerdetails"):
                st.code(traceback.format_exc())
            return False
        
        # Teste den Key gegen die API (nur wenn requests verfügbar)
        if not requests:
            st.warning("⚠️ 'requests' Paket fehlt - Key gespeichert aber nicht getestet")
            st.info("Installiere 'requests' für API-Tests: pip install requests")
            return True
            
        st.info("🔍 Teste API-Key...")
        # Verwende die offizielle Gemini API mit X-goog-api-key Header
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": key
        }
        data = {
            "contents": [{
                "parts": [{"text": "Hallo"}]
            }]
        }
        
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        
        if resp.status_code == 200:
            st.success("✅ API-Key ist gültig und funktioniert mit gemini-2.0-flash!")
            st.balloons()
            return True
        else:
            st.error(f"❌ API antwortet mit Status {resp.status_code}")
            with st.expander("🔍 API Antwort"):
                st.code(resp.text)
            
            # Try alternative models (all use X-goog-api-key header!)
            models_to_try = [
                "gemini-1.5-flash-latest",
                "gemini-1.5-flash",
                "gemini-1.5-pro-latest",
                "gemini-1.5-pro"
            ]
            
            for model in models_to_try:
                st.info(f"Versuche {model}...")
                url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                resp_alt = requests.post(url_alt, headers=headers, json=data, timeout=10)
                if resp_alt.status_code == 200:
                    st.success(f"✅ API-Key funktioniert mit {model}!")
                    st.balloons()
                    return True
                else:
                    st.warning(f"❌ {model}: {resp_alt.status_code}")
                    with st.expander(f"🔍 {model} Antwort"):
                        st.code(resp_alt.text)
            
            st.error("Kein funktionierendes Modell gefunden. Bitte prüfe deinen API-Key.")
            return False
            
    except requests.exceptions.Timeout:
        st.warning("⏱️ Timeout beim Testen. Key wurde trotzdem gespeichert.")
        return True  # Consider it saved
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Netzwerkfehler: {e}")
        st.warning("Key wurde gespeichert, aber Test fehlgeschlagen.")
        return True  # Consider it saved
    except Exception as e:
        st.error(f"❌ Unerwarteter Fehler: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False

def call_gemini(prompt):
    """Call Gemini AI directly via REST API."""
    api_key = load_api_key()
    if not api_key:
        st.error("🔑 API-Key fehlt!")
        st.stop()
    
    # Verwende v1beta API mit X-goog-api-key Header (NICHT Query Parameter!)
    models_to_try = [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    last_error = None
    
    for model in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            # Debug: Log the request
            if response.status_code != 200:
                st.warning(f"⚠️ {model} Status: {response.status_code}")
                with st.expander(f"🔍 Request/Response Details für {model}"):
                    st.write("**Request URL:**", url)
                    st.write("**Request Headers:**", {k: v[:20]+'...' if len(v) > 20 else v for k, v in headers.items()})
                    st.write("**Request Data (first 500 chars):**")
                    st.code(str(data)[:500])
                    st.write("**Response:**")
                    st.code(response.text)
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract the generated text from the response
                if result.get("candidates") and result["candidates"][0].get("content"):
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    st.success(f"✅ Verwendet: {model}")
                    return text.strip()
                else:
                    raise RuntimeError("Keine Antwort von der API erhalten")
            elif response.status_code == 404:
                last_error = f"{model}: 404 Not Found"
                continue  # Try next model
            else:
                last_error = f"{model}: HTTP {response.status_code}"
                response.raise_for_status()
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                continue  # Try next model
            else:
                last_error = f"{model}: {str(e)}"
                st.error(f"HTTP Fehler mit {model}: {str(e)}")
                with st.expander("🔍 Fehlerdetails"):
                    st.code(e.response.text if hasattr(e, 'response') else str(e))
                continue
        except Exception as e:
            last_error = f"{model}: {str(e)}"
            st.warning(f"⚠️ {model} fehlgeschlagen: {str(e)}")
            continue
    
    # If we get here, all models failed
    st.error("❌ Alle Gemini-Modelle fehlgeschlagen!")
    st.error(f"Letzter Fehler: {last_error}")
    return None

def search_swiss_food_api(name):
    """Suche in Swiss Food Database. Returns nutrition dict or None."""
    try:
        base_url = "https://api.webapp.prod.blv.foodcase-services.com/BLV_WebApp_WS/webresources/BLV-api"
        
        # 1. Suche nach Lebensmittel
        search_url = f"{base_url}/foods"
        params = {"search": name, "lang": "de", "limit": 3}
        response = requests.get(search_url, params=params, timeout=8)
        
        if response.status_code != 200:
            return None
            
        foods = response.json()
        if not foods or len(foods) == 0:
            return None
        
        # 2. Hole DBID
        food = foods[0]
        food_id = food.get("id")
        if not food_id:
            return None
            
        dbid_url = f"{base_url}/fooddbid/{food_id}"
        dbid_resp = requests.get(dbid_url, timeout=8)
        if dbid_resp.status_code != 200:
            return None
            
        dbid_data = dbid_resp.json()
        if not isinstance(dbid_data, list) or len(dbid_data) == 0:
            return None
        food_dbid = dbid_data[0]
        
        # 3. Hole Nährwerte
        values_url = f"{base_url}/values"
        values_params = {"DBID": food_dbid, "componentsetid": 1, "lang": "de"}
        values_resp = requests.get(values_url, params=values_params, timeout=8)
        
        if values_resp.status_code != 200:
            return None
            
        values = values_resp.json()
        
        # Parse Nährwerte
        component_map = {
            "ENER1": "kcal", "PROT": "protein", "CHO": "carbs",
            "FAT": "fat", "FIBC": "fiber"
        }
        
        result = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}
        matched_name = food.get("names", [{}])[0].get("term", name) if "names" in food else name
        
        for value in values:
            component = value.get("component", {})
            component_code = component.get("code", "")
            
            if component_code in component_map:
                key = component_map[component_code]
                value_str = value.get("value", "0")
                try:
                    if isinstance(value_str, str):
                        value_str = value_str.replace(',', '.')
                    result[key] = float(value_str)
                except:
                    pass
        
        return {"nutrition": result, "matched_name": matched_name, "source": "Swiss Food DB 🇨🇭"}
        
    except:
        return None

def search_openfoodfacts_api(name):
    """Suche in Open Food Facts. Returns nutrition dict or None."""
    try:
        # Open Food Facts API (weltweit, crowdsourced)
        search_url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": name,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 3,
            "fields": "product_name,nutriments"
        }
        
        response = requests.get(search_url, params=params, timeout=8)
        if response.status_code != 200:
            return None
            
        data = response.json()
        products = data.get("products", [])
        
        if not products:
            return None
        
        # Nehme ersten Treffer
        product = products[0]
        nutriments = product.get("nutriments", {})
        matched_name = product.get("product_name", name)
        
        # Extrahiere Nährwerte (pro 100g)
        result = {
            "kcal": nutriments.get("energy-kcal_100g", 0) or 0,
            "protein": nutriments.get("proteins_100g", 0) or 0,
            "carbs": nutriments.get("carbohydrates_100g", 0) or 0,
            "fat": nutriments.get("fat_100g", 0) or 0,
            "fiber": nutriments.get("fiber_100g", 0) or 0
        }
        
        # Nur zurückgeben wenn mindestens kcal vorhanden
        if result["kcal"] > 0:
            return {"nutrition": result, "matched_name": matched_name, "source": "Open Food Facts 🌍"}
        
        return None
        
    except:
        return None

def search_usda_api(name):
    """Suche in USDA FoodData Central (kostenlos, kein Key nötig für Basis-Suche). Returns nutrition dict or None."""
    try:
        # USDA FoodData Central - Foundation Foods (öffentlich)
        search_url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {
            "query": name,
            "pageSize": 3,
            "api_key": "DEMO_KEY"  # DEMO_KEY erlaubt 30 requests/hour/IP
        }
        
        response = requests.get(search_url, params=params, timeout=8)
        if response.status_code != 200:
            return None
            
        data = response.json()
        foods = data.get("foods", [])
        
        if not foods:
            return None
        
        # Nehme ersten Treffer
        food = foods[0]
        matched_name = food.get("description", name)
        nutrients = food.get("foodNutrients", [])
        
        # USDA Nutrient IDs
        nutrient_map = {
            1008: "kcal",      # Energy
            1003: "protein",   # Protein
            1005: "carbs",     # Carbohydrate
            1004: "fat",       # Total lipid (fat)
            1079: "fiber"      # Fiber, total dietary
        }
        
        result = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}
        
        for nutrient in nutrients:
            nutrient_id = nutrient.get("nutrientId")
            if nutrient_id in nutrient_map:
                key = nutrient_map[nutrient_id]
                value = nutrient.get("value", 0)
                result[key] = float(value) if value else 0
        
        # Nur zurückgeben wenn mindestens kcal vorhanden
        if result["kcal"] > 0:
            return {"nutrition": result, "matched_name": matched_name, "source": "USDA FoodData 🇺🇸"}
        
        return None
        
    except:
        return None

def compute_nutrition_from_swiss(ingredients, portions=1):
    """Calculate nutrition using multiple free APIs with fallback chain:
    1. Swiss Food Database (BLV)
    2. Open Food Facts (global)
    3. USDA FoodData Central
    4. Local database
    5. Estimates
    
    Args:
        ingredients: List of ingredient groups
        portions: Number of servings (default 1). Result will be per portion.
    
    Returns dict with keys kcal, protein, carbs, fat, fiber (ints) - per portion.
    """
    # Lokale Fallback-Datenbank für häufige vegane Zutaten (pro 100g)
    nutrition_db = {
        # Getreide & Mehl
        "mehl": {"kcal": 364, "protein": 10, "carbs": 76, "fat": 1, "fiber": 3},
        "weizenmehl": {"kcal": 364, "protein": 10, "carbs": 76, "fat": 1, "fiber": 3},
        "dinkelmehl": {"kcal": 338, "protein": 15, "carbs": 70, "fat": 2, "fiber": 9},
        "vollkornmehl": {"kcal": 340, "protein": 13, "carbs": 72, "fat": 2, "fiber": 10},
        "haferflocken": {"kcal": 379, "protein": 13, "carbs": 58, "fat": 7, "fiber": 10},
        "reis": {"kcal": 130, "protein": 3, "carbs": 28, "fat": 0, "fiber": 0},
        "nudeln": {"kcal": 371, "protein": 13, "carbs": 74, "fat": 1, "fiber": 3},
        "pasta": {"kcal": 371, "protein": 13, "carbs": 74, "fat": 1, "fiber": 3},
        "brot": {"kcal": 265, "protein": 9, "carbs": 49, "fat": 3, "fiber": 4},
        
        # Hülsenfrüchte
        "linsen": {"kcal": 116, "protein": 9, "carbs": 20, "fat": 0, "fiber": 8},
        "kichererbsen": {"kcal": 164, "protein": 9, "carbs": 27, "fat": 3, "fiber": 7},
        "bohnen": {"kcal": 127, "protein": 9, "carbs": 23, "fat": 0, "fiber": 7},
        "kidneybohnen": {"kcal": 127, "protein": 9, "carbs": 23, "fat": 0, "fiber": 7},
        "schwarze bohnen": {"kcal": 132, "protein": 9, "carbs": 24, "fat": 1, "fiber": 9},
        "erbsen": {"kcal": 81, "protein": 5, "carbs": 14, "fat": 0, "fiber": 5},
        "tofu": {"kcal": 76, "protein": 8, "carbs": 2, "fat": 5, "fiber": 1},
        "räuchertofu": {"kcal": 150, "protein": 15, "carbs": 3, "fat": 9, "fiber": 2},
        "tempeh": {"kcal": 193, "protein": 19, "carbs": 9, "fat": 11, "fiber": 9},
        
        # Gemüse
        "tomate": {"kcal": 18, "protein": 1, "carbs": 4, "fat": 0, "fiber": 1},
        "tomaten": {"kcal": 18, "protein": 1, "carbs": 4, "fat": 0, "fiber": 1},
        "zwiebel": {"kcal": 40, "protein": 1, "carbs": 9, "fat": 0, "fiber": 2},
        "zwiebeln": {"kcal": 40, "protein": 1, "carbs": 9, "fat": 0, "fiber": 2},
        "knoblauch": {"kcal": 149, "protein": 6, "carbs": 33, "fat": 1, "fiber": 2},
        "karotte": {"kcal": 41, "protein": 1, "carbs": 10, "fat": 0, "fiber": 3},
        "karotten": {"kcal": 41, "protein": 1, "carbs": 10, "fat": 0, "fiber": 3},
        "möhre": {"kcal": 41, "protein": 1, "carbs": 10, "fat": 0, "fiber": 3},
        "möhren": {"kcal": 41, "protein": 1, "carbs": 10, "fat": 0, "fiber": 3},
        "paprika": {"kcal": 31, "protein": 1, "carbs": 6, "fat": 0, "fiber": 2},
        "zucchini": {"kcal": 17, "protein": 1, "carbs": 3, "fat": 0, "fiber": 1},
        "aubergine": {"kcal": 25, "protein": 1, "carbs": 6, "fat": 0, "fiber": 3},
        "brokkoli": {"kcal": 34, "protein": 3, "carbs": 7, "fat": 0, "fiber": 3},
        "blumenkohl": {"kcal": 25, "protein": 2, "carbs": 5, "fat": 0, "fiber": 2},
        "spinat": {"kcal": 23, "protein": 3, "carbs": 4, "fat": 0, "fiber": 2},
        "salat": {"kcal": 15, "protein": 1, "carbs": 3, "fat": 0, "fiber": 1},
        "gurke": {"kcal": 15, "protein": 1, "carbs": 4, "fat": 0, "fiber": 1},
        "lauch": {"kcal": 61, "protein": 1, "carbs": 14, "fat": 0, "fiber": 2},
        
        # Nüsse & Samen
        "mandel": {"kcal": 579, "protein": 21, "carbs": 22, "fat": 50, "fiber": 12},
        "mandeln": {"kcal": 579, "protein": 21, "carbs": 22, "fat": 50, "fiber": 12},
        "walnuss": {"kcal": 654, "protein": 15, "carbs": 14, "fat": 65, "fiber": 7},
        "walnüsse": {"kcal": 654, "protein": 15, "carbs": 14, "fat": 65, "fiber": 7},
        "cashew": {"kcal": 553, "protein": 18, "carbs": 30, "fat": 44, "fiber": 3},
        "cashews": {"kcal": 553, "protein": 18, "carbs": 30, "fat": 44, "fiber": 3},
        "erdnuss": {"kcal": 567, "protein": 26, "carbs": 16, "fat": 49, "fiber": 8},
        "erdnüsse": {"kcal": 567, "protein": 26, "carbs": 16, "fat": 49, "fiber": 8},
        "sonnenblumenkerne": {"kcal": 584, "protein": 21, "carbs": 20, "fat": 51, "fiber": 9},
        "kürbiskerne": {"kcal": 559, "protein": 30, "carbs": 11, "fat": 49, "fiber": 6},
        "sesam": {"kcal": 573, "protein": 18, "carbs": 23, "fat": 50, "fiber": 12},
        "leinsamen": {"kcal": 534, "protein": 18, "carbs": 29, "fat": 42, "fiber": 27},
        "chiasamen": {"kcal": 486, "protein": 17, "carbs": 42, "fat": 31, "fiber": 34},
        
        # Öle & Fette
        "öl": {"kcal": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
        "olivenöl": {"kcal": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
        "rapsöl": {"kcal": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
        "sonnenblumenöl": {"kcal": 884, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
        "kokosöl": {"kcal": 862, "protein": 0, "carbs": 0, "fat": 100, "fiber": 0},
        
        # Milchalternativen
        "hafermilch": {"kcal": 47, "protein": 1, "carbs": 7, "fat": 2, "fiber": 1},
        "sojamilch": {"kcal": 54, "protein": 3, "carbs": 6, "fat": 2, "fiber": 1},
        "mandelmilch": {"kcal": 24, "protein": 1, "carbs": 3, "fat": 1, "fiber": 0},
        "kokosmilch": {"kcal": 230, "protein": 2, "carbs": 6, "fat": 24, "fiber": 2},
        
        # Süßungsmittel
        "zucker": {"kcal": 387, "protein": 0, "carbs": 100, "fat": 0, "fiber": 0},
        "ahornsirup": {"kcal": 260, "protein": 0, "carbs": 67, "fat": 0, "fiber": 0},
        "agavendicksaft": {"kcal": 310, "protein": 0, "carbs": 76, "fat": 0, "fiber": 0},
        "honig": {"kcal": 304, "protein": 0, "carbs": 82, "fat": 0, "fiber": 0},
        
        # Gewürze & Würze (geringe Mengen, daher Nullwerte)
        "salz": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "pfeffer": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "paprikapulver": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "curry": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "kurkuma": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "kreuzkümmel": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "zimt": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "muskat": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "ingwer": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "petersilie": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "basilikum": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "oregano": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "thymian": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "rosmarin": {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0},
        "sojasauce": {"kcal": 53, "protein": 5, "carbs": 5, "fat": 0, "fiber": 0},
        "essig": {"kcal": 19, "protein": 0, "carbs": 1, "fat": 0, "fiber": 0},
        "senf": {"kcal": 66, "protein": 4, "carbs": 6, "fat": 3, "fiber": 3},
        "tomatenmark": {"kcal": 82, "protein": 4, "carbs": 18, "fat": 0, "fiber": 3},
        
        # Kartoffeln & Stärke
        "kartoffel": {"kcal": 77, "protein": 2, "carbs": 17, "fat": 0, "fiber": 2},
        "kartoffeln": {"kcal": 77, "protein": 2, "carbs": 17, "fat": 0, "fiber": 2},
        "süßkartoffel": {"kcal": 86, "protein": 2, "carbs": 20, "fat": 0, "fiber": 3},
        "süßkartoffeln": {"kcal": 86, "protein": 2, "carbs": 20, "fat": 0, "fiber": 3},
        "stärke": {"kcal": 381, "protein": 0, "carbs": 91, "fat": 0, "fiber": 0},
        "maisstärke": {"kcal": 381, "protein": 0, "carbs": 91, "fat": 0, "fiber": 0},
        
        # Obst
        "apfel": {"kcal": 52, "protein": 0, "carbs": 14, "fat": 0, "fiber": 2},
        "banane": {"kcal": 89, "protein": 1, "carbs": 23, "fat": 0, "fiber": 3},
        "orange": {"kcal": 47, "protein": 1, "carbs": 12, "fat": 0, "fiber": 2},
        "zitrone": {"kcal": 29, "protein": 1, "carbs": 9, "fat": 0, "fiber": 3},
        "beeren": {"kcal": 57, "protein": 1, "carbs": 14, "fat": 0, "fiber": 2},
        "erdbeeren": {"kcal": 32, "protein": 1, "carbs": 8, "fat": 0, "fiber": 2},
        "heidelbeeren": {"kcal": 57, "protein": 1, "carbs": 14, "fat": 0, "fiber": 2},
        "himbeeren": {"kcal": 52, "protein": 1, "carbs": 12, "fat": 1, "fiber": 7},
        "mango": {"kcal": 60, "protein": 1, "carbs": 15, "fat": 0, "fiber": 2},
        "ananas": {"kcal": 50, "protein": 1, "carbs": 13, "fat": 0, "fiber": 1},
        "avocado": {"kcal": 160, "protein": 2, "carbs": 9, "fat": 15, "fiber": 7},
    }
    
    try:
        total = {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}
        
        
        st.write("🔍 **Nährwertberechnung (Multi-API mit Fallback)**")
        st.write("📊 Fallback: Swiss 🇨🇭 → OpenFood 🌍 → USDA 🇺🇸 → Lokal 💾 → Schätzung ⚖️")
        
        for g_idx, g in enumerate(ingredients):
            group_name = g.get("group", "Unbekannt")
            st.write(f"  **Gruppe {g_idx+1}: {group_name}**")
            
            for it_idx, it in enumerate(g.get("items", [])):
                amount = it.get("amount", "0")
                unit = it.get("unit", "")  # Leerer String als default, nicht "g"
                name = it.get("name", "").strip()
                
                # Sicherheit: unit kann None sein
                if unit is None:
                    unit = ""
                
                if not name or not amount:
                    continue
                
                # Extrahiere Zahl aus Menge
                try:
                    # Behandle Bereichsangaben wie "50-100" → nimm Durchschnitt
                    amount_str = str(amount).strip()
                    
                    # Check für Bereiche (z.B. "50-100", "1-2")
                    if '-' in amount_str and not amount_str.startswith('-'):
                        parts = amount_str.split('-')
                        if len(parts) == 2:
                            try:
                                num1 = float(parts[0].replace(',', '.').strip())
                                num2 = float(parts[1].replace(',', '.').strip())
                                amt = (num1 + num2) / 2  # Durchschnitt
                                st.write(f"    📊 {name}: Bereich {amount_str} → Durchschnitt {amt}")
                            except:
                                amount_str = parts[0]  # Nehme erste Zahl
                    
                    # Normale Zahlenextraktion
                    amount_clean = ''.join(c for c in amount_str if c.isdigit() or c == '.' or c == ',')
                    amount_clean = amount_clean.replace(',', '.')
                    amt = float(amount_clean) if amount_clean else 0
                    
                    if amt <= 0:
                        st.write(f"    ⚠️ {name}: Menge ungültig ({amount})")
                        continue
                        
                except Exception as e:
                    st.write(f"    ⚠️ {name}: Konnte Menge nicht parsen ({amount}) - Fehler: {e}")
                    continue
                
                # API-Fallback-Kette: Swiss → Open Food Facts → USDA → Lokale DB → Schätzung
                api_result = None
                found_nutr = None
                matched_name = None
                source = ""
                
                # 1. Versuche Swiss Food Database
                api_result = search_swiss_food_api(name)
                
                # 2. Falls nicht gefunden, versuche Open Food Facts
                if not api_result:
                    api_result = search_openfoodfacts_api(name)
                
                # 3. Falls immer noch nicht gefunden, versuche USDA
                if not api_result:
                    api_result = search_usda_api(name)
                
                # Wenn API erfolgreich
                if api_result:
                    found_nutr = api_result["nutrition"]
                    matched_name = api_result["matched_name"]
                    source = api_result["source"]
                    st.write(f"    ✅ {source}: {name} → {matched_name}")
                
                # 4. Fallback zu lokaler Datenbank
                if not found_nutr:
                    name_lower = name.lower()
                    for db_key, db_values in nutrition_db.items():
                        if db_key in name_lower or name_lower in db_key:
                            found_nutr = db_values
                            matched_name = db_key
                            st.write(f"    💾 Fallback: {name} → {matched_name}")
                            break
                
                if found_nutr:
                    # Berechne Faktor basierend auf Einheit
                    factor = amt / 100.0  # Standard: pro 100g
                    
                    # Einheitenumrechnung
                    unit_lower = unit.lower().strip()
                    
                    # Gewichtseinheiten
                    if unit_lower in ['kg', 'kilo', 'kilogramm']:
                        factor = (amt * 1000) / 100.0
                    elif unit_lower in ['mg', 'milligramm']:
                        factor = (amt / 1000) / 100.0
                    elif unit_lower in ['g', 'gramm', 'gr']:
                        factor = amt / 100.0
                    
                    # Volumeneinheiten
                    elif unit_lower in ['ml', 'milliliter']:
                        factor = amt / 100.0
                    elif unit_lower in ['l', 'liter']:
                        factor = (amt * 1000) / 100.0
                    elif unit_lower in ['cl', 'centiliter']:
                        factor = (amt * 10) / 100.0
                    elif unit_lower in ['dl', 'deciliter']:
                        factor = (amt * 100) / 100.0
                    
                    # Löffel & Tassen
                    elif unit_lower in ['el', 'esslöffel', 'essl', 'eßlöffel', 'tbsp', 'essloffel']:
                        factor = (amt * 15) / 100.0  # ~15g/15ml pro EL
                        st.write(f"      📏 {amt} EL = ~{amt*15}g")
                    elif unit_lower in ['tl', 'teelöffel', 'teel', 'tsp', 'teeloffel']:
                        factor = (amt * 5) / 100.0   # ~5g/5ml pro TL
                        st.write(f"      📏 {amt} TL = ~{amt*5}g")
                    elif unit_lower in ['msp', 'messerspitze', 'messerspitzen']:
                        factor = (amt * 2) / 100.0   # ~2g pro Messerspitze
                        st.write(f"      📏 {amt} Msp = ~{amt*2}g")
                    elif unit_lower in ['tasse', 'tassen', 'cup', 'cups', 'becher']:
                        factor = (amt * 240) / 100.0  # ~240ml pro Tasse
                        st.write(f"      📏 {amt} Tasse(n) = ~{amt*240}ml")
                    
                    # Beschreibende Mengen (geringe/keine Nährwerte)
                    elif unit_lower in ['prise', 'prisen', 'spritzer', 'schuss', 'etwas', 'wenig', 'nach belieben', 'nach geschmack', 'belieben', 'geschmack']:
                        factor = 0  # Vernachlässigbar
                        st.write(f"      💨 {amt} {unit} = vernachlässigbar")
                    elif unit_lower in ['handvoll', 'hand voll']:
                        factor = (amt * 40) / 100.0  # ~40g pro Handvoll
                        st.write(f"      📏 {amt} Handvoll = ~{amt*40}g")
                    
                    # Verpackungseinheiten
                    elif unit_lower in ['dose', 'dosen']:
                        factor = (amt * 400) / 100.0  # Standard-Dose ~400g
                        st.write(f"      📏 {amt} Dose(n) = ~{amt*400}g")
                    elif unit_lower in ['glas', 'gläser']:
                        factor = (amt * 200) / 100.0  # Standard-Glas ~200ml
                        st.write(f"      📏 {amt} Glas = ~{amt*200}ml")
                    elif unit_lower in ['packung', 'pkg', 'pack']:
                        factor = (amt * 250) / 100.0  # Standard-Packung ~250g
                        st.write(f"      📏 {amt} Packung(en) = ~{amt*250}g")
                    elif unit_lower in ['bund', 'bündel']:
                        factor = (amt * 100) / 100.0  # Bund Petersilie etc ~100g
                        st.write(f"      📏 {amt} Bund = ~{amt*100}g")
                    
                    # Scheiben & Stücke
                    elif unit_lower in ['scheibe', 'scheiben']:
                        # Kontext-abhängig
                        name_lower = name.lower()
                        if 'brot' in name_lower or 'toast' in name_lower:
                            factor = (amt * 30) / 100.0  # ~30g pro Brotscheibe
                            st.write(f"      📏 {amt} Scheibe(n) Brot = ~{amt*30}g")
                        elif 'käse' in name_lower or 'wurst' in name_lower:
                            factor = (amt * 20) / 100.0  # ~20g pro Käse/Wurstscheibe
                            st.write(f"      📏 {amt} Scheibe(n) = ~{amt*20}g")
                        else:
                            factor = (amt * 25) / 100.0  # Default ~25g
                            st.write(f"      📏 {amt} Scheibe(n) = ~{amt*25}g")
                    
                    elif unit_lower in ['würfel']:
                        name_lower = name.lower()
                        if 'hefe' in name_lower:
                            factor = (amt * 42) / 100.0  # ~42g pro Hefewürfel
                            st.write(f"      📏 {amt} Würfel Hefe = ~{amt*42}g")
                        else:
                            factor = (amt * 10) / 100.0  # ~10g pro Würfel
                            st.write(f"      📏 {amt} Würfel = ~{amt*10}g")
                    
                    elif unit_lower in ['riegel']:
                        factor = (amt * 100) / 100.0  # ~100g pro Riegel
                        st.write(f"      📏 {amt} Riegel = ~{amt*100}g")
                    
                    # Spezielle Lebensmittel-Formen
                    elif unit_lower in ['blatt', 'blätter']:
                        factor = (amt * 1) / 100.0  # ~1g pro Blatt (Basilikum etc)
                        st.write(f"      📏 {amt} Blatt/Blätter = ~{amt*1}g")
                    
                    elif unit_lower in ['stange', 'stangen']:
                        name_lower = name.lower()
                        if 'lauch' in name_lower or 'porree' in name_lower:
                            factor = (amt * 150) / 100.0  # ~150g pro Stange Lauch
                            st.write(f"      📏 {amt} Stange(n) Lauch = ~{amt*150}g")
                        elif 'stangensellerie' in name_lower or 'sellerie' in name_lower:
                            factor = (amt * 40) / 100.0  # ~40g pro Selleriestange
                            st.write(f"      📏 {amt} Stange(n) Sellerie = ~{amt*40}g")
                        else:
                            factor = (amt * 100) / 100.0
                            st.write(f"      📏 {amt} Stange(n) = ~{amt*100}g")
                    
                    elif unit_lower in ['knolle', 'knollen']:
                        name_lower = name.lower()
                        if 'knoblauch' in name_lower:
                            factor = (amt * 40) / 100.0  # ~40g pro Knoblauchknolle
                            st.write(f"      📏 {amt} Knolle(n) Knoblauch = ~{amt*40}g")
                        elif 'ingwer' in name_lower:
                            factor = (amt * 50) / 100.0  # ~50g pro Ingwerknolle
                            st.write(f"      📏 {amt} Knolle(n) Ingwer = ~{amt*50}g")
                        else:
                            factor = (amt * 100) / 100.0
                            st.write(f"      📏 {amt} Knolle(n) = ~{amt*100}g")
                    
                    elif unit_lower in ['kopf', 'köpfe']:
                        name_lower = name.lower()
                        if 'salat' in name_lower:
                            factor = (amt * 200) / 100.0  # ~200g pro Salatkopf
                            st.write(f"      📏 {amt} Kopf Salat = ~{amt*200}g")
                        elif 'kohl' in name_lower or 'blumenkohl' in name_lower:
                            factor = (amt * 600) / 100.0  # ~600g pro Kohlkopf
                            st.write(f"      📏 {amt} Kopf Kohl = ~{amt*600}g")
                        else:
                            factor = (amt * 300) / 100.0
                            st.write(f"      📏 {amt} Kopf = ~{amt*300}g")
                    
                    # Regionale/Alte Maße
                    elif unit_lower in ['pfund']:
                        factor = (amt * 500) / 100.0  # 1 Pfund = 500g
                        st.write(f"      📏 {amt} Pfund = {amt*500}g")
                    elif unit_lower in ['oz', 'unze', 'unzen', 'ounce']:
                        factor = (amt * 28.35) / 100.0  # 1oz ≈ 28.35g
                        st.write(f"      📏 {amt} oz = ~{amt*28.35:.1f}g")
                    elif unit_lower in ['lb', 'pound', 'pounds']:
                        factor = (amt * 453.6) / 100.0  # 1lb ≈ 453.6g
                        st.write(f"      📏 {amt} lb = ~{amt*453.6:.1f}g")
                    
                    # Stückzahlen - verwende realistische Schätzungen
                    elif unit_lower in ['stück', 'stk', 'st', 'x', '']:
                        # Schätze Gewicht basierend auf Zutat
                        name_lower = name.lower()
                        if 'kartoffel' in name_lower:
                            factor = (amt * 150) / 100.0  # ~150g pro Kartoffel
                            st.write(f"      📏 {amt} Kartoffel(n) = ~{amt*150}g")
                        elif 'zwiebel' in name_lower:
                            factor = (amt * 100) / 100.0  # ~100g pro Zwiebel
                            st.write(f"      📏 {amt} Zwiebel(n) = ~{amt*100}g")
                        elif 'knoblauch' in name_lower or 'zehe' in name_lower:
                            factor = (amt * 5) / 100.0    # ~5g pro Knoblauchzehe
                            st.write(f"      📏 {amt} Zehe(n) = ~{amt*5}g")
                        elif 'tomate' in name_lower:
                            factor = (amt * 150) / 100.0  # ~150g pro Tomate
                            st.write(f"      📏 {amt} Tomate(n) = ~{amt*150}g")
                        elif 'paprika' in name_lower:
                            factor = (amt * 180) / 100.0  # ~180g pro Paprika
                            st.write(f"      📏 {amt} Paprika = ~{amt*180}g")
                        elif 'ei' in name_lower or 'eier' in name_lower:
                            factor = (amt * 60) / 100.0   # ~60g pro Ei
                            st.write(f"      📏 {amt} Ei(er) = ~{amt*60}g")
                        else:
                            # Fallback: Bei fehlender Einheit, nehme an dass Menge in Gramm ist
                            factor = amt / 100.0
                            st.write(f"      ⚠️ Einheit unklar '{unit}' - nehme {amt}g an")
                    
                    # Mengenangaben ohne Gewicht
                    elif unit_lower in ['prise', 'etwas', 'nach geschmack', 'belieben']:
                        factor = 0
                    
                    # Unbekannte Einheit
                    else:
                        factor = amt / 100.0
                        st.write(f"      ⚠️ Unbekannte Einheit '{unit}' - nehme {amt}g an")
                    
                    # Berechne Nährwerte
                    added = {
                        "kcal": int(found_nutr["kcal"] * factor),
                        "protein": int(found_nutr["protein"] * factor),
                        "carbs": int(found_nutr["carbs"] * factor),
                        "fat": int(found_nutr["fat"] * factor),
                        "fiber": int(found_nutr["fiber"] * factor)
                    }
                    
                    # Addiere zu Gesamt
                    for key in total:
                        total[key] += added[key]
                    
                    st.write(f"      → {added['kcal']} kcal, {added['protein']}g Protein, {added['carbs']}g KH, {added['fat']}g Fett")
                else:
                    # Nicht gefunden - verwende Durchschnittswert
                    default_nutr = {"kcal": 50, "protein": 2, "carbs": 10, "fat": 1, "fiber": 1}
                    factor = amt / 100.0
                    added = {key: int(val * factor) for key, val in default_nutr.items()}
                    for key in total:
                        total[key] += added[key]
                    st.write(f"    ⚠️ {amt}{unit} {name} → {added['kcal']} kcal (Schätzwert)")
        
        # Berechne Nährwerte pro Portion
        if portions > 1:
            st.write(f"\n**📊 Gesamtrezept ({portions} Portionen):** {total['kcal']} kcal | {total['protein']}g Protein | {total['carbs']}g KH | {total['fat']}g Fett | {total['fiber']}g Ballaststoffe")
            
            # Teile durch Portionen für pro-Person-Werte
            per_portion = {
                "kcal": int(total['kcal'] / portions),
                "protein": int(total['protein'] / portions),
                "carbs": int(total['carbs'] / portions),
                "fat": int(total['fat'] / portions),
                "fiber": int(total['fiber'] / portions)
            }
            
            st.success(f"**🎯 Pro Portion (1/{portions}):** {per_portion['kcal']} kcal | {per_portion['protein']}g Protein | {per_portion['carbs']}g KH | {per_portion['fat']}g Fett | {per_portion['fiber']}g Ballaststoffe")
            return per_portion
        else:
            st.success(f"**🎯 Gesamt:** {total['kcal']} kcal | {total['protein']}g Protein | {total['carbs']}g KH | {total['fat']}g Fett | {total['fiber']}g Ballaststoffe")
            return total
        
    except Exception as e:
        st.error(f"Fehler bei der Nährwertberechnung: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return {"kcal": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0}

def try_parse_json(s):
    try:
        return json.loads(s)
    except Exception:
        # sometimes model returns markdown fenced JSON; try to extract
        import re
        m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", s)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
        # fallback: try to find first { ... }
        m2 = re.search(r"(\{[\s\S]*\})", s)
        if m2:
            try:
                return json.loads(m2.group(1))
            except Exception:
                return None
    return None


def apply_parsed_to_session(parsed, for_edit=False, rerun=True):
    """Populate session_state with parsed recipe so form fields are filled.
    if for_edit is True, populate edit-mode keys, else populate create-mode keys.
    """
    if not isinstance(parsed, dict):
        return

    st.write("🔄 Übertrage Felder ins Formular...")
    
    # Zuerst alle Werte aus dem Formular löschen
    keys_to_clear = [
        "Titel des Rezepts*", "Untertitel", "Kategorie", 
        "Vorbereitungszeit (z. B. 10 Min)", "Kochzeit (z. B. 30 Min)",
        "Portionen", "Schwierigkeitsgrad", "Tipps oder Varianten"
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    # Mapping von Feldern
    field_map = {
        "Titel des Rezepts*": "title",
        "Untertitel": "subtitle", 
        "Kategorie": "category",
        "Vorbereitungszeit (z. B. 10 Min)": "preparationTime",
        "Kochzeit (z. B. 30 Min)": "cookTime",
        "Portionen": "portion",
        "Schwierigkeitsgrad": "difficulty",
        "Tipps oder Varianten": "tips"
    }

    # Copy simple fields
    fields_copied = []
    for form_field, json_field in field_map.items():
        try:
            value = parsed.get(json_field, "")
            if form_field == "Portionen":
                value = int(value) if value else 1
            st.session_state[form_field] = value
            fields_copied.append(form_field)
        except Exception as e:
            st.error(f"Fehler beim Kopieren von {json_field}: {str(e)}")

    # Nährwerte
    try:
        nutr = parsed.get("nutrition", {}) or {}
        nutrition_map = {
            "kcal": "kcal",
            "protein": "protein",
            "carbs": "carbs", 
            "fat": "fat",
            "fiber": "fiber"
        }
        for session_key, json_key in nutrition_map.items():
            try:
                st.session_state[session_key] = int(nutr.get(json_key, 0))
                fields_copied.append(f"Nährwert: {session_key}")
            except Exception as e:
                st.error(f"Fehler beim Kopieren des Nährwerts {json_key}: {str(e)}")
    except Exception as e:
        st.error(f"Fehler beim Kopieren der Nährwerte: {str(e)}")

    # Zutaten
    try:
        ing = parsed.get("ingredients", []) or []
        st.session_state["num_groups"] = max(1, len(ing))
        
        for i, group in enumerate(ing):
            # Gruppenname
            try:
                st.session_state[f"groupname_{i}"] = group.get("group", "")
                fields_copied.append(f"Zutatengruppe {i+1}")
            except Exception as e:
                st.error(f"Fehler beim Kopieren der Zutatengruppe {i+1}: {str(e)}")
            
            # Zutaten der Gruppe
            items = group.get("items", []) or []
            st.session_state[f"items_{i}"] = max(1, len(items))
            
            for j, item in enumerate(items):
                try:
                    st.session_state[f"amount_{i}_{j}"] = item.get("amount", "")
                    st.session_state[f"unit_{i}_{j}"] = item.get("unit", "")
                    st.session_state[f"name_{i}_{j}"] = item.get("name", "")
                    fields_copied.append(f"Zutat {i+1}.{j+1}")
                except Exception as e:
                    st.error(f"Fehler beim Kopieren der Zutat {i+1}.{j+1}: {str(e)}")
    except Exception as e:
        st.error(f"Fehler beim Kopieren der Zutaten: {str(e)}")

    # Zubereitungsschritte erst aus session_state löschen
    step_keys = [key for key in st.session_state.keys() if any(
        key.startswith(prefix) for prefix in ["time_", "needed_", "n_amount_", "n_unit_", "n_name_", "sub_", "subtext_"]
    )]
    for key in step_keys:
        del st.session_state[key]
    
    # Dann neue Schritte setzen
    try:
        steps = parsed.get("steps", []) or []
        st.session_state["num_steps"] = max(1, len(steps))
        
        for s, step in enumerate(steps):
            # Zeit pro Schritt
            try:
                st.session_state[f"time_{s}"] = step.get("time", "")
                fields_copied.append(f"Schritt {s+1} Zeit")
            except Exception as e:
                st.error(f"Fehler beim Kopieren der Zeit für Schritt {s+1}: {str(e)}")
            
            # Benötigte Zutaten pro Schritt
            try:
                needed = step.get("needed", []) or []
                st.session_state[f"needed_{s}"] = max(0, len(needed))
                
                for n, need in enumerate(needed):
                    st.session_state[f"n_amount_{s}_{n}"] = need.get("amount", "")
                    st.session_state[f"n_unit_{s}_{n}"] = need.get("unit", "")
                    st.session_state[f"n_name_{s}_{n}"] = need.get("name", "")
                    fields_copied.append(f"Schritt {s+1} Zutat {n+1}")
            except Exception as e:
                st.error(f"Fehler beim Kopieren der benötigten Zutaten für Schritt {s+1}: {str(e)}")
            
            # Teilschritte
            try:
                substeps = step.get("substeps", []) or []
                st.session_state[f"sub_{s}"] = max(1, len(substeps))
                
                for subi, subv in enumerate(substeps):
                    st.session_state[f"subtext_{s}_{subi}"] = subv
                    fields_copied.append(f"Schritt {s+1} Teilschritt {subi+1}")
            except Exception as e:
                st.error(f"Fehler beim Kopieren der Teilschritte für Schritt {s+1}: {str(e)}")
                
    except Exception as e:
        st.error(f"Fehler beim Kopieren der Zubereitungsschritte: {str(e)}")

    # Bearbeitungsmodus-spezifische Felder
    if for_edit:
        try:
            # Hauptfelder für Bearbeitungsmodus
            st.session_state["Titel*"] = parsed.get("title", "")
            fields_copied.append("Titel (Bearbeitungsmodus)")
            
            # Zutaten im Bearbeitungsmodus
            for gi, group in enumerate(ing):
                try:
                    st.session_state[f"gname_{gi}"] = group.get("group", "")
                    fields_copied.append(f"Zutatengruppe {gi+1} (Bearbeitungsmodus)")
                    
                    for ji, item in enumerate(group.get("items", [])):
                        st.session_state[f"e_amount_{gi}_{ji}"] = item.get("amount", "")
                        st.session_state[f"e_unit_{gi}_{ji}"] = item.get("unit", "")
                        st.session_state[f"e_name_{gi}_{ji}"] = item.get("name", "")
                        fields_copied.append(f"Zutat {gi+1}.{ji+1} (Bearbeitungsmodus)")
                except Exception as e:
                    st.error(f"Fehler beim Kopieren der Zutaten im Bearbeitungsmodus: {str(e)}")
            
            # Schritte im Bearbeitungsmodus
            for si, step in enumerate(steps):
                try:
                    st.session_state[f"e_time_{si}"] = step.get("time", "")
                    fields_copied.append(f"Schritt {si+1} Zeit (Bearbeitungsmodus)")
                    
                    for ni, need in enumerate(step.get("needed", [])):
                        st.session_state[f"e_n_amount_{si}_{ni}"] = need.get("amount", "")
                        st.session_state[f"e_n_unit_{si}_{ni}"] = need.get("unit", "")
                        st.session_state[f"e_n_name_{si}_{ni}"] = need.get("name", "")
                        fields_copied.append(f"Schritt {si+1} Zutat {ni+1} (Bearbeitungsmodus)")
                    
                    for subi, subv in enumerate(step.get("substeps", [])):
                        st.session_state[f"e_sub_{si}_{subi}"] = subv
                        fields_copied.append(f"Schritt {si+1} Teilschritt {subi+1} (Bearbeitungsmodus)")
                except Exception as e:
                    st.error(f"Fehler beim Kopieren der Schritte im Bearbeitungsmodus: {str(e)}")
                    
        except Exception as e:
            st.error(f"Fehler beim Kopieren der Bearbeitungsmodus-Felder: {str(e)}")

    # Statusmeldung
    st.write(f"✅ {len(fields_copied)} Felder erfolgreich übertragen")
    
    # Formular neu laden wenn gewünscht
    if rerun:
        try:
            safe_rerun()
        except Exception as e:
            st.error(f"Fehler beim Neuladen des Formulars: {str(e)}")

# ====== Streamlit App ======
st.set_page_config(page_title="VeganTalia Admin", layout="wide")
st.title("🥦 VeganTalia Rezept-Admin")

# Einmalige Abhängigkeitsprüfung am Anfang
if not check_dependencies():
    st.stop()

# Load API key at startup (configures genai if available)
_ = load_api_key()

# Hauptnavigation
mode = st.sidebar.radio(
    "Was möchtest du tun?",
    ["Neues Rezept erstellen", "Rezept bearbeiten", "Rezept löschen", "Alle Rezepte ansehen", "🏠 Startseiten-Rezepte", "📋 Vorlagen verwalten", "📸 Bilder verwalten"]
)

# Auto-Save Toggle (GANZ OBEN in der Sidebar, direkt nach Navigation)
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Speicher-Einstellungen")
auto_save = st.sidebar.checkbox(
    "🔄 Auto-Save aktivieren",
    value=st.session_state.get('auto_save_enabled', False),
    help="Wenn aktiviert: Änderungen werden sofort gespeichert (alte Funktion). Wenn deaktiviert: Nur manuelles Speichern über Button."
)
st.session_state['auto_save_enabled'] = auto_save

if not auto_save:
    st.sidebar.warning("⚠️ Auto-Save ist AUS - du musst manuell speichern!")
else:
    st.sidebar.success("✅ Auto-Save ist AN - Änderungen werden sofort gespeichert")

st.sidebar.markdown("---")

recipes = load_recipes()

# ====== Rezept-Erstellung ======
if mode == "Neues Rezept erstellen":
    st.header("➕ Neues Rezept hinzufügen")
    
    # === REZEPT-TEMPLATES ===
    with st.expander("📋 Rezept aus Vorlage erstellen", expanded=False):
        st.markdown("**Wähle eine Vorlage für schnelleren Start:**")
        
        # Standard-Vorlagen (immer verfügbar)
        default_templates = {
            "🥗 Salat": {
                "category": "Salate & Vorspeisen",
                "difficulty": "Einfach",
                "ingredients": [{"group": "Basis", "items": [
                    {"amount": "200", "unit": "g", "name": "Blattsalat"},
                    {"amount": "1", "unit": "Stück", "name": "Gurke"},
                    {"amount": "200", "unit": "g", "name": "Tomaten"}
                ]}],
                "tags": ["salat", "frisch", "schnell"]
            },
            "🍝 Pasta": {
                "category": "Hauptgerichte",
                "difficulty": "Mittel",
                "ingredients": [{"group": "Pasta", "items": [
                    {"amount": "400", "unit": "g", "name": "Pasta"},
                    {"amount": "400", "unit": "ml", "name": "Tomatensauce"},
                    {"amount": "2", "unit": "Zehen", "name": "Knoblauch"}
                ]}],
                "tags": ["pasta", "italienisch", "klassiker"]
            },
            "🍲 Suppe": {
                "category": "Suppen & Eintöpfe",
                "difficulty": "Einfach",
                "ingredients": [{"group": "Basis", "items": [
                    {"amount": "1", "unit": "l", "name": "Gemüsebrühe"},
                    {"amount": "3", "unit": "Stück", "name": "Kartoffeln"},
                    {"amount": "2", "unit": "Stück", "name": "Karotten"}
                ]}],
                "tags": ["suppe", "warm", "comfort-food"]
            },
            "🍕 Pizza": {
                "category": "Hauptgerichte",
                "difficulty": "Mittel",
                "ingredients": [
                    {"group": "Teig", "items": [
                        {"amount": "500", "unit": "g", "name": "Mehl"},
                        {"amount": "300", "unit": "ml", "name": "Wasser"},
                        {"amount": "1", "unit": "Pck", "name": "Hefe"}
                    ]},
                    {"group": "Belag", "items": [
                        {"amount": "200", "unit": "ml", "name": "Tomatensauce"},
                        {"amount": "200", "unit": "g", "name": "Veganer Käse"}
                    ]}
                ],
                "tags": ["pizza", "italienisch", "klassiker"]
            },
            "🍰 Kuchen": {
                "category": "Desserts",
                "difficulty": "Mittel",
                "ingredients": [{"group": "Teig", "items": [
                    {"amount": "300", "unit": "g", "name": "Mehl"},
                    {"amount": "200", "unit": "g", "name": "Zucker"},
                    {"amount": "200", "unit": "ml", "name": "Pflanzenmilch"}
                ]}],
                "tags": ["dessert", "süß", "backen"]
            }
        }
        
        # Lade benutzerdefinierte Vorlagen
        custom_templates_list = load_templates()
        
        # Kombiniere beide (benutzerdefiniert zuerst)
        templates = {}
        
        # Füge benutzerdefinierte Vorlagen hinzu
        for custom_tmpl in custom_templates_list:
            templates[custom_tmpl.get("name", "Unbenannt")] = custom_tmpl
        
        # Füge Standard-Vorlagen hinzu (wenn Name nicht schon existiert)
        for name, tmpl in default_templates.items():
            if name not in templates:
                templates[name] = tmpl
        
        # Info über Vorlagen-Verwaltung
        if custom_templates_list:
            st.info(f"💡 {len(custom_templates_list)} eigene Vorlage(n) + {len(default_templates)} Standard-Vorlagen verfügbar")
        else:
            st.info("💡 5 Standard-Vorlagen verfügbar. Erstelle eigene unter '📋 Vorlagen verwalten'")
        
        template_choice = st.selectbox("Vorlage wählen:", ["Keine"] + list(templates.keys()))
        
        if template_choice != "Keine" and st.button("✅ Vorlage übernehmen"):
            template = templates[template_choice]
            # Übertrage Template-Daten in session_state
            st.session_state["Kategorie"] = template.get("category", "")
            st.session_state["Schwierigkeitsgrad"] = template.get("difficulty", "Einfach")
            
            # Zutaten
            ingredients = template.get("ingredients", [])
            st.session_state["num_groups"] = len(ingredients)
            for i, group in enumerate(ingredients):
                st.session_state[f"groupname_{i}"] = group.get("group", "")
                items = group.get("items", [])
                st.session_state[f"items_{i}"] = len(items)
                for j, item in enumerate(items):
                    st.session_state[f"amount_{i}_{j}"] = item.get("amount", "")
                    st.session_state[f"unit_{i}_{j}"] = item.get("unit", "")
                    st.session_state[f"name_{i}_{j}"] = item.get("name", "")
            
            # Tags
            if template.get("tags"):
                st.session_state["custom_tags"] = ", ".join(template["tags"])
            
            st.success(f"✅ Vorlage '{template_choice}' wurde geladen!")
            st.info("🔄 Scrolle nach unten um die Vorlage zu sehen und anzupassen.")
            safe_rerun()

    # Recipe generation assistant
    with st.expander("🧙‍♂️ Rezept-Assistent: URLs, Text oder AI"):
        gen_type = st.radio(
            "Wie möchtest du das Rezept erstellen?",
            ["URLs (bis zu 3 Links)", "Freier Text / Beschreibung", "Gemini AI (kostenlos)"],
            index=0
        )
        
        # Check API key early if Gemini is selected
        if gen_type == "Gemini AI (kostenlos)":
            api_key = load_api_key()
            if not api_key:
                st.error("🔑 Gemini API-Key fehlt - Bitte einrichten:")
                
                st.markdown("""
                **So richtest du den API-Key ein:**
                1. Gehe zu [Google AI Studio](https://aistudio.google.com/app/apikey)
                2. Klicke auf 'Create API Key' (kostenlos)
                3. Kopiere den Key hier ein:
                """)
                
                # API Key Input
                api_key_input = st.text_input(
                    "API Key",
                    type="password",
                    help="Der Key wird sicher in config/.env gespeichert.",
                    key="api_key_setup_input"
                )
                
                # Save Button
                if st.button("✅ Speichern & Verwenden", key="save_api_key_btn", type="primary"):
                    if not api_key_input:
                        st.error("❌ Bitte gib einen API-Key ein!")
                    elif len(api_key_input) < 20:
                        st.error("❌ API-Key zu kurz (min. 20 Zeichen)!")
                    else:
                        with st.spinner("Speichere und teste API-Key..."):
                            if save_api_key(api_key_input):
                                st.success("✅ API-Key gespeichert und getestet!")
                                st.info("🔄 Seite wird neu geladen...")
                                time.sleep(2)
                                safe_rerun()
                            else:
                                st.error("❌ Speichern/Testen fehlgeschlagen - siehe Fehler oben")
                
                st.stop()  # Stop here until key is configured
        
        if gen_type == "URLs (bis zu 3 Links)":
            url1 = st.text_input("🔗 Erste URL (Hauptquelle)")
            url2 = st.text_input("🔗 Zweite URL (optional)")
            url3 = st.text_input("🔗 Dritte URL (optional)")
            ai_input = "\n".join([u for u in [url1, url2, url3] if u.strip()])
        else:
            ai_input = st.text_area(
                "✍️ Beschreibe dein Rezept" if gen_type == "Freier Text / Beschreibung" 
                else "🤖 Was für ein Rezept soll Gemini erstellen?",
                help="Bei Freitext: Beschreibe das Rezept so detailliert wie möglich.\n"
                     "Bei Gemini: Beschreibe was du kochen möchtest, Gemini macht daraus ein Rezept."
            )
            
        if st.button("🎲 Rezept generieren"): 
            try:
                combined = ""
                if gen_type == "URLs (bis zu 3 Links)":
                    # Process URLs
                    urls = [u.strip() for u in ai_input.splitlines() if u.strip()]
                    if not urls:
                        st.error("Bitte mindestens eine URL eingeben.")
                        st.stop()
                    
                    progress_text = "Lade Rezeptdaten..."
                    progress_bar = st.progress(0, text=progress_text)
                    
                    texts = []
                    with st.spinner(""):
                        for i, u in enumerate(urls):
                            progress_bar.progress((i / len(urls)), f"Lade URL {i+1} von {len(urls)}...")
                            try:
                                text = fetch_url_text(u)
                                if text:
                                    texts.append(f"URL {i+1}:\n{text}")
                                    st.success(f"✅ URL {i+1} erfolgreich geladen", icon="✅")
                                else:
                                    st.warning(f"⚠️ URL {i+1}: Keine Daten gefunden", icon="⚠️")
                            except Exception as e:
                                st.error(f"❌ URL {i+1}: Fehler beim Laden: {str(e)}", icon="🚫")
                            time.sleep(0.2)
                            
                    progress_bar.progress(1.0, "Fertig!")
                    
                    if texts:
                        combined = "\n\n---\n\n".join(texts)
                        st.success(f"✅ {len(texts)} von {len(urls)} URLs erfolgreich verarbeitet")
                    else:
                        st.error("❌ Konnte keine Rezeptdaten von den URLs laden.")
                        st.stop()
                        
                elif gen_type == "Gemini AI (kostenlos)":
                    if not ai_input or not ai_input.strip():
                        st.error("❌ Bitte beschreibe was für ein Rezept du erstellen möchtest!")
                        st.stop()
                    
                    with st.spinner("Generiere Rezept mit Gemini AI..."):
                        prompt = f"""Erstelle ein VOLLSTÄNDIGES veganes Rezept basierend auf dieser Beschreibung:
{ai_input}

Gib das Rezept im folgenden JSON-Format zurück:

{{
  "title": "Rezeptname",
  "subtitle": "Kurze Beschreibung",
  "category": "Hauptgerichte",
  "preparationTime": "15 Min",
  "cookTime": "30 Min",
  "portion": 4,
  "difficulty": "Mittel",
  "ingredients": [
    {{
      "group": "Für den Hauptteil",
      "items": [
        {{"amount": "200", "unit": "g", "name": "Kichererbsen"}},
        {{"amount": "2", "unit": "EL", "name": "Olivenöl"}},
        {{"amount": "1", "unit": "Zehe", "name": "Knoblauch"}}
      ]
    }}
  ],
  "steps": [
    {{
      "time": "5 Min",
      "needed": [
        {{"amount": "200", "unit": "g", "name": "Kichererbsen"}},
        {{"amount": "2", "unit": "EL", "name": "Olivenöl"}}
      ],
      "substeps": [
        "Kichererbsen in ein Sieb geben und abspülen",
        "Mit Olivenöl in den Mixer geben und glatt pürieren"
      ]
    }},
    {{
      "time": "10 Min",
      "needed": [
        {{"amount": "1", "unit": "Zehe", "name": "Knoblauch"}}
      ],
      "substeps": [
        "Knoblauch schälen und fein hacken",
        "Zur Masse geben und nochmal kurz mixen"
      ]
    }}
  ],
  "tips": "Kann auch mit Tahini verfeinert werden"
}}

KRITISCH WICHTIG:
- JEDER Schritt MUSS ein "needed"-Array mit den verwendeten Zutaten enthalten!
- Das "needed"-Array darf NIEMALS leer sein!
- Trage die Zutaten mit exakten Mengen ein die in diesem Schritt benutzt werden
- Erstelle mindestens 5-8 detaillierte Schritte
- Gib NUR valides JSON zurück, KEINE Erklärungen oder Markdown
"""
                        combined = call_gemini(prompt)
                        
                        if not combined:
                            st.error("❌ Gemini konnte kein Rezept generieren.")
                            st.stop()
                        
                        # Parse JSON direkt (Gemini gibt bereits JSON zurück)
                        parsed = try_parse_json(combined)
                        if not parsed or not parsed.get("title"):
                            st.error("❌ Gemini hat kein valides Rezept-JSON zurückgegeben.")
                            st.stop()
                        
                else:
                    # Process free text
                    combined = ai_input
                    parsed = extract_recipe_info(combined)

                # Für Gemini AI: parsed wurde bereits oben gesetzt
                # Für andere Modi: extract_recipe_info wurde oben aufgerufen
                if gen_type != "Gemini AI (kostenlos)":
                    parsed = extract_recipe_info(combined)
                
                if parsed:
                    st.success("✨ Rezept erfolgreich generiert!")
                    
                    # ensure nutrition exists (estimate if missing)
                    if not parsed.get("nutrition"):
                        with st.spinner("🧮 Berechne Nährwerte..."):
                            try:
                                portions = parsed.get("portion", 1)
                                parsed["nutrition"] = compute_nutrition_from_swiss(parsed.get("ingredients", []), portions)
                            except Exception as e:
                                st.warning(f"Nährwertberechnung fehlgeschlagen: {e}")
                                parsed["nutrition"] = {"kcal":0,"protein":0,"carbs":0,"fat":0,"fiber":0}
                    
                    # Verwende die zentrale process_form_transfer Funktion
                    transfer_success = process_form_transfer(parsed)
                    
                    if transfer_success:
                        st.success("✅ Rezept wurde in die Formularfelder übertragen! Scrolle nach unten zum Bearbeiten.")
                    else:
                        st.error("❌ Fehler beim Übertragen. Bitte versuche es erneut oder kontaktiere Support.")
                    
                    # Vorschau ENTFERNT - nicht mehr benötigt
                    
                    # Speichern für JSON-Vorschau (optional)
                    st.session_state["preview_recipe"] = parsed
                    
                    # Zeige Debug-Info nur wenn gewünscht
                    with st.expander("🔍 Debug-Info & JSON", expanded=False):
                        st.write("Gefundene Felder:", list(parsed.keys()))
                        st.json(parsed)
                else:
                    st.error("Konnte keine Rezeptinformationen aus dem Text extrahieren. Rohdaten:")
                    st.code(combined)
            except Exception as e:
                st.error(f"AI-Generierung fehlgeschlagen: {e}")

    # Formularfelder - verwenden Session State Keys statt default values
    title = st.text_input("Titel des Rezepts*", key="Titel des Rezepts*")
    subtitle = st.text_input("Untertitel", key="Untertitel")
    
    # Kategorie mit Option für neue Kategorie
    categories = load_categories()
    categories_with_new = categories + ["➕ Neue Kategorie..."]
    category_selection = st.selectbox("Kategorie", categories_with_new, key="Kategorie")
    
    if category_selection == "➕ Neue Kategorie...":
        new_category = st.text_input("Neue Kategorie eingeben:", key="new_category_input")
        if new_category and new_category.strip():
            category = new_category.strip()
            # Füge neue Kategorie zu categories.json hinzu
            if category not in categories:
                categories.append(category)
                if save_categories(categories):
                    st.success(f"✅ Neue Kategorie '{category}' hinzugefügt!")
                    load_categories.clear()  # Cache leeren
        else:
            category = ""
    else:
        category = category_selection
    
    preparation_time = st.text_input("Vorbereitungszeit (z. B. 10 Min)", key="Vorbereitungszeit (z. B. 10 Min)")
    cook_time = st.text_input("Kochzeit (z. B. 30 Min)", key="Kochzeit (z. B. 30 Min)")
    
    # Portionen: Lies aus session_state OHNE Key-Konflikt
    portion_value = st.session_state.get("portion_value", 2)
    portion = st.number_input("Portionen", min_value=1, max_value=20, value=portion_value, key="portion_input")
    
    difficulty = st.selectbox("Schwierigkeitsgrad", ["Einfach", "Mittel", "Schwer"], key="Schwierigkeitsgrad")
    
    # === Tags System ===
    st.subheader("🏷️ Tags")
    
    # Sammle existierende Tags aus allen Rezepten
    all_existing_tags = set()
    for recipe in load_recipes():
        if "tags" in recipe and recipe["tags"]:
            if isinstance(recipe["tags"], list):
                all_existing_tags.update(recipe["tags"])
            elif isinstance(recipe["tags"], str):
                all_existing_tags.update([t.strip() for t in recipe["tags"].split(",") if t.strip()])
    
    # Zeige populäre Tags als Vorschläge
    if all_existing_tags:
        st.markdown("**Beliebte Tags:**")
        popular_tags = sorted(all_existing_tags)[:10]
        tag_cols = st.columns(min(5, len(popular_tags)))
        selected_tags = []
        for i, tag in enumerate(popular_tags):
            with tag_cols[i % 5]:
                if st.checkbox(tag, key=f"tag_check_{tag}"):
                    selected_tags.append(tag)
    else:
        selected_tags = []
    
    # Freies Eingabefeld für neue/weitere Tags
    custom_tags_input = st.text_input(
        "Weitere Tags (komma-getrennt)",
        placeholder="z.B. glutenfrei, schnell, familienfreundlich",
        key="custom_tags"
    )
    
    # Kombiniere ausgewählte + custom Tags
    final_tags = selected_tags.copy()
    if custom_tags_input:
        final_tags.extend([t.strip().lower() for t in custom_tags_input.split(",") if t.strip()])
    
    # Zeige finale Tags
    if final_tags:
        st.info(f"🏷️ Tags: {', '.join(final_tags)}")

    # === Veröffentlichungs-Status ===
    st.subheader("🌐 Veröffentlichung")
    is_published = st.checkbox(
        "✅ Veröffentlicht",
        value=True,
        help="Nur veröffentlichte Rezepte erscheinen auf der Website",
        key="is_published"
    )
    if is_published:
        st.success("Rezept ist öffentlich sichtbar")
    else:
        st.warning("Rezept ist offline (nur im Admin sichtbar)")
    
    st.info("💡 Tipp: 'Startseiten-Rezepte' kannst du unter dem Menüpunkt '🏠 Startseiten-Rezepte' festlegen")

    # === Bild-Upload (3 Modi) ===
    st.subheader("📸 Rezeptbild")
    
    image_mode = st.radio(
        "Bild-Quelle wählen:",
        ["📁 Datei hochladen", "📷 Kamera", "🖼️ Dateiname (src/assets/)", "🌐 URL (extern)"],
        horizontal=True,
        key="image_mode"
    )
    
    image_base64 = ""
    image_filename = ""
    image_url = ""
    
    if "📁" in image_mode:
        # Upload: Speichere als Base64
        image_file = st.file_uploader("Bild hochladen", type=["png", "jpg", "jpeg"], key="img_upload")
        if image_file:
            image_base64 = encode_image_to_base64(image_file)
            
            # Optional: Auch in src/assets/ speichern
            col_save, col_preview = st.columns([1, 3])
            with col_save:
                if st.checkbox("Auch in src/assets/ speichern", value=True):
                    # Pfad relativ zum Script (admin/ → ../src/assets/)
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    assets_path = os.path.join(script_dir, "..", "src", "assets")
                    os.makedirs(assets_path, exist_ok=True)
                    
                    # Generiere Dateiname aus Titel
                    title_slug = st.session_state.get("Titel des Rezepts*", "rezept").lower()
                    title_slug = "".join(c if c.isalnum() else "_" for c in title_slug)[:30]
                    ext = image_file.name.split(".")[-1]
                    save_filename = f"{title_slug}.{ext}"
                    
                    save_path = os.path.join(assets_path, save_filename)
                    with open(save_path, "wb") as f:
                        f.write(image_file.getbuffer())
                    st.success(f"✅ Gespeichert: src/assets/{save_filename}")
                    image_filename = save_filename
            
            with col_preview:
                st.image(image_file, width=200, caption="Vorschau")
    
    elif "�" in image_mode:
        # Kamera: Live-Aufnahme
        camera_image = st.camera_input("Foto aufnehmen", key="camera_input")
        if camera_image:
            image_base64 = encode_image_to_base64(camera_image)
            st.success("✅ Kamera-Foto erfasst!")
            
            # Optional: Auch in src/assets/ speichern
            if st.checkbox("Auch in src/assets/ speichern", value=False):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                assets_path = os.path.join(script_dir, "..", "src", "assets")
                os.makedirs(assets_path, exist_ok=True)
                
                title_slug = st.session_state.get("Titel des Rezepts*", "rezept").lower()
                title_slug = "".join(c if c.isalnum() else "_" for c in title_slug)[:30]
                filename = f"{title_slug}-camera.jpg"
                
                with open(os.path.join(assets_path, filename), "wb") as f:
                    f.write(camera_image.getbuffer())
                
                st.info(f"💾 Gespeichert als: {filename}")
                image_filename = filename
    
    elif "�🖼️" in image_mode:
        # Dateiname: Nutze Bilder aus ../src/assets/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        assets_path = os.path.join(script_dir, "..", "src", "assets")
        if os.path.exists(assets_path):
            existing_images = [f for f in os.listdir(assets_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
            if existing_images:
                image_filename = st.selectbox("Wähle existierendes Bild:", [""] + existing_images, key="img_select")
                if image_filename:
                    # Zeige Vorschau
                    preview_path = os.path.join(assets_path, image_filename)
                    st.image(preview_path, width=200, caption=image_filename)
            else:
                st.warning("⚠️ Keine Bilder in src/assets/ gefunden. Lade ein Bild hoch oder nutze eine URL.")
        else:
            st.error(f"❌ Ordner src/assets/ existiert nicht: {assets_path}")
    
    elif "🌐" in image_mode:
        # URL: Externe Bild-URL
        image_url = st.text_input("Bild-URL eingeben:", placeholder="https://example.com/bild.jpg", key="img_url")
        if image_url:
            try:
                # Vorschau
                st.image(image_url, width=200, caption="Vorschau (extern)")
                
                # Optional: Bild herunterladen und in assets/ speichern
                if st.checkbox("Bild herunterladen und lokal speichern", value=False):
                    import requests
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        assets_path = os.path.join(script_dir, "..", "src", "assets")
                        os.makedirs(assets_path, exist_ok=True)
                        
                        title_slug = st.session_state.get("Titel des Rezepts*", "rezept").lower()
                        title_slug = "".join(c if c.isalnum() else "_" for c in title_slug)[:30]
                        ext = image_url.split(".")[-1].split("?")[0]  # Entferne Query-Params
                        if ext not in ['png', 'jpg', 'jpeg', 'webp']:
                            ext = 'jpg'
                        save_filename = f"{title_slug}.{ext}"
                        
                        save_path = os.path.join(assets_path, save_filename)
                        with open(save_path, "wb") as f:
                            f.write(response.content)
                        
                        # Konvertiere zu Base64 für recipes.json
                        image_base64 = base64.b64encode(response.content).decode('utf-8')
                        image_filename = save_filename
                        st.success(f"✅ Heruntergeladen: src/assets/{save_filename}")
                    else:
                        st.error(f"❌ Download fehlgeschlagen: HTTP {response.status_code}")
            except Exception as e:
                st.error(f"❌ Fehler beim Laden der URL: {e}")

    st.subheader("🧂 Zutaten")
    ingredient_groups = []
    
    # num_groups: Session State initialisieren (nur einmal)
    if "num_groups" not in st.session_state:
        st.session_state["num_groups"] = 1
    
    num_groups = st.number_input("Anzahl der Zutaten-Obergruppen", min_value=1, key="num_groups")
    
    for i in range(num_groups):
        st.markdown(f"#### Obergruppe {i+1}")
        group_name = st.text_input(f"Obergruppenname {i+1}", key=f"groupname_{i}")
        
        # items count: Session State initialisieren
        if f"items_{i}" not in st.session_state:
            st.session_state[f"items_{i}"] = 1
        
        num_items = st.number_input(f"Anzahl Zutaten in Gruppe {i+1}", min_value=1, key=f"items_{i}")
        
        items = []
        for j in range(num_items):
            cols = st.columns([0.5,0.5,2,2,5,1])
            
            # Verschiebe-Buttons
            with cols[0]:
                if j > 0:
                    if st.button("↑", key=f"up_ing_{i}_{j}", help="Nach oben"):
                        # Tausche Werte in session_state
                        for field in ["amount", "unit", "name"]:
                            key_current = f"{field}_{i}_{j}"
                            key_above = f"{field}_{i}_{j-1}"
                            temp = st.session_state.get(key_current, "")
                            st.session_state[key_current] = st.session_state.get(key_above, "")
                            st.session_state[key_above] = temp
                        safe_rerun()
            with cols[1]:
                if j < num_items - 1:
                    if st.button("↓", key=f"down_ing_{i}_{j}", help="Nach unten"):
                        # Tausche Werte in session_state
                        for field in ["amount", "unit", "name"]:
                            key_current = f"{field}_{i}_{j}"
                            key_below = f"{field}_{i}_{j+1}"
                            temp = st.session_state.get(key_current, "")
                            st.session_state[key_current] = st.session_state.get(key_below, "")
                            st.session_state[key_below] = temp
                        safe_rerun()
            
            with cols[2]:
                amount = st.text_input(f"Menge", key=f"amount_{i}_{j}", label_visibility="collapsed", placeholder="Menge")
            with cols[3]:
                unit = st.text_input(f"Einheit", key=f"unit_{i}_{j}", label_visibility="collapsed", placeholder="Einheit")
            with cols[4]:
                name = st.text_input(f"Zutat", key=f"name_{i}_{j}", label_visibility="collapsed", placeholder="Zutat")
            with cols[5]:
                if st.button("✕", key=f"del_ing_create_{i}_{j}", help="Zutat löschen"):
                    # Lösche die Werte aus session_state
                    for field in ["amount", "unit", "name"]:
                        st.session_state.pop(f"{field}_{i}_{j}", None)
                    # Hinweis: Anzahl wird beim nächsten Rerun angepasst
                    safe_rerun()
            
            if name.strip():
                items.append({"amount": amount, "unit": unit, "name": name})
        
        ingredient_groups.append({"group": group_name, "items": items})

    st.subheader("🍳 Zubereitungsschritte")
    
    num_steps_default = st.session_state.get("num_steps", 1)
    num_steps = st.number_input("Anzahl Schritte", min_value=1, value=num_steps_default, key="num_steps")
    
    steps = []
    for s in range(num_steps):
        st.markdown(f"#### Schritt {s+1}")
        
        # Verschiebe-Buttons für Hauptschritte
        col_up, col_down, col_time, col_del = st.columns([0.5, 0.5, 8, 1])
        
        with col_up:
            if s > 0:
                if st.button("↑", key=f"up_main_{s}", help="Schritt nach oben"):
                    # Tausche ALLE Daten des Schrittes (inkl. aller Unterpunkte)
                    s_above = s - 1
                    
                    # 1. Hauptdaten tauschen
                    for field in ["time"]:
                        key_current = f"{field}_{s}"
                        key_above = f"{field}_{s_above}"
                        temp = st.session_state.get(key_current, "")
                        st.session_state[key_current] = st.session_state.get(key_above, "")
                        st.session_state[key_above] = temp
                    
                    # 2. Anzahlen tauschen
                    num_needed_current = st.session_state.get(f"needed_{s}", 0)
                    num_needed_above = st.session_state.get(f"needed_{s_above}", 0)
                    num_sub_current = st.session_state.get(f"sub_{s}", 1)
                    num_sub_above = st.session_state.get(f"sub_{s_above}", 1)
                    
                    st.session_state[f"needed_{s}"] = num_needed_above
                    st.session_state[f"needed_{s_above}"] = num_needed_current
                    st.session_state[f"sub_{s}"] = num_sub_above
                    st.session_state[f"sub_{s_above}"] = num_sub_current
                    
                    # 3. Alle benötigten Zutaten tauschen
                    max_needed = max(num_needed_current, num_needed_above)
                    for n in range(max_needed):
                        for field in ["n_amount", "n_unit", "n_name"]:
                            key_current = f"{field}_{s}_{n}"
                            key_above = f"{field}_{s_above}_{n}"
                            temp = st.session_state.get(key_current, "")
                            st.session_state[key_current] = st.session_state.get(key_above, "")
                            st.session_state[key_above] = temp
                    
                    # 4. Alle Substeps tauschen
                    max_sub = max(num_sub_current, num_sub_above)
                    for sub in range(max_sub):
                        key_current = f"subtext_{s}_{sub}"
                        key_above = f"subtext_{s_above}_{sub}"
                        temp = st.session_state.get(key_current, "")
                        st.session_state[key_current] = st.session_state.get(key_above, "")
                        st.session_state[key_above] = temp
                    
                    safe_rerun()
        
        with col_down:
            if s < num_steps - 1:
                if st.button("↓", key=f"down_main_{s}", help="Schritt nach unten"):
                    # Tausche ALLE Daten des Schrittes (inkl. aller Unterpunkte)
                    s_below = s + 1
                    
                    # 1. Hauptdaten tauschen
                    for field in ["time"]:
                        key_current = f"{field}_{s}"
                        key_below = f"{field}_{s_below}"
                        temp = st.session_state.get(key_current, "")
                        st.session_state[key_current] = st.session_state.get(key_below, "")
                        st.session_state[key_below] = temp
                    
                    # 2. Anzahlen tauschen
                    num_needed_current = st.session_state.get(f"needed_{s}", 0)
                    num_needed_below = st.session_state.get(f"needed_{s_below}", 0)
                    num_sub_current = st.session_state.get(f"sub_{s}", 1)
                    num_sub_below = st.session_state.get(f"sub_{s_below}", 1)
                    
                    st.session_state[f"needed_{s}"] = num_needed_below
                    st.session_state[f"needed_{s_below}"] = num_needed_current
                    st.session_state[f"sub_{s}"] = num_sub_below
                    st.session_state[f"sub_{s_below}"] = num_sub_current
                    
                    # 3. Alle benötigten Zutaten tauschen
                    max_needed = max(num_needed_current, num_needed_below)
                    for n in range(max_needed):
                        for field in ["n_amount", "n_unit", "n_name"]:
                            key_current = f"{field}_{s}_{n}"
                            key_below = f"{field}_{s_below}_{n}"
                            temp = st.session_state.get(key_current, "")
                            st.session_state[key_current] = st.session_state.get(key_below, "")
                            st.session_state[key_below] = temp
                    
                    # 4. Alle Substeps tauschen
                    max_sub = max(num_sub_current, num_sub_below)
                    for sub in range(max_sub):
                        key_current = f"subtext_{s}_{sub}"
                        key_below = f"subtext_{s_below}_{sub}"
                        temp = st.session_state.get(key_current, "")
                        st.session_state[key_current] = st.session_state.get(key_below, "")
                        st.session_state[key_below] = temp
                    
                    safe_rerun()
        
        with col_time:
            time = st.text_input(f"Zeit", key=f"time_{s}", placeholder="z.B. 10 Min", label_visibility="collapsed")
        
        with col_del:
            if st.button("✕", key=f"del_step_create_{s}", help="Schritt löschen"):
                st.session_state["num_steps"] = max(1, num_steps - 1)
                st.session_state.pop(f"time_{s}", None)
                st.session_state.pop(f"needed_{s}", None)
                st.session_state.pop(f"sub_{s}", None)
                safe_rerun()
        
        st.markdown("**Benötigte Zutaten:**")
        needed = []
        num_needed_default = st.session_state.get(f"needed_{s}", 0)
        num_needed = st.number_input(f"Anzahl benötigter Zutaten Schritt {s+1}", min_value=0, value=num_needed_default, key=f"needed_{s}")
        
        for n in range(num_needed):
            cols = st.columns([0.5, 0.5, 2, 2, 5, 1])
            
            # Verschiebe-Buttons für benötigte Zutaten
            with cols[0]:
                if n > 0:
                    if st.button("↑", key=f"up_need_{s}_{n}", help="Nach oben"):
                        for field in ["n_amount", "n_unit", "n_name"]:
                            key_current = f"{field}_{s}_{n}"
                            key_above = f"{field}_{s}_{n-1}"
                            temp = st.session_state.get(key_current, "")
                            st.session_state[key_current] = st.session_state.get(key_above, "")
                            st.session_state[key_above] = temp
                        safe_rerun()
            
            with cols[1]:
                if n < num_needed - 1:
                    if st.button("↓", key=f"down_need_{s}_{n}", help="Nach unten"):
                        for field in ["n_amount", "n_unit", "n_name"]:
                            key_current = f"{field}_{s}_{n}"
                            key_below = f"{field}_{s}_{n+1}"
                            temp = st.session_state.get(key_current, "")
                            st.session_state[key_current] = st.session_state.get(key_below, "")
                            st.session_state[key_below] = temp
                        safe_rerun()
            
            with cols[2]:
                n_amount = st.text_input(f"Menge", key=f"n_amount_{s}_{n}", label_visibility="collapsed", placeholder="Menge")
            with cols[3]:
                n_unit = st.text_input(f"Einheit", key=f"n_unit_{s}_{n}", label_visibility="collapsed", placeholder="Einheit")
            with cols[4]:
                n_name = st.text_input(f"Zutat", key=f"n_name_{s}_{n}", label_visibility="collapsed", placeholder="Zutat")
            with cols[5]:
                if st.button("✕", key=f"del_needed_create_{s}_{n}", help="Zutat entfernen"):
                    st.session_state[f"needed_{s}"] = max(0, num_needed - 1)
                    for field in ["n_amount", "n_unit", "n_name"]:
                        st.session_state.pop(f"{field}_{s}_{n}", None)
                    safe_rerun()
            
            if n_name.strip():
                needed.append({"amount": n_amount, "unit": n_unit, "name": n_name})
        
        st.markdown("**Zwischenschritte:**")
        substeps = []
        num_sub_default = st.session_state.get(f"sub_{s}", 1)
        num_sub = st.number_input(f"Anzahl Zwischenschritte {s+1}", min_value=1, value=num_sub_default, key=f"sub_{s}")
        
        for sub in range(num_sub):
            subcols = st.columns([0.5, 0.5, 10, 1])
            
            # Verschiebe-Buttons für Zwischenschritte
            with subcols[0]:
                if sub > 0:
                    if st.button("↑", key=f"up_sub_{s}_{sub}", help="Nach oben"):
                        key_current = f"subtext_{s}_{sub}"
                        key_above = f"subtext_{s}_{sub-1}"
                        temp = st.session_state.get(key_current, "")
                        st.session_state[key_current] = st.session_state.get(key_above, "")
                        st.session_state[key_above] = temp
                        safe_rerun()
            
            with subcols[1]:
                if sub < num_sub - 1:
                    if st.button("↓", key=f"down_sub_{s}_{sub}", help="Nach unten"):
                        key_current = f"subtext_{s}_{sub}"
                        key_below = f"subtext_{s}_{sub+1}"
                        temp = st.session_state.get(key_current, "")
                        st.session_state[key_current] = st.session_state.get(key_below, "")
                        st.session_state[key_below] = temp
                        safe_rerun()
            
            with subcols[2]:
                subtext = st.text_area(f"Zwischenschritt {sub+1}", key=f"subtext_{s}_{sub}", label_visibility="collapsed", placeholder=f"Zwischenschritt {sub+1}")
            
            with subcols[3]:
                if st.button("✕", key=f"del_sub_create_{s}_{sub}", help="Zwischenschritt löschen"):
                    st.session_state[f"sub_{s}"] = max(1, num_sub - 1)
                    st.session_state.pop(f"subtext_{s}_{sub}", None)
                    safe_rerun()
            
            if subtext.strip():
                substeps.append(subtext)
        
        steps.append({"time": time, "needed": needed, "substeps": substeps})


    st.subheader("💡 Tipps & Variationen")
    tips = st.text_area("Tipps oder Varianten")

    st.subheader("🍽️ Nährwerte (optional)")
    
    # Check for pending nutrition values from AI calculation
    pending_nutr = st.session_state.pop("pending_nutrition_values", None)
    if pending_nutr:
        # Transfer to session state keys BEFORE widgets are created
        st.session_state["kcal"] = int(pending_nutr.get('kcal', 0))
        st.session_state["protein"] = int(pending_nutr.get('protein', 0))
        st.session_state["carbs"] = int(pending_nutr.get('carbs', 0))
        st.session_state["fat"] = int(pending_nutr.get('fat', 0))
        st.session_state["fiber"] = int(pending_nutr.get('fiber', 0))
        st.success("✅ Nährwerte wurden übernommen!")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: kcal = st.number_input("kcal", min_value=0, key="kcal")
    with col2: protein = st.number_input("Eiweiß (g)", min_value=0, key="protein")
    with col3: carbs = st.number_input("KH (g)", min_value=0, key="carbs")
    with col4: fat = st.number_input("Fett (g)", min_value=0, key="fat")
    with col5: fiber = st.number_input("Ballaststoffe (g)", min_value=0, key="fiber")

    if st.button("📋 Vorschau anzeigen"):
        preview = {
            "title": title,
            "subtitle": subtitle,
            "category": category,
            "preparationTime": preparation_time,
            "cookTime": cook_time,
            "portion": portion,
            "difficulty": difficulty,
            "image": image_base64,
            "ingredients": ingredient_groups,
            "steps": steps,
            "tips": tips,
            "nutrition": {
                "kcal": kcal,
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
                "fiber": fiber
            }
        }
        
        # === MENGENRECHNER-VORSCHAU ===
        st.markdown("---")
        st.markdown("### 🍽️ Mengenrechner-Vorschau")
        st.info("💡 Teste wie die Mengen bei unterschiedlichen Portionszahlen aussehen:")
        
        preview_portions = st.slider(
            "Portionen für Vorschau:",
            min_value=1,
            max_value=20,
            value=portion,
            key="preview_portions_slider"
        )
        
        if preview_portions != portion:
            scale_factor = preview_portions / portion
            
            st.markdown(f"**📊 Umrechnung: {portion} → {preview_portions} Portionen (Faktor: {scale_factor:.2f})**")
            
            # Zeige umgerechnete Zutaten
            with st.expander("🧂 Umgerechnete Zutaten", expanded=True):
                for group in ingredient_groups:
                    st.markdown(f"**{group.get('group', 'Gruppe')}:**")
                    for item in group.get("items", []):
                        amount = item.get("amount", "")
                        unit = item.get("unit", "")
                        name = item.get("name", "")
                        
                        # Versuche Menge zu skalieren
                        try:
                            amount_num = float(amount.replace(",", "."))
                            scaled_amount = amount_num * scale_factor
                            
                            # Formatierung
                            if scaled_amount % 1 == 0:
                                display_amount = f"{int(scaled_amount)}"
                            else:
                                display_amount = f"{scaled_amount:.1f}"
                            
                            st.write(f"• {display_amount} {unit} {name}")
                        except:
                            # Falls nicht numerisch, zeige Original
                            st.write(f"• {amount} {unit} {name}")
            
            # Zeige umgerechnete Nährwerte
            if kcal > 0 or protein > 0 or carbs > 0 or fat > 0:
                with st.expander("📊 Umgerechnete Nährwerte (gesamt)", expanded=True):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("Kalorien", f"{int(kcal * preview_portions)} kcal")
                    with col2:
                        st.metric("Protein", f"{int(protein * preview_portions)}g")
                    with col3:
                        st.metric("KH", f"{int(carbs * preview_portions)}g")
                    with col4:
                        st.metric("Fett", f"{int(fat * preview_portions)}g")
                    with col5:
                        st.metric("Ballaststoffe", f"{int(fiber * preview_portions)}g")
        
        st.markdown("---")
        st.json(preview)
        st.session_state["preview_recipe"] = preview
    # AI-based nutrition estimate
    if st.button("🔬 Nährwerte berechnen (AI)"):
        try:
            # Berechne Nährwerte
            with st.spinner("Berechne Nährwerte..."):
                nutr = compute_nutrition_from_swiss(ingredient_groups, portion)
            
            # Zeige Vorschau der berechneten Werte
            st.info("Berechnete Nährwerte (pro Portion):")
            cols = st.columns(5)
            with cols[0]: st.metric("Kalorien", f"{nutr.get('kcal', 0)} kcal")
            with cols[1]: st.metric("Protein", f"{nutr.get('protein', 0)}g")
            with cols[2]: st.metric("Kohlenhydrate", f"{nutr.get('carbs', 0)}g")
            with cols[3]: st.metric("Fett", f"{nutr.get('fat', 0)}g")
            with cols[4]: st.metric("Ballaststoffe", f"{nutr.get('fiber', 0)}g")
            
            # Bestätigungsdialog
            if st.button("✅ Diese Werte übernehmen", key="apply_nutr_main"):
                # Speichere in temporärem Key für nächsten Rerun
                st.session_state["pending_nutrition_values"] = nutr
                st.success("✅ Nährwerte werden beim nächsten Laden übernommen!")
                safe_rerun()
        except Exception as e:
            st.error(f"Nährwertberechnung fehlgeschlagen: {e}")

    # Final save and reset buttons
    col_save, col_reset = st.columns(2)
    with col_save:
        if st.button("📥 Rezept speichern"):
            try:
                # Bestimme Bild-Feld basierend auf Modus
                final_image = ""
                final_image_filename = ""
                final_image_url = ""
                
                if "📁" in st.session_state.get("image_mode", ""):
                    final_image = image_base64
                    final_image_filename = image_filename
                elif "🖼️" in st.session_state.get("image_mode", ""):
                    final_image_filename = image_filename
                elif "🌐" in st.session_state.get("image_mode", ""):
                    final_image_url = image_url
                    if image_base64:  # Falls heruntergeladen
                        final_image = image_base64
                        final_image_filename = image_filename
                
                recipe_to_save = {
                    "title": st.session_state.get("Titel des Rezepts*", title),
                    "subtitle": st.session_state.get("Untertitel", subtitle),
                    "category": st.session_state.get("Kategorie", category),
                    "preparationTime": st.session_state.get("Vorbereitungszeit (z. B. 10 Min)", preparation_time),
                    "cookTime": st.session_state.get("Kochzeit (z. B. 30 Min)", cook_time),
                    "portion": portion,  # GEÄNDERT: Direkt vom Widget
                    "difficulty": st.session_state.get("Schwierigkeitsgrad", difficulty),
                    "tags": final_tags,
                    "published": st.session_state.get("is_published", True),
                    # Featured-Rezepte werden über "Startseiten-Rezepte" verwaltet
                    "featuredWeek": False,
                    "featuredWeekText": "",
                    "featuredMonth": False,
                    "featuredMonthText": "",
                    "featuredSeason": False,
                    "featuredSeasonText": "",
                    "image": final_image,
                    "image_filename": final_image_filename,
                    "image_url": final_image_url,
                    "ingredients": ingredient_groups,
                    "steps": steps,
                    "tips": st.session_state.get("Tipps oder Varianten", tips),
                    "nutrition": {
                        "kcal": int(st.session_state.get("kcal", 0)),
                        "protein": int(st.session_state.get("protein", 0)),
                        "carbs": int(st.session_state.get("carbs", 0)),
                        "fat": int(st.session_state.get("fat", 0)),
                        "fiber": int(st.session_state.get("fiber", 0)),
                    }
                }
                
                # === VALIDIERUNG ===
                validation = validate_recipe(recipe_to_save)
                
                # Zeige Fehler (kritisch)
                if validation["errors"]:
                    st.error("**❌ Kritische Fehler gefunden:**")
                    for err in validation["errors"]:
                        st.error(err)
                    st.warning("⚠️ Bitte behebe die Fehler vor dem Speichern!")
                    st.stop()
                
                # Zeige Warnungen (optional)
                if validation["warnings"]:
                    with st.expander("⚠️ Warnungen (nicht kritisch, aber empfohlen)", expanded=True):
                        for warn in validation["warnings"]:
                            st.warning(warn)
                        st.info("💡 Du kannst trotzdem speichern, aber diese Punkte verbessern die Qualität.")
                
                # Füge Metadaten hinzu
                recipe_to_save = add_metadata_to_recipe(recipe_to_save, is_new=True)
                
                # Generiere SEO-Metadaten
                seo_data = generate_seo_metadata(recipe_to_save)
                recipe_to_save["seo"] = seo_data
                
                all_recipes = load_recipes()
                all_recipes.append(recipe_to_save)
                if save_recipes(all_recipes, force_save=True):
                    st.success("✅ Rezept wurde erfolgreich gespeichert!")
                    # clear preview
                    st.session_state["preview_recipe"] = None
                    recipes = load_recipes()
                else:
                    st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
            except Exception as e:
                st.error(f"Speichern fehlgeschlagen: {e}")
    
    with col_reset:
        if st.button("↩️ Formular zurücksetzen"):
            # Lösche alle Formular-bezogenen session_state Werte
            keys_to_clear = [
                "Titel des Rezepts*", "Untertitel", "Kategorie",
                "Vorbereitungszeit (z. B. 10 Min)", "Kochzeit (z. B. 30 Min)",
                "portion_value", "Schwierigkeitsgrad", "Tipps oder Varianten",
                "kcal", "protein", "carbs", "fat", "fiber",
                "preview_recipe", "pending_nutrition_values"
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            st.success("✅ Formular wurde zurückgesetzt!")
            safe_rerun()

# ========== TEIL 2 ==========

# Sicherstellen, dass session_state keys existieren
if "preview_recipe" not in st.session_state:
    st.session_state["preview_recipe"] = None
if "edit_index" not in st.session_state:
    st.session_state["edit_index"] = None

# NOTE: Saving now happens via the dedicated Save buttons inside the create/edit forms

# === Modus: Rezept bearbeiten ===
if mode == "Rezept bearbeiten":
    st.header("✏️ Rezept bearbeiten")
    recipes = load_recipes()
    
    # Nutze gefilterte Rezepte wenn vorhanden
    display_recipes = st.session_state.get("filtered_recipes", recipes)
    
    if not display_recipes:
        if len(recipes) > 0:
            st.info("🔍 Keine Rezepte gefunden. Ändere deine Suchkriterien in der Sidebar.")
        else:
            st.info("Keine Rezepte vorhanden. Lege zuerst ein neues Rezept an oder importiere eine recipes.json.")
    else:
        # Zeige nur gefilterte Rezepte mit originalem Index
        titles = []
        recipe_map = {}  # Mapping von Titel zu Rezept
        for r in display_recipes:
            orig_idx = recipes.index(r) if r in recipes else -1
            title = f"{orig_idx+1}. {r.get('title','(kein Titel)')}"
            titles.append(title)
            recipe_map[title] = r
        
        # Bestimme Default-Auswahl (falls edit_index gesetzt)
        default_index = 0  # "---"
        
        if "edit_index" in st.session_state and st.session_state["edit_index"] is not None:
            try:
                if 0 <= st.session_state["edit_index"] < len(recipes):
                    # Finde den Titel des aktuell bearbeiteten Rezepts
                    current_recipe = recipes[st.session_state["edit_index"]]
                    
                    # Finde den Index in display_recipes
                    for i, r in enumerate(display_recipes):
                        if r == current_recipe:
                            default_index = i + 1  # +1 wegen "---" am Anfang
                            break
            except:
                # Falls Fehler, reset
                st.session_state["edit_index"] = None
        
        # Selectbox OHNE key, damit default_index funktioniert
        sel = st.selectbox(
            "Wähle ein Rezept zum Bearbeiten", 
            options=["---"] + titles, 
            index=default_index
        )
        
        if sel != "---":
            # Finde das Original-Rezept in der vollständigen Liste
            selected_recipe = recipe_map[sel]
            idx = recipes.index(selected_recipe)
            st.session_state["edit_index"] = idx
            r = recipes[idx]
            
            # Aktionsbuttons: Duplizieren & Löschen
            col_dup, col_del = st.columns([1, 1])
            with col_dup:
                if st.button("🔄 Rezept duplizieren", key="duplicate_recipe"):
                    # Erstelle Kopie
                    new_recipe = r.copy()
                    new_recipe["title"] = r.get("title", "Rezept") + " (Kopie)"
                    
                    # Entferne IDs/Metadaten für neue Kopie
                    new_recipe.pop("created_at", None)
                    new_recipe.pop("updated_at", None)
                    new_recipe.pop("version", None)
                    
                    # Füge zur Liste hinzu
                    recipes.append(new_recipe)
                    if save_recipes(recipes, force_save=True):
                        st.success(f"✅ '{new_recipe['title']}' wurde erstellt!")
                        time.sleep(1)
                        safe_rerun()
                    else:
                        st.error("❌ Fehler beim Duplizieren")
            
            with col_del:
                if st.button("🗑️ Rezept löschen", key="delete_recipe_edit"):
                    # Sicherheitsabfrage via session_state
                    if st.session_state.get("confirm_delete") == idx:
                        try:
                            recipes.pop(idx)
                            if save_recipes(recipes, force_save=True):
                                st.success("✅ Rezept gelöscht!")
                                st.session_state.pop("confirm_delete", None)
                                st.session_state.pop("edit_index", None)
                                time.sleep(1)
                                safe_rerun()
                            else:
                                st.error("❌ Fehler beim Löschen")
                        except IndexError:
                            st.error("❌ Fehler: Rezept-Index ungültig. Bitte Seite neu laden.")
                            st.session_state.pop("confirm_delete", None)
                    else:
                        st.session_state["confirm_delete"] = idx
                        st.warning("⚠️ Nochmal klicken zum Bestätigen!")

            # AI helper for editing - ERWEITERT
            with st.expander("🤖 KI-Assistent (Gemini)", expanded=False):
                st.markdown("**Schnelle KI-Aktionen:**")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("✨ SEO verbessern", key="ai_seo", help="Optimiert Titel, Untertitel und SEO-Text"):
                        with st.spinner("🤖 KI optimiert SEO..."):
                            prompt = f"""Du bist SEO-Experte für vegane Rezept-Websites.
                            
Aktuelles Rezept:
Titel: {r.get('title', '')}
Untertitel: {r.get('subtitle', '')}
Kategorie: {r.get('category', '')}
Zutaten: {', '.join([item.get('name', '') for group in r.get('ingredients', []) for item in group.get('items', [])])}

Aufgabe:
1. Verbessere den Titel (max 60 Zeichen, SEO-optimiert, appetitlich)
2. Verbessere den Untertitel (max 120 Zeichen, verkaufsfördernd)
3. Generiere SEO-Meta-Description (max 155 Zeichen, mit Keywords)

Format GENAU so:
TITEL: [neuer Titel]
UNTERTITEL: [neuer Untertitel]
META: [Meta-Description]"""
                            
                            result = call_gemini(prompt)
                            if result:
                                # Parse Result
                                lines = result.strip().split('\n')
                                for line in lines:
                                    if line.startswith('TITEL:'):
                                        st.session_state['ai_title'] = line.replace('TITEL:', '').strip()
                                    elif line.startswith('UNTERTITEL:'):
                                        st.session_state['ai_subtitle'] = line.replace('UNTERTITEL:', '').strip()
                                    elif line.startswith('META:'):
                                        st.session_state['ai_meta'] = line.replace('META:', '').strip()
                                
                                st.success("✅ SEO-Vorschläge generiert!")
                                st.info("📝 Vorschläge weiter unten in den Feldern sichtbar")
                                safe_rerun()
                
                with col2:
                    if st.button("🏷️ Tags vorschlagen", key="ai_tags", help="Analysiert Rezept und schlägt Tags vor"):
                        with st.spinner("🤖 KI analysiert Rezept..."):
                            prompt = f"""Analysiere dieses vegane Rezept und schlage passende Tags vor.

Rezept: {r.get('title', '')}
Zutaten: {', '.join([item.get('name', '') for group in r.get('ingredients', []) for item in group.get('items', [])])}
Schwierigkeit: {r.get('difficulty', '')}
Zeit: {r.get('preparationTime', '')} + {r.get('cookTime', '')}

Schlage 5-10 passende Tags vor aus diesen Kategorien:
- Zeitaufwand: schnell, mittel, zeitintensiv
- Ernährung: proteinreich, kalorienarm, glutenfrei, sojafrei, nussfrei
- Anlass: Meal-Prep, Party, Festtag, Alltag
- Stil: comfort food, healthy, herzhaft, süß
- Jahreszeit: Sommer, Winter, Herbst, Frühling

Format: Kommagetrennte Liste ohne Anführungszeichen."""
                            
                            result = call_gemini(prompt)
                            if result:
                                st.session_state['ai_tags'] = result.strip()
                                st.success("✅ Tags generiert!")
                                st.code(result.strip())
                
                with col3:
                    if st.button("🔢 Nährwerte schätzen", key="ai_nutrition", help="Berechnet Nährwerte aus Zutaten"):
                        with st.spinner("🤖 KI berechnet Nährwerte..."):
                            ingredients_text = '\n'.join([
                                f"{item.get('amount', '')} {item.get('unit', '')} {item.get('name', '')}"
                                for group in r.get('ingredients', [])
                                for item in group.get('items', [])
                            ])
                            
                            prompt = f"""Schätze die Nährwerte pro Portion für dieses vegane Rezept.

Portionen: {r.get('portion', 1)}
Zutaten:
{ingredients_text}

Berechne die Nährwerte PRO PORTION und antworte NUR mit Zahlen im Format:
KCAL: [Zahl]
PROTEIN: [Zahl]
CARBS: [Zahl]
FAT: [Zahl]
FIBER: [Zahl]"""
                            
                            result = call_gemini(prompt)
                            if result:
                                # Parse Result
                                for line in result.strip().split('\n'):
                                    if 'KCAL:' in line:
                                        st.session_state['ai_kcal'] = int(''.join(filter(str.isdigit, line)))
                                    elif 'PROTEIN:' in line:
                                        st.session_state['ai_protein'] = int(''.join(filter(str.isdigit, line)))
                                    elif 'CARBS:' in line:
                                        st.session_state['ai_carbs'] = int(''.join(filter(str.isdigit, line)))
                                    elif 'FAT:' in line:
                                        st.session_state['ai_fat'] = int(''.join(filter(str.isdigit, line)))
                                    elif 'FIBER:' in line:
                                        st.session_state['ai_fiber'] = int(''.join(filter(str.isdigit, line)))
                                
                                st.success("✅ Nährwerte geschätzt!")
                                st.info("📝 Werte weiter unten in den Feldern übernehmen")
                                safe_rerun()
                
                with col4:
                    if st.button("🔄 Variante erstellen", key="ai_variation", help="Generiert eine Rezept-Variante"):
                        st.session_state["show_variation_options"] = True
                        safe_rerun()
                
                # Varianten-Generator (zeigt sich nach Button-Klick)
                if st.session_state.get("show_variation_options"):
                    st.markdown("---")
                    st.markdown("**🔄 Rezept-Variante generieren:**")
                    
                    variation_type = st.selectbox(
                        "Art der Variante:",
                        ["Glutenfrei", "High-Protein", "Low-Carb", "Budget-Version", "Schnellversion (< 30 Min)", 
                         "Gourmet-Version", "Meal-Prep optimiert", "Kinder-freundlich", "Eigene..."],
                        key="variation_type"
                    )
                    
                    custom_variation = ""
                    if variation_type == "Eigene...":
                        custom_variation = st.text_input("Beschreibe die gewünschte Variante:", key="custom_variation")
                    
                    if st.button("🚀 Variante jetzt generieren", key="generate_variation"):
                        variation_desc = custom_variation if variation_type == "Eigene..." else variation_type
                        
                        with st.spinner(f"🤖 Generiere {variation_desc}-Variante..."):
                            ingredients_text = '\n'.join([
                                f"- {item.get('amount', '')} {item.get('unit', '')} {item.get('name', '')}"
                                for group in r.get('ingredients', [])
                                for item in group.get('items', [])
                            ])
                            
                            steps_text = '\n'.join([
                                f"{i+1}. {step.get('substeps', [''])[0]}"
                                for i, step in enumerate(r.get('steps', []))
                            ])
                            
                            prompt = f"""Erstelle eine {variation_desc}-Variante von diesem veganen Rezept.

ORIGINAL-REZEPT:
Titel: {r.get('title', '')}
Zutaten:
{ingredients_text}

Zubereitung:
{steps_text}

AUFGABE:
Erstelle eine {variation_desc}-Version dieses Rezepts. Passe Zutaten UND Zubereitung an!

FORMAT (GENAU einhalten):
TITEL: [Neuer Titel inkl. '{variation_desc}']
ZUTATEN:
- [Menge] [Einheit] [Name]
- [weitere Zutaten...]

ZUBEREITUNG:
1. [Schritt 1]
2. [Schritt 2]
...

ÄNDERUNGEN:
- [Was wurde geändert und warum]"""
                            
                            result = call_gemini(prompt)
                            if result:
                                st.session_state['ai_variation_result'] = result
                                st.success(f"✅ {variation_desc}-Variante generiert!")
                                safe_rerun()
                    
                    # Zeige generierte Variante
                    if st.session_state.get('ai_variation_result'):
                        st.markdown("---")
                        st.markdown("**📋 Generierte Variante:**")
                        st.code(st.session_state['ai_variation_result'], language="text")
                        
                        col_save, col_cancel = st.columns([1, 1])
                        with col_save:
                            if st.button("💾 Als neues Rezept speichern", key="save_variation"):
                                # Parse die generierte Variante
                                variation_text = st.session_state['ai_variation_result']
                                parsed = extract_recipe_info(variation_text)
                                
                                if parsed:
                                    # Erstelle neues Rezept basierend auf Original
                                    new_recipe = r.copy()
                                    new_recipe["title"] = parsed.get("title", r.get("title", "") + " (Variante)")
                                    
                                    # Aktualisiere mit AI-Vorschlägen
                                    if parsed.get("ingredients"):
                                        new_recipe["ingredients"] = parsed["ingredients"]
                                    if parsed.get("steps"):
                                        new_recipe["steps"] = parsed["steps"]
                                    
                                    # Entferne Metadaten für neues Rezept
                                    new_recipe.pop("created_at", None)
                                    new_recipe.pop("updated_at", None)
                                    new_recipe.pop("version", None)
                                    
                                    # Füge zur Liste hinzu
                                    recipes.append(new_recipe)
                                    if save_recipes(recipes, force_save=True):
                                        st.success(f"✅ Variante '{new_recipe['title']}' wurde erstellt!")
                                        st.session_state.pop('ai_variation_result', None)
                                        st.session_state.pop('show_variation_options', None)
                                        time.sleep(1)
                                        safe_rerun()
                                    else:
                                        st.error("❌ Fehler beim Speichern")
                                else:
                                    st.error("❌ Konnte Variante nicht parsen. Bitte manuell erstellen.")
                        
                        with col_cancel:
                            if st.button("❌ Verwerfen", key="discard_variation"):
                                st.session_state.pop('ai_variation_result', None)
                                st.session_state.pop('show_variation_options', None)
                                safe_rerun()
                
                st.markdown("---")
                st.markdown("**Freie KI-Anweisung:**")
                ai_instruction = st.text_area("Anweisung an die AI (z. B. 'Ersetze 200g Mehl durch 200g Dinkelmehl')", key="ai_custom")
                if st.button("AI-Anweisung anwenden", key="ai_apply"):
                    try:
                        # Use the instruction text as input for recipe extraction
                        parsed = extract_recipe_info(ai_instruction)
                        if parsed:
                            # Merge with existing recipe data
                            merged = r.copy()
                            for key, value in parsed.items():
                                if value:  # Only update non-empty values
                                    merged[key] = value
                            # do NOT save immediately — populate edit form so user can review and click 'Änderungen speichern'
                            apply_parsed_to_session(parsed, for_edit=True)
                            st.success("AI-Änderung übernommen. Bitte überprüfe die Felder und klicke 'Änderungen speichern', um zu speichern.")
                        else:
                            st.error("Konnte keine Änderungen aus der Anweisung extrahieren. Anweisung war:")
                            st.code(ai_instruction)
                    except Exception as e:
                        st.error(f"AI-Anwendung fehlgeschlagen: {e}")

            # Vorbefüllte Felder - MIT KI-VORSCHLÄGEN
            # Nutze KI-Vorschläge falls vorhanden
            title_value = st.session_state.get('ai_title', r.get("title", ""))
            subtitle_value = st.session_state.get('ai_subtitle', r.get("subtitle", ""))
            
            e_title = st.text_input("Titel*", value=title_value, key="edit_title")
            if st.session_state.get('ai_title'):
                st.success(f"💡 KI-Vorschlag übernommen!")
                if st.button("❌ KI-Vorschlag verwerfen", key="clear_ai_title"):
                    st.session_state.pop('ai_title', None)
                    safe_rerun()
            
            e_subtitle = st.text_input("Untertitel", value=subtitle_value, key="edit_subtitle")
            if st.session_state.get('ai_subtitle'):
                st.success(f"💡 KI-Vorschlag übernommen!")
                if st.button("❌ KI-Vorschlag verwerfen", key="clear_ai_subtitle"):
                    st.session_state.pop('ai_subtitle', None)
                    safe_rerun()
            
            # Kategorie mit dynamischer Liste
            categories_list = load_categories()
            current_cat = r.get("category", "")
            try:
                cat_index = categories_list.index(current_cat) if current_cat in categories_list else 0
            except:
                cat_index = 0
            e_category = st.selectbox("Kategorie", categories_list, index=cat_index, key="e_cat")
            
            e_prep = st.text_input("Vorbereitungszeit", value=r.get("preparationTime",""))
            e_cook = st.text_input("Kochzeit", value=r.get("cookTime",""))
            e_portion = st.number_input("Portionen", min_value=1, value=int(r.get("portion",1)))
            try:
                e_diff = st.selectbox("Schwierigkeit", ["Einfach","Mittel","Schwer"], index=["Einfach","Mittel","Schwer"].index(r.get("difficulty","Einfach")))
            except:
                e_diff = r.get("difficulty","Einfach")

            # === Veröffentlichungs-Status ===
            st.subheader("🌐 Veröffentlichung")
            col1, col2 = st.columns(2)
            
            with col1:
                e_published = st.checkbox(
                    "✅ Veröffentlicht",
                    value=r.get("published", True),
                    help="Nur veröffentlichte Rezepte erscheinen auf der Website",
                    key="e_is_published"
                )
                if e_published:
                    st.success("Rezept ist öffentlich sichtbar")
                else:
                    st.warning("Rezept ist offline (nur im Admin sichtbar)")
            
            with col2:
                # Zeige Featured-Status als Info
                featured_status = []
                if r.get("featuredWeek", False):
                    featured_status.append("📅 Rezept der Woche")
                if r.get("featuredMonth", False):
                    featured_status.append("🗓️ Monatsrezept")
                if r.get("featuredSeason", False):
                    featured_status.append("🍂 Jahreszeitrezept")
                
                if featured_status:
                    st.info("🏠 " + " | ".join(featured_status))
                    st.caption("Änderung unter '🏠 Startseiten-Rezepte'")
            
            st.markdown("---")

            # Image edit
            st.markdown("**Bild (optional)**")
            cols_img = st.columns([1,1])
            with cols_img[0]:
                if r.get("image"):
                    try:
                        st.markdown("**Aktuelles Bild:**")
                        img_src = get_image_display(r, width=200)
                        if img_src:
                            st.image(img_src, width=200)
                    except Exception:
                        st.error("Fehler beim Laden des aktuellen Bildes")
                else:
                    st.info("Kein Bild vorhanden")
                
            with cols_img[1]:
                new_img = st.file_uploader("Neues Bild hochladen", type=["png","jpg","jpeg"], key="edit_img", 
                    help="Das neue Bild ersetzt nach dem Speichern das aktuelle Bild")
                if new_img:
                    try:
                        new_img_b64 = base64.b64encode(new_img.read()).decode("utf-8")
                        st.markdown("**Vorschau des neuen Bildes:**")
                        st.image(new_img, width=200)
                    except Exception:
                        st.error("Fehler beim Laden des neuen Bildes")
                        new_img_b64 = ""
                else:
                    new_img_b64 = r.get("image","")

            # Ingredients edit
            st.subheader("Zutaten bearbeiten")
            edit_ingredient_groups = []
            for gi, group in enumerate(r.get("ingredients",[])):
                st.markdown(f"**Obergruppe {gi+1}**")
                g_name = st.text_input(f"Obergruppenname {gi+1}", value=group.get("group",""), key=f"gname_{gi}")
                
                items = []
                for ji, it in enumerate(group.get("items",[])):
                    cols = st.columns([0.5, 0.5, 2, 2, 6, 1])
                    
                    # Verschiebe-Buttons für Zutaten
                    with cols[0]:
                        if ji > 0:
                            if st.button("↑", key=f"up_edit_ing_{gi}_{ji}", help="Nach oben"):
                                # Tausche in der Liste
                                temp = r["ingredients"][gi]["items"][ji]
                                r["ingredients"][gi]["items"][ji] = r["ingredients"][gi]["items"][ji-1]
                                r["ingredients"][gi]["items"][ji-1] = temp
                                if save_recipes(recipes, force_save=True):
                                    # Wichtig: edit_index explizit setzen BEVOR rerun
                                    st.session_state["edit_index"] = idx
                                    safe_rerun()
                    
                    with cols[1]:
                        if ji < len(group.get("items",[])) - 1:
                            if st.button("↓", key=f"down_edit_ing_{gi}_{ji}", help="Nach unten"):
                                # Tausche in der Liste
                                temp = r["ingredients"][gi]["items"][ji]
                                r["ingredients"][gi]["items"][ji] = r["ingredients"][gi]["items"][ji+1]
                                r["ingredients"][gi]["items"][ji+1] = temp
                                if save_recipes(recipes, force_save=True):
                                    st.session_state["edit_index"] = idx
                                    safe_rerun()
                    
                    with cols[2]:
                        a = st.text_input(f"Menge", value=str(it.get("amount","")), key=f"e_amount_{gi}_{ji}", label_visibility="collapsed", placeholder="Menge")
                    with cols[3]:
                        u = st.text_input(f"Einheit", value=it.get("unit",""), key=f"e_unit_{gi}_{ji}", label_visibility="collapsed", placeholder="Einheit")
                    with cols[4]:
                        n = st.text_input(f"Name", value=it.get("name",""), key=f"e_name_{gi}_{ji}", label_visibility="collapsed", placeholder="Zutat")
                    with cols[5]:
                        if st.button("✕", key=f"del_ing_{gi}_{ji}"):
                            # Entferne Zutat aus dem Rezept und speichere sofort
                            try:
                                r["ingredients"][gi]["items"].pop(ji)
                                if save_recipes(recipes, force_save=True):
                                    safe_rerun()
                                else:
                                    st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                            except Exception as e:
                                st.error(f"Fehler beim Löschen der Zutat: {e}")
                    
                    # NICHT direkt übernehmen - nur im Formular anzeigen
                    # Die Werte werden erst beim "💾 Änderungen speichern" gespeichert
                    items.append({"amount": a, "unit": u, "name": n})
                
                # Möglichkeit, neue Zeile in der Gruppe hinzuzufügen
                if st.button(f"Zutat zu Gruppe {gi+1} hinzufügen", key=f"add_ing_g{gi}"):
                    try:
                        r["ingredients"][gi]["items"].append({"amount":"", "unit":"", "name":""})
                        if save_recipes(recipes, force_save=True):
                            safe_rerun()
                        else:
                            st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen der Zutat: {e}")
                
                # Sammle die bearbeiteten Zutaten (werden erst beim "Speichern" Button übernommen)
                edit_ingredient_groups.append({"group": g_name, "items": items})

            # Steps edit
            st.subheader("Zubereitungsschritte bearbeiten")
            
            edit_steps = []
            for si, step in enumerate(r.get("steps",[])):
                st.markdown(f"**Schritt {si+1}**")
                
                # Verschiebe-Buttons für Hauptschritte
                col_up, col_down, col_time = st.columns([0.5, 0.5, 9])
                
                with col_up:
                    if si > 0:
                        if st.button("↑", key=f"up_edit_step_{si}", help="Schritt nach oben"):
                            temp = r["steps"][si]
                            r["steps"][si] = r["steps"][si-1]
                            r["steps"][si-1] = temp
                            if save_recipes(recipes, force_save=True):
                                st.session_state["edit_index"] = idx
                                safe_rerun()
                
                with col_down:
                    if si < len(r.get("steps",[])) - 1:
                        if st.button("↓", key=f"down_edit_step_{si}", help="Schritt nach unten"):
                            temp = r["steps"][si]
                            r["steps"][si] = r["steps"][si+1]
                            r["steps"][si+1] = temp
                            if save_recipes(recipes, force_save=True):
                                st.session_state["edit_index"] = idx
                                safe_rerun()
                
                with col_time:
                    s_time = st.text_input(f"Zeit", value=step.get("time",""), key=f"e_time_{si}", label_visibility="collapsed", placeholder="Zeit")
                
                # Lösch-Button für Schritt
                if st.button("✕ Schritt löschen", key=f"del_edit_step_{si}"):
                    try:
                        r["steps"].pop(si)
                        if save_recipes(recipes, force_save=True):
                            safe_rerun()
                        else:
                            st.error("❌ Speichern fehlgeschlagen")
                    except Exception as e:
                        st.error(f"Fehler: {e}")
                
                # needed
                needed_list = []
                for ni, need in enumerate(step.get("needed",[])):
                    c_up, c_down, c1, c2, c3, c4 = st.columns([0.5, 0.5, 2, 2, 5, 1])
                    
                    # Verschiebe-Buttons für benötigte Zutaten
                    with c_up:
                        if ni > 0:
                            if st.button("↑", key=f"up_edit_need_{si}_{ni}", help="Nach oben"):
                                temp = r["steps"][si]["needed"][ni]
                                r["steps"][si]["needed"][ni] = r["steps"][si]["needed"][ni-1]
                                r["steps"][si]["needed"][ni-1] = temp
                                if save_recipes(recipes, force_save=True):
                                    st.session_state["edit_index"] = idx
                                    safe_rerun()
                    
                    with c_down:
                        if ni < len(step.get("needed",[])) - 1:
                            if st.button("↓", key=f"down_edit_need_{si}_{ni}", help="Nach unten"):
                                temp = r["steps"][si]["needed"][ni]
                                r["steps"][si]["needed"][ni] = r["steps"][si]["needed"][ni+1]
                                r["steps"][si]["needed"][ni+1] = temp
                                if save_recipes(recipes, force_save=True):
                                    st.session_state["edit_index"] = idx
                                    safe_rerun()
                    
                    with c1:
                        na = st.text_input(f"Menge", value=str(need.get("amount","")), key=f"e_n_amount_{si}_{ni}", label_visibility="collapsed", placeholder="Menge")
                    with c2:
                        nu = st.text_input(f"Einheit", value=need.get("unit",""), key=f"e_n_unit_{si}_{ni}", label_visibility="collapsed", placeholder="Einheit")
                    with c3:
                        nn = st.text_input(f"Zutat", value=need.get("name",""), key=f"e_n_name_{si}_{ni}", label_visibility="collapsed", placeholder="Zutat")
                    with c4:
                        if st.button("✕", key=f"del_need_{si}_{ni}"):
                            try:
                                r["steps"][si]["needed"].pop(ni)
                                if save_recipes(recipes, force_save=True):
                                    safe_rerun()
                                else:
                                    st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                            except Exception as e:
                                st.error(f"Fehler beim Löschen der benötigten Zutat: {e}")
                    # Übernehme Änderungen
                    if nn is not None and nn != "":
                        needed_list.append({"amount": na, "unit": nu, "name": nn})
                
                # Button zum Hinzufügen neuer benötigter Zutaten
                if st.button(f"+ Benötigte Zutat zu Schritt {si+1}", key=f"add_need_{si}"):
                    try:
                        r["steps"][si].setdefault("needed", []).append({"amount": "", "unit": "", "name": ""})
                        if save_recipes(recipes, force_save=True):
                            safe_rerun()
                        else:
                            st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen der benötigten Zutat: {e}")
                
                # substeps
                substeps_current = step.get("substeps", [])
                
                # Hole die aktuelle Anzahl der Zwischenschritte für diesen Schritt
                num_substeps = st.session_state.get(f"num_substeps_{si}", len(step.get("substeps", [])))
                
                # Zwischenschritte anzeigen und verwalten
                substeps_to_keep = []
                for subi in range(num_substeps):
                    cols = st.columns([0.5, 0.5, 8, 1])
                    
                    # Verschiebe-Buttons für Zwischenschritte
                    with cols[0]:
                        if subi > 0:
                            if st.button("↑", key=f"up_edit_sub_{si}_{subi}", help="Nach oben"):
                                temp = r["steps"][si]["substeps"][subi]
                                r["steps"][si]["substeps"][subi] = r["steps"][si]["substeps"][subi-1]
                                r["steps"][si]["substeps"][subi-1] = temp
                                if save_recipes(recipes, force_save=True):
                                    st.session_state["edit_index"] = idx
                                    safe_rerun()
                    
                    with cols[1]:
                        if subi < len(substeps_current) - 1:
                            if st.button("↓", key=f"down_edit_sub_{si}_{subi}", help="Nach unten"):
                                temp = r["steps"][si]["substeps"][subi]
                                r["steps"][si]["substeps"][subi] = r["steps"][si]["substeps"][subi+1]
                                r["steps"][si]["substeps"][subi+1] = temp
                                if save_recipes(recipes, force_save=True):
                                    st.session_state["edit_index"] = idx
                                    safe_rerun()
                    
                    with cols[2]:
                        current_value = step.get("substeps", [])[subi] if subi < len(step.get("substeps", [])) else ""
                        sval = st.text_area(
                            f"Zwischenschritt {si+1}.{subi+1}", 
                            value=current_value,
                            key=f"e_sub_{si}_{subi}",
                            label_visibility="collapsed",
                            placeholder="Zwischenschritt-Beschreibung"
                        )
                    with cols[3]:
                        if st.button("✕", key=f"del_sub_{si}_{subi}"):
                            try:
                                if 0 <= subi < len(r["steps"][si].get("substeps", [])):
                                    r["steps"][si]["substeps"].pop(subi)
                                    if save_recipes(recipes, force_save=True):
                                        safe_rerun()
                                    else:
                                        st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                            except Exception as e:
                                st.error(f"Fehler beim Löschen des Zwischenschritts: {e}")
                    
                    # Übernehme Änderungen
                    if sval and sval.strip():
                        substeps_to_keep.append(sval)
                
                # Buttons für Zwischenschritt-Management
                col1, col2 = st.columns([1,1])
                with col1:
                    if st.button(f"+ Zwischenschritt", key=f"add_sub_{si}"):
                        try:
                            r["steps"][si].setdefault("substeps", []).append("")
                            st.session_state[f"num_substeps_{si}"] = len(r["steps"][si]["substeps"])  # sync counter
                            if save_recipes(recipes, force_save=True):
                                safe_rerun()
                            else:
                                st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                        except Exception as e:
                            st.error(f"Fehler beim Hinzufügen des Zwischenschritts: {e}")
                with col2:
                    if num_substeps > 1 and st.button("- Letzten Zwischenschritt entfernen", key=f"remove_last_sub_{si}"):
                        try:
                            if r["steps"][si].get("substeps"):
                                r["steps"][si]["substeps"].pop()
                                st.session_state[f"num_substeps_{si}"] = len(r["steps"][si]["substeps"])  # sync
                                if save_recipes(recipes, force_save=True):
                                    safe_rerun()
                                else:
                                    st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                        except Exception as e:
                            st.error(f"Fehler beim Entfernen des letzten Zwischenschritts: {e}")
                
                # Speichere den Schritt - NICHT direkt in r schreiben
                step_data = {"time": s_time, "needed": needed_list, "substeps": substeps_to_keep}
                edit_steps.append(step_data)
                
                # Button zum Löschen des gesamten Schritts
                if si > 0:  # Erlaube Löschen nur wenn es nicht der erste Schritt ist
                    if st.button(f"🗑️ Schritt {si+1} komplett löschen", key=f"del_step_{si}"):
                        try:
                            r["steps"].pop(si)
                            if save_recipes(recipes, force_save=True):
                                st.session_state["edit_index"] = idx
                                safe_rerun()
                            else:
                                st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                        except Exception as e:
                            st.error(f"Fehler beim Löschen des Schritts: {e}")
                    
                st.markdown("---")  # Visuelle Trennung zwischen den Schritten

            # Buttons für Schritt-Management
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Neuen Hauptschritt hinzufügen", key="add_main_step"):
                    try:
                        r.setdefault("steps", []).append({
                            "time": "10 Min",
                            "needed": [],
                            "substeps": [""]
                        })
                        if save_recipes(recipes, force_save=True):
                            safe_rerun()
                        else:
                            st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Schritts: {e}")
            
            # tips & nutrition
            st.markdown("---")
            e_tips = st.text_area("Tipps", value=r.get("tips",""))
            
            st.subheader("Nährwerte")
            
            # Zeige KI-Button wenn Nährwerte fehlen
            if st.session_state.get('ai_kcal'):
                st.info("💡 KI hat Nährwerte geschätzt - Übernimm sie mit den Buttons unten!")
            
            nc1, nc2, nc3, nc4, nc5 = st.columns(5)
            with nc1:
                kcal_value = st.session_state.get('ai_kcal', int(r.get("nutrition",{}).get("kcal",0)))
                e_kcal = st.number_input("kcal", min_value=0, value=kcal_value, key="e_kcal")
                if st.session_state.get('ai_kcal') and st.button("✅", key="accept_kcal"):
                    st.session_state.pop('ai_kcal', None)
                    safe_rerun()
            with nc2:
                protein_value = st.session_state.get('ai_protein', int(r.get("nutrition",{}).get("protein",0)))
                e_protein = st.number_input("Protein (g)", min_value=0, value=protein_value, key="e_protein")
                if st.session_state.get('ai_protein') and st.button("✅", key="accept_protein"):
                    st.session_state.pop('ai_protein', None)
                    safe_rerun()
            with nc3:
                carbs_value = st.session_state.get('ai_carbs', int(r.get("nutrition",{}).get("carbs",0)))
                e_carbs = st.number_input("KH (g)", min_value=0, value=carbs_value, key="e_carbs")
                if st.session_state.get('ai_carbs') and st.button("✅", key="accept_carbs"):
                    st.session_state.pop('ai_carbs', None)
                    safe_rerun()
            with nc4:
                fat_value = st.session_state.get('ai_fat', int(r.get("nutrition",{}).get("fat",0)))
                e_fat = st.number_input("Fett (g)", min_value=0, value=fat_value, key="e_fat")
                if st.session_state.get('ai_fat') and st.button("✅", key="accept_fat"):
                    st.session_state.pop('ai_fat', None)
                    safe_rerun()
            with nc5:
                fiber_value = st.session_state.get('ai_fiber', int(r.get("nutrition",{}).get("fiber",0)))
                e_fiber = st.number_input("Ballast. (g)", min_value=0, value=fiber_value, key="e_fiber")
                if st.session_state.get('ai_fiber') and st.button("✅", key="accept_fiber"):
                    st.session_state.pop('ai_fiber', None)
                    safe_rerun()

            if st.button("🔬 Nährwerte berechnen (Swiss Food DB)", key="calc_nutr"):
                try:
                    # Berechne Nährwerte
                    with st.spinner("Berechne Nährwerte..."):
                        nutr = compute_nutrition_from_swiss(edit_ingredient_groups, e_portion)
                        
                    # Zeige Vorschau der berechneten Werte
                    st.info("Berechnete Nährwerte (pro Portion):")
                    cols = st.columns(5)
                    with cols[0]: st.metric("Kalorien", f"{nutr.get('kcal', 0)} kcal")
                    with cols[1]: st.metric("Protein", f"{nutr.get('protein', 0)}g")
                    with cols[2]: st.metric("Kohlenhydrate", f"{nutr.get('carbs', 0)}g")
                    with cols[3]: st.metric("Fett", f"{nutr.get('fat', 0)}g")
                    with cols[4]: st.metric("Ballaststoffe", f"{nutr.get('fiber', 0)}g")
                    
                    # Speichere berechnete Werte temporär
                    st.session_state["calculated_nutrition"] = nutr
                        
                except Exception as e:
                    st.error(f"Nährwertberechnung fehlgeschlagen: {e}")
            
            # Button zum Übernehmen der berechneten Werte (außerhalb des oberen if-Blocks)
            if st.session_state.get("calculated_nutrition"):
                if st.button("✅ Berechnete Werte übernehmen", key="apply_nutr"):
                    nutr = st.session_state["calculated_nutrition"]
                    # Schreibe die Werte DIREKT ins Rezept-Objekt (nicht in session_state Keys!)
                    r["nutrition"] = {
                        "kcal": int(nutr.get('kcal', 0)),
                        "protein": int(nutr.get('protein', 0)),
                        "carbs": int(nutr.get('carbs', 0)),
                        "fat": int(nutr.get('fat', 0)),
                        "fiber": int(nutr.get('fiber', 0))
                    }
                    # Speichere und lade neu
                    if save_recipes(recipes, force_save=True):
                        st.session_state["calculated_nutrition"] = None  # Clear
                        st.success("✅ Nährwerte übernommen!")
                        safe_rerun()
                    else:
                        st.error("❌ Nährwerte konnten nicht gespeichert werden")

            # Save, Reset or delete buttons
            colsave, colreset, coldel = st.columns(3)
            with colsave:
                if st.button("💾 Änderungen speichern"):
                    # Übernehme Kopf-Felder
                    r["title"] = e_title
                    r["subtitle"] = e_subtitle
                    r["category"] = e_category
                    r["preparationTime"] = e_prep
                    r["cookTime"] = e_cook
                    r["portion"] = e_portion
                    r["difficulty"] = e_diff
                    r["published"] = e_published
                    # recipeOfWeek wird nicht hier gesetzt (separater Menüpunkt)
                    r["image"] = new_img_b64
                    r["tips"] = e_tips
                    r["nutrition"] = {"kcal": e_kcal, "protein": e_protein, "carbs": e_carbs, "fat": e_fat, "fiber": e_fiber}
                    
                    # WICHTIG: Übernehme bearbeitete Zutaten und Schritte
                    r["ingredients"] = edit_ingredient_groups
                    r["steps"] = edit_steps
                    
                    recipes[idx] = r
                    if save_recipes(recipes, force_save=True):
                        st.success("✅ Änderungen erfolgreich gespeichert!")
                    else:
                        st.error("❌ Speichern fehlgeschlagen - siehe Fehler oben")
            
            with colreset:
                if st.button("↩️ Änderungen verwerfen"):
                    # Lade Rezepte neu um Original-Daten wiederherzustellen
                    st.session_state["edit_index"] = idx  # Behalte Auswahl
                    st.success("✅ Alle Änderungen wurden verworfen! Formular wird neu geladen...")
                    safe_rerun()
            
            with coldel:
                # Delete current recipe (with confirmation)
                if st.button("🗑️ Rezept löschen", key=f"del_req_{idx}"):
                    st.session_state["confirm_delete"] = idx
                if st.session_state.get("confirm_delete") == idx:
                    st.warning("Klicke nochmals zum Bestätigen des Löschens.")
                    if st.button("Bestätige endgültiges Löschen", key=f"del_confirm_{idx}"):
                        recipes.pop(idx)
                        if save_recipes(recipes, force_save=True):
                            st.success("✅ Rezept wurde gelöscht!")
                            # clear state and reload
                            st.session_state["confirm_delete"] = None
                            st.session_state["edit_index"] = None
                            recipes = load_recipes()
                            safe_rerun()
                        else:
                            st.error("❌ Löschen fehlgeschlagen - siehe Fehler oben")
# === Modus: Rezept löschen (mit Bulk-Operationen) ===
if mode == "Rezept löschen":
    st.header("🗑️ Rezepte verwalten (Bulk-Operationen)")
    recipes = load_recipes()
    
    # Nutze gefilterte Rezepte wenn vorhanden
    display_recipes = st.session_state.get("filtered_recipes", recipes)
    
    if not display_recipes:
        st.info("Keine Rezepte vorhanden (oder keine passen zum Filter).")
    else:
        st.info(f"📋 {len(display_recipes)} Rezepte angezeigt")
        
        # === BULK-AUSWAHL ===
        st.markdown("### ☑️ Mehrfachauswahl")
        
        # "Alle auswählen" Checkbox
        select_all = st.checkbox("Alle auswählen/abwählen", key="select_all_bulk")
        
        # Speichere Auswahl in session_state
        if "bulk_selected" not in st.session_state:
            st.session_state["bulk_selected"] = set()
        
        if select_all:
            # Alle IDs hinzufügen
            st.session_state["bulk_selected"] = set(range(len(recipes)))
        
        # Zeige Rezepte mit Checkboxen
        selected_indices = []
        
        for display_idx, recipe in enumerate(display_recipes):
            # Finde Original-Index in der vollständigen Liste
            try:
                original_idx = recipes.index(recipe)
            except ValueError:
                # Falls Rezept nicht in Liste (sollte nicht passieren, aber sicher ist sicher)
                original_idx = display_idx
            
            col_check, col_title, col_cat, col_diff = st.columns([0.5, 4, 2, 1.5])
            
            with col_check:
                is_selected = st.checkbox(
                    "",
                    value=original_idx in st.session_state["bulk_selected"],
                    key=f"bulk_check_{original_idx}",
                    label_visibility="collapsed"
                )
                if is_selected:
                    st.session_state["bulk_selected"].add(original_idx)
                    selected_indices.append(original_idx)
                else:
                    st.session_state["bulk_selected"].discard(original_idx)
            
            with col_title:
                st.write(f"**{recipe.get('title', '(kein Titel)')}**")
            with col_cat:
                st.write(recipe.get('category', 'Keine'))
            with col_diff:
                st.write(recipe.get('difficulty', '-'))
        
        # === BULK-AKTIONEN ===
        st.markdown("---")
        st.markdown(f"### ⚡ Aktionen ({len(st.session_state['bulk_selected'])} ausgewählt)")
        
        if len(st.session_state["bulk_selected"]) > 0:
            col_del, col_cat, col_deselect = st.columns(3)
            
            with col_del:
                if st.button("🗑️ Ausgewählte löschen", type="primary"):
                    # Sicherheitsabfrage
                    if st.session_state.get("confirm_bulk_delete"):
                        # Lösche in umgekehrter Reihenfolge (höchste Index zuerst)
                        deleted_count = 0
                        errors = 0
                        for idx in sorted(st.session_state["bulk_selected"], reverse=True):
                            try:
                                if 0 <= idx < len(recipes):
                                    recipes.pop(idx)
                                    deleted_count += 1
                                else:
                                    errors += 1
                            except IndexError:
                                errors += 1
                        
                        if save_recipes(recipes, force_save=True):
                            if errors > 0:
                                st.warning(f"⚠️ {deleted_count} Rezepte gelöscht, {errors} Fehler (ungültige Indizes)")
                            else:
                                st.success(f"✅ {deleted_count} Rezepte gelöscht!")
                            st.session_state["bulk_selected"] = set()
                            st.session_state.pop("confirm_bulk_delete", None)
                            time.sleep(1)
                            safe_rerun()
                        else:
                            st.error("❌ Löschen fehlgeschlagen")
                    else:
                        st.session_state["confirm_bulk_delete"] = True
                        st.warning("⚠️ Nochmal klicken zum Bestätigen!")
            
            with col_cat:
                new_category = st.selectbox(
                    "Kategorie ändern zu:",
                    [""] + load_categories(),
                    key="bulk_new_category"
                )
                
                if new_category and st.button("✏️ Kategorie ändern"):
                    for idx in st.session_state["bulk_selected"]:
                        recipes[idx]["category"] = new_category
                    
                    if save_recipes(recipes, force_save=True):
                        st.success(f"✅ Kategorie für {len(st.session_state['bulk_selected'])} Rezepte geändert!")
                        time.sleep(1)
                        safe_rerun()
                    else:
                        st.error("❌ Änderung fehlgeschlagen")
            
            with col_deselect:
                if st.button("❌ Auswahl aufheben"):
                    st.session_state["bulk_selected"] = set()
                    st.session_state.pop("confirm_bulk_delete", None)
                    # Kein Rerun nötig - Checkbox-Zustand wird automatisch gecleart
        else:
            st.info("💡 Wähle mindestens ein Rezept aus, um Bulk-Aktionen zu nutzen.")


# === Modus: Alle Rezepte ansehen (Liste) ===
if mode == "Alle Rezepte ansehen":
    st.header("📚 Alle Rezepte")
    recipes = load_recipes()
    if not recipes:
        st.info("Noch keine Rezepte vorhanden.")
    else:
        for i, r in enumerate(recipes):
            # Defensive rendering: ensure recipe is a dict
            if not isinstance(r, dict):
                with st.expander(f"{i+1}. (Ungültiges Rezeptformat)"):
                    st.write(r)
                continue

            title = r.get('title') or '(kein Titel)'
            subtitle = r.get('subtitle','') or ''
            category = r.get('category','') or ''
            portion = r.get('portion','')
            difficulty = r.get('difficulty','') or ''

            header = f"{i+1}. {title}"
            with st.expander(header):
                cols = st.columns([1,4])
                with cols[0]:
                    img_src = get_image_display(r, width=140)
                    if img_src:
                        try:
                            st.image(img_src, width=140)
                        except Exception:
                            pass
                with cols[1]:
                    md = f"**{title}**"
                    if subtitle:
                        md += f"  \n{subtitle}"
                    st.markdown(md)
                    meta_parts = []
                    if category:
                        meta_parts.append(f"Kategorie: {category}")
                    if portion or portion == 0:
                        meta_parts.append(f"Portionen: {portion}")
                    if difficulty:
                        meta_parts.append(f"Schwierigkeit: {difficulty}")
                    if meta_parts:
                        st.write(" — ".join(meta_parts))

                    # Zutaten
                    st.write("**Zutaten:**")
                    ingredients = r.get("ingredients") or []
                    if isinstance(ingredients, list) and ingredients:
                        for g in ingredients:
                            if not isinstance(g, dict):
                                continue
                            gname = g.get('group','')
                            if gname:
                                st.write(f"- **{gname}**")
                            for it in g.get('items',[]) or []:
                                am = it.get('amount','')
                                un = it.get('unit','')
                                nm = it.get('name','')
                                if nm:
                                    st.write(f"  - {am} {un} {nm}")
                    else:
                        st.write("(keine Zutaten angegeben)")

                    # Schritte
                    st.write("**Zubereitung:**")
                    steps = r.get('steps') or []
                    if isinstance(steps, list) and steps:
                        for si, step in enumerate(steps):
                            if isinstance(step, dict):
                                t = step.get('time','')
                                st.write(f"{si+1}. ({t})")
                                for sub in step.get('substeps',[]) or []:
                                    if sub:
                                        st.write(f"   - {sub}")
                            else:
                                if step:
                                    st.write(f"{si+1}. {step}")
                    else:
                        st.write("(keine Schritte angegeben)")

                    # Tipps & Nährwerte
                    st.write("**Tipps:**")
                    st.write(r.get("tips","") or "(keine Tipps)")
                    st.write("**Nährwerte:**")
                    st.write(r.get("nutrition",{}) or "(keine Nährwerte)")

# === Modus: Startseiten-Rezepte ===
if mode == "🏠 Startseiten-Rezepte":
    st.header("🏠 Startseiten-Rezepte verwalten")
    
    st.markdown("""
    **Wähle bis zu 3 Rezepte für die Startseite:**
    - 📅 **Rezept der Woche** - Wöchentlich wechselnd
    - 🗓️ **Monatsrezept** - Jeden Monat ein Highlight
    - 🍂 **Jahreszeitrezept** - Passend zur Jahreszeit
    
    Jedes Rezept erscheint mit Bild, Titel, Untertitel und deinem Zusatztext auf der Startseite.
    """)
    
    recipes = load_recipes()
    
    if not recipes:
        st.warning("Noch keine Rezepte vorhanden. Erstelle zuerst ein Rezept!")
    else:
        # Tabs für die drei Slots
        tab1, tab2, tab3 = st.tabs(["📅 Rezept der Woche", "🗓️ Monatsrezept", "🍂 Jahreszeitrezept"])
        
        # === TAB 1: Rezept der Woche ===
        with tab1:
            st.subheader("📅 Rezept der Woche")
            
            # Finde aktuelles Rezept der Woche
            current = None
            current_idx = None
            for i, r in enumerate(recipes):
                if r.get("featuredWeek", False):
                    current = r
                    current_idx = i
                    break
            
            # Zeige aktuelles
            if current:
                st.success(f"📍 Aktuell: **{current.get('title', 'Unbenannt')}**")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    img_src = get_image_display(current, width=200)
                    if img_src:
                        try:
                            st.image(img_src, width=200)
                        except:
                            pass
                
                with col2:
                    st.markdown(f"**{current.get('title')}**")
                    if current.get('subtitle'):
                        st.markdown(f"*{current.get('subtitle')}*")
                    
                    if current.get("featuredWeekText"):
                        st.info(f"💬 {current['featuredWeekText']}")
                    else:
                        st.warning("⚠️ Kein Zusatztext")
                
                if st.button("🗑️ Rezept der Woche entfernen", key="remove_week"):
                    recipes[current_idx]["featuredWeek"] = False
                    recipes[current_idx]["featuredWeekText"] = ""
                    if save_recipes(recipes, force_save=True):
                        st.success("✅ Entfernt!")
                        safe_rerun()
            else:
                st.info("Kein Rezept der Woche ausgewählt")
            
            st.markdown("---")
            
            # Neues auswählen
            published = [(i, r) for i, r in enumerate(recipes) if r.get("published", True)]
            
            if published:
                options = ["(Nicht festlegen)"] + [f"{r.get('title', 'Unbenannt')}" for i, r in published]
                selected = st.selectbox("Neues Rezept der Woche:", options, key="sel_week")
                
                if selected != "(Nicht festlegen)":
                    idx = options.index(selected) - 1
                    actual_idx, recipe = published[idx]
                    
                    # Vorschau
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        img_src = get_image_display(recipe, width=150)
                        if img_src:
                            try:
                                st.image(img_src, width=150)
                            except:
                                pass
                    with col2:
                        st.write(f"**{recipe.get('title')}**")
                        st.caption(f"Kategorie: {recipe.get('category', '?')}")
                    
                    week_text = st.text_area(
                        "Zusatztext",
                        value=recipe.get("featuredWeekText", ""),
                        placeholder="z.B. 'Perfekt für kalte Herbsttage!'",
                        key="week_text"
                    )
                    
                    if st.button("� Festlegen", key="set_week"):
                        for i, r in enumerate(recipes):
                            if i == actual_idx:
                                recipes[i]["featuredWeek"] = True
                                recipes[i]["featuredWeekText"] = week_text
                            else:
                                recipes[i]["featuredWeek"] = False
                        
                        if save_recipes(recipes, force_save=True):
                            st.success(f"✅ '{recipe.get('title')}' ist jetzt Rezept der Woche!")
                            safe_rerun()
        
        # === TAB 2: Monatsrezept ===
        with tab2:
            st.subheader("🗓️ Monatsrezept")
            
            # Finde aktuelles Monatsrezept
            current = None
            current_idx = None
            for i, r in enumerate(recipes):
                if r.get("featuredMonth", False):
                    current = r
                    current_idx = i
                    break
            
            # Zeige aktuelles
            if current:
                st.success(f"📍 Aktuell: **{current.get('title', 'Unbenannt')}**")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    img_src = get_image_display(current, width=200)
                    if img_src:
                        try:
                            st.image(img_src, width=200)
                        except:
                            pass
                
                with col2:
                    st.markdown(f"**{current.get('title')}**")
                    if current.get('subtitle'):
                        st.markdown(f"*{current.get('subtitle')}*")
                    
                    if current.get("featuredMonthText"):
                        st.info(f"💬 {current['featuredMonthText']}")
                    else:
                        st.warning("⚠️ Kein Zusatztext")
                
                if st.button("🗑️ Monatsrezept entfernen", key="remove_month"):
                    recipes[current_idx]["featuredMonth"] = False
                    recipes[current_idx]["featuredMonthText"] = ""
                    if save_recipes(recipes, force_save=True):
                        st.success("✅ Entfernt!")
                        safe_rerun()
            else:
                st.info("Kein Monatsrezept ausgewählt")
            
            st.markdown("---")
            
            # Neues auswählen
            published = [(i, r) for i, r in enumerate(recipes) if r.get("published", True)]
            
            if published:
                options = ["(Nicht festlegen)"] + [f"{r.get('title', 'Unbenannt')}" for i, r in published]
                selected = st.selectbox("Neues Monatsrezept:", options, key="sel_month")
                
                if selected != "(Nicht festlegen)":
                    idx = options.index(selected) - 1
                    actual_idx, recipe = published[idx]
                    
                    # Vorschau
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        img_src = get_image_display(recipe, width=150)
                        if img_src:
                            try:
                                st.image(img_src, width=150)
                            except:
                                pass
                    with col2:
                        st.write(f"**{recipe.get('title')}**")
                        st.caption(f"Kategorie: {recipe.get('category', '?')}")
                    
                    month_text = st.text_area(
                        "Zusatztext",
                        value=recipe.get("featuredMonthText", ""),
                        placeholder="z.B. 'Das Highlight im Oktober!'",
                        key="month_text"
                    )
                    
                    if st.button("🗓️ Festlegen", key="set_month"):
                        for i, r in enumerate(recipes):
                            if i == actual_idx:
                                recipes[i]["featuredMonth"] = True
                                recipes[i]["featuredMonthText"] = month_text
                            else:
                                recipes[i]["featuredMonth"] = False
                        
                        if save_recipes(recipes, force_save=True):
                            st.success(f"✅ '{recipe.get('title')}' ist jetzt Monatsrezept!")
                            safe_rerun()
        
        # === TAB 3: Jahreszeitrezept ===
        with tab3:
            st.subheader("🍂 Jahreszeitrezept")
            
            # Finde aktuelles Jahreszeitrezept
            current = None
            current_idx = None
            for i, r in enumerate(recipes):
                if r.get("featuredSeason", False):
                    current = r
                    current_idx = i
                    break
            
            # Zeige aktuelles
            if current:
                st.success(f"📍 Aktuell: **{current.get('title', 'Unbenannt')}**")
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    img_src = get_image_display(current, width=200)
                    if img_src:
                        try:
                            st.image(img_src, width=200)
                        except:
                            pass
                
                with col2:
                    st.markdown(f"**{current.get('title')}**")
                    if current.get('subtitle'):
                        st.markdown(f"*{current.get('subtitle')}*")
                    
                    if current.get("featuredSeasonText"):
                        st.info(f"💬 {current['featuredSeasonText']}")
                    else:
                        st.warning("⚠️ Kein Zusatztext")
                
                if st.button("🗑️ Jahreszeitrezept entfernen", key="remove_season"):
                    recipes[current_idx]["featuredSeason"] = False
                    recipes[current_idx]["featuredSeasonText"] = ""
                    if save_recipes(recipes, force_save=True):
                        st.success("✅ Entfernt!")
                        safe_rerun()
            else:
                st.info("Kein Jahreszeitrezept ausgewählt")
            
            st.markdown("---")
            
            # Neues auswählen
            published = [(i, r) for i, r in enumerate(recipes) if r.get("published", True)]
            
            if published:
                options = ["(Nicht festlegen)"] + [f"{r.get('title', 'Unbenannt')}" for i, r in published]
                selected = st.selectbox("Neues Jahreszeitrezept:", options, key="sel_season")
                
                if selected != "(Nicht festlegen)":
                    idx = options.index(selected) - 1
                    actual_idx, recipe = published[idx]
                    
                    # Vorschau
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        img_src = get_image_display(recipe, width=150)
                        if img_src:
                            try:
                                st.image(img_src, width=150)
                            except:
                                pass
                    with col2:
                        st.write(f"**{recipe.get('title')}**")
                        st.caption(f"Kategorie: {recipe.get('category', '?')}")
                    
                    season_text = st.text_area(
                        "Zusatztext",
                        value=recipe.get("featuredSeasonText", ""),
                        placeholder="z.B. 'Ein Herbstklassiker!' oder 'Frühlingszauber'",
                        key="season_text"
                    )
                    
                    if st.button("🍂 Festlegen", key="set_season"):
                        for i, r in enumerate(recipes):
                            if i == actual_idx:
                                recipes[i]["featuredSeason"] = True
                                recipes[i]["featuredSeasonText"] = season_text
                            else:
                                recipes[i]["featuredSeason"] = False
                        
                        if save_recipes(recipes, force_save=True):
                            st.success(f"✅ '{recipe.get('title')}' ist jetzt Jahreszeitrezept!")
                            safe_rerun()

# === Modus: Vorlagen verwalten ===
if mode == "📋 Vorlagen verwalten":
    st.header("📋 Vorlagen & Kategorien verwalten")
    
    st.markdown("""
    **Verwalte deine Rezept-Organisation:**
    - **Vorlagen:** Spare Zeit beim Erstellen ähnlicher Rezepte
    - **Kategorien:** Passe die verfügbaren Kategorien an deine Bedürfnisse an
    """)
    
    # Haupttabs: Vorlagen vs Kategorien
    main_tab1, main_tab2 = st.tabs(["📋 Vorlagen", "📁 Kategorien"])
    
    with main_tab1:
        st.subheader("📋 Rezept-Vorlagen")
        st.markdown("""
        **Was sind Vorlagen?**
        - Spare Zeit beim Erstellen ähnlicher Rezepte (z.B. alle Pasta-Gerichte)
        - Erstelle deine eigenen Standard-Rezeptstrukturen
        - Nutze Vorlagen als Schnellstart statt bei Null anzufangen
        """)
        
        templates = load_templates()
        
        # Tabs für verschiedene Aktionen
        tab1, tab2, tab3 = st.tabs(["➕ Neue Vorlage", "📖 Aus Rezept erstellen", "✏️ Vorlagen bearbeiten"])
    
    with tab1:
        st.subheader("➕ Neue Vorlage von Grund auf erstellen")
        
        with st.form("new_template_form"):
            tmpl_name = st.text_input("Vorlagen-Name (z.B. '🥗 Mein Salat', '🍝 Meine Pasta')", max_chars=50)
            tmpl_desc = st.text_area("Beschreibung (optional)", max_chars=200)
            tmpl_cat = st.selectbox("Standard-Kategorie", [""] + load_categories())
            tmpl_diff = st.selectbox("Standard-Schwierigkeit", ["Einfach", "Mittel", "Schwer"])
            
            st.markdown("**Standard-Zutaten (optional):**")
            st.info("💡 Lasse Felder leer wenn die Vorlage nur Kategorie/Schwierigkeit vorgeben soll")
            
            tmpl_ingredients_text = st.text_area(
                "Zutaten (eine pro Zeile, Format: 'Menge Einheit Name' z.B. '200 g Mehl')",
                height=150
            )
            
            tmpl_tags = st.text_input("Standard-Tags (kommagetrennt, z.B. 'schnell, einfach, vegan')")
            
            submit_new = st.form_submit_button("💾 Vorlage speichern")
            
            if submit_new:
                if not tmpl_name or not tmpl_name.strip():
                    st.error("❌ Bitte gib einen Namen für die Vorlage ein!")
                else:
                    # Parse ingredients
                    ingredients_list = []
                    if tmpl_ingredients_text.strip():
                        for line in tmpl_ingredients_text.strip().split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            parts = line.split(None, 2)  # Split max 3 parts
                            if len(parts) >= 3:
                                ingredients_list.append({
                                    "amount": parts[0],
                                    "unit": parts[1],
                                    "name": parts[2]
                                })
                            elif len(parts) == 2:
                                ingredients_list.append({
                                    "amount": parts[0],
                                    "unit": "",
                                    "name": parts[1]
                                })
                            elif len(parts) == 1:
                                ingredients_list.append({
                                    "amount": "",
                                    "unit": "",
                                    "name": parts[0]
                                })
                    
                    # Create template
                    new_template = {
                        "name": tmpl_name.strip(),
                        "description": tmpl_desc.strip() if tmpl_desc else "",
                        "category": tmpl_cat,
                        "difficulty": tmpl_diff,
                        "ingredients": [{"group": "Basis", "items": ingredients_list}] if ingredients_list else [],
                        "tags": [t.strip() for t in tmpl_tags.split(",") if t.strip()] if tmpl_tags else []
                    }
                    
                    templates.append(new_template)
                    if save_templates(templates):
                        st.success(f"✅ Vorlage '{tmpl_name}' wurde gespeichert!")
                        st.info("🔄 Gehe zu 'Neues Rezept erstellen' um die Vorlage zu nutzen")
                        time.sleep(2)
                        safe_rerun()
    
    with tab2:
        st.subheader("📖 Vorlage aus bestehendem Rezept erstellen")
        st.info("💡 Wähle ein Rezept aus und erstelle daraus eine Vorlage für ähnliche Rezepte")
        
        recipes = load_recipes()
        if not recipes:
            st.warning("Noch keine Rezepte vorhanden. Lege zuerst Rezepte an.")
        else:
            recipe_titles = [f"{i+1}. {r.get('title', '(kein Titel)')}" for i, r in enumerate(recipes)]
            selected_idx = st.selectbox("Rezept auswählen:", range(len(recipes)), 
                                       format_func=lambda x: recipe_titles[x])
            
            selected_recipe = recipes[selected_idx]
            
            st.markdown("**Vorschau des gewählten Rezepts:**")
            with st.expander("📄 Rezept anzeigen"):
                st.json(selected_recipe)
            
            with st.form("recipe_to_template_form"):
                tmpl_name = st.text_input("Name für die Vorlage", 
                                         value=f"📋 {selected_recipe.get('title', 'Vorlage')}")
                tmpl_desc = st.text_area("Beschreibung der Vorlage", 
                                        value=f"Vorlage basierend auf: {selected_recipe.get('title', '')}")
                
                include_ingredients = st.checkbox("Zutaten übernehmen", value=True)
                include_tags = st.checkbox("Tags übernehmen", value=True)
                
                submit_from_recipe = st.form_submit_button("💾 Als Vorlage speichern")
                
                if submit_from_recipe:
                    new_template = {
                        "name": tmpl_name.strip(),
                        "description": tmpl_desc.strip(),
                        "category": selected_recipe.get("category", ""),
                        "difficulty": selected_recipe.get("difficulty", "Einfach"),
                        "ingredients": selected_recipe.get("ingredients", []) if include_ingredients else [],
                        "tags": selected_recipe.get("tags", []) if include_tags else []
                    }
                    
                    templates.append(new_template)
                    if save_templates(templates):
                        st.success(f"✅ Vorlage '{tmpl_name}' aus Rezept erstellt!")
                        time.sleep(2)
                        safe_rerun()
    
    with tab3:
        st.subheader("✏️ Bestehende Vorlagen bearbeiten/löschen")
        
        if not templates:
            st.info("Noch keine Vorlagen vorhanden. Erstelle zuerst eine Vorlage in den anderen Tabs.")
        else:
            st.markdown(f"**{len(templates)} Vorlage(n) gespeichert:**")
            
            for idx, tmpl in enumerate(templates):
                with st.expander(f"{tmpl.get('name', f'Vorlage {idx+1}')}"):
                    st.write(f"**Beschreibung:** {tmpl.get('description', '(keine)')}")
                    st.write(f"**Kategorie:** {tmpl.get('category', '(keine)')}")
                    st.write(f"**Schwierigkeit:** {tmpl.get('difficulty', 'Einfach')}")
                    
                    if tmpl.get("ingredients"):
                        st.write(f"**Zutaten:** {sum(len(g.get('items', [])) for g in tmpl.get('ingredients', []))} Stück")
                    
                    if tmpl.get("tags"):
                        st.write(f"**Tags:** {', '.join(tmpl['tags'])}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Löschen", key=f"del_tmpl_{idx}"):
                            templates.pop(idx)
                            if save_templates(templates):
                                st.success("✅ Vorlage gelöscht!")
                                time.sleep(1)
                                safe_rerun()
                    
                    with col2:
                        st.info("💡 Bearbeiten kommt bald - lösche und erstelle neu")
    
    with main_tab2:
        st.subheader("📁 Kategorien verwalten")
        st.markdown("""
        **Kategorien anpassen:**
        - Füge deine eigenen Kategorien hinzu
        - Lösche ungenutzte Kategorien
        - Kategorien werden in allen Dropdowns verwendet
        """)
        
        categories = load_categories()
        
        # Tabs für Kategorien-Aktionen
        cat_tab1, cat_tab2 = st.tabs(["➕ Kategorie hinzufügen", "✏️ Kategorien bearbeiten"])
        
        with cat_tab1:
            st.markdown("**Neue Kategorie hinzufügen:**")
            
            with st.form("new_category_form"):
                new_cat = st.text_input("Kategorie-Name (z.B. 'Frühstück', 'Smoothies', 'Backen')", max_chars=50)
                
                submit_cat = st.form_submit_button("➕ Kategorie hinzufügen")
                
                if submit_cat:
                    if not new_cat or not new_cat.strip():
                        st.error("❌ Bitte gib einen Namen ein!")
                    elif new_cat.strip() in categories:
                        st.warning(f"⚠️ Kategorie '{new_cat.strip()}' existiert bereits!")
                    else:
                        categories.append(new_cat.strip())
                        if save_categories(categories):
                            st.success(f"✅ Kategorie '{new_cat.strip()}' hinzugefügt!")
                            st.info("🔄 Ab jetzt in allen Dropdown-Menüs verfügbar")
                            time.sleep(2)
                            safe_rerun()
        
        with cat_tab2:
            st.markdown("**Bestehende Kategorien verwalten:**")
            
            if not categories:
                st.warning("⚠️ Keine Kategorien vorhanden!")
            else:
                st.info(f"📋 {len(categories)} Kategorie(n) verfügbar")
                
                # Zeige verwendete Kategorien in Rezepten
                recipes = load_recipes()
                used_categories = {}
                for recipe in recipes:
                    cat = recipe.get("category", "")
                    if cat:
                        used_categories[cat] = used_categories.get(cat, 0) + 1
                
                # Bearbeitungs-Modus Flag
                if "editing_category" not in st.session_state:
                    st.session_state["editing_category"] = None
                
                # Liste alle Kategorien
                for idx, cat in enumerate(categories):
                    # Prüfe ob diese Kategorie gerade bearbeitet wird
                    is_editing = st.session_state["editing_category"] == idx
                    
                    if is_editing:
                        # EDIT-MODUS: Zeige Textfeld
                        st.markdown(f"**Kategorie bearbeiten:**")
                        col_edit, col_save, col_cancel = st.columns([4, 1, 1])
                        
                        with col_edit:
                            new_name = st.text_input(
                                "Neuer Name", 
                                value=cat, 
                                key=f"edit_cat_name_{idx}",
                                label_visibility="collapsed"
                            )
                        
                        with col_save:
                            if st.button("✅", key=f"save_cat_{idx}"):
                                if new_name and new_name.strip() and new_name.strip() != cat:
                                    old_name = cat
                                    new_name_clean = new_name.strip()
                                    
                                    # Prüfe ob neuer Name schon existiert
                                    if new_name_clean in categories and new_name_clean != old_name:
                                        st.error(f"❌ Kategorie '{new_name_clean}' existiert bereits!")
                                    else:
                                        # Update Kategorie in der Liste
                                        categories[idx] = new_name_clean
                                        
                                        # Update alle Rezepte die diese Kategorie nutzen
                                        recipes_updated = False
                                        for recipe in recipes:
                                            if recipe.get("category") == old_name:
                                                recipe["category"] = new_name_clean
                                                recipes_updated = True
                                        
                                        # Speichern
                                        if save_categories(categories):
                                            if recipes_updated:
                                                save_recipes(recipes, force_save=True)
                                                st.success(f"✅ Kategorie '{old_name}' → '{new_name_clean}' umbenannt und {used_categories.get(old_name, 0)} Rezepte aktualisiert!")
                                            else:
                                                st.success(f"✅ Kategorie '{old_name}' → '{new_name_clean}' umbenannt!")
                                            st.session_state["editing_category"] = None
                                            time.sleep(1)
                                            safe_rerun()
                                elif new_name.strip() == cat:
                                    # Keine Änderung
                                    st.session_state["editing_category"] = None
                                    safe_rerun()
                                else:
                                    st.error("❌ Bitte gib einen Namen ein!")
                        
                        with col_cancel:
                            if st.button("❌", key=f"cancel_cat_{idx}"):
                                st.session_state["editing_category"] = None
                                safe_rerun()
                        
                        st.markdown("---")
                    
                    else:
                        # NORMAL-MODUS: Zeige Kategorie mit Buttons
                        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                        
                        with col1:
                            usage_count = used_categories.get(cat, 0)
                            if usage_count > 0:
                                st.write(f"**{cat}** ({usage_count} Rezept{'e' if usage_count != 1 else ''})")
                            else:
                                st.write(f"{cat} (nicht verwendet)")
                        
                        with col2:
                            # Verschieben
                            move_col1, move_col2 = st.columns(2)
                            with move_col1:
                                if idx > 0 and st.button("↑", key=f"cat_up_{idx}"):
                                    categories[idx], categories[idx-1] = categories[idx-1], categories[idx]
                                    if save_categories(categories):
                                        safe_rerun()
                            with move_col2:
                                if idx < len(categories) - 1 and st.button("↓", key=f"cat_down_{idx}"):
                                    categories[idx], categories[idx+1] = categories[idx+1], categories[idx]
                                    if save_categories(categories):
                                        safe_rerun()
                        
                        with col3:
                            if st.button("✏️", key=f"edit_cat_{idx}"):
                                st.session_state["editing_category"] = idx
                                safe_rerun()
                        
                        with col4:
                            if st.button("🗑️", key=f"del_cat_{idx}"):
                                if usage_count > 0:
                                    st.warning(f"⚠️ '{cat}' wird von {usage_count} Rezept(en) verwendet!")
                                    st.info("💡 Tipp: Benenne um oder ändere die Kategorie der betroffenen Rezepte")
                                else:
                                    categories.pop(idx)
                                    if save_categories(categories):
                                        st.success(f"✅ Kategorie '{cat}' gelöscht!")
                                        time.sleep(1)
                                        safe_rerun()

# === Dashboard / Statistiken ===
st.sidebar.markdown("## 📊 Dashboard")
recipes_count = len(recipes)
st.sidebar.metric("Gesamt Rezepte", recipes_count)

# Git Status anzeigen
try:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_status = subprocess.run(
        ["git", "status", "--short", "admin/recipes.json", "admin/templates.json", "admin/categories.json"],
        cwd=repo_root,
        capture_output=True,
        timeout=2,
        text=True
    )
    
    if git_status.returncode == 0:
        changes = git_status.stdout.strip()
        if changes:
            st.sidebar.warning(f"⚠️ Ungespeicherte Git-Änderungen")
        else:
            # Prüfe ob Commits vorhanden sind die noch nicht gepusht wurden
            git_unpushed = subprocess.run(
                ["git", "log", "@{u}..", "--oneline"],
                cwd=repo_root,
                capture_output=True,
                timeout=2,
                text=True
            )
            if git_unpushed.returncode == 0 and git_unpushed.stdout.strip():
                unpushed_count = len(git_unpushed.stdout.strip().split("\n"))
                st.sidebar.info(f"📤 {unpushed_count} Commit(s) bereit zum Push")
            else:
                st.sidebar.success("✅ Git: Alles synchronisiert")
except:
    pass  # Git-Status nicht kritisch

# Kategorien-Verteilung
if recipes_count > 0:
    categories = {}
    difficulties = {}
    recent_recipe = None
    recent_date = None
    
    for r in recipes:
        # Kategorien zählen
        cat = r.get("category", "Ohne Kategorie")
        categories[cat] = categories.get(cat, 0) + 1
        
        # Schwierigkeit zählen
        diff = r.get("difficulty", "Unbekannt")
        difficulties[diff] = difficulties.get(diff, 0) + 1
        
        # Zuletzt bearbeitet finden
        updated = r.get("updated_at") or r.get("created_at")
        if updated:
            if recent_date is None or updated > recent_date:
                recent_date = updated
                recent_recipe = r.get("title", "Unbekannt")
    
    # Kategorien anzeigen
    if categories:
        st.sidebar.markdown("**📁 Kategorien:**")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            st.sidebar.write(f"• {cat}: {count}")
    
    # Zuletzt bearbeitet
    if recent_recipe:
        st.sidebar.markdown(f"**🕒 Zuletzt:** {recent_recipe}")

# === Suche & Filter ===
st.sidebar.markdown("---")
st.sidebar.markdown("## 🔍 Suche & Filter")

# Suchfeld
search_query = st.sidebar.text_input("Suche nach Titel/Zutat", key="search_query", placeholder="z.B. Lasagne oder Tofu")

# Filter
filter_category = st.sidebar.selectbox(
    "Kategorie filtern",
    ["Alle"] + sorted(list(set(r.get("category", "Ohne Kategorie") for r in recipes)))
)

filter_difficulty = st.sidebar.selectbox(
    "Schwierigkeit filtern",
    ["Alle", "Einfach", "Mittel", "Schwer"]
)

# Funktion zum Filtern der Rezepte
def filter_recipes(recipes, search="", category="Alle", difficulty="Alle"):
    """Filtert Rezepte basierend auf Suchkriterien."""
    filtered = recipes
    
    # Textsuche
    if search and search.strip():
        search_lower = search.lower().strip()
        filtered = [r for r in filtered if 
                   search_lower in r.get("title", "").lower() or
                   search_lower in r.get("subtitle", "").lower() or
                   any(search_lower in item.get("name", "").lower() 
                       for group in r.get("ingredients", []) 
                       for item in group.get("items", []))]
    
    # Kategorie-Filter
    if category != "Alle":
        filtered = [r for r in filtered if r.get("category") == category]
    
    # Schwierigkeit-Filter
    if difficulty != "Alle":
        filtered = [r for r in filtered if r.get("difficulty") == difficulty]
    
    return filtered

# Speichere gefilterte Rezepte in session_state
st.session_state["filtered_recipes"] = filter_recipes(
    recipes, 
    search_query, 
    filter_category, 
    filter_difficulty
)

# Zeige Anzahl gefilterter Rezepte
if search_query or filter_category != "Alle" or filter_difficulty != "Alle":
    st.sidebar.info(f"🔎 {len(st.session_state['filtered_recipes'])} von {len(recipes)} Rezepten")

# === Seitliches Info / Import / Export ===
st.sidebar.markdown("---")
st.sidebar.markdown("**Import / Export**")
# Always show uploader so user can pick a file; process immediately and reload
uploaded = st.sidebar.file_uploader("Importiere recipes.json (wähle Datei)", type=["json"], key="imp")

# Guard gegen Endlos-Schleife: Nur verarbeiten wenn noch nicht importiert
if uploaded is not None and not st.session_state.get("import_processed"):
    try:
        parsed = json.load(uploaded)
        if isinstance(parsed, list):
            save_recipes(parsed)
            st.session_state["import_processed"] = True
            st.success("Import erfolgreich. Neuladen...")
            safe_rerun()
        else:
            st.error("Die Datei muss ein Array von Rezepten sein.")
    except Exception as e:
        st.error(f"Import-Fehler: {e}")
elif uploaded is None:
    # Reset flag wenn kein Upload mehr vorhanden
    st.session_state.pop("import_processed", None)

if st.sidebar.button("Exportiere recipes.json"):
    recipes = load_recipes()
    st.sidebar.download_button("Download recipes.json", data=json.dumps(recipes, ensure_ascii=False, indent=2), file_name="recipes.json", mime="application/json")

# === Paket-Updates ===
st.sidebar.markdown("---")
st.sidebar.markdown("**🔧 Wartung**")

# Version History / Restore
script_dir = os.path.dirname(os.path.abspath(__file__))
backup_dir = os.path.join(script_dir, "recipes_history")
if os.path.exists(backup_dir):
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("recipes_")], reverse=True)
    if backups:
        with st.sidebar.expander("⏮️ Version History (Restore)"):
            st.markdown("**Letzte 5 Backups:**")
            for backup in backups[:5]:
                # Parse Timestamp
                timestamp_str = backup.replace("recipes_", "").replace(".json", "")
                try:
                    from datetime import datetime
                    dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    display_time = dt.strftime("%d.%m.%Y %H:%M")
                except:
                    display_time = timestamp_str
                
                col_info, col_restore = st.columns([3, 1])
                with col_info:
                    st.text(display_time)
                with col_restore:
                    if st.button("↩️", key=f"restore_{backup}"):
                        # Restore Backup
                        backup_path = os.path.join(backup_dir, backup)
                        try:
                            with open(backup_path, "r", encoding="utf-8") as f:
                                restored_recipes = json.load(f)
                            if save_recipes(restored_recipes):
                                st.success(f"✅ Version von {display_time} wiederhergestellt!")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Restore fehlgeschlagen: {e}")

if st.sidebar.button("🔄 Auf Updates prüfen"):
    st.session_state.pop('update_check_done', None)  # Erlaube neue Prüfung
    st.rerun()

if st.sidebar.button("📦 Pakete neu installieren"):
    required = ['requests', 'beautifulsoup4', 'google-generativeai', 'pillow']
    with st.spinner("Installiere Pakete..."):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--force-reinstall"] + required)
            st.success("✅ Alle Pakete neu installiert!")
            st.info("🔄 Bitte App neu starten")
        except Exception as e:
            st.error(f"❌ Fehler: {e}")

# === Modus: Bilder verwalten ===
if mode == "📸 Bilder verwalten":
    st.header("📸 Bilder-Galerie & Verwaltung")
    
    st.markdown("""
    **Alle Rezeptbilder:**
    - Verwalte deine Bilder zentral
    - Konvertiere Base64 zu WebP-Dateien
    - Wiederverwende Bilder für neue Rezepte
    """)
    
    # Tabs: Rezeptbilder vs Galerie
    tab1, tab2 = st.tabs(["📋 Rezeptbilder (aus JSON)", "📁 Galerie (Dateien)"])
    
    with tab1:
        st.subheader("Bilder aus Rezepten")
        
        recipe_images = extract_images_from_recipes()
        
        if not recipe_images:
            st.info("📁 Keine Bilder in Rezepten gefunden.")
        else:
            st.success(f"✅ {len(recipe_images)} Bild(er) in Rezepten")
            
            # Suche
            search_recipe = st.text_input("🔍 Suche nach Rezeptname", placeholder="z.B. Käsespätzle", key="search_recipe")
            
            if search_recipe:
                recipe_images = [img for img in recipe_images if search_recipe.lower() in img['title'].lower()]
                st.info(f"🔎 {len(recipe_images)} Treffer")
            
            # Anzeige
            cols_per_row = 3
            for i in range(0, len(recipe_images), cols_per_row):
                cols = st.columns(cols_per_row)
                
                for col_idx, img in enumerate(recipe_images[i:i+cols_per_row]):
                    with cols[col_idx]:
                        try:
                            # Zeige Bild
                            if img['image_type'] == 'base64':
                                st.image(img['image_data'], use_container_width=True)
                                
                                # Info
                                st.caption(f"**{img['title']}**")
                                size_mb = img['size'] / (1024 * 1024)
                                st.caption(f"� {size_mb:.1f} MB (Base64) | 📅 {img['date']}")
                                st.caption(f"🔖 {img['recipe']}")
                                
                                # Aktion: Zu Datei konvertieren
                                if st.button("💾 Als WebP speichern", key=f"convert_{img['recipe']}", help="Konvertiert zu Datei"):
                                    with st.spinner("Konvertiere..."):
                                        try:
                                            # Decode Base64
                                            import io
                                            from PIL import Image
                                            
                                            # Extrahiere Base64-Daten
                                            if ',' in img['image_data']:
                                                base64_data = img['image_data'].split(',', 1)[1]
                                            else:
                                                base64_data = img['image_data']
                                            
                                            # Decode und öffne als Bild
                                            image_bytes = base64.b64decode(base64_data)
                                            image_file = io.BytesIO(image_bytes)
                                            
                                            # Speichere als Datei
                                            filename = save_recipe_image(image_file, img['recipe'])
                                            
                                            if filename:
                                                st.success(f"✅ Gespeichert: {filename}")
                                                st.info("💡 Du kannst jetzt das Rezept bearbeiten und den Dateinamen verwenden!")
                                            
                                        except Exception as e:
                                            st.error(f"❌ Fehler: {e}")
                            
                            else:  # file
                                # Zeige Vorschau (falls Datei existiert)
                                st.caption(f"**{img['title']}**")
                                st.code(img['filename'], language=None)
                                st.caption(f"🔖 {img['recipe']}")
                        
                        except Exception as e:
                            st.error(f"Fehler: {e}")
    
    with tab2:
        st.subheader("Datei-Galerie")
        
        images = list_recipe_images()
        
        if not images:
            st.info("📁 Noch keine Dateien in der Galerie. Konvertiere Base64-Bilder oder lade neue hoch.")
        else:
            st.success(f"✅ {len(images)} Datei(en) gefunden")
            
            # Suche
            search_query = st.text_input("🔍 Suche nach Dateiname", placeholder="z.B. käsespätzle", key="search_gallery")
            
            # Filter
            if search_query:
                images = [img for img in images if search_query.lower() in img['filename'].lower()]
                st.info(f"🔎 {len(images)} Treffer")
            
            # Anzeige
            cols_per_row = 3
            for i in range(0, len(images), cols_per_row):
                cols = st.columns(cols_per_row)
                
                for col_idx, img in enumerate(images[i:i+cols_per_row]):
                    with cols[col_idx]:
                        try:
                            # Zeige Bild
                            st.image(img['path'], use_container_width=True)
                            
                            # Info
                            st.caption(f"**{img['filename']}**")
                            size_mb = img['size'] / (1024 * 1024)
                            st.caption(f"📏 {size_mb:.2f} MB | 📅 {img['date'].strftime('%d.%m.%Y %H:%M')}")
                            st.caption(f"📂 {img['source']}")
                            
                            # URL zum Kopieren
                            st.code(img['url'], language=None)
                            
                            # Aktionen
                            col_del, col_use = st.columns(2)
                            
                            with col_del:
                                # Nur löschen wenn nicht in assets (sind statisch)
                                if img['source'] != 'src/assets':
                                    if st.button("🗑️", key=f"del_img_{img['filename']}_{img['source']}", help="Bild löschen"):
                                        try:
                                            os.remove(img['path'])
                                            st.success("✅ Gelöscht!")
                                            time.sleep(0.5)
                                            safe_rerun()
                                        except Exception as e:
                                            st.error(f"❌ Fehler: {e}")
                                else:
                                    st.caption("🔒 Statisch")
                            
                            with col_use:
                                if st.button("📋", key=f"copy_img_{img['filename']}_{img['source']}", help="URL kopieren"):
                                    st.session_state['selected_image'] = img['url']
                                    st.info(f"✅ {img['url']}")
                            
                        except Exception as e:
                            st.error(f"Fehler beim Laden: {e}")
        
        # Upload neuer Bilder
        st.markdown("---")
        st.subheader("📤 Neues Bild hochladen")
        
        upload_file = st.file_uploader("Bild auswählen", type=['jpg', 'jpeg', 'png', 'webp'], key="gallery_upload")
        upload_slug = st.text_input("Slug/Name (z.B. 'vegane-pizza')", key="gallery_slug")
        
        if st.button("💾 Bild speichern") and upload_file and upload_slug:
            with st.spinner("Speichere Bild..."):
                filename = save_recipe_image(upload_file, upload_slug)
                if filename:
                    st.success(f"✅ Bild gespeichert: {filename}")
                    time.sleep(1)
                    safe_rerun()

# ========== ENDE TEIL 2 ==========
