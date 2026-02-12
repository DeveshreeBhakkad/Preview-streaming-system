from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import os
import uuid
import subprocess
import time
import glob

from backend.stream.stream_controller import StreamController
from backend.stream.buffer_manager import BufferManager

# -----------------------------
# APP INIT
# -----------------------------
app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR = os.path.join(BASE_DIR, "data")
HLS_DIR = os.path.join(DATA_DIR, "hls")

os.makedirs(HLS_DIR, exist_ok=True)

# -----------------------------
# STATIC FILES
# -----------------------------
# Frontend
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# HLS output
app.mount("/hls", StaticFiles(directory=HLS_DIR), name="hls")

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# FRONTEND ENTRY POINT
# -----------------------------
@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# -----------------------------
# DEBUG BUFFER (DEV)
# -----------------------------
@app.get("/debug-buffer")
def debug_buffer():
    bm = BufferManager()
    bm.initialize()
    return {"active_chunks": bm.get_active_chunks()}

# -----------------------------
# RAW MP4 PREVIEW (OPTIONAL)
# -----------------------------


# -----------------------------
# HLS PREVIEW (CORE FEATURE)
# -----------------------------
@app.post("/start-hls-preview")
async def start_hls_preview(request: Request):
    body = await request.json()
    video_url = body.get("url")

    if not video_url or not video_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    preview_dir = os.path.join(HLS_DIR, preview_id)
    os.makedirs(preview_dir, exist_ok=True)

    playlist_path = os.path.join(preview_dir, "playlist.m3u8")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", video_url,
        "-codec:v", "libx264",
        "-codec:a", "aac",
        "-hls_time", "10",
        "-hls_list_size", "0",
        "-f", "hls",
        playlist_path
    ]

    subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # ---- WAIT FOR SEGMENTS ----
    timeout = 20
    start = time.time()

    while True:
        ts_files = glob.glob(os.path.join(preview_dir, "*.ts"))
        if len(ts_files) >= 2:
            break

        if time.time() - start > timeout:
            raise HTTPException(
                status_code=500,
                detail="HLS generation timeout"
            )

        time.sleep(0.5)

    playlist_url = f"/hls/{preview_id}/playlist.m3u8"

    return {
        "playlist_url": playlist_url
    }
