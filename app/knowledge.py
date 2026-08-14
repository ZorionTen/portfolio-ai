import json
import os
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CACHE_SECONDS = 6 * 60 * 60
MAX_CONTEXT_CHUNKS = 7
MAX_CONTEXT_CHARACTERS = 8_000

SENSITIVE_LINE_PATTERNS = (
    re.compile(r"\b(shein|walmart|amazon|tiktok|cedcommerce|threecolts)\b", re.IGNORECASE),
    re.compile(r"\b(phone|postal code|compensation|salary|work authorization|sponsorship)\b", re.IGNORECASE),
    re.compile(r"₹|\bLPA\b", re.IGNORECASE),
    re.compile(r"(?:\+?\d[\s-]?){9,}\d"),
)

STOP_WORDS = {
    "a", "about", "an", "and", "are", "can", "does", "for", "from", "he", "his", "how",
    "i", "in", "is", "it", "me", "of", "on", "or", "the", "to", "what", "with", "zaid",
}


@dataclass(frozen=True)
class KnowledgeChunk:
    text: str
    source: str
    url: str | None = None


@dataclass(frozen=True)
class RetrievalResult:
    context: str
    sources: tuple[str, ...]


class KnowledgeRetriever:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: tuple[KnowledgeChunk, ...] = ()
        self._expires_at = 0.0

    def retrieve(self, query: str) -> RetrievalResult:
        chunks = self._get_chunks()
        ranked = rank_chunks(query, chunks)
        selected: list[KnowledgeChunk] = []
        character_count = 0

        for chunk in ranked[:MAX_CONTEXT_CHUNKS]:
            if character_count + len(chunk.text) > MAX_CONTEXT_CHARACTERS:
                continue
            selected.append(chunk)
            character_count += len(chunk.text)

        context = "\n\n".join(
            f"[Source: {chunk.source}]\n{chunk.text}" for chunk in selected
        )
        sources = tuple(dict.fromkeys(chunk.source for chunk in selected))
        return RetrievalResult(context=context, sources=sources)

    def _get_chunks(self) -> tuple[KnowledgeChunk, ...]:
        now = time.monotonic()
        if self._chunks and now < self._expires_at:
            return self._chunks

        with self._lock:
            if self._chunks and now < self._expires_at:
                return self._chunks

            chunks = tuple(self._load_skills_chunks() + self._load_github_chunks())
            if chunks:
                self._chunks = chunks
                self._expires_at = now + CACHE_SECONDS
            return self._chunks

    def _load_skills_chunks(self) -> list[KnowledgeChunk]:
        skills_file = Path(os.getenv("SKILLS_FILE", "../JOB_APPLICATION_MASTER.md"))
        try:
            content = skills_file.read_text(encoding="utf-8")
        except OSError:
            return []

        safe_content = sanitize_job_master(content)
        return [
            KnowledgeChunk(text=section, source="Verified skills profile")
            for section in chunk_markdown(safe_content)
        ]

    def _load_github_chunks(self) -> list[KnowledgeChunk]:
        knowledge_url = os.getenv(
            "GITHUB_KNOWLEDGE_URL",
            "https://portfolio-backend-lutt.onrender.com/api/github/knowledge",
        )
        request = Request(knowledge_url, headers={"User-Agent": "zorionten-portfolio-ai"})
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return []

        chunks: list[KnowledgeChunk] = []
        for source in payload.get("sources", []):
            source_name = source.get("source", "GitHub project evidence")
            source_url = source.get("url")
            chunks.extend(
                KnowledgeChunk(text=section, source=source_name, url=source_url)
                for section in chunk_markdown(source.get("text", ""))
            )
        return chunks


def sanitize_job_master(content: str) -> str:
    safe_lines = []
    for line in content.splitlines():
        if any(pattern.search(line) for pattern in SENSITIVE_LINE_PATTERNS):
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines)


def chunk_markdown(content: str, max_characters: int = 1_200) -> list[str]:
    chunks: list[str] = []
    heading = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(f"{heading}\n{text}".strip())
        buffer = []

    for line in content.splitlines():
        if line.startswith("#"):
            flush()
            heading = line.strip()
            continue
        projected = len(heading) + sum(len(item) for item in buffer) + len(line)
        if projected > max_characters:
            flush()
        buffer.append(line)
    flush()
    return chunks


def rank_chunks(query: str, chunks: tuple[KnowledgeChunk, ...]) -> list[KnowledgeChunk]:
    query_terms = [term for term in tokenize(query) if term not in STOP_WORDS]
    if not query_terms:
        return list(chunks)

    scored = []
    for index, chunk in enumerate(chunks):
        tokens = Counter(tokenize(chunk.text))
        source_tokens = set(tokenize(chunk.source))
        score = sum(1 + min(tokens[term], 4) for term in query_terms if term in tokens)
        score += sum(3 for term in query_terms if term in source_tokens)
        if score:
            scored.append((score, -index, chunk))

    if not scored:
        return [chunk for chunk in chunks if chunk.source == "Verified skills profile"]
    scored.sort(reverse=True, key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored]


def tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+", value.lower())
