from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import rag, ingest
from app.documents import DEFAULT_DOCUMENTS

app = FastAPI(title="RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str
    mode: str = "hybrid"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/seed")
def seed_endpoint():
    count = rag.seed(DEFAULT_DOCUMENTS)
    return {"chunks_stored": count}


@app.post("/ask")
def ask_endpoint(request: AskRequest):
    return rag.answer(request.question, mode=request.mode)

@app.post("/upload")
def upload_endpoint(file: UploadFile = File(...)):
    name = file.filename or "upload"
    text = ingest.extract_text(name, file.file)

    if not text.strip():
        return {"error": "No readable text found in that file. "}

    document = {
        "base_id": ingest.make_base_id(name),
        "source": name,
        "text": text,
    }
    chunks_stored = rag.seed([document])

    return {
        "filename": name, 
        "base_id": document["base_id"],
        "chunks_stored": chunks_stored,
    }
