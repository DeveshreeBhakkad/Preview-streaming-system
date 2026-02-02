## 📽️ Previewly ⚡

>  Instant Video Preview System (Backend-Controlled Streaming)

Previewly is a backend-driven video preview platform that allows users to instantly preview large downloadable videos without waiting for full downloads.

The system focuses on how real streaming platforms work internally buffering, chunking, adaptive logic, and controlled playback rather than just playing a video.

---

## 🚀 Key Highlights

- 🔗 Paste any direct downloadable video URL
- ⚡ Start watching immediately
- ⏪ Limited rewind using backend-controlled buffer window
- 🧠 ML-assisted adaptive buffering based on network conditions
- 📦 Backend decides which chunks exist (not the browser)
- 🌐 HLS-based streaming for full playback support
- 🧠 System Architecture (High Level)

---

## Tech 

- Frontend: HTML, CSS, JS, HLS.js
- Backend: FastAPI
- Streaming Logic:
 - Chunk-based streaming
 - Sliding window buffer
 - ML-driven forward buffer prediction
- Media Format: HLS (.m3u8 + .ts segments)

---

## 🛠️ Project Status

This project is being developed incrementally as a portfolio-grade system to understand real-world streaming architectures.

---

## Completed

- Backend-controlled chunk streaming
- Sliding window buffer (limited rewind)
- ML-based adaptive forward buffering
- HLS generation & playback
- Remote URL preview streaming
- Preview-focused UI (Preview Mode)

---

## In Progress

- Strict rewind enforcement at player level
- Session-based preview isolation
- Network-aware chunk throttling
- UI polish & transitions

---

## ⚠️ Note on Media Files

Sample media files are used only for local testing.
They are not part of the core system and may be removed or replaced in future commits.

---

## 🎯 Why This Project?

Most video players rely entirely on the browser.
Previewly demonstrates how streaming platforms control playback from the backend, which is critical for:
  - Previews
  - Paywalls
  - DRM-like behavior
  - Bandwidth control
  - Cost optimization

---

## 🧪 Intended Use

- Learning distributed streaming systems
- Demonstrating backend + ML integration
- Recruiter-facing portfolio project

💡 This project prioritizes system design, control, and architecture over simple video playback.
