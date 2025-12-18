# Tools Reference

Complete reference for all MCP tools exposed by Reachy MCP Server.

---

## Movement Tools

### `move_head`

Move robot head to look in a direction.

**Arguments:**
- `direction` (string, required): Direction to look
  - Valid values: `"left"`, `"right"`, `"up"`, `"down"`, `"front"`
- `speed` (number, optional): Movement speed from 0.1 to 1.0
  - Default: 0.5
  - 0.1 = very slow, 1.0 = maximum speed

**Returns:** Confirmation message

**Example:**
```
"Move robot head to look left"
→ move_head(direction="left", speed=0.5)
→ "Head moved left at speed 0.5"
```

**Safety:** Rate limited, workspace validated

---

### `execute_dance`

Perform a choreographed dance from the library.

**Arguments:**
- `dance_name` (string, optional): Name of specific dance
  - If omitted, a random dance is selected

**Returns:** Dance name and confirmation

**Example:**
```
"Have the robot dance"
→ execute_dance()
→ "Started random_dance_5 (15 seconds)"

"Do the happy dance"
→ execute_dance(dance_name="happy")
→ "Started happy dance"
```

**Safety:** Rate limited

---

### `express_emotion`

Display an emotion animation.

**Arguments:**
- `emotion` (string, required): Emotion to express
  - Valid values: `"happy"`, `"sad"`, `"surprised"`, `"thinking"`, `"excited"`, `"neutral"`

**Returns:** Confirmation message

**Example:**
```
"Express happy emotion"
→ express_emotion(emotion="happy")
→ "Expressed happy emotion"
```

**Safety:** Rate limited

---

## Vision Tools

### `analyze_view`

Capture and analyze what robot sees through camera.

**Arguments:**
- `question` (string, required): Analysis prompt
  - Examples: "What do you see?", "What emotion is this person showing?", "Is there anyone in the room?"
- `use_local` (boolean, optional): Use local VLM vs cloud
  - `false` (default): Use GPT-4V (more accurate, requires API key)
  - `true`: Use local SmolVLM2 (private, runs on device)

**Returns:** Analysis result from vision model

**Example:**
```
"What do you see through your camera?"
→ analyze_view(question="Describe what you see", use_local=false)
→ "I see a person sitting at a desk with a computer and coffee mug"

"Analyze the person's emotion"
→ analyze_view(question="What emotion is this person showing?")
→ "The person appears happy, with a slight smile"
```

**Safety:** Rate limited, camera availability checked

---

### `set_face_tracking`

Enable or disable automatic face following.

**Arguments:**
- `enabled` (boolean, required): True to enable, False to disable

**Returns:** Confirmation message

**Example:**
```
"Enable face tracking"
→ set_face_tracking(enabled=true)
→ "Face tracking enabled using YOLO"

"Stop following my face"
→ set_face_tracking(enabled=false)
→ "Face tracking disabled"
```

**Safety:** Rate limited, camera availability checked

---

## System Tools

### `get_status`

Get current robot status.

**Arguments:** None

**Returns:** JSON object with:
- `joints`: Current joint positions (degrees)
- `battery`: Battery status (if available)
- `camera`: Camera availability and state
- `vision`: Vision system availability
- `connected`: Connection status
- `errors`: Any current errors

**Example:**
```
"What's the robot's current status?"
→ get_status()
→ {
    "joints": {
      "neck_pitch": 10.5,
      "neck_yaw": -5.2,
      ...
    },
    "camera": {
      "available": true,
      "face_tracking": false
    },
    "connected": true,
    "errors": []
  }
```

**Safety:** No rate limiting (read-only)

---

### `emergency_stop`

**⚠️ EMERGENCY: Immediately halt all robot motion.**

**Arguments:**
- `reason` (string, optional): Reason for stop (for logging)
  - Default: "User initiated"

**Returns:** Confirmation that robot is in safe state

**Example:**
```
"Emergency stop!"
→ emergency_stop(reason="Obstacle detected")
→ "Emergency stop activated: Obstacle detected. Robot halted and in safe state."
```

**Safety:** ALWAYS executed, bypasses rate limiting

**Effects:**
- Clears all movement queues
- Stops current motion immediately
- Disables face tracking
- Sets emergency stop flag (blocks future commands until reset)

---

## Usage Patterns

### Sequential Commands

```
"Move head left, then analyze what you see"
1. move_head(direction="left")
2. analyze_view(question="What do you see?")
```

### Conditional Execution

```
"If there's a person in view, wave at them"
1. analyze_view(question="Is there a person in this image?")
2. If "yes": execute_dance(dance_name="wave")
```

### Status Checking

```
"Check battery and camera status"
→ get_status()
→ Returns full status including battery and camera
```

---

## Rate Limiting

**Default:** 30 commands per minute

Commands that are rate limited:
- move_head
- execute_dance
- express_emotion
- analyze_view
- set_face_tracking

Commands NOT rate limited:
- get_status (read-only)
- emergency_stop (always priority)

**Exceeded limit?** Wait 60 seconds or adjust `MAX_COMMANDS_PER_MINUTE` in config.

---

## Error Handling

All tools return error messages if execution fails:

```
"Move head to invalid direction"
→ move_head(direction="sideways")
→ "Error: Invalid direction: sideways. Must be one of ['left', 'right', 'up', 'down', 'front']"
```

Common errors:
- `RateLimitExceededError`: Too many commands
- `CameraError`: Camera not available
- `SafetyError`: Movement blocked by safety checks
- `HardwareError`: Robot hardware issue

Check `logs/robot_commands.jsonl` for full audit trail.

---

## Resources

In addition to tools, you can read robot resources:

- `reachy://status/current` - Real-time robot state
- `reachy://status/health` - System health
- `reachy://config/limits` - Joint limits
- `reachy://config/safety` - Safety configuration

Claude can reference these proactively.

---

## Best Practices

1. **Check status first** before complex operations
2. **Use appropriate speeds** - slower is safer
3. **Monitor rate limits** - space out commands
4. **Have emergency stop ready** - safety first
5. **Check camera availability** before vision commands
6. **Use descriptive questions** for vision analysis

---

For more details, see:
- [Installation Guide](installation.md)
- [Configuration Guide](configuration.md)
- [README](../README.md)
