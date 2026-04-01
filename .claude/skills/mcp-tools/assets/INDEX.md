# MCP Templates Quick Reference

## Template Selection Guide

**Choose the right template for your needs:**

| Template | When to Use | Lines of Code | Complexity |
|----------|-------------|---------------|------------|
| **hello-world-server** | First MCP project, learning basics | 209 | Simple |
| **full-server** | Production apps, all features | 867 | Advanced |
| **client-integration** | Connecting to MCP servers | 562 | Intermediate |

## What's Included

### hello-world-server/
```
Minimal MCP server (209 lines)
├── 1 Tool: greet (multi-language)
├── 1 Resource: welcome message
├── 1 Prompt: greeting template
└── Full documentation (178 lines)
```

### full-server/
```
Production-ready MCP server (867 lines)
├── 7 Tools:
│   ├── Task management (add, list, complete)
│   ├── Text analysis (statistics)
│   ├── Batch processing (progress tracking)
│   ├── Note taking (with tags)
│   └── Server statistics
├── Dynamic Resources:
│   ├── Documentation (getting started, API)
│   ├── Real-time data (tasks, stats)
│   └── User-generated (notes)
├── 3 Prompts:
│   ├── Task planning
│   ├── Text improvement
│   └── Note summaries
└── Features:
    ├── Progress reporting
    ├── Error handling
    ├── Input validation
    └── Structured logging
```

### client-integration/
```
Complete MCP client (562 lines)
├── MCPClient class:
│   ├── Connection management
│   ├── Tool operations
│   ├── Resource operations
│   └── Prompt operations
├── Example workflows:
│   ├── Hello world demo
│   ├── Full server demo
│   └── Custom server
├── Interactive REPL mode
└── Integration patterns:
    ├── FastAPI example
    └── LangChain example
```

## Quick Commands

### Run Hello World
```bash
# Start server
cd hello-world-server && python main.py

# Test with client
cd client-integration
python stdio_client.py hello
```

### Run Full Server
```bash
# Start server
cd full-server && python main.py

# Test with client
cd client-integration
python stdio_client.py full
```

### Interactive Mode
```bash
cd client-integration
python stdio_client.py interactive python ../hello-world-server/main.py
```

### Custom Server
```bash
cd client-integration
python stdio_client.py custom python /path/to/your/server.py
```

## Template Matrix

### Features by Template

| Feature | hello-world | full-server | client |
|---------|------------|-------------|--------|
| Basic Tools | ✓ | ✓ | - |
| Multiple Tools | - | ✓ | - |
| Static Resources | ✓ | ✓ | - |
| Dynamic Resources | - | ✓ | - |
| Prompts | ✓ | ✓ | - |
| Error Handling | Basic | Advanced | ✓ |
| Progress Reporting | - | ✓ | ✓ |
| Input Validation | - | ✓ | - |
| Structured Logging | Basic | Advanced | ✓ |
| Data Storage | - | In-memory | - |
| Tool Calls | - | - | ✓ |
| Resource Reading | - | - | ✓ |
| Prompt Usage | - | - | ✓ |
| Interactive Mode | - | - | ✓ |

### Use Case Matrix

| Use Case | Recommended Template |
|----------|---------------------|
| Learning MCP basics | hello-world-server |
| Production deployment | full-server |
| Complex workflows | full-server |
| Client integration | client-integration |
| Testing servers | client-integration |
| Quick prototype | hello-world-server |
| Task management | full-server |
| Data processing | full-server |
| API integration | client-integration |

## File Structure

```
assets/
├── README.md                    (Overview & learning path)
├── INDEX.md                     (This file - quick reference)
├── hello-world-server/
│   ├── main.py                  (209 lines - minimal server)
│   ├── README.md                (178 lines - documentation)
│   └── requirements.txt         (Dependencies)
├── full-server/
│   ├── main.py                  (867 lines - complete server)
│   ├── README.md                (422 lines - comprehensive docs)
│   └── requirements.txt         (Dependencies + optional)
└── client-integration/
    ├── stdio_client.py          (562 lines - complete client)
    ├── README.md                (451 lines - integration guide)
    └── requirements.txt         (Dependencies + integrations)
```

## Code Statistics

| Template | Python Code | Documentation | Total |
|----------|-------------|---------------|-------|
| hello-world-server | 209 | 178 | 387 |
| full-server | 867 | 422 | 1,289 |
| client-integration | 562 | 451 | 1,013 |
| **TOTAL** | **1,638** | **1,051** | **2,689** |

## API Coverage

### Tools API
- **hello-world**: 1 tool (basic pattern)
- **full-server**: 7 tools (all patterns)
- **client**: Calls any tool

### Resources API
- **hello-world**: 1 static resource
- **full-server**: 4+ dynamic resources
- **client**: Reads any resource

### Prompts API
- **hello-world**: 1 template
- **full-server**: 3 sophisticated templates
- **client**: Uses any prompt

## Learning Progression

### Week 1: Basics
1. Read `README.md`
2. Run hello-world-server
3. Test with client
4. Understand structure

### Week 2: Advanced
1. Study full-server
2. Run example workflows
3. Add custom tool
4. Deploy locally

### Week 3: Integration
1. Build custom client
2. Integrate with app
3. Add persistence
4. Production setup

### Week 4: Production
1. Replace in-memory storage
2. Add authentication
3. Implement monitoring
4. Deploy to production

## Common Patterns

### Server Patterns
```python
# Tool pattern (from hello-world)
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(...)]

@server.call_tool()
async def call_tool(name, arguments):
    return handle_tool(name, arguments)
```

### Client Patterns
```python
# Connection pattern (from client-integration)
async with client.connect_to_server("python", ["server.py"]):
    result = await client.call_tool("my_tool", {...})
```

### Resource Patterns
```python
# Dynamic resource (from full-server)
@server.list_resources()
async def list_resources():
    return [Resource(uri=f"data://{key}", ...)]

@server.read_resource()
async def read_resource(uri):
    return get_data_for_uri(uri)
```

## Next Steps

1. **Choose your template** (see selection guide above)
2. **Read the README** for that template
3. **Run the code** to see it in action
4. **Modify for your needs** using customization guides
5. **Deploy to production** following best practices

## Resources

- **Main README**: `README.md` - Complete overview
- **Individual READMEs**: Each template has detailed docs
- **MCP Docs**: https://modelcontextprotocol.io
- **Python SDK**: https://github.com/modelcontextprotocol/python-sdk

## Support

For help:
1. Check template README
2. Review troubleshooting sections
3. See MCP documentation
4. Ask in MCP community

---

**All templates are production-quality, fully documented, and ready to run.**
