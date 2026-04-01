# MCP Reference Documentation

This directory contains comprehensive reference documentation for the Model Context Protocol (MCP).

## Quick Navigation

### Core References

1. **[Core Concepts](./core-concepts.md)** (1,069 lines)
   - MCP architecture and principles
   - JSON-RPC protocol fundamentals
   - Capabilities and negotiation
   - Primitives (Resources, Prompts, Tools)
   - Message types and error handling
   - Security model and best practices

2. **[Servers](./servers.md)** (1,533 lines)
   - Complete server development guide
   - Python (FastMCP) and TypeScript implementations
   - Implementing resources, prompts, and tools
   - Server lifecycle and state management
   - Advanced patterns (streaming, subscriptions, progress)
   - Production-ready examples
   - Testing and troubleshooting

3. **[Clients](./clients.md)** (1,379 lines)
   - Client integration patterns
   - Connecting to servers (stdio, HTTP SSE)
   - Multi-server management
   - Using primitives (resources, prompts, tools)
   - Advanced patterns (caching, batching, circuit breakers)
   - Error handling and recovery
   - Production best practices

4. **[Transports](./transports.md)** (1,166 lines)
   - Stdio transport (process-based)
   - HTTP with SSE transport (web-based)
   - Custom transport implementation
   - Message framing protocols
   - Authentication and security
   - Connection management
   - Troubleshooting transport issues

## Quick Start

### Building Your First Server

```python
# See servers.md for complete guide
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def greet(name: str) -> str:
    """Greet someone"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

### Building Your First Client

```python
# See clients.md for complete guide
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "greet",
                arguments={"name": "World"}
            )
            print(result.content[0].text)
```

## Reference Organization

### By Topic

**Getting Started**
- core-concepts.md: Overview and Architecture
- servers.md: Getting Started (Python/TypeScript)
- clients.md: Getting Started (Python/TypeScript)
- transports.md: Overview

**Development**
- servers.md: Core Components, Implementing Primitives
- clients.md: Using Primitives
- core-concepts.md: Primitives, Message Types

**Advanced Topics**
- servers.md: Advanced Patterns
- clients.md: Advanced Patterns
- transports.md: Custom Transports
- core-concepts.md: Security Model

**Deployment**
- servers.md: Best Practices, Production Example
- clients.md: Best Practices
- transports.md: Best Practices
- core-concepts.md: Best Practices

**Troubleshooting**
- All files: Dedicated troubleshooting sections

### By Use Case

**"I want to expose data to AI agents"**
→ Start with servers.md → Resources section

**"I want to create AI-callable functions"**
→ Start with servers.md → Tools section

**"I want to create prompt templates"**
→ Start with servers.md → Prompts section

**"I want to connect to MCP servers"**
→ Start with clients.md → Connecting to Servers

**"I want to build a web-based MCP server"**
→ Start with transports.md → HTTP with SSE Transport

**"I want to understand the protocol"**
→ Start with core-concepts.md → JSON-RPC Protocol

**"I want to secure my MCP server"**
→ Start with core-concepts.md → Security Model

## Coverage Summary

### Servers (servers.md)
- ✅ Python FastMCP framework
- ✅ TypeScript Server SDK
- ✅ Resource implementation and templates
- ✅ Prompt creation and messages
- ✅ Tool implementation with validation
- ✅ Lifecycle hooks (startup/shutdown)
- ✅ State management
- ✅ Error handling
- ✅ Advanced patterns (streaming, subscriptions, progress)
- ✅ Security best practices
- ✅ Performance optimization
- ✅ Testing strategies
- ✅ Complete production example

### Clients (clients.md)
- ✅ Python client implementation
- ✅ TypeScript client implementation
- ✅ Stdio transport connections
- ✅ HTTP SSE transport connections
- ✅ Multi-server management
- ✅ Resource operations
- ✅ Prompt operations
- ✅ Tool execution
- ✅ Subscriptions and notifications
- ✅ Advanced patterns (caching, batching, circuit breakers)
- ✅ Error handling and recovery
- ✅ Connection lifecycle management
- ✅ Production best practices

### Transports (transports.md)
- ✅ Stdio transport (Python/TypeScript)
- ✅ HTTP SSE transport (Python/TypeScript)
- ✅ Custom transport implementation
- ✅ WebSocket transport example
- ✅ Message framing protocols
- ✅ Authentication and authorization
- ✅ CORS configuration
- ✅ Connection timeouts
- ✅ Graceful shutdown
- ✅ Health checks
- ✅ Error recovery
- ✅ Debugging techniques

### Core Concepts (core-concepts.md)
- ✅ MCP architecture
- ✅ Client-server model
- ✅ JSON-RPC protocol
- ✅ Request/response/notification formats
- ✅ Standard methods
- ✅ Capability negotiation
- ✅ Primitives (Resources, Prompts, Tools)
- ✅ Message types
- ✅ Error codes and handling
- ✅ Security model
- ✅ Authentication and authorization
- ✅ Input validation
- ✅ Rate limiting
- ✅ Secrets management
- ✅ Best practices

## Code Examples

All reference files include:
- ✅ Complete, runnable code examples
- ✅ Python and TypeScript implementations
- ✅ Error handling patterns
- ✅ Production-ready practices
- ✅ Common patterns and anti-patterns
- ✅ Troubleshooting scenarios

## Total Coverage

- **5,181 lines** of comprehensive documentation
- **4 major reference documents**
- **Both Python and TypeScript** implementations
- **Production-ready** examples throughout
- **Complete coverage** from hello-world to production

## Contributing

These references are based on the official MCP documentation and SDK implementations. When updating:

1. Keep examples practical and runnable
2. Include both Python and TypeScript where applicable
3. Add troubleshooting tips from real-world issues
4. Update the line counts in this README
5. Maintain consistency across all files

## Version

These references are current as of MCP Protocol Version: 2024-11-05

Last Updated: 2026-02-11
