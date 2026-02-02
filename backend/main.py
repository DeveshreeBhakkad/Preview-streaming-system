from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.utils.hls_generator import generate_hls_from_url
from fastapi import FastAPI, Request, HTTPException
import uuid
import subprocess

from backend.stream.stream_controller import StreamController
from backend.stream.buffer_manager import BufferManager

import os

app = FastAPI()

# -----------------------------
# STATIC FILES (HLS - optional)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HLS_DIR = os.path.join(BASE_DIR, "data", "hls")

if os.path.exists(HLS_DIR):
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
def home():
    return {"status": "Backend is running"}

# -----------------------------
# DEBUG BUFFER (DEV ONLY)
# -----------------------------
@app.get("/debug-buffer")
def debug_buffer():
    bm = BufferManager()
    bm.initialize()
    return {"active_chunks": bm.get_active_chunks()}

# -----------------------------
# PREVIEW STREAM (CORE API)
# -----------------------------
CHUNK_SIZE = 1024 * 1024  # 1 MB per chunk


from fastapi import Query

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

    # FFmpeg command (HLS generation)
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

    try:
        subprocess.Popen(cmd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    playlist_url = f"http://127.0.0.1:8000/hls/{preview_id}/playlist.m3u8"

    return {
        "playlist_url": playlist_url
    }
