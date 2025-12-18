"""
Rate limiting for robot commands.

Prevents command flooding that could damage hardware or cause safety issues.
"""

import time
from collections import deque
from threading import Lock

from ..config import get_config
from ..utils import RateLimitExceededError, get_logger

logger = get_logger("safety.rate_limiter")


class RateLimiter:
    """
    Token bucket rate limiter for robot commands.

    Limits commands per time window to prevent:
    - Motor overheating
    - Hardware damage from rapid movements
    - Battery drain
    - Unsafe command sequences
    """

    def __init__(self, max_commands_per_minute: int | None = None):
        """
        Initialize rate limiter.

        Args:
            max_commands_per_minute: Maximum commands allowed per minute
                                   (uses config if None)
        """
        config = get_config()
        self.limit = max_commands_per_minute or config.max_commands_per_minute

        self._commands: deque[float] = deque(maxlen=self.limit)
        self._lock = Lock()

        logger.info(f"Rate limiter initialized: {self.limit} commands/minute")

    def check_rate_limit(self, tool_name: str) -> None:
        """
        Check if command is allowed under rate limit.

        Args:
            tool_name: Name of tool being executed

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        now = time.time()

        with self._lock:
            # Remove commands older than 60 seconds
            cutoff = now - 60.0
            while self._commands and self._commands[0] < cutoff:
                self._commands.popleft()

            # Check if limit reached
            if len(self._commands) >= self.limit:
                logger.warning(
                    f"Rate limit exceeded: {len(self._commands)}/{self.limit}",
                    extra={"extra_fields": {"tool": tool_name, "limit": self.limit}},
                )
                raise RateLimitExceededError(len(self._commands), self.limit)

            # Record command
            self._commands.append(now)
            remaining = self.limit - len(self._commands)

            logger.debug(
                f"Rate limit check passed: {len(self._commands)}/{self.limit} "
                f"({remaining} remaining)"
            )

    def get_current_count(self) -> int:
        """
        Get current command count in window.

        Returns:
            Number of commands in current window
        """
        now = time.time()
        cutoff = now - 60.0

        with self._lock:
            # Clean old commands
            while self._commands and self._commands[0] < cutoff:
                self._commands.popleft()

            return len(self._commands)

    def get_remaining(self) -> int:
        """
        Get remaining command quota.

        Returns:
            Number of commands remaining in window
        """
        return self.limit - self.get_current_count()

    def reset(self) -> None:
        """Reset rate limiter (clear all recorded commands)."""
        with self._lock:
            self._commands.clear()
            logger.info("Rate limiter reset")

    def is_exhausted(self) -> bool:
        """
        Check if rate limit is exhausted.

        Returns:
            True if no commands remaining
        """
        return self.get_remaining() <= 0
