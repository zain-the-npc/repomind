"""
FastAPI app. Two routes:
  POST /index  {repo_url} -> {repo_id}
  POST /chat   {repo_id, question} -> {answer, sources}
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag_pipeline

app = FastAPI(title="codebase-rag")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before real deploy
    allow_methods=["*"],
    allow_headers=["*"],
)


class IndexRequest(BaseModel):
    repo_url: str


class IndexResponse(BaseModel):
    repo_id: str


class ChatRequest(BaseModel):
    repo_id: str
    question: str


class Source(BaseModel):
    file: str
    function: str | None
    lines: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.post("/index", response_model=IndexResponse)
def index(req: IndexRequest):
    try:
        repo_id = rag_pipeline.index_repo(req.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
    return IndexResponse(repo_id=repo_id)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = rag_pipeline.query(req.repo_id, req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    return ChatResponse(**result)


@app.get("/health")
def health():
    return {"status": "ok"}