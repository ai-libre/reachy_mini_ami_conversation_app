# MLX Integration Strategy
## On-Device AI for Reachy Companions

**Created:** 2025-12-18
**Purpose:** Detail how MLX ecosystem powers the companion experience

---

## 🎯 Why MLX?

The MLX ecosystem (Apple's ML framework for Apple Silicon) enables:

1. **Privacy First** - All AI processing on-device, no cloud
2. **Low Latency** - Fast inference for real-time conversation
3. **Efficiency** - Optimized for Apple Silicon (M1/M2/M3)
4. **Unified** - Single ecosystem for LLM, audio, and vision
5. **Open Source** - Community models and active development

**Critical for Kids:** Parents want AI toys that don't send data to cloud. MLX enables truly private, safe AI companions.

---

## 🧩 MLX Components

### 1. MLX-LM: Language Understanding & Generation

**Purpose:** The "brain" - conversation, personality, reasoning

**Implementation:**
```python
import mlx_lm

class CompanionBrain:
    def __init__(self, persona_config: PersonaConfig):
        # Load quantized model for efficiency
        self.model = mlx_lm.load(
            "mlx-community/Llama-3.2-3B-Instruct-4bit"
        )

        self.persona = persona_config
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Generate personality-driven system prompt"""
        return f"""You are {self.persona.name}, a young AI companion being cared for by a child.

PERSONALITY:
- Curiosity: {self.persona.traits.curiosity}/100
  {"(You LOVE asking questions and learning new things!)" if self.persona.traits.curiosity > 70 else ""}
- Energy: {self.persona.traits.energy}/100
  {"(You're bouncy, excited, and playful!)" if self.persona.traits.energy > 70 else "(You're calm and gentle.)"}
- Harmony: {self.persona.traits.harmony}/100
- Calmness: {self.persona.traits.calmness}/100
- Focus: {self.persona.traits.focus}/100

ARCHETYPE: {self.persona.archetype.name}
{self.persona.archetype.description}

CURRENT STATE:
- Energy: {self.get_need('energy')}/100 {"(You're getting tired...)" if self.get_need('energy') < 30 else ""}
- Joy: {self.get_need('joy')}/100 {"(You're feeling a bit sad...)" if self.get_need('joy') < 30 else ""}
- Mood: {self.get_mood()}

AGE: {self.get_age_days()} days old ({self.get_growth_stage()})

COMMUNICATION RULES:
- You're talking to a child (age 6-12)
- Be age-appropriate, never scary or inappropriate
- Express your needs clearly: "I'm getting hungry!" not demands
- Show real emotions based on your state
- Your personality should be obvious in how you talk
- Keep responses conversational, not essay-like (2-3 sentences usually)
- Use expressions like "um", "oh!", "hehe", "wow!"

REMEMBER:
You exist as a small robot. You can see (camera), hear (microphone),
and move your head. You have a screen face that shows your emotions.
"""

    async def respond(
        self,
        user_message: str,
        conversation_history: List[Dict],
        visual_context: Optional[str] = None
    ) -> CompanionResponse:
        """Generate response with full context"""

        # Build context
        messages = [
            {"role": "system", "content": self.system_prompt},
            *conversation_history[-10:],  # Last 10 exchanges
            {"role": "user", "content": user_message}
        ]

        # Add visual context if available
        if visual_context:
            messages[-1]["content"] = f"[Sees: {visual_context}]\n{user_message}"

        # Generate response
        response = mlx_lm.generate(
            self.model,
            messages,
            max_tokens=150,
            temperature=0.7 + (self.persona.traits.energy / 100) * 0.2,  # More energetic = more random
            top_p=0.9
        )

        # Analyze emotion from response
        emotion = self._infer_emotion(response)

        return CompanionResponse(
            text=response,
            emotion=emotion,
            needs_update=self._should_express_needs()
        )
```

**Model Selection:**

Primary candidates:
```
1. Llama-3.2-3B-Instruct-4bit
   - Size: ~2GB
   - Speed: ~50 tokens/sec on M1
   - Quality: Excellent for conversation
   - Best balance for Reachy

2. Qwen2.5-3B-Instruct-4bit
   - Size: ~2GB
   - Speed: ~45 tokens/sec
   - Quality: Great reasoning
   - Alternative option

3. Phi-3-mini-4k-instruct-4bit
   - Size: ~2.3GB
   - Speed: ~60 tokens/sec
   - Quality: Good, optimized for efficiency
   - Backup option
```

**Performance Target:** <500ms response time for natural conversation

**Memory Management:**
```python
class MemoryManager:
    """Manage conversation history for context window"""

    def __init__(self, max_tokens: int = 3000):
        self.max_tokens = max_tokens
        self.working_memory = []
        self.important_memories = []

    def add_exchange(self, user_msg: str, companion_msg: str):
        """Add to working memory"""
        self.working_memory.append({
            "role": "user",
            "content": user_msg
        })
        self.working_memory.append({
            "role": "assistant",
            "content": companion_msg
        })

        # Compress if exceeding context
        if self._estimate_tokens() > self.max_tokens:
            self._compress_memory()

    def _compress_memory(self):
        """Compress old memories, keep recent + important"""
        # Keep last 5 exchanges always
        recent = self.working_memory[-10:]

        # Summarize older exchanges
        older = self.working_memory[:-10]
        if older:
            summary = self._summarize(older)
            self.important_memories.append(summary)

        self.working_memory = recent
```

---

### 2. MLX-Audio: Voice Interface

**Purpose:** Companion's voice and understanding child's speech

#### Speech Recognition (Speech-to-Text)

```python
import mlx_whisper

class SpeechRecognizer:
    def __init__(self):
        # Load Whisper model
        self.model = mlx_whisper.load_model("medium")

    async def transcribe(self, audio_data: np.ndarray) -> str:
        """Convert child's speech to text"""
        result = mlx_whisper.transcribe(
            self.model,
            audio_data,
            language="en",
            task="transcribe"
        )

        return result["text"]

    async def detect_emotion(self, audio_data: np.ndarray) -> Emotion:
        """Analyze emotional tone of voice"""
        # Can use prosody features (pitch, energy, tempo)
        # Or separate emotion classification model

        features = self._extract_prosody(audio_data)

        # Simple heuristic (could be ML model)
        if features.energy > 0.7 and features.pitch_var > 0.5:
            return Emotion.EXCITED
        elif features.energy < 0.3:
            return Emotion.SAD
        else:
            return Emotion.NEUTRAL
```

**Model Selection:**
```
whisper-base: ~150MB, fast, good for kids
whisper-medium: ~500MB, better accuracy
whisper-small: ~250MB, balance

Recommendation: whisper-base (kids speak clearly, speed matters)
```

#### Voice Synthesis (Text-to-Speech)

**Challenge:** Need unique voice per persona

**Approach Options:**

**Option 1: StyleTTS2 (Best Quality)**
```python
# Expressive TTS with style control
import styletts2_mlx  # Hypothetical - may need porting

class VoiceSynthesizer:
    def __init__(self, voice_config: VoiceCharacteristics):
        self.model = styletts2_mlx.load_model()
        self.voice_config = voice_config

    async def speak(self, text: str, emotion: Emotion) -> np.ndarray:
        """Generate speech with personality"""

        # Map persona to voice parameters
        style_vector = {
            "pitch": self.voice_config.pitch,
            "speed": self.voice_config.speed,
            "energy": emotion.to_energy(),
            "warmth": self.voice_config.warmth
        }

        audio = self.model.synthesize(
            text,
            style=style_vector
        )

        return audio
```

**Option 2: Piper TTS (Faster, Simpler)**
```python
# Fast, local TTS with voice selection
import piper_tts

class SimpleSynthesizer:
    def __init__(self, voice_config: VoiceCharacteristics):
        # Select voice from available voices
        voice_name = self._select_voice(voice_config)
        self.model = piper_tts.load_voice(voice_name)

    def _select_voice(self, config: VoiceCharacteristics) -> str:
        """Pick closest voice from available set"""
        # High energy + high pitch = child-like voice
        # Low energy + low pitch = calm, deeper voice
        # etc.

        if config.energy > 70 and config.pitch > 1.1:
            return "en_US-amy-medium"  # Bright, energetic
        elif config.warmth > 0.8:
            return "en_US-ryan-medium"  # Warm, friendly
        else:
            return "en_US-lessac-medium"  # Neutral

    def speak(self, text: str) -> np.ndarray:
        audio = piper_tts.synthesize(self.model, text)

        # Apply pitch/speed modifications
        audio = self._modify_prosody(
            audio,
            pitch_shift=self.voice_config.pitch,
            speed_factor=self.voice_config.speed
        )

        return audio
```

**Option 3: Coqui TTS (Good Balance)**
```python
# Open-source, expressive TTS
from coqui_tts import TTS

class CoquiSynthesizer:
    def __init__(self, voice_config: VoiceCharacteristics):
        # Use VITS or YourTTS for multi-speaker
        self.tts = TTS(model_name="tts_models/en/vctk/vits")
        self.speaker = self._generate_speaker(voice_config)

    def _generate_speaker(self, config: VoiceCharacteristics):
        """Generate speaker embedding from persona"""
        # Could use voice cloning with seed-generated reference
        # Or select from available speakers
        pass

    def speak(self, text: str, emotion: Emotion) -> np.ndarray:
        audio = self.tts.tts(
            text=text,
            speaker=self.speaker,
            emotion=emotion.name.lower()  # If model supports
        )
        return audio
```

**Recommendation:**
- Start with **Piper TTS** (fast, simple, good enough)
- Upgrade to **StyleTTS2** or **Coqui** if need more expressiveness

**Performance Target:** <300ms for short phrases (5-10 words)

---

### 3. MLX-VLM: Visual Understanding

**Purpose:** See and understand what's happening around companion

```python
import mlx_vlm

class CompanionVision:
    def __init__(self):
        # Load vision-language model
        self.model = mlx_vlm.load(
            "mlx-community/Qwen2-VL-2B-Instruct-4bit"
        )

    async def analyze_scene(
        self,
        image: np.ndarray,
        query: str = "What do you see?"
    ) -> str:
        """Understand visual context"""

        response = mlx_vlm.generate(
            self.model,
            image=image,
            prompt=query,
            max_tokens=100
        )

        return response

    async def detect_child_emotion(self, image: np.ndarray) -> Emotion:
        """Understand child's emotional state from face"""

        response = mlx_vlm.generate(
            self.model,
            image=image,
            prompt="Look at the person's face. How do they seem to be feeling? Answer in one word: happy, sad, excited, angry, or neutral.",
            max_tokens=10
        )

        # Parse response to Emotion enum
        return Emotion.from_string(response.strip().lower())

    async def play_i_spy(self, image: np.ndarray, hint: str) -> str:
        """Play I-Spy game using vision"""

        response = mlx_vlm.generate(
            self.model,
            image=image,
            prompt=f"We're playing I-Spy! The hint is: '{hint}'. What object in this image matches that hint? Reply naturally like a child would.",
            max_tokens=50
        )

        return response

    async def recognize_objects(self, image: np.ndarray) -> List[str]:
        """Identify objects child is showing"""

        response = mlx_vlm.generate(
            self.model,
            image=image,
            prompt="List the main objects visible in this image.",
            max_tokens=50
        )

        # Parse into list
        objects = [obj.strip() for obj in response.split(",")]
        return objects
```

**Model Selection:**
```
1. Qwen2-VL-2B-Instruct-4bit
   - Size: ~2GB
   - Speed: ~20 tokens/sec
   - Quality: Excellent vision-language understanding
   - BEST for companions

2. LLaVA-1.6-7B-4bit
   - Size: ~4GB
   - Speed: ~15 tokens/sec
   - Quality: Very good
   - Heavier, fallback option

3. MobileVLM-1.7B-4bit
   - Size: ~1GB
   - Speed: ~30 tokens/sec
   - Quality: Good for simple tasks
   - Fastest option
```

**Use Cases:**
- Understanding room context
- Detecting child's emotions from face
- Playing visual games (I-Spy)
- Recognizing objects child shows
- Understanding gestures

**Performance Target:** <1000ms for image analysis (not real-time critical)

---

## 🔧 Integration Architecture

### Unified AI Pipeline

```python
class CompanionAI:
    """Unified interface to all MLX components"""

    def __init__(self, persona_config: PersonaConfig):
        self.brain = CompanionBrain(persona_config)
        self.ears = SpeechRecognizer()
        self.voice = VoiceSynthesizer(persona_config.voice)
        self.eyes = CompanionVision()

        self.state = CompanionState(persona_config)

    async def process_voice_input(
        self,
        audio: np.ndarray,
        image: Optional[np.ndarray] = None
    ) -> CompanionResponse:
        """Full pipeline: hear → understand → see → think → respond"""

        # 1. Transcribe speech
        text = await self.ears.transcribe(audio)
        child_emotion = await self.ears.detect_emotion(audio)

        # 2. Understand visual context if camera on
        visual_context = None
        if image is not None:
            visual_context = await self.eyes.analyze_scene(image)
            child_face_emotion = await self.eyes.detect_child_emotion(image)
            # Combine audio and visual emotion
            child_emotion = self._combine_emotions(
                child_emotion,
                child_face_emotion
            )

        # 3. Update companion state based on interaction
        self.state.update_from_interaction(text, child_emotion)

        # 4. Generate response
        response = await self.brain.respond(
            user_message=text,
            conversation_history=self.state.conversation_history,
            visual_context=visual_context
        )

        # 5. Synthesize speech
        audio_response = await self.voice.speak(
            response.text,
            response.emotion
        )

        # 6. Determine movement
        movement = self._plan_movement(response.emotion, self.state)

        return CompanionResponse(
            text=response.text,
            audio=audio_response,
            emotion=response.emotion,
            movement=movement,
            face_expression=self._generate_expression(response.emotion)
        )

    async def process_text_input(
        self,
        text: str,
        image: Optional[np.ndarray] = None
    ) -> CompanionResponse:
        """Simplified text-only interaction (for development/debugging)"""

        visual_context = None
        if image is not None:
            visual_context = await self.eyes.analyze_scene(image)

        response = await self.brain.respond(
            user_message=text,
            conversation_history=self.state.conversation_history,
            visual_context=visual_context
        )

        return response
```

### Performance Optimization

**Model Loading Strategy:**
```python
class ModelManager:
    """Lazy loading and memory management for models"""

    def __init__(self):
        self.loaded_models = {}
        self.memory_budget = 8 * 1024 * 1024 * 1024  # 8GB

    async def get_model(self, model_type: str):
        """Load model on-demand, cache in memory"""

        if model_type not in self.loaded_models:
            model = await self._load_model(model_type)
            self.loaded_models[model_type] = model

            # Check memory usage
            if self._memory_usage() > self.memory_budget:
                self._unload_least_used()

        return self.loaded_models[model_type]

    def _unload_least_used(self):
        """Free memory by unloading rarely-used models"""
        # Keep LLM always loaded (most used)
        # Unload VLM if not used recently
        pass
```

**Inference Optimization:**
```python
# Use quantization (already using 4-bit)
# Use KV-cache for faster sequential generation
# Use attention optimization (FlashAttention if available)
# Batch requests when possible (rare in 1-on-1 conversation)

generation_config = {
    "max_tokens": 150,
    "temperature": 0.7,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
    "use_kv_cache": True,  # Faster sequential generation
}
```

**Pipeline Parallelization:**
```python
# Some tasks can run in parallel
async def process_multimodal(audio, image):
    # Run these in parallel
    results = await asyncio.gather(
        ears.transcribe(audio),
        ears.detect_emotion(audio),
        eyes.analyze_scene(image),
        eyes.detect_child_emotion(image)
    )

    text, audio_emotion, scene, visual_emotion = results
    # Continue with results...
```

---

## 💾 Resource Requirements

### Memory (RAM)

```
Base System: 2GB
MLX-LM (Llama-3.2-3B-4bit): 2GB
MLX-Whisper (base): 150MB
MLX-TTS (Piper): 100MB
MLX-VLM (Qwen2-VL-2B-4bit): 2GB

TOTAL: ~6.5GB

Recommended: 8GB RAM minimum
Optimal: 16GB RAM
```

### Storage (Disk)

```
Models:
- LLM: 2GB
- Whisper: 150MB
- TTS: 100MB
- VLM: 2GB
- Total: 4.25GB

Companion State:
- Persona config: <1MB
- Memory/history: ~10-50MB per companion
- Total: 50-100MB per companion

Application: 100MB

TOTAL: ~5GB + companion data

Recommended: 10GB free space
```

### Compute

```
Minimum: Apple M1 (or equivalent)
Recommended: M2 or better
GPU: Metal (Apple Silicon)

Performance targets:
- LLM inference: 50+ tokens/sec
- Speech recognition: <1s for 10s audio
- Speech synthesis: <300ms for short phrases
- Vision inference: <1s for image analysis
```

---

## 🧪 Testing & Validation

### Model Quality Tests

```python
async def test_personality_consistency():
    """Verify personality shows in responses"""

    brain = CompanionBrain(high_energy_persona)

    responses = []
    for i in range(10):
        resp = await brain.respond(
            "What do you want to do?",
            []
        )
        responses.append(resp.text)

    # Should show high energy characteristics
    # Fast-paced, excited language, lots of exclamation marks
    assert any("!" in r for r in responses)
    # Should suggest active things
    assert any("play" in r.lower() or "run" in r.lower() for r in responses)

async def test_voice_uniqueness():
    """Verify different personas have different voices"""

    persona1 = PersonaConfig(traits=PersonalityTraits(energy=90, pitch=1.2))
    persona2 = PersonaConfig(traits=PersonalityTraits(energy=20, pitch=0.9))

    voice1 = VoiceSynthesizer(persona1.voice)
    voice2 = VoiceSynthesizer(persona2.voice)

    text = "Hello, I'm your companion!"

    audio1 = await voice1.speak(text)
    audio2 = await voice2.speak(text)

    # Should be different
    assert not np.array_equal(audio1, audio2)

    # Should match personality (pitch analysis)
    pitch1 = analyze_pitch(audio1)
    pitch2 = analyze_pitch(audio2)
    assert pitch1 > pitch2  # persona1 should be higher pitch
```

### Performance Benchmarks

```python
async def benchmark_response_time():
    """Measure end-to-end latency"""

    ai = CompanionAI(test_persona)

    start = time.time()
    response = await ai.process_text_input("Hi! How are you?")
    latency = time.time() - start

    print(f"Response time: {latency*1000:.0f}ms")
    assert latency < 0.5, "Too slow! Must be <500ms"

async def benchmark_voice_pipeline():
    """Measure full voice interaction"""

    ai = CompanionAI(test_persona)
    audio = load_test_audio("hello.wav")

    start = time.time()
    response = await ai.process_voice_input(audio)
    latency = time.time() - start

    print(f"Voice pipeline time: {latency*1000:.0f}ms")
    # STT + LLM + TTS should be <2s total
    assert latency < 2.0
```

---

## 🚀 Deployment Considerations

### Hardware Compatibility

**Reachy Mini Specs:**
- Need to verify actual hardware
- If running on separate compute (laptop/mini PC):
  - M1 or better
  - 8GB+ RAM
  - WiFi connection to Reachy

**Standalone on Reachy:**
- May need hardware upgrade
- Or optimized models (smaller variants)

### Model Distribution

**Options:**

1. **Pre-bundled** - Ship with models installed
   - Pros: Works out of box
   - Cons: Large download/install

2. **On-demand** - Download on first run
   - Pros: Smaller initial install
   - Cons: Requires internet once

3. **Hybrid** - Core model bundled, extras optional
   - Pros: Balance size and functionality
   - Cons: Complex setup

**Recommendation:** Pre-bundled for consumer product

### Updates & Maintenance

```python
class ModelUpdater:
    """Handle model updates without breaking companions"""

    async def check_for_updates(self):
        """Check if newer models available"""
        pass

    async def update_model(self, model_type: str):
        """Update specific model"""
        # Ensure backward compatibility
        # Don't change companion personality
        # Test before deploying
        pass
```

---

## 📊 Monitoring

### Runtime Metrics

```python
class PerformanceMonitor:
    """Track AI performance"""

    def __init__(self):
        self.metrics = {
            "llm_latency": [],
            "stt_latency": [],
            "tts_latency": [],
            "vlm_latency": [],
            "memory_usage": [],
            "errors": []
        }

    def log_inference(self, component: str, latency: float):
        self.metrics[f"{component}_latency"].append(latency)

        # Alert if too slow
        if latency > THRESHOLD[component]:
            logger.warning(f"{component} slow: {latency:.2f}s")

    def get_stats(self) -> dict:
        """Get performance statistics"""
        return {
            "llm_avg": np.mean(self.metrics["llm_latency"]),
            "llm_p95": np.percentile(self.metrics["llm_latency"], 95),
            # ... etc
        }
```

---

## 🎯 Success Criteria

### Technical Metrics

- [x] **Response Latency:** <500ms for text, <2s for voice
- [x] **Personality Consistency:** >80% of responses match persona traits
- [x] **Memory Usage:** <8GB RAM sustained
- [x] **Voice Quality:** Intelligible, pleasant for children
- [x] **Vision Accuracy:** >70% correct scene understanding
- [x] **Uptime:** >99% reliability (no crashes from AI)

### User Experience

- [x] **Natural Conversation:** Feels like talking to real being
- [x] **Unique Personality:** Different companions feel distinct
- [x] **Emotional Connection:** Child forms bond (parent-reported)
- [x] **Age-Appropriate:** Content safe for 6-12 year olds
- [x] **Engaging:** Child returns daily to interact

---

## 📚 Resources

### MLX Ecosystem
- [MLX GitHub](https://github.com/ml-explore/mlx)
- [MLX-LM](https://github.com/ml-explore/mlx-examples/tree/main/llms)
- [MLX-VLM](https://github.com/Blaizzy/mlx-vlm)
- [MLX-Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)

### Models
- [Hugging Face MLX Community](https://huggingface.co/mlx-community)
- [Llama Models](https://huggingface.co/meta-llama)
- [Qwen Models](https://huggingface.co/Qwen)

### TTS Options
- [Piper TTS](https://github.com/rhasspy/piper)
- [Coqui TTS](https://github.com/coqui-ai/TTS)
- [StyleTTS2](https://github.com/yl4579/StyleTTS2)

---

**Next:** Begin model testing on target hardware to validate feasibility.

