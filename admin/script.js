(() => {
  // --- STATE ---
  let recipes = [];
  let ingredientGroupCount = 0;
  let stepCount = 0;
  let currentImageBase64 = '';
  let currentEditImageBase64 = '';
  let currentEditIndex = null;
  let featuredRecipe = { recipeIndex: 0, additionalText: '' };

  // --- ELEMENTS ---
  const startSection = document.getElementById('start-section');
  const importJsonStartBtn = document.getElementById('import-json-start-btn');
  const importFileStart = document.getElementById('import-file-start');
  const menuSection = document.getElementById('menu-section');

  const createModeBtn = document.getElementById('create-mode-btn');
  const editModeBtn = document.getElementById('edit-mode-btn');
  const exportBtn = document.getElementById('export-json-btn');

  const importBtn = document.getElementById('import-json-btn'); // Neuer Lade-Button
  const importFile = document.getElementById('import-file');     // verstecktes Input

  const formSection = document.getElementById('form-section');
  const createBackBtn = document.getElementById('create-back-btn');
  const recipeForm = document.getElementById('recipe-form');
  const ingredientsContainer = document.getElementById('ingredients-container');
  const addIngredientGroupBtn = document.getElementById('add-ingredient-group');
  const stepsContainer = document.getElementById('steps-container');
  const addStepBtn = document.getElementById('add-step');
  const imageInput = document.getElementById('image');
  const imagePreview = document.getElementById('image-preview');

  const editSection = document.getElementById('edit-section');
  const editBackBtn = document.getElementById('edit-back-btn');
  const searchInput = document.getElementById('search-recipe');
  const searchResults = document.getElementById('search-results');
  const editFormContainer = document.getElementById('edit-form');
  const editForm = document.getElementById('edit-recipe-form');
  const editIngredientsContainer = document.getElementById('edit-ingredients-container');
  const editStepsContainer = document.getElementById('edit-steps-container');
  const editAddIngredientBtn = document.getElementById('edit-add-ingredient-group');
  const editAddStepBtn = document.getElementById('edit-add-step');
  const editImageInput = document.getElementById('edit-image');
  const editImagePreview = document.getElementById('edit-image-preview');
  const saveEditBtn = document.getElementById('save-edit-btn');
  const deleteEditBtn = document.getElementById('delete-edit-btn');

  const featuredSection = document.getElementById('featured-section');
  const featuredBackBtn = document.getElementById('featured-back-btn');
  const featuredModeBtn = document.getElementById('featured-mode-btn');

  const recipeList = document.getElementById('recipe-list');

  // --- INIT ---
  if (loadFromStorage()) showMenu(); 
  else showStart();

  // --- SHOW/HIDE ---
  function showStart() {
    startSection.style.display = 'block';
    menuSection.style.display = 'none';
    formSection.style.display = 'none';
    editSection.style.display = 'none';
    featuredSection.style.display = 'none';
  }
  function showMenu() {
    startSection.style.display = 'none';
    menuSection.style.display = 'block';
    formSection.style.display = 'none';
    editSection.style.display = 'none';
    featuredSection.style.display = 'none';
    renderRecipes();
  }

  // --- LOCALSTORAGE ---
  function loadFromStorage() {
    const raw = localStorage.getItem('vt_recipes');
    if (!raw) return false;
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        recipes = parsed;
        // Load featured
        const featuredRaw = localStorage.getItem('vt_featured');
        if (featuredRaw) {
          try {
            featuredRecipe = JSON.parse(featuredRaw);
          } catch (e) { console.warn('Featured parse error', e); }
        }
        return true;
      }
    } catch (e) { console.warn('LocalStorage parse error', e); }
    return false;
  }
  function persist() { localStorage.setItem('vt_recipes', JSON.stringify(recipes)); }
  function persistFeatured() { localStorage.setItem('vt_featured', JSON.stringify(featuredRecipe)); }
  function persistAndRender() { persist(); renderRecipes(); }

  // --- IMPORT JSON (Start) ---
  importJsonStartBtn.addEventListener('click', () => importFileStart.click());
  importFileStart.addEventListener('change', e => handleImportFile(e, true));

  // --- IMPORT JSON (Menü) ---
  importBtn.addEventListener('click', () => importFile.click());
  importFile.addEventListener('change', e => handleImportFile(e));

  function handleImportFile(e, isStart=false) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result);
        if (!Array.isArray(parsed)) throw new Error('JSON muss ein Array sein');
        recipes = parsed;
        persistAndRender();
        showMenu();
        alert('Import erfolgreich!');
      } catch (err) { alert('Import fehlgeschlagen: ' + err.message); }
    };
    reader.readAsText(file);
    e.target.value = '';
  }

  // --- EXPORT JSON ---
  exportBtn.addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(recipes, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'recipes.json';
    a.click();
    URL.revokeObjectURL(url);
  });

  // --- MENU BUTTONS ---
  createModeBtn.addEventListener('click', () => {
    resetCreateForm();
    formSection.style.display = 'block';
    editSection.style.display = 'none';
  });
  editModeBtn.addEventListener('click', () => {
    resetEditForm();
    formSection.style.display = 'none';
    editSection.style.display = 'block';
    editFormContainer.style.display = 'none';
  });
  createBackBtn.addEventListener('click', showMenu);
  editBackBtn.addEventListener('click', showMenu);
  featuredModeBtn.addEventListener('click', () => {
    formSection.style.display = 'none';
    editSection.style.display = 'none';
    featuredSection.style.display = 'block';
    loadFeaturedSection();
  });
  featuredBackBtn.addEventListener('click', showMenu);

  // --- FEATURED SECTION ---
  function loadFeaturedSection() {
    const select = document.getElementById('featured-recipe-select');
    select.innerHTML = '';
    
    recipes.forEach((r, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = `${idx + 1}. ${r.title}`;
      if (idx === featuredRecipe.recipeIndex) opt.selected = true;
      select.appendChild(opt);
    });
    
    document.getElementById('featured-additional-text').value = featuredRecipe.additionalText || '';
    updateFeaturedPreview();
  }

  function updateFeaturedPreview() {
    const idx = parseInt(document.getElementById('featured-recipe-select').value);
    const recipe = recipes[idx];
    if (!recipe) return;
    
    const preview = document.getElementById('featured-preview');
    preview.innerHTML = `
      <h4>${recipe.title}</h4>
      <p><strong>Zeit:</strong> ${recipe.cookTime || recipe.preparationTime || 'N/A'}</p>
      <p><strong>Portionen:</strong> ${recipe.portion || 'N/A'}</p>
      <p><strong>Schwierigkeit:</strong> ${recipe.difficulty || 'N/A'}</p>
    `;
  }

  document.getElementById('featured-recipe-select')?.addEventListener('change', updateFeaturedPreview);

  document.getElementById('btn-save-featured')?.addEventListener('click', () => {
    const idx = parseInt(document.getElementById('featured-recipe-select').value);
    const additionalText = document.getElementById('featured-additional-text').value;
    
    featuredRecipe = { recipeIndex: idx, additionalText };
    persistFeatured();
    
    // Export featured.json
    const blob = new Blob([JSON.stringify(featuredRecipe, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'featured.json';
    a.click();
    URL.revokeObjectURL(url);
    
    alert('Rezept der Woche gespeichert und featured.json heruntergeladen!');
  });

  // --- INGREDIENTS ---
  function addIngredientGroup(container) {
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
    container.appendChild(groupDiv);

    const ingredientsList = groupDiv.querySelector('.ingredients');
    const addIngredientBtn = groupDiv.querySelector('.add-ingredient');
    addIngredientBtn.addEventListener('click', () => {
      const row = document.createElement('div');
      row.className = 'ingredient-row';
      row.style.display = 'flex';
      row.style.gap = '8px';
      row.innerHTML = `
        <input type="text" class="amount" placeholder="Menge">
        <input type="text" class="unit" placeholder="Einheit">
        <input type="text" class="ingredient" placeholder="Zutat">
        <button type="button" class="delete-ingredient">✕</button>
      `;
      ingredientsList.appendChild(row);
      row.querySelector('.delete-ingredient').addEventListener('click', () => row.remove());
    });
  }
  addIngredientGroupBtn.addEventListener('click', () => addIngredientGroup(ingredientsContainer));
  editAddIngredientBtn.addEventListener('click', () => addIngredientGroup(editIngredientsContainer));

  // --- STEPS ---
  function addStep(container) {
    stepCount++;
    const stepDiv = document.createElement('div');
    stepDiv.className = 'step';
    stepDiv.innerHTML = `
      <h4>Schritt ${stepCount}</h4>
      <input type="text" class="step-time" placeholder="Zeit">
      <div class="needed-ingredients"></div>
      <button type="button" class="add-needed-ingredient">Zutat hinzufügen</button>
      <div class="step-substeps"></div>
      <button type="button" class="add-substep">Zubereitungs-Zwischenschritt hinzufügen</button>
      <hr>
    `;
    container.appendChild(stepDiv);

    const neededContainer = stepDiv.querySelector('.needed-ingredients');
    stepDiv.querySelector('.add-needed-ingredient').addEventListener('click', () => {
      const ing = document.createElement('div');
      ing.className = 'needed-row';
      ing.style.display = 'flex';
      ing.style.gap = '8px';
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
  }
  addStepBtn.addEventListener('click', () => addStep(stepsContainer));
  editAddStepBtn.addEventListener('click', () => addStep(editStepsContainer));

  // --- IMAGE PREVIEW ---
  imageInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      currentImageBase64 = reader.result;
      imagePreview.src = currentImageBase64;
      imagePreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
  });
  editImageInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      currentEditImageBase64 = reader.result;
      editImagePreview.src = currentEditImageBase64;
      editImagePreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
  });

  // --- HELPER FUNCTIONS ---
  function getRecipeFromForm(ingredientsCont, stepsCont, titleId, subtitleId, categoryId, prepId, cookId, portionId, diffId, tipsId, kcalId, proteinId, carbsId, fatId, fiberId) {
    const ingredientGroups = Array.from(ingredientsCont.querySelectorAll('.ingredient-group')).map(group => ({
      group: group.querySelector('.group-name').value,
      items: Array.from(group.querySelectorAll('.ingredient-row')).map(row => ({
        amount: row.querySelector('.amount').value,
        unit: row.querySelector('.unit').value,
        name: row.querySelector('.ingredient').value
      }))
    }));

    const steps = Array.from(stepsCont.querySelectorAll('.step')).map(step => ({
      time: step.querySelector('.step-time').value,
      needed: Array.from(step.querySelectorAll('.needed-row')).map(n => ({
        amount: n.querySelector('.needed-amount').value,
        unit: n.querySelector('.needed-unit').value,
        name: n.querySelector('.needed-name').value
      })),
      substeps: Array.from(step.querySelectorAll('.substep')).map(s => s.value)
    }));

    return {
      title: document.getElementById(titleId).value,
      subtitle: document.getElementById(subtitleId).value,
      category: document.getElementById(categoryId).value,
      preparationTime: document.getElementById(prepId).value,
      cookTime: document.getElementById(cookId).value,
      portion: document.getElementById(portionId).value,
      difficulty: document.getElementById(diffId).value,
      ingredients: ingredientGroups,
      steps: steps,
      tips: document.getElementById(tipsId).value,
      nutrition: {
        kcal: document.getElementById(kcalId).value,
        protein: document.getElementById(proteinId).value,
        carbs: document.getElementById(carbsId).value,
        fat: document.getElementById(fatId).value,
        fiber: document.getElementById(fiberId).value
      }
    };
  }

  // --- CREATE SUBMIT ---
  recipeForm.addEventListener('submit', e => {
    e.preventDefault();
    const recipe = getRecipeFromForm(ingredientsContainer, stepsContainer, 'title','subtitle','category','preparation-time','cook-time','portion','difficulty','tips','kcal','protein','carbs','fat','fiber');
    recipe.image = currentImageBase64 || '';
    recipes.push(recipe);
    persistAndRender();
    alert('Rezept hinzugefügt!');
    resetCreateForm();
  });

  // --- RESET FORM ---
  function resetCreateForm() {
    recipeForm.reset();
    ingredientsContainer.innerHTML = '';
    stepsContainer.innerHTML = '';
    currentImageBase64 = '';
    imagePreview.style.display = 'none';
    ingredientGroupCount = 0;
    stepCount = 0;
  }
  function resetEditForm() {
    editForm.reset();
    editIngredientsContainer.innerHTML = '';
    editStepsContainer.innerHTML = '';
    editFormContainer.style.display = 'none';
    currentEditImageBase64 = '';
    editImagePreview.style.display = 'none';
    currentEditIndex = null;
    ingredientGroupCount = 0;
    stepCount = 0;
    searchInput.value = '';
    searchResults.innerHTML = '';
  }

  // --- RENDER LIST ---
  function renderRecipes() {
    recipeList.innerHTML = '';
    recipes.forEach((r, i) => {
      const li = document.createElement('li');
      li.textContent = `${r.title} (${r.category})`;
      recipeList.appendChild(li);
    });
  }

  // --- LIVE SEARCH ---
  searchInput.addEventListener('input', () => {
    const term = searchInput.value.toLowerCase();
    searchResults.innerHTML = '';
    if (!term) return;
    recipes.forEach((r, i) => {
      if (r.title.toLowerCase().includes(term)) {
        const li = document.createElement('li');
        li.textContent = r.title;
        li.addEventListener('click', () => editRecipe(i));
        searchResults.appendChild(li);
      }
    });
  });

  function editRecipe(index) {
    currentEditIndex = index;
    const r = recipes[index];
    editFormContainer.style.display = 'block';
    document.getElementById('edit-title').value = r.title;
    document.getElementById('edit-subtitle').value = r.subtitle;
    document.getElementById('edit-category').value = r.category;
    document.getElementById('edit-preparation-time').value = r.preparationTime;
    document.getElementById('edit-cook-time').value = r.cookTime;
    document.getElementById('edit-portion').value = r.portion;
    document.getElementById('edit-difficulty').value = r.difficulty;
    document.getElementById('edit-tips').value = r.tips;
    document.getElementById('edit-kcal').value = r.nutrition.kcal;
    document.getElementById('edit-protein').value = r.nutrition.protein;
    document.getElementById('edit-carbs').value = r.nutrition.carbs;
    document.getElementById('edit-fat').value = r.nutrition.fat;
    document.getElementById('edit-fiber').value = r.nutrition.fiber;

    editIngredientsContainer.innerHTML = '';
    r.ingredients.forEach(group => {
      addIngredientGroup(editIngredientsContainer);
      const lastGroup = editIngredientsContainer.lastChild;
      lastGroup.querySelector('.group-name').value = group.group;
      const ingredientsList = lastGroup.querySelector('.ingredients');
      group.items.forEach(item => {
        const row = document.createElement('div');
        row.className = 'ingredient-row';
        row.style.display = 'flex';
        row.style.gap = '8px';
        row.innerHTML = `
          <input type="text" class="amount" placeholder="Menge" value="${item.amount}">
          <input type="text" class="unit" placeholder="Einheit" value="${item.unit}">
          <input type="text" class="ingredient" placeholder="Zutat" value="${item.name}">
          <button type="button" class="delete-ingredient">✕</button>
        `;
        ingredientsList.appendChild(row);
        row.querySelector('.delete-ingredient').addEventListener('click', () => row.remove());
      });
    });

    editStepsContainer.innerHTML = '';
    r.steps.forEach(step => {
      addStep(editStepsContainer);
      const lastStep = editStepsContainer.lastChild;
      lastStep.querySelector('.step-time').value = step.time;

      const neededContainer = lastStep.querySelector('.needed-ingredients');
      step.needed.forEach(n => {
        const ing = document.createElement('div');
        ing.className = 'needed-row';
        ing.style.display = 'flex';
        ing.style.gap = '8px';
        ing.innerHTML = `
          <input type="text" class="needed-amount" placeholder="Menge" value="${n.amount}">
          <input type="text" class="needed-unit" placeholder="Einheit" value="${n.unit}">
          <input type="text" class="needed-name" placeholder="Zutat" value="${n.name}">
          <button type="button" class="delete-ingredient">✕</button>
        `;
        neededContainer.appendChild(ing);
        ing.querySelector('.delete-ingredient').addEventListener('click', () => ing.remove());
      });

      const substepsContainer = lastStep.querySelector('.step-substeps');
      step.substeps.forEach(sub => {
        const subElem = document.createElement('textarea');
        subElem.placeholder = "Zubereitungs-Zwischenschritt";
        subElem.className = "substep";
        subElem.value = sub;
        substepsContainer.appendChild(subElem);
      });
    });

    if (r.image) {
      currentEditImageBase64 = r.image;
      editImagePreview.src = r.image;
      editImagePreview.style.display = 'block';
    } else {
      editImagePreview.style.display = 'none';
    }
  }

  saveEditBtn.addEventListener('click', () => {
    if (currentEditIndex === null) return;
    const updated = getRecipeFromForm(editIngredientsContainer, editStepsContainer, 'edit-title','edit-subtitle','edit-category','edit-preparation-time','edit-cook-time','edit-portion','edit-difficulty','edit-tips','edit-kcal','edit-protein','edit-carbs','edit-fat','edit-fiber');
    updated.image = currentEditImageBase64;
    recipes[currentEditIndex] = updated;
    persistAndRender();
    alert('Änderungen gespeichert!');
    resetEditForm();
  });

  deleteEditBtn.addEventListener('click', () => {
    if (currentEditIndex === null) return;
    if (confirm('Rezept wirklich löschen?')) {
      recipes.splice(currentEditIndex, 1);
      persistAndRender();
      resetEditForm();
    }
  });

})();
