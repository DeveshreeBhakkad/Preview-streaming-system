import requests


class ChunkFetcher:
    def __init__(self, video_url: str, chunk_size: int):
        self.video_url = video_url
        self.chunk_size = chunk_size

    def fetch_chunk(self, chunk_id: int) -> bytes:
        """
        Fetch a specific chunk using HTTP Range requests
        """
        start = (chunk_id - 1) * self.chunk_size
        end = start + self.chunk_size - 1

        headers = {
            "Range": f"bytes={start}-{end}"
        }

        response = requests.get(
            self.video_url,
            headers=headers,
            stream=True,
            timeout=10
        )

        if response.status_code not in (200, 206):
            raise RuntimeError(
                f"Failed to fetch chunk {chunk_id}, status={response.status_code}"
            )

        return response.content
