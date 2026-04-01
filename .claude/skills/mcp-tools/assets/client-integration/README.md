# MCP Client Integration Examples

Complete examples for connecting to MCP servers and using their capabilities from Python client applications.

## Overview

This package demonstrates:
- Connecting to MCP servers via stdio transport
- Discovering server capabilities (tools, resources, prompts)
- Calling tools with various argument types
- Reading static and dynamic resources
- Using prompt templates
- Error handling and best practices
- Interactive REPL for server exploration

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### Run Hello World Examples

```bash
python stdio_client.py hello
```

This connects to the hello-world-server and demonstrates:
- Listing and calling the `greet` tool
- Reading the welcome resource
- Using the greeting prompt template

#### Run Full Server Examples

```bash
python stdio_client.py full
```

This connects to the full-server and demonstrates:
- Task management workflow (add, list, complete)
- Text analysis
- Batch processing with progress
- Note taking and retrieval
- Server statistics
- Prompt templates for planning

#### Interactive Mode

```bash
python stdio_client.py interactive python ../hello-world-server/main.py
```

Launch an interactive REPL to explore any MCP server:
- Type `tools` to list available tools
- Type `resources` to list resources
- Type `prompts` to list prompts
- Type `call <tool> <json>` to call a tool
- Type `read <uri>` to read a resource
- Type `prompt <name> <json>` to use a prompt
- Type `quit` to exit

#### Connect to Custom Server

```bash
python stdio_client.py custom python /path/to/your/server.py
```

## Client Architecture

### MCPClient Class

The `MCPClient` class provides a clean interface for MCP interactions:

```python
class MCPClient:
    async def connect_to_server(command, args)  # Connect via stdio
    async def list_tools()                       # Discover tools
    async def call_tool(name, arguments)         # Execute tools
    async def list_resources()                   # Discover resources
    async def read_resource(uri)                 # Read resources
    async def list_prompts()                     # Discover prompts
    async def get_prompt(name, arguments)        # Use prompts
```

### Connection Pattern

```python
from stdio_client import MCPClient

client = MCPClient()

async with client.connect_to_server("python", ["server.py"]):
    # Client is connected, session initialized
    tools = await client.list_tools()
    result = await client.call_tool("my_tool", {"arg": "value"})
    # Connection automatically closed on exit
```

## Usage Examples

### Example 1: Calling a Simple Tool

```python
async def example_simple_tool():
    client = MCPClient()

    async with client.connect_to_server("python", ["../hello-world-server/main.py"]):
        # Call the greet tool
        result = await client.call_tool("greet", {
            "name": "Alice",
            "language": "french"
        })

        # Result will contain: "Bonjour, Alice!"
```

### Example 2: Reading Resources

```python
async def example_read_resource():
    client = MCPClient()

    async with client.connect_to_server("python", ["../full-server/main.py"]):
        # List all resources
        resources = await client.list_resources()

        # Read documentation
        doc = await client.read_resource("docs://getting-started")

        # Read dynamic data
        tasks = await client.read_resource("data://tasks")
```

### Example 3: Using Prompts

```python
async def example_use_prompt():
    client = MCPClient()

    async with client.connect_to_server("python", ["../full-server/main.py"]):
        # Get a prompt template
        prompt = await client.get_prompt("task-planning", {
            "project_name": "My Project",
            "goal": "Build a feature",
            "complexity": "medium"
        })

        # Use the prompt with an AI model
        # prompt.messages contains the formatted prompt
```

### Example 4: Task Management Workflow

```python
async def example_task_workflow():
    client = MCPClient()

    async with client.connect_to_server("python", ["../full-server/main.py"]):
        # Add a task
        await client.call_tool("add_task", {
            "title": "Implement feature X",
            "priority": "high",
            "due_date": "2026-03-01"
        })

        # List all high priority tasks
        await client.call_tool("list_tasks", {
            "priority": "high",
            "completed": False
        })

        # Complete task 0
        await client.call_tool("complete_task", {
            "task_id": 0
        })
```

### Example 5: Error Handling

```python
async def example_error_handling():
    client = MCPClient()

    try:
        async with client.connect_to_server("python", ["server.py"]):
            try:
                # Try to call a tool
                result = await client.call_tool("my_tool", {
                    "invalid_arg": "value"
                })
            except Exception as tool_error:
                print(f"Tool error: {tool_error}")
                # Handle tool-specific errors

    except Exception as connection_error:
        print(f"Connection error: {connection_error}")
        # Handle connection errors
```

## Advanced Patterns

### Auto-Discovery Pattern

Automatically discover and use server capabilities:

```python
async def auto_discover_server():
    client = MCPClient()

    async with client.connect_to_server("python", ["server.py"]):
        # Discover what's available
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()

        # Use the first tool (if any)
        if tools:
            tool = tools[0]
            print(f"Calling {tool['name']}...")

            # Build arguments from schema
            args = {}
            if tool['schema']:
                required = tool['schema'].get('required', [])
                # Populate required arguments with defaults
                for arg in required:
                    args[arg] = "default_value"

            result = await client.call_tool(tool['name'], args)
```

### Batch Operations Pattern

Process multiple operations efficiently:

```python
async def batch_operations():
    client = MCPClient()

    async with client.connect_to_server("python", ["../full-server/main.py"]):
        # Add multiple tasks
        tasks = [
            {"title": "Task 1", "priority": "high"},
            {"title": "Task 2", "priority": "medium"},
            {"title": "Task 3", "priority": "low"}
        ]

        for task_data in tasks:
            await client.call_tool("add_task", task_data)

        # Process them as a batch
        await client.call_tool("process_batch", {
            "items": [t["title"] for t in tasks],
            "operation": "uppercase"
        })
```

### Resource Caching Pattern

Cache frequently accessed resources:

```python
class CachingClient:
    def __init__(self, client: MCPClient):
        self.client = client
        self.cache = {}

    async def read_resource_cached(self, uri: str):
        if uri not in self.cache:
            result = await self.client.read_resource(uri)
            self.cache[uri] = result
        return self.cache[uri]
```

## Integration Patterns

### Integration with FastAPI

```python
from fastapi import FastAPI, HTTPException
from stdio_client import MCPClient

app = FastAPI()
client = MCPClient()

@app.on_event("startup")
async def startup():
    # Connect to server at startup
    await client.connect_to_server("python", ["server.py"])

@app.post("/call-tool")
async def call_tool(tool_name: str, arguments: dict):
    try:
        result = await client.call_tool(tool_name, arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Integration with LangChain

```python
from langchain.tools import Tool
from stdio_client import MCPClient

async def create_langchain_tools(client: MCPClient):
    """Convert MCP tools to LangChain tools."""
    tools_info = await client.list_tools()

    langchain_tools = []
    for tool_info in tools_info:
        async def call_mcp_tool(arguments: str):
            import json
            args = json.loads(arguments)
            return await client.call_tool(tool_info['name'], args)

        langchain_tools.append(Tool(
            name=tool_info['name'],
            description=tool_info['description'],
            func=call_mcp_tool
        ))

    return langchain_tools
```

## Testing Your Integration

### Unit Test Example

```python
import pytest
from stdio_client import MCPClient

@pytest.mark.asyncio
async def test_tool_call():
    client = MCPClient()

    async with client.connect_to_server("python", ["../hello-world-server/main.py"]):
        result = await client.call_tool("greet", {
            "name": "Test",
            "language": "english"
        })

        assert result is not None
        assert "Hello, Test" in str(result)

@pytest.mark.asyncio
async def test_resource_read():
    client = MCPClient()

    async with client.connect_to_server("python", ["../full-server/main.py"]):
        result = await client.read_resource("docs://getting-started")

        assert result is not None
        assert "Getting Started" in str(result)
```

## Troubleshooting

### Common Issues

**Connection Fails**
- Check server command and path
- Ensure server has execute permissions
- Verify Python environment has required packages
- Check server logs for startup errors

**Tool Call Fails**
- Verify tool name is correct (case-sensitive)
- Check arguments match schema
- Ensure all required arguments are provided
- Check server logs for errors

**Resource Not Found**
- List resources to see what's available
- Check URI format matches server pattern
- Verify resource exists (for dynamic resources)

**Prompt Generation Fails**
- Check prompt name is correct
- Verify arguments match requirements
- Ensure required arguments are provided

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Monitoring Connections

Track connection lifecycle:

```python
async with client.connect_to_server("python", ["server.py"]) as conn:
    print(f"Connected: {client.session.info.name}")
    # Use client
    print("Connection still active")
# Connection closed here
print("Connection closed")
```

## Best Practices

1. **Always use context managers** - Ensures proper cleanup
2. **Handle errors gracefully** - Network and tool errors can occur
3. **Validate arguments** - Check against schema before calling
4. **Cache when appropriate** - Don't fetch static resources repeatedly
5. **Log operations** - Track what your client is doing
6. **Test thoroughly** - Write tests for all tool interactions
7. **Version carefully** - MCP protocol may evolve

## Performance Tips

- Reuse client connections when possible
- Cache static resources
- Use batch operations for multiple items
- Handle progress updates for long operations
- Implement timeouts for tool calls
- Pool connections for concurrent operations

## Security Considerations

- Validate server identity before connecting
- Sanitize all inputs to tools
- Don't log sensitive data
- Use secure transport in production
- Implement rate limiting
- Validate server responses

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io)

## License

This template is provided as-is for learning and development purposes.
