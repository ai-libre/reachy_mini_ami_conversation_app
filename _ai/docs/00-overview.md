# Reachy Mini AMI Conversation App - Overview

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## What This Is

A real-time conversational AI system for the **Reachy Mini robot** that creates an embodied AI assistant through:

- 🎙️ **Real-time voice conversation** via OpenAI's Realtime API
- 👁️ **Vision processing** (cloud GPT-4V or local SmolVLM2)
- 💃 **Choreographed motion** with layered animation system
- 🎭 **Customizable AI personalities** through profile system
- 🌐 **Web UI** (Gradio) or console interface

## Core Innovation

The system's **layered motion architecture** is particularly sophisticated:

### Primary Motion Layer (Sequential)
- Dances from library
- Emotional expressions
- Breathing idle animations
- Goto poses

### Secondary Motion Layer (Additive)
- Speech-reactive wobble (synced with AI audio output)
- Face tracking (follows detected faces)
- Composed in world-frame coordinates

This allows the robot to track faces while dancing, or sway naturally while speaking from any pose.

## Architecture at a Glance

```
┌─────────────────┐
│   User Voice    │
└────────┬────────┘
         │
    ┌────▼─────────────────┐
    │  OpenAI Realtime API │ ◄─── Tool Calls
    │   (WebSocket)        │
    └────┬─────────────────┘
         │
         ├──► Audio Output ──► HeadWobbler ──┐
         │                                    │
         ├──► Transcripts ──► Gradio UI      │
         │                                    │
         └──► Tool Dispatch                  │
                │                             │
                ├─► Camera Tool ──► VisionProcessor
                ├─► Dance Tool                │
                ├─► Emotion Tool              │
                └─► Head Tracking Toggle      │
                                              │
┌────────────────────────────────────────────▼────┐
│          Movement Manager (100Hz)               │
│                                                  │
│  Primary Queue ──┬──► Compose ──► Reachy Mini  │
│  (Sequential)    │      ▲                       │
│                  │      │                       │
│  Secondary ──────┘      │                       │
│  (Additive)             │                       │
│                         │                       │
│  ◄──────────────────────┘                       │
│    Face Tracking from CameraWorker              │
└─────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. **100Hz Control Loop**
Movement manager runs at 100Hz for smooth, responsive motion control. All moves compose into a single `set_target()` call per tick.

### 2. **Audio Latency Compensation**
HeadWobbler includes 80ms latency compensation to sync head movements with perceived audio output.

### 3. **Thread-Safe Architecture**
Each subsystem runs in its own thread with lock-protected shared state:
- Main: Async OpenAI connection
- MovementManager: Real-time control
- CameraWorker: Frame capture
- HeadWobbler: Audio processing
- VisionManager: Periodic analysis

### 4. **Profile System**
AI personalities are modular and configurable:
- Custom prompts with template expansion
- Tool subsetting
- Profile-specific tool implementations

### 5. **Dual Vision System**
- **Cloud:** GPT-4V (accurate, requires API)
- **Local:** SmolVLM2 (private, runs on device)

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **AI** | OpenAI Realtime API (GPT-4 with audio) |
| **Vision** | GPT-4V, SmolVLM2, YOLO v8, MediaPipe |
| **Robot Control** | reachy_mini SDK, dances_library |
| **Audio** | librosa (resampling), numpy/scipy |
| **Web UI** | Gradio, fastrtc, aiortc (WebRTC) |
| **Language** | Python 3.10+, asyncio, threading |

## Use Cases

1. **Interactive Robot Companion:** Natural conversation with embodied responses
2. **Emotion-Aware Assistant:** Reads facial expressions and responds appropriately
3. **Educational Demonstrations:** Shows AI + robotics integration
4. **Custom Personalities:** Create specialized assistants (e.g., emotion_reader profile)
5. **Research Platform:** Explore multimodal AI interactions

## Quick Start

```bash
# Install
uv sync --extra all_vision

# Run with Gradio UI
reachy-mini-conversation-app --gradio --head-tracker yolo

# Console mode
reachy-mini-conversation-app
```

## Repository Health

- ✅ Type checking (mypy)
- ✅ Linting (ruff)
- ✅ Unit tests (pytest)
- ✅ CI/CD (GitHub Actions)
- ✅ Locked dependencies (uv.lock)
- ✅ Pre-commit hooks

## What Makes This Special

This isn't just "chatbot on a robot." It's a carefully orchestrated system where:

- Audio deltas drive motion in real-time
- Vision provides grounding for conversation
- Motion layers compose mathematically
- Tools extend AI capabilities dynamically
- Everything runs with minimal latency

The result is a robot that feels **alive** — it breathes when idle, sways when speaking, tracks your face, dances on request, and holds natural conversations about what it sees.
