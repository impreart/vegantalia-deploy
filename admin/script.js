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
