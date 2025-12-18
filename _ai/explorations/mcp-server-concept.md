# MCP Server for Reachy Robot Control - Deep Exploration

**Created:** 2025-12-18 06:39:12 UTC
**Last Updated:** 2025-12-18 06:39:12 UTC

## The Big Idea

Create an **MCP (Model Context Protocol) server** that exposes Reachy Mini robot control capabilities to Claude Desktop, Claude Code, and other MCP-compatible clients. This would enable **natural language robot control** from any MCP host without needing the full realtime conversation app.

### Vision Statement

> "Control your Reachy Mini robot through conversational AI in Claude Desktop, just like you would through specialized software - but with the flexibility of natural language understanding built into your daily AI assistant."

## Conceptual Architecture

### Current System (Baseline)

```
User Voice
    ↓
OpenAI Realtime API (WebSocket)
    ↓
Tool Dispatcher
    ↓
Robot Control (MovementManager, etc.)
    ↓
Reachy Mini Hardware
```

**Characteristics:**
- Standalone application
- Real-time audio conversation
- Tightly coupled to OpenAI Realtime API
- Runs as dedicated process
- Full control over UX

### Proposed MCP Architecture

```
Claude Desktop/Code (MCP Host)
    ↓
MCP Protocol (JSON-RPC over stdio/HTTP)
    ↓
Reachy MCP Server
    ├─► Tools (Actions)
    ├─► Resources (Status/Telemetry)
    ├─► Prompts (Common Tasks)
    └─► Sampling (Autonomous Behaviors)
    ↓
Robot Control Layer (Reuse existing code!)
    ↓
Reachy Mini Hardware
```

**Characteristics:**
- Plugin/extension model
- Text-based interaction (with potential for multimodal)
- Host-agnostic (works with any MCP client)
- Runs as background service
- Host controls UX

## Deep Analysis: Why This Is Brilliant

### 1. **Separation of Concerns**

Current system: **Monolithic**
```
[Conversation UI + AI Integration + Robot Control] = One App
```

MCP approach: **Modular**
```
[Claude Desktop UI] ←MCP→ [Robot Control Server] → [Reachy Mini]
```

**Benefits:**
- Robot control becomes a **reusable service**
- Multiple frontends can use same backend
- Easier testing (mock MCP client)
- Independent deployment/updates

### 2. **Native Integration with Daily Workflow**

**Current:** Open dedicated app, start conversation
**MCP:** Robot control available in Claude Desktop alongside all your other tools

**Scenario:**
```
You're coding in Claude Desktop:
"Claude, move the robot to look at my screen"
[Robot head turns toward your monitor]

"Now grab that object on my desk"
[Robot gripper activates]

"Great, now continue helping me with this Python bug..."
[Seamlessly back to coding]
```

**The robot becomes just another tool** in your AI toolkit, like filesystem access or web search.

### 3. **Complementary to Existing System**

**Not a replacement** - these systems serve different purposes:

| Use Case | Best System |
|----------|-------------|
| **Real-time conversation partner** | Current app (OpenAI Realtime) |
| **Quick robot commands during work** | MCP server (Claude Desktop) |
| **Autonomous task execution** | MCP sampling capability |
| **Low-latency audio-reactive motion** | Current app (HeadWobbler) |
| **Scripted automation** | MCP tools + prompts |

### 4. **Opens New Interaction Paradigms**

#### A. Multi-Step Autonomous Tasks (MCP Sampling)

```
User: "Survey the room and catalog what you see"

MCP Server initiates sampling:
├─ Call Claude: "Plan a room survey pattern"
├─ Execute: move_head("left")
├─ Execute: capture_camera()
├─ Call Claude: "Analyze this view"
├─ Execute: move_head("center")
├─ Execute: capture_camera()
├─ Call Claude: "Analyze this view"
├─ Execute: move_head("right")
├─ Execute: capture_camera()
├─ Call Claude: "Analyze this view"
└─ Call Claude: "Synthesize all views into room description"

Returns: "The room contains a desk with computer,
         bookshelf with 15 books, and a person sitting..."
```

**This is impossible with current tool-only architecture** - requires server-initiated LLM calls.

#### B. Persistent Context (MCP Resources)

```
Resources exposed:
- reachy://status/joints        (Current joint angles)
- reachy://status/battery       (Power levels)
- reachy://config/limits        (Joint constraints)
- reachy://history/movements    (Recent actions log)
- reachy://camera/latest-frame  (Current view)
```

Claude can **proactively reference** this context:
```
User: "Can the robot reach that object?"

Claude (internally):
├─ Reads reachy://status/joints (current position)
├─ Reads reachy://config/limits (reach envelope)
├─ Estimates object position from context
└─ Calculates: "No, that's 85cm away, max reach is 60cm"

Response: "Unfortunately, that object is beyond my reach
           envelope. I can reach up to 60cm from my base."
```

#### C. Reusable Prompt Templates

```
Prompts:
- "Greet visitor" → Full greeting choreography
- "Search for object" → Systematic visual scan
- "Return to home" → Safe idle position
- "Emergency stop" → Immediate halt + safe state
```

Users can invoke these with one click or quick command.

## Tool Design Deep Dive

### Core Tools (Essential)

#### 1. **Movement Tools**

```json
{
  "name": "move_head",
  "description": "Move robot head to look in a direction",
  "inputSchema": {
    "type": "object",
    "properties": {
      "direction": {
        "type": "string",
        "enum": ["left", "right", "up", "down", "front"],
        "description": "Direction to look"
      },
      "speed": {
        "type": "number",
        "minimum": 0.1,
        "maximum": 1.0,
        "default": 0.5,
        "description": "Movement speed (0.1=slow, 1.0=fast)"
      }
    },
    "required": ["direction"]
  }
}
```

**Implementation reuses existing code:**
```python
from reachy_mini_conversation_app.tools.move_head import MoveHeadTool

async def move_head_mcp(direction: str, speed: float = 0.5):
    # Delegate to existing tool
    tool = MoveHeadTool()
    result = await tool.execute(
        {"direction": direction, "speed": speed},
        deps  # Shared dependencies
    )
    return result
```

#### 2. **Vision Tools**

```json
{
  "name": "analyze_view",
  "description": "Capture and analyze what robot sees through camera",
  "inputSchema": {
    "type": "object",
    "properties": {
      "question": {
        "type": "string",
        "description": "What to analyze (e.g., 'What emotion is this person showing?')"
      },
      "use_local_vision": {
        "type": "boolean",
        "default": false,
        "description": "Use local VLM (private) vs cloud GPT-4V (more accurate)"
      }
    },
    "required": ["question"]
  }
}
```

**Again, reuses existing camera tool infrastructure.**

#### 3. **Motion Sequence Tools**

```json
{
  "name": "execute_dance",
  "description": "Perform a dance from the library",
  "inputSchema": {
    "type": "object",
    "properties": {
      "dance_name": {
        "type": "string",
        "description": "Name of dance (use list_dances to see options)"
      }
    },
    "required": ["dance_name"]
  }
}
```

```json
{
  "name": "list_dances",
  "description": "Get list of available dances",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

#### 4. **Emotion Expression**

```json
{
  "name": "express_emotion",
  "description": "Play an emotion animation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "emotion": {
        "type": "string",
        "enum": ["happy", "sad", "surprised", "thinking", "excited"],
        "description": "Emotion to express"
      }
    },
    "required": ["emotion"]
  }
}
```

#### 5. **Safety Controls**

```json
{
  "name": "emergency_stop",
  "description": "IMMEDIATELY halt all motion and enter safe state",
  "inputSchema": {
    "type": "object",
    "properties": {
      "reason": {
        "type": "string",
        "description": "Why emergency stop was triggered (for logging)"
      }
    }
  }
}
```

**Critical safety feature** - must be low-latency.

### Advanced Tools (Power Features)

#### 6. **Face Tracking**

```json
{
  "name": "set_face_tracking",
  "description": "Enable/disable automatic face following",
  "inputSchema": {
    "type": "object",
    "properties": {
      "enabled": {"type": "boolean"},
      "tracking_mode": {
        "type": "string",
        "enum": ["yolo", "mediapipe"],
        "default": "yolo"
      }
    },
    "required": ["enabled"]
  }
}
```

#### 7. **Custom Movement Sequences**

```json
{
  "name": "execute_custom_sequence",
  "description": "Execute a programmed sequence of movements",
  "inputSchema": {
    "type": "object",
    "properties": {
      "sequence": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "action": {"type": "string"},
            "params": {"type": "object"},
            "delay_ms": {"type": "number"}
          }
        }
      }
    }
  }
}
```

**Example use:**
```javascript
execute_custom_sequence({
  sequence: [
    {action: "move_head", params: {direction: "left"}, delay_ms: 1000},
    {action: "analyze_view", params: {question: "What's here?"}, delay_ms: 500},
    {action: "move_head", params: {direction: "right"}, delay_ms: 1000},
    {action: "move_head", params: {direction: "front"}, delay_ms: 500}
  ]
})
```

## Resource Design Deep Dive

### Dynamic Robot State

```
reachy://status/current
├─ joints: {neck_pitch: 10.5, neck_yaw: -5.2, ...}
├─ battery: {percentage: 78, voltage: 12.4V, charging: false}
├─ temperature: {cpu: 45C, motors: 38C}
├─ camera: {fps: 30, resolution: "1280x720", active: true}
└─ errors: []
```

**Implementation:**
```python
@mcp.resource("reachy://status/current")
async def get_current_status():
    return {
        "uri": "reachy://status/current",
        "mimeType": "application/json",
        "text": json.dumps({
            "joints": robot.get_joint_positions(),
            "battery": robot.get_battery_status(),
            # ... etc
        }, indent=2)
    }
```

Claude can read this **proactively** before executing commands.

### Movement History

```
reachy://history/recent-movements?limit=10
```

Returns last 10 movements with timestamps, useful for:
- "Undo last movement"
- "Repeat what you just did"
- Debugging motion sequences

### Configuration Schemas

```
reachy://config/joint-limits
├─ neck_pitch: {min: -45, max: 45, speed_limit: 60}
├─ neck_yaw: {min: -90, max: 90, speed_limit: 80}
└─ ...
```

Claude can validate commands **before execution**:
```
User: "Look straight up at the ceiling"
Claude checks reachy://config/joint-limits
Claude: "I can only tilt my head 45° upward due to mechanical limits.
         Should I move to maximum upward angle?"
```

### Camera Feed (Multimodal!)

```
reachy://camera/stream
```

**Future possibility:** If MCP supports image/video resources (likely soon), Claude Desktop could **see what the robot sees in real-time**.

```
User: "What am I holding?"
Claude:
├─ Reads reachy://camera/stream (gets image)
├─ Analyzes with vision
└─ "You're holding a coffee mug with a blue handle"
```

## Prompt Templates Design

### 1. **Quick Actions**

```
Prompt: "greet-visitor"
Template: |
  Execute the following greeting sequence:
  1. Move head to face forward
  2. Wave animation if available
  3. Express 'happy' emotion
  4. Say hello via TTS if equipped
```

### 2. **Diagnostic Routines**

```
Prompt: "system-check"
Template: |
  Perform complete robot system check:
  1. Read all joint positions
  2. Check battery status
  3. Test camera functionality
  4. Verify face tracking works
  5. Test one dance move
  6. Return comprehensive status report
```

### 3. **Situational Awareness**

```
Prompt: "where-am-i"
Template: |
  Using camera and vision:
  1. Capture current view
  2. Analyze environment type (office/home/lab/etc)
  3. Identify notable objects
  4. Detect if people present
  5. Provide situational summary
```

### 4. **Emergency Procedures**

```
Prompt: "safe-shutdown"
Template: |
  Safely prepare robot for shutdown:
  1. Stop all current movements
  2. Move to neutral/home position
  3. Disable face tracking
  4. Close camera feed
  5. Log shutdown time
  6. Confirm ready for power-off
```

## MCP Sampling: Autonomous Behaviors

**Sampling** is MCP's most powerful feature - server can **initiate LLM calls** to implement multi-step reasoning.

### Example: Object Search

```python
@mcp.sampling_handler
async def search_for_object(object_name: str):
    """
    Autonomous multi-step object search.

    Uses sampling to let Claude plan and execute search pattern.
    """

    # Initial planning call
    plan = await client.sample(
        messages=[{
            "role": "user",
            "content": f"Plan a systematic search pattern to find a {object_name}. "
                      f"Robot has 180° horizontal view, 90° vertical. "
                      f"Return JSON with search positions."
        }]
    )

    search_positions = json.loads(plan)

    # Execute search
    for pos in search_positions:
        # Move head
        await move_head(pos['direction'])
        await asyncio.sleep(0.5)  # Stabilize

        # Capture and analyze
        frame = camera_worker.get_latest_frame()

        # Ask Claude if object found
        result = await client.sample(
            messages=[{
                "role": "user",
                "content": f"Is there a {object_name} in this image?",
                "images": [encode_image(frame)]
            }]
        )

        if "yes" in result.lower():
            return {
                "found": True,
                "position": pos,
                "description": result
            }

    return {
        "found": False,
        "searched_positions": len(search_positions)
    }
```

**User experience:**
```
User: "Find my coffee mug"

[Robot autonomously]:
- Plans search pattern
- Looks left, analyzes
- Looks center, analyzes
- Looks right, analyzes ← Finds it!

Response: "Found your coffee mug on the right side of your desk,
           next to the lamp. It appears to be a blue ceramic mug."
```

### Example: Gesture-Based Interaction

```python
@mcp.sampling_handler
async def wait_for_gesture():
    """
    Wait for user gesture and respond appropriately.

    Uses continuous sampling to interpret gestures.
    """

    while True:
        frame = camera_worker.get_latest_frame()

        # Ask Claude to interpret
        interpretation = await client.sample(
            messages=[{
                "role": "user",
                "content": "Analyze this image. Is the person making any gesture "
                          "(wave, thumbs up, pointing, etc)? If yes, describe it. "
                          "If no gesture, respond 'NONE'."
                images: [encode_image(frame)]
            }]
        )

        if interpretation != "NONE":
            # Respond to gesture
            response = await client.sample(
                messages=[{
                    "role": "user",
                    "content": f"User made this gesture: {interpretation}. "
                              f"What's an appropriate robot response? "
                              f"Choose from: wave, thumbs_up, nod, dance, express_emotion"
                }]
            )

            # Execute response
            await execute_action_from_text(response)
            return interpretation

        await asyncio.sleep(0.5)
```

## Security & Safety Analysis

### Critical Safety Considerations

#### 1. **Rate Limiting (Essential for Hardware)**

```python
class RateLimiter:
    def __init__(self, max_commands_per_minute: int = 30):
        self.limit = max_commands_per_minute
        self.commands = deque(maxlen=max_commands_per_minute)

    def check_allowed(self) -> bool:
        now = time.time()

        # Remove commands older than 60s
        while self.commands and now - self.commands[0] > 60:
            self.commands.popleft()

        if len(self.commands) >= self.limit:
            return False

        self.commands.append(now)
        return True
```

**Why:** Prevent rapid command sequences that could:
- Overheat motors
- Damage mechanical components
- Drain battery rapidly
- Create dangerous situations

#### 2. **User Confirmation for Dangerous Operations**

```python
DANGEROUS_OPERATIONS = [
    "execute_custom_sequence",
    "move_at_high_speed",
    "extended_movement"
]

@mcp.tool
async def execute_custom_sequence(sequence):
    # Require explicit confirmation
    confirmation = await mcp.request_confirmation(
        prompt=f"Execute sequence with {len(sequence)} steps?\n"
               f"Preview: {json.dumps(sequence, indent=2)}",
        dangerous=True
    )

    if not confirmation:
        return "User cancelled sequence execution"

    # Execute with monitoring
    return await run_sequence_with_safety_checks(sequence)
```

#### 3. **Workspace Boundaries**

```python
class WorkspaceBoundary:
    """Prevent robot from moving outside safe zone"""

    def __init__(self):
        self.safe_zone = {
            'x_min': -0.3, 'x_max': 0.3,
            'y_min': -0.3, 'y_max': 0.3,
            'z_min': 0.0,  'z_max': 0.5
        }

    def is_safe_position(self, x, y, z) -> bool:
        return (
            self.safe_zone['x_min'] <= x <= self.safe_zone['x_max'] and
            self.safe_zone['y_min'] <= y <= self.safe_zone['y_max'] and
            self.safe_zone['z_min'] <= z <= self.safe_zone['z_max']
        )

    def validate_movement(self, target_pose) -> bool:
        # Calculate end-effector position
        position = forward_kinematics(target_pose)

        if not self.is_safe_position(*position):
            raise SafetyError(f"Movement would exit safe workspace: {position}")

        return True
```

#### 4. **Emergency Stop Always Available**

```python
# Global emergency stop flag (thread-safe)
emergency_stop_active = threading.Event()

def check_emergency_stop():
    """Check before every movement"""
    if emergency_stop_active.is_set():
        raise EmergencyStopError("Emergency stop activated")

@mcp.tool(priority="highest")
async def emergency_stop(reason: str = "User initiated"):
    """Immediate halt - highest priority tool"""
    logger.critical(f"EMERGENCY STOP: {reason}")

    emergency_stop_active.set()

    # Stop all motion
    movement_manager.emergency_halt()

    # Move to safe position
    await move_to_safe_pose()

    # Disable all tracking
    camera_worker.disable_tracking()

    return f"Emergency stop activated: {reason}"
```

#### 5. **Audit Logging**

```python
class RobotCommandLogger:
    def __init__(self, log_file: str = "robot_commands.jsonl"):
        self.log_file = log_file

    def log_command(self, command: str, args: dict, result: str, user: str):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command,
            "arguments": args,
            "result": result,
            "user": user,
            "safety_checks_passed": True
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
```

**Every command logged for:**
- Safety audits
- Incident investigation
- Usage analytics
- Debugging

### Network Security

#### Recommended Transport: stdio (Local Only)

```json
{
  "mcpServers": {
    "reachy-robot": {
      "command": "python",
      "args": ["-m", "reachy_mcp_server"],
      "env": {
        "ROBOT_IP": "192.168.1.100",
        "SAFETY_MODE": "strict"
      }
    }
  }
}
```

**Benefits:**
- No network exposure
- OS-level security (process isolation)
- Fast (microsecond latency)
- Simple setup

**Only for:** Same machine as Claude Desktop

#### Alternative: HTTP + Authentication (Remote Access)

```python
app = FastAPI()

@app.middleware("http")
async def verify_auth_token(request: Request, call_next):
    token = request.headers.get("Authorization")

    if not verify_token(token):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"}
        )

    return await call_next(request)

# TLS required
uvicorn.run(app,
    host="0.0.0.0",
    port=8443,
    ssl_certfile="cert.pem",
    ssl_keyfile="key.pem"
)
```

**Only if:** Remote robot control needed (advanced use case)

## Implementation Strategy

### Phase 1: Minimal Viable MCP Server

**Goal:** Basic robot control from Claude Desktop

**Features:**
- 5 core tools: move_head, analyze_view, execute_dance, express_emotion, emergency_stop
- 2 resources: reachy://status/current, reachy://config/limits
- stdio transport (local only)
- Safety: rate limiting + emergency stop

**Code reuse:**
```
reachy_mcp_server/
├── __init__.py
├── server.py              # MCP server setup
├── tools/
│   ├── movement.py        # Wraps existing MoveHeadTool, etc.
│   ├── vision.py          # Wraps CameraTool
│   └── safety.py          # Emergency stop, validation
├── resources/
│   └── status.py          # Robot state resources
└── bridge.py              # Connects to existing robot control
```

**Bridging to existing code:**
```python
# Import existing infrastructure
from reachy_mini_conversation_app.moves import MovementManager
from reachy_mini_conversation_app.camera_worker import CameraWorker
from reachy_mini_conversation_app.tools.core_tools import ToolDependencies

# Initialize shared components
robot = ReachyMini()
movement_manager = MovementManager(robot)
camera_worker = CameraWorker(robot)

deps = ToolDependencies(
    robot=robot,
    movement_manager=movement_manager,
    camera_worker=camera_worker,
    vision_manager=None  # Optional
)

# MCP tools delegate to existing tools
@mcp.tool()
async def move_head(direction: str):
    from reachy_mini_conversation_app.tools.move_head import MoveHeadTool
    tool = MoveHeadTool()
    return await tool.execute({"direction": direction}, deps)
```

**Estimated effort:** ~3-5 days

### Phase 2: Advanced Features

**Add:**
- Remaining tools (face tracking, custom sequences)
- Prompt templates (greet-visitor, system-check, etc.)
- More resources (movement history, camera stream)
- Enhanced safety (workspace boundaries, confirmation dialogs)

**Estimated effort:** ~5-7 days

### Phase 3: Sampling Capabilities

**Add:**
- Autonomous search behaviors
- Multi-step task execution
- Gesture recognition
- Contextual awareness

**Estimated effort:** ~7-10 days (requires careful testing)

## Claude Desktop vs Claude Code: Key Differences

### Claude Desktop Use Case

**Environment:** Daily AI assistant
**Interaction:** Conversational, ad-hoc commands
**Context:** General purpose work

**Example workflows:**
```
While writing email:
"Claude, have the robot wave at the camera for a fun photo"

During coding:
"Check if there's anyone behind me"
→ Robot looks back, reports "No one there"

General assistant:
"I'm about to start a meeting, have robot greet attendees"
```

**Characteristics:**
- Spontaneous interactions
- Context switching between robot and other tasks
- Multimodal (text input, potentially future voice)

### Claude Code Plugin Use Case

**Environment:** Development/debugging
**Interaction:** Programmatic, test-driven
**Context:** Software development

**Example workflows:**
```python
# In code file
def test_robot_reach():
    """Test if robot can reach target positions"""

    # Claude Code uses MCP to query robot
    limits = claude.read_resource("reachy://config/limits")

    # Claude Code generates test cases
    test_positions = claude.sample(
        "Generate 10 test positions within robot workspace"
    )

    # Execute tests via MCP tools
    for pos in test_positions:
        result = claude.call_tool("move_to_position", pos)
        assert result.success
```

**Characteristics:**
- Systematic testing
- Debugging robot behaviors
- Automated validation
- Code generation for robot control

### Unified Server, Different Clients

**Same MCP server serves both!**

```
Reachy MCP Server
    ↑
    ├─── Claude Desktop (personal use)
    ├─── Claude Code (development)
    ├─── Cursor (alternative IDE)
    └─── Future clients...
```

## Comparison: MCP vs Current System

### When to Use Each

| Scenario | MCP Server | Current Realtime App |
|----------|-----------|---------------------|
| **Quick robot command during work** | ✅ Perfect | ❌ Overkill |
| **Real-time conversation with audio** | ❌ Not designed for this | ✅ Ideal |
| **Scripted automation** | ✅ Excellent | ⚠️ Possible but awkward |
| **Low-latency motion sync** | ❌ No audio processing | ✅ HeadWobbler optimized |
| **Multi-app integration** | ✅ Universal MCP client support | ❌ Standalone only |
| **Complex autonomous tasks** | ✅ Sampling enables this | ⚠️ Tool chaining only |
| **Development/testing** | ✅ Easy to mock/test | ⚠️ Harder to test |

### Coexistence Strategy

**Both systems can run simultaneously!**

```
Reachy Mini Robot
    ↑
    ├─── MCP Server (port 8000, stdio)
    │    └─── Claude Desktop client
    │
    └─── Realtime App (port 8080, WebSocket)
         └─── Gradio UI
```

**Key insight:** They share the same `MovementManager` instance!

```python
# Shared singleton
movement_manager = MovementManager.get_instance()

# Both systems use same backend
mcp_server.set_movement_manager(movement_manager)
realtime_app.set_movement_manager(movement_manager)
```

**Benefits:**
- Use whichever interface fits the task
- Consistent robot behavior
- Shared state and logging

## Future Possibilities

### 1. **Multimodal MCP Resources**

When MCP supports image/video resources:

```
reachy://camera/live-stream
├─ Type: video/mp4
├─ FPS: 30
└─ Resolution: 1280x720
```

Claude Desktop could **see through robot's eyes continuously**.

### 2. **Spatial Audio Integration**

```
reachy://audio/input
└─ 3D audio with direction detection
```

Robot could **tell you where sounds come from**.

### 3. **Haptic Feedback Resources**

```
reachy://sensors/force
└─ Gripper force sensor data
```

**Sensitive object manipulation** with real-time force monitoring.

### 4. **Collaborative Multi-Robot**

```python
# Control multiple robots via one MCP server
@mcp.tool()
async def coordinate_robots(robot_ids: List[str], task: str):
    """Coordinate multiple Reachy robots for collaborative task"""

    # Plan task distribution
    plan = await client.sample(
        f"Plan how {len(robot_ids)} robots should collaborate on: {task}"
    )

    # Execute in parallel
    tasks = []
    for robot_id, subtask in zip(robot_ids, plan.subtasks):
        tasks.append(execute_on_robot(robot_id, subtask))

    await asyncio.gather(*tasks)
```

### 5. **AR/VR Visualization**

```
reachy://visualization/ar-pose
└─ Real-time robot pose in AR coordinate system
```

**See robot's intended movements** in AR before execution.

### 6. **Voice MCP Integration**

Future MCP spec might support audio:

```
reachy://audio/microphone → Real-time audio input
reachy://audio/speaker → Real-time audio output
```

Then MCP server could **subsume entire realtime app functionality**.

## Architectural Patterns to Adopt

### 1. **Adapter Pattern**

```python
class ReachyAdapter:
    """Adapts existing robot control to MCP interface"""

    def __init__(self, deps: ToolDependencies):
        self.deps = deps
        self.tool_map = self._build_tool_map()

    def _build_tool_map(self):
        """Map MCP tool names to existing tool implementations"""
        from reachy_mini_conversation_app.tools import (
            MoveHeadTool, CameraTool, DanceTool, PlayEmotionTool
        )

        return {
            "move_head": MoveHeadTool(),
            "analyze_view": CameraTool(),
            "execute_dance": DanceTool(),
            "express_emotion": PlayEmotionTool()
        }

    async def execute_tool(self, name: str, args: dict):
        """Execute tool through existing infrastructure"""
        tool = self.tool_map.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        return await tool.execute(args, self.deps)
```

### 2. **Facade Pattern**

```python
class RobotFacade:
    """Simplified interface for MCP server"""

    def __init__(self):
        self.robot = ReachyMini()
        self.movement = MovementManager(self.robot)
        self.camera = CameraWorker(self.robot)
        self.safety = SafetyMonitor()

    async def move_safely(self, command: dict):
        """Execute movement with safety checks"""
        # Pre-check
        self.safety.validate_command(command)

        # Execute
        result = await self.movement.execute(command)

        # Post-check
        self.safety.verify_completion(result)

        return result
```

### 3. **Observer Pattern**

```python
class RobotStateObserver:
    """Notify MCP clients of state changes"""

    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback):
        self.subscribers.append(callback)

    async def notify_state_change(self, state: dict):
        """Push updates to subscribed MCP clients"""
        for callback in self.subscribers:
            await callback(state)

# In MCP server
@mcp.notification
async def robot_state_changed(state: dict):
    """Proactive notification to client"""
    await mcp.send_notification("robot/state_changed", state)
```

## Development Roadmap

### Milestone 1: Proof of Concept (Week 1-2)
- [ ] Basic MCP server with stdio transport
- [ ] 3 essential tools: move_head, analyze_view, emergency_stop
- [ ] 1 resource: reachy://status/current
- [ ] Integration with existing codebase
- [ ] Manual testing with Claude Desktop

### Milestone 2: Safety & Reliability (Week 3-4)
- [ ] Rate limiting implementation
- [ ] Workspace boundary validation
- [ ] Audit logging
- [ ] Error handling and recovery
- [ ] Automated safety tests

### Milestone 3: Feature Complete (Week 5-6)
- [ ] All core tools implemented
- [ ] Resources for status, history, config
- [ ] Prompt templates for common tasks
- [ ] Documentation and examples
- [ ] Claude Code plugin testing

### Milestone 4: Advanced Capabilities (Week 7-8)
- [ ] MCP sampling for autonomous behaviors
- [ ] Multi-step task execution
- [ ] Gesture recognition
- [ ] Performance optimization
- [ ] Production deployment guide

### Milestone 5: Polish & Release (Week 9-10)
- [ ] User documentation
- [ ] Video tutorials
- [ ] Example workflows
- [ ] Community feedback integration
- [ ] Public release on MCP registry

## Key Insights & Reflections

### 1. **MCP Enables New Interaction Paradigms**

The shift from "dedicated robot app" to "robot as a tool in your AI assistant" is profound. It changes how users think about and interact with robots.

**Before:** "I'm going to use the robot app"
**After:** "Hey Claude, tell the robot to..."

The robot becomes **ambient**, always available, context-aware.

### 2. **Sampling Is The Killer Feature**

MCP sampling (server-initiated LLM calls) enables **true autonomy**:
- Plan multi-step tasks
- Adapt to unexpected situations
- Reason about sensor data
- Learn from interactions

This wasn't possible with simple tool calling.

### 3. **Safety Is Paramount**

Robot control via AI requires **defense in depth**:
- Rate limiting (prevent command flooding)
- Workspace boundaries (physical safety)
- User confirmation (dangerous operations)
- Emergency stop (always accessible)
- Audit logging (accountability)

**Never compromise on safety** - reputation and trust are fragile.

### 4. **Reuse Is Strategic**

By reusing existing codebase:
- Leverage 4,569 lines of tested code
- Maintain consistency between interfaces
- Share bug fixes and improvements
- Reduce maintenance burden

**Don't rewrite** - wrap and adapt.

### 5. **Multimodal Future Is Exciting**

When MCP supports:
- Video streams (robot vision)
- Audio I/O (conversations)
- Haptic data (force feedback)
- AR overlays (visualization)

The MCP server could **replace the entire realtime app** while adding new capabilities.

### 6. **Community Potential**

Publishing to MCP registry:
- Enables anyone with Claude Desktop to control Reachy
- Inspires other robot manufacturers
- Creates ecosystem of robot MCP servers
- Standardizes robot-AI interactions

**This could be bigger than just Reachy** - it's a pattern for all robotics.

---

## Conclusion: The Vision

**An MCP server for Reachy Mini transforms the robot from a specialized system into a universal AI tool.** It makes robot control:

- **Accessible:** Available in daily AI assistant
- **Flexible:** Works with any MCP client
- **Safe:** Comprehensive safety mechanisms
- **Powerful:** Sampling enables autonomy
- **Extensible:** Easy to add new capabilities
- **Shareable:** Publish to MCP registry

**This isn't just an implementation detail - it's a paradigm shift in human-robot interaction.**

The future where robots are **ambient AI tools** rather than **dedicated systems** is not just possible - with MCP, it's **straightforward to implement**.

Let's build it. 🤖✨
