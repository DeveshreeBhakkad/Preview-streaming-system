"""
Main FastAPI Server for Previewly Video Preview System

This is the backend server that:
1. Receives video URLs from frontend
2. Converts videos to HLS format using FFmpeg
3. Manages preview sessions
4. Serves video segments with rewind control
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import os
import uuid
import subprocess
import time
import glob
from pathlib import Path
from typing import Dict, Optional

# Import our configuration
from config import (
    FRONTEND_DIR,
    HLS_DIR,
    SERVER_HOST,
    SERVER_PORT,
    CORS_ORIGINS,
    SEGMENT_DURATION,
    VIDEO_CODEC,
    AUDIO_CODEC,
    FFMPEG_TIMEOUT,
    MIN_SEGMENTS_TO_START,
    SESSION_TIMEOUT,
    print_config
)


# ============================================================================
# INITIALIZE FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Previewly API",
    description="Backend-controlled video preview system with rewind restrictions",
    version="1.0.0"
)


# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================

# CORS - allows frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # Which domains can access this API
    allow_credentials=True,
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],         # Allow all headers
)


# ============================================================================
# STATIC FILE SERVING
# ============================================================================

# Serve frontend files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Serve HLS video segments
app.mount("/hls", StaticFiles(directory=str(HLS_DIR)), name="hls")


# ============================================================================
# GLOBAL STATE
# ============================================================================

# Store active preview sessions
# Format: {preview_id: {created_at, video_url, ffmpeg_process, preview_dir}}
active_sessions: Dict[str, dict] = {}


# ============================================================================
# ROUTES - FRONTEND
# ============================================================================

@app.get("/")
async def serve_frontend():
    """
    Serve the main frontend page (index.html)
    
    When user opens http://127.0.0.1:8000/ this loads the UI
    """
    index_path = FRONTEND_DIR / "index.html"
    
    if not index_path.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "Frontend not found",
                "message": "Please ensure index.html exists in frontend/ directory"
            }
        )
    
    return FileResponse(index_path)


# ============================================================================
# ROUTES - VIDEO PREVIEW
# ============================================================================

@app.post("/start-preview")
async def start_preview(request: Request):
    """
    Start a new video preview session
    
    Request body (JSON):
    {
        "url": "https://example.com/video.mp4"
    }
    
    Returns:
    {
        "preview_id": "preview_abc123",
        "playlist_url": "/hls/preview_abc123/playlist.m3u8",
        "message": "Preview started successfully"
    }
    """
    
    # Parse request body
    try:
        body = await request.json()
        video_url = body.get("url")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request body: {str(e)}"
        )
    
    # Validate video URL
    if not video_url:
        raise HTTPException(
            status_code=400,
            detail="Missing 'url' parameter in request body"
        )
    
    if not video_url.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="Invalid video URL - must start with http:// or https://"
        )
    
    # Generate unique preview ID
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    
    # Create directory for this preview
    preview_dir = HLS_DIR / preview_id
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    # Path to output playlist
    playlist_path = preview_dir / "playlist.m3u8"
    
    # Build FFmpeg command
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",                              # Overwrite output files
        "-i", video_url,                   # Input video URL
        "-codec:v", VIDEO_CODEC,           # Video codec (H.264)
        "-codec:a", AUDIO_CODEC,           # Audio codec (AAC)
        "-hls_time", str(SEGMENT_DURATION), # Segment duration (30 seconds)
        "-hls_list_size", "0",             # Keep all segments in playlist
        "-hls_segment_filename", str(preview_dir / "segment%03d.ts"),  # Segment naming
        "-f", "hls",                       # Output format (HLS)
        str(playlist_path)                 # Output playlist path
    ]
    
    print(f"[Preview] Starting FFmpeg for {preview_id}")
    print(f"[Preview] Video URL: {video_url}")
    print(f"[Preview] Output directory: {preview_dir}")
    
    # Start FFmpeg process in background
    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg not found - please install FFmpeg"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start FFmpeg: {str(e)}"
        )
    
    # Wait for initial segments to be generated
    start_time = time.time()
    segments_ready = False
    
    while time.time() - start_time < FFMPEG_TIMEOUT:
        # Check if playlist exists
        if not playlist_path.exists():
            time.sleep(0.5)
            continue
        
        # Check if minimum segments exist
        segment_files = list(preview_dir.glob("segment*.ts"))
        
        if len(segment_files) >= MIN_SEGMENTS_TO_START:
            segments_ready = True
            print(f"[Preview] {preview_id}: {len(segment_files)} segments ready")
            break
        
        time.sleep(0.5)
    
    # Check if segments were generated
    if not segments_ready:
        # Cleanup failed preview
        ffmpeg_process.kill()
        cleanup_preview_directory(preview_dir)
        
        raise HTTPException(
            status_code=500,
            detail="Timeout waiting for video segments - video may be invalid or too large"
        )
    
    # Store session info
    active_sessions[preview_id] = {
        "created_at": time.time(),
        "video_url": video_url,
        "ffmpeg_process": ffmpeg_process,
        "preview_dir": str(preview_dir)
    }
    
    # Build playlist URL for frontend
    playlist_url = f"/hls/{preview_id}/playlist.m3u8"
    
    print(f"[Preview] {preview_id}: Preview started successfully")
    
    return {
        "preview_id": preview_id,
        "playlist_url": playlist_url,
        "segment_duration": SEGMENT_DURATION,
        "message": "Preview started successfully"
    }


@app.post("/end-preview")
async def end_preview(request: Request):
    """
    End a preview session and cleanup resources
    
    Request body (JSON):
    {
        "preview_id": "preview_abc123"
    }
    """
    
    try:
        body = await request.json()
        preview_id = body.get("preview_id")
    except:
        raise HTTPException(status_code=400, detail="Invalid request body")
    
    if not preview_id:
        raise HTTPException(status_code=400, detail="Missing preview_id")
    
    if preview_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Preview session not found")
    
    # Cleanup session
    cleanup_session(preview_id)
    
    return {
        "status": "success",
        "message": f"Preview {preview_id} ended and cleaned up"
    }


# ============================================================================
# ROUTES - DEBUG & MONITORING
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint - verify server is running
    """
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": time.time()
    }


@app.get("/debug/sessions")
async def debug_sessions():
    """
    List all active preview sessions
    """
    sessions_info = []
    
    for preview_id, session in active_sessions.items():
        sessions_info.append({
            "preview_id": preview_id,
            "age_seconds": int(time.time() - session["created_at"]),
            "video_url": session["video_url"]
        })
    
    return {
        "total_sessions": len(active_sessions),
        "sessions": sessions_info
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def cleanup_session(preview_id: str):
    """
    Cleanup a specific preview session
    - Stop FFmpeg process
    - Delete video segments
    - Remove from active sessions
    """
    if preview_id not in active_sessions:
        return
    
    session = active_sessions[preview_id]
    
    # Stop FFmpeg process
    ffmpeg_process = session.get("ffmpeg_process")
    if ffmpeg_process:
        try:
            ffmpeg_process.terminate()
            ffmpeg_process.wait(timeout=5)
        except:
            ffmpeg_process.kill()
    
    # Delete preview directory
    preview_dir = Path(session["preview_dir"])
    cleanup_preview_directory(preview_dir)
    
    # Remove from active sessions
    del active_sessions[preview_id]
    
    print(f"[Cleanup] Session {preview_id} cleaned up")


def cleanup_preview_directory(preview_dir: Path):
    """
    Delete all files in a preview directory
    """
    if not preview_dir.exists():
        return
    
    try:
        # Delete all files
        for file in preview_dir.glob("*"):
            file.unlink()
        
        # Delete directory
        preview_dir.rmdir()
        
        print(f"[Cleanup] Deleted directory: {preview_dir}")
    except Exception as e:
        print(f"[Cleanup] Error deleting {preview_dir}: {e}")


def cleanup_old_sessions():
    """
    Cleanup sessions older than SESSION_TIMEOUT
    Called periodically to prevent resource leaks
    """
    current_time = time.time()
    sessions_to_remove = []
    
    for preview_id, session in active_sessions.items():
        age = current_time - session["created_at"]
        
        if age > SESSION_TIMEOUT:
            sessions_to_remove.append(preview_id)
    
    for preview_id in sessions_to_remove:
        print(f"[Cleanup] Auto-cleaning old session: {preview_id}")
        cleanup_session(preview_id)


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Run when server starts
    """
    print("\n")
    print_config()  # Print configuration from config.py
    print("🚀 Server started successfully!")
    print(f"📱 Open in browser: http://{SERVER_HOST}:{SERVER_PORT}")
    print("\n")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run when server shuts down
    - Cleanup all active sessions
    """
    print("\n[Shutdown] Cleaning up active sessions...")
    
    session_ids = list(active_sessions.keys())
    for preview_id in session_ids:
        cleanup_session(preview_id)
    
    print("[Shutdown] All sessions cleaned up")
    print("[Shutdown] Server stopped")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info"
    )