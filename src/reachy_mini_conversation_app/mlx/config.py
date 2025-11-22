"""Configuration for MLX-based local LLM processing.

Provides centralized configuration with environment variable overrides.
All settings can be customized via environment variables with MLX_ prefix.
"""

import os
import logging
from dataclasses import dataclass
from typing import Literal


logger = logging.getLogger(__name__)


@dataclass
class MLXConfig:
    """Configuration for MLX-based local LLM processing.

    All fields can be overridden via environment variables:
    - MLX_LLM_MODEL: Language model path
    - MLX_LLM_TEMPERATURE: Sampling temperature (0.0-1.0)
    - MLX_LLM_MAX_TOKENS: Maximum tokens to generate
    - MLX_VLM_MODEL: Vision-language model path
    - MLX_TTS_MODEL: Text-to-speech model path
    - MLX_TTS_VOICE: TTS voice name
    - MLX_TTS_SPEED: TTS speed multiplier
    - MLX_TTS_LANG_CODE: TTS language code
    - MLX_USE_PROMPT_CACHE: Enable prompt caching (true/false)
    - MLX_ENABLE_STREAMING: Enable streaming generation (true/false)
    - MLX_DEVICE: Hardware device (auto/metal/cuda/cpu)

    Example:
        >>> config = MLXConfig()
        >>> print(config.llm_model)
        mlx-community/Hermes-2-Pro-Llama-3-8B-4bit

        >>> os.environ["MLX_LLM_MODEL"] = "custom-model"
        >>> config = MLXConfig()
        >>> print(config.llm_model)
        custom-model
    """

    # ========================================
    # LLM Configuration
    # ========================================
    llm_model: str = "mlx-community/Hermes-2-Pro-Llama-3-8B-4bit"
    """Language model path (HuggingFace or local).

    Recommended models:
    - Hermes-2-Pro-Llama-3-8B-4bit (function calling, 4.5GB)
    - Qwen2.5-3B-Instruct-4bit (smaller, faster, 2GB)
    - Llama-3.2-3B-Instruct-4bit (good balance, 2.5GB)
    """

    llm_temperature: float = 0.7
    """Sampling temperature for LLM (0.0 = deterministic, 1.0 = creative)."""

    llm_max_tokens: int = 500
    """Maximum tokens to generate per response."""

    # ========================================
    # VLM Configuration
    # ========================================
    vlm_model: str = "mlx-community/SmolVLM-Instruct-4bit"
    """Vision-language model path.

    Recommended models:
    - SmolVLM-Instruct-4bit (best quality, 1.5GB)
    - SmolVLM-2.2B-4bit (alias for above)
    """

    # ========================================
    # Audio Configuration
    # ========================================
    tts_model: str = "prince-canuma/Kokoro-82M"
    """Text-to-speech model path.

    Kokoro-82M: High-quality, fast, 82M parameters
    """

    tts_voice: str = "af_heart"
    """TTS voice name.

    Kokoro voices:
    - af_heart: American Female (warm, friendly)
    - am_adam: American Male (neutral)
    - bf_emma: British Female (professional)
    - bm_lewis: British Male (deep)
    """

    tts_speed: float = 1.0
    """TTS speed multiplier (0.5 = slower, 2.0 = faster)."""

    tts_lang_code: str = "a"
    """TTS language code.

    Kokoro codes:
    - a: American English
    - b: British English
    """

    # ========================================
    # Performance Configuration
    # ========================================
    use_prompt_cache: bool = True
    """Enable prompt caching for faster repeated prompts."""

    enable_streaming: bool = True
    """Enable streaming generation (lower perceived latency)."""

    device: Literal["auto", "metal", "cuda", "cpu"] = "auto"
    """Hardware device to use.

    - auto: Auto-detect best available
    - metal: Force Apple Silicon GPU
    - cuda: Force NVIDIA GPU
    - cpu: Force CPU (slow)
    """

    # ========================================
    # Hardware Thresholds
    # ========================================
    max_memory_gb: float = 16.0
    """Maximum memory usage in GB (warning threshold)."""

    def __post_init__(self):
        """Apply environment variable overrides."""
        # LLM
        self.llm_model = os.getenv("MLX_LLM_MODEL", self.llm_model)
        self.llm_temperature = float(os.getenv("MLX_LLM_TEMPERATURE", self.llm_temperature))
        self.llm_max_tokens = int(os.getenv("MLX_LLM_MAX_TOKENS", self.llm_max_tokens))

        # VLM
        self.vlm_model = os.getenv("MLX_VLM_MODEL", self.vlm_model)

        # TTS
        self.tts_model = os.getenv("MLX_TTS_MODEL", self.tts_model)
        self.tts_voice = os.getenv("MLX_TTS_VOICE", self.tts_voice)
        self.tts_speed = float(os.getenv("MLX_TTS_SPEED", self.tts_speed))
        self.tts_lang_code = os.getenv("MLX_TTS_LANG_CODE", self.tts_lang_code)

        # Performance
        use_cache_env = os.getenv("MLX_USE_PROMPT_CACHE", "").lower()
        if use_cache_env in ("true", "1", "yes"):
            self.use_prompt_cache = True
        elif use_cache_env in ("false", "0", "no"):
            self.use_prompt_cache = False

        enable_stream_env = os.getenv("MLX_ENABLE_STREAMING", "").lower()
        if enable_stream_env in ("true", "1", "yes"):
            self.enable_streaming = True
        elif enable_stream_env in ("false", "0", "no"):
            self.enable_streaming = False

        device_env = os.getenv("MLX_DEVICE", "").lower()
        if device_env in ("auto", "metal", "cuda", "cpu"):
            self.device = device_env  # type: ignore[assignment]

        # Log configuration
        self._log_config()

    def _log_config(self):
        """Log configuration summary."""
        logger.info("MLX Configuration:")
        logger.info(f"  LLM Model: {self.llm_model}")
        logger.info(f"  VLM Model: {self.vlm_model}")
        logger.info(f"  TTS Model: {self.tts_model}")
        logger.info(f"  TTS Voice: {self.tts_voice}")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Prompt Cache: {self.use_prompt_cache}")
        logger.info(f"  Streaming: {self.enable_streaming}")
