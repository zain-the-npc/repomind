# 🧠 RepoMind

Paste a GitHub repo. Ask it anything. Get answers with real file + line citations — no hallucinated APIs.

**🔗 Live:** [repomind-psi-flame.vercel.app](https://repomind-psi-flame.vercel.app)
*(free-tier backend — first request may take 30-60s to wake up)*

## Why

Exact symbol lookups (`raise_for_status`) and natural-language questions ("how does auth work?") need different search strategies — one's lexical, one's semantic. RepoMind runs both and fuses the results, instead of betting on one.

## How it works

```
GitHub URL → Fetch → Chunk (AST + tree-sitter) → Embed → Qdrant
                                                              │
Question → Rewrite → Hybrid Search (BM25 + dense, RRF) → Rerank → Answer + citations
```

## Stack

| Layer | Tool | Why |
|---|---|---|
| Vector DB | Qdrant | Native hybrid search + RRF fusion, no manual plumbing |
| Embeddings | `text-embedding-3-small` | Solid quality/cost, one model everywhere |
| Chunking | `ast` (Python) + `tree-sitter` (JS/TS/Go/Java/Rust/C/C++) | Never splits mid-function |
| Reranking | `bge-reranker-base` | Cross-encoder precision on final top-5 |
| Backend | FastAPI + SSE streaming | Typed, async, live token streaming |
| Frontend | React + TypeScript + Vite | — |

## 📊 The honest eval

Ran hybrid vs. vector-only on 15 hand-labeled queries:

| Method | Hit rate (top-5) |
|---|---|
| Vector-only | 87% |
| Hybrid (BM25 + dense + RRF) | 73% |

Hybrid **didn't** win here — mostly natural-language queries, and BM25 noise dragged RRF down. Hybrid's real edge showed on short exact-symbol queries (`HTTPAdapter`), where it tied vector-only. Also found a chunking gap: nested class methods aren't separately retrievable yet. Measured, not assumed. ✅

## ⚠️ Known limitation

Hosted on Render's free tier (512MB RAM) — tight for an ML pipeline running embeddings + reranker + LLM per request. Expect cold starts and occasional slowness. Same code, more headroom = solid. Clone locally for guaranteed stability.

## Roadmap

- Method-level chunking (per-method, not per-class)
- Incremental re-indexing on file diffs
- Private repo support

## Structure

```
backend/
├── main.py              # FastAPI routes
├── rag_pipeline.py       # index_repo() + query()
├── github_fetch.py
├── chunking/             # AST + tree-sitter
├── embeddings.py
├── vector_store.py       # Qdrant hybrid search
├── rerank.py
└── query_rewrite.py
eval/                     # hybrid vs vector-only test
frontend/                 # React chat UI
```