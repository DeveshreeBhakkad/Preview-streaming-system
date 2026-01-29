from backend.stream.chunk_fetcher import ChunkFetcher
from backend.stream.buffer_manager import BufferManager


class StreamController:
    def __init__(self, video_url: str, chunk_size: int):
        self.buffer_manager = BufferManager()
        self.fetcher = ChunkFetcher(video_url, chunk_size)

    def stream(self):
        """
        Generator yielding video chunks based on buffer rules
        """
        self.buffer_manager.initialize()

        while True:
            active_chunks = self.buffer_manager.get_active_chunks()

            for chunk_id in active_chunks:
                try:
                    data = self.fetcher.fetch_chunk(chunk_id)
                except Exception as e:
                    print(f"[StreamController] {e}")
                    return

                if not data:
                    return

                yield data

            self.buffer_manager.slide_forward()
