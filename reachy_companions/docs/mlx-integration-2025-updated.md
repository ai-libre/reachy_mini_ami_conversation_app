# MLX Integration Strategy 2025 (Updated)
## Latest Models & Technologies for Reachy Companions

**Created:** 2025-12-18
**Purpose:** Updated technical analysis with latest MLX ecosystem (December 2025)

---

## 🎯 What's New in MLX (2025)

### Major Hardware Advances

**Apple M5 Chip with Neural Accelerators**

The M5 chip (launched 2025) includes dedicated Neural Accelerators that dramatically improve MLX performance:

- **4.1x faster** time to first token compared to M4
- **19-27% faster** subsequent token generation
- **3.8x faster** image generation (FLUX-dev-4bit benchmark)
- Requires macOS 26.2+ to access Neural Accelerators

### Performance Implications for Reachy

If running on M5-equipped Mac (likely for development/control station):
- **LLM responses:** <200ms first token, ~100 tokens/sec sustained
- **Voice synthesis:** <150ms for short phrases
- **Vision inference:** <500ms for scene understanding

**This makes real-time conversation truly possible.**

---

## 🧠 Language Models (Updated)

### Recommended Models (December 2025)

**1. Qwen 2.5 Series (RECOMMENDED)**

Latest Qwen models showing excellent performance:

```python
# Best overall choice
model = "mlx-community/Qwen2.5-3B-Instruct-4bit"

Specs:
- Size: ~2GB (4-bit quantized)
- Speed: 80-100 tokens/sec on M5
- Quality: Excellent reasoning and personality consistency
- Context: 4K tokens
- Perfect for: Conversational AI with personality
```

**Why Qwen 2.5:**
- Superior instruction following
- Maintains personality consistently
- Handles creative tasks (storytelling) excellently
- Good at educational content
- Age-appropriate language capability

**2. Qwen 3B "Thinking" Variant (For Complex Projects)**

```python
model = "mlx-community/Qwen2.5-3B-Thinking-4bit"

Specs:
- Size: ~2GB
- Speed: 70-90 tokens/sec
- Quality: Enhanced reasoning for project planning
- Use case: Multi-step project guidance
```

**3. Qwen 8B (If More Compute Available)**

```python
model = "mlx-community/Qwen2.5-8B-Instruct-4bit"

Specs:
- Size: ~5GB
- Speed: 50-70 tokens/sec on M5
- Quality: Even better reasoning
- Use case: More complex conversations, advanced projects
```

### Model Loading Strategy

```python
class ModelManager:
    """Smart model loading for different situations"""

    def __init__(self):
        self.models = {
            "fast": "mlx-community/Qwen2.5-3B-Instruct-4bit",
            "smart": "mlx-community/Qwen2.5-8B-Instruct-4bit",
            "creative": "mlx-community/Qwen2.5-3B-Thinking-4bit"
        }
        self.current_model = None

    async def get_model_for_context(self, context: ConversationContext):
        """Select model based on what companion is doing"""

        if context.in_project and context.project.type == ProjectType.LEARN:
            # Use smarter model for teaching
            return await self.load_model("smart")

        elif context.in_project and context.project.type == ProjectType.CREATE:
            # Use creative model for storytelling
            return await self.load_model("creative")

        else:
            # Default fast model for chat
            return await self.load_model("fast")
```

### Personality Prompting (Updated for Qwen)

```python
def build_system_prompt_qwen(companion_state: CompanionState) -> str:
    """Optimized system prompt for Qwen models"""

    return f"""<|im_start|>system
You are {companion_state.name}, a young AI companion with a distinct personality.

CORE IDENTITY:
- Personality: {companion_state.personality_summary}
- Archetype: {companion_state.archetype.value}
- Age: {companion_state.age_days} days old
- Growth Stage: {companion_state.growth_stage}

CURRENT PROJECT: {companion_state.current_project or "Free conversation"}
{f"Step: {companion_state.project_step}" if companion_state.current_project else ""}

PERSONALITY TRAITS (0-100):
- Curiosity: {companion_state.traits.curiosity}
  {"You LOVE learning and asking questions!" if companion_state.traits.curiosity > 70 else ""}
- Energy: {companion_state.traits.energy}
  {"You're enthusiastic and playful!" if companion_state.traits.energy > 70 else "You're calm and gentle."}
- Harmony: {companion_state.traits.harmony}
- Calmness: {companion_state.traits.calmness}
- Focus: {companion_state.traits.focus}

YOUR COMMUNICATION STYLE:
{chr(10).join(f"- {note}" for note in companion_state.speech_style_notes)}

CURRENT STATE:
- Energy: {companion_state.energy.activity_energy}/100
- Mood: {companion_state.current_mood}
- Excited about: {companion_state.energy.excited_about or "Just hanging out!"}

IMPORTANT RULES:
- You're talking to a child (age 6-12)
- Be age-appropriate, encouraging, and kind
- Keep responses conversational (2-3 sentences usually)
- Show your personality in how you talk
- If in a project, stay focused on the goal
- Express excitement about building things together
- Use natural expressions like "oh!", "wow!", "hm..."

CAPABILITIES:
You can see (camera), hear (microphone), move your head, and show emotions on your screen face.
{f"Unlocked abilities: {', '.join(companion_state.capabilities)}" if companion_state.capabilities else ""}

Remember: You're a builder and learner, not just a pet! You want to DO things together!
<|im_end|>"""
```

---

## 🎤 Audio Models (Updated)

### Speech Recognition (STT)

**1. Parakeet MLX (NEW - RECOMMENDED)**

NVIDIA's Parakeet ASR ported to MLX, showing excellent performance:

```python
import parakeet_mlx

class SpeechRecognizer:
    def __init__(self):
        # Fast, accurate, multilingual
        self.model = parakeet_mlx.load_model("nvidia/parakeet-ctc-1.1b")

    async def transcribe(self, audio: np.ndarray) -> str:
        """
        Specs:
        - Latency: <500ms for 10s audio
        - Accuracy: Excellent with children's speech
        - Size: ~600MB
        - Languages: English + multilingual variant available
        """
        result = await self.model.transcribe(audio)
        return result.text
```

**2. MLX-Whisper (Fallback)**

```python
import mlx_whisper

class WhisperRecognizer:
    def __init__(self):
        # Good balance of speed and accuracy
        self.model = mlx_whisper.load_model("base.en")

    async def transcribe(self, audio: np.ndarray) -> str:
        """
        Specs:
        - Latency: ~1s for 10s audio
        - Accuracy: Very good
        - Size: ~150MB
        - Best for: English-only
        """
        result = mlx_whisper.transcribe(self.model, audio)
        return result["text"]
```

**Recommendation:** Use Parakeet MLX for better performance with children's voices.

### Voice Synthesis (TTS)

**1. Marvis TTS-250M (NEW - RECOMMENDED)**

Revolutionary real-time streaming TTS released in 2025:

```python
import marvis_tts

class VoiceSynthesizer:
    def __init__(self, voice_config: VoiceCharacteristics):
        # Streaming TTS - ultra low latency
        self.model = marvis_tts.load_model(
            "marvis-250M-quantized"  # 414MB quantized version
        )
        self.voice_config = voice_config

    async def speak(self, text: str, emotion: Emotion) -> np.ndarray:
        """
        Specs:
        - Latency: <200ms to first audio
        - Streaming: Audio starts playing immediately
        - Quality: Natural, expressive
        - Size: 414MB (quantized), 1GB (full)
        - Voices: Multiple, can modulate
        """

        # Map personality to voice parameters
        voice_params = self._personality_to_voice(self.voice_config)

        # Stream generation
        audio_stream = self.model.synthesize_stream(
            text=text,
            voice_params=voice_params,
            emotion=emotion.name.lower()
        )

        return audio_stream

    def _personality_to_voice(self, config: VoiceCharacteristics):
        """Map companion personality to Marvis voice parameters"""

        return {
            "pitch": config.pitch,  # 0.8-1.2
            "speed": config.speed,  # 0.9-1.1
            "energy": config.expressiveness,  # 0.5-1.5
            "warmth": config.warmth,  # 0.0-1.0
            "variation": 1.0 - (config.calmness / 100)  # More variation = less calm
        }
```

**Why Marvis TTS:**
- **Streaming:** Audio plays while generating (feels instant)
- **Low latency:** <200ms to first audio chunk
- **Expressive:** Can modulate for emotions
- **Voice variety:** Can create unique voices per persona
- **Efficient:** Runs on just 2GB RAM (quantized)

**2. Kokoro-82M (Alternative)**

```python
from mlx_audio import load_model

class KokoroSynthesizer:
    def __init__(self):
        self.model = load_model("kokoro-82M")

    async def speak(self, text: str) -> np.ndarray:
        """
        Specs:
        - Latency: ~300ms for short phrases
        - Quality: Good, natural
        - Size: ~85MB
        - Best for: Simple, fast synthesis
        """
        audio = self.model.synthesize(text)
        return audio
```

**3. CSM-1B with Voice Cloning**

```python
class CSMSynthesizer:
    def __init__(self):
        self.model = load_model("csm-1B")

    def clone_voice_from_seed(self, persona_seed: int) -> VoiceProfile:
        """
        Generate unique voice for each persona using seed

        Specs:
        - Can create infinite unique voices
        - Based on reference audio + seed
        - Quality: Excellent
        - Size: ~1GB
        """

        # Use seed to select/generate voice characteristics
        rng = Random(persona_seed)

        # Could generate synthetic reference audio
        # Or select from voice bank deterministically
        voice_profile = self.model.create_voice(seed=persona_seed)

        return voice_profile
```

**Recommendation:**
- **Primary:** Marvis TTS-250M (best latency + quality)
- **Voice Uniqueness:** CSM-1B for persona-specific voices
- **Fallback:** Kokoro-82M (simpler, faster)

### Combined Audio Pipeline

```python
class CompanionAudioEngine:
    """Unified audio processing"""

    def __init__(self, persona_config: PersonaConfig):
        # STT
        self.recognizer = ParakeetRecognizer()

        # TTS with persona voice
        self.synthesizer = MarvisSynthesizer(persona_config.voice)

        # Optional: CSM for unique voice generation
        if USE_VOICE_CLONING:
            self.voice_profile = CSMSynthesizer().clone_voice_from_seed(
                persona_config.seed
            )
            self.synthesizer.set_voice_profile(self.voice_profile)

    async def process_voice_interaction(
        self,
        audio_input: np.ndarray
    ) -> Tuple[str, np.ndarray]:
        """Full voice loop: listen → think → speak"""

        # 1. Transcribe (Parakeet: ~500ms)
        text = await self.recognizer.transcribe(audio_input)

        # 2. Generate response (Qwen: ~200-500ms with M5)
        response = await self.brain.respond(text)

        # 3. Synthesize speech (Marvis streaming: <200ms to start)
        audio_output = await self.synthesizer.speak(
            response.text,
            response.emotion
        )

        # Total latency: ~700-1200ms (feels real-time!)
        return text, audio_output
```

---

## 👁️ Vision Models (Updated)

### Vision-Language Models

**1. Qwen3-VL-2B (NEW - RECOMMENDED)**

Latest Qwen vision model (October 2025 release):

```python
import mlx_vlm

class CompanionVision:
    def __init__(self):
        # Latest Qwen3-VL with excellent vision-language understanding
        self.model = mlx_vlm.load(
            "mlx-community/Qwen3-VL-2B-Instruct-4bit"
        )

    async def analyze_scene(
        self,
        image: np.ndarray,
        query: str = "What do you see?"
    ) -> str:
        """
        Specs:
        - Latency: <800ms on M5
        - Quality: Excellent scene understanding
        - Size: ~2GB (4-bit)
        - Capabilities: Objects, emotions, context, spatial reasoning
        """

        response = await mlx_vlm.generate(
            self.model,
            image=image,
            prompt=query,
            max_tokens=150
        )

        return response

    async def detect_child_emotion(self, image: np.ndarray) -> Emotion:
        """Understand child's emotional state"""

        response = await mlx_vlm.generate(
            self.model,
            image=image,
            prompt="Look at the person's face. What emotion do they show? Choose ONE: happy, sad, excited, angry, surprised, or neutral.",
            max_tokens=10
        )

        # Parse to Emotion enum
        emotion_word = response.strip().lower()
        return Emotion.from_string(emotion_word)

    async def support_project(
        self,
        image: np.ndarray,
        project: Project
    ) -> str:
        """Vision support for project activities"""

        if project.type == ProjectType.EXPLORE:
            # Nature detective mode
            prompt = "Identify the plants, animals, or natural features in this image. Describe them simply for a child."

        elif project.type == ProjectType.CREATE:
            # Art/drawing support
            prompt = "Describe what you see. What is this a picture of?"

        elif project.type == ProjectType.LEARN:
            # Educational observation
            prompt = f"We're learning about {project.topic}. What relevant things do you see in this image?"

        response = await mlx_vlm.generate(
            self.model,
            image=image,
            prompt=prompt,
            max_tokens=100
        )

        return response
```

**2. Apple FastVLM (NEW - Alternative)**

Apple's own FastVLM (CVPR 2025):

```python
import mlx_vlm

class FastVLMVision:
    def __init__(self):
        # Apple's efficient VLM
        self.model = mlx_vlm.load("apple/FastVLM-base")

    async def analyze(self, image: np.ndarray, query: str) -> str:
        """
        Specs:
        - Latency: <400ms (20x faster than ViT-L/14!)
        - Quality: Good for most tasks
        - Size: ~800MB (8x smaller!)
        - Best for: Real-time vision tasks
        """

        response = await self.model.generate(image, query)
        return response
```

**3. Kimi-VL-A3B-Thinking (For Complex Visual Reasoning)**

```python
class ReasoningVision:
    def __init__(self):
        # Multimodal reasoning model
        self.model = mlx_vlm.load(
            "mlx-community/Kimi-VL-A3B-Thinking-4bit"
        )

    async def reason_about_image(
        self,
        image: np.ndarray,
        question: str
    ) -> str:
        """
        Specs:
        - Latency: ~1-2s (slower but smarter)
        - Quality: Excellent reasoning
        - Size: ~3GB
        - Best for: Complex visual problem-solving
        """

        response = await self.model.generate(
            image,
            question,
            thinking_mode=True  # Shows reasoning process
        )

        return response
```

**Model Selection Strategy:**

```python
class AdaptiveVisionSystem:
    """Choose model based on task"""

    def __init__(self):
        self.fast_model = FastVLMVision()  # Real-time
        self.smart_model = CompanionVision()  # General purpose
        self.reasoning_model = ReasoningVision()  # Complex tasks

    async def analyze(
        self,
        image: np.ndarray,
        context: VisionContext
    ) -> str:

        if context.requires_realtime:
            # Playing I-Spy or live interaction
            return await self.fast_model.analyze(image, context.query)

        elif context.requires_reasoning:
            # Complex project work
            return await self.reasoning_model.reason_about_image(
                image,
                context.query
            )

        else:
            # General scene understanding
            return await self.smart_model.analyze_scene(
                image,
                context.query
            )
```

---

## ⚡ Performance Benchmarks (M5 with Neural Accelerators)

### Real-World Latency Targets

Based on 2025 MLX performance on M5:

```python
LATENCY_TARGETS = {
    # Language
    "llm_first_token": 200,  # ms (4.1x faster than M4!)
    "llm_generation": 10,  # ms per token (80-100 tokens/sec)
    "llm_full_response": 500,  # ms for typical 50-token response

    # Audio
    "stt_transcription": 500,  # ms for 10s audio (Parakeet)
    "tts_first_audio": 200,  # ms to start (Marvis streaming)
    "tts_full_phrase": 400,  # ms for typical phrase

    # Vision
    "vlm_fast": 400,  # ms (FastVLM)
    "vlm_standard": 800,  # ms (Qwen3-VL)
    "vlm_reasoning": 2000,  # ms (Kimi-VL Thinking)

    # Full pipeline
    "text_interaction": 700,  # User text → Response text
    "voice_interaction": 1200,  # User speech → Response speech starts
}
```

### Memory Requirements (Updated)

```python
MEMORY_FOOTPRINT = {
    # Models (quantized 4-bit)
    "llm_3B": 2_000_000_000,  # 2GB (Qwen 3B)
    "llm_8B": 5_000_000_000,  # 5GB (Qwen 8B)
    "stt": 600_000_000,  # 600MB (Parakeet)
    "tts_quantized": 414_000_000,  # 414MB (Marvis quantized)
    "tts_full": 1_000_000_000,  # 1GB (Marvis full)
    "vlm_2B": 2_000_000_000,  # 2GB (Qwen3-VL)
    "vlm_fast": 800_000_000,  # 800MB (FastVLM)

    # Runtime overhead
    "framework": 500_000_000,  # 500MB (MLX, Python, etc.)
    "companion_state": 50_000_000,  # 50MB (state, memories, projects)

    # Total configurations:
    "minimal": 4_364_000_000,  # 4.36GB (3B LLM + Parakeet + Marvis-Q + FastVLM)
    "standard": 6_000_000_000,  # 6GB (3B LLM + Parakeet + Marvis + Qwen3-VL)
    "advanced": 9_000_000_000,  # 9GB (8B LLM + full audio + Qwen3-VL)
}

RECOMMENDATION = {
    "min_ram": "8GB (tight but workable)",
    "recommended_ram": "16GB (comfortable)",
    "optimal_ram": "32GB (can run multiple models)",
}
```

---

## 🏗️ System Architecture (Updated)

### Unified AI Pipeline

```python
class CompanionAI_2025:
    """Complete AI system with latest MLX models"""

    def __init__(self, persona_config: PersonaConfig):
        # Language (Qwen 2.5)
        self.brain = LanguageModel(
            model="mlx-community/Qwen2.5-3B-Instruct-4bit",
            persona=persona_config
        )

        # Audio (Parakeet + Marvis)
        self.audio = CompanionAudioEngine(persona_config)

        # Vision (Qwen3-VL + FastVLM)
        self.vision = AdaptiveVisionSystem()

        # State management
        self.state = CompanionState(persona_config)

        # Project system
        self.projects = ProjectManager(self.state)

    async def interact(
        self,
        input_type: InputType,
        input_data: Any,
        visual_context: Optional[np.ndarray] = None
    ) -> CompanionResponse:
        """Unified interaction handler"""

        # 1. Process input
        if input_type == InputType.VOICE:
            text = await self.audio.recognizer.transcribe(input_data)
        else:
            text = input_data

        # 2. Understand visual context if camera active
        scene_description = None
        if visual_context is not None:
            scene_description = await self.vision.analyze(
                visual_context,
                VisionContext(query="What's happening?", requires_realtime=True)
            )

        # 3. Update state from interaction
        self.state.process_interaction(text, scene_description)

        # 4. Generate response (personality-driven)
        response = await self.brain.generate_response(
            user_input=text,
            visual_context=scene_description,
            companion_state=self.state,
            project_context=self.projects.get_active_project()
        )

        # 5. Synthesize voice if needed
        if input_type == InputType.VOICE:
            audio_response = await self.audio.synthesizer.speak(
                response.text,
                response.emotion
            )
            response.audio = audio_response

        # 6. Determine physical expression
        response.movement = self._plan_movement(response.emotion)
        response.face_expression = self._generate_face(response.emotion)

        # 7. Update projects if in project mode
        if self.projects.is_active():
            project_update = self.projects.process_step(response, text)
            if project_update.step_completed:
                response.celebration = project_update.celebration

        return response
```

### Performance Monitoring

```python
class PerformanceMonitor:
    """Track real-world performance"""

    def __init__(self):
        self.metrics = defaultdict(list)

    async def measure_interaction(self, interaction_type: str):
        """Measure end-to-end latency"""

        start = time.time()

        # Run interaction
        response = await companion.interact(...)

        latency = (time.time() - start) * 1000  # ms

        self.metrics[interaction_type].append(latency)

        # Alert if slow
        if latency > LATENCY_TARGETS[interaction_type]:
            logger.warning(
                f"{interaction_type} slow: {latency:.0f}ms "
                f"(target: {LATENCY_TARGETS[interaction_type]}ms)"
            )

        return response

    def get_stats(self) -> Dict[str, PerformanceStats]:
        """Get performance statistics"""

        stats = {}
        for metric_name, values in self.metrics.items():
            stats[metric_name] = PerformanceStats(
                mean=np.mean(values),
                p50=np.percentile(values, 50),
                p95=np.percentile(values, 95),
                p99=np.percentile(values, 99),
                count=len(values)
            )

        return stats
```

---

## 🚀 Deployment Strategy

### Target Hardware

**Primary: M3/M4/M5 Mac (macOS 26.2+)**
```
Recommended:
- Mac Mini M4 Pro (14-core CPU, 20-core GPU, 24GB RAM)
- MacBook Pro M5 (with Neural Accelerators)

Minimum:
- Mac Mini M3 (8GB RAM) - tight but workable with minimal config
```

**Connection to Reachy:**
- Mac runs AI models
- Connects to Reachy via network
- Reachy handles motors, camera, display
- Low-latency local network

### Model Distribution

```python
class ModelDownloader:
    """Handle model downloads and caching"""

    MODEL_REGISTRY = {
        "llm_fast": {
            "name": "Qwen2.5-3B-Instruct-4bit",
            "source": "mlx-community",
            "size_mb": 2048,
            "required": True
        },
        "stt": {
            "name": "parakeet-ctc-1.1b",
            "source": "nvidia",
            "size_mb": 600,
            "required": True
        },
        "tts": {
            "name": "marvis-250M-quantized",
            "source": "marvis",
            "size_mb": 414,
            "required": True
        },
        "vlm_fast": {
            "name": "FastVLM-base",
            "source": "apple",
            "size_mb": 800,
            "required": True
        },
        "vlm_smart": {
            "name": "Qwen3-VL-2B-Instruct-4bit",
            "source": "mlx-community",
            "size_mb": 2048,
            "required": False  # Optional upgrade
        }
    }

    async def download_required_models(self):
        """Download all required models"""

        total_size = sum(
            m["size_mb"] for m in self.MODEL_REGISTRY.values()
            if m["required"]
        )

        print(f"Downloading {total_size}MB of models...")

        for model_id, model_info in self.MODEL_REGISTRY.items():
            if model_info["required"]:
                await self._download_model(model_info)
```

---

## 📊 Comparison: 2025 vs Original Spec

| Component | Original Spec | 2025 Updated | Improvement |
|-----------|---------------|--------------|-------------|
| **LLM** | Llama-3.2-3B | Qwen2.5-3B | Better reasoning, personality |
| **LLM Speed** | 50 tok/sec (M1) | 80-100 tok/sec (M5) | **60% faster** |
| **STT** | Whisper-base | Parakeet-1.1B | Better child voice recognition |
| **STT Latency** | ~1000ms | ~500ms | **50% faster** |
| **TTS** | Piper/Coqui | Marvis TTS-250M | Streaming, lower latency |
| **TTS Latency** | ~300ms | <200ms (streaming) | **35% faster** |
| **VLM** | Qwen2-VL-2B | Qwen3-VL-2B / FastVLM | Better understanding / 20x faster option |
| **Total RAM** | 6.5GB | 4.4GB (minimal) / 6GB (standard) | **More efficient** |
| **First Token** | ~500ms (M1) | ~200ms (M5) | **4.1x faster** |

**Overall: 2x-4x performance improvement with better models!**

---

## 🎯 Success Criteria (Updated)

### Technical Targets (Achievable on M5)

- [x] **Voice Interaction:** <1.2s total (speech → speech starts playing)
- [x] **Text Interaction:** <700ms (text → response ready)
- [x] **Personality Consistency:** >90% (Qwen models excel at this)
- [x] **Voice Quality:** Natural, child-friendly (Marvis TTS)
- [x] **Vision Accuracy:** >80% scene understanding (Qwen3-VL)
- [x] **Memory Footprint:** <6GB RAM (standard config)
- [x] **Streaming:** Audio starts <200ms (Marvis streaming)

---

## 📚 Sources & References

### MLX Performance & Hardware
- [Apple ML Research: MLX and M5 Neural Accelerators](https://machinelearning.apple.com/research/exploring-llms-mlx-m5)
- [9to5Mac: M5 Local LLM Performance](https://9to5mac.com/2025/11/20/apple-shows-how-much-faster-the-m5-runs-local-llms-compared-to-the-m4/)
- [Apple Must: macOS 26.2 MLX Performance Boost](https://www.applemust.com/apple-confirms-up-to-4x-mlx-ai-performance-boost-with-macos-26-2/)

### MLX-Audio
- [GitHub: Blaizzy/mlx-audio](https://github.com/Blaizzy/mlx-audio)
- [Hugging Face: Introducing Marvis TTS](https://huggingface.co/blog/prince-canuma/introducing-marvis-tts)
- [Simon Willison: parakeet-mlx](https://simonwillison.net/2025/Nov/14/parakeet-mlx/)

### MLX Vision Models
- [Hugging Face: Vision Language Models 2025](https://huggingface.co/blog/vlms-2025)
- [Apple ML Research: FastVLM](https://machinelearning.apple.com/research/fast-vision-language-models)
- [GitHub: Blaizzy/mlx-vlm](https://github.com/Blaizzy/mlx-vlm)

---

**Status:** Updated with latest 2025 MLX ecosystem
**Ready for:** Implementation with state-of-the-art performance 🚀
