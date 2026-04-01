#!/usr/bin/env python3
"""
Minimal MCP Server Template
============================

A simple "Hello World" MCP server demonstrating:
- One tool (greet)
- One resource (welcome message)
- One prompt template (greeting)

This is the simplest possible MCP server to get started.
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    PromptMessage,
    GetPromptResult,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hello-world-server")

# Create the MCP server instance
server = Server("hello-world-server")


# ============================================================================
# TOOLS - Functions that can be called by clients
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="greet",
            description="Generate a personalized greeting message",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the person to greet"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["english", "spanish", "french"],
                        "description": "Language for the greeting",
                        "default": "english"
                    }
                },
                "required": ["name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution."""
    if name != "greet":
        raise ValueError(f"Unknown tool: {name}")

    # Extract arguments
    person_name = arguments.get("name", "World")
    language = arguments.get("language", "english")

    # Generate greeting based on language
    greetings = {
        "english": f"Hello, {person_name}!",
        "spanish": f"¡Hola, {person_name}!",
        "french": f"Bonjour, {person_name}!"
    }

    greeting = greetings.get(language, greetings["english"])
    logger.info(f"Generated greeting: {greeting}")

    return [
        TextContent(
            type="text",
            text=greeting
        )
    ]


# ============================================================================
# RESOURCES - Static content that can be read by clients
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="welcome://message",
            name="Welcome Message",
            description="A welcome message for new users",
            mimeType="text/plain"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    if uri != "welcome://message":
        raise ValueError(f"Unknown resource: {uri}")

    welcome_text = """
Welcome to the Hello World MCP Server!

This server demonstrates the basic building blocks of MCP:

1. Tools - Functions that can be called (like 'greet')
2. Resources - Static content that can be read (like this message)
3. Prompts - Templates for generating prompts

Try calling the 'greet' tool with your name!
"""

    logger.info("Welcome resource accessed")
    return welcome_text.strip()


# ============================================================================
# PROMPTS - Templates for generating AI prompts
# ============================================================================

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompt templates."""
    return [
        Prompt(
            name="greeting-prompt",
            description="Generate a prompt for creating a personalized greeting",
            arguments=[
                {
                    "name": "name",
                    "description": "Name of the person to greet",
                    "required": True
                },
                {
                    "name": "style",
                    "description": "Style of greeting (formal, casual, enthusiastic)",
                    "required": False
                }
            ]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Generate a prompt from a template."""
    if name != "greeting-prompt":
        raise ValueError(f"Unknown prompt: {name}")

    person_name = arguments.get("name", "friend") if arguments else "friend"
    style = arguments.get("style", "casual") if arguments else "casual"

    # Create different prompts based on style
    style_templates = {
        "formal": f"Please compose a formal greeting message for {person_name}, suitable for a professional setting.",
        "casual": f"Write a friendly, casual greeting for {person_name}.",
        "enthusiastic": f"Create an enthusiastic and energetic greeting for {person_name}!"
    }

    prompt_text = style_templates.get(style, style_templates["casual"])

    return GetPromptResult(
        description=f"Greeting prompt for {person_name}",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=prompt_text)
            )
        ]
    )


# ============================================================================
# SERVER STARTUP
# ============================================================================

async def main():
    """Run the MCP server."""
    logger.info("Starting Hello World MCP Server...")
    logger.info("Server capabilities: tools, resources, prompts")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
