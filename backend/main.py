"""
Main FastAPI Server for Previewly Video Preview System
DOWNLOAD-FIRST APPROACH - Most reliable method
Downloads video, then converts locally
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
import requests
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
# ROUTES - VIDEO PREVIEW (DOWNLOAD-FIRST MODE)
# ============================================================================

@app.post("/start-preview")
async def start_preview(request: Request):
    """
    Start video preview - DOWNLOAD FIRST APPROACH
    Downloads video to disk, then converts locally (much faster!)
    """
    
    # Parse request body
    try:
        body = await request.json()
        video_url = body.get("url")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request body: {str(e)}")
    
    # Validate
    if not video_url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")
    if not video_url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    
    # Generate preview ID
    preview_id = f"preview_{uuid.uuid4().hex[:8]}"
    
    # Create directory
    preview_dir_str = os.path.join(str(HLS_DIR), preview_id)
    os.makedirs(preview_dir_str, exist_ok=True)
    
    # Paths
    playlist_path_str = os.path.join(preview_dir_str, "playlist.m3u8")
    segment_pattern = os.path.join(preview_dir_str, "segment%03d.ts")
    local_video_path = os.path.join(preview_dir_str, "input_video.mp4")
    
    print(f"\n{'='*70}")
    print(f"[Preview] NEW REQUEST (DOWNLOAD-FIRST MODE)")
    print(f"{'='*70}")
    print(f"[Preview] ID: {preview_id}")
    print(f"[Preview] URL: {video_url}")
    print(f"{'='*70}\n")
    
    # STEP 1: DOWNLOAD VIDEO FIRST
    print(f"[Download] Starting download...")
    print(f"[Download] Saving to: {local_video_path}\n")
    
    download_start = time.time()
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(
            video_url, 
            headers=headers, 
            stream=True,
            timeout=60
        )
        response.raise_for_status()
        
        # Get file size
        total_size = int(response.headers.get('content-length', 0))
        if total_size > 0:
            total_mb = total_size / (1024 * 1024)
            print(f"[Download] File size: {total_mb:.1f} MB")
        
        # Download in chunks
        downloaded = 0
        last_log = 0
        with open(local_video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    downloaded_mb = downloaded / (1024 * 1024)
                    
                    # Log every 10MB
                    if downloaded_mb - last_log >= 10:
                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            print(f"[Download] {downloaded_mb:.0f}MB / {total_mb:.0f}MB ({pct:.0f}%)")
                        else:
                            print(f"[Download] {downloaded_mb:.0f}MB downloaded...")
                        last_log = downloaded_mb
        
        download_time = int(time.time() - download_start)
        file_size_mb = os.path.getsize(local_video_path) / (1024 * 1024)
        print(f"\n[Download] ✅ Complete! {file_size_mb:.1f}MB in {download_time}s")
        
    except requests.exceptions.Timeout:
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(status_code=500, detail="Download timeout - video URL too slow")
    except requests.exceptions.RequestException as e:
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")
    except Exception as e:
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")
    
    # STEP 2: RUN FFMPEG ON LOCAL FILE (much faster!)
    print(f"\n[FFmpeg] Starting conversion on LOCAL file...")
    print(f"[FFmpeg] Mode: STREAM COPY (no re-encoding)")
    print(f"[FFmpeg] Input: {local_video_path}\n")
    
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i", local_video_path,   # LOCAL FILE (not URL!)
        "-c", "copy",              # Copy streams (fast!)
        "-f", "hls",
        "-hls_time", "10",
        "-hls_list_size", "0",
        "-hls_segment_filename", segment_pattern,
        "-start_number", "0",
        playlist_path_str
    ]
    
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
    except Exception as e:
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(status_code=500, detail=f"FFmpeg failed: {str(e)}")
    
    # STEP 3: WAIT FOR SEGMENTS
    start_time = time.time()
    segments_ready = False
    min_segments = 3      # Wait for 3 segments
    max_wait = 60         # 60 seconds max
    last_count = 0
    
    print(f"[Preview] Waiting for {min_segments} segments...\n")
    
    time.sleep(2)
    
    if ffmpeg_process.poll() is not None:
        stdout, stderr = ffmpeg_process.communicate()
        print(f"[FFmpeg] ❌ Crashed!")
        print(f"[FFmpeg] Error: {stderr[:1000] if stderr else 'Unknown'}\n")
        cleanup_preview_directory(Path(preview_dir_str))
        raise HTTPException(status_code=500, detail="FFmpeg failed")
    
    while time.time() - start_time < max_wait:
        elapsed = int(time.time() - start_time)
        
        # Check if FFmpeg done
        if ffmpeg_process.poll() is not None:
            segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
            segment_count = len(segment_files)
            if segment_count > 0:
                segments_ready = True
                print(f"\n[Preview] ✅ FFmpeg done! {segment_count} segments ({elapsed}s)\n")
                break
            else:
                stdout, stderr = ffmpeg_process.communicate()
                print(f"\n[FFmpeg] ❌ No segments!")
                print(f"[FFmpeg] Error: {stderr[:1000]}\n")
                cleanup_preview_directory(Path(preview_dir_str))
                raise HTTPException(status_code=500, detail="FFmpeg failed to create segments")
        
        if os.path.exists(playlist_path_str):
            segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
            segment_count = len(segment_files)
            
            if segment_count != last_count and segment_count > 0:
                print(f"[Preview] ✓ {segment_count} segment(s) ({elapsed}s)")
                last_count = segment_count
            
            if segment_count >= min_segments:
                segments_ready = True
                print(f"\n[Preview] ✅ {segment_count} segments ready! ({elapsed}s)")
                print(f"[Preview] FFmpeg continues in background...\n")
                break
        else:
            if elapsed % 5 == 0 and elapsed > 0:
                print(f"[Preview] Processing... ({elapsed}s)")
        
        time.sleep(1.0)
    
    if not segments_ready:
        segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
        segment_count = len(segment_files)
        
        if segment_count >= 1:
            print(f"[Preview] ⚠️ Using {segment_count} partial segment(s)\n")
            segments_ready = True
        else:
            try:
                if ffmpeg_process.poll() is None:
                    ffmpeg_process.terminate()
            except:
                pass
            cleanup_preview_directory(Path(preview_dir_str))
            raise HTTPException(status_code=500, detail="Timeout - no segments created")
    
    # Count final segments
    segment_files = glob.glob(os.path.join(preview_dir_str, "segment*.ts"))
    segment_count = len(segment_files)
    
    # Store session
    active_sessions[preview_id] = {
        "created_at": time.time(),
        "video_url": video_url,
        "local_video": local_video_path,
        "ffmpeg_process": ffmpeg_process,
        "preview_dir": preview_dir_str,
        "segment_count": segment_count
    }
    
    playlist_url = f"/hls/{preview_id}/playlist.m3u8"
    
    print(f"{'='*70}")
    print(f"[Preview] ✅ PREVIEW READY!")
    print(f"{'='*70}")
    print(f"[Preview] Segments: {segment_count} (~{segment_count * 10}s)")
    print(f"[Preview] Playlist: {playlist_url}")
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
    print(f"   Small: https://www.w3schools.com/html/mov_bbb.mp4")
    print(f"   Big Buck Bunny: https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4")
    print(f"\n⚡ DOWNLOAD-FIRST MODE:")
    print(f"   Downloads video first, then converts")
    print(f"   Much more reliable!")
    print(f"   Works with any video format\n")


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