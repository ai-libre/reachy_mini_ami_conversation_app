"""
Configuration management for Reachy MCP Server.

Handles environment variables, validation, and provides type-safe configuration
access throughout the application.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SafetyMode(str, Enum):
    """Safety mode configuration."""

    STRICT = "strict"  # All safety checks, confirmations required
    PERMISSIVE = "permissive"  # Safety checks, fewer confirmations
    DISABLED = "disabled"  # No safety checks (development only!)


class TransportMode(str, Enum):
    """MCP transport mode."""

    STDIO = "stdio"  # Standard input/output (local)
    HTTP = "http"  # HTTP with SSE (remote)


class FaceTrackingMode(str, Enum):
    """Face tracking implementation."""

    YOLO = "yolo"
    MEDIAPIPE = "mediapipe"
    DISABLED = "disabled"


class Config(BaseSettings):
    """
    Reachy MCP Server configuration.

    Loads from environment variables with validation and type conversion.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========================================================================
    # Robot Connection
    # ========================================================================
    robot_host: str = Field(
        default="192.168.1.100",
        description="Robot IP address or hostname",
    )
    robot_port: int = Field(
        default=50051,
        ge=1,
        le=65535,
        description="Robot gRPC port",
    )

    # ========================================================================
    # Safety Configuration
    # ========================================================================
    safety_mode: SafetyMode = Field(
        default=SafetyMode.STRICT,
        description="Safety mode (strict/permissive/disabled)",
    )
    max_commands_per_minute: int = Field(
        default=30,
        ge=1,
        le=1000,
        description="Rate limit for commands",
    )
    require_confirmation: bool = Field(
        default=True,
        description="Require user confirmation for dangerous operations",
    )

    # Workspace boundaries (meters)
    workspace_x_min: float = Field(default=-0.3, le=0.0)
    workspace_x_max: float = Field(default=0.3, ge=0.0)
    workspace_y_min: float = Field(default=-0.3, le=0.0)
    workspace_y_max: float = Field(default=0.3, ge=0.0)
    workspace_z_min: float = Field(default=0.0, ge=0.0)
    workspace_z_max: float = Field(default=0.5, ge=0.0)

    # ========================================================================
    # Vision Configuration
    # ========================================================================
    use_local_vision: bool = Field(
        default=False,
        description="Use local VLM instead of cloud GPT-4V",
    )
    local_vision_model: str = Field(
        default="HuggingFaceTB/SmolVLM2-2.2B-Instruct",
        description="Local vision model identifier",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (required if not using local vision)",
    )

    # ========================================================================
    # Camera Configuration
    # ========================================================================
    enable_camera: bool = Field(
        default=True,
        description="Enable camera functionality",
    )
    face_tracking_mode: FaceTrackingMode = Field(
        default=FaceTrackingMode.YOLO,
        description="Face tracking implementation",
    )

    # ========================================================================
    # Logging Configuration
    # ========================================================================
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_file: Path = Field(
        default=Path("logs/reachy_mcp.log"),
        description="Log file path",
    )
    audit_log: Path = Field(
        default=Path("logs/robot_commands.jsonl"),
        description="Audit log for robot commands",
    )
    structured_logging: bool = Field(
        default=False,
        description="Use structured (JSON) logging",
    )

    # ========================================================================
    # MCP Server Configuration
    # ========================================================================
    mcp_transport: TransportMode = Field(
        default=TransportMode.STDIO,
        description="MCP transport mode",
    )
    mcp_http_host: str = Field(
        default="127.0.0.1",
        description="HTTP server host (if using HTTP transport)",
    )
    mcp_http_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="HTTP server port",
    )
    mcp_http_auth_token: Optional[str] = Field(
        default=None,
        description="Authentication token for HTTP transport",
    )

    # ========================================================================
    # Performance Tuning
    # ========================================================================
    enable_metrics: bool = Field(
        default=True,
        description="Enable performance metrics collection",
    )
    metrics_interval: int = Field(
        default=60,
        ge=1,
        description="Metrics collection interval (seconds)",
    )
    max_concurrent_tools: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent tool executions",
    )

    # ========================================================================
    # Development Settings
    # ========================================================================
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode (verbose logging, relaxed safety)",
    )
    mock_robot: bool = Field(
        default=False,
        description="Use mock robot (no hardware required)",
    )
    enable_mcp_inspector: bool = Field(
        default=False,
        description="Enable MCP inspector for debugging",
    )

    # ========================================================================
    # Validators
    # ========================================================================

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate OpenAI API key is present if not using local vision."""
        use_local = info.data.get("use_local_vision", False)
        if not use_local and not v:
            raise ValueError("OPENAI_API_KEY required when USE_LOCAL_VISION=false")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v_upper

    @field_validator("safety_mode")
    @classmethod
    def warn_disabled_safety(cls, v: SafetyMode) -> SafetyMode:
        """Warn if safety is disabled."""
        if v == SafetyMode.DISABLED:
            import warnings

            warnings.warn(
                "⚠️  SAFETY_MODE=disabled: All safety checks are OFF! "
                "This should ONLY be used in development. "
                "NEVER use in production or near people/objects.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @field_validator("log_file", "audit_log")
    @classmethod
    def ensure_log_directory(cls, v: Path) -> Path:
        """Ensure log directory exists."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def is_safety_enabled(self) -> bool:
        """Check if safety checks are enabled."""
        return self.safety_mode != SafetyMode.DISABLED

    def is_strict_mode(self) -> bool:
        """Check if running in strict safety mode."""
        return self.safety_mode == SafetyMode.STRICT

    def workspace_bounds(self) -> dict:
        """Get workspace boundary configuration."""
        return {
            "x_min": self.workspace_x_min,
            "x_max": self.workspace_x_max,
            "y_min": self.workspace_y_min,
            "y_max": self.workspace_y_max,
            "z_min": self.workspace_z_min,
            "z_max": self.workspace_z_max,
        }

    def validate_robot_connection(self) -> None:
        """
        Validate robot connection configuration.

        Raises:
            ValueError: If configuration is invalid
        """
        if self.mock_robot:
            return  # Skip validation for mock

        # Check robot host is not empty
        if not self.robot_host or self.robot_host.strip() == "":
            raise ValueError("ROBOT_HOST cannot be empty")

        # Warn if using default IP
        if self.robot_host == "192.168.1.100":
            import warnings

            warnings.warn(
                "Using default ROBOT_HOST (192.168.1.100). "
                "Make sure this matches your robot's actual IP address.",
                UserWarning,
                stacklevel=2,
            )


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance (singleton).

    Returns:
        Config: Configuration object
    """
    global _config
    if _config is None:
        _config = Config()
        _config.validate_robot_connection()
    return _config


def reload_config() -> Config:
    """
    Reload configuration from environment.

    Useful for testing or runtime reconfiguration.

    Returns:
        Config: New configuration object
    """
    global _config
    _config = Config()
    _config.validate_robot_connection()
    return _config
