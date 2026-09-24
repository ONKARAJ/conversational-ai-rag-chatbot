"""End-to-end smoke test with a fake model (no Groq key, no network).

Run from backend/:  python -m tests.test_smoke
It uses a temporary SQLite file, so your real conversations are untouched.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="chatbot-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TMP / 'test.db'}"
os.environ["CHROMA_DIR"] = str(TMP / "chroma")
os.environ["RAG_ENABLED"] = "false"
os.environ["GROQ_API_KEY"] = "test-key-not-used"

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeListChatModel  # noqa: E402

import main  # noqa: E402
from app.services.chat import chat_service  # noqa: E402
from app.services.history import SQLiteChatMessageHistory  # noqa: E402
from app.services.llm import build_conversational_chain, count_tokens  # noqa: E402

SESSION_A = "11111111-1111-4111-8111-111111111111"
SESSION_B = "22222222-2222-4222-8222-222222222222"
HEADERS_A = {"X-Client-Session-ID": SESSION_A}
HEADERS_B = {"X-Client-Session-ID": SESSION_B}


def main_test() -> None:
    fake = FakeListChatModel(responses=["Reply one.", "Reply two.", "Reply three.", "Reply four."])

    with TestClient(main.app) as client:
        # The chain built at startup would need a real key; swap in the fake.
        chat_service._chain = build_conversational_chain(fake)

        health = client.get("/api/health").json()
        assert health["status"] == "ok", health
        assert client.get("/api/conversations").status_code == 422

        # --- create two conversations --------------------------------------
        a = client.post("/api/conversations", json={}, headers=HEADERS_A).json()
        b = client.post("/api/conversations", json={}, headers=HEADERS_B).json()
        assert a["id"].startswith("conversation_") and a["id"] != b["id"]
        assert a["title"] == "New chat"
        assert client.get("/api/conversations", headers=HEADERS_A).json()[0]["id"] == a["id"]
        assert client.get("/api/conversations", headers=HEADERS_B).json()[0]["id"] == b["id"]

        # --- talk in A ------------------------------------------------------
        r = client.post(
            f"/api/conversations/{a['id']}/messages",
            json={"content": "My name is Onkar and I build GenAI apps."},
            headers=HEADERS_A,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["assistant_message"]["content"] == "Reply one."
        assert body["title"] == "My name is Onkar and I build GenAI apps."  # auto-title

        # --- talk in B ------------------------------------------------------
        client.post(
            f"/api/conversations/{b['id']}/messages",
            json={"content": "I am Priya."},
            headers=HEADERS_B,
        )

        # --- cross-session access is denied -------------------------------
        assert client.get(f"/api/conversations/{a['id']}", headers=HEADERS_B).status_code == 404
        assert client.patch(
            f"/api/conversations/{a['id']}",
            json={"title": "stolen"},
            headers=HEADERS_B,
        ).status_code == 404
        assert client.delete(f"/api/conversations/{a['id']}", headers=HEADERS_B).status_code == 404
        assert client.post(
            f"/api/conversations/{a['id']}/messages",
            json={"content": "cross-session"},
            headers=HEADERS_B,
        ).status_code == 404

        # --- isolation: A's history must not contain B's turns --------------
        history_a = [m.content for m in SQLiteChatMessageHistory(a["id"]).messages]
        history_b = [m.content for m in SQLiteChatMessageHistory(b["id"]).messages]
        assert any("Onkar" in m for m in history_a)
        assert not any("Priya" in m for m in history_a), history_a
        assert not any("Onkar" in m for m in history_b), history_b

        # --- transcript round-trip -----------------------------------------
        detail = client.get(f"/api/conversations/{a['id']}", headers=HEADERS_A).json()
        assert [m["role"] for m in detail["messages"]] == ["human", "ai"]

        # --- rename ---------------------------------------------------------
        renamed = client.patch(
            f"/api/conversations/{a['id']}",
            json={"title": "Portfolio project"},
            headers=HEADERS_A,
        ).json()
        assert renamed["title"] == "Portfolio project"

        # --- search -----------------------------------------------------------
        found = client.get(
            "/api/conversations", params={"search": "priya"}, headers=HEADERS_B
        ).json()
        assert [c["id"] for c in found] == [b["id"]], found
        assert client.get(
            "/api/conversations", params={"search": "priya"}, headers=HEADERS_A
        ).json() == []

        # --- validation and 404s ---------------------------------------------
        assert client.post(
            f"/api/conversations/{a['id']}/messages",
            json={"content": "  "},
            headers=HEADERS_A,
        ).status_code == 422
        assert client.get("/api/conversations/conversation_missing", headers=HEADERS_A).status_code == 404
        assert (
            client.post(
                "/api/conversations/conversation_missing/messages",
                json={"content": "hi"},
                headers=HEADERS_A,
            ).status_code
            == 404
        )

        # --- delete cascades ---------------------------------------------------
        assert client.delete(f"/api/conversations/{b['id']}", headers=HEADERS_B).status_code == 204
        assert client.get(f"/api/conversations/{b['id']}", headers=HEADERS_B).status_code == 404
        assert not SQLiteChatMessageHistory(b["id"]).messages

        # --- token counter behaves ----------------------------------------------
        from langchain_core.messages import HumanMessage

        assert count_tokens([HumanMessage(content="hello world")]) > 0

    print("All smoke tests passed.")


if __name__ == "__main__":
    main_test()
