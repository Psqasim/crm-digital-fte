# Hello World MCP Server

A minimal MCP (Model Context Protocol) server template demonstrating the core concepts of building an MCP server.

## What This Template Includes

This is the simplest possible MCP server, perfect for learning the basics:

- **One Tool**: `greet` - Generate personalized greetings in multiple languages
- **One Resource**: `welcome://message` - A static welcome message
- **One Prompt**: `greeting-prompt` - Template for creating greeting prompts

## Quick Start

### Installation

```bash
# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Run directly
python main.py

# Or make it executable
chmod +x main.py
./main.py
```

The server will start and communicate via stdin/stdout using the MCP protocol.

## Understanding the Code

### Server Structure

```python
from mcp.server import Server
server = Server("hello-world-server")
```

Every MCP server needs a unique name identifier.

### Tools

Tools are functions that clients can call:

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    # Return list of available tools

@server.call_tool()
async def call_tool(name: str, arguments: Any):
    # Handle tool execution
```

### Resources

Resources are static content that clients can read:

```python
@server.list_resources()
async def list_resources() -> list[Resource]:
    # Return list of available resources

@server.read_resource()
async def read_resource(uri: str) -> str:
    # Return resource content
```

### Prompts

Prompts are templates for generating AI prompts:

```python
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    # Return list of available prompts

@server.get_prompt()
async def get_prompt(name: str, arguments: dict):
    # Generate prompt from template
```

## Testing the Server

Use the MCP inspector or a client to interact with the server:

```bash
# Install MCP inspector
npm install -g @modelcontextprotocol/inspector

# Run inspector
mcp-inspector python main.py
```

Then visit http://localhost:5173 to interact with your server.

## Example Interactions

### Calling the Greet Tool

```json
{
  "name": "greet",
  "arguments": {
    "name": "Alice",
    "language": "spanish"
  }
}
```

Response: "¡Hola, Alice!"

### Reading the Welcome Resource

```json
{
  "uri": "welcome://message"
}
```

Returns the welcome message text.

### Using the Greeting Prompt

```json
{
  "name": "greeting-prompt",
  "arguments": {
    "name": "Bob",
    "style": "enthusiastic"
  }
}
```

Returns a prompt template for creating an enthusiastic greeting.

## Next Steps

Once you understand this minimal server:

1. **Add more tools** - Create new functions with different capabilities
2. **Add dynamic resources** - Generate resources from external data
3. **Enhance prompts** - Create more sophisticated prompt templates
4. **Add error handling** - Implement robust error checking
5. **Add logging** - Track server activity

See the `full-server/` template for a more complete example with all these features.

## Common Issues

### Server won't start
- Check Python version (requires 3.10+)
- Ensure all dependencies are installed
- Check logs for error messages

### Client can't connect
- Verify server is running via stdio
- Check that client is configured correctly
- Ensure MCP protocol versions match

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io)

## License

This template is provided as-is for learning and development purposes.
