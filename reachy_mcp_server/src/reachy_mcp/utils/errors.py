"""
Custom exceptions for Reachy MCP Server.

Provides clear, structured error hierarchy for different failure modes.
"""


class ReachyMCPError(Exception):
    """Base exception for all Reachy MCP errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# ============================================================================
# Configuration Errors
# ============================================================================


class ConfigurationError(ReachyMCPError):
    """Configuration is invalid or missing."""

    pass


class ValidationError(ReachyMCPError):
    """Input validation failed."""

    pass


# ============================================================================
# Robot Connection Errors
# ============================================================================


class RobotConnectionError(ReachyMCPError):
    """Cannot connect to robot."""

    pass


class RobotNotReadyError(ReachyMCPError):
    """Robot is not in ready state."""

    pass


class RobotTimeoutError(ReachyMCPError):
    """Robot operation timed out."""

    pass


# ============================================================================
# Safety Errors
# ============================================================================


class SafetyError(ReachyMCPError):
    """Safety violation detected."""

    pass


class RateLimitExceededError(SafetyError):
    """Command rate limit exceeded."""

    def __init__(self, commands_sent: int, limit: int):
        super().__init__(
            f"Rate limit exceeded: {commands_sent} commands sent, limit is {limit}/minute",
            {"commands_sent": commands_sent, "limit": limit},
        )


class WorkspaceBoundaryViolation(SafetyError):
    """Movement would exit safe workspace."""

    def __init__(self, position: tuple, bounds: dict):
        super().__init__(
            f"Position {position} outside workspace bounds",
            {"position": position, "bounds": bounds},
        )


class EmergencyStopActive(SafetyError):
    """Emergency stop is active, no commands accepted."""

    pass


# ============================================================================
# Hardware Errors
# ============================================================================


class HardwareError(ReachyMCPError):
    """Hardware-level error (motors, sensors, etc)."""

    pass


class MotorError(HardwareError):
    """Motor error (overheat, stall, etc)."""

    pass


class SensorError(HardwareError):
    """Sensor error (camera, IMU, etc)."""

    pass


class CameraError(SensorError):
    """Camera-specific error."""

    pass


# ============================================================================
# Tool Execution Errors
# ============================================================================


class ToolExecutionError(ReachyMCPError):
    """Tool execution failed."""

    pass


class ToolNotFoundError(ToolExecutionError):
    """Requested tool does not exist."""

    pass


class ToolArgumentError(ToolExecutionError):
    """Tool arguments are invalid."""

    pass


# ============================================================================
# Vision Errors
# ============================================================================


class VisionError(ReachyMCPError):
    """Vision processing error."""

    pass


class VisionModelError(VisionError):
    """Vision model error (load failure, inference error)."""

    pass


class VisionAPIError(VisionError):
    """Cloud vision API error."""

    pass


# ============================================================================
# Resource Errors
# ============================================================================


class ResourceError(ReachyMCPError):
    """Resource access error."""

    pass


class ResourceNotFoundError(ResourceError):
    """Requested resource does not exist."""

    pass


class ResourceUnavailableError(ResourceError):
    """Resource temporarily unavailable."""

    pass
