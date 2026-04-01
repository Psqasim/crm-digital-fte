# MCP Server Development Reference

## Table of Contents
1. [Overview](#overview)
2. [Server Architecture](#server-architecture)
3. [Getting Started](#getting-started)
4. [Core Components](#core-components)
5. [Implementing Primitives](#implementing-primitives)
6. [Server Lifecycle](#server-lifecycle)
7. [Advanced Patterns](#advanced-patterns)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

MCP servers expose data and functionality to LLM applications through a standardized protocol. Servers can provide:

- **Resources**: File-like data that can be read by clients
- **Prompts**: Templated messages for LLM interactions
- **Tools**: Functions that can be called by the LLM

### Key Characteristics

- **Stateful**: Servers maintain connection state with clients
- **Asynchronous**: All operations are async by default
- **Protocol-based**: Communication via JSON-RPC 2.0
- **Transport-agnostic**: Works over stdio, HTTP SSE, or custom transports

## Server Architecture

### Basic Architecture

```
┌─────────────────────────────────────────┐
│         MCP Server Application          │
├─────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │Resources │  │  Prompts │  │ Tools │ │
│  └──────────┘  └──────────┘  └───────┘ │
├─────────────────────────────────────────┤
│          MCP Server Framework           │
├─────────────────────────────────────────┤
│         Transport Layer (stdio)         │
└─────────────────────────────────────────┘
```

### Request-Response Flow

1. Client sends JSON-RPC request
2. Server validates request structure
3. Server routes to appropriate handler
4. Handler processes and returns result
5. Server sends JSON-RPC response

## Getting Started

### Python Server (Recommended)

```python
# server.py
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

# Initialize server
mcp = FastMCP("my-server")

@mcp.resource("config://app")
def get_config() -> str:
    """Return application configuration"""
    return "Configuration data here"

@mcp.tool()
def calculate(operation: str, x: float, y: float) -> float:
    """Perform basic calculations

    Args:
        operation: One of 'add', 'subtract', 'multiply', 'divide'
        x: First number
        y: Second number
    """
    if operation == "add":
        return x + y
    elif operation == "subtract":
        return x - y
    elif operation == "multiply":
        return x * y
    elif operation == "divide":
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return x / y
    else:
        raise ValueError(f"Unknown operation: {operation}")

@mcp.prompt()
def review_prompt(code: str, language: str = "python") -> str:
    """Generate code review prompt

    Args:
        code: The code to review
        language: Programming language
    """
    return f"""Please review this {language} code:

```{language}
{code}
```

Provide feedback on:
- Code quality
- Best practices
- Potential bugs
- Performance concerns
"""

if __name__ == "__main__":
    mcp.run()
```

### TypeScript Server

```typescript
// server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Create server instance
const server = new Server(
  {
    name: "example-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      resources: {},
      tools: {},
      prompts: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "calculate",
        description: "Perform basic arithmetic operations",
        inputSchema: {
          type: "object",
          properties: {
            operation: {
              type: "string",
              enum: ["add", "subtract", "multiply", "divide"],
              description: "The operation to perform",
            },
            x: {
              type: "number",
              description: "First number",
            },
            y: {
              type: "number",
              description: "Second number",
            },
          },
          required: ["operation", "x", "y"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "calculate") {
    const { operation, x, y } = request.params.arguments as {
      operation: string;
      x: number;
      y: number;
    };

    let result: number;
    switch (operation) {
      case "add":
        result = x + y;
        break;
      case "subtract":
        result = x - y;
        break;
      case "multiply":
        result = x * y;
        break;
      case "divide":
        if (y === 0) {
          throw new Error("Cannot divide by zero");
        }
        result = x / y;
        break;
      default:
        throw new Error(`Unknown operation: ${operation}`);
    }

    return {
      content: [
        {
          type: "text",
          text: `Result: ${result}`,
        },
      ],
    };
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});

// List available resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "config://app",
        name: "Application Configuration",
        mimeType: "application/json",
        description: "Current application configuration",
      },
    ],
  };
});

// Read resource contents
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  if (request.params.uri === "config://app") {
    return {
      contents: [
        {
          uri: "config://app",
          mimeType: "application/json",
          text: JSON.stringify(
            {
              version: "1.0.0",
              environment: "production",
            },
            null,
            2
          ),
        },
      ],
    };
  }

  throw new Error(`Unknown resource: ${request.params.uri}`);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

## Core Components

### 1. Resources

Resources are file-like data sources that clients can read.

#### Resource URI Schemes

```python
# File resources
"file:///path/to/file.txt"

# Custom schemes
"config://app/settings"
"database://users/table"
"api://endpoint/data"
```

#### Resource Implementation (Python)

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource, TextContent, ImageContent
import base64

mcp = FastMCP("resource-server")

# Simple text resource
@mcp.resource("doc://readme")
def get_readme() -> str:
    """Return README content"""
    with open("README.md") as f:
        return f.read()

# Dynamic resource with parameters
@mcp.resource("user://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """Get user profile data"""
    # Fetch from database
    user = database.get_user(user_id)
    return f"User: {user.name}\nEmail: {user.email}"

# List all available resources
@mcp.list_resources()
def list_available_resources() -> list[Resource]:
    """Return list of available resources"""
    return [
        Resource(
            uri="doc://readme",
            name="README",
            mimeType="text/markdown",
            description="Project documentation"
        ),
        Resource(
            uri="config://app",
            name="Configuration",
            mimeType="application/json",
            description="App configuration"
        )
    ]

# Binary resource (image)
@mcp.resource("image://logo")
def get_logo() -> ImageContent:
    """Return company logo"""
    with open("logo.png", "rb") as f:
        data = base64.b64encode(f.read()).decode()

    return ImageContent(
        type="image",
        data=data,
        mimeType="image/png"
    )
```

#### Resource Templates

```python
from mcp.types import ResourceTemplate

@mcp.list_resource_templates()
def list_templates() -> list[ResourceTemplate]:
    """Define resource URI templates"""
    return [
        ResourceTemplate(
            uriTemplate="file:///{path}",
            name="File Access",
            description="Read any file from the filesystem",
            mimeType="text/plain"
        ),
        ResourceTemplate(
            uriTemplate="user://{user_id}/profile",
            name="User Profiles",
            description="Access user profile data"
        )
    ]
```

### 2. Prompts

Prompts are templated messages and instructions for the LLM.

#### Basic Prompt (Python)

```python
@mcp.prompt()
def code_review(language: str, code: str) -> str:
    """Generate a code review prompt

    Args:
        language: Programming language
        code: Code to review
    """
    return f"""Please review this {language} code:

```{language}
{code}
```

Focus on:
1. Code quality and readability
2. Best practices
3. Potential bugs
4. Performance optimization
5. Security concerns
"""

# Prompt with multiple messages
from mcp.types import PromptMessage, TextContent

@mcp.prompt()
def debug_session(error_message: str, stack_trace: str) -> list[PromptMessage]:
    """Create debugging session prompt"""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"I encountered this error: {error_message}"
            )
        ),
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"Stack trace:\n{stack_trace}"
            )
        ),
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text="Can you help me debug this issue?"
            )
        )
    ]
```

#### TypeScript Prompt Handler

```typescript
import { ListPromptsRequestSchema, GetPromptRequestSchema } from "@modelcontextprotocol/sdk/types.js";

server.setRequestHandler(ListPromptsRequestSchema, async () => {
  return {
    prompts: [
      {
        name: "code_review",
        description: "Generate code review prompt",
        arguments: [
          {
            name: "language",
            description: "Programming language",
            required: true,
          },
          {
            name: "code",
            description: "Code to review",
            required: true,
          },
        ],
      },
    ],
  };
});

server.setRequestHandler(GetPromptRequestSchema, async (request) => {
  if (request.params.name === "code_review") {
    const { language, code } = request.params.arguments || {};

    return {
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `Please review this ${language} code:\n\n\`\`\`${language}\n${code}\n\`\`\``,
          },
        },
      ],
    };
  }

  throw new Error(`Unknown prompt: ${request.params.name}`);
});
```

### 3. Tools

Tools are functions that can be called by the LLM to perform actions.

#### Tool Implementation (Python)

```python
from typing import Any
from mcp.types import Tool, TextContent

@mcp.tool()
def search_database(
    query: str,
    table: str,
    limit: int = 10
) -> list[dict[str, Any]]:
    """Search database for records

    Args:
        query: Search query string
        table: Database table name
        limit: Maximum results to return

    Returns:
        List of matching records
    """
    results = database.search(table, query, limit=limit)
    return results

@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    cc: list[str] | None = None
) -> dict[str, str]:
    """Send an email

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        cc: Optional CC recipients

    Returns:
        Status information
    """
    try:
        email_client.send(
            to=to,
            subject=subject,
            body=body,
            cc=cc or []
        )
        return {
            "status": "sent",
            "message": f"Email sent to {to}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Tool with complex return type
@mcp.tool()
def analyze_code(file_path: str) -> TextContent:
    """Analyze code file for issues

    Args:
        file_path: Path to code file

    Returns:
        Analysis results
    """
    with open(file_path) as f:
        code = f.read()

    issues = static_analyzer.analyze(code)

    report = "Code Analysis Report\n"
    report += "=" * 50 + "\n\n"

    for issue in issues:
        report += f"Line {issue.line}: {issue.message}\n"
        report += f"Severity: {issue.severity}\n\n"

    return TextContent(
        type="text",
        text=report
    )
```

#### TypeScript Tool with Validation

```typescript
import { z } from "zod";

// Define input schema
const SearchSchema = z.object({
  query: z.string().min(1),
  table: z.string(),
  limit: z.number().int().positive().max(100).default(10),
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "search_database",
        description: "Search database for records",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query string",
              minLength: 1,
            },
            table: {
              type: "string",
              description: "Database table name",
            },
            limit: {
              type: "number",
              description: "Maximum results to return",
              default: 10,
              minimum: 1,
              maximum: 100,
            },
          },
          required: ["query", "table"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "search_database") {
    // Validate input
    const args = SearchSchema.parse(request.params.arguments);

    // Execute search
    const results = await database.search(
      args.table,
      args.query,
      args.limit
    );

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(results, null, 2),
        },
      ],
    };
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});
```

## Server Lifecycle

### Initialization Sequence

```python
from mcp.server.fastmcp import FastMCP
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("my-server")

# Lifecycle hooks
@mcp.on_startup()
async def startup():
    """Called when server starts"""
    logger.info("Server starting up...")
    # Initialize database connections
    await database.connect()
    # Load configuration
    await config.load()
    logger.info("Server ready")

@mcp.on_shutdown()
async def shutdown():
    """Called when server shuts down"""
    logger.info("Server shutting down...")
    # Close database connections
    await database.disconnect()
    # Clean up resources
    await cleanup_temp_files()
    logger.info("Server stopped")
```

### Error Handling

```python
from mcp.types import McpError, ErrorCode

@mcp.tool()
def risky_operation(data: str) -> str:
    """Operation that might fail"""
    try:
        # Validate input
        if not data:
            raise McpError(
                ErrorCode.INVALID_PARAMS,
                "Data cannot be empty"
            )

        # Perform operation
        result = process_data(data)

        # Validate output
        if not result:
            raise McpError(
                ErrorCode.INTERNAL_ERROR,
                "Processing failed to produce result"
            )

        return result

    except ValueError as e:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"Invalid data format: {e}"
        )
    except PermissionError:
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            "Insufficient permissions"
        )
    except Exception as e:
        logger.exception("Unexpected error")
        raise McpError(
            ErrorCode.INTERNAL_ERROR,
            f"Operation failed: {e}"
        )
```

### State Management

```python
from typing import Any
from contextlib import asynccontextmanager

class ServerState:
    """Manage server state"""

    def __init__(self):
        self.connections: dict[str, Any] = {}
        self.cache: dict[str, Any] = {}
        self.session_data: dict[str, dict] = {}

    async def initialize(self):
        """Initialize server state"""
        await self._load_cache()
        await self._setup_connections()

    async def cleanup(self):
        """Clean up server state"""
        await self._close_connections()
        await self._save_cache()

# Use state in server
state = ServerState()

@mcp.on_startup()
async def startup():
    await state.initialize()

@mcp.on_shutdown()
async def shutdown():
    await state.cleanup()

@mcp.tool()
def get_cached_data(key: str) -> Any:
    """Retrieve cached data"""
    if key not in state.cache:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"No data found for key: {key}"
        )
    return state.cache[key]
```

## Advanced Patterns

### Dynamic Resource Discovery

```python
import os
from pathlib import Path

@mcp.list_resources()
def list_files() -> list[Resource]:
    """Dynamically list all files in workspace"""
    resources = []

    for file_path in Path("./workspace").rglob("*"):
        if file_path.is_file():
            resources.append(
                Resource(
                    uri=f"file:///{file_path}",
                    name=file_path.name,
                    mimeType=get_mime_type(file_path),
                    description=f"File: {file_path.relative_to('./workspace')}"
                )
            )

    return resources

@mcp.resource("file:///{path}")
def read_file(path: str) -> str:
    """Read any file from workspace"""
    file_path = Path("./workspace") / path

    if not file_path.exists():
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"File not found: {path}"
        )

    if not file_path.is_relative_to("./workspace"):
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            "Access denied: path outside workspace"
        )

    with open(file_path) as f:
        return f.read()
```

### Streaming Responses

```python
from typing import AsyncIterator

@mcp.tool()
async def stream_logs(
    service: str,
    lines: int = 100
) -> AsyncIterator[str]:
    """Stream log lines from service

    Args:
        service: Service name
        lines: Number of lines to stream
    """
    log_file = f"/var/log/{service}.log"

    with open(log_file) as f:
        # Skip to last N lines
        all_lines = f.readlines()
        recent_lines = all_lines[-lines:]

        for line in recent_lines:
            yield line.strip()
```

### Progress Tracking

```python
from mcp.types import ProgressNotification

@mcp.tool()
async def process_large_dataset(dataset_id: str) -> str:
    """Process large dataset with progress updates"""

    dataset = await load_dataset(dataset_id)
    total_items = len(dataset)

    for i, item in enumerate(dataset):
        # Process item
        await process_item(item)

        # Send progress notification
        if i % 100 == 0:
            progress = (i / total_items) * 100
            await mcp.send_progress(
                ProgressNotification(
                    progress=progress,
                    total=100,
                    message=f"Processed {i}/{total_items} items"
                )
            )

    return f"Processed {total_items} items"
```

### Resource Subscriptions

```python
from mcp.types import ResourceSubscription
import asyncio

# Track subscribed resources
subscriptions: set[str] = set()

@mcp.subscribe_resource()
async def subscribe(uri: str):
    """Handle resource subscription"""
    subscriptions.add(uri)
    logger.info(f"Client subscribed to {uri}")

@mcp.unsubscribe_resource()
async def unsubscribe(uri: str):
    """Handle resource unsubscription"""
    subscriptions.discard(uri)
    logger.info(f"Client unsubscribed from {uri}")

# Background task to notify subscribers
async def watch_resources():
    """Watch resources and notify subscribers of changes"""
    while True:
        for uri in subscriptions:
            if resource_changed(uri):
                await mcp.notify_resource_updated(uri)

        await asyncio.sleep(5)
```

## Best Practices

### 1. Security

```python
import os
from pathlib import Path

@mcp.tool()
def read_safe_file(file_path: str) -> str:
    """Safely read file with security checks"""

    # Define allowed directory
    SAFE_DIR = Path("/app/data")

    # Resolve absolute path
    requested_path = Path(file_path).resolve()

    # Check if path is within safe directory
    if not requested_path.is_relative_to(SAFE_DIR):
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            "Access denied: path outside allowed directory"
        )

    # Check file exists
    if not requested_path.exists():
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"File not found: {file_path}"
        )

    # Check file size
    if requested_path.stat().st_size > 10_000_000:  # 10MB
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            "File too large (max 10MB)"
        )

    # Read file
    with open(requested_path) as f:
        return f.read()

# Environment variable validation
def get_api_key() -> str:
    """Get API key from environment"""
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise McpError(
            ErrorCode.INTERNAL_ERROR,
            "API_KEY not configured"
        )
    return api_key
```

### 2. Performance

```python
from functools import lru_cache
import asyncio

# Caching expensive operations
@lru_cache(maxsize=128)
def expensive_computation(param: str) -> str:
    """Cache expensive computation results"""
    return complex_algorithm(param)

# Rate limiting
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_calls: int, window: int):
        self.max_calls = max_calls
        self.window = window
        self.calls: defaultdict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time()
        # Remove old calls
        self.calls[client_id] = [
            t for t in self.calls[client_id]
            if now - t < self.window
        ]

        if len(self.calls[client_id]) >= self.max_calls:
            return False

        self.calls[client_id].append(now)
        return True

limiter = RateLimiter(max_calls=100, window=60)

@mcp.tool()
async def rate_limited_operation(client_id: str, data: str) -> str:
    """Rate-limited operation"""
    if not limiter.is_allowed(client_id):
        raise McpError(
            ErrorCode.RESOURCE_EXHAUSTED,
            "Rate limit exceeded"
        )

    return await perform_operation(data)

# Connection pooling
from contextlib import asynccontextmanager

class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.connections: list = []
        self.semaphore = asyncio.Semaphore(max_connections)

    @asynccontextmanager
    async def acquire(self):
        async with self.semaphore:
            if self.connections:
                conn = self.connections.pop()
            else:
                conn = await create_connection()

            try:
                yield conn
            finally:
                self.connections.append(conn)

pool = ConnectionPool()

@mcp.tool()
async def query_database(query: str) -> list:
    """Query database using connection pool"""
    async with pool.acquire() as conn:
        return await conn.execute(query)
```

### 3. Testing

```python
import pytest
from mcp.server.fastmcp import FastMCP

@pytest.fixture
def test_server():
    """Create test server instance"""
    mcp = FastMCP("test-server")

    @mcp.tool()
    def test_tool(input: str) -> str:
        return f"Processed: {input}"

    return mcp

@pytest.mark.asyncio
async def test_tool_call(test_server):
    """Test tool execution"""
    result = await test_server.call_tool(
        "test_tool",
        arguments={"input": "test data"}
    )

    assert result == "Processed: test data"

@pytest.mark.asyncio
async def test_resource_read(test_server):
    """Test resource reading"""
    content = await test_server.read_resource("config://app")
    assert content is not None

# Integration testing
@pytest.mark.asyncio
async def test_server_lifecycle():
    """Test full server lifecycle"""
    mcp = FastMCP("test-server")

    startup_called = False
    shutdown_called = False

    @mcp.on_startup()
    async def startup():
        nonlocal startup_called
        startup_called = True

    @mcp.on_shutdown()
    async def shutdown():
        nonlocal shutdown_called
        shutdown_called = True

    # Simulate server start
    await mcp._startup()
    assert startup_called

    # Simulate server stop
    await mcp._shutdown()
    assert shutdown_called
```

### 4. Logging and Monitoring

```python
import logging
from datetime import datetime

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log all tool calls
@mcp.tool()
def monitored_tool(param: str) -> str:
    """Tool with monitoring"""
    start_time = datetime.now()

    try:
        logger.info(f"Tool called with param: {param}")
        result = process_param(param)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Tool completed in {duration}s")

        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}", exc_info=True)
        raise

# Metrics collection
from collections import Counter

metrics = {
    "tool_calls": Counter(),
    "resource_reads": Counter(),
    "errors": Counter()
}

@mcp.tool()
def tracked_tool(param: str) -> str:
    """Tool with metrics tracking"""
    metrics["tool_calls"]["tracked_tool"] += 1

    try:
        return process(param)
    except Exception as e:
        metrics["errors"]["tracked_tool"] += 1
        raise
```

## Troubleshooting

### Common Issues

#### 1. Server Not Responding

```python
# Add timeout handling
import asyncio

@mcp.tool()
async def long_running_task(data: str) -> str:
    """Task with timeout protection"""
    try:
        result = await asyncio.wait_for(
            process_data(data),
            timeout=30.0
        )
        return result
    except asyncio.TimeoutError:
        raise McpError(
            ErrorCode.TIMEOUT,
            "Operation timed out after 30 seconds"
        )
```

#### 2. Resource Not Found

```python
@mcp.resource("file:///{path}")
def safe_file_read(path: str) -> str:
    """Read file with better error messages"""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"Resource not found: {path}\n"
            f"Available resources can be listed with list_resources()"
        )
    except PermissionError:
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            f"Permission denied reading: {path}"
        )
```

#### 3. Invalid Tool Parameters

```python
from pydantic import BaseModel, validator

class SearchParams(BaseModel):
    """Validated search parameters"""
    query: str
    limit: int = 10
    offset: int = 0

    @validator("query")
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v

    @validator("limit")
    def limit_in_range(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("Limit must be between 1 and 100")
        return v

@mcp.tool()
def validated_search(query: str, limit: int = 10, offset: int = 0) -> list:
    """Search with validated parameters"""
    # Validate using Pydantic
    params = SearchParams(query=query, limit=limit, offset=offset)

    return database.search(
        params.query,
        limit=params.limit,
        offset=params.offset
    )
```

#### 4. Memory Leaks

```python
import weakref
from typing import Any

class ResourceManager:
    """Manage resources with automatic cleanup"""

    def __init__(self):
        self._resources: dict[str, Any] = {}
        self._finalizers: dict[str, Any] = {}

    def register(self, key: str, resource: Any, cleanup_fn: callable):
        """Register resource with cleanup function"""
        self._resources[key] = resource
        self._finalizers[key] = weakref.finalize(
            resource,
            cleanup_fn
        )

    def cleanup(self, key: str):
        """Manually cleanup resource"""
        if key in self._finalizers:
            self._finalizers[key]()
            del self._finalizers[key]
            del self._resources[key]

    def cleanup_all(self):
        """Cleanup all resources"""
        for key in list(self._resources.keys()):
            self.cleanup(key)

manager = ResourceManager()

@mcp.on_shutdown()
async def cleanup():
    """Cleanup all resources on shutdown"""
    manager.cleanup_all()
```

### Debug Mode

```python
import os

# Enable debug mode
DEBUG = os.getenv("MCP_DEBUG", "false").lower() == "true"

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)

    # Log all requests
    @mcp.on_request()
    async def log_request(request):
        logger.debug(f"Request: {request}")

    # Log all responses
    @mcp.on_response()
    async def log_response(response):
        logger.debug(f"Response: {response}")
```

### Health Checks

```python
@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Server health check"""
    checks = {}

    # Check database
    try:
        await database.ping()
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Check external API
    try:
        await api_client.ping()
        checks["api"] = "healthy"
    except Exception as e:
        checks["api"] = f"unhealthy: {e}"

    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage("/")
    checks["disk"] = {
        "total": total,
        "used": used,
        "free": free,
        "status": "healthy" if free > total * 0.1 else "low"
    }

    return {
        "status": "healthy" if all(
            v == "healthy" or (isinstance(v, dict) and v.get("status") == "healthy")
            for v in checks.values()
        ) else "degraded",
        "checks": checks
    }
```

## Complete Example: Production Server

```python
# production_server.py
import os
import logging
from pathlib import Path
from typing import Any
from mcp.server.fastmcp import FastMCP
from mcp.types import Resource, TextContent, McpError, ErrorCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize server
mcp = FastMCP(
    "production-server",
    dependencies=["database", "cache", "api-client"]
)

# Configuration
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
MAX_FILE_SIZE = 10_000_000  # 10MB

# State management
class ServerState:
    def __init__(self):
        self.db = None
        self.cache = None
        self.api = None

    async def initialize(self):
        logger.info("Initializing server state...")
        # Initialize connections
        self.db = await init_database()
        self.cache = await init_cache()
        self.api = await init_api_client()
        logger.info("Server state initialized")

    async def cleanup(self):
        logger.info("Cleaning up server state...")
        if self.db:
            await self.db.close()
        if self.cache:
            await self.cache.close()
        if self.api:
            await self.api.close()
        logger.info("Server state cleaned up")

state = ServerState()

# Lifecycle hooks
@mcp.on_startup()
async def startup():
    await state.initialize()

@mcp.on_shutdown()
async def shutdown():
    await state.cleanup()

# Resources
@mcp.list_resources()
def list_workspace_files() -> list[Resource]:
    """List all files in workspace"""
    resources = []

    for file_path in WORKSPACE_DIR.rglob("*"):
        if file_path.is_file():
            resources.append(
                Resource(
                    uri=f"file:///{file_path.relative_to(WORKSPACE_DIR)}",
                    name=file_path.name,
                    mimeType=get_mime_type(file_path),
                    description=f"File: {file_path.relative_to(WORKSPACE_DIR)}"
                )
            )

    return resources

@mcp.resource("file:///{path}")
def read_workspace_file(path: str) -> str:
    """Read file from workspace"""
    file_path = (WORKSPACE_DIR / path).resolve()

    # Security check
    if not file_path.is_relative_to(WORKSPACE_DIR):
        raise McpError(
            ErrorCode.PERMISSION_DENIED,
            "Access denied: path outside workspace"
        )

    # Existence check
    if not file_path.exists():
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"File not found: {path}"
        )

    # Size check
    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            f"File too large (max {MAX_FILE_SIZE / 1_000_000}MB)"
        )

    with open(file_path) as f:
        return f.read()

# Tools
@mcp.tool()
async def search_database(
    query: str,
    table: str,
    limit: int = 10
) -> list[dict[str, Any]]:
    """Search database for records

    Args:
        query: Search query string
        table: Database table name
        limit: Maximum results to return (1-100)
    """
    if not 1 <= limit <= 100:
        raise McpError(
            ErrorCode.INVALID_PARAMS,
            "Limit must be between 1 and 100"
        )

    try:
        results = await state.db.search(table, query, limit=limit)
        return results
    except Exception as e:
        logger.error(f"Database search failed: {e}")
        raise McpError(
            ErrorCode.INTERNAL_ERROR,
            f"Search failed: {e}"
        )

@mcp.tool()
async def health_check() -> dict[str, Any]:
    """Check server health"""
    checks = {}

    # Database health
    try:
        await state.db.ping()
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Cache health
    try:
        await state.cache.ping()
        checks["cache"] = "healthy"
    except Exception as e:
        checks["cache"] = f"unhealthy: {e}"

    return {
        "status": "healthy" if all(
            v == "healthy" for v in checks.values()
        ) else "degraded",
        "checks": checks
    }

# Prompts
@mcp.prompt()
def code_review(language: str, code: str) -> str:
    """Generate code review prompt"""
    return f"""Please review this {language} code:

```{language}
{code}
```

Provide feedback on:
1. Code quality and readability
2. Best practices and patterns
3. Potential bugs or issues
4. Performance considerations
5. Security concerns
"""

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

This comprehensive reference covers all aspects of MCP server development with production-ready examples and best practices.
