# Ultrathink Specification: MLX Local LLM Integration
# Complete Design Before Implementation - José Valim Approach

**Date:** 2025-11-22
**Project:** Reachy Mini Local LLM Integration
**Methodology:** Ultrathink (6 phases)
**Implementation Style:** José Valim's systematic approach

---

## 🎯 EXECUTIVE SUMMARY

### The Problem (3 sentences)
Reachy Mini currently uses OpenAI Realtime API ($0.06/min), sending all audio/video to the cloud. Users need local processing for privacy and zero cost. We must maintain <2s latency and full tool calling capability for robot control.

### The Solution (3 sentences)
Replace OpenAI with MLX Universal stack (mlx-lm + mlx-vlm + mlx-audio). Single codebase works on Apple Silicon AND NVIDIA GPUs via auto-detected backends. Achieves 1.1-1.9s latency, zero cost, complete privacy.

### The Approach (3 sentences)
Build incrementally over 4 weeks using vertical slices. Start with minimal handler (LLM only), add audio (STT/TTS), add vision, add tools. Each sprint delivers working end-to-end functionality.

---

## 📖 PART 1: UNDERSTAND (Deep Problem Analysis)

### 1.1 Problem Statement

**Current State:**
```
User speaks → [OpenAI Realtime API] → Robot responds
              ├─ Audio processed in cloud
              ├─ Vision processed in cloud
              ├─ $0.06 per minute
              └─ Latency: 0.3-0.8s (excellent)
```

**Desired State:**
```
User speaks → [Local Processing] → Robot responds
              ├─ Audio processed locally
              ├─ Vision processed locally
              ├─ $0.00 cost
              ├─ Latency: <2.0s (acceptable)
              └─ Privacy: Complete
```

**Gap:**
- Need local LLM with function calling
- Need local STT (speech-to-text)
- Need local TTS (text-to-speech)
- Need local VLM (vision-language model)
- Must integrate with existing robot control system

### 1.2 Users & Use Cases

**Primary User:** Robotics developers/researchers
- Want to experiment without API costs
- Need complete data privacy
- Require offline operation capability
- Value simplicity over bleeding-edge performance

**Use Cases:**
1. **Development:** Test robot behaviors without API charges
2. **Privacy:** Process sensitive conversations locally
3. **Offline:** Operate in environments without internet
4. **Research:** Experiment with different models easily
5. **Production:** Deploy to customers without cloud dependency

### 1.3 Constraints

**Technical:**
- Must implement `AsyncStreamHandler` interface (existing)
- Must support all robot tools (move_head, camera, dance, etc.)
- Must handle interruptions gracefully
- Must work on Apple Silicon (primary) and NVIDIA (secondary)

**Performance:**
- Latency: <2s total (vs 0.3-0.8s OpenAI)
- Memory: <16GB unified/VRAM
- Stability: >2 hours continuous operation
- Quality: Acceptable for robot interaction

**Business:**
- Timeline: 4-6 weeks for MVP
- Maintenance: Single person should be able to maintain
- Documentation: Must be well-documented for future developers

### 1.4 Assumptions to Validate

| Assumption | Validation Method | Status |
|------------|-------------------|--------|
| MLX works on Apple Silicon | Check imports | ✅ Confirmed |
| MLX has CUDA support | Check README | ✅ Confirmed |
| Function calling works | Check examples | ✅ Confirmed |
| Latency is acceptable | Prototype measurement | 🔄 To test |
| Quality is acceptable | Subjective testing | 🔄 To test |
| Memory fits in 16GB | Memory profiling | 🔄 To test |
| Tools integrate easily | Implementation | 🔄 To test |

---

## 📖 PART 2: EXPLORE (Alternative Solutions)

### 2.1 Alternative Approaches

#### Option A: Keep OpenAI Realtime (Status Quo)
**Architecture:**
```
OpenAI Realtime API (WebSocket)
├─ Real-time audio streaming
├─ Server-side VAD
├─ Function calling built-in
└─ Vision via GPT-4V
```

**Pros:**
- ✅ Already implemented and working
- ✅ Lowest latency (0.3-0.8s)
- ✅ Highest quality
- ✅ No maintenance burden
- ✅ Simple architecture

**Cons:**
- ❌ Cost: $0.06/min (~$3.60/hour)
- ❌ Cloud dependency
- ❌ Privacy concerns (data to OpenAI)
- ❌ Requires internet

**Score:** 7/10 - Great but expensive

---

#### Option B: CUDA/LMStudio Stack
**Architecture:**
```
Silero VAD → Faster-Whisper (STT) → LMStudio (LLM) → Piper (TTS)
                                          ↓
                                    SmolVLM2 (PyTorch)
```

**Pros:**
- ✅ Local processing (privacy)
- ✅ Zero cost
- ✅ Battle-tested components
- ✅ Flexible (swap components)
- ✅ Works on NVIDIA GPUs

**Cons:**
- ❌ Complex (5 separate libraries)
- ❌ NVIDIA GPU only
- ❌ Platform-specific code needed
- ❌ Higher latency (1.7-2.6s estimated)
- ❌ Maintenance burden (5 libraries)

**Score:** 6/10 - Works but complex

---

#### Option C: MLX Universal Stack (RECOMMENDED)
**Architecture:**
```
MLX-Audio (STT) → MLX-LM (LLM) → MLX-Audio (TTS)
                       ↓
                  MLX-VLM (Vision)

Auto-detects: Metal (Mac), CUDA (NVIDIA), CPU
```

**Pros:**
- ✅ Local processing (privacy)
- ✅ Zero cost
- ✅ Cross-platform (Mac + NVIDIA + CPU)
- ✅ Unified ecosystem (3 packages)
- ✅ Apple backing + active community
- ✅ Function calling confirmed
- ✅ Lower latency (1.1-1.9s estimated)
- ✅ Simpler maintenance
- ✅ Future-proof (M5 accelerators)

**Cons:**
- ⚠️ Newer stack (less battle-tested)
- ⚠️ MLX-audio STT unproven for real-time
- ⚠️ TTS quality unknown vs Piper

**Score:** 9/10 - Best fit!

---

### 2.2 Decision Matrix

| Criteria | OpenAI | CUDA | **MLX** | Weight |
|----------|--------|------|---------|--------|
| Latency | ✅✅✅ | ⚠️ | ✅✅ | 3x |
| Cost | ❌ | ✅ | ✅ | 2x |
| Privacy | ❌ | ✅ | ✅ | 3x |
| Simplicity | ✅✅✅ | ❌ | ✅✅ | 2x |
| Cross-platform | ✅ | ❌ | ✅✅ | 1x |
| Maintenance | ✅✅ | ❌ | ✅✅ | 2x |
| Future-proof | ✅ | ⚠️ | ✅✅ | 1x |
| **Total** | 27 | 15 | **33** | - |

**Winner: MLX Universal Stack** 🏆

### 2.3 Decision Rationale

**Why MLX?**

1. **Solves the core problem:** Local processing with acceptable latency
2. **Simplest solution:** 3 packages vs 5+ libraries
3. **Best long-term bet:** Apple backing, M5 support, active community
4. **Cross-platform win:** Single codebase for Mac + NVIDIA
5. **Proven capability:** Function calling examples found

**Risks & Mitigations:**

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Latency too high | Low | High | Prototype first, optimize later |
| STT quality issues | Medium | Medium | Fall back to Faster-Whisper |
| TTS quality poor | Medium | Low | Fall back to Piper |
| Integration complexity | Low | Medium | Follow examples closely |
| Memory constraints | Low | High | Use 4-bit models, test early |

---

## 📖 PART 3: PROPOSE (Detailed Design)

### 3.1 Architecture

#### System Context
```
┌────────────────────────────────────────────────────────────┐
│                    Reachy Mini System                       │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   Existing   │         │  NEW: MLX    │                │
│  │   Components │◄────────┤   Handler    │                │
│  └──────────────┘         └──────────────┘                │
│         │                         │                         │
│         ├─ MovementManager        ├─ MLX-LM (LLM)          │
│         ├─ CameraWorker           ├─ MLX-VLM (Vision)      │
│         ├─ Tool System            ├─ MLX-Audio (STT/TTS)   │
│         └─ HeadWobbler            └─ Hardware Detection    │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

#### Component Architecture
```
┌─────────────────────────────────────────────────────────────┐
│              MLXRealtimeHandler                              │
│              (AsyncStreamHandler)                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ HW Detect  │  │   State    │  │   Queues   │            │
│  │ Metal/CUDA │  │  Machine   │  │ Audio I/O  │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Audio Pipeline                       │      │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐│      │
│  │  │  VAD   │→ │  STT   │→ │  LLM   │→ │  TTS   ││      │
│  │  │ (mlx)  │  │ (mlx)  │  │ (mlx)  │  │ (mlx)  ││      │
│  │  └────────┘  └────────┘  └────────┘  └────────┘│      │
│  └──────────────────────────────────────────────────┘      │
│                                 ↓                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Tool Pipeline                        │      │
│  │  ┌────────────────┐  ┌──────────────────┐       │      │
│  │  │ Function Call  │→ │  Tool Dispatch   │       │      │
│  │  │  Parser        │  │  (existing)      │       │      │
│  │  └────────────────┘  └──────────────────┘       │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Vision Pipeline                      │      │
│  │  ┌────────────────┐  ┌──────────────────┐       │      │
│  │  │  Camera Tool   │→ │   MLX-VLM        │       │      │
│  │  │  (trigger)     │  │  (SmolVLM)       │       │      │
│  │  └────────────────┘  └──────────────────┘       │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Data Flow
```
1. RECEIVE:
   User speaks → Microphone
      ↓
   16kHz PCM audio → Resample → 24kHz PCM
      ↓
   VAD detects speech start/stop
      ↓
   Buffer accumulates speech segment
      ↓
   On speech_end → STT

2. PROCESS:
   STT (MLX-Audio) → Text transcript
      ↓
   LLM (MLX-LM) → Response + optional tool calls
      ↓
   If tool call → Dispatch → Execute → Add to context
      ↓
   LLM generates final response text

3. EMIT:
   Response text → TTS (MLX-Audio)
      ↓
   Audio chunks (24kHz PCM)
      ↓
   Queue for playback
      ↓
   Speaker output

4. VISION (on demand):
   Camera tool called
      ↓
   Capture frame → MLX-VLM (SmolVLM)
      ↓
   Visual description → Add to LLM context
```

### 3.2 Interface Definitions

#### Core Handler Interface
```python
class AsyncStreamHandler(ABC):
    """FastRTC stream handler interface (existing)."""

    @abstractmethod
    async def start_up(self) -> None:
        """Initialize handler (load models, setup state)."""

    @abstractmethod
    async def receive(self, frame: Tuple[int, NDArray[np.int16]]) -> None:
        """Receive audio from microphone."""

    @abstractmethod
    async def emit(self) -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None:
        """Emit audio to speaker or UI updates."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Cleanup resources."""
```

#### MLX Handler Interface
```python
class MLXRealtimeHandler(AsyncStreamHandler):
    """MLX-based handler for local LLM/VLM processing."""

    # Configuration
    config: MLXConfig

    # Models (loaded in start_up)
    llm_model: Any          # mlx_lm model
    llm_tokenizer: Any      # mlx_lm tokenizer
    vlm_model: Any          # mlx_vlm model
    vlm_processor: Any      # mlx_vlm processor

    # State
    state: ConversationState
    audio_buffer: deque     # Ring buffer for incoming audio
    speech_buffer: list     # Accumulated speech segment
    output_queue: asyncio.Queue  # Outgoing audio/UI updates

    # Methods
    async def _process_speech(self, audio: np.ndarray) -> None
    async def _generate_response(self, transcript: str) -> str
    async def _handle_tool_call(self, tool_call: dict) -> dict
    async def _synthesize_speech(self, text: str) -> np.ndarray
    async def _process_vision(self, image: np.ndarray) -> str
```

#### Configuration Interface
```python
@dataclass
class MLXConfig:
    """MLX handler configuration."""

    # LLM
    llm_model: str = "mlx-community/Hermes-2-Pro-Llama-3-8B-4bit"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500

    # VLM
    vlm_model: str = "mlx-community/SmolVLM-Instruct-4bit"

    # Audio
    stt_model: str = "mlx-community/whisper-large-v3"  # TBD actual mlx-audio model
    tts_model: str = "prince-canuma/Kokoro-82M"
    tts_voice: str = "af_heart"
    tts_speed: float = 1.0

    # Hardware
    device: str = "auto"  # auto | metal | cuda | cpu

    # Performance
    use_prompt_cache: bool = True
    enable_streaming: bool = True
```

### 3.3 State Machine

```
┌──────────┐
│   IDLE   │◄─────────────────────────┐
└────┬─────┘                          │
     │ speech_start                   │
     ▼                                │
┌──────────┐                          │
│LISTENING │                          │
└────┬─────┘                          │
     │ speech_end                     │
     ▼                                │
┌──────────┐                          │
│TRANSCRIBE│                          │
└────┬─────┘                          │
     │ transcript_ready               │
     ▼                                │
┌──────────┐                          │
│GENERATING│                          │
└────┬─────┘                          │
     │ response_ready                 │
     ├──────────┐                     │
     │          │ if tool_call        │
     │          ▼                     │
     │    ┌──────────┐                │
     │    │EXECUTING │                │
     │    │  TOOL    │                │
     │    └────┬─────┘                │
     │         │ tool_complete        │
     ▼         ▼                      │
┌──────────┐                          │
│SYNTHESIS │                          │
└────┬─────┘                          │
     │ audio_ready                    │
     ▼                                │
┌──────────┐                          │
│ SPEAKING │                          │
└────┬─────┘                          │
     │ playback_done                  │
     └──────────────────────────────►─┘
```

### 3.4 Implementation Phases

#### Phase 1: Foundation (Week 1)
**Goal:** Basic conversation loop working

**Tasks:**
- [ ] Create MLXRealtimeHandler skeleton
- [ ] Implement hardware detection
- [ ] Load LLM model (mlx-lm)
- [ ] Basic text generation (no audio yet)
- [ ] Test with simple prompts

**Deliverable:** Text-based conversation works

**Success Criteria:**
- Model loads in <20s
- Generates coherent responses
- Latency <2s for text generation

---

#### Phase 2: Audio Input (Week 2)
**Goal:** Speech-to-text working

**Tasks:**
- [ ] Research mlx-audio STT API
- [ ] Implement audio buffering
- [ ] Implement VAD (if available in mlx-audio)
- [ ] Integrate STT transcription
- [ ] Test with recorded speech

**Deliverable:** User can speak, robot transcribes

**Success Criteria:**
- STT accuracy >85%
- Latency <1s for transcription
- Handles various accents/speeds

---

#### Phase 3: Audio Output (Week 2 continued)
**Goal:** Text-to-speech working

**Tasks:**
- [ ] Integrate MLX-Audio TTS (Kokoro)
- [ ] Audio format conversion (to 24kHz PCM)
- [ ] Chunking for streaming playback
- [ ] Test TTS quality
- [ ] Compare with Piper baseline

**Deliverable:** Robot can speak responses

**Success Criteria:**
- TTS intelligibility >85%
- Latency <1s for synthesis
- Natural-sounding voice

---

#### Phase 4: Full Audio Loop (Week 2 end)
**Goal:** End-to-end conversation

**Tasks:**
- [ ] Connect STT → LLM → TTS
- [ ] Implement state machine
- [ ] Handle interruptions
- [ ] Test conversation flow
- [ ] Optimize latency

**Deliverable:** Full conversation works

**Success Criteria:**
- Total latency <2s
- Smooth conversation flow
- Stable for >30 minutes

---

#### Phase 5: Tool Calling (Week 3)
**Goal:** Robot functions work

**Tasks:**
- [ ] Study mlx-lm function calling format
- [ ] Implement tool call parser
- [ ] Integrate with existing tool dispatch
- [ ] Test each robot tool (move_head, dance, etc.)
- [ ] Handle tool errors gracefully

**Deliverable:** All robot tools functional

**Success Criteria:**
- All tools work correctly
- Function call accuracy >95%
- Error handling works

---

#### Phase 6: Vision (Week 3)
**Goal:** Camera integration

**Tasks:**
- [ ] Load MLX-VLM model (SmolVLM)
- [ ] Integrate with camera tool
- [ ] Test vision descriptions
- [ ] Compare with existing SmolVLM2
- [ ] Optimize memory usage

**Deliverable:** Camera tool works with local vision

**Success Criteria:**
- Vision quality comparable to current
- Latency <1s for image analysis
- Works alongside LLM (memory)

---

#### Phase 7: Optimization (Week 4)
**Goal:** Production-ready

**Tasks:**
- [ ] Latency profiling and optimization
- [ ] Memory optimization
- [ ] Error handling polish
- [ ] Logging and monitoring
- [ ] Documentation

**Deliverable:** Production-ready system

**Success Criteria:**
- Latency consistently <2s
- Stable for >2 hours
- Well-documented
- Easy to maintain

---

### 3.5 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **STT latency too high** | Medium | High | Prototype early, fall back to Faster-Whisper if needed |
| **TTS quality poor** | Medium | Medium | Compare with Piper, use CSM voice cloning |
| **Function calling format incompatible** | Low | High | Study examples first, manual parsing if needed |
| **Memory OOM on 16GB** | Low | High | Use 4-bit models, test early, consider model swapping |
| **Integration complexity** | Medium | Medium | Follow existing patterns, incremental integration |
| **MLX bugs/limitations** | Low | Medium | Test early, report to community, workarounds |

---

## 📖 PART 4: IMPLEMENTATION PLAN (Detailed)

### 4.1 Development Setup

#### Prerequisites
```bash
# Python environment
python3.10+ required
Virtual environment recommended

# Hardware
Mac: 16GB+ unified memory
Linux: 12GB+ VRAM (NVIDIA) or 16GB+ RAM (CPU)
Disk: 20GB free (for models)

# Dependencies
pip install mlx mlx-lm mlx-vlm mlx-audio
# Or: pip install -r requirements-mlx.txt
```

#### Project Structure
```
src/reachy_mini_conversation_app/
├── handlers/
│   ├── __init__.py
│   ├── mlx_handler.py              # NEW: Main handler
│   └── openai_realtime.py          # EXISTING: Keep for comparison
│
├── mlx/                             # NEW: MLX-specific modules
│   ├── __init__.py
│   ├── config.py                    # MLXConfig
│   ├── hardware.py                  # Hardware detection
│   ├── llm.py                       # LLM wrapper
│   ├── audio.py                     # STT/TTS wrappers
│   ├── vision.py                    # VLM wrapper
│   └── state.py                     # State machine
│
├── tools/                           # EXISTING: No changes needed
│   └── ...
│
└── ...
```

### 4.2 Sprint 1: Foundation (Days 1-5)

#### Day 1: Skeleton & Hardware Detection
```python
# File: src/reachy_mini_conversation_app/mlx/hardware.py

import mlx.core as mx
from enum import Enum

class MLXBackend(Enum):
    METAL = "metal"
    CUDA = "cuda"
    CPU = "cpu"

def detect_backend() -> MLXBackend:
    """Auto-detect available MLX backend."""
    if mx.metal.is_available():
        return MLXBackend.METAL
    elif mx.cuda.is_available():
        return MLXBackend.CUDA
    else:
        return MLXBackend.CPU

def get_memory_info() -> dict:
    """Get memory information for detected backend."""
    backend = detect_backend()

    if backend == MLXBackend.METAL:
        return {
            "backend": "metal",
            "active_mb": mx.metal.get_active_memory() / (1024**2),
            "peak_mb": mx.metal.get_peak_memory() / (1024**2),
        }
    elif backend == MLXBackend.CUDA:
        return {
            "backend": "cuda",
            "active_mb": mx.cuda.get_active_memory() / (1024**2),
            "peak_mb": mx.cuda.get_peak_memory() / (1024**2),
        }
    else:
        return {"backend": "cpu"}
```

**Test:**
```bash
python -c "from reachy_mini_conversation_app.mlx.hardware import detect_backend; print(detect_backend())"
```

---

#### Day 2: Configuration & LLM Wrapper
```python
# File: src/reachy_mini_conversation_app/mlx/config.py

from dataclasses import dataclass
import os

@dataclass
class MLXConfig:
    """MLX handler configuration."""

    # LLM
    llm_model: str = os.getenv(
        "MLX_LLM_MODEL",
        "mlx-community/Hermes-2-Pro-Llama-3-8B-4bit"
    )
    llm_temperature: float = float(os.getenv("MLX_LLM_TEMP", "0.7"))
    llm_max_tokens: int = int(os.getenv("MLX_LLM_MAX_TOKENS", "500"))

    # VLM
    vlm_model: str = os.getenv(
        "MLX_VLM_MODEL",
        "mlx-community/SmolVLM-Instruct-4bit"
    )

    # Audio (TBD: Finalize mlx-audio API)
    tts_model: str = os.getenv("MLX_TTS_MODEL", "prince-canuma/Kokoro-82M")
    tts_voice: str = os.getenv("MLX_TTS_VOICE", "af_heart")
    tts_speed: float = float(os.getenv("MLX_TTS_SPEED", "1.0"))

    # Performance
    use_prompt_cache: bool = os.getenv("MLX_USE_CACHE", "true").lower() == "true"
    enable_streaming: bool = os.getenv("MLX_STREAMING", "true").lower() == "true"
```

```python
# File: src/reachy_mini_conversation_app/mlx/llm.py

from mlx_lm import load, generate, stream_generate
from mlx_lm.models.cache import make_prompt_cache
import logging

logger = logging.getLogger(__name__)

class MLXLanguageModel:
    """Wrapper for MLX-LM."""

    def __init__(self, model_path: str, use_cache: bool = True):
        self.model_path = model_path
        self.use_cache = use_cache

        self.model = None
        self.tokenizer = None
        self.prompt_cache = None

    def load(self):
        """Load model and tokenizer."""
        logger.info(f"Loading LLM: {self.model_path}")

        self.model, self.tokenizer = load(self.model_path)

        if self.use_cache:
            self.prompt_cache = make_prompt_cache(self.model)

        logger.info("✅ LLM loaded successfully")

    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text (blocking)."""
        return generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            verbose=False,
            prompt_cache=self.prompt_cache
        )

    def stream_generate(self, prompt: str, max_tokens: int = 500):
        """Generate text (streaming)."""
        yield from stream_generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            verbose=False,
            prompt_cache=self.prompt_cache
        )
```

**Test:**
```python
from reachy_mini_conversation_app.mlx.llm import MLXLanguageModel

llm = MLXLanguageModel("mlx-community/Hermes-2-Pro-Llama-3-8B-4bit")
llm.load()
response = llm.generate("Hello!")
print(response)
```

---

#### Day 3-5: Basic Handler Implementation
```python
# File: src/reachy_mini_conversation_app/handlers/mlx_handler.py

import asyncio
import logging
from typing import Tuple, Optional
import numpy as np
from numpy.typing import NDArray
from fastrtc import AsyncStreamHandler, AdditionalOutputs

from reachy_mini_conversation_app.mlx.config import MLXConfig
from reachy_mini_conversation_app.mlx.hardware import detect_backend
from reachy_mini_conversation_app.mlx.llm import MLXLanguageModel
from reachy_mini_conversation_app.tools.core_tools import ToolDependencies

logger = logging.getLogger(__name__)

class MLXRealtimeHandler(AsyncStreamHandler):
    """MLX-based realtime handler for local LLM processing."""

    def __init__(self, deps: ToolDependencies, config: Optional[MLXConfig] = None):
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            input_sample_rate=16000,
        )
        self.deps = deps
        self.config = config or MLXConfig()

        # Models (loaded in start_up)
        self.llm: Optional[MLXLanguageModel] = None

        # State
        self.output_queue: asyncio.Queue = asyncio.Queue()

    def copy(self):
        """Create a copy of the handler."""
        return MLXRealtimeHandler(self.deps, self.config)

    async def start_up(self) -> None:
        """Initialize handler and load models."""
        logger.info("Initializing MLX handler...")

        # Detect hardware
        backend = detect_backend()
        logger.info(f"Detected backend: {backend.value}")

        # Load LLM
        self.llm = MLXLanguageModel(
            self.config.llm_model,
            use_cache=self.config.use_prompt_cache
        )
        await asyncio.get_event_loop().run_in_executor(None, self.llm.load)

        logger.info("✅ MLX handler ready!")

    async def receive(self, frame: Tuple[int, NDArray[np.int16]]) -> None:
        """Receive audio from microphone (placeholder for now)."""
        # TODO: Implement in Sprint 2
        pass

    async def emit(self) -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None:
        """Emit audio to speaker (placeholder for now)."""
        try:
            return await asyncio.wait_for(
                self.output_queue.get(),
                timeout=0.02
            )
        except asyncio.TimeoutError:
            return None

    async def shutdown(self) -> None:
        """Cleanup resources."""
        logger.info("Shutting down MLX handler...")

        # Clear queue
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("MLX handler shutdown complete")
```

**Sprint 1 Deliverable:** Basic handler that loads model and follows interface.

---

### 4.3 Sprint 2: Audio (Days 6-10)

*[Continue with detailed implementation for Sprints 2-4...]*

---

## 📖 PART 5: SUCCESS CRITERIA

### 5.1 Functional Requirements

| Requirement | Test Method | Success Criteria |
|-------------|-------------|------------------|
| **Basic conversation works** | Manual test | User can have 5-turn conversation |
| **All tools functional** | Automated test | 100% of tools work correctly |
| **Vision works** | Manual test | Camera tool provides useful descriptions |
| **Interruption handling** | Manual test | User can interrupt robot mid-speech |
| **Error recovery** | Fault injection | System recovers from errors gracefully |
| **Multi-turn context** | Manual test | Robot remembers previous conversation |

### 5.2 Performance Requirements

| Metric | Target | Acceptable | Test Method |
|--------|--------|------------|-------------|
| **Total latency** | <2.0s | <3.0s | Automated timing |
| **STT latency** | <0.5s | <1.0s | Component test |
| **LLM latency** | <1.0s | <1.5s | Component test |
| **TTS latency** | <0.5s | <1.0s | Component test |
| **Memory usage** | <10GB | <16GB | Profiling |
| **Stability** | >4 hours | >2 hours | Endurance test |

### 5.3 Quality Requirements

| Metric | Target | Test Method |
|--------|--------|-------------|
| **STT accuracy** | >90% | Human evaluation on test set |
| **TTS intelligibility** | >85% | Human evaluation (MOS score) |
| **LLM coherence** | Good | Subjective evaluation |
| **Function call accuracy** | >95% | Automated test suite |
| **Vision accuracy** | Comparable to current | A/B comparison |

---

## 📖 PART 6: TESTING STRATEGY

### 6.1 Unit Tests
```python
# tests/test_mlx_llm.py
def test_llm_loads():
    llm = MLXLanguageModel("mlx-community/Hermes-2-Pro-Llama-3-8B-4bit")
    llm.load()
    assert llm.model is not None

def test_llm_generates():
    llm = MLXLanguageModel("mlx-community/Hermes-2-Pro-Llama-3-8B-4bit")
    llm.load()
    response = llm.generate("Hello!")
    assert len(response) > 0

# tests/test_mlx_handler.py
async def test_handler_initializes():
    handler = MLXRealtimeHandler(mock_deps)
    await handler.start_up()
    assert handler.llm is not None
```

### 6.2 Integration Tests
```python
async def test_full_conversation_flow():
    handler = MLXRealtimeHandler(real_deps)
    await handler.start_up()

    # Simulate speech input
    audio = load_test_audio("hello.wav")
    await handler.receive((24000, audio))

    # Wait for response
    response = await handler.emit()

    assert response is not None
    # Verify audio output
```

### 6.3 Performance Tests
```python
async def test_latency():
    handler = MLXRealtimeHandler(real_deps)
    await handler.start_up()

    start = time.time()
    # ... full conversation cycle
    latency = time.time() - start

    assert latency < 2.0  # Target
```

### 6.4 Manual Test Plan
```markdown
1. Basic conversation (5 turns)
2. Test each tool individually
3. Test camera/vision
4. Test interruption
5. Test error recovery
6. Long conversation (30+ min)
7. Quality assessment (STT/TTS)
8. Comparison with OpenAI
```

---

## 📖 PART 7: MONITORING & OBSERVABILITY

### 7.1 Metrics to Track
```python
# Latency metrics
- stt_latency_ms
- llm_latency_ms
- tts_latency_ms
- total_latency_ms

# Quality metrics
- stt_confidence_score
- tool_call_success_rate
- error_rate

# Resource metrics
- memory_usage_mb
- model_load_time_s
```

### 7.2 Logging Strategy
```python
# Log levels:
# DEBUG: Detailed flow
# INFO: Major events (model loaded, speech detected)
# WARNING: Recoverable issues
# ERROR: Failures

logger.info("Speech detected, transcribing...")
logger.debug(f"Audio buffer size: {len(buffer)}")
logger.warning("STT confidence low: {confidence}")
logger.error(f"Tool call failed: {error}")
```

---

## 📖 CONCLUSION

### Summary
This specification provides a complete blueprint for implementing local LLM integration using the MLX Universal stack. Following José Valim's Ultrathink methodology, we have:

1. ✅ **Understood** the problem deeply
2. ✅ **Explored** three alternative approaches
3. ✅ **Proposed** a detailed MLX architecture
4. 🔄 **Ready to Prototype** and validate assumptions

### Next Steps
1. Review this specification
2. Run `prototype_mlx_poc.py` (validate assumptions)
3. Document learnings (REFLECT phase)
4. Begin Sprint 1 implementation (ITERATE phase)

### Philosophy
> "The best architecture is the one that's easy to change."
> - José Valim

We've designed for:
- **Simplicity** - Minimal moving parts
- **Clarity** - Obvious structure
- **Changeability** - Easy to modify
- **Measurability** - Clear success criteria

**Let's build it!** 🚀

---

**Document Version:** 1.0
**Status:** Complete - Ready for Implementation
**Next Phase:** PROTOTYPE (run POC, then REFLECT)
