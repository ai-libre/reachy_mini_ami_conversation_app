"""
Safety monitoring and enforcement.

Coordinates all safety checks and maintains emergency stop state.
"""

import threading
from typing import Any

from ..config import SafetyMode, get_config
from ..utils import EmergencyStopActive, get_logger
from .rate_limiter import RateLimiter
from .validator import WorkspaceValidator

logger = get_logger("safety.monitor")


class SafetyMonitor:
    """
    Central safety monitoring and enforcement.

    Coordinates rate limiting, validation, and emergency stop.
    """

    def __init__(self):
        """Initialize safety monitor."""
        config = get_config()

        self.safety_mode = config.safety_mode
        self.rate_limiter = RateLimiter()
        self.validator = WorkspaceValidator()

        # Emergency stop state
        self._emergency_stop_active = threading.Event()
        self._emergency_stop_reason = ""
        self._lock = threading.Lock()

        logger.info(
            f"Safety monitor initialized (mode: {self.safety_mode.value})",
            extra={"extra_fields": {"mode": self.safety_mode.value}},
        )

        if not self.is_enabled():
            logger.warning(
                "⚠️  SAFETY DISABLED - All safety checks are OFF! "
                "This should ONLY be used in development."
            )

    def is_enabled(self) -> bool:
        """
        Check if safety checks are enabled.

        Returns:
            True if safety is enabled
        """
        return self.safety_mode != SafetyMode.DISABLED

    def is_strict_mode(self) -> bool:
        """
        Check if running in strict safety mode.

        Returns:
            True if strict mode
        """
        return self.safety_mode == SafetyMode.STRICT

    def check_before_execution(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """
        Perform all pre-execution safety checks.

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Raises:
            EmergencyStopActive: If emergency stop is active
            RateLimitExceededError: If rate limit exceeded
            ValidationError: If arguments invalid
        """
        # Always check emergency stop, even if safety disabled
        if self.is_emergency_stop_active():
            logger.error(
                f"Blocked {tool_name}: Emergency stop active",
                extra={"extra_fields": {"tool": tool_name, "reason": self._emergency_stop_reason}},
            )
            raise EmergencyStopActive(
                f"Emergency stop active: {self._emergency_stop_reason}",
                {"reason": self._emergency_stop_reason},
            )

        # Skip other checks if safety disabled
        if not self.is_enabled():
            logger.debug(f"Safety checks bypassed for {tool_name} (safety disabled)")
            return

        # Rate limiting
        try:
            self.rate_limiter.check_rate_limit(tool_name)
        except Exception as e:
            logger.error(
                f"Rate limit check failed for {tool_name}: {e}",
                extra={"extra_fields": {"tool": tool_name}},
            )
            raise

        # Argument validation
        try:
            self.validator.validate_tool_arguments(tool_name, arguments)
        except Exception as e:
            logger.error(
                f"Validation failed for {tool_name}: {e}",
                extra={"extra_fields": {"tool": tool_name, "arguments": arguments}},
            )
            raise

        logger.debug(f"All safety checks passed for {tool_name}")

    def activate_emergency_stop(self, reason: str = "User initiated") -> None:
        """
        Activate emergency stop.

        Args:
            reason: Reason for emergency stop
        """
        with self._lock:
            self._emergency_stop_active.set()
            self._emergency_stop_reason = reason

        logger.critical(
            f"🚨 EMERGENCY STOP ACTIVATED: {reason}",
            extra={"extra_fields": {"reason": reason}},
        )

    def deactivate_emergency_stop(self) -> None:
        """Deactivate emergency stop."""
        with self._lock:
            previous_reason = self._emergency_stop_reason
            self._emergency_stop_active.clear()
            self._emergency_stop_reason = ""

        logger.warning(
            f"Emergency stop deactivated (was: {previous_reason})",
            extra={"extra_fields": {"previous_reason": previous_reason}},
        )

    def is_emergency_stop_active(self) -> bool:
        """
        Check if emergency stop is active.

        Returns:
            True if emergency stop active
        """
        return self._emergency_stop_active.is_set()

    def get_safety_status(self) -> dict[str, Any]:
        """
        Get current safety status.

        Returns:
            Dictionary with safety status information
        """
        return {
            "enabled": self.is_enabled(),
            "mode": self.safety_mode.value,
            "emergency_stop_active": self.is_emergency_stop_active(),
            "emergency_stop_reason": self._emergency_stop_reason,
            "rate_limit": {
                "limit": self.rate_limiter.limit,
                "current": self.rate_limiter.get_current_count(),
                "remaining": self.rate_limiter.get_remaining(),
            },
            "workspace_bounds": self.validator.bounds,
        }

    def reset(self) -> None:
        """Reset safety monitor (clear rate limits, deactivate emergency stop)."""
        self.rate_limiter.reset()
        self.deactivate_emergency_stop()
        logger.info("Safety monitor reset")
