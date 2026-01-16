from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import time
import os

app = FastAPI()


# -----------------------------
# BASIC HEALTH CHECK (PHASE 2)
# -----------------------------
@app.get("/")
def home():
    return {"status": "Backend is running"}


# -----------------------------
# TEXT STREAMING (PHASE 2)
# -----------------------------
def text_stream():
    """
    Generator that streams text chunks one by one.
    Used only to understand streaming behavior.
    """
    for i in range(1, 6):
        time.sleep(1)  # simulate delay
        yield f"Chunk {i}\n"


@app.get("/stream-text")
def stream_text():
    """
    Streams text data gradually to the browser.
    """
    return StreamingResponse(
        text_stream(),
        media_type="text/plain"
    )


# -----------------------------
# VIDEO STREAMING (PHASE 3)
# -----------------------------
VIDEO_PATH = "data/sample_video.mp4"


def video_stream():
    """
    Generator that reads a video file in binary chunks
    and streams it without full download.
    """
    with open(VIDEO_PATH, "rb") as video:
        while True:
            chunk = video.read(1024 * 1024)  # 1 MB chunks
            if not chunk:
                break
            yield chunk


@app.get("/video")
def stream_video():
    """
    Streams the video file to the browser.
    """
    return StreamingResponse(
        video_stream(),
        media_type="video/mp4"
    )

    
