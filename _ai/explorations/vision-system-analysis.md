# Vision System Analysis

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Dual Vision Architecture

The system supports **two complementary vision approaches**:

1. **Cloud Vision (GPT-4V):** High accuracy, requires internet, costs per API call
2. **Local Vision (SmolVLM2):** Privacy-preserving, runs on device, requires GPU

### Why Both?

Different use cases require different trade-offs:

| Aspect | Cloud (GPT-4V) | Local (SmolVLM2) |
|--------|---------------|------------------|
| **Accuracy** | Excellent | Good |
| **Privacy** | Data sent to OpenAI | Fully local |
| **Cost** | ~$0.01-0.05 per image | Free (after model download) |
| **Latency** | 500-2000ms | 100-500ms (with GPU) |
| **Internet Required** | Yes | No |
| **Setup** | Just API key | Model download (~5GB) |

## Vision Processing Paths

### Path 1: Cloud Vision (GPT-4V)

```
User: "What do you see?"
    │
    ▼
AI calls camera tool
    │
    ├─► CameraWorker.get_latest_frame()
    │   └─► Returns RGB numpy array
    │
    ├─► Encode as JPEG
    │   └─► cv2.imencode('.jpg', frame)
    │
    ├─► Base64 encode
    │   └─► base64.b64encode(jpg_bytes)
    │
    ├─► Send to OpenAI API
    │   POST https://api.openai.com/v1/chat/completions
    │   {
    │     "model": "gpt-4-vision-preview",
    │     "messages": [{
    │       "role": "user",
    │       "content": [
    │         {"type": "text", "text": "What do you see?"},
    │         {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    │       ]
    │     }]
    │   }
    │
    └─► Receive description
        └─► Return to Realtime API
            └─► AI speaks result
```

**Advantages:**
- Extremely accurate
- Handles complex scenes
- Understands context and nuance
- Reads text in images
- Detects emotions accurately

**Disadvantages:**
- Network latency (500ms+)
- Costs money per request
- Requires internet
- Privacy concerns

### Path 2: Local Vision (SmolVLM2)

```
User: "What do you see?"
    │
    ▼
AI calls camera tool
    │
    ├─► CameraWorker.get_latest_frame()
    │   └─► Returns RGB numpy array
    │
    ├─► VisionManager.process(frame, prompt)
    │   │
    │   ├─► Load model (cached after first load)
    │   │   └─► HuggingFaceTB/SmolVLM2-2.2B-Instruct
    │   │
    │   ├─► Preprocess image
    │   │   └─► processor(images=frame, text=prompt, return_tensors="pt")
    │   │
    │   ├─► Run inference
    │   │   └─► model.generate(**inputs, max_new_tokens=200)
    │   │
    │   └─► Decode output
    │       └─► processor.decode(outputs[0], skip_special_tokens=True)
    │
    └─► Return description
        └─► AI speaks result
```

**Advantages:**
- Fast (100-500ms with GPU)
- Private (no data leaves device)
- No internet required
- No per-use cost

**Disadvantages:**
- Lower accuracy than GPT-4V
- Requires GPU (slow on CPU)
- Large model download (~5GB)
- Less contextual understanding

## Implementation Deep Dive

### CameraWorker: Frame Buffering

```python
class CameraWorker:
    def __init__(self, robot: ReachyMini, target_fps: int = 30):
        self._cap = cv2.VideoCapture(0)  # Default camera
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._target_fps = target_fps
        self._running = False

    def _capture_loop(self):
        """Run at 30Hz, capture and buffer frames"""
        target_dt = 1.0 / self._target_fps

        while self._running:
            start = time.time()

            # Capture frame
            ret, frame = self._cap.read()

            if ret:
                # Store latest frame (thread-safe)
                with self._frame_lock:
                    self._latest_frame = frame.copy()

                # Face tracking (if enabled)
                if self._head_tracker:
                    self._process_face_tracking(frame)

            # Sleep to maintain FPS
            elapsed = time.time() - start
            time.sleep(max(0, target_dt - elapsed))

    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get latest camera frame (thread-safe).

        Returns RGB numpy array (not BGR!).
        """
        with self._frame_lock:
            if self._latest_frame is None:
                return None

            # Convert BGR (OpenCV format) to RGB (expected by vision models)
            rgb_frame = cv2.cvtColor(self._latest_frame, cv2.COLOR_BGR2RGB)
            return rgb_frame.copy()
```

**Key Design Decisions:**

1. **Latest frame only:** No frame queue, just most recent
   - Why: Vision is not real-time critical; latest is good enough
   - Avoids memory buildup

2. **BGR → RGB conversion:** OpenCV uses BGR, models expect RGB
   - Critical bug if forgotten!
   - Handled in `get_latest_frame()` for tool use

3. **Thread-safe access:** Lock protects concurrent reads/writes
   - CameraWorker writes at 30Hz
   - Tools read on-demand

4. **Copy semantics:** Always return copies, never references
   - Prevents race conditions
   - Slight performance cost but worth it

### VisionProcessor: Local VLM

```python
class VisionProcessor:
    def __init__(self, model_name: str = "HuggingFaceTB/SmolVLM2-2.2B-Instruct"):
        self.model_name = model_name
        self._model = None
        self._processor = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    def _load_model(self):
        """Lazy load model (expensive operation)"""
        if self._model is not None:
            return  # Already loaded

        logger.info(f"Loading vision model: {self.model_name}")

        self._processor = AutoProcessor.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )

        self._model = AutoModelForVision2Seq.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16 if self._device == "cuda" else torch.float32
        ).to(self._device)

        logger.info(f"Model loaded on {self._device}")

    async def process_image(self, image: np.ndarray, prompt: str) -> str:
        """
        Process image with local VLM.

        Args:
            image: RGB numpy array (H, W, 3)
            prompt: Text prompt (e.g., "Describe this image")

        Returns:
            Generated text description
        """
        # Lazy load (first call only)
        self._load_model()

        # Convert numpy to PIL Image
        pil_image = Image.fromarray(image)

        # Preprocess
        inputs = self._processor(
            text=prompt,
            images=pil_image,
            return_tensors="pt"
        ).to(self._device)

        # Generate
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=False  # Deterministic for consistency
            )

        # Decode
        generated_text = self._processor.decode(
            outputs[0],
            skip_special_tokens=True
        )

        # Extract answer (model may echo prompt)
        answer = self._extract_answer(generated_text, prompt)

        return answer

    def _extract_answer(self, generated: str, prompt: str) -> str:
        """
        Extract actual answer from generated text.

        SmolVLM2 often echoes the prompt, so we strip it.
        """
        # Simple heuristic: answer follows prompt
        if prompt in generated:
            return generated.split(prompt)[-1].strip()
        return generated.strip()
```

**Optimization Notes:**

1. **Lazy Loading:** Model loaded on first use (not at startup)
   - Saves ~5-10s startup time
   - Allows running without `--local-vision` flag

2. **GPU Auto-Detection:** Uses CUDA if available, CPU otherwise
   - GPU: 100-200ms inference
   - CPU: 2-5s inference (not recommended)

3. **float16 on GPU:** Half precision for speed
   - 2x faster inference
   - Minimal accuracy loss
   - Only on CUDA (CPU doesn't support it well)

4. **Caching:** Model stays loaded between calls
   - First call: ~5s (load model)
   - Subsequent calls: ~200ms (inference only)

### VisionManager: Periodic Processing

Optional component that runs vision processing **automatically** at intervals.

```python
class VisionManager:
    def __init__(
        self,
        camera_worker: CameraWorker,
        vision_processor: VisionProcessor,
        interval: float = 5.0
    ):
        self._camera = camera_worker
        self._processor = vision_processor
        self._interval = interval
        self._running = False
        self._thread = None

        # Store latest description
        self._latest_description: Optional[str] = None
        self._description_lock = threading.Lock()

    def _processing_loop(self):
        """Run vision processing every N seconds"""
        while self._running:
            try:
                # Get frame
                frame = self._camera.get_latest_frame()
                if frame is None:
                    time.sleep(self._interval)
                    continue

                # Process with generic prompt
                prompt = "Describe what you see in this image."
                description = asyncio.run(
                    self._processor.process_image(frame, prompt)
                )

                # Store result
                with self._description_lock:
                    self._latest_description = description

                logger.debug(f"Vision update: {description[:100]}...")

            except Exception as e:
                logger.error(f"Vision processing error: {e}")

            # Wait for next interval
            time.sleep(self._interval)

    def get_latest_description(self) -> Optional[str]:
        """Get most recent vision description"""
        with self._description_lock:
            return self._latest_description
```

**Use Case:** Proactive awareness. AI can reference what robot "sees" without explicit camera tool call.

**Trade-off:** Uses GPU/network every 5s. May not be worth it for most applications.

## Face Tracking Integration

### YOLO-based Tracking

```python
from ultralytics import YOLO
import supervision as sv

class YoloHeadTracker:
    def __init__(self, model_name: str = "yolov8n-face.pt"):
        self.model = YOLO(model_name)
        self.tracker = sv.ByteTrack()  # Multi-object tracking

    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces in frame.

        Returns:
            List of detections: [{"bbox": (x1,y1,x2,y2), "confidence": 0.95}, ...]
        """
        # Run inference
        results = self.model(frame, verbose=False)[0]

        # Extract bounding boxes
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            confidence = box.conf[0].cpu().numpy()

            if confidence > 0.5:  # Confidence threshold
                detections.append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": confidence
                })

        return detections
```

**Performance:**
- YOLOv8n (nano): ~15ms per frame (60fps capable)
- YOLOv8s (small): ~25ms per frame (40fps capable)
- YOLOv8m (medium): ~40ms per frame (25fps capable)

**Choice:** YOLOv8n is default (fastest, sufficient accuracy for face detection).

### MediaPipe Tracking

```python
from reachy_mini_toolbox.mediapipe import HeadTracker

class MediaPipeHeadTracker:
    def __init__(self):
        self.tracker = HeadTracker()

    def detect(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Detect face with MediaPipe.

        Returns:
            {"face_center": (x, y, z), "landmarks": [...]} or None
        """
        result = self.tracker.detect(frame)

        if result:
            return {
                "face_center": result.face_center,
                "landmarks": result.landmarks
            }

        return None
```

**Differences from YOLO:**

| Feature | YOLO | MediaPipe |
|---------|------|-----------|
| **Speed** | Faster (~15ms) | Slower (~25ms) |
| **Detail** | Bounding box only | 468 facial landmarks |
| **Tracking** | Detection only | Pose estimation |
| **Use Case** | Simple face tracking | Detailed face analysis |

**Choice:** YOLO for basic tracking, MediaPipe for detailed facial analysis.

## Vision Tool Implementation

### Camera Tool with Vision Selection

```python
@ToolRegistry.register
class CameraTool(Tool):
    name = "camera"
    description = "Capture and analyze what you see through your camera"
    parameters_schema = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "What to look for or analyze (e.g., 'What emotion is this person showing?')"
            }
        },
        "required": ["prompt"]
    }

    async def execute(self, args: dict, deps: ToolDependencies) -> str:
        prompt = args["prompt"]

        # Check camera availability
        if not deps.camera_worker:
            return "Error: Camera not available"

        # Get latest frame
        frame = deps.camera_worker.get_latest_frame()
        if frame is None:
            return "Error: No camera frame captured yet"

        # Process with appropriate vision system
        try:
            if deps.vision_manager:
                # Local vision
                description = await deps.vision_manager.vision_processor.process_image(
                    frame, prompt
                )
            else:
                # Cloud vision (GPT-4V)
                description = await self._process_with_gpt4v(frame, prompt)

            return description

        except Exception as e:
            logger.error(f"Vision processing failed: {e}")
            return f"Error: Could not process image - {str(e)}"

    async def _process_with_gpt4v(self, frame: np.ndarray, prompt: str) -> str:
        """Send frame to GPT-4V for analysis"""
        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        jpg_bytes = buffer.tobytes()
        base64_image = base64.b64encode(jpg_bytes).decode('utf-8')

        # Call OpenAI API
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }],
            max_tokens=300
        )

        return response.choices[0].message.content
```

## Performance Optimization Strategies

### 1. Frame Skip for Vision

Don't process every frame; sample at lower rate.

```python
# CameraWorker captures at 30fps
# Vision processes at 1fps (every 30th frame)

frame_count = 0
VISION_INTERVAL = 30

while running:
    frame = capture_frame()
    frame_count += 1

    if frame_count % VISION_INTERVAL == 0:
        process_vision(frame)  # Every ~1 second
```

### 2. Resolution Reduction

Vision models don't need full resolution.

```python
def preprocess_for_vision(frame: np.ndarray, target_size: int = 512) -> np.ndarray:
    """Resize frame to target size (preserving aspect ratio)"""
    h, w = frame.shape[:2]
    scale = target_size / max(h, w)

    new_w = int(w * scale)
    new_h = int(h * scale)

    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized
```

**Impact:**
- 1920x1080 → 512x288: ~15x fewer pixels
- Faster encoding, faster network transfer, faster inference
- Minimal accuracy loss for most tasks

### 3. Batch Processing

Process multiple prompts on same image in one call.

```python
# Instead of:
desc1 = process("What emotion?")
desc2 = process("How many people?")
desc3 = process("What are they doing?")

# Do:
combined_prompt = """
1. What emotion is shown?
2. How many people are there?
3. What are they doing?
"""
combined_desc = process(combined_prompt)
```

## Error Handling & Edge Cases

### No Camera Available

```python
if not deps.camera_worker:
    return "I don't have access to a camera right now."
```

### Camera Not Yet Initialized

```python
frame = deps.camera_worker.get_latest_frame()
if frame is None:
    return "My camera is still warming up. Try again in a moment."
```

### Vision Processing Timeout

```python
try:
    description = await asyncio.wait_for(
        process_vision(frame, prompt),
        timeout=5.0  # 5 second timeout
    )
except asyncio.TimeoutError:
    return "Vision processing took too long. Try again."
```

### API Rate Limiting (GPT-4V)

```python
except openai.RateLimitError:
    return "I'm being rate-limited by the vision API. Please wait a moment."
```

### Model Not Downloaded (SmolVLM2)

```python
except HFValidationError:
    return "Vision model not downloaded. Please run setup script."
```

## Vision Prompt Engineering

### Good Vision Prompts

```python
# ✅ Specific and actionable
"What emotion is this person displaying?"
"How many people are in the scene?"
"Describe the main object in the center of the image."
"Is there any text visible? If so, what does it say?"

# ✅ Contextual
"I'm looking at someone. Do they seem happy or sad?"
"Describe what's on the desk in front of me."
```

### Bad Vision Prompts

```python
# ❌ Too vague
"What do you see?"  # Everything? Be specific.

# ❌ Too complex
"Describe the image in detail including all objects, their positions, colors, lighting conditions, and emotional context."  # Will timeout or truncate

# ❌ Ambiguous
"Look at the thing."  # What thing?
```

## Future Improvements

### Potential Enhancements

1. **Video Understanding:** Process sequences of frames for temporal context
2. **Depth Integration:** Use depth camera for 3D scene understanding
3. **Fine-tuned Models:** Train SmolVLM2 on robot-specific scenarios
4. **Edge Caching:** Cache descriptions for similar scenes (avoid reprocessing)
5. **Multi-modal Fusion:** Combine vision + audio for richer context

### Advanced Features

```python
# Object tracking over time
tracker = ObjectTracker()
tracker.update(frame)
objects = tracker.get_tracked_objects()  # {"person_1": bbox, "cup_2": bbox}

# Depth-aware scene understanding
depth_map = depth_camera.get_depth()
scene_3d = reconstruct_scene(frame, depth_map)

# Gesture recognition
gesture = gesture_recognizer.detect(frame)
if gesture == "wave":
    robot.wave_back()
```

---

## Key Insights

1. **Dual systems for flexibility:** Cloud for accuracy, local for privacy/speed
2. **Thread-safe frame buffering:** Critical for reliable vision access
3. **Lazy loading optimization:** Don't pay model load cost unless needed
4. **BGR/RGB conversion gotcha:** OpenCV vs vision models
5. **Face tracking complements vision:** Real-time tracking + on-demand analysis

The vision system transforms Reachy Mini from a **blind automation** into a **seeing assistant** that can understand and respond to its environment.
