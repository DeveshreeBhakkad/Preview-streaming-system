import os
import uuid
import subprocess
import requests


def generate_hls_from_url(video_url: str, base_output_dir: str) -> str:
    preview_id = str(uuid.uuid4())[:8]
    output_dir = os.path.join(base_output_dir, f"preview_{preview_id}")
    os.makedirs(output_dir, exist_ok=True)

    temp_video_path = os.path.join(output_dir, "source.mp4")

    # Download remote video
    with requests.get(video_url, stream=True, timeout=20) as r:
        r.raise_for_status()
        with open(temp_video_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    playlist_path = os.path.join(output_dir, "playlist.m3u8")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", temp_video_path,
        "-codec:v", "libx264",
        "-codec:a", "aac",
        "-start_number", "0",
        "-hls_time", "6",
        "-hls_list_size", "0",
        "-f", "hls",
        playlist_path
    ]

    subprocess.run(cmd, check=True)

    return f"preview_{preview_id}/playlist.m3u8"
