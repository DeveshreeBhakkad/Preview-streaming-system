const video = document.getElementById("video");
const statusText = document.getElementById("status");

// Backend HLS playlist
const HLS_URL = "http://127.0.0.1:8000/hls/playlist.m3u8";

function setStatus(msg) {
  statusText.textContent = msg;
}

if (Hls.isSupported()) {
  const hls = new Hls({
    enableWorker: true,
    lowLatencyMode: false,
  });

  setStatus("Loading HLS stream…");

  hls.loadSource(HLS_URL);
  hls.attachMedia(video);

  hls.on(Hls.Events.MANIFEST_PARSED, () => {
    setStatus("Stream ready — press play");
  });

  hls.on(Hls.Events.ERROR, (event, data) => {
    console.error("HLS error:", data);

    if (data.fatal) {
      switch (data.type) {
        case Hls.ErrorTypes.NETWORK_ERROR:
          setStatus("Network error — retrying…");
          hls.startLoad();
          break;

        case Hls.ErrorTypes.MEDIA_ERROR:
          setStatus("Media error — attempting recovery…");
          hls.recoverMediaError();
          break;

        default:
          setStatus("Fatal error — reload page");
          hls.destroy();
          break;
      }
    }
  });

} else if (video.canPlayType("application/vnd.apple.mpegurl")) {
  // Safari fallback
  video.src = HLS_URL;
  setStatus("Native HLS support detected");

} else {
  setStatus("HLS not supported in this browser");
}
