"""
Adapter layer for bridging existing reachy_mini_conversation_app code.

Provides clean interface between MCP server and existing robot control code.
"""

from .deps import RobotDependencies, create_robot_dependencies
from .robot import RobotAdapter

__all__ = [
    "RobotAdapter",
    "RobotDependencies",
    "create_robot_dependencies",
]
