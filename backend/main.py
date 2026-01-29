from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

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


@app.post("/start-preview")
async def start_preview(request: Request):
    body = await request.json()
    video_url = body.get("url")

    if not video_url or not video_url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid or missing video URL")

    controller = StreamController(
        video_url=video_url,
        chunk_size=CHUNK_SIZE
    )

    return StreamingResponse(
        controller.stream(),
        media_type="video/mp4"
    )
