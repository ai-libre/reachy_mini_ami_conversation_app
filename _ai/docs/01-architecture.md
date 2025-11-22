# System Architecture Deep Dive

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Threading Model

The application uses a **multi-threaded architecture** with careful synchronization:

### Thread Overview

```
Main Thread (asyncio event loop)
├─ OpenAI WebSocket connection
├─ Gradio UI server
└─ Tool dispatch coordinator

MovementManager Thread (100Hz)
├─ Command queue polling
├─ Primary move sequencing
├─ Secondary move composition
└─ Robot target updates

CameraWorker Thread (30Hz+)
├─ Frame capture
├─ Face detection/tracking
└─ Frame buffering

HeadWobbler Thread
├─ Audio delta processing
├─ Latency compensation (80ms)
└─ Sway offset generation

VisionManager Thread (optional)
├─ Periodic vision processing (5s)
└─ Local VLM inference

SpeechTapper (embedded in audio pipeline)
├─ Real-time VAD
└─ Sway generation
```

### Synchronization Strategy

| Component | Mechanism | Purpose |
|-----------|-----------|---------|
| Movement commands | `queue.Queue` | Thread-safe command passing |
| Face tracking offsets | `threading.Lock` | Atomic offset updates |
| Camera frames | `threading.Lock` | Safe frame access |
| Activity tracking | `threading.Lock` | Idle detection |
| Wobble state | `threading.Lock` | Audio sync state |

## Motion Layering System

### Conceptual Model

The motion system uses **pose composition** rather than joint-level mixing:

```python
# Every 10ms:
primary_pose = get_current_primary_move_pose()  # Dance, emotion, or breathing
secondary_offsets = {
    'speech_sway': wobbler.get_offsets(),
    'face_tracking': camera.get_face_offsets()
}

final_pose = compose_world_offset(primary_pose, secondary_offsets)
robot.set_target(final_pose)
```

### Why This Works

1. **World-frame composition:** Offsets are applied in world coordinates, not joint space
2. **Pose preservation:** Primary motion maintains its choreographed character
3. **Smooth blending:** No discontinuities when switching moves
4. **Mathematical simplicity:** Composition is associative and commutative

### Primary Move Queue

```python
PrimaryMoveQueue:
    moves: List[Move]  # Sequential execution
    current_index: int
    current_frame: int

    def tick():
        if current_move.is_complete():
            advance_to_next()
        return current_move.get_pose(current_frame)
```

**Move Types:**
- **DanceMove:** From reachy_mini_dances_library
- **EmotionMove:** Recorded emotion clips
- **GotoMove:** Single target pose
- **BreathingMove:** Infinite idle loop

### Secondary Move Composition

Secondary moves are **additive offsets** applied to the primary pose:

#### Speech Wobble (HeadWobbler)
```python
# Audio delta → Head motion
audio_delta = openai_audio_chunk  # 24kHz PCM
envelope = abs(audio_delta)
target_angle = envelope * sensitivity
current_offset = smooth_towards(target_angle, damping)

# Applied with 80ms latency compensation
```

#### Face Tracking
```python
# Face position → Look-at offset
face_bbox = tracker.detect(frame)
face_center_3d = camera.unproject(bbox_center)
look_at_pose = robot.compute_ik(face_center_3d)
offset = extract_offset(look_at_pose, current_pose)

# Smooth interpolation when face lost
if no_face_detected:
    offset *= decay_factor
```

## Data Flow Diagrams

### Tool Call Flow

```
User: "Dance for me!"
    │
    ▼
OpenAI Realtime API (server-side intent detection)
    │
    ▼
function_call_arguments.done event
    │
    ▼
dispatch_tool_call(name="dance", args={})
    │
    ▼
DanceTool.execute(args, deps)
    │
    ├─► Get random dance from library
    ├─► Wrap in DanceMove
    └─► deps.movement_manager.queue_command("queue_move", move)
        │
        ▼
    MovementManager receives command
        │
        ▼
    Add to primary_move_queue
        │
        ▼
    Execute in 100Hz control loop
        │
        ▼
    Robot dances!
```

### Vision Processing Flow

```
Camera Frame (30Hz)
    │
    ├─► Face Detection (YOLO/MediaPipe)
    │   └─► Update face_tracking_offsets
    │
    └─► Frame Buffer (latest frame)
            │
            ▼
        Tool: camera.execute()
            │
            ├─► Cloud: Send to GPT-4V
            │   └─► Get description
            │
            └─► Local: Run SmolVLM2
                └─► Get description
                    │
                    ▼
                Return to OpenAI API
                    │
                    ▼
                AI uses description in conversation
```

### Audio Processing Flow

```
User Microphone (16kHz)
    │
    ├─► Resample to 24kHz
    │   └─► Send to OpenAI API
    │
    ▼
OpenAI Server
    ├─► VAD (Voice Activity Detection)
    ├─► Transcription
    ├─► LLM Processing
    └─► TTS Audio Generation
        │
        ▼
    Audio Deltas Stream (24kHz)
        │
        ├─► Play through speaker
        │
        └─► HeadWobbler
            ├─► Extract envelope
            ├─► Generate sway offsets
            └─► Send to MovementManager
                │
                ▼
            Robot head wobbles while speaking
```

## Component Dependencies

```
main.py
├─► Robot (reachy_mini SDK)
├─► MovementManager
│   ├─► DancesLibrary
│   ├─► EmotionLibrary
│   └─► CameraWorker (for face tracking)
│
├─► CameraWorker
│   └─► HeadTracker (YOLO or MediaPipe)
│
├─► HeadWobbler
│   └─► MovementManager (offset injection)
│
├─► VisionManager (optional)
│   ├─► VisionProcessor (SmolVLM2)
│   └─► CameraWorker (frame source)
│
├─► ToolRegistry
│   ├─► Profile system
│   └─► ToolDependencies
│       ├─► Robot
│       ├─► MovementManager
│       ├─► CameraWorker
│       └─► VisionManager
│
└─► Stream (Gradio or Console)
    ├─► OpenAIRealtimeHandler
    │   └─► ToolDispatcher
    └─► Audio pipelines
```

## State Management

### Movement State
- **Last pose cache:** Preserves pose when queue empties
- **Breathing idle:** Activates after 30s inactivity
- **Activity marks:** Tool calls and responses reset timer

### Conversation State
- **Transcripts:** Full conversation history
- **Tool results:** Injected as conversation items
- **Session context:** Maintained across reconnections

### Vision State
- **Frame buffer:** Latest camera frame
- **Face position:** Smoothed tracking coordinates
- **Vision descriptions:** Cached for context

## Error Handling Philosophy

### Rate-Limited Logging
High-frequency errors (100Hz control loop) use rate limiting:
```python
last_error_time = time.time()
if now - last_error_time > 1.0:  # Log at most 1/sec
    logger.error(...)
    last_error_time = now
```

### Graceful Degradation
- **Face lost:** Smoothly decay tracking offsets
- **Vision failure:** Return error to AI, continue conversation
- **Move error:** Return to neutral pose, log error
- **WebSocket disconnect:** Auto-reconnect with backoff

### Critical vs Non-Critical
- **Critical:** Robot control (MovementManager must not crash)
- **Non-critical:** Vision, tools (can fail without breaking session)

## Performance Characteristics

| Subsystem | Frequency | Latency | CPU Usage |
|-----------|-----------|---------|-----------|
| Movement Control | 100Hz | <10ms | Low |
| Camera Processing | 30Hz | <33ms | Medium |
| Face Tracking | 30Hz | <50ms | Medium-High |
| Audio Wobble | Real-time | 80ms (compensated) | Low |
| Vision Analysis | 5s intervals | 1-3s | High (during inference) |
| OpenAI API | Event-driven | 200-500ms | Low |

## Scalability Considerations

### Current Limitations
- Single robot instance
- Local processing for vision (GPU recommended)
- WebRTC peer-to-peer (no relay server)

### Extension Points
- Profile system allows new personalities
- Tool system allows new capabilities
- Move libraries are extensible
- Vision processors are pluggable

## Security Model

- **API Keys:** Environment variables only
- **Network:** WebSocket over TLS
- **Vision:** Local processing option (no cloud)
- **Sandboxing:** Tools are whitelisted (no arbitrary code execution)

---

This architecture prioritizes **real-time responsiveness**, **smooth motion**, and **extensibility** while maintaining a clean separation of concerns.
