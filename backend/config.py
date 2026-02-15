"""
Configuration Settings for Previewly Video Preview System

This file contains all the settings that control how the system works.
Change values here to customize behavior without touching other code.
"""

import os
from pathlib import Path

# ============================================================================
# PROJECT PATHS
# ============================================================================

# Get the base directory (where this file lives)
BASE_DIR = Path(__file__).resolve().parent.parent

# Frontend files (HTML, CSS, JS)
FRONTEND_DIR = BASE_DIR / "frontend"

# Data storage
DATA_DIR = BASE_DIR / "data"

# HLS output directory (where video segments are stored)
HLS_DIR = DATA_DIR / "hls"

# Create directories if they don't exist
HLS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# VIDEO SEGMENT SETTINGS
# ============================================================================

# How long each video segment should be (in seconds)
# Smaller = more segments, finer control, more overhead
# Larger = fewer segments, less control, better performance
SEGMENT_DURATION = 30  # 30 seconds per segment

# Video quality settings
VIDEO_CODEC = "libx264"  # H.264 codec (widely supported)
AUDIO_CODEC = "aac"      # AAC audio (widely supported)
VIDEO_PRESET = "fast"    # Encoding speed (ultrafast, fast, medium, slow)


# ============================================================================
# BUFFER CONTROL SETTINGS (YOUR UNIQUE FEATURE!)
# ============================================================================

# How many MINUTES user can rewind (backward buffer)
BACKWARD_BUFFER_MINUTES = 2  # 2 minutes = 120 seconds

# How many MINUTES to buffer ahead (forward buffer)
FORWARD_BUFFER_MINUTES = 2   # 2 minutes = 120 seconds

# Calculate number of segments (auto-calculated, don't change)
MAX_BACKWARD_SEGMENTS = int((BACKWARD_BUFFER_MINUTES * 60) / SEGMENT_DURATION)
MAX_FORWARD_SEGMENTS = int((FORWARD_BUFFER_MINUTES * 60) / SEGMENT_DURATION)

# Total segments active at any time
TOTAL_ACTIVE_SEGMENTS = MAX_BACKWARD_SEGMENTS + 1 + MAX_FORWARD_SEGMENTS


# ============================================================================
# SERVER SETTINGS
# ============================================================================

# Server host and port
SERVER_HOST = "127.0.0.1"  # localhost
SERVER_PORT = 8000         # Port 8000

# CORS (Cross-Origin Resource Sharing) - allows frontend to talk to backend
CORS_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]


# ============================================================================
# SESSION SETTINGS
# ============================================================================

# How long before preview sessions auto-cleanup (in seconds)
SESSION_TIMEOUT = 7200  # 1 hour = 3600 seconds

# Maximum concurrent preview sessions allowed
MAX_CONCURRENT_SESSIONS = 100


# ============================================================================
# FFMPEG SETTINGS
# ============================================================================

# FFmpeg timeout for initial segment generation (seconds)
FFMPEG_TIMEOUT = 600  # Wait max 30 seconds for first segments

# Minimum segments needed before preview can start
MIN_SEGMENTS_TO_START = 1  # Need at least 2 segments ready


# ============================================================================
# LOGGING & DEBUG
# ============================================================================

# Enable debug logging
DEBUG = True  # Set to False in production

# Log level
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR


# ============================================================================
# CALCULATED VALUES (READ-ONLY)
# ============================================================================

# These are calculated automatically - don't modify directly

# Approximate buffer sizes
BACKWARD_BUFFER_SECONDS = BACKWARD_BUFFER_MINUTES * 60
FORWARD_BUFFER_SECONDS = FORWARD_BUFFER_MINUTES * 60

# Rewind limit message for users
REWIND_LIMIT_MESSAGE = f"⚠️ Rewind limited to last {BACKWARD_BUFFER_MINUTES} minute(s) (preview mode)"

# Preview info message
PREVIEW_INFO = f"""
Preview Configuration:
- Segment Duration: {SEGMENT_DURATION} seconds
- Backward Buffer: {BACKWARD_BUFFER_MINUTES} minutes ({MAX_BACKWARD_SEGMENTS} segments)
- Forward Buffer: {FORWARD_BUFFER_MINUTES} minutes ({MAX_FORWARD_SEGMENTS} segments)
- Total Active Segments: {TOTAL_ACTIVE_SEGMENTS}
"""


# ============================================================================
# DISPLAY SETTINGS (SHOW ON STARTUP)
# ============================================================================

def print_config():
    """Print configuration on server startup"""
    print("=" * 60)
    print("🎬 PREVIEWLY - VIDEO PREVIEW SYSTEM")
    print("=" * 60)
    print(f"✓ Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"✓ Segment Duration: {SEGMENT_DURATION} seconds")
    print(f"✓ Backward Buffer: {BACKWARD_BUFFER_MINUTES} min ({MAX_BACKWARD_SEGMENTS} segments)")
    print(f"✓ Forward Buffer: {FORWARD_BUFFER_MINUTES} min ({MAX_FORWARD_SEGMENTS} segments)")
    print(f"✓ Total Active: {TOTAL_ACTIVE_SEGMENTS} segments per session")
    print(f"✓ Rewind Control: ENABLED")
    print("=" * 60)


# ============================================================================
# VALIDATION
# ============================================================================

# Validate settings on import
if SEGMENT_DURATION <= 0:
    raise ValueError("SEGMENT_DURATION must be positive")

if MAX_BACKWARD_SEGMENTS < 0 or MAX_FORWARD_SEGMENTS < 0:
    raise ValueError("Buffer segments cannot be negative")

if not HLS_DIR.exists():
    raise RuntimeError(f"HLS directory does not exist: {HLS_DIR}")