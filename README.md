# RepoMind

Chat with any public GitHub repository. Paste a URL, ask questions in plain English, and get answers grounded in the actual codebase — with file and function citations for every claim.

## Overview

RepoMind indexes a repository's code and documentation, then answers natural-language questions about it using retrieval-augmented generation (RAG). Every answer traces back to specific files, functions, and line ranges — no hallucinated APIs, no guessing.

The core engineering bet: **exact symbol lookups and natural-language questions need different retrieval strategies.** Asking "what does `raise_for_status` do" and asking "how does this library handle errors" are fundamentally different queries — one needs lexical matching, the other needs semantic understanding. RepoMind runs both in parallel and fuses the results.

## Architecture

```
GitHub URL
    │
    ▼
┌─────────────────┐
│  Fetch & Filter  │  GitHub Trees API + raw content fetch
└────────┬─────────┘
         ▼
┌─────────────────┐
│     Chunking     │  AST-based (Python) / tree-sitter (JS, TS, Go, Java, Rust, C/C++)
└────────┬─────────┘  Docs split by heading
         ▼
┌─────────────────┐
│    Embedding     │  OpenAI text-embedding-3-small
└────────┬─────────┘
         ▼
┌─────────────────┐
│  Vector Store    │  Qdrant — dense + sparse (BM25) vectors per chunk
└────────┬─────────┘
         ▼
    [ Question ]
         │
         ▼
┌─────────────────┐
│  Query Rewrite   │  LLM expands vague questions into retrieval-friendly queries
└────────┬─────────┘
         ▼
┌─────────────────┐
│  Hybrid Search   │  BM25 + dense search, fused via Reciprocal Rank Fusion (RRF)
└────────┬─────────┘
         ▼
┌─────────────────┐
│    Reranking     │  Cross-encoder (bge-reranker-base) — top 20 → top 5
└────────┬─────────┘
         ▼
┌─────────────────┐
│    Generation    │  LLM answers strictly from retrieved context, cites sources
└─────────────────┘
```

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI | Async, typed, minimal boilerplate for a two-route API |
| Vector DB | Qdrant | Native hybrid search (BM25 + dense) with built-in RRF fusion — no manual fusion logic needed |
| Embeddings | OpenAI `text-embedding-3-small` | Strong quality-to-cost ratio; one consistent model across indexing and querying |
| Code chunking | Python `ast` + `tree-sitter` | Real AST parsing per language instead of naive line-splitting; never splits a function mid-body |
| Reranking | `bge-reranker-base` (cross-encoder) | Free, local, meaningfully improves precision on the final top-5 sent to the LLM |
| Generation | GPT-4o-mini | Cost-efficient for grounded, citation-constrained answers |
| Frontend | React + TypeScript + Vite | Fast dev loop, typed API contracts with the backend |

## How Hybrid Search Works

Each chunk is stored with two vector representations:

- **Dense vector** — semantic embedding, captures meaning and paraphrase ("how do I authenticate" ≈ "sending credentials")
- **Sparse vector (BM25)** — lexical, captures exact terms ("raise_for_status" matches literally, even with no semantic similarity to the question)

At query time, both searches run in parallel against the same filtered set (scoped to one repo), and Qdrant fuses the two ranked lists using **Reciprocal Rank Fusion (RRF)** — a chunk ranked highly by either method surfaces near the top, without needing to tune relative score weights.

The fused top-20 candidates are then passed through a cross-encoder reranker, which reads the question and each candidate together (rather than comparing precomputed embeddings) for a more precise final top-5.

## Evaluation

A hand-written test set (`eval/test_queries.json`) checks whether the expected source file appears in the top-5 results, comparing hybrid search against dense-only (vector) search.

| Method | Hit rate (top-5, n=15) |
|---|---|
| Vector-only | 87% |
| Hybrid (BM25 + dense + RRF) | 73% |

**Honest takeaway:** on this query mix — mostly natural-language questions — dense-only search outperformed hybrid. RRF fusion can down-rank a strong semantic match when BM25 finds no literal keyword overlap and returns unrelated high-lexical-score noise. Hybrid's advantage is concentrated in short, exact-symbol queries (e.g. `HTTPAdapter`, `PreparedRequest class`), where both methods tied. The eval also surfaced a chunking gap: two misses (`raise_for_status`, `iter_content`) were single methods nested inside a class, which the current chunker keeps bundled with the parent class rather than as separately retrievable units.

This is the result of measuring rather than assuming.

## Usage

1. Paste a public GitHub repository URL and index it.
2. Ask questions in plain English.
3. Every answer includes clickable citations: file path, function/class name, and line range.

## Roadmap

- Method-level chunking (split class bodies into per-method chunks with class context preserved in metadata)
- Incremental re-indexing based on file diffs
- Streaming responses in the chat UI
- Support for private repositories via authenticated cloning

## Project Structure

```
repo-chat/
├── backend/
│   ├── main.py              # FastAPI routes
│   ├── rag_pipeline.py      # index_repo() + query()
│   ├── github_fetch.py      # repo fetching via GitHub API
│   ├── chunking/
│   │   ├── code_chunker.py  # AST (Python) + tree-sitter (multi-language)
│   │   └── doc_chunker.py   # heading-based markdown/doc splitting
│   ├── embeddings.py        # OpenAI embedding wrapper
│   ├── vector_store.py      # Qdrant client, hybrid search
│   ├── rerank.py            # cross-encoder reranking
│   └── query_rewrite.py     # LLM query expansion for vague questions
├── eval/
│   ├── test_queries.json    # hand-labeled test set
│   └── run_eval.py          # hybrid vs. vector-only comparison
└── frontend/                # React + TypeScript chat UI
```