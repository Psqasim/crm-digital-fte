# MCP Server & Client Templates

Production-quality templates for building and integrating with Model Context Protocol (MCP) servers.

## Overview

This directory contains three complete, runnable templates:

1. **hello-world-server/** - Minimal MCP server for learning basics
2. **full-server/** - Comprehensive server with all features
3. **client-integration/** - Client examples for connecting to servers

Each template is fully documented, includes working code, and is ready to run.

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

Each template has its own virtual environment and dependencies:

```bash
# Navigate to any template directory
cd hello-world-server/  # or full-server/ or client-integration/

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Templates

### 1. Hello World Server

**Location**: `hello-world-server/`

**Purpose**: Learn MCP fundamentals with the simplest possible server.

**Features**:
- 1 tool: `greet` (personalized greetings in multiple languages)
- 1 resource: `welcome://message` (static welcome text)
- 1 prompt: `greeting-prompt` (greeting template)

**Run It**:
```bash
cd hello-world-server
python main.py
```

**Best For**:
- First-time MCP developers
- Understanding core concepts
- Quick prototyping

**Learn More**: See [hello-world-server/README.md](hello-world-server/README.md)

---

### 2. Full-Featured Server

**Location**: `full-server/`

**Purpose**: Production-ready server demonstrating all MCP capabilities.

**Features**:
- **7 Tools**: Task management, text analysis, batch processing, notes, stats
- **Dynamic Resources**: Real-time data, documentation, notes
- **3 Prompts**: Task planning, text improvement, note summaries
- **Advanced Capabilities**:
  - Progress reporting for long operations
  - Comprehensive error handling
  - Input validation
  - Structured logging
  - In-memory data store

**Run It**:
```bash
cd full-server
python main.py
```

**Best For**:
- Production deployments
- Understanding best practices
- Complex applications
- Learning advanced patterns

**Learn More**: See [full-server/README.md](full-server/README.md)

---

### 3. Client Integration

**Location**: `client-integration/`

**Purpose**: Connect to and use MCP servers from Python applications.

**Features**:
- Complete client implementation
- Connection management via stdio
- Tool discovery and execution
- Resource reading
- Prompt template usage
- Interactive REPL mode
- Example workflows

**Run Examples**:
```bash
cd client-integration

# Test with hello-world-server
python stdio_client.py hello

# Test with full-server
python stdio_client.py full

# Interactive mode
python stdio_client.py interactive python ../hello-world-server/main.py
```

**Best For**:
- Integrating MCP into applications
- Testing MCP servers
- Understanding client patterns
- Building custom clients

**Learn More**: See [client-integration/README.md](client-integration/README.md)

## Learning Path

### For Beginners

1. **Start with hello-world-server**
   - Read `hello-world-server/README.md`
   - Run the server: `python hello-world-server/main.py`
   - Study `hello-world-server/main.py` to understand structure

2. **Test with the client**
   - Run: `python client-integration/stdio_client.py hello`
   - See how clients interact with servers

3. **Explore interactively**
   - Run: `python client-integration/stdio_client.py interactive python hello-world-server/main.py`
   - Try calling tools, reading resources, using prompts

### For Intermediate Users

1. **Study full-server**
   - Read `full-server/README.md`
   - Understand the architecture section
   - See how multiple tools/resources/prompts work together

2. **Run complete workflows**
   - Run: `python client-integration/stdio_client.py full`
   - Study the task management, text analysis, batch processing examples

3. **Customize for your needs**
   - Add a new tool to full-server (see Customization Guide)
   - Add a new resource type
   - Create custom prompt templates

### For Advanced Users

1. **Production deployment**
   - Replace in-memory storage with database
   - Add authentication and authorization
   - Implement rate limiting
   - Set up monitoring and logging

2. **Integration patterns**
   - Integrate with FastAPI/Flask (see client examples)
   - Connect to LangChain (see integration patterns)
   - Build custom transports (SSE, WebSocket)

3. **Scale and optimize**
   - Add caching layers
   - Implement connection pooling
   - Optimize for concurrent requests
   - Add health checks and metrics

## Architecture Overview

### MCP Server Structure

```
MCP Server
├── Tools (Functions clients can call)
│   ├── @list_tools() - Return available tools
│   └── @call_tool() - Execute tool
├── Resources (Content clients can read)
│   ├── @list_resources() - Return available resources
│   └── @read_resource() - Return resource content
├── Prompts (Templates for AI prompts)
│   ├── @list_prompts() - Return available prompts
│   └── @get_prompt() - Generate prompt from template
└── Server Lifecycle
    └── main() - Initialize and run server
```

### MCP Client Structure

```
MCP Client
├── Connection Management
│   └── connect_to_server() - Establish stdio connection
├── Tool Operations
│   ├── list_tools() - Discover available tools
│   └── call_tool() - Execute tool
├── Resource Operations
│   ├── list_resources() - Discover resources
│   └── read_resource() - Read resource content
└── Prompt Operations
    ├── list_prompts() - Discover prompts
    └── get_prompt() - Get prompt template
```

### Communication Flow

```
Client Application
       ↓
    MCPClient
       ↓ (stdio)
    MCP Server
       ↓
  Server Logic
   (Tools/Resources/Prompts)
```

## Common Use Cases

### 1. Building a Custom Tool Server

Use `hello-world-server` as starting point:
1. Add your tool to `list_tools()`
2. Implement handler in `call_tool()`
3. Test with client: `python stdio_client.py interactive python your_server.py`

### 2. Creating a Data Access Server

Use `full-server` pattern:
1. Replace in-memory storage with database
2. Expose data as resources
3. Add CRUD tools for data management

### 3. Building an AI Assistant Backend

Combine patterns:
1. Tools for actions (from full-server)
2. Resources for knowledge base
3. Prompts for AI interactions
4. Client integration for application

## Testing

### Testing Servers

```bash
# Option 1: MCP Inspector (requires Node.js)
npm install -g @modelcontextprotocol/inspector
mcp-inspector python your_server.py

# Option 2: Client integration examples
python client-integration/stdio_client.py custom python your_server.py

# Option 3: Interactive mode
python client-integration/stdio_client.py interactive python your_server.py
```

### Testing Clients

```bash
# Run example workflows
cd client-integration
python stdio_client.py hello
python stdio_client.py full

# Run unit tests (if pytest installed)
pytest
```

## Customization Guide

### Adding a New Tool

1. **Define the tool** in `list_tools()`:
```python
Tool(
    name="my_tool",
    description="What it does",
    inputSchema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "First parameter"}
        },
        "required": ["param1"]
    }
)
```

2. **Implement handler**:
```python
async def handle_my_tool(args: dict) -> list[TextContent]:
    param1 = args["param1"]
    result = f"Processed: {param1}"
    return [TextContent(type="text", text=result)]
```

3. **Route in call_tool()**:
```python
elif name == "my_tool":
    return await handle_my_tool(arguments)
```

### Adding a New Resource

1. **List the resource**:
```python
Resource(
    uri="data://my-resource",
    name="My Resource",
    description="My resource description",
    mimeType="application/json"
)
```

2. **Handle reads**:
```python
elif uri == "data://my-resource":
    return json.dumps({"key": "value"})
```

### Adding a New Prompt

1. **List the prompt**:
```python
Prompt(
    name="my-prompt",
    description="Generates a prompt for...",
    arguments=[{"name": "param1", "required": True}]
)
```

2. **Generate the prompt**:
```python
elif name == "my-prompt":
    param1 = arguments.get("param1")
    prompt_text = f"Do something with {param1}"
    return GetPromptResult(
        description="My prompt",
        messages=[PromptMessage(
            role="user",
            content=TextContent(type="text", text=prompt_text)
        )]
    )
```

## Troubleshooting

### Server Issues

**Server won't start**
- Check Python version: `python --version` (need 3.10+)
- Install dependencies: `pip install -r requirements.txt`
- Check logs for errors

**Tools not working**
- Verify tool schema is valid JSON
- Check arguments match schema
- Look for errors in logs

**Resources not found**
- List resources to see what's available
- Check URI format
- Verify resource handler exists

### Client Issues

**Can't connect to server**
- Verify server path is correct
- Check server is executable
- Ensure server uses stdio transport

**Tool calls fail**
- Check tool name (case-sensitive)
- Verify arguments are correct
- Check server logs for errors

### General Issues

**Import errors**
- Activate virtual environment
- Install dependencies: `pip install -r requirements.txt`
- Check Python version compatibility

**Permission errors**
- Make scripts executable: `chmod +x main.py`
- Check file permissions
- Verify write access for logs/data

## Best Practices

### Server Development

1. **Start small** - Begin with hello-world, add features incrementally
2. **Validate inputs** - Check all parameters before processing
3. **Handle errors** - Catch and report errors gracefully
4. **Log operations** - Track what's happening for debugging
5. **Document thoroughly** - Explain tools, resources, prompts clearly
6. **Test extensively** - Test all tools, edge cases, errors

### Client Development

1. **Use context managers** - Ensure connections close properly
2. **Cache when appropriate** - Don't fetch static data repeatedly
3. **Handle timeouts** - Long operations may timeout
4. **Validate responses** - Check server responses are valid
5. **Log interactions** - Track calls for debugging
6. **Test error cases** - Network failures, invalid responses, etc.

## Resources

### Documentation
- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io)

### Tools
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) - Web UI for testing
- [MCP CLI](https://github.com/modelcontextprotocol/cli) - Command-line tools

### Community
- [MCP GitHub](https://github.com/modelcontextprotocol)
- [Discord Server](https://discord.gg/modelcontextprotocol)

## Next Steps

1. **Run the examples** - See MCP in action
2. **Study the code** - Understand patterns and structure
3. **Build something** - Create your own server/client
4. **Share** - Contribute back to the community

## Support

For issues with these templates:
1. Check the individual README files
2. Review troubleshooting sections
3. Check MCP documentation
4. Ask in the MCP community

## License

These templates are provided as-is for learning and development purposes.
