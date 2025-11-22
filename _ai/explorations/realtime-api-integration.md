# OpenAI Realtime API Integration

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Why Realtime API?

Traditional chatbots use a **request-response cycle**:
```
User speaks → STT → Text to LLM → Text response → TTS → Audio output
Total latency: 2-5 seconds
```

OpenAI Realtime API uses **bidirectional streaming**:
```
User speaks → Server (VAD + STT + LLM + TTS all streaming) → Audio output
Total latency: 300-800ms
```

**Key Advantages:**
1. **Low latency:** AI responds while you're still speaking
2. **Natural interruptions:** Can cut off AI mid-sentence
3. **Server-side VAD:** No need to implement voice activity detection
4. **Native audio:** No separate TTS API calls
5. **Function calling:** Tools integrated into conversation flow

## Architecture: WebSocket Connection

### Connection Lifecycle

```python
class OpenAIRealtimeHandler:
    async def connect(self):
        # 1. Establish WebSocket
        self.client = await RealtimeClient(
            api_key=config.OPENAI_API_KEY,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )

        # 2. Wait for connection
        await self.client.wait_for_connection()

        # 3. Configure session
        await self._setup_session()

        # 4. Register event handlers
        await self._setup_event_handlers()
```

### Session Configuration

```python
async def _setup_session(self):
    await self.client.session.update(
        session={
            # Modalities
            "modalities": ["text", "audio"],  # Both supported

            # Voice
            "voice": "sage",  # or: alloy, ash, coral, echo

            # Audio formats
            "input_audio_format": "pcm16",   # 16-bit PCM
            "output_audio_format": "pcm16",  # 16-bit PCM

            # Transcription (optional but recommended)
            "input_audio_transcription": {
                "model": "whisper-1"
            },

            # Instructions (system prompt)
            "instructions": self._load_profile_prompt(),

            # Tools (function calling)
            "tools": self._build_tool_definitions(),

            # Temperature
            "temperature": 0.8,  # Slightly creative

            # Turn detection (VAD settings)
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,   # Include 300ms before speech
                "silence_duration_ms": 500  # 500ms silence = end of turn
            }
        }
    )
```

**Critical Settings:**

| Setting | Value | Why |
|---------|-------|-----|
| `modalities` | `["text", "audio"]` | Enables audio I/O |
| `voice` | `"sage"` | Voice personality |
| `turn_detection.type` | `"server_vad"` | Server handles speech detection |
| `silence_duration_ms` | `500` | Balance between responsiveness and false triggers |

## Event-Driven Architecture

### Core Events

The Realtime API is **event-driven**. Server sends events; client handles them.

```python
async def _setup_event_handlers(self):
    # Audio streaming
    self.client.on("response.audio.delta", self._on_audio_delta)
    self.client.on("response.audio.done", self._on_audio_done)

    # Transcripts
    self.client.on("conversation.item.completed", self._on_item_completed)

    # Function calling
    self.client.on("response.function_call_arguments.delta", self._on_function_args_delta)
    self.client.on("response.function_call_arguments.done", self._on_function_call_done)

    # Errors
    self.client.on("error", self._on_error)

    # Input audio (user speech detected)
    self.client.on("input_audio_buffer.speech_started", self._on_speech_started)
    self.client.on("input_audio_buffer.speech_stopped", self._on_speech_stopped)
```

### Event: Audio Delta (Streaming Output)

**Most frequent event.** AI response audio arrives in chunks.

```python
async def _on_audio_delta(self, event: dict):
    """
    Event structure:
    {
        "type": "response.audio.delta",
        "delta": "base64_encoded_pcm16_audio",
        "response_id": "resp_123",
        "item_id": "item_456",
        "output_index": 0,
        "content_index": 0
    }
    """
    delta = event.get("delta")
    if not delta:
        return

    # Decode audio (base64 → bytes)
    audio_bytes = base64.b64decode(delta)

    # 1. Send to head wobbler (motion generation)
    self.head_wobbler.process_audio_delta(audio_bytes)

    # 2. Forward to audio output (speaker)
    await self.audio_output_stream.write(audio_bytes)

    # 3. Track for transcript (optional)
    self._current_response_audio.append(audio_bytes)
```

**Key Insight:** Same audio stream drives both speaker output AND robot motion. Perfect sync.

### Event: Function Call (Tool Dispatch)

When AI decides to use a tool, you get a function call event.

```python
async def _on_function_call_done(self, event: dict):
    """
    Event structure:
    {
        "type": "response.function_call_arguments.done",
        "call_id": "call_abc123",
        "name": "camera",
        "arguments": '{"prompt": "What do you see?"}'
    }
    """
    call_id = event["call_id"]
    tool_name = event["name"]
    args_json = event["arguments"]

    # Parse arguments
    args = json.loads(args_json)

    # Execute tool
    try:
        result = await self.tool_dispatcher.dispatch(tool_name, args)
        output = result  # Success
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        output = f"Error: {str(e)}"

    # Return result to AI
    await self.client.conversation.item.create(
        item={
            "type": "function_call_output",
            "call_id": call_id,  # Must match!
            "output": output
        }
    )

    # Request AI to continue (respond based on tool result)
    await self.client.response.create()
```

**Flow:**
1. AI decides to call tool
2. `function_call_arguments.done` event fires
3. You execute tool, get result
4. You send result back via `conversation.item.create`
5. You request AI response via `response.create`
6. AI speaks/responds based on tool result

### Event: Transcript Completion

When a conversation turn completes (user or AI), transcript is available.

```python
async def _on_item_completed(self, event: dict):
    """
    Event structure:
    {
        "type": "conversation.item.completed",
        "item": {
            "id": "item_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "I see a desk and a computer."
                },
                {
                    "type": "audio",
                    "transcript": "I see a desk and a computer."
                }
            ]
        }
    }
    """
    item = event["item"]
    role = item["role"]  # "user" or "assistant"

    # Extract text/transcript
    text = self._extract_text_from_item(item)

    # Update UI transcript
    self.transcripts.append({
        "role": role,
        "content": text
    })

    # Mark activity (for idle detection)
    self.movement_manager.queue_command("mark_activity")
```

## Audio Pipeline

### Input Audio (User → AI)

```python
async def send_user_audio(self, audio_chunk: bytes):
    """
    Send user microphone audio to AI.

    Args:
        audio_chunk: Raw PCM16 audio at 16kHz
    """
    # Resample 16kHz → 24kHz (API requirement)
    resampled = librosa.resample(
        np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32),
        orig_sr=16000,
        target_sr=24000
    )

    # Convert back to PCM16
    resampled_pcm16 = (resampled * 32767).astype(np.int16).tobytes()

    # Send to API
    await self.client.input_audio_buffer.append(
        audio=base64.b64encode(resampled_pcm16).decode()
    )
```

**Why resample?** OpenAI Realtime API expects 24kHz input. Most microphones output 16kHz or 48kHz.

### Output Audio (AI → Speaker)

```python
async def _on_audio_delta(self, event: dict):
    audio_bytes = base64.b64decode(event["delta"])

    # Audio is already 24kHz PCM16 (as configured in session)

    # Forward to speaker
    await self.audio_output_stream.write(audio_bytes)
```

**Note:** Output audio is already at correct sample rate. No resampling needed.

## Conversation Management

### Conversation Items

The API maintains a conversation history as "items":

```
Conversation:
├─ Item 1 (user message)
│  └─ "What do you see?"
├─ Item 2 (assistant message)
│  └─ "Let me look." + [function_call: camera]
├─ Item 3 (function_call_output)
│  └─ "I see a desk with a computer and a person."
└─ Item 4 (assistant message)
   └─ "I can see you're at a desk with your computer."
```

### Adding Items Programmatically

```python
# Add user message (e.g., from text input)
await self.client.conversation.item.create(
    item={
        "type": "message",
        "role": "user",
        "content": [
            {"type": "input_text", "text": "Tell me a joke"}
        ]
    }
)

# Request AI response
await self.client.response.create()
```

### Clearing History

```python
# Clear all conversation history
await self.client.conversation.clear()

# Re-add system instructions if needed
await self._setup_session()
```

## Advanced: Idle Detection & Engagement

### Problem

If user stops talking, robot should eventually prompt re-engagement.

### Implementation

```python
class IdleDetector:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._last_user_speech: float = time.time()

    def on_speech_started(self):
        """Called when user starts speaking"""
        self._last_user_speech = time.time()

    async def check_idle(self):
        """Call this periodically"""
        idle_duration = time.time() - self._last_user_speech

        if idle_duration > self.timeout:
            # User hasn't spoken in 30 seconds
            await self._engage_user()
            self._last_user_speech = time.time()  # Reset timer

    async def _engage_user(self):
        """Prompt user"""
        await self.client.conversation.item.create(
            item={
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "[Silence for 30 seconds]"}]
            }
        )
        await self.client.response.create()

        # AI will see this and respond with something like:
        # "Are you still there?" or "Is there anything else I can help with?"
```

**Effect:** Robot proactively engages after silence, feels more alive.

## Error Handling & Reconnection

### WebSocket Disconnection

```python
async def _on_disconnect(self):
    logger.warning("Disconnected from OpenAI Realtime API")

    # Attempt reconnection with exponential backoff
    for attempt in range(5):
        delay = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
        logger.info(f"Reconnecting in {delay}s (attempt {attempt+1}/5)")
        await asyncio.sleep(delay)

        try:
            await self.connect()
            logger.info("Reconnected successfully")
            return
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")

    # Give up after 5 attempts
    logger.error("Failed to reconnect, shutting down")
    raise ConnectionError("Could not reconnect to OpenAI API")
```

### Rate Limiting

```python
async def _on_error(self, event: dict):
    error = event.get("error", {})
    error_type = error.get("type")

    if error_type == "rate_limit_exceeded":
        logger.warning("Rate limit hit, backing off")
        await asyncio.sleep(5)  # Wait 5 seconds
        # Retry last request if applicable

    elif error_type == "invalid_request_error":
        logger.error(f"Invalid request: {error.get('message')}")
        # Don't retry, fix the request

    else:
        logger.error(f"API error: {error}")
```

## Performance Optimization

### Minimize Latency

```python
# ✅ Good: Stream audio immediately
async def _on_audio_delta(self, event: dict):
    audio_bytes = base64.b64decode(event["delta"])
    await self.audio_output_stream.write(audio_bytes)  # No buffering

# ❌ Bad: Buffer entire response before playing
async def _on_audio_delta(self, event: dict):
    self._buffer.append(audio_bytes)

async def _on_audio_done(self, event: dict):
    all_audio = b''.join(self._buffer)
    await self.audio_output_stream.write(all_audio)  # Delayed playback
```

### Reduce Token Usage

```python
# Use concise system prompts
instructions = """
You are Reachy, a helpful robot assistant.
Be concise and friendly.
"""

# vs. overly verbose:
instructions = """
You are Reachy, an advanced robotic assistant powered by state-of-the-art
artificial intelligence designed to help users with a wide variety of tasks
including but not limited to answering questions, providing information,
performing physical actions through your robotic body, and engaging in
natural conversation...
"""
# (Costs more, no benefit)
```

## Integration with Robot Systems

### Coordination Points

```python
class OpenAIRealtimeHandler:
    def __init__(
        self,
        movement_manager: MovementManager,
        head_wobbler: HeadWobbler,
        tool_dispatcher: ToolDispatcher,
    ):
        self.movement_manager = movement_manager
        self.head_wobbler = head_wobbler
        self.tool_dispatcher = tool_dispatcher

    async def _on_audio_delta(self, event: dict):
        audio_bytes = base64.b64decode(event["delta"])

        # 1. Motion sync
        self.head_wobbler.process_audio_delta(audio_bytes)

        # 2. Audio output
        await self.audio_output.write(audio_bytes)

    async def _on_function_call_done(self, event: dict):
        # 3. Tool execution
        result = await self.tool_dispatcher.dispatch(...)

        # 4. Activity tracking
        self.movement_manager.queue_command("mark_activity")

    async def _on_speech_started(self, event: dict):
        # 5. Listening cues
        self.movement_manager.queue_command("toggle_freeze", enable=True)

    async def _on_speech_stopped(self, event: dict):
        self.movement_manager.queue_command("toggle_freeze", enable=False)
```

**Key Integration Points:**
1. **Audio → Motion:** HeadWobbler processes same stream
2. **Tools → Movement:** Tools queue robot moves
3. **Speech events → Antennas:** Freeze during listening
4. **Activity tracking:** Prevent idle breathing during conversation

---

## Key Insights

1. **Event-driven is essential:** WebSocket model enables low latency
2. **Audio is the source of truth:** Same stream for speaker + motion
3. **Function calling integrates naturally:** Tools feel like part of conversation
4. **Server-side VAD is powerful:** No need to implement speech detection
5. **Error handling is critical:** Network issues WILL happen, plan for them

The Realtime API is what makes this system feel **conversational** rather than **command-driven**. It's the difference between a robot and a companion.
