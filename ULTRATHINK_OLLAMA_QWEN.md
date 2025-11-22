# Ultrathink Spec: Ollama + Qwen Vision Integration

**Date:** 2025-11-22
**Following:** José Valim Ultrathink Methodology
**Status:** Proposal - Awaiting Implementation Decision

---

## Phase 1: Understand 🔍

### Current State Analysis

**Existing Implementation (Sprint 1-2):**
```
┌─────────────────────────────────────────┐
│         Current MLX Stack               │
├─────────────────────────────────────────┤
│ LLM:    MLX-LM (Hermes-2-Pro-8B-4bit)  │
│ STT:    MLX-Audio (Whisper)            │
│ TTS:    MLX-Audio (Kokoro-82M)         │
│ Vision: [Planned] SmolVLM              │
│ Tools:  [Planned] Function calling     │
└─────────────────────────────────────────┘
```

**Strengths:**
- ✅ Unified MLX ecosystem (one framework)
- ✅ Native Apple Silicon + CUDA support
- ✅ Fast inference with unified memory
- ✅ Audio pipeline working end-to-end

**Limitations:**
- ⚠️ Limited model selection (vs Ollama)
- ⚠️ Manual model management
- ⚠️ Function calling requires parsing
- ⚠️ No easy model switching

### Proposed New Architecture

**Hybrid Approach:**
```
┌─────────────────────────────────────────┐
│      Hybrid Ollama + MLX Stack          │
├─────────────────────────────────────────┤
│ LLM:    Ollama (Qwen3/DeepSeek/Phi-4)  │  ← NEW
│ STT:    MLX-Audio (Whisper)            │  ← Keep
│ TTS:    MLX-Audio (Kokoro-82M)         │  ← Keep
│ Vision: MLX-VLM (Qwen2-VL-2B)          │  ← NEW
│ Tools:  Ollama Native (built-in)       │  ← NEW
└─────────────────────────────────────────┘
```

**Why Hybrid?**
1. **Ollama for LLM:** Better model selection, easier management, built-in tools
2. **MLX-Audio:** Already working, fast, no reason to change
3. **MLX-VLM:** Native vision, better quality than running through Ollama

---

## Phase 2: Explore 🗺️

### Ollama Capabilities (2025)

**Latest Models:**
- **Qwen3** - Latest generation, MoE models, excellent reasoning
- **DeepSeek-R1** - Open reasoning model (O3-level performance)
- **Phi-4** - 14B Microsoft model, state-of-the-art
- **gpt-oss** - OpenAI open source models

**Python API:**
```python
import ollama

# Simple chat
response = ollama.chat(
    model='qwen3',
    messages=[
        {'role': 'system', 'content': 'You are a helpful robot assistant.'},
        {'role': 'user', 'content': 'Move your head up'}
    ],
    tools=[{
        'type': 'function',
        'function': {
            'name': 'move_head',
            'description': 'Move the robot head',
            'parameters': {...}
        }
    }]
)

# Check for tool calls
if response.message.tool_calls:
    for tool in response.message.tool_calls:
        # Execute tool
        result = execute_tool(tool.function.name, tool.function.arguments)
```

**Key Features:**
- ✅ Native function calling (no parsing!)
- ✅ Streaming support
- ✅ Async client available
- ✅ Structured outputs (JSON schema)
- ✅ Easy model switching: `ollama pull qwen3`

### MLX-VLM Qwen Capabilities

**Models Available:**
- **Qwen2-VL-2B-Instruct-4bit** - Fast, 2B params, 4-bit quantized
- **Qwen2.5-VL-32B-Instruct-8bit** - High quality, 32B params

**Python API:**
```python
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template

# Load model
model, processor = load("mlx-community/Qwen2-VL-2B-Instruct-4bit")

# Single image
images = ["path/to/camera_frame.jpg"]
prompt = "What do you see?"
formatted_prompt = apply_chat_template(
    processor, model.config, prompt, num_images=len(images)
)
output = generate(model, processor, formatted_prompt, images)

# Multi-image comparison
images = ["before.jpg", "after.jpg"]
prompt = "Compare these two images"
output = generate(model, processor, formatted_prompt, images)

# Video understanding
# Supports video analysis with --video flag
```

**Key Features:**
- ✅ Multi-image support
- ✅ Video understanding
- ✅ Audio + image multi-modal
- ✅ Native MLX (fast)
- ✅ 4-bit quantization (low memory)

---

## Phase 3: Propose 💡

### Architecture Decision

**Recommended Approach: Hybrid Ollama + MLX**

#### Component Selection

| Component | Choice | Reasoning |
|-----------|--------|-----------|
| **LLM** | Ollama (Qwen3) | • Easy model management<br>• Built-in function calling<br>• Latest models available<br>• Streaming support |
| **STT** | MLX-Audio (Whisper) | • Already working<br>• Fast on MLX<br>• No reason to change |
| **TTS** | MLX-Audio (Kokoro) | • Already working<br>• High quality voices<br>• Keep what works |
| **Vision** | MLX-VLM (Qwen2-VL) | • Multi-image support<br>• Video capable<br>• Native MLX performance |
| **Tools** | Ollama Native | • No parsing needed<br>• Standard format<br>• Easier to maintain |

#### Data Flow

```
User speaks
     ↓
VAD detects → Buffer audio
     ↓
STT (MLX-Audio Whisper) → Transcription
     ↓
Ollama LLM (Qwen3 + tools) → Response or Tool Call
     ↓
If tool call:
  ├─→ camera → MLX-VLM (Qwen2-VL) → Image description
  ├─→ move_head → Execute → Confirmation
  └─→ dance → Execute → Confirmation
     ↓
TTS (MLX-Audio Kokoro) → Speech
     ↓
Speaker plays audio
```

### Integration Points

**1. Ollama LLM Wrapper**
```python
# New file: src/reachy_mini_conversation_app/llm/ollama_client.py

import ollama
from typing import List, Dict, Optional

class OllamaLLM:
    """Wrapper for Ollama LLM with function calling."""

    def __init__(self, model: str = "qwen3", host: str = "http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=host)
        self.messages = []

    def chat(
        self,
        message: str,
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ):
        """Send chat message with optional tools."""
        self.messages.append({"role": "user", "content": message})

        response = self.client.chat(
            model=self.model,
            messages=self.messages,
            tools=tools,
            stream=stream
        )

        # Check for tool calls
        if response.message.tool_calls:
            return {
                "type": "tool_call",
                "tool_calls": response.message.tool_calls
            }

        # Regular text response
        self.messages.append(response.message)
        return {
            "type": "text",
            "content": response.message.content
        }
```

**2. MLX-VLM Vision Wrapper**
```python
# New file: src/reachy_mini_conversation_app/mlx/vision.py

from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
import numpy as np
from PIL import Image

class VLMProcessor:
    """Wrapper for MLX-VLM Qwen vision."""

    def __init__(self, model_path: str = "mlx-community/Qwen2-VL-2B-Instruct-4bit"):
        self.model_path = model_path
        self.model = None
        self.processor = None

    def load(self):
        """Load vision model."""
        self.model, self.processor = load(self.model_path)

    def analyze_image(
        self,
        image: np.ndarray | str,
        prompt: str = "Describe what you see."
    ) -> str:
        """Analyze single image."""
        # Convert numpy to PIL if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        formatted_prompt = apply_chat_template(
            self.processor,
            self.model.config,
            prompt,
            num_images=1
        )

        output = generate(
            self.model,
            self.processor,
            formatted_prompt,
            [image],
            verbose=False
        )

        return output

    def compare_images(
        self,
        images: List[np.ndarray | str],
        prompt: str = "Compare these images."
    ) -> str:
        """Analyze multiple images."""
        # Convert all to PIL
        pil_images = []
        for img in images:
            if isinstance(img, np.ndarray):
                pil_images.append(Image.fromarray(img))
            else:
                pil_images.append(img)

        formatted_prompt = apply_chat_template(
            self.processor,
            self.model.config,
            prompt,
            num_images=len(pil_images)
        )

        output = generate(
            self.model,
            self.processor,
            formatted_prompt,
            pil_images,
            verbose=False
        )

        return output
```

**3. Updated Handler Integration**
```python
# Update: src/reachy_mini_conversation_app/handlers/hybrid_handler.py

class HybridRealtimeHandler(AsyncStreamHandler):
    """Hybrid Ollama + MLX handler."""

    def __init__(self, deps, config):
        # ... same init as before ...

        # Components
        self.llm = OllamaLLM(model=config.ollama_model)  # NEW
        self.stt = STTProcessor()  # Keep
        self.tts = TTSProcessor()  # Keep
        self.vlm = VLMProcessor()  # NEW
        self.vad = SimpleVAD()  # Keep

    async def _process_speech_buffer(self):
        """STT → Ollama → Tool/TTS pipeline."""

        # 1. STT (unchanged)
        transcription = await loop.run_in_executor(
            None, self.stt.transcribe_audio, audio, sample_rate
        )

        # 2. Ollama LLM with tools
        tools = get_tool_specs_ollama()  # Convert to Ollama format

        response = await loop.run_in_executor(
            None, self.llm.chat, transcription, tools
        )

        # 3. Handle response type
        if response["type"] == "tool_call":
            # Execute tools
            for tool_call in response["tool_calls"]:
                result = await self._execute_tool(tool_call)

                # If camera tool, use VLM
                if tool_call.function.name == "camera":
                    frame = self.deps.camera_worker.get_latest_frame()
                    description = await loop.run_in_executor(
                        None, self.vlm.analyze_image, frame
                    )
                    result["description"] = description

                # Send result back to Ollama
                response = await loop.run_in_executor(
                    None, self.llm.chat, json.dumps(result), None
                )

        # 4. TTS (unchanged)
        audio = await loop.run_in_executor(
            None, self.tts.synthesize, response["content"]
        )

        # Queue for playback...
```

---

## Phase 4: Prototype 🔨

### Proof of Concept Implementation

**File: `prototype_ollama_qwen.py`**

```python
#!/usr/bin/env python3
"""Proof of concept: Ollama + Qwen Vision integration.

Tests:
1. Ollama connection and chat
2. Ollama function calling
3. MLX-VLM Qwen2 image analysis
4. Combined workflow (chat → tool → vision → response)
"""

import ollama
from mlx_vlm import load, generate
from mlx_vlm.prompt_utils import apply_chat_template
from PIL import Image
import json

def test_ollama_chat():
    """Test 1: Basic Ollama chat."""
    print("=" * 60)
    print("Test 1: Ollama Chat")
    print("=" * 60)

    try:
        response = ollama.chat(
            model='qwen3',
            messages=[
                {'role': 'user', 'content': 'Say hello in one sentence'}
            ]
        )
        print(f"✅ Ollama Response: {response.message.content}")
        return True
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        return False


def test_ollama_tools():
    """Test 2: Ollama function calling."""
    print("\n" + "=" * 60)
    print("Test 2: Ollama Function Calling")
    print("=" * 60)

    tools = [{
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': 'Get weather for a location',
            'parameters': {
                'type': 'object',
                'properties': {
                    'location': {'type': 'string', 'description': 'City name'},
                    'unit': {'type': 'string', 'enum': ['C', 'F']}
                },
                'required': ['location']
            }
        }
    }]

    try:
        response = ollama.chat(
            model='qwen3',
            messages=[
                {'role': 'user', 'content': 'What is the weather in Paris?'}
            ],
            tools=tools
        )

        if response.message.tool_calls:
            tool_call = response.message.tool_calls[0]
            print(f"✅ Tool called: {tool_call.function.name}")
            print(f"   Arguments: {tool_call.function.arguments}")
            return True
        else:
            print("⚠️  No tool call made")
            return False
    except Exception as e:
        print(f"❌ Tool calling test failed: {e}")
        return False


def test_qwen_vision():
    """Test 3: MLX-VLM Qwen2 vision."""
    print("\n" + "=" * 60)
    print("Test 3: Qwen2-VL Vision")
    print("=" * 60)

    try:
        print("Loading Qwen2-VL model...")
        model, processor = load("mlx-community/Qwen2-VL-2B-Instruct-4bit")

        # Create test image (or load from file)
        test_image = "http://images.cocodataset.org/val2017/000000039769.jpg"
        prompt = "Describe this image briefly."

        formatted_prompt = apply_chat_template(
            processor, model.config, prompt, num_images=1
        )

        output = generate(model, processor, formatted_prompt, [test_image], verbose=False)

        print(f"✅ Vision output: {output}")
        return True
    except Exception as e:
        print(f"❌ Vision test failed: {e}")
        return False


def test_combined_workflow():
    """Test 4: Combined Ollama + Vision workflow."""
    print("\n" + "=" * 60)
    print("Test 4: Combined Workflow")
    print("=" * 60)

    try:
        # Define camera tool
        tools = [{
            'type': 'function',
            'function': {
                'name': 'camera',
                'description': 'Take a photo and describe what you see',
                'parameters': {'type': 'object', 'properties': {}}
            }
        }]

        # Step 1: User asks to look
        print("User: 'What do you see?'")
        response = ollama.chat(
            model='qwen3',
            messages=[
                {'role': 'system', 'content': 'You are a robot. Use the camera tool to see.'},
                {'role': 'user', 'content': 'What do you see?'}
            ],
            tools=tools
        )

        # Step 2: Check for camera tool call
        if response.message.tool_calls:
            tool = response.message.tool_calls[0]
            print(f"✅ Robot wants to use: {tool.function.name}")

            # Step 3: Execute camera (use vision model)
            print("📸 Taking photo and analyzing...")
            model, processor = load("mlx-community/Qwen2-VL-2B-Instruct-4bit")
            test_image = "http://images.cocodataset.org/val2017/000000039769.jpg"

            formatted_prompt = apply_chat_template(
                processor, model.config, "Describe what you see.", num_images=1
            )
            vision_result = generate(model, processor, formatted_prompt, [test_image], verbose=False)

            print(f"👁️  Vision: {vision_result}")

            # Step 4: Send result back to Ollama
            final_response = ollama.chat(
                model='qwen3',
                messages=[
                    {'role': 'system', 'content': 'You are a robot.'},
                    {'role': 'user', 'content': 'What do you see?'},
                    response.message,
                    {'role': 'tool', 'content': vision_result}
                ]
            )

            print(f"🤖 Robot says: {final_response.message.content}")
            return True
        else:
            print("⚠️  Robot didn't call camera tool")
            return False

    except Exception as e:
        print(f"❌ Combined workflow test failed: {e}")
        return False


def main():
    """Run all proof of concept tests."""
    print("\n" + "=" * 60)
    print("Ollama + Qwen Vision Proof of Concept")
    print("=" * 60)

    tests = [
        ("Ollama Chat", test_ollama_chat),
        ("Ollama Function Calling", test_ollama_tools),
        ("Qwen Vision", test_qwen_vision),
        ("Combined Workflow", test_combined_workflow),
    ]

    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Ready to implement.")
        print("\nNext steps:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Pull model: ollama pull qwen3")
        print("3. Install mlx-vlm: pip install mlx-vlm")
        print("4. Begin Sprint 3 implementation")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
```

---

## Phase 5: Reflect 🤔

### Trade-off Analysis

#### Option A: Pure MLX (Current Plan)
**Pros:**
- ✅ Unified framework
- ✅ No external dependencies
- ✅ Fast unified memory

**Cons:**
- ❌ Limited model selection
- ❌ Manual function call parsing
- ❌ Harder model management

#### Option B: Hybrid Ollama + MLX (Proposed)
**Pros:**
- ✅ Best-in-class models (Qwen3, DeepSeek-R1)
- ✅ Native function calling
- ✅ Easy model switching
- ✅ Keep working audio pipeline
- ✅ Better vision (Qwen2-VL multi-image)

**Cons:**
- ❌ Ollama must be running (extra process)
- ❌ HTTP overhead for LLM calls
- ❌ Two frameworks (Ollama + MLX)

#### Option C: Pure Ollama
**Pros:**
- ✅ Simple architecture
- ✅ One framework

**Cons:**
- ❌ No audio support (STT/TTS)
- ❌ Would need to replace working pipeline
- ❌ Not optimized for Apple Silicon like MLX

### Recommendation

**Go with Option B: Hybrid Ollama + MLX**

**Reasoning:**
1. **Pragmatic:** Keep what works (audio), upgrade what matters (LLM, vision)
2. **Best tools:** Ollama for LLM management, MLX for audio/vision performance
3. **Future-proof:** Easy to switch LLM models, add new capabilities
4. **José Valim approved:** "Use the best tool for each job"

---

## Phase 6: Iterate 🔄

### Implementation Roadmap

#### Sprint 3A: Ollama Integration (2-3 days)

**Day 1: Ollama LLM Wrapper**
- [ ] Create `src/reachy_mini_conversation_app/llm/ollama_client.py`
- [ ] Implement OllamaLLM class with chat, streaming, tools
- [ ] Add configuration for Ollama (model, host)
- [ ] Write unit tests

**Day 2: Tool Calling Integration**
- [ ] Convert tool specs to Ollama format
- [ ] Implement tool execution dispatcher
- [ ] Handle tool results back to Ollama
- [ ] Test multi-turn tool conversations

**Day 3: Handler Integration**
- [ ] Update handler to use OllamaLLM
- [ ] Replace MLX-LM generate with Ollama chat
- [ ] Test full conversation flow
- [ ] Benchmark latency vs MLX-LM

#### Sprint 3B: Vision Integration (2-3 days)

**Day 1: MLX-VLM Wrapper**
- [ ] Create `src/reachy_mini_conversation_app/mlx/vision.py`
- [ ] Implement VLMProcessor class
- [ ] Add single image analysis
- [ ] Add multi-image comparison

**Day 2: Camera Tool Integration**
- [ ] Integrate VLM with camera tool
- [ ] Test vision-based conversations
- [ ] Handle vision results in Ollama context
- [ ] Test "What do you see?" workflow

**Day 3: Advanced Features**
- [ ] Video analysis (optional)
- [ ] Multi-image comparison for "before/after"
- [ ] Error handling and fallbacks
- [ ] Performance optimization

#### Sprint 3C: Polish & Testing (1-2 days)

- [ ] End-to-end integration test
- [ ] Latency profiling and optimization
- [ ] Error recovery and edge cases
- [ ] Documentation and examples
- [ ] Create Sprint 3 completion doc

### Success Criteria

✅ **Functional:**
- User can have conversation with Ollama LLM
- Robot executes tools (move_head, dance, etc.)
- Camera tool triggers vision analysis
- Vision results incorporated in conversation

✅ **Performance:**
- End-to-end latency < 5s (acceptable)
- Tool calls execute correctly
- Vision analysis < 3s for single image

✅ **Quality:**
- Better responses than MLX-LM (Qwen3 > Hermes)
- Accurate vision descriptions
- Smooth tool execution

---

## Dependencies & Installation

### Ollama Setup

```bash
# Install Ollama
# Mac: brew install ollama
# Linux: curl https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Pull recommended model
ollama pull qwen3

# Alternative models
ollama pull deepseek-r1
ollama pull phi4
```

### Python Dependencies

```bash
# Add to requirements.txt
ollama>=0.4.0
mlx-vlm>=0.2.0
pillow>=10.0.0
```

### Configuration

```python
# Add to src/reachy_mini_conversation_app/config.py

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
VLM_MODEL = os.getenv("VLM_MODEL", "mlx-community/Qwen2-VL-2B-Instruct-4bit")
```

---

## Migration Strategy

### Backward Compatibility

Create handler selection:
```python
# In main.py
if args.mlx:
    handler = MLXRealtimeHandler(deps, config)  # Sprint 1-2
elif args.hybrid or args.ollama:
    handler = HybridRealtimeHandler(deps, config)  # Sprint 3
else:
    handler = OpenaiRealtimeHandler(deps, config)  # Original
```

### Testing Both Implementations

```bash
# Test pure MLX
python -m reachy_mini_conversation_app.main --mlx

# Test hybrid Ollama + MLX
python -m reachy_mini_conversation_app.main --hybrid

# Compare latency
pytest tests/test_handler_comparison.py
```

---

## Risk Assessment & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ollama service down | High | Fallback to MLX-LM, health check on startup |
| Slow tool execution | Medium | Async execution, timeout handling |
| Large vision model | Medium | Use 2B variant, consider caching |
| Integration complexity | Low | Prototype first, incremental testing |

---

## References & Sources

**Ollama:**
- [GitHub - ollama/ollama](https://github.com/ollama/ollama)
- [Ollama Python library](https://github.com/ollama/ollama-python)
- [Ollama Documentation](https://docs.ollama.com)
- [Ollama Model Library](https://ollama.com/library)
- [Ollama Blog](https://ollama.com/blog)

**MLX-VLM:**
- Repository: `_ai/refs/repos/mlx-vlm/`
- Models: [mlx-community on HuggingFace](https://huggingface.co/mlx-community)

**Latest Research:**
- DeepSeek-R1, Qwen3, Phi-4 capabilities from Ollama updates (2025)

---

## Conclusion: José Valim's Perspective

**What José Would Say:**

> "This is pragmatic engineering. You're not married to one framework—you choose the best tool for each part:
>
> - Ollama makes LLM management trivial. Use it.
> - MLX-Audio already works. Keep it.
> - MLX-VLM gives you better vision. Use it.
>
> Don't over-engineer. Test the hypothesis with the prototype. If Ollama's HTTP overhead is acceptable (it likely is), ship it. You can always optimize later.
>
> Make it work, make it right, make it fast. In that order."

**Recommendation:** ✅ Proceed with Hybrid Ollama + MLX approach.

---

**Next Action:** Run `prototype_ollama_qwen.py` to validate hypothesis, then begin Sprint 3A implementation.
