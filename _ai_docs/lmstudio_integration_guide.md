# LMStudio Integration Guide for Reachy Mini

**Approach:** Jose Valim Ultrathink - Propose → Reflect → Iterate

---

## 1. PROPOSAL: LMStudio as Local LLM Backend

### 1.1 Why LMStudio?

**✅ Advantages:**
- **OpenAI-Compatible API:** Drop-in replacement for OpenAI client
- **User-Friendly:** GUI for model management
- **Performance:** Optimized inference with llama.cpp
- **Multi-Model:** Easy to switch between models
- **GPU Acceleration:** CUDA, Metal (Apple), Vulkan support
- **Function Calling:** Supports tool use with compatible models

**📊 Performance Expectations:**
```
Hardware: RTX 4070 (12GB VRAM)
Model: Hermes-2-Pro-Llama-3-8B (Q4_K_M quantization)

Token Generation: ~40-80 tokens/second
First Token Latency: ~200-500ms
Function Calling: Supported with high accuracy
```

---

## 2. ARCHITECTURE: Modular Component Design

### 2.1 Component Stack

```
┌─────────────────────────────────────────┐
│    Reachy Mini Conversation App         │
├─────────────────────────────────────────┤
│  Handler Layer (AsyncStreamHandler)     │
│  ┌───────────────────────────────────┐  │
│  │  LocalLLMRealtimeHandler          │  │
│  └───────────────────────────────────┘  │
├─────────────────────────────────────────┤
│  Pipeline Components                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │   VAD   │→ │   STT   │→ │   LLM   │ │
│  │ Silero  │  │ Whisper │  │LMStudio │ │
│  └─────────┘  └─────────┘  └─────────┘ │
│                                ↓        │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Speaker │← │   TTS   │← │  Tools  │ │
│  │  24kHz  │  │  Piper  │  │ Dispatch│ │
│  └─────────┘  └─────────┘  └─────────┘ │
└─────────────────────────────────────────┘
```

### 2.2 Data Flow

```
User speaks
    ↓
[Microphone] → 16kHz PCM audio
    ↓
[Resample] → 24kHz PCM audio
    ↓
[VAD] → Detect speech start/stop
    ↓
[Buffer] → Accumulate speech segments
    ↓
[STT: Whisper] → Text transcription
    ↓
[LLM: LMStudio] → Response with optional function calls
    ↓
[Tool Dispatch] → Execute robot actions (if function call)
    ↓
[TTS: Piper] → Audio synthesis
    ↓
[Speaker] → 24kHz PCM audio output
```

---

## 3. COMPONENT IMPLEMENTATION

### 3.1 Component A: Silero VAD

**Purpose:** Detect when user starts/stops speaking

```python
# File: src/reachy_mini_conversation_app/vad/silero_vad.py

import torch
import numpy as np
from typing import Optional


class SileroVAD:
    """Silero VAD for speech detection."""

    def __init__(
        self,
        sample_rate: int = 24000,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500,
    ):
        """Initialize Silero VAD.

        Args:
            sample_rate: Audio sample rate (16000 or 24000)
            threshold: Speech probability threshold (0.0-1.0)
            min_speech_duration_ms: Minimum speech duration to trigger
            min_silence_duration_ms: Minimum silence to end speech
        """
        self.sample_rate = sample_rate
        self.threshold = threshold

        # Load Silero VAD model
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )

        (
            self.get_speech_timestamps,
            self.save_audio,
            self.read_audio,
            self.VADIterator,
            self.collect_chunks,
        ) = utils

        self.vad_iterator = self.VADIterator(
            model=self.model,
            threshold=self.threshold,
            sampling_rate=self.sample_rate,
            min_speech_duration_ms=min_speech_duration_ms,
            min_silence_duration_ms=min_silence_duration_ms,
        )

    def __call__(self, audio_chunk: np.ndarray) -> Optional[dict]:
        """Process audio chunk and return VAD decision.

        Args:
            audio_chunk: Audio data (int16 or float32)

        Returns:
            Dictionary with 'speech_start' or 'speech_end' event, or None
        """
        # Convert to float32 if needed
        if audio_chunk.dtype == np.int16:
            audio_chunk = audio_chunk.astype(np.float32) / 32768.0

        # Convert to tensor
        audio_tensor = torch.from_numpy(audio_chunk)

        # Get VAD decision
        speech_dict = self.vad_iterator(audio_tensor, return_seconds=False)

        if speech_dict:
            return speech_dict

        return None

    def reset(self):
        """Reset VAD state."""
        self.vad_iterator.reset_states()


# Example usage:
# vad = SileroVAD(sample_rate=24000)
# result = vad(audio_chunk)
# if result and 'start' in result:
#     print("Speech started!")
```

**Reflection:**
- ✅ Silero VAD is lightweight (~1MB)
- ✅ Works well on CPU
- ✅ Low latency (<10ms per chunk)
- ⚠️ Requires tuning threshold for robot environment (motor noise)

---

### 3.2 Component B: Faster-Whisper STT

**Purpose:** Transcribe speech to text

```python
# File: src/reachy_mini_conversation_app/stt/local_whisper.py

import asyncio
import logging
import numpy as np
from typing import AsyncIterator, Optional
from faster_whisper import WhisperModel


logger = logging.getLogger(__name__)


class FasterWhisperSTT:
    """Local speech-to-text using Faster-Whisper."""

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cuda",
        compute_type: str = "float16",
        sample_rate: int = 24000,
    ):
        """Initialize Faster-Whisper.

        Args:
            model_size: Model size (tiny.en, base.en, small.en, medium.en)
            device: Device (cuda, cpu)
            compute_type: Compute type (float16, int8, int8_float16)
            sample_rate: Input audio sample rate
        """
        self.sample_rate = sample_rate

        logger.info(f"Loading Whisper model: {model_size} on {device}")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        logger.info("Whisper model loaded")

    def transcribe(
        self,
        audio: np.ndarray,
        language: str = "en",
    ) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio data (float32, normalized -1 to 1)
            language: Language code

        Returns:
            Transcribed text
        """
        # Faster-Whisper expects float32 audio
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        # Transcribe
        segments, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,  # Use internal VAD filtering
            vad_parameters=dict(
                threshold=0.5,
                min_speech_duration_ms=250,
            ),
        )

        # Collect all segments
        text = " ".join([segment.text for segment in segments])
        return text.strip()

    async def transcribe_async(
        self,
        audio: np.ndarray,
        language: str = "en",
    ) -> str:
        """Async transcription wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.transcribe,
            audio,
            language,
        )


# Example usage:
# stt = FasterWhisperSTT(model_size="base.en", device="cuda")
# text = await stt.transcribe_async(audio_buffer)
```

**Reflection:**
- ✅ Very fast (16x realtime on base.en with GPU)
- ✅ Good accuracy
- ✅ Built-in VAD filtering
- ⚠️ Needs decent audio buffer (1-5 seconds) for accuracy
- 💡 Idea: Use streaming mode for partial transcripts

---

### 3.3 Component C: LMStudio Client

**Purpose:** LLM inference with function calling

```python
# File: src/reachy_mini_conversation_app/llm/lmstudio_client.py

import json
import logging
import asyncio
from typing import Any, Dict, List, AsyncIterator, Optional
from openai import AsyncOpenAI


logger = logging.getLogger(__name__)


class LMStudioClient:
    """LMStudio client with OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "local-model",  # Will use whatever is loaded in LMStudio
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """Initialize LMStudio client.

        Args:
            base_url: LMStudio server URL
            model: Model identifier (use "local-model" for LMStudio)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed",  # LMStudio doesn't require API key
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Conversation history
        self.messages: List[Dict[str, Any]] = []

    def add_system_message(self, content: str):
        """Add system message to conversation."""
        self.messages.append({
            "role": "system",
            "content": content,
        })

    def add_user_message(self, content: str):
        """Add user message to conversation."""
        self.messages.append({
            "role": "user",
            "content": content,
        })

    def add_assistant_message(self, content: str):
        """Add assistant message to conversation."""
        self.messages.append({
            "role": "assistant",
            "content": content,
        })

    def add_tool_result(self, tool_call_id: str, result: str):
        """Add tool call result to conversation."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })

    async def chat_completion(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate chat completion.

        Args:
            tools: List of tool definitions (function calling)

        Returns:
            Response dictionary with content or tool_calls
        """
        try:
            # Build request kwargs
            kwargs = {
                "model": self.model,
                "messages": self.messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            # Add tools if provided
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            # Make API call
            response = await self.client.chat.completions.create(**kwargs)

            # Extract response
            choice = response.choices[0]
            message = choice.message

            # Check if tool calls
            if message.tool_calls:
                return {
                    "type": "tool_calls",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        }
                        for tc in message.tool_calls
                    ],
                }

            # Regular text response
            return {
                "type": "text",
                "content": message.content or "",
            }

        except Exception as e:
            logger.error(f"LMStudio API error: {e}")
            return {
                "type": "error",
                "content": f"LLM error: {str(e)}",
            }

    async def chat_completion_stream(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """Generate streaming chat completion.

        Args:
            tools: List of tool definitions

        Yields:
            Text chunks
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": self.messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            stream = await self.client.chat.completions.create(**kwargs)

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LMStudio streaming error: {e}")
            yield f"Error: {str(e)}"

    def clear_history(self):
        """Clear conversation history."""
        self.messages = []


# Example usage:
# client = LMStudioClient()
# client.add_system_message("You are a helpful robot assistant.")
# client.add_user_message("What's the weather?")
# response = await client.chat_completion(tools=tool_specs)
```

**Reflection:**
- ✅ OpenAI-compatible = easy integration
- ✅ Tool calling works with compatible models
- ⚠️ Need to manage conversation history
- 💡 Consider streaming for better UX

---

### 3.4 Component D: Piper TTS

**Purpose:** Text-to-speech synthesis

```python
# File: src/reachy_mini_conversation_app/tts/piper_tts.py

import asyncio
import logging
import numpy as np
import subprocess
import tempfile
import wave
from typing import Optional
from pathlib import Path


logger = logging.getLogger(__name__)


class PiperTTS:
    """Piper TTS for speech synthesis."""

    def __init__(
        self,
        model_path: str = "en_US-lessac-medium.onnx",
        config_path: Optional[str] = None,
        speaker_id: int = 0,
        sample_rate: int = 22050,
    ):
        """Initialize Piper TTS.

        Args:
            model_path: Path to Piper ONNX model
            config_path: Path to model config (auto-detect if None)
            speaker_id: Speaker ID for multi-speaker models
            sample_rate: Output sample rate
        """
        self.model_path = Path(model_path)
        self.config_path = Path(config_path) if config_path else self.model_path.with_suffix(".json")
        self.speaker_id = speaker_id
        self.sample_rate = sample_rate

        # Verify Piper installation
        try:
            subprocess.run(
                ["piper", "--version"],
                check=True,
                capture_output=True,
            )
            logger.info("Piper TTS ready")
        except FileNotFoundError:
            logger.error("Piper not found. Install with: pip install piper-tts")
            raise

    def synthesize(self, text: str) -> np.ndarray:
        """Synthesize text to audio.

        Args:
            text: Text to synthesize

        Returns:
            Audio array (float32, normalized -1 to 1)
        """
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name

        try:
            # Run Piper
            process = subprocess.Popen(
                [
                    "piper",
                    "--model", str(self.model_path),
                    "--config", str(self.config_path),
                    "--output_file", output_path,
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Send text to stdin
            process.communicate(input=text.encode("utf-8"))

            # Read WAV file
            with wave.open(output_path, "rb") as wav:
                audio_data = wav.readframes(wav.getnframes())
                audio = np.frombuffer(audio_data, dtype=np.int16)

            # Convert to float32 and normalize
            audio = audio.astype(np.float32) / 32768.0

            return audio

        finally:
            # Cleanup temp file
            Path(output_path).unlink(missing_ok=True)

    async def synthesize_async(self, text: str) -> np.ndarray:
        """Async synthesis wrapper."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.synthesize, text)

    def synthesize_to_24khz_pcm(self, text: str) -> np.ndarray:
        """Synthesize and resample to 24kHz int16 PCM.

        Args:
            text: Text to synthesize

        Returns:
            Audio array (int16, 24kHz)
        """
        # Synthesize
        audio = self.synthesize(text)

        # Resample to 24kHz if needed
        if self.sample_rate != 24000:
            from scipy import signal
            num_samples = int(len(audio) * 24000 / self.sample_rate)
            audio = signal.resample(audio, num_samples)

        # Convert back to int16
        audio = (audio * 32768.0).astype(np.int16)

        return audio


# Example usage:
# tts = PiperTTS(model_path="voices/en_US-lessac-medium.onnx")
# audio = await tts.synthesize_async("Hello, I am Reachy Mini!")
```

**Reflection:**
- ✅ Fast synthesis (~2-4x realtime)
- ✅ Good quality
- ✅ Low resource usage
- ⚠️ Not streaming (need full text first)
- 💡 Idea: Use sentence splitting for faster perceived response

---

## 4. FULL HANDLER IMPLEMENTATION

### 4.1 LocalLLMRealtimeHandler

```python
# File: src/reachy_mini_conversation_app/handlers/local_llm_handler.py

import asyncio
import base64
import logging
import numpy as np
from typing import Tuple, Optional, Dict, Any
from collections import deque
from dataclasses import dataclass
from numpy.typing import NDArray

import cv2
import gradio as gr
from fastrtc import AsyncStreamHandler, AdditionalOutputs

from reachy_mini_conversation_app.config import config
from reachy_mini_conversation_app.prompts import get_session_instructions
from reachy_mini_conversation_app.tools.core_tools import (
    ToolDependencies,
    get_tool_specs,
    dispatch_tool_call,
)
from reachy_mini_conversation_app.vad.silero_vad import SileroVAD
from reachy_mini_conversation_app.stt.local_whisper import FasterWhisperSTT
from reachy_mini_conversation_app.llm.lmstudio_client import LMStudioClient
from reachy_mini_conversation_app.tts.piper_tts import PiperTTS


logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Track conversation state."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

    current: str = IDLE


class LocalLLMRealtimeHandler(AsyncStreamHandler):
    """Fully local LLM handler using LMStudio + Whisper + Piper."""

    def __init__(self, deps: ToolDependencies):
        """Initialize the handler."""
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            input_sample_rate=16000,
        )
        self.deps = deps

        # Audio configuration
        self.target_input_rate = 24000
        self.resample_ratio = self.target_input_rate / self.input_sample_rate

        # Components (initialized in start_up)
        self.vad: Optional[SileroVAD] = None
        self.stt: Optional[FasterWhisperSTT] = None
        self.llm: Optional[LMStudioClient] = None
        self.tts: Optional[PiperTTS] = None

        # State
        self.state = ConversationState()
        self.audio_buffer = deque(maxlen=int(24000 * 10))  # 10 seconds max
        self.speech_buffer: list = []
        self.output_queue: asyncio.Queue = asyncio.Queue()

        # Timing
        self.last_speech_time = 0.0
        self.speech_start_time = 0.0

    def copy(self):
        """Create a copy of the handler."""
        return LocalLLMRealtimeHandler(self.deps)

    def resample_audio(self, audio: NDArray[np.int16]) -> NDArray[np.int16]:
        """Resample audio using linear interpolation."""
        if self.input_sample_rate == self.target_input_rate:
            return audio

        input_length = len(audio)
        output_length = int(input_length * self.resample_ratio)

        input_time = np.arange(input_length)
        output_time = np.linspace(0, input_length - 1, output_length)

        resampled = np.interp(output_time, input_time, audio.astype(np.float32))
        return resampled.astype(np.int16)

    async def start_up(self) -> None:
        """Initialize all local components."""
        logger.info("Initializing local LLM handler...")

        try:
            # Initialize VAD
            logger.info("Loading Silero VAD...")
            self.vad = SileroVAD(
                sample_rate=self.target_input_rate,
                threshold=0.5,
                min_speech_duration_ms=250,
                min_silence_duration_ms=500,
            )

            # Initialize STT
            logger.info("Loading Faster-Whisper...")
            self.stt = FasterWhisperSTT(
                model_size=getattr(config, "WHISPER_MODEL", "base.en"),
                device=getattr(config, "WHISPER_DEVICE", "cuda"),
                compute_type="float16",
                sample_rate=self.target_input_rate,
            )

            # Initialize LLM
            logger.info("Connecting to LMStudio...")
            self.llm = LMStudioClient(
                base_url=getattr(config, "LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
                model=getattr(config, "LMSTUDIO_MODEL", "local-model"),
                temperature=0.7,
                max_tokens=500,
            )

            # Add system message
            self.llm.add_system_message(get_session_instructions())

            # Initialize TTS
            logger.info("Loading Piper TTS...")
            self.tts = PiperTTS(
                model_path=getattr(config, "PIPER_MODEL_PATH", "en_US-lessac-medium.onnx"),
                sample_rate=22050,
            )

            logger.info("✅ Local LLM handler ready!")

        except Exception as e:
            logger.error(f"Failed to initialize local LLM handler: {e}")
            raise

    async def receive(self, frame: Tuple[int, NDArray[np.int16]]) -> None:
        """Receive audio frame from microphone."""
        if not self.vad:
            return

        _, audio = frame
        audio = audio.squeeze()

        # Resample if needed
        if self.input_sample_rate != self.target_input_rate:
            audio = self.resample_audio(audio)

        # Add to buffer
        self.audio_buffer.extend(audio)

        # Run VAD
        vad_result = self.vad(audio)

        if vad_result:
            if "start" in vad_result:
                # Speech started
                logger.debug("Speech started")
                self.state.current = ConversationState.LISTENING
                self.speech_start_time = asyncio.get_event_loop().time()
                self.speech_buffer = []

                # Clear output queue (interrupt)
                while not self.output_queue.empty():
                    try:
                        self.output_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                # Notify movement manager
                self.deps.movement_manager.set_listening(True)

                # Send partial transcript
                await self.output_queue.put(
                    AdditionalOutputs({"role": "user_partial", "content": "[Listening...]"})
                )

            elif "end" in vad_result:
                # Speech ended
                logger.debug("Speech ended")
                self.state.current = ConversationState.PROCESSING
                self.deps.movement_manager.set_listening(False)

                # Process the speech
                asyncio.create_task(self._process_speech())

        # If listening, accumulate speech
        if self.state.current == ConversationState.LISTENING:
            self.speech_buffer.extend(audio)

    async def _process_speech(self):
        """Process accumulated speech."""
        if not self.stt or not self.llm or not self.tts:
            logger.error("Components not initialized")
            return

        if not self.speech_buffer:
            logger.warning("No speech buffer to process")
            return

        try:
            # Convert buffer to numpy array
            speech_audio = np.array(self.speech_buffer, dtype=np.int16)

            # Transcribe
            logger.debug("Transcribing speech...")
            transcript = await self.stt.transcribe_async(speech_audio)

            if not transcript:
                logger.warning("Empty transcript")
                return

            logger.info(f"User: {transcript}")

            # Send transcript to UI
            await self.output_queue.put(
                AdditionalOutputs({"role": "user", "content": transcript})
            )

            # Add to conversation
            self.llm.add_user_message(transcript)

            # Get LLM response
            logger.debug("Generating LLM response...")
            response = await self.llm.chat_completion(tools=get_tool_specs())

            # Handle response
            if response["type"] == "tool_calls":
                # Handle tool calls
                for tool_call in response["tool_calls"]:
                    await self._handle_tool_call(tool_call)

                # Get follow-up response
                response = await self.llm.chat_completion()

            if response["type"] == "text":
                # Speak response
                await self._speak(response["content"])

        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            await self._speak("Sorry, I encountered an error.")

        finally:
            self.state.current = ConversationState.IDLE
            self.speech_buffer = []

    async def _handle_tool_call(self, tool_call: Dict[str, Any]):
        """Handle a tool call."""
        tool_name = tool_call["name"]
        tool_args = tool_call["arguments"]
        call_id = tool_call["id"]

        logger.info(f"Tool call: {tool_name}({tool_args})")

        # Notify UI
        await self.output_queue.put(
            AdditionalOutputs({
                "role": "assistant",
                "content": f"🛠️ Using tool: {tool_name}",
                "metadata": {"title": f"🛠️ {tool_name}", "status": "running"},
            })
        )

        # Execute tool
        import json
        tool_result = await dispatch_tool_call(
            tool_name,
            json.dumps(tool_args),
            self.deps,
        )

        logger.debug(f"Tool result: {tool_result}")

        # Add result to conversation
        if self.llm:
            self.llm.add_tool_result(call_id, json.dumps(tool_result))

        # Handle camera tool
        if tool_name == "camera" and "b64_im" in tool_result:
            # Display image in UI
            if self.deps.camera_worker:
                np_img = self.deps.camera_worker.get_latest_frame()
                if np_img is not None:
                    rgb_frame = cv2.cvtColor(np_img, cv2.COLOR_BGR2RGB)
                    img = gr.Image(value=rgb_frame)
                    await self.output_queue.put(
                        AdditionalOutputs({"role": "assistant", "content": img})
                    )

    async def _speak(self, text: str):
        """Synthesize and queue speech."""
        if not self.tts or not text:
            return

        logger.info(f"Assistant: {text}")

        # Send transcript to UI
        await self.output_queue.put(
            AdditionalOutputs({"role": "assistant", "content": text})
        )

        # Add to conversation
        if self.llm:
            self.llm.add_assistant_message(text)

        # Synthesize speech
        self.state.current = ConversationState.SPEAKING

        try:
            # Split text into sentences for faster response
            sentences = self._split_sentences(text)

            for sentence in sentences:
                # Synthesize
                audio = await self.tts.synthesize_async(sentence)

                # Convert to int16 PCM 24kHz
                audio_24k = self.tts.synthesize_to_24khz_pcm(sentence)

                # Queue for playback
                # Chunk into frames (480 samples = 20ms at 24kHz)
                chunk_size = 480
                for i in range(0, len(audio_24k), chunk_size):
                    chunk = audio_24k[i : i + chunk_size]
                    if len(chunk) > 0:
                        await self.output_queue.put(
                            (24000, chunk.reshape(1, -1))
                        )

                        # Feed to head wobbler
                        if self.deps.head_wobbler:
                            # Convert to base64 for wobbler (expects OpenAI format)
                            chunk_b64 = base64.b64encode(chunk.tobytes()).decode()
                            self.deps.head_wobbler.feed(chunk_b64)

        except Exception as e:
            logger.error(f"TTS error: {e}")

        finally:
            self.state.current = ConversationState.IDLE

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    async def emit(self) -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None:
        """Emit audio frame or UI updates."""
        try:
            return await asyncio.wait_for(
                self.output_queue.get(),
                timeout=0.02,
            )
        except asyncio.TimeoutError:
            return None

    async def shutdown(self) -> None:
        """Cleanup resources."""
        logger.info("Shutting down local LLM handler...")

        # Clear queues
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Reset state
        self.state.current = ConversationState.IDLE
        self.audio_buffer.clear()
        self.speech_buffer = []

        logger.info("Local LLM handler shutdown complete")
```

**Reflection:**
- ✅ Implements full AsyncStreamHandler interface
- ✅ Integrates all components (VAD, STT, LLM, TTS)
- ✅ Supports tool calling
- ✅ Handles interruptions
- ⚠️ Sequential processing = higher latency than OpenAI realtime
- 💡 Future: Add streaming for lower perceived latency

---

## 5. CONFIGURATION

### 5.1 Update config.py

```python
# src/reachy_mini_conversation_app/config.py

class Config:
    # ... existing config ...

    # LLM Backend Selection
    LLM_BACKEND = os.getenv("LLM_BACKEND", "openai")  # openai | lmstudio

    # LMStudio Configuration
    LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")

    # Whisper Configuration
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")

    # Piper TTS Configuration
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "en_US-lessac-medium.onnx")
```

### 5.2 Update .env.example

```bash
# LLM Backend Selection
LLM_BACKEND=lmstudio  # openai | lmstudio

# LMStudio Configuration (when LLM_BACKEND=lmstudio)
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model

# Local STT Configuration
WHISPER_MODEL=base.en  # tiny.en | base.en | small.en | medium.en
WHISPER_DEVICE=cuda    # cuda | cpu

# Local TTS Configuration
PIPER_MODEL_PATH=voices/en_US-lessac-medium.onnx
```

### 5.3 Update main.py

```python
# src/reachy_mini_conversation_app/main.py

def main():
    # ... existing code ...

    # Create handler based on config
    if config.LLM_BACKEND == "lmstudio":
        from reachy_mini_conversation_app.handlers.local_llm_handler import LocalLLMRealtimeHandler
        handler = LocalLLMRealtimeHandler(deps)
    else:
        from reachy_mini_conversation_app.openai_realtime import OpenaiRealtimeHandler
        handler = OpenaiRealtimeHandler(deps)

    # ... rest of main ...
```

---

## 6. SETUP GUIDE

### 6.1 Install Dependencies

```bash
# Update pyproject.toml
[project.optional-dependencies]
local_llm = [
    "faster-whisper>=1.0.0",
    "piper-tts>=1.2.0",
    "torch>=2.0.0",  # Already in local_vision
]

# Install
uv sync --extra local_llm
# or
pip install -e .[local_llm]
```

### 6.2 Setup LMStudio

1. **Download LMStudio:**
   - Visit: https://lmstudio.ai/
   - Download for your platform

2. **Download a Model:**
   ```
   Recommended: NousResearch/Hermes-2-Pro-Llama-3-8B-GGUF
   Quantization: Q4_K_M (good balance of speed/quality)
   Size: ~4.5GB
   ```

3. **Start LMStudio Server:**
   - Open LMStudio
   - Go to "Local Server" tab
   - Load your model
   - Start server on port 1234

4. **Test Connection:**
   ```python
   import requests
   response = requests.get("http://localhost:1234/v1/models")
   print(response.json())
   ```

### 6.3 Setup Whisper

```bash
# Faster-Whisper will auto-download models on first use
# Models cached to: ~/.cache/huggingface/hub/

# Pre-download (optional):
python -c "from faster_whisper import WhisperModel; WhisperModel('base.en')"
```

### 6.4 Setup Piper

```bash
# Install Piper
pip install piper-tts

# Download voice model
mkdir -p voices
cd voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

# Test
echo "Hello from Piper" | piper --model voices/en_US-lessac-medium.onnx --output_file test.wav
```

### 6.5 Configuration

```bash
# Create .env
cp .env.example .env

# Edit .env
LLM_BACKEND=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
WHISPER_MODEL=base.en
WHISPER_DEVICE=cuda
PIPER_MODEL_PATH=voices/en_US-lessac-medium.onnx
```

---

## 7. TESTING

### 7.1 Component Tests

```bash
# Test VAD
python -c "
from reachy_mini_conversation_app.vad.silero_vad import SileroVAD
import numpy as np
vad = SileroVAD()
audio = np.random.randn(4800).astype(np.float32)
result = vad(audio)
print(f'VAD result: {result}')
"

# Test STT
python -c "
import asyncio
from reachy_mini_conversation_app.stt.local_whisper import FasterWhisperSTT
stt = FasterWhisperSTT()
# Generate 3 seconds of test audio
import numpy as np
audio = np.random.randn(24000 * 3).astype(np.float32)
text = asyncio.run(stt.transcribe_async(audio))
print(f'Transcript: {text}')
"

# Test LMStudio
python -c "
import asyncio
from reachy_mini_conversation_app.llm.lmstudio_client import LMStudioClient
async def test():
    client = LMStudioClient()
    client.add_user_message('Hello!')
    response = await client.chat_completion()
    print(f'Response: {response}')
asyncio.run(test())
"

# Test TTS
python -c "
import asyncio
from reachy_mini_conversation_app.tts.piper_tts import PiperTTS
tts = PiperTTS(model_path='voices/en_US-lessac-medium.onnx')
audio = asyncio.run(tts.synthesize_async('Hello from Piper!'))
print(f'Generated {len(audio)} audio samples')
"
```

### 7.2 Integration Test

```bash
# Run the app with local LLM
reachy-mini-conversation-app --gradio

# Expected startup logs:
# - ✅ Loading Silero VAD...
# - ✅ Loading Faster-Whisper...
# - ✅ Connecting to LMStudio...
# - ✅ Loading Piper TTS...
# - ✅ Local LLM handler ready!
```

---

## 8. TROUBLESHOOTING

### 8.1 Common Issues

**Issue: LMStudio connection failed**
```
Solution:
1. Ensure LMStudio server is running
2. Check port 1234 is open
3. Try: curl http://localhost:1234/v1/models
```

**Issue: Whisper CUDA out of memory**
```
Solution:
1. Use smaller model: WHISPER_MODEL=tiny.en
2. Use CPU: WHISPER_DEVICE=cpu
3. Free GPU memory from other processes
```

**Issue: Piper model not found**
```
Solution:
1. Download voice model to correct path
2. Update PIPER_MODEL_PATH in .env
3. Check file exists: ls -la voices/
```

**Issue: High latency**
```
Solution:
1. Use faster Whisper model (tiny.en)
2. Use quantized LLM (Q4_K_M)
3. Enable GPU acceleration
4. Check CPU/GPU usage during inference
```

---

## 9. PERFORMANCE TUNING

### 9.1 Latency Breakdown

```
Component            | Time (ms)  | Optimization
---------------------|------------|---------------------------
VAD detection        | 5-10       | Already optimal
Audio buffering      | 500-1000   | Trade-off with accuracy
Whisper transcribe   | 200-800    | Use smaller model / GPU
LLM inference        | 500-2000   | Use quantized model / GPU
Tool execution       | 50-500     | Varies by tool
TTS synthesis        | 300-1000   | Sentence splitting
Total                | 1555-5310  | Target: <2000ms
```

### 9.2 Optimization Strategies

**1. Model Selection:**
```python
# Fast setup (lower quality)
WHISPER_MODEL=tiny.en           # ~200ms transcription
LMSTUDIO_MODEL=llama-3-8b-Q4    # ~500ms inference
PIPER_VOICE=lessac-low          # ~300ms synthesis
# Total: ~1000ms

# Balanced setup (recommended)
WHISPER_MODEL=base.en           # ~400ms
LMSTUDIO_MODEL=hermes-2-pro-Q4  # ~800ms
PIPER_VOICE=lessac-medium       # ~500ms
# Total: ~1700ms

# Quality setup (slower)
WHISPER_MODEL=small.en          # ~800ms
LMSTUDIO_MODEL=hermes-2-pro-Q5  # ~1200ms
PIPER_VOICE=lessac-high         # ~800ms
# Total: ~2800ms
```

**2. Streaming Improvements:**
```python
# Current: Wait for full synthesis
# Future: Stream audio as it's generated

async def _speak_streaming(self, text: str):
    # Split into sentences
    sentences = self._split_sentences(text)

    for sentence in sentences:
        # Start synthesis immediately
        audio_task = asyncio.create_task(
            self.tts.synthesize_async(sentence)
        )

        # Await and stream
        audio = await audio_task
        # Queue immediately (don't wait for all sentences)
        await self._queue_audio(audio)
```

**3. Parallel Processing:**
```python
# Process VAD and STT in parallel where possible
# Use multiprocessing for CPU-bound tasks
```

---

## 10. NEXT STEPS

### Implementation Checklist:

- [ ] Create directory structure for new components
- [ ] Implement SileroVAD class
- [ ] Implement FasterWhisperSTT class
- [ ] Implement LMStudioClient class
- [ ] Implement PiperTTS class
- [ ] Implement LocalLLMRealtimeHandler
- [ ] Update config.py with new settings
- [ ] Update .env.example
- [ ] Update main.py with handler factory
- [ ] Update pyproject.toml dependencies
- [ ] Test each component individually
- [ ] Test full integration
- [ ] Write documentation
- [ ] Create usage examples

### Future Enhancements:

- [ ] Add streaming STT (partial transcripts)
- [ ] Add streaming TTS (lower latency)
- [ ] Support multiple LLM backends (Ollama, vLLM)
- [ ] Add voice activity visualization
- [ ] Add latency monitoring
- [ ] Add conversation export/import
- [ ] Support custom wake words
- [ ] Add emotion detection from voice

---

**End of LMStudio Integration Guide**

This guide provides a complete roadmap for integrating local LLM capabilities using LMStudio. The modular design ensures compatibility with the existing codebase while enabling fully local, privacy-preserving operation.
