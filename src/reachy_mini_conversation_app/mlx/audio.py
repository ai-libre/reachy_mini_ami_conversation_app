"""Audio processing module for MLX-based STT and TTS.

Provides wrappers around mlx-audio for:
- Speech-to-Text (Whisper)
- Text-to-Speech (Kokoro-82M)
- Voice Activity Detection (for turn detection)

Designed for real-time conversation with buffering and streaming.
"""

import logging
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional, Iterator, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import mlx-audio - will be None if not installed
try:
    from mlx_audio.stt.generate import generate as stt_generate
    from mlx_audio.stt.utils import load_model as load_stt_model
    from mlx_audio.tts.models.kokoro import KokoroPipeline
    from mlx_audio.tts.utils import load_model as load_tts_model
    import soundfile as sf
    MLX_AUDIO_AVAILABLE = True
except ImportError:
    stt_generate = None  # type: ignore[assignment]
    load_stt_model = None  # type: ignore[assignment]
    KokoroPipeline = None  # type: ignore[assignment]
    load_tts_model = None  # type: ignore[assignment]
    sf = None  # type: ignore[assignment]
    MLX_AUDIO_AVAILABLE = False
    logger.debug("mlx-audio not available (not installed)")


@dataclass
class AudioSegment:
    """A segment of audio with text and timing."""

    text: str
    start: float
    end: float
    duration: float


class STTProcessor:
    """Speech-to-Text processor using mlx-audio.

    Example:
        >>> stt = STTProcessor()
        >>> stt.load()
        >>> text = stt.transcribe_audio(audio_array, sample_rate=16000)
        >>> print(text)
        "Hello, how are you?"
    """

    def __init__(
        self,
        model_path: str = "mlx-community/whisper-large-v3-turbo",
        max_tokens: int = 128,
    ):
        """Initialize STT processor.

        Args:
            model_path: HuggingFace model path or local path
            max_tokens: Maximum tokens to generate
        """
        if not MLX_AUDIO_AVAILABLE:
            raise ImportError(
                "mlx-audio not installed. Install with: pip install mlx-audio"
            )

        self.model_path = model_path
        self.max_tokens = max_tokens
        self.model = None
        self.temp_dir = Path(tempfile.gettempdir()) / "mlx_audio_stt"
        self.temp_dir.mkdir(exist_ok=True)

        logger.info(f"STT Processor initialized: {model_path}")

    def load(self) -> None:
        """Load the STT model."""
        logger.info(f"Loading STT model: {self.model_path}")
        self.model = load_stt_model(self.model_path)
        logger.info("✅ STT model loaded")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None

    def transcribe_audio(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        verbose: bool = False,
    ) -> str:
        """Transcribe audio array to text.

        Args:
            audio: Audio array (int16 or float32)
            sample_rate: Sample rate of audio
            verbose: Print transcription progress

        Returns:
            Transcribed text

        Note:
            This saves audio to a temp file, as mlx-audio expects file paths.
            For real-time streaming, buffer audio until speech end detected.
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load() first.")

        # Save audio to temp file
        temp_file = self.temp_dir / f"audio_{id(audio)}.wav"
        try:
            # Convert to float32 if needed
            if audio.dtype == np.int16:
                audio_float = audio.astype(np.float32) / 32768.0
            else:
                audio_float = audio

            # Ensure mono
            if len(audio_float.shape) > 1:
                audio_float = audio_float.mean(axis=0)

            # Save to WAV file
            sf.write(str(temp_file), audio_float, sample_rate)

            # Generate transcription
            temp_output = self.temp_dir / f"output_{id(audio)}"
            segments = stt_generate(
                model=self.model,
                audio_path=str(temp_file),
                output_path=str(temp_output),
                format="json",
                verbose=verbose,
                max_tokens=self.max_tokens,
            )

            # Extract text
            text = segments.text.strip() if hasattr(segments, "text") else ""
            return text

        finally:
            # Cleanup temp files
            if temp_file.exists():
                temp_file.unlink()
            for ext in [".txt", ".json", ".srt", ".vtt"]:
                output_file = Path(str(temp_output) + ext)
                if output_file.exists():
                    output_file.unlink()

    def __repr__(self) -> str:
        """String representation."""
        status = "loaded" if self.is_loaded() else "not loaded"
        return f"STTProcessor(model={self.model_path}, status={status})"


class TTSProcessor:
    """Text-to-Speech processor using mlx-audio Kokoro.

    Example:
        >>> tts = TTSProcessor(voice="af_heart")
        >>> tts.load()
        >>> audio = tts.synthesize("Hello, world!")
        >>> # audio is numpy array at 24000 Hz
    """

    def __init__(
        self,
        model_path: str = "prince-canuma/Kokoro-82M",
        voice: str = "af_heart",
        speed: float = 1.0,
        lang_code: str = "a",
        sample_rate: int = 24000,
    ):
        """Initialize TTS processor.

        Args:
            model_path: HuggingFace model path or local path
            voice: Voice preset (af_heart, af_nova, bf_emma, etc.)
            speed: Speech speed multiplier (0.5 to 2.0)
            lang_code: Language code (a=American, b=British)
            sample_rate: Output sample rate (default 24000 Hz)
        """
        if not MLX_AUDIO_AVAILABLE:
            raise ImportError(
                "mlx-audio not installed. Install with: pip install mlx-audio"
            )

        self.model_path = model_path
        self.voice = voice
        self.speed = speed
        self.lang_code = lang_code
        self.sample_rate = sample_rate
        self.model = None
        self.pipeline = None

        logger.info(
            f"TTS Processor initialized: {model_path} (voice={voice}, speed={speed})"
        )

    def load(self) -> None:
        """Load the TTS model and create pipeline."""
        logger.info(f"Loading TTS model: {self.model_path}")
        self.model = load_tts_model(self.model_path)
        self.pipeline = KokoroPipeline(
            lang_code=self.lang_code, model=self.model, repo_id=self.model_path
        )
        logger.info("✅ TTS model loaded")

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None and self.pipeline is not None

    def synthesize(self, text: str, split_pattern: str = r"\n+") -> np.ndarray:
        """Synthesize text to audio.

        Args:
            text: Text to synthesize
            split_pattern: Regex pattern to split text into chunks

        Returns:
            Audio array (float32) at self.sample_rate

        Note:
            Returns combined audio from all chunks.
            For streaming, use synthesize_streaming() instead.
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load() first.")

        audio_chunks = []
        for _, _, audio in self.pipeline(
            text, voice=self.voice, speed=self.speed, split_pattern=split_pattern
        ):
            # audio is [1, n_samples] or [n_samples]
            if len(audio.shape) > 1:
                audio = audio[0]  # Get first channel (mono)
            audio_chunks.append(audio)

        # Concatenate all chunks
        if not audio_chunks:
            return np.array([], dtype=np.float32)

        combined_audio = np.concatenate(audio_chunks)
        return combined_audio

    def synthesize_streaming(
        self, text: str, split_pattern: str = r"\n+"
    ) -> Iterator[np.ndarray]:
        """Synthesize text to audio with streaming chunks.

        Args:
            text: Text to synthesize
            split_pattern: Regex pattern to split text into chunks

        Yields:
            Audio chunks (float32) at self.sample_rate

        Example:
            >>> for chunk in tts.synthesize_streaming("Hello, world!"):
            ...     # Play or queue chunk
            ...     play_audio(chunk, sample_rate=24000)
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load() first.")

        for _, _, audio in self.pipeline(
            text, voice=self.voice, speed=self.speed, split_pattern=split_pattern
        ):
            # audio is [1, n_samples] or [n_samples]
            if len(audio.shape) > 1:
                audio = audio[0]  # Get first channel (mono)
            yield audio

    def __repr__(self) -> str:
        """String representation."""
        status = "loaded" if self.is_loaded() else "not loaded"
        return f"TTSProcessor(model={self.model_path}, voice={self.voice}, status={status})"


class SimpleVAD:
    """Simple Voice Activity Detection using energy threshold.

    This is a basic VAD for Sprint 2. In Sprint 3, consider using
    a more sophisticated VAD like Silero VAD or WebRTC VAD.

    Example:
        >>> vad = SimpleVAD(threshold=0.01)
        >>> is_speech = vad.is_speech(audio_chunk)
        >>> if is_speech:
        ...     buffer.append(audio_chunk)
    """

    def __init__(
        self,
        threshold: float = 0.01,
        min_speech_duration: float = 0.3,
        min_silence_duration: float = 0.5,
        sample_rate: int = 16000,
    ):
        """Initialize VAD.

        Args:
            threshold: Energy threshold for speech detection
            min_speech_duration: Minimum speech duration in seconds
            min_silence_duration: Minimum silence to end speech in seconds
            sample_rate: Audio sample rate
        """
        self.threshold = threshold
        self.min_speech_frames = int(min_speech_duration * sample_rate / 160)  # 10ms frames
        self.min_silence_frames = int(min_silence_duration * sample_rate / 160)
        self.sample_rate = sample_rate

        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False

        logger.info(f"VAD initialized: threshold={threshold}")

    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio contains speech.

        Args:
            audio: Audio chunk (int16 or float32)

        Returns:
            True if speech detected
        """
        # Convert to float32 if needed
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0

        # Calculate energy
        energy = np.mean(np.abs(audio))

        # Update counters
        if energy > self.threshold:
            self.speech_frames += 1
            self.silence_frames = 0
        else:
            self.silence_frames += 1

        # State machine
        if not self.is_speaking:
            # Check if speech started
            if self.speech_frames >= self.min_speech_frames:
                self.is_speaking = True
                logger.debug("Speech started")
                return True
        else:
            # Check if speech ended
            if self.silence_frames >= self.min_silence_frames:
                self.is_speaking = False
                self.speech_frames = 0
                logger.debug("Speech ended")
                return False
            return True

        return self.is_speaking

    def reset(self):
        """Reset VAD state."""
        self.speech_frames = 0
        self.silence_frames = 0
        self.is_speaking = False
