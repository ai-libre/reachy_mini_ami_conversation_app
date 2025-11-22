# AI Documentation for Reachy Mini Conversation App

**Purpose:** Technical documentation for integrating local LLM/VLM capabilities into the Reachy Mini conversation app.

**Methodology:** Following Jose Valim's "Ultrathink" approach - Propose → Reflect → Iterate

---

## 📚 Document Index

### 1. [Architecture Analysis](architecture_analysis.md)
**Comprehensive deep dive into the current system and integration planning**

**Contents:**
- Current architecture breakdown (LLM, Vision, Tools, Audio, Movement)
- Integration points for local LLM
- Three implementation approaches (Fully Local, Hybrid, Enhanced Current)
- Phased implementation roadmap
- Technical specifications
- Hardware requirements
- Code structure proposal

**When to read:** Start here to understand the entire system architecture.

**Key Takeaways:**
- Current system uses OpenAI Realtime API (WebSocket, real-time audio)
- Vision already has local option (SmolVLM2)
- Modular architecture supports multiple backends
- Trade-off: Privacy/Cost vs Latency

---

### 2. [LMStudio Integration Guide](lmstudio_integration_guide.md)
**Detailed implementation guide for local LLM using LMStudio**

**Contents:**
- Why LMStudio?
- Component architecture (VAD, STT, LLM, TTS)
- Full code implementations for each component:
  - SileroVAD (speech detection)
  - FasterWhisperSTT (speech-to-text)
  - LMStudioClient (LLM inference)
  - PiperTTS (text-to-speech)
- Complete LocalLLMRealtimeHandler implementation
- Configuration guide
- Setup instructions
- Testing procedures
- Performance tuning
- Troubleshooting

**When to read:** When ready to implement the local LLM integration.

**Key Takeaways:**
- 4 components needed: VAD → STT → LLM → TTS
- LMStudio provides OpenAI-compatible API
- Recommended models: Hermes-2-Pro, Faster-Whisper base.en, Piper lessac-medium
- Expected latency: 1-3 seconds (vs 0.3-0.8s OpenAI)

---

### 3. [Quick Start Roadmap](QUICK_START_ROADMAP.md)
**Phase-by-phase implementation plan with concrete actions**

**Contents:**
- Executive summary (Current vs Target)
- 6-phase implementation plan:
  - Phase 0: Environment Setup (Day 1)
  - Phase 1: Component Development (Week 1)
  - Phase 2: Handler Integration (Week 2)
  - Phase 3: Configuration & Integration (Week 3)
  - Phase 4: Tool Integration (Week 4)
  - Phase 5: Testing & Optimization (Week 5)
  - Phase 6: Documentation (Week 6)
- Daily workflow
- Success metrics
- Risk mitigation
- Quick command reference

**When to read:** When ready to start coding.

**Key Takeaways:**
- 6-week implementation timeline
- Start with environment setup and component testing
- Build modular components before full integration
- Test each phase thoroughly before moving on

---

## 🎯 Quick Navigation

### I want to...

**Understand the current architecture**
→ Read: [Architecture Analysis](architecture_analysis.md) Sections 1-2

**Understand how local LLM will work**
→ Read: [Architecture Analysis](architecture_analysis.md) Section 3
→ Read: [LMStudio Integration Guide](lmstudio_integration_guide.md) Section 2

**See code examples**
→ Read: [LMStudio Integration Guide](lmstudio_integration_guide.md) Sections 3-4

**Start implementing**
→ Read: [Quick Start Roadmap](QUICK_START_ROADMAP.md)
→ Follow: Phase-by-phase plan

**Configure the system**
→ Read: [LMStudio Integration Guide](lmstudio_integration_guide.md) Section 5-6

**Troubleshoot issues**
→ Read: [LMStudio Integration Guide](lmstudio_integration_guide.md) Section 8

**Optimize performance**
→ Read: [LMStudio Integration Guide](lmstudio_integration_guide.md) Section 9

---

## 🏗️ Architecture Overview

### Current System (OpenAI-based)
```
User → Microphone → [OpenAI Realtime API] → Speaker
                           ↓
                    [Tool Dispatch] → Robot Actions
                           ↓
                    [Camera + GPT Vision] → Visual Understanding
```

### Target System (Fully Local)
```
User → Microphone → [VAD] → [STT: Whisper] → [LLM: LMStudio]
                                                    ↓
                                            [Tool Dispatch] → Robot Actions
                                                    ↓
                                            [TTS: Piper] → Speaker
                                                    ↓
                                        [Camera + SmolVLM2] → Visual Understanding
```

### Key Differences
| Component | Current | Local | Trade-off |
|-----------|---------|-------|-----------|
| **LLM** | OpenAI Realtime | LMStudio | Latency: 0.5s → 1.5s |
| **STT** | OpenAI Whisper | Faster-Whisper | Quality: 95% → 90% |
| **TTS** | OpenAI TTS | Piper | Naturalness: 9/10 → 7/10 |
| **Vision** | GPT-4V / SmolVLM2 | SmolVLM2 | Already local ✅ |
| **Privacy** | Cloud | Local | ✅ Complete |
| **Cost** | $0.06/min | $0 | ✅ Free |
| **Latency** | 0.3-0.8s | 1-3s | ⚠️ Slower |

---

## 📦 Component Stack

### Speech Processing
- **VAD:** Silero VAD (~1MB, CPU-friendly)
- **STT:** Faster-Whisper (base.en: 74M params, 1GB RAM)
- **TTS:** Piper (lessac-medium: 22kHz, good quality)

### LLM Backend
- **Server:** LMStudio (OpenAI-compatible API)
- **Model:** Hermes-2-Pro-Llama-3-8B (Q4_K_M, 4.5GB)
- **Function Calling:** Native support

### Vision (Existing)
- **Model:** SmolVLM2-2.2B-Instruct
- **Device:** CUDA/MPS/CPU auto-detect
- **Processing:** 5-second intervals

---

## 🔧 Development Workflow

### 1. Initial Setup
```bash
# Clone and setup
cd reachy_mini_ami_conversation_app

# Install dependencies
uv sync --extra local_vision
pip install faster-whisper piper-tts

# Create development branch
git checkout -b feature/local-llm-integration
```

### 2. Environment Configuration
```bash
# Install LMStudio (GUI)
# Download from: https://lmstudio.ai/

# Download models
python -c "from faster_whisper import WhisperModel; WhisperModel('base.en')"

# Download Piper voice
mkdir -p voices && cd voices
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

### 3. Configuration
```bash
# Update .env
echo "LLM_BACKEND=lmstudio" >> .env
echo "WHISPER_MODEL=base.en" >> .env
echo "PIPER_MODEL_PATH=voices/en_US-lessac-medium.onnx" >> .env
```

### 4. Development
```bash
# Follow phases in Quick Start Roadmap
# Implement components one at a time
# Test thoroughly at each step
```

### 5. Testing
```bash
# Run tests
pytest tests/

# Run app with debug
LLM_BACKEND=lmstudio reachy-mini-conversation-app --gradio --debug
```

---

## 📊 Success Criteria

### Functional Requirements
- ✅ End-to-end conversation works
- ✅ All robot tools functional (move_head, camera, dance, etc.)
- ✅ Vision integration with local SmolVLM2
- ✅ Interruption handling
- ✅ Error recovery

### Performance Requirements
- **Latency:** <2 seconds (speech → response start)
- **Accuracy:** >85% transcription accuracy
- **Stability:** >2 hours continuous operation
- **Memory:** <16GB VRAM or graceful CPU fallback

### Quality Requirements
- **Audio Quality:** Intelligible TTS (>7/10 subjective)
- **Response Quality:** Coherent, contextual responses
- **Tool Accuracy:** Correct function calling >90%

---

## 🚨 Known Challenges

### 1. Latency
**Challenge:** Sequential processing (STT → LLM → TTS) adds latency
**Mitigation:**
- Use fastest models (tiny.en, Q4 quantization)
- Implement sentence-level streaming
- Parallel processing where possible

### 2. Function Calling
**Challenge:** Not all local LLMs support robust function calling
**Mitigation:**
- Use proven models (Hermes-2-Pro)
- Test thoroughly with all tools
- Implement fallback mechanisms

### 3. GPU Memory
**Challenge:** Running multiple models simultaneously
**Mitigation:**
- Model swapping (unload when not in use)
- CPU offloading for less critical components
- Quantization (Q4 vs Q8)

### 4. Audio Quality
**Challenge:** Local TTS may sound less natural
**Mitigation:**
- Test multiple TTS engines
- Use higher quality models if acceptable latency
- Consider voice cloning for better personalization

---

## 🎓 Learning Path

### For Beginners
1. **Day 1-2:** Read Architecture Analysis (understand the system)
2. **Day 3:** Install LMStudio and test manually
3. **Day 4-5:** Read LMStudio Integration Guide (understand components)
4. **Week 2+:** Follow Quick Start Roadmap (implement phase by phase)

### For Experienced Developers
1. **Hour 1:** Skim Architecture Analysis (focus on Section 3)
2. **Hour 2:** Review code snippets in LMStudio Integration Guide
3. **Hour 3:** Set up environment (LMStudio + models)
4. **Week 1+:** Jump into implementation (Phase 1+)

---

## 📞 Support & Resources

### Internal Resources
- **Codebase:** Current implementation examples
- **Tests:** See `tests/` directory for patterns
- **Profiles:** See `src/reachy_mini_conversation_app/profiles/` for tool examples

### External Resources
- **LMStudio:** https://lmstudio.ai/docs
- **Faster-Whisper:** https://github.com/SYSTRAN/faster-whisper
- **Piper TTS:** https://github.com/rhasspy/piper
- **Silero VAD:** https://github.com/snakers4/silero-vad
- **Hermes-2-Pro:** https://huggingface.co/NousResearch/Hermes-2-Pro-Llama-3-8B

### Community
- **Reachy Community:** https://forum.pollen-robotics.com/
- **LMStudio Discord:** https://discord.gg/lmstudio

---

## 🗺️ Roadmap Summary

```
Week 0: [Reading & Setup]
  ├── Understand architecture
  ├── Install LMStudio
  ├── Download models
  └── Test components

Week 1: [Component Development]
  ├── Implement SileroVAD
  ├── Implement FasterWhisperSTT
  ├── Implement LMStudioClient
  └── Implement PiperTTS

Week 2: [Handler Integration]
  ├── Create LocalLLMRealtimeHandler
  ├── Implement audio pipeline
  ├── Implement processing pipeline
  └── Implement output pipeline

Week 3: [Configuration & Integration]
  ├── Update config.py
  ├── Update .env
  ├── Create handler factory
  └── Test backend switching

Week 4: [Tool Integration]
  ├── Test all robot tools
  ├── Verify function calling
  └── Integrate camera + vision

Week 5: [Testing & Optimization]
  ├── End-to-end testing
  ├── Performance tuning
  ├── Memory optimization
  └── Error handling

Week 6: [Documentation & Polish]
  ├── User guide
  ├── Developer guide
  ├── Troubleshooting
  └── Release prep
```

---

## ✅ Next Steps

1. **Read the documents in order:**
   - Architecture Analysis (understand)
   - LMStudio Integration Guide (learn)
   - Quick Start Roadmap (execute)

2. **Set up your environment:**
   - Install LMStudio
   - Download models
   - Test components

3. **Start Phase 1:**
   - Create directory structure
   - Implement first component (SileroVAD)
   - Write tests

4. **Iterate and improve:**
   - Follow the roadmap
   - Test thoroughly
   - Optimize as needed

---

**Questions? Start with the [Quick Start Roadmap](QUICK_START_ROADMAP.md) for immediate next steps!**

Good luck with the implementation! 🚀
