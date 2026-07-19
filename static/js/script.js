const form = document.getElementById("try-on-form");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result");
const resultImg = document.getElementById("result-img");
const submitBtn = document.getElementById("submit-btn");

function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `tab-${name}`);
  });
}

document.querySelectorAll("[data-tab]").forEach((el) => {
  el.addEventListener("click", () => switchTab(el.dataset.tab));
});

function updateSubmitState() {
  const personId = document.getElementById("person_id").value;
  const anyGarment = ["top_id", "bottom_id", "shoes_id"].some(
    (id) => document.getElementById(id).value
  );
  submitBtn.disabled = !personId || !anyGarment;
}

function buildThumb(entry, { withDelete }) {
  const item = document.createElement("div");
  item.className = "library-item";
  item.dataset.id = entry.id;

  const img = document.createElement("img");
  img.src = entry.image_url;
  img.alt = entry.label || "";
  item.appendChild(img);

  if (withDelete) {
    const del = document.createElement("button");
    del.type = "button";
    del.className = "delete-btn";
    del.title = "Delete";
    del.textContent = "×";
    item.appendChild(del);
  }

  return item;
}

function clearEmptyState(grid) {
  const empty = grid.querySelector(".empty-state");
  if (empty) empty.remove();
}

// --- Select grids (Try It On tab): click to pick, no add/delete controls ---

function setupSelectGrid(gridId) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  const hiddenField = document.getElementById(grid.dataset.hiddenField);
  const toggle = grid.dataset.toggle === "true";

  grid.addEventListener("click", (event) => {
    const item = event.target.closest(".library-item");
    if (!item) return;

    const alreadySelected = item.classList.contains("selected");
    grid.querySelectorAll(".library-item.selected").forEach((el) => el.classList.remove("selected"));

    if (toggle && alreadySelected) {
      hiddenField.value = "";
    } else {
      item.classList.add("selected");
      hiddenField.value = item.dataset.id;
    }
    updateSubmitState();
  });

  // Auto-select the most recently added photo (first in the grid).
  if (!toggle) {
    const firstItem = grid.querySelector(".library-item");
    if (firstItem) {
      firstItem.classList.add("selected");
      hiddenField.value = firstItem.dataset.id;
    }
  }
}

function addToSelectGrid(gridId, entry) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  clearEmptyState(grid);
  const item = buildThumb(entry, { withDelete: false });
  grid.appendChild(item);

  // Non-toggle grids (your photo) auto-select the newest addition, same as on page load.
  if (grid.dataset.toggle !== "true") {
    grid.querySelectorAll(".library-item.selected").forEach((el) => el.classList.remove("selected"));
    item.classList.add("selected");
    const hiddenField = document.getElementById(grid.dataset.hiddenField);
    if (hiddenField) hiddenField.value = entry.id;
    updateSubmitState();
  }
}

function removeFromSelectGrid(gridId, id) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  const el = grid.querySelector(`.library-item[data-id="${id}"]`);
  if (!el) return;
  const wasSelected = el.classList.contains("selected");
  el.remove();
  if (wasSelected) {
    const hiddenField = document.getElementById(grid.dataset.hiddenField);
    if (hiddenField) {
      hiddenField.value = "";
      updateSubmitState();
    }
  }
}

// --- Manage grids (My Closet tab): add + delete, mirrored into the partner select grid ---

function setupManageGrid(gridId) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  const endpoint = grid.dataset.endpoint;
  const category = grid.dataset.category;
  const partnerId = grid.dataset.partner;
  const addInput = grid.querySelector(".library-add-input");

  grid.addEventListener("click", (event) => {
    const deleteBtn = event.target.closest(".delete-btn");
    if (!deleteBtn) return;
    const item = event.target.closest(".library-item");
    if (!confirm("Delete this photo?")) return;

    fetch(`${endpoint}/${item.dataset.id}`, { method: "DELETE" }).then((resp) => {
      if (!resp.ok) return;
      item.remove();
      removeFromSelectGrid(partnerId, item.dataset.id);
    });
  });

  addInput.addEventListener("change", async () => {
    const file = addInput.files[0];
    if (!file) return;

    let label = "";
    if (category) {
      label = prompt("Describe this item (optional):", "") || "";
    }

    const formData = new FormData();
    formData.append("image", file);
    if (label) formData.append("label", label);
    if (category) formData.append("category", category);

    statusEl.textContent = "Saving...";
    try {
      const resp = await fetch(endpoint, { method: "POST", body: formData });
      const entry = await resp.json();
      if (!resp.ok) {
        statusEl.classList.add("error");
        statusEl.textContent = entry.error || "Could not save image.";
        return;
      }
      grid.appendChild(buildThumb(entry, { withDelete: true }));
      addToSelectGrid(partnerId, entry);
      statusEl.textContent = "";
    } catch (err) {
      statusEl.classList.add("error");
      statusEl.textContent = `Upload failed: ${err.message}`;
    } finally {
      addInput.value = "";
    }
  });
}

["select-people", "select-top", "select-bottom", "select-shoes"].forEach(setupSelectGrid);
["manage-people", "manage-top", "manage-bottom", "manage-shoes"].forEach(setupManageGrid);
updateSubmitState();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  submitBtn.disabled = true;
  submitBtn.classList.add("loading");
  statusEl.classList.remove("error");
  statusEl.textContent = "Generating your outfit... this can take a couple of minutes for multiple items.";
  resultSection.classList.add("hidden");

  try {
    const response = await fetch("/try-on", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      statusEl.classList.add("error");
      statusEl.textContent = data.error || "Something went wrong.";
      return;
    }

    statusEl.textContent = "Done!";
    resultImg.src = data.image_url;
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    statusEl.classList.add("error");
    statusEl.textContent = `Request failed: ${err.message}`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
    updateSubmitState();
  }
});
