from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import os

from backend.stream.buffer_manager import BufferManager

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HLS_DIR = os.path.join(BASE_DIR, "data", "hls")

app.mount(
    "/hls",
    StaticFiles(directory=HLS_DIR),
    name="hls"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# BASIC HEALTH CHECK (PHASE 2)
# -----------------------------
@app.get("/")
def home():
    return {"status": "Backend is running"}

from backend.stream.buffer_manager import BufferManager

@app.get("/debug-buffer")
def debug_buffer():
    bm = BufferManager()
    bm.initialize()
    return {
        "active_chunks": bm.get_active_chunks()
    }

# -----------------------------
# VIDEO CONFIG
# -----------------------------
VIDEO_PATH = "data/sample_video_frag.mp4"

BYTES_PER_CHUNK = 1024 * 1024  # 1 MB ≈ 30 sec (approx)


# -----------------------------
# BUFFER MANAGER INSTANCE
# -----------------------------
buffer_manager = BufferManager()


# -----------------------------
# CONTROLLED VIDEO STREAM
# -----------------------------
def controlled_video_stream():
    """
    Streams video using backend-controlled chunk buffer
    """
    buffer_manager.initialize()

    with open(VIDEO_PATH, "rb") as video:
        while True:
            active_chunks = buffer_manager.get_active_chunks()

            for chunk_id in active_chunks:
                start_byte = (chunk_id - 1) * BYTES_PER_CHUNK
                video.seek(start_byte)

                data = video.read(BYTES_PER_CHUNK)
                if not data:
                    return

                yield data

            buffer_manager.slide_forward()


# -----------------------------
# CONTROLLED STREAM ENDPOINT
# -----------------------------
@app.get("/video-controlled")
def stream_video_controlled():
    return StreamingResponse(
        controlled_video_stream(),
        media_type="video/mp4"
    )
