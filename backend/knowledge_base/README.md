# Knowledge base

Drop `.md` or `.txt` files in this folder to put them in the RAG index.

On startup the backend reads every file here, splits it into ~800-character
chunks, embeds them with `all-MiniLM-L6-v2` and stores them in Chroma under
`backend/data/chroma/`.

If the folder contains no `.md`/`.txt` files other than this README, the five
sample pet documents from the original notebook are indexed instead, so the
retriever always has something to find.

**After adding or editing files, delete `backend/data/chroma/` and restart the
backend** — the index is only built when the collection is empty.
