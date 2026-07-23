# Hybrid Search RAG From Scratch

A Retrieval-Augmented Generation application built from scratch — no RAG
framework — to understand how retrieval, embeddings, vector search, and grounded
generation actually work under the hood. Upload your own documents and ask
questions; every answer cites the exact chunks it was built from.

- **Backend:** FastAPI + Supabase (pgvector) + Gemini (via the OpenAI-compatible endpoint)
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS
- **Pipeline:** chunk → embed → store → **hybrid retrieve** → augment → generate, with citations

## Demo

![RAG From Scratch — asking a question, then inspecting how hybrid vs. vector retrieval ranked the chunks](docs/demo.gif)

## Features

- **Hybrid retrieval** — vector similarity *and* Postgres full-text search, fused
  with Reciprocal Rank Fusion (see below).
- **Document upload** — drop in a PDF, `.txt`, or `.md`; it's parsed, chunked,
  embedded, and searchable immediately.
- **Grounded answers with citations** — the model answers only from retrieved
  context and cites each chunk it used.
- **Built by hand** — chunking, embeddings, cosine similarity, and the retrieval
  SQL are all written from first principles, no LangChain/LlamaIndex.

## How retrieval works

Pure vector search matches *meaning* well but blurs exact tokens — search for a
term like `match_chunks` or `ModuleNotFoundError` and embeddings return chunks
that are *generally about* the topic, often ranking the chunk that literally
contains the term below one that doesn't. Keyword search is the opposite: precise
on exact terms, blind to paraphrases.

**Hybrid search runs both and fuses the results with Reciprocal Rank Fusion
(RRF).** The two methods score on incompatible scales (cosine similarity ~0–1 vs.
`ts_rank` ~0.06), so RRF ignores the scores and uses only *rank*: each retriever
awards a chunk `1 / (60 + rank)` points, and the points are summed. A chunk both
methods rank well beats a chunk only one method loves — retrieval by consensus.

The fusion lives in the `hybrid_match_chunks` SQL function
(`backend/sql/schema.sql`); the app passes each question down both paths — as raw
text for keyword matching and as a 1536-dim vector for semantic matching.

## Structure

```
.
├── backend/                FastAPI service (RAG pipeline + API)
│   ├── app/
│   │   ├── main.py         endpoints: /health, /seed, /ask, /upload
│   │   ├── rag.py          embed, hybrid retrieve, pick_best, generate, seed
│   │   ├── chunker.py      word-based chunker with overlap
│   │   ├── ingest.py       PDF / text extraction for uploads
│   │   └── documents.py    default knowledge base
│   ├── sql/schema.sql      database schema + retrieval functions
│   └── requirements.txt
└── frontend/               Next.js chat UI
    └── app/                layout, page, styles
```

## Setup

### 1. Database (Supabase)

Create a Supabase project, then run `backend/sql/schema.sql` in the SQL Editor.
It creates the `rag_chunks` table, the full-text index, and both retrieval
functions (`match_chunks` and `hybrid_match_chunks`).

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
uvicorn app.main:app --reload --port 8000   # run from backend/, note app.main
```

`.env` needs: `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `GEMINI_EMBED_MODEL`,
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

The knowledge base starts empty — see [Adding your own knowledge](#adding-your-own-knowledge) below.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000 — ask questions, or use **Upload** to add a document.

## Adding your own knowledge

The knowledge base starts empty. Add content two ways:

- **Upload files** from the UI (or `POST /upload`) — PDF, `.txt`, or `.md`. They
  are parsed, chunked, embedded, and searchable immediately.
- **Edit `backend/app/documents.py`** — add entries to `DEFAULT_DOCUMENTS`, each
  with a `base_id`, `source`, and `text`, then run `POST /seed` to load them.

## Notes

- Embeddings use `gemini-embedding-001` truncated to **1536 dimensions**, which
  must match the `vector(1536)` column.
- Secrets live only in `.env` / `.env.local`, which are gitignored. Never commit them.
