from collections import deque

# -----------------------------
# BUFFER CONFIGURATION
# -----------------------------
BACKWARD_LIMIT = 2
FORWARD_LIMIT = 2
MAX_BUFFER_SIZE = BACKWARD_LIMIT + 1 + FORWARD_LIMIT


class BufferManager:
    def __init__(self):
        self.buffer = deque()
        self.current_chunk_id = 0

    def initialize(self):
        """
        Initialize buffer with current + forward chunks
        """
        self.current_chunk_id = 1
        self.buffer.clear()

        self.buffer.append(1)  # current
        self.buffer.append(2)  # forward
        self.buffer.append(3)  # forward

    def slide_forward(self):
        """
        Move buffer window forward by one chunk
        """
        self.current_chunk_id += 1
        next_chunk = self.current_chunk_id + FORWARD_LIMIT
        self.buffer.append(next_chunk)

        while len(self.buffer) > MAX_BUFFER_SIZE:
            self.buffer.popleft()

    def get_active_chunks(self):
        """
        Returns list of chunk IDs currently allowed
        """
        return list(self.buffer)
