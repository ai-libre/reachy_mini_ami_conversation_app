# Motion System Analysis

**Created:** 2025-11-22 14:28:52 UTC
**Last Updated:** 2025-11-22 14:28:52 UTC

## Deep Dive: Layered Motion Architecture

### The Problem This Solves

Traditional robot animation systems face a critical challenge: **composing concurrent behaviors**. How do you make a robot that can:

- Dance while tracking a face?
- Wobble while speaking during an emotion?
- Breathe while maintaining the end pose of a dance?

Most systems choose one of these approaches:

1. **Priority-based:** Higher priority motion wins (face tracking interrupts dance)
2. **Joint partitioning:** Different joints for different behaviors (head tracks, body dances)
3. **Behavior switching:** Strictly one at a time

This codebase uses a **fourth approach: pose composition in world coordinates**.

### Mathematical Foundation

#### Primary Motion (Sequential)

```
Primary Queue: [Dance₁, Emotion₁, Goto₁, Breathing∞]

At time t:
  current_move = queue[current_index]
  current_frame = frames_since_move_start

  primary_pose = current_move.get_pose(current_frame)

  if current_move.is_complete():
    current_index += 1
    current_frame = 0
```

**Characteristics:**
- Mutually exclusive (only one plays at a time)
- Frame-based playback (choreographed)
- Cached last pose for smooth transitions

#### Secondary Motion (Additive)

```
Secondary Offsets:
  speech_offset = head_wobbler.get_offset()     # Audio-reactive
  tracking_offset = camera.get_face_offset()    # Face-following

Combined:
  secondary_total = compose(speech_offset, tracking_offset)
```

**Characteristics:**
- Concurrent (both active simultaneously)
- Real-time generated (not pre-recorded)
- Relative offsets (not absolute poses)

#### Composition Function

```python
def compose_world_offset(base_pose: dict, offset_pose: dict) -> dict:
    """
    Compose poses in world frame.

    Mathematically:
      T_final = T_base ⊕ T_offset

    Where ⊕ is pose composition operator (not simple addition!).
    """
    # Simplified (actual implementation uses proper kinematics)
    final_pose = {}
    for joint in base_pose.keys():
        base_value = base_pose[joint]
        offset_value = offset_pose.get(joint, 0.0)

        # Composition in world frame (not joint angles!)
        final_pose[joint] = compose_transform(base_value, offset_value)

    return final_pose
```

### Why World-Frame Composition Works

**Joint-space addition doesn't work:**
```python
# BAD: Joint angle addition
head_pitch = dance_pose["head_pitch"] + tracking_offset["head_pitch"]
# Problem: Coordinate frames differ at each dance pose!
```

**World-frame composition does work:**
```python
# GOOD: World-frame offset
base_transform = forward_kinematics(dance_pose)
offset_transform = compute_offset_in_world_frame(tracking_offset)
final_transform = base_transform ⊕ offset_transform
final_pose = inverse_kinematics(final_transform)
```

**Intuition:** "From the current dance pose, look 10° to the left" makes sense. "Add 10° to the head pitch joint" doesn't (what if the head is already tilted?).

### Control Loop Timing

```
Every 10ms (100Hz):
┌─────────────────────────────────────────┐
│ 1. Process Commands (~0.1ms)            │
│    - Dequeue new moves                  │
│    - Update activity timestamp          │
├─────────────────────────────────────────┤
│ 2. Idle Detection (~0.01ms)             │
│    - Check if 30s elapsed               │
│    - Start breathing if idle            │
├─────────────────────────────────────────┤
│ 3. Primary Pose (~0.5ms)                │
│    - Get current frame from move        │
│    - Advance move if complete           │
│    - Cache pose for next tick           │
├─────────────────────────────────────────┤
│ 4. Secondary Offsets (~0.2ms)           │
│    - Read wobble offset (lock)          │
│    - Read tracking offset (lock)        │
├─────────────────────────────────────────┤
│ 5. Composition (~1ms)                   │
│    - Compose world-frame offsets        │
│    - Apply listening freeze             │
├─────────────────────────────────────────┤
│ 6. Robot Command (~2ms)                 │
│    - Send set_target() to robot         │
├─────────────────────────────────────────┤
│ 7. Sleep (~6ms)                         │
│    - Wait for next 10ms tick            │
└─────────────────────────────────────────┘
Total: ~10ms (100Hz maintained)
```

**Critical Insight:** Only ONE `set_target()` call per tick. All motion layers compose BEFORE sending to robot.

## Audio-Reactive Motion (HeadWobbler)

### The Challenge: Latency Compensation

**Problem:** Audio playback has ~80ms latency from generation to speaker output. If robot motion is generated from the same audio stream, it will appear to lag behind the sound.

**Solution:** Buffer motion offsets with timestamps, apply 80ms in the future.

### Audio Processing Pipeline

```
OpenAI Audio Delta (24kHz PCM16)
    │
    ├─► Speaker (plays with 80ms latency)
    │
    └─► HeadWobbler
        │
        ├─► Extract Envelope
        │   └─ envelope = abs(audio_samples)
        │
        ├─► Map to Angle
        │   └─ target_angle = (envelope / 32768) * sensitivity
        │
        ├─► Smooth Approach
        │   └─ current += (target - current) * damping
        │
        └─► Buffer with Timestamp
            └─ buffer.append((time.now() + 0.08, offset))
                │
                ▼
        MovementManager (reads at 100Hz)
            │
            └─► Get offset for current timestamp
                └─ Returns offset if timestamp ≤ now
```

### Why This Works

```python
# At t=0.000s: Audio delta arrives
audio_delta = b'\x00\x10\x20...'  # Loud sound

# HeadWobbler processes immediately
envelope = np.abs(audio_delta)
target_angle = 15.0  # degrees

# Buffer with future timestamp
offset_buffer.append((t=0.080, {"head_rotation": 15.0}))

# At t=0.080s: MovementManager checks buffer
current_offset = wobbler.get_offset()  # Returns 15.0 degrees
# At exactly the same time: speaker outputs the loud sound

# Result: Head wobble synchronized with perceived audio!
```

### Tuning Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| `sensitivity` | 30.0 | Max wobble angle (degrees) |
| `damping` | 0.3 | Smoothing factor (0=instant, 1=no motion) |
| `latency_compensation` | 0.08 | Buffer delay (seconds) |

**Experimental tuning:**
```python
# More exaggerated motion
sensitivity = 45.0, damping = 0.5

# Subtle motion
sensitivity = 15.0, damping = 0.2

# Sync adjustment
latency_compensation = measured_latency  # Use actual audio pipeline delay
```

## Face Tracking Offsets

### Coordinate Frame Transformations

```
Camera Pixel (x, y)
    │
    ├─► Bounding Box Detection (YOLO/MediaPipe)
    │   └─ bbox = (x1, y1, x2, y2)
    │
    ├─► Center Point
    │   └─ center = ((x1+x2)/2, (y1+y2)/2)
    │
    ├─► Unproject to 3D (camera intrinsics)
    │   └─ face_pos_3d = camera_matrix⁻¹ · [x, y, estimated_depth]
    │
    ├─► Transform to Robot Frame
    │   └─ face_in_robot = T_camera_to_robot · face_pos_3d
    │
    ├─► Compute Look-At IK
    │   └─ look_at_pose = robot.compute_ik(target=face_in_robot)
    │
    └─► Extract Offset
        └─ offset = look_at_pose ⊖ current_pose
            │
            ▼
    MovementManager applies offset
```

### Smooth Face Loss Handling

**Problem:** Face detection is noisy. Faces disappear when turning, blinking, etc.

**Solution:** Exponential decay of tracking offset.

```python
# When face detected
if face_bbox:
    target_offset = compute_offset(face_bbox)
    current_offset = lerp(current_offset, target_offset, alpha=0.3)

# When face lost
else:
    current_offset *= 0.9  # Decay toward zero

    if abs(current_offset) < 0.1:
        current_offset = 0.0  # Snap to zero when small
```

**Effect:**
- Face detected: Smooth approach to target
- Face lost: Gradual return to center (not instant snap)
- Multiple frames to stabilize tracking

### Performance Optimization

```python
# CameraWorker runs at 30Hz (33ms budget)
def _tracking_loop(self):
    target_dt = 1.0 / 30.0

    while self._running:
        start_time = time.time()

        # 1. Capture frame (~5ms)
        frame = self._cap.read()

        # 2. Face detection (~15ms with YOLO, ~20ms with MediaPipe)
        detections = self._tracker.detect(frame)

        # 3. Compute offset (~2ms)
        if detections:
            offset = self._compute_face_offset(detections[0])
            self._update_offset(offset)

        # 4. Sleep for remainder (~11ms)
        elapsed = time.time() - start_time
        time.sleep(max(0, target_dt - elapsed))
```

**Typical Timing:**
- YOLO: 20-25ms per frame (achieves 35-40 fps)
- MediaPipe: 25-30ms per frame (achieves 30-33 fps)

## Breathing Idle Animation

### Purpose

When robot is inactive (no moves in queue, no conversation), it should appear "alive" through subtle breathing motion.

### Implementation

```python
class BreathingMove:
    def __init__(self):
        self.frames_per_cycle = 200  # 2 seconds at 100Hz
        self.amplitude = 5.0  # degrees

    def get_pose(self, frame: int) -> dict:
        # Sinusoidal breathing
        phase = (frame % self.frames_per_cycle) / self.frames_per_cycle
        angle = math.sin(phase * 2 * math.pi) * self.amplitude

        return {
            "neck_pitch": angle,
            "l_antenna": angle * 0.5,
            "r_antenna": -angle * 0.5,
        }

    def is_complete(self) -> bool:
        return False  # Infinite loop
```

### Activation Logic

```python
def _should_start_breathing(self):
    # Don't start if already breathing
    if self._is_currently_breathing():
        return False

    # Don't start if moves in queue
    if not self._primary_queue.is_empty():
        return False

    # Start if idle for 30 seconds
    idle_duration = time.time() - self._last_activity_time
    return idle_duration > 30.0

def _start_breathing(self):
    # Preserve current pose as starting point
    current_pose = self._last_cached_pose

    # Create breathing move that starts from current pose
    breathing = BreathingMove(base_pose=current_pose)

    # Add to queue
    self._primary_queue.add(breathing)
```

**Subtlety:** Breathing starts from whatever pose the robot ended in, not a hardcoded "home" pose. This prevents jarring transitions.

## Listening Freeze (Antenna Behavior)

### Motivation

When user is speaking, robot should appear attentive. Freezing antennas simulates "ears perked up, listening."

### Implementation

```python
def _apply_listening_freeze(self, pose: dict) -> dict:
    if not self._listening:
        return pose  # No modification

    # Freeze antennas at current position
    frozen_pose = pose.copy()
    frozen_pose["l_antenna"] = self._frozen_antenna_l
    frozen_pose["r_antenna"] = self._frozen_antenna_r

    # Blend over time for smooth transition
    if self._freeze_blend < 1.0:
        self._freeze_blend = min(1.0, self._freeze_blend + 0.05)  # 1 second blend

        # Lerp between moving and frozen
        frozen_pose["l_antenna"] = lerp(
            pose["l_antenna"],
            self._frozen_antenna_l,
            self._freeze_blend
        )
        frozen_pose["r_antenna"] = lerp(
            pose["r_antenna"],
            self._frozen_antenna_r,
            self._freeze_blend
        )

    return frozen_pose
```

**Effect:** Antennas smoothly transition to frozen position over ~1 second, remain still during user speech, then smoothly blend back to motion.

---

## Insights & Observations

### What Makes This Architecture Powerful

1. **Composability:** New secondary behaviors add without touching existing code
2. **Frame-agnostic:** Primary moves are frame-based, secondary are real-time
3. **Synchronization:** Audio-visual sync through latency compensation
4. **Smoothness:** All transitions are blended, no discontinuities

### Potential Improvements

1. **Multi-priority queues:** Allow interrupt-able vs non-interruptable moves
2. **Blend transitions:** Cross-fade between primary moves instead of instant switch
3. **Dynamic frequency:** Adapt control loop rate based on motion complexity
4. **Predictive tracking:** Use face velocity for smoother tracking

### Lessons for Other Robotics Projects

- **Separation of concerns:** Primary vs secondary motion layers
- **Timing guarantees:** 100Hz control loop is hard requirement
- **Latency matters:** Audio-visual sync makes or breaks perceived quality
- **Graceful degradation:** When face lost, smooth return (not instant)

This motion system is the **heart** of what makes Reachy Mini feel alive and responsive.
