# Memory Design Patterns

## Contents
1. [Sliding Window Memory](#sliding-window-memory)
2. [Summarization Memory](#summarization-memory)
3. [Entity / Fact Memory](#entity--fact-memory)
4. [Hybrid Memory (Short + Long Term)](#hybrid-memory-short--long-term)
5. [Memory Writing Strategies](#memory-writing-strategies)
6. [Memory Schema Design](#memory-schema-design)

---

## Sliding Window Memory

Keep only the last N messages to control context size.

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage, SystemMessage

class SlidingWindowHistory(InMemoryChatMessageHistory):
    max_messages: int = 20

    def add_messages(self, messages: list[BaseMessage]) -> None:
        super().add_messages(messages)
        all_msgs = self.messages
        if len(all_msgs) > self.max_messages:
            # Preserve system message if present at index 0
            if all_msgs and isinstance(all_msgs[0], SystemMessage):
                trimmed = [all_msgs[0]] + all_msgs[-(self.max_messages - 1):]
            else:
                trimmed = all_msgs[-self.max_messages:]
            self.clear()
            super().add_messages(trimmed)
```

---

## Summarization Memory

Compress old turns into a summary to reduce token usage.

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

llm = ChatOpenAI(model="gpt-4o-mini")

SUMMARIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Summarize this conversation history concisely, preserving key facts:"),
    ("human", "{history}"),
])

async def summarize_and_trim(
    history: InMemoryChatMessageHistory,
    keep_recent: int = 6,
    max_total: int = 20,
) -> None:
    messages = history.messages
    if len(messages) <= max_total:
        return

    to_summarize = messages[:-keep_recent]
    recent = messages[-keep_recent:]

    summary = await llm.ainvoke(
        SUMMARIZE_PROMPT.format_messages(
            history="\n".join(f"{m.type}: {m.content}" for m in to_summarize)
        )
    )

    history.clear()
    history.add_messages([
        SystemMessage(content=f"Previous conversation summary: {summary.content}"),
        *recent,
    ])
```

---

## Entity / Fact Memory

Extract structured facts and store them for later retrieval.

```python
from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Extract factual statements about the user from this message.
One fact per line. Only clear, stable facts.
Example: 'User prefers Python over Java', 'User works in finance'
If no facts, return NONE."""),
    ("human", "{message}"),
])

llm = ChatOpenAI(model="gpt-4o-mini")
vector_store = PGVector(
    embeddings=OpenAIEmbeddings(),
    collection_name="user_facts",
    connection="postgresql+psycopg://...",
)

async def extract_and_store_facts(user_id: str, message: str) -> list[str]:
    response = await llm.ainvoke(EXTRACT_PROMPT.format_messages(message=message))
    if response.content.strip() == "NONE":
        return []

    facts = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
    docs = [
        Document(
            page_content=fact,
            metadata={"user_id": user_id, "type": "fact"},
        )
        for fact in facts
    ]
    vector_store.add_documents(docs)
    return facts

async def retrieve_relevant_facts(user_id: str, query: str, k: int = 5) -> list[str]:
    results = vector_store.similarity_search(
        query, k=k, filter={"user_id": {"$eq": user_id}}
    )
    return [doc.page_content for doc in results]
```

---

## Hybrid Memory (Short + Long Term)

Combine in-session conversation history with retrieved long-term memories.

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector

llm = ChatOpenAI(model="gpt-4o")
long_term = PGVector(
    embeddings=OpenAIEmbeddings(),
    collection_name="agent_memories",
    connection="postgresql+psycopg://...",
)
short_term: dict[str, InMemoryChatMessageHistory] = {}

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant.\n\nRelevant memories:\n{memories}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])

def inject_memories(inputs: dict) -> dict:
    user_id = inputs.get("user_id", "default")
    docs = long_term.similarity_search(
        inputs["input"], k=5, filter={"user_id": {"$eq": user_id}}
    )
    inputs["memories"] = "\n".join(f"- {d.page_content}" for d in docs) or "None."
    return inputs

chain = RunnableLambda(inject_memories) | PROMPT | llm

agent = RunnableWithMessageHistory(
    chain,
    lambda sid: short_term.setdefault(sid, InMemoryChatMessageHistory()),
    input_messages_key="input",
    history_messages_key="chat_history",
)

response = agent.invoke(
    {"input": "What programming languages do I use?", "user_id": "user-123"},
    config={"configurable": {"session_id": "session-abc"}},
)
```

---

## Memory Writing Strategies

### Hot Path (synchronous — simple, adds latency)
```python
async def agent_hot_path(user_id: str, message: str) -> str:
    memories = await retrieve_relevant_facts(user_id, message)
    response = await llm.ainvoke(...)
    # Block response until memory is written
    await extract_and_store_facts(user_id, f"User: {message}\nAssistant: {response.content}")
    return response.content
```

### Background Task (async — lower latency, eventual consistency)
```python
import asyncio

async def agent_background(user_id: str, message: str) -> str:
    memories = await retrieve_relevant_facts(user_id, message)
    response = await llm.ainvoke(...)
    # Fire-and-forget — does not block response
    asyncio.create_task(
        extract_and_store_facts(user_id, f"User: {message}\nAssistant: {response.content}")
    )
    return response.content
```

---

## Memory Schema Design

**Recommended metadata fields:**
```python
from datetime import datetime, UTC

memory_metadata = {
    "user_id": "user-123",           # partition key for user isolation
    "session_id": "session-abc",     # conversation context
    "type": "preference",            # preference | fact | event | summary
    "importance": 0.8,               # float 0-1 for relevance scoring
    "created_at": datetime.now(UTC).isoformat(),
    "source": "extracted",           # extracted | user_stated | inferred
}
```

**LangGraph namespace strategy:**
```python
# Hierarchical namespaces for isolation
("memories", user_id)                # all user memories
("memories", user_id, "facts")       # structured facts only
("memories", user_id, "preferences") # preferences only
("memories", "global")               # shared across users
```

**TTL / Memory pruning (pgvector):**
```sql
-- Remove old low-importance memories
DELETE FROM langchain_pg_embedding
WHERE (cmetadata->>'importance')::float < 0.3
  AND created_at < NOW() - INTERVAL '30 days';
```
