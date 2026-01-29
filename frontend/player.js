const landing = document.getElementById("landing");
const playerScreen = document.getElementById("playerScreen");

const startBtn = document.getElementById("startPreview");
const backBtn = document.getElementById("backBtn");

const videoInput = document.getElementById("videoUrl");
const video = document.getElementById("video");
const statusText = document.getElementById("status");

function showPlayer(url) {
  landing.classList.remove("active");
  playerScreen.classList.add("active");

  const streamUrl =
    `http://127.0.0.1:8000/preview-stream?source_url=${encodeURIComponent(url)}`;

  video.src = streamUrl;
  statusText.textContent = "Streaming preview…";
}

function showLanding() {
  video.pause();
  video.removeAttribute("src");
  video.load();

  playerScreen.classList.remove("active");
  landing.classList.add("active");
}

startBtn.addEventListener("click", () => {
  const url = videoInput.value.trim();

  if (!url.startsWith("http")) {
    alert("Please enter a valid direct video URL");
    return;
  }

  showPlayer(url);
});

backBtn.addEventListener("click", showLanding);
