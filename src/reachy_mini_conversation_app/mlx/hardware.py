"""Hardware detection and information for MLX backend.

Automatically detects available MLX backend (Metal, CUDA, or CPU)
and provides memory information for monitoring.
"""

import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Try to import MLX - will be None if not installed
try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    mx = None  # type: ignore[assignment]
    MLX_AVAILABLE = False
    logger.debug("MLX not available (not installed)")


class MLXBackend(Enum):
    """Available MLX hardware backends."""

    METAL = "metal"  # Apple Silicon GPU
    CUDA = "cuda"    # NVIDIA GPU
    CPU = "cpu"      # CPU fallback


def detect_backend() -> MLXBackend:
    """Auto-detect available MLX backend.

    Checks in priority order:
    1. Metal (Apple Silicon) - if available
    2. CUDA (NVIDIA GPU) - if available
    3. CPU - fallback

    Returns:
        MLXBackend enum value

    Example:
        >>> backend = detect_backend()
        >>> print(f"Using: {backend.value}")
        Using: metal
    """
    if not MLX_AVAILABLE or mx is None:
        logger.warning("MLX not available - using CPU fallback")
        return MLXBackend.CPU

    if mx.metal.is_available():
        logger.info("🍎 Metal backend available (Apple Silicon)")
        return MLXBackend.METAL
    elif mx.cuda.is_available():
        logger.info("🟢 CUDA backend available (NVIDIA GPU)")
        return MLXBackend.CUDA
    else:
        logger.info("💻 Using CPU backend (no GPU acceleration)")
        return MLXBackend.CPU


def get_memory_info() -> Dict[str, Any]:
    """Get memory information for detected backend.

    Returns:
        Dictionary with backend type and memory usage:
        - backend: str (metal/cuda/cpu)
        - active_mb: float (if GPU)
        - peak_mb: float (if GPU)

    Example:
        >>> info = get_memory_info()
        >>> print(f"Backend: {info['backend']}")
        >>> print(f"Active memory: {info.get('active_mb', 0):.2f} MB")
    """
    if not MLX_AVAILABLE or mx is None:
        return {"backend": "cpu", "error": "MLX not installed"}

    backend = detect_backend()

    if backend == MLXBackend.METAL:
        try:
            active_bytes = mx.metal.get_active_memory()
            peak_bytes = mx.metal.get_peak_memory()

            return {
                "backend": "metal",
                "active_mb": active_bytes / (1024**2),
                "peak_mb": peak_bytes / (1024**2),
                "active_gb": active_bytes / (1024**3),
                "peak_gb": peak_bytes / (1024**3),
            }
        except Exception as e:
            logger.warning(f"Could not get Metal memory info: {e}")
            return {"backend": "metal", "error": str(e)}

    elif backend == MLXBackend.CUDA:
        try:
            active_bytes = mx.cuda.get_active_memory()
            peak_bytes = mx.cuda.get_peak_memory()

            return {
                "backend": "cuda",
                "active_mb": active_bytes / (1024**2),
                "peak_mb": peak_bytes / (1024**2),
                "active_gb": active_bytes / (1024**3),
                "peak_gb": peak_bytes / (1024**3),
            }
        except Exception as e:
            logger.warning(f"Could not get CUDA memory info: {e}")
            return {"backend": "cuda", "error": str(e)}

    else:
        return {"backend": "cpu"}


def log_hardware_info():
    """Log hardware detection and memory information.

    Useful for debugging and monitoring.
    """
    backend = detect_backend()
    memory_info = get_memory_info()

    logger.info(f"MLX Backend: {backend.value}")

    if "active_gb" in memory_info:
        logger.info(
            f"Memory: {memory_info['active_gb']:.2f} GB active, "
            f"{memory_info['peak_gb']:.2f} GB peak"
        )
