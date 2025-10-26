#!/bin/bash
# =====================================================
# Setup Script: VeganTalia Admin-Panel Installation
# =====================================================

TARGET_DIR="D://vegantalia/admin"

echo "📁 Erstelle Admin-Verzeichnis unter $TARGET_DIR..."
mkdir -p "$TARGET_DIR"

# =====================================================
# HTML-Datei (admin.html)
# =====================================================
cat > "$TARGET_DIR/admin.html" <<'EOL'
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VeganTalia Admin</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>VeganTalia Rezept-Admin</h1>
  <p>Hier kannst du neue Rezepte hinzufügen oder bestehende bearbeiten</p>
</header>

<main>
  <section id="form-section">
    <h2>Neues Rezept hinzufügen</h2>
    <form id="recipe-form">
      <input type="text" id="title" placeholder="Titel" required>
      <input type="text" id="subtitle" placeholder="Untertitel">
      <input type="file" id="image" accept="image/*">
      <select id="category">
        <option>Hauptgerichte</option>
        <option>Salate</option>
        <option>Dessert</option>
        <option>Vorspeise</option>
        <option>Schnelle Rezepte</option>
      </select>
      <input type="text" id="preparation-time" placeholder="Vorbereitung">
      <input type="text" id="cook-time" placeholder="Kochzeit">
      <input type="number" id="portion" placeholder="Portionen" value="2">
      <select id="difficulty">
        <option>Einfach</option>
        <option>Mittel</option>
        <option>Schwer</option>
      </select>

      <h3>Zutaten</h3>
      <div id="ingredients-container"></div>
      <button type="button" id="add-ingredient-group">Obergruppe hinzufügen</button>

      <h3>Zubereitung</h3>
      <div id="steps-container"></div>
      <button type="button" id="add-step">Neuen Schritt hinzufügen</button>

      <h3>Tipps & Variationen</h3>
      <textarea id="tips"></textarea>

      <h3>Nährwerte</h3>
      <input type="number" id="kcal" placeholder="kcal">
      <input type="number" id="protein" placeholder="Eiweiß">
      <input type="number" id="carbs" placeholder="KH">
      <input type="number" id="fat" placeholder="Fett">
      <input type="number" id="fiber" placeholder="Ballaststoffe">

      <button type="submit">Rezept speichern</button>
    </form>
  </section>

  <section id="list-section">
    <h2>Gespeicherte Rezepte</h2>
    <ul id="recipe-list"></ul>
  </section>
</main>

<script src="script.js"></script>
</body>
</html>
EOL

# =====================================================
# JavaScript-Datei (script.js)
# =====================================================
cat > "$TARGET_DIR/script.js" <<'EOL'
let recipes = [];

// ===== Zutaten =====
let ingredientGroupCount = 0;
const ingredientsContainer = document.getElementById('ingredients-container');
const addIngredientGroupBtn = document.getElementById('add-ingredient-group');

addIngredientGroupBtn.addEventListener('click', () => {
  ingredientGroupCount++;
  const groupDiv = document.createElement('div');
  groupDiv.className = 'ingredient-group';
  groupDiv.innerHTML = `
    <h4>Obergruppe ${ingredientGroupCount}</h4>
    <input type="text" placeholder="Obergruppenname" class="group-name">
    <div class="ingredients"></div>
    <button type="button" class="add-ingredient">Zutat hinzufügen</button>
    <hr>
  `;
  ingredientsContainer.appendChild(groupDiv);

  const ingredientsList = groupDiv.querySelector('.ingredients');
  const addIngredientBtn = groupDiv.querySelector('.add-ingredient');

  addIngredientBtn.addEventListener('click', () => {
    const row = document.createElement('div');
    row.className = 'ingredient-row';
    row.innerHTML = `
      <input type="text" class="amount" placeholder="Menge">
      <input type="text" class="unit" placeholder="Einheit">
      <input type="text" class="ingredient" placeholder="Zutat">
      <button type="button" class="delete-ingredient">✕</button>
    `;
    ingredientsList.appendChild(row);
    row.querySelector('.delete-ingredient').addEventListener('click', () => row.remove());
  });
});

// ===== Zubereitung =====
let stepCount = 0;
const stepsContainer = document.getElementById('steps-container');
const addStepBtn = document.getElementById('add-step');

addStepBtn.addEventListener('click', () => {
  stepCount++;
  const stepDiv = document.createElement('div');
  stepDiv.className = 'step';
  stepDiv.innerHTML = `
    <h4>Schritt ${stepCount}</h4>
    <input type="text" class="step-time" placeholder="Zeit">
    <p><strong>Was benötigt:</strong></p>
    <div class="needed-ingredients"></div>
    <button type="button" class="add-needed-ingredient">Zutat hinzufügen</button>
    <h5>Zubereitungs-Zwischenschritte:</h5>
    <div class="step-substeps"></div>
    <button type="button" class="add-substep">Zubereitungs-Zwischenschritt hinzufügen</button>
    <hr>
  `;
  stepsContainer.appendChild(stepDiv);

  const neededContainer = stepDiv.querySelector('.needed-ingredients');
  stepDiv.querySelector('.add-needed-ingredient').addEventListener('click', () => {
    const ing = document.createElement('div');
    ing.className = 'needed-row';
    ing.innerHTML = `
      <input type="text" class="needed-amount" placeholder="Menge">
      <input type="text" class="needed-unit" placeholder="Einheit">
      <input type="text" class="needed-name" placeholder="Zutat">
      <button type="button" class="delete-ingredient">✕</button>
    `;
    neededContainer.appendChild(ing);
    ing.querySelector('.delete-ingredient').addEventListener('click', () => ing.remove());
  });

  const substepsContainer = stepDiv.querySelector('.step-substeps');
  stepDiv.querySelector('.add-substep').addEventListener('click', () => {
    const sub = document.createElement('textarea');
    sub.placeholder = "Zubereitungs-Zwischenschritt";
    sub.className = "substep";
    substepsContainer.appendChild(sub);
  });
});

// ===== Rezept speichern =====
const form = document.getElementById('recipe-form');
const recipeList = document.getElementById('recipe-list');

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const ingredientGroups = Array.from(document.querySelectorAll('.ingredient-group')).map(group => ({
    group: group.querySelector('.group-name').value,
    items: Array.from(group.querySelectorAll('.ingredient-row')).map(row => ({
      amount: row.querySelector('.amount').value,
      unit: row.querySelector('.unit').value,
      name: row.querySelector('.ingredient').value
    }))
  }));

  const steps = Array.from(document.querySelectorAll('.step')).map(step => ({
    time: step.querySelector('.step-time').value,
    needed: Array.from(step.querySelectorAll('.needed-row')).map(r => ({
      amount: r.querySelector('.needed-amount').value,
      unit: r.querySelector('.needed-unit').value,
      name: r.querySelector('.needed-name').value
    })),
    substeps: Array.from(step.querySelectorAll('.substep')).map(s => s.value)
  }));

  const recipe = {
    title: document.getElementById('title').value,
    subtitle: document.getElementById('subtitle').value,
    category: document.getElementById('category').value,
    preparationTime: document.getElementById('preparation-time').value,
    cookTime: document.getElementById('cook-time').value,
    portion: document.getElementById('portion').value,
    difficulty: document.getElementById('difficulty').value,
    ingredients: ingredientGroups,
    steps: steps,
    tips: document.getElementById('tips').value,
    nutrition: {
      kcal: document.getElementById('kcal').value,
      protein: document.getElementById('protein').value,
      carbs: document.getElementById('carbs').value,
      fat: document.getElementById('fat').value,
      fiber: document.getElementById('fiber').value
    },
    createdAt: new Date().toISOString()
  };

  recipes.push(recipe);
  renderRecipes();
  saveToJSON();
  form.reset();
  ingredientsContainer.innerHTML = '';
  stepsContainer.innerHTML = '';
  ingredientGroupCount = 0;
  stepCount = 0;
});

function renderRecipes() {
  recipeList.innerHTML = '';
  recipes.forEach((r, idx) => {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${r.title}</strong> (${r.category}) <button onclick="deleteRecipe(${idx})">Löschen</button>`;
    recipeList.appendChild(li);
  });
}

function deleteRecipe(index) {
  recipes.splice(index, 1);
  renderRecipes();
  saveToJSON();
}

function saveToJSON() {
  const blob = new Blob([JSON.stringify(recipes, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'recipes.json';
  a.click();
}
EOL

# =====================================================
# CSS-Datei (style.css)
# =====================================================
cat > "$TARGET_DIR/style.css" <<'EOL'
body {
  font-family: 'Inter', sans-serif;
  background: linear-gradient(135deg, #f0fff4, #e8f5e9);
  color: #333;
  margin: 0;
  padding: 20px;
}
h1 {
  color: #256c2b;
  text-align: center;
  margin-bottom: 20px;
}
form {
  background: rgba(255, 255, 255, 0.85);
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  padding: 25px;
  max-width: 900px;
  margin: 0 auto;
}
input[type="text"],
input[type="number"],
select,
textarea {
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  border: 1px solid #d0d0d0;
  border-radius: 10px;
  background-color: #fff;
  box-sizing: border-box;
  font-size: 15px;
}
textarea {
  resize: vertical;
  min-height: 60px;
}
button {
  background-color: #2e7d32;
  color: white;
  padding: 8px 14px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  transition: all 0.2s ease-in-out;
}
button:hover {
  background-color: #256c2b;
  transform: translateY(-1px);
}
.ingredient-group, .step {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 20px;
  padding: 15px;
  margin-bottom: 20px;
  box-shadow: 0 3px 8px rgba(0,0,0,0.08);
}
.ingredient-row, .needed-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.delete-ingredient {
  background-color: #e53935;
}
.delete-ingredient:hover {
  background-color: #c62828;
}
.add-ingredient, .add-ingredient-group, .add-needed-ingredient, .add-substep, #add-step {
  margin-top: 5px;
  margin-bottom: 10px;
  display: inline-block;
}
.add-substep {
  background-color: #039be5;
}
.add-substep:hover {
  background-color: #0288d1;
}
.add-needed-ingredient {
  background-color: #f9a825;
}
.add-needed-ingredient:hover {
  background-color: #f57f17;
}
.substep, textarea.substep {
  width: 100%;
  min-height: 50px;
  margin-top: 6px;
  border-radius: 10px;
  border: 1px solid #ccc;
  padding: 6px;
  background: rgba(255,255,255,0.7);
}
#recipe-list {
  margin-top: 30px;
  padding: 0;
  list-style: none;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
}
#recipe-list li {
  background: white;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
#recipe-list button {
  background: #e53935;
}
#recipe-list button:hover {
  background: #c62828;
}
EOL

# =====================================================
# recipes.json vorbereiten
# =====================================================
echo "[]" > "$TARGET_DIR/recipes.json"

echo "✅ Setup abgeschlossen! Öffne $TARGET_DIR/admin.html im Browser."
