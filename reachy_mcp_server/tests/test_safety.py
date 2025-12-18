"""Tests for safety layer."""

import time

import pytest

from reachy_mcp.utils import (
    EmergencyStopActive,
    RateLimitExceededError,
    ValidationError,
    WorkspaceBoundaryViolation,
)


def test_rate_limiter_basic(rate_limiter):
    """Test basic rate limiting."""
    # Should allow commands under limit
    for i in range(5):
        rate_limiter.check_rate_limit(f"test_tool_{i}")

    assert rate_limiter.get_current_count() == 5
    assert rate_limiter.get_remaining() == 5  # limit is 10


def test_rate_limiter_exceeded(rate_limiter):
    """Test rate limit exceeded."""
    # Fill up to limit
    for i in range(10):
        rate_limiter.check_rate_limit(f"test_{i}")

    # Next one should fail
    with pytest.raises(RateLimitExceededError):
        rate_limiter.check_rate_limit("overflow")


def test_rate_limiter_reset(rate_limiter):
    """Test rate limiter reset."""
    for i in range(5):
        rate_limiter.check_rate_limit(f"test_{i}")

    assert rate_limiter.get_current_count() == 5

    rate_limiter.reset()
    assert rate_limiter.get_current_count() == 0


def test_workspace_validator_valid_position(workspace_validator):
    """Test valid position validation."""
    # Should not raise
    workspace_validator.validate_position(0.1, 0.1, 0.2)
    workspace_validator.validate_position(-0.2, -0.1, 0.1)
    workspace_validator.validate_position(0.0, 0.0, 0.0)


def test_workspace_validator_invalid_position(workspace_validator):
    """Test invalid position validation."""
    with pytest.raises(WorkspaceBoundaryViolation):
        workspace_validator.validate_position(5.0, 0.0, 0.0)  # Too far

    with pytest.raises(WorkspaceBoundaryViolation):
        workspace_validator.validate_position(0.0, 5.0, 0.0)  # Too far

    with pytest.raises(WorkspaceBoundaryViolation):
        workspace_validator.validate_position(0.0, 0.0, 5.0)  # Too high


def test_workspace_validator_joint_limits(workspace_validator):
    """Test joint limit validation."""
    # Valid angles
    workspace_validator.validate_joint_limits("neck_pitch", 30.0)
    workspace_validator.validate_joint_limits("neck_yaw", -45.0)

    # Invalid angles
    with pytest.raises(ValidationError):
        workspace_validator.validate_joint_limits("neck_pitch", 100.0)

    with pytest.raises(ValidationError):
        workspace_validator.validate_joint_limits("neck_yaw", -120.0)


def test_workspace_validator_tool_arguments(workspace_validator):
    """Test tool argument validation."""
    # Valid arguments
    workspace_validator.validate_tool_arguments(
        "move_head", {"direction": "left", "speed": 0.5}
    )

    # Invalid direction
    with pytest.raises(ValidationError):
        workspace_validator.validate_tool_arguments(
            "move_head", {"direction": "invalid"}
        )

    # Invalid speed
    with pytest.raises(ValidationError):
        workspace_validator.validate_tool_arguments(
            "move_head", {"direction": "left", "speed": 2.0}
        )


def test_safety_monitor_emergency_stop(safety_monitor):
    """Test emergency stop functionality."""
    assert not safety_monitor.is_emergency_stop_active()

    # Activate emergency stop
    safety_monitor.activate_emergency_stop("Testing")
    assert safety_monitor.is_emergency_stop_active()

    # Should block commands
    with pytest.raises(EmergencyStopActive):
        safety_monitor.check_before_execution("move_head", {"direction": "left"})

    # Deactivate
    safety_monitor.deactivate_emergency_stop()
    assert not safety_monitor.is_emergency_stop_active()


def test_safety_monitor_checks(safety_monitor):
    """Test safety monitor pre-execution checks."""
    # Should pass with valid arguments under rate limit
    safety_monitor.check_before_execution("move_head", {"direction": "left"})

    # Should enforce rate limit
    for i in range(35):  # Exceed limit of 30
        try:
            safety_monitor.check_before_execution("move_head", {"direction": "front"})
        except RateLimitExceededError:
            break
    else:
        pytest.fail("Rate limit not enforced")


def test_safety_monitor_status(safety_monitor):
    """Test safety status retrieval."""
    status = safety_monitor.get_safety_status()

    assert "enabled" in status
    assert "mode" in status
    assert "emergency_stop_active" in status
    assert "rate_limit" in status
    assert "workspace_bounds" in status


def test_safety_monitor_reset(safety_monitor):
    """Test safety monitor reset."""
    # Fill rate limit
    for i in range(10):
        safety_monitor.check_before_execution("move_head", {"direction": "left"})

    # Activate emergency stop
    safety_monitor.activate_emergency_stop("Test")

    # Reset
    safety_monitor.reset()

    # Should be clean
    assert not safety_monitor.is_emergency_stop_active()
    assert safety_monitor.rate_limiter.get_current_count() == 0
