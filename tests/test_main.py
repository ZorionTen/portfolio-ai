from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.knowledge import RetrievalResult
from app.main import app, strengthen_hiring_response

client = TestClient(app)


def test_health() -> None:
    with patch.dict("os.environ", {}, clear=True):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "chatConfigured": False}


def test_chat_requires_configuration() -> None:
    with patch.dict("os.environ", {}, clear=True):
        response = client.post("/chat", json={
            "message": "What does he build now?",
            "history": [
                {"role": "user", "content": "Tell me about Zaid."},
                {"role": "assistant", "content": "Zaid is a backend-focused engineer."},
            ],
        })

    assert response.status_code == 503
    assert response.json() == {"detail": "Chat is not configured"}


def test_chat_uses_groq_with_verified_context() -> None:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content="Zaid builds reliable backend systems (Source: Verified skills profile)."
        ))]
    )

    with (
        patch.dict(
            "os.environ",
            {"GROQ_API_KEY": "gsk_test", "GROQ_MODEL": "llama-3.3-70b-versatile"},
            clear=True,
        ),
        patch("app.main.Groq") as groq,
        patch("app.main.knowledge_retriever.retrieve") as retrieve,
    ):
        retrieve.return_value = RetrievalResult(
            context="[Source: Verified skills profile]\nZaid builds reliable APIs.",
            sources=("Verified skills profile",),
        )
        groq.return_value.chat.completions.create.return_value = completion
        response = client.post("/chat", json={
            "message": "What does he build now?",
            "history": [
                {"role": "user", "content": "Tell me about Zaid."},
                {"role": "assistant", "content": "Zaid is a backend-focused engineer."},
            ],
        })

    assert response.status_code == 200
    assert response.json() == {
        "response": "Zaid builds reliable backend systems (Source: Verified skills profile).",
        "sources": ["Verified skills profile"],
    }
    groq.assert_called_once_with(api_key="gsk_test", timeout=15)
    request = groq.return_value.chat.completions.create.call_args.kwargs
    assert request["model"] == "llama-3.3-70b-versatile"
    assert request["messages"][0]["role"] == "system"
    assert "Retrieved portfolio context" in request["messages"][1]["content"]
    assert request["messages"][2:4] == [
        {"role": "user", "content": "Tell me about Zaid."},
        {"role": "assistant", "content": "Zaid is a backend-focused engineer."},
    ]
    assert request["messages"][4] == {"role": "user", "content": "What does he build now?"}
    retrieve.assert_called_once()
    retrieval_query = retrieve.call_args.args[0]
    assert "Tell me about Zaid" in retrieval_query
    assert "What does he build now" in retrieval_query


def test_chat_rejects_more_than_fifty_history_messages() -> None:
    history = [
        {"role": "user", "content": f"Message {index}"}
        for index in range(51)
    ]

    response = client.post("/chat", json={"message": "Continue", "history": history})

    assert response.status_code == 422


def test_hiring_response_removes_undermining_hedges() -> None:
    response = strengthen_hiring_response(
        "Yes, Zaid has strong adaptability. "
        "Although his primary experience is in backend engineering, he has built cross-platform apps. "
        "While Swift is not listed in his portfolio, his learning ability makes him a strong candidate."
    )

    assert response == (
        "Yes, Zaid has strong adaptability. "
        "He has built cross-platform apps. "
        "His learning ability makes him a strong candidate."
    )
