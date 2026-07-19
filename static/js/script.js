const form = document.getElementById("try-on-form");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result");
const resultImg = document.getElementById("result-img");
const submitBtn = document.getElementById("submit-btn");

function setupDropzone(zoneId, previewId) {
  const zone = document.getElementById(zoneId);
  const preview = document.getElementById(previewId);
  const input = zone.querySelector("input[type=file]");

  function showPreview(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      preview.style.backgroundImage = `url(${e.target.result})`;
      preview.classList.add("has-preview");
      zone.classList.add("has-image");
      preview.querySelector(".dz-label").textContent = file.name;
    };
    reader.readAsDataURL(file);
  }

  input.addEventListener("change", () => showPreview(input.files[0]));

  ["dragenter", "dragover"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.add("drag-over");
    })
  );

  ["dragleave", "drop"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
    })
  );

  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) {
      input.files = e.dataTransfer.files;
      showPreview(file);
    }
  });
}

setupDropzone("person-dropzone", "person-preview");
setupDropzone("garment-dropzone", "garment-preview");

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
    resultImg.src = `/static/${data.result_image}`;
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    statusEl.classList.add("error");
    statusEl.textContent = `Request failed: ${err.message}`;
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove("loading");
  }
});
