"""
Pytest configuration and fixtures for Reachy MCP Server tests.
"""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    os.environ["MOCK_ROBOT"] = "true"
    os.environ["SAFETY_MODE"] = "disabled"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["ROBOT_HOST"] = "127.0.0.1"


@pytest.fixture
def mock_robot():
    """Create mock robot for testing."""
    robot = MagicMock()
    robot.get_joint_positions.return_value = {
        "neck_pitch": 0.0,
        "neck_yaw": 0.0,
        "neck_roll": 0.0,
        "l_antenna": 0.0,
        "r_antenna": 0.0,
    }
    robot.set_target.return_value = None
    return robot


@pytest.fixture
def mock_deps(mock_robot):
    """Create mock dependencies."""
    from reachy_mcp.adapters import RobotDependencies
    from reachy_mini_conversation_app.tools.core_tools import ToolDependencies

    tool_deps = ToolDependencies(
        robot=mock_robot,
        movement_manager=MagicMock(),
        camera_worker=None,
        vision_manager=None,
    )

    return RobotDependencies(
        robot=mock_robot,
        movement_manager=MagicMock(),
        camera_worker=None,
        vision_manager=None,
        tool_deps=tool_deps,
    )


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing."""
    from reachy_mcp.safety import RateLimiter

    return RateLimiter(max_commands_per_minute=10)


@pytest.fixture
def workspace_validator():
    """Create workspace validator for testing."""
    from reachy_mcp.safety import WorkspaceValidator

    return WorkspaceValidator()


@pytest.fixture
def safety_monitor():
    """Create safety monitor for testing."""
    from reachy_mcp.safety import SafetyMonitor

    return SafetyMonitor()
