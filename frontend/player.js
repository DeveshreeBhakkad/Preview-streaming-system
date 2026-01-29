const video = document.getElementById("video");
const startBtn = document.getElementById("startBtn");
const urlInput = document.getElementById("videoUrl");
const statusText = document.getElementById("status");
const wrapper = document.getElementById("videoWrapper");

const BACKEND_BASE = "http://127.0.0.1:8000";

function setStatus(msg) {
  statusText.textContent = msg;
}

startBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();

  if (!url) {
    setStatus("Please paste a valid video URL");
    return;
  }

  setStatus("Initializing preview…");
  wrapper.classList.remove("hidden");

  // Directly assign streaming endpoint
  video.src = `${BACKEND_BASE}/start-preview?url=${encodeURIComponent(url)}`;
  video.load();

  setStatus("Preview streaming started ⚡");
});
