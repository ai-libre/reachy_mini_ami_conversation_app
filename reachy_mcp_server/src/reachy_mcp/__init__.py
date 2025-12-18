"""Reachy MCP Server - Model Context Protocol server for Reachy Mini robot control."""

__version__ = "1.0.0"

from .config import get_config
from .server import ReachyMCPServer

__all__ = [
    "__version__",
    "ReachyMCPServer",
    "get_config",
]
