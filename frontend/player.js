/**
 * Previewly - Video Player Script
 * Handles HLS video playback with progressive loading
 */

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ Player.js loaded successfully");

  // Get DOM elements
  const urlInput = document.getElementById("urlInput");
  const startBtn = document.getElementById("startBtn");
  const video = document.getElementById("video");
  const videoWrapper = document.getElementById("videoWrapper");
  const statusText = document.getElementById("status");

  // Global variables
  let hlsInstance = null;
  let currentPreviewId = null;

  // Helper function to update status message
  function setStatus(message) {
    statusText.textContent = message;
  }

  // Verify all elements exist
  if (!urlInput || !startBtn || !video || !videoWrapper || !statusText) {
    console.error("❌ Some HTML elements not found!");
    return;
  }
  console.log("✅ All HTML elements found");

  // Button click handler
  startBtn.addEventListener("click", async () => {
    const videoUrl = urlInput.value.trim();

    // Validate URL
    if (!videoUrl) {
      setStatus("❌ Please enter a video URL");
      return;
    }

    if (!videoUrl.startsWith("http://") && !videoUrl.startsWith("https://")) {
      setStatus("❌ URL must start with http:// or https://");
      return;
    }

    // Update UI
    setStatus("⏳ Preparing instant preview...");
    videoWrapper.classList.add("hidden");

    // Cleanup previous HLS instance
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }

    try {
      // Send request to backend
      console.log("📤 Sending request to backend...");
      const response = await fetch("/start-preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: videoUrl }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to start preview");
      }

      console.log("✅ Backend response:", data);

      // Get playlist URL
      const playlistUrl = data.playlist_url;
      currentPreviewId = data.preview_id;

      // Show video wrapper
      videoWrapper.classList.remove("hidden");

      // Initialize HLS player
      initializeHLSPlayer(playlistUrl);

      setStatus(`✅ Preview ready — press play ▶️`);
    } catch (error) {
      console.error("❌ Error:", error);
      setStatus(`❌ Error: ${error.message}`);
    }
  });

  // Initialize HLS.js player
  function initializeHLSPlayer(playlistUrl) {
    console.log("🎬 Initializing HLS player...");
    console.log("📺 Playlist URL:", playlistUrl);

    if (Hls.isSupported()) {
      // Create HLS instance
      hlsInstance = new Hls({
        debug: false,
        enableWorker: true,
        lowLatencyMode: false,
      });

      // Load the playlist
      hlsInstance.loadSource(playlistUrl);
      hlsInstance.attachMedia(video);

      // Handle HLS events
      hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log("✅ Playlist loaded successfully");
        setStatus("✅ Video ready — press play ▶️");
      });

      hlsInstance.on(Hls.Events.ERROR, (event, data) => {
        console.error("❌ HLS Error:", data);

        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log("🔄 Network error, attempting to recover...");
              hlsInstance.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log("🔄 Media error, attempting to recover...");
              hlsInstance.recoverMediaError();
              break;
            default:
              console.error("💥 Fatal error, cannot recover");
              setStatus("❌ Playback error occurred");
              hlsInstance.destroy();
              break;
          }
        }
      });

      hlsInstance.on(Hls.Events.LEVEL_LOADED, (event, data) => {
        console.log(`📊 Loaded ${data.details.fragments.length} segments`);
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native HLS support (Safari)
      console.log("🍎 Using native HLS support");
      video.src = playlistUrl;
      setStatus("✅ Video ready — press play ▶️");
    } else {
      console.error("❌ HLS not supported in this browser");
      setStatus("❌ Your browser doesn't support HLS playback");
    }
  }

  // Video event listeners
  video.addEventListener("play", () => {
    console.log("▶️ Video playing");
    setStatus("▶️ Playing...");
  });

  video.addEventListener("pause", () => {
    console.log("⏸️ Video paused");
    setStatus("⏸️ Paused");
  });

  video.addEventListener("ended", () => {
    console.log("✅ Video ended");
    setStatus("✅ Video finished");
  });

  video.addEventListener("error", (e) => {
    console.error("❌ Video error:", e);
    const errorCode = video.error ? video.error.code : "unknown";
    const errorMessage = {
      1: "Video loading aborted",
      2: "Network error while loading video",
      3: "Video decoding failed",
      4: "Video format not supported",
    }[errorCode] || "Unknown video error";
    
    setStatus(`❌ ${errorMessage}`);
  });

  // Cleanup on page unload
  window.addEventListener("beforeunload", () => {
    if (hlsInstance) {
      hlsInstance.destroy();
    }

    // Notify backend to cleanup
    if (currentPreviewId) {
      fetch("/end-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preview_id: currentPreviewId }),
        keepalive: true,
      }).catch((err) => console.log("Cleanup notification failed:", err));
    }
  });

  console.log("✅ Player initialized successfully");
});