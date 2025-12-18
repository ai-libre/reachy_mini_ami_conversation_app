"""Utility modules for Reachy MCP Server."""

from .errors import (
    CameraError,
    ConfigurationError,
    EmergencyStopActive,
    HardwareError,
    MotorError,
    RateLimitExceededError,
    ReachyMCPError,
    ResourceError,
    RobotConnectionError,
    SafetyError,
    ToolExecutionError,
    ValidationError,
    VisionError,
    WorkspaceBoundaryViolation,
)
from .logging import AuditLogger, get_audit_logger, get_logger, setup_logging

__all__ = [
    # Errors
    "ReachyMCPError",
    "ConfigurationError",
    "ValidationError",
    "RobotConnectionError",
    "SafetyError",
    "RateLimitExceededError",
    "WorkspaceBoundaryViolation",
    "EmergencyStopActive",
    "HardwareError",
    "MotorError",
    "CameraError",
    "ToolExecutionError",
    "VisionError",
    "ResourceError",
    # Logging
    "setup_logging",
    "get_logger",
    "get_audit_logger",
    "AuditLogger",
]
