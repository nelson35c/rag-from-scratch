-- RAG From Scratch — database schema
--
-- Run this once on a fresh Supabase project (SQL Editor → New query → paste →
-- Run). It creates everything the backend needs: the chunks table, a full-text
-- column for keyword search, and the two retrieval functions.

-- ---------------------------------------------------------------------------
-- 1. pgvector — lets Postgres store and compare embeddings
-- ---------------------------------------------------------------------------
create extension if not exists vector;

-- ---------------------------------------------------------------------------
-- 2. The chunks table
--
--   embedding : the 1536-dim vector (must match gemini-embedding-001 truncated
--               to dimensions=1536).
--   fts       : a generated tsvector for keyword search. Postgres fills it in
--               automatically from the text column, for existing and future
--               rows — no application code involved. The two-argument
--               to_tsvector(...) form is required (it is immutable, which
--               generated columns need).
-- ---------------------------------------------------------------------------
create table rag_chunks (
    id          bigserial primary key,
    chunk_id    text not null unique,
    source      text not null,
    text        text not null,
    embedding   vector(1536),
    created_at  timestamptz default now(),
    fts         tsvector generated always as (to_tsvector('english', "text")) stored
);

-- Keyword-search index (GIN is built for "which rows contain this word?").
create index rag_chunks_fts_idx on rag_chunks using gin (fts);

-- Optional at small scale: a vector index for faster similarity search. Uncomment
-- once you have thousands of rows; below that, a sequential scan is fine.
-- create index rag_chunks_vec_idx
--     on rag_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ---------------------------------------------------------------------------
-- 3. Vector-only search (the original / baseline retriever)
--
-- Returns the closest chunks by cosine similarity. <=> is pgvector's cosine
-- distance; 1 - distance = similarity. Kept for comparison against hybrid.
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- 4. Hybrid search with Reciprocal Rank Fusion (the retriever the app uses)
--
-- Runs vector search AND keyword search, then fuses them by RANK (not score,
-- since cosine similarity and ts_rank live on incompatible scales). Each list
-- awards a chunk 1/(rrf_k + rank) points; the points are summed. A chunk both
-- methods rank well beats a chunk only one method loves.
--
--   query_text      : the raw question, for keyword matching
--   query_embedding : the question's vector, for semantic matching
--   rrf_k           : fusion constant; 60 is the standard default
-- ---------------------------------------------------------------------------
create or replace function hybrid_match_chunks (
    query_text text,
    query_embedding vector(1536),
    match_count int default 6,
    rrf_k int default 60
)
returns table (chunk_id text, source text, text text, score float)
language sql
as $$
with vector_hits as (
    select
        rag_chunks.chunk_id,
        row_number() over (order by rag_chunks.embedding <=> query_embedding) as rank_pos
    from rag_chunks
    order by rag_chunks.embedding <=> query_embedding
    limit 30
),
keyword_hits as (
    select
        rag_chunks.chunk_id,
        row_number() over (
            order by ts_rank(rag_chunks.fts, websearch_to_tsquery('english', query_text)) desc
        ) as rank_pos
    from rag_chunks
    where rag_chunks.fts @@ websearch_to_tsquery('english', query_text)
    limit 30
)
select
    c.chunk_id,
    c.source,
    c.text,
    (
        coalesce(1.0 / (rrf_k + v.rank_pos), 0.0)
      + coalesce(1.0 / (rrf_k + k.rank_pos), 0.0)
    )::float as score
from rag_chunks c
left join vector_hits  v on v.chunk_id = c.chunk_id
left join keyword_hits k on k.chunk_id = c.chunk_id
where v.chunk_id is not null or k.chunk_id is not null
order by score desc
limit match_count;
$$;
