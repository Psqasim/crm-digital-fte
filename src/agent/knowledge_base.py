from __future__ import annotations

import re
from pathlib import Path

from src.agent.models import KBResult

_DEFAULT_DOCS_PATH = Path(__file__).parent.parent.parent / "context" / "product-docs.md"

# Stop words excluded from scoring to reduce noise
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "be", "it", "i", "my", "we", "our",
    "you", "your", "this", "that", "have", "has", "had", "do", "does",
    "not", "from", "by", "as", "if", "so", "will", "can", "how", "what",
}


def _tokenize(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
    return tokens - _STOP_WORDS


def _jaccard_score(query_words: set[str], section_words: set[str]) -> float:
    if not query_words or not section_words:
        return 0.0
    intersection = query_words & section_words
    union = query_words | section_words
    return len(intersection) / len(union)


def _load_sections(docs_path: Path) -> list[tuple[str, str]]:
    """Split document by ## level headers into (title, body) pairs."""
    text = docs_path.read_text(encoding="utf-8")
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_body: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if current_title and current_body:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line[3:].strip()
            current_body = []
        else:
            current_body.append(line)

    if current_title and current_body:
        sections.append((current_title, "\n".join(current_body).strip()))

    return sections


class KnowledgeBase:
    def __init__(self, docs_path: str | Path | None = None) -> None:
        if docs_path is None:
            path = _DEFAULT_DOCS_PATH
        else:
            path = Path(docs_path)

        if not path.is_absolute():
            path = Path.cwd() / path

        self._sections = _load_sections(path)

    def search(self, query: str, top_k: int = 3) -> list[KBResult]:
        query_words = _tokenize(query)
        results: list[KBResult] = []

        for title, body in self._sections:
            # Score = Jaccard(query, body) boosted by title overlap
            body_words = _tokenize(body)
            title_words = _tokenize(title)

            body_score = _jaccard_score(query_words, body_words)
            title_score = _jaccard_score(query_words, title_words)
            # Title match is a strong signal — blend with 0.3 title weight
            score = body_score * 0.7 + title_score * 0.3

            content = body[:500]
            results.append(KBResult(section_title=title, content=content, relevance_score=round(score, 4)))

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:top_k]
