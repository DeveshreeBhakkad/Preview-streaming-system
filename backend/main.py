from fastapi import FastAPI


app = FastAPI()

@app.get("/")
def home():
    return {"message": "Backend is running"}

import time
from fastapi.responses import StreamingResponse


def text_stream():
    for i in range(1, 6):
        time.sleep(1)
        yield f"Chunk {i}\n"


@app.get("/stream")
def stream_text():
    return StreamingResponse(
        text_stream(),
        media_type="text/plain"
    )
