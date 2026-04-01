# MCP Core Concepts Reference

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [JSON-RPC Protocol](#json-rpc-protocol)
4. [Capabilities](#capabilities)
5. [Primitives](#primitives)
6. [Message Types](#message-types)
7. [Error Handling](#error-handling)
8. [Security Model](#security-model)
9. [Best Practices](#best-practices)

## Overview

The Model Context Protocol (MCP) is an open protocol that standardizes how AI applications communicate with external data sources and tools. MCP enables:

- **Contextual Information**: LLMs can access relevant data sources
- **Tool Execution**: LLMs can perform actions through standardized tools
- **Prompt Templates**: Reusable prompt structures for common tasks
- **Interoperability**: Any MCP-compatible client can connect to any MCP server

### Key Principles

1. **Stateful Connections**: Maintain context across multiple interactions
2. **Capability Negotiation**: Clients and servers declare their features
3. **Asynchronous Communication**: Non-blocking operations throughout
4. **Type Safety**: Strongly typed messages and responses
5. **Extensibility**: Easy to add new primitives and capabilities

## Architecture

### Three-Layer Model

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│  (LLM, AI Agent, Application Logic)     │
├─────────────────────────────────────────┤
│         Protocol Layer (MCP)            │
│  (Capabilities, Primitives, Messages)   │
├─────────────────────────────────────────┤
│         Transport Layer                 │
│  (Stdio, HTTP SSE, Custom)              │
└─────────────────────────────────────────┘
```

### Client-Server Model

```
┌──────────────┐                    ┌──────────────┐
│              │   1. Initialize    │              │
│              │ ──────────────────>│              │
│              │                    │              │
│              │   2. Capabilities  │              │
│    Client    │ <──────────────────│    Server    │
│              │                    │              │
│              │   3. Requests      │              │
│              │ ──────────────────>│              │
│              │                    │              │
│              │   4. Responses     │              │
│              │ <──────────────────│              │
└──────────────┘                    └──────────────┘
```

### Multi-Server Architecture

```
                ┌──────────────┐
                │              │
                │    Client    │
                │              │
                └───────┬──────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        v               v               v
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ FileSystem   │ │  Database    │ │   Web API    │
│   Server     │ │   Server     │ │   Server     │
└──────────────┘ └──────────────┘ └──────────────┘
```

## JSON-RPC Protocol

MCP uses JSON-RPC 2.0 for all communication.

### Request Format

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "calculate",
    "arguments": {
      "operation": "add",
      "x": 5,
      "y": 3
    }
  },
  "id": 1
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Result: 8"
      }
    ]
  },
  "id": 1
}
```

### Notification Format

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/progress",
  "params": {
    "progress": 50,
    "total": 100,
    "message": "Processing..."
  }
}
```

### Error Format

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid parameters",
    "data": {
      "details": "Parameter 'x' must be a number"
    }
  },
  "id": 1
}
```

### Standard Methods

#### Lifecycle Methods

```python
# Initialize connection
{
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {"listChanged": true},
      "sampling": {}
    },
    "clientInfo": {
      "name": "ExampleClient",
      "version": "1.0.0"
    }
  }
}

# Server response
{
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "resources": {},
      "tools": {},
      "prompts": {}
    },
    "serverInfo": {
      "name": "ExampleServer",
      "version": "1.0.0"
    }
  }
}
```

#### Resource Methods

```python
# List resources
{"method": "resources/list", "params": {}}

# Read resource
{
  "method": "resources/read",
  "params": {
    "uri": "file:///data/config.json"
  }
}

# List resource templates
{"method": "resources/templates/list", "params": {}}

# Subscribe to resource
{
  "method": "resources/subscribe",
  "params": {
    "uri": "file:///data/config.json"
  }
}

# Unsubscribe from resource
{
  "method": "resources/unsubscribe",
  "params": {
    "uri": "file:///data/config.json"
  }
}
```

#### Prompt Methods

```python
# List prompts
{"method": "prompts/list", "params": {}}

# Get prompt
{
  "method": "prompts/get",
  "params": {
    "name": "code_review",
    "arguments": {
      "language": "python",
      "code": "def hello(): pass"
    }
  }
}
```

#### Tool Methods

```python
# List tools
{"method": "tools/list", "params": {}}

# Call tool
{
  "method": "tools/call",
  "params": {
    "name": "search_database",
    "arguments": {
      "query": "active users",
      "limit": 10
    }
  }
}
```

## Capabilities

Capabilities define what features a client or server supports.

### Server Capabilities

```python
from mcp.types import ServerCapabilities

capabilities = ServerCapabilities(
    # Resource support
    resources={
        "subscribe": True,  # Supports resource subscriptions
        "listChanged": True  # Can notify of resource list changes
    },

    # Prompt support
    prompts={
        "listChanged": True  # Can notify of prompt list changes
    },

    # Tool support
    tools={
        "listChanged": True  # Can notify of tool list changes
    },

    # Logging support
    logging={}
)
```

### Client Capabilities

```python
from mcp.types import ClientCapabilities

capabilities = ClientCapabilities(
    # Root support
    roots={
        "listChanged": True  # Can notify when roots change
    },

    # Sampling support (for prompts)
    sampling={},

    # Experimental features
    experimental={}
)
```

### Capability Negotiation

```python
# Python server with capabilities
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "my-server",
    capabilities={
        "resources": {"subscribe": True},
        "tools": {},
        "prompts": {}
    }
)

# TypeScript server with capabilities
import { Server } from "@modelcontextprotocol/sdk/server/index.js";

const server = new Server(
  {
    name: "my-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      resources: { subscribe: true },
      tools: {},
      prompts: {},
    },
  }
);
```

## Primitives

MCP defines three core primitives for communication.

### 1. Resources

Resources represent data that can be read by the client.

#### Resource Structure

```python
from mcp.types import Resource

resource = Resource(
    uri="file:///data/config.json",
    name="Configuration",
    description="Application configuration file",
    mimeType="application/json"
)
```

#### Resource Content

```python
from mcp.types import TextContent, BlobContent, ImageContent
import base64

# Text content
text_content = TextContent(
    type="text",
    text="Configuration data here",
    uri="file:///data/config.json",
    mimeType="application/json"
)

# Binary content
blob_content = BlobContent(
    type="blob",
    blob=base64.b64encode(binary_data).decode(),
    uri="file:///data/image.png",
    mimeType="image/png"
)

# Image content (special case of blob)
image_content = ImageContent(
    type="image",
    data=base64.b64encode(image_data).decode(),
    mimeType="image/png"
)
```

#### Resource Templates

```python
from mcp.types import ResourceTemplate

template = ResourceTemplate(
    uriTemplate="file:///{path}",
    name="File Access",
    description="Read any file from the filesystem",
    mimeType="text/plain"
)
```

### 2. Prompts

Prompts are templated messages for LLM interactions.

#### Prompt Structure

```python
from mcp.types import Prompt, PromptArgument

prompt = Prompt(
    name="code_review",
    description="Generate code review prompt",
    arguments=[
        PromptArgument(
            name="language",
            description="Programming language",
            required=True
        ),
        PromptArgument(
            name="code",
            description="Code to review",
            required=True
        )
    ]
)
```

#### Prompt Messages

```python
from mcp.types import PromptMessage, TextContent

messages = [
    PromptMessage(
        role="user",
        content=TextContent(
            type="text",
            text=f"Please review this {language} code:\n\n{code}"
        )
    ),
    PromptMessage(
        role="assistant",
        content=TextContent(
            type="text",
            text="I'll review this code for quality, bugs, and best practices."
        )
    ),
    PromptMessage(
        role="user",
        content=TextContent(
            type="text",
            text="Focus on security concerns."
        )
    )
]
```

### 3. Tools

Tools are functions that can be called by the LLM.

#### Tool Structure

```python
from mcp.types import Tool

tool = Tool(
    name="search_database",
    description="Search database for records",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "table": {
                "type": "string",
                "description": "Database table"
            },
            "limit": {
                "type": "number",
                "description": "Max results",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["query", "table"]
    }
)
```

#### Tool Result

```python
from mcp.types import CallToolResult, TextContent

result = CallToolResult(
    content=[
        TextContent(
            type="text",
            text="Found 5 matching records:\n1. User A\n2. User B\n..."
        )
    ],
    isError=False
)
```

## Message Types

### Request Messages

```python
from mcp.types import (
    InitializeRequest,
    ListResourcesRequest,
    ReadResourceRequest,
    ListPromptsRequest,
    GetPromptRequest,
    ListToolsRequest,
    CallToolRequest
)

# Initialize
init_request = InitializeRequest(
    method="initialize",
    params={
        "protocolVersion": "2024-11-05",
        "capabilities": {...},
        "clientInfo": {...}
    }
)

# Call tool
tool_request = CallToolRequest(
    method="tools/call",
    params={
        "name": "calculate",
        "arguments": {"x": 5, "y": 3}
    }
)
```

### Response Messages

```python
from mcp.types import (
    InitializeResult,
    ListResourcesResult,
    ReadResourceResult,
    CallToolResult
)

# Initialize response
init_result = InitializeResult(
    protocolVersion="2024-11-05",
    capabilities={...},
    serverInfo={...}
)

# Tool call response
tool_result = CallToolResult(
    content=[
        TextContent(type="text", text="Result: 8")
    ]
)
```

### Notification Messages

```python
from mcp.types import (
    ProgressNotification,
    ResourceUpdatedNotification,
    ResourceListChangedNotification
)

# Progress notification
progress = ProgressNotification(
    method="notifications/progress",
    params={
        "progressToken": "task-123",
        "progress": 50,
        "total": 100
    }
)

# Resource updated
resource_updated = ResourceUpdatedNotification(
    method="notifications/resources/updated",
    params={
        "uri": "file:///data/config.json"
    }
)
```

## Error Handling

### Error Codes

MCP uses standard JSON-RPC error codes plus custom codes:

```python
from mcp.types import ErrorCode

# Standard JSON-RPC errors
ErrorCode.PARSE_ERROR = -32700
ErrorCode.INVALID_REQUEST = -32600
ErrorCode.METHOD_NOT_FOUND = -32601
ErrorCode.INVALID_PARAMS = -32602
ErrorCode.INTERNAL_ERROR = -32603

# Custom MCP errors
ErrorCode.RESOURCE_NOT_FOUND = -32001
ErrorCode.RESOURCE_UNAVAILABLE = -32002
ErrorCode.TOOL_NOT_FOUND = -32003
ErrorCode.TOOL_EXECUTION_ERROR = -32004
ErrorCode.PERMISSION_DENIED = -32005
ErrorCode.TIMEOUT = -32006
ErrorCode.RATE_LIMITED = -32007
```

### Error Response

```python
from mcp.types import McpError

# Create error
error = McpError(
    code=ErrorCode.INVALID_PARAMS,
    message="Invalid parameters provided",
    data={
        "parameter": "limit",
        "expected": "number between 1-100",
        "received": "0"
    }
)

# Error response
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid parameters provided",
    "data": {
      "parameter": "limit",
      "expected": "number between 1-100",
      "received": "0"
    }
  },
  "id": 1
}
```

### Error Handling in Code

```python
# Server-side error handling
from mcp.types import McpError, ErrorCode

@mcp.tool()
def validate_and_execute(param: str) -> str:
    """Tool with validation"""
    if not param:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            "Parameter cannot be empty"
        )

    try:
        result = perform_operation(param)
        return result
    except PermissionError:
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            "Insufficient permissions to perform operation"
        )
    except TimeoutError:
        raise McpError(
            ErrorCode.TIMEOUT,
            "Operation timed out"
        )
    except Exception as e:
        raise McpError(
            ErrorCode.INTERNAL_ERROR,
            f"Unexpected error: {str(e)}"
        )

# Client-side error handling
try:
    result = await session.call_tool(
        "validate_and_execute",
        arguments={"param": "value"}
    )
except McpError as e:
    if e.error.code == ErrorCode.INVALID_PARAMS:
        print(f"Invalid input: {e.error.message}")
    elif e.error.code == ErrorCode.PERMISSION_DENIED:
        print("Access denied")
    else:
        print(f"Error: {e.error.message}")
```

## Security Model

### Authentication

MCP does not define authentication mechanisms but supports them at the transport layer.

```python
# HTTP SSE with bearer token
from starlette.middleware.authentication import AuthenticationMiddleware

app = Starlette(
    routes=[...],
    middleware=[
        Middleware(AuthenticationMiddleware, backend=TokenAuthBackend())
    ]
)

# Client with authentication
async with sse_client(
    "http://localhost:8000/sse",
    headers={"Authorization": "Bearer secret-token"}
) as (read, write):
    ...
```

### Authorization

Servers should implement their own authorization logic.

```python
from mcp.types import McpError, ErrorCode

@mcp.tool()
def protected_operation(user_id: str, action: str) -> str:
    """Tool with authorization check"""

    # Check permissions
    if not has_permission(user_id, action):
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            f"User {user_id} does not have permission for action: {action}"
        )

    # Perform operation
    return perform_action(action)
```

### Input Validation

Always validate inputs to prevent injection attacks.

```python
import re
from pathlib import Path

@mcp.resource("file:///{path}")
def read_file_safe(path: str) -> str:
    """Safely read file with validation"""

    # Validate path format
    if not re.match(r'^[a-zA-Z0-9/_.-]+$', path):
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            "Invalid path format"
        )

    # Resolve path
    full_path = (BASE_DIR / path).resolve()

    # Ensure within allowed directory
    if not full_path.is_relative_to(BASE_DIR):
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            "Path outside allowed directory"
        )

    # Read file
    with open(full_path) as f:
        return f.read()
```

### Rate Limiting

Implement rate limiting to prevent abuse.

```python
from collections import defaultdict
from time import time

class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_requests: int, window: int):
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed"""
        now = time()

        # Remove old requests
        self.requests[client_id] = [
            t for t in self.requests[client_id]
            if now - t < self.window
        ]

        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False

        # Record request
        self.requests[client_id].append(now)
        return True

# Use in tool
limiter = RateLimiter(max_requests=100, window=60)

@mcp.tool()
async def rate_limited_tool(client_id: str, data: str) -> str:
    """Tool with rate limiting"""
    if not limiter.is_allowed(client_id):
        raise McpError(
            ErrorCode.RATE_LIMITED,
            "Rate limit exceeded. Try again later."
        )

    return process_data(data)
```

### Secrets Management

Never hardcode secrets; use environment variables or secret managers.

```python
import os
from typing import Optional

class SecretManager:
    """Manage secrets securely"""

    @staticmethod
    def get_secret(name: str) -> str:
        """Get secret from environment"""
        secret = os.getenv(name)
        if not secret:
            raise McpError(
                ErrorCode.INTERNAL_ERROR,
                f"Secret '{name}' not configured"
            )
        return secret

    @staticmethod
    def get_optional_secret(name: str) -> Optional[str]:
        """Get optional secret"""
        return os.getenv(name)

# Usage
@mcp.tool()
async def call_external_api(endpoint: str) -> dict:
    """Call external API with authentication"""

    api_key = SecretManager.get_secret("API_KEY")

    response = await http_client.get(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"}
    )

    return response.json()
```

## Best Practices

### 1. Idempotency

Design tools to be idempotent when possible.

```python
@mcp.tool()
def create_or_update_record(id: str, data: dict) -> dict:
    """Idempotent operation"""

    # Check if exists
    existing = database.get(id)

    if existing:
        # Update existing
        database.update(id, data)
        return {"status": "updated", "id": id}
    else:
        # Create new
        database.create(id, data)
        return {"status": "created", "id": id}
```

### 2. Clear Error Messages

Provide actionable error messages.

```python
@mcp.tool()
def process_file(file_path: str) -> str:
    """Process file with clear errors"""

    if not os.path.exists(file_path):
        raise McpError(
            ErrorCode.RESOURCE_NOT_FOUND,
            f"File not found: {file_path}\n"
            f"Please ensure the file exists and the path is correct."
        )

    if not os.access(file_path, os.R_OK):
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            f"Cannot read file: {file_path}\n"
            f"Please check file permissions."
        )

    try:
        return process(file_path)
    except ValueError as e:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"Invalid file format: {e}\n"
            f"Expected format: JSON"
        )
```

### 3. Progress Reporting

Report progress for long-running operations.

```python
from mcp.types import ProgressNotification

@mcp.tool()
async def process_large_dataset(dataset_id: str) -> str:
    """Process with progress reporting"""

    items = load_dataset(dataset_id)
    total = len(items)

    for i, item in enumerate(items):
        # Process item
        await process_item(item)

        # Report progress every 10%
        if i % (total // 10) == 0:
            await mcp.send_notification(
                ProgressNotification(
                    progress=i,
                    total=total,
                    message=f"Processed {i}/{total} items"
                )
            )

    return f"Processed {total} items successfully"
```

### 4. Resource Cleanup

Always clean up resources properly.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_connection():
    """Managed database connection"""
    conn = await database.connect()
    try:
        yield conn
    finally:
        await conn.close()

@mcp.tool()
async def query_database(query: str) -> list:
    """Query with automatic cleanup"""
    async with managed_connection() as conn:
        result = await conn.execute(query)
        return result
```

### 5. Versioning

Version your servers and handle compatibility.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="my-server",
    version="2.1.0"  # Semantic versioning
)

# Handle version-specific behavior
@mcp.tool()
def version_aware_tool(data: str, api_version: str = "v2") -> str:
    """Tool with version support"""

    if api_version == "v1":
        return process_v1(data)
    elif api_version == "v2":
        return process_v2(data)
    else:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"Unsupported API version: {api_version}\n"
            f"Supported versions: v1, v2"
        )
```

### 6. Documentation

Document all primitives clearly.

```python
@mcp.tool()
def search_database(
    query: str,
    table: str,
    limit: int = 10,
    offset: int = 0
) -> list[dict]:
    """Search database for matching records.

    This tool performs a full-text search across the specified
    database table and returns matching records.

    Args:
        query: Search query string (supports wildcards: *, ?)
        table: Database table name (must exist)
        limit: Maximum number of results (1-100, default: 10)
        offset: Number of results to skip (default: 0)

    Returns:
        List of matching records as dictionaries

    Raises:
        INVALID_PARAMS: If parameters are invalid
        RESOURCE_NOT_FOUND: If table doesn't exist
        PERMISSION_DENIED: If user lacks read access
        INTERNAL_ERROR: If database query fails

    Examples:
        Search for active users:
        {"query": "status:active", "table": "users", "limit": 20}

        Paginated search:
        {"query": "*@example.com", "table": "contacts", "limit": 10, "offset": 20}
    """
    # Implementation...
```

This comprehensive core concepts reference covers the foundational architecture, protocols, and patterns that power MCP.
