# MCP Transport Mechanisms Reference

## Table of Contents
1. [Overview](#overview)
2. [Transport Architecture](#transport-architecture)
3. [Stdio Transport](#stdio-transport)
4. [HTTP with SSE Transport](#http-with-sse-transport)
5. [Custom Transports](#custom-transports)
6. [Message Framing](#message-framing)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

MCP uses a transport layer to handle the communication between clients and servers. The transport is responsible for:

- **Message Delivery**: Sending JSON-RPC messages between client and server
- **Bidirectional Communication**: Supporting both request-response and server-initiated messages
- **Connection Management**: Establishing and maintaining connections
- **Error Handling**: Detecting and handling transport-level errors

### Supported Transports

1. **Stdio (Standard Input/Output)**: Process-based communication
2. **HTTP with SSE (Server-Sent Events)**: Web-based communication
3. **Custom**: Implement your own transport mechanism

## Transport Architecture

### Transport Interface

All transports implement a common interface for message passing:

```
┌─────────────────────────────────────────┐
│            Application Layer            │
├─────────────────────────────────────────┤
│          JSON-RPC Protocol              │
├─────────────────────────────────────────┤
│      Transport Interface (Read/Write)   │
├─────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌─────┐ │
│  │   Stdio   │  │HTTP + SSE │  │ ... │ │
│  └───────────┘  └───────────┘  └─────┘ │
└─────────────────────────────────────────┘
```

### Message Flow

```
Client                          Server
   │                              │
   │──────── Request ────────────>│
   │                              │
   │<─────── Response ────────────│
   │                              │
   │<──── Notification ───────────│
   │                              │
```

## Stdio Transport

The stdio transport uses standard input and output streams for communication. This is ideal for:

- Local development
- CLI tools
- Process-based architectures
- Desktop applications

### Python Stdio Server

```python
# server.py
from mcp.server.fastmcp import FastMCP
import sys
import logging

# Configure logging to stderr (not stdout, which is used for protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

mcp = FastMCP("stdio-server")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone by name"""
    logger.info(f"Greeting {name}")
    return f"Hello, {name}!"

if __name__ == "__main__":
    # Run with stdio transport (default)
    logger.info("Starting stdio server...")
    mcp.run(transport="stdio")
```

**Key Points:**
- Stdout is reserved for protocol messages
- All logging must go to stderr
- Server reads from stdin, writes to stdout
- Client writes to server's stdin, reads from server's stdout

### Python Stdio Client

```python
# client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Connect to stdio server"""

    # Define server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None  # Optional environment variables
    )

    # Connect to server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # Call tool
            result = await session.call_tool(
                "greet",
                arguments={"name": "World"}
            )

            print(f"Result: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
```

### TypeScript Stdio Server

```typescript
// server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  {
    name: "stdio-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool handlers
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "greet",
        description: "Greet someone by name",
        inputSchema: {
          type: "object",
          properties: {
            name: {
              type: "string",
              description: "Name to greet",
            },
          },
          required: ["name"],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "greet") {
    const { name } = request.params.arguments as { name: string };

    // Log to stderr, not stdout
    console.error(`Greeting ${name}`);

    return {
      content: [
        {
          type: "text",
          text: `Hello, ${name}!`,
        },
      ],
    };
  }

  throw new Error(`Unknown tool: ${request.params.name}`);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("Stdio server running");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

### TypeScript Stdio Client

```typescript
// client.ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

async function main() {
  // Create transport
  const transport = new StdioClientTransport({
    command: "node",
    args: ["server.js"],
  });

  // Create client
  const client = new Client(
    {
      name: "stdio-client",
      version: "1.0.0",
    },
    {
      capabilities: {},
    }
  );

  // Connect
  await client.connect(transport);
  await client.initialize();

  // Call tool
  const result = await client.callTool({
    name: "greet",
    arguments: { name: "World" },
  });

  console.log("Result:", result.content[0].text);

  await client.close();
}

main().catch(console.error);
```

### Stdio with Environment Variables

```python
import os
from mcp import StdioServerParameters

# Pass environment variables to server
server_params = StdioServerParameters(
    command="python",
    args=["server.py"],
    env={
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "API_KEY": os.getenv("API_KEY"),
        "LOG_LEVEL": "DEBUG"
    }
)
```

### Stdio Error Handling

```python
import asyncio
import sys

async def robust_stdio_connection():
    """Stdio connection with error handling"""

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Use session
                result = await session.call_tool("greet", arguments={"name": "World"})
                return result

    except asyncio.TimeoutError:
        print("Server connection timed out", file=sys.stderr)
        raise

    except OSError as e:
        print(f"Failed to start server process: {e}", file=sys.stderr)
        raise

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        raise
```

## HTTP with SSE Transport

HTTP with Server-Sent Events (SSE) enables web-based MCP communication. This is ideal for:

- Web applications
- Browser-based tools
- Remote server access
- Containerized deployments

### Architecture

```
┌─────────────────────────────────────────┐
│              Client                     │
├─────────────────────────────────────────┤
│  HTTP POST         │      SSE           │
│  (Requests) ───────┼─────> (Events)     │
└─────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────┐
│              Server                     │
├─────────────────────────────────────────┤
│  /messages         │   /sse              │
│  (Receive POST)    │   (Send Events)     │
└─────────────────────────────────────────┘
```

### Python SSE Server

```python
# sse_server.py
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response, StreamingResponse
import uvicorn
import json
import asyncio
from typing import AsyncIterator

# Create MCP server
mcp = FastMCP("sse-server")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone"""
    return f"Hello, {name}!"

# SSE endpoint
async def sse_endpoint(request):
    """Server-Sent Events endpoint"""

    async def event_stream() -> AsyncIterator[str]:
        """Generate SSE events"""
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"

            # Keep connection alive
            while True:
                # Send heartbeat every 30 seconds
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            # Client disconnected
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Message endpoint
async def message_endpoint(request):
    """Handle incoming JSON-RPC messages"""
    try:
        message = await request.json()

        # Process message with MCP server
        response = await mcp.handle_message(message)

        return Response(
            content=json.dumps(response),
            media_type="application/json"
        )

    except Exception as e:
        return Response(
            content=json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": message.get("id")
            }),
            media_type="application/json",
            status_code=500
        )

# Create Starlette app
app = Starlette(
    routes=[
        Route("/sse", sse_endpoint),
        Route("/messages", message_endpoint, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Python SSE Client

```python
# sse_client.py
import asyncio
import aiohttp
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    """Connect to SSE server"""

    # Connect using SSE transport
    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # Call tool
            result = await session.call_tool(
                "greet",
                arguments={"name": "World"}
            )

            print(f"Result: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
```

### TypeScript SSE Server (Express)

```typescript
// sse-server.ts
import express from "express";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  SSEServerTransport,
  SSEClientTransport,
} from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const app = express();
app.use(express.json());

// Create MCP server
const mcpServer = new Server(
  {
    name: "sse-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool handlers
mcpServer.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "greet",
        description: "Greet someone",
        inputSchema: {
          type: "object",
          properties: {
            name: { type: "string" },
          },
          required: ["name"],
        },
      },
    ],
  };
});

mcpServer.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "greet") {
    const { name } = request.params.arguments as { name: string };
    return {
      content: [{ type: "text", text: `Hello, ${name}!` }],
    };
  }
  throw new Error("Unknown tool");
});

// SSE endpoint
app.get("/sse", async (req, res) => {
  console.log("Client connected to SSE");

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  // Create SSE transport
  const transport = new SSEServerTransport("/messages", res);
  await mcpServer.connect(transport);

  req.on("close", () => {
    console.log("Client disconnected");
  });
});

// Message endpoint
app.post("/messages", async (req, res) => {
  // Handle JSON-RPC message
  const message = req.body;
  console.log("Received message:", message);

  // Process with MCP server
  // Response sent via SSE
  res.status(202).end();
});

const PORT = 8000;
app.listen(PORT, () => {
  console.log(`SSE server running on http://localhost:${PORT}`);
});
```

### TypeScript SSE Client

```typescript
// sse-client.ts
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
  // Create SSE transport
  const transport = new SSEClientTransport(
    new URL("http://localhost:8000/sse")
  );

  // Create client
  const client = new Client(
    {
      name: "sse-client",
      version: "1.0.0",
    },
    {
      capabilities: {},
    }
  );

  // Connect
  await client.connect(transport);
  await client.initialize();

  // Call tool
  const result = await client.callTool({
    name: "greet",
    arguments: { name: "World" },
  });

  console.log("Result:", result.content[0].text);

  await client.close();
}

main().catch(console.error);
```

### SSE with Authentication

```python
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    SimpleUser,
    requires
)

class TokenAuthBackend(AuthenticationBackend):
    """Bearer token authentication"""

    async def authenticate(self, conn):
        if "Authorization" not in conn.headers:
            return None

        auth = conn.headers["Authorization"]
        scheme, token = auth.split()

        if scheme.lower() != "bearer":
            return None

        # Validate token
        if token != "secret-token":
            return None

        return AuthCredentials(["authenticated"]), SimpleUser("user")

# Add middleware
app = Starlette(
    routes=[...],
    middleware=[
        Middleware(
            AuthenticationMiddleware,
            backend=TokenAuthBackend()
        )
    ]
)

# Protect endpoints
@requires("authenticated")
async def sse_endpoint(request):
    # Only accessible with valid token
    ...

# Client usage
async with sse_client(
    "http://localhost:8000/sse",
    headers={"Authorization": "Bearer secret-token"}
) as (read, write):
    ...
```

### SSE with CORS

```python
from starlette.middleware.cors import CORSMiddleware

app = Starlette(routes=[...])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Custom Transports

You can implement custom transport mechanisms for specialized needs.

### Custom Transport Interface (Python)

```python
from typing import AsyncIterator
from mcp.types import JSONRPCMessage

class CustomTransport:
    """Custom transport implementation"""

    async def read(self) -> AsyncIterator[JSONRPCMessage]:
        """Read messages from transport"""
        raise NotImplementedError

    async def write(self, message: JSONRPCMessage):
        """Write message to transport"""
        raise NotImplementedError

    async def close(self):
        """Close transport"""
        raise NotImplementedError
```

### WebSocket Transport Example (Python)

```python
import asyncio
import json
from typing import AsyncIterator
import websockets
from mcp.types import JSONRPCMessage

class WebSocketTransport:
    """WebSocket-based transport"""

    def __init__(self, websocket):
        self.websocket = websocket
        self.closed = False

    async def read(self) -> AsyncIterator[JSONRPCMessage]:
        """Read messages from WebSocket"""
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    yield json.loads(message)
        except websockets.exceptions.ConnectionClosed:
            self.closed = True

    async def write(self, message: JSONRPCMessage):
        """Write message to WebSocket"""
        if self.closed:
            raise Exception("WebSocket closed")

        await self.websocket.send(json.dumps(message))

    async def close(self):
        """Close WebSocket"""
        if not self.closed:
            await self.websocket.close()
            self.closed = True

# WebSocket server
async def websocket_handler(websocket, path):
    """Handle WebSocket connection"""
    transport = WebSocketTransport(websocket)

    async with ClientSession(transport.read(), transport.write) as session:
        await session.initialize()

        # Handle messages until connection closes
        while not transport.closed:
            await asyncio.sleep(0.1)

# Start WebSocket server
async def main():
    async with websockets.serve(websocket_handler, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Transport with Encryption

```python
from cryptography.fernet import Fernet
import base64

class EncryptedTransport:
    """Transport with message encryption"""

    def __init__(self, underlying_transport, key: bytes):
        self.transport = underlying_transport
        self.cipher = Fernet(key)

    async def read(self) -> AsyncIterator[JSONRPCMessage]:
        """Read and decrypt messages"""
        async for encrypted_message in self.transport.read():
            # Decrypt message
            decrypted = self.cipher.decrypt(encrypted_message)
            yield json.loads(decrypted)

    async def write(self, message: JSONRPCMessage):
        """Encrypt and write message"""
        # Serialize and encrypt
        serialized = json.dumps(message).encode()
        encrypted = self.cipher.encrypt(serialized)

        await self.transport.write(encrypted)

    async def close(self):
        """Close underlying transport"""
        await self.transport.close()

# Usage
key = Fernet.generate_key()
encrypted_transport = EncryptedTransport(base_transport, key)
```

## Message Framing

MCP messages are framed differently depending on the transport.

### Stdio Message Framing

Messages are newline-delimited JSON:

```
{"jsonrpc":"2.0","method":"initialize","params":{...},"id":1}\n
{"jsonrpc":"2.0","result":{...},"id":1}\n
{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}\n
```

**Implementation:**

```python
import sys
import json

# Write message (server to client)
def write_message(message: dict):
    """Write JSON-RPC message to stdout"""
    json.dump(message, sys.stdout)
    sys.stdout.write("\n")
    sys.stdout.flush()

# Read message (client from server)
def read_message() -> dict:
    """Read JSON-RPC message from stdin"""
    line = sys.stdin.readline()
    if not line:
        raise EOFError("No more input")
    return json.loads(line)
```

### SSE Message Framing

Server-to-client messages use SSE format:

```
data: {"jsonrpc":"2.0","result":{...},"id":1}\n\n
data: {"jsonrpc":"2.0","method":"notifications/message"}\n\n
```

Client-to-server uses HTTP POST with JSON body:

```
POST /messages HTTP/1.1
Content-Type: application/json

{"jsonrpc":"2.0","method":"tools/call","params":{...},"id":2}
```

**SSE Event Format:**

```python
def format_sse_message(message: dict) -> str:
    """Format message as SSE event"""
    return f"data: {json.dumps(message)}\n\n"

# Send SSE event
async def send_event(response, message: dict):
    """Send SSE event to client"""
    event = format_sse_message(message)
    await response.write(event.encode())
    await response.drain()
```

### Custom Framing

```python
import struct

class LengthPrefixedTransport:
    """Transport with length-prefixed messages"""

    async def write(self, message: JSONRPCMessage):
        """Write length-prefixed message"""
        # Serialize message
        data = json.dumps(message).encode('utf-8')

        # Write length (4 bytes, big-endian)
        length = struct.pack('>I', len(data))
        await self.stream.write(length)

        # Write message
        await self.stream.write(data)
        await self.stream.drain()

    async def read(self) -> AsyncIterator[JSONRPCMessage]:
        """Read length-prefixed messages"""
        while True:
            # Read length
            length_bytes = await self.stream.readexactly(4)
            length = struct.unpack('>I', length_bytes)[0]

            # Read message
            data = await self.stream.readexactly(length)
            message = json.loads(data.decode('utf-8'))

            yield message
```

## Best Practices

### 1. Logging Best Practices

```python
import sys
import logging

# For stdio servers: ALWAYS log to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Critical for stdio!
)

logger = logging.getLogger(__name__)

@mcp.tool()
def my_tool(param: str) -> str:
    # Log to stderr
    logger.info(f"Tool called with: {param}")
    return result
```

### 2. Connection Timeouts

```python
import asyncio

async def connect_with_timeout(server_params, timeout: float = 30.0):
    """Connect with timeout"""
    try:
        async with asyncio.timeout(timeout):
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return session
    except asyncio.TimeoutError:
        raise Exception(f"Connection timed out after {timeout}s")
```

### 3. Graceful Shutdown

```python
import signal

class GracefulServer:
    """Server with graceful shutdown"""

    def __init__(self):
        self.mcp = FastMCP("server")
        self.should_stop = False

    def setup_signals(self):
        """Setup signal handlers"""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

    def handle_signal(self, sig, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.should_stop = True

    async def run(self):
        """Run server with graceful shutdown"""
        self.setup_signals()

        try:
            await self.mcp.run()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        # Close connections, save state, etc.
```

### 4. Health Checks

```python
# For HTTP/SSE servers
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time()
    }

# For stdio servers
@mcp.tool()
async def ping() -> str:
    """Simple health check tool"""
    return "pong"
```

### 5. Error Recovery

```python
class RobustTransport:
    """Transport with automatic recovery"""

    def __init__(self, create_transport_fn):
        self.create_transport = create_transport_fn
        self.transport = None
        self.max_retries = 3

    async def ensure_connected(self):
        """Ensure transport is connected"""
        if self.transport is None:
            for attempt in range(self.max_retries):
                try:
                    self.transport = await self.create_transport()
                    return
                except Exception as e:
                    logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))
                    else:
                        raise

    async def write(self, message):
        """Write with auto-recovery"""
        await self.ensure_connected()

        try:
            await self.transport.write(message)
        except Exception as e:
            logger.error(f"Write failed: {e}")
            self.transport = None
            await self.ensure_connected()
            await self.transport.write(message)
```

## Troubleshooting

### Common Issues

#### 1. Stdio: Output Mixing

**Problem:** Protocol messages mixed with logs

```python
# ❌ Wrong - logs to stdout
print("Debug message")
logging.basicConfig(stream=sys.stdout)

# ✅ Correct - logs to stderr
print("Debug message", file=sys.stderr)
logging.basicConfig(stream=sys.stderr)
```

#### 2. SSE: Connection Drops

**Problem:** SSE connections timeout

```python
# Add heartbeat
async def sse_endpoint(request):
    async def event_stream():
        while True:
            # Send heartbeat every 30 seconds
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            await asyncio.sleep(30)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

#### 3. Process Not Starting

**Problem:** Server process fails to start

```python
import sys
import subprocess

# Debug process startup
try:
    process = subprocess.Popen(
        ["python", "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Check if process started
    returncode = process.poll()
    if returncode is not None:
        stderr = process.stderr.read()
        print(f"Process failed to start: {stderr}", file=sys.stderr)

except FileNotFoundError:
    print("Server script not found", file=sys.stderr)
except Exception as e:
    print(f"Failed to start process: {e}", file=sys.stderr)
```

#### 4. Message Framing Errors

**Problem:** Invalid JSON in messages

```python
import json

def safe_read_message():
    """Safely read JSON message"""
    try:
        line = sys.stdin.readline()

        if not line:
            raise EOFError("Stream closed")

        # Strip whitespace
        line = line.strip()

        if not line:
            raise ValueError("Empty message")

        return json.loads(line)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        logger.error(f"Raw message: {line}")
        raise
```

#### 5. Transport Debugging

```python
class DebugTransport:
    """Transport wrapper with debugging"""

    def __init__(self, transport):
        self.transport = transport
        self.message_count = 0

    async def read(self):
        """Read with logging"""
        async for message in self.transport.read():
            self.message_count += 1
            logger.debug(f"← Received message #{self.message_count}: {message}")
            yield message

    async def write(self, message):
        """Write with logging"""
        self.message_count += 1
        logger.debug(f"→ Sending message #{self.message_count}: {message}")
        await self.transport.write(message)

# Usage
debug_transport = DebugTransport(base_transport)
```

This comprehensive transport reference covers all aspects of MCP communication mechanisms with production-ready examples and troubleshooting guidance.
