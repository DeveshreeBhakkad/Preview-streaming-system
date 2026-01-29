from backend.stream.buffer_manager import BufferManager
from backend.stream.chunk_fetcher import ChunkFetcher


class StreamController:
    def __init__(self, source_url: str, bytes_per_chunk: int):
        self.source_url = source_url
        self.bytes_per_chunk = bytes_per_chunk

        self.buffer_manager = BufferManager()
        self.chunk_fetcher = ChunkFetcher(
            source_url=source_url,
            bytes_per_chunk=bytes_per_chunk
        )

    def stream(self):
        """
        Generator that yields video chunks based on buffer rules
        """
        self.buffer_manager.initialize()

        while True:
            active_chunks = self.buffer_manager.get_active_chunks()

            for chunk_id in active_chunks:
                data = self.chunk_fetcher.fetch_chunk(chunk_id)

                if not data:
                    return  # End of stream or error

                yield data

            self.buffer_manager.slide_forward()
