const form = document.getElementById("try-on-form");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result");
const resultImg = document.getElementById("result-img");
const submitBtn = document.getElementById("submit-btn");
const garmentDescInput = document.getElementById("garment_desc");

function updateSubmitState() {
  const personId = document.getElementById("person_id").value;
  const garmentId = document.getElementById("garment_id").value;
  submitBtn.disabled = !personId || !garmentId;
}

function setupLibrary(gridId) {
  const grid = document.getElementById(gridId);
  const endpoint = grid.dataset.endpoint;
  const hiddenField = document.getElementById(grid.dataset.hiddenField);
  const addInput = grid.querySelector(".library-add-input");

  function selectItem(itemEl) {
    grid.querySelectorAll(".library-item").forEach((el) => el.classList.remove("selected"));
    itemEl.classList.add("selected");
    hiddenField.value = itemEl.dataset.id;
    if (gridId === "garments-grid" && itemEl.dataset.label) {
      garmentDescInput.value = itemEl.dataset.label;
    }
    updateSubmitState();
  }

  function buildItem(entry) {
    const item = document.createElement("div");
    item.className = "library-item";
    item.dataset.id = entry.id;
    item.dataset.label = entry.label || "";

    const img = document.createElement("img");
    img.src = entry.image_url;
    img.alt = entry.label || "";
    item.appendChild(img);

    const del = document.createElement("button");
    del.type = "button";
    del.className = "delete-btn";
    del.title = "Delete";
    del.textContent = "×";
    item.appendChild(del);

    return item;
  }

  grid.addEventListener("click", (event) => {
    const deleteBtn = event.target.closest(".delete-btn");
    const item = event.target.closest(".library-item");
    if (!item) return;

    if (deleteBtn) {
      if (!confirm("Delete this photo?")) return;
      fetch(`${endpoint}/${item.dataset.id}`, { method: "DELETE" }).then((resp) => {
        if (!resp.ok) return;
        const wasSelected = item.classList.contains("selected");
        item.remove();
        if (wasSelected) {
          hiddenField.value = "";
          updateSubmitState();
        }
      });
      return;
    }

    selectItem(item);
  });

  addInput.addEventListener("change", async () => {
    const file = addInput.files[0];
    if (!file) return;

    let label = "";
    if (gridId === "garments-grid") {
      label = prompt("Describe this garment (optional):", "") || "";
    }

    const formData = new FormData();
    formData.append("image", file);
    if (label) formData.append("label", label);

    statusEl.textContent = "Saving...";
    try {
      const resp = await fetch(endpoint, { method: "POST", body: formData });
      const entry = await resp.json();
      if (!resp.ok) {
        statusEl.classList.add("error");
        statusEl.textContent = entry.error || "Could not save image.";
        return;
      }
      const item = buildItem(entry);
      grid.appendChild(item);
      selectItem(item);
      statusEl.textContent = "";
    } catch (err) {
      statusEl.classList.add("error");
      statusEl.textContent = `Upload failed: ${err.message}`;
    } finally {
      addInput.value = "";
    }
  });

  // Auto-select the most recently added item (first in the grid) on load.
  const firstItem = grid.querySelector(".library-item");
  if (firstItem) selectItem(firstItem);
}

setupLibrary("people-grid");
setupLibrary("garments-grid");
updateSubmitState();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  submitBtn.disabled = true;
  submitBtn.classList.add("loading");
  statusEl.classList.remove("error");
  statusEl.textContent = "Generating your try-on... this can take up to a minute.";
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
