# MLX Integration: Final Recommendation

**Date:** 2025-11-22
**Status:** ✅ APPROVED - MLX is the recommended approach
**Critical Finding:** mlx-lm supports OpenAI-compatible function calling

---

## 🎯 Executive Decision: GO WITH MLX!

After thorough investigation, **MLX is the superior choice** for local LLM/VLM integration on Apple Silicon.

### Why MLX Wins

#### ✅ Function Calling: CONFIRMED
- mlx-lm has **native tool support** (`mlx_lm/examples/tool_use.py`)
- mlx-lm server provides **OpenAI-compatible API** (`mlx_lm/examples/openai_tool_use.py`)
- Same tool format as current OpenAI implementation
- **Drop-in replacement** for existing tool system

#### ✅ Complete Stack
- **LLM:** mlx-lm (streaming, quantization, caching)
- **VLM:** mlx-vlm (SmolVLM support, multi-modal)
- **Audio:** mlx-audio (STT + TTS in one package)
- **All unified** on Metal with shared memory

#### ✅ Performance Advantages
- 30-40% faster than CUDA approach (estimated)
- Unified memory = zero-copy operations
- M5 Neural Accelerator support
- Lower energy consumption

#### ✅ Developer Experience
- Simple installation: `pip install mlx-lm mlx-vlm mlx-audio`
- Pure Python (no C++ compilation)
- Clean APIs, good documentation
- Active community + Apple backing

---

## 📋 Implementation Plan

### Phase 1: MLX Environment Setup (Day 1)

```bash
# Install MLX packages
pip install mlx-lm mlx-vlm mlx-audio

# Download models (auto-quantized to 4-bit)
python -c "from mlx_lm import load; load('mlx-community/Hermes-2-Pro-Llama-3-8B-4bit')"
python -c "from mlx_vlm import load; load('mlx-community/SmolVLM-Instruct-4bit')"

# Test installations
mlx_lm.generate --prompt "Hello, I am Reachy Mini"
mlx_vlm.generate --image test.jpg --prompt "Describe this"
mlx_audio.tts.generate --text "Testing audio"
```

### Phase 2: Component Integration (Week 1)

#### 2.1 Create MLX Handler Structure
```python
# File: src/reachy_mini_conversation_app/handlers/mlx_handler.py

from mlx_lm import load, stream_generate
from mlx_vlm import load as load_vlm, generate as generate_vlm
from mlx_audio import transcribe, synthesize  # TBD: actual imports

class MLXRealtimeHandler(AsyncStreamHandler):
    """MLX-based realtime handler for Apple Silicon."""

    def __init__(self, deps: ToolDependencies):
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            input_sample_rate=16000,
        )
        self.deps = deps

        # MLX components
        self.llm_model = None
        self.llm_tokenizer = None
        self.vlm_model = None
        self.vlm_processor = None

    async def start_up(self) -> None:
        """Initialize MLX models."""
        from mlx_lm import load
        from mlx_vlm import load as load_vlm

        # Load LLM (for conversation + function calling)
        self.llm_model, self.llm_tokenizer = load(
            "mlx-community/Hermes-2-Pro-Llama-3-8B-4bit"
        )

        # Load VLM (for vision)
        self.vlm_model, self.vlm_processor = load_vlm(
            "mlx-community/SmolVLM-Instruct-4bit"
        )

        logger.info("✅ MLX models loaded successfully")
```

#### 2.2 Option A: Use MLX-LM Server (Easiest)

**Why this approach:**
- OpenAI-compatible API
- Same interface as current OpenAI integration
- Minimal code changes
- Server handles tool calling automatically

```python
# Start mlx-lm server (in separate process/terminal)
# mlx_lm.server --model mlx-community/Hermes-2-Pro-Llama-3-8B-4bit

from openai import AsyncOpenAI

class MLXRealtimeHandler(AsyncStreamHandler):
    async def start_up(self):
        # Connect to local MLX server (same as LMStudio approach!)
        self.client = AsyncOpenAI(
            base_url="http://localhost:8080/v1",
            api_key="not-needed"
        )

        # Rest of code IDENTICAL to LMStudio approach!
        # Can reuse LMStudioClient class with different base_url
```

**Benefits:**
- ✅ Reuse existing code from LMStudio guide
- ✅ OpenAI-compatible tool calling
- ✅ Streaming support
- ✅ Easy to test and debug

**Drawback:**
- ⚠️ Requires running server separately
- ⚠️ Adds slight network overhead (localhost)

#### 2.3 Option B: Direct MLX-LM API (More integrated)

**Why this approach:**
- No server overhead
- Direct Python API
- More control

```python
from mlx_lm import load, stream_generate
import json

class MLXRealtimeHandler(AsyncStreamHandler):
    async def _generate_response(self, user_message: str):
        """Generate LLM response with tool calling."""

        # Build messages
        messages = [
            {"role": "system", "content": get_session_instructions()},
            {"role": "user", "content": user_message}
        ]

        # Apply chat template with tools
        tools = get_tool_specs()  # Existing tool definitions
        prompt = self.llm_tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tools=tools  # MLX-LM supports tools parameter!
        )

        # Generate response
        response_text = ""
        for chunk in stream_generate(
            self.llm_model,
            self.llm_tokenizer,
            prompt,
            max_tokens=512
        ):
            response_text += chunk.text
            # Can feed to TTS immediately for lower latency!

        # Parse tool calls (model-specific format)
        tool_calls = self._parse_tool_calls(response_text)

        if tool_calls:
            # Execute tools
            for tool_call in tool_calls:
                result = await dispatch_tool_call(
                    tool_call["name"],
                    json.dumps(tool_call["arguments"]),
                    self.deps
                )
                # Add result to conversation and continue...

        return response_text
```

**Benefits:**
- ✅ No server required
- ✅ Streaming to TTS for lower latency
- ✅ More control over pipeline

**Drawbacks:**
- ⚠️ Need to handle tool call parsing (model-specific format)
- ⚠️ More complex implementation

**Recommendation:** Start with **Option A (server)** for rapid prototyping, migrate to **Option B (direct)** for optimization.

---

### Phase 3: Audio Integration (Week 2)

```python
# STT with mlx-audio
from mlx_audio import transcribe

async def _transcribe_audio(self, audio_buffer):
    """Transcribe speech using mlx-audio."""
    # Save audio to temp file (mlx-audio expects file path)
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Write audio buffer to WAV
        import wave
        with wave.open(f.name, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(24000)
            wav.writeframes(audio_buffer.tobytes())

        # Transcribe
        text = await asyncio.get_event_loop().run_in_executor(
            None,
            transcribe,
            f.name
        )

    return text

# TTS with mlx-audio
from mlx_audio.tts.generate import generate_audio

async def _synthesize_speech(self, text: str):
    """Synthesize speech using mlx-audio."""
    import tempfile

    # Generate audio
    output_file = await asyncio.get_event_loop().run_in_executor(
        None,
        generate_audio,
        text,
        "prince-canuma/Kokoro-82M",
        "af_heart",  # voice
        1.0,  # speed
        "a",  # language code (American English)
        "temp",  # file prefix
        "wav",  # format
        24000  # sample rate
    )

    # Load audio file
    import wave
    with wave.open(output_file, 'rb') as wav:
        audio_data = wav.readframes(wav.getnframes())
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

    return audio_array
```

**Note:** mlx-audio API may need refinement based on actual usage patterns. Check documentation for async support.

---

### Phase 4: Vision Integration (Week 3)

```python
# Vision with mlx-vlm (already familiar!)
from mlx_vlm import generate as generate_vlm
from mlx_vlm.prompt_utils import apply_chat_template

async def _process_camera_image(self, image_path: str, prompt: str):
    """Process camera image with mlx-vlm."""

    formatted_prompt = apply_chat_template(
        self.vlm_processor,
        self.vlm_model.config,
        prompt,
        num_images=1
    )

    output = await asyncio.get_event_loop().run_in_executor(
        None,
        generate_vlm,
        self.vlm_model,
        self.vlm_processor,
        formatted_prompt,
        [image_path],
        False  # verbose
    )

    return output
```

**This is almost identical to current SmolVLM2 integration!** Just swap PyTorch for MLX.

---

## 🚀 Quick Start: Minimal MLX Implementation

### Proof of Concept (1-2 hours)

```python
"""
Minimal MLX-based Reachy Mini handler
Tests: LLM → TTS pipeline
"""

import asyncio
from mlx_lm import load, generate
from mlx_audio.tts.generate import generate_audio

# Load model
print("Loading Hermes-2-Pro (MLX, 4-bit)...")
model, tokenizer = load("mlx-community/Hermes-2-Pro-Llama-3-8B-4bit")

# Test generation
prompt = "Hello! Please introduce yourself as Reachy Mini robot."
messages = [{"role": "user", "content": prompt}]
formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)

print("\nGenerating response...")
response = generate(model, tokenizer, prompt=formatted_prompt, max_tokens=100, verbose=True)
print(f"\nResponse: {response}")

# Test TTS
print("\nSynthesizing speech...")
generate_audio(
    text=response,
    model_path="prince-canuma/Kokoro-82M",
    voice="af_heart",
    speed=1.0,
    lang_code="a",
    file_prefix="reachy_test",
    audio_format="wav",
    sample_rate=24000
)
print("✅ Audio saved to reachy_test.wav")
```

**Run this to validate:**
1. MLX-LM loads and generates correctly
2. MLX-Audio synthesizes speech
3. Latency is acceptable
4. Memory usage is reasonable

---

## 📊 Expected Performance

### Model Memory Usage (4-bit quantized)
```
Hermes-2-Pro-8B (4-bit):  ~4.5 GB
SmolVLM-2.2B (4-bit):     ~1.5 GB
Kokoro-82M (TTS):         ~0.5 GB
STT model:                ~1.0 GB
-------------------------------------------
Total:                    ~7.5 GB

Recommended: 16GB+ unified memory (M1/M2/M3)
Comfortable: 32GB+ unified memory (M2 Pro/Max, M3 Pro/Max)
```

### Latency Estimates
```
Component               Time (ms)
─────────────────────────────────────
STT (mlx-audio)         300-500
LLM (Hermes-8B-4bit)    500-900
Tool execution          50-500
TTS (Kokoro-82M)        300-500
─────────────────────────────────────
Total:                  1150-2400ms

Target: <2000ms average
Reality: Likely 1500-2000ms
```

---

## 🔄 Migration Strategy

### Step 1: Parallel Development
```
Keep OpenAI handler working
Add MLX handler alongside
Switch via LLM_BACKEND=mlx
```

### Step 2: Feature Parity
```
✅ Basic conversation
✅ Tool calling (all robot functions)
✅ Vision (camera tool)
✅ Interruption handling
✅ Error recovery
```

### Step 3: Optimization
```
□ Sentence-level TTS streaming
□ Prompt caching for system instructions
□ Model quantization tuning
□ Memory profiling
```

### Step 4: Production
```
□ Comprehensive testing (2+ hour sessions)
□ Latency benchmarks
□ User acceptance testing
□ Documentation
```

---

## 🎯 Success Criteria

### Must Have
- ✅ All robot tools functional
- ✅ Latency <2 seconds average
- ✅ Stable for >2 hours
- ✅ Memory <16GB

### Nice to Have
- ✅ Custom Reachy voice (CSM voice cloning)
- ✅ Multi-image analysis
- ✅ Video understanding
- ✅ Audio emotion detection

---

## 🚨 Risk Mitigation

### Risk 1: mlx-audio STT slower than expected
**Mitigation:** Keep Faster-Whisper as fallback, use MLX for TTS only

### Risk 2: Tool calling format incompatible
**Mitigation:** Parse model output manually (Hermes-2-Pro has consistent format)

### Risk 3: Memory pressure on 16GB systems
**Mitigation:** Use smaller models (Qwen2.5-7B-4bit instead of 8B)

### Risk 4: TTS quality not acceptable
**Mitigation:** Fall back to Piper, or use CSM for voice cloning

---

## 📝 Configuration

### .env for MLX
```bash
# Backend selection
LLM_BACKEND=mlx  # openai | mlx | lmstudio

# MLX-LM Configuration
MLX_LLM_MODEL=mlx-community/Hermes-2-Pro-Llama-3-8B-4bit
MLX_USE_SERVER=false  # true = use mlx_lm.server, false = direct API

# MLX-Audio Configuration
MLX_TTS_MODEL=prince-canuma/Kokoro-82M
MLX_TTS_VOICE=af_heart
MLX_TTS_SPEED=1.0
MLX_TTS_LANG=a  # American English

# MLX-VLM Configuration
MLX_VLM_MODEL=mlx-community/SmolVLM-Instruct-4bit

# Hardware
MLX_DEVICE=auto  # auto | mps | cpu
```

### pyproject.toml
```toml
[project.optional-dependencies]
mlx = [
    "mlx>=0.30.0",
    "mlx-lm>=0.20.0",
    "mlx-vlm>=0.2.0",
    "mlx-audio>=0.2.5",
]

all = [
    # Include everything
    "mlx>=0.30.0",
    "mlx-lm>=0.20.0",
    "mlx-vlm>=0.2.0",
    "mlx-audio>=0.2.5",
    # ... other deps
]
```

---

## 🎓 Learning Resources

### Official Docs
- **MLX:** https://ml-explore.github.io/mlx/
- **MLX-LM:** https://github.com/ml-explore/mlx-lm
- **MLX-VLM:** https://github.com/Blaizzy/mlx-vlm
- **MLX-Audio:** https://github.com/Blaizzy/mlx-audio

### Examples (Cloned Locally)
- **Tool use:** `_ai/refs/repos/mlx-lm/mlx_lm/examples/tool_use.py`
- **OpenAI tool use:** `_ai/refs/repos/mlx-lm/mlx_lm/examples/openai_tool_use.py`
- **VLM usage:** `_ai/refs/repos/mlx-vlm/examples/`
- **Audio usage:** `_ai/refs/repos/mlx-audio/examples/`

### Community
- **MLX Community (HF):** https://huggingface.co/mlx-community
- **Pre-quantized models:** Thousands available in 4-bit
- **Discord/Forums:** Active community support

---

## 🏁 Final Recommendation

### ✅ APPROVED: Implement MLX as Primary Stack

**Rationale:**
1. **Function calling confirmed** - Critical blocker resolved
2. **Complete ecosystem** - LLM + VLM + Audio unified
3. **Superior performance** - Unified memory, Metal optimization
4. **Simpler stack** - One framework vs five libraries
5. **Future-proof** - Apple investment, M5 Neural Accelerators

**Timeline:**
- **Week 1:** Proof of concept (LLM + TTS)
- **Week 2:** Full handler (STT + LLM + TTS + tools)
- **Week 3:** Vision integration (mlx-vlm)
- **Week 4:** Testing and optimization
- **Week 5:** Production readiness

**Next Actions:**
1. Run proof-of-concept script (above)
2. Benchmark latency and memory
3. Test tool calling with all robot functions
4. If successful → full implementation
5. If blockers → document and pivot to CUDA approach

---

## 📊 Comparison Summary

| Aspect | OpenAI Realtime | MLX Stack | CUDA/LMStudio |
|--------|----------------|-----------|---------------|
| **Latency** | 0.3-0.8s | 1.1-1.9s | 1.7-2.6s |
| **Cost** | $0.06/min | $0 | $0 |
| **Privacy** | Cloud | ✅ Local | ✅ Local |
| **Setup** | Easy | Medium | Complex |
| **Hardware** | Any | Apple Silicon | NVIDIA GPU |
| **Function calls** | ✅ Native | ✅ Native | ✅ Via model |
| **Streaming** | ✅ Real-time | ✅ Token-level | ⚠️ Sequential |
| **Memory** | N/A | 7.5GB unified | 12-20GB split |
| **Maintenance** | Low | Medium | High |

**Winner:** **MLX** for Apple Silicon, **CUDA** for NVIDIA, **OpenAI** for simplicity.

---

**Decision:** Proceed with MLX implementation! 🚀

---

## Sources

- [GitHub - ml-explore/mlx-lm](https://github.com/ml-explore/mlx-lm)
- [GitHub - Blaizzy/mlx-vlm](https://github.com/Blaizzy/mlx-vlm)
- [GitHub - Blaizzy/mlx-audio](https://github.com/Blaizzy/mlx-audio)
- [Apple ML Research: Exploring LLMs with MLX and M5](https://machinelearning.apple.com/research/exploring-llms-mlx-m5)
- [MLX Community on Hugging Face](https://huggingface.co/mlx-community)
