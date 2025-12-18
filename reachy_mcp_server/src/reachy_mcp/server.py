"""
Main MCP server for Reachy Mini robot control.

This module implements the Model Context Protocol server that exposes
robot capabilities as tools and resources.
"""

import asyncio
import signal
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from .adapters import RobotAdapter, create_robot_dependencies
from .config import get_config
from .safety import SafetyMonitor
from .utils import get_audit_logger, get_logger, setup_logging

# Initialize logging
logger, audit_logger = setup_logging()
logger = get_logger("server")


class ReachyMCPServer:
    """
    Reachy Mini MCP Server.

    Exposes robot control capabilities through Model Context Protocol.
    """

    def __init__(self):
        """Initialize MCP server."""
        self.config = get_config()
        self.server = Server("reachy-robot")

        # Initialize robot components
        logger.info("Initializing robot dependencies...")
        self.deps = create_robot_dependencies()
        self.robot = RobotAdapter(self.deps)
        self.safety = SafetyMonitor()

        logger.info("✓ Reachy MCP Server initialized")

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available robot control tools."""
            return [
                Tool(
                    name="move_head",
                    description="Move robot head to look in a direction (left/right/up/down/front)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "direction": {
                                "type": "string",
                                "enum": ["left", "right", "up", "down", "front"],
                                "description": "Direction to look",
                            },
                            "speed": {
                                "type": "number",
                                "minimum": 0.1,
                                "maximum": 1.0,
                                "default": 0.5,
                                "description": "Movement speed (0.1=slow, 1.0=fast)",
                            },
                        },
                        "required": ["direction"],
                    },
                ),
                Tool(
                    name="analyze_view",
                    description="Capture and analyze what robot sees through camera",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "What to analyze (e.g., 'What emotion is this person showing?')",
                            },
                            "use_local": {
                                "type": "boolean",
                                "default": False,
                                "description": "Use local VLM (private) vs cloud GPT-4V (more accurate)",
                            },
                        },
                        "required": ["question"],
                    },
                ),
                Tool(
                    name="execute_dance",
                    description="Perform a choreographed dance from the library",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dance_name": {
                                "type": "string",
                                "description": "Name of dance (omit for random selection)",
                            },
                        },
                    },
                ),
                Tool(
                    name="express_emotion",
                    description="Display an emotion animation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "emotion": {
                                "type": "string",
                                "enum": ["happy", "sad", "surprised", "thinking", "excited", "neutral"],
                                "description": "Emotion to express",
                            },
                        },
                        "required": ["emotion"],
                    },
                ),
                Tool(
                    name="set_face_tracking",
                    description="Enable or disable automatic face following",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "enabled": {
                                "type": "boolean",
                                "description": "True to enable, False to disable",
                            },
                        },
                        "required": ["enabled"],
                    },
                ),
                Tool(
                    name="emergency_stop",
                    description="IMMEDIATELY halt all robot motion and enter safe state",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "default": "User initiated",
                                "description": "Reason for emergency stop (for logging)",
                            },
                        },
                    },
                ),
                Tool(
                    name="get_status",
                    description="Get current robot status (joints, battery, errors, etc)",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Execute robot control tool."""
            import time

            start_time = time.time()

            try:
                # Safety checks (except for status queries and emergency stop)
                if name not in ["get_status", "emergency_stop"]:
                    self.safety.check_before_execution(name, arguments)

                # Execute tool
                result = await self._execute_tool(name, arguments)

                duration_ms = (time.time() - start_time) * 1000

                # Log to audit trail
                get_audit_logger().log_command(
                    tool_name=name,
                    arguments=arguments,
                    result=result,
                    success=True,
                    duration_ms=duration_ms,
                )

                logger.info(
                    f"Tool executed: {name} ({duration_ms:.1f}ms)",
                    extra={"extra_fields": {"tool": name, "duration_ms": duration_ms}},
                )

                return [TextContent(type="text", text=result)]

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = f"Error: {str(e)}"

                # Log to audit trail
                get_audit_logger().log_command(
                    tool_name=name,
                    arguments=arguments,
                    result=error_msg,
                    success=False,
                    duration_ms=duration_ms,
                    error=str(e),
                )

                logger.error(
                    f"Tool failed: {name} - {e}",
                    extra={"extra_fields": {"tool": name, "error": str(e)}},
                )

                return [TextContent(type="text", text=error_msg)]

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available robot resources."""
            return [
                Resource(
                    uri="reachy://status/current",
                    name="Current Robot Status",
                    description="Real-time robot state (joints, battery, camera, etc)",
                    mimeType="application/json",
                ),
                Resource(
                    uri="reachy://status/health",
                    name="System Health",
                    description="Robot health status and error information",
                    mimeType="application/json",
                ),
                Resource(
                    uri="reachy://config/limits",
                    name="Joint Limits",
                    description="Joint angle limits and constraints",
                    mimeType="application/json",
                ),
                Resource(
                    uri="reachy://config/safety",
                    name="Safety Configuration",
                    description="Current safety settings and thresholds",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read robot resource."""
            import json

            try:
                if uri == "reachy://status/current":
                    status = self.robot.get_status()
                    return json.dumps(status, indent=2)

                elif uri == "reachy://status/health":
                    health = {
                        "connected": True,
                        "emergency_stop_active": self.safety.is_emergency_stop_active(),
                        "errors": [],
                    }
                    return json.dumps(health, indent=2)

                elif uri == "reachy://config/limits":
                    limits = {
                        "joints": {
                            "neck_pitch": {"min": -45.0, "max": 45.0, "unit": "degrees"},
                            "neck_yaw": {"min": -90.0, "max": 90.0, "unit": "degrees"},
                            "neck_roll": {"min": -30.0, "max": 30.0, "unit": "degrees"},
                            "l_antenna": {"min": -180.0, "max": 180.0, "unit": "degrees"},
                            "r_antenna": {"min": -180.0, "max": 180.0, "unit": "degrees"},
                        }
                    }
                    return json.dumps(limits, indent=2)

                elif uri == "reachy://config/safety":
                    safety_config = self.safety.get_safety_status()
                    return json.dumps(safety_config, indent=2)

                else:
                    return json.dumps({"error": f"Unknown resource: {uri}"})

            except Exception as e:
                logger.error(f"Failed to read resource {uri}: {e}")
                return json.dumps({"error": str(e)})

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """
        Execute tool by name.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Execution result
        """
        if name == "move_head":
            direction = arguments["direction"]
            speed = arguments.get("speed", 0.5)
            return await self.robot.move_head(direction, speed)

        elif name == "analyze_view":
            question = arguments["question"]
            use_local = arguments.get("use_local", False)
            return await self.robot.analyze_view(question, use_local)

        elif name == "execute_dance":
            dance_name = arguments.get("dance_name")
            return await self.robot.execute_dance(dance_name)

        elif name == "express_emotion":
            emotion = arguments["emotion"]
            return await self.robot.express_emotion(emotion)

        elif name == "set_face_tracking":
            enabled = arguments["enabled"]
            return await self.robot.set_face_tracking(enabled)

        elif name == "emergency_stop":
            reason = arguments.get("reason", "User initiated")
            return await self.robot.emergency_stop(reason)

        elif name == "get_status":
            import json
            status = self.robot.get_status()
            return json.dumps(status, indent=2)

        else:
            return f"Unknown tool: {name}"

    async def run(self) -> None:
        """Run MCP server with stdio transport."""
        logger.info("Starting Reachy MCP Server...")
        logger.info(f"Safety mode: {self.config.safety_mode.value}")
        logger.info(f"Robot: {self.config.robot_host}:{self.config.robot_port}")

        async with stdio_server() as (read_stream, write_stream):
            logger.info("✓ MCP Server running (stdio transport)")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )

    def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("Shutting down Reachy MCP Server...")

        try:
            from .adapters.deps import cleanup_robot_dependencies
            cleanup_robot_dependencies(self.deps)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        logger.info("✓ Shutdown complete")


async def main() -> None:
    """Main entry point for MCP server."""
    server = ReachyMCPServer()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        server.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await server.run()
    except Exception as e:
        logger.critical(f"Server crashed: {e}", exc_info=True)
        server.cleanup()
        sys.exit(1)


def cli_main() -> None:
    """CLI entry point (for pyproject.toml script)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    cli_main()
