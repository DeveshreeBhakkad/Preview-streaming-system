const hero = document.getElementById("hero");
const overlay = document.getElementById("playerOverlay");
const video = document.getElementById("video");

const startBtn = document.getElementById("startBtn");
const exitBtn = document.getElementById("exitBtn");
const statusText = document.getElementById("status");
const linkInput = document.getElementById("videoLink");

startBtn.addEventListener("click", () => {
  const url = linkInput.value.trim();

  if (!url) {
    alert("Please paste a video link first.");
    return;
  }

  /* Hero exit animation */
  hero.style.opacity = "0";
  hero.style.transform = "translateY(20px) scale(0.97)";

  setTimeout(() => {
    hero.classList.add("hidden");

    overlay.classList.remove("hidden");
    requestAnimationFrame(() => {
      overlay.style.opacity = "1";
    });

    statusText.textContent = "Preview playing…";
    video.controls = false;   // important for later rewind control
    video.src = url;
  }, 450);
});

exitBtn.addEventListener("click", () => {
  video.pause();
  video.src = "";

  overlay.style.opacity = "0";

  setTimeout(() => {
    overlay.classList.add("hidden");

    hero.classList.remove("hidden");
    hero.style.opacity = "1";
    hero.style.transform = "none";
  }, 450);
});
