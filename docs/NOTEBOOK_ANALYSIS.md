# Existing Notebook Analysis

A record of what `ChatBotsHistory.ipynb` contained and how each piece was carried
into this application. Nothing here claims functionality the notebook did not have.

## 1. What the notebook does

It is a linear LangChain tutorial: 18 code cells, no functions, no classes, no
application loop. It covers two tracks that never meet.

**Track A — conversation with memory (cells 0–10)**

1. Load `GROQ_API_KEY` with `python-dotenv`.
2. Create `ChatGroq(model="openai/gpt-oss-120b", groq_api_key=...)`.
3. Show that a bare `model.invoke([...])` has no memory unless you pass the
   previous turns yourself.
4. Introduce `RunnableWithMessageHistory` over an in-memory `store = {}` dict,
   and demonstrate that `session_id="chat1"` and `session_id="chat2"` keep
   separate histories.
5. Add a `ChatPromptTemplate` with a `{language}` system message and a
   `MessagesPlaceholder(variable_name="messages")`.
6. Add `trim_messages(max_tokens=70, ...)` and chain it in front of the prompt.

**Track B — retrieval (cells 11–17)**

7. Define five `Document` objects about pets.
8. Embed them with `HuggingFaceEmbeddings(model="all-MiniLM-L6-v2")`.
9. Store them with `Chroma.from_documents(...)` (in-memory).
10. Build a retriever with `k=1` and a prompt that says to answer using the
    provided context only, then invoke it once with "tell me about dogs".

## 2. Which parts are GenAI

| Notebook cell | Element |
|---|---|
| 1, 12 | `ChatGroq` — the LLM, `openai/gpt-oss-120b` |
| 6 | `ChatPromptTemplate` + `MessagesPlaceholder` with a `{language}` variable |
| 4, 7, 10 | `RunnableWithMessageHistory` for per-session memory |
| 8 | `trim_messages` for context-window management |
| 9 | LCEL composition: `RunnablePassthrough.assign(...) \| prompt \| model` |

## 3. Which parts are RAG

| Notebook cell | Element |
|---|---|
| 11 | Five hardcoded `Document`s (the corpus) |
| 13 | `HuggingFaceEmbeddings("all-MiniLM-L6-v2")` |
| 14 | `Chroma.from_documents(...)` — vector store |
| 15 | `similarity_search_with_score("cat")` |
| 16 | `as_retriever(search_type="similarity", search_kwargs={"k": 1})` |
| 17 | `{"context": retriever, "question": RunnablePassthrough()} \| prompt \| llm` |

Note that the RAG chain in cell 17 has **no memory** and the chat chain in
cell 10 has **no retrieval**. Joining them is new work, described in §6.

## 4. How conversation memory currently works

```python
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

with_message_history = RunnableWithMessageHistory(
    chain, get_session_history, input_messages_key="messages"
)
response = with_message_history.invoke(
    {"messages": [HumanMessage(content="...")], "language": "hindi"},
    config={"configurable": {"session_id": "chat4"}},
)
```

`RunnableWithMessageHistory` reads the history for the given `session_id`,
prepends it to the `messages` input, runs the chain, then appends the new human
message and the AI reply back into that history object. Isolation comes entirely
from the dict key: `chat1` and `chat2` index different `ChatMessageHistory`
objects, so they cannot see each other.

Limitation: `store` is a Python dict in the notebook process. Restart the kernel
and every conversation is gone.

## 5. What needed to change for the web

| Issue in the notebook | Why it blocks a web app | Change made |
|---|---|---|
| `session_id` hardcoded to `"chat1"`, `"chat4"`… | The browser must choose the session | Session id is the `conversation_id` in the URL path |
| `store = {}` | Dies with the process; invisible to the REST API | `SQLiteChatMessageHistory` reading the same table the API serves |
| `Chroma.from_documents(...)` at cell level | Re-embeds the corpus on every run | Persisted collection, built once at startup, reused afterwards |
| Embeddings loaded inline | Seconds of load time per call if done per request | Loaded once in the FastAPI lifespan handler |
| `max_tokens=70` | Keeps roughly one or two turns; the assistant forgets immediately | `MAX_HISTORY_TOKENS=3000`, configurable |
| `token_counter=model` | Couples trimming to the chat model object | Local `tiktoken` counter, with a character-based fallback |
| `os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")` | Raises `TypeError` when the variable is absent | Only set when a value exists |
| `HuggingFaceEmbeddings(model=...)` | `model_name` is the documented argument; `model` is not accepted by every release | Uses `model_name` |
| No error handling | Any provider failure becomes a traceback | Typed errors mapped to JSON responses |
| Retrieval separate from chat | Grounded answers have no memory | Retrieval result injected into the conversational prompt as `{context}` |

## 6. Which notebook code is reused

Reused with the same structure and behaviour:

- The Groq model configuration — `app/services/llm.py::build_model`
- The system prompt with `{language}` and the `MessagesPlaceholder` — `build_prompt`
- `trim_messages(strategy="last", include_system=True, allow_partial=False, start_on="human")` — `build_trimmer`
- The LCEL composition `RunnablePassthrough.assign(messages=itemgetter("messages") | trimmer) | prompt | model` — `build_chain`
- `RunnableWithMessageHistory(chain, get_session_history, input_messages_key="messages")` — `build_conversational_chain`
- The `get_session_history(session_id)` factory signature — `app/services/history.py`
- The five pet documents — `app/services/rag.py::seed_documents`
- MiniLM embeddings, Chroma, and the similarity retriever — `app/services/rag.py`
- The "answer using the provided context only" instruction — `app/services/llm.py::CONTEXT_TEMPLATE`

## 7. Which notebook code was refactored

- **`store = {}` → `SQLiteChatMessageHistory`.** Same `BaseChatMessageHistory`
  interface (`messages`, `add_messages`, `clear`), different storage. This is
  why the REST API and LangChain never disagree about what was said: there is
  one `messages` table and both read it.
- **`rag_chain` → context injection.** The notebook's standalone RAG chain
  answered one question with no history. Here the retriever runs first, its
  output is formatted into the `{context}` slot of the conversational prompt,
  and the reply goes through the same memory-backed chain. The strict
  "context only" instruction is preserved but scoped, so the assistant can
  still answer ordinary questions when retrieval finds nothing relevant.
- **Retriever `k=1` → `k=3`** (`RAG_TOP_K`). One chunk is often too little to
  answer with; three is still small enough to keep the prompt tight.
- **Corpus loading.** Still falls back to the five pet documents, but any
  `.md`/`.txt` file dropped into `backend/knowledge_base/` is chunked and
  indexed instead.
- **Cell-level globals → startup singletons.** `rag_service` and `chat_service`
  are initialised in the FastAPI lifespan handler.

## 8. Known deprecation

`RunnableWithMessageHistory` is marked deprecated in LangChain 1.x in favour of
LangGraph's persistence layer. It still works, and it is what the notebook used,
so it is kept here deliberately. If you are asked about it in an interview, the
honest answer is: the memory mechanism is intact and the storage behind it is
now durable; migrating to LangGraph checkpointers would swap the wrapper without
changing the session-id model this app is built on.
