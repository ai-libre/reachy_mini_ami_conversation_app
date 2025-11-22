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
    STTProcessor,
    TTSProcessor,
    SimpleVAD,
)
from reachy_mini_conversation_app.mlx.llm import MLXLanguageModel


logger = logging.getLogger(__name__)


class MLXRealtimeHandler(AsyncStreamHandler):
    """MLX-based realtime handler for local LLM processing.

    Sprint 1: Foundation ✅
    - Basic handler structure
    - LLM model loading
    - State machine integration

    Sprint 2: Audio ✅ (Current)
    - STT integration (Whisper)
    - TTS integration (Kokoro-82M)
    - VAD for turn detection
    - Full conversation pipeline

    Sprint 3: Features (Next)
    - Tool calling integration
    - Vision integration (SmolVLM)
    - Advanced error handling
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
        self.stt: STTProcessor | None = None
        self.tts: TTSProcessor | None = None
        self.vad: SimpleVAD | None = None

        # Audio buffering for STT
        self.audio_buffer: list[NDArray[np.int16]] = []
        self.is_recording = False

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

        # Load audio models
        logger.info("Loading STT model...")
        self.stt = STTProcessor()
        try:
            self.stt.load()
            logger.info("✅ STT loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load STT: {e}")
            raise

        logger.info(f"Loading TTS model: {self.config.tts_model}")
        self.tts = TTSProcessor(
            model_path=self.config.tts_model,
            voice=self.config.tts_voice,
            speed=self.config.tts_speed,
            lang_code=self.config.tts_lang_code,
            sample_rate=self.output_sample_rate,
        )
        try:
            self.tts.load()
            logger.info("✅ TTS loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load TTS: {e}")
            raise

        # Initialize VAD
        self.vad = SimpleVAD(sample_rate=self.input_sample_rate)
        logger.info("✅ VAD initialized")

        # Add system message
        system_prompt = self._get_system_prompt()
        self.llm.add_message("system", system_prompt)

        logger.info("=" * 60)
        logger.info("MLX Handler Ready")
        logger.info("=" * 60)

    async def receive(self, frame: Tuple[int, NDArray[np.int16]]) -> None:
        """Receive audio frame from microphone and process with STT.

        Pipeline:
        1. Use VAD to detect speech
        2. Buffer audio while speaking
        3. When speech ends, transcribe buffer
        4. Send transcription to LLM
        5. Generate TTS response

        Args:
            frame: (sample_rate, audio_array) from microphone
        """
        _, array = frame

        # Check for speech using VAD
        has_speech = self.vad.is_speech(array)

        if has_speech and not self.is_recording:
            # Speech started
            self.is_recording = True
            self.audio_buffer = [array]
            self.state_machine.transition_to(
                ConversationState.LISTENING, "Speech detected"
            )
            logger.debug("Started recording audio")

        elif has_speech and self.is_recording:
            # Continue recording
            self.audio_buffer.append(array)

        elif not has_speech and self.is_recording:
            # Speech ended - process buffered audio
            self.is_recording = False
            logger.debug(f"Speech ended, processing {len(self.audio_buffer)} frames")

            # Transition to processing state
            self.state_machine.transition_to(
                ConversationState.PROCESSING, "Speech ended, transcribing"
            )

            # Process audio in background task (don't block receive)
            asyncio.create_task(self._process_speech_buffer())

            # Clear buffer
            self.audio_buffer = []

    async def emit(self) -> Tuple[int, NDArray[np.int16]] | AdditionalOutputs | None:
        """Emit audio frame to speaker.

        Sprint 1: Returns silence (placeholder)
        Sprint 2: Will return TTS output

        Returns:
            Audio frame or metadata for the stream
        """
        # Emit items from queue (TTS audio or metadata)
        return await wait_for_item(self.output_queue)  # type: ignore[no-any-return]

    async def _process_speech_buffer(self) -> None:
        """Process buffered speech through STT → LLM → TTS pipeline.

        This is the core conversation loop:
        1. Transcribe audio buffer with STT
        2. Send transcription to LLM
        3. Generate TTS audio from LLM response
        4. Queue audio for playback
        """
        if not self.audio_buffer:
            logger.warning("Empty audio buffer, skipping processing")
            self.state_machine.transition_to(ConversationState.IDLE, "Empty buffer")
            return

        try:
            # Step 1: Transcribe audio (STT)
            logger.info("Transcribing audio...")
            combined_audio = np.concatenate(self.audio_buffer)

            # Run STT in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                None, self.stt.transcribe_audio, combined_audio, self.input_sample_rate
            )

            if not transcription:
                logger.warning("Empty transcription, skipping")
                self.state_machine.transition_to(ConversationState.IDLE, "Empty transcription")
                return

            logger.info(f"User said: {transcription}")

            # Send transcription to UI
            await self.output_queue.put(
                AdditionalOutputs({"role": "user", "content": transcription})
            )

            # Step 2: Generate LLM response
            logger.info("Generating LLM response...")
            self.llm.add_message("user", transcription)

            # Get tools for function calling
            tools = get_tool_specs()

            # Apply chat template with tools
            prompt = self.llm.apply_chat_template(
                messages=self.llm.get_history(),
                tools=tools
            )

            # Generate response in thread pool (blocking)
            response_text = await loop.run_in_executor(
                None, self.llm.generate, prompt
            )

            # TODO Sprint 3: Handle function calls
            # tool_call = self.llm.parse_function_call(response_text)
            # if tool_call:
            #     await self._handle_tool_call(tool_call)
            #     return

            # Add assistant message to history
            self.llm.add_message("assistant", response_text)
            logger.info(f"Assistant response: {response_text}")

            # Send response to UI
            await self.output_queue.put(
                AdditionalOutputs({"role": "assistant", "content": response_text})
            )

            # Step 3: Generate TTS audio
            logger.info("Generating speech...")
            self.state_machine.transition_to(
                ConversationState.SPEAKING, "Generating TTS"
            )

            # Generate TTS in thread pool (blocking)
            audio = await loop.run_in_executor(
                None, self.tts.synthesize, response_text
            )

            # Convert float32 to int16 for output
            audio_int16 = (audio * 32767).astype(np.int16)

            # Queue audio for playback (in chunks if needed)
            chunk_size = 4800  # 200ms at 24kHz
            for i in range(0, len(audio_int16), chunk_size):
                chunk = audio_int16[i:i+chunk_size]
                # Reshape to (1, n_samples) for mono
                chunk_2d = chunk.reshape(1, -1)
                await self.output_queue.put((self.output_sample_rate, chunk_2d))

            # Update timing
            self.last_activity_time = asyncio.get_event_loop().time()

            # Back to idle
            self.state_machine.transition_to(ConversationState.IDLE, "TTS complete")

        except Exception as e:
            logger.error(f"Error in speech processing pipeline: {e}")
            import traceback
            traceback.print_exc()

            # Send error to UI
            await self.output_queue.put(
                AdditionalOutputs({"role": "assistant", "content": f"Error: {str(e)}"})
            )

            # Reset to idle
            self.state_machine.transition_to(ConversationState.IDLE, "Error occurred")

    async def shutdown(self) -> None:
        """Shutdown the handler and cleanup resources."""
        logger.info("Shutting down MLX handler...")

        # Reset state
        self.state_machine.reset()

        # Clear models (free memory)
        self.llm = None
        self.stt = None
        self.tts = None
        self.vad = None

        # Clear audio buffer
        self.audio_buffer = []
        self.is_recording = False

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
