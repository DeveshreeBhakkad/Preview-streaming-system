"""
Main FastAPI Server for Previewly Video Preview System
PROGRESSIVE LOADING MODE - Start playing immediately!
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
import threading
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
    description="Backend-controlled video preview system with progressive loading",
    version="1.0.0"
)


# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# STATIC FILE SERVING
# ============================================================================

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/hls", StaticFiles(directory=str(HLS_DIR)), name="hls")


# ============================================================================
# GLOBAL STATE
# ============================================================================

active_sessions: Dict[str, dict] = {}


# ============================================================================
# ROUTES - FRONTEND
# ============================================================================

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    index_path = FRONTEND_DIR / "index.html"
    
    if not index_path.exists():
        return JSONResponse(
            status_code=404,
            content={
                "error": "Frontend not found",
                "message": "index.html not found"
            }
        )
    
    return FileResponse(index_path)


# ============================================================================
# ROUTES - VIDEO PREVIEW (PROGRESSIVE MODE)
# ============================================================================

@app.post("/start-preview")
async def start_preview(request: Request):
    """
    Start video preview - PROGRESSIVE MODE
    Returns after first segment, continues encoding in background
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
            detail="Missing 'url' parameter"
        )
    
    if not video_url.startswith("http"):
        raise HTTPException(
            status_code=400,
            detail="URL must start with http:// or https://"
        )
    
    # Generate unique preview ID
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    
    # Create directory
    preview_dir_str = os.path.join(str(HLS_DIR), preview_id)
    os.makedirs(preview_dir_str, exist_ok=True)
    
    # Define paths
    playlist_path_str = os.path.join(preview_dir_str, "playlist.m3u8")
    segment_pattern = os.path.join(preview_dir_str, "segment%03d.ts")
    
    print(f"\n{'='*70}")
    print(f"[Preview] NEW PREVIEW REQUEST (PROGRESSIVE MODE)")
    print(f"{'='*70}")
    print(f"[Preview] ID: {preview_id}")
    print(f"[Preview] URL: {video_url}")
    print(f"[Preview] Output: {os.path.abspath(preview_dir_str)}")
    print(f"{'='*70}\n")
    
    # Build FFmpeg command - RE-ENCODE with progressive HLS
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-y",
        "-i", video_url,
        # RE-ENCODE
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        # HLS settings for progressive loading
        "-f", "hls",
        "-hls_time", "10",
        "-hls_list_size", "0",           # Keep all segments in playlist
        "-hls_flags", "append_list",     # Append to playlist as segments ready
        "-hls_segment_filename", segment_pattern,
        playlist_path_str
    ]
    
    print(f"[FFmpeg] Starting conversion...")
    print(f"[FFmpeg] Mode: PROGRESSIVE (play while encoding)")
    print(f"[FFmpeg] Codec: H.264 ultrafast + AAC")
    print(f"[FFmpeg] Segments: 10 seconds each\n")
    
    # Start FFmpeg process
    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(HLS_DIR)
        )
        print(f"[FFmpeg] Process started (PID: {ffmpeg_process.pid})")
        print(f"[FFmpeg] Encoding in background...\n")
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start FFmpeg: {str(e)}"
        )
    
    # Wait for FIRST segment only (progressive mode)
    start_time = time.time()
    segments_ready = False
    max_wait = 90  # Wait max 90 seconds for first segment
    
    print(f"[Preview] Waiting for first segment (max {max_wait}s)...\n")
    
    # Check if FFmpeg crashes immediately
    time.sleep(3)
    if ffmpeg_process.poll() is not None:
        stdout, stderr = ffmpeg_process.communicate()
        print(f"[FFmpeg] ❌ Process exited early!")
        print(f"\n{'='*70}")
        print(f"[FFmpeg] ERROR:")
        print(f"{'='*70}")
        print(stderr[:2000] if stderr else "(empty)")
        print(f"{'='*70}\n")
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail="FFmpeg failed to start"
        )
    
    # Wait for first segment
    while time.time() - start_time < max_wait:
        elapsed = int(time.time() - start_time)
        
        # Check if FFmpeg crashed
        if ffmpeg_process.poll() is not None:
            stdout, stderr = ffmpeg_process.communicate()
            print(f"\n[FFmpeg] ❌ Process stopped unexpectedly!")
            print(f"[FFmpeg] Error: {stderr[:500] if stderr else 'Unknown'}\n")
            cleanup_preview_directory(Path(preview_dir_str))
            raise HTTPException(
                status_code=500,
                detail="FFmpeg stopped - video may be invalid"
            )
        
        # Check for playlist
        if not os.path.exists(playlist_path_str):
            if elapsed % 15 == 0 and elapsed > 0:
                print(f"[Preview] Waiting... ({elapsed}s)")
            time.sleep(2.0)
            continue
        
        # Check for at least ONE segment
        segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
        
        if len(segment_files) >= 1:
            # FIRST SEGMENT READY - RETURN IMMEDIATELY!
            segments_ready = True
            print(f"[Preview] ✅ First segment ready! ({elapsed}s)")
            print(f"[Preview] 🎬 Starting playback now")
            print(f"[Preview] 📹 FFmpeg continues encoding in background\n")
            break
        
        time.sleep(2.0)
    
    # Check if we got first segment
    if not segments_ready:
        print(f"\n[Preview] ❌ Timeout - no segments after {max_wait}s\n")
        
        try:
            if ffmpeg_process.poll() is None:
                ffmpeg_process.terminate()
            stdout, stderr = ffmpeg_process.communicate(timeout=5)
            print(f"[FFmpeg] Output: {stderr[:1000] if stderr else 'None'}\n")
        except:
            try:
                ffmpeg_process.kill()
            except:
                pass
        
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail=f"Timeout waiting for first segment. Video may be too large or slow to encode."
        )
    
    # Store session (FFmpeg still running!)
    active_sessions[preview_id] = {
        "created_at": time.time(),
        "video_url": video_url,
        "ffmpeg_process": ffmpeg_process,
        "preview_dir": preview_dir_str,
        "mode": "progressive"
    }
    
    playlist_url = f"/hls/{preview_id}/playlist.m3u8"
    
    print(f"{'='*70}")
    print(f"[Preview] ✅ PREVIEW READY!")
    print(f"{'='*70}")
    print(f"[Preview] Mode: PROGRESSIVE")
    print(f"[Preview] Playlist: {playlist_url}")
    print(f"[Preview] Status: Playing + Encoding simultaneously")
    print(f"{'='*70}\n")
    
    return {
        "preview_id": preview_id,
        "playlist_url": playlist_url,
        "segment_duration": 10,
        "mode": "progressive",
        "message": "Preview ready - more segments loading"
    }


@app.post("/end-preview")
async def end_preview(request: Request):
    """End a preview session"""
    
    try:
        body = await request.json()
        preview_id = body.get("preview_id")
    except:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    if not preview_id:
        raise HTTPException(status_code=400, detail="Missing preview_id")
    
    if preview_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    cleanup_session(preview_id)
    
    return {
        "status": "success",
        "message": f"Preview {preview_id} ended"
    }


# ============================================================================
# ROUTES - DEBUG
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": time.time()
    }


@app.get("/debug/sessions")
async def debug_sessions():
    """List active sessions"""
    sessions_info = []
    
    for preview_id, session in active_sessions.items():
        age = int(time.time() - session["created_at"])
        
        # Check if FFmpeg still running
        ffmpeg_running = False
        ffmpeg_process = session.get("ffmpeg_process")
        if ffmpeg_process and ffmpeg_process.poll() is None:
            ffmpeg_running = True
        
        # Count segments
        preview_dir = session["preview_dir"]
        segment_count = len(glob.glob(os.path.join(preview_dir, "segment*.ts")))
        
        sessions_info.append({
            "preview_id": preview_id,
            "age_seconds": age,
            "video_url": session["video_url"],
            "mode": session.get("mode", "unknown"),
            "segments": segment_count,
            "ffmpeg_running": ffmpeg_running
        })
    
    return {
        "total_sessions": len(active_sessions),
        "sessions": sessions_info
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def cleanup_session(preview_id: str):
    """Cleanup a preview session"""
    if preview_id not in active_sessions:
        return
    
    print(f"[Cleanup] Cleaning up: {preview_id}")
    
    session = active_sessions[preview_id]
    
    # Stop FFmpeg if still running
    ffmpeg_process = session.get("ffmpeg_process")
    if ffmpeg_process:
        try:
            if ffmpeg_process.poll() is None:
                print(f"[Cleanup] Stopping FFmpeg...")
                ffmpeg_process.terminate()
                ffmpeg_process.wait(timeout=5)
        except:
            try:
                ffmpeg_process.kill()
            except:
                pass
    
    # Delete directory
    preview_dir = Path(session["preview_dir"])
    cleanup_preview_directory(preview_dir)
    
    # Remove from sessions
    del active_sessions[preview_id]
    
    print(f"[Cleanup] Done\n")


def cleanup_preview_directory(preview_dir: Path):
    """Delete preview directory"""
    if not preview_dir.exists():
        return
    
    try:
        file_count = 0
        for file in preview_dir.glob("*"):
            try:
                file.unlink()
                file_count += 1
            except:
                pass
        
        try:
            preview_dir.rmdir()
            if file_count > 0:
                print(f"[Cleanup] Deleted {file_count} files")
        except:
            pass
            
    except Exception as e:
        print(f"[Cleanup] Error: {e}")


# ============================================================================
# STARTUP & SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Server startup"""
    print("\n")
    print_config()
    print("🚀 Server started!")
    print(f"📱 Open: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"\n💡 Test URLs:")
    print(f"   Small: https://www.w3schools.com/html/mov_bbb.mp4")
    print(f"   Big Buck Bunny: https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4")
    print(f"\n⚡ PROGRESSIVE MODE:")
    print(f"   Video starts playing after ~5-30 seconds")
    print(f"   Rest of video loads while you watch")
    print(f"   Like YouTube/Netflix!\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Server shutdown"""
    print("\n[Shutdown] Cleaning up...")
    
    session_ids = list(active_sessions.keys())
    for preview_id in session_ids:
        cleanup_session(preview_id)
    
    print("[Shutdown] Done\n")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info"
    )