from collections import deque
from backend.ml.network_model import predict_forward_buffer

# -----------------------------
# BUFFER CONFIGURATION
# -----------------------------
BACKWARD_LIMIT = 2


class BufferManager:
    def __init__(self):
        self.buffer = deque()
        self.current_chunk_id = 0
        self.forward_limit = 2  # default fallback

    def _update_forward_limit(self):
        """
        Update forward buffer size using ML prediction
        """

        # Simulated network metrics (Phase 5 scope)
        network_metrics = {
            "bandwidth_kbps": 1200,
            "latency_ms": 140,
            "jitter_ms": 15,
            "packet_loss_pct": 1.2
        }

        self.forward_limit = predict_forward_buffer(network_metrics)

        print(f"[ML] Adaptive forward buffer size: {self.forward_limit}")

    def initialize(self):
        """
        Initialize buffer with current + forward chunks
        """
        self._update_forward_limit()

        self.current_chunk_id = 1
        self.buffer.clear()

        # current chunk
        self.buffer.append(self.current_chunk_id)

        # forward chunks
        for i in range(1, self.forward_limit + 1):
            self.buffer.append(self.current_chunk_id + i)

    def slide_forward(self):
        """
        Move buffer window forward by one chunk
        """
        self._update_forward_limit()

        self.current_chunk_id += 1
        next_chunk = self.current_chunk_id + self.forward_limit
        self.buffer.append(next_chunk)

        max_buffer_size = BACKWARD_LIMIT + 1 + self.forward_limit

        while len(self.buffer) > max_buffer_size:
            self.buffer.popleft()

    def get_active_chunks(self):
        """
        Returns list of chunk IDs currently allowed
        """
        return list(self.buffer)
