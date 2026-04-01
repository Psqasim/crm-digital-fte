# ChromaDB Reference

## Contents
1. [Installation](#installation)
2. [Client Types](#client-types)
3. [Collection Operations](#collection-operations)
4. [Query & Get API](#query--get-api)
5. [Embedding Functions](#embedding-functions)
6. [HNSW Configuration](#hnsw-configuration)
7. [Distance Metrics](#distance-metrics)
8. [LangChain Chroma Integration](#langchain-chroma-integration)

---

## Installation

```bash
pip install chromadb                  # core library
pip install langchain-chroma          # LangChain wrapper
```

---

## Client Types

```python
import chromadb

# In-memory (ephemeral, testing only)
client = chromadb.Client()            # alias: chromadb.EphemeralClient()

# Persistent (local disk)
client = chromadb.PersistentClient(path="./chroma_db")

# Remote server
client = chromadb.HttpClient(
    host="localhost",
    port=8000,          # default
    ssl=False,
    headers={},
)
# Run server: chroma run --path ./chroma_db --port 8000

# Cloud
import os
client = chromadb.CloudClient(
    api_key=os.environ["CHROMA_API_KEY"],
    tenant="my-tenant",
    database="my-database",
)
```

---

## Collection Operations

```python
# Create
collection = client.create_collection(
    name="agent_memories",
    metadata={"hnsw:space": "cosine"},
    embedding_function=my_ef,           # optional
)

# Get or create (idempotent)
collection = client.get_or_create_collection(
    name="agent_memories",
    metadata={"hnsw:space": "cosine"},
)

# Get / Delete / List
collection = client.get_collection(name="agent_memories")
client.delete_collection(name="agent_memories")
collections = client.list_collections()
client.reset()  # delete all - use with caution

# Add documents
collection.add(
    documents=["User prefers Python", "User works in finance"],
    metadatas=[
        {"user_id": "u1", "type": "preference"},
        {"user_id": "u1", "type": "fact"},
    ],
    ids=["mem-001", "mem-002"],
    # embeddings=[[...], [...]]  # omit to auto-embed via embedding_function
)

# Upsert (insert or update)
collection.upsert(
    documents=["Updated text"],
    metadatas=[{"user_id": "u1"}],
    ids=["mem-001"],
)

# Update
collection.update(
    ids=["mem-001"],
    documents=["New text"],
    metadatas=[{"type": "updated"}],
)

# Delete
collection.delete(ids=["mem-001"])
collection.delete(where={"user_id": "u1"})  # by filter

# Count
count = collection.count()
```

---

## Query & Get API

```python
# Semantic search
results = collection.query(
    query_texts=["What does the user prefer?"],   # OR query_embeddings=[[...]]
    n_results=5,                                   # default: 10
    where={"user_id": "u1"},                       # metadata filter
    where_document={"$contains": "Python"},        # document content filter
    ids=["mem-001", "mem-002"],                    # constrain to specific IDs
    include=["documents", "metadatas", "distances"],  # default
)
# results keys: ids, documents, metadatas, distances

# Get by ID or filter
items = collection.get(
    ids=["mem-001"],
    include=["documents", "metadatas"],
)

# Get with pagination
items = collection.get(
    where={"user_id": "u1"},
    limit=100,
    offset=0,
)
```

### Metadata filter operators

```python
# Basic equality (shorthand)
where={"user_id": "u1"}

# Comparison
where={"score": {"$gt": 0.5}}
where={"score": {"$gte": 0.5}}
where={"score": {"$lt": 1.0}}
where={"score": {"$lte": 1.0}}
where={"type": {"$ne": "deleted"}}

# List membership
where={"type": {"$in": ["preference", "fact"]}}
where={"type": {"$nin": ["deleted"]}}

# Logical operators
where={"$and": [{"user_id": "u1"}, {"type": "preference"}]}
where={"$or": [{"type": "preference"}, {"type": "fact"}]}
```

---

## Embedding Functions

All in `chromadb.utils.embedding_functions`:

```python
from chromadb.utils import embedding_functions

# Default: all-MiniLM-L6-v2 (local, no API key needed)
default_ef = embedding_functions.DefaultEmbeddingFunction()

# OpenAI
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="sk-...",                    # or OPENAI_API_KEY env var
    model_name="text-embedding-3-small", # default: text-embedding-ada-002
)

# Sentence Transformers (local)
sentence_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",
)

# Cohere
cohere_ef = embedding_functions.CohereEmbeddingFunction(
    api_key="...",
    model_name="embed-english-v3.0",
)

# Pass to collection
collection = client.get_or_create_collection(
    name="agent_memories",
    embedding_function=openai_ef,
)
```

Also available: Google Generative AI, HuggingFace, Jina AI, Mistral, Together AI.

---

## HNSW Configuration

Set via `metadata` at collection creation (most params cannot change after):

```python
collection = client.create_collection(
    name="agent_memories",
    metadata={
        "hnsw:space": "cosine",           # "cosine" | "l2" | "ip" (default: "l2")
        "hnsw:construction_ef": 100,      # candidate list during build (default: 100)
        "hnsw:search_ef": 100,            # candidate list during query (default: 100)
        "hnsw:M": 16,                     # max connections per node (default: 16)
        "hnsw:num_threads": 4,            # threads for indexing
        "hnsw:batch_size": 100,           # vectors per batch
        "hnsw:sync_threshold": 1000,      # storage sync trigger
        "hnsw:resize_factor": 1.2,        # index growth multiplier
    }
)
```

Modifiable after creation: `hnsw:search_ef`, `hnsw:num_threads`, `hnsw:batch_size`, `hnsw:sync_threshold`, `hnsw:resize_factor`

---

## Distance Metrics

| Key | Metric | Best For |
|-----|--------|----------|
| `"l2"` | Squared L2 (default) | Absolute spatial proximity |
| `"cosine"` | Cosine similarity | Text embeddings (angle only) |
| `"ip"` | Inner product | Recommendations, magnitude matters |

---

## LangChain Chroma Integration

```python
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import chromadb
import uuid

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Option A: LangChain manages the client
vector_store = Chroma(
    collection_name="agent_memories",
    embedding_function=embeddings,
    persist_directory="./chroma_db",   # omit for in-memory
)

# Option B: Pass pre-configured client
persistent_client = chromadb.PersistentClient(path="./chroma_db")
vector_store = Chroma(
    client=persistent_client,
    collection_name="agent_memories",
    embedding_function=embeddings,
)

# Option C: Remote server
http_client = chromadb.HttpClient(host="localhost", port=8000)
vector_store = Chroma(
    client=http_client,
    collection_name="agent_memories",
    embedding_function=embeddings,
)

# Create from existing documents
uuids = [str(uuid.uuid4()) for _ in docs]
vector_store = Chroma.from_documents(
    documents=docs,
    embedding=embeddings,
    collection_name="agent_memories",
    persist_directory="./chroma_db",
)

# Document management
vector_store.add_documents(documents=docs, ids=uuids)
vector_store.update_document(document_id=uuids[0], document=docs[0])
vector_store.update_documents(ids=uuids, documents=docs)
vector_store.delete(ids=[uuids[0]])

# Search methods
results = vector_store.similarity_search("user preferences", k=5)
results = vector_store.similarity_search_with_score("topic", k=3)
results = vector_store.similarity_search_by_vector(embedding=[...], k=5)
results = vector_store.max_marginal_relevance_search("query", k=5, fetch_k=20)

# With metadata filter (ChromaDB where syntax)
results = vector_store.similarity_search(
    "preferences", k=5,
    filter={"user_id": "u1"},
)

# As retriever
retriever = vector_store.as_retriever(
    search_type="mmr",         # "similarity" | "mmr" | "similarity_score_threshold"
    search_kwargs={"k": 5},
)
```

### Cloud deployment constructor params

```python
vector_store = Chroma(
    collection_name="agent_memories",
    embedding_function=embeddings,
    chroma_cloud_api_key=os.environ["CHROMA_API_KEY"],
    tenant="my-tenant",
    database="my-database",
)
```
