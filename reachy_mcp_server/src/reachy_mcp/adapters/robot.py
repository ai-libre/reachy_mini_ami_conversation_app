"""
Robot adapter providing high-level interface to robot control.

Wraps existing reachy_mini_conversation_app code with clean MCP-friendly API.
"""

from typing import Any

from ..utils import SafetyError, ToolExecutionError, get_logger
from .deps import RobotDependencies

logger = get_logger("adapters.robot")


class RobotAdapter:
    """
    High-level adapter for robot control.

    Provides clean interface for MCP tools to interact with robot,
    wrapping existing tool implementations.
    """

    def __init__(self, deps: RobotDependencies):
        """
        Initialize robot adapter.

        Args:
            deps: Robot dependencies
        """
        self.deps = deps
        self._tool_cache: dict[str, Any] = {}

    def _get_tool(self, tool_class: type):
        """
        Get tool instance (cached).

        Args:
            tool_class: Tool class to instantiate

        Returns:
            Tool instance
        """
        tool_name = tool_class.__name__
        if tool_name not in self._tool_cache:
            self._tool_cache[tool_name] = tool_class()
        return self._tool_cache[tool_name]

    async def move_head(self, direction: str, speed: float = 0.5) -> str:
        """
        Move robot head to look in direction.

        Args:
            direction: Direction to look (left/right/up/down/front)
            speed: Movement speed (0.1-1.0)

        Returns:
            Result message

        Raises:
            ToolExecutionError: If movement fails
        """
        from reachy_mini_conversation_app.tools.move_head import MoveHeadTool

        try:
            tool = self._get_tool(MoveHeadTool)
            result = await tool.execute(
                {"direction": direction, "speed": speed}, self.deps.tool_deps
            )
            logger.info(f"Head moved {direction} at speed {speed}")
            return result
        except Exception as e:
            logger.error(f"Failed to move head: {e}")
            raise ToolExecutionError(f"Head movement failed: {e}", {"direction": direction}) from e

    async def analyze_view(self, prompt: str, use_local: bool = False) -> str:
        """
        Capture and analyze camera view.

        Args:
            prompt: Analysis prompt (e.g., "What emotion is this person showing?")
            use_local: Use local VLM vs cloud GPT-4V

        Returns:
            Analysis result

        Raises:
            ToolExecutionError: If analysis fails
        """
        from reachy_mini_conversation_app.tools.camera import CameraTool

        if not self.deps.is_camera_available():
            return "Camera not available"

        try:
            tool = self._get_tool(CameraTool)
            result = await tool.execute({"prompt": prompt}, self.deps.tool_deps)
            logger.info(f"Vision analysis completed: {prompt[:50]}...")
            return result
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            raise ToolExecutionError(f"Vision analysis failed: {e}", {"prompt": prompt}) from e

    async def execute_dance(self, dance_name: str | None = None) -> str:
        """
        Perform choreographed dance.

        Args:
            dance_name: Name of dance (None for random)

        Returns:
            Result message

        Raises:
            ToolExecutionError: If dance fails
        """
        from reachy_mini_conversation_app.tools.dance import DanceTool

        try:
            tool = self._get_tool(DanceTool)
            args = {"dance_name": dance_name} if dance_name else {}
            result = await tool.execute(args, self.deps.tool_deps)
            logger.info(f"Dance executed: {dance_name or 'random'}")
            return result
        except Exception as e:
            logger.error(f"Dance execution failed: {e}")
            raise ToolExecutionError(f"Dance failed: {e}", {"dance_name": dance_name}) from e

    async def express_emotion(self, emotion: str) -> str:
        """
        Play emotion animation.

        Args:
            emotion: Emotion to express (happy/sad/surprised/etc)

        Returns:
            Result message

        Raises:
            ToolExecutionError: If emotion fails
        """
        from reachy_mini_conversation_app.tools.play_emotion import PlayEmotionTool

        try:
            tool = self._get_tool(PlayEmotionTool)
            result = await tool.execute({"emotion": emotion}, self.deps.tool_deps)
            logger.info(f"Emotion expressed: {emotion}")
            return result
        except Exception as e:
            logger.error(f"Emotion expression failed: {e}")
            raise ToolExecutionError(f"Emotion failed: {e}", {"emotion": emotion}) from e

    async def set_face_tracking(self, enabled: bool) -> str:
        """
        Enable/disable face tracking.

        Args:
            enabled: True to enable, False to disable

        Returns:
            Result message

        Raises:
            ToolExecutionError: If tracking control fails
        """
        from reachy_mini_conversation_app.tools.head_tracking import HeadTrackingTool

        if not self.deps.is_camera_available():
            return "Camera not available - face tracking requires camera"

        try:
            tool = self._get_tool(HeadTrackingTool)
            result = await tool.execute({"enable": enabled}, self.deps.tool_deps)
            logger.info(f"Face tracking {'enabled' if enabled else 'disabled'}")
            return result
        except Exception as e:
            logger.error(f"Face tracking control failed: {e}")
            raise ToolExecutionError(
                f"Face tracking failed: {e}", {"enabled": enabled}
            ) from e

    async def stop_movement(self) -> str:
        """
        Stop all current movements.

        Returns:
            Result message
        """
        from reachy_mini_conversation_app.tools.stop_dance import StopDanceTool

        try:
            tool = self._get_tool(StopDanceTool)
            result = await tool.execute({}, self.deps.tool_deps)
            logger.info("All movements stopped")
            return result
        except Exception as e:
            logger.error(f"Stop movement failed: {e}")
            raise ToolExecutionError(f"Stop failed: {e}") from e

    async def emergency_stop(self, reason: str = "User initiated") -> str:
        """
        EMERGENCY STOP - immediate halt of all motion.

        Args:
            reason: Reason for emergency stop (for logging)

        Returns:
            Result message
        """
        logger.critical(f"⚠️  EMERGENCY STOP: {reason}")

        try:
            # Clear movement queue
            self.deps.movement_manager.queue_command("clear_queue")

            # Stop all motion
            await self.stop_movement()

            # Disable face tracking
            if self.deps.is_camera_available():
                try:
                    await self.set_face_tracking(False)
                except Exception:
                    pass  # Best effort

            logger.critical("✓ Emergency stop completed - robot in safe state")
            return f"Emergency stop activated: {reason}. Robot halted and in safe state."

        except Exception as e:
            logger.critical(f"Emergency stop failed: {e}")
            raise SafetyError(f"Emergency stop failed: {e}", {"reason": reason}) from e

    def get_joint_positions(self) -> dict[str, float]:
        """
        Get current joint positions.

        Returns:
            Dictionary of joint name to angle (degrees)
        """
        try:
            positions = self.deps.robot.get_joint_positions()
            logger.debug(f"Joint positions: {positions}")
            return positions
        except Exception as e:
            logger.error(f"Failed to get joint positions: {e}")
            return {}

    def get_status(self) -> dict[str, Any]:
        """
        Get comprehensive robot status.

        Returns:
            Status dictionary with joints, battery, errors, etc
        """
        try:
            status = {
                "joints": self.get_joint_positions(),
                "connected": True,
                "errors": [],
            }

            # Add battery info if available
            if hasattr(self.deps.robot, "get_battery_status"):
                try:
                    status["battery"] = self.deps.robot.get_battery_status()
                except Exception as e:
                    logger.warning(f"Could not get battery status: {e}")
                    status["battery"] = {"available": False}

            # Add camera status
            status["camera"] = {
                "available": self.deps.is_camera_available(),
                "face_tracking": (
                    self.deps.camera_worker.tracking_enabled
                    if self.deps.camera_worker
                    else False
                ),
            }

            # Add vision status
            status["vision"] = {"local_available": self.deps.is_vision_available()}

            logger.debug("Status retrieved successfully")
            return status

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "connected": False,
                "error": str(e),
            }
