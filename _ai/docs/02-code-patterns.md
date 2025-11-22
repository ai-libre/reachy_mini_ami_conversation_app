# Code Patterns and Conventions

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## File Organization Patterns

### Module Structure

```
src/reachy_mini_conversation_app/
├─ Core modules (flat)
│  ├─ main.py              # Entry point, orchestration
│  ├─ config.py            # Environment configuration
│  ├─ openai_realtime.py   # OpenAI API handler
│  ├─ moves.py             # Movement manager
│  └─ camera_worker.py     # Camera processing
│
├─ Subpackages (cohesive features)
│  ├─ audio/               # Audio processing utilities
│  ├─ tools/               # Tool implementations
│  ├─ vision/              # Vision processing
│  ├─ profiles/            # AI personalities
│  └─ prompts/             # Prompt templates
│
└─ Supporting
   ├─ utils.py             # Shared utilities
   └─ dance_emotion_moves.py  # Move wrappers
```

**Convention:** Flat structure for main components, subpackages for feature groups.

## Common Design Patterns

### 1. Worker Thread Pattern

Used in: `MovementManager`, `CameraWorker`, `HeadWobbler`, `VisionManager`

```python
class WorkerThread:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)

    def _run_loop(self):
        while self._running:
            try:
                self._process_tick()
            except Exception as e:
                self._handle_error(e)
            self._sleep_for_next_tick()
```

**Why:** Consistent lifecycle management, clean shutdown, error isolation.

### 2. Command Queue Pattern

Used in: `MovementManager`

```python
class CommandProcessor:
    def __init__(self):
        self._command_queue: queue.Queue = queue.Queue()

    def send_command(self, command: str, **kwargs):
        """Thread-safe command submission"""
        self._command_queue.put((command, kwargs))

    def _process_commands(self):
        """Process all pending commands (in worker thread)"""
        while not self._command_queue.empty():
            try:
                command, kwargs = self._command_queue.get_nowait()
                self._execute_command(command, **kwargs)
            except queue.Empty:
                break
```

**Why:** Decouples command submission from execution, thread-safe, non-blocking.

### 3. Registry Pattern

Used in: `ToolRegistry`

```python
class ToolRegistry:
    _tools: Dict[str, Type[Tool]] = {}

    @classmethod
    def register(cls, tool_class: Type[Tool]):
        """Decorator for automatic registration"""
        cls._tools[tool_class.name] = tool_class
        return tool_class

    @classmethod
    def get_tool(cls, name: str) -> Optional[Type[Tool]]:
        return cls._tools.get(name)

# Usage:
@ToolRegistry.register
class CameraTool(Tool):
    name = "camera"
    ...
```

**Why:** Automatic discovery, extensible, no manual imports needed.

### 4. Dependency Injection

Used in: `ToolDependencies`

```python
@dataclass
class ToolDependencies:
    """Shared dependencies for all tools"""
    robot: ReachyMini
    movement_manager: MovementManager
    camera_worker: Optional[CameraWorker]
    vision_manager: Optional[VisionManager]

class Tool:
    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        # Tools receive all dependencies explicitly
        deps.movement_manager.queue_command(...)
        frame = deps.camera_worker.get_latest_frame()
```

**Why:** Testable, explicit dependencies, no global state.

### 5. Profile-Based Configuration

Used in: Profile system

```python
# Profile discovery
profile_dir = Path("profiles") / profile_name
instructions_file = profile_dir / "instructions.txt"
tools_file = profile_dir / "tools.txt"

# Template expansion
text = "[default_prompt]"
expanded = expand_template(text, profile_dir)  # Recursive expansion

# Tool resolution
shared_tools = Path("tools/")
profile_tools = profile_dir  # Override shared tools
```

**Why:** Modular personalities, no code changes for new profiles, template reuse.

### 6. Async Event Handlers

Used in: `OpenAIRealtimeHandler`

```python
async def setup_event_handlers(self):
    """Register event handlers for OpenAI API"""
    self.client.on("conversation.item.completed", self._on_item_completed)
    self.client.on("response.audio.delta", self._on_audio_delta)
    self.client.on("function_call_arguments.done", self._on_function_call)

async def _on_audio_delta(self, delta: dict):
    """Handle streaming audio from AI"""
    audio_bytes = base64.b64decode(delta["delta"])
    self.head_wobbler.process_audio_delta(audio_bytes)
    # ... forward to audio output
```

**Why:** Clean separation of concerns, easy to add new event handlers.

## Coding Conventions

### Type Hints

**Everywhere:**
```python
def get_latest_frame(self) -> Optional[np.ndarray]:
    """Returns latest camera frame or None"""
    with self._lock:
        return self._latest_frame.copy() if self._latest_frame is not None else None
```

**Why:** Type safety, IDE support, mypy validation.

### Logging

**Structured logging with context:**
```python
logger.info(f"Starting camera worker (fps={self._target_fps})")
logger.debug(f"Face detected at ({x}, {y})")
logger.error(f"Failed to capture frame: {e}")
```

**Rate-limited for high-frequency:**
```python
if time.time() - self._last_error_log > 1.0:
    logger.error(f"Control loop error: {e}")
    self._last_error_log = time.time()
```

### Error Handling

**Critical paths (don't crash):**
```python
try:
    self._update_robot_pose()
except Exception as e:
    logger.error(f"Movement error: {e}", exc_info=True)
    self._safe_fallback_pose()  # Return to known good state
```

**Non-critical (fail fast):**
```python
def execute_tool(self, name: str):
    tool = self.registry.get_tool(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")  # Let caller handle
    return tool.execute()
```

### Configuration

**Environment-based with defaults:**
```python
class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-realtime")
    HEAD_TRACKER: Optional[str] = os.getenv("HEAD_TRACKER")  # None = disabled

    def validate(self):
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required")
```

### Docstrings

**Module-level:**
```python
"""
Movement manager for Reachy Mini robot.

Runs a 100Hz control loop that:
1. Processes command queue
2. Updates primary move sequence
3. Composes secondary offsets
4. Sends targets to robot
"""
```

**Function-level (when non-obvious):**
```python
def compose_world_offset(base_pose: dict, offsets: dict) -> dict:
    """
    Compose pose with world-frame offsets.

    Args:
        base_pose: Primary pose (dance, emotion, etc.)
        offsets: Dict of offset poses (speech, tracking)

    Returns:
        Composed pose with all offsets applied
    """
```

## Common Idioms

### Thread-Safe Property Access

```python
@property
def latest_frame(self) -> Optional[np.ndarray]:
    with self._lock:
        return self._frame.copy() if self._frame is not None else None

@latest_frame.setter
def latest_frame(self, frame: np.ndarray):
    with self._lock:
        self._frame = frame
```

### Optional Dependency Handling

```python
if self._camera_worker is not None:
    frame = self._camera_worker.get_latest_frame()
else:
    return "Camera not available"
```

### Graceful Cleanup

```python
def cleanup(self):
    """Stop all services in reverse startup order"""
    components = [
        ("vision_manager", self._vision_manager),
        ("camera_worker", self._camera_worker),
        ("head_wobbler", self._head_wobbler),
        ("movement_manager", self._movement_manager),
    ]

    for name, component in components:
        if component:
            try:
                component.stop()
                logger.info(f"Stopped {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
```

### Retry with Backoff

```python
async def connect_with_retry(self, max_retries: int = 4):
    for attempt in range(max_retries):
        try:
            await self._connect()
            return
        except Exception as e:
            delay = 2 ** attempt  # Exponential backoff
            logger.warning(f"Connection failed (attempt {attempt+1}), retrying in {delay}s")
            await asyncio.sleep(delay)
    raise ConnectionError("Max retries exceeded")
```

## Anti-Patterns to Avoid

### ❌ Global State

```python
# Bad
current_robot = None

def set_robot(robot):
    global current_robot
    current_robot = robot
```

**Why:** Hard to test, implicit dependencies, race conditions.

### ❌ Blocking in Async Functions

```python
# Bad
async def process():
    time.sleep(1)  # Blocks event loop!
```

**Use:** `await asyncio.sleep(1)`

### ❌ Catching All Exceptions Silently

```python
# Bad
try:
    critical_operation()
except:
    pass  # Silent failure!
```

**Use:** Specific exceptions, always log.

### ❌ Mutable Default Arguments

```python
# Bad
def add_move(moves=[]):
    moves.append(...)  # Shared across calls!
```

**Use:** `def add_move(moves=None): moves = moves or []`

## Testing Patterns

### Mock External Dependencies

```python
@pytest.fixture
def mock_robot():
    return MagicMock(spec=ReachyMini)

def test_movement_manager(mock_robot):
    manager = MovementManager(robot=mock_robot)
    manager.queue_command("goto_pose", pose={...})
    assert mock_robot.set_target.called
```

### Async Test Utilities

```python
@pytest.mark.asyncio
async def test_openai_handler():
    handler = OpenAIRealtimeHandler(...)
    await handler.connect()
    assert handler.is_connected()
```

---

These patterns create a **consistent**, **maintainable**, and **testable** codebase that scales well with added features.
