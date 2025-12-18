"""Reachy MCP Server - Model Context Protocol server for Reachy Mini robot control."""

__version__ = "1.0.0"

# Lazy imports to avoid importing heavy dependencies at package level
# Users should import directly: from reachy_mcp.config import get_config
__all__ = [
    "__version__",
]


def get_config():
    """Get configuration instance (lazy import)."""
    from .config import get_config as _get_config
    return _get_config()


def create_server():
    """Create MCP server instance (lazy import)."""
    from .server import ReachyMCPServer
    return ReachyMCPServer()
