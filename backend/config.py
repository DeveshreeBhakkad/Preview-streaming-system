"""
Configuration for Previewly Video Preview System
Centralized settings for all components
"""

import os
from pathlib import Path

# ============================================================================
# DIRECTORY PATHS
# ============================================================================

# Base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Frontend directory (HTML, CSS, JS)
FRONTEND_DIR = BASE_DIR / "frontend"

# Data directory
DATA_DIR = BASE_DIR / "data"

# HLS output directory (where video segments are stored)
HLS_DIR = DATA_DIR / "hls"

# Create directories if they don't exist
HLS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# SERVER SETTINGS
# ============================================================================

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000

# CORS settings (allow frontend to communicate with backend)
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


# ============================================================================
# VIDEO PROCESSING SETTINGS
# ============================================================================

# HLS segment duration (seconds)
SEGMENT_DURATION = 30

# Video codec
VIDEO_CODEC = "libx264"

# Audio codec
AUDIO_CODEC = "aac"

# FFmpeg timeout (seconds to wait for video processing)
FFMPEG_TIMEOUT = 120  # 2 minutes

# Minimum segments required before starting playback
MIN_SEGMENTS_TO_START = 1


# ============================================================================
# REWIND CONTROL SETTINGS (for future Phase 5)
# ============================================================================

# Buffer sizes (in minutes)
BACKWARD_BUFFER_MINUTES = 2  # User can rewind 2 minutes back
FORWARD_BUFFER_MINUTES = 2   # Keep 2 minutes ahead buffered

# Calculate number of segments for each buffer
BACKWARD_BUFFER_SEGMENTS = (BACKWARD_BUFFER_MINUTES * 60) // SEGMENT_DURATION  # 4 segments
FORWARD_BUFFER_SEGMENTS = (FORWARD_BUFFER_MINUTES * 60) // SEGMENT_DURATION    # 4 segments

# Total active segments at any time (backward + current + forward)
TOTAL_ACTIVE_SEGMENTS = BACKWARD_BUFFER_SEGMENTS + 1 + FORWARD_BUFFER_SEGMENTS  # 9 segments


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

# Session timeout (seconds)
SESSION_TIMEOUT = 3600  # 1 hour


# ============================================================================
# VALIDATION
# ============================================================================

# Validate paths
assert FRONTEND_DIR.exists(), f"Frontend directory not found: {FRONTEND_DIR}"
assert HLS_DIR.exists(), f"HLS directory not found: {HLS_DIR}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_config():
    """Print configuration summary"""
    print("=" * 60)
    print("🎬 PREVIEWLY - VIDEO PREVIEW SYSTEM")
    print("=" * 60)
    print(f"✓ Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"✓ Segment Duration: {SEGMENT_DURATION} seconds")
    print(f"✓ Backward Buffer: {BACKWARD_BUFFER_MINUTES} min ({BACKWARD_BUFFER_SEGMENTS} segments)")
    print(f"✓ Forward Buffer: {FORWARD_BUFFER_MINUTES} min ({FORWARD_BUFFER_SEGMENTS} segments)")
    print(f"✓ Total Active: {TOTAL_ACTIVE_SEGMENTS} segments per session")
    print(f"✓ Rewind Control: ENABLED")
    print("=" * 60)