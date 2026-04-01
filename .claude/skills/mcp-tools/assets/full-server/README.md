# Full-Featured MCP Server

A comprehensive, production-ready MCP server template demonstrating all major features and best practices.

## Features Demonstrated

### Tools (7 total)
- **Task Management**: Add, list, and complete tasks with priorities and due dates
- **Text Analysis**: Analyze text statistics with optional detailed metrics
- **Batch Processing**: Process multiple items with progress reporting
- **Note Taking**: Save and retrieve notes with tags
- **Statistics**: Get server metrics and performance data

### Resources (Dynamic)
- **Static Documentation**: Getting started guide and API reference
- **Dynamic Data**: Real-time task lists and statistics
- **Note Resources**: Individual notes accessible as resources

### Prompts (3 templates)
- **Task Planning**: Generate detailed project task breakdowns
- **Text Improvement**: Get suggestions for improving text
- **Note Summary**: Summarize multiple notes with different formats

### Advanced Features
- Progress reporting for long-running operations
- Comprehensive error handling and validation
- Structured logging with multiple levels
- In-memory data store (easily replaceable with database)
- Input validation and type checking
- Detailed API documentation

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Direct execution
python main.py

# Or with executable permissions
chmod +x main.py
./main.py
```

### Testing with MCP Inspector

```bash
# Install inspector (requires Node.js)
npm install -g @modelcontextprotocol/inspector

# Launch inspector
mcp-inspector python main.py
```

Visit http://localhost:5173 to interact with the server through the web UI.

## Usage Examples

### Task Management

#### Add a Task
```json
{
  "tool": "add_task",
  "arguments": {
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication to the API",
    "priority": "high",
    "due_date": "2026-03-01"
  }
}
```

#### List Tasks by Priority
```json
{
  "tool": "list_tasks",
  "arguments": {
    "priority": "high",
    "completed": false
  }
}
```

#### Complete a Task
```json
{
  "tool": "complete_task",
  "arguments": {
    "task_id": 0
  }
}
```

### Text Analysis

#### Basic Analysis
```json
{
  "tool": "analyze_text",
  "arguments": {
    "text": "The quick brown fox jumps over the lazy dog.",
    "include_details": true
  }
}
```

Response includes:
- Character count
- Word count
- Line count
- Sentence count (with details)
- Average word length (with details)
- Average sentence length (with details)

### Batch Processing

```json
{
  "tool": "process_batch",
  "arguments": {
    "items": ["hello", "world", "mcp", "server"],
    "operation": "uppercase"
  }
}
```

Watch the logs for progress updates as items are processed.

### Note Taking

#### Save a Note
```json
{
  "tool": "save_note",
  "arguments": {
    "key": "meeting-2026-02-11",
    "content": "Discussed MCP integration strategy. Key points: standardize tools, improve documentation, add examples.",
    "tags": ["meeting", "strategy", "mcp"]
  }
}
```

#### Read Note as Resource
```json
{
  "resource": "notes://meeting-2026-02-11"
}
```

### Server Statistics

```json
{
  "tool": "get_stats",
  "arguments": {
    "include_details": true
  }
}
```

## Architecture

### Code Organization

```
main.py
├── Logging Configuration
├── Server Configuration
├── Utility Functions
│   ├── validate_input()
│   ├── simulate_long_operation()
│   └── log_to_client()
├── Tools
│   ├── @list_tools()
│   ├── @call_tool()
│   └── Tool Handlers (8 functions)
├── Resources
│   ├── @list_resources()
│   └── @read_resource()
├── Prompts
│   ├── @list_prompts()
│   └── @get_prompt()
└── Server Lifecycle
    └── main()
```

### Data Store

The server uses an in-memory dictionary for demonstration:

```python
data_store = {
    "tasks": [],        # List of task dictionaries
    "notes": {},        # Key-value note storage
    "counters": {       # Performance metrics
        "api_calls": 0,
        "errors": 0
    }
}
```

**Production Note**: Replace with a proper database (SQLite, PostgreSQL, etc.) for persistence.

### Error Handling Pattern

All tool calls follow this pattern:

```python
try:
    # Increment metrics
    # Log the operation
    # Validate inputs
    # Execute operation
    # Return success response
except Exception as e:
    # Increment error counter
    # Log error with details
    # Re-raise for client handling
```

### Progress Reporting

Long-running operations use async generators:

```python
async def simulate_long_operation(duration: float, task_name: str):
    steps = 10
    for i in range(steps):
        await asyncio.sleep(duration / steps)
        progress = (i + 1) / steps
        logger.info(f"{task_name}: {progress * 100:.0f}% complete")
        yield progress
```

## Customization Guide

### Adding a New Tool

1. Add tool definition to `list_tools()`:
```python
Tool(
    name="my_tool",
    description="What it does",
    inputSchema={...}
)
```

2. Add handler function:
```python
async def handle_my_tool(args: dict) -> list[TextContent]:
    # Validate inputs
    # Perform operation
    # Return results
```

3. Route in `call_tool()`:
```python
elif name == "my_tool":
    return await handle_my_tool(arguments)
```

### Adding a New Resource

1. Add to `list_resources()`:
```python
Resource(
    uri="data://my-resource",
    name="My Resource",
    description="Description",
    mimeType="application/json"
)
```

2. Handle in `read_resource()`:
```python
elif uri == "data://my-resource":
    return json.dumps(my_data)
```

### Adding a New Prompt

1. Add to `list_prompts()`:
```python
Prompt(
    name="my-prompt",
    description="What it generates",
    arguments=[...]
)
```

2. Handle in `get_prompt()`:
```python
elif name == "my-prompt":
    # Build prompt from arguments
    return GetPromptResult(...)
```

## Production Considerations

### Persistence
- Replace in-memory data store with database
- Consider SQLite for simple deployments
- Use PostgreSQL/MySQL for production scale

### Security
- Validate all inputs rigorously
- Sanitize user-provided data
- Implement rate limiting
- Add authentication if needed

### Performance
- Add caching for frequently accessed resources
- Implement connection pooling for databases
- Use async I/O for external calls
- Monitor memory usage

### Monitoring
- Integrate with logging platforms (Sentry, LogDNA)
- Add structured logging
- Track metrics (response times, error rates)
- Set up alerting

### Testing
- Write unit tests for each tool handler
- Add integration tests for workflows
- Test error conditions
- Validate input schemas

## Troubleshooting

### Common Issues

**Server won't start**
- Check Python version (3.10+ required)
- Verify all dependencies installed
- Check for syntax errors in modifications

**Tools not appearing**
- Ensure tool is in `list_tools()` return
- Check tool schema syntax
- Verify server restarted after changes

**Resources not loading**
- Check URI format matches pattern
- Ensure resource listed in `list_resources()`
- Verify data exists for dynamic resources

**Prompts not working**
- Validate prompt name matches
- Check argument requirements
- Ensure proper GetPromptResult format

### Debug Mode

Enable detailed logging:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Logs

Watch logs for:
- Tool calls with arguments
- Resource accesses
- Errors with stack traces
- Progress updates

## API Reference

### Tools

| Tool | Description | Required Args | Optional Args |
|------|-------------|---------------|---------------|
| `add_task` | Create new task | title | description, priority, due_date |
| `list_tasks` | List all tasks | - | priority, completed |
| `complete_task` | Mark task done | task_id | - |
| `analyze_text` | Text statistics | text | include_details |
| `process_batch` | Batch processing | items, operation | - |
| `save_note` | Save note | key, content | tags |
| `get_stats` | Server statistics | - | include_details |

### Resources

| URI Pattern | Description | Type |
|-------------|-------------|------|
| `docs://getting-started` | Getting started guide | Markdown |
| `docs://api-reference` | API documentation | Markdown |
| `data://tasks` | All tasks | JSON |
| `data://stats` | Server statistics | JSON |
| `notes://{key}` | Individual note | Text |

### Prompts

| Prompt | Description | Required Args | Optional Args |
|--------|-------------|---------------|---------------|
| `task-planning` | Project breakdown | project_name, goal | complexity |
| `text-improvement` | Text suggestions | text | style |
| `note-summary` | Summarize notes | note_keys | format |

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [Best Practices Guide](https://modelcontextprotocol.io/docs/best-practices)

## License

This template is provided as-is for learning and development purposes.
