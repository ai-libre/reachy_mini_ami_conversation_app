# Configuration Guide

Comprehensive guide to configuring Reachy MCP Server.

## Configuration Methods

### 1. Environment Variables (Recommended)

Create a `.env` file in the `reachy_mcp_server/` directory:

```bash
cp .env.example .env
# Edit .env with your settings
```

### 2. System Environment Variables

```bash
export ROBOT_HOST=192.168.1.100
export SAFETY_MODE=strict
python -m reachy_mcp.server
```

### 3. Claude Desktop Config

Pass environment variables through MCP configuration:

```json
{
  "mcpServers": {
    "reachy-robot": {
      "env": {
        "ROBOT_HOST": "192.168.1.100",
        "SAFETY_MODE": "strict"
      }
    }
  }
}
```

---

## Configuration Categories

### Robot Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ROBOT_HOST` | string | `192.168.1.100` | Robot IP address |
| `ROBOT_PORT` | integer | `50051` | Robot gRPC port |

**Example:**
```bash
ROBOT_HOST=10.0.0.50
ROBOT_PORT=50051
```

---

### Safety Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SAFETY_MODE` | enum | `strict` | Safety enforcement level |
| `MAX_COMMANDS_PER_MINUTE` | integer | `30` | Rate limit threshold |
| `REQUIRE_CONFIRMATION` | boolean | `true` | Require confirmation for dangerous ops |

**Safety Modes:**

- **`strict`** (Production) - All safety checks enabled, confirmations required
- **`permissive`** (Testing) - Safety checks enabled, fewer confirmations
- **`disabled`** (Development) - ⚠️ **DANGEROUS** - No safety checks

**Example:**
```bash
SAFETY_MODE=strict
MAX_COMMANDS_PER_MINUTE=30
REQUIRE_CONFIRMATION=true
```

⚠️ **Never use `SAFETY_MODE=disabled` in production or near people!**

---

### Workspace Boundaries

Defines safe movement area (meters from robot base):

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WORKSPACE_X_MIN` | float | `-0.3` | Minimum X coordinate |
| `WORKSPACE_X_MAX` | float | `0.3` | Maximum X coordinate |
| `WORKSPACE_Y_MIN` | float | `-0.3` | Minimum Y coordinate |
| `WORKSPACE_Y_MAX` | float | `0.3` | Maximum Y coordinate |
| `WORKSPACE_Z_MIN` | float | `0.0` | Minimum Z coordinate |
| `WORKSPACE_Z_MAX` | float | `0.5` | Maximum Z coordinate |

**Example:**
```bash
WORKSPACE_X_MIN=-0.3
WORKSPACE_X_MAX=0.3
WORKSPACE_Y_MIN=-0.3
WORKSPACE_Y_MAX=0.3
WORKSPACE_Z_MIN=0.0
WORKSPACE_Z_MAX=0.5
```

---

### Vision Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `USE_LOCAL_VISION` | boolean | `false` | Use local VLM vs cloud |
| `LOCAL_VISION_MODEL` | string | `SmolVLM2-2.2B-Instruct` | Local model identifier |
| `OPENAI_API_KEY` | string | *(required)* | OpenAI API key (if cloud vision) |

**Cloud Vision (GPT-4V):**
```bash
USE_LOCAL_VISION=false
OPENAI_API_KEY=sk-proj-abc123...
```

**Local Vision (Private):**
```bash
USE_LOCAL_VISION=true
LOCAL_VISION_MODEL=HuggingFaceTB/SmolVLM2-2.2B-Instruct
```

---

### Camera Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_CAMERA` | boolean | `true` | Enable camera functionality |
| `FACE_TRACKING_MODE` | enum | `yolo` | Face tracking implementation |

**Face Tracking Modes:**

- **`yolo`** - Fast, uses YOLOv8 (recommended)
- **`mediapipe`** - Detailed, provides 468 facial landmarks
- **`disabled`** - No face tracking

**Example:**
```bash
ENABLE_CAMERA=true
FACE_TRACKING_MODE=yolo
```

---

### Logging Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | enum | `INFO` | Logging verbosity |
| `LOG_FILE` | path | `logs/reachy_mcp.log` | Application log file |
| `AUDIT_LOG` | path | `logs/robot_commands.jsonl` | Command audit trail |
| `STRUCTURED_LOGGING` | boolean | `false` | Use JSON format |

**Log Levels:**
- `DEBUG` - Very verbose (development)
- `INFO` - Normal operations (production)
- `WARNING` - Warnings only
- `ERROR` - Errors only
- `CRITICAL` - Critical errors only

**Example:**
```bash
LOG_LEVEL=INFO
LOG_FILE=logs/reachy_mcp.log
AUDIT_LOG=logs/robot_commands.jsonl
STRUCTURED_LOGGING=false
```

---

### MCP Server Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MCP_TRANSPORT` | enum | `stdio` | Transport mode |
| `MCP_HTTP_HOST` | string | `127.0.0.1` | HTTP server host |
| `MCP_HTTP_PORT` | integer | `8000` | HTTP server port |
| `MCP_HTTP_AUTH_TOKEN` | string | *(optional)* | Auth token for HTTP |

**Transport Modes:**

- **`stdio`** (Recommended) - Standard input/output (local only)
- **`http`** - HTTP with SSE (remote access)

**Example (stdio):**
```bash
MCP_TRANSPORT=stdio
```

**Example (HTTP - advanced):**
```bash
MCP_TRANSPORT=http
MCP_HTTP_HOST=0.0.0.0
MCP_HTTP_PORT=8000
MCP_HTTP_AUTH_TOKEN=secret-token-here
```

---

### Performance Tuning

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_METRICS` | boolean | `true` | Collect performance metrics |
| `METRICS_INTERVAL` | integer | `60` | Metrics collection interval (seconds) |
| `MAX_CONCURRENT_TOOLS` | integer | `3` | Max parallel tool executions |

**Example:**
```bash
ENABLE_METRICS=true
METRICS_INTERVAL=60
MAX_CONCURRENT_TOOLS=3
```

---

### Development Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DEBUG_MODE` | boolean | `false` | Enable debug mode |
| `MOCK_ROBOT` | boolean | `false` | Use mock robot (no hardware) |
| `ENABLE_MCP_INSPECTOR` | boolean | `false` | Enable MCP debugging |

**Example (testing without hardware):**
```bash
DEBUG_MODE=true
MOCK_ROBOT=true
SAFETY_MODE=disabled
```

⚠️ **Development settings should NEVER be used in production!**

---

## Configuration Profiles

### Production Profile

```bash
ROBOT_HOST=192.168.1.100
SAFETY_MODE=strict
MAX_COMMANDS_PER_MINUTE=30
REQUIRE_CONFIRMATION=true
ENABLE_CAMERA=true
FACE_TRACKING_MODE=yolo
USE_LOCAL_VISION=false
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
MCP_TRANSPORT=stdio
```

### Development Profile

```bash
ROBOT_HOST=127.0.0.1
SAFETY_MODE=permissive
MAX_COMMANDS_PER_MINUTE=100
DEBUG_MODE=true
MOCK_ROBOT=true
LOG_LEVEL=DEBUG
MCP_TRANSPORT=stdio
```

### Testing Profile

```bash
MOCK_ROBOT=true
SAFETY_MODE=disabled
ENABLE_CAMERA=false
LOG_LEVEL=ERROR
```

---

## Validation

Configuration is validated on startup. Invalid values cause immediate errors:

```
ValidationError: OPENAI_API_KEY required when USE_LOCAL_VISION=false
ConfigurationError: ROBOT_HOST cannot be empty
ValueError: Invalid log level: VERBOSE
```

---

## Configuration Precedence

1. Environment variables (highest priority)
2. `.env` file
3. Default values (lowest priority)

---

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Rotate API keys** regularly
3. **Use `strict` safety mode** in production
4. **Limit network exposure** (prefer `stdio` transport)
5. **Enable audit logging** for security tracking
6. **Set strong `MCP_HTTP_AUTH_TOKEN`** if using HTTP

---

## Troubleshooting

### "Configuration validation failed"

Check that all required variables are set:
- `ROBOT_HOST` must not be empty
- `OPENAI_API_KEY` required if `USE_LOCAL_VISION=false`

### "Warning: Using default ROBOT_HOST"

You're using the default IP `192.168.1.100`. Verify this matches your robot's actual IP.

### "Safety disabled warning"

You've set `SAFETY_MODE=disabled`. This is **dangerous** and should only be used in development.

---

## Next Steps

- [Installation Guide](installation.md) - Setup instructions
- [Tools Reference](tools-reference.md) - Available commands
- [README](../README.md) - Overview

---

**Need help?** Check logs at `logs/reachy_mcp.log` for detailed information.
