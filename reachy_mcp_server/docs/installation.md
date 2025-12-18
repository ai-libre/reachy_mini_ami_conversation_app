# Installation Guide

## Prerequisites

- Python 3.10 or higher
- Reachy Mini robot on same network
- `reachy_mini_conversation_app` package installed

## Step 1: Install MCP Server

```bash
cd reachy_mcp_server
pip install -e .
```

This installs the MCP server and all dependencies.

## Step 2: Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` to match your setup:

```bash
# Robot connection (REQUIRED)
ROBOT_HOST=192.168.1.100  # Your robot's IP address
ROBOT_PORT=50051

# OpenAI API key (if using cloud vision)
OPENAI_API_KEY=sk-your-key-here

# Safety settings
SAFETY_MODE=strict  # strict, permissive, or disabled
MAX_COMMANDS_PER_MINUTE=30

# Camera and vision
ENABLE_CAMERA=true
FACE_TRACKING_MODE=yolo  # yolo, mediapipe, or disabled
USE_LOCAL_VISION=false  # true for local VLM, false for GPT-4V
```

## Step 3: Test Server

Test the server standalone:

```bash
python -m reachy_mcp.server
```

You should see:
```
[2025-12-18 06:39:12] INFO    : Logging configured
[2025-12-18 06:39:12] INFO    : Initializing robot dependencies...
[2025-12-18 06:39:13] INFO    : ✓ Robot connected successfully
[2025-12-18 06:39:13] INFO    : ✓ Reachy MCP Server initialized
[2025-12-18 06:39:13] INFO    : Starting Reachy MCP Server...
```

Press `Ctrl+C` to stop.

## Step 4: Configure Claude Desktop

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "reachy-robot": {
      "command": "python",
      "args": ["-m", "reachy_mcp.server"],
      "env": {
        "ROBOT_HOST": "192.168.1.100",
        "SAFETY_MODE": "strict",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the same content.

## Step 5: Restart Claude Desktop

1. Quit Claude Desktop completely
2. Restart Claude Desktop
3. The MCP server will start automatically when Claude launches

## Step 6: Verify Integration

In Claude Desktop, type:

```
"List available robot commands"
```

Claude should respond with the available tools:
- move_head
- analyze_view
- execute_dance
- express_emotion
- set_face_tracking
- emergency_stop
- get_status

## Troubleshooting

### "Cannot connect to robot"

- Verify robot IP address is correct: `ping 192.168.1.100`
- Check robot is powered on and on same network
- Verify `ROBOT_HOST` in config matches robot IP

### "Camera not available"

- Check `ENABLE_CAMERA=true` in config
- Verify camera is not in use by another process
- Try restarting the MCP server

### "OpenAI API key required"

- If using cloud vision (`USE_LOCAL_VISION=false`), you need an OpenAI API key
- Add `OPENAI_API_KEY=sk-...` to your `.env` file
- Or set `USE_LOCAL_VISION=true` to use local vision model

### "Rate limit exceeded"

- You've sent more than 30 commands per minute
- Wait 60 seconds for the limit to reset
- Or adjust `MAX_COMMANDS_PER_MINUTE` in config

### Logs

Check logs for detailed error information:

```bash
cat logs/reachy_mcp.log
cat logs/robot_commands.jsonl  # Audit trail
```

## Next Steps

- Read [Configuration Guide](configuration.md) for all options
- See [Tools Reference](tools-reference.md) for command details
- Run examples: `python examples/basic_usage.py`

## Development Installation

For development with testing tools:

```bash
pip install -e ".[dev]"
pytest tests/
```
