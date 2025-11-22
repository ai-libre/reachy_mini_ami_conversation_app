"""MLX-based realtime handler for local LLM processing.

This handler replaces OpenAI Realtime API with local MLX models:
- LLM: mlx-lm (Hermes-2-Pro-8B with function calling)
- Audio: mlx-audio (STT + TTS) - Sprint 2
- Vision: mlx-vlm (SmolVLM) - Sprint 3

Implements AsyncStreamHandler interface for fastrtc compatibility.
"""

import logging
import asyncio
from typing import Any, Tuple, Literal
from datetime import datetime

import numpy as np
from fastrtc import AdditionalOutputs, AsyncStreamHandler, wait_for_item
from numpy.typing import NDArray

from reachy_mini_conversation_app.tools.core_tools import (
    ToolDependencies,
    get_tool_specs,
)
from reachy_mini_conversation_app.mlx import (
    MLXConfig,
    detect_backend,
    get_memory_info,
    ConversationState,
    ConversationStateMachine,
)
from reachy_mini_conversation_app.mlx.llm import MLXLanguageModel


logger = logging.getLogger(__name__)


class MLXRealtimeHandler(AsyncStreamHandler):
    """MLX-based realtime handler for local LLM processing.

    Sprint 1: Foundation (Current)
    - Basic handler structure
    - LLM model loading
    - State machine integration
    - Placeholder audio methods

    Sprint 2: Audio (Next)
    - STT integration
    - TTS integration
    - Full audio pipeline

    Sprint 3: Features
    - Tool calling
    - Vision integration
    - Error handling
    """

    def __init__(
        self,
        deps: ToolDependencies,
        config: MLXConfig | None = None,
    ):
        """Initialize MLX handler.

        Args:
            deps: Tool dependencies (robot control, camera, etc.)
            config: MLX configuration (uses defaults if None)
        """
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,  # Match OpenAI for compatibility
            input_sample_rate=16000,   # Respeaker output
        )
        self.deps = deps
        self.config = config or MLXConfig()

        # Type hints for strict typing
        self.output_sample_rate: Literal[24000]
        self.input_sample_rate: Literal[16000]

        # Audio queue (same interface as OpenAI handler)
        self.output_queue: "asyncio.Queue[Tuple[int, NDArray[np.int16]] | AdditionalOutputs]" = asyncio.Queue()

        # MLX components (loaded in start_up)
        self.llm: MLXLanguageModel | None = None
        # TODO Sprint 2: Add STT and TTS models
        # self.stt: MLXAudioProcessor | None = None
        # self.tts: MLXAudioProcessor | None = None

        # State machine
        self.state_machine = ConversationStateMachine(
            initial_state=ConversationState.IDLE,
            on_transition=self._on_state_transition,
        )

        # Timing
        self.last_activity_time = asyncio.get_event_loop().time()
        self.start_time = asyncio.get_event_loop().time()

        logger.info("MLXRealtimeHandler initialized")

    def copy(self) -> "MLXRealtimeHandler":
        """Create a copy of the handler.

        Required by fastrtc for stream management.
        """
        return MLXRealtimeHandler(self.deps, self.config)

    async def start_up(self) -> None:
        """Start the handler and load MLX models.

        This is called once when the stream starts.
        Loads LLM model and initializes audio processors.
        """
        logger.info("=" * 60)
        logger.info("MLX Handler Starting Up")
        logger.info("=" * 60)

        # Detect and log hardware backend
        backend = detect_backend()
        logger.info(f"MLX Backend: {backend.value}")

        memory_info = get_memory_info()
        if "active_gb" in memory_info:
            logger.info(
                f"Memory: {memory_info['active_gb']:.2f} GB active, "
                f"{memory_info['peak_gb']:.2f} GB peak"
            )

        # Load LLM model
        logger.info(f"Loading LLM: {self.config.llm_model}")
        self.llm = MLXLanguageModel(
            model_path=self.config.llm_model,
            use_cache=self.config.use_prompt_cache,
            temperature=self.config.llm_temperature,
            max_tokens=self.config.llm_max_tokens,
        )

        try:
            self.llm.load()
            logger.info("✅ LLM loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            raise

        # TODO Sprint 2: Load audio models
        # logger.info("Loading STT and TTS models...")
        # self.stt = load_stt_model(self.config)
        # self.tts = load_tts_model(self.config)

        # Add system message
        system_prompt = self._get_system_prompt()
        self.llm.add_message("system", system_prompt)

        logger.info("=" * 60)
        logger.info("MLX Handler Ready")
        logger.info("=" * 60)

    async def receive(self, frame: Tuple[int, NDArray[np.int16]]) -> None:
        """Receive audio frame from microphone.

        Sprint 1: Placeholder (no processing)
        Sprint 2: Will implement STT processing

        Args:
            frame: (sample_rate, audio_array) from microphone
        """
        # TODO Sprint 2: Implement STT processing
        # For now, just log that we're receiving audio
        _, array = frame
        logger.debug(f"Received audio frame: {array.shape}")

        # Update state to LISTENING if we detect audio
        # (In Sprint 2, we'll use VAD here)
        if self.state_machine.current_state == ConversationState.IDLE:
            self.state_machine.transition_to(
                ConversationState.LISTENING,
                "Audio input detected"
            )

    async def emit(self) -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None:
        """Emit audio frame to speaker.

        Sprint 1: Returns silence (placeholder)
        Sprint 2: Will return TTS output

        Returns:
            Audio frame or metadata for the stream
        """
        # TODO Sprint 2: Return actual TTS audio
        # For now, return items from queue or None
        return await wait_for_item(self.output_queue)  # type: ignore[no-any-return]

    async def shutdown(self) -> None:
        """Shutdown the handler and cleanup resources."""
        logger.info("Shutting down MLX handler...")

        # Reset state
        self.state_machine.reset()

        # Clear models (free memory)
        self.llm = None
        # TODO Sprint 2: Clear audio models
        # self.stt = None
        # self.tts = None

        # Clear output queue
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("MLX handler shutdown complete")

    def _on_state_transition(self, transition: Any) -> None:
        """Callback for state transitions.

        Used for logging and triggering side effects.

        Args:
            transition: StateTransition object
        """
        logger.info(
            f"State: {transition.from_state.name} → {transition.to_state.name} "
            f"({transition.reason})"
        )

        # Update movement manager based on state
        if transition.to_state == ConversationState.LISTENING:
            self.deps.movement_manager.set_listening(True)
        else:
            self.deps.movement_manager.set_listening(False)

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM.

        Returns:
            System prompt string
        """
        # TODO: Use prompts.get_session_instructions() or similar
        # For now, simple prompt
        return (
            "You are a helpful AI assistant running on a Reachy Mini robot. "
            "You have access to tools for controlling the robot. "
            "Be concise and friendly in your responses."
        )

    def format_timestamp(self) -> str:
        """Format current timestamp with date, time, and elapsed seconds.

        Returns:
            Formatted timestamp string
        """
        loop_time = asyncio.get_event_loop().time()
        elapsed_seconds = loop_time - self.start_time
        dt = datetime.now()
        return f"[{dt.strftime('%Y-%m-%d %H:%M:%S')} | +{elapsed_seconds:.1f}s]"
