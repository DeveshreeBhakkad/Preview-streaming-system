from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.stream.stream_controller import StreamController
from backend.stream.buffer_manager import BufferManager

import os
import uuid
import subprocess
import time

app = FastAPI()

# -----------------------------
# PATHS
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HLS_DIR = os.path.join(BASE_DIR, "data", "hls")
os.makedirs(HLS_DIR, exist_ok=True)
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

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
# HEALTH CHECK
# -----------------------------
@app.get("/")
def serve_frontend():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# -----------------------------
# DEBUG BUFFER (DEV ONLY)
# -----------------------------
@app.get("/debug-buffer")
def debug_buffer():
    bm = BufferManager()
    bm.initialize()
    return {"active_chunks": bm.get_active_chunks()}

# -----------------------------
# RAW STREAM (EXPERIMENTAL)
# -----------------------------
CHUNK_SIZE = 1024 * 1024  # 1 MB

@app.get("/start-preview")
def start_preview(url: str = Query(...)):
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    controller = StreamController(
        video_url=url,
        chunk_size=CHUNK_SIZE
    )

    return StreamingResponse(
        controller.stream(),
        media_type="video/mp4"
    )

# -----------------------------
# HLS PREVIEW (REAL SYSTEM)
# -----------------------------
@app.post("/start-hls-preview")
async def start_hls_preview(request: Request):
    body = await request.json()
    video_url = body.get("url")

    if not video_url or not video_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid video URL")

    # Unique preview folder
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    preview_dir = os.path.join(HLS_DIR, preview_id)
    os.makedirs(preview_dir, exist_ok=True)

    playlist_path = os.path.join(preview_dir, "playlist.m3u8")

    # FFmpeg command
    cmd = [
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

    # Start FFmpeg
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # -----------------------------
    # WAIT UNTIL PLAYLIST IS READY
    # -----------------------------
    timeout = 15  # seconds
    start_time = time.time()

    while True:
        if os.path.exists(playlist_path):
            with open(playlist_path, "r") as f:
                content = f.read()
                if ".ts" in content:
                    break

        if time.time() - start_time > timeout:
            raise HTTPException(
                status_code=500,
                detail="HLS generation timeout"
            )

        time.sleep(0.5)

    playlist_url = f"http://127.0.0.1:8000/hls/{preview_id}/playlist.m3u8"

    return {
        "playlist_url": playlist_url
    }

from fastapi.responses import FileResponse

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)
