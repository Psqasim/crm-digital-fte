# MCP Client Integration Reference

## Table of Contents
1. [Overview](#overview)
2. [Client Architecture](#client-architecture)
3. [Getting Started](#getting-started)
4. [Connecting to Servers](#connecting-to-servers)
5. [Using Primitives](#using-primitives)
6. [Client Lifecycle](#client-lifecycle)
7. [Advanced Patterns](#advanced-patterns)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

MCP clients connect to servers to access resources, prompts, and tools. Clients can:

- **Discover**: List available resources, prompts, and tools
- **Access**: Read resources and get prompt templates
- **Execute**: Call tools to perform actions
- **Subscribe**: Receive updates when resources change

### Key Characteristics

- **Multi-server**: Can connect to multiple servers simultaneously
- **Async-first**: Built on asynchronous operations
- **Type-safe**: Strongly typed interfaces
- **Protocol-aware**: Handles JSON-RPC communication

## Client Architecture

### Basic Architecture

```
┌─────────────────────────────────────────┐
│         LLM Application Layer           │
├─────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Server 1 │  │ Server 2 │  │Server3│ │
│  └──────────┘  └──────────┘  └───────┘ │
├─────────────────────────────────────────┤
│          MCP Client Framework           │
├─────────────────────────────────────────┤
│    Transport Layer (stdio/HTTP SSE)     │
└─────────────────────────────────────────┘
```

### Client Responsibilities

1. **Connection Management**: Establish and maintain server connections
2. **Protocol Handling**: Send/receive JSON-RPC messages
3. **Capability Negotiation**: Determine what features are available
4. **Request Routing**: Send requests to appropriate servers
5. **Response Processing**: Handle server responses and errors

## Getting Started

### Python Client

```python
# client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Define server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env={"API_KEY": "your-api-key"}
    )

    # Connect to server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")

            # Call a tool
            result = await session.call_tool(
                "calculate",
                arguments={"operation": "add", "x": 5, "y": 3}
            )
            print(f"Result: {result.content[0].text}")

            # List resources
            resources = await session.list_resources()
            print(f"Available resources: {[r.name for r in resources.resources]}")

            # Read a resource
            resource_content = await session.read_resource("config://app")
            print(f"Resource: {resource_content.contents[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
```

### TypeScript Client

```typescript
// client.ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function main() {
  // Create transport
  const transport = new StdioClientTransport({
    command: "node",
    args: ["server.js"],
    env: {
      API_KEY: "your-api-key",
    },
  });

  // Create client
  const client = new Client(
    {
      name: "example-client",
      version: "1.0.0",
    },
    {
      capabilities: {
        roots: {
          listChanged: true,
        },
        sampling: {},
      },
    }
  );

  // Connect to server
  await client.connect(transport);

  // Initialize
  const initResult = await client.initialize();
  console.log("Server capabilities:", initResult.capabilities);

  // List tools
  const tools = await client.listTools();
  console.log("Available tools:", tools.tools.map((t) => t.name));

  // Call tool
  const result = await client.callTool({
    name: "calculate",
    arguments: {
      operation: "add",
      x: 5,
      y: 3,
    },
  });
  console.log("Result:", result.content[0].text);

  // List resources
  const resources = await client.listResources();
  console.log("Available resources:", resources.resources.map((r) => r.name));

  // Read resource
  const resourceContent = await client.readResource({
    uri: "config://app",
  });
  console.log("Resource:", resourceContent.contents[0].text);

  // Close connection
  await client.close();
}

main().catch(console.error);
```

## Connecting to Servers

### Stdio Transport (Python)

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os

async def connect_stdio_server():
    """Connect to server using stdio transport"""

    server_params = StdioServerParameters(
        command="python",
        args=["-m", "my_server"],
        env={
            "API_KEY": os.getenv("API_KEY"),
            "LOG_LEVEL": "INFO"
        }
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            init_result = await session.initialize()
            print(f"Connected to: {init_result.serverInfo.name}")
            print(f"Server version: {init_result.serverInfo.version}")
            print(f"Capabilities: {init_result.capabilities}")

            # Use session
            yield session
```

### HTTP SSE Transport (Python)

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async def connect_sse_server():
    """Connect to server using SSE transport"""

    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session
```

### Multiple Server Connections (Python)

```python
from typing import Dict
from mcp import ClientSession

class MultiServerClient:
    """Manage multiple server connections"""

    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}

    async def connect_server(self, name: str, params: StdioServerParameters):
        """Connect to a server"""
        async with stdio_client(params) as (read, write):
            session = ClientSession(read, write)
            await session.initialize()
            self.sessions[name] = session
            return session

    async def disconnect_server(self, name: str):
        """Disconnect from a server"""
        if name in self.sessions:
            await self.sessions[name].close()
            del self.sessions[name]

    async def disconnect_all(self):
        """Disconnect from all servers"""
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()

# Usage
async def main():
    client = MultiServerClient()

    # Connect to multiple servers
    await client.connect_server("filesystem", StdioServerParameters(
        command="python",
        args=["fs_server.py"]
    ))

    await client.connect_server("database", StdioServerParameters(
        command="python",
        args=["db_server.py"]
    ))

    # Use servers
    fs_session = client.sessions["filesystem"]
    db_session = client.sessions["database"]

    # Read file
    file_content = await fs_session.read_resource("file:///data.txt")

    # Query database
    db_result = await db_session.call_tool(
        "query",
        arguments={"sql": "SELECT * FROM users"}
    )

    # Cleanup
    await client.disconnect_all()
```

### TypeScript Multiple Servers

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

class MultiServerClient {
  private clients: Map<string, Client> = new Map();

  async connectServer(name: string, command: string, args: string[]) {
    const transport = new StdioClientTransport({
      command,
      args,
    });

    const client = new Client(
      {
        name: `client-${name}`,
        version: "1.0.0",
      },
      {
        capabilities: {},
      }
    );

    await client.connect(transport);
    await client.initialize();

    this.clients.set(name, client);
    return client;
  }

  getClient(name: string): Client | undefined {
    return this.clients.get(name);
  }

  async disconnectAll() {
    for (const client of this.clients.values()) {
      await client.close();
    }
    this.clients.clear();
  }
}

// Usage
async function main() {
  const multiClient = new MultiServerClient();

  // Connect to servers
  await multiClient.connectServer("fs", "node", ["fs-server.js"]);
  await multiClient.connectServer("db", "node", ["db-server.js"]);

  // Use clients
  const fsClient = multiClient.getClient("fs")!;
  const dbClient = multiClient.getClient("db")!;

  const files = await fsClient.listResources();
  const dbTools = await dbClient.listTools();

  await multiClient.disconnectAll();
}
```

## Using Primitives

### Resources

```python
async def work_with_resources(session: ClientSession):
    """Examples of working with resources"""

    # List all resources
    resources_response = await session.list_resources()
    for resource in resources_response.resources:
        print(f"Resource: {resource.name}")
        print(f"  URI: {resource.uri}")
        print(f"  Type: {resource.mimeType}")
        print(f"  Description: {resource.description}")

    # Read a specific resource
    content = await session.read_resource("file:///data/config.json")

    # Handle different content types
    for item in content.contents:
        if item.type == "text":
            print(f"Text content: {item.text}")
        elif item.type == "blob":
            print(f"Binary content: {len(item.blob)} bytes")

    # List resource templates
    templates = await session.list_resource_templates()
    for template in templates.resourceTemplates:
        print(f"Template: {template.uriTemplate}")
        print(f"  Name: {template.name}")

    # Use template to construct URI
    # Template: "file:///{path}"
    user_path = "documents/report.pdf"
    uri = f"file:///{user_path}"
    content = await session.read_resource(uri)
```

### Resource Subscriptions (TypeScript)

```typescript
async function subscribeToResources(client: Client) {
  // Subscribe to resource updates
  await client.subscribeResource({
    uri: "file:///data/config.json",
  });

  // Handle resource updates
  client.setNotificationHandler(
    {
      method: "notifications/resources/updated",
    },
    (notification) => {
      console.log("Resource updated:", notification.params.uri);

      // Re-read the resource
      client.readResource({ uri: notification.params.uri }).then((content) => {
        console.log("Updated content:", content);
      });
    }
  );

  // Unsubscribe when done
  await client.unsubscribeResource({
    uri: "file:///data/config.json",
  });
}
```

### Prompts

```python
async def work_with_prompts(session: ClientSession):
    """Examples of working with prompts"""

    # List available prompts
    prompts_response = await session.list_prompts()
    for prompt in prompts_response.prompts:
        print(f"Prompt: {prompt.name}")
        print(f"  Description: {prompt.description}")

        # Show arguments
        if prompt.arguments:
            for arg in prompt.arguments:
                required = " (required)" if arg.required else ""
                print(f"  - {arg.name}{required}: {arg.description}")

    # Get a prompt with arguments
    prompt_result = await session.get_prompt(
        "code_review",
        arguments={
            "language": "python",
            "code": "def hello():\n    print('Hello, world!')"
        }
    )

    # Use the prompt messages
    for message in prompt_result.messages:
        print(f"Role: {message.role}")
        print(f"Content: {message.content.text}")

    # Send to LLM
    response = await send_to_llm(prompt_result.messages)
    print(f"LLM Response: {response}")
```

### TypeScript Prompts

```typescript
async function workWithPrompts(client: Client) {
  // List prompts
  const prompts = await client.listPrompts();

  for (const prompt of prompts.prompts) {
    console.log(`Prompt: ${prompt.name}`);

    if (prompt.arguments) {
      for (const arg of prompt.arguments) {
        console.log(`  - ${arg.name}: ${arg.description}`);
      }
    }
  }

  // Get prompt with arguments
  const promptResult = await client.getPrompt({
    name: "code_review",
    arguments: {
      language: "typescript",
      code: 'function hello() {\n  console.log("Hello");\n}',
    },
  });

  // Use with LLM
  const messages = promptResult.messages.map((msg) => ({
    role: msg.role,
    content: msg.content.text,
  }));

  const llmResponse = await callLLM(messages);
}
```

### Tools

```python
async def work_with_tools(session: ClientSession):
    """Examples of working with tools"""

    # List available tools
    tools_response = await session.list_tools()
    for tool in tools_response.tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Input schema: {tool.inputSchema}")

    # Call a tool
    result = await session.call_tool(
        "search_database",
        arguments={
            "query": "active users",
            "table": "users",
            "limit": 10
        }
    )

    # Handle tool result
    for content in result.content:
        if content.type == "text":
            print(f"Result: {content.text}")

    # Call tool with error handling
    try:
        result = await session.call_tool(
            "send_email",
            arguments={
                "to": "user@example.com",
                "subject": "Test",
                "body": "Test message"
            }
        )
        print("Email sent successfully")
    except McpError as e:
        print(f"Tool error: {e.error.message}")

    # Handle progress notifications
    def on_progress(notification):
        print(f"Progress: {notification.progress}/{notification.total}")
        print(f"Message: {notification.message}")

    result = await session.call_tool(
        "process_large_file",
        arguments={"file_path": "/data/large.csv"},
        progress_callback=on_progress
    )
```

### TypeScript Tool Execution

```typescript
async function workWithTools(client: Client) {
  // List tools
  const tools = await client.listTools();

  for (const tool of tools.tools) {
    console.log(`Tool: ${tool.name}`);
    console.log(`  Description: ${tool.description}`);
    console.log(`  Schema:`, JSON.stringify(tool.inputSchema, null, 2));
  }

  // Call tool
  const result = await client.callTool({
    name: "search_database",
    arguments: {
      query: "active users",
      table: "users",
      limit: 10,
    },
  });

  // Process result
  for (const content of result.content) {
    if (content.type === "text") {
      console.log("Result:", content.text);
    }
  }

  // Error handling
  try {
    await client.callTool({
      name: "risky_operation",
      arguments: { data: "test" },
    });
  } catch (error) {
    if (error instanceof McpError) {
      console.error("Tool error:", error.message);
      console.error("Error code:", error.code);
    }
  }

  // With progress tracking
  client.setNotificationHandler(
    {
      method: "notifications/progress",
    },
    (notification) => {
      console.log(
        `Progress: ${notification.params.progress}/${notification.params.total}`
      );
    }
  );

  await client.callTool({
    name: "long_running_task",
    arguments: { input: "data" },
  });
}
```

## Client Lifecycle

### Connection Management (Python)

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

class ManagedClient:
    """Client with lifecycle management"""

    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: ClientSession | None = None
        self._read = None
        self._write = None

    async def connect(self):
        """Establish connection"""
        self._read, self._write = await stdio_client(self.server_params).__aenter__()
        self.session = ClientSession(self._read, self._write)
        await self.session.__aenter__()

        # Initialize
        init_result = await self.session.initialize()
        print(f"Connected to {init_result.serverInfo.name}")

        return self

    async def disconnect(self):
        """Close connection"""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None

        if self._read and self._write:
            # Cleanup transport
            pass

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[ClientSession]:
        """Context manager for connection"""
        await self.connect()
        try:
            yield self.session
        finally:
            await self.disconnect()

# Usage
async def main():
    client = ManagedClient(StdioServerParameters(
        command="python",
        args=["server.py"]
    ))

    async with client.connection() as session:
        tools = await session.list_tools()
        print(f"Tools: {tools}")
```

### Reconnection Logic (Python)

```python
import asyncio
from typing import Optional

class ResilientClient:
    """Client with automatic reconnection"""

    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
        self.session: Optional[ClientSession] = None
        self.max_retries = 3
        self.retry_delay = 1.0

    async def connect_with_retry(self) -> ClientSession:
        """Connect with retry logic"""
        for attempt in range(self.max_retries):
            try:
                async with stdio_client(self.server_params) as (read, write):
                    session = ClientSession(read, write)
                    await session.initialize()
                    self.session = session
                    print(f"Connected successfully (attempt {attempt + 1})")
                    return session

            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise Exception("Max retries reached")

    async def call_tool_safe(self, name: str, arguments: dict) -> Any:
        """Call tool with automatic reconnection"""
        try:
            if not self.session:
                await self.connect_with_retry()

            return await self.session.call_tool(name, arguments=arguments)

        except Exception as e:
            print(f"Tool call failed: {e}")

            # Try to reconnect
            self.session = None
            await self.connect_with_retry()

            # Retry the call
            return await self.session.call_tool(name, arguments=arguments)
```

### TypeScript Connection Management

```typescript
class ManagedClient {
  private client?: Client;
  private transport?: StdioClientTransport;

  constructor(
    private command: string,
    private args: string[]
  ) {}

  async connect(): Promise<Client> {
    this.transport = new StdioClientTransport({
      command: this.command,
      args: this.args,
    });

    this.client = new Client(
      {
        name: "managed-client",
        version: "1.0.0",
      },
      {
        capabilities: {},
      }
    );

    await this.client.connect(this.transport);
    await this.client.initialize();

    console.log("Client connected");
    return this.client;
  }

  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.close();
      this.client = undefined;
    }

    if (this.transport) {
      // Cleanup transport
      this.transport = undefined;
    }

    console.log("Client disconnected");
  }

  getClient(): Client {
    if (!this.client) {
      throw new Error("Client not connected");
    }
    return this.client;
  }
}

// Usage
async function main() {
  const managedClient = new ManagedClient("node", ["server.js"]);

  try {
    const client = await managedClient.connect();

    const tools = await client.listTools();
    console.log("Tools:", tools);

    // Use client...
  } finally {
    await managedClient.disconnect();
  }
}
```

## Advanced Patterns

### Caching Client (Python)

```python
from typing import Dict, Any, Optional
import time

class CachingClient:
    """Client with response caching"""

    def __init__(self, session: ClientSession, ttl: int = 60):
        self.session = session
        self.ttl = ttl  # Time to live in seconds
        self.cache: Dict[str, tuple[Any, float]] = {}

    async def list_tools_cached(self):
        """List tools with caching"""
        cache_key = "tools_list"

        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl:
                print("Returning cached tools")
                return result

        print("Fetching fresh tools")
        result = await self.session.list_tools()
        self.cache[cache_key] = (result, time.time())
        return result

    async def read_resource_cached(self, uri: str):
        """Read resource with caching"""
        cache_key = f"resource:{uri}"

        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl:
                return result

        result = await self.session.read_resource(uri)
        self.cache[cache_key] = (result, time.time())
        return result

    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cache entries"""
        if pattern is None:
            self.cache.clear()
        else:
            keys_to_remove = [
                key for key in self.cache.keys()
                if pattern in key
            ]
            for key in keys_to_remove:
                del self.cache[key]
```

### Request Batching (Python)

```python
import asyncio
from typing import List, Tuple

class BatchingClient:
    """Client with request batching"""

    def __init__(self, session: ClientSession):
        self.session = session
        self.batch_size = 5
        self.batch_delay = 0.1  # seconds
        self.pending_requests: List[Tuple[str, dict]] = []

    async def queue_tool_call(self, name: str, arguments: dict) -> Any:
        """Queue a tool call for batching"""
        future = asyncio.Future()
        self.pending_requests.append((name, arguments, future))

        # Process batch if it's full
        if len(self.pending_requests) >= self.batch_size:
            await self._process_batch()

        return await future

    async def _process_batch(self):
        """Process batched requests"""
        if not self.pending_requests:
            return

        requests = self.pending_requests[:]
        self.pending_requests.clear()

        # Execute requests concurrently
        tasks = [
            self.session.call_tool(name, arguments=args)
            for name, args, _ in requests
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Resolve futures
        for (_, _, future), result in zip(requests, results):
            if isinstance(result, Exception):
                future.set_exception(result)
            else:
                future.set_result(result)

    async def flush(self):
        """Process all pending requests"""
        await self._process_batch()
```

### Tool Call Chain (TypeScript)

```typescript
class ToolChain {
  constructor(private client: Client) {}

  async execute(steps: Array<{ tool: string; args: any }>): Promise<any[]> {
    const results: any[] = [];

    for (const step of steps) {
      console.log(`Executing: ${step.tool}`);

      const result = await this.client.callTool({
        name: step.tool,
        arguments: step.args,
      });

      results.push(result);

      // Use previous result in next step if needed
      if (step.args._usePreviousResult && results.length > 0) {
        const previousResult = results[results.length - 2];
        step.args = {
          ...step.args,
          previousResult,
        };
      }
    }

    return results;
  }

  async executeParallel(
    steps: Array<{ tool: string; args: any }>
  ): Promise<any[]> {
    const promises = steps.map((step) =>
      this.client.callTool({
        name: step.tool,
        arguments: step.args,
      })
    );

    return Promise.all(promises);
  }
}

// Usage
async function main() {
  const client = await connectClient();
  const chain = new ToolChain(client);

  // Sequential execution
  const results = await chain.execute([
    { tool: "search", args: { query: "users" } },
    { tool: "filter", args: { criteria: "active" } },
    { tool: "export", args: { format: "csv" } },
  ]);

  // Parallel execution
  const parallelResults = await chain.executeParallel([
    { tool: "analyze_a", args: { data: "dataset1" } },
    { tool: "analyze_b", args: { data: "dataset2" } },
    { tool: "analyze_c", args: { data: "dataset3" } },
  ]);
}
```

### Circuit Breaker Pattern (Python)

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker for tool calls"""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        recovery_timeout: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def call(self, func):
        """Decorator for circuit breaker"""
        async def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result

            except Exception as e:
                self._on_failure()
                raise

        return wrapper

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt reset"""
        if self.last_failure_time is None:
            return True

        elapsed = datetime.now() - self.last_failure_time
        return elapsed > timedelta(seconds=self.recovery_timeout)

# Usage
breaker = CircuitBreaker()

@breaker.call
async def call_tool_protected(session: ClientSession, name: str, args: dict):
    """Tool call with circuit breaker protection"""
    return await session.call_tool(name, arguments=args)
```

## Best Practices

### 1. Error Handling

```python
from mcp.types import McpError, ErrorCode

async def robust_tool_call(
    session: ClientSession,
    tool_name: str,
    arguments: dict,
    max_retries: int = 3
) -> Any:
    """Robust tool call with error handling"""

    for attempt in range(max_retries):
        try:
            result = await session.call_tool(tool_name, arguments=arguments)
            return result

        except McpError as e:
            if e.error.code == ErrorCode.INVALID_PARAMS:
                # Don't retry for invalid params
                print(f"Invalid parameters: {e.error.message}")
                raise

            elif e.error.code == ErrorCode.METHOD_NOT_FOUND:
                # Tool doesn't exist
                print(f"Tool not found: {tool_name}")
                raise

            elif e.error.code == ErrorCode.INTERNAL_ERROR:
                # Server error, retry
                print(f"Server error (attempt {attempt + 1}): {e.error.message}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                raise

            else:
                # Unknown error
                print(f"Unexpected error: {e}")
                raise

        except asyncio.TimeoutError:
            print(f"Timeout (attempt {attempt + 1})")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            raise

        except Exception as e:
            print(f"Unexpected exception: {e}")
            raise
```

### 2. Resource Management

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_session(server_params: StdioServerParameters):
    """Properly managed session with cleanup"""

    session = None
    transport = None

    try:
        # Setup
        async with stdio_client(server_params) as (read, write):
            transport = (read, write)
            session = ClientSession(read, write)
            await session.initialize()

            yield session

    except Exception as e:
        print(f"Session error: {e}")
        raise

    finally:
        # Cleanup
        if session:
            try:
                await session.close()
            except Exception as e:
                print(f"Error closing session: {e}")

# Usage
async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    async with managed_session(server_params) as session:
        # Use session safely
        result = await session.call_tool("my_tool", arguments={})
```

### 3. Timeout Management (TypeScript)

```typescript
async function callWithTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number
): Promise<T> {
  let timeoutHandle: NodeJS.Timeout;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutHandle = setTimeout(() => {
      reject(new Error(`Operation timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });

  try {
    return await Promise.race([promise, timeoutPromise]);
  } finally {
    clearTimeout(timeoutHandle!);
  }
}

// Usage
async function robustToolCall(client: Client) {
  try {
    const result = await callWithTimeout(
      client.callTool({
        name: "slow_operation",
        arguments: {},
      }),
      5000 // 5 second timeout
    );

    console.log("Result:", result);
  } catch (error) {
    if (error.message.includes("timed out")) {
      console.error("Operation timed out");
    } else {
      console.error("Operation failed:", error);
    }
  }
}
```

### 4. Input Validation

```python
from pydantic import BaseModel, validator

class ToolCallRequest(BaseModel):
    """Validated tool call request"""
    tool_name: str
    arguments: dict

    @validator("tool_name")
    def validate_tool_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Tool name cannot be empty")
        if not v.isidentifier():
            raise ValueError("Tool name must be valid identifier")
        return v

    @validator("arguments")
    def validate_arguments(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Arguments must be a dictionary")
        return v

async def validated_tool_call(session: ClientSession, request: dict):
    """Call tool with validated input"""
    # Validate request
    validated = ToolCallRequest(**request)

    # Execute
    return await session.call_tool(
        validated.tool_name,
        arguments=validated.arguments
    )
```

## Troubleshooting

### Connection Issues

```python
import sys
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_connection():
    """Debug connection issues"""
    try:
        server_params = StdioServerParameters(
            command="python",
            args=["-u", "server.py"],  # -u for unbuffered output
            env={"PYTHONUNBUFFERED": "1"}
        )

        async with stdio_client(server_params) as (read, write):
            # Test transport
            print("Transport established", file=sys.stderr)

            session = ClientSession(read, write)

            # Test initialization
            init_result = await session.initialize()
            print(f"Initialized: {init_result}", file=sys.stderr)

            # Test basic operation
            tools = await session.list_tools()
            print(f"Tools available: {len(tools.tools)}", file=sys.stderr)

    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
```

### Server Not Responding

```typescript
async function diagnoseServer(client: Client) {
  console.log("Starting server diagnosis...");

  try {
    // Test basic connectivity
    console.log("Testing initialization...");
    const init = await callWithTimeout(client.initialize(), 5000);
    console.log("✓ Server initialized:", init.serverInfo.name);

    // Test capabilities
    console.log("Testing tool listing...");
    const tools = await callWithTimeout(client.listTools(), 5000);
    console.log(`✓ Found ${tools.tools.length} tools`);

    // Test resource listing
    console.log("Testing resource listing...");
    const resources = await callWithTimeout(client.listResources(), 5000);
    console.log(`✓ Found ${resources.resources.length} resources`);

    // Test simple tool call
    if (tools.tools.length > 0) {
      console.log("Testing tool call...");
      const result = await callWithTimeout(
        client.callTool({
          name: tools.tools[0].name,
          arguments: {},
        }),
        5000
      );
      console.log("✓ Tool call successful");
    }

    console.log("All tests passed!");
  } catch (error) {
    console.error("✗ Diagnosis failed:", error);
  }
}
```

### Memory Leaks

```python
import gc
import weakref

class LeakDetector:
    """Detect potential memory leaks in client"""

    def __init__(self):
        self.tracked_objects = []

    def track(self, obj, name: str):
        """Track an object for leaks"""
        ref = weakref.ref(obj, lambda x: self._on_destroy(name))
        self.tracked_objects.append((name, ref))

    def _on_destroy(self, name: str):
        """Called when tracked object is destroyed"""
        print(f"Object destroyed: {name}")

    def check_leaks(self):
        """Check for leaked objects"""
        leaked = []
        for name, ref in self.tracked_objects:
            if ref() is not None:
                leaked.append(name)

        if leaked:
            print(f"Potential leaks detected: {leaked}")
        else:
            print("No leaks detected")

        return leaked

# Usage
detector = LeakDetector()

async def test_for_leaks():
    """Test client for memory leaks"""

    for i in range(100):
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            session = ClientSession(read, write)
            detector.track(session, f"session_{i}")

            await session.initialize()
            await session.list_tools()

        # Force garbage collection
        gc.collect()

    # Check for leaks
    detector.check_leaks()
```

This comprehensive client reference covers all aspects of integrating with MCP servers, with production-ready examples and best practices.
