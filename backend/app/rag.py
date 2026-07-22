import os
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client
from app.chunker import chunk_text

load_dotenv()

ai = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)


def embed(text):
    response = ai.embeddings.create(
        model=os.getenv("GEMINI_EMBED_MODEL"),
        input=text,
        dimensions=1536,
    )
    return response.data[0].embedding


def embed_many(texts):
    response = ai.embeddings.create(
        model=os.getenv("GEMINI_EMBED_MODEL"),
        input=texts,
        dimensions=1536,
    )
    return [item.embedding for item in response.data]


def retrieve(question, top_k=6):
    question_vector = embed(question)
    results = supabase.rpc("match_chunks", {
        "query_embedding": question_vector,
        "match_count": top_k,
    }).execute()
    return results.data


def pick_best(chunks, limit=4):
    seen = set()
    picked = []
    for chunk in chunks:
        doc = chunk["chunk_id"].split("#")[0]
        if doc not in seen:
            picked.append(chunk)
            seen.add(doc)
        if len(picked) >= limit:
            break
    return picked


def answer(question):
    chunks = retrieve(question)
    if not chunks:
        return {"answer": "I don't have any information to answer that.", "citations": []}

    context_chunks = pick_best(chunks)
    context = "\n\n".join(f"[{c['chunk_id']}] {c['text']}" for c in context_chunks)

    system_prompt = """You answer questions using ONLY the context provided.

Rules:
1. Use only facts found in the context. Never invent information.
2. After each fact you use, cite its source like [returns#1].
3. If the context does not contain the answer, say you don't know.
4. Be concise and friendly."""

    user_prompt = f"""Context:
{context}

Question: {question}"""

    response = ai.chat.completions.create(
        model=os.getenv("GEMINI_CHAT_MODEL"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    return {
        "answer": response.choices[0].message.content,
        "citations": [c["chunk_id"] for c in context_chunks],
    }


def seed(documents):
    all_chunks = []
    for doc in documents:
        all_chunks.extend(
            chunk_text(doc["text"], source=doc["source"], base_id=doc["base_id"])
        )

    texts = [c["text"] for c in all_chunks]
    for chunk, embedding in zip(all_chunks, embed_all(texts)):
        chunk["embedding"] = embedding

    supabase.table("rag_chunks").upsert(all_chunks, on_conflict="chunk_id").execute()
    return len(all_chunks)

def embed_all(texts, batch_size=100):
    embeddings = []
    for start in range(0, len(texts), batch_size):
        embeddings.extend(embed_many(texts[start:start + batch_size]))
    return embeddings