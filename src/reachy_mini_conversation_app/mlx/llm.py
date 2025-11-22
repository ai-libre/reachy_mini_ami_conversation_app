"""LLM wrapper for MLX-based language models.

Provides a clean interface to mlx-lm with:
- Model loading and caching
- Text generation (blocking and streaming)
- Function calling support
- Prompt caching for performance
"""

import json
import logging
from typing import Any, Optional, Iterator, Dict, List

from mlx_lm import load, generate, stream_generate
from mlx_lm.models.cache import make_prompt_cache


logger = logging.getLogger(__name__)


class MLXLanguageModel:
    """Wrapper for MLX-LM language models.

    Handles model loading, generation, and function calling.

    Example:
        >>> llm = MLXLanguageModel("mlx-community/Hermes-2-Pro-Llama-3-8B-4bit")
        >>> llm.load()
        >>> response = llm.generate("Hello, world!")
        >>> print(response)
    """

    def __init__(
        self,
        model_path: str,
        use_cache: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """Initialize LLM wrapper.

        Args:
            model_path: HuggingFace model path or local path
            use_cache: Enable prompt caching (faster repeated prompts)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        """
        self.model_path = model_path
        self.use_cache = use_cache
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Model components (loaded in load())
        self.model: Optional[Any] = None
        self.tokenizer: Optional[Any] = None
        self.prompt_cache: Optional[Any] = None

        # Conversation history
        self.messages: List[Dict[str, str]] = []

        self._loaded = False

    def load(self) -> None:
        """Load model and tokenizer.

        Downloads model if not cached locally.
        Creates prompt cache if enabled.

        Raises:
            RuntimeError: If model loading fails
        """
        if self._loaded:
            logger.warning("Model already loaded, skipping...")
            return

        logger.info(f"Loading LLM: {self.model_path}")
        logger.info("This may take a few minutes on first run (downloading model)...")

        try:
            self.model, self.tokenizer = load(self.model_path)

            if self.use_cache:
                self.prompt_cache = make_prompt_cache(self.model)
                logger.debug("Prompt cache enabled")

            self._loaded = True
            logger.info("✅ LLM loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            raise RuntimeError(f"LLM loading failed: {e}") from e

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded

    def apply_chat_template(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Apply chat template to messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions for function calling

        Returns:
            Formatted prompt string

        Example:
            >>> messages = [{"role": "user", "content": "Hello!"}]
            >>> prompt = llm.apply_chat_template(messages)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        kwargs = {
            "add_generation_prompt": True,
            "tokenize": False,  # Return string, not tokens
        }

        if tools:
            kwargs["tools"] = tools

        return self.tokenizer.apply_chat_template(messages, **kwargs)

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        verbose: bool = False,
    ) -> str:
        """Generate text (blocking).

        Args:
            prompt: Input prompt (use apply_chat_template for conversations)
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            verbose: Print generation progress

        Returns:
            Generated text

        Example:
            >>> response = llm.generate("Hello!", max_tokens=50)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        return generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens or self.max_tokens,
            temp=temperature or self.temperature,
            verbose=verbose,
            prompt_cache=self.prompt_cache if self.use_cache else None,
        )

    def stream_generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Iterator[Any]:
        """Generate text (streaming).

        Yields tokens as they are generated (lower perceived latency).

        Args:
            prompt: Input prompt
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Yields:
            Generation response objects with .text attribute

        Example:
            >>> for chunk in llm.stream_generate("Hello!"):
            ...     print(chunk.text, end="", flush=True)
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        yield from stream_generate(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens or self.max_tokens,
            temp=temperature or self.temperature,
            verbose=False,
            prompt_cache=self.prompt_cache if self.use_cache else None,
        )

    def parse_function_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse function call from model response.

        Hermes-2-Pro format:
            <tool_call>
            {"name": "function_name", "arguments": {...}}
            </tool_call>

        Args:
            response: Model response text

        Returns:
            Dict with 'name' and 'arguments', or None if no function call

        Example:
            >>> response = llm.generate(prompt_with_tools)
            >>> tool_call = llm.parse_function_call(response)
            >>> if tool_call:
            ...     result = execute_tool(tool_call['name'], **tool_call['arguments'])
        """
        tool_open = "<tool_call>"
        tool_close = "</tool_call>"

        if tool_open not in response or tool_close not in response:
            return None

        try:
            start = response.find(tool_open) + len(tool_open)
            end = response.find(tool_close)
            tool_json = response[start:end].strip()

            tool_call = json.loads(tool_json)

            if "name" in tool_call and "arguments" in tool_call:
                return tool_call
            else:
                logger.warning(f"Invalid tool call format: {tool_call}")
                return None

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tool call: {e}")
            return None

    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history.

        Args:
            role: Message role ('system', 'user', 'assistant', 'tool')
            content: Message content

        Example:
            >>> llm.add_message("system", "You are a helpful assistant.")
            >>> llm.add_message("user", "Hello!")
        """
        self.messages.append({"role": role, "content": content})

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.messages.copy()

    def __repr__(self) -> str:
        """String representation."""
        status = "loaded" if self._loaded else "not loaded"
        return f"MLXLanguageModel(model={self.model_path}, status={status})"
