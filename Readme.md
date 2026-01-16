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

The backend now controls which video chunks exist using a sliding window buffer.
Old chunks are deleted automatically, naturally limiting rewind.

## Design Note

The current implementation focuses on backend-controlled streaming logic.
Playback may pause after a fixed duration because HTML5 video elements
require continuous buffered ranges.

This behavior is expected and demonstrates why real streaming systems
use MediaSource API on the frontend, which will be implemented in the next phase.
