# Single-Agent Patterns

Comprehensive patterns for building single-agent systems with tools, structured outputs, and model configurations.

## Table of Contents
- Basic Agent Configuration
- Tool Integration Patterns
- Structured Output Patterns
- Model Settings and Configuration
- Tool Context Management
- Advanced Tool Patterns

## Basic Agent Configuration

### Minimal Agent

```python
from agents import Agent, Runner
import asyncio

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant."
)

async def main():
    result = await Runner.run(agent, "Hello!")
    print(result.final_output)

asyncio.run(main())
```

### Agent with Model Selection

```python
agent = Agent(
    name="Fast Agent",
    instructions="Respond concisely.",
    model="gpt-4o-mini"  # Options: gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.
)
```

### Agent with Custom ModelSettings

```python
from agents import Agent, ModelSettings

agent = Agent(
    name="Creative Writer",
    instructions="Write creatively.",
    model_settings=ModelSettings(
        temperature=0.9,           # Higher = more creative
        max_tokens=1000,          # Limit output length
        top_p=0.95,               # Nucleus sampling
        frequency_penalty=0.5,    # Reduce repetition
        presence_penalty=0.3      # Encourage topic diversity
    )
)
```

## Tool Integration Patterns

### Simple Function Tool

```python
from agents import function_tool

@function_tool
def calculate_tip(bill_amount: float, tip_percentage: float = 20.0) -> str:
    """Calculate tip amount for a bill.

    Args:
        bill_amount: The total bill amount in dollars
        tip_percentage: Tip percentage (default 20%)

    Returns:
        Formatted tip calculation
    """
    tip = bill_amount * (tip_percentage / 100)
    total = bill_amount + tip
    return f"Bill: ${bill_amount:.2f}, Tip ({tip_percentage}%): ${tip:.2f}, Total: ${total:.2f}"

agent = Agent(
    name="Tip Calculator",
    instructions="Help calculate tips for bills.",
    tools=[calculate_tip]
)
```

**Key points:**
- Function name becomes tool name (use `name_override` to customize)
- Docstring becomes tool description
- Args section describes parameters to the LLM
- Type hints generate JSON schema automatically
- Default values are supported

### Async Function Tools

```python
import asyncio
import httpx

@function_tool
async def fetch_user_profile(user_id: int) -> str:
    """Fetch user profile from API.

    Args:
        user_id: The user's ID number
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/users/{user_id}")
        data = response.json()
        return f"User: {data['name']}, Email: {data['email']}"

agent = Agent(
    name="User Lookup",
    tools=[fetch_user_profile]
)
```

### Multiple Tools with Parallel Execution

By default, the agent can call multiple tools in parallel:

```python
@function_tool
def get_stock_price(symbol: str) -> str:
    """Get current stock price.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL)
    """
    # Simulated - use real API in production
    prices = {"AAPL": 175.50, "GOOGL": 142.30, "MSFT": 380.00}
    return f"{symbol}: ${prices.get(symbol, 'N/A')}"

@function_tool
def get_company_info(symbol: str) -> str:
    """Get company information.

    Args:
        symbol: Stock ticker symbol
    """
    companies = {
        "AAPL": "Apple Inc. - Technology",
        "GOOGL": "Alphabet Inc. - Technology",
        "MSFT": "Microsoft Corp. - Technology"
    }
    return companies.get(symbol, "Unknown company")

agent = Agent(
    name="Stock Assistant",
    tools=[get_stock_price, get_company_info],
    model_settings=ModelSettings(
        parallel_tool_calls=True  # Default: allows parallel execution
    )
)

# When user asks "What's the price and info for AAPL?",
# both tools are called simultaneously
```

### Disable Parallel Tool Calls

Force sequential tool execution:

```python
agent = Agent(
    name="Sequential Agent",
    tools=[tool1, tool2, tool3],
    model_settings=ModelSettings(
        parallel_tool_calls=False  # Tools called one at a time
    )
)
```

### Tool with Custom Name and Description

```python
@function_tool(
    name_override="search_docs",
    description_override="Search the documentation database for relevant information"
)
def internal_search_function(query: str) -> str:
    # Implementation
    return f"Results for: {query}"
```

### Disable Docstring Parsing

```python
@function_tool(use_docstring_info=False)
def my_tool(arg1: str) -> str:
    """This docstring is ignored."""
    return arg1.upper()
```

## Structured Output Patterns

### Basic Pydantic Model Output

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(description="Product name")
    price: float = Field(description="Price in USD")
    category: str = Field(description="Product category")
    in_stock: bool = Field(description="Availability status")

agent = Agent(
    name="Product Extractor",
    instructions="Extract product information from text.",
    output_type=Product
)

async def main():
    result = await Runner.run(
        agent,
        "The iPhone 15 costs $799 and is available in the Electronics category"
    )

    product = result.final_output_as(Product)
    print(f"{product.name}: ${product.price} ({'In Stock' if product.in_stock else 'Out of Stock'})")
```

### Complex Nested Models

```python
from typing import List
from pydantic import BaseModel, Field

class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str

class Contact(BaseModel):
    name: str
    email: str
    phone: str

class Customer(BaseModel):
    customer_id: str = Field(description="Unique customer identifier")
    contact: Contact = Field(description="Contact information")
    address: Address = Field(description="Mailing address")
    orders: List[str] = Field(description="List of order IDs")

agent = Agent(
    name="Customer Data Extractor",
    instructions="Extract customer information from support tickets.",
    output_type=Customer
)
```

### Optional Fields with Defaults

```python
from typing import Optional

class BlogPost(BaseModel):
    title: str
    content: str
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    published: bool = False

agent = Agent(
    name="Blog Post Extractor",
    output_type=BlogPost
)
```

### List of Structured Items

```python
class Task(BaseModel):
    task_id: int
    description: str
    priority: str  # "high", "medium", "low"
    due_date: Optional[str] = None

class TodoList(BaseModel):
    tasks: List[Task] = Field(description="List of tasks")

agent = Agent(
    name="Task Extractor",
    instructions="Extract all tasks from meeting notes.",
    output_type=TodoList
)
```

## Tool Context Management

### Accessing Context in Tools

Share state across tool calls without sending to LLM:

```python
from agents import RunContextWrapper
from dataclasses import dataclass

@dataclass
class AppContext:
    user_id: str
    api_key: str
    session_id: str

@function_tool
def get_user_orders(ctx: RunContextWrapper[AppContext]) -> str:
    """Fetch orders for the current user."""
    user_id = ctx.context.user_id
    api_key = ctx.context.api_key

    # Use context to make authenticated API call
    # In production, call real API with these credentials
    return f"Orders for user {user_id}: [Order1, Order2, Order3]"

@function_tool
def update_preferences(
    ctx: RunContextWrapper[AppContext],
    preference_key: str,
    value: str
) -> str:
    """Update user preferences.

    Args:
        preference_key: The preference to update
        value: The new value
    """
    user_id = ctx.context.user_id
    return f"Updated {preference_key}={value} for user {user_id}"

# Type the agent with context type
agent = Agent[AppContext](
    name="User Assistant",
    tools=[get_user_orders, update_preferences]
)

async def main():
    context = AppContext(
        user_id="user_123",
        api_key="sk-...",
        session_id="sess_456"
    )

    result = await Runner.run(
        agent,
        "Show my orders and set notification preference to email",
        context=context  # Available to all tool calls
    )
    print(result.final_output)
```

### Tool Context with Additional Metadata

```python
from agents.tool_context import ToolContext

@function_tool
def debug_tool(ctx: ToolContext[AppContext], action: str) -> str:
    """Perform action with debug info.

    Args:
        action: The action to perform
    """
    # Access tool-specific metadata
    print(f"Tool: {ctx.tool_name}")
    print(f"Call ID: {ctx.tool_call_id}")
    print(f"Arguments: {ctx.tool_arguments}")

    # Access shared context
    print(f"User: {ctx.context.user_id}")

    return f"Executed {action}"
```

## Advanced Tool Patterns

### Conditional Tool Enabling

Enable/disable tools dynamically based on context:

```python
def is_admin_user(ctx: RunContextWrapper[AppContext], agent: Agent) -> bool:
    """Check if current user is admin."""
    return ctx.context.user_id in ["admin_1", "admin_2"]

@function_tool(
    is_enabled=is_admin_user  # Only available for admin users
)
def delete_data(ctx: RunContextWrapper[AppContext], data_id: str) -> str:
    """Delete data (admin only).

    Args:
        data_id: ID of data to delete
    """
    return f"Deleted {data_id}"

@function_tool(
    is_enabled=True  # Always available
)
def read_data(data_id: str) -> str:
    """Read data (available to all).

    Args:
        data_id: ID of data to read
    """
    return f"Data: {data_id}"
```

### Custom Tool Error Handling

```python
from agents import ToolErrorFunction

def custom_error_handler(error: Exception, tool_name: str) -> str:
    """Custom error message sent to LLM when tool fails."""
    if isinstance(error, ValueError):
        return f"Invalid input for {tool_name}: {str(error)}"
    elif isinstance(error, KeyError):
        return f"Data not found in {tool_name}"
    else:
        return f"Tool {tool_name} encountered an error. Try rephrasing your request."

@function_tool(failure_error_function=custom_error_handler)
def risky_operation(value: int) -> str:
    """Operation that might fail.

    Args:
        value: Input value (must be positive)
    """
    if value < 0:
        raise ValueError("Value must be positive")
    return f"Result: {value * 2}"
```

### Tools Returning Structured Output

Tools can return structured data types:

```python
from agents import ToolOutputText, ToolOutputImage

@function_tool
def generate_chart(data: str) -> ToolOutputImage:
    """Generate a chart from data.

    Args:
        data: Comma-separated values
    """
    # Generate chart image (simulated)
    image_url = "https://example.com/chart.png"
    return ToolOutputImage(image_url=image_url)

@function_tool
def format_report(content: str) -> ToolOutputText:
    """Format text as a report.

    Args:
        content: Report content
    """
    formatted = f"=== REPORT ===\n{content}\n=============="
    return ToolOutputText(text=formatted)
```

## Model Configuration Details

### Comprehensive ModelSettings Example

```python
from agents import ModelSettings

settings = ModelSettings(
    # Sampling parameters
    temperature=0.7,          # 0.0-2.0, higher = more random
    top_p=0.9,               # Nucleus sampling threshold
    frequency_penalty=0.0,    # -2.0 to 2.0, reduces repetition
    presence_penalty=0.0,     # -2.0 to 2.0, encourages new topics

    # Output control
    max_tokens=1500,         # Maximum output length
    verbosity="medium",      # "low", "medium", "high"

    # Tool control
    parallel_tool_calls=True,  # Allow parallel tool execution
    tool_choice="auto",       # "auto", "required", or specific tool

    # Caching and storage
    prompt_cache_retention="24h",  # Extended prompt caching
    store=True,                    # Store for later retrieval

    # Metadata
    metadata={"user_id": "123", "session": "abc"},

    # Additional API parameters
    extra_headers={"X-Custom": "value"}
)

agent = Agent(
    name="Configured Agent",
    model_settings=settings
)
```

### Reasoning Models Configuration

For models with reasoning capabilities (e.g., o1):

```python
from agents import Reasoning

settings = ModelSettings(
    reasoning=Reasoning(
        effort="medium"  # "low", "medium", "high"
    )
)

agent = Agent(
    name="Reasoning Agent",
    instructions="Think step-by-step to solve complex problems.",
    model="o1-preview",
    model_settings=settings
)
```

### Per-Run Model Override

```python
from agents.run import RunConfig

# Override model settings for specific run
result = await Runner.run(
    agent,
    "Complex question requiring more tokens",
    run_config=RunConfig(
        model_settings=ModelSettings(max_tokens=3000)
    )
)
```

## Common Patterns Summary

| Pattern | When to Use | Key Components |
|---------|-------------|----------------|
| Basic agent | Simple Q&A | `Agent(name, instructions)` |
| With tools | Need actions/data | `@function_tool` + `tools=[...]` |
| Structured output | Need typed data | `output_type=PydanticModel` |
| Async tools | API calls, I/O | `async def` tool functions |
| Context sharing | State across tools | `RunContextWrapper[T]` |
| Conditional tools | Role-based access | `is_enabled=callable` |
| Custom errors | Better error messages | `failure_error_function` |
| Model tuning | Control behavior | `ModelSettings(...)` |
