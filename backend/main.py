"""
Main FastAPI Server for Previewly Video Preview System
WAIT FOR FULL CONVERSION - Complete video playback
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
    description="Backend-controlled video preview system",
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
# ROUTES - VIDEO PREVIEW
# ============================================================================

@app.post("/start-preview")
async def start_preview(request: Request):
    """Start video preview - WAITS FOR FULL CONVERSION"""
    
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
    
    # Create directory using absolute paths
    preview_dir_str = os.path.join(str(HLS_DIR), preview_id)
    os.makedirs(preview_dir_str, exist_ok=True)
    
    # Define paths
    playlist_path_str = os.path.join(preview_dir_str, "playlist.m3u8")
    segment_pattern = os.path.join(preview_dir_str, "segment%03d.ts")
    
    print(f"\n{'='*70}")
    print(f"[Preview] NEW PREVIEW REQUEST")
    print(f"{'='*70}")
    print(f"[Preview] Preview ID: {preview_id}")
    print(f"[Preview] Video URL: {video_url}")
    print(f"[Preview] Output: {os.path.abspath(preview_dir_str)}")
    print(f"{'='*70}\n")
    
    # Build FFmpeg command with User-Agent to bypass 403 errors
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-y",
        "-i", video_url,
        "-c", "copy",           # Copy streams (fast)
        "-f", "hls",
        "-hls_time", "10",      # 10 second segments
        "-hls_list_size", "0",  # Keep all segments
        "-hls_segment_filename", segment_pattern,
        playlist_path_str
    ]
    
    print(f"[FFmpeg] Starting conversion with browser User-Agent...")
    print(f"[FFmpeg] Segment size: 10 seconds")
    print(f"[FFmpeg] This will wait for FULL conversion to complete\n")
    
    # Start FFmpeg process
    try:
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(HLS_DIR)
        )
        print(f"[FFmpeg] Process started (PID: {ffmpeg_process.pid})\n")
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
    
    # Wait for FFmpeg to finish converting the ENTIRE video
    start_time = time.time()
    segments_ready = False
    last_count = 0
    ffmpeg_finished = False
    
    print(f"[Preview] Converting video (timeout: {FFMPEG_TIMEOUT}s)...\n")
    
    # Check if FFmpeg crashes immediately
    time.sleep(3)
    if ffmpeg_process.poll() is not None:
        stdout, stderr = ffmpeg_process.communicate()
        print(f"[FFmpeg] ❌ Process exited early!")
        print(f"\n{'='*70}")
        print(f"[FFmpeg] ERROR OUTPUT:")
        print(f"{'='*70}")
        print(stderr[:1000] if stderr else "(empty)")
        print(f"{'='*70}\n")
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail="FFmpeg failed to start - check server logs for details"
        )
    
    # Wait for FFmpeg to finish converting
    while time.time() - start_time < FFMPEG_TIMEOUT:
        elapsed = int(time.time() - start_time)
        
        # Check if FFmpeg finished
        ffmpeg_status = ffmpeg_process.poll()
        if ffmpeg_status is not None:
            # FFmpeg finished!
            ffmpeg_finished = True
            print(f"[Preview] ✅ FFmpeg conversion complete! (took {elapsed}s)")
            break
        
        # Check playlist exists
        if not os.path.exists(playlist_path_str):
            if elapsed % 15 == 0 and elapsed > 0:
                print(f"[Preview] Converting... ({elapsed}s elapsed)")
            time.sleep(2.0)
            continue
        
        # Check segment count
        segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
        segment_count = len(segment_files)
        
        # Show progress
        if segment_count != last_count and segment_count > 0:
            if segment_count == 1:
                print(f"[Preview] ✓ First segment ready ({elapsed}s)")
            elif segment_count % 10 == 0:  # Show every 10 segments
                print(f"[Preview] ✓ {segment_count} segments converted... ({elapsed}s)")
            last_count = segment_count
        
        time.sleep(2.0)  # Check every 2 seconds
    
    # Final check
    if not ffmpeg_finished:
        # Timeout - but check if we have segments
        segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
        segment_count = len(segment_files)
        
        if segment_count > 0:
            print(f"\n[Preview] ⚠️ Timeout after {FFMPEG_TIMEOUT}s")
            print(f"[Preview] BUT {segment_count} segments available - using partial video")
            print(f"[Preview] Terminating FFmpeg...\n")
            try:
                ffmpeg_process.terminate()
                ffmpeg_process.wait(timeout=5)
            except:
                try:
                    ffmpeg_process.kill()
                except:
                    pass
            segments_ready = True
        else:
            print(f"\n[Preview] ❌ TIMEOUT after {FFMPEG_TIMEOUT}s with NO segments!\n")
            
            # Get FFmpeg error
            try:
                ffmpeg_process.terminate()
                stdout, stderr = ffmpeg_process.communicate(timeout=5)
                print(f"[FFmpeg] Error output:\n{stderr[:1000] if stderr else 'None'}\n")
            except:
                try:
                    ffmpeg_process.kill()
                except:
                    pass
            
            cleanup_preview_directory(Path(preview_dir_str))
            raise HTTPException(
                status_code=500,
                detail=f"Timeout waiting for video conversion ({FFMPEG_TIMEOUT}s)"
            )
    else:
        segments_ready = True
    
    # Count final segments
    segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
    segment_count = len(segment_files)
    
    if segment_count == 0:
        print(f"[Preview] ❌ No segments generated!\n")
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail="No video segments were generated"
        )
    
    # Calculate video duration
    video_duration_seconds = segment_count * 10
    video_duration_minutes = video_duration_seconds // 60
    
    print(f"\n[Preview] ✅ SUCCESS!")
    print(f"[Preview] Total segments: {segment_count}")
    print(f"[Preview] Video duration: ~{video_duration_minutes}m {video_duration_seconds % 60}s")
    print(f"[Preview] Ready for playback!\n")
    
    # Store session
    active_sessions[preview_id] = {
        "created_at": time.time(),
        "video_url": video_url,
        "ffmpeg_process": ffmpeg_process,
        "preview_dir": preview_dir_str,
        "segment_count": segment_count
    }
    
    playlist_url = f"/hls/{preview_id}/playlist.m3u8"
    
    print(f"[Preview] Playlist URL: {playlist_url}")
    print(f"{'='*70}\n")
    
    return {
        "preview_id": preview_id,
        "playlist_url": playlist_url,
        "segment_duration": 10,
        "total_segments": segment_count,
        "video_duration_seconds": video_duration_seconds,
        "message": "Preview ready - full video available"
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
        sessions_info.append({
            "preview_id": preview_id,
            "age_seconds": age,
            "video_url": session["video_url"],
            "segment_count": session.get("segment_count", 0)
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
    
    print(f"[Cleanup] Cleaning up session: {preview_id}")
    
    session = active_sessions[preview_id]
    
    # Stop FFmpeg if still running
    ffmpeg_process = session.get("ffmpeg_process")
    if ffmpeg_process:
        try:
            if ffmpeg_process.poll() is None:
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
    
    # Remove from active sessions
    del active_sessions[preview_id]
    
    print(f"[Cleanup] Session {preview_id} cleaned up\n")


def cleanup_preview_directory(preview_dir: Path):
    """Delete preview directory and contents"""
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
            print(f"[Cleanup] Deleted {file_count} files from {preview_dir.name}")
        except:
            print(f"[Cleanup] Could not delete directory {preview_dir.name}")
            
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
    print("🚀 Server started successfully!")
    print(f"📱 Open: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"\n💡 Working Test URLs:")
    print(f"   Small (10s): https://www.w3schools.com/html/mov_bbb.mp4")
    print(f"   Big Buck Bunny (9m): https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4")
    print(f"   Sample (30s): https://filesamples.com/samples/video/mp4/sample_1280x720.mp4")
    print(f"\n⏳ Note: Server waits for FULL conversion before playing")
    print(f"   Larger videos may take 1-3 minutes to convert\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Server shutdown"""
    print("\n[Shutdown] Cleaning up active sessions...")
    
    session_ids = list(active_sessions.keys())
    for preview_id in session_ids:
        cleanup_session(preview_id)
    
    print("[Shutdown] All sessions cleaned up")
    print("[Shutdown] Server stopped\n")


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