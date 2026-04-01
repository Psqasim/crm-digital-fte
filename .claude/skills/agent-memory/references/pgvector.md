# pgvector Reference

## Contents
1. [Installation & Setup](#installation--setup)
2. [SQL Reference](#sql-reference)
3. [Index Types](#index-types)
4. [Distance Operators](#distance-operators)
5. [Python Integration (raw psycopg)](#python-integration-raw-psycopg)
6. [LangChain PGVector](#langchain-pgvector)
7. [Performance Tuning](#performance-tuning)

---

## Installation & Setup

**PostgreSQL extension:**
```bash
# Docker (recommended for dev)
docker run --name pgvector-container \
  -e POSTGRES_USER=langchain \
  -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain \
  -p 5432:5432 \
  -d pgvector/pgvector:pg16

# Or build from source
cd /tmp && git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
cd pgvector && make && make install
```

**Enable in database:**
```sql
CREATE EXTENSION vector;
```

**Python packages:**
```bash
pip install psycopg[binary]           # psycopg3 (required by langchain-postgres)
pip install langchain-postgres        # LangChain PGVector wrapper
pip install pgvector                  # raw pgvector Python bindings
```

---

## SQL Reference

**Vector types:** vector(n) | halfvec(n) | bit(n) | sparsevec(n)

**Create table:**
```sql
CREATE TABLE memories (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT,
    metadata    JSONB,
    embedding   vector(1536),   -- dimension must match your model
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    user_id     TEXT
);
```

**CRUD:**
```sql
INSERT INTO memories (content, embedding, user_id)
VALUES ('User likes Python', '[0.1, 0.2, ...]', 'user-123');

-- Upsert
INSERT INTO memories (id, content, embedding) VALUES (1, 'text', '[0.1, ...]')
ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding;

UPDATE memories SET embedding = '[1,2,3]' WHERE id = 1;
DELETE FROM memories WHERE id = 1;
SELECT AVG(embedding) FROM memories WHERE user_id = 'user-123';
```

---

## Index Types

### HNSW (recommended — no training data needed)
```sql
-- Cosine distance (best for text embeddings)
CREATE INDEX ON memories USING hnsw (embedding vector_cosine_ops);

-- L2 distance
CREATE INDEX ON memories USING hnsw (embedding vector_l2_ops);

-- Inner product
CREATE INDEX ON memories USING hnsw (embedding vector_ip_ops);

-- With tuning parameters
CREATE INDEX ON memories USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- m: max connections per node (default 16, range 2-100)
-- ef_construction: candidate list size during build (default 64, range 4-1000)

SET hnsw.ef_search = 100;  -- query-time recall tuning (default 40)
SET hnsw.iterative_scan = strict_order;   -- for filtered queries (v0.8.0+)
```

### IVFFlat (requires training data first)
```sql
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);   -- lists: sqrt(row_count) is a good start
SET ivfflat.probes = 10;  -- query-time recall tuning (default 1)
```

---

## Distance Operators

| Operator | Distance Type | Use Case |
|----------|--------------|----------|
| `<->` | L2 (Euclidean) | General spatial proximity |
| `<=>` | Cosine distance | Text embeddings (direction only) |
| `<#>` | Negative inner product | Multiply by -1 for similarity score |
| `<+>` | L1 (Manhattan) | Sparse vectors |
| `<~>` | Hamming | Binary vectors |
| `<%>` | Jaccard | Binary vectors |

```sql
-- k-nearest neighbors by cosine distance
SELECT id, content, embedding <=> '[0.1, 0.2, ...]' AS distance
FROM memories ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 5;

-- Cosine SIMILARITY (not distance)
SELECT 1 - (embedding <=> '[0.1, 0.2, ...]') AS similarity FROM memories;

-- Filter then rank
SELECT * FROM memories
WHERE user_id = 'user-123'
ORDER BY embedding <=> '[0.1, ...]' LIMIT 5;

-- With partial index for user-specific ANN
CREATE INDEX ON memories USING hnsw (embedding vector_cosine_ops)
  WHERE (user_id = 'user-123');
```

---

## Python Integration (raw psycopg)

```python
import psycopg
from pgvector.psycopg import register_vector

conn = psycopg.connect("postgresql://user:pass@localhost/db")
register_vector(conn)

# Insert
with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO memories (content, embedding, user_id) VALUES (%s, %s, %s)",
        ("User likes Python", [0.1, 0.2], "user-123")
    )
    conn.commit()

# Query - note: pass embedding twice for both ORDER BY and distance return
query_vec = [0.1, 0.2]
with conn.cursor() as cur:
    cur.execute(
        "SELECT id, content, 1 - (embedding <=> %s) AS similarity "
        "FROM memories WHERE user_id = %s "
        "ORDER BY embedding <=> %s LIMIT %s",
        (query_vec, "user-123", query_vec, 5)
    )
    rows = cur.fetchall()
```

---

## LangChain PGVector

```python
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Connection string MUST use psycopg3 driver (postgresql+psycopg not psycopg2)
connection = "postgresql+psycopg://user:pass@localhost:5432/dbname"

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="agent_memories",
    connection=connection,
    use_jsonb=True,       # Use JSONB for metadata (recommended)
)

# Add documents
docs = [
    Document(page_content="User prefers Python", metadata={"user_id": "u1", "type": "preference"}),
]
vector_store.add_documents(docs, ids=["mem-001"])

# Delete
vector_store.delete(ids=["mem-001"])

# Similarity search
results = vector_store.similarity_search("programming preferences", k=5)

# With distance scores
results = vector_store.similarity_search_with_score("topic", k=3)
for doc, score in results:
    print(f"Score: {score:.4f} | {doc.page_content}")

# With metadata filter
results = vector_store.similarity_search(
    "preferences", k=5,
    filter={"user_id": {"$eq": "u1"}},
)

# Combined filters
results = vector_store.similarity_search(
    "facts", k=5,
    filter={"$and": [
        {"user_id": {"$eq": "u1"}},
        {"type": {"$in": ["preference", "fact"]}},
    ]},
)
# All operators: $eq $ne $lt $lte $gt $gte $in $nin $between $like $ilike $and $or

# As retriever
retriever = vector_store.as_retriever(
    search_type="mmr",   # "similarity" | "mmr" | "similarity_score_threshold"
    search_kwargs={"k": 5, "fetch_k": 20},
)
```

---

## Performance Tuning

```sql
SET maintenance_work_mem = '8GB';           -- faster index builds
SET max_parallel_maintenance_workers = 7;   -- parallel index creation

-- Monitor index build
SELECT phase, round(100.0 * blocks_done / nullif(blocks_total, 0), 1) AS "%"
FROM pg_stat_progress_create_index;
```

**Common embedding dimensions:**
- OpenAI `text-embedding-3-small`: 1536 dims
- OpenAI `text-embedding-3-large`: 3072 dims
- `all-MiniLM-L6-v2` (Sentence Transformers): 384 dims

**Note:** langchain-postgres manages its own tables. No built-in migration — drop and recreate if schema changes.
