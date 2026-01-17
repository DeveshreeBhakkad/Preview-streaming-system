## Project Status

This project is being developed incrementally as a personal portfolio project
to understand real-world video streaming systems.

### Completed Phases
- Phase 1: Python streaming fundamentals (generators)
- Phase 2: FastAPI streaming responses
- Phase 3: Video streaming from backend
- Phase 4.1: Conceptual buffer model (sliding window)
- Phase 4.2: Buffer logic simulation using deque
- Phase 4.3: Backend-controlled chunk streaming with limited rewind
- Phase 4.4: MediaSource-based controlled streaming (conceptual)

The backend controls which video chunks exist using a sliding window buffer.
Old chunks are deleted automatically, naturally limiting rewind.

---

## Phase 4 — Backend-Controlled Streaming

In this phase, the backend controls video streaming using a sliding window buffer instead of relying on the browser’s default buffering.

### Key Features
- Time-based chunk streaming
- Sliding window buffer (limited rewind + forward prefetch)
- Old chunks deleted from backend memory
- MediaSource API used for manual chunk appending

### Design Note
This phase intentionally uses raw chunk streaming to demonstrate backend buffer control.
Full playback requires timestamped media segments (e.g., HLS/DASH), which are planned as a future extension.

### Outcome
Phase 4 focuses on system design and buffering control rather than full media playback.
