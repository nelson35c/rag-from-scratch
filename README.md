# RAG From Scratch

A Retrieval-Augmented Generation (RAG) application built from scratch — no RAG
framework — to learn how retrieval, embeddings, vector search, and grounded
generation actually work under the hood. It answers questions over your own
notes and cites the exact chunks each answer is built from.

- **Backend:** FastAPI + Supabase (pgvector) + Gemini (via the OpenAI-compatible endpoint)
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS
- **Pipeline:** chunk → embed → store → retrieve → augment → generate, with citations

## Structure

```
.
├── backend/      FastAPI service (RAG pipeline + API)
│   ├── main.py        API endpoints (/health, /seed, /ask)
│   ├── rag.py         embed, retrieve, pick_best, generate, seed
│   ├── chunker.py     word-based chunker with overlap
│   └── documents.py   the knowledge base
└── frontend/     Next.js chat UI
    └── app/           layout, page, styles
```

## Setup

### 1. Database (Supabase)

Create a Supabase project and run this in the SQL Editor:

```sql
create extension if not exists vector;

create table rag_chunks (
    id bigserial primary key,
    chunk_id text not null unique,
    source text not null,
    text text not null,
    embedding vector(1536),
    created_at timestamptz default now()
);

create or replace function match_chunks (
    query_embedding vector(1536),
    match_count int default 6
)
returns table (chunk_id text, source text, text text, similarity float)
language sql
as $$
    select
        rag_chunks.chunk_id,
        rag_chunks.source,
        rag_chunks.text,
        1 - (rag_chunks.embedding <=> query_embedding) as similarity
    from rag_chunks
    order by rag_chunks.embedding <=> query_embedding
    limit match_count;
$$;
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in your keys
python -m uvicorn main:app --reload --port 8000
```

Seed the knowledge base once the server is up: `POST http://localhost:8000/seed`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Notes

- Embeddings use `gemini-embedding-001` truncated to **1536 dimensions**, which
  must match the `vector(1536)` column.
- Secrets live only in `.env` / `.env.local`, which are gitignored. Never commit them.
