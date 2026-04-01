# Session Management Patterns

Comprehensive patterns for managing conversation history and memory with sessions.

## Table of Contents
- Sessions Overview
- Basic Session Usage
- Multi-Turn Conversations
- Multi-Agent Session Sharing
- Session Storage Backends
- Advanced Session Patterns

## Sessions Overview

Sessions provide automatic conversation history management, enabling multi-turn conversations where agents remember previous context.

### Key Benefits

- **Automatic history management**: No manual message tracking
- **Multi-turn conversations**: Agents remember previous exchanges
- **Multi-agent sharing**: Multiple agents access same conversation
- **Persistent storage**: Conversations survive across runs
- **Context continuity**: References to previous topics work naturally

### When to Use Sessions

- **Chatbots and assistants**: Multi-turn conversational UIs
- **Customer support**: Maintain context across interactions
- **Multi-agent workflows**: Share history across specialists
- **Stateful applications**: Remember user preferences and context
- **Long-running conversations**: Track conversation over time

## Basic Session Usage

### SQLite Session (Default)

```python
from agents import Agent, Runner, SQLiteSession
import asyncio

agent = Agent(
    name="Assistant",
    instructions="Be helpful and remember previous context.",
)

async def main():
    # Create session with conversation ID and database file
    session = SQLiteSession(
        conversation_id="user_123",
        db_path="conversations.db"  # Optional: defaults to in-memory
    )

    # First message
    result1 = await Runner.run(
        agent,
        "My name is Alice",
        session=session
    )
    print(result1.final_output)  # "Nice to meet you, Alice!"

    # Second message - agent remembers
    result2 = await Runner.run(
        agent,
        "What's my name?",
        session=session
    )
    print(result2.final_output)  # "Your name is Alice."

asyncio.run(main())
```

### In-Memory Session

```python
from agents import SQLiteSession

# Don't specify db_path for in-memory storage
session = SQLiteSession("conversation_123")  # Stored in memory only
```

### Persistent File-Based Session

```python
# Store conversations in a file
session = SQLiteSession(
    conversation_id="support_chat_456",
    db_path="/path/to/conversations.db"
)

# Conversations persist across application restarts
```

## Multi-Turn Conversations

### Natural Reference Resolution

Sessions enable natural conversation flow:

```python
async def conversation_example():
    agent = Agent(
        name="Travel Assistant",
        instructions="Help plan travel. Be concise.",
    )

    session = SQLiteSession("travel_planning", "travel.db")

    # Turn 1: Establish topic
    result = await Runner.run(
        agent,
        "I want to visit Japan next month",
        session=session
    )
    print(f"Agent: {result.final_output}")

    # Turn 2: Reference "it" (Japan)
    result = await Runner.run(
        agent,
        "What's the weather like there in March?",  # "there" = Japan
        session=session
    )
    print(f"Agent: {result.final_output}")

    # Turn 3: Continue context
    result = await Runner.run(
        agent,
        "What about hotels?",  # Context: hotels in Japan for March
        session=session
    )
    print(f"Agent: {result.final_output}")
```

### Session-Based User Preferences

Remember user preferences across conversation:

```python
async def preference_tracking():
    agent = Agent(
        name="Shopping Assistant",
        instructions="Help with shopping. Remember user preferences.",
    )

    session = SQLiteSession("shopping_session", "shop.db")

    # Establish preferences
    await Runner.run(
        agent,
        "I prefer sustainable and eco-friendly products",
        session=session
    )

    # Later in conversation - agent remembers
    result = await Runner.run(
        agent,
        "Show me some laptop bags",  # Will prioritize eco-friendly options
        session=session
    )
    print(result.final_output)
```

### Conversation Summarization

Manage long conversations with periodic summarization:

```python
async def long_conversation():
    agent = Agent(name="Assistant")
    summarizer = Agent(
        name="Summarizer",
        instructions="Summarize conversation history concisely."
    )

    session = SQLiteSession("long_chat", "chats.db")
    turn_count = 0
    max_turns_before_summary = 10

    while True:
        user_input = input("You: ")
        if user_input.lower() == "quit":
            break

        # Normal conversation
        result = await Runner.run(agent, user_input, session=session)
        print(f"Agent: {result.final_output}")

        turn_count += 1

        # Periodically summarize to keep context manageable
        if turn_count >= max_turns_before_summary:
            # In production, you'd compress the session here
            print("📋 Creating conversation summary...")
            turn_count = 0
```

## Multi-Agent Session Sharing

### Shared Session Across Agents

Multiple agents access the same conversation history:

```python
from agents import Agent, Runner, SQLiteSession
import asyncio

# Different specialized agents
support_agent = Agent(
    name="Support Agent",
    instructions="Help with general support inquiries."
)

technical_agent = Agent(
    name="Technical Agent",
    instructions="Handle technical issues and troubleshooting."
)

billing_agent = Agent(
    name="Billing Agent",
    instructions="Manage billing and payment questions."
)

async def multi_agent_support():
    # Shared session
    session = SQLiteSession("support_ticket_789", "support.db")

    # Turn 1: Support agent starts
    result = await Runner.run(
        support_agent,
        "I'm having issues with my account",
        session=session
    )
    print(f"Support: {result.final_output}")

    # Turn 2: Hand off to billing (sees previous context)
    result = await Runner.run(
        billing_agent,
        "Check my recent charges",  # Billing agent sees account context
        session=session
    )
    print(f"Billing: {result.final_output}")

    # Turn 3: Technical agent joins (sees full history)
    result = await Runner.run(
        technical_agent,
        "The mobile app also crashes on startup",
        session=session
    )
    print(f"Technical: {result.final_output}")

asyncio.run(multi_agent_support())
```

### Session with Handoff Pattern

Combine sessions with agent handoffs:

```python
async def handoff_with_session():
    # Specialists with shared session
    l1_support = Agent(
        name="L1 Support",
        handoff_description="First-level support",
        instructions="Handle common issues, escalate complex ones."
    )

    l2_support = Agent(
        name="L2 Support",
        handoff_description="Advanced technical support",
        instructions="Handle escalated technical issues. Previous conversation context available."
    )

    triage = Agent(
        name="Triage",
        instructions="Route to appropriate support level.",
        handoffs=[l1_support, l2_support]
    )

    # Shared session across handoffs
    session = SQLiteSession("escalation_case", "cases.db")

    result = await Runner.run(
        triage,
        "My enterprise deployment is failing with error code 5000",
        session=session  # History maintained through handoffs
    )

    # All agents in the handoff chain have access to full conversation
    print(result.final_output)
```

### Context Continuity Across Sessions

Resume conversations with same session ID:

```python
async def resume_conversation():
    agent = Agent(name="Assistant")

    # Day 1: Start conversation
    session = SQLiteSession("ongoing_project", "projects.db")
    await Runner.run(
        agent,
        "We're building a mobile app for food delivery",
        session=session
    )

    # Later (Day 2): Resume with same session
    session = SQLiteSession("ongoing_project", "projects.db")  # Same ID
    result = await Runner.run(
        agent,
        "What database should we use?",  # Agent remembers the app context
        session=session
    )
    print(result.final_output)
```

## Session Storage Backends

### SQLite Session (Built-in)

```python
from agents import SQLiteSession

# File-based (persistent)
session = SQLiteSession(
    conversation_id="chat_123",
    db_path="/var/app/conversations.db"
)

# In-memory (temporary)
session = SQLiteSession("temp_chat")  # No db_path = in-memory

# With custom table name
session = SQLiteSession(
    conversation_id="custom_123",
    db_path="data.db",
    table_name="conversations"  # Optional
)
```

### Redis Session (Optional)

Requires `pip install 'openai-agents[redis]'`:

```python
from agents import RedisSession

# Connect to Redis
session = RedisSession(
    conversation_id="chat_456",
    redis_url="redis://localhost:6379/0"
)

# With authentication
session = RedisSession(
    conversation_id="secure_chat",
    redis_url="redis://:password@redis-server:6379/0"
)

# With TTL (auto-expire conversations)
session = RedisSession(
    conversation_id="temp_session",
    redis_url="redis://localhost:6379",
    ttl=3600  # Expire after 1 hour
)
```

### Custom Session Backend

Implement custom storage:

```python
from agents import Session
from typing import List

class CustomSession(Session):
    """Custom session storage implementation."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.messages = []

    async def get_messages(self) -> List[dict]:
        """Retrieve conversation history."""
        # Load from your storage (database, API, etc.)
        return self.messages

    async def add_message(self, message: dict):
        """Store a new message."""
        # Save to your storage
        self.messages.append(message)

    async def clear(self):
        """Clear conversation history."""
        self.messages = []

# Use custom session
custom_session = CustomSession("my_conversation")
result = await Runner.run(agent, "Hello", session=custom_session)
```

## Advanced Session Patterns

### Session Namespacing

Organize sessions by user/project:

```python
def get_session(user_id: str, conversation_type: str):
    """Create namespaced session."""
    conversation_id = f"{user_id}:{conversation_type}"
    return SQLiteSession(conversation_id, "app.db")

# Usage
alice_support = get_session("alice_123", "support")
alice_orders = get_session("alice_123", "orders")
bob_support = get_session("bob_456", "support")

# Each has independent history
await Runner.run(agent, "Help me", session=alice_support)
await Runner.run(agent, "Check my order", session=alice_orders)
```

### Session Metadata

Track session information:

```python
from datetime import datetime
import json

class MetadataSession(SQLiteSession):
    """Session with metadata tracking."""

    def __init__(self, conversation_id: str, db_path: str, metadata: dict):
        super().__init__(conversation_id, db_path)
        self.metadata = metadata
        self.created_at = datetime.now()

    def get_info(self):
        """Get session information."""
        return {
            "conversation_id": self.conversation_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.messages)
        }

# Usage
session = MetadataSession(
    "support_123",
    "app.db",
    metadata={
        "user_id": "user_789",
        "user_tier": "premium",
        "department": "sales"
    }
)

await Runner.run(agent, "Question", session=session)
print(session.get_info())
```

### Session Branching

Create conversation branches:

```python
async def branch_conversation():
    """Explore different conversation paths."""

    agent = Agent(name="Assistant")

    # Main conversation
    main_session = SQLiteSession("main_conv", "conversations.db")
    await Runner.run(agent, "Tell me about Python", session=main_session)

    # Branch 1: Explore web frameworks
    branch1 = SQLiteSession("branch_1_web", "conversations.db")
    # Copy main conversation to branch
    # Then continue with different question
    result1 = await Runner.run(
        agent,
        "What are the best web frameworks?",
        session=branch1
    )

    # Branch 2: Explore data science
    branch2 = SQLiteSession("branch_2_data", "conversations.db")
    result2 = await Runner.run(
        agent,
        "What about data science libraries?",
        session=branch2
    )

    return result1.final_output, result2.final_output
```

### Session Cleanup

Manage session lifecycle:

```python
async def cleanup_old_sessions():
    """Clean up old or inactive sessions."""
    import sqlite3
    from datetime import datetime, timedelta

    db_path = "conversations.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete sessions older than 30 days
    cutoff_date = datetime.now() - timedelta(days=30)

    cursor.execute("""
        DELETE FROM sessions
        WHERE last_activity < ?
    """, (cutoff_date.isoformat(),))

    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"Deleted {deleted_count} old sessions")
```

### Session Export/Import

Backup and restore conversations:

```python
async def export_session(session: SQLiteSession, filepath: str):
    """Export session to JSON."""
    messages = await session.get_messages()

    data = {
        "conversation_id": session.conversation_id,
        "exported_at": datetime.now().isoformat(),
        "messages": messages
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

async def import_session(filepath: str, new_conversation_id: str):
    """Import session from JSON."""
    with open(filepath, 'r') as f:
        data = json.load(f)

    session = SQLiteSession(new_conversation_id, "restored.db")

    for message in data["messages"]:
        await session.add_message(message)

    return session

# Usage
# Export
await export_session(my_session, "backup.json")

# Import
restored_session = await import_session("backup.json", "restored_chat")
```

## Best Practices

1. **Use unique conversation IDs** - Namespace by user/context
2. **Choose appropriate backend** - SQLite for simple, Redis for distributed
3. **Implement cleanup** - Remove old sessions periodically
4. **Handle session errors** - Gracefully handle missing/corrupt sessions
5. **Share sessions wisely** - Only when agents need same context
6. **Monitor session size** - Summarize or archive long conversations
7. **Secure session data** - Encrypt sensitive conversation history
8. **Test resumption** - Verify sessions work across restarts
9. **Version session schema** - Plan for schema migrations
10. **Log session activity** - Track usage and performance

## Common Patterns Summary

| Use Case | Pattern | Key Components |
|----------|---------|----------------|
| Simple chat | Single session | `SQLiteSession(id, db)` |
| Multi-turn support | Persistent session | File-based SQLite |
| Multi-agent collab | Shared session | Same session across agents |
| Distributed system | Redis session | `RedisSession(id, url)` |
| Temporary chat | In-memory session | SQLite without db_path |
| Long conversations | Periodic summarization | Compress old history |
| User organization | Namespaced IDs | `{user_id}:{type}` format |
| Conversation backup | Export/import | JSON serialization |
