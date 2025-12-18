"""
Workspace and command validation.

Ensures commands are safe before execution.
"""

from typing import Any

from ..config import get_config
from ..utils import ValidationError, WorkspaceBoundaryViolation, get_logger

logger = get_logger("safety.validator")


class WorkspaceValidator:
    """
    Validates movements stay within safe workspace boundaries.

    Prevents collisions and dangerous poses by enforcing spatial constraints.
    """

    def __init__(self):
        """Initialize workspace validator with configured boundaries."""
        config = get_config()
        self.bounds = config.workspace_bounds()

        logger.info(
            f"Workspace validator initialized with bounds: {self.bounds}",
            extra={"extra_fields": {"bounds": self.bounds}},
        )

    def validate_position(self, x: float, y: float, z: float) -> None:
        """
        Validate 3D position is within workspace.

        Args:
            x: X coordinate (meters)
            y: Y coordinate (meters)
            z: Z coordinate (meters)

        Raises:
            WorkspaceBoundaryViolation: If position outside bounds
        """
        if not self.is_position_safe(x, y, z):
            logger.error(
                f"Position ({x:.3f}, {y:.3f}, {z:.3f}) outside workspace bounds",
                extra={"extra_fields": {"position": (x, y, z), "bounds": self.bounds}},
            )
            raise WorkspaceBoundaryViolation((x, y, z), self.bounds)

        logger.debug(f"Position ({x:.3f}, {y:.3f}, {z:.3f}) validated - within bounds")

    def is_position_safe(self, x: float, y: float, z: float) -> bool:
        """
        Check if 3D position is within safe workspace.

        Args:
            x: X coordinate (meters)
            y: Y coordinate (meters)
            z: Z coordinate (meters)

        Returns:
            True if position is safe
        """
        return (
            self.bounds["x_min"] <= x <= self.bounds["x_max"]
            and self.bounds["y_min"] <= y <= self.bounds["y_max"]
            and self.bounds["z_min"] <= z <= self.bounds["z_max"]
        )

    def validate_joint_limits(self, joint_name: str, angle: float) -> None:
        """
        Validate joint angle is within safe limits.

        Args:
            joint_name: Name of joint
            angle: Desired angle (degrees)

        Raises:
            ValidationError: If angle exceeds joint limits
        """
        # Joint limits for Reachy Mini (degrees)
        joint_limits = {
            "neck_pitch": (-45.0, 45.0),
            "neck_yaw": (-90.0, 90.0),
            "neck_roll": (-30.0, 30.0),
            "l_antenna": (-180.0, 180.0),
            "r_antenna": (-180.0, 180.0),
        }

        if joint_name not in joint_limits:
            logger.warning(f"Unknown joint: {joint_name}")
            return  # Unknown joint, can't validate

        min_angle, max_angle = joint_limits[joint_name]

        if not (min_angle <= angle <= max_angle):
            logger.error(
                f"Joint {joint_name} angle {angle}° outside limits [{min_angle}°, {max_angle}°]",
                extra={
                    "extra_fields": {
                        "joint": joint_name,
                        "angle": angle,
                        "limits": (min_angle, max_angle),
                    }
                },
            )
            raise ValidationError(
                f"Joint {joint_name} angle {angle}° outside limits [{min_angle}°, {max_angle}°]",
                {
                    "joint": joint_name,
                    "angle": angle,
                    "min": min_angle,
                    "max": max_angle,
                },
            )

        logger.debug(f"Joint {joint_name} angle {angle}° validated - within limits")

    def validate_tool_arguments(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """
        Validate tool arguments are safe and well-formed.

        Args:
            tool_name: Name of tool
            arguments: Tool arguments

        Raises:
            ValidationError: If arguments are invalid
        """
        # Tool-specific validation
        if tool_name == "move_head":
            self._validate_move_head_args(arguments)
        elif tool_name == "execute_dance":
            self._validate_dance_args(arguments)
        elif tool_name == "express_emotion":
            self._validate_emotion_args(arguments)
        # Add more tool-specific validation as needed

        logger.debug(f"Arguments for {tool_name} validated successfully")

    def _validate_move_head_args(self, args: dict[str, Any]) -> None:
        """Validate move_head arguments."""
        direction = args.get("direction")
        valid_directions = ["left", "right", "up", "down", "front"]

        if direction not in valid_directions:
            raise ValidationError(
                f"Invalid direction: {direction}. Must be one of {valid_directions}",
                {"direction": direction, "valid": valid_directions},
            )

        speed = args.get("speed", 0.5)
        if not (0.1 <= speed <= 1.0):
            raise ValidationError(
                f"Invalid speed: {speed}. Must be between 0.1 and 1.0",
                {"speed": speed},
            )

    def _validate_dance_args(self, args: dict[str, Any]) -> None:
        """Validate dance arguments."""
        # Dance name validation would require accessing dance library
        # For now, just ensure it's a string if provided
        dance_name = args.get("dance_name")
        if dance_name is not None and not isinstance(dance_name, str):
            raise ValidationError(
                f"Invalid dance_name type: {type(dance_name).__name__}. Must be string",
                {"dance_name": dance_name},
            )

    def _validate_emotion_args(self, args: dict[str, Any]) -> None:
        """Validate emotion arguments."""
        emotion = args.get("emotion")
        valid_emotions = ["happy", "sad", "surprised", "thinking", "excited", "neutral"]

        if emotion not in valid_emotions:
            raise ValidationError(
                f"Invalid emotion: {emotion}. Must be one of {valid_emotions}",
                {"emotion": emotion, "valid": valid_emotions},
            )
