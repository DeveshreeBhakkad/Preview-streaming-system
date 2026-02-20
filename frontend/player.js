/**
 * Previewly Video Player
 * Handles video preview loading and playback
 */

// Wait for page to fully load
document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ Player.js loaded successfully");

  // Get HTML elements by their IDs
  const urlInput = document.getElementById("urlInput");
  const startBtn = document.getElementById("startBtn");
  const video = document.getElementById("video");
  const videoWrapper = document.getElementById("videoWrapper");
  const statusText = document.getElementById("status");

  // Global variables
  let hlsInstance = null;
  let currentPreviewId = null;

  /**
   * Update status message for user
   */
  function setStatus(message) {
    console.log(`[Status] ${message}`);
    statusText.textContent = message;
  }

  /**
   * Validate all required elements exist
   */
  if (!urlInput || !startBtn || !video || !videoWrapper || !statusText) {
    console.error("❌ Required HTML elements not found!");
    console.error("Missing:", {
      urlInput: !!urlInput,
      startBtn: !!startBtn,
      video: !!video,
      videoWrapper: !!videoWrapper,
      statusText: !!statusText
    });
    alert("Error: Page elements not found. Please refresh.");
    return;
  }

  console.log("✅ All HTML elements found");

  /**
   * Main function: Start video preview
   */
  startBtn.addEventListener("click", async () => {
    console.log("🎬 Preview button clicked");

    // Get URL from input box
    const videoUrl = urlInput.value?.trim();

    // Validate URL exists
    if (!videoUrl) {
      setStatus("⚠️ Please paste a video URL");
      return;
    }

    // Validate URL format
    if (!videoUrl.startsWith("http://") && !videoUrl.startsWith("https://")) {
      setStatus("⚠️ Invalid URL - must start with http:// or https://");
      return;
    }

    console.log(`📹 Video URL: ${videoUrl}`);

    // Show loading message
    setStatus("⏳ Preparing instant preview...");

    // Hide video player while loading
    videoWrapper.classList.add("hidden");

    // Cleanup previous HLS instance if exists
    if (hlsInstance) {
      console.log("🧹 Cleaning up previous HLS instance");
      hlsInstance.destroy();
      hlsInstance = null;
    }

    try {
      // Send request to backend to start preview
      console.log("📤 Sending request to backend...");
      
      const response = await fetch("/start-preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          url: videoUrl
        })
      });

      console.log(`📥 Backend response: ${response.status}`);

      // Check if request was successful
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start preview");
      }

      // Parse response data
      const data = await response.json();
      console.log("✅ Preview data received:", data);

      // Validate response has playlist URL
      if (!data.playlist_url) {
        throw new Error("No playlist URL in response");
      }

      // Store preview ID for later
      currentPreviewId = data.preview_id;

      // Show video player
      videoWrapper.classList.remove("hidden");

      // Initialize HLS video player
      console.log("🎥 Initializing HLS player...");
      initializeHLSPlayer(data.playlist_url);

    } catch (error) {
      console.error("❌ Error starting preview:", error);
      
      // Show user-friendly error message
      if (error.message.includes("fetch")) {
        setStatus("❌ Cannot connect to server. Is it running?");
      } else if (error.message.includes("timeout")) {
        setStatus("❌ Request timeout - video may be too large");
      } else {
        setStatus(`❌ Error: ${error.message}`);
      }
    }
  });

  /**
   * Initialize HLS.js video player
   */
  function initializeHLSPlayer(playlistUrl) {
    console.log(`🎬 Loading playlist: ${playlistUrl}`);

    // Check if HLS.js is supported
    if (window.Hls && Hls.isSupported()) {
      console.log("✅ HLS.js is supported");

      // Create new HLS instance
      hlsInstance = new Hls({
        debug: false,
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 30
      });

      // Load the playlist
      hlsInstance.loadSource(playlistUrl);

      // Attach to video element
      hlsInstance.attachMedia(video);

      // Event: Manifest (playlist) loaded successfully
      hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log("✅ HLS manifest parsed successfully");
        setStatus("✅ Preview ready — press play ▶️");
      });

      // Event: Error occurred
      hlsInstance.on(Hls.Events.ERROR, (event, data) => {
        console.error("❌ HLS error:", data);

        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.error("Fatal network error");
              setStatus("❌ Network error loading video");
              
              // Try to recover
              console.log("🔄 Attempting to recover...");
              hlsInstance.startLoad();
              break;

            case Hls.ErrorTypes.MEDIA_ERROR:
              console.error("Fatal media error");
              setStatus("❌ Media error - attempting recovery...");
              
              // Try to recover
              hlsInstance.recoverMediaError();
              break;

            default:
              console.error("Fatal error - cannot recover");
              setStatus("❌ Playback error");
              hlsInstance.destroy();
              break;
          }
        }
      });

      // Event: Level (quality) loaded
      hlsInstance.on(Hls.Events.LEVEL_LOADED, (event, data) => {
        console.log(`📊 Level loaded: ${data.details.totalduration}s duration`);
      });

    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native HLS support (Safari)
      console.log("✅ Native HLS support detected (Safari)");
      
      video.src = playlistUrl;
      
      video.addEventListener("loadedmetadata", () => {
        console.log("✅ Video metadata loaded");
        setStatus("✅ Preview ready — press play ▶️");
      });

      video.addEventListener("error", (e) => {
        console.error("❌ Video error:", e);
        setStatus("❌ Error loading video");
      });

    } else {
      // HLS not supported
      console.error("❌ HLS not supported in this browser");
      setStatus("❌ HLS not supported in this browser");
      alert("Your browser doesn't support HLS playback. Please use Chrome, Firefox, or Safari.");
    }
  }

 
  // When video is paused
  video.addEventListener("pause", () => {
    console.log("⏸️ Video paused");
    setStatus("⏸️ Paused");
  });

  // When video ends
  video.addEventListener("ended", () => {
    console.log("🏁 Video ended");
    setStatus("🏁 Preview ended");
  });

  // When video has an error
  video.addEventListener("error", (e) => {
    console.error("❌ Video element error:", e);
    
    const error = video.error;
    if (error) {
      let errorMessage = "Unknown error";
      
      switch (error.code) {
        case MediaError.MEDIA_ERR_ABORTED:
          errorMessage = "Playback aborted";
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          errorMessage = "Network error loading video";
          break;
        case MediaError.MEDIA_ERR_DECODE:
          errorMessage = "Video decoding error";
          break;
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMessage = "Video format not supported";
          break;
      }
      
      setStatus(`❌ ${errorMessage}`);
    }
  });

  /**
   * Cleanup when page is closed
   */
  window.addEventListener("beforeunload", () => {
    console.log("🧹 Page closing - cleaning up...");
    
    if (hlsInstance) {
      hlsInstance.destroy();
    }
    
    // Optionally notify backend to cleanup
    if (currentPreviewId) {
      fetch("/end-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preview_id: currentPreviewId }),
        keepalive: true
      }).catch(err => console.log("Cleanup notification failed:", err));
    }
  });

  console.log("✅ Player initialized successfully");
});