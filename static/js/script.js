const form = document.getElementById("try-on-form");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result");
const resultImg = document.getElementById("result-img");
const submitBtn = document.getElementById("submit-btn");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(form);
  submitBtn.disabled = true;
  statusEl.textContent = "Generating your try-on... this can take up to a minute.";
  resultSection.classList.add("hidden");

  try {
    const response = await fetch("/try-on", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      statusEl.textContent = data.error || "Something went wrong.";
      return;
    }

    statusEl.textContent = "Done!";
    resultImg.src = `/static/${data.result_image}`;
    resultSection.classList.remove("hidden");
  } catch (err) {
    statusEl.textContent = `Request failed: ${err.message}`;
  } finally {
    submitBtn.disabled = false;
  }
});
