# Tool System Design Analysis

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Philosophy: AI as Orchestrator

The tool system embodies a key insight: **The AI doesn't control the robot directly; it orchestrates pre-built capabilities.**

### Why This Matters

**Bad Approach:**
```python
# AI generates arbitrary robot commands
tool: "set_joint_angle"
args: {"joint": "neck_pitch", "angle": 23.5}
```

**Problems:**
- AI must understand kinematics
- Unsafe poses possible
- No artistic control over motion
- Brittle (breaks with robot changes)

**This Approach:**
```python
# AI selects from curated behaviors
tool: "dance"
args: {}  # Implementation handles all details
```

**Advantages:**
- AI focuses on intent, not mechanics
- Behaviors are safe and tested
- Artists/engineers control aesthetics
- Robot-agnostic (tool adapts to hardware)

## Tool Lifecycle

### 1. Definition

```python
@ToolRegistry.register
class CameraTool(Tool):
    name = "camera"
    description = "Capture and analyze what you see through your camera"
    parameters_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "What to look for or analyze in the image"
            }
        },
        "required": ["prompt"]
    }
```

**Key Components:**
- **name:** Identifier (must match tool call from AI)
- **description:** Shown to AI (influences when tool is used)
- **parameters_schema:** JSON Schema (validates args)

### 2. Registration

```python
class ToolRegistry:
    _tools: Dict[str, Type[Tool]] = {}

    @classmethod
    def register(cls, tool_class: Type[Tool]):
        cls._tools[tool_class.name] = tool_class
        return tool_class
```

**Mechanism:**
- Decorator pattern for auto-registration
- No manual imports needed
- Discover all tools at runtime

### 3. Profile Filtering

```python
# profiles/example/tools.txt
camera
dance
play_emotion
sweep_look  # Profile-specific tool

# Load process
def load_profile_tools(profile_name: str):
    enabled = read_tools_txt(profile_name)

    tools = []
    for tool_name in enabled:
        # Check profile-local first
        custom = load_custom_tool(profile_name, tool_name)
        if custom:
            tools.append(custom)
        else:
            # Fall back to shared tools
            tools.append(ToolRegistry.get_tool(tool_name))

    return tools
```

**Why Filter:**
- Control AI capabilities per personality
- Simpler prompts (fewer options = clearer intent)
- Profile-specific behaviors (e.g., emotion_reader profile)

### 4. OpenAI Registration

```python
# Convert to OpenAI function definition
for tool in profile_tools:
    client.session.update(
        session={
            "tools": [{
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_schema
            }]
        }
    )
```

**Effect:** AI now knows these tools exist and when to use them.

### 5. Execution

```python
# OpenAI event: response.function_call_arguments.done
async def _on_function_call(event: dict):
    call_id = event["call_id"]
    name = event["name"]
    args = json.loads(event["arguments"])

    # Dispatch to tool
    result = await tool_dispatcher.dispatch(name, args, deps)

    # Return result to AI
    client.conversation.item.create({
        "type": "function_call_output",
        "call_id": call_id,
        "output": result
    })
```

## Tool Implementation Patterns

### Pattern 1: Stateless Tool

No persistent state; pure function of inputs.

```python
class MoveHeadTool(Tool):
    name = "move_head"

    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        direction = args["direction"]  # "left", "right", "up", "down"

        # Create single-frame goto move
        pose = self._direction_to_pose(direction)
        move = GotoMove(pose, duration_ms=1000)

        # Queue move
        deps.movement_manager.queue_command("queue_move", move=move)

        return f"Moving head {direction}"
```

**Characteristics:**
- No `__init__` state
- Inputs → outputs only
- Thread-safe by default

### Pattern 2: Stateful Tool (with Shared State)

Accesses shared state through dependencies.

```python
class HeadTrackingTool(Tool):
    name = "head_tracking"

    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        enable = args["enable"]  # boolean

        if not deps.camera_worker:
            return "Camera not available"

        # Toggle tracking in shared state
        deps.camera_worker.set_tracking_enabled(enable)

        if enable:
            return "Face tracking enabled"
        else:
            return "Face tracking disabled"
```

**Characteristics:**
- Modifies shared state (CameraWorker)
- State persists across tool calls
- Thread-safe through deps' internal locks

### Pattern 3: Async Tool (I/O Bound)

Performs async operations (vision, network).

```python
class CameraTool(Tool):
    name = "camera"

    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        prompt = args["prompt"]

        # Get latest frame (from thread-safe buffer)
        frame = deps.camera_worker.get_latest_frame()
        if frame is None:
            return "No camera frame available"

        # Async vision processing
        if deps.vision_manager:
            # Local VLM
            description = await deps.vision_manager.process(frame, prompt)
        else:
            # Cloud GPT-4V
            description = await self._process_with_gpt4v(frame, prompt)

        return description
```

**Characteristics:**
- Uses `await` for I/O
- Non-blocking (event loop continues)
- Error handling for network/model failures

### Pattern 4: Profile-Specific Tool

Custom tool in profile directory.

```python
# profiles/example/sweep_look.py
class SweepLookTool(Tool):
    name = "sweep_look"
    description = "Sweep head left to right to scan the environment"

    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        # Create sequence of goto moves
        left_pose = {"neck_yaw": -30.0}
        center_pose = {"neck_yaw": 0.0}
        right_pose = {"neck_yaw": 30.0}

        moves = [
            GotoMove(left_pose, duration_ms=1000),
            GotoMove(right_pose, duration_ms=2000),  # Sweep across
            GotoMove(center_pose, duration_ms=1000),  # Return
        ]

        for move in moves:
            deps.movement_manager.queue_command("queue_move", move=move)

        return "Sweeping view across environment"
```

**Characteristics:**
- Lives in profile directory
- Overrides shared tool if same name
- Profile-specific behavior

## Dependency Injection Deep Dive

### Why Dependency Injection?

**Without DI (global state):**
```python
# Global variables
robot = None
movement_manager = None

class DanceTool(Tool):
    async def execute(self, args: dict) -> str:
        global movement_manager
        movement_manager.queue_command(...)  # Uh oh, what if None?
```

**Problems:**
- Hard to test (can't mock)
- Implicit dependencies (unclear what tool needs)
- Race conditions (globals)
- Initialization order matters

**With DI:**
```python
@dataclass
class ToolDependencies:
    robot: ReachyMini
    movement_manager: MovementManager
    camera_worker: Optional[CameraWorker]
    vision_manager: Optional[VisionManager]

class DanceTool(Tool):
    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        deps.movement_manager.queue_command(...)  # Guaranteed to exist
```

**Advantages:**
- Explicit dependencies
- Easy to test (pass mock deps)
- Thread-safe (no globals)
- Type-checked (mypy knows types)

### Dependency Construction

```python
# In main.py
def main():
    # Initialize components
    robot = ReachyMini()
    movement_manager = MovementManager(robot)
    camera_worker = CameraWorker(robot) if not args.no_camera else None
    vision_manager = VisionManager() if args.local_vision else None

    # Bundle dependencies
    deps = ToolDependencies(
        robot=robot,
        movement_manager=movement_manager,
        camera_worker=camera_worker,
        vision_manager=vision_manager,
    )

    # Pass to tool dispatcher
    dispatcher = ToolDispatcher(deps)

    # Tools now have access to all dependencies
    result = await dispatcher.dispatch("camera", {"prompt": "..."})
```

## Tool Discovery & Dynamic Loading

### Shared Tools Discovery

```python
# tools/__init__.py auto-imports all tools
from .camera import CameraTool
from .dance import DanceTool
from .play_emotion import PlayEmotionTool
# ... etc

# Each tool @ToolRegistry.register decorator runs
# Result: All tools registered before main() runs
```

### Profile Tools Discovery

```python
def load_custom_tool(profile_dir: Path, tool_name: str) -> Optional[Type[Tool]]:
    tool_file = profile_dir / f"{tool_name}.py"

    if not tool_file.exists():
        return None

    # Dynamic import
    spec = importlib.util.spec_from_file_location(tool_name, tool_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find Tool subclass in module
    for item in dir(module):
        obj = getattr(module, item)
        if isinstance(obj, type) and issubclass(obj, Tool) and obj != Tool:
            return obj

    return None
```

**Power:** New tools added by dropping `.py` file in profile folder. No code changes needed.

## Error Handling Strategy

### Tool-Level Errors

```python
class CameraTool(Tool):
    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        try:
            frame = deps.camera_worker.get_latest_frame()
            if frame is None:
                return "Error: Camera not available"

            description = await self._process_vision(frame, args["prompt"])
            return description

        except Exception as e:
            logger.error(f"Camera tool failed: {e}", exc_info=True)
            return f"Error: {str(e)}"
```

**Philosophy:** Tools return error strings, don't raise exceptions. AI can handle errors conversationally.

### Dispatcher-Level Errors

```python
class ToolDispatcher:
    async def dispatch(self, name: str, args: dict, deps: ToolDependencies) -> str:
        tool_class = ToolRegistry.get_tool(name)

        if not tool_class:
            return f"Error: Unknown tool '{name}'"

        try:
            tool = tool_class()
            result = await tool.execute(args, deps)
            return result

        except Exception as e:
            logger.error(f"Tool {name} crashed: {e}", exc_info=True)
            return f"Error: Tool {name} failed: {str(e)}"
```

**Why:** Even if tool crashes, conversation continues. AI sees error message and can respond ("Sorry, I couldn't capture an image").

## Tool Descriptions: Guiding AI Behavior

### Good Tool Descriptions

```python
# ✅ Clear, actionable, specific
description = "Capture and analyze what you see through your camera. Use this when the user asks what you see, or to identify objects, people, or emotions."

# ✅ Includes when to use
description = "Play an emotion animation. Use this to express feelings like happiness, sadness, or surprise."

# ✅ Describes outcome
description = "Move your head to look in a direction. After moving, your head will point left/right/up/down."
```

### Bad Tool Descriptions

```python
# ❌ Too vague
description = "Camera tool"

# ❌ Implementation details
description = "Captures frame from cv2.VideoCapture and sends to GPT-4V API"

# ❌ Missing context
description = "Dance"  # When should this be used?
```

**Impact:** Good descriptions drastically improve AI's tool selection accuracy.

## Advanced: Tool Chaining

AI can chain multiple tools to accomplish complex tasks.

**User:** "Look around and tell me what you see"

**AI's Plan:**
1. Call `sweep_look` (scan environment)
2. Wait for sweep to complete
3. Call `camera` with prompt "describe the environment"
4. Speak description to user

**Actual Execution:**
```
AI: <calls sweep_look tool>
Tool: "Sweeping view across environment"

AI: <waits ~3 seconds while sweep plays>

AI: <calls camera tool with prompt="describe the environment">
Tool: "I see a well-lit office with a desk, computer, and a person sitting nearby."

AI: <speaks to user>
"I can see you're in a well-lit office with a desk and computer."
```

**Mechanism:** OpenAI Realtime API handles the orchestration. Each tool call completes before next is issued.

## Performance Considerations

### Tool Latency Budget

| Tool | Typical Latency | Type |
|------|----------------|------|
| `dance` | <1ms | Instant (queue command) |
| `play_emotion` | <1ms | Instant (queue command) |
| `move_head` | <1ms | Instant (queue command) |
| `head_tracking` | <1ms | Instant (toggle flag) |
| `camera` (cloud) | 500-2000ms | Network I/O |
| `camera` (local) | 100-500ms | GPU compute |
| `stop_dance` | <1ms | Instant (clear queue) |
| `do_nothing` | <1ms | Instant (noop) |

**Design Implication:** Quick tools (movement commands) are instant. Slow tools (vision) are async and don't block.

### Async Best Practices

```python
# ✅ Good: Truly async
async def execute(self, args: dict, deps: ToolDependencies) -> str:
    result = await some_async_operation()
    return result

# ❌ Bad: Blocking in async function
async def execute(self, args: dict, deps: ToolDependencies) -> str:
    time.sleep(2)  # Blocks event loop!
    return "done"

# ✅ Good: If blocking is unavoidable, use executor
async def execute(self, args: dict, deps: ToolDependencies) -> str:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, blocking_function)
    return result
```

---

## Key Insights

1. **Tools are the robot's API:** They define what the AI can do
2. **Descriptions matter:** They guide AI's decision-making
3. **Dependency injection:** Enables testing and clear contracts
4. **Error handling:** Tools return strings, don't crash
5. **Profile system:** Allows tool customization without code changes

This tool system makes the AI **powerful but constrained** — exactly what you want in a robot control system.
