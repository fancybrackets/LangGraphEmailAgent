const catalogList = document.getElementById("catalog-list");
const installedSelect = document.getElementById("installed-model-select");
const activateBtn = document.getElementById("activate-installed-btn");
const deleteBtn = document.getElementById("delete-installed-btn");
const refreshBtn = document.getElementById("refresh-installed-btn");
const activeModelBadge = document.getElementById("settings-active-model");
const resultBox = document.getElementById("settings-result");

function setResult(text, isError = false) {
  resultBox.textContent = text;
  resultBox.style.color = isError ? "#c92a2a" : "#4b5563";
}

async function apiJSON(path, options = {}) {
  const resp = await fetch(path, options);
  let data = {};
  try {
    data = await resp.json();
  } catch {
    data = {};
  }
  if (!resp.ok) {
    throw new Error(data?.detail || "Bilinmeyen hata");
  }
  return data;
}

async function loadInstalledModels() {
  const data = await apiJSON("/models");
  installedSelect.innerHTML = "";
  for (const model of data.models || []) {
    const option = document.createElement("option");
    option.value = model.name;
    option.textContent = model.name;
    installedSelect.appendChild(option);
  }
  activeModelBadge.textContent = data.active_model || "(secilmedi)";
}

async function loadCatalog() {
  const data = await apiJSON("/models/catalog");
  catalogList.innerHTML = "";

  for (const item of data.catalog || []) {
    const row = document.createElement("div");
    row.className = "catalog-item";
    row.innerHTML = `
      <div>
        <div class="catalog-title">${item.label}</div>
        <div class="catalog-sub">${item.name}</div>
        <div class="catalog-sub">${item.notes}</div>
      </div>
    `;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = "Indir";
    btn.addEventListener("click", async () => {
      setResult(`${item.name} indiriliyor...`);
      try {
        const res = await apiJSON("/models/pull", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: item.name }),
        });
        setResult(res.message || `${item.name} indirildi.`);
        await loadInstalledModels();
      } catch (error) {
        setResult(`Hata: ${error.message}`, true);
      }
    });

    row.appendChild(btn);
    catalogList.appendChild(row);
  }
}

async function activateSelected() {
  const model = installedSelect.value;
  if (!model) {
    setResult("Aktif etmek icin kurulu model sec.", true);
    return;
  }
  try {
    const data = await apiJSON("/models/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    setResult(`Aktif model: ${data.active_model}`);
    await loadInstalledModels();
  } catch (error) {
    setResult(`Hata: ${error.message}`, true);
  }
}

async function deleteSelected() {
  const model = installedSelect.value;
  if (!model) {
    setResult("Silmek icin kurulu model sec.", true);
    return;
  }
  try {
    const data = await apiJSON("/models/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    setResult(data.message || `${model} silindi.`);
    await loadInstalledModels();
  } catch (error) {
    setResult(`Hata: ${error.message}`, true);
  }
}

activateBtn.addEventListener("click", activateSelected);
deleteBtn.addEventListener("click", deleteSelected);
refreshBtn.addEventListener("click", async () => {
  try {
    await loadInstalledModels();
    setResult("Model listesi yenilendi.");
  } catch (error) {
    setResult(`Hata: ${error.message}`, true);
  }
});

loadCatalog().catch((error) => setResult(`Hata: ${error.message}`, true));
loadInstalledModels().catch((error) => setResult(`Hata: ${error.message}`, true));
