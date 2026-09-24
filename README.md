# Context-Aware Conversational AI Chatbot

Session-based conversational memory with retrieval, built on LangChain + Groq,
served by FastAPI, with a React chat client.

Every conversation gets its own id. That id is the LangChain `session_id`, the
SQLite foreign key, and the URL path segment — one identifier all the way
through, which is what keeps two conversations from ever seeing each other's
history.

Grown out of `ChatBotsHistory.ipynb`. See
[`docs/NOTEBOOK_ANALYSIS.md`](docs/NOTEBOOK_ANALYSIS.md) for exactly which parts
of the notebook are reused and which were refactored, and why.

---

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running it](#running-it)
- [How conversation ids work](#how-conversation-ids-work)
- [How memory works](#how-memory-works)
- [Why message trimming matters](#why-message-trimming-matters)
- [How RAG works](#how-rag-works)
- [LangSmith tracing](#langsmith-tracing)
- [Two databases, two jobs](#two-databases-two-jobs)
- [API reference](#api-reference)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## What it does

- Start a new conversation and get a unique session id
- Keep chatting in that session with full context
- Run several conversations side by side with completely separate memory
- Switch back to an old conversation and continue it, context intact
- Rename and delete conversations
- Search across conversation titles and message bodies
- Ground answers in a local knowledge base, with the retrieved passages shown
- Markdown and syntax-highlighted code in replies, with copy buttons
- Light and dark themes, responsive down to a phone

---

## Architecture

```
┌──────────────────────── Browser ────────────────────────┐
│  React 18 + Vite + Tailwind        localhost:5173       │
│  Sidebar · Thread · Composer                            │
└──────────────────┬──────────────────────────────────────┘
                   │  fetch('/api/…')  → Vite dev proxy
┌──────────────────▼──────────────────────────────────────┐
│  FastAPI                            localhost:8000      │
│                                                         │
│  api/conversations.py  ← Pydantic validation, CORS       │
│         │                                               │
│  services/chat.py                                       │
│    ├── services/rag.py     retrieve top-k passages      │
│    └── services/llm.py     RunnableWithMessageHistory   │
│            ├── trim_messages                            │
│            ├── ChatPromptTemplate {language} {context}  │
│            └── ChatGroq                                 │
│                    │                                    │
│  services/history.py  SQLiteChatMessageHistory           │
└──────────┬────────────────────────────┬─────────────────┘
           │                            │
   ┌───────▼────────┐          ┌────────▼─────────┐
   │ SQLite         │          │ Chroma           │
   │ conversations  │          │ knowledge base   │
   │ + messages     │          │ + MiniLM vectors │
   └────────────────┘          └──────────────────┘
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 – 3.12 | 3.13 works, but some ML wheels lag behind |
| Node.js | 18+ (20 LTS recommended) | `node --version` |
| Groq API key | free | https://console.groq.com/keys |
| Disk | ~2 GB | `sentence-transformers` pulls in PyTorch |

No Docker, no Redis, no external database needed.

---

## Setup

### 1. Environment variables

From the project root:

```bash
cp .env.example .env
```

Open `.env` and set your key:

```
GROQ_API_KEY=gsk_your_actual_key_here
```

That file is git-ignored and read only by the backend. The React app never sees
it — it talks to FastAPI, and FastAPI talks to Groq.

### 2. Backend

```bash
cd backend
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

The first install is the slow one (PyTorch). If you want to skip it for now,
set `RAG_ENABLED=false` in `.env` and install without the last four lines of
`requirements.txt`; the chat side works fine without retrieval.

### 3. Frontend

```bash
cd frontend
npm install
```

---

## Running it

Two terminals.

**Terminal 1 — backend**

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

First start downloads the MiniLM model (~90 MB) and builds the Chroma index.
Wait for:

```
Ready. model=openai/gpt-oss-120b | llm_configured=True | rag_available=True (5 docs)
```

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**.

Interactive API docs are at **http://localhost:8000/docs**.

### LangSmith tracing

The backend uses an explicit LangChain LangSmith tracer on the production
chain invocation. It traces the question, model response, model run, latency,
errors, and conversation metadata. The React app never receives the LangSmith key.

For local development, add these values to the root `.env` file (or
`backend/.env`) and restart the backend:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=conversational-ai-rag-chatbot
```

On Render, add the same three variables under **Dashboard → Service →
Environment → Environment Variables**. Store the real key as a secret value;
do not put it in the repository or any `frontend/.env` file. The backend startup
log reports tracing and configuration status without printing the key.

To verify a trace, create a conversation and send a message through the app (or
the `POST /api/conversations/{id}/messages` endpoint). Open the LangSmith
workspace, select the `conversational-ai-rag-chatbot` project, and open the
newest `conversation_turn` run. The run contains the question and response;
its metadata includes `conversation_id`, `model`, and retrieved document count.
The model child run shows the provider call, timing, and any error details.

If the project is empty, confirm the backend log says
`langsmith_tracing=True | langsmith_configured=True`, then restart and send a
new message. A real `LANGSMITH_API_KEY` is required for traces to be uploaded.

### Anonymous session privacy

The browser creates one cryptographically random UUID and stores it in
`localStorage`. Every API request sends it in the `X-Client-Session-ID` header.
The backend stores that value on each new conversation and scopes list, create,
read, rename, delete, and message operations to it. Changing only a
conversation id cannot cross that boundary; another browser or device has a
different UUID. Existing conversations from before this field was added remain
in SQLite but are unassigned and are not returned to any anonymous session.

**Optional — verify the backend without spending a single token:**

```bash
cd backend
python -m tests.test_smoke
```

That runs the full API against a fake model and asserts, among other things,
that conversation A's history never contains conversation B's turns.

---

## How conversation ids work

`POST /api/conversations` generates an id like `conversation_8f42a1c9d0b74e3a`
and returns it. From then on that single string is:

- the primary key in the `conversations` table
- the foreign key on every row in `messages`
- the path segment in `/api/conversations/{id}/messages`
- the `session_id` handed to LangChain:

```python
chain.invoke(
    {"messages": [HumanMessage(content=question)], "language": ..., "context": ...},
    config={"configurable": {"session_id": conversation_id}},
)
```

The notebook hardcoded `"chat1"` and `"chat4"`. The only real change is that the
value now comes from the frontend.

---

## How memory works

One turn, end to end:

1. The frontend POSTs the user's text to `/api/conversations/{id}/messages`.
2. `chat_service` loads that conversation's settings (language, RAG on/off).
3. If retrieval is on, the retriever runs and the passages are formatted into
   the prompt's `{context}` slot.
4. `RunnableWithMessageHistory` calls `get_session_history(id)`, which returns a
   `SQLiteChatMessageHistory` bound to that id. It reads every prior message row
   for that conversation and prepends them to the new one.
5. `trim_messages` cuts the list down to the token budget.
6. The prompt renders — system message, then the trimmed history, then the new
   question — and goes to Groq.
7. The reply comes back, and the history adapter writes the user message and the
   AI message into the `messages` table.
8. The API returns both persisted rows plus any retrieved sources.

Isolation is structural, not a check somewhere: a history object only ever
issues `SELECT ... WHERE conversation_id = :id`. A different conversation is a
different id, so it reads different rows.

The notebook's in-memory `store = {}` was replaced by this SQLite-backed class so
that the transcript the REST API serves and the history LangChain reads are the
same rows — no duplicate state, and nothing lost on restart.

---

## Why message trimming matters

Chat models are stateless. Every turn re-sends the whole conversation, so an
untrimmed thread grows the prompt without bound:

- **Cost** climbs on every message, because you pay for the re-sent history each time.
- **Latency** climbs with it — more input tokens means more time to first token.
- **It eventually breaks.** Past the model's context window the request fails
  outright, and it fails on the longest, most valuable conversations first.

`strategy="last"` keeps the most recent turns and drops the oldest, on the bet
that recent context matters most. `start_on="human"` makes sure the surviving
window opens on a user turn, so the model never sees a reply with no question
attached. `include_system=True` keeps the system message whatever else goes.

The notebook used `max_tokens=70` — enough to demonstrate the mechanism, far too
small to hold a conversation. The default here is `MAX_HISTORY_TOKENS=3000`.
Trade-off: raising it means better long-range recall and higher cost per turn.

---

## How RAG works

```
knowledge_base/*.md  →  chunks  →  MiniLM embeddings  →  Chroma  (startup, once)

user question  →  similarity search (k=3)  →  {context}  →  prompt  →  Groq
```

- **Corpus.** Any `.md` or `.txt` file in `backend/knowledge_base/` is split into
  ~800-character chunks. If that folder is empty, the five pet documents from the
  notebook are indexed instead, so the retriever always has something to find.
- **Embeddings.** `all-MiniLM-L6-v2` via `langchain-huggingface`, loaded once at
  startup — it takes seconds, which is why it does not happen per request.
- **Store.** Chroma with a `persist_directory`, so a restart reuses the existing
  collection rather than re-embedding. The notebook's `Chroma.from_documents(...)`
  was purely in-memory.
- **Use.** The retrieved passages go into the same prompt as the conversation
  history, so a grounded answer still knows what you said three turns ago. When
  nothing relevant comes back, the model is told to answer normally rather than
  invent a citation.
- **Visibility.** Retrieved passages appear under the reply behind a
  "N retrieved passages" toggle, with source names and relevance scores.

Adding your own documents:

```bash
cp my-notes.md backend/knowledge_base/
rm -rf backend/data/chroma        # the index is only built when empty
# restart the backend
```

You can inspect retrieval directly: `GET /api/rag/search?q=rabbits`.

---

## Two databases, two jobs

They are easy to confuse, and they are not the same thing.

| | **Conversation store** (SQLite) | **Vector store** (Chroma) |
|---|---|---|
| Holds | What was said, by whom, in which conversation | Knowledge-base passages + their embeddings |
| Keyed by | `conversation_id` | Vector similarity |
| Written when | Every message | Only when the knowledge base is (re)indexed |
| Read by | The API and `SQLiteChatMessageHistory` | The retriever |
| Per user | Yes — memory is private to a conversation | No — shared reference material |
| If deleted | Chat history is gone | Retrieval stops until you rebuild it; conversations are unaffected |

Short version: SQLite remembers **your conversation**; Chroma stores **facts to
look things up in**. Deleting a conversation removes its messages and nothing
else — the knowledge base is untouched.

---

## API reference

Base URL `http://localhost:8000`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/conversations` | Create a conversation; returns its id |
| `GET` | `/api/conversations` | List conversations, newest first. `?search=` matches titles and message bodies |
| `GET` | `/api/conversations/{id}` | Conversation with its full transcript |
| `PATCH` | `/api/conversations/{id}` | Rename, or change `language` / `rag_enabled` |
| `DELETE` | `/api/conversations/{id}` | Delete the conversation and its messages |
| `POST` | `/api/conversations/{id}/messages` | Send a message, get the reply |
| `GET` | `/api/health` | Key present? Model? Knowledge base loaded? |
| `GET` | `/api/rag/search?q=` | Inspect what the retriever returns |

Send a message:

```bash
curl -X POST http://localhost:8000/api/conversations/conversation_abc123/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What do you know about rabbits?"}'
```

```json
{
  "conversation_id": "conversation_abc123",
  "user_message":      { "id": 7, "role": "human", "content": "…", "created_at": "…" },
  "assistant_message": { "id": 8, "role": "ai",    "content": "…", "created_at": "…" },
  "sources": [{ "source": "mammal-pets-doc", "snippet": "Rabbits are social…", "score": 0.62 }],
  "used_rag": true,
  "title": "What do you know about rabbits?"
}
```

Errors always come back in one shape, with no stack trace:

```json
{ "error": { "code": "llm_unavailable", "message": "Groq rate limit reached. Wait a few seconds and try again." } }
```

Codes: `conversation_not_found` (404), `invalid_request` / `empty_message` (422),
`configuration_error` (503), `llm_unavailable` (502), `llm_timeout` (504),
`retrieval_failed`, `storage_error`, `internal_error` (500).

---

## Project structure

```
project-root/
├── backend/
│   ├── main.py                     FastAPI app, lifespan, error handlers
│   ├── requirements.txt
│   ├── knowledge_base/             drop .md/.txt files here to index them
│   ├── data/                       SQLite + Chroma (git-ignored, auto-created)
│   ├── tests/test_smoke.py         end-to-end test with a fake model
│   └── app/
│       ├── models.py               Conversation, Message (SQLAlchemy)
│       ├── schemas.py              Pydantic request/response models
│       ├── core/
│       │   ├── config.py           settings from .env
│       │   ├── database.py         engine, session, Base
│       │   └── errors.py           typed, user-safe errors
│       ├── api/
│       │   ├── conversations.py    the six conversation endpoints
│       │   └── system.py           /api/health, /api/rag/search
│       └── services/
│           ├── llm.py              model, prompt, trimmer, chain  ← from the notebook
│           ├── history.py          SQLiteChatMessageHistory       ← replaces store={}
│           ├── rag.py              embeddings, Chroma, retriever  ← from the notebook
│           ├── chat.py             one turn, end to end
│           └── conversations.py    CRUD
├── frontend/
│   ├── index.html
│   ├── vite.config.js              dev proxy /api → :8000
│   ├── tailwind.config.js
│   └── src/
│       ├── App.jsx
│       ├── components/             Sidebar, ChatHeader, MessageList, Message,
│       │                           MarkdownMessage, Composer, SourcesStrip, …
│       ├── hooks/                  useConversations, useThread, useHealth, …
│       ├── services/api.js         the only file that touches the network
│       └── lib/format.js
├── docs/NOTEBOOK_ANALYSIS.md
├── .env.example
└── README.md
```

### Design notes

- **Layers.** Routes validate and delegate; services hold the logic; models
  describe storage. No LangChain import anywhere in `api/`, no SQL anywhere in
  `llm.py`.
- **Startup, not request time.** The embedding model, the vector store and the
  chain are built once in the lifespan handler.
- **Blocking work off the event loop.** The Groq call runs in a threadpool via
  `run_in_threadpool`, so one slow reply doesn't stall other requests.
- **Swapping SQLite for Postgres.** Change `DATABASE_URL`, install `psycopg`,
  done — no SQLite-specific types are used, and `connect_args` is applied only
  for SQLite.

---

## Troubleshooting

**"Cannot reach the backend."**
The backend isn't running, or it's on a different port. Check
http://localhost:8000/api/health. If you moved the port, update `VITE_BACKEND_URL`
in `frontend/.env` and `CORS_ORIGINS` in `.env`.

**"GROQ_API_KEY is not set on the server."**
`.env` must be in the **project root** (or in `backend/`), the key must have no
quotes around it, and the backend must be restarted after you add it.

**"Groq rejected the API key."**
The key is present but invalid or revoked. Generate a new one at
console.groq.com/keys.

**"The model is unavailable."**
Groq retires model names periodically. Set `GROQ_MODEL` in `.env` to a current
one from console.groq.com/docs/models.

**Backend starts but `rag_available=False`.**
Either `RAG_ENABLED=false`, or `sentence-transformers` / `chromadb` didn't
install. Check the startup logs for the reason — the chat still works without
retrieval. On first run the model download also needs network access.

**Backend startup is very slow the first time.**
Expected: it's downloading MiniLM and embedding the corpus. Subsequent starts
reuse `backend/data/chroma`.

**Edited a knowledge-base file but answers didn't change.**
The index is only built when the collection is empty. `rm -rf backend/data/chroma`
and restart.

**CORS errors in the browser console.**
Add your frontend origin to `CORS_ORIGINS` and restart the backend. In dev you
normally won't hit this, since Vite proxies `/api` and the browser stays on one
origin.

**`ModuleNotFoundError: No module named 'app'`.**
Run uvicorn from inside `backend/`, not from the project root.

**Port already in use.**
`uvicorn main:app --reload --port 8010`, or `npm run dev -- --port 5180`.

**The assistant forgets things from early in a long chat.**
That's trimming doing its job. Raise `MAX_HISTORY_TOKENS` in `.env` if you want a
longer window — it costs more per turn.

**Conversations disappeared.**
Check whether `backend/data/conversations.db` still exists; it's git-ignored, so
a clean checkout starts empty.
