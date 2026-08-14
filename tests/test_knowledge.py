import json
from io import BytesIO
from unittest.mock import patch

from app.knowledge import (
    KnowledgeChunk,
    KnowledgeRetriever,
    chunk_markdown,
    rank_chunks,
    sanitize_job_master,
)


class JsonResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        self.close()


def test_job_master_sanitization_removes_sensitive_and_confidential_lines() -> None:
    content = """# Skills
- PHP and MongoDB
- Phone: +91 99999 99999
- Current compensation: ₹11 LPA
- Built a confidential Walmart integration
- Multi-tenant reliability engineering
"""

    sanitized = sanitize_job_master(content)

    assert "PHP and MongoDB" in sanitized
    assert "Multi-tenant reliability engineering" in sanitized
    assert "99999" not in sanitized
    assert "compensation" not in sanitized
    assert "Walmart" not in sanitized


def test_retrieval_ranks_relevant_skills_context() -> None:
    chunks = (
        KnowledgeChunk("React and TypeScript frontend work", "GitHub: frontend"),
        KnowledgeChunk("PHP, MongoDB, Redis, queues, and workers", "Verified skills profile"),
    )

    ranked = rank_chunks("What backend queue experience does Zaid have?", chunks)

    assert ranked[0].source == "Verified skills profile"


def test_github_context_is_loaded_only_from_the_java_knowledge_feed() -> None:
    payload = {
        "sources": [
            {
                "source": "GitHub: MDRead",
                "text": "# MDRead\nElectron Markdown reader with Mermaid",
                "url": "https://github.com/ZorionTen/MDRead",
            },
            {
                "source": "Private project evidence",
                "text": "Private repository evidence supports TypeScript and NestJS.",
                "url": None,
            },
        ]
    }
    response = JsonResponse(json.dumps(payload).encode())

    with (
        patch.dict("os.environ", {"GITHUB_KNOWLEDGE_URL": "http://java/api/github/knowledge"}),
        patch("app.knowledge.urlopen", return_value=response) as urlopen,
    ):
        chunks = KnowledgeRetriever()._load_github_chunks()

    urlopen.assert_called_once()
    assert {chunk.source for chunk in chunks} == {"GitHub: MDRead", "Private project evidence"}
    assert any("Electron" in chunk.text for chunk in chunks)


def test_markdown_is_split_into_bounded_sections() -> None:
    chunks = chunk_markdown("# Skills\nPHP\n## Projects\nRushServe", max_characters=30)

    assert chunks == ["# Skills\nPHP", "## Projects\nRushServe"]
