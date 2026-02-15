"""
Main FastAPI Server for Previewly Video Preview System
ULTRA-FAST MODE - Optimized for slower computers
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
# ROUTES - VIDEO PREVIEW (ULTRA-FAST MODE)
# ============================================================================

@app.post("/start-preview")
async def start_preview(request: Request):
    """
    Start video preview - ULTRA-FAST MODE
    Optimized for slower computers with lower quality/faster encoding
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
    
    # Validate
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
    
    # Generate preview ID
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    
    # Create directory
    preview_dir_str = os.path.join(str(HLS_DIR), preview_id)
    os.makedirs(preview_dir_str, exist_ok=True)
    
    # Paths
    playlist_path_str = os.path.join(preview_dir_str, "playlist.m3u8")
    segment_pattern = os.path.join(preview_dir_str, "segment%03d.ts")
    
    print(f"\n{'='*70}")
    print(f"[Preview] NEW REQUEST (ULTRA-FAST MODE)")
    print(f"{'='*70}")
    print(f"[Preview] ID: {preview_id}")
    print(f"[Preview] URL: {video_url}")
    print(f"[Preview] Output: {os.path.abspath(preview_dir_str)}")
    print(f"{'='*70}\n")
    
    # ULTRA-FAST encoding with LOWER resolution
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-y",
        "-i", video_url,
        # Scale down to 480p for speed
        "-vf", "scale=854:480",
        # Ultra-fast encoding settings
        "-c:v", "libx264",
        "-preset", "ultrafast",     # Fastest encoding
        "-tune", "zerolatency",     # Optimized for speed
        "-crf", "28",               # Lower quality = faster
        "-maxrate", "800k",         # Limit bitrate
        "-bufsize", "1600k",
        # Audio settings
        "-c:a", "aac",
        "-b:a", "96k",              # Lower audio bitrate
        "-ac", "1",                 # Mono audio for speed
        # HLS settings
        "-f", "hls",
        "-hls_time", "10",          # 10 second segments
        "-hls_list_size", "0",      # Keep all segments
        "-hls_segment_filename", segment_pattern,
        playlist_path_str
    ]
    
    print(f"[FFmpeg] Starting ULTRA-FAST encoding...")
    print(f"[FFmpeg] Quality: 480p (optimized for speed)")
    print(f"[FFmpeg] Preset: ultrafast + zerolatency")
    print(f"[FFmpeg] Audio: Mono 96kbps")
    print(f"[FFmpeg] Expected: 2-3x faster than before!\n")
    
    # Start FFmpeg
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
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail="FFmpeg not found"
        )
    except Exception as e:
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start FFmpeg: {str(e)}"
        )
    
    # Wait for segments
    start_time = time.time()
    segments_ready = False
    min_segments = 2      # Wait for 2 segments
    max_wait = 120        # Max 2 minutes
    last_count = 0
    last_log = 0
    
    print(f"[Preview] Waiting for {min_segments} segments (max {max_wait}s)...\n")
    
    # Initial wait
    time.sleep(3)
    
    # Check if crashed immediately
    if ffmpeg_process.poll() is not None:
        stdout, stderr = ffmpeg_process.communicate()
        print(f"[FFmpeg] ❌ Crashed immediately!")
        print(f"[FFmpeg] Error: {stderr[:1000] if stderr else 'Unknown'}\n")
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(
            status_code=500,
            detail="FFmpeg crashed on start"
        )
    
    # Wait loop
    while time.time() - start_time < max_wait:
        elapsed = int(time.time() - start_time)
        
        # Check if FFmpeg finished
        if ffmpeg_process.poll() is not None:
            segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
            segment_count = len(segment_files)
            
            if segment_count >= min_segments:
                segments_ready = True
                print(f"\n[Preview] ✅ FFmpeg finished! {segment_count} segments total ({elapsed}s)\n")
                break
            else:
                stdout, stderr = ffmpeg_process.communicate()
                print(f"\n[Preview] ❌ FFmpeg finished but only {segment_count} segment(s)")
                print(f"[FFmpeg] Error: {stderr[:1000] if stderr else 'None'}\n")
                cleanup_preview_directory(Path(preview_dir_str))
                raise HTTPException(
                    status_code=500,
                    detail=f"FFmpeg finished but only created {segment_count} segment(s)"
                )
        
        # Check for playlist and segments
        if os.path.exists(playlist_path_str):
            segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
            segment_count = len(segment_files)
            
            # Show progress
            if segment_count != last_count and segment_count > 0:
                print(f"[Preview] ✓ {segment_count} segment(s) ready ({elapsed}s)")
                last_count = segment_count
            
            # Check if we have enough
            if segment_count >= min_segments:
                segments_ready = True
                print(f"\n[Preview] ✅ {segment_count} segments ready! ({elapsed}s)")
                print(f"[Preview] Starting playback now")
                print(f"[Preview] FFmpeg continues in background...\n")
                break
        else:
            # Show progress every 10 seconds while waiting
            if elapsed - last_log >= 10 and elapsed > 0:
                print(f"[Preview] Still encoding... ({elapsed}s)")
                last_log = elapsed
        
        time.sleep(2.0)
    
    # Final check
    if not segments_ready:
        print(f"\n[Preview] ❌ Timeout after {max_wait}s\n")
        
        # Count what we have
        segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
        segment_count = len(segment_files)
        
        print(f"[Debug] Found {segment_count} segment(s) in directory")
        
        # If we have at least 1 segment, use it (partial video)
        if segment_count >= 1:
            print(f"[Preview] ⚠️ Using {segment_count} partial segment(s)\n")
            segments_ready = True
        else:
            # No segments at all - complete failure
            print(f"[Preview] ❌ No segments created\n")
            
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
                detail="Timeout - no segments created. Video may be too complex or system too slow."
            )
    
    # Count final segments
    segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
    segment_count = len(segment_files)
    
    # Store session (FFmpeg may still be running!)
    active_sessions[preview_id] = {
        "created_at": time.time(),
        "video_url": video_url,
        "ffmpeg_process": ffmpeg_process,
        "preview_dir": preview_dir_str,
        "segment_count": segment_count
    }
    
    playlist_url = f"/hls/{preview_id}/playlist.m3u8"
    
    print(f"{'='*70}")
    print(f"[Preview] ✅ PREVIEW READY!")
    print(f"{'='*70}")
    print(f"[Preview] Playlist: {playlist_url}")
    print(f"[Preview] Segments: {segment_count} (~{segment_count * 10}s)")
    print(f"[Preview] Status: {'Complete' if ffmpeg_process.poll() is not None else 'Encoding continues...'}")
    print(f"{'='*70}\n")
    
    return {
        "preview_id": preview_id,
        "playlist_url": playlist_url,
        "segment_duration": 10,
        "available_segments": segment_count,
        "message": "Preview ready"
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
        
        # Check FFmpeg status
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
    print(f"   Small (10s): https://www.w3schools.com/html/mov_bbb.mp4")
    print(f"   Big Buck Bunny: https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4")
    print(f"\n⚡ ULTRA-FAST MODE:")
    print(f"   480p quality for maximum speed")
    print(f"   Optimized for slower computers")
    print(f"   Should be 2-3x faster than before!\n")


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