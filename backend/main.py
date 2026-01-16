from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import os

from backend.stream.buffer_manager import BufferManager

app = FastAPI()

# -----------------------------
# BASIC HEALTH CHECK (PHASE 2)
# -----------------------------
@app.get("/")
def home():
    return {"status": "Backend is running"}


# -----------------------------
# VIDEO CONFIG
# -----------------------------
VIDEO_PATH = "data/sample_video.mp4"
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
