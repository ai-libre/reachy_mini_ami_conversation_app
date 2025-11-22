# Reachy Mini Conversation App - Architecture Analysis

**Date:** 2025-11-22
**Purpose:** Understanding current architecture for local LLM/VLM integration
**Approach:** Ultrathink (Propose → Reflect)

---

## 1. CURRENT ARCHITECTURE ANALYSIS

### 1.1 Core Components

The application follows a **layered, event-driven architecture** with the following key components:

#### **A. LLM Integration Layer** (`openai_realtime.py`)
- **Current Implementation:** OpenAI Realtime API (WebSocket-based)
- **Key Class:** `OpenaiRealtimeHandler(AsyncStreamHandler)`
- **Features:**
  - Real-time bidirectional audio streaming
  - Server-side VAD (Voice Activity Detection)
  - Function calling (tool execution)
  - Automatic transcription (Whisper)
  - Audio format: PCM 24kHz output, 16kHz input (resampled to 24kHz)

**Critical Dependencies:**
```python
- AsyncOpenAI client
- WebSocket connection to OpenAI
- Event-driven async architecture
- Audio resampling (16kHz → 24kHz)
```

#### **B. Vision Processing** (`vision/processors.py`)
- **Dual Mode Support:**
  1. **Remote Vision:** GPT-realtime vision (default, via camera tool)
  2. **Local Vision:** SmolVLM2-2.2B-Instruct (optional, via `--local-vision`)

**Local Vision Implementation:**
```python
class VisionProcessor:
    - Model: SmolVLM2 (HuggingFace Transformers)
    - Device support: CUDA, MPS (Apple Silicon), CPU
    - Periodic processing: 5-second intervals
    - Async threading architecture
```

#### **C. Tool System** (`tools/core_tools.py`)
- **Architecture:** Plugin-based with profile support
- **Tool Discovery:**
  1. Profile-specific tools (`profiles/{name}/tool_name.py`)
  2. Shared tools library (`tools/tool_name.py`)

**Tool Execution Flow:**
```
LLM → function_call_arguments.done event
    → dispatch_tool_call()
    → Tool.__call__(deps, **kwargs)
    → Result sent back to LLM
```

**Available Tools:**
- `move_head`, `camera`, `head_tracking`
- `dance`, `stop_dance`
- `play_emotion`, `stop_emotion`
- `do_nothing`

#### **D. Audio Pipeline** (`audio/`)
- **Head Wobbler:** Speech-reactive head motion
- **Speech Tapper:** Rhythm-based motion
- **Integration:** Feeds from OpenAI audio deltas

#### **E. Movement System** (`moves.py`)
- **MovementManager:** Queues and blends multiple motion layers
- **Layers:**
  - Primary moves (dances, emotions, poses)
  - Speech-reactive wobble
  - Face-tracking offsets

#### **F. Stream Management**
- **Web Mode:** Gradio UI with FastRTC
- **Console Mode:** LocalStream for direct audio

---

## 2. INTEGRATION POINTS FOR LOCAL LLM

### 2.1 Critical Integration Points

#### **A. Handler Interface** (`AsyncStreamHandler`)
The `OpenaiRealtimeHandler` implements FastRTC's `AsyncStreamHandler` protocol:

```python
class AsyncStreamHandler:
    async def start_up() -> None
    async def receive(frame: Tuple[int, NDArray[np.int16]]) -> None
    async def emit() -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None
    async def shutdown() -> None
```

**Requirements for Local LLM:**
- Must implement same async interface
- Handle audio input streaming
- Generate audio output streaming
- Support tool calling mechanism
- Provide transcription capabilities

#### **B. Event System**
Current OpenAI events that must be replicated:

```python
# User Events
- input_audio_buffer.speech_started
- input_audio_buffer.speech_stopped
- conversation.item.input_audio_transcription.partial
- conversation.item.input_audio_transcription.completed

# Assistant Events
- response.created
- response.audio.delta  # PCM audio chunks
- response.audio_transcript.done
- response.done

# Tool Events
- response.function_call_arguments.done
```

#### **C. Audio Processing Requirements**
```python
Input:  16kHz PCM mono (from ReSpeaker)
        ↓ (resample)
        24kHz PCM mono (to LLM)

Output: 24kHz PCM mono (from LLM)
        → Direct to speaker
```

---

## 3. PROPOSAL: LOCAL LLM INTEGRATION

### 3.1 Architecture Option A: LMStudio as Backend

**Approach:** Replace OpenAI client with LMStudio API (OpenAI-compatible)

```python
class LocalLLMRealtimeHandler(AsyncStreamHandler):
    """Local LLM handler using LMStudio backend."""

    def __init__(self, deps: ToolDependencies):
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            input_sample_rate=16000,
        )
        self.deps = deps

        # Components needed:
        self.llm_client = None       # LMStudio API client
        self.tts_engine = None       # Local TTS (e.g., Coqui TTS, Piper)
        self.stt_engine = None       # Local STT (e.g., Whisper.cpp, Faster-Whisper)
        self.vad_detector = None     # VAD (e.g., Silero VAD)
```

**Component Breakdown:**

#### **3.1.1 Speech-to-Text (STT)**
Options:
1. **Faster-Whisper** (Recommended)
   - Fast inference with CTranslate2
   - Supports streaming
   - Low latency

2. **Whisper.cpp**
   - C++ implementation
   - Very fast
   - Lower memory footprint

Implementation:
```python
from faster_whisper import WhisperModel

class LocalSTT:
    def __init__(self):
        self.model = WhisperModel(
            "base.en",  # or "small.en", "medium.en"
            device="cuda",  # or "cpu"
            compute_type="float16"
        )

    async def transcribe_stream(self, audio_buffer):
        # Accumulate audio until VAD detects pause
        # Return partial and final transcripts
        pass
```

#### **3.1.2 Voice Activity Detection (VAD)**
**Silero VAD** (Recommended)
```python
import torch

class LocalVAD:
    def __init__(self):
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad'
        )
        self.get_speech_timestamps = utils[0]

    def detect_speech(self, audio_chunk):
        # Returns speech/non-speech timestamps
        pass
```

#### **3.1.3 LLM Backend (LMStudio)**
**Configuration:**
```python
from openai import AsyncOpenAI  # LMStudio has OpenAI-compatible API

class LMStudioClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url="http://localhost:1234/v1",  # LMStudio default
            api_key="not-needed"
        )

    async def chat_completion(self, messages, tools):
        response = await self.client.chat.completions.create(
            model="local-model",  # Model loaded in LMStudio
            messages=messages,
            tools=tools,
            stream=True
        )
        async for chunk in response:
            yield chunk
```

**Recommended Local Models:**
- **Qwen2.5-7B-Instruct** (function calling support)
- **Mistral-7B-Instruct-v0.3** (function calling)
- **Llama-3.1-8B-Instruct** (tool use)
- **Hermes-2-Pro-Llama-3-8B** (excellent function calling)

#### **3.1.4 Text-to-Speech (TTS)**
Options:

**Option A: Piper TTS** (Fast, high quality)
```python
from piper import PiperVoice

class LocalTTS:
    def __init__(self):
        self.voice = PiperVoice.load(
            "en_US-lessac-medium.onnx"
        )

    async def synthesize_stream(self, text):
        # Returns PCM audio chunks
        for audio_chunk in self.voice.synthesize_stream_raw(text):
            yield audio_chunk
```

**Option B: Coqui TTS** (More natural, slower)
```python
from TTS.api import TTS

class CoquiTTS:
    def __init__(self):
        self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")

    async def synthesize(self, text):
        wav = self.tts.tts(text)
        return wav
```

**Option C: StyleTTS2** (SOTA quality, slower)

#### **3.1.5 Vision (Already Implemented!)**
The codebase already has local vision with SmolVLM2:
- Use existing `VisionProcessor` class
- Already supports CUDA/MPS/CPU
- Already integrated with camera tool

---

### 3.2 Architecture Option B: Hybrid Approach

**Concept:** Use Claude API for LLM reasoning, local models for STT/TTS/Vision

```python
class HybridHandler(AsyncStreamHandler):
    """Hybrid handler: Claude LLM + Local STT/TTS/Vision."""

    def __init__(self, deps: ToolDependencies):
        # Local components
        self.stt = LocalSTT()
        self.tts = LocalTTS()
        self.vad = LocalVAD()

        # Cloud LLM
        self.claude_client = anthropic.AsyncAnthropic()

        # Already have local vision!
        # Use existing VisionProcessor
```

**Benefits:**
- Best LLM reasoning (Claude)
- Privacy for audio (local STT/TTS)
- Already have local vision
- Faster audio pipeline
- No audio sent to cloud

---

## 4. REFLECTION: CHOOSING THE RIGHT APPROACH

### 4.1 Option A Analysis: Fully Local (LMStudio)

**✅ Advantages:**
1. **Complete Privacy:** All data stays local
2. **No API Costs:** One-time compute investment
3. **Offline Operation:** No internet dependency
4. **Customization:** Full control over all models
5. **Existing Vision:** SmolVLM2 already working

**❌ Challenges:**
1. **Complexity:** Need to integrate 4 separate models (STT, VAD, LLM, TTS)
2. **Latency:** Chain of models adds delay
   - Audio → VAD → STT → LLM → TTS → Audio
   - Estimated: 1-3 seconds total latency
3. **Hardware Requirements:**
   - LLM: 7B-8B models need 8-16GB VRAM
   - Whisper: 1-2GB VRAM
   - TTS: 1-2GB VRAM or CPU
   - Total: ~12-20GB VRAM or mixed CPU/GPU
4. **Function Calling:** Not all local models support robust function calling
5. **Streaming Complexity:** Each component needs async streaming
6. **No Real-time Audio:** Unlike OpenAI's realtime API, this is sequential

### 4.2 Option B Analysis: Hybrid (Claude + Local Audio/Vision)

**✅ Advantages:**
1. **Best LLM Quality:** Claude's reasoning and function calling
2. **Faster Audio:** Local STT/TTS reduces network latency
3. **Privacy Hybrid:** Audio stays local, only text to Claude
4. **Simpler Integration:** Reuse existing tool system
5. **Local Vision:** Already have SmolVLM2
6. **Proven Stack:** Claude + local models is tested

**❌ Challenges:**
1. **API Costs:** Claude API usage (but cheaper without audio)
2. **Internet Required:** For Claude API
3. **Latency:** Still sequential processing
4. **Complexity:** Need to build state machine for conversation

### 4.3 Option C: Enhanced Current (OpenAI + More Local Vision)

**Keep current architecture but enhance:**
- Keep OpenAI Realtime for conversation
- Expand local vision usage
- Add more local vision models (SAM2, YOLO-World)
- Add local audio processing (noise reduction, etc.)

**✅ Advantages:**
1. **Minimal Changes:** Leverage existing working system
2. **Best Latency:** OpenAI Realtime is optimized
3. **Proven:** Current stack is stable
4. **Easy Wins:** Just add more local vision capabilities

**❌ Disadvantages:**
1. **API Costs:** Highest cost option
2. **Privacy:** Audio/video to cloud
3. **Internet Required:** Always

---

## 5. RECOMMENDED APPROACH: Phased Implementation

### Phase 1: Parallel Development (2 Handlers)
Create modular architecture supporting multiple handlers:

```python
# config.py
class Config:
    LLM_BACKEND = os.getenv("LLM_BACKEND", "openai")  # "openai", "lmstudio", "claude"
    STT_BACKEND = os.getenv("STT_BACKEND", "openai")  # "openai", "whisper"
    TTS_BACKEND = os.getenv("TTS_BACKEND", "openai")  # "openai", "piper", "coqui"
    VISION_BACKEND = os.getenv("VISION_BACKEND", "openai")  # "openai", "local"

# main.py
def create_handler(deps):
    backend = config.LLM_BACKEND
    if backend == "openai":
        return OpenaiRealtimeHandler(deps)
    elif backend == "lmstudio":
        return LocalLLMHandler(deps)
    elif backend == "claude":
        return ClaudeHybridHandler(deps)
```

### Phase 2: Component Development

#### **Step 1: Local STT Integration**
```python
class LocalSTTHandler:
    """Handles local speech-to-text with Faster-Whisper."""

    async def process_audio_stream(self, audio_buffer):
        # VAD detection
        # Accumulate speech segments
        # Transcribe on pause
        # Return partial + final transcripts
```

#### **Step 2: Local TTS Integration**
```python
class LocalTTSHandler:
    """Handles local text-to-speech with Piper."""

    async def synthesize_stream(self, text_stream):
        # Stream text chunks
        # Generate audio chunks
        # Yield PCM audio at 24kHz
```

#### **Step 3: LMStudio Integration**
```python
class LMStudioHandler:
    """Handles LLM inference via LMStudio."""

    async def chat_completion(self, messages, tools):
        # OpenAI-compatible API
        # Support function calling
        # Stream responses
```

#### **Step 4: Full Local Handler**
```python
class LocalLLMRealtimeHandler(AsyncStreamHandler):
    """Fully local realtime handler."""

    def __init__(self, deps):
        self.stt = LocalSTTHandler()
        self.llm = LMStudioHandler()
        self.tts = LocalTTSHandler()
        self.vad = SileroVAD()

        # State machine for conversation
        self.state = ConversationState()
```

---

## 6. IMPLEMENTATION ROADMAP

### 6.1 Milestone 1: Foundation (Week 1-2)
- [x] Architecture analysis (this document)
- [ ] Set up development environment
- [ ] Install LMStudio and test API
- [ ] Test local Whisper (Faster-Whisper)
- [ ] Test local TTS (Piper)
- [ ] Test VAD (Silero)

### 6.2 Milestone 2: Component Integration (Week 3-4)
- [ ] Create `LocalSTTHandler` class
- [ ] Create `LocalTTSHandler` class
- [ ] Create `LocalVADHandler` class
- [ ] Create `LMStudioClient` class
- [ ] Test each component independently

### 6.3 Milestone 3: Handler Development (Week 5-6)
- [ ] Create `LocalLLMRealtimeHandler` skeleton
- [ ] Implement audio receive pipeline
- [ ] Implement STT pipeline
- [ ] Implement LLM pipeline
- [ ] Implement TTS pipeline
- [ ] Implement audio emit pipeline

### 6.4 Milestone 4: Tool Integration (Week 7)
- [ ] Adapt tool calling for local LLM
- [ ] Test function calling with Hermes-2-Pro
- [ ] Integrate with existing tool system
- [ ] Test camera tool with local vision

### 6.5 Milestone 5: Testing & Optimization (Week 8)
- [ ] End-to-end testing
- [ ] Latency optimization
- [ ] Memory optimization
- [ ] Error handling
- [ ] Fallback mechanisms

### 6.6 Milestone 6: Documentation (Week 9)
- [ ] User documentation
- [ ] Configuration guide
- [ ] Model selection guide
- [ ] Troubleshooting guide

---

## 7. TECHNICAL SPECIFICATIONS

### 7.1 Local Model Requirements

#### **STT: Faster-Whisper**
```python
# Installation
pip install faster-whisper

# Models (choose based on accuracy/speed tradeoff)
- tiny.en:    39M params,  ~1GB RAM,   ~32x realtime
- base.en:    74M params,  ~1GB RAM,   ~16x realtime  ← Recommended
- small.en:   244M params, ~2GB RAM,   ~6x realtime
- medium.en:  769M params, ~5GB RAM,   ~2x realtime
```

#### **VAD: Silero VAD**
```python
# Installation
pip install torch  # Already have from local_vision

# Model
- silero_vad: ~1MB, CPU-friendly, <10ms latency
```

#### **LLM: LMStudio Models**
```python
# Recommended models with function calling:
1. Hermes-2-Pro-Llama-3-8B (8GB VRAM)
   - Excellent function calling
   - Fast inference
   - Good reasoning

2. Qwen2.5-7B-Instruct (7GB VRAM)
   - Native function calling
   - Multilingual
   - Good performance

3. Mistral-7B-Instruct-v0.3 (7GB VRAM)
   - Function calling support
   - Fast
   - Good quality
```

#### **TTS: Piper**
```python
# Installation
pip install piper-tts

# Voice models (choose based on quality/speed)
- lessac-low:    22kHz, fast, good quality      ← Recommended
- lessac-medium: 22kHz, medium, better quality
- lessac-high:   22kHz, slow, best quality
```

### 7.2 Hardware Requirements

**Minimum (CPU Only):**
- CPU: 8+ cores
- RAM: 16GB
- Storage: 20GB
- Estimated latency: 2-4 seconds

**Recommended (GPU):**
- GPU: 12GB+ VRAM (RTX 3060, 4070, etc.)
- CPU: 8+ cores
- RAM: 16GB
- Storage: 20GB
- Estimated latency: 0.5-1.5 seconds

**Optimal (High-end GPU):**
- GPU: 24GB+ VRAM (RTX 4090, A5000, etc.)
- CPU: 12+ cores
- RAM: 32GB
- Storage: 50GB
- Estimated latency: 0.3-0.8 seconds

### 7.3 Network Requirements

**Fully Local:** None (all processing on-device)

**Hybrid (Claude):**
- Bandwidth: 1-5 Mbps
- Latency: <100ms to Anthropic servers

---

## 8. CODE STRUCTURE PROPOSAL

```
src/reachy_mini_conversation_app/
├── handlers/
│   ├── __init__.py
│   ├── base.py                    # AsyncStreamHandler base
│   ├── openai_realtime.py         # Current (moved)
│   ├── local_llm_handler.py       # New: Fully local
│   └── claude_hybrid_handler.py   # New: Claude + local audio
│
├── stt/
│   ├── __init__.py
│   ├── base.py                    # STT interface
│   ├── openai_stt.py             # OpenAI Whisper
│   └── local_whisper.py          # Faster-Whisper
│
├── tts/
│   ├── __init__.py
│   ├── base.py                    # TTS interface
│   ├── openai_tts.py             # OpenAI TTS
│   ├── piper_tts.py              # Piper TTS
│   └── coqui_tts.py              # Coqui TTS
│
├── vad/
│   ├── __init__.py
│   ├── base.py                    # VAD interface
│   └── silero_vad.py             # Silero VAD
│
├── llm/
│   ├── __init__.py
│   ├── base.py                    # LLM client interface
│   ├── openai_client.py          # OpenAI client
│   ├── lmstudio_client.py        # LMStudio client
│   └── claude_client.py          # Anthropic client
│
└── vision/
    ├── __init__.py
    ├── processors.py              # Existing SmolVLM2
    └── yolo_head_tracker.py       # Existing YOLO
```

---

## 9. CONFIGURATION EXAMPLE

```bash
# .env file for fully local setup

# Backend selection
LLM_BACKEND=lmstudio          # openai | lmstudio | claude
STT_BACKEND=whisper           # openai | whisper
TTS_BACKEND=piper             # openai | piper | coqui
VISION_BACKEND=local          # openai | local

# LMStudio configuration
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=hermes-2-pro-llama-3-8b

# Local STT configuration
WHISPER_MODEL=base.en         # tiny.en | base.en | small.en | medium.en
WHISPER_DEVICE=cuda           # cuda | cpu

# Local TTS configuration
PIPER_VOICE=en_US-lessac-medium
PIPER_QUALITY=high            # low | medium | high

# Local Vision (existing)
LOCAL_VISION_MODEL=HuggingFaceTB/SmolVLM2-2.2B-Instruct
HF_HOME=./cache

# Hardware optimization
USE_GPU=true
GPU_LAYERS=35                 # For LLM offloading
```

---

## 10. NEXT STEPS

### Immediate Actions:
1. ✅ Create this analysis document
2. [ ] Set up development branch: `feature/local-llm-integration`
3. [ ] Install and test LMStudio
4. [ ] Create proof-of-concept for STT pipeline
5. [ ] Create proof-of-concept for TTS pipeline
6. [ ] Test end-to-end latency

### Questions to Resolve:
1. **Which approach?** Fully local or hybrid?
2. **Which LLM model?** Hermes-2-Pro vs Qwen2.5 vs Mistral?
3. **Which TTS?** Piper vs Coqui vs StyleTTS2?
4. **Acceptable latency?** What's the target response time?
5. **Hardware constraints?** What GPU/CPU is available?

### Research Needed:
- [ ] Benchmark local LLMs for function calling accuracy
- [ ] Test streaming TTS options for latency
- [ ] Evaluate conversation state management
- [ ] Design interrupt handling for local pipeline

---

## 11. APPENDIX: Code Snippets

### A. Minimal Local Handler Skeleton

```python
import asyncio
import logging
from typing import Tuple, Any
import numpy as np
from numpy.typing import NDArray
from fastrtc import AsyncStreamHandler, AdditionalOutputs

logger = logging.getLogger(__name__)


class LocalLLMRealtimeHandler(AsyncStreamHandler):
    """Fully local LLM handler for Reachy Mini."""

    def __init__(self, deps):
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            input_sample_rate=16000,
        )
        self.deps = deps

        # Audio buffers
        self.audio_buffer = []
        self.output_queue = asyncio.Queue()

        # State
        self.is_listening = False
        self.is_speaking = False

    async def start_up(self) -> None:
        """Initialize all local components."""
        logger.info("Initializing local LLM handler...")

        # TODO: Initialize STT
        # self.stt = FasterWhisper()

        # TODO: Initialize VAD
        # self.vad = SileroVAD()

        # TODO: Initialize LLM
        # self.llm = LMStudioClient()

        # TODO: Initialize TTS
        # self.tts = PiperTTS()

        logger.info("Local LLM handler ready!")

    async def receive(self, frame: Tuple[int, NDArray[np.int16]]) -> None:
        """Receive audio from microphone."""
        sample_rate, audio = frame

        # TODO: Buffer audio
        # TODO: Run VAD
        # TODO: When speech detected, transcribe
        # TODO: Send to LLM
        pass

    async def emit(self) -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None:
        """Emit audio to speaker."""
        # TODO: Get audio from TTS queue
        # TODO: Return audio chunks

        try:
            return await asyncio.wait_for(
                self.output_queue.get(),
                timeout=0.02
            )
        except asyncio.TimeoutError:
            return None

    async def shutdown(self) -> None:
        """Cleanup resources."""
        logger.info("Shutting down local LLM handler...")
        # TODO: Cleanup models
```

### B. Configuration Factory

```python
# main.py modification

def create_handler(deps: ToolDependencies):
    """Factory function to create appropriate handler."""
    backend = config.LLM_BACKEND

    if backend == "openai":
        from reachy_mini_conversation_app.handlers.openai_realtime import OpenaiRealtimeHandler
        return OpenaiRealtimeHandler(deps)

    elif backend == "lmstudio":
        from reachy_mini_conversation_app.handlers.local_llm_handler import LocalLLMRealtimeHandler
        return LocalLLMRealtimeHandler(deps)

    elif backend == "claude":
        from reachy_mini_conversation_app.handlers.claude_hybrid_handler import ClaudeHybridHandler
        return ClaudeHybridHandler(deps)

    else:
        raise ValueError(f"Unknown LLM backend: {backend}")


# In main():
# handler = OpenaiRealtimeHandler(deps)  # OLD
handler = create_handler(deps)          # NEW
```

---

**End of Analysis Document**

This document provides a comprehensive foundation for integrating local LLM/VLM capabilities into the Reachy Mini conversation app. The modular approach allows for flexible deployment scenarios while maintaining compatibility with the existing architecture.
