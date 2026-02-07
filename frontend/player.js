document.addEventListener("DOMContentLoaded", () => {
  console.log("player.js loaded");

  const urlInput = document.getElementById("urlInput");
  const startBtn = document.getElementById("startBtn");
  const video = document.getElementById("video");
  const wrapper = document.getElementById("videoWrapper");
  const statusText = document.getElementById("status");

  function setStatus(msg) {
    statusText.textContent = msg;
  }

  if (!urlInput) {
    console.error("❌ Input with id='urlInput' not found");
    setStatus("Internal UI error: input not found");
    return;
  }

  if (!startBtn) {
    console.error("❌ Button with id='startBtn' not found");
    setStatus("Internal UI error: button not found");
    return;
  }

  startBtn.addEventListener("click", async () => {
    console.log("Preview button clicked");

    const url = urlInput.value?.trim();
    if (!url) {
      setStatus("Please paste a video URL");
      return;
    }

    setStatus("Preparing instant preview…");

    let res;
    try {
      res = await fetch("/start-hls-preview", ... {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
    } catch (err) {
      console.error(err);
      setStatus("Backend not reachable");
      return;
    }

    const data = await res.json();

    if (!data.playlist_url) {
      setStatus("Failed to load preview");
      return;
    }

    wrapper.classList.remove("hidden");

    if (window.Hls && Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(data.playlist_url);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setStatus("Preview ready — press play ▶️");
     });

    } else {
      video.src = data.playlist_url;
      video.play();
      setStatus("Streaming preview ⚡");
    }
  });
});
