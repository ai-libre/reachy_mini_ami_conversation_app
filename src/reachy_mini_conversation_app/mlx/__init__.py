"""MLX integration module for local LLM/VLM processing.

This module provides MLX-based alternatives to cloud API processing:
- LLM: mlx-lm (language models with function calling)
- VLM: mlx-vlm (vision-language models)
- Audio: mlx-audio (STT + TTS)

Auto-detects hardware backend:
- Metal (Apple Silicon)
- CUDA (NVIDIA GPUs)
- CPU (fallback)
"""

from .hardware import detect_backend, get_memory_info, MLXBackend
from .config import MLXConfig
from .state import ConversationState, ConversationStateMachine, StateTransition

# Audio components - may not be available if mlx-audio not installed
try:
    from .audio import STTProcessor, TTSProcessor, SimpleVAD, AudioSegment
    _audio_available = True
except ImportError:
    STTProcessor = None  # type: ignore[assignment, misc]
    TTSProcessor = None  # type: ignore[assignment, misc]
    SimpleVAD = None  # type: ignore[assignment, misc]
    AudioSegment = None  # type: ignore[assignment, misc]
    _audio_available = False

__all__ = [
    "detect_backend",
    "get_memory_info",
    "MLXBackend",
    "MLXConfig",
    "ConversationState",
    "ConversationStateMachine",
    "StateTransition",
    "STTProcessor",
    "TTSProcessor",
    "SimpleVAD",
    "AudioSegment",
]
