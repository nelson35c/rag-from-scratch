from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag
from documents import DEFAULT_DOCUMENTS

app = FastAPI(title="RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/seed")
def seed_endpoint():
    count = rag.seed(DEFAULT_DOCUMENTS)
    return {"chunks_stored": count}


@app.post("/ask")
def ask_endpoint(request: AskRequest):
    return rag.answer(request.question)