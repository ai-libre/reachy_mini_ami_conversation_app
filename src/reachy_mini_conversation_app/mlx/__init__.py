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

__all__ = [
    "detect_backend",
    "get_memory_info",
    "MLXBackend",
    "MLXConfig",
    "ConversationState",
    "ConversationStateMachine",
    "StateTransition",
]
