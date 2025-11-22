# Key Components Deep Dive

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## MovementManager (`moves.py`)

**Purpose:** Central motion control system running at 100Hz.

### Responsibilities

1. **Command Queue Processing**
   - Receives commands from tools via thread-safe queue
   - Commands: `queue_move`, `clear_queue`, `mark_activity`, `toggle_freeze`, etc.

2. **Primary Move Sequencing**
   - Maintains sequential queue of moves (dances, emotions, gotos)
   - Advances through moves as they complete
   - Handles transitions smoothly

3. **Idle Breathing**
   - Starts breathing animation after 30s of inactivity
   - Activity marks from tools/responses reset timer
   - Preserves last pose when starting breathing

4. **Secondary Offset Composition**
   - Reads speech wobble offsets from HeadWobbler
   - Reads face tracking offsets from CameraWorker
   - Composes with primary pose in world frame

5. **Listening Freeze**
   - Optionally freezes antennas during user speech
   - Blends between frozen and moving states

### Control Loop

```python
def _control_loop(self):
    target_dt = 1.0 / 100.0  # 100Hz

    while self._running:
        loop_start = time.time()

        try:
            # 1. Process commands from queue
            self._process_command_queue()

            # 2. Check idle timeout
            if self._should_start_breathing():
                self._start_breathing()

            # 3. Get primary pose
            primary_pose = self._get_current_primary_pose()

            # 4. Get secondary offsets
            speech_offsets = self._wobbler.get_offsets()
            face_offsets = self._camera.get_face_offsets()

            # 5. Compose
            final_pose = self._compose_pose(primary_pose, speech_offsets, face_offsets)

            # 6. Apply listening freeze to antennas
            if self._freeze_antennas:
                final_pose = self._apply_antenna_freeze(final_pose)

            # 7. Send to robot
            self._robot.set_target(final_pose)

        except Exception as e:
            self._handle_error(e)

        # 8. Sleep for remainder of 10ms tick
        elapsed = time.time() - loop_start
        sleep_time = max(0, target_dt - elapsed)
        time.sleep(sleep_time)
```

### Key Methods

| Method | Purpose |
|--------|---------|
| `queue_command()` | Thread-safe command submission |
| `_process_command_queue()` | Execute pending commands |
| `_get_current_primary_pose()` | Get pose from current move or cache |
| `_compose_pose()` | Combine primary + secondary |
| `start()` / `stop()` | Lifecycle management |

---

## CameraWorker (`camera_worker.py`)

**Purpose:** Frame capture, buffering, and face tracking at 30Hz.

### Responsibilities

1. **Frame Capture**
   - Captures from OpenCV VideoCapture
   - Target 30fps, achieves 30-40fps typically
   - Thread-safe frame storage

2. **Face Tracking**
   - Integrates YOLO or MediaPipe tracker
   - Detects face bounding boxes
   - Computes look-at poses

3. **Offset Calculation**
   - Converts face position to robot pose
   - Extracts translation/rotation offsets
   - Smooth interpolation when face lost

4. **Frame Buffering**
   - Latest frame available to camera tool
   - Lock-protected access
   - Automatic BGR→RGB conversion for tools

### Face Tracking Flow

```python
def _tracking_loop(self):
    while self._running:
        frame = self._capture_frame()

        if self._head_tracker:
            detections = self._head_tracker.detect(frame)

            if detections:
                bbox = detections[0]  # Use first face
                face_center = self._bbox_center(bbox)

                # Convert pixel coords to 3D position
                face_pos_3d = self._unproject(face_center, estimated_depth=0.5)

                # Compute look-at pose
                look_at_pose = self._robot.compute_ik(face_pos_3d)

                # Extract offset from current pose
                offset = self._extract_offset(look_at_pose, current_pose)

                # Update offset (thread-safe)
                self._update_face_offset(offset)
            else:
                # Smooth decay when face lost
                self._decay_face_offset(decay_rate=0.9)

        self._sleep_to_maintain_fps()
```

### Integration Points

- **MovementManager:** Provides face tracking offsets
- **Camera Tool:** Provides latest frame for vision
- **Head Tracker:** Pluggable (YOLO or MediaPipe)

---

## OpenAIRealtimeHandler (`openai_realtime.py`)

**Purpose:** WebSocket connection to OpenAI Realtime API, audio streaming, tool dispatch.

### Responsibilities

1. **Session Management**
   - Establish WebSocket connection
   - Configure session (modalities, tools, voice)
   - Handle reconnection with backoff

2. **Audio Streaming**
   - **Input:** 16kHz → resample to 24kHz → send to API
   - **Output:** Receive 24kHz deltas → forward to speaker

3. **Event Handling**
   - `response.audio.delta`: Forward audio, update HeadWobbler
   - `conversation.item.completed`: Track transcripts
   - `response.function_call_arguments.done`: Dispatch tool

4. **Tool Dispatch**
   - Parse function call arguments
   - Execute tool via ToolDispatcher
   - Inject result as conversation item

5. **Idle Detection**
   - Monitor silence duration (no user speech)
   - Trigger engagement after timeout (e.g., "Are you still there?")

### Event Handler Example

```python
async def _on_audio_delta(self, event: dict):
    """Handle streaming audio from AI response"""
    delta = event.get("delta")
    if not delta:
        return

    # Decode audio
    audio_bytes = base64.b64decode(delta)

    # Send to head wobbler for motion generation
    self._head_wobbler.process_audio_delta(audio_bytes)

    # Forward to audio output (speaker)
    await self._audio_output.write(audio_bytes)
```

### Tool Call Flow

```python
async def _on_function_call_done(self, event: dict):
    """Execute tool when arguments are complete"""
    call_id = event["call_id"]
    name = event["name"]
    args = json.loads(event["arguments"])

    try:
        # Execute tool
        result = await self._tool_dispatcher.dispatch(name, args)

        # Inject result into conversation
        await self._client.conversation.item.create(
            item={
                "type": "function_call_output",
                "call_id": call_id,
                "output": result
            }
        )

        # Request AI response
        await self._client.response.create()

    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        # Send error to AI
        await self._client.conversation.item.create(
            item={
                "type": "function_call_output",
                "call_id": call_id,
                "output": f"Error: {e}"
            }
        )
```

---

## HeadWobbler (`audio/head_wobbler.py`)

**Purpose:** Convert AI audio output to head motion offsets with latency compensation.

### Key Concepts

1. **Audio Processing**
   - Receives 24kHz PCM audio deltas from OpenAI
   - Extracts envelope (smoothed amplitude)
   - Maps to head rotation angles

2. **Latency Compensation**
   - Audio has ~80ms latency before heard
   - Buffers motion offsets to sync with perceived audio
   - Configurable delay

3. **Smooth Motion**
   - Applies damping to avoid jerky movements
   - Gradual approach to target angle
   - Returns to neutral when audio stops

### Processing Pipeline

```python
def process_audio_delta(self, audio_bytes: bytes):
    """Process audio chunk and generate motion"""
    # Convert bytes to numpy array
    audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)

    # Extract envelope (smoothed amplitude)
    envelope = np.abs(audio_data)
    avg_amplitude = np.mean(envelope)

    # Map to target angle
    normalized = avg_amplitude / 32768.0  # int16 range
    target_angle = normalized * self.sensitivity  # degrees

    # Smooth approach
    current_angle = self._current_angle
    new_angle = current_angle + (target_angle - current_angle) * self.damping

    # Store offset with timestamp
    offset = {"head_rotation": new_angle}
    timestamp = time.time() + self.latency_compensation

    with self._lock:
        self._offset_buffer.append((timestamp, offset))

def get_offsets(self) -> dict:
    """Get current motion offset (called by MovementManager at 100Hz)"""
    now = time.time()

    with self._lock:
        # Remove expired offsets
        while self._offset_buffer and self._offset_buffer[0][0] < now:
            self._offset_buffer.popleft()

        # Return current offset
        if self._offset_buffer:
            return self._offset_buffer[0][1]
        else:
            return {"head_rotation": 0}  # Neutral
```

---

## Tool System (`tools/`)

**Purpose:** Extensible capabilities exposed to AI.

### Tool Base Class

```python
class Tool(ABC):
    name: str = ""  # Tool identifier
    description: str = ""  # For AI
    parameters_schema: dict = {}  # JSON schema

    @abstractmethod
    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        """
        Execute tool with given arguments.

        Args:
            args: Validated arguments from AI
            deps: Shared dependencies

        Returns:
            Result string sent back to AI
        """
        pass
```

### Tool Implementation Example

```python
@ToolRegistry.register
class DanceTool(Tool):
    name = "dance"
    description = "Make the robot dance"
    parameters_schema = {
        "type": "object",
        "properties": {
            "style": {
                "type": "string",
                "enum": ["happy", "energetic", "calm"],
                "description": "Dance style"
            }
        }
    }

    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        style = args.get("style", "happy")

        # Get dance from library
        dances = deps.movement_manager.get_dances()
        dance = self._select_dance(dances, style)

        # Queue move
        move = DanceMove(dance)
        deps.movement_manager.queue_command("queue_move", move=move)

        return f"Started {dance.name} dance!"
```

### Tool Registration

Tools auto-register via decorator:

```python
@ToolRegistry.register
class MyTool(Tool):
    name = "my_tool"
    ...
```

Then discovered at runtime:

```python
tools = ToolRegistry.get_all_tools()
for tool in tools:
    client.register_tool(tool.name, tool.description, tool.parameters_schema)
```

---

## Profile System (`profiles/`)

**Purpose:** Modular AI personalities with custom prompts and tools.

### Profile Structure

```
profiles/example/
├── instructions.txt      # Prompt with template expansion
├── tools.txt            # Whitelist of enabled tools
└── sweep_look.py        # Custom tool implementation
```

### Template Expansion

```python
# instructions.txt
You are Reachy.

[witty_identity]

Your passions:
[passion_for_lobster_jokes]

# Expands recursively:
prompts/identities/witty_identity.txt → content
prompts/passion_for_lobster_jokes.txt → content
```

### Tool Resolution

```python
def load_profile_tools(profile_name: str):
    profile_dir = Path("profiles") / profile_name
    tools_file = profile_dir / "tools.txt"

    enabled_tools = []

    for tool_name in tools_file.read_text().splitlines():
        # Check profile-local first
        custom_tool = profile_dir / f"{tool_name}.py"
        if custom_tool.exists():
            tool_class = load_module(custom_tool)
            enabled_tools.append(tool_class)
        else:
            # Fall back to shared tools
            tool_class = ToolRegistry.get_tool(tool_name)
            if tool_class:
                enabled_tools.append(tool_class)

    return enabled_tools
```

---

These components form a **cohesive system** where each part has a clear responsibility and well-defined interfaces.
