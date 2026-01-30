const urlInput = document.getElementById("urlInput");
const startBtn = document.getElementById("startBtn");
const video = document.getElementById("video");
const wrapper = document.getElementById("videoWrapper");
const statusText = document.getElementById("status");

function setStatus(msg) {
  statusText.textContent = msg;
}

startBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  if (!url) return;

  setStatus("Preparing instant preview…");

  const res = await fetch("http://127.0.0.1:8000/start-hls-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });

  const data = await res.json();

  if (!data.playlist_url) {
    setStatus("Failed to load preview");
    return;
  }

  wrapper.classList.remove("hidden");

  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(data.playlist_url);
    hls.attachMedia(video);

    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      video.play();
      setStatus("Streaming preview ⚡");
    });
  } else {
    video.src = data.playlist_url;
    video.play();
  }
});
