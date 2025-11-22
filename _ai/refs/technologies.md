# Technology References

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Core Technologies

### OpenAI Realtime API

**Documentation:** https://platform.openai.com/docs/guides/realtime
**Python SDK:** https://github.com/openai/openai-python

**Key Features:**
- Bidirectional audio streaming via WebSocket
- Server-side Voice Activity Detection (VAD)
- Function calling (tools)
- Multiple modalities (text + audio)
- Low-latency TTS (<500ms)

**Used For:**
- Voice conversation loop
- Tool dispatching
- Audio generation for speech

**Configuration:**
```python
session_config = {
    "modalities": ["text", "audio"],
    "instructions": prompt,
    "voice": "sage",  # or alloy, ash, coral, echo
    "input_audio_format": "pcm16",
    "output_audio_format": "pcm16",
    "input_audio_transcription": {"model": "whisper-1"},
    "tools": tool_definitions,
    "temperature": 0.8,
}
```

---

### Reachy Mini SDK

**Repository:** https://github.com/pollen-robotics/reachy_mini
**Documentation:** https://docs.pollen-robotics.com/

**Key Features:**
- Joint control (position, speed, torque)
- IK/FK solvers
- Kinematics chain
- Built-in moves library

**Used For:**
- Robot hardware control
- Pose calculations
- Movement execution

**Example:**
```python
from reachy_mini import ReachyMini

robot = ReachyMini()
robot.set_target({
    "neck_roll": 0.0,
    "neck_pitch": 10.0,
    "neck_yaw": 5.0,
    # ... other joints
})
```

---

### Gradio + fastrtc

**Gradio:** https://gradio.app/
**fastrtc:** https://github.com/freddyaboulton/fastrtc

**Key Features:**
- WebRTC streaming with low latency
- Web UI framework
- Real-time audio/video
- Chatbot interface

**Used For:**
- Web-based UI
- Remote robot control
- Transcript display
- Audio streaming

**Example:**
```python
from fastrtc import Stream

stream = Stream(
    mode=mode,
    input_sample_rate=16000,
    output_sample_rate=24000,
)

with gr.Blocks() as demo:
    chatbot = gr.Chatbot(type="messages")
    stream.render(chatbot=chatbot)

demo.launch()
```

---

### Vision Models

#### GPT-4 Vision (Cloud)

**Documentation:** https://platform.openai.com/docs/guides/vision

**Used For:**
- Image understanding
- Scene description
- Emotion detection

**Example:**
```python
response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    }]
)
```

#### SmolVLM2 (Local)

**Repository:** https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct
**Model Size:** 2.2B parameters

**Used For:**
- Local vision processing (privacy)
- Image-to-text
- Faster inference (with GPU)

**Example:**
```python
from transformers import AutoProcessor, AutoModelForVision2Seq

processor = AutoProcessor.from_pretrained("HuggingFaceTB/SmolVLM2-2.2B-Instruct")
model = AutoModelForVision2Seq.from_pretrained("HuggingFaceTB/SmolVLM2-2.2B-Instruct")

inputs = processor(text=prompt, images=image, return_tensors="pt")
outputs = model.generate(**inputs)
description = processor.decode(outputs[0], skip_special_tokens=True)
```

---

### Face Tracking

#### YOLOv8

**Repository:** https://github.com/ultralytics/ultralytics
**Documentation:** https://docs.ultralytics.com/

**Used For:**
- Fast face detection
- Bounding box tracking
- Real-time performance (30fps+)

**Example:**
```python
from ultralytics import YOLO

model = YOLO("yolov8n-face.pt")
results = model(frame)
for box in results[0].boxes:
    x1, y1, x2, y2 = box.xyxy[0]
    # Use bounding box
```

#### MediaPipe

**Repository:** https://github.com/google/mediapipe
**Documentation:** https://developers.google.com/mediapipe

**Used For:**
- Face mesh detection
- Landmark tracking
- 468 facial landmarks

**Example:**
```python
from reachy_mini_toolbox.mediapipe import HeadTracker

tracker = HeadTracker()
result = tracker.detect(frame)
if result:
    x, y, z = result.face_center
```

---

### Audio Processing

#### librosa

**Documentation:** https://librosa.org/

**Used For:**
- Audio resampling (16kHz ↔ 24kHz)
- Sample rate conversion

**Example:**
```python
import librosa

audio_24k = librosa.resample(audio_16k, orig_sr=16000, target_sr=24000)
```

#### NumPy/SciPy

**Used For:**
- Audio buffer manipulation
- Envelope extraction
- Signal processing

---

### Development Tools

#### uv

**Repository:** https://github.com/astral-sh/uv
**Documentation:** https://docs.astral.sh/uv/

**Used For:**
- Fast Python package installer
- Virtual environment management
- Lock file generation

**Commands:**
```bash
uv venv --python 3.12.1
uv sync --extra all_vision
uv pip install <package>
```

#### ruff

**Repository:** https://github.com/astral-sh/ruff
**Documentation:** https://docs.astral.sh/ruff/

**Used For:**
- Linting (replaces flake8, pylint)
- Formatting (replaces black)
- Import sorting

**Configuration:** `pyproject.toml`

#### mypy

**Documentation:** https://mypy.readthedocs.io/

**Used For:**
- Static type checking
- Type hint validation

**Configuration:** `pyproject.toml`

#### pytest

**Documentation:** https://docs.pytest.org/

**Used For:**
- Unit testing
- Async testing (pytest-asyncio)
- Fixtures and mocking

---

## Python Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| openai | >=2.1 | OpenAI API client |
| fastrtc | >=0.0.33 | WebRTC streaming |
| gradio | >=5.49.0 | Web UI framework |
| aiortc | >=1.13.0 | WebRTC implementation |
| opencv-python | >=4.12.0.88 | Camera and vision |
| torch | >=2.7.0 | ML model runtime |
| transformers | >=4.47.1 | Hugging Face models |
| ultralytics | >=8.3.0 | YOLO models |
| supervision | >=0.27.0 | Detection utilities |
| librosa | >=0.10.0 | Audio processing |
| numpy | >=1.26.0 | Numerical computing |
| scipy | >=1.14.0 | Scientific computing |
| reachy_mini | >=1.0.0.rc4 | Robot control |
| reachy_mini_dances_library | latest | Dance moves |

---

## Hardware Requirements

### Minimum
- **CPU:** Multi-core (4+ cores recommended)
- **RAM:** 4GB
- **Camera:** USB webcam (720p+)
- **Audio:** Microphone + speaker

### Recommended (with local vision)
- **GPU:** NVIDIA GPU with 4GB+ VRAM
- **CUDA:** 11.8+
- **RAM:** 8GB+
- **Storage:** 10GB for models

---

## Network Requirements

- **OpenAI API:** HTTPS + WebSocket (wss://)
- **Gradio:** WebRTC (STUN/TURN for remote access)
- **Bandwidth:** ~100kbps for audio streaming

---

## Operating Systems

- ✅ **Linux** (primary development)
- ✅ **macOS** (compatible)
- ⚠️ **Windows** (may need WSL for full compatibility)

---

## External Services

| Service | Purpose | Cost |
|---------|---------|------|
| OpenAI API | Realtime conversation, vision | Pay-per-use |
| Hugging Face Hub | Model downloads | Free (with account) |

---

These technologies combine to create a **low-latency**, **multimodal**, and **extensible** conversational robot system.
