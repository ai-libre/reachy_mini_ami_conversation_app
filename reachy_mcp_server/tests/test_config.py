"""Tests for configuration management."""

import os

import pytest

from reachy_mcp.config import Config, SafetyMode, reload_config
from reachy_mcp.utils import ConfigurationError, ValidationError


def test_config_defaults():
    """Test default configuration values."""
    config = Config()

    assert config.robot_host == "192.168.1.100"
    assert config.robot_port == 50051
    assert config.safety_mode == SafetyMode.STRICT
    assert config.max_commands_per_minute == 30
    assert config.enable_camera is True


def test_config_from_env(monkeypatch):
    """Test configuration loading from environment."""
    monkeypatch.setenv("ROBOT_HOST", "10.0.0.1")
    monkeypatch.setenv("SAFETY_MODE", "permissive")
    monkeypatch.setenv("MAX_COMMANDS_PER_MINUTE", "60")

    config = reload_config()

    assert config.robot_host == "10.0.0.1"
    assert config.safety_mode == SafetyMode.PERMISSIVE
    assert config.max_commands_per_minute == 60


def test_safety_mode_validation():
    """Test safety mode enum validation."""
    config = Config(safety_mode="strict")
    assert config.safety_mode == SafetyMode.STRICT

    config = Config(safety_mode="permissive")
    assert config.safety_mode == SafetyMode.PERMISSIVE

    config = Config(safety_mode="disabled")
    assert config.safety_mode == SafetyMode.DISABLED


def test_openai_key_validation():
    """Test OpenAI API key validation."""
    # Should not raise if local vision
    config = Config(use_local_vision=True, openai_api_key=None)
    assert config.use_local_vision is True

    # Should raise if cloud vision without key
    with pytest.raises(ValidationError):
        Config(use_local_vision=False, openai_api_key=None)


def test_workspace_bounds():
    """Test workspace boundary configuration."""
    config = Config()
    bounds = config.workspace_bounds()

    assert "x_min" in bounds
    assert "x_max" in bounds
    assert bounds["x_min"] < bounds["x_max"]


def test_is_safety_enabled():
    """Test safety enabled check."""
    config = Config(safety_mode="strict")
    assert config.is_safety_enabled() is True

    config = Config(safety_mode="disabled")
    assert config.is_safety_enabled() is False


def test_is_strict_mode():
    """Test strict mode check."""
    config = Config(safety_mode="strict")
    assert config.is_strict_mode() is True

    config = Config(safety_mode="permissive")
    assert config.is_strict_mode() is False
