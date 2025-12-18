"""
Basic usage examples for Reachy MCP Server.

This demonstrates how to test the MCP server programmatically.
"""

import asyncio
import json

from reachy_mcp.server import ReachyMCPServer


async def example_basic_usage():
    """Example: Basic robot control through MCP server."""
    print("=== Basic Usage Example ===\n")

    # Initialize server (this connects to robot)
    server = ReachyMCPServer()

    try:
        # Example 1: Move head
        print("1. Moving head left...")
        result = await server._execute_tool("move_head", {"direction": "left", "speed": 0.5})
        print(f"   Result: {result}\n")

        await asyncio.sleep(1)

        # Example 2: Get status
        print("2. Getting robot status...")
        status_json = await server._execute_tool("get_status", {})
        status = json.loads(status_json)
        print(f"   Joints: {status.get('joints', {})}")
        print(f"   Camera available: {status.get('camera', {}).get('available', False)}\n")

        await asyncio.sleep(1)

        # Example 3: Express emotion
        print("3. Expressing happy emotion...")
        result = await server._execute_tool("express_emotion", {"emotion": "happy"})
        print(f"   Result: {result}\n")

        await asyncio.sleep(2)

        # Example 4: Emergency stop
        print("4. Testing emergency stop...")
        result = await server._execute_tool("emergency_stop", {"reason": "Testing"})
        print(f"   Result: {result}\n")

    finally:
        # Cleanup
        server.cleanup()


async def example_vision():
    """Example: Using robot vision."""
    print("=== Vision Example ===\n")

    server = ReachyMCPServer()

    try:
        # Check if camera is available
        print("1. Checking camera availability...")
        status_json = await server._execute_tool("get_status", {})
        status = json.loads(status_json)

        if not status.get("camera", {}).get("available", False):
            print("   ⚠️  Camera not available!")
            return

        print("   ✓ Camera available\n")

        # Analyze view
        print("2. Analyzing current view...")
        result = await server._execute_tool(
            "analyze_view",
            {"question": "Describe what you see in one sentence", "use_local": False}
        )
        print(f"   Vision result: {result}\n")

    finally:
        server.cleanup()


async def example_safety():
    """Example: Demonstrating safety features."""
    print("=== Safety Features Example ===\n")

    server = ReachyMCPServer()

    try:
        # Get safety configuration
        print("1. Current safety configuration:")
        safety_status = server.safety.get_safety_status()
        print(f"   Mode: {safety_status['mode']}")
        print(f"   Rate limit: {safety_status['rate_limit']['limit']} commands/minute")
        print(f"   Emergency stop: {'ACTIVE' if safety_status['emergency_stop_active'] else 'inactive'}\n")

        # Test rate limiting
        print("2. Testing rate limiting...")
        for i in range(5):
            try:
                result = await server._execute_tool("move_head", {"direction": "front"})
                print(f"   Command {i+1}: OK")
            except Exception as e:
                print(f"   Command {i+1}: {e}")

        print(f"   Commands remaining: {server.safety.rate_limiter.get_remaining()}\n")

    finally:
        server.cleanup()


async def example_resources():
    """Example: Reading MCP resources."""
    print("=== Resources Example ===\n")

    server = ReachyMCPServer()

    try:
        # List all resources
        resources = await server.server._handlers.list_resources()
        print("Available resources:")
        for resource in resources:
            print(f"   - {resource.uri}: {resource.name}")
        print()

        # Read specific resources
        print("Reading reachy://status/current:")
        status = await server.server._handlers.read_resource("reachy://status/current")
        print(f"{status}\n")

        print("Reading reachy://config/safety:")
        safety = await server.server._handlers.read_resource("reachy://config/safety")
        print(f"{safety}\n")

    finally:
        server.cleanup()


def main():
    """Run all examples."""
    print("╔═══════════════════════════════════════════════╗")
    print("║   Reachy MCP Server - Usage Examples         ║")
    print("╚═══════════════════════════════════════════════╝\n")

    # Run examples
    asyncio.run(example_basic_usage())
    print("\n" + "="*50 + "\n")

    asyncio.run(example_vision())
    print("\n" + "="*50 + "\n")

    asyncio.run(example_safety())
    print("\n" + "="*50 + "\n")

    asyncio.run(example_resources())

    print("\n✓ All examples completed!")


if __name__ == "__main__":
    main()
