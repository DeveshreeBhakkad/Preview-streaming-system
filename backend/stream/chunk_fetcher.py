import requests


class ChunkFetcher:
    def __init__(self, source_url: str, bytes_per_chunk: int):
        self.source_url = source_url
        self.bytes_per_chunk = bytes_per_chunk

    def fetch_chunk(self, chunk_id: int) -> bytes | None:
        """
        Fetch a single chunk from remote URL using HTTP Range
        """
        start_byte = (chunk_id - 1) * self.bytes_per_chunk
        end_byte = start_byte + self.bytes_per_chunk - 1

        headers = {
            "Range": f"bytes={start_byte}-{end_byte}"
        }

        response = requests.get(
            self.source_url,
            headers=headers,
            stream=True,
            timeout=10
        )

        # 206 = Partial Content (expected)
        if response.status_code not in (200, 206):
            return None

        return response.content
