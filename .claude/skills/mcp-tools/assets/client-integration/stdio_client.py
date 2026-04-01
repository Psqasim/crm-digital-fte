#!/usr/bin/env python3
"""
MCP Client Integration Examples
================================

Demonstrates how to connect to MCP servers and use their capabilities:
- Connect via stdio transport
- List and call tools
- Read resources
- Use prompt templates

This client can connect to any MCP server and interact with its features.
"""

import asyncio
import json
import sys
from typing import Any, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================================
# MCP CLIENT CLASS
# ============================================================================

class MCPClient:
    """
    A comprehensive MCP client that demonstrates all interaction patterns.
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = None

    @asynccontextmanager
    async def connect_to_server(self, command: str, args: list[str] = None):
        """
        Connect to an MCP server via stdio.

        Args:
            command: Command to run the server (e.g., "python")
            args: Arguments for the command (e.g., ["server.py"])

        Example:
            async with client.connect_to_server("python", ["main.py"]):
                # Use client here
        """
        if args is None:
            args = []

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None
        )

        print(f"Connecting to server: {command} {' '.join(args)}")

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session

                # Initialize the session
                await session.initialize()

                # Get server info
                print(f"Connected to: {session.info.name}")
                print(f"Version: {session.info.version}")
                print(f"Capabilities: {session.info.capabilities}")
                print("-" * 60)

                yield self

    # ========================================================================
    # TOOL OPERATIONS
    # ========================================================================

    async def list_tools(self) -> list[dict]:
        """List all available tools on the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.list_tools()

        print(f"\nFound {len(result.tools)} tools:")
        for tool in result.tools:
            print(f"\n  {tool.name}")
            print(f"    Description: {tool.description}")
            if hasattr(tool, 'inputSchema'):
                required = tool.inputSchema.get('required', [])
                properties = tool.inputSchema.get('properties', {})
                if properties:
                    print(f"    Parameters:")
                    for param_name, param_info in properties.items():
                        req_marker = "*" if param_name in required else " "
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        print(f"      {req_marker} {param_name} ({param_type}): {param_desc}")

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.inputSchema if hasattr(tool, 'inputSchema') else None
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool with the given arguments.

        Args:
            name: Tool name
            arguments: Dictionary of arguments

        Returns:
            Tool result
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        print(f"\nCalling tool: {name}")
        print(f"Arguments: {json.dumps(arguments, indent=2)}")

        result = await self.session.call_tool(name, arguments)

        print(f"Result:")
        for content in result.content:
            if hasattr(content, 'text'):
                print(content.text)
            else:
                print(content)

        return result

    # ========================================================================
    # RESOURCE OPERATIONS
    # ========================================================================

    async def list_resources(self) -> list[dict]:
        """List all available resources on the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.list_resources()

        print(f"\nFound {len(result.resources)} resources:")
        for resource in result.resources:
            print(f"\n  {resource.uri}")
            print(f"    Name: {resource.name}")
            print(f"    Description: {resource.description}")
            print(f"    Type: {resource.mimeType}")

        return [
            {
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mimeType
            }
            for resource in result.resources
        ]

    async def read_resource(self, uri: str) -> str:
        """
        Read a resource from the server.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        print(f"\nReading resource: {uri}")

        result = await self.session.read_resource(uri)

        print(f"Content:")
        for content in result.contents:
            if hasattr(content, 'text'):
                print(content.text)
            elif hasattr(content, 'blob'):
                print(f"<binary data: {len(content.blob)} bytes>")
            else:
                print(content)

        return result

    # ========================================================================
    # PROMPT OPERATIONS
    # ========================================================================

    async def list_prompts(self) -> list[dict]:
        """List all available prompt templates on the server."""
        if not self.session:
            raise RuntimeError("Not connected to server")

        result = await self.session.list_prompts()

        print(f"\nFound {len(result.prompts)} prompts:")
        for prompt in result.prompts:
            print(f"\n  {prompt.name}")
            print(f"    Description: {prompt.description}")
            if hasattr(prompt, 'arguments') and prompt.arguments:
                print(f"    Arguments:")
                for arg in prompt.arguments:
                    req_marker = "*" if arg.get('required', False) else " "
                    print(f"      {req_marker} {arg['name']}: {arg.get('description', '')}")

        return [
            {
                "name": prompt.name,
                "description": prompt.description,
                "arguments": prompt.arguments if hasattr(prompt, 'arguments') else []
            }
            for prompt in result.prompts
        ]

    async def get_prompt(self, name: str, arguments: dict[str, str] = None) -> Any:
        """
        Get a prompt template with the given arguments.

        Args:
            name: Prompt name
            arguments: Dictionary of arguments

        Returns:
            Generated prompt
        """
        if not self.session:
            raise RuntimeError("Not connected to server")

        print(f"\nGetting prompt: {name}")
        if arguments:
            print(f"Arguments: {json.dumps(arguments, indent=2)}")

        result = await self.session.get_prompt(name, arguments)

        print(f"Description: {result.description}")
        print(f"Messages:")
        for message in result.messages:
            print(f"  Role: {message.role}")
            print(f"  Content: {message.content.text if hasattr(message.content, 'text') else message.content}")

        return result


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

async def example_hello_world_server():
    """
    Example: Connect to hello-world-server and demonstrate basic usage.
    """
    print("=" * 60)
    print("Example: Hello World Server")
    print("=" * 60)

    client = MCPClient()

    # Connect to the server
    async with client.connect_to_server("python", ["../hello-world-server/main.py"]):

        # List and call tools
        print("\n" + "=" * 60)
        print("TOOLS")
        print("=" * 60)
        await client.list_tools()

        await client.call_tool("greet", {
            "name": "Alice",
            "language": "spanish"
        })

        # List and read resources
        print("\n" + "=" * 60)
        print("RESOURCES")
        print("=" * 60)
        await client.list_resources()

        await client.read_resource("welcome://message")

        # List and use prompts
        print("\n" + "=" * 60)
        print("PROMPTS")
        print("=" * 60)
        await client.list_prompts()

        await client.get_prompt("greeting-prompt", {
            "name": "Bob",
            "style": "enthusiastic"
        })


async def example_full_server():
    """
    Example: Connect to full-server and demonstrate advanced features.
    """
    print("\n\n")
    print("=" * 60)
    print("Example: Full-Featured Server")
    print("=" * 60)

    client = MCPClient()

    async with client.connect_to_server("python", ["../full-server/main.py"]):

        # Task management workflow
        print("\n" + "=" * 60)
        print("TASK MANAGEMENT WORKFLOW")
        print("=" * 60)

        # Add tasks
        await client.call_tool("add_task", {
            "title": "Build MCP integration",
            "description": "Integrate MCP into the application",
            "priority": "high",
            "due_date": "2026-03-15"
        })

        await client.call_tool("add_task", {
            "title": "Write documentation",
            "description": "Document MCP usage and examples",
            "priority": "medium"
        })

        # List tasks
        await client.call_tool("list_tasks", {})

        # Complete a task
        await client.call_tool("complete_task", {
            "task_id": 0
        })

        # Text analysis
        print("\n" + "=" * 60)
        print("TEXT ANALYSIS")
        print("=" * 60)

        await client.call_tool("analyze_text", {
            "text": "The Model Context Protocol enables seamless integration between AI models and external tools. It provides a standardized way to expose capabilities and exchange information.",
            "include_details": True
        })

        # Batch processing
        print("\n" + "=" * 60)
        print("BATCH PROCESSING")
        print("=" * 60)

        await client.call_tool("process_batch", {
            "items": ["Hello", "MCP", "World"],
            "operation": "uppercase"
        })

        # Note taking
        print("\n" + "=" * 60)
        print("NOTE TAKING")
        print("=" * 60)

        await client.call_tool("save_note", {
            "key": "mcp-learnings",
            "content": "MCP provides a powerful abstraction for tool integration. Key concepts: tools, resources, prompts.",
            "tags": ["mcp", "learning", "integration"]
        })

        # Read note as resource
        await client.read_resource("notes://mcp-learnings")

        # Get statistics
        print("\n" + "=" * 60)
        print("SERVER STATISTICS")
        print("=" * 60)

        await client.call_tool("get_stats", {
            "include_details": True
        })

        # Use prompts
        print("\n" + "=" * 60)
        print("PROMPT TEMPLATES")
        print("=" * 60)

        await client.get_prompt("task-planning", {
            "project_name": "MCP Integration",
            "goal": "Full MCP support in the application",
            "complexity": "medium"
        })


async def example_custom_server(command: str, args: list[str]):
    """
    Example: Connect to a custom server and explore its capabilities.

    Args:
        command: Command to run the server
        args: Arguments for the command
    """
    print("=" * 60)
    print("Example: Custom Server")
    print("=" * 60)

    client = MCPClient()

    async with client.connect_to_server(command, args):

        # Auto-discover and display all capabilities
        print("\n" + "=" * 60)
        print("SERVER CAPABILITIES")
        print("=" * 60)

        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()

        print(f"\nSummary:")
        print(f"  Tools: {len(tools)}")
        print(f"  Resources: {len(resources)}")
        print(f"  Prompts: {len(prompts)}")


# ============================================================================
# INTERACTIVE MODE
# ============================================================================

async def interactive_mode(command: str, args: list[str]):
    """
    Interactive REPL for exploring an MCP server.

    Args:
        command: Command to run the server
        args: Arguments for the command
    """
    print("=" * 60)
    print("MCP Interactive Client")
    print("=" * 60)
    print("\nCommands:")
    print("  tools              - List tools")
    print("  resources          - List resources")
    print("  prompts            - List prompts")
    print("  call <tool> <json> - Call a tool")
    print("  read <uri>         - Read a resource")
    print("  prompt <name> <json> - Get a prompt")
    print("  quit               - Exit")
    print("=" * 60)

    client = MCPClient()

    async with client.connect_to_server(command, args):

        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                parts = user_input.split(maxsplit=2)
                cmd = parts[0].lower()

                if cmd == "quit":
                    break

                elif cmd == "tools":
                    await client.list_tools()

                elif cmd == "resources":
                    await client.list_resources()

                elif cmd == "prompts":
                    await client.list_prompts()

                elif cmd == "call" and len(parts) >= 3:
                    tool_name = parts[1]
                    args_json = parts[2]
                    arguments = json.loads(args_json)
                    await client.call_tool(tool_name, arguments)

                elif cmd == "read" and len(parts) >= 2:
                    uri = parts[1]
                    await client.read_resource(uri)

                elif cmd == "prompt" and len(parts) >= 3:
                    prompt_name = parts[1]
                    args_json = parts[2]
                    arguments = json.loads(args_json)
                    await client.get_prompt(prompt_name, arguments)

                else:
                    print("Unknown command or invalid syntax")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for the client examples."""

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python stdio_client.py hello       - Run hello-world-server examples")
        print("  python stdio_client.py full        - Run full-server examples")
        print("  python stdio_client.py interactive <command> [args...] - Interactive mode")
        print("  python stdio_client.py custom <command> [args...] - Connect to custom server")
        print("\nExamples:")
        print("  python stdio_client.py hello")
        print("  python stdio_client.py full")
        print("  python stdio_client.py interactive python ../hello-world-server/main.py")
        print("  python stdio_client.py custom python my_server.py")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "hello":
        await example_hello_world_server()

    elif mode == "full":
        await example_full_server()

    elif mode == "interactive":
        if len(sys.argv) < 3:
            print("Error: interactive mode requires server command")
            sys.exit(1)
        command = sys.argv[2]
        args = sys.argv[3:] if len(sys.argv) > 3 else []
        await interactive_mode(command, args)

    elif mode == "custom":
        if len(sys.argv) < 3:
            print("Error: custom mode requires server command")
            sys.exit(1)
        command = sys.argv[2]
        args = sys.argv[3:] if len(sys.argv) > 3 else []
        await example_custom_server(command, args)

    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        raise
