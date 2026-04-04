#!/usr/bin/env python3
"""
production/database/seed_knowledge_base.py
Phase 4A: Seed the knowledge_base table from context/product-docs.md.

Usage:
    DATABASE_URL=postgresql://... OPENAI_API_KEY=sk-... python seed_knowledge_base.py

Steps:
1. Reads context/product-docs.md from the project root
2. Splits into chunks by heading (## / ###) or ~500-word windows
3. Calls OpenAI text-embedding-3-small to generate 1536-dim embeddings
4. Upserts all chunks into knowledge_base via queries.upsert_knowledge_base
5. Prints progress: "Seeded X chunks into knowledge_base"
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg
from openai import AsyncOpenAI

# Resolve project root relative to this file's location
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PRODUCT_DOCS_PATH = _PROJECT_ROOT / "context" / "product-docs.md"

# Chunk settings
_MAX_WORDS_PER_CHUNK = 500
_EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIMENSIONS = 1536


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _split_into_chunks(text: str) -> list[dict[str, str]]:
    """Split markdown text into chunks by ## heading boundaries.

    Each chunk is {"title": str, "content": str, "category": str}.
    If a section exceeds _MAX_WORDS_PER_CHUNK words it is further split into
    ~500-word windows so individual embeddings stay within token budgets.
    """
    # Split on level-2 headings (## Heading)
    sections = re.split(r"\n(?=## )", text.strip())
    chunks: list[dict[str, str]] = []

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().splitlines()
        heading = lines[0].lstrip("#").strip() if lines else "General"
        body = "\n".join(lines[1:]).strip()

        # Infer a rough category from the heading
        category = _infer_category(heading)

        # Split oversized sections into word-window sub-chunks
        words = body.split()
        if len(words) <= _MAX_WORDS_PER_CHUNK:
            chunks.append({"title": heading, "content": body, "category": category})
        else:
            # Slide through in ~500-word windows with 50-word overlap
            step = _MAX_WORDS_PER_CHUNK - 50
            for i, start in enumerate(range(0, len(words), step)):
                window = words[start : start + _MAX_WORDS_PER_CHUNK]
                sub_title = f"{heading} (part {i + 1})"
                chunks.append(
                    {
                        "title": sub_title,
                        "content": " ".join(window),
                        "category": category,
                    }
                )

    return chunks


def _infer_category(heading: str) -> str:
    """Map a heading string to a known category."""
    heading_lower = heading.lower()
    mapping = {
        "billing": "billing",
        "plan": "billing",
        "pricing": "billing",
        "payment": "billing",
        "integrat": "integration",
        "slack": "integration",
        "jira": "integration",
        "salesforce": "integration",
        "zapier": "integration",
        "api": "integration",
        "onboard": "onboarding",
        "setup": "onboarding",
        "workspace": "onboarding",
        "getting started": "onboarding",
        "bug": "bug",
        "error": "bug",
        "troubleshoot": "bug",
        "automat": "feature_question",
        "workflow": "feature_question",
        "task": "feature_question",
        "permission": "feature_question",
        "role": "feature_question",
        "export": "feature_question",
        "import": "feature_question",
        "report": "feature_question",
        "security": "escalation",
        "data": "escalation",
        "gdpr": "escalation",
        "compliance": "escalation",
    }
    for keyword, cat in mapping.items():
        if keyword in heading_lower:
            return cat
    return "general"


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

async def _embed_chunks(
    client: AsyncOpenAI,
    chunks: list[dict[str, str]],
) -> list[list[float]]:
    """Call OpenAI text-embedding-3-small in batches of 100."""
    embeddings: list[list[float]] = []
    batch_size = 100

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        texts = [f"{c['title']}\n\n{c['content']}" for c in batch]

        response = await client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=texts,
        )
        for item in response.data:
            embeddings.append(item.embedding)

        print(
            f"  Embedded batch {batch_start // batch_size + 1} "
            f"({len(batch)} chunks)...",
            flush=True,
        )

    return embeddings


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

async def _upsert_all(
    pool: asyncpg.Pool,
    chunks: list[dict[str, str]],
    embeddings: list[list[float]],
) -> int:
    """Upsert all chunks into knowledge_base; return count of upserted rows."""
    # Import here to avoid circular import if this script is run standalone
    from production.database.queries import upsert_knowledge_base  # noqa: PLC0415

    seeded = 0
    for chunk, embedding in zip(chunks, embeddings):
        kb_id = await upsert_knowledge_base(
            pool=pool,
            title=chunk["title"],
            content=chunk["content"],
            category=chunk["category"],
            embedding=embedding,
        )
        if kb_id:
            seeded += 1
        else:
            print(f"  WARNING: upsert returned None for '{chunk['title']}'", file=sys.stderr)

    return seeded


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)
    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY environment variable is required.", file=sys.stderr)
        sys.exit(1)
    if not _PRODUCT_DOCS_PATH.exists():
        print(f"ERROR: product-docs.md not found at {_PRODUCT_DOCS_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {_PRODUCT_DOCS_PATH} ...", flush=True)
    text = _PRODUCT_DOCS_PATH.read_text(encoding="utf-8")

    print("Splitting into chunks ...", flush=True)
    chunks = _split_into_chunks(text)
    print(f"  {len(chunks)} chunks identified.", flush=True)

    print("Generating embeddings (OpenAI text-embedding-3-small) ...", flush=True)
    client = AsyncOpenAI(api_key=openai_api_key)
    embeddings = await _embed_chunks(client, chunks)

    print("Connecting to database ...", flush=True)
    pool = await asyncpg.create_pool(dsn=database_url, min_size=1, max_size=5)

    try:
        print("Upserting chunks into knowledge_base ...", flush=True)
        seeded = await _upsert_all(pool, chunks, embeddings)
        print(f"Seeded {seeded} chunks into knowledge_base", flush=True)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
