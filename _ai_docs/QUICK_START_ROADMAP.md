# Quick Start: Local LLM Integration Roadmap

**Goal:** Replace OpenAI realtime API with fully local LLM stack (LMStudio + Whisper + Piper)

---

## 🎯 Executive Summary

### Current Architecture
- **LLM:** OpenAI Realtime API (cloud, real-time audio streaming)
- **Vision:** SmolVLM2 (already local!)
- **Cost:** ~$0.06/minute (audio) + $0.005/image

### Target Architecture
- **LLM:** LMStudio (local, sequential processing)
- **STT:** Faster-Whisper (local)
- **TTS:** Piper (local)
- **Vision:** SmolVLM2 (keep existing)
- **Cost:** $0 (after hardware investment)

### Trade-offs
- ✅ Privacy: All data local
- ✅ Cost: No API fees
- ✅ Offline: No internet needed
- ❌ Latency: 1-3s vs 0.3-0.8s (OpenAI)
- ❌ Complexity: 4 models vs 1 API

---

## 📋 Phase-by-Phase Implementation

### Phase 0: Environment Setup (Day 1)
**Goal:** Install all dependencies and test models independently

```bash
# 1. Install Python dependencies
uv sync --extra local_vision  # You already have this
pip install faster-whisper piper-tts

# 2. Install LMStudio
# Download from: https://lmstudio.ai/
# Launch and download: Hermes-2-Pro-Llama-3-8B-Q4_K_M

# 3. Test LMStudio API
curl http://localhost:1234/v1/models

# 4. Download Whisper model
python -c "from faster_whisper import WhisperModel; WhisperModel('base.en')"

# 5. Download Piper voice
mkdir -p voices && cd voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

**Deliverable:** All models downloaded and tested independently

---

### Phase 1: Component Development (Week 1)
**Goal:** Build modular components for VAD, STT, LLM, TTS

#### 1.1 Create Directory Structure
```bash
mkdir -p src/reachy_mini_conversation_app/{vad,stt,llm,tts,handlers}
touch src/reachy_mini_conversation_app/vad/__init__.py
touch src/reachy_mini_conversation_app/stt/__init__.py
touch src/reachy_mini_conversation_app/llm/__init__.py
touch src/reachy_mini_conversation_app/tts/__init__.py
touch src/reachy_mini_conversation_app/handlers/__init__.py
```

#### 1.2 Implement Components (in order)
1. **VAD (1-2 hours)**
   - File: `src/reachy_mini_conversation_app/vad/silero_vad.py`
   - Test: Detect speech in audio chunks
   - See: `_ai_docs/lmstudio_integration_guide.md` Section 3.1

2. **STT (2-3 hours)**
   - File: `src/reachy_mini_conversation_app/stt/local_whisper.py`
   - Test: Transcribe 3-second audio clip
   - See: `_ai_docs/lmstudio_integration_guide.md` Section 3.2

3. **LLM Client (2-3 hours)**
   - File: `src/reachy_mini_conversation_app/llm/lmstudio_client.py`
   - Test: Chat completion with function calling
   - See: `_ai_docs/lmstudio_integration_guide.md` Section 3.3

4. **TTS (2-3 hours)**
   - File: `src/reachy_mini_conversation_app/tts/piper_tts.py`
   - Test: Synthesize "Hello" to WAV
   - See: `_ai_docs/lmstudio_integration_guide.md` Section 3.4

**Deliverable:** 4 standalone, tested components

---

### Phase 2: Handler Integration (Week 2)
**Goal:** Build LocalLLMRealtimeHandler that orchestrates all components

#### 2.1 Handler Skeleton
- File: `src/reachy_mini_conversation_app/handlers/local_llm_handler.py`
- Implement: `AsyncStreamHandler` interface
- See: `_ai_docs/lmstudio_integration_guide.md` Section 4

#### 2.2 Audio Pipeline
```python
# Implement receive() method
def receive(frame):
    1. Resample audio (16kHz → 24kHz)
    2. Run VAD
    3. Buffer speech segments
    4. On speech_end → trigger _process_speech()
```

#### 2.3 Processing Pipeline
```python
# Implement _process_speech() method
async def _process_speech():
    1. Transcribe buffered audio (STT)
    2. Send to LLM
    3. Handle function calls (tools)
    4. Generate response text
    5. Synthesize speech (TTS)
    6. Queue audio for emit()
```

#### 2.4 Output Pipeline
```python
# Implement emit() method
def emit():
    1. Return queued audio chunks
    2. Return UI updates (transcripts)
    3. Handle interruptions
```

**Deliverable:** Working LocalLLMRealtimeHandler (basic functionality)

---

### Phase 3: Configuration & Integration (Week 3)
**Goal:** Integrate handler into main app with config switching

#### 3.1 Update Configuration
```python
# src/reachy_mini_conversation_app/config.py

class Config:
    # Add new config vars
    LLM_BACKEND = os.getenv("LLM_BACKEND", "openai")
    LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
    PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "voices/en_US-lessac-medium.onnx")
```

#### 3.2 Update .env
```bash
# Add to .env.example and .env
LLM_BACKEND=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
WHISPER_MODEL=base.en
WHISPER_DEVICE=cuda
PIPER_MODEL_PATH=voices/en_US-lessac-medium.onnx
```

#### 3.3 Update Main Entry Point
```python
# src/reachy_mini_conversation_app/main.py

def create_handler(deps):
    if config.LLM_BACKEND == "lmstudio":
        from .handlers.local_llm_handler import LocalLLMRealtimeHandler
        return LocalLLMRealtimeHandler(deps)
    else:
        from .openai_realtime import OpenaiRealtimeHandler
        return OpenaiRealtimeHandler(deps)

# In main():
handler = create_handler(deps)  # Instead of OpenaiRealtimeHandler(deps)
```

**Deliverable:** Switchable backend via LLM_BACKEND env var

---

### Phase 4: Tool Integration (Week 4)
**Goal:** Ensure all robot tools work with local LLM

#### 4.1 Test Tool Calling
```python
# Test each tool with local LLM:
- move_head
- camera (with local SmolVLM2)
- head_tracking
- dance
- play_emotion
- do_nothing
```

#### 4.2 Handle Tool Response Format
```python
# Ensure LMStudio tool calls match OpenAI format:
{
    "tool_calls": [
        {
            "id": "call_123",
            "name": "move_head",
            "arguments": {"direction": "left"}
        }
    ]
}
```

**Deliverable:** All tools working with local LLM

---

### Phase 5: Testing & Optimization (Week 5)
**Goal:** End-to-end testing and latency optimization

#### 5.1 Functional Tests
```bash
# Test scenarios:
1. Basic conversation (no tools)
2. Move head (tool calling)
3. Camera + vision (local VLM)
4. Dance sequence
5. Interruption handling
6. Error recovery
```

#### 5.2 Performance Optimization
```
Target latency: <2 seconds (vs 1.5-5.3s current)

Optimizations:
1. Use faster Whisper model (tiny.en)
2. Use Q4 quantized LLM
3. Implement sentence-level TTS streaming
4. Parallel tool execution where possible
```

#### 5.3 Memory Optimization
```
Monitor GPU VRAM usage:
- Whisper: ~1-2GB
- LLM: ~4-8GB (depends on model)
- SmolVLM2: ~4-6GB
Total: ~10-16GB VRAM

If OOM: Use CPU offloading or smaller models
```

**Deliverable:** Production-ready local LLM integration

---

### Phase 6: Documentation (Week 6)
**Goal:** Complete user-facing documentation

#### 6.1 User Guide
- Installation steps
- Configuration options
- Model selection guide
- Troubleshooting

#### 6.2 Developer Guide
- Architecture overview
- Adding new components
- Testing procedures
- Performance tuning

**Deliverable:** Comprehensive documentation

---

## 🔧 Development Workflow

### Daily Workflow
```bash
# 1. Start LMStudio server
# Open LMStudio → Load model → Start server

# 2. Update code
git checkout -b feature/local-llm-integration

# 3. Test component
pytest tests/test_local_whisper.py

# 4. Run app
LLM_BACKEND=lmstudio reachy-mini-conversation-app --gradio --debug

# 5. Monitor logs
# Look for: "✅ Local LLM handler ready!"

# 6. Test conversation
# Speak to robot, verify response
```

### Testing Checklist
- [ ] Component unit tests pass
- [ ] Integration test passes
- [ ] No memory leaks
- [ ] Latency < 2 seconds
- [ ] Tool calls work
- [ ] Interruption handling works
- [ ] Error recovery works

---

## 📊 Success Metrics

### Functional Requirements
- ✅ Conversation works end-to-end
- ✅ All tools functional
- ✅ Vision integration works
- ✅ Interruption handling
- ✅ Error recovery

### Performance Requirements
- **Latency:** <2s (speech → response start)
- **Accuracy:** >85% transcription accuracy
- **Stability:** >2 hours continuous operation
- **Memory:** <16GB VRAM or graceful CPU fallback

---

## 🚨 Risk Mitigation

### High-Risk Areas
1. **Latency:** Sequential processing slower than real-time API
   - Mitigation: Optimize each component, consider streaming

2. **Function Calling:** Not all local LLMs support it well
   - Mitigation: Use Hermes-2-Pro (proven function calling)

3. **GPU Memory:** Running all models simultaneously
   - Mitigation: CPU offloading, model swapping

4. **Audio Quality:** TTS may sound robotic
   - Mitigation: Test multiple TTS engines (Piper, Coqui, StyleTTS2)

---

## 🎓 Learning Resources

### Key Documents
1. **Architecture Analysis:** `_ai_docs/architecture_analysis.md`
   - Current system deep dive
   - Integration points
   - Three implementation approaches

2. **LMStudio Integration Guide:** `_ai_docs/lmstudio_integration_guide.md`
   - Detailed component specs
   - Full code implementations
   - Configuration examples

### External Resources
- **Faster-Whisper:** https://github.com/SYSTRAN/faster-whisper
- **LMStudio:** https://lmstudio.ai/docs
- **Piper TTS:** https://github.com/rhasspy/piper
- **Silero VAD:** https://github.com/snakers4/silero-vad
- **Hermes-2-Pro:** https://huggingface.co/NousResearch/Hermes-2-Pro-Llama-3-8B

---

## 🚀 Quick Start Command Reference

```bash
# Setup
uv sync --extra local_vision
pip install faster-whisper piper-tts

# Download models (automated on first run)
python -c "from faster_whisper import WhisperModel; WhisperModel('base.en')"

# Configure
echo "LLM_BACKEND=lmstudio" >> .env

# Run with local LLM
reachy-mini-conversation-app --gradio

# Switch back to OpenAI
echo "LLM_BACKEND=openai" >> .env
```

---

## 📝 Next Immediate Actions

1. **Review Documentation**
   - Read `_ai_docs/architecture_analysis.md`
   - Read `_ai_docs/lmstudio_integration_guide.md`

2. **Environment Setup**
   - Install LMStudio
   - Download Hermes-2-Pro-Llama-3-8B model
   - Test LMStudio API

3. **Create Branch**
   ```bash
   git checkout -b feature/local-llm-integration
   ```

4. **Start Phase 1**
   - Create directory structure
   - Implement SileroVAD
   - Write unit tests

5. **Iterate**
   - Follow phase-by-phase roadmap
   - Test each component thoroughly
   - Commit frequently

---

## 🤔 Decision Points

### Before Starting
1. **Which approach?**
   - Option A: Fully local (recommended for privacy)
   - Option B: Hybrid Claude + local audio
   - Option C: Enhanced current (minimal changes)

2. **Which LLM model?**
   - Hermes-2-Pro-Llama-3-8B (recommended, best function calling)
   - Qwen2.5-7B-Instruct (alternative, good performance)
   - Mistral-7B-Instruct-v0.3 (alternative, fast)

3. **Which TTS?**
   - Piper (recommended, fast, good quality)
   - Coqui (alternative, more natural, slower)
   - StyleTTS2 (alternative, SOTA, very slow)

4. **Acceptable latency?**
   - Target: <2s (1-3s realistic)
   - OpenAI: 0.3-0.8s (for comparison)

---

**Ready to start? Begin with Phase 0 and follow the roadmap!**

Good luck! 🚀
