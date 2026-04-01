#!/usr/bin/env python3
"""
Full-Featured MCP Server Template
==================================

A comprehensive MCP server demonstrating all major features:
- Multiple tools with various input/output types
- Dynamic and static resources
- Sophisticated prompt templates
- Progress reporting for long-running operations
- Comprehensive error handling and logging
- Input validation
- Resource management

This template showcases production-ready patterns for building robust MCP servers.
"""

import asyncio
import logging
import json
import time
from typing import Any, AsyncIterator
from datetime import datetime
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    Prompt,
    PromptMessage,
    GetPromptResult,
    LoggingLevel,
)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("full-featured-server")

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

server = Server("full-featured-server")

# In-memory data store (replace with database in production)
data_store = {
    "tasks": [],
    "notes": {},
    "counters": {"api_calls": 0, "errors": 0}
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_input(value: Any, field_name: str, expected_type: type) -> None:
    """Validate input parameters."""
    if not isinstance(value, expected_type):
        raise ValueError(
            f"Invalid {field_name}: expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )


async def simulate_long_operation(duration: float, task_name: str) -> AsyncIterator[float]:
    """Simulate a long-running operation with progress updates."""
    steps = 10
    for i in range(steps):
        await asyncio.sleep(duration / steps)
        progress = (i + 1) / steps
        logger.info(f"{task_name}: {progress * 100:.0f}% complete")
        yield progress


def log_to_client(level: LoggingLevel, message: str, data: dict | None = None) -> None:
    """Send structured logs to the client."""
    log_data = {"message": message, "timestamp": datetime.now().isoformat()}
    if data:
        log_data.update(data)

    # In a real implementation, this would use server.send_log_message()
    logger.log(
        level=getattr(logging, level.upper()),
        msg=json.dumps(log_data)
    )


# ============================================================================
# TOOLS - Multiple tools demonstrating various patterns
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        # Simple CRUD operations
        Tool(
            name="add_task",
            description="Add a new task to the task list",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Task priority level",
                        "default": "medium"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date in ISO format (YYYY-MM-DD)",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    }
                },
                "required": ["title"]
            }
        ),

        Tool(
            name="list_tasks",
            description="List all tasks, optionally filtered by priority",
            inputSchema={
                "type": "object",
                "properties": {
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Filter by priority (optional)"
                    },
                    "completed": {
                        "type": "boolean",
                        "description": "Filter by completion status (optional)"
                    }
                }
            }
        ),

        Tool(
            name="complete_task",
            description="Mark a task as completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to complete",
                        "minimum": 0
                    }
                },
                "required": ["task_id"]
            }
        ),

        # Data processing tool
        Tool(
            name="analyze_text",
            description="Analyze text and return statistics (word count, character count, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze"
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed analysis (sentence count, average word length)",
                        "default": False
                    }
                },
                "required": ["text"]
            }
        ),

        # Long-running operation with progress
        Tool(
            name="process_batch",
            description="Process a batch of items (demonstrates progress reporting)",
            inputSchema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Items to process"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["uppercase", "lowercase", "reverse", "count"],
                        "description": "Operation to perform on each item"
                    }
                },
                "required": ["items", "operation"]
            }
        ),

        # Note-taking tool
        Tool(
            name="save_note",
            description="Save a note with a unique key",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Unique key for the note"
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    }
                },
                "required": ["key", "content"]
            }
        ),

        # System information tool
        Tool(
            name="get_stats",
            description="Get server statistics and performance metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed metrics",
                        "default": False
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution with comprehensive error handling."""
    try:
        # Increment API call counter
        data_store["counters"]["api_calls"] += 1

        log_to_client(
            LoggingLevel.INFO,
            f"Tool called: {name}",
            {"arguments": arguments}
        )

        # Route to appropriate handler
        if name == "add_task":
            return await handle_add_task(arguments)
        elif name == "list_tasks":
            return await handle_list_tasks(arguments)
        elif name == "complete_task":
            return await handle_complete_task(arguments)
        elif name == "analyze_text":
            return await handle_analyze_text(arguments)
        elif name == "process_batch":
            return await handle_process_batch(arguments)
        elif name == "save_note":
            return await handle_save_note(arguments)
        elif name == "get_stats":
            return await handle_get_stats(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        data_store["counters"]["errors"] += 1
        log_to_client(
            LoggingLevel.ERROR,
            f"Error executing tool {name}",
            {"error": str(e)}
        )
        raise


# ============================================================================
# TOOL HANDLERS
# ============================================================================

async def handle_add_task(args: dict) -> list[TextContent]:
    """Add a new task."""
    task = {
        "id": len(data_store["tasks"]),
        "title": args["title"],
        "description": args.get("description", ""),
        "priority": args.get("priority", "medium"),
        "due_date": args.get("due_date"),
        "completed": False,
        "created_at": datetime.now().isoformat()
    }

    data_store["tasks"].append(task)
    logger.info(f"Created task: {task['title']}")

    return [
        TextContent(
            type="text",
            text=f"Task created successfully!\n\n{json.dumps(task, indent=2)}"
        )
    ]


async def handle_list_tasks(args: dict) -> list[TextContent]:
    """List tasks with optional filtering."""
    tasks = data_store["tasks"]

    # Apply filters
    if "priority" in args:
        tasks = [t for t in tasks if t["priority"] == args["priority"]]

    if "completed" in args:
        tasks = [t for t in tasks if t["completed"] == args["completed"]]

    if not tasks:
        return [TextContent(type="text", text="No tasks found matching criteria.")]

    # Format task list
    task_list = "\n\n".join([
        f"Task #{t['id']}: {t['title']}\n"
        f"  Priority: {t['priority']}\n"
        f"  Status: {'✓ Completed' if t['completed'] else '○ Pending'}\n"
        f"  Due: {t['due_date'] or 'Not set'}"
        for t in tasks
    ])

    return [
        TextContent(
            type="text",
            text=f"Found {len(tasks)} task(s):\n\n{task_list}"
        )
    ]


async def handle_complete_task(args: dict) -> list[TextContent]:
    """Mark a task as completed."""
    task_id = args["task_id"]

    if task_id >= len(data_store["tasks"]):
        raise ValueError(f"Task {task_id} not found")

    task = data_store["tasks"][task_id]
    task["completed"] = True
    task["completed_at"] = datetime.now().isoformat()

    logger.info(f"Completed task: {task['title']}")

    return [
        TextContent(
            type="text",
            text=f"Task #{task_id} '{task['title']}' marked as completed!"
        )
    ]


async def handle_analyze_text(args: dict) -> list[TextContent]:
    """Analyze text and return statistics."""
    text = args["text"]
    include_details = args.get("include_details", False)

    # Basic stats
    words = text.split()
    stats = {
        "characters": len(text),
        "words": len(words),
        "lines": len(text.splitlines())
    }

    # Detailed stats
    if include_details:
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        stats["sentences"] = len(sentences)
        stats["avg_word_length"] = sum(len(w) for w in words) / len(words) if words else 0
        stats["avg_sentence_length"] = len(words) / len(sentences) if sentences else 0

    return [
        TextContent(
            type="text",
            text=f"Text Analysis Results:\n\n{json.dumps(stats, indent=2)}"
        )
    ]


async def handle_process_batch(args: dict) -> list[TextContent]:
    """Process batch items with progress reporting."""
    items = args["items"]
    operation = args["operation"]

    results = []
    total = len(items)

    # Simulate processing with progress updates
    for i, item in enumerate(items):
        # Process item based on operation
        if operation == "uppercase":
            result = item.upper()
        elif operation == "lowercase":
            result = item.lower()
        elif operation == "reverse":
            result = item[::-1]
        elif operation == "count":
            result = f"{item}: {len(item)} characters"
        else:
            result = item

        results.append(result)

        # Simulate processing time and log progress
        await asyncio.sleep(0.1)
        progress = (i + 1) / total * 100
        logger.info(f"Batch processing: {progress:.0f}% complete ({i + 1}/{total})")

    return [
        TextContent(
            type="text",
            text=f"Batch processing complete!\n\nOperation: {operation}\n"
                 f"Processed {total} items\n\n"
                 f"Results:\n{json.dumps(results, indent=2)}"
        )
    ]


async def handle_save_note(args: dict) -> list[TextContent]:
    """Save a note with metadata."""
    key = args["key"]
    note = {
        "content": args["content"],
        "tags": args.get("tags", []),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    data_store["notes"][key] = note
    logger.info(f"Saved note: {key}")

    return [
        TextContent(
            type="text",
            text=f"Note saved successfully!\n\nKey: {key}\nTags: {', '.join(note['tags'])}"
        )
    ]


async def handle_get_stats(args: dict) -> list[TextContent]:
    """Get server statistics."""
    include_details = args.get("include_details", False)

    stats = {
        "api_calls": data_store["counters"]["api_calls"],
        "errors": data_store["counters"]["errors"],
        "tasks": {
            "total": len(data_store["tasks"]),
            "completed": sum(1 for t in data_store["tasks"] if t["completed"]),
            "pending": sum(1 for t in data_store["tasks"] if not t["completed"])
        },
        "notes": len(data_store["notes"])
    }

    if include_details:
        stats["uptime"] = "N/A (in-memory server)"
        stats["memory_usage"] = "N/A"
        stats["task_breakdown"] = {
            "by_priority": {
                priority: sum(1 for t in data_store["tasks"] if t["priority"] == priority)
                for priority in ["low", "medium", "high", "urgent"]
            }
        }

    return [
        TextContent(
            type="text",
            text=f"Server Statistics:\n\n{json.dumps(stats, indent=2)}"
        )
    ]


# ============================================================================
# RESOURCES - Dynamic and static resources
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    resources = [
        # Static documentation
        Resource(
            uri="docs://getting-started",
            name="Getting Started Guide",
            description="Introduction to using this MCP server",
            mimeType="text/markdown"
        ),

        Resource(
            uri="docs://api-reference",
            name="API Reference",
            description="Complete API documentation",
            mimeType="text/markdown"
        ),

        # Dynamic resources
        Resource(
            uri="data://tasks",
            name="All Tasks",
            description="Complete list of all tasks in JSON format",
            mimeType="application/json"
        ),

        Resource(
            uri="data://stats",
            name="Server Statistics",
            description="Real-time server statistics",
            mimeType="application/json"
        )
    ]

    # Add a resource for each saved note
    for key in data_store["notes"]:
        resources.append(
            Resource(
                uri=f"notes://{key}",
                name=f"Note: {key}",
                description=f"Saved note with key '{key}'",
                mimeType="text/plain"
            )
        )

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content."""
    logger.info(f"Reading resource: {uri}")

    # Static documentation
    if uri == "docs://getting-started":
        return """
# Getting Started with Full-Featured MCP Server

## Overview
This server provides a comprehensive example of MCP capabilities including:
- Task management
- Text analysis
- Batch processing
- Note-taking
- Server statistics

## Quick Start

### Adding a Task
Use the `add_task` tool:
```json
{
  "title": "My First Task",
  "description": "Learn about MCP",
  "priority": "high"
}
```

### Analyzing Text
Use the `analyze_text` tool:
```json
{
  "text": "Your text here",
  "include_details": true
}
```

### Saving Notes
Use the `save_note` tool:
```json
{
  "key": "meeting-notes",
  "content": "Discussion points...",
  "tags": ["work", "important"]
}
```

See the API Reference for complete documentation.
"""

    elif uri == "docs://api-reference":
        return """
# API Reference

## Tools

### Task Management
- `add_task` - Create a new task
- `list_tasks` - List all tasks with optional filters
- `complete_task` - Mark task as complete

### Text Processing
- `analyze_text` - Analyze text statistics
- `process_batch` - Process multiple items with progress tracking

### Data Storage
- `save_note` - Save notes with tags

### Server Info
- `get_stats` - Get server statistics

## Resources

### Documentation
- `docs://getting-started` - Getting started guide
- `docs://api-reference` - This document

### Data
- `data://tasks` - All tasks (JSON)
- `data://stats` - Server statistics (JSON)
- `notes://{key}` - Individual notes

## Prompts

- `task-planning` - Generate task breakdown
- `text-improvement` - Suggest text improvements
- `note-summary` - Summarize notes
"""

    # Dynamic data resources
    elif uri == "data://tasks":
        return json.dumps(data_store["tasks"], indent=2)

    elif uri == "data://stats":
        stats = await handle_get_stats({"include_details": True})
        return stats[0].text

    # Note resources
    elif uri.startswith("notes://"):
        key = uri.replace("notes://", "")
        if key not in data_store["notes"]:
            raise ValueError(f"Note not found: {key}")

        note = data_store["notes"][key]
        return f"# Note: {key}\n\n{note['content']}\n\nTags: {', '.join(note['tags'])}\nCreated: {note['created_at']}"

    else:
        raise ValueError(f"Unknown resource: {uri}")


# ============================================================================
# PROMPTS - Sophisticated prompt templates
# ============================================================================

@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompt templates."""
    return [
        Prompt(
            name="task-planning",
            description="Generate a detailed task breakdown for a project",
            arguments=[
                {
                    "name": "project_name",
                    "description": "Name of the project",
                    "required": True
                },
                {
                    "name": "goal",
                    "description": "Main goal or objective",
                    "required": True
                },
                {
                    "name": "complexity",
                    "description": "Project complexity level",
                    "required": False
                }
            ]
        ),

        Prompt(
            name="text-improvement",
            description="Get suggestions for improving text",
            arguments=[
                {
                    "name": "text",
                    "description": "Text to improve",
                    "required": True
                },
                {
                    "name": "style",
                    "description": "Target style (professional, casual, academic)",
                    "required": False
                }
            ]
        ),

        Prompt(
            name="note-summary",
            description="Summarize multiple notes",
            arguments=[
                {
                    "name": "note_keys",
                    "description": "Comma-separated note keys to summarize",
                    "required": True
                },
                {
                    "name": "format",
                    "description": "Summary format (brief, detailed, bullet-points)",
                    "required": False
                }
            ]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Generate prompts from templates."""
    logger.info(f"Generating prompt: {name}")

    if name == "task-planning":
        project_name = arguments.get("project_name", "Unnamed Project") if arguments else "Unnamed Project"
        goal = arguments.get("goal", "Complete the project") if arguments else "Complete the project"
        complexity = arguments.get("complexity", "medium") if arguments else "medium"

        prompt_text = f"""Please create a detailed task breakdown for the following project:

Project: {project_name}
Goal: {goal}
Complexity: {complexity}

Generate a comprehensive list of tasks including:
1. High-level milestones
2. Specific actionable tasks
3. Dependencies between tasks
4. Estimated priority levels
5. Suggested timeline

Format the output as a structured task list that can be used with the add_task tool."""

        return GetPromptResult(
            description=f"Task planning for {project_name}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )

    elif name == "text-improvement":
        text = arguments.get("text", "") if arguments else ""
        style = arguments.get("style", "professional") if arguments else "professional"

        prompt_text = f"""Please analyze the following text and provide improvement suggestions:

Text:
{text}

Target Style: {style}

Provide:
1. Overall assessment
2. Specific improvement suggestions
3. Rewritten version
4. Explanation of changes

Focus on clarity, tone, grammar, and effectiveness."""

        return GetPromptResult(
            description="Text improvement suggestions",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )

    elif name == "note-summary":
        note_keys = arguments.get("note_keys", "").split(",") if arguments else []
        summary_format = arguments.get("format", "detailed") if arguments else "detailed"

        # Gather note contents
        note_contents = []
        for key in note_keys:
            key = key.strip()
            if key in data_store["notes"]:
                note = data_store["notes"][key]
                note_contents.append(f"## {key}\n{note['content']}")

        all_notes = "\n\n".join(note_contents) if note_contents else "No notes found"

        prompt_text = f"""Please summarize the following notes:

{all_notes}

Format: {summary_format}

Provide a {summary_format} summary that captures:
1. Main themes and topics
2. Key points from each note
3. Connections between notes
4. Action items or next steps (if any)"""

        return GetPromptResult(
            description=f"Summary of {len(note_contents)} note(s)",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )

    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# SERVER LIFECYCLE
# ============================================================================

async def main():
    """Run the MCP server with full initialization."""
    logger.info("=" * 60)
    logger.info("Starting Full-Featured MCP Server")
    logger.info("=" * 60)
    logger.info("Capabilities:")
    logger.info("  - Tools: 7 (task management, text analysis, batch processing)")
    logger.info("  - Resources: Dynamic (docs, data, notes)")
    logger.info("  - Prompts: 3 (task planning, text improvement, summaries)")
    logger.info("  - Features: Progress reporting, logging, error handling")
    logger.info("=" * 60)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
